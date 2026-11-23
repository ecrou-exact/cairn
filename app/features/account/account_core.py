"""Owner account: first-run setup, password login, TOTP second factor."""

from __future__ import annotations

import hmac

import pyotp
import segno
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import func, select

from app.core.db_class.base import utcnow
from app.core.db_class.owner import Owner
from app.core.extensions import db
from app.core.security.secret_core import delete_secret, get_secret, put_secret
from app.core.utils.logger import log_action
from app.core.utils.settings import get_setting

MIN_PASSWORD_LENGTH = 12
# Vault entry names, not secrets.
TOTP_SECRET_NAME = "auth.totp"  # noqa: S105  # nosec B105
TOTP_PENDING_NAME = "auth.totp.pending"
TOTP_ISSUER = "Cairn"

_hasher = PasswordHasher()
# Verified against when the username is unknown, so both paths take the same time.
_DUMMY_HASH = _hasher.hash("cairn-timing-equaliser")


class AccountError(ValueError):
    pass


def owner_exists() -> bool:
    return bool(db.session.scalar(select(func.count()).select_from(Owner)))


def get_owner() -> Owner | None:
    return db.session.scalar(select(Owner).where(Owner.deleted_at.is_(None)))


def load_owner_from_session_id(session_id: str) -> Owner | None:
    owner_id, _, version = session_id.partition(":")
    owner = get_owner()
    if owner is None or str(owner.id) != owner_id or str(owner.session_version) != version:
        return None
    return owner


