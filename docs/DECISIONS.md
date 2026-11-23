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

## D-034 · 2026-11-21 · accepted — Profile and connected accounts
- Owner request: a profile picture and profile now, a user system later; connect GitHub, Claude and other accounts that can give access to resources.
- **Profile** fields live on `Owner` (display name, about, picture) while Cairn is single-user; the user system will move them to a user table with the same names, and actors will become `user:<id>`. The picture is cropped to a 256 px square, re-encoded as JPEG without metadata, stored like uploads and served sandboxed; without one, initials on a stone of the mark colour.
- **Connected accounts** (`Connection`: provider github / anthropic / other, label, hint, state, identity, facts, default per provider). The token goes straight to the vault (`connection:<id>`), is never shown again, and is erased when the account is removed (no trash for credentials). A job checks it: GitHub `GET /user` (login, scopes), Anthropic through the official `anthropic` SDK (`models.list`, no tokens spent). `token_for(provider)` gives the default account's token to server-side code only.
- **Access to resources:** link previews of GitHub issues and pull requests go through the API with the default GitHub account, so private repositories get real titles. Claude runs (Phase 5) take the default Anthropic key; modules get "other" tokens only when the owner grants them.
- Credential changes are logged but not undoable (they cannot be replayed without the secret).

## D-035 · 2026-11-21 · accepted — The graph: Pivotick draws, Cairn decides the picture
- Pivotick 3.0.0 vendored from npm (ES build: self-contained, no bare imports; tarball SHA-256 in `vendor.json`). Source read first (constructor is `new Pivotick(container, data, options)`; the docs show an older object form).
- Owner direction: override whatever makes it simpler and consistent with Cairn; the graph must read left to right with clean lines and a real meaning.
- **The plan is laid out by Cairn** (`graph_core.plan_layout`) and every card is pinned (`fx`/`fy`): a column per step, a task right of what blocks it or comes before it, of what blocks its parent tasks, and of its own subtasks (a parent is done when they are); rows grouped by project then reordered by barycentre sweeps to uncross lines; straight edges. Pivotick's tree layouts were tried and dropped: they stacked this data into a narrow column.
- **Cards are the nodes** (`shape: 'none'` + `html`), built with DOM methods: type stone, project, score, title, status, due date, priority, blocked / unblocks. Coloured by the project (a wash, no stripe), styled with Cairn tokens.
- **Cairn's chrome only:** `UI.mode: 'viewer'`, Pivotick's grid, viewport rail and minimap hidden; Cairn draws toolbar, zoom / now / fit buttons, legend and the side panel (click a card; double click opens the task). The view opens on Pivotick's `ready` event at a readable zoom centred on the best actionable task, or fitted when the whole plan is readable.
- **Critical path** (server): the chain of open `blocks` tasks with the most work left (estimate − time spent, unestimated = 1 h and counted); lit cards glow, the others step back.
- **CSP:** the graph page alone adds `style-src-attr 'unsafe-inline'`, because Pivotick writes a few `style="…"` attributes in its own markup; `<style>` elements stay forbidden (no selectors, so no CSS that reads the page) and scripts stay `'self'`. The simulation worker is off (`useWorker: false`): every node is pinned, and the worker's `data:` fallback is blocked by the CSP anyway.
- Live: `task.changed` / `project.changed` re-fetch and apply only the differences (added / removed / changed cards and edges), positions included.

