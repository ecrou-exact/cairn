import base64
import os
import stat

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.db_class.secret import Secret
from app.core.extensions import db
from app.core.security import vault
from app.core.security.secret_core import delete_secret, get_secret, put_secret


def test_secret_round_trip_and_never_plain_in_db(ctx):
    put_secret("anthropic.main", "sk-ant-very-secret-value-1234")
    db.session.commit()
    row = db.session.query(Secret).one()
    assert b"very-secret" not in row.ciphertext
    assert row.hint == "••••••••1234"
    assert get_secret("anthropic.main") == "sk-ant-very-secret-value-1234"
    assert delete_secret("anthropic.main") is True
    assert get_secret("anthropic.main") is None


def test_ciphertext_is_bound_to_its_name():
    cipher = vault.Cipher(AESGCM.generate_key(bit_length=256))
    nonce, data = cipher.encrypt("github.token", "ghp_x")
    with pytest.raises(InvalidTag):
        cipher.decrypt("other.name", nonce, data)


def test_invalid_names_and_empty_values_are_refused(ctx):
    with pytest.raises(ValueError):
        put_secret("Bad Name", "x")
    with pytest.raises(ValueError):
        put_secret("ok.name", "")


def test_masked_never_shows_short_secrets():
    assert vault.masked("short") == "••••••••"
    assert vault.masked("") == ""


def test_master_key_from_env(monkeypatch, tmp_path):
    key = os.urandom(32)
    monkeypatch.setenv("CAIRN_MASTER_KEY", base64.urlsafe_b64encode(key).decode())
    assert vault.load_master_key(tmp_path, create=False) == vault.MasterKey(key, "env")


def test_master_key_file_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("CAIRN_MASTER_KEY", raising=False)
    monkeypatch.setattr(vault, "_keyring_usable", lambda: False)
    with pytest.raises(vault.VaultError):
        vault.load_master_key(tmp_path, create=False)
    created = vault.load_master_key(tmp_path, create=True)
    assert created.source == "file"
    assert vault.load_master_key(tmp_path, create=False).key == created.key
    if os.name == "posix":
        assert stat.S_IMODE((tmp_path / vault.KEY_FILE_NAME).stat().st_mode) == 0o600


def test_wrong_key_size_is_refused(monkeypatch, tmp_path):
    monkeypatch.setenv("CAIRN_MASTER_KEY", base64.urlsafe_b64encode(b"too short").decode())
    with pytest.raises(vault.VaultError):
        vault.load_master_key(tmp_path, create=False)
