"""The brief of a task: everything a Claude run on it must know, as one Markdown document.

PROJECT_BRIEF.md §6: "the task's instructions, acceptance criteria, resources and
corrections are always passed to the run". The agent runner (Phase 5) sends this text;
the task page shows the same text so the owner sees exactly what Claude will get.

Order: what to do, how it is judged, how to do it (project → parent tasks → task, the most
specific last), corrections, what it depends on, what to use.
"""

from __future__ import annotations

import re

from app.core.db_class.planning import Task
from app.features.comments import comments_core
from app.features.resources import resources_core
from app.features.tasks import dependencies_core, tasks_core, workflow

MAX_INLINE = 4000  # longer notes and snippets are cut, with a pointer to the resource


def fence(text: str, language: str = "") -> str:
    """A fenced block that the text cannot close: longer than any backtick run inside."""
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    marks = "`" * max(3, longest + 1)
    return f"{marks}{language}\n{text.rstrip()}\n{marks}"


def _clip(text: str) -> str:
    return text if len(text) <= MAX_INLINE else text[:MAX_INLINE].rstrip() + "\n… (cut, see the resource)"


def _section(title: str, body: str) -> str:
    return f"## {title}\n\n{body.strip()}\n"


def _resource_lines(resource) -> str:
    head = f"- **{resource.title}** ({resources_core.KIND_LABELS[resource.kind].lower()})"
    if resource.url:
        head += f": <{resource.url}>"
    if resource.path:
        head += f": `{resource.path}`"
    if resource.has_file:
        head += f": uploaded file `{resource.original_name}`"
    parts = [head]
    if resource.description_md.strip():
        parts.append("  " + " ".join(resource.description_md.split())[:300])
    if resource.body.strip() and resource.kind in ("note", "snippet", "tool"):
        if resource.kind == "note":
            block = "\n".join(f"> {line}" if line else ">" for line in _clip(resource.body).splitlines())
        else:
            block = fence(
                _clip(resource.body), resource.language or ("shell" if resource.kind == "tool" else "")
            )
        parts.append("\n" + block + "\n")
    return "\n".join(parts)


def task_brief(task: Task) -> str:
    chain = tasks_core.ancestors(task)
    lines = [f"# Task: {task.title}", ""]
    facts = [
        f"- Type: {task.type} · status: {workflow.label_of(task.status)} · priority: {task.priority}",
    ]
    project = task.project
    if project is not None:
        where = [f"- Project: {project.name}"]
        if project.github_repo:
            where.append(f"repository `{project.github_repo}` (default branch `{project.default_branch}`)")
        if project.local_path:
            where.append(f"local path `{project.local_path}`")
        facts.append(", ".join(where))
    if chain:
        facts.append("- Part of: " + " › ".join(parent.title for parent in chain))
    if task.due_on:
        facts.append(f"- Due: {task.due_on.isoformat()}{' (hard deadline)' if task.hard_deadline else ''}")
    if task.estimate_hours:
        facts.append(f"- Estimate: {task.estimate_hours:g} h")
    if task.tags:
        facts.append("- Tags: " + ", ".join(task.tags))
    lines += [*facts, ""]

    sections = []
    if task.description_md.strip():
        sections.append(_section("What to do", task.description_md))
    if task.acceptance_md.strip():
        sections.append(_section("Acceptance criteria", task.acceptance_md))
    if task.checklist:
        sections.append(
            _section(
                "Checklist",
                "\n".join(f"- [{'x' if item['done'] else ' '}] {item['text']}" for item in task.checklist),
            )
        )

    instructions = []
    if project is not None and project.claude_instructions_md.strip():
        instructions.append(
            f"### From the project {project.name}\n\n{project.claude_instructions_md.strip()}"
        )
    for parent in chain:
        if parent.claude_instructions_md.strip():
            instructions.append(
                f"### From the parent task {parent.title}\n\n{parent.claude_instructions_md.strip()}"
            )
    if task.claude_instructions_md.strip():
        instructions.append(f"### For this task\n\n{task.claude_instructions_md.strip()}")
    if instructions:
        sections.append(_section("How it must be done", "\n\n".join(instructions)))

    corrections = comments_core.corrections_for_task(task, chain)
    if corrections:
        body = "Feedback from the owner on earlier work. Follow it; it overrides habits.\n\n"
        body += "\n".join(
            f"- ({source}, {c.created_at:%Y-%m-%d}) " + " ".join(c.body_md.split())
            for source, c in corrections
        )
        sections.append(_section("Corrections", body))

    deps = dependencies_core.for_task(task.id)
    dep_lines = [
        f"- Blocked by: {other.title} ({workflow.label_of(other.status)})" for _, other in deps["blocked_by"]
    ]
    dep_lines += [
        f"- Comes after: {other.title} ({workflow.label_of(other.status)})" for _, other in deps["follows"]
    ]
    dep_lines += [f"- Unblocks: {other.title}" for _, other in deps["blocks"]]
    dep_lines += [f"- Related: {other.title}" for _, other in deps["relates"]]
    if dep_lines:
        sections.append(_section("Dependencies", "\n".join(dep_lines)))

    subtasks = tasks_core.subtasks(task.id)
    if subtasks:
        sections.append(
            _section(
                "Subtasks",
                "\n".join(f"- [{' ' if sub.is_open else 'x'}] {sub.title}" for sub in subtasks),
            )
        )

    attached = [r for _, r in resources_core.for_target("task", task.id)]
    if project is not None:
        known = {r.id for r in attached}
        attached += [r for _, r in resources_core.for_target("project", project.id) if r.id not in known]
    if attached:
        sections.append(_section("Resources", "\n".join(_resource_lines(r) for r in attached)))

    return "\n".join(lines) + "\n".join(sections)
