"""A project from one machine to another (D-084): one file with the project, its tasks and subtasks,
their dependencies, conditions, timers, comments, resources (with their files), linked work and
instances. Read back on the other machine: what is new is added, what changed is taken when it is newer
there, what is newer here stays. Shown first, written only when the owner confirms.

Never in the file: secrets, tokens, the vault, `.env`, the history of changes, Claude's sessions.
Folders are this machine's: a project already here keeps its own, a new one gets the one the owner gives.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Date, Uuid, or_, select

from app.core.db_class.base import UTCDateTime, utcnow
from app.core.db_class.claude import ProjectInstance
from app.core.db_class.comment import Comment
from app.core.db_class.planning import Dependency, ExternalCondition, Project, Task, TimeEntry
from app.core.db_class.resource import Resource, ResourceLink
from app.core.db_class.worklink import WorkLink
from app.core.extensions import db
from app.core.utils.events import publish
from app.core.utils.history import batch
from app.core.utils.logger import log_action
from app.core.utils.settings import get_setting
from app.features.projects import projects_core
from app.features.resources import storage_core
from app.features.tasks import dependencies_core

FORMAT = 1
# In the order they are written: what a row points to comes before it.
MODELS: dict[str, type] = {
    "project": Project,
    "project_instance": ProjectInstance,
    "task": Task,
    "dependency": Dependency,
    "external_condition": ExternalCondition,
    "time_entry": TimeEntry,
    "resource": Resource,
    "resource_link": ResourceLink,
    "comment": Comment,
    "work_link": WorkLink,
}
DERIVED = {"is_open", "blocked_by_count", "unblocks_count", "score", "score_explain"}
KEPT_HERE = {"project": {"local_path", "slug"}}  # this machine's own


class TransferError(ValueError):
    pass


def _value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def _row(item: Any) -> dict[str, Any]:
    return {col.name: _value(getattr(item, col.key)) for col in item.__table__.columns}


def _parse(model: type, row: dict[str, Any]) -> dict[str, Any]:
    """A row of the file as the model's values, only its known columns."""
    found = {}
    for col in model.__table__.columns:
        if col.name not in row:
            continue
        value = row[col.name]
        try:
            if value is not None and isinstance(col.type, Uuid):
                value = uuid.UUID(value)
            elif value is not None and isinstance(col.type, UTCDateTime):
                value = datetime.fromisoformat(value)
            elif value is not None and isinstance(col.type, Date):
                value = date.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise TransferError(f"This file is damaged ({col.name}).") from exc
        found[col.key] = value
    if "id" not in found:
        raise TransferError("This file is damaged (a row without id).")
    return found


def _rows(project: Project) -> dict[str, list[Any]]:
    tasks = list(db.session.scalars(select(Task).where(Task.project_id == project.id)))
    ids = {task.id for task in tasks}
    targets = [("project", project.id), *(("task", t) for t in ids)]

    def on(model):
        return or_(*((model.target_type == kind) & (model.target_id == ref) for kind, ref in targets))

    links = list(db.session.scalars(select(ResourceLink).where(on(ResourceLink))))
    resource_ids = {link.resource_id for link in links}
    return {
        "project": [project],
        "project_instance": list(
            db.session.scalars(select(ProjectInstance).where(ProjectInstance.project_id == project.id))
        ),
        "task": sorted(tasks, key=lambda t: (t.parent_id is not None, t.created_at)),
        "dependency": list(
            db.session.scalars(
                select(Dependency).where(Dependency.from_task_id.in_(ids), Dependency.to_task_id.in_(ids))
            )
        ),
        "external_condition": list(
            db.session.scalars(select(ExternalCondition).where(ExternalCondition.task_id.in_(ids)))
        ),
        "time_entry": list(db.session.scalars(select(TimeEntry).where(TimeEntry.task_id.in_(ids)))),
        "resource": list(db.session.scalars(select(Resource).where(Resource.id.in_(resource_ids)))),
        "resource_link": links,
        "comment": list(db.session.scalars(select(Comment).where(on(Comment)))),
        "work_link": list(db.session.scalars(select(WorkLink).where(on(WorkLink)))),
    }


def export(project: Project) -> bytes:
    """The project as a file (gzip JSON), its files inside."""
    rows = _rows(project)
    files: dict[str, str] = {}
    for name in [r.stored_name for r in rows["resource"] if r.stored_name] + [project.image_name]:
        if not name:
            continue
        try:
            files[name] = base64.b64encode(storage_core.path_of(name).read_bytes()).decode()
        except (OSError, storage_core.StorageError):
            continue  # gone from this machine: the rest still goes
    data = {
        "cairn_export": FORMAT,
        "exported_at": utcnow().isoformat(),
        "project": str(project.id),
        "name": project.name,
        "tables": {name: [_row(item) for item in items] for name, items in rows.items()},
        "files": files,
    }
    with batch():
        log_action("project.export", target_type="project", target_id=project.id)
    return gzip.compress(json.dumps(data, ensure_ascii=False).encode(), mtime=0)


SUFFIX = ".cairn"
SHOWN = 20


def exchange_folder() -> Path | None:
    """The folder of the setting, when it is one."""
    raw = get_setting("projects.transfer_folder").strip()
    folder = Path(raw).expanduser() if raw else None
    return folder if folder is not None and folder.is_absolute() and folder.is_dir() else None


def file_name(project: Project) -> str:
    return f"cairn-{project.slug}-{date.today().isoformat()}{SUFFIX}"


