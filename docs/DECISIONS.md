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

## D-008 · 2026-11-20 · proposed — Frontend
- **Choice:** server-rendered Jinja templates + per-component JS modules (ES modules, no inline scripts), Bootstrap 5.3 (latest stable at build time), Font Awesome 7 Free (matches Pivotick default), esbuild or Vite only to bundle Pivotick; no SPA framework unless analysis of Flowintel/Rulezet says otherwise (Rulezet uses Vue 3 on parts of the frontend — to confirm in conventions).
- **Calendar:** FullCalendar (MIT standard plugins) — to evaluate vs. alternatives; Gantt: to evaluate (Frappe Gantt MIT, or a Pivotick-consistent custom SVG).

## D-009 · 2026-11-20 · proposed — Design skill
- **Candidates:** Anthropic `frontend-design` skill (anthropics/skills, Apache-2.0) — explicitly targets the "AI-generated look" (generic fonts, purple gradients, predictable layouts); others to compare during Discovery.
- **Choice pending** comparison; whatever is chosen is installed as a project skill in `.claude/skills/` and switchable from the app's Skills page.

## D-010 · 2026-11-20 · proposed — Other libraries (to justify individually before adding)
`psutil` (processes/ports, all OS) · `keyring` (OS secret store) · `cryptography` (AES-GCM vault) · `argon2-cffi` · `pyotp` · `Flask-Login`, `Flask-WTF` (CSRF), `Flask-Limiter` · `pydantic` v2 (schemas shared by API/forms/MCP) · `httpx` · `GitPython` or plain `git` subprocess for worktrees · `dateparser` (NL dates) · `icalendar` (read-only feed) · `platformdirs` · tests: `pytest`, `playwright`; lint: `ruff`, `mypy`, `eslint`; security: `pip-audit`, `bandit`, `npm audit`.
