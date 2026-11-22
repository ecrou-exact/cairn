"""Resources and the resource library (PROJECT_BRIEF.md §2.4).

- One resource, many places: `attach` links a library resource to a project or a task.
- Uploading a file that is already in the library (same SHA-256) attaches the existing
  resource instead of storing a second copy.
- Web addresses get a preview (title, description) from the `resources.preview` job;
  GitHub addresses are understood at once (repository, issue / PR number, file).
- Soft delete; the file on disk goes only when the resource is deleted for good.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import IO, Any

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select

from app.core.db_class.base import utcnow
from app.core.db_class.planning import Project, Task
from app.core.db_class.resource import RESOURCE_KINDS, Resource, ResourceLink
from app.core.extensions import db
from app.core.jobs import jobs_core
from app.core.schema.resources import MISSING, LinkCreate, ResourceCreate, ResourceUpdate, required_fields
from app.core.utils.actor import current_actor
from app.core.utils.events import publish
from app.core.utils.history import batch, register_undo
from app.core.utils.listing import FilterSpec, ListPage, ListSpec, run_list
from app.core.utils.logger import log_action
from app.core.utils.settings import get_setting
from app.features.resources import preview_core, storage_core

KIND_LABELS = {
    "url": "Link",
    "file": "File",
    "image": "Image",
    "snippet": "Snippet",
    "tool": "Tool",
    "note": "Note",
    "github": "GitHub",
}
KIND_ICONS = {
    "url": "fa-link",
    "file": "fa-file",
    "image": "fa-image",
    "snippet": "fa-code",
    "tool": "fa-screwdriver-wrench",
    "note": "fa-note-sticky",
    "github": "fa-code-pull-request",
}
KIND_HINTS = {
    "url": "A web page, with its title and preview",
    "file": "A path to a file or folder on this machine",
    "snippet": "Code or a command to copy again",
    "tool": "An app or service you use, with its link",
    "note": "A few lines of Markdown",
    "github": "An issue, pull request or repository",
}
TARGETS = {"project": Project, "task": Task}
FIELDS = ("title", "description_md", "url", "body", "language", "path", "icon", "tags")


class ResourceError(ValueError):
    pass


class ResourceNotFound(ResourceError):
    pass


def get_resource(resource_id: uuid.UUID, *, deleted: bool = False) -> Resource:
    resource = db.session.get(Resource, resource_id)
    if resource is None or resource.is_deleted != deleted:
        raise ResourceNotFound(
            "This resource does not exist." if not deleted else "This resource is not in the trash."
        )
    return resource


def icon_of(resource: Resource) -> str:
    return resource.icon or KIND_ICONS[resource.kind]


def _changed(resource: Resource, *targets: tuple[str, uuid.UUID]) -> None:
    publish(
        "resource.changed",
        {"id": str(resource.id), "targets": [f"{kind}:{target}" for kind, target in targets]},
    )


def _targets_of(resource_id: uuid.UUID) -> list[tuple[str, uuid.UUID]]:
    return list(
        db.session.execute(
            select(ResourceLink.target_type, ResourceLink.target_id).where(
                ResourceLink.resource_id == resource_id
            )
        ).tuples()
    )


def _live_target(target_type: str, target_id: uuid.UUID) -> Project | Task:
    model = TARGETS.get(target_type)
    target = db.session.get(model, target_id) if model else None
    if target is None or target.is_deleted:
        raise ResourceError(f"This {target_type} does not exist.")
    return target


def _url_facts(resource: Resource) -> None:
    """GitHub reference now, web preview later (job), after the address is set or changed."""
    meta = {key: value for key, value in resource.meta.items() if key not in ("github", "preview")}
    if resource.url:
        ref = preview_core.github_ref(resource.url)
        if ref:
            meta["github"] = ref
    resource.meta = meta
    if resource.url and resource.kind in ("url", "github", "tool") and get_setting("resources.previews"):
        db.session.flush()
        jobs_core.enqueue(
            "resources.preview",
            {"resource_id": str(resource.id)},
            title=f"Preview of {resource.url[:120]}",
        )


def _default_title(data: ResourceCreate) -> str:
    if data.title:
        return data.title
    ref = preview_core.github_ref(data.url or "")
    return preview_core.github_title(ref) if ref else preview_core.default_title(data.url or "")


def create(data: ResourceCreate, attach_to: LinkCreate | None = None) -> Resource:
    values = data.model_dump(mode="json")
    values["title"] = _default_title(data)
    with batch():
        if attach_to is not None:
            _live_target(attach_to.target_type, attach_to.target_id)
        resource = Resource(**values, meta={}, created_by=current_actor())
        db.session.add(resource)
        db.session.flush()
        log_action(
            "resource.create",
            target_type="resource",
            target_id=resource.id,
            diff={k: [None, v] for k, v in values.items() if v not in (None, "", [])},
        )
        _url_facts(resource)
        _changed(resource)
        if attach_to is not None:
            attach(resource.id, attach_to)
    return resource


def upload(
    stream: IO[bytes], filename: str | None, attach_to: LinkCreate | None = None
) -> tuple[Resource, bool]:
    """Store an uploaded file as a `file` or `image` resource; (resource, True if new).

    The same content already in the library is reused (and attached), not stored twice.
    """
    if attach_to is not None:
        _live_target(attach_to.target_type, attach_to.target_id)
    max_bytes = int(get_setting("resources.max_upload_mb")) * 1024 * 1024
    stored = storage_core.store(stream, filename, max_bytes)
    existing = db.session.scalar(
        select(Resource)
        .where(
            Resource.sha256 == stored.sha256, Resource.deleted_at.is_(None), Resource.stored_name.is_not(None)
        )
        .limit(1)
    )
    try:
        with batch():
            if existing is not None:
                if attach_to is not None and not _link_between(existing.id, attach_to):
                    attach(existing.id, attach_to)
                resource, new = existing, False
            else:
                resource = Resource(
                    kind="image" if stored.image else "file",
                    title=stored.original_name[:200],
                    stored_name=stored.stored_name,
                    original_name=stored.original_name,
                    mime=stored.mime,
                    size_bytes=stored.size_bytes,
                    sha256=stored.sha256,
                    meta={"image": stored.image} if stored.image else {},
                    created_by=current_actor(),
                )
                db.session.add(resource)
                db.session.flush()
                log_action(
                    "resource.create",
                    target_type="resource",
                    target_id=resource.id,
                    diff={
                        "kind": [None, resource.kind],
                        "title": [None, resource.title],
                        "size_bytes": [None, resource.size_bytes],
                    },
                )
                _changed(resource)
                if attach_to is not None:
                    attach(resource.id, attach_to)
                new = True
    except BaseException:
        storage_core.remove(stored.stored_name)
        raise
    if not new:
        storage_core.remove(stored.stored_name)
    return resource, new


def update(resource_id: uuid.UUID, data: ResourceUpdate) -> Resource:
    resource = get_resource(resource_id)
    fields = data.model_dump(mode="json", exclude_unset=True)
    if "title" in fields and not fields["title"]:
        raise ResourceError("A resource needs a title.")
    merged = {key: fields.get(key, getattr(resource, key)) for key in ("url", "body", "path")}
    try:
        missing = required_fields(
            resource.kind, url=merged["url"], body=merged["body"] or "", path=merged["path"]
        )
    except ValueError as exc:
        raise ResourceError(str(exc)) from exc
    if missing and not (resource.kind == "file" and resource.has_file):
        raise ResourceError(MISSING[missing])
    diff = {
        key: [getattr(resource, key), value]
        for key, value in fields.items()
        if getattr(resource, key) != value
    }
    if not diff:
        return resource
    with batch():
        for key in diff:
            setattr(resource, key, fields[key])
        log_action("resource.update", target_type="resource", target_id=resource.id, diff=diff)
        if "url" in diff:
            _url_facts(resource)
        _changed(resource, *_targets_of(resource.id))
    return resource


def apply_preview(resource_id: uuid.UUID, found: dict[str, str] | None, error: str | None = None) -> None:
    """Called by the preview job: facts found on the page, or why it failed. Not an owner
    change, so not in the undo history; still logged."""
    resource = db.session.get(Resource, resource_id)
    if resource is None:
        return
    preview = dict(found or {})
    preview["fetched_at"] = utcnow().isoformat()
    if error:
        preview["error"] = error
    resource.meta = {**resource.meta, "preview": preview}
    log_action(
        "resource.preview",
        target_type="resource",
        target_id=resource.id,
        meta={"ok": not error, "title": preview.get("title", "")},
        level="warning" if error else "info",
    )
    _changed(resource, *_targets_of(resource.id))


def refresh_preview(resource_id: uuid.UUID) -> None:
    resource = get_resource(resource_id)
    if not resource.url:
        raise ResourceError("This resource has no web address.")
    if not get_setting("resources.previews"):
        raise ResourceError("Link previews are turned off in the settings.")
    with batch():
        _url_facts(resource)


def use_preview_title(resource_id: uuid.UUID) -> Resource:
    resource = get_resource(resource_id)
    title = resource.meta.get("preview", {}).get("title")
    if not title:
        raise ResourceError("No page title was found for this address.")
    return update(resource.id, ResourceUpdate(title=title))


def delete(resource_id: uuid.UUID) -> None:
    resource = get_resource(resource_id)
    with batch():
        resource.deleted_at = utcnow()
        log_action(
            "resource.delete",
            target_type="resource",
            target_id=resource.id,
            diff={"deleted_at": [None, resource.deleted_at.isoformat()]},
        )
        _changed(resource, *_targets_of(resource.id))


def restore(resource_id: uuid.UUID) -> None:
    resource = get_resource(resource_id, deleted=True)
    with batch():
        log_action(
            "resource.restore",
            target_type="resource",
            target_id=resource.id,
            diff={"deleted_at": [resource.deleted_at.isoformat(), None]},
        )
        resource.deleted_at = None
        _changed(resource, *_targets_of(resource.id))


def purge(resource_id: uuid.UUID) -> None:
    """Delete for good, from the trash only: the resource, its links and its file."""
    resource = get_resource(resource_id, deleted=True)
    stored = resource.stored_name
    db.session.execute(sql_delete(ResourceLink).where(ResourceLink.resource_id == resource.id))
    log_action(
        "resource.purge",
        target_type="resource",
        target_id=resource.id,
        meta={"title": resource.title, "kind": resource.kind},
        level="warning",
    )
    db.session.delete(resource)
    db.session.commit()
    if stored:
        storage_core.remove(stored)


# -- links -----------------------------------------------------------------------------------


def _link_between(resource_id: uuid.UUID, data: LinkCreate) -> ResourceLink | None:
    return db.session.scalar(
        select(ResourceLink).where(
            ResourceLink.resource_id == resource_id,
            ResourceLink.target_type == data.target_type,
            ResourceLink.target_id == data.target_id,
        )
    )


def _link_snapshot(link: ResourceLink) -> dict[str, Any]:
    return {
        "resource_id": str(link.resource_id),
        "target_type": link.target_type,
        "target_id": str(link.target_id),
        "note": link.note,
    }


def attach(resource_id: uuid.UUID, data: LinkCreate) -> ResourceLink:
    resource = get_resource(resource_id)
    target = _live_target(data.target_type, data.target_id)
    if _link_between(resource.id, data) is not None:
        name = getattr(target, "title", None) or getattr(target, "name", "")
        raise ResourceError(f"“{resource.title}” is already attached to “{name}”.")
    with batch():
        link = ResourceLink(**data.model_dump(), resource_id=resource.id, created_by=current_actor())
        db.session.add(link)
        db.session.flush()
        log_action(
            "resource.attach", target_type="resource_link", target_id=link.id, meta=_link_snapshot(link)
        )
        _changed(resource, (data.target_type, data.target_id))
    return link


def detach(link_id: uuid.UUID) -> ResourceLink:
    link = db.session.get(ResourceLink, link_id)
    if link is None:
        raise ResourceNotFound("This resource is not attached there.")
    with batch():
        log_action(
            "resource.detach", target_type="resource_link", target_id=link.id, meta=_link_snapshot(link)
        )
        resource = db.session.get(Resource, link.resource_id)
        _changed(resource, (link.target_type, link.target_id))
        db.session.delete(link)
        db.session.flush()
    return link


def forget_targets(target_type: str, target_ids: list[uuid.UUID]) -> None:
    """Links to projects or tasks deleted for good go with them (the resources stay)."""
    if target_ids:
        db.session.execute(
            sql_delete(ResourceLink).where(
                ResourceLink.target_type == target_type, ResourceLink.target_id.in_(target_ids)
            )
        )


# -- undo ------------------------------------------------------------------------------------


def _undo_create(row) -> None:
    resource = db.session.get(Resource, uuid.UUID(row.target_id))
    if resource is not None and not resource.is_deleted:
        delete(resource.id)


def _undo_update(row) -> None:
    old = {key: values[0] for key, values in row.diff.items()}
    update(uuid.UUID(row.target_id), ResourceUpdate.model_validate(old))


def _undo_delete(row) -> None:
    resource = db.session.get(Resource, uuid.UUID(row.target_id))
    if resource is not None and resource.is_deleted:
        restore(resource.id)


def _undo_restore(row) -> None:
    resource = db.session.get(Resource, uuid.UUID(row.target_id))
    if resource is not None and not resource.is_deleted:
        delete(resource.id)


def _undo_attach(row) -> None:
    link = db.session.get(ResourceLink, uuid.UUID(row.target_id))
    if link is not None:
        detach(link.id)


def _undo_detach(row) -> None:
    meta = row.meta
    data = LinkCreate(target_type=meta["target_type"], target_id=meta["target_id"], note=meta["note"])
    if _link_between(uuid.UUID(meta["resource_id"]), data) is None:
        attach(uuid.UUID(meta["resource_id"]), data)


register_undo("resource.create", _undo_create)
register_undo("resource.update", _undo_update)
register_undo("resource.delete", _undo_delete)
register_undo("resource.restore", _undo_restore)
register_undo("resource.attach", _undo_attach)
register_undo("resource.detach", _undo_detach)


# -- reading ---------------------------------------------------------------------------------


def _uses():
    return (
        select(func.count(ResourceLink.id))
        .where(ResourceLink.resource_id == Resource.id)
        .correlate(Resource)
        .scalar_subquery()
    )


def list_spec() -> ListSpec:
    uses = _uses()
    return ListSpec(
        sortable={
            "updated": Resource.updated_at,
            "created": Resource.created_at,
            "title": func.lower(Resource.title),
            "kind": Resource.kind,
            "uses": uses,
        },
        default_sort="updated",
        default_direction="desc",
        tiebreak=Resource.id,
        searchable=(
            Resource.title,
            Resource.description_md,
            Resource.url,
            Resource.body,
            Resource.path,
            Resource.original_name,
        ),
        filters=(
            FilterSpec("kind", "Kind", Resource.kind, tuple((k, KIND_LABELS[k]) for k in RESOURCE_KINDS)),
            FilterSpec(
                "used",
                "Used",
                None,
                (("yes", "Attached somewhere"), ("no", "Not attached")),
                conditions={"yes": uses > 0, "no": uses == 0},
            ),
        ),
        views=("cards", "table"),
    )


def list_resources(args: Mapping[str, Any]) -> ListPage:
    return run_list(list_spec(), select(Resource).where(Resource.deleted_at.is_(None)), args)


def use_counts(resource_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not resource_ids:
        return {}
    rows = db.session.execute(
        select(ResourceLink.resource_id, func.count())
        .where(ResourceLink.resource_id.in_(resource_ids))
        .group_by(ResourceLink.resource_id)
    )
    return dict(rows.tuples().all())


def for_target(target_type: str, target_id: uuid.UUID) -> list[tuple[ResourceLink, Resource]]:
    """Live resources attached to a project or a task, in the order they were attached."""
    return list(
        db.session.execute(
            select(ResourceLink, Resource)
            .join(Resource, Resource.id == ResourceLink.resource_id)
            .where(
                ResourceLink.target_type == target_type,
                ResourceLink.target_id == target_id,
                Resource.deleted_at.is_(None),
            )
            .order_by(ResourceLink.created_at, ResourceLink.id)
        ).tuples()
    )


def usages(resource_id: uuid.UUID) -> list[tuple[ResourceLink, Project | Task]]:
    """Where a resource is attached: (link, live project or task)."""
    found = []
    for link in db.session.scalars(
        select(ResourceLink).where(ResourceLink.resource_id == resource_id).order_by(ResourceLink.created_at)
    ):
        target = db.session.get(TARGETS[link.target_type], link.target_id)
        if target is not None and not target.is_deleted:
            found.append((link, target))
    return found


def deleted_resources() -> list[Resource]:
    return list(
        db.session.scalars(
            select(Resource).where(Resource.deleted_at.is_not(None)).order_by(Resource.deleted_at.desc())
        )
    )
