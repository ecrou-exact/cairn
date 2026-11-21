"""Test fixtures.

Requests must run without an outer app context: Flask reuses an active app context for
requests, so `g` (and Flask-Login's cached user) would leak between requests and clients.
Tests that call core code directly use the `ctx` fixture or `with app.app_context()`.
"""

from __future__ import annotations

import pyotp
import pytest

from app import create_app
from app.core.extensions import db
from app.features.account import account_core

USERNAME = "owner"
PASSWORD = "correct horse battery staple"


@pytest.fixture()
def app(tmp_path):
    app = create_app("testing")
    app.config["CAIRN_UPLOAD_DIR"] = tmp_path / "uploads"
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()  # close pooled SQLite connections (ResourceWarning on Python 3.13+)


@pytest.fixture()
def ctx(app):
    with app.app_context():
        yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def owner(app):
    with app.app_context():
        account_core.create_owner(USERNAME, PASSWORD)
    return USERNAME


@pytest.fixture()
def signed_in(client, owner):
    response = client.post("/login", data={"username": USERNAME, "password": PASSWORD})
    assert response.status_code == 302
    return client


def load_owner(app):
    with app.app_context():
        found = account_core.get_owner()
        db.session.expunge(found)
        return found


def enable_totp(app, client) -> str:
    """Turn on TOTP through the real routes; return the seed."""
    from app.core.security.secret_core import get_secret

    client.post("/account/security/totp/start")
    with app.app_context():
        seed = get_secret(account_core.TOTP_PENDING_NAME)
    client.post("/account/security/totp/confirm", data={"code": pyotp.TOTP(seed).now()})
    return seed
