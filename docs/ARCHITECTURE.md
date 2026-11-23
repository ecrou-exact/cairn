# Architecture

> Status: **proposed** (Phase 1). Becomes the reference once the owner approves it.
> Follows `docs/OWNER_CONVENTIONS.md` and the decisions in `docs/DECISIONS.md`.

---

## 1. Processes

```
                 Browser (Jinja + Custom Elements + Pivotick + Vitrine)
                    │  HTTPS/HTTP on 127.0.0.1   ▲ SSE /events
                    ▼                            │
┌──────────────────────────── web ─────────────────────────────┐
│ Flask app (gunicorn on Linux/macOS, waitress on Windows)      │
│  features/* (HTML)   api/* (REST, blueprints)    /mcp (MCP)   │
│                 └──────── core services ────────┘            │
└───────────────┬───────────────────────────────┬──────────────┘
                │ SQLAlchemy                     │ /events polls the event table
                ▼                                ▼
        PostgreSQL (prod) / SQLite (dev)   ◄── event table (written by web and worker)
                ▲
┌───────────────┴──────────── worker ──────────────────────────┐
│ manage.py worker: job runner (lanes) + daily jobs + supervisors│
│  ├─ agent lane: Claude Agent SDK runs (asyncio loop / run)    │
│  ├─ io lane: GitHub sync, URL fetch, notifications            │
│  ├─ module lane: automations and action modules               │
│  └─ instance supervisor: child processes, health checks, ports│
└───────────────────────────────────────────────────────────────┘
        │ subprocess (arg lists, no shell)        │ HTTPS
        ▼                                         ▼
  git worktrees · project instances        GitHub API · Anthropic API
```

