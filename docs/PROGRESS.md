# Progress

> Living checklist. Re-read at the start of every session. Phases follow `PROJECT_BRIEF.md` §18.
> A phase starts only when the previous one works end to end.
> **Platform:** production target is Ubuntu Linux; the app must run on Linux, macOS and Windows (see `docs/DECISIONS.md` D-001).

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[?]` waiting for owner

---

## Phase 1 — Discovery  *(done 2026-11-21, D-014)*
Goal: owner approves architecture + design direction.

- [x] Read `PROJECT_BRIEF.md` in full
- [x] First research pass on external tools (Pivotick, Vitrine, Claude Agent SDK, design skills) → `docs/DECISIONS.md` (draft)
- [x] Analyse owner repos (`ecrou-exact`): rulezet-core, vitrine, flowintel, other recent repos on GitHub
  - [x] Structure, layering, component organisation (templates / static js / css per component)
  - [x] Commit style (seen: `fix: [scope] message`, gitchangelog), PR / issue style, docs style
  - [x] Tooling: uv + pyproject, Alembic, tests layout, linters, install/launch/update scripts
  - [x] Background jobs: Rulezet uses a DB-backed `BackgroundJob` queue + `worker.py` + APScheduler (no Redis) — study it
  - [x] Write `docs/OWNER_CONVENTIONS.md`
- [~] Deep read of Pivotick source (constructor + data API verified, D-013; Simplify/filters/table/plugins still to read in Phase 4 prep) (typed API reference, Simplify, filters, legend, table, plugins, history, `_variables.scss`); confirm constructor signature
- [x] Deep read of Vitrine source (configuration, theming, security, common attributes, vt-log, vt-json, editing; `main` built and vendored, D-019)
- [x] Read Agent SDK pages not yet covered (permissions, hooks, sessions, MCP, streaming input) and its source; per-run `env` verified (D-049) — sign-in question open
- [x] Compare design skills, propose a base (D-009) — install after reading their source
- [x] Write `docs/ARCHITECTURE.md`, `docs/SECURITY.md` (threat model), `CLAUDE.md` (proposed)
- [x] Propose names + 3 logo directions (`docs/IDENTITY.md`, `docs/brand/`)
- [x] §19 questions answered (owner delegated, D-014)
- [x] Architecture and design direction approved (D-014)

## Phase 2 — Foundations  *(done except deployment files, saved views and CI on three OS — needs a push)*
- [x] Repo skeleton (app factory, `features/` layout, uv + `uv.lock`, ruff, bandit, pytest, `manage.py`) — pre-commit still to add
- [x] Cross-platform base: `pathlib`, `platformdirs` data dir, argv-only subprocess, CI matrix ubuntu / macos / windows × Python 3.12 / 3.13
- [x] Config from env/.env, SQLAlchemy + Alembic, SQLite dev / PostgreSQL extra, JSON settings (`app/settings/`) with typed overrides, Settings page + API (D-022)
- [~] `BaseEntity` (UUID, timestamps, `created_by`, soft delete), `Activity` log with actor + diff + batch — undo service comes with the first editable entities (Phase 3)
- [x] Auth: single owner, Argon2id, TOTP with replay protection, CSRF, rate limits, Strict cookies, session version (password change signs out others), deny-by-default access, localhost bind — WebAuthn optional later
- [x] Secrets vault (AES-256-GCM bound to the secret name; master key from env, OS keyring or 0600 key file)
- [x] Security headers + strict CSP (no inline, no eval); Trusted Types report-only (D-018)
- [~] Design tokens + 4 themes + Auto, mapped to Bootstrap and Vitrine, theme picker in Settings — `--pvt-*` bridge comes with the graph (Phase 4)
- [~] Component library — done: table/card list, filter bar, sortable headers, pagination, status pill, badge, empty state, loading/error state, live notice, live status, confirm dialog (`<cn-confirm>`); to do with their first use in Phase 3: form fields, modal, side panel, toast
- [~] Server-side list engine (filter/search/sort/paginate on full dataset, URL state, API JSON) — saved views to do
- [x] Vitrine wrapper component `<cn-vitrine>` (single config point, theme sync, form field mode)
- [x] Job queue (lanes, retries/backoff, timeouts, cancellation, crash recovery, SQLite single-worker lock, daily clean-up) + Jobs page + job page with live log + API (D-021)
- [x] Realtime channel (SSE over the event table, gap-safe resume) + client event bus + header live indicator (D-020)
- [~] `manage.py` works on all OS (setup / start / serve threaded / worker) — `install.sh`, systemd units, Docker Compose still to do
- **Done when:** login, theme switch, empty app shell, jobs page and live push work end to end, tests green on all three OS in CI.

## Phase 3 — Core planning  *(done except the JSON schema registry, which comes with the MCP server in Phase 5)*
- [x] Projects CRUD (§2.1): list (cards/table, stats), page with its tasks, form, colours, delete with its tasks, trash
- [x] Tasks + subtasks (§2.2), configurable types / statuses / workflow transitions / default status (D-023)
- [x] Dependencies (blocks, follows, relates, duplicates), cycle detection naming the loop, blocked state everywhere, "why blocked" chain — critical path left for the graph (Phase 4)
- [x] Resources + resource library (D-027): links with background preview, GitHub items, notes, snippets, tools, file paths, uploads; attach anywhere, reuse identical files, trash, undo, API — snapshot for Claude and image descriptions come with Phase 5
- [x] Quick add with natural-language parsing and live preview, duplicate detection; full tabbed form; Markdown editors through Vitrine; unsaved-changes guard
- [x] Inline status / priority edit, bulk edit (status, priority, project, tags, trash) in one undoable batch, task templates (D-026)
- [x] File upload: drop, choose or paste a screenshot anywhere on a task / project / library page (Vitrine `vt-upload`), images re-encoded without metadata, files served download-only
- [x] Priority score (configurable weights, explanation), "What should I do now?", needs-attention radar, deadline risk on dependency chains against working time
- [x] History with undo per action (D-024), trash with restore and delete for good, command palette (Ctrl/Cmd+K), keyboard shortcuts (`?` lists them)
- [x] Cairn's own roadmap as a plan (`docs/roadmap.json`, `python manage.py roadmap`)
- [x] Time tracking (start / stop, time spent vs estimate) (D-025)
- [x] Comments thread and corrections log on tasks and projects (retire / reactivate, inherited from project and parent tasks); task brief for Claude shown, downloadable and in the API (D-028)
- [x] Related context per task: close tasks, matching resources, schedule fit — panel, brief, API; base of "Ask Claude to fill a task" (D-029, roadmap `fill-task`, Phase 6)
- [x] Recurring tasks: form, quick add (`weekly`, `every 2 weeks`, `tous les mois`), next occurrence on done, undoable (D-030)
- [x] External conditions (review, upstream release, PR merged, date, other) block the task until they happen; date ones lift themselves (D-031) — GitHub auto-resolution in Phase 7
- [x] Custom task fields (text, number, date, link, choice list) defined in Settings, checked by the core (D-032)
- [~] JSON schema registry shared by API, forms and MCP tools — schemas exist per feature (`core/schema/`), registry/`describe_schema` comes with the MCP server (Phase 5)

## Interface and account (owner requests, 2026-11-21)
- [x] Visual identity: contour header band, trail-marked sidebar, slabs instead of outlined boxes, Today at a glance, sign-in brand panel (D-033)
- [x] Foldable menu, drawer menu on phones
- [x] Profile (display name, about, picture) and connected accounts (GitHub, Claude API key, others) in the vault, checked by a job; GitHub previews of private issues / PRs (D-034)
- [x] One look on every page (D-042): dark contour page bands, stone buttons, field wells, filters folded behind a button, floating bulk bar, stone empty states, restyled drop zone with drop-anywhere
- [ ] Multi-user system (later, on request)

## Phase 4 — Graph (Pivotick, full integration per §4)  *(done 2026-11-22)*
- [x] Pivotick vendored, data adapter (`graph_core`, `/api/graph`), task cards as nodes, edge styles per kind, `--pvt-*` mapped to Cairn tokens, Cairn chrome (D-035)
- [x] Left-to-right plan layout computed by Cairn (steps as columns, pinned cards, straight lines), opening view on what to do now
- [x] Critical path computed and lit; side panel on click; live updates through SSE
- [x] Levels: cases per project, a case opens its subtasks' graph with a breadcrumb, dependencies lifted between levels; hover peek; a graph on every task page (D-036)
- [x] View remembered per graph for the session; right-click menu on cards; edits go through the API (D-043) — no layout switch: Cairn lays the plan out (D-035)
- [x] Framing computed by Cairn (Pivotick's first fit off), table view in plan order (`t`), contour ground (D-043)
- [x] Find in the graph (`/`): any task of the view by its title, subtasks inside a case included; the view glides to the card that holds it, selected, side panel open (D-040)
- [x] Collapse/expand and clustering are the levels (cases, a case's own graph, everything; D-036); data table (D-043). Encodings of a running agent and of an instance come with Phases 5 and 8
- [x] Edit from the graph's side panel: move to an allowed status, link to another card (blocks, blocked by, comes after, relates); the graph and the panel follow live
- [x] The graph lives in the projects: plan of projects ordered by project links on the Projects page, a project's plan in its Plan tab, no Graph menu entry (D-044); project page in tabs (D-045); task page in tabs with a band and folded forms (D-047)
- [x] Path above the graph (All projects / project / case) with Up and Backspace to go back one level (D-042)
- [x] Link mode (L or the link button): touch what comes first, then what it blocks; works by touch on phones; filters by state (ready, blocked, late, due soon) and tag, a case kept when a subtask matches
- [x] 300+ cards measured: ~0.4 s server, ~0.8 s first draw, < 4 ms per zoom (D-046)

## Phase 5 — Claude  *(current)*
- [x] Claude Code in a terminal inside Cairn (the owner's own `claude`, own sign-in), in a project's folder or on a task with its brief; every session on the machine in view with its context %, model, title, activity; running count in the menu (D-050)
- [x] Claude from anywhere: launcher (header, Alt+C, palette, buttons in context), intents (task, pull request, fix, review, new project), owner's rules in every session, resume any conversation in Cairn (D-051)
- [x] Cairn's MCP server over stdio in every session opened from Cairn: read the plan, create tasks and subtasks, change statuses, link, comment — changes approved in Claude Code, logged and undoable as `claude:<session>` (D-052)
- [x] What each Claude is doing: its last steps and now line on every card, the editor or terminal an outside session runs in; running instances with their ports and log on the Claude page (D-054)
- [x] Terminal fixes: every key reaches Claude, closing never hangs on Linux / macOS, a conversation open elsewhere is moved to Cairn instead of doubled (D-055)
- [x] Free sessions linked to a project at any time, a folder read into a new project (`update_project`), stop any Claude, account usage in the menu and on sessions (D-056)
- [x] Claude skills in the library, given to the sessions opened from Cairn; context gauge on the window Claude Code reports (D-058)
- [x] Claude live graph: sessions, their agents, running tools, background tasks and processes, skills; one session in full with its files, commands, searches and servers since the last request (D-059)
- [x] Cairn's own Claude, opened with the app; notes between it and the projects' Claudes (`take_note`, `inbox`, `note_done`), `create_project`, `claude_sessions` (D-060)
- [x] The main Claude in a panel beside every page (open, fold, stop, relaunch), knowing the page in front, able to work on Cairn itself (D-063)
- [x] Security review of the main Claude's access: findings fixed or recorded (D-064)
- [x] Claude on the plan's graph: the task it is on lit with its current step, its live graph one click away (D-066)
- [x] A project's icon chosen with Vitrine's icon picker, or a picture; its folder opened in the file manager or the editor (D-067)
- [x] The main Claude opens a project's Claude and hands it work, approved by the owner (D-068)
- [x] More MCP tools: schedule, task edits, resources, comments, `describe_schema` (D-069) — changesets for bulk changes come with Phase 6
- [ ] Later, optional: agent runs through the Claude Agent SDK with an API key (D-049, D-050) — the terminal covers the owner's own Claude Code
- [ ] Stop / "pause" (interrupt + resume by session id) / mid-run instruction / re-run with corrections
- [ ] Permission UI (`can_use_tool` + `PreToolUse` hooks), directory allowlist (`cwd` + `add_dirs`), sandbox on Linux/macOS
- [ ] Git worktree per run, context files, hard rules via system prompt append
- [ ] Chat (global/scoped), accounts/models, usage dashboard, skills library

## Phase 6 — Planning intake  ·  Phase 7 — GitHub  ·  Phase 8 — Instances & ports
- [x] Changesets: proposed by Claude, tried first, approved one by one, applied and undone at once (D-071)
- [x] Claude's tools on a page (D-072); an instance started with the machine (D-073)
- [ ] Intake: from free text and attachments to a changeset (the main Claude does it by its rules; a guided form is left)
- [ ] Ask Claude to fill a task from a few words (read-only research run → changeset), owner request 2026-11-21 (D-029)
- [ ] GitHub accounts, inbox, link/sync, webhooks or polling
- [x] Instances: definitions per project, start / stop / restart in a terminal (logs with history), port check and next free port as PORT, listening ports shown as links (D-053)
- [x] Instances running outside Cairn (other clones, worktrees, Docker) in each project, with their ports and their logs in a terminal (D-061)
- [x] Cairn starts with the session on Linux: `manage.py autostart on` (D-062)
- [x] Instances survive a restart of Cairn (Linux, macOS), their log kept; stop one found outside Cairn (D-070)
- [ ] Instances: indicator in the header, restart on crash, registry across projects

## Phase 9 — Modules  ·  Phase 10 — Calendar & activity  ·  Phase 11 — Hardening & release
- [ ] Module registry, event automations, task action modules
- [ ] Owner ideas (2026-11-23), later: mail connected for Claude; evening summary of what was done with its branches, for a day or a period, then sent to the owner's time-tracking API
- [ ] Calendar, scheduled runs, Gantt timeline, activity feed, right-now panel, alerts
- [ ] Security review, E2E (Playwright), docs, logo, packaging, release checklist
