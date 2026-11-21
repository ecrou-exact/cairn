"""Recurring tasks: when the next occurrence falls (PROJECT_BRIEF.md §2.2, "weekly release check").

A recurrence is `{"every": n, "unit": day|week|month|year, "anchor": due|done}`:
- `due`: the next one keeps the rhythm of the dates (every Monday stays every Monday), and
  skips the periods already past if the task was done late;
- `done`: the next one comes n units after the day it was done ("water the plants 3 days
  after the last time").

The task's dates (start, do on, due) all move by the same amount, so their spacing stays.
Creating the occurrence is `tasks_core`'s job; this module only computes dates.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any

UNITS = {
    "day": ("day", "days"),
    "week": ("week", "weeks"),
    "month": ("month", "months"),
    "year": ("year", "years"),
}
MAX_STEPS = 1000


def shift(day: date, every: int, unit: str) -> date:
    if unit == "day":
        return day + timedelta(days=every)
    if unit == "week":
        return day + timedelta(weeks=every)
    months = every * (12 if unit == "year" else 1)
    year, month = divmod(day.month - 1 + months, 12)
    year += day.year
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def describe(rule: dict[str, Any] | None) -> str:
    """`Every 2 weeks, from the due date` — for pages and the brief."""
    if not rule:
        return ""
    one, many = UNITS[rule["unit"]]
    every = rule["every"]
    rhythm = f"Every {one}" if every == 1 else f"Every {every} {many}"
    return f"{rhythm}, {'from the due date' if rule.get('anchor', 'due') == 'due' else 'after it is done'}"


def next_dates(
    rule: dict[str, Any], *, start_on: date | None, do_on: date | None, due_on: date | None, today: date
) -> dict[str, date | None]:
    """The dates of the next occurrence. A task without any date gets a due date."""
    every, unit = rule["every"], rule["unit"]
    anchor_day = due_on or do_on or start_on
    if rule.get("anchor", "due") == "done" or anchor_day is None:
        new_anchor = shift(today, every, unit)
    else:
        new_anchor, steps = shift(anchor_day, every, unit), 1
        while new_anchor <= today and steps < MAX_STEPS:  # done late: skip the periods already past
            steps += 1
            new_anchor = shift(anchor_day, every * steps, unit)
    if anchor_day is None:
        return {"start_on": None, "do_on": None, "due_on": new_anchor}
    delta = new_anchor - anchor_day  # every date moves together, so their spacing stays
    return {
        "start_on": start_on + delta if start_on else None,
        "do_on": do_on + delta if do_on else None,
        "due_on": due_on + delta if due_on else None,
    }
