"""Where uploaded files live (docs/SECURITY.md T8).

- One root (`CAIRN_UPLOAD_DIR`, by default `<data dir>/uploads`), files under random names
  (`ab/ab12…`), never under a name the browser sent; every path is resolved and checked to
  stay inside the root.
- Size checked while reading, not trusted from headers.
- Images (PNG, JPEG, GIF, WebP) are decoded and encoded again: metadata such as GPS
  positions goes away, and a file that only pretends to be an image is not kept as one.
  Anything else is kept as is and only ever downloaded, never shown inline.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import mimetypes
import os
import re
import secrets
import tempfile
import time
import unicodedata
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import IO

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

IMAGE_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "GIF": "image/gif", "WEBP": "image/webp"}
IMAGE_EXTENSIONS = {"PNG": ".png", "JPEG": ".jpg", "GIF": ".gif", "WEBP": ".webp"}
MAX_PIXELS = 40_000_000  # well under Pillow's own decompression-bomb limit
CHUNK = 1024 * 1024
_NAME = re.compile(r"^[0-9a-f]{32}$")


class StorageError(ValueError):
    pass


@dataclass(frozen=True)
class StoredFile:
    stored_name: str
    original_name: str
    mime: str
    size_bytes: int
    sha256: str
    image: dict[str, int] | None  # {"width", "height"} for images


def root() -> Path:
    path = Path(current_app.config["CAIRN_UPLOAD_DIR"])
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def path_of(stored_name: str) -> Path:
    if not _NAME.match(stored_name or ""):
        raise StorageError("Not a stored file name.")
    base = root()
    path = (base / stored_name[:2] / stored_name).resolve()
    if not path.is_relative_to(base):
        raise StorageError("Outside the upload folder.")
    return path


def clean_name(filename: str | None) -> str:
    """The name to show and to download as: no folders, no control characters."""
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(c for c in unicodedata.normalize("NFC", name) if unicodedata.category(c)[0] != "C")
    name = name.strip(" .")[:255]
    return name or "file"


def _receive(stream: IO[bytes], max_bytes: int, folder: Path) -> tuple[Path, int, str]:
    digest = hashlib.sha256()
    size = 0
    handle = tempfile.NamedTemporaryFile(dir=folder, prefix="incoming-", delete=False)  # noqa: SIM115
    try:
        with handle:
            while chunk := stream.read(CHUNK):
                size += len(chunk)
                if size > max_bytes:
                    raise StorageError(f"This file is larger than {max_bytes // (1024 * 1024)} MB.")
                digest.update(chunk)
                handle.write(chunk)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise
    if size == 0:
        Path(handle.name).unlink(missing_ok=True)
        raise StorageError("This file is empty.")
    return Path(handle.name), size, digest.hexdigest()


def _reencode(path: Path) -> tuple[bytes, str, dict[str, int]] | None:
    """(new bytes, format, size) when the file is an image Cairn shows, else None.

    Raises StorageError for an image too large to decode safely."""
    try:
        with Image.open(path, formats=list(IMAGE_FORMATS)) as image:
            width, height = image.size
            if width * height > MAX_PIXELS:
                raise StorageError("This image is too large (more than 40 megapixels).")
            fmt = image.format
            out = io.BytesIO()
            image.info.pop("comment", None)
            if getattr(image, "is_animated", False):
                image.save(out, format=fmt, save_all=True)
            else:
                image.load()
                clean = ImageOps.exif_transpose(image)
                if fmt == "JPEG" and clean.mode not in ("RGB", "L"):
                    clean = clean.convert("RGB")
                clean.save(out, format=fmt, **({"quality": 90} if fmt == "JPEG" else {}))
                width, height = clean.size
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        return None  # not an image Cairn shows (or a damaged one): kept as a file, download only
    return out.getvalue(), fmt, {"width": width, "height": height}


def store(stream: IO[bytes], filename: str | None, max_bytes: int) -> StoredFile:
    base = root()
    temp, size, sha = _receive(stream, max_bytes, base)
    try:
        name = secrets.token_hex(16)
        target = base / name[:2] / name
        target.parent.mkdir(exist_ok=True)
        original = clean_name(filename)
        image = _reencode(temp)
        if image is not None:
            data, fmt, dims = image
            target.write_bytes(data)
            stem = original.rsplit(".", 1)[0] if "." in original else original
            return StoredFile(
                name, f"{stem}{IMAGE_EXTENSIONS[fmt]}", IMAGE_FORMATS[fmt], len(data), sha, dims
            )
        os.replace(temp, target)
        mime = mimetypes.guess_type(original)[0] or "application/octet-stream"
        return StoredFile(name, original, mime, size, sha, None)
    finally:
        temp.unlink(missing_ok=True)


def remove(stored_name: str) -> None:
    path = path_of(stored_name)
    path.unlink(missing_ok=True)
    with contextlib.suppress(OSError):
        path.parent.rmdir()  # only when empty


def remove_orphan_files(older_than: timedelta = timedelta(days=1)) -> int:
    """Delete stored files nothing refers to (an upload whose change was rolled back),
    once they are old enough not to belong to an upload in progress."""
    from sqlalchemy import select

    from app.core.db_class.owner import Owner
    from app.core.db_class.planning import Project
    from app.core.db_class.resource import Resource
    from app.core.extensions import db

    base = root()
    known = {
        name
        for column in (Resource.stored_name, Owner.avatar_name, Project.image_name)
        for name in db.session.scalars(select(column).where(column.is_not(None)))
    }
    limit = time.time() - older_than.total_seconds()
    removed = 0
    stored = [path for path in base.glob("*/*") if path.name not in known]
    for path in [*stored, *base.glob("incoming-*")]:
        if path.is_file() and path.stat().st_mtime < limit:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


AVATAR_SIZE = 256


def store_square(stream: IO[bytes], max_bytes: int) -> str:
    """A picture cropped to a centred square and resized, saved as PNG without metadata (a logo
    keeps its transparency)."""
    base = root()
    temp, _size, _sha = _receive(stream, max_bytes, base)
    try:
        try:
            with Image.open(temp, formats=list(IMAGE_FORMATS)) as image:
                width, height = image.size
                if width * height > MAX_PIXELS:
                    raise StorageError("This image is too large (more than 40 megapixels).")
                image.load()
                square = ImageOps.fit(
                    ImageOps.exif_transpose(image).convert("RGBA"), (AVATAR_SIZE, AVATAR_SIZE)
                )
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
            raise StorageError("Use a PNG, JPEG, GIF or WebP picture.") from exc
        name = secrets.token_hex(16)
        target = base / name[:2] / name
        target.parent.mkdir(exist_ok=True)
        out = io.BytesIO()
        square.save(out, format="PNG", optimize=True)
        target.write_bytes(out.getvalue())
        return name
    finally:
        temp.unlink(missing_ok=True)


def serve_square(stored_name: str | None):
    """The response for a picture kept by `store_square`; None when there is none."""
    from flask import send_file

    path = path_of(stored_name) if stored_name else None
    if path is None or not path.is_file():
        return None
    mime = "image/png" if path.read_bytes()[:4] == b"\x89PNG" else "image/jpeg"  # older ones are JPEG
    response = send_file(path, mimetype=mime, max_age=0, conditional=True)
    response.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
    response.headers["Cache-Control"] = "private, no-cache"
    return response