def save(project: Project) -> Path:
    """Export into the exchange folder; the same day's file is replaced."""
    folder = exchange_folder()
    if folder is None:
        raise TransferError("Set an exchange folder in Settings → Projects first.")
    target = folder / file_name(project)
    draft = target.with_suffix(".part")
    draft.write_bytes(export(project))
    draft.replace(target)
    return target


def waiting_files() -> list[dict[str, Any]]:
    """The project files of the exchange folder, the newest first."""
    folder = exchange_folder()
    if folder is None:
        return []
    found = []
    for path in folder.glob(f"*{SUFFIX}"):
        try:
            if path.is_file() and not path.is_symlink():
                found.append({"name": path.name, "at": datetime.fromtimestamp(path.stat().st_mtime)})
        except OSError:
            continue
    return sorted(found, key=lambda f: f["at"], reverse=True)[:SHOWN]


def from_folder(name: str) -> bytes:
    folder = exchange_folder()
    path = folder / name if folder else None
    if path is None or path.name != name or not name.endswith(SUFFIX) or not path.is_file():
        raise TransferError("This file is not in the exchange folder.")
    return path.read_bytes()


def read(blob: bytes) -> dict[str, Any]:
    try:
        data = json.loads(gzip.decompress(blob) if blob[:2] == b"\x1f\x8b" else blob)
    except (OSError, ValueError, EOFError) as exc:
        raise TransferError("This is not a file exported by Cairn.") from exc
    if not isinstance(data, dict) or data.get("cairn_export") != FORMAT:
        raise TransferError("This is not a file exported by this version of Cairn.")
    tables = data.get("tables")
    if not isinstance(tables, dict) or len(tables.get("project") or []) != 1:
        raise TransferError("This file holds no project.")
    if set(tables) - set(MODELS) or not all(isinstance(rows, list) for rows in tables.values()):
        raise TransferError("This file is damaged.")
    return data


def _newer(theirs: dict[str, Any], mine: Any) -> bool:
    there, here = theirs.get("updated_at"), getattr(mine, "updated_at", None)
    return there is not None and (here is None or there > here)


def _merge(data: dict[str, Any], folder: str | None) -> dict[str, Any]:
    """Write the file's rows into the session; what was done, by table."""
    counts: dict[str, dict[str, int]] = {}
    changed: list[str] = []
    project_row = data["tables"]["project"][0]
    project_id = _parse(Project, project_row)["id"]
    here = db.session.get(Project, project_id)
    for table, model in MODELS.items():
        rows = data["tables"].get(table, [])
        done = counts.setdefault(table, {"new": 0, "updated": 0, "kept": 0})
        for raw in rows:
            values = _parse(model, raw)
            mine = db.session.get(model, values["id"])
            if model is Project:
                if values["id"] != project_id:
                    raise TransferError("This file is damaged (two projects).")
                values["local_path"] = here.local_path if here else (folder or None)
                values["slug"] = here.slug if here else projects_core._free_slug(values["slug"])
                if not here and values.get("image_name") not in data["files"]:
                    values["image_name"] = None
            if model is Task and values.get("project_id") != project_id:
                raise TransferError("This file is damaged (a task of another project).")
            for name in DERIVED:
                values.pop(name, None)
            if mine is None:
                db.session.add(model(**values))
                done["new"] += 1
                if model is Task:
                    changed.append(f"new: {values['title']}")
            elif _newer(values, mine):
                for name, value in values.items():
                    if name not in KEPT_HERE.get(table, ()):
                        setattr(mine, name, value)
                done["updated"] += 1
                if model is Task:
                    changed.append(f"updated: {values['title']}")
            else:
                done["kept"] += 1
        db.session.flush()
    return {"counts": counts, "changed": changed, "exists": here is not None}


def preview(blob: bytes, folder: str | None = None) -> dict[str, Any]:
    """What an import would do, without writing anything."""
    data = read(blob)
    try:
        with db.session.begin_nested():
            found = _merge(data, folder)
            raise _TriedOut(found)
    except _TriedOut as tried:
        found = tried.found
    finally:
        db.session.expire_all()
    return {"name": data["name"], "exported_at": data["exported_at"], **found}


class _TriedOut(Exception):
    def __init__(self, found: dict[str, Any]) -> None:
        super().__init__("tried out")
        self.found = found


def bring(blob: bytes, folder: str | None = None) -> tuple[Project, dict[str, Any]]:
    """Import, all or nothing."""
    data = read(blob)
    with batch():
        found = _merge(data, folder)
        for name, content in data["files"].items():
            try:
                body = base64.b64decode(content, validate=True)
                target = storage_core.path_of(name)
            except (ValueError, storage_core.StorageError) as exc:
                raise TransferError("This file is damaged (an attached file).") from exc
            if target.exists():
                continue
            known = _sha(name, data)
            if known is not None and hashlib.sha256(body).hexdigest() != known:
                raise TransferError("This file is damaged (an attached file differs).")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        project = db.session.get(Project, uuid.UUID(data["project"]))
        dependencies_core.refresh_derived()
        log_action(
            "project.import",
            target_type="project",
            target_id=project.id,
            meta={table: c for table, c in found["counts"].items() if c["new"] or c["updated"]},
        )
        publish("project.changed", {"id": str(project.id), "name": project.name})
    return project, found


def _sha(name: str, data: dict[str, Any]) -> str | None:
    for row in data["tables"].get("resource", []):
        if row.get("stored_name") == name:
            return row.get("sha256")
    return None
