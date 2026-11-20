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
- Front end: Jinja + Vue 3 UMD (no build step), ES modules, delimiters `[[ ]]`; reusable components in `static/js/components/` + `static/css/components/`; feature code in `static/{js,css}/<feature>/`.
- No inline `<style>`/`<script>`, no hard-coded colours (design tokens only), no `console.log`, no `| safe` on user data. Strict CSP must keep working.
- All code, Markdown, JSON, logs and diffs are displayed through the Vitrine wrapper component, fed via `content`/`data` properties.
- Configuration values in `app/config/<key>.json` settings, not in code.
- Soft delete from user actions; hard delete only from the trash.
- No dead code, no duplicates; refactor when two things look alike.
- Before declaring done: tests (`python manage.py test`), `ruff`, `bandit -r app/`.

## Layout
See `docs/ARCHITECTURE.md` §2. Commands will be listed here once the skeleton exists (Phase 2).
