"""Owner sign-in, first-run setup and security settings."""

from __future__ import annotations

import time

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user

from app.core.extensions import limiter
from app.core.utils.decorators import public
from app.features.account import account_core as core
from app.features.account.account_forms import LoginForm, PasswordForm, SetupForm, TotpForm

account = Blueprint("account", __name__)

PENDING_KEY = "cairn_pending_2fa"
PENDING_TTL_SECONDS = 300


def _safe_next(target: str | None) -> str:
    """Only same-site relative paths are followed after login (no open redirect)."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return url_for("home.index")


def _me() -> core.Owner:
    """The signed-in owner as a real object (never pass the `current_user` proxy to login_user)."""
    return current_user._get_current_object()


def _finish_login(owner: core.Owner) -> Response:
    session.clear()  # new session on login: no fixation
    login_user(owner)
    session.permanent = True
    core.record_login(owner)
    return redirect(_safe_next(request.args.get("next")))


@account.route("/setup", methods=["GET", "POST"])
@public
@limiter.limit("10 per minute")
def setup():
    if core.owner_exists():
        return redirect(url_for("account.login"))
    form = SetupForm()
    if form.validate_on_submit():
        try:
            owner = core.create_owner(form.username.data, form.password.data)
        except core.AccountError as exc:
            form.password.errors.append(str(exc))
        else:
            flash("Welcome to Cairn. Turn on two-factor sign-in in Security settings.", "success")
            return _finish_login(owner)
    return render_template("account/setup.html", form=form)


@account.route("/login", methods=["GET", "POST"])
@public
@limiter.limit("10 per minute; 50 per hour", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home.index"))
    form = LoginForm()
    if form.validate_on_submit():
        owner = core.authenticate(form.username.data, form.password.data)
        if owner is None:
            form.password.errors.append("Wrong username or password.")
        elif owner.totp_enabled:
            session.clear()
            session[PENDING_KEY] = {"id": owner.get_id(), "at": time.time()}
            return redirect(url_for("account.login_code", next=request.args.get("next")))
        else:
            return _finish_login(owner)
    return render_template("account/login.html", form=form)


@account.route("/login/code", methods=["GET", "POST"])
@public
@limiter.limit("10 per minute; 30 per hour", methods=["POST"])
def login_code():
    pending = session.get(PENDING_KEY)
    if not pending or time.time() - pending.get("at", 0) > PENDING_TTL_SECONDS:
        session.pop(PENDING_KEY, None)
        return redirect(url_for("account.login"))
    owner = core.load_owner_from_session_id(pending["id"])
    if owner is None:
        session.pop(PENDING_KEY, None)
        return redirect(url_for("account.login"))
    form = TotpForm()
    if form.validate_on_submit():
        if core.verify_totp(owner, form.code.data):
            return _finish_login(owner)
        form.code.errors.append("This code is not valid.")
    return render_template("account/login_code.html", form=form)


@account.route("/logout", methods=["POST"])
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("account.login"))


@account.route("/account/security", methods=["GET"])
def security():
    return render_template(
        "account/security.html",
        password_form=PasswordForm(),
        totp_form=TotpForm(),
        enrolling=core.pending_totp_qr_svg(_me()) is not None,
    )


@account.route("/account/security/password", methods=["POST"])
@limiter.limit("10 per hour")
def change_password():
    form = PasswordForm()
    if form.validate_on_submit():
        try:
            core.change_password(_me(), form.current.data, form.new.data)
        except core.AccountError as exc:
            flash(str(exc), "danger")
        else:
            login_user(_me())  # keep this session valid with the new session version
            flash("Password changed. Other sessions are signed out.", "success")
    else:
        flash(" ".join(e for errors in form.errors.values() for e in errors), "danger")
    return redirect(url_for("account.security"))


@account.route("/account/security/totp/start", methods=["POST"])
def totp_start():
    if current_user.totp_enabled:
        abort(409)
    core.start_totp_enrolment(_me())
    return redirect(url_for("account.security"))


@account.route("/account/security/totp/qr.svg", methods=["GET"])
def totp_qr():
    svg = core.pending_totp_qr_svg(_me())
    if svg is None:
        abort(404)
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-store"})


@account.route("/account/security/totp/confirm", methods=["POST"])
@limiter.limit("10 per minute")
def totp_confirm():
    form = TotpForm()
    try:
        if not form.validate_on_submit():
            raise core.AccountError("Enter the 6-digit code.")
        core.confirm_totp(_me(), form.code.data)
    except core.AccountError as exc:
        flash(str(exc), "danger")
    else:
        login_user(_me())
        flash("Two-factor sign-in is on.", "success")
    return redirect(url_for("account.security"))


@account.route("/account/security/totp/disable", methods=["POST"])
@limiter.limit("10 per minute")
def totp_disable():
    form = TotpForm()
    try:
        if not form.validate_on_submit():
            raise core.AccountError("Enter the 6-digit code.")
        core.disable_totp(_me(), form.code.data)
    except core.AccountError as exc:
        flash(str(exc), "danger")
    else:
        flash("Two-factor sign-in is off.", "warning")
    return redirect(url_for("account.security"))


# -- profile ---------------------------------------------------------------------------------


@account.get("/account/profile")
def profile():
    return render_template("account/profile.html", owner=_me())


@account.post("/account/profile")
def save_profile():
    core.update_profile(_me(), request.form.get("display_name", ""), request.form.get("bio", ""))
    flash("Profile saved.", "success")
    return redirect(url_for("account.profile"))


@account.post("/account/profile/avatar")
def upload_avatar():
    from werkzeug.exceptions import RequestEntityTooLarge

    from app.features.resources.storage_core import StorageError

    try:
        picture = request.files.get("avatar")
    except RequestEntityTooLarge:
        picture = None
    if picture is None or not picture.filename:
        flash("Choose a picture first.", "warning")
        return redirect(url_for("account.profile"))
    try:
        core.set_avatar(_me(), picture.stream)
    except StorageError as exc:
        flash(str(exc), "danger")
    else:
        flash("Picture updated.", "success")
    return redirect(url_for("account.profile"))


@account.post("/account/profile/avatar/remove")
def remove_avatar():
    core.remove_avatar(_me())
    flash("Picture removed: your initials are shown instead.", "success")
    return redirect(url_for("account.profile"))


@account.get("/account/avatar")
def avatar():
    from app.features.resources import storage_core

    return storage_core.serve_square(_me().avatar_name) or abort(404)
