# Decisions

> Format: ID · date · status (proposed / accepted / superseded) · context · options · choice · reason.
> "Proposed" decisions wait for owner approval at the end of Discovery.

---

## D-001 · 2026-11-20 · accepted — Target platform
- **Context:** owner deploys on Ubuntu Linux; the project is open source and must work everywhere.
- **Choice:** Ubuntu is the reference platform (install script, systemd, Docker Compose); Linux, macOS and Windows are all supported for running and developing.
- **Consequences:** `pathlib` + `platformdirs`; `psutil` for processes and ports; no `fork`-only libraries as hard requirements; no shell strings (`subprocess` with arg lists); line endings via `.gitattributes`; CI matrix on ubuntu-latest / macos-latest / windows-latest; Claude Agent SDK sandbox used where the OS supports it (Linux/macOS), stricter permission prompts elsewhere.

## D-002 · 2026-11-20 · proposed — Backend stack
- **Choice:** Python 3.12+, Flask 3, SQLAlchemy 2, Alembic (Flask-Migrate), PostgreSQL in prod / SQLite in dev, uv + `pyproject.toml` + `uv.lock`.
- **Reason:** same stack as the owner's Rulezet (Flask 3, SQLAlchemy, PostgreSQL, uv), all cross-platform.

## D-003 · 2026-11-20 · proposed — Background jobs
- **Options:** Celery + Redis (heavy, weak Windows support) · RQ + Redis (needs `fork`, not on Windows) · Dramatiq + Redis · **DB-backed queue + dedicated worker process + APScheduler** (Rulezet's pattern).
- **Choice:** DB-backed queue (lanes, retries/backoff, timeouts, cancellation, `SELECT … FOR UPDATE SKIP LOCKED` on PostgreSQL, single-worker lock on SQLite) in a separate `worker.py` process; APScheduler for scheduled/recurring items. Redis optional later for realtime fan-out only.
- **Reason:** no extra service, works on every OS, already proven in the owner's codebase, job state lives in the same DB as the Jobs page.

## D-004 · 2026-11-20 · proposed — Realtime
- **Choice:** Server-Sent Events (one stream per tab, typed events), backed by PostgreSQL `LISTEN/NOTIFY` (in-process bus on SQLite).
- **Reason:** one-way server→client is all views need; simpler and more CSP/proxy friendly than WebSockets; commands go through normal CSRF-protected POSTs.

## D-005 · 2026-11-20 · proposed — Claude integration
- **Choice:** official **Claude Agent SDK for Python** (`claude-agent-sdk`) with one `ClaudeSDKClient` per run, executed in the worker with its own asyncio loop.
- **Facts verified in docs (2026-11-20):** `ClaudeAgentOptions` has `model`, `cwd`, `add_dirs`, `allowed_tools`/`disallowed_tools`, `permission_mode`, `can_use_tool`, `hooks` (PreToolUse, PermissionRequest…), `mcp_servers` (in-process via `create_sdk_mcp_server`, or HTTP/SSE/stdio), `system_prompt` preset + `append`, `skills`, `setting_sources`, `resume`/`session_id`/`fork_session`, `max_turns`, `max_budget_usd`, `env`, `sandbox`. Client has `interrupt()`, `query()` mid-session, `set_model()`, `set_permission_mode()`. `ResultMessage` gives `total_cost_usd`, `usage`, `model_usage` (per model, incl. subagents).
- **Gaps to resolve:** no native pause → implement as interrupt + resume by session id; multi-account → per-run `env={"ANTHROPIC_API_KEY": …}` must be verified; claude.ai login cannot be offered by third-party apps → API keys (or Bedrock/Vertex/Foundry).
- **App MCP server:** exposed over HTTP (streamable) on localhost with a per-run token, so the same server serves the SDK runs and an external `claude` CLI; services shared with the REST API (one implementation per behaviour).

## D-006 · 2026-11-20 · proposed — Graph: Pivotick
- **Facts:** MIT, v3.0.0 on `main`, npm `pivotick` (ESM/UMD/IIFE + CSS), deps on d3 modules, DOMPurify, marked. Layouts force / tree (horizontal, radial) / structured; `nodeTypeAccessor`+`nodeStyleMap`, `edgeTypeAccessor`+`edgeStyleMap`, `renderNode`, badges, tiers; UI modes full/light/viewer/static; context menus per node/edge/canvas/selection; write-path hooks (`onBeforeNodeCreate`, `onBeforeEdgeCreate`, `isValidConnection`, `onBeforeDelete`, edit commits); runtime `addNode`/`addEdge`/`removeNode`/`removeEdge`; i18n incl. `fr`; Simplify clustering; node expansion; Font Awesome 7 icons.
- **Watch-outs:** constructor signature differs across docs pages (check source); programmatic mutations bypass hooks; no documented `update` method; adding nodes needs `reheat()`; canvas renderer experimental (use SVG); locale fixed per instance; no CDN → vendor via npm build.

## D-007 · 2026-11-20 · proposed — Code/Markdown/JSON display: Vitrine
- **Facts:** MIT, v0.14.0, pre-1.0, not on npm (install from GitHub tag or jsDelivr `gh/ecrou-exact/vitrine@0.14.0`). Components used here: `vt-code`, `vt-markdown`, `vt-json`, `vt-diff`, `vt-log`, `vt-terminal`, `vt-git`, `vt-job`. Strict CSP compatible (constructable stylesheets, Trusted Types policy `vitrine`), sanitised via DOMPurify with fail-closed self-test. Theming through 31 `--vt-*` colour tokens + typography/spacing tokens; `copy`/`download`/`search` toggles via `attr="false"`.
- **Choice:** per-component ES modules served from the app (self-hosted, pinned tag, SRI), wrapped in one app component; feed untrusted data through the `content`/`data` property, never inline markup.
- **Note:** Vitrine is the owner's own library — gaps found here can be fixed upstream directly.

## D-008 · 2026-11-21 · proposed — Frontend
- **Facts:** Rulezet, flask-launchpad and Flowintel all use Jinja + **Vue 3 UMD without build step** (`createApp` in templates, ES modules, `[[ ]]` delimiters), Bootstrap 5.3 and Font Awesome vendored in `static/`.
- **Choice:** same. Bootstrap 5.3, Font Awesome 7 Free (Pivotick's default icon font), Vue 3 UMD, all vendored and pinned. Pivotick is vendored from its npm `dist/` (no bundler needed). No SPA, no Node build in production; Node only for dev tooling (eslint, Playwright).
- **Calendar:** FullCalendar, wrapped as `CalendarView` like in Rulezet. **Charts:** ECharts (Rulezet `ChartViewer`). **Gantt:** to evaluate in Phase 10 (FullCalendar resource timeline is premium → candidates: Frappe Gantt (MIT) or a custom SVG timeline).

## D-009 · 2026-11-21 · proposed — Design skill
- **Compared:** Anthropic `frontend-design` (official, Apache-2.0, guardrails against the generic AI look, fast); UI/UX Pro Max (style/palette/font database, heavy on tokens and time); Impeccable (audit/critique/polish commands for an existing UI). Third-party skills can carry prompt injection (Snyk: 36% of analysed skills) → read before install.
- **Choice:** `frontend-design` as the base for creating screens; Impeccable as a review pass on finished screens (after reading its source). Both installed as project skills in `.claude/skills/`, switchable from the app's Skills page.

## D-011 · 2026-11-21 · superseded by D-015 — Start from the owner's flask-launchpad
- **Context:** `ecrou-exact/flask-launchpad` is the owner's own Flask template: auth, roles, per-user settings, seven themes + Theme Studio, structured `log_action`, Flask-RESTX API, DB job runner with pause/resume/cancel/retry, data table, pagination, toasts, confirm modal, tests per feature.
- **Options:** start from scratch · copy flask-launchpad as the skeleton and adapt it.
- **Choice:** copy flask-launchpad's structure and the pieces that fit (app factory, decorators, logger, settings, jobs, themes, components), then harden (TOTP, vault, CSP, single-owner auth). Not a git fork: history starts here. Licence check of flask-launchpad needed (no LICENSE file seen) — it is the owner's own code, so the owner decides.
- **Default port:** `127.0.0.1:7010` (7009 is used by Rulezet / flask-launchpad).

## D-012 · 2026-11-21 · proposed — Vitrine delivery
- Tag `v0.14.0` exists on `ecrou-exact/vitrine` (release tags contain `dist/`). Add Vitrine as a **git submodule pinned to the tag** (Rulezet pattern) and serve `dist/esm/vt-*.js` from `static/vendor/vitrine/`; no CDN. Trusted Types policy `vitrine` declared in the CSP.

## D-013 · 2026-11-21 · accepted — Pivotick API facts verified in source (v3.0.0)
- Constructor: `new Pivotick(container, data?, options?)` (`src/Graph.ts:87`), the form used in `project-graph`.
- Live updates: `updateData(nodes, edges)` (batched add-or-update), `setData`, `addNode`, `addEdge`, `removeNode`, `removeEdge`, `removeBySource`; events `nodeAdd/nodeRemove/nodeChange/edgeAdd/edgeRemove/edgeChange/dataBatchChanged`. Selection: `addToSelection`, `removeFromSelection`. Legend: `setLegend`.

## D-010 · 2026-11-20 · proposed — Other libraries (to justify individually before adding)
`psutil` (processes/ports, all OS) · `keyring` (OS secret store) · `cryptography` (AES-GCM vault) · `argon2-cffi` · `pyotp` · `Flask-Login`, `Flask-WTF` (CSRF), `Flask-Limiter` · `pydantic` v2 (schemas shared by API/forms/MCP) · `httpx` · `GitPython` or plain `git` subprocess for worktrees · `dateparser` (NL dates) · `icalendar` (read-only feed) · `platformdirs` · tests: `pytest`, `playwright`; lint: `ruff`, `mypy`, `eslint`; security: `pip-audit`, `bandit`, `npm audit`.

---

## D-014 · 2026-11-21 · accepted — Discovery closed (owner delegated every choice: "décide toi")
| Topic | Choice | Reason |
|---|---|---|
| Name | **Cairn** (repo `ecrou-exact/cairn`) | short, vendor-neutral, matches the plan/graph idea (`docs/IDENTITY.md`) |
| Logo | **Direction A — Cairn** (`docs/brand/logo-a-cairn.svg`) | pairs with the name, legible at 16 px |
| Skeleton | see D-015 | |
| D-002 to D-013 | accepted as written | |
| Context file in managed projects | **app-managed by default** (passed to runs, not committed); per-project setting "commit `CLAUDE.md`" | never pollutes upstream repos without consent |
| Default Claude permissions | auto-approve **read + edit inside the run's worktree**; shell commands from a per-project allowlist (tests, lint, build); everything else asks in the UI | fast for normal work, safe by default |
| Actions without confirmation | **none by default**: push, PR, issue, comment, release, branch deletion always confirm; the owner can switch a module to `auto` per scope | security first (§11) |
| Database | PostgreSQL in production, SQLite for dev/tests | owner's stack |
| Deployment | local Ubuntu machine, native install (`install.sh` + systemd user units); Docker Compose provided as an option; bind `127.0.0.1` | no remote exposure by default |
| Instance port range | **8100–8199** (setting) | away from 7009/7010 and common dev ports (3000, 5000, 5173, 8000, 8080) |
| Working hours | Mon–Fri 09:00–18:00, local time zone (setting) | sensible default, editable |
| Default app port | `127.0.0.1:7010` | |

## D-015 · 2026-11-21 · accepted — Build the skeleton from scratch
- **Context:** owner: "you don't have to use flask-launchpad, do what's best".
- **Choice:** new code written for Cairn's needs (single owner, strict CSP, vault, agent runs, SSE), following the conventions in `docs/OWNER_CONVENTIONS.md` (route → core, `log_action`, JSON settings, Vue 3 UMD, component folders). flask-launchpad and Rulezet are used as references for ideas only, no code copied.
- **Reason:** flask-launchpad is multi-user (registration, roles, comments, profanity filter); stripping it would leave dead code, which the brief forbids (§15).
- **Python:** project pinned to **3.12** via `.python-version` (Ubuntu 24.04 LTS default), `requires-python = ">=3.12"`, tested on 3.12 and latest in CI.

## D-016 · 2026-11-21 · accepted — Front end: native Web Components instead of Vue (supersedes the Vue part of D-008)
- **Context:** the owner's apps use Vue 3 UMD with in-DOM templates. Vue compiles those templates at runtime with `new Function`, which needs `'unsafe-eval'` in the CSP. The brief requires a strict CSP (§11), and Vue 3 has no CSP-safe runtime compiler.
- **Options:** Vue with `'unsafe-eval'` (rejected: weakens XSS protection) · Vue SFCs precompiled by a Vite build (adds a Node build to every install) · **framework-free Custom Elements** (ES modules, no build).
- **Choice:** Custom Elements written as ES modules (`static/js/components/cn-*.js`), DOM built with `document.createElement`/`textContent` (no `innerHTML` with data), styles in `static/css/components/`. Same model as Vitrine (the owner's own library) and Pivotick (vanilla TS), so the three fit together. Server-rendered Jinja stays the base of every page (progressive enhancement).

## D-017 · 2026-11-21 · accepted — Licence AGPL-3.0-or-later
- Same as Rulezet and Flowintel; a self-hosted web app should share its improvements when offered as a service.

## D-018 · 2026-11-21 · accepted — Layout details fixed while building the skeleton
- Settings defaults live in `app/settings/<key>.json` (not `app/config/`, which would clash with `app/config.py`).
- Fonts: **IBM Plex Sans** (UI) and **IBM Plex Mono** (code), self-hosted (SIL OFL). Technical yet warm, not the overused Inter/Roboto.
- Accent colour: terracotta (`#b9481f` on light themes, `#f08a5d` on dark) from the logo's dot.
- Trusted Types sent as **report-only** until Bootstrap, Pivotick and Vitrine are verified under enforcement (Phase 11).
- One `Activity` table serves as audit log, entity history (diff + batch for undo) and activity feed: one implementation (§15).
- Flask-Login's `UserMixin` is not used on SQLAlchemy models (its `__eq__` on `get_id()` interferes with the identity map); `get_id()` embeds `session_version` so a password change signs out every other session.
- Production server: gunicorn on Linux/macOS, waitress on Windows (`manage.py serve` picks).

## D-019 · 2026-11-21 · accepted — Vitrine from `main`, built and vendored (supersedes D-012)
- **Context:** owner: take Vitrine's latest `main`, not the last release. `main` has no `dist/` (built files exist only in release commits).
- **Choice:** build `main` with its own lockfile (`npm ci --ignore-scripts && npm run build`) and vendor `dist/esm/`, `dist/languages/`, `dist/syntax-themes/` into `app/static/vendor/vitrine/` without source maps (≈4 MB). `dist/vendor/` (ECharts, Mermaid, icon sets, maps — 10 MB) is left out until a feature needs it. Commit, date and how to rebuild are in `vendor.json`. No submodule: same vendoring as Bootstrap and Font Awesome.
- **Wrapper:** `<cn-vitrine kind=…>` (`static/js/components/cn-vitrine.js`) is the only place that loads Vitrine: imports one `vt-<kind>.js` module on demand, maps Cairn's theme to Vitrine's light/dark (syntax colours) while `bridges.css` maps `--vt-*` to `--cn-*`, feeds text through `content`, and turns a child `<textarea name>` (no-JS fallback) into an editor plus hidden input. Content comes from a `<script type="application/json">` written with `| tojson`.

## D-020 · 2026-11-21 · accepted — Realtime: event table polled by the SSE stream (refines D-004)
- **Choice:** `publish()` adds a row to `event` in the same transaction as the change (never announces a rolled-back change). `GET /events` polls the table every second. No LISTEN/NOTIFY and no in-process bus: the worker is a separate process, and polling works the same on SQLite and PostgreSQL. Switch to NOTIFY only if polling ever costs something measurable.
- **No lost events:** ids come from a sequence (SQLite `AUTOINCREMENT`, never reused after a prune). `EventCursor` waits up to 5 s on an id gap (a PostgreSQL transaction committing a lower id later), then gives up on it; the SSE `id:` is the resume point below any open gap and the client drops duplicates by event id. Live pages read the last event id *before* their data and pass it as `<meta name="cn-events-after">`.
- **Threads:** a stream closes after `SSE_LIFETIME_SECONDS` (300) and the browser reconnects with `Last-Event-ID`. `serve` runs gunicorn `gthread` / waitress with 16 threads, because every open tab holds one stream.
- Events are pruned after a day by the daily `system.prune` job.

## D-021 · 2026-11-21 · accepted — Job queue details (refines D-003)
- Claim = conditional `UPDATE … WHERE id = ? AND status = 'queued'`: one worker wins, on SQLite and PostgreSQL, without `SKIP LOCKED`.
- Lanes (`jobs.lanes` setting) are thread pools in one worker process. On SQLite a lock file holding PID + process start time (checked with psutil, so it works on every OS and survives crashes) allows a single worker.
- Retries with exponential backoff (15 s × 2ⁿ); a timeout fails the job (retryable), a cancel ends it as cancelled. Running jobs are heartbeated every 30 s; a job without heartbeat for 2 min is requeued.
- Recurring work: the worker's housekeeping enqueues `system.prune` daily. APScheduler comes with the calendar (Phase 10), when schedules become owner-defined.
- Only handlers registered with `manual=True` can be started from the Jobs page or the API.
- Job logs are `HH:MM:SS LEVEL message` lines, a format `vt-log` splits into time, level and message.

## D-022 · 2026-11-21 · accepted — REST API as plain blueprints, settings typed by pydantic
- `/api/*` blueprints in `app/api/` instead of Flask-RESTX (not needed for a single-owner app; one dependency less). Inputs validated by `app/core/schema/` models (`extra="forbid"`), errors as `{"error", "details"}` with 4xx codes. Same session auth and CSRF header as the pages; MCP gets its own auth in Phase 5.
- Every `app/settings/<key>.json` has a pydantic type in `SETTING_TYPES` (tested): an override must fit it (e.g. `jobs.lanes` must keep every lane).

## D-023 · 2026-11-21 · accepted — Planning model and derived columns
- `Project`, `Task`, `Dependency`, `TimeEntry` in `db_class/planning.py`. Statuses, workflow transitions, the default status, task types and score weights are settings (`tasks.*.json`), typed and checked for consistency (`Workflow` schema).
- Status *kinds* (open, active, waiting, done, cancelled) drive behaviour, not status names: renaming or adding statuses never breaks the logic.
- `is_open`, `blocked_by_count`, `unblocks_count`, `score`, `score_explain` are stored columns, recomputed by `refresh_derived()` after every planning change and every 6 h (job `tasks.rescore`). Stored so lists filter and sort on them in SQL (§14.3); written without touching `updated_at` so "untouched for N days" stays true.
- `blocks` + `follows` edges must stay acyclic together; a refused link names the loop. Dependencies are links, hard-deleted, kept in the activity log for undo.
- "Today" is the server's local date: Cairn runs on the owner's machine or server.

## D-024 · 2026-11-21 · accepted — History batches own the transaction
- `history.batch()` groups every activity row of one owner action; the outermost batch commits or rolls back everything. Undo replays inverses registered per action (`register_undo`) through the same core functions, inside a new batch: undo is validated, logged and itself undoable. A batch containing an action without an inverse (purge, timer) cannot be undone.
- Routes open the batch themselves to show an Undo button with the right batch id (`flash_undo`).

## D-025 · 2026-11-21 · accepted — Features beyond the brief, kept because they remove daily friction
- **Quick-add preview:** what was understood is shown as chips while typing, with possible duplicates (difflib ratio ≥ 0.82 against open tasks).
- **Needs attention:** overdue, due soon (hard deadline flagged, still blocked flagged), active but untouched for N days, marked blocked with nothing left blocking. Thresholds in `tasks.attention`.
- **Unblock impact and blocking chain:** "finishing this unblocks N tasks" and the transitive chain of open blockers on a blocked task.
- **Time tracking:** one running timer; "Start working" moves the task to the first active status; closing or deleting a task stops its timer; time spent vs estimate on the task.
- Quick add understands French weekday names and "demain" as well as English.

## D-026 · 2026-11-21 · accepted — Bulk edit, deadline risk, templates, roadmap as data
- **Bulk edit** applies one change to many tasks in one batch (one undo). Tasks the workflow refuses are skipped and named; the others change. Inline status/priority selects in tables save on change (buttons without JavaScript).
- **Deadline risk:** remaining work of the task and of every open task blocking it (estimate − time spent) against working time to the due date (`tasks.capacity`: hours per day, working days). Unestimated tasks are counted as unknown and reported, never guessed.
- **Templates** live in the `tasks.templates` setting (typed); `sequential` chains subtasks with `follows`.
- **Plan import** (`plan_import_core`, `manage.py roadmap [file]`): a project and tasks with parents and `blocked_by`, matched by slug and title so re-importing only adds what is new; all or nothing. Cairn's own roadmap is `docs/roadmap.json` — Cairn plans itself. The intake (Phase 6) will reuse this path.
- **Shortcuts:** `n`, `/`, `g`+letter, `?`; ignored while typing, including inside Vitrine editors (composed path).

## D-027 · 2026-11-21 · accepted — Resources: one library, links, safe file storage
- A resource exists once (`Resource`) and is attached through `ResourceLink` rows to projects and tasks; detaching never deletes it. Uploading content already in the library (same SHA-256) reuses and attaches the existing resource.
- Uploads: Vitrine's `vt-upload` (owner's library) wrapped by `<cn-upload>`; a plain file field without JavaScript. Files are stored under random names in one folder, path checked to stay inside it; size checked while reading (`resources.max_upload_mb`, ≤ 50 MB). PNG / JPEG / GIF / WebP are decoded and re-encoded with **Pillow** (new dependency): EXIF and GPS go away, a fake image is kept as a plain download-only file; > 40 Mpx refused. SVG is never shown inline.
- Link previews are fetched by a job, never during a request: http(s) only also after redirects, 1 MB, 10 s, head only, as text; result in `meta`, the owner's title wins ("Use the page title" is a button). On by default (`resources.previews`), as the brief asks; it contacts only the sites the owner saved. GitHub addresses are parsed locally (repo, issue / PR number, file at commit); the GitHub integration (Phase 7) will enrich them.
- A job queued inside a change batch is part of it (no separate commit); its queueing is undoable (cancel if not started).
- Deferred: content snapshot for Claude and Claude-written image descriptions (Phase 5, they need the agent runner).

## D-028 · 2026-11-21 · accepted — Comments, corrections log and the task brief
- One `Comment` table for tasks and projects; kind `comment` or `correction`. A correction can be retired (kept in the log, no longer given to Claude) instead of deleted. Soft delete, trash, undo like the rest.
- Corrections that apply to a task: its project's, then its parent tasks' (outermost first), then its own — the most specific last, so it reads as the final word.
- **Task brief** (`tasks/brief_core.py`): one Markdown document with what to do, acceptance criteria, checklist, instructions (project → parents → task), active corrections, dependencies, subtasks and resources (task's, then the project's; notes and snippets inline, cut at 4 000 characters, fences longer than any backtick run inside). It is shown on the task page, downloadable (`/tasks/<id>/brief.md`) and in the API (`/api/tasks/<id>/brief`); the agent runner (Phase 5) will send this same text, so what the owner reads is what Claude gets. The hard rules (no attribution, no push) stay in the run's system prompt, not in the brief.
- Live panels: `[data-live-target][data-live-events]` + `[data-live-notice]` (`static/js/core/live-panels.js`) for any panel that shows things attached to a task or project.

## D-029 · 2026-11-21 · accepted — "Ask Claude to fill a task", and the related-context search it builds on
- Owner request (2026-11-21): at any moment, add a task in a few words and ask Claude to fill it, researching it in the graph, the schedule and everything else. Planned as roadmap item `fill-task` (Phase 6), blocked by the MCP server, the runner and changeset review: a read-only run gathers context and **proposes** a changeset (description, criteria, checklist, estimate, priority, dates that fit the schedule, dependencies, resources); the owner approves item by item. No button before it works.
- Built now: `tasks/related_core.related_for(task)` — close tasks (shared title words and tags, title similarity, same project; parent / subtasks excluded), library resources matching the task's words or tags (site names ignored), and schedule fit (working time to the due date minus open estimated work due by then). Every match says why. Shown in a "Related" panel on the task page (attach a suggested resource in one click), added to the task brief as "Possibly related (check before relying on it)", in the API (`/api/tasks/<id>/related`); it will be the `find_related` MCP tool.

## D-030 · 2026-11-21 · accepted — Recurring tasks
- `Task.recurrence = {"every", "unit": day|week|month|year, "anchor": due|done}`. When the task moves to a status of kind *done* (not cancelled), the next occurrence is created in the same batch: same fields, checklist unticked, all dates moved by one step so their spacing stays. `due` keeps the rhythm and skips periods already past when done late; `done` counts from the completion day. Months clamp to the last day (31 Jan → 28 Feb).
- `next_occurrence_id` makes it happen once: reopening and closing again does not make a second copy while the first is alive. Undoing the "done" removes the occurrence (it is part of the batch, `task.recur` has an inverse).
- Subtasks are not copied (a template is the tool for a repeated tree). Quick add understands `daily`, `weekly`, `every 2 weeks`, `chaque semaine`, `tous les mois`.

## D-031 · 2026-11-21 · accepted — External conditions block like tasks
- `ExternalCondition` (task, kind review / release / pr / date / other, label, optional link, `until_on`, `resolved_at`): what a task waits for outside Cairn. An open one counts in `blocked_by_count`, so "blocked" means the same everywhere (badges, filters, "what should I do now", the brief). Resolved by hand ("It happened"); a `date` one lifts itself on its day through the daily recompute, with no write. Auto-resolution of PRs and releases comes with the GitHub sync (Phase 7).
- Like dependencies, conditions are links: removed for good, kept in the activity log, undoable.

## D-032 · 2026-11-21 · accepted — Custom task fields
- Defined by the owner in the typed setting `tasks.custom_fields` (key → label, type text / number / date / url / select with options, hint); values in `Task.custom` (JSON). `tasks_core.clean_custom` is the one check for forms, API and future MCP tools: unknown keys refused, numbers parsed, dates ISO, links http(s) only, select within its options, empty values dropped.
- Shown in the Advanced tab of the task form, on the task page and in the brief; carried to the next occurrence of a repeating task. Removing a definition hides its values (they stay stored). Filtering lists by custom fields is left for saved views.

## D-033 · 2026-11-21 · accepted — Visual identity: "a marked trail through stone"
- Owner request: the header and the whole interface need a real identity.
- **Signature:** a dark basalt header band in every theme (`--cn-chrome-*` tokens, defined by each theme like every other colour) with faint topographic contour lines (`static/img/contours.svg`, used as a CSS mask and coloured by `--cn-chrome-line`, so no colour lives in the asset) and a 3 px terracotta edge (`--cn-mark`, the logo's dot). The lowercase wordmark `cairn` sits beside the stone mark.
- **Wayfinding:** the sidebar is split into Plan / System; the current page carries a terracotta trail marker. Page eyebrows start with a small stone of the mark colour.
- **Today** greets by time of day and shows the plan at a glance as a row of stones (open, ready, blocked, late, done this week), each stone edged with its meaning's colour.
- **Sign-in and setup:** the dark contour panel with the pitch ("Plan the path. Let the work follow.") beside the form.
- Links read as text (coloured, underlined on hover); content width 92 rem for wide screens. Fonts unchanged (IBM Plex, vendored).
- **Slabs, not boxes** (owner feedback: outlined cards and side stripes are seen everywhere): panels, cards, tables, dialogs have no outline; a layered soft shadow per theme (`--cn-slab-shadow`, `--cn-slab-hover`) raises them, corners a little rounder at the bottom (`--cn-radius-slab`), panel titles start with a small terracotta stone. Coloured states (blocked, risk, correction, preview) are tinted slabs, never side stripes; a project's colour washes the top of its card.
