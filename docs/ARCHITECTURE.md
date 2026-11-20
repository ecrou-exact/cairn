# Architecture

> Status: **proposed** (Phase 1). Becomes the reference once the owner approves it.
> Follows `docs/OWNER_CONVENTIONS.md` and the decisions in `docs/DECISIONS.md`.

---

## 1. Processes

```
                 Browser (Jinja + Vue 3 UMD + Pivotick + Vitrine)
                    │  HTTPS/HTTP on 127.0.0.1   ▲ SSE /events
                    ▼                            │
┌──────────────────────────── web ─────────────────────────────┐
│ Flask app (gunicorn on Linux/macOS, waitress on Windows)      │
│  features/* (HTML)   api/* (REST, Flask-RESTX)   /mcp (MCP)   │
│                 └──────── core services ────────┘            │
└───────────────┬───────────────────────────────┬──────────────┘
                │ SQLAlchemy                     │ NOTIFY / in-process bus
                ▼                                ▼
        PostgreSQL (prod) / SQLite (dev)   ◄── events table + LISTEN/NOTIFY
                ▲
┌───────────────┴──────────── worker ──────────────────────────┐
│ worker.py: job runner (lanes) + APScheduler + supervisors     │
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
- Both read the same config and DB. On SQLite only one worker is allowed (file lock).
- Child processes (Claude runs, instances) are tracked by PID + start time with `psutil`, so supervision works on Linux, macOS and Windows; on Linux/macOS they get their own process group so a stop kills the whole tree.

## 2. Code layout

```
app/
  __init__.py                  create_app(start_worker=False)
  api/                         REST namespaces (thin, call core)
  mcp/                         MCP server: tool definitions → core services
  core/
    db_class/                  models (one module per feature)
    schema/                    pydantic models = the single source of field definitions
    utils/                     decorators, log_action, settings, vault, events, paths
  features/
    account/ admin/ settings/  (from the owner's flask-launchpad patterns)
    dashboard/ project/ task/ dependency/ resource/ graph/
    calendar/ timeline/ activity/
    chat/ run/ skill/ account_ai/ usage/
    github/ instance/ module/ alert/ jobs/
      <feature>.py  <feature>_core.py
  jobs/handlers/               @register_handler('<type>') per domain
  modules/                     built-in automation + action modules (plugin registry)
  templates/<feature>/
  static/{css,js}/{components,<feature>}/
  static/vendor/               bootstrap, fontawesome, vue, pivotick, vitrine (pinned)
  config/<key>.json            settings defaults (statuses, types, weights, ports…)
worker.py  manage.py  launch.sh  wsgi.py
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
| `Resource` | type (url, file, image, snippet, tool, note, github), title, payload json, snapshot (for Claude, sandboxed), description (image) | many-to-many with projects/tasks (library) |
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
- `GET /events` (SSE), one connection per tab, authenticated by session, filtered server-side by what the page subscribes to.
- Producer: `events.publish(type, payload)` writes to `event` table and `NOTIFY` (PostgreSQL) or an in-process queue (SQLite, single process dev mode). `Last-Event-ID` replays missed events.

## 6. Cross-platform rules
See D-001. Paths via `pathlib`/`platformdirs`; processes via `psutil`; no `fork`-only code; subprocess argument lists only; `.gitattributes` forces LF; CI on Ubuntu, macOS and Windows.