## D-036 · 2026-11-21 · accepted — Graph levels, hover peek, a graph on every task
- Owner request: too many cards at once; a project should show its cases, a click opens the case's own graph with a breadcrumb; the graph on every task page; a better hover title.
- **Levels** (`graph_data`): `top` (default: tasks without a shown parent, the cases), `children` (a root's direct subtasks), `around` (a root without subtasks: itself and the tasks it is linked to), `all` (everything, subtasks linked to their parent). Dependencies between deeper tasks are **lifted** to the cards shown (a link between subtasks of two cases appears between the cases, with how many links it stands for). A case's weight on the critical path is the work left in its open subtasks (its own estimate if it has one, never a made-up hour).
- Cards with subtasks show "done/total subtasks" with a progress line and a stacked look; double click (or the side panel's button) opens `/graph?root=<id>`; the breadcrumb (All projects › project › parents › case) is computed by the server.
- **Hover peek** (Cairn's, dark like the header) replaces Pivotick's tooltip: full title, project, status, type, priority, due date, what a double click will do.
- The stage is one Jinja macro (`macros/graph.html`) mounted by `graph.js` on every `[data-graph]`: the Graph page and a compact stage on each task page (CSP for graphs applied there too).

## D-037 · 2026-11-21 · accepted — Claude runs use the local Claude Code first
- Owner request: not only the Claude API — the Claude Code installed on this machine must be usable from the app.
- New connection provider **Claude Code (this machine)**: nothing stored; Cairn finds `claude` on PATH (or a path the owner gives) and checks it with `claude --version` (argv list, no shell, read-only, 20 s timeout). `connections_core.claude_code_path()` gives the executable to use.
- **Phase 5 design:** the runner drives Claude Code through the Claude Agent SDK pointed at this executable, so runs use Claude Code's own sign-in (the owner's subscription or console login) and its settings; an Anthropic API key connection is a fallback only, passed per run through the SDK's `env`, never written to disk. To confirm when reading the Agent SDK pages (roadmap `sdk-read`): CLI path option, auth precedence when no key is given, per-run `env`.

## D-038 · 2026-11-21 · accepted — Today, redone; the final mark
- Owner request: the home page must be much more modern; the promised logo.
- **Today:** a dark hero band (contours, a warm glow of the mark colour) with the greeting, the plan at a glance and quick add as the main field; **Next up**, the task to do now, raised over the band with the biggest parts of its score in words, what it unblocks, Start and "In the plan"; then slabs: **Then** (the following tasks with a score bar and a start button), **This week** (seven days with what is due each day, late tasks flagged), **Needs a look**, **Projects** (progress, open / blocked / late, graph link), **Lately** (activity told as sentences: "You moved X to In progress", noise such as jobs and secrets left out).
- **Mark:** three organic stones resting on each other, each a little lighter than the one below, with the mark-coloured sun above (`docs/brand/cairn-mark.svg`); the same paths in the app (`brand_mark`) and the favicon (light / dark via `prefers-color-scheme`).

## D-039 · 2026-11-21 · accepted — Project page: work beside context
- Owner feedback: the project page's organisation did not work (everything stacked, tasks at the bottom).
- A dark band lit by the project's colour (name, status, repository, branch, local path, stack; open / done / blocked / late / next due; progress), with Open the graph, Edit, Trash. Below, two columns: **work** (the project's plan as a compact graph of its cases, then its tasks with quick add, templates, filters and bulk edit) and **context** (next up here, about with links, resources, discussion). One column under 1100 px.
- Band stats and slab headers moved to `core/base.css`, shared by Today and the project page.

## D-040 · 2026-11-22 · accepted — Find in the graph
- A level shows cases, so most tasks are hidden inside a card; Pivotick's own search only knows the nodes drawn. **Cairn searches on the server** (`graph_core.find`) over every task of the view's scope, with the same levels and filters as the graph (one `_level()` for both), and answers with the **card that holds each match**: the task itself, or the case it is inside, with the titles in between.
- Matching is the palette's: the title contains the words, case-insensitive, literal; done tasks only when the view shows them. Order: on this graph before filtered out, shallower before deeper, open first, then score; 8 results and how many more.
- Choosing a match glides to its card, selects it (a visible ring, also used by link mode's first pick) and opens its side panel; a match inside a case says so ("double-click it to open its subtasks"); a match left out by the filters opens the task page. `/` focuses the field (as it focuses list searches), arrows and Enter pick, Esc clears. Not on the compact task-page graph, which is small enough to read.

## D-041 · 2026-11-22 · accepted — Windows with Smart App Control enforced
- Smart App Control (enforcement mode) refuses unsigned native modules. On the owner's machine it blocks uv's managed CPython builds (`_sqlite3.pyd`) and SQLAlchemy's Cython modules; pydantic-core, cryptography, argon2, Pillow, psutil and PyYAML load.
- **Fix on such a machine, nothing changed in the repo:** the signed python.org interpreter (`uv sync --python <python.org python.exe>`, or the `UV_PYTHON` user variable) and SQLAlchemy in pure Python, set in the user's uv config (`%APPDATA%\uv\uv.toml`: `no-binary-package = ["sqlalchemy"]`, `[extra-build-variables] sqlalchemy = { DISABLE_SQLALCHEMY_CEXT = "1" }`). The full suite passes this way on Python 3.15.
- `.python-version` stays 3.12 (Ubuntu 24.04's default, D-001); Linux and other Windows machines keep the compiled SQLAlchemy.

## D-042 · 2026-11-22 · accepted — One look on every page, less text, filters folded away
- Owner feedback: the file drop zone was ugly; buttons, card heads and the background must have more style and be the same everywhere; more visual, less text; the filters must be hidden.
- **Page headers** are a compact dark contour band (Today's hero language) on every page; their intro is one line. **Background**: a warm glow of the mark and faint contour lines at the top of the content.
- **Buttons are stones** (rounder at the bottom): the primary one lit by the mark with a soft glow, the others raised slabs without outline that lift on hover. **Fields** are wells with a focus ring. Card heads and panel headers get a hairline under the title.
- **Filters folded away:** every list's filters (and the graph's state, tag, done tasks) live behind a "Filters" button showing how many are on, in a panel that opens on click (`<details>`, no script); search and the view switch stay visible; a cross clears everything.
- **Bulk edit** appears only once a task is ticked (CSS `:has`), as a dark bar floating at the bottom of the screen. **Empty states** are a stone with the icon, a title and one line.
- **Uploads:** Vitrine's `vt-upload` restyled through its `::part()`s (`css/components/upload.css`); `<cn-upload>` sets `is-dragging` on itself (Vitrine's own state is not reachable from outside) and, with `paste="page"`, takes files **dropped anywhere on the page**, with a full-page overlay saying where they go. The library's add block: a large drop zone with three short chips (details in tooltips) beside a grid of "Create" stones.
- **Graph path:** above the graph, `All projects / project / case` with an **Up** button (and `Backspace`) to go back one level.

## D-043 · 2026-11-22 · accepted — The graph frames itself; menu, remembered view, table, contour ground
- **Framing by Cairn:** Pivotick's first fit measures the SVG, which misses the HTML cards, and waits up to ~3 s for them to settle before `ready`; on Cairn's instance it is replaced by a no-op (`fitAndCenterWhenSettled`), its late deferred fit is cancelled, and the simulation stops at once (`warmupTicks: 0, cooldownTime: 0`; every card is pinned). Cairn frames from the server's places (a card's `x, y` is its centre): the whole plan when readable, else zoomed on what to do now placed near the left so what it opens up is visible.
- **Right-click menu** on a card (Pivotick's own is off): open the task, open its subtasks, link from here, details, move to an allowed status. Keyboard: arrows, Esc.
- **Remembered view:** zoom and position per graph (path + query) in `sessionStorage`, so going down into a case and coming back Up lands where you were; the crosshair still goes back to "now". Session only: a new day opens on what to do now.
- **Table view** (`t`): the same cards in plan order (step, task, project, status, priority, due, score, links), redrawn live; not sortable on purpose, the order is the plan's.
- **Ground:** Cairn's contour lines in two large faint layers instead of Pivotick-style dots (owner request).

## D-044 · 2026-11-22 · accepted — The graph lives in the projects; projects are ordered by links
- Owner request: the "Graph" menu entry served no purpose; see a graph only in the projects, and a graph that decides in which order to do the projects and the tasks. Owner's choices: links between projects; the plan of projects on the Projects page.
- **`ProjectLink`** (`from_project` passes before `to_project`, note): acyclic (the loop is named, same path search as task dependencies, now shared in `core/utils/graphs.path_between`), logged, undoable, `/api/project-links`. It **orders, it does not block** the projects' tasks.
- **Plan of projects** (`graph_core.project_plan`, `/api/graph?view=projects`): projects as cards (progress, open, blocked, late, next due, next task, best ready score), laid out by the same `plan_layout` (its row order is now a `sort_key`); a project stands right of the projects that pass before it **and** of the projects whose tasks block or come before its own (one edge with how many task links). Order mode (`L`), side panel (passes before / after, remove an order, add one), right-click menu. Archived projects left out.
- **No Graph page:** the sidebar entry and `g g` go; `/graph` without a case redirects to the Projects page (or the project's Plan tab); `/graph?root=` stays as a case's own graph, under Projects in the menu. Breadcrumbs start at "All projects" → `/projects`.

## D-045 · 2026-11-22 · accepted — Project page in three tabs
- Owner feedback: too many things on the project and task pages.
- The project band (with the **next task** to do there, in place of "Open the graph") over three tabs, each its own URL (`?tab=`, works without script): **Plan** (the project's full graph with its level and folded filters, and the projects it passes before / after), **Tasks** (quick add, templates, list), **About** (description and links, resources, discussion). A list search, filter, sort or page lands on Tasks.

## D-046 · 2026-11-22 · accepted — 300+ cards: measured, nothing to change
- Server (`tests/test_graph_scale.py`, kept in the suite): 360 tasks, 300 links, a subtask every sixth task → the three views (everything, cases, plan of projects) in ~0.4 s together; no two cards on one spot; the test fails above 3 s.
- Browser (Pivotick 3.0.0 with 360 pinned HTML cards and Cairn's options, measured in Chrome on the owner's machine): first render ~0.8 s; a zoom or pan ~0.7 ms of script and layout on average, 3.2 ms at worst. The default "Cases" level draws far fewer cards; "Everything" is the only view at full size. No virtualisation needed.

## D-047 · 2026-11-22 · accepted — Task page in tabs; forms you rarely need are folded
- Owner feedback: too many things on the task page (everything stacked, every form open).
- **Task band** with the project band's look (tinted by the task's project): path, title, status, priority, blocked, due, tags; numbers (score, unblocks, estimate, time spent, subtasks done); actions (start / stop, allowed moves, edit, trash).
- **Five tabs**, each its own URL (`?tab=`): **Work** (description, checklist, acceptance criteria, subtasks), **Plan** (links, conditions, the graph around it), **Files** (resources), **Discussion** (comments and corrections), **Claude** (instructions, brief). Forms return to their tab (`tab=` on redirects, `request.full_path` in the shared panels).
- **Side column** kept slim: the score's three biggest reasons (the full breakdown folded), planning facts, related, history folded.
- **Fold** (`.cn-fold`, a `<details>` with a "+ …" summary, no script): "Link another task", "Wait for something outside", "A link, from the library, or a new note" (the drop zone stays visible), "Write a comment" (open when there is none yet). Used on project pages too.

## D-048 · 2026-11-22 · accepted — Actions in drop-downs on a band
- Owner feedback: the row of status buttons, Edit and trash in the task band looked bad; wanted a drop-down or icon-and-text.
- The task band keeps one main button (**Start working** / Stop the timer), then a **status drop-down** (the current status with its colour dot; the moves the workflow allows, each with its dot) and a **"⋯" menu** (Edit, the brief for Claude as Markdown, Move to trash in red, still confirmed).
- `details.cn-menu` (opens without script) + `core/menus.js`: closes on a click outside or Escape (focus back on its button), one menu open at a time; the folded list filters use it too. A band with a menu no longer clips its content (its contours keep the rounded corners).

## D-049 · 2026-11-22 · accepted — Claude Agent SDK read (docs and source, 0.2.187)
- Dependency added: `claude-agent-sdk` 0.2.187 (D-002). Docs read on code.claude.com (agent-sdk/python, permissions, hooks, sessions, mcp, streaming-vs-single-mode, quickstart, troubleshooting, authentication, sandboxing); source read for the points below.
- **Executable** (`_internal/transport/subprocess_cli.py::_find_cli`): the wheel bundles `claude.exe` (2.1.330 here, Authenticode-signed, so Smart App Control lets it run); without `cli_path` the bundled one comes first, then a native `claude.exe` on an absolute PATH entry (Windows) or `which claude`; `.cmd`/`.bat` are refused on Windows. `cli_path` skips discovery: Cairn passes the Claude Code connection's path (`connections_core.claude_code_path()`).
- **Environment:** the CLI gets the parent's environment with `options.env` merged over it; an inherited variable can be overridden but not removed, so the worker must not carry `ANTHROPIC_API_KEY` itself; a key is given per run through `env` only.
- **Permissions:** `can_use_tool(tool_name, input, ToolPermissionContext) → PermissionResultAllow | PermissionResultDeny` works with `query()` and `ClaudeSDKClient` (the SDK switches prompts to stdio itself); order: hooks → deny rules → ask rules → mode → allow rules → `can_use_tool`. Modes: default, acceptEdits, plan, dontAsk, bypassPermissions, auto.
- **Hooks:** `HookMatcher(matcher, hooks, timeout)`; a PreToolUse hook answers `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": …}}`.
- **Sessions:** `resume`, `fork_session`, `session_id` (UUID), `continue_conversation`; the id is in `ResultMessage.session_id`. `interrupt()` needs streaming mode (`ClaudeSDKClient`).
- **Results:** `ResultMessage` (subtype success / error_*, `is_error`, `num_turns`, `total_cost_usd`, `usage`, `model_usage`, `session_id`); errors `CLINotFoundError`, `CLIConnectionError`, `ProcessError`, `ResultError`, `CLIJSONDecodeError`.
- **Sandbox:** macOS (Seatbelt), Linux/WSL2 (bubblewrap); **not on native Windows** (commands run unsandboxed) and it covers Bash only, not Read/Edit/Write or MCP. On Windows Cairn relies on permission prompts and the directory allowlist.
- **Sign-in — open question for the owner:** the SDK quickstart says Anthropic does not allow third-party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK, unless previously approved, and asks for API-key authentication. This questions D-037 (runs on the local Claude Code's own sign-in). Decision pending.

## D-050 · 2026-11-22 · accepted — Claude Code in a terminal inside Cairn; every session in view
- Owner request: "my Claude Code directly in this app, as if I had opened it in a terminal", so that someone who installs Cairn only needs their own Claude Code installed and signed in; and see everywhere in the app where Claude runs, how full it is, with several sessions at once. This replaces D-037's plan of driving Claude Code through the Agent SDK with the owner's sign-in (the SDK quickstart asks third-party products to use API keys, D-049): Cairn **hosts** the owner's own `claude`, it does not drive it. Agent runs through the SDK (with an API key) stay possible later.
- **Terminal:** `pty_host.Pty` (ConPTY via `pywinpty` on Windows, `ptyprocess` on Linux/macOS; tested under Smart App Control) runs `claude --session-id <uuid>` (plus the task's brief as first message when asked, cut at 24k characters for Windows' command line) in the project's local folder, the executable from the Claude Code connection (`claude_code_path`). One `Terminal` per session in the web process: a reader thread keeps the output (2 M characters) and records the end; leaving the page does not stop it. `ClaudeSession` rows keep folder, project, task, session id, pid, how it ended; sessions left "running" by a restart are closed with the reason.
- **Transport without WebSocket** (waitress, Cairn's production server on Windows, has none): output by SSE on `/claude/sessions/<id>/stream` (`id` = output sequence, so the browser resumes; a page that comes back replays the kept output; the stream closes every `SSE_LIFETIME_SECONDS`); keys by `POST /api/claude/sessions/<id>/input` in ordered batches of a few ms; `resize`, `stop`. gunicorn runs **one** process (16 threads): terminals live in it.
- **Front end:** xterm.js 6.0.0 + fit add-on vendored (ES modules); `<cn-terminal>` in Cairn's colours and mono font. xterm writes three `<style>` elements: terminal pages get `style-src-elem 'self' 'nonce-…'` and the component gives those elements the nonce; Ctrl+K in a terminal belongs to it, not to the palette.
- **Seeing every session:** `transcript_core` reads Claude Code's transcripts (`~/.claude/projects/<folder with non-alphanumerics as "-">/<session id>.jsonl`, the end only): context in use = input + cache creation + cache read tokens of the last assistant turn, over the model's window (`claude.context_windows` setting; a session past it counts against 1M), the model, the title Claude Code gave it, the last activity. Sessions started **outside** Cairn are found by their `claude` process (`psutil`: folder, start time; helpers whose parent is `claude` skipped) and the newest transcript of their folder.
- **Views:** a **Claude** page (menu) with every session as a card (context gauge, title, project, task, folder, model, tokens, working / waiting for you), live every 5 s; a running count on the menu's Claude entry on every page; a **Claude** tab on projects (open Claude in the project) and the task's Claude tab (start Claude on the task with its brief, or open it in the folder); a session page with its band and the terminal at full height.

## D-051 · 2026-11-22 · accepted — Claude from anywhere: launcher, intents, rules, new projects, resume
- Owner request: launch Claude from anywhere — on a task, a project, a new project, to answer a pull request, to fix something — and talk to Claude in Cairn as in a terminal, linked to the app.
- **Launcher** (`<cn-claude-launch>` in the shell): the header's **Claude** button, `Alt+C`, the palette ("Open Claude…"), and `[data-claude-launch]` buttons prefilled with a project, a task, an intent — on task rows and cards (only where Claude can open: a project with a local folder), project cards and band, Today's next task, the graph's right-click menu, the task band's menu.
- **Intents** (`terminal_core.PRESET_INFO`, one place for every entry point): work freely, on a task (its brief), answer a pull request (its URL: read it and its review with `gh`, answer, change, test, show the diff and **wait for the owner's go** before committing or pushing), fix a bug (cause, fix, failing test first, diff, wait), review the changes (findings by importance, no change unless asked), and **new project** (Cairn creates the project and its folder — only a new or empty folder, full path — then Claude asks, proposes and sets it up).
- **Rules in every session:** `claude.rules` (setting: no AI attribution anywhere, no push / merge / publish without the owner's go, ask before guessing) and the project's Claude instructions go to `--append-system-prompt-file` (a file in the data folder, deleted when the session ends: Windows caps a command line at 32k characters).
- **Resume:** any Claude Code conversation on the machine — started outside Cairn, or one of Cairn's that ended — reopens in Cairn's terminal (`claude --resume <id>` in its folder, its project found by folder); one already open in Cairn is returned as is. A conversation can therefore have several session rows (the id is indexed, not unique).
- Next: Claude linked to Cairn through an MCP server (D-052), project instances (Phase 8).

## D-052 · 2026-11-22 · accepted — Claude linked to Cairn through an MCP server
- Owner request: talk to Claude inside Cairn as in a terminal, but with the terminal linked to the app.
- **Cairn's MCP server** (`features/claude/mcp_server.py`, `mcp` 2.x `MCPServer` — FastMCP's successor, source read): `python manage.py mcp` over **stdio**, started by Claude Code itself for every session Cairn opens (`--mcp-config <data>/claude/<session>.mcp.json`, deleted with the session; `CAIRN_MCP_SESSION` names the session). No port, no token on the wire, works with every server and OS; nothing but the protocol on stdout (logs on stderr).
- **Tools** (the same cores as the pages and the API): `cairn_overview`, `list_tasks` (project by id / slug / name, state, search), `get_task` (the brief), `next_tasks` — allowed up front (`--allowedTools`); `create_task` (subtasks too, in the session's project by default), `set_task_status`, `link_tasks` (cycles refused with the loop named), `comment_on_task` (or a correction for later runs) — **Claude Code asks the owner** before each. Changes are made as `claude:<session>`: logged, in the history, undoable. Deliberate refusals are `ToolError` (Claude gets the reason); any other failure keeps its text on the server.
- Argv order: the first message right after the executable, the variadic `--mcp-config` / `--allowedTools` last (they would swallow it); a message starting with "-" gets a leading space.
- **Fresh sessions (fix, owner report):** a Claude opened in Cairn warned "Transcript saving is off — inherited CLAUDE_CODE_CHILD_SESSION marker": Cairn's server had been started from a Claude Code session and passed its markers on. The child environment now drops the markers a running Claude Code gives its children (`CLAUDECODE`, `CLAUDE_PID`, `CLAUDE_EFFORT`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_EXECPATH`, `CLAUDE_AGENT_SDK_VERSION`, `CLAUDE_CODE_CHILD_*`, `CLAUDE_CODE_SESSION_*`, `CLAUDE_CODE_MESSAGING_*` — a token among them), and keeps the owner's own settings (`CLAUDE_CODE_USE_BEDROCK`, limits…).

## D-053 · 2026-11-22 · accepted — Project instances run from Cairn
- Owner request: launch a project's instances from Cairn (Phase 8, first part).
- **`ProjectInstance`** (project, name, command, optional subfolder inside the project's folder, optional port): defined in the project's **Instances** tab or `/api/instances`; removing one is a soft delete, logged and undoable; a running one must be stopped first.
- **Running:** the same terminals as Claude (`terminal_core.open_session`, now shared: one session row per run with `kind` claude / instance, files removed at the end, `<kind>.changed` events); logs in colour with their history, start / stop / restart, never two runs of one instance at once.
- **Command:** the owner's text split into argv (no shell); the program is looked up on PATH. Windows runs `.cmd` / `.bat` scripts (npm, yarn, pnpm…) only through `cmd.exe /d /c`: those, and only those, go through it (the command is the owner's own).
- **Ports:** an asked port is checked (bind on 127.0.0.1); if taken, the next free one within 50 is used and given as `PORT`. The ports the process and its children actually **listen** on (psutil) are shown as `localhost:<port>` links.
- **Stopping** uses the terminal's `close(force=True)`: pywinpty's `terminate()` alone leaves its sockets open.
- Next for Phase 8: a header indicator of running instances, restart on crash, an instance registry across projects.

## D-054 · 2026-11-22 · accepted — What each Claude is doing, where it runs; instances on the Claude page
- Follows D-050 (see everywhere where Claude runs): a gauge says how full a session is, not what it does.
- **Last steps** (`transcript_core._events`, from the end of the transcript already read for the context): what the owner typed (commands Claude Code records as user turns, starting with `<`, left out) and what Claude did — its text and each tool call put in words with an icon (`describe_tool`: editing / reading a file relative to the folder, the command's own description, searches, web, delegation, Cairn's MCP tools as "Cairn: …"). The last 8 are kept; the newest of Claude's is its **now** line. On every session card, live every 5 s; times in the browser's local time.
- **Where an outside session runs** (`host_of`): the closest editor or terminal app among the `claude` process's parents (VS Code, Cursor, JetBrains, Windows Terminal, iTerm2, tmux… before a bare shell), "a terminal" when none is known.
- **Instances on the Claude page:** the running ones in their own section with their listening ports and the last lines of their log (`terminal_core.preview`: escape sequences stripped, redrawn lines kept at their last state) shown through `<cn-vitrine kind="log">`, which gains a `content` setter for live updates. Not used for Claude itself: a full-screen program reads poorly that way, its steps come from the transcript.
- Session files (rules, MCP config) of sessions closed because Cairn restarted are removed when they are closed (their reader died with the old process).

## D-055 · 2026-11-23 · accepted — The terminal takes every key; one conversation, one Claude
- Owner report: commands could not be sent from Cairn's terminal, and it did not follow the same conversation open in another terminal.
- **Keys:** every input schema strips strings (`Strict`), so Enter, Space and Tab sent alone became empty and were refused (422, hidden by the page). `TerminalInput` strips nothing; the page shows input that could not be sent, cuts long pastes into pieces, and sends its first size (it was fitted before the resize listener existed, so the program stayed at 120×32).
- **Closing on Linux / macOS:** `ptyprocess.close()` waits for the buffer lock its reader holds until the program prints: Close, Stop and the interpreter's end could hang. `Pty.kill` signals the process group (hang-up, then kill), the reader reaps the program (exit codes are recorded) and releases the terminal; invalid UTF-8 is replaced instead of ending the reader; `close_all` runs at exit.
- **One conversation, one Claude:** two Claude Codes resumed on one conversation never see each other's turns, and a terminal Cairn did not open cannot be mirrored. The conversation an outside process holds is read from Claude Code's own registry (`~/.claude/sessions/<pid>.json`, undocumented: anything unexpected falls back to the newest transcript of the folder). Resuming one open elsewhere is refused; **Move to Cairn** (confirmed, `take_over` in the API) closes the other one, waits for it, then resumes here, and is logged. Never when Cairn runs inside that very session.

## D-056 · 2026-11-23 · accepted — Free sessions, linked when the owner wants; stop any Claude; usage left
- Owner request: reach a detected Claude without a project, link it to a project (or a new one for a folder, which Claude reads) whenever wanted, stop any conversation at any time, see how much Claude usage is left.
- **Free:** the launcher opens Claude in any folder (`SessionStart.folder`); **Move to Cairn** needs no project. A session page links it to a project, to a new one, or to none (`/link`); a conversation resumed later keeps its last link. Cairn's MCP tools follow the link at once (they read the session's row); the project's instructions, part of the system prompt, apply from the next opening.
- **A folder Claude reads:** "New project" now takes a folder with files: Claude reads it without changing anything, fills the project with the new MCP tool `update_project` (description, stack, tags, repository, branch; approved in Claude Code, undoable) and proposes tasks. From a session, the reading is done in a separate new session: nothing is typed into a conversation in progress, where a key could answer a permission prompt.
- **Stop:** on every card; an outside one by pid and start time (a reused pid is never closed), never the one Cairn runs in. Its conversation can be resumed.
- **Usage left:** Claude Code hands `rate_limits` to its status line. Sessions opened from Cairn get `--settings` with Cairn's status line (`statusline.py`), which keeps only those numbers (`<data>/claude/limits.json`), then runs the owner's own from `~/.claude/settings.json` (a project's own status line does not show in Cairn). No credentials read, no request made. The numbers are the account's; they move only while a Claude opened in Cairn runs, so the time they were read is shown, and a window past its reset is hidden. Shown in the header next to the Claude button, in the menu under Claude while one runs, on the Claude page and on each session.

## D-057 · 2026-11-23 · accepted — Static files carry no session
- Owner report: a page shows for an instant without its styles when changing page. Versioned static files were `immutable` but also `Vary: Cookie` (Flask's session), so browsers revalidated every stylesheet at each page. The session is no longer saved on static responses; the brand mark has its size in the markup, so it never draws full-size before the styles.

## D-058 · 2026-11-23 · accepted — Skills in the library; the real context window
- Owner request: a category of resources for skills Claude can use; and a gauge that does not lie.
- **Skills** are a resource kind (`skill`): a folder on this machine with a SKILL.md, or instructions written in Cairn (front matter made from the title and notes when absent). Not attached: for every session Cairn opens; attached: only for those projects and tasks. `skills_core` copies them, as a session opens, to a plugin folder of its own (`claude --plugin-dir`, plugin `cairn-skills`), removed with the session: nothing is written in `~/.claude` nor in the project. Links are not followed, folders over 20 MB or no longer readable are left out and logged. A session already open gets a new skill when reopened.
- **Context window:** the size was guessed (200k, then 1M once past it), so the gauge jumped. Claude Code tells its status line the model's real size: kept per model (D-056 file) and used for every session, outside ones too; the setting still wins for a model it lists. The ring now says "context": it is how full the conversation is, not the account's usage.
- **Usage kept current:** sessions outside Cairn report too when the owner's status line calls `statusline.py <data>/claude/limits.json --keep` (added to the owner's `~/.claude/statusline.sh` with their go, 2026-11-23). Within a window the number only grows, so an idle session never brings an older one back.

## D-059 · 2026-11-23 · accepted — What Claude is doing, as a live graph
- Owner request: see concretely, as a graph, what goes on: sessions, the agents and shells they open.
- **Facts only** (`live_core`): tool calls without a result while Claude Code's registry says `busy`; background tasks (`backgroundTaskId`) without an end notification, started by this process; agents from `<session>/subagents/*.meta.json` (`finished`) and their transcripts, nested by the call that started them, one silent for 10 minutes counted as cut; processes by `psutil` (shells, wrappers and pipe filters skipped) with their ports. A process is named by its program and plain words only: options, `NAME=value` and addresses may carry secrets. Only a transcript's end is read, again only when it changed.
- **Two levels:** every session with what is alive; one session (double click) with all it did since the owner's last request: files changed, commands, reads, searches, web, skills, MCP servers.
- Laid out by Cairn (a tree left to right, pinned), drawn by Pivotick; `graph/stage.js` now holds what the plan's graph and this one share. Polled every 3 s while in view: transcripts send no events.

## D-060 · 2026-11-23 · accepted — Cairn's own Claude, and notes between Claudes
- Owner request: one Claude opens with the app and manages everything; each project has its own when needed; from a project's Claude, "take a note" reaches the main one.
- **Main Claude** (`main_core`): opened by the web server as it starts (`CAIRN_WEB`, set by `manage.py start` / `serve`; with auto-reload only the serving process; setting `claude.main_autostart`), in `<data>/main`, resuming its last conversation. It is the session whose folder that is: no new column. It uses nothing of the account until spoken to.
- **Notes:** `take_note` (for the main Claude, or `for_project`), `inbox`, `note_done`. A note is a library resource of kind note tagged `to-main` / `to-project`, attached to its project: seen, logged, undoable. Rules tell each Claude a note is information, never an order. Writing tools still ask the owner (D-052).
- The main Claude also gets `create_project` and `claude_sessions`. It is told to read `inbox` at each request: nothing is typed into a terminal (D-056), so a note does not wake it. It does not open a project's Claude itself yet: terminals live in the web process, the MCP server does not.

## D-061 · 2026-11-23 · accepted — A project's instances wherever they run, and their logs
- Owner request: in each project, see what runs (several copies of one repository at once), open the one wanted in a new browser page, read its log in a Cairn terminal.
- **Found** (`found_core`): what listens on a TCP port (`psutil`) or publishes one (`docker ps`, compose's working folder) in the project's folder, or in another copy of its repository: a worktree (same git folder) or a clone (a common remote, or the project's GitHub repository). Shown with its folder, branch, where it runs, since when, its ports as links opening a new page; the tab counts what runs. A Claude and Cairn's own instances are left out. Git is read from its files: no git process.
- **Logs:** files the process writes (`open_files`, its output on Linux), recent `*.log` of the copy, or `docker logs`, followed in a terminal (`kind` log, `follow.py`, rotation handled). Only a log found for that project can be opened, never a path given by a request. An instance that writes to its own terminal only has no log Cairn can read: start it from Cairn.
- Not done: stopping one from here; instances started from Cairn still end with Cairn.

## D-062 · 2026-11-23 · accepted — Cairn starts with the session (Linux)
- Owner request: Cairn opens every morning. `manage.py autostart on` writes two systemd user services (`cairn-web` running `serve`, `cairn-worker`), with the PATH of the shell that ran it (Claude Code, node, docker are found), and an autostart entry that opens the page once Cairn answers. No root; `off` removes everything. They follow the graphical session: the master key is in its keyring. `serve`, not `start`: no auto-reload, so a file change does not close the terminals.

## D-063 · 2026-11-23 · accepted — The main Claude beside every page
- Owner request: the Claude that opens with Cairn is the most important one: a panel beside the pages, opened, folded, closed and relaunched at will, told to act on the page in front, on everything, or on Cairn itself.
- **Dock** (`<cn-claude-dock>` in the shell, `Alt+J`): open or folded (cookie, read by the server; by default as `claude.main_autostart`), fold keeps Claude running, stop closes it, relaunch resumes its conversation. Not on the main session's own page: its terminal is there.
- **In a frame** (`/claude/sessions/<id>/panel`): a terminal needs a looser style policy, which stays in that page, frameable by Cairn's own pages only; every other page keeps the strict policy and cannot be framed.
- **The page in front:** the dock tells it (`/api/claude/page`), `current_page` gives it to Claude with the project, task or resource it shows.
- **Cairn itself:** `--add-dir` on Cairn's code, with rules: CLAUDE.md first, a branch in a worktree, the diff shown, the owner's go before merging, never a restart by itself.
- A terminal's stream is open only while its tab is in view (six connections per browser).

## D-064 · 2026-11-23 · accepted — Security review of the main Claude's access
- **Session key given to every program (fixed, high):** Claudes and instances inherited Cairn's environment, `CAIRN_SECRET_KEY` with it: any of them could forge the owner's session, and so start commands without approval. Nothing named `CAIRN_*` is passed on any more.
- **Approvals assumed, not enforced (fixed, high):** D-052 counts on Claude Code asking before a change; a permissive mode (auto) need not. Every session gets `ask` rules on Cairn's writing tools; the main one also on edits of Cairn's code, push, merge and service commands.
- **Files that give the owner's rights (reduced):** `.env`, the vault's key file, the database and session files are refused to Claude Code's file tools. Not a sandbox: a program run by a session is still the owner's user.
- **Notes as an injection path (reduced):** a project's Claude, steered by hostile content, could write to the main one. Notes come with a warning, the rules say report rather than obey, 8000 characters at most; acting on one meets the `ask` rules.
- **Data folder readable by other users when outside a private home (fixed):** 0700 at start.
- **Log links (fixed):** a symbolic link in a repository's log folder could show a file from elsewhere to the owner.
- Reviewed, nothing to change: the panel's frame (own origin only, messages checked, strict policy elsewhere), CSRF and deny-by-default on the new endpoints, the status line (numbers only; runs the owner's own command).
- **Accepted:** same-user isolation needs a sandbox (Phase 5, permissions); a project's Claude can write notes as any session of this user could.

## D-065 · 2026-11-23 · accepted — Projects: graph or cards
- Owner request: not both on one page. Two tabs: the list (cards or table) first, the graph second (`?mode=graph`).

## D-066 · 2026-11-23 · accepted — Claude on the plan's graph
- Owner request: in a project's graph, see the task Claude works on, and open what it does inside.
- The task a running session is on (opened from it, or moved to an active status through Cairn's MCP server, within its project) is lit on the plan with Claude's current step; a case is lit for a task inside it. Click: the panel says what it does, with its graph and terminal; double click on a task without subtasks opens that graph (D-059), which leads back to the plan. Asked every 4 s while in view. A Claude outside Cairn says no task: not shown.

## D-067 · 2026-11-23 · accepted — A project's icon or picture; its folder opened on the machine
- Owner request. **Icon:** Vitrine's `vt-icon-picker` (two Font Awesome sets vendored from the same commit), wrapped by `<cn-icon-field>` over the text field; brands allowed (`fa-brands fa-docker`). **Picture:** `Project.image_name`, a 256 px square PNG without metadata, shown instead of the icon everywhere (`project_mark`).
- **Folder:** the path opens the file manager, a button the editor (`projects.editor`, `code`). The project's own folder only, as one argument, no shell; through `systemd-run --user` on Linux so that restarting Cairn does not close it.
- **Found on the way:** the daily clean-up deleted profile pictures (it knew resources only): it now knows every stored file's owner.

## D-068 · 2026-11-23 · accepted — The main Claude opens a project's Claude and hands it work
- `open_project_claude(project, work, task_id)` (main session only): the MCP server writes a `ClaudeRequest`, the web process opens the session (`handover_core.watch`) and answers; the tool waits 20 s. With a task, its Claude gets the brief and is lit on the plan (D-066). It is told to stay in the project, ask when unclear, and answer with `take_note`.
- **Guards:** Claude Code asks the owner first in every mode (`ask` rule, D-064); another session is refused; a request older than a minute, or left when Cairn restarts, is never opened; claimed before opening, so never twice; at most `claude.max_open` sessions; a project whose Claude is open is not typed into, a note is left.

## D-069 · 2026-11-23 · accepted — More MCP tools: schedule, resources, comments, describe_schema
- `mcp_plan_tools` (reading allowed up front: `schedule`, `list_resources`, `get_resource`, `list_comments`, `describe_schema`; asking the owner: `update_task`, `schedule_task`, `add_resource`, `attach_resource`, `comment_on_project`), on the same cores and pydantic schemas as the pages. `describe_schema` gives the schemas themselves, with the task types, statuses and moves from the settings. Invalid input names each wrong field.
- **Kept from Claude:** creating or attaching a skill (it would speak to later sessions), a file by its path, a project's instructions, the inbox tags. A resource's text is cut at 20 000 characters and marked as data.
- Left for Phase 6: changesets for bulk changes.

## D-070 · 2026-11-23 · accepted — Instances survive a restart of Cairn
- Owner need: come back the next morning and find what runs. On Linux and macOS an instance runs under a **runner** of its own (`runner.py`: a pseudo-terminal, a log file cut at 4 MB, a private Unix socket for keys and sizes, a state file), started on Linux by the session's systemd so that stopping Cairn's service does not stop it. Cairn sees it through `Survivor`, with `Pty`'s face: terminal, preview, stop and restart are unchanged.
- **As Cairn starts** (`instances_core.reattach`, before anything looks at the sessions) it follows again those still alive (the runner's command line names the session: a reused pid is never taken for it) and closes the others with their exit code. The log of an ended one is shown on its page and kept 7 days.
- The environment is passed by a 0600 file removed as soon as it is read, never on a command line.
- **Stop one found outside Cairn**: its process and children, or its container; pid and start time checked; never Cairn itself.
- Windows keeps the terminal in Cairn's process (ConPTY belongs to its creator). Not done: starting instances again after the machine restarts.

## D-071 · 2026-11-23 · accepted — Changesets: Claude proposes, the owner approves one by one
- `propose_changeset` (allowed up front: it only records a proposal) takes up to 60 items: create_task, update_task, set_status, link_tasks, comment; a task is its id or the key of an earlier item. It is **tried and rolled back** first, through the same cores, so a loop, a forbidden move or a missing task is told to Claude and never reaches the owner.
- **Review** (`/changesets/<id>`): each change with what it replaces and why; unchecking one refuses those that need it (checked again by the server). Applied in one batch as `claude:<session>`, all or nothing, undone at once (it then waits again). Announced in the panel, on the Claude page and on the project.
- Not in a changeset: statuses' workflow is not bypassed; skills, files, project instructions and deletions stay the owner's.

## D-072 · 2026-11-23 · accepted — Claude's tools, on a page
- Owner request. `/claude/tools`: Cairn's own tools (what each does, allowed or asking), and every tool called in the end of the conversations of the last 7 days (Claude Code's, MCP servers', skills), with calls, failures and last use. Names and counts only.

## D-073 · 2026-11-23 · accepted — An instance started with the machine
- `ProjectInstance.autostart`, off by default: started as Cairn starts for the first time since the machine did or the session opened again (a mark in the runtime folder), not at each restart of Cairn, so an instance the owner stopped stays stopped.

## D-074 · 2026-11-23 · accepted — Built with, and a footer
- Owner request: see the tools Cairn itself is made of (terminal in the browser, Vitrine…), and a cleaner footer. `/built-with` lists them by part of Cairn with what each does here; versions and licences come from `vendor.json`, the installed packages and PATH. A test fails when a vendored library or a dependency of `pyproject.toml` is missing from the list. The tools Claude calls stay on Claude → Tools (D-072).
- Footer on every page: Cairn and its version, Built with, source, licence, security; at the bottom of the window on a short page.

## D-075 · 2026-11-23 · accepted — Read a Claude running outside Cairn
- Owner request, besides moving it: see it in Cairn as in its terminal. **View** opens a terminal (`kind` log) that prints the conversation from its transcript as it grows: requests, answers, tool calls with what they changed and the start of their result. Read-only, and the other terminal is not touched. A live mirror is not possible: a terminal Cairn did not open cannot be attached to.
- What a conversation holds is untrusted: escape sequences and control characters (bidirectional ones too) are removed before anything is printed. The view is found again for the same conversation; the process is checked by pid and start time.
- **Background sessions** of Claude Code (registered as `bg`, run from a version's own file, so not named `claude`) are found and shown, to read only. A Claude that holds one at work is not moved nor stopped from Cairn: that would cut it. Found on the owner's machine: a conversation sent to the background had left its terminal's card on an old copy.

## D-076 · 2026-11-23 · accepted — From quick add to the full form
- Owner request: wherever a task is added in one line, a button opens the full form with the same words, already understood (project, dates, type, tags, priority, estimate, repetition) and, for a subtask, its parent. Also in the palette. The words go through `POST /tasks/quick/full`, so no token ends in the address.

## D-077 · 2026-11-23 · accepted — A git worktree per Claude
- A Claude opened on a task works in a worktree of its own (`<data>/worktrees/<project>/<branch>`), on `<type>/<task>` from the project's main branch; the same task finds it again. A setting (`claude.worktrees`, on) and a box in the launcher decide; a folder that is not a git repository is used as it is. The same when the main Claude hands over a task. Its rules say to stay in it.
- The project's Claude tab lists them: branch, task, commits, what is not committed, the Claude in them. **Removing** one takes the folder only: never `--force`, never with changes not committed, never with a Claude open in it, and the branch always stays.
- Not in a worktree: what git ignores (a virtual environment, `.env`).

## D-078 · 2026-11-23 · accepted — Day summary and time entries (Kimai)
- **The day** (`/day`): read on demand from git (every branch of every repository on the machine, the owner's commits only, a rebased or cloned commit once), GitHub through the owner's `gh` (pull requests, issues, commits of repositories not here), the tasks finished and timed in Cairn, and when the owner asked something to Claude (counted, never its words). Nothing is fetched. The facts are kept; the summary follows them until the owner writes in it.
- **Rules** (`/day/rules`): which repositories, words or kinds of work go to which project and activity. `guidance` is the owner's own words, for Claude; `save_time_rule` lets Claude write a rule when told where something goes. Nothing about an employer is in the code: another user sets their `.env` and their rules, or imports a rules file (no address, no token in it).
- **Entries** are drafts. The day's length (8 h) goes whole to the projects worked on that day, in equal parts, however long each took (owner's rule: one project, 8 h; two, 4 h each). Work no rule places is not counted; `recap.ignored` leaves personal repositories out.
- **Sending** is the owner's click, confirmed: not an MCP tool, refused to any other actor. Never over what Kimai holds, never twice (an entry whose answer was lost is found again). Cairn has no call that changes or deletes in Kimai.
- **The token** is in `.env` (owner's choice), read at each call, https only, no redirect followed, never in a page, a log, the database or the environment of a program Cairn starts.

## D-079 · 2026-11-23 · accepted — Every instance of the machine, in the menu
- Owner request: a menu entry with all that runs, by project, whoever started it; each project's name leads to it. What listens in a git folder of no project is listed apart, with a button that makes it a project (nothing else is done on it there). Looked at again every 8 seconds, only while the page is in front. What listens outside any git folder (the system's services) is not shown.

## D-080 · 2026-11-23 · accepted — Cairn from any Claude Code
- Owner request: in their own terminal, "start a project on Cairn". `this_project` (read) finds the project of the folder: the nearest folder that holds it, a worktree of it, or the only project it is a clone of (`place_core`, also used for the sessions seen outside Cairn). `start_project` makes it, once, only while Cairn runs; nothing is written in the folder; never for the home folder.
- The same MCP server is set up for every Claude Code of the machine. It finds who started it from the process above: a session Cairn opened keeps its identity, another acts as `claude:<conversation>` and its project is its folder's.
- `manage.py claude-connect show | on | off | status` puts in, or takes out, the MCP server (by `claude mcp`, user scope), the rules that ask before writing in Cairn in every permission mode, and the `cairn` skill. Shown before; a copy of `settings.json` is kept; it stops before any change if something there is not Cairn's.
- An outside session does not get the rules that keep Cairn's own files from sessions Cairn opens (D-064): it is the owner's own terminal.
- One command, `/cairn`, with arguments (`-init`, `-status`, `-next`, `-update`, `-bring`, `-copies`, `-note`) rather than several commands: the skill reads `$ARGUMENTS` (owner's choice).

## D-081 · 2026-11-23 · accepted — One project whatever its copies; what it already has, brought in
- Owner request: thirteen clones of a repository, each on its branch, are one project. **Copies** (`/projects/<slug>/copies`): the project's folder, its worktrees and every clone sharing one of its remotes, with branch, what is not committed or pushed, the pull request of that branch (matched on the head repository too, so another fork's branch of the same name does not count), instances and Claudes in it. Starting a project from one of the copies says the others.
- **Bring in** (`/projects/<slug>/bring`, shown after a project is made): to-do lists (open boxes, or list items of a TODO / ROADMAP file), GitHub's open issues and boards (`read:project` needed on the owner's `gh`), skills of the folder, commands its files give. What Cairn has already is left out. Tasks become a proposal (D-071); a skill is read in full and taken by the owner only, never by Claude (D-069); a command is added, not started. A link leading out of the folder is not read.

## D-082 · 2026-11-23 · accepted — What happens outside Cairn, in the project (first steps)
- A project's Claude tab lists the Claude Codes of the owner's terminals working in any copy of it (`place_core`), besides the ones Cairn opened.
- The Copies page (branches, changes, pull requests, what runs) and the Instances page read themselves again while in front (`<cn-refresh>`, every 15 and 8 seconds), never while something in them is in use or open. Nothing is written in the owner's repositories and nothing is polled when no page looks.

## D-083 · 2026-11-23 · accepted — Work linked to a project, a task, a subtask
- Owner request: link a branch, a commit, a pull request, a Claude conversation or a folder to a project, a task or a subtask, so that a Claude starts with the real context. On the task's Work tab and the project's About tab, by the API, and by Claude (`link_work`, asked; `linked_work`; `/cairn -link`).
- An instance of the project can be linked too (by its name): its state, folder, command and ports reach the brief. Instances show the folder they run in, on the project and on the Instances page.
- What Cairn made for a task is shown without being linked: its worktrees and the Claudes opened on it. A subtask also gets its parents' and its project's links.
- Each is described where it lives: its last commits from the project's copies, the pull request from GitHub, the conversation from Cairn. The task's brief has a **Linked work** section with all of it; text from a pull request is data, as everywhere else.

## D-084 · 2026-11-23 · accepted — A project from one machine to another
- Owner request: work at the office and at home. **Export** (project page) gives one file: the project, its tasks and subtasks, dependencies, conditions, timers, comments, resources with their files, linked work, instances. **Import** (Projects page) shows what it would change, then writes it all or nothing.
- Rows keep their ids, so the same project is merged back and forth: new rows added, changed ones taken when newer in the file, newer ones here kept. The folder and the address (slug) stay this machine's; a new project asks for its folder.
- An **exchange folder** (setting `projects.transfer_folder`: a Nextcloud, Dropbox or Syncthing folder, a USB key) spares the download and the upload: Export saves there, Import lists what is there. Mail cannot carry a file from a link (`mailto:` has no attachments), so it is not offered.
- Not in the file: secrets, tokens, the vault, `.env`, the history of changes, Claude's sessions. Scores and counters are recomputed. An import is not undoable: the preview says what it does first.

## D-085 · 2026-11-23 · accepted — A task per pull request; links picked from the project
- Owner request (Lookyloo: one task per pull request). **A task per pull request or issue** (project's Actions menu) lists the open pull requests and issues of the project's GitHub repository and the branches of its copies, each with the task that has it already; the chosen ones become tasks (an issue a bug), each linked to it and, for a pull request, to its branch. Undoable in one step.
- A task's Linked work tab offers the same, **Pick from the project**, one click a link. An issue is a kind of link too.
