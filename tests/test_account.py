import pyotp
import pytest
from sqlalchemy import select

from app.core.db_class.activity import Activity
from app.core.extensions import db
from app.core.security.secret_core import put_secret
from app.features.account import account_core
from app.features.account.account import _safe_next
from tests.conftest import PASSWORD, USERNAME, enable_totp, load_owner


def actions(app):
    with app.app_context():
        return [a.action for a in db.session.scalars(select(Activity).order_by(Activity.created_at))]


def test_setup_creates_owner_and_signs_in(app, client):
    response = client.post("/setup", data={"username": "theo", "password": PASSWORD, "confirm": PASSWORD})
    assert response.status_code == 302
    assert client.get("/").status_code == 200
    assert "auth.owner_create" in actions(app)


def test_setup_is_closed_once_owner_exists(app, client, owner):
    response = client.post("/setup", data={"username": "x", "password": PASSWORD, "confirm": PASSWORD})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with app.app_context(), pytest.raises(account_core.AccountError):
        account_core.create_owner("other", PASSWORD)


def test_short_password_is_refused(ctx):
    with pytest.raises(account_core.AccountError):
        account_core.create_owner("theo", "short")


def test_wrong_password_is_logged_and_refused(app, client, owner):
    response = client.post("/login", data={"username": USERNAME, "password": "wrong password here"})
    assert response.status_code == 200
    assert "Wrong username or password." in response.get_data(as_text=True)
    assert "auth.login_failed" in actions(app)
    assert client.get("/").status_code == 302


def test_unknown_user_gets_same_message(client, owner):
    response = client.post("/login", data={"username": "nobody", "password": PASSWORD})
    assert "Wrong username or password." in response.get_data(as_text=True)


def test_login_follows_only_local_next(app, client, owner):
    response = client.post("/login?next=/account/security", data={"username": USERNAME, "password": PASSWORD})
    assert response.headers["Location"].endswith("/account/security")
    with app.test_request_context():
        for target in ("https://evil.example", "//evil.example", "/\\evil.example", None):
            assert _safe_next(target) == "/"


def test_logout_requires_post(signed_in):
    assert signed_in.get("/logout").status_code == 405
    assert signed_in.post("/logout").status_code == 302
    assert signed_in.get("/").status_code == 302


def test_totp_enrolment_then_login_needs_code(app, signed_in):
    seed = enable_totp(app, signed_in)
    assert load_owner(app).totp_enabled
    signed_in.post("/logout")

    response = signed_in.post("/login", data={"username": USERNAME, "password": PASSWORD})
    assert response.headers["Location"].startswith("/login/code")
    assert signed_in.get("/").status_code == 302  # the password alone opens no session

    bad = signed_in.post("/login/code", data={"code": "000000"})
    assert "This code is not valid." in bad.get_data(as_text=True)

    with app.app_context():  # the enrolment code used the current step; allow one more for the test
        account_core.get_owner().totp_last_step = None
        db.session.commit()
    good = signed_in.post("/login/code", data={"code": pyotp.TOTP(seed).now()})
    assert good.status_code == 302
    assert signed_in.get("/").status_code == 200


def test_totp_code_cannot_be_replayed(ctx, owner):
    seed = pyotp.random_base32()
    put_secret(account_core.TOTP_SECRET_NAME, seed)
    me = account_core.get_owner()
    me.totp_enabled = True
    db.session.commit()
    code = pyotp.TOTP(seed).now()
    assert account_core.verify_totp(me, code) is True
    assert account_core.verify_totp(me, code) is False


def test_qr_code_only_during_enrolment(app, signed_in):
    assert signed_in.get("/account/security/totp/qr.svg").status_code == 404
    signed_in.post("/account/security/totp/start")
    response = signed_in.get("/account/security/totp/qr.svg")
    assert response.mimetype == "image/svg+xml"
    assert response.headers["Cache-Control"] == "no-store"


def test_password_change_signs_out_other_sessions(app, signed_in):
    other = app.test_client()
    other.post("/login", data={"username": USERNAME, "password": PASSWORD})
    assert other.get("/").status_code == 200

    new = "an even longer passphrase"
    signed_in.post("/account/security/password", data={"current": PASSWORD, "new": new, "confirm": new})
    assert signed_in.get("/").status_code == 200
    assert other.get("/").status_code == 302
    with app.app_context():
        assert account_core.authenticate(USERNAME, new) is not None
