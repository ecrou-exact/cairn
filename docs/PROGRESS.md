# Progress

> Living checklist. Re-read at the start of every session. Phases follow `PROJECT_BRIEF.md` §18.
> A phase starts only when the previous one works end to end.
> **Platform:** production target is Ubuntu Linux; the app must run on Linux, macOS and Windows (see `docs/DECISIONS.md` D-001).

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[?]` waiting for owner

---

## Phase 1 — Discovery  *(current)*
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
- [~] Deep read of Vitrine source (delivery decided, D-012; per-component attributes to read in Phase 2 prep) (common attributes, vt-json, vt-diff, vt-log, vt-markdown, `configure()`); pick bundle vs loader
- [ ] Read Agent SDK pages not yet covered (permissions, hooks, sessions, MCP, streaming input); verify per-run `ANTHROPIC_API_KEY` via `env`
- [x] Compare design skills, propose a base (D-009) — install after reading their source
- [x] Write `docs/ARCHITECTURE.md`, `docs/SECURITY.md` (threat model), `CLAUDE.md` (proposed)
- [x] Propose names + 3 logo directions (`docs/IDENTITY.md`, `docs/brand/`)
- [?] Batch the §19 questions to the owner
- [?] Owner approval of architecture and design direction

## Phase 2 — Foundations
- [ ] Repo skeleton (Flask app factory, `features/` component layout like Rulezet, uv, pyproject, ruff, pytest, pre-commit)
- [ ] Cross-platform base: `pathlib` everywhere, `platformdirs` for data/config dirs, no shell=True, CI matrix ubuntu / macos / windows
- [ ] Config (env + settings table), SQLAlchemy + Alembic, SQLite dev / PostgreSQL prod
- [ ] Base entity mixin: UUID, timestamps, `created_by`, history/audit table + diff + undo service
- [ ] Auth: owner account, Argon2, TOTP (WebAuthn optional), CSRF, rate limiting, secure cookies, localhost bind
- [ ] Secrets vault (AES-GCM; master key from OS keyring, fallback env/key file with 0600 perms on headless Ubuntu)
- [ ] Security headers + strict CSP, Trusted Types (Vitrine policy)
- [ ] Design tokens + themes (light, dark, 1–2 distinctive) mapped to Bootstrap, `--pvt-*`, `--vt-*`
- [ ] Component library (table/card list, filter bar, pagination, form fields, modal, side panel, badge, status pill, empty/loading/error, toast, confirm dialog)
- [ ] Server-side list engine (filter/search/sort/paginate on full dataset, URL state, saved views)
- [ ] Vitrine wrapper component (single config point)
- [ ] Job queue (lanes, retries/backoff, timeouts, cancellation) + Jobs page
- [ ] Realtime channel (SSE) + client event bus
- [ ] Packaging skeleton: `install.sh` (Ubuntu), systemd units (web + worker), Docker Compose, dev launcher that also works on macOS/Windows
- **Done when:** login, theme switch, empty app shell, jobs page and live push work end to end, tests green on all three OS in CI.

## Phase 3 — Core planning
- [ ] Projects CRUD (§2.1), tasks + subtasks (§2.2), configurable types/statuses/workflow
- [ ] Dependencies (task→task, external conditions), cycle detection, blocked state, critical path
- [ ] Resources + resource library
- [ ] Quick-add with NL parsing; full tabbed form; inline + bulk edit; pickers; drag&drop/paste upload; Markdown editor with Vitrine preview; templates
- [ ] Priority score (configurable weights, "explain why"), "What should I do now?", deadline risk
- [ ] History/undo UI, command palette (Ctrl/Cmd+K), shortcuts
- [ ] JSON schema registry shared by API, forms and MCP tools

## Phase 4 — Graph (Pivotick, full integration per §4)
- [ ] Graph wrapper + data adapter; node/edge type styling; `--pvt-*` theming
- [ ] Layout switch remembered per view; write-path hooks → API; context menus; side panel editing
- [ ] Filters, search/focus, collapse/expand, clustering, legend, data table; encodings (status, priority, deadline, blocked, running agent, instance)
- [ ] Critical path & chain highlight; live updates via SSE + runtime API; 300+ node tuning

## Phase 5 — Claude
- [ ] App MCP server (typed tools, `describe_schema`, changeset tool, authz per scope)
- [ ] Agent runner on Claude Agent SDK (`ClaudeSDKClient` per run, own asyncio loop in the worker)
- [ ] Stop / "pause" (interrupt + resume by session id) / mid-run instruction / re-run with corrections
- [ ] Permission UI (`can_use_tool` + `PreToolUse` hooks), directory allowlist (`cwd` + `add_dirs`), sandbox on Linux/macOS
- [ ] Git worktree per run, context files, hard rules via system prompt append
- [ ] Chat (global/scoped), accounts/models, usage dashboard, skills library

## Phase 6 — Planning intake  ·  Phase 7 — GitHub  ·  Phase 8 — Instances & ports
- [ ] Intake → changeset → approval → graph
- [ ] GitHub accounts, inbox, link/sync, webhooks or polling
- [ ] Instances: definitions, registry, port allocation (psutil, works on all OS), supervision, logs (`vt-log`), header indicator

## Phase 9 — Modules  ·  Phase 10 — Calendar & activity  ·  Phase 11 — Hardening & release
- [ ] Module registry, event automations, task action modules
- [ ] Calendar, scheduled runs, Gantt timeline, activity feed, right-now panel, alerts
- [ ] Security review, E2E (Playwright), docs, logo, packaging, release checklist
