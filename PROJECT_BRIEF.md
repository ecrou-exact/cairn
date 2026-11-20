# Project Brief — AI-Native Developer Workspace

> **Audience:** Claude Code. This document is the single source of truth for building this application.
> Read it in full before writing any code. When something here is ambiguous, ask the owner before building on a guess; for anything quick to change, pick the most sensible option, write it down in `docs/DECISIONS.md`, and carry on.

---

## 0. How you must work on this project

1. **Take your time.** Quality beats speed. There is no deadline for the first version; there is a very high bar for quality, coherence and finish.
2. **Keep a living memory in Markdown**, updated as you go (not at the end):
   - `docs/PROGRESS.md` — what is done, in progress, next; checklist per phase (see §18).
   - `docs/DECISIONS.md` — architecture/design decisions with date, context, options considered, choice and reason.
   - `docs/ARCHITECTURE.md` — current architecture, data model, module map, data flows.
   - `CLAUDE.md` (repo root) — conventions and rules for any future Claude session working on this repo.
   Re-read `docs/PROGRESS.md` and `CLAUDE.md` at the start of every session.
3. **Study the owner's way of working first.** The owner works on open-source projects, all hosted on GitHub, and uses Claude Code heavily. Before designing, analyse their recent repositories (structure, stack, naming, commit style, PR style, issue style, docs style, UI patterns). Reference projects for UI and code organisation: **Rulezet** and **Flowintel** (component-based Flask apps). Summarise what you learned in `docs/OWNER_CONVENTIONS.md` and follow it.
4. **Research before building.** For UI/UX design, find and load well-regarded design skills / guidelines (see §14). For every external library (Pivotick, Vitrine, etc.), read its documentation and source before integrating it — do not guess its API.
5. **Feel free to pull in external tools and libraries** when they solve a problem well, but justify each dependency in `docs/DECISIONS.md` (maintenance status, licence, size, security).
6. **Everything must work end to end.** No placeholder buttons, no fake data, no "TODO: wire later" in the UI. A feature is either finished and connected to the backend, or it is not shipped.
7. **Document everything.** The project will be published on GitHub as an open-source project (see §16).
8. **Security comes first** in every decision (see §11).
9. **Never add Claude/AI attribution** in commits, PRs, branch names or code comments of this repository or of any repository the app manages (no `Co-Authored-By: Claude`, no `@claude`, no "Generated with Claude Code"). This is a hard rule.

---

## 1. Vision

A single, self-hosted web application that becomes the owner's **one place to work** as an open-source developer. It replaces juggling many Claude Code terminals, browser tabs, notes and local servers.

It does four things:

1. **Plans** — captures every task with full context (details, links, files, dependencies, deadlines, priority), and orders them intelligently.
2. **Visualises** — shows the whole plan as a faithful, readable, interactive graph (Pivotick) and as tables/cards, all editable.
3. **Executes with AI** — Claude Code is embedded in the app, has controlled access to the app's data and to the projects' files, can be run on several tasks in parallel, and is observable and controllable live.
4. **Operates** — manages GitHub links (issues, PRs), local running instances and their ports, credentials, accounts, usage, automation modules and alerts.
5. **Organises time** — a calendar and activity timeline show, at a glance, what Claude is doing / did / will do, on which project and task, at what moment, next to the owner's own deadlines and scheduled work (§6.9). This is a core goal, not a secondary view.

**Ultimate workflow the app must make effortless:**

