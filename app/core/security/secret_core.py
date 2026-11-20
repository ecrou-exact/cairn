"""Store and read secrets. The only module that sees plain secret values."""

from __future__ import annotations

import re

from flask import current_app
from sqlalchemy import select

from app.core.db_class.base import utcnow
from app.core.db_class.secret import Secret
from app.core.extensions import db
from app.core.security.vault import Cipher, VaultError, masked
from app.core.utils.logger import log_action

_NAME = re.compile(r"^[a-z][a-z0-9_.:-]{1,119}$")


def _cipher() -> Cipher:
    cipher = current_app.extensions.get("cairn.cipher")
    if cipher is None:
        raise VaultError("The vault is not initialised.")
    return cipher


def _get_row(name: str) -> Secret | None:
    return db.session.scalar(select(Secret).where(Secret.name == name, Secret.deleted_at.is_(None)))


def put_secret(name: str, value: str) -> Secret:
    if not _NAME.match(name):
        raise ValueError("Secret names use lowercase letters, digits and . _ : -")
    if not value:
        raise ValueError("A secret cannot be empty.")
    nonce, ciphertext = _cipher().encrypt(name, value)
    row = _get_row(name)
    action = "secret.update" if row else "secret.create"
    if row is None:
        row = Secret(name=name, nonce=nonce, ciphertext=ciphertext)
        db.session.add(row)
    else:
        row.nonce, row.ciphertext, row.updated_at = nonce, ciphertext, utcnow()
    row.hint = masked(value)
    db.session.flush()
    log_action(action, target_type="secret", target_id=name)
    return row


def get_secret(name: str) -> str | None:
    row = _get_row(name)
    if row is None:
        return None
    return _cipher().decrypt(name, row.nonce, row.ciphertext)


def delete_secret(name: str) -> bool:
    row = _get_row(name)
    if row is None:
        return False
    db.session.delete(row)
    log_action("secret.delete", target_type="secret", target_id=name, level="warning")
    return True
