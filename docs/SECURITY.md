# Security and threat model

> Status: **proposed** (Phase 1). Security is the first priority of every decision (`PROJECT_BRIEF.md` §11).

## 1. What we protect
| Asset | Why it matters |
|---|---|
| API keys (Anthropic), GitHub tokens, other service keys | money, write access to the owner's repos and to upstream projects |
| Source code on disk (projects, worktrees) | integrity of open-source projects the owner maintains |
| The owner's GitHub identity (push, PR, comments, releases) | public actions in the owner's name |
| Task data, notes, attachments | private plans, unpublished security work |
| The machine itself | Claude and instances execute commands |

## 2. Actors and trust
- **Owner** — the only trusted human. Authenticated (password + TOTP).
- **Claude runs** — semi-trusted: act for the owner, but can be manipulated by content they read.
- **Content from outside** (URLs, issues, PRs, files, images, repo docs) — **untrusted**. It can inform, never command.
- **Modules** — trusted code, limited to their declared permissions.
- **Network** — untrusted; default bind is `127.0.0.1`.

## 3. Threats and mitigations
| # | Threat | Mitigation |
|---|---|---|
| T1 | Someone on the network reaches the app | bind to localhost by default; remote exposure needs explicit config + HTTPS (reverse proxy) + `SESSION_COOKIE_SECURE`; auth even locally |
| T2 | Password guessing / session theft | Argon2id, TOTP (WebAuthn optional), Flask-Limiter on auth, HttpOnly + SameSite=Strict cookies, session rotation on login, idle timeout |
| T3 | CSRF | Flask-WTF CSRF on every state-changing request (API from the front end included); external API only with `X-API-KEY` |
| T4 | XSS through Markdown, issues, logs, Claude output | strict CSP (`default-src 'self'`, no `unsafe-inline`/`unsafe-eval`, `object-src 'none'`, `base-uri 'none'`, `frame-ancestors 'none'`), Trusted Types (`vitrine` policy + app policy), Vitrine for all rendering with `content`/`data` properties, Pivotick `renderNode` built with `textContent` only, Jinja autoescape, no `| safe` on user data |
| T5 | Prompt injection from fetched content | content wrapped and labelled as untrusted data in prompts; Claude writes go through **changesets** by default; side-effect tools (push, PR, comment, release, delete) always require owner confirmation unless an `auto` module allows that exact action in that scope; `PreToolUse` hook denies anything outside the scope |
| T6 | Claude escapes its directory or runs dangerous commands | `cwd` = worktree, `add_dirs` = allowlist only; `disallowed_tools` patterns for destructive commands (`rm -rf`, `git push --force`, `curl … | sh`…); approval UI for everything not pre-approved; Agent SDK sandbox enabled on Linux/macOS (`sandbox.enabled`, `filesystem.denyWrite`, network allowlist) |
| T7 | Secrets leak (DB dump, logs, front end, Claude context) | vault: AES-256-GCM, master key from OS keyring or `CLAUDE_MANAGER_MASTER_KEY` / key file (0600) on headless servers, never in DB or repo; masked after save; log filter redacting known secret values; each run gets only its own API key via `env`; GitHub token never given to Claude — GitHub actions go through app tools |
| T8 | Path traversal on uploads/downloads/resources | storage under one root, random file names, `Path.resolve()` + `is_relative_to(root)` checks, size and type limits, images re-encoded, served with `Content-Disposition` + `X-Content-Type-Options: nosniff` |
| T9 | Command injection (instances, git, modules) | commands stored as argv lists, `subprocess` without shell, values never interpolated into shell strings; git called with `--` before paths |
| T10 | SSRF through URL fetching | fetcher blocks private/loopback/link-local ranges (re-checked after DNS and redirects), size/time limits, no credentials forwarded |
| T11 | Malicious or compromised dependency / skill | pinned versions (`uv.lock`, vendored front-end files with SRI), `pip-audit`, `bandit`, CodeQL in CI, Dependabot; third-party skills reviewed before install and installed read-only |
| T12 | A module or run does something irreversible | declared permissions per module; confirmation for external side effects; audit log; undo for app data; never force-push / delete branches / publish without explicit permission |
| T14 | The Claude terminal (D-050) used to run something else, or reached by someone else | only the configured Claude Code executable is started, as an argv list, never a shell; only in a folder the owner chose (a project's, or any existing one when free, D-056); every start and end logged with its folder; input and output endpoints behind the owner's session (deny by default) and CSRF on writes; no WebSocket, so no cross-site socket; Cairn binds to localhost (T1). It is the owner's own Claude Code with their own permissions and sign-in: what it may do there is Claude Code's permission system, as in any terminal. The terminal page allows `<style>` only with its response nonce (xterm.js), scripts stay `'self'`. The dock shows such a page in a frame, allowed to Cairn's own pages only (D-063). The process inherits Cairn's environment minus `CLAUDECODE`: keep secrets out of the web process's environment (the vault holds them) |
| T13 | Unauthorised MCP access | the MCP server is a stdio child of the Claude Code session Cairn opened (no listening port, nothing for another process to call); it runs as that session (`claude:<id>`), every change logged and undoable; changing tools need the owner's approval in Claude Code; only planning data is exposed (no secrets, no files) |

## 4. Audit
Every sensitive action is logged with actor and diff: logins, credential changes, account switches, pushes, PRs, comments, releases, module executions, permission decisions, settings changes.

## 5. Reporting
Once public: `SECURITY.md` at the repo root explains how to report a vulnerability privately (GitHub private vulnerability reporting).