- **web** never runs long work; it enqueues jobs and streams events.
- **worker** is a separate process (same reasons as Rulezet's `worker.py`: no web timeouts on long jobs, no recycling mid-job, no GIL contention).
- Both read the same config and DB. On SQLite only one worker is allowed (`WorkerLock`: PID + start time, checked with psutil).
- Start both: `python manage.py start` (or `serve`) and `python manage.py worker`.
- Child processes (Claude runs, instances) are tracked by PID + start time with `psutil`, so supervision works on Linux, macOS and Windows; on Linux/macOS they get their own process group so a stop kills the whole tree.

## 2. Code layout

```
app/
  __init__.py                  create_app(start_worker=False)
  api/                         REST blueprints under /api (thin: validate with schema/, call core)
  mcp/                         MCP server: tool definitions → core services
  core/
    db_class/                  models (one module per feature)
    schema/                    pydantic models = the single source of field definitions
    jobs/                      jobs_core (lifecycle), registry, context (log/progress/cancel), worker
    utils/                     decorators, log_action, settings, events (SSE), listing (server-side lists)
  features/
    account/ admin/ settings/  (from the owner's flask-launchpad patterns)
    dashboard/ project/ task/ dependency/ resource/ graph/
    calendar/ timeline/ activity/
    chat/ run/ skill/ account_ai/ usage/
    github/ instance/ module/ alert/ jobs/
      <feature>.py  <feature>_core.py
  jobs/                        @register_handler('<type>') handlers, one module per domain (system.py…)
  modules/                     built-in automation + action modules (plugin registry)
  templates/<feature>/
  static/{css,js}/{components,<feature>}/
  static/vendor/               bootstrap, fontawesome, fonts, pivotick, vitrine (pinned, see vendor.json)
  settings/<key>.json          settings defaults (statuses, types, weights, ports…)
manage.py  wsgi.py
migrations/  tests/  docs/
```

## 3. Data model (summary)

All entities inherit `BaseEntity`: `id UUID`, `created_at`, `updated_at`, `created_by` (`user` | `claude:<run-id>` | `module:<id>`), `deleted_at` (soft delete).

| Entity | Key fields | Relations |
|---|---|---|
| `Project` | name, slug, description_md, status, colour, icon, github_repo, default_branch, local_path, stack[], links[], claude_instructions_md, context_file_mode | tags, resources, instance_defs, module_bindings |
| `Task` | title, description_md, type, status, priority, importance, urgency, start/due/do_on/completed dates, hard_deadline, estimate, actual, acceptance_md, claude_instructions_md, assignee, recurrence, branch, worktree_path, score (cached) + score_explain (json) | project, parent (self), checklist_items, corrections, comments, tags, custom_values, resources, github_links, runs |
| `Dependency` | kind (`blocks`, `relates`, `duplicates`, `follows`), from_task, to_task | cycle check on write (blocks/follows) |
| `ExternalCondition` | kind (review, upstream release, date, PR merged, free), payload json, resolved_at, auto_resolver | task |
| `Resource` | kind (url, file, image, snippet, tool, note, github), title, description_md, url, body (note / code / command), language, path, icon, tags, stored file (random name, original name, mime, size, sha256), meta json (page preview, GitHub reference, image size) — snapshot for Claude and image description come in Phase 5 | `ResourceLink` (resource, target_type project/task, target_id, note): one resource in the library, attached anywhere |
| `AgentRun` | status, account_id, model, skills[], modules[], prompt, session_id, worktree, branch, cost_usd, tokens json, started/ended, summary_md, scheduled_for | tasks (m2m), events, file_changes, permission_requests |
| `RunEvent` | run, seq, type, payload json | streamed to UI |
| `ChangeSet` / `ChangeSetItem` | origin (run/intake/module), status, op (create/update/delete/link), target, diff json, decision | applied atomically by core |
| `Module` / `ModuleBinding` / `ModuleExecution` | key, scope (global/project/task), settings json, auto/confirm, ordered steps, status, output | |
| `InstanceDef` / `Instance` | command (argv list), cwd, env (vault refs), port range, health URL, URL pattern / pid, port, status, started_at | project, task, github_link |
| `Account` (AI / GitHub / other) | provider, label, vault_ref, default_model, quota | |
| `Secret` | name, ciphertext, nonce, key_version | never leaves the vault service |
| `Alert` | type, severity, message, link, read_at | |
| `Job` | type, lane, status, progress, attempts, run_after, timeout, result, logs | |
| `History` | entity_type, entity_id, actor, action, diff json, batch_id | undo = replay inverse diff of a batch |
| `Setting` / `SettingHistory` | key, value, base_value | Rulezet pattern |
| `CalendarBlock` | owner (me/claude), task, start, end, recurrence | scheduled work and scheduled runs |

Configurable lists (types, statuses, workflow transitions, priorities, score weights, port range, branch naming) are settings, validated by the same pydantic schemas used by forms, API and MCP tools.

## 4. Key flows

**Edit anything (form, table, graph, Claude, module)** → `core.<feature>.update()` → validation (schema + business rules: cycles, workflow) → DB write + `History` row + `log_action` → `events.publish(entity.changed)` → SSE → every open view patches itself (graph uses `updateData` / `addNode` / `removeEdge`).

**Claude run** → `run_core.enqueue()` → job on agent lane (respects concurrency limit, account quota, task not blocked) → worker creates a worktree (`git worktree add`, branch `<type>/<task-slug>`), writes the context file, builds `ClaudeAgentOptions` (`cwd` = worktree, `add_dirs` allowlist, `system_prompt` preset + appended hard rules, `mcp_servers` = app MCP over HTTP with a run-scoped token, `can_use_tool` + `PreToolUse` hooks → permission requests in UI, `env` with the run's API key only) → streams messages into `RunEvent` → SSE. Controls: stop = `interrupt()` + `disconnect()`; pause = interrupt + keep `session_id`, resume = new client with `resume`; new instruction = `query()` on the live client.

**Planning intake** → chat message with attachments → run with intake prompt; fetched content passed as clearly delimited untrusted data → Claude calls `propose_changeset` (not direct writes) → owner reviews item by item → `changeset_core.apply()` in one transaction → graph updates live.

**Module** → domain event (`task.status_changed`, `github.pr_merged`…) → registry matches bindings → execution job → each step declares the permissions it needs; side-effect steps wait for confirmation unless the binding is `auto`.

## 5. Realtime
- `GET /events?topics=job,setting` (SSE), one connection per tab (`static/js/core/events.js`), authenticated by session, filtered server-side by topic prefix.
- Producer: `events.publish(type, payload)` adds an `event` row in the caller's transaction; the stream polls it every second (D-020). `Last-Event-ID` (or `?after=`) resumes; id gaps are waited on for 5 s so nothing is skipped.
- Live pages pass the last event id read before their data (`<meta name="cn-events-after">`); `<cn-live-status>` in the header shows the connection state.
- Event types so far: `job.changed`, `job.progress`, `job.log`, `setting.changed`, `task.changed`, `project.changed`, `resource.changed`, `comment.changed` (with the `kind:id` targets it is attached to).

## 3b. Planning (Phase 3)
- Code: `features/projects/` and `features/tasks/` (`tasks_core`, `dependencies_core` with `refresh_derived`, `score_core`, `quickadd_core`, `timer_core`, `workflow`), `features/trash/`, `features/history/`; API in `api/planning_api.py`; schemas in `core/schema/planning.py`.
- **Score** (`score_core.py`): `project weight × Σ weight × value`, each value in 0..1 — priority (critical 1, high .7, medium .4, low .1), importance and urgency ((n−1)/4), deadline (1 when due or late, down to 0 at `deadline_horizon_days`), hard deadline (the deadline value again), unblocks (open tasks waiting on it transitively, /5, max 1), quick win (1/(1+h/4), .5 without estimate), age (days/30, max 1). Weights: setting `tasks.score_weights`. Every task keeps the breakdown shown on its page.
- **What should I do now?** open, not blocked, not waiting, `do_on`/`start_on` not in the future, by score.
- **History:** one batch per owner action, undo per batch (D-024). Soft delete everywhere; hard delete only from `/trash`.
- **Front end:** `cn-quick-add` (live parse preview), `cn-picker` (combobox over `/api/search`, tasks or resources), `cn-upload` (Vitrine `vt-upload`: drop, choose or paste files), `cn-palette` (Ctrl/Cmd+K), `cn-timer`, `cn-form-guard` (unsaved changes), `cn-confirm`.

## 3c. Resources (Phase 3)
- Code: `features/resources/` — `resources_core` (create, upload with SHA-256 reuse, attach / detach, trash, undo), `storage_core` (upload folder, random names, size check while reading, images re-encoded by Pillow, orphan clean-up in `system.prune`), `preview_core` (page head parser, GitHub address parser); job `resources.preview` (lane io); API `api/resources_api.py`; schemas `core/schema/resources.py`.
- Files live in `<data dir>/uploads/ab/ab…` (`CAIRN_UPLOAD_DIR`). Served by `/resources/<id>/file`: images inline as their re-encoded type, everything else `application/octet-stream` as an attachment; always `CSP: default-src 'none'; sandbox` and `nosniff`.
- Pages: `/resources` library (cards/table, kind and "used" filters, sort by uses), resource page, form per kind; a resources panel on task and project pages (paste a link, pick from the library, drop / paste files, new note / snippet / tool / path). Settings `resources.max_upload_mb`, `resources.previews`.
- Jobs queued inside a change batch join it: undoing the change cancels the job if it has not started (`job.enqueue` / `job.cancel` / `job.retry` have inverses).

## 3d. Comments, corrections, brief (Phase 3)
- Code: `features/comments/` (`comments_core`, routes posting from task / project pages), `features/tasks/brief_core.py`; API `api/comments_api.py`; schemas `core/schema/comments.py`; model `db_class/comment.py`.
- `brief_core.task_brief(task)` is the single source of what a run on a task receives (D-028).
- `related_core.related_for(task)`: related tasks, resources and schedule fit with reasons (D-029); future MCP tool `find_related`.

## 4b. Graph (Phase 4)
- `features/graph/graph_core.py`: `_level()` decides the cards of a view (project, root, level, state, tag, closed) and which card stands for any task in scope; `graph_data(...)` → Pivotick raw nodes (pinned `x/y/fx/fy` from `plan_layout`) and edges (dependencies lifted to the cards + subtasks), the critical path, the number of steps and the breadcrumb; `find(text, ...)` → tasks whose title matches, each with its card and the cases in between. `project_plan()` → the plan of projects (`/api/graph?view=projects`). `/api/graph` and `/api/graph/find` share one query parser. No Graph page (D-044): the plan of projects is on `/projects`, a project's plan in its Plan tab (`graph.graph_view()` reads the filters for both), `/graph?root=` is a case's own graph; pages with a graph get the graph CSP (`style-src-attr`).
- `features/projects/project_links_core.py`: project order links (`ProjectLink`), acyclic via `core/utils/graphs.path_between` (shared with task dependencies), logged and undoable; `/api/project-links`.
- `static/js/graph/graph.js`: Pivotick in `viewer` mode, cards from `node.getData()`, Cairn chrome (zoom, find, link mode, critical path, side panel, peek), live diffing; styles in `static/css/graph/graph.css` (`--pvt-*` bridge included). D-035.

## 5b. Lists, settings, display
- **Lists:** a feature declares a `ListSpec` (sortable, searchable, filters, tiebreak) and calls `run_list(spec, query, request.args)`; anything undeclared in the URL is ignored. Macros in `templates/macros/list.html` (search and view switch visible, filters folded in a `<details>` panel), styles in `css/components/list.css`.
- **Uploads:** `<cn-upload>` (`js/components/cn-upload.js`) wraps Vitrine's `vt-upload`, styled through its parts in `css/components/upload.css`; `paste="page"` adds paste and drop anywhere on the page. The API returns the same page as JSON (`schema/common.page_dict`).
- **Settings:** defaults in `app/settings/<key>.json`, overrides in `setting_override` (with the default they were made from, to flag "new default"). Typed by `SETTING_TYPES`; page `/settings`, API `/api/settings`.
- **Code, JSON, logs:** always `<cn-vitrine>` (D-019).

## 6. Cross-platform rules
See D-001. Paths via `pathlib`/`platformdirs`; processes via `psutil`; no `fork`-only code; subprocess argument lists only; `.gitattributes` forces LF; CI on Ubuntu, macOS and Windows.

## 4c. Claude in a terminal (Phase 5, D-050)
- `features/claude/pty_host.py`: one program in a pseudo-terminal (pywinpty / ptyprocess). `terminal_core.py`: sessions (start in a project's folder, input, resize, stop, output kept for resuming, end recorded), `ClaudeSession` rows. `transcript_core.py`: context use, model, title and the last steps (what you asked, the tools Claude called, in words) from Claude Code's transcripts; sessions outside Cairn via `psutil`, with the editor or terminal they run in. `claude_core.py`: the overview, running instances with the end of their log (`terminal_core.preview`) (D-054). A conversation open outside Cairn (`transcript_core.open_elsewhere`, from Claude Code's registry) is moved, never opened twice; terminals are closed by signals on Linux / macOS and at exit (`close_all`) (D-055).
- Pages `/claude` (overview), `/claude/sessions/<id>` (terminal, nonce CSP), SSE `/claude/sessions/<id>/stream`; API `/api/claude/sessions` (list, start), `…/input`, `…/resize`, `…/stop`, `…/link`, `/api/claude/outside/stop`. Usage left: `limits_core.py`, written by `statusline.py` (D-056). Library skills as a per-session plugin: `skills_core.py` (D-058). Main Claude and notes: `main_core.py` (D-060), work handed to a project's Claude: `handover_core.py` (D-068); its panel on every page: `cn-claude-dock.js`, `/claude/sessions/<id>/panel` (D-063). Changesets: `features/changesets/` (D-071). Tools page: `tools_core.py` (D-072). Live graph `/claude/live`, `/api/claude/live`: `live_core.py`, `claude/live-graph.js` on `graph/stage.js`, shared with the plan's graph (D-059). Front: `components/cn-terminal.js` (xterm.js), `claude/overview.js`, `core/claude-count.js` (menu count).
- `features/claude/mcp_server.py`: Cairn's MCP server (`manage.py mcp`, stdio), built per session; tools call the planning cores as `claude:<session>` (D-052).
- `features/instances/instances_core.py`: a project's commands (`ProjectInstance`), run through `terminal_core.open_session(kind="instance")`; ports via psutil. Tab on the project page, `/api/instances` (D-053). Those outside Cairn and their logs: `found_core.py`, `follow.py` (D-061). Each runs under `runner.py`, seen by `survivor.py`, and outlives Cairn (D-070).
