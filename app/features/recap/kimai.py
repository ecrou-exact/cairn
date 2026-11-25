"""Kimai (the owner's time tracking), through its REST API (D-078).

The address and the token come from `.env` only (`CAIRN_KIMAI_URL`, `CAIRN_KIMAI_TOKEN`): never in
the database, a page, a log or a program Cairn starts. Cairn reads what it needs and can create a
time entry; it has no call that changes or deletes anything in Kimai.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from typing import Any

TIMEOUT = 20
CATALOG_SECONDS = 600
SIZE = 100  # entries asked at once
_catalog: dict[str, Any] = {}


class KimaiError(ValueError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect would carry the token to another address."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def address() -> str:
    return os.environ.get("CAIRN_KIMAI_URL", "").strip().rstrip("/")


def _token() -> str:
    return os.environ.get("CAIRN_KIMAI_TOKEN", "").strip()


def configured() -> bool:
    return bool(_token()) and urllib.parse.urlsplit(address()).scheme == "https"


def _call(path: str, data: dict[str, Any] | None = None) -> Any:
    if not configured():
        raise KimaiError("Set CAIRN_KIMAI_URL (https) and CAIRN_KIMAI_TOKEN in .env, then restart Cairn.")
    request = urllib.request.Request(  # noqa: S310 (https only, see `configured`)
        f"{address()}/api/{path}",
        data=None if data is None else json.dumps(data).encode(),
        headers={
            "Authorization": f"Bearer {_token()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "cairn",
        },
        method="GET" if data is None else "POST",
    )
    try:
        with urllib.request.build_opener(_NoRedirect).open(request, timeout=TIMEOUT) as answer:
            return json.load(answer)
    except urllib.error.HTTPError as exc:
        raise KimaiError(_refusal(exc)) from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise KimaiError("Kimai did not answer as expected. Check it before you send again.") from None


def _refusal(exc: urllib.error.HTTPError) -> str:
    if exc.code in (401, 403):
        return "Kimai refused the token in .env, or what it asked for."
    told: list[str] = []
    try:
        answer = json.load(exc)
        fields = (answer.get("errors") or {}).get("children") or {}
        for name, field in fields.items():
            if isinstance(field, dict):
                told += [f"{name}: {error}" for error in field.get("errors") or []]
        told += (answer.get("errors") or {}).get("errors") or []
    except (ValueError, AttributeError, OSError):
        told = []
    return f"Kimai refused ({exc.code})" + (": " + "; ".join(map(str, told))[:400] if told else ".")


def catalog() -> list[dict[str, Any]]:
    """The projects time can be logged on, each with its activities (its own, then the shared ones)."""
    if _catalog and time.monotonic() - _catalog["at"] < CATALOG_SECONDS:
        return _catalog["projects"]
    activities = _call("activities")
    shared = [a for a in activities if not a.get("project")]
    found = []
    for project in _call("projects"):
        own = [a for a in activities if a.get("project") == project["id"]]
        found.append(
            {
                "id": project["id"],
                "name": project["name"],
                "customer": project.get("parentTitle") or "",
                "activities": [
                    {"id": a["id"], "name": a["name"]}
                    for a in [*own, *(shared if project.get("globalActivities", True) else [])]
                ],
            }
        )
    _catalog.update(at=time.monotonic(), projects=found)
    return found


def labels(project_id: int, activity_id: int) -> tuple[str, str]:
    """The names of a project and one of its activities; refused when Kimai has no such pair."""
    for project in catalog():
        if project["id"] == project_id:
            for activity in project["activities"]:
                if activity["id"] == activity_id:
                    return project["name"], activity["name"]
    raise KimaiError("Kimai has no such activity for this project.")


def entries(day: date, last: date | None = None) -> list[dict[str, Any]]:
    """What Kimai already holds for the owner that day, or from that day to `last` (a week at most)."""
    last = last or day
    query = urllib.parse.urlencode(
        {
            "begin": f"{day}T00:00:00",
            "end": f"{last}T23:59:59",
            "full": "true",
            "size": str(SIZE),
            "order": "ASC",
        }
    )
    found = []
    rows = _call(f"timesheets?{query}")
    if len(rows) >= SIZE:
        raise KimaiError("Kimai holds too many entries here to check them all.")
    for row in rows:
        begin = datetime.fromisoformat(row["begin"]).replace(tzinfo=None)
        end = datetime.fromisoformat(row["end"]).replace(tzinfo=None) if row.get("end") else None
        found.append(
            {
                "id": row["id"],
                "begin": begin,
                "end": end,
                "minutes": round((end - begin).total_seconds() / 60) if end else 0,
                "project": row["project"]["id"],
                "project_name": row["project"]["name"],
                "activity": row["activity"]["id"],
                "activity_name": row["activity"]["name"],
                "description": row.get("description") or "",
                "tags": row.get("tags") or [],
            }
        )
    return found


def create(
    begin: datetime, minutes: int, project: int, activity: int, description: str, tags: list[str]
) -> int:
    data: dict[str, Any] = {
        "begin": begin.isoformat(timespec="seconds"),
        "end": (begin + timedelta(minutes=minutes)).isoformat(timespec="seconds"),
        "project": project,
        "activity": activity,
        "description": description,
    }
    if tags:
        data["tags"] = ",".join(tags)
    answer = _call("timesheets", data)
    try:
        return int(answer["id"])
    except (KeyError, TypeError, ValueError):
        raise KimaiError("Kimai answered without an entry. Check it before you send again.") from None
