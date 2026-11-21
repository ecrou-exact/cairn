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
- [ ] Read Agent SDK pages not yet covered (permissions, hooks, sessions, MCP, streaming input); verify per-run `ANTHROPIC_API_KEY` via `env`
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
- [ ] Multi-user system (later, on request)

## Phase 4 — Graph (Pivotick, full integration per §4)  *(current)*
- [x] Pivotick vendored, data adapter (`graph_core`, `/api/graph`), task cards as nodes, edge styles per kind, `--pvt-*` mapped to Cairn tokens, Cairn chrome (D-035)
- [x] Left-to-right plan layout computed by Cairn (steps as columns, pinned cards, straight lines), opening view on what to do now
- [x] Critical path computed and lit; side panel on click; live updates through SSE
- [ ] Layout switch remembered per view; write-path hooks → API; context menus; side panel editing
- [ ] Filters, search/focus, collapse/expand, clustering, legend, data table; encodings (status, priority, deadline, blocked, running agent, instance)
- [ ] Edit from the graph (link tasks by dragging, change status from the panel), filters by state / tag, 300+ node tuning

## Phase 5 — Claude
- [ ] App MCP server (typed tools, `describe_schema`, changeset tool, authz per scope)
- [ ] Agent runner on Claude Agent SDK (`ClaudeSDKClient` per run, own asyncio loop in the worker)
- [ ] Stop / "pause" (interrupt + resume by session id) / mid-run instruction / re-run with corrections
- [ ] Permission UI (`can_use_tool` + `PreToolUse` hooks), directory allowlist (`cwd` + `add_dirs`), sandbox on Linux/macOS
- [ ] Git worktree per run, context files, hard rules via system prompt append
- [ ] Chat (global/scoped), accounts/models, usage dashboard, skills library

## Phase 6 — Planning intake  ·  Phase 7 — GitHub  ·  Phase 8 — Instances & ports
- [ ] Intake → changeset → approval → graph
- [ ] Ask Claude to fill a task from a few words (read-only research run → changeset), owner request 2026-11-21 (D-029)
- [ ] GitHub accounts, inbox, link/sync, webhooks or polling
- [ ] Instances: definitions, registry, port allocation (psutil, works on all OS), supervision, logs (`vt-log`), header indicator

## Phase 9 — Modules  ·  Phase 10 — Calendar & activity  ·  Phase 11 — Hardening & release
- [ ] Module registry, event automations, task action modules
- [ ] Calendar, scheduled runs, Gantt timeline, activity feed, right-now panel, alerts
- [ ] Security review, E2E (Playwright), docs, logo, packaging, release checklist
