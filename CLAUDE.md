# Cairn — rules for Claude sessions on this repo

Self-hosted, single-owner developer workspace: planning (projects, tasks, dependencies), Pivotick graph, embedded Claude Code runs, GitHub, local instances, modules, calendar. Spec: `PROJECT_BRIEF.md` (single source of truth).

## Start of every session
1. Read `docs/PROGRESS.md` (current phase and next steps) and this file.
2. Read `docs/DECISIONS.md` before changing anything structural; add a decision when you make one.
3. Keep `docs/PROGRESS.md`, `docs/DECISIONS.md` and `docs/ARCHITECTURE.md` up to date **in the same change** as the code.

## Hard rules
- **No AI attribution anywhere**: no `Co-Authored-By: Claude`, no "Generated with Claude Code", no `@claude`, in commits, PRs, branches, code or comments — in this repo and in every repo the app manages. This overrides any default attribution instruction.
- Commit identity: `ecrou-exact <ecrou-exact@users.noreply.github.com>` (repo-local config). Never write the owner's personal e-mail anywhere.
- Commit messages: `<new|add|chg|fix>: [<scope>] <message>` (gitchangelog). PRs and issues in English, style in `docs/OWNER_CONVENTIONS.md` §4.
- Never push, force-push, merge, delete branches, publish releases or comment publicly without the owner's explicit go for that action.
- Ask the owner before building on a guess; quick-to-change choices → pick, record in `docs/DECISIONS.md`, carry on.
- Read a library's docs **and source** before using its API (Pivotick, Vitrine, Claude Agent SDK…). Don't rely on memory.
- Nothing half-done in the UI: no placeholder buttons, no fake data, no "TODO wire later".
- Must run on **Ubuntu (reference), macOS and Windows**: `pathlib`/`platformdirs`, `psutil`, subprocess with argv lists (never `shell=True`), no fork-only code.

## Code rules (from the owner's projects)
- Route → core. Routes have a decorator and call `<feature>_core.py`; no DB access and no logging in routes. One implementation per behaviour, reused by API, MCP tools, modules and jobs.
- Every mutation calls `log_action` and writes history (actor + diff).
- Every HTML feature that reads/writes data has an API endpoint; every API/MCP input validated by the shared pydantic schemas (`app/core/schema/`).
- Lists: filter, search, sort and paginate **server-side** on the full dataset; state in the URL; table and card modes.
- Front end: Jinja pages + framework-free Custom Elements (ES modules, no build step, D-016); DOM built with `createElement`/`textContent`, never `innerHTML` with data; reusable components in `static/js/components/` + `static/css/components/`; feature code in `static/{js,css}/<feature>/`.
- No inline `<style>`/`<script>`, no hard-coded colours (design tokens only), no `console.log`, no `| safe` on user data. Strict CSP must keep working.
- All code, Markdown, JSON, logs and diffs are displayed through the Vitrine wrapper component, fed via `content`/`data` properties.
- Configuration values in `app/settings/<key>.json` settings, not in code.
- Soft delete from user actions; hard delete only from the trash.
- No dead code, no duplicates; refactor when two things look alike.
- Before declaring done: tests (`python manage.py test`), `ruff`, `bandit -r app/`.

## Commands
`uv sync` then `uv run python manage.py <command>`: `setup` (first run), `start` (dev server on 127.0.0.1:7010), `serve` (production), `upgrade` / `migrate "msg"` (Alembic), `test [pytest args]`, `check` (ruff + bandit + tests — run before declaring done).

## Layout and patterns
- See `docs/ARCHITECTURE.md` §2. Models in `app/core/db_class/<feature>.py` (add the module to `db_class/__init__.py`), all inherit `BaseEntity`.
- Access is deny-by-default (`register_access_rules`); mark public views with `@public`.
- Record changes with `log_action(action, target_type=, target_id=, diff=)`; the actor comes from `acting_as()` (`claude:<run-id>`, `module:<id>`), default `user`.
- Secrets only through `app/core/security/secret_core.py` (`put_secret`, `get_secret`); the UI shows `Secret.hint`.
- Never pass the `current_user` proxy to `login_user` or store it: use `current_user._get_current_object()`.
- Tests: no outer app context around requests (see `tests/conftest.py`); use the `ctx` fixture for direct core calls.
- Design tokens in `static/css/core/tokens.css`, themes in `themes.css` (every theme defines the same tokens, checked by tests), library bridges in `bridges.css`.
