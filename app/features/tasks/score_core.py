"""The computed priority score (PROJECT_BRIEF.md §3), with its explanation.

score = project weight × Σ weight(factor) × value(factor), every value between 0 and 1:

| factor        | value                                                                  |
|---------------|------------------------------------------------------------------------|
| priority      | critical 1 · high 0.7 · medium 0.4 · low 0.1                           |
| importance    | (importance − 1) / 4                                                   |
| urgency       | (urgency − 1) / 4                                                      |
| deadline      | 1 when due or overdue, falling to 0 at `deadline_horizon_days`         |
| hard deadline | the deadline value again, when the deadline is hard                    |
| unblocks      | open tasks waiting on this one (transitively), 5 or more → 1           |
| quick win     | 1 / (1 + estimate in hours / 4); 0.5 without estimate                  |
| age           | days since creation / 30, at most 1                                    |

Weights are the `tasks.score_weights` setting.
"""

from __future__ import annotations

from datetime import date
from typing import Any

PRIORITY_VALUES = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.1}
FACTORS = (
    ("priority", "Priority"),
    ("importance", "Importance"),
    ("urgency", "Urgency"),
    ("deadline", "Deadline"),
    ("hard_deadline_bonus", "Hard deadline"),
    ("unblocks", "Unblocks other tasks"),
    ("quick_win", "Quick win"),
    ("age", "Age"),
)


def _deadline(due_on: date | None, today: date, horizon: int) -> tuple[float, str]:
    if due_on is None:
        return 0.0, "no due date"
    days = (due_on - today).days
    if days <= 0:
        return 1.0, "overdue" if days < 0 else "due today"
    return max(0.0, 1 - days / horizon), f"due in {days} day{'s' if days > 1 else ''}"


def compute(
    *,
    priority: str,
    importance: int,
    urgency: int,
    due_on: date | None,
    hard_deadline: bool,
    estimate_hours: float | None,
    created_on: date,
    unblocks: int,
    project_weight: float,
    weights: dict[str, Any],
    today: date,
) -> tuple[float, list[dict[str, Any]]]:
    deadline, deadline_detail = _deadline(due_on, today, int(weights["deadline_horizon_days"]))
    age_days = max(0, (today - created_on).days)
    values: dict[str, tuple[float, str]] = {
        "priority": (PRIORITY_VALUES.get(priority, 0.4), priority),
        "importance": ((importance - 1) / 4, f"{importance} / 5"),
        "urgency": ((urgency - 1) / 4, f"{urgency} / 5"),
        "deadline": (deadline, deadline_detail),
        "hard_deadline_bonus": (
            deadline if hard_deadline else 0.0,
            "hard" if hard_deadline else "soft or none",
        ),
        "unblocks": (min(1.0, unblocks / 5), f"{unblocks} task{'s' if unblocks != 1 else ''} waiting"),
        "quick_win": (
            0.5 if estimate_hours is None else 1 / (1 + estimate_hours / 4),
            "no estimate" if estimate_hours is None else f"{estimate_hours:g} h",
        ),
        "age": (min(1.0, age_days / 30), f"{age_days} day{'s' if age_days != 1 else ''} old"),
    }
    explain: list[dict[str, Any]] = []
    total = 0.0
    for key, label in FACTORS:
        value, detail = values[key]
        points = float(weights[key]) * value
        total += points
        explain.append({"factor": key, "label": label, "detail": detail, "points": round(points, 1)})
    if project_weight != 1:
        explain.append(
            {
                "factor": "project",
                "label": "Project weight",
                "detail": f"× {project_weight:g}",
                "points": None,
            }
        )
    return round(total * project_weight, 1), explain
