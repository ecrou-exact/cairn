"""Secrets vault (PROJECT_BRIEF.md §11).

Secrets are encrypted with AES-256-GCM before they reach the database. The
master key never goes in the database or the repository. It is read, in order:

1. `CAIRN_MASTER_KEY` (urlsafe base64 of 32 bytes), for containers and CI;
2. the OS keyring (Secret Service, macOS Keychain, Windows Credential Locker);
3. a key file `master.key` in the data directory, created with owner-only
   permissions — the fallback for headless Ubuntu servers without a keyring.

Plain values are only returned to server code that needs them (a run's API key,
a GitHub call). The UI only ever sees `masked()`.
"""

from __future__ import annotations

import base64
import logging
import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path

import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from keyring.errors import KeyringError

_log = logging.getLogger("cairn.vault")
KEYRING_SERVICE = "cairn"
KEYRING_ITEM = "master-key"
KEY_FILE_NAME = "master.key"


class VaultError(RuntimeError):
    pass


@dataclass(frozen=True)
class MasterKey:
    key: bytes
    source: str  # "env", "keyring" or "file"


def _decode(raw: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(raw.strip().encode())
    except ValueError as exc:
        raise VaultError("The master key is not valid base64.") from exc
    if len(key) != 32:
        raise VaultError("The master key must be 32 bytes (AES-256).")
    return key


def _encode(key: bytes) -> str:
    return base64.urlsafe_b64encode(key).decode()


def _keyring_usable() -> bool:
    backend = keyring.get_keyring()
    # The "fail" and "null" backends mean there is no usable store on this machine.
    return type(backend).__module__.split(".")[-1] not in {"fail", "null"}


def _write_key_file(path: Path, key: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "w", encoding="ascii") as handle:
        handle.write(_encode(key))


def load_master_key(data_dir: Path, *, create: bool) -> MasterKey:
    """Return the master key, creating it in the best available store when `create`."""
    env_value = os.environ.get("CAIRN_MASTER_KEY")
    if env_value:
        return MasterKey(_decode(env_value), "env")

    if _keyring_usable():
        try:
            stored = keyring.get_password(KEYRING_SERVICE, KEYRING_ITEM)
            if stored:
                return MasterKey(_decode(stored), "keyring")
        except KeyringError as exc:
            _log.warning("OS keyring unavailable (%s); falling back to the key file.", type(exc).__name__)

    key_file = data_dir / KEY_FILE_NAME
    if key_file.exists():
        return MasterKey(_decode(key_file.read_text(encoding="ascii")), "file")

    if not create:
        raise VaultError("No master key found. Run `python manage.py setup` first.")

    key = AESGCM.generate_key(bit_length=256)
    if _keyring_usable():
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_ITEM, _encode(key))
            return MasterKey(key, "keyring")
        except KeyringError as exc:
            _log.warning("Could not store the master key in the OS keyring (%s).", type(exc).__name__)
    _write_key_file(key_file, key)
    return MasterKey(key, "file")


class Cipher:
    """AES-256-GCM with a random 96-bit nonce per value; the secret name is bound as associated data."""

    def __init__(self, key: bytes) -> None:
        self._aead = AESGCM(key)

    def encrypt(self, name: str, plaintext: str) -> tuple[bytes, bytes]:
        nonce = secrets.token_bytes(12)
        return nonce, self._aead.encrypt(nonce, plaintext.encode(), name.encode())

    def decrypt(self, name: str, nonce: bytes, ciphertext: bytes) -> str:
        return self._aead.decrypt(nonce, ciphertext, name.encode()).decode()


def masked(value: str | None) -> str:
    """What the UI may show of a secret: its last 4 characters at most."""
    if not value:
        return ""
    tail = value[-4:] if len(value) >= 12 else ""
    return f"••••••••{tail}"
