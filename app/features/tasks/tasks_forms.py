"""The task form: HTML fields to schema input and back (checklist as `[x] text` lines)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.core.db_class.planning import Task
from app.core.utils.web import optional, split_list
from app.features.tasks import workflow

_CHECK = re.compile(r"^\s*(?:[-*]\s*)?\[( |x|X)\]\s*(.+)$")


def checklist_from_text(raw: str | None) -> list[dict[str, Any]]:
    items = []
    for line in (raw or "").splitlines():
        if not line.strip():
            continue
        match = _CHECK.match(line)
        if match:
            items.append({"text": match[2].strip(), "done": match[1].lower() == "x"})
        else:
            items.append({"text": line.strip().lstrip("-* ").strip(), "done": False})
    return items


def checklist_to_text(items: list[dict[str, Any]]) -> str:
    return "\n".join(f"[{'x' if item.get('done') else ' '}] {item['text']}" for item in items)


def values_from_form(form: Mapping[str, str]) -> dict[str, Any]:
    """Every field of the full task form, as the schema expects it."""
    return {
        "title": form.get("title", ""),
        "description_md": form.get("description_md", ""),
        "project_id": optional(form, "project_id"),
        "parent_id": optional(form, "parent_id"),
        "type": form.get("type", ""),
        "status": optional(form, "status"),
        "priority": form.get("priority", ""),
        "importance": form.get("importance") or 3,
        "urgency": form.get("urgency") or 3,
        "start_on": optional(form, "start_on"),
        "due_on": optional(form, "due_on"),
        "hard_deadline": form.get("hard_deadline") == "on",
        "do_on": optional(form, "do_on"),
        "estimate_hours": optional(form, "estimate_hours"),
        "assignee": optional(form, "assignee") or "me",
        "tags": split_list(form.get("tags")),
        "checklist": checklist_from_text(form.get("checklist")),
        "acceptance_md": form.get("acceptance_md", ""),
        "claude_instructions_md": form.get("claude_instructions_md", ""),
        "recurrence": recurrence_from_form(form),
        "custom": {key: form.get(f"custom__{key}", "") for key in workflow.custom_fields()},
    }


def recurrence_from_form(form: Mapping[str, str]) -> dict[str, Any] | None:
    unit = form.get("repeat_unit") or ""
    if not unit:
        return None
    return {
        "every": form.get("repeat_every") or 1,
        "unit": unit,
        "anchor": form.get("repeat_anchor") or "due",
    }


def values_from_task(task: Task) -> dict[str, Any]:
    """What the edit form shows for an existing task (strings as the inputs hold them)."""
    return {
        "title": task.title,
        "description_md": task.description_md,
        "project_id": str(task.project_id) if task.project_id else "",
        "parent_id": str(task.parent_id) if task.parent_id else "",
        "type": task.type,
        "status": task.status,
        "priority": task.priority,
        "importance": task.importance,
        "urgency": task.urgency,
        "start_on": task.start_on.isoformat() if task.start_on else "",
        "due_on": task.due_on.isoformat() if task.due_on else "",
        "hard_deadline": task.hard_deadline,
        "do_on": task.do_on.isoformat() if task.do_on else "",
        "estimate_hours": f"{task.estimate_hours:g}" if task.estimate_hours else "",
        "assignee": task.assignee,
        "tags": ", ".join(task.tags),
        "checklist": checklist_to_text(task.checklist),
        "acceptance_md": task.acceptance_md,
        "claude_instructions_md": task.claude_instructions_md,
        "repeat_unit": (task.recurrence or {}).get("unit", ""),
        "repeat_every": (task.recurrence or {}).get("every", 1),
        "repeat_anchor": (task.recurrence or {}).get("anchor", "due"),
        **{f"custom__{key}": _shown(value) for key, value in task.custom.items()},
    }


def _shown(value: Any) -> str:
    return f"{value:g}" if isinstance(value, float) else str(value)
