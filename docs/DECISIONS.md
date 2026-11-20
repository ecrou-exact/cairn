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
