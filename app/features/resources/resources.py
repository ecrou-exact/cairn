"""Resource pages: library, resource page, form, upload (drop or paste), attach and detach."""

from __future__ import annotations

import uuid
from datetime import date
from urllib.parse import quote

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, send_file, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from app.core.schema.resources import CREATABLE_KINDS, ResourceCreate, ResourceUpdate
from app.core.utils.events import latest_event_id
from app.core.utils.history import batch
from app.core.utils.settings import get_setting
from app.core.utils.web import FormErrors, back_to, flash_undo, local_path, validate
from app.features.projects import projects_core
from app.features.resources import resources_core, storage_core
from app.features.resources.resources_forms import (
    KIND_FIELDS,
    parse_link,
    values_from_form,
    values_from_resource,
)

resources = Blueprint("resources", __name__)

# Uploaded files are never run or rendered by the browser as a page.
FILE_CSP = "default-src 'none'; img-src 'self'; sandbox"


def _resource_or_404(resource_id: uuid.UUID):
    try:
        return resources_core.get_resource(resource_id)
    except resources_core.ResourceNotFound:
        abort(404)


def _kinds() -> list[tuple[str, str, str, str]]:
    """(kind, label, icon, hint) of what the owner can create by hand, for the "New" links."""
    return [
        (k, resources_core.KIND_LABELS[k], resources_core.KIND_ICONS[k], resources_core.KIND_HINTS[k])
        for k in CREATABLE_KINDS
    ]


def _form(kind: str, values, errors=None, resource=None, status=200):
    return (
        render_template(
            "resources/form.html",
            kind=kind,
            fields=KIND_FIELDS[kind],
            kinds=_kinds(),
            values=values,
            errors=errors or {},
            resource=resource,
            attach=request.values.get("attach", ""),
            back=local_path(request.values.get("next")),
            max_mb=get_setting("resources.max_upload_mb"),
        ),
        status,
    )


@resources.get("/resources")
def index():
    after = latest_event_id()
    page = resources_core.list_resources(request.args)
    return render_template(
        "resources/index.html",
        page=page,
        uses=resources_core.use_counts([r.id for r in page.items]),
        kinds=_kinds(),
        counts=resources_core.kind_counts(),
        events_after=after,
        max_mb=get_setting("resources.max_upload_mb"),
    )


@resources.get("/resources/new")
def new():
    kind = request.args.get("kind", "url")
    if kind not in CREATABLE_KINDS:
        abort(404)
    return _form(kind, {"language": "shell" if kind == "tool" else ""})


@resources.post("/resources/new")
def create():
    kind = request.form.get("kind", "")
    if kind not in CREATABLE_KINDS:
        abort(400)
    target = parse_link(request.form.get("attach"))
    try:
        with batch() as batch_id:
            resource = resources_core.create(
                validate(ResourceCreate, {"kind": kind, **values_from_form(request.form, kind)}), target
            )
    except FormErrors as exc:
        return _form(kind, request.form, exc.errors, status=422)
    except resources_core.ResourceError as exc:
        return _form(kind, request.form, {"": str(exc)}, status=422)
    flash_undo(f"Added “{resource.title}”.", batch_id)
    return redirect(back_to(url_for("resources.detail", resource_id=resource.id)))


@resources.post("/resources/quick")
def quick_link():
    """A web address pasted in a resources panel: a link (or GitHub item), attached at once."""
    url = (request.form.get("url") or "").strip()
    target = parse_link(request.form.get("attach"))
    kind = "github" if url.lower().startswith(("https://github.com/", "http://github.com/")) else "url"
    try:
        with batch() as batch_id:
            resource = resources_core.create(validate(ResourceCreate, {"kind": kind, "url": url}), target)
    except FormErrors as exc:
        flash(next(iter(exc.errors.values())), "danger")
    except resources_core.ResourceError as exc:
        flash(str(exc), "danger")
    else:
        flash_undo(f"Attached “{resource.title}”.", batch_id)
    return redirect(back_to(url_for("resources.index")))


@resources.post("/resources/upload")
def upload():
    target = parse_link(request.form.get("attach"))
    try:
        files = [f for f in request.files.getlist("files") if f and f.filename]
    except RequestEntityTooLarge:
        flash("These files are too large to send at once (50 MB at most).", "danger")
        return redirect(back_to(url_for("resources.index")))
    if not files:
        flash("Choose or drop a file first.", "warning")
        return redirect(back_to(url_for("resources.index")))
    added, reused, problems = [], [], []
    with batch() as batch_id:
        for file in files:
            try:
                resource, new = resources_core.upload(file.stream, file.filename, target)
            except (storage_core.StorageError, resources_core.ResourceError) as exc:
                problems.append(f"{storage_core.clean_name(file.filename)}: {exc}")
                continue
            (added if new else reused).append(resource)
    for problem in problems:
        flash(problem, "danger")
    if added or reused:
        parts = []
        if added:
            parts.append(f"Uploaded {_names(added)}")
        if reused:
            parts.append(f"{_names(reused)} {'was' if len(reused) == 1 else 'were'} already in the library")
        flash_undo(". ".join(parts) + ".", batch_id)
        if not target and len(added) == 1 and not reused:
            return redirect(url_for("resources.detail", resource_id=added[0].id))
    return redirect(back_to(url_for("resources.index")))


def _names(items) -> str:
    names = [f"“{item.title}”" for item in items[:3]]
    return ", ".join(names) + (f" and {len(items) - 3} more" if len(items) > 3 else "")