def _check_password_rules(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AccountError(f"The password must be at least {MIN_PASSWORD_LENGTH} characters long.")


def create_owner(username: str, password: str) -> Owner:
    if owner_exists():
        raise AccountError("The owner account already exists.")
    username = username.strip()
    if not username:
        raise AccountError("A username is required.")
    _check_password_rules(password)
    owner = Owner(username=username, password_hash=_hasher.hash(password))
    db.session.add(owner)
    db.session.flush()
    log_action("auth.owner_create", target_type="owner", target_id=owner.id)
    db.session.commit()
    return owner


def authenticate(username: str, password: str) -> Owner | None:
    owner = get_owner()
    candidate = owner if owner is not None and owner.username == username.strip() else None
    try:
        _hasher.verify(candidate.password_hash if candidate else _DUMMY_HASH, password)
    except (VerificationError, InvalidHashError):
        log_action("auth.login_failed", level="warning", meta={"username": username[:64]})
        db.session.commit()
        return None
    if candidate is None:
        return None
    if _hasher.check_needs_rehash(candidate.password_hash):
        candidate.password_hash = _hasher.hash(password)
        db.session.commit()
    return candidate


def record_login(owner: Owner) -> None:
    owner.last_login_at = utcnow()
    log_action("auth.login", target_type="owner", target_id=owner.id)
    db.session.commit()


def theme_choices() -> dict[str, str]:
    return dict(get_setting("ui.themes"))


def set_theme(owner: Owner, theme: str) -> None:
    if theme not in theme_choices():
        raise AccountError("This theme does not exist.")
    if theme != owner.theme:
        log_action(
            "owner.theme", target_type="owner", target_id=owner.id, diff={"theme": [owner.theme, theme]}
        )
        owner.theme = theme
        db.session.commit()


def change_password(owner: Owner, current: str, new: str) -> None:
    try:
        _hasher.verify(owner.password_hash, current)
    except (VerificationError, InvalidHashError) as exc:
        raise AccountError("The current password is wrong.") from exc
    _check_password_rules(new)
    owner.password_hash = _hasher.hash(new)
    owner.session_version += 1
    log_action("auth.password_change", target_type="owner", target_id=owner.id, level="warning")
    db.session.commit()


# --- TOTP ---------------------------------------------------------------------------------------


def start_totp_enrolment(owner: Owner) -> str:
    """Create a pending TOTP seed; it becomes active only after a valid code (`confirm_totp`)."""
    seed = pyotp.random_base32()
    put_secret(TOTP_PENDING_NAME, seed)
    db.session.commit()
    return pyotp.TOTP(seed).provisioning_uri(name=owner.username, issuer_name=TOTP_ISSUER)


def pending_totp_qr_svg(owner: Owner) -> str | None:
    seed = get_secret(TOTP_PENDING_NAME)
    if seed is None:
        return None
    uri = pyotp.TOTP(seed).provisioning_uri(name=owner.username, issuer_name=TOTP_ISSUER)
    return segno.make(uri, error="m").svg_inline(scale=5, dark="#1d1b18", light="#ffffff")


def confirm_totp(owner: Owner, code: str) -> None:
    seed = get_secret(TOTP_PENDING_NAME)
    if seed is None:
        raise AccountError("Start the set-up again: no pending code.")
    step = _matching_step(seed, code.strip())
    if step is None:
        raise AccountError("This code is not valid. Check your device's clock and try again.")
    put_secret(TOTP_SECRET_NAME, seed)
    delete_secret(TOTP_PENDING_NAME)
    owner.totp_enabled = True
    owner.totp_last_step = step
    owner.session_version += 1
    log_action("auth.totp_enable", target_type="owner", target_id=owner.id, level="warning")
    db.session.commit()


def disable_totp(owner: Owner, code: str) -> None:
    if not verify_totp(owner, code):
        raise AccountError("This code is not valid.")
    delete_secret(TOTP_SECRET_NAME)
    owner.totp_enabled = False
    log_action("auth.totp_disable", target_type="owner", target_id=owner.id, level="warning")
    db.session.commit()


def _matching_step(seed: str, code: str) -> int | None:
    """Time step (30 s window) the code belongs to, accepting one step of clock drift."""
    totp = pyotp.TOTP(seed)
    now_step = totp.timecode(utcnow())
    for step in (now_step, now_step - 1, now_step + 1):
        if hmac.compare_digest(totp.generate_otp(step), code):
            return step
    return None


def verify_totp(owner: Owner, code: str) -> bool:
    """Check a code once: a code already used (same or older step) is refused (no replay)."""
    if not owner.totp_enabled:
        return False
    seed = get_secret(TOTP_SECRET_NAME)
    step = _matching_step(seed, code.strip()) if seed else None
    ok = step is not None and step > (owner.totp_last_step or 0)
    if ok:
        owner.totp_last_step = step
        db.session.commit()
    else:
        log_action("auth.totp_failed", target_type="owner", target_id=owner.id, level="warning")
        db.session.commit()
    return ok


# -- profile ---------------------------------------------------------------------------------

AVATAR_MAX_BYTES = 8 * 1024 * 1024


def update_profile(owner: Owner, display_name: str, bio: str) -> None:
    display_name, bio = " ".join(display_name.split())[:80], bio.strip()[:300]
    diff = {
        k: [getattr(owner, k), v]
        for k, v in (("display_name", display_name), ("bio", bio))
        if getattr(owner, k) != v
    }
    if not diff:
        return
    owner.display_name, owner.bio = display_name, bio
    log_action("account.profile", target_type="owner", target_id=owner.id, diff=diff)
    db.session.commit()


def set_avatar(owner: Owner, stream) -> None:
    from app.features.resources import storage_core

    name = storage_core.store_square(stream, AVATAR_MAX_BYTES)
    old, owner.avatar_name = owner.avatar_name, name
    log_action("account.avatar", target_type="owner", target_id=owner.id)
    db.session.commit()
    if old:
        storage_core.remove(old)


def remove_avatar(owner: Owner) -> None:
    from app.features.resources import storage_core

    if owner.avatar_name:
        old, owner.avatar_name = owner.avatar_name, None
        log_action("account.avatar_removed", target_type="owner", target_id=owner.id)
        db.session.commit()
        storage_core.remove(old)