1. The owner opens a chat with Claude inside the app and dumps their priorities in free text: what must be done, by when, on which project, with URLs, files, images, issue links.
2. Claude analyses every element for real (opens URLs, reads files, inspects images, reads GitHub issues/PRs, reads the target repo's docs), then creates well-documented tasks and subtasks, sets dependencies, deadlines, estimates and priorities, and attaches the resources.
3. Claude shows a **proposed plan** (diff of what it will create/change). The owner approves, edits or rejects, in whole or per item.
4. The graph immediately reflects the plan: clear, faithful, readable, efficient.
5. For each task the owner can then: edit manually, add things, ask Claude to break it down, ask Claude to work on it, give corrections or instructions on how it must be done, and let enabled modules automate follow-up steps (e.g. open the PR on validation).

---

## 2. Domain model (minimum; extend where logical)

Design the schema so it is **complete, consistent and easy for Claude to fill in** through a typed API (see §6.3). Every entity has: `id` (UUID), `created_at`, `updated_at`, `created_by` (`user` | `claude:<run-id>` | `module:<id>`), and full change history (§2.10).

### 2.1 Project
- Name, slug, description (Markdown), status (active / paused / archived), colour, icon.
- GitHub repository (`owner/repo`), default branch, local path on disk.
- Stack / languages, links (docs, website, CI, issue tracker…).
- Project-level instructions for Claude (Markdown) — merged into that project's generated `CLAUDE.md` context (§6.5).
- Default modules enabled for the project.
- Local instance definitions (§10).
- Tags.

### 2.2 Task
| Field | Notes |
|---|---|
| Title | short, imperative |
| Description | Markdown, rendered with Vitrine |
| Project | optional (personal tasks allowed) |
| Parent task | for subtasks — unlimited depth, but UI must stay readable |
| Type | feature, bug, refactor, docs, review, research, release, ops, meeting, personal… (configurable list) |
| Status | backlog → todo → in progress → in review → blocked → done / cancelled (configurable workflow; transitions can trigger modules) |
| Priority | explicit level (critical/high/medium/low) **and** a computed score (§3) |
| Importance / urgency | separate inputs feeding the score (Eisenhower-like) |
| Dates | start date, due date (deadline), hard vs soft deadline, scheduled "do on" date, completed date |
| Estimate / actual | estimated effort, time actually spent (manual or tracked) |
| Dependencies | see §2.3 |
| Resources | see §2.4 |
| Acceptance criteria | checklist, Markdown |
| Checklist | lightweight steps that are not full subtasks |
| Instructions for Claude | how this task must be done, constraints, things to avoid |
| Corrections log | owner feedback on Claude's work, kept and fed back into later runs |
| GitHub links | issues, PRs, branches, commits (§9) |
| Branch / worktree | branch name and worktree path when work starts (§6.6) |
| Linked instances | local instances for this task/PR (§10) |
| Assignee | `me`, `claude`, or another person (free text, for open-source collaborators) |
| Tags / labels | free, with colours |
| Recurrence | optional (e.g. weekly release check) |
| Custom fields | user-defined key/value fields with types (text, number, date, URL, select) |
| Agent runs | history of Claude runs on this task (§6) |
| Comments / notes | Markdown thread, from owner or Claude |

### 2.3 Dependencies
- Task → task: `blocks` / `blocked by`, `relates to`, `duplicates`, `follows` (soft order).
- Task → external condition: "waiting for review from X", "waiting for upstream release vX.Y", "waiting for a date", "waiting for a PR to be merged" (auto-resolved by GitHub sync when possible).
- Cycle detection on every change (reject with a clear message).
- Blocked tasks are visibly blocked everywhere (graph, tables, cards) with the reason.
- Critical path computed and highlightable.

### 2.4 Resources (attachable to projects and tasks)
Anything the owner uses often, typed:
- URL (with fetched title / preview; snapshot of content for Claude when allowed)
- File (uploaded, or a reference to a path on disk / in a repo)
- Image (with Claude-generated description for context)
- Code snippet / command (rendered with Vitrine)
- Tool / app shortcut (name, URL or command, icon)
- Note (Markdown)
- GitHub item (issue, PR, discussion, file at commit)
A **resource library** lets the owner reuse the same resource across tasks/projects without duplicating it.

### 2.5 Agent run
One Claude Code session working on something. Fields: task(s), project, account used, model, skills loaded, modules active, prompt/instructions, status (queued / running / waiting for approval / paused / stopped / failed / done), live event stream, files changed, commands run, cost and tokens, start/end, final summary, linked branch/worktree/PR.

### 2.6 Module
An automation rule the owner can turn on globally, per project or per task (§8).

### 2.7 Instance
A local running process tied to a project/task/PR (§10).

### 2.8 Account & credentials
Claude accounts / API keys, GitHub tokens, other service keys (§11).

### 2.9 Alert
Something that went wrong or needs attention (§13).

### 2.10 History / audit
Every create/update/delete on every entity, with actor and diff. Undo for the last changes. Required both for trust in Claude's edits and for security.

---

## 3. Prioritisation & scheduling

- A **computed priority score** combines: explicit priority, importance, urgency, deadline proximity (hard deadlines weigh more), number of tasks it unblocks, estimate, age, project weight. The formula is documented, its weights are configurable, and every score has an "explain why" tooltip.
- **"What should I do now?"** view: ordered list of actionable (not blocked) tasks.
- Optional **auto-scheduling**: given the owner's available time (configurable working hours), propose a day/week plan respecting dependencies and deadlines. The owner accepts or adjusts; Claude can also produce it.
- Deadline risk detection: warn when the remaining estimate of a dependency chain exceeds the time left.

---

## 4. Graph view — full Pivotick implementation

Use **[Pivotick](https://pivotick.github.io/Pivotick/)** (TypeScript graph library built on D3 force simulations). This must be a **complete, deep integration**, not a minimal embed. Read its docs (configuration, callbacks, UI, i18n, API reference) and source first.

Things the docs describe and that you must use properly:
- Layouts: `force`, `tree` (incl. `horizontal` and `radial`), `structured`. Let the owner switch layout and remember the choice per view.
- Styling: `nodeTypeAccessor` + `nodeStyleMap` to style per entity type (project, task, subtask, external dependency, GitHub issue, PR, instance…), `defaultNodeStyle`, `defaultEdgeStyle`, `defaultLabelStyle`, `renderNode`, `renderLabel`; theme through `--pvt-*` CSS variables bound to the app's theme tokens.
- Directed edges (`isDirected`) with distinct edge styles per dependency type.
- UI modes (`full`, `light`, `viewer`, `static`), sidebar, tooltips with custom renderers, context menus on nodes / edges / canvas, selection, filters, legend, data table.
- Callbacks (`onNodeClick`, hover, simulation events…) wired to the app.
- Runtime API (`addNode`, `addEdge`, updates, removal) for live updates without full reload.
- i18n options.

What the graph must let the owner do (**everything doable in forms must be doable from the graph**):
- Create a task (canvas context menu), a subtask (node context menu), a dependency (drag or context menu between two nodes), delete/change a dependency (edge context menu).
- Open a task in a side panel and edit all its fields in place.
- Change status/priority quickly, start/stop a Claude run, open linked PR/issue/instance.
- Filter by project, status, tag, assignee, date range, priority, "blocked", "critical path"; search and focus a node; collapse/expand subtasks and projects.
- Visual encodings: status (colour/shape), priority (size or badge), deadline (badge, overdue state), blocked (marker), running Claude agent (animated indicator), linked running instance.
- Highlight critical path and the full dependency chain of a selected node.
- Live updates when Claude or a module changes data (via the realtime channel, §12).
- Readability at scale: labels hide sensibly on zoom (`minLabelFontSize`), clustering per project, sensible defaults so the graph is legible with 300+ nodes.

Claude must be able to read and change the graph's data through the same API (§6.3) — the graph is just a view of the task data.

If Pivotick lacks something essential, write a small, documented extension around it (do not fork silently) and consider proposing it upstream.

---

## 5. Forms & manual editing

- **Very complete yet fast** task creation: a quick-add (title + project + due date, with natural-language parsing such as "fix login bug for rulezet by friday #bug !high") and a full form with every field from §2.2.
- Full form organised in clear sections/tabs (Essentials, Planning, Dependencies, Resources, GitHub, Claude, Advanced), not one endless page.
- Inline editing in tables and cards; bulk edit (status, tags, project, priority) on multi-selection.
- Pickers with search for tasks (dependencies), resources, GitHub issues/PRs.
- Drag & drop file/image upload; paste an image from clipboard.
- Markdown editor with live preview through Vitrine.
- Validation on client **and** server, with clear messages; unsaved-changes protection.
- Templates for recurring task shapes (e.g. "release", "bug triage", "review PR").
- Keyboard shortcuts and a command palette (Ctrl/Cmd+K) for creation, navigation, search, starting runs.

---

## 6. Claude Code integration (core of the product)

### 6.1 Embedded chat
- A chat panel available everywhere (global context) and inside each project/task (scoped context).
- Streaming responses rendered with Vitrine (Markdown, code, JSON).
- Attach files, images, URLs, tasks and GitHub items to a message.
- Choose per conversation/run: **account**, **model**, **skills** to load, **modules** active.
- Show tool calls and file changes as readable, collapsible steps.

### 6.2 Running Claude Code
- Use the official **Claude Agent SDK** (or the `claude` CLI in headless streaming JSON mode if the SDK is unsuitable — document the choice). Verify current APIs in the official docs; do not rely on memory.
- Each agent run is a **background job** (§12) with a live event stream to the UI.
- **Parallel runs** on several tasks at the same time, with a configurable concurrency limit.
- Controls on every run: **stop**, **pause/resume** where possible, **send a new instruction** mid-run, **re-run** with corrections, approve/deny permission requests from the UI.
- Live progress visible in: the run panel, the task page, the graph node, and a global "Runs" dashboard.

### 6.3 Claude's access to the app (tools)
Expose the app's capabilities to Claude through an **MCP server** provided by the app (preferred), so Claude can:
- Read/search/create/update/delete projects, tasks, subtasks, dependencies, resources, comments, custom fields, schedules.
- Read GitHub data via the app's integration (issues, PRs, comments, files) and create/link items.
- List/start/stop instances, read their logs and ports.
- Read alerts and usage.
- Propose a plan as a **changeset** that the owner approves (default), or apply directly when the owner has allowed it for that scope.

Tools must have strict JSON schemas, clear descriptions and good error messages, so Claude fills data correctly and consistently. Provide a `describe_schema` tool explaining every field and allowed value.

### 6.4 Claude's access to files and repositories
- Access is limited to an explicit allowlist of directories (each project's local path / worktrees, the app's attachment storage). Nothing outside.
- Shell commands run with the permission mode configured per scope; dangerous commands require approval in the UI.

### 6.5 Context discipline
Claude must stay strictly inside the context and requirements the owner sets, and never wander outside the task scope. To achieve that:
- For each managed project, the app generates and maintains a **context file** (`CLAUDE.md` in the project, or an app-managed equivalent if the owner prefers not to commit it — make this a setting) that contains: project conventions learned from the repo (contributing guide, code style, commit/PR conventions, test commands, docs location), the owner's project instructions, and the hard rules below.
- Before working on any task, Claude must read that context file and the project's own docs (README, CONTRIBUTING, docs/), and respect the project's existing patterns as closely as possible.
- Hard rules injected into every run:
  - Never add Claude/AI attribution to commits, PRs, branches, code or comments (no `@claude`, no `Co-Authored-By: Claude`, no "Generated with…").
  - Never push, merge, force-push, delete branches, publish releases or comment publicly unless a module or the owner explicitly allows that action for this scope.
  - Stay within the task's scope; if something outside it seems necessary, stop and ask.
  - Follow the owner's corrections log for the task and project.
- The task's instructions, acceptance criteria, resources and corrections are always passed to the run.

### 6.6 Isolation for parallel work
- Each code-changing run works in its **own git worktree and branch** (naming convention configurable, e.g. `<type>/<task-slug>`), so parallel runs on the same repo never conflict.
- Worktrees are listed, linked to their task, and cleaned up (with confirmation) when the task is done.

### 6.7 Accounts, models, usage
- Several Claude accounts / API keys; **switch account at any time** (globally or per run). Show which account each run uses.
- Model selection per run, with a default per project.
- **Usage dashboard**: tokens, cost, runs, duration — per account, project, task, model, day/week/month; limits and quota alerts (§13).

### 6.8 Skills
- A skills library inside the app: install, list, enable/disable, pick per run. Include the UI/design skill(s) chosen in §14 and allow the owner to say from the interface "use this skill instead".

### 6.9 Activity timeline & calendar (see what Claude does, where, when)
The owner must be able to organise their time around what Claude and they themselves are doing. Build:

- **Calendar view** (day / week / month / agenda) showing on one timeline:
  - Claude runs: past (actual start–end), running (live, growing block), queued and **scheduled** (planned start), each coloured by project, labelled with the task, account and model.
  - The owner's scheduled work ("do on" dates, time blocks), task deadlines (hard vs soft), start dates, milestones and releases.
  - Module executions (PR opened, release made, issue created…) as events.
  - Instance lifetimes (optional layer).
- **Layers & filters**: toggle Claude / me / deadlines / modules / instances; filter by project, account, status, tag. Same server-side filtering rules as everywhere (§14.3).
- **Interactions**: drag a task onto the calendar to schedule it (for me or for Claude); drag a Claude run block to reschedule a queued run; resize a block to change estimate/time box; click any block to open the task, the run's live stream or its result; create a task or schedule a run by selecting a time slot.
- **Scheduled Claude runs**: the owner can plan "Claude works on task X tomorrow at 9:00" or "every night, triage new issues". The scheduler respects the concurrency limit, account quotas and dependencies (a run never starts while its task is blocked), and alerts on conflicts.
- **Per-project swimlane / Gantt-style timeline**: one lane per project (and optionally per Claude run slot), showing tasks over time with dependency arrows and the critical path, consistent with the graph data.
- **Activity feed**: chronological, filterable log of everything that happened (who: me / Claude run / module; what; on which project/task; when), each entry linking to the entity and its diff. Daily and weekly summaries ("what Claude did today on each project"), generated on demand or by a module.
- **"Right now" panel** (dashboard + header): which Claude runs are active, on which project/task, since when, current step, plus the next scheduled items.
- Optional export/sync to an external calendar (iCal feed, read-only) — decide and document.

---

## 7. Planning intake (chat → plan)

When the owner sends priorities in free text, Claude must:
1. Extract each item: what, project, deadline (absolute dates; resolve "next Friday"), importance, constraints.
2. Analyse every attached element: fetch URLs, read files, describe images, read linked GitHub issues/PRs, read the target repo's docs.
3. Detect duplicates with existing tasks and propose merging/updating instead of creating.
4. Produce tasks/subtasks with descriptions, acceptance criteria, estimates, dependencies, resources attached, priority computed.
5. Ask the owner only the questions that block planning, batched together.
6. Present the result as a reviewable changeset (create/update/link), applied on approval, then reflected live in the graph.

---

## 8. Modules (automation)

Modules are configurable automations, enabled globally, per project or per task. Each module defines: trigger (event), conditions, actions, required approvals, and a log of executions. Examples to ship:

- **Validate → PR:** when the owner marks a task as validated, Claude writes a clean PR title and description **in English** following the project's conventions, links the issue, commits with a proper message (project's commit style, no AI attribution), pushes the branch and opens the PR. Shows the result in the task.
- **Issue → task:** new GitHub issues assigned to me / labelled X create tasks automatically.
- **PR merged → close task** and resolve dependent "waiting for merge" conditions.
- **CI failed → alert + optional Claude fix run.**
- **Review requested → review task** with the PR linked.
- **Deadline approaching → reminder.**
- **Run finished → start instance for review** (§10).

### 8.1 Task action modules (toggleable "to do" actions)
Besides event-driven automations, provide **action modules**: reusable, well-defined pieces of work that can be switched on or off on a task (or as defaults on a project), and that appear in the task as steps Claude (or the owner) performs. Examples to ship:

- **Make a PR** — branch, clean commits in the project's style, English title/description following the project's PR template, linked issue, push, open PR, link it to the task.
- **Make a release** — determine next version (semver from commits/changelog conventions), update changelog and version files, tag, draft GitHub release notes in English, publish only after confirmation.
- **Make an issue** — write a well-structured issue in English (context, steps to reproduce / proposal, acceptance criteria) using the repo's issue templates and labels; link it to the task.
- **Review a PR** — read diff and context, run tests locally (optionally in an instance, §10), draft review comments for the owner to approve.
- **Write/update docs**, **add tests**, **update changelog**, **run checks** (lint, tests, build) before handing over.
- **Start a review instance** — launch a local instance of the task's branch and attach its link.

Behaviour:
- On the task form and in the graph context menu, the owner ticks which action modules apply; each becomes a visible step with its own status (pending / running / waiting for approval / done / failed) and output (link to the PR, release, issue…).
- Actions can be chained in a defined order (e.g. *run checks → make PR → start review instance*) and triggered manually, on status change (e.g. "validated"), or on a schedule (§6.9).
- Each action module has editable settings per project (templates, branch naming, labels, release strategy, required confirmations) and uses the project's context file (§6.5).
- Claude can propose action modules when planning a task (e.g. a bug task gets "make PR" by default), but the owner's toggles decide.
- New action modules are added through the same plugin registry as other modules, with a documented interface (inputs, permissions, steps, outputs).

### 8.2 Common requirements
Requirements: modules never exceed their declared permissions; actions with external side effects (push, PR, comment) show a confirmation unless the owner chose "auto" for that module and scope; every execution is logged and reversible where possible. Design the module system so new modules are easy to add (plugin-style registry, documented).

---

## 9. GitHub integration

- Connect via token (fine-grained PAT) or GitHub App; multiple accounts possible.
- Browse/search issues and PRs of the owner's repos; **create tasks from issues/PRs**, link existing tasks to them, keep status in sync (open/closed/merged, review state, CI status, labels, assignees).
- Show linked GitHub data inside tasks (rendered with Vitrine) and as nodes in the graph.
- Claude can use these links as context.
- Sync runs in background jobs with webhooks when available, polling otherwise; respect rate limits.

---

## 10. Local instances & ports

The owner runs local instances of projects, often **one instance per PR or per project**. The app must make this visible and one click away.

- Per project, define how to run an instance: command, working dir (project path or a task's worktree), env vars (secrets via the vault), port or port range, health-check URL, URL pattern.
- **Instance registry**: every running instance with project, task/PR, branch/worktree, port, PID, status (starting / healthy / unhealthy / stopped / crashed), uptime, URL.
- **Automatic port allocation** from a configured range, with conflict detection (also detect ports already used by processes the app did not start).
- One-click **Open** (opens the URL in a new tab), **Start / Stop / Restart**, **Logs** (live, rendered with Vitrine), copy-free direct link.
- Visible from: a global "Instances" page (table/cards), each project, each task, each PR link, the graph (node badge), and a compact always-visible indicator in the header (number of running instances, quick menu with links).
- Instances started by a module or by Claude are tracked the same way.
- Alerts when an instance crashes or a health check fails.
- Optional: Docker/compose support if the owner's projects use it (check during §0.3 analysis).

---

## 11. Security (first priority)

- **Self-hosted, single-owner by default.** Bind to localhost by default; any remote exposure requires explicit config and HTTPS.
- Authentication even locally (strong password + optional TOTP/WebAuthn), secure session cookies, CSRF protection, rate limiting on auth.
- **Secrets vault:** all API keys and tokens (Claude, GitHub, others) encrypted at rest (key from env/OS keyring, never in the DB or repo), never sent to the frontend after saving (masked), never logged, never passed to Claude's context. Runs receive only the credentials their scope needs.
- Strict **Content Security Policy**, no inline scripts, sanitised Markdown/HTML (Vitrine is sanitised by default — keep it that way), output encoding everywhere.
- Server-side authorisation checks on every endpoint and every MCP tool.
- Input validation with schemas on every API boundary; parameterised queries only.
- File access restricted to allowlisted paths; path traversal protection on uploads/downloads.
- Shell execution: no string interpolation of user/LLM input into shell commands; permission prompts for dangerous operations.
- Treat content fetched from URLs, files, issues and PRs as **untrusted data** for Claude (prompt-injection awareness: it can inform, never command).
- Audit log of sensitive actions (credential changes, pushes, module executions, account switches).
- Dependency scanning and pinned versions; document a threat model in `docs/SECURITY.md`.

---

## 12. Background jobs & realtime

- A proper job queue (e.g. Celery/RQ with Redis, or equivalent — decide and document) for: Claude runs, GitHub sync, URL fetching/analysis, instance supervision, module execution, notifications, scheduled tasks.
- Job states, retries with backoff, timeouts, cancellation, visible in a "Jobs" page.
- Realtime channel (WebSocket or SSE) pushing updates to every open view (graph, tables, task pages, runs, instances, alerts).

---

## 13. Alerts & notifications

- Alerts for: failed/stuck runs, permission requests waiting, module failures, CI failures, crashed instances, failed syncs, expiring/invalid tokens, quota or usage thresholds, approaching/overdue deadlines, blocked critical-path tasks.
- In-app notification centre (severity, read/unread, link to the cause, filter), toast for urgent ones, optional desktop/browser notifications.
- Configurable per alert type.

---

## 14. UI / UX

### 14.1 Direction
- **Clean, airy, intentional, with a real identity. It must not look AI-generated.** No generic gradients, no emoji decoration, no cluttered dashboards.
- Research and load design skills/guidelines from the web (e.g. well-known frontend design skills for Claude Code, design-system references), pick one as the base, document why in `docs/DECISIONS.md`, and follow it consistently. The owner can switch skill from the interface.
- Stack: **Bootstrap** (latest stable) + **Font Awesome**, plus whatever else is justified. Templates may be used as a starting point if they fit the identity.
- **Multiple colour themes** (at least light, dark and one or two distinctive ones), built on design tokens (CSS variables) shared by Bootstrap overrides, Pivotick (`--pvt-*`) and Vitrine variables.
- Consistent spacing scale, typography scale, iconography and empty/loading/error states.
- Accessible: keyboard navigation, focus states, contrast AA, ARIA where needed.

### 14.2 Logo & identity
- **Create a logo for the project**: original, simple, legible at favicon size, delivered as SVG (+ PNG sizes, favicon, light/dark variants). Propose 2–3 directions with a short rationale, let the owner choose, then apply it everywhere (header, favicon, README, docs).
- Propose a project name if the owner has not set one (list options; owner decides).

### 14.3 Components & data views
- Work **component-based**, the way Rulezet and Flowintel are organised: reusable UI components (table, card, filter bar, pagination, form fields, modal, side panel, badge, status pill, empty state, Vitrine wrapper, graph wrapper…), each in its own place with its own template/script/style.
- Every list offers **table mode and card mode**, with filters, search, sortable column headers and pagination.
- **Filtering, search and sorting always run server-side on the full dataset**, never only on the 25 rows currently displayed. Pagination, counts and sort order must stay correct across filters. URL reflects state (shareable/bookmarkable, back button works).
- Saved views/filters.

### 14.4 Vitrine for all code, Markdown and JSON
- Use **[Vitrine](https://github.com/ecrou-exact/vitrine)** (framework-free web components to display code, Markdown and JSON; syntax highlighting, line numbers, search, preview/source tabs, collapsible JSON trees; sanitised, CSP-friendly, themable with CSS variables) for **every** display of code, Markdown, JSON, logs and diffs. Never show raw unstyled code.
- **Adapt it to the app**: remove/disable features useless here (e.g. copy and download buttons where not wanted), bind its CSS variables to the app themes. Wrap it in one app component so configuration lives in one place. Read its README and source before integrating.

### 14.5 Main screens (minimum)
Dashboard (today, next actions, "right now" Claude activity, running instances, alerts, usage) · Graph · Tasks (table/cards) · Task detail · Projects · Project detail · Calendar (Claude + me + deadlines + modules, §6.9) · Project timeline / Gantt · Activity feed · Chat · Runs · Instances · GitHub inbox (issues/PRs) · Modules · Resources library · Skills · Usage · Alerts · Jobs · Settings (accounts, credentials, themes, defaults, working hours, security).

---

## 15. Code quality rules

- Readable, consistently named code; logical file and folder names; correct spelling in names, UI text and docs.
- Clear layering (models / services / API / MCP tools / jobs / UI components). Business logic lives in services, reused by API, MCP tools, modules and jobs — **one implementation per behaviour**.
- **No dead code, no duplicates.** Reuse before writing; refactor when two things start to look alike.
- **No scattered CSS or inline styles/scripts.** Styles organised per component plus shared tokens; scripts per component/module.
- Configuration over hard-coding: lists (statuses, types, priorities), weights, ports, paths, limits are configurable.
- Database migrations for every schema change. Respect the schema everywhere (API, forms, MCP tools validate against the same definitions).
- Tests: unit tests for services, API tests, tests for MCP tools, key end-to-end UI flows. Linters/formatters configured and run.
- Commit history of this repo follows the owner's conventions (from §0.3), without AI attribution.

---

## 16. Documentation

- `README.md`: what it is, screenshots, features, quick start, configuration, security notes.
- `docs/`: architecture, data model, API, MCP tools reference, modules (incl. how to write one), instances config, GitHub setup, Claude setup (accounts, models, skills), themes, security/threat model, contributing guide, changelog.
- Keep docs updated in the same change as the code.

---

## 17. Suggested tech stack (confirm after §0.3)

Default proposal, aligned with Rulezet/Flowintel — adjust if the owner's repos show a different preference, and record the decision:
- Backend: Python, Flask, SQLAlchemy, Alembic migrations, PostgreSQL (SQLite allowed for dev).
- Jobs: Celery or RQ + Redis. Realtime: Flask-SocketIO or SSE.
- Claude: Claude Agent SDK (Python) + an app-provided MCP server.
- Frontend: server-rendered templates + component JS (as in Flowintel), Bootstrap, Font Awesome, Pivotick, Vitrine.
- Packaging: Docker Compose + a native install script.

---

## 18. Delivery plan (phases with acceptance criteria)

Track each phase in `docs/PROGRESS.md`. Do not start a phase before the previous one works end to end.

1. **Discovery** — analyse owner's repos, research design skills, read Pivotick/Vitrine docs and source, write conventions, decisions, architecture, threat model; propose names/logo directions. *Done when the owner has approved the architecture and design direction.*
2. **Foundations** — project skeleton, auth, secrets vault, design tokens & themes, component library, Vitrine wrapper, job queue, realtime channel, audit log. 
3. **Core planning** — projects, tasks, subtasks, dependencies, resources, forms, tables/cards with server-side filter/sort/pagination, priority score, history/undo.
4. **Graph** — full Pivotick integration per §4, live updates.
5. **Claude** — MCP server, chat, runs as jobs, live stream, stop/pause/re-instruct, permissions UI, worktrees, context files, accounts/models, usage, skills.
6. **Planning intake** — chat → analysed changeset → approval → graph.
7. **GitHub** — accounts, import/link/sync issues and PRs, GitHub nodes in graph.
8. **Instances & ports** — registry, port allocation, start/stop/logs, header indicator.
9. **Modules** — registry, event automations and task action modules (make PR, release, issue, review…) per §8.
10. **Calendar & activity** — calendar, scheduled Claude runs, project timeline, activity feed, "right now" panel (§6.9); alerts and dashboard polish.
11. **Hardening & release** — security review, tests, docs, logo final, packaging, open-source release checklist.

---

## 19. Questions to ask the owner during Discovery (batch them)

- Project name preference? Logo direction?
- Which repositories to analyse first (list the owner's recent active repos found on GitHub and confirm)?
- Commit the generated `CLAUDE.md` into managed projects, or keep it app-side only?
- Default permission level for Claude runs (ask for everything / auto-approve read & edit / per project)?
- Which modules should be on by default, and which actions may ever run without confirmation?
- Database preference (PostgreSQL vs SQLite) and deployment target (local machine only, home server, Docker)?
- Port range for local instances; do projects use Docker?
- Working hours for auto-scheduling.