@resources.get("/resources/<uuid:resource_id>")
def detail(resource_id: uuid.UUID):
    after = latest_event_id()
    resource = _resource_or_404(resource_id)
    return render_template(
        "resources/detail.html",
        resource=resource,
        usages=resources_core.usages(resource.id),
        project_options=projects_core.options(),
        previews_on=get_setting("resources.previews"),
        events_after=after,
    )


@resources.get("/resources/<uuid:resource_id>/file")
def file(resource_id: uuid.UUID):
    resource = _resource_or_404(resource_id)
    if not resource.has_file:
        abort(404)
    try:
        path = storage_core.path_of(resource.stored_name)
    except storage_core.StorageError:
        abort(404)
    if not path.is_file():
        abort(404)
    inline = resource.kind == "image" and request.args.get("download") != "1"
    response = send_file(
        path,
        mimetype=resource.mime if inline else "application/octet-stream",
        as_attachment=not inline,
        download_name=resource.original_name or "file",
        conditional=True,
        max_age=0,
    )
    response.headers["Content-Security-Policy"] = FILE_CSP
    response.headers["Cache-Control"] = "private, no-cache"
    return response


@resources.get("/resources/<uuid:resource_id>/text")
def text(resource_id: uuid.UUID):
    """A note, a snippet or a link as a file to keep (D-096)."""
    found = resources_core.text_of(_resource_or_404(resource_id))
    if found is None:
        abort(404)
    name, body = found
    response = Response(body, mimetype="text/plain; charset=utf-8")
    response.headers["Content-Disposition"] = f"attachment; filename={quote(name)}"
    response.headers["Content-Security-Policy"] = FILE_CSP
    return response


@resources.post("/resources/zip")
def zip_download():
    """The chosen resources in one zip (D-096)."""
    try:
        ids = [uuid.UUID(raw) for raw in request.form.getlist("resource_ids")]
        blob = resources_core.zip_of(ids)
    except (ValueError, resources_core.ResourceError) as exc:
        flash(
            str(exc) if isinstance(exc, resources_core.ResourceError) else "Choose the resources to take.",
            "warning",
        )
        return redirect(back_to(url_for("resources.index")))
    response = Response(blob, mimetype="application/zip")
    response.headers["Content-Disposition"] = f"attachment; filename=resources-{date.today().isoformat()}.zip"
    return response


@resources.get("/resources/<uuid:resource_id>/edit")
def edit(resource_id: uuid.UUID):
    resource = _resource_or_404(resource_id)
    return _form(resource.kind, values_from_resource(resource), resource=resource)


@resources.post("/resources/<uuid:resource_id>/edit")
def save(resource_id: uuid.UUID):
    resource = _resource_or_404(resource_id)
    values = values_from_form(request.form, resource.kind)
    try:
        with batch() as batch_id:
            resources_core.update(resource.id, validate(ResourceUpdate, values))
    except FormErrors as exc:
        return _form(resource.kind, request.form, exc.errors, resource, status=422)
    except resources_core.ResourceError as exc:
        return _form(resource.kind, request.form, {"": str(exc)}, resource, status=422)
    flash_undo("Saved.", batch_id)
    return redirect(url_for("resources.detail", resource_id=resource.id))


@resources.post("/resources/<uuid:resource_id>/delete")
def delete(resource_id: uuid.UUID):
    resource = _resource_or_404(resource_id)
    with batch() as batch_id:
        resources_core.delete(resource.id)
    flash_undo(f"“{resource.title}” moved to the trash.", batch_id)
    return redirect(back_to(url_for("resources.index")))


@resources.post("/resources/<uuid:resource_id>/preview")
def refresh_preview(resource_id: uuid.UUID):
    _resource_or_404(resource_id)
    try:
        resources_core.refresh_preview(resource_id)
    except resources_core.ResourceError as exc:
        flash(str(exc), "danger")
    else:
        flash("Fetching the page again. The preview appears here when it is done.", "info")
    return redirect(url_for("resources.detail", resource_id=resource_id))


@resources.post("/resources/<uuid:resource_id>/use-title")
def use_title(resource_id: uuid.UUID):
    _resource_or_404(resource_id)
    try:
        with batch() as batch_id:
            resource = resources_core.use_preview_title(resource_id)
    except resources_core.ResourceError as exc:
        flash(str(exc), "danger")
    else:
        flash_undo(f"Renamed to “{resource.title}”.", batch_id)
    return redirect(url_for("resources.detail", resource_id=resource_id))


@resources.post("/resources/attach")
def attach():
    target = parse_link(f"{request.form.get('target_type', '')}:{request.form.get('target_id', '')}")
    try:
        resource_id = uuid.UUID(request.form.get("resource_id", ""))
    except ValueError:
        resource_id = None
    if target is None or resource_id is None:
        flash("Pick what to attach, and where.", "warning")
        return redirect(back_to(url_for("resources.index")))
    try:
        with batch() as batch_id:
            resources_core.attach(resource_id, target)
    except resources_core.ResourceError as exc:
        flash(str(exc), "danger")
    else:
        flash_undo("Attached.", batch_id)
    return redirect(back_to(url_for("resources.detail", resource_id=resource_id)))


@resources.post("/resources/links/<uuid:link_id>/detach")
def detach(link_id: uuid.UUID):
    try:
        with batch() as batch_id:
            link = resources_core.detach(link_id)
    except resources_core.ResourceNotFound:
        abort(404)
    flash_undo("Detached. The resource stays in the library.", batch_id)
    return redirect(back_to(url_for("resources.detail", resource_id=link.resource_id)))
