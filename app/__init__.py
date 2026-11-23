"""Cairn application factory."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from app.config import ROOT_DIR, get_config


def create_app(env: str | None = None) -> Flask:
    load_dotenv(ROOT_DIR / ".env")
    config = get_config(env)

    app = Flask(__name__)
    app.config.from_object(config)
    app.config["SQLALCHEMY_DATABASE_URI"] = config.database_uri()
    app.config["CAIRN_DATA_DIR"] = config.data_dir()
    keep_private(app.config["CAIRN_DATA_DIR"])
    app.config["CAIRN_UPLOAD_DIR"] = app.config["CAIRN_DATA_DIR"] / "uploads"
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("CAIRN_SECRET_KEY is not set. Run `python manage.py setup` first.")

    logging.basicConfig(level=logging.DEBUG if app.debug else logging.INFO)

    _init_extensions(app)
    _init_vault(app)
    _register_blueprints(app)

    from app.api import register_api
    from app.core.security.headers import register_security_headers
    from app.core.utils.decorators import register_access_rules
    from app.core.utils.static_versions import register_static_versions
    from app.core.utils.template_filters import register_template_filters

    register_api(app)
    register_access_rules(app)
    register_template_filters(app)
    register_security_headers(app)
    register_static_versions(app)
    return app


def keep_private(folder: Path) -> None:
    """The data folder (database, vault key, transcripts of what runs) is the owner's alone."""
    if os.name != "posix" or not folder.is_dir():
        return
    try:
        if folder.stat().st_uid == os.getuid() and folder.stat().st_mode & 0o077:
            folder.chmod(0o700)
    except OSError:
        logging.getLogger("cairn").warning("The data folder %s could not be made private", folder)


def _init_extensions(app: Flask) -> None:
    from app.core import db_class  # noqa: F401  (registers every model)
    from app.core.extensions import csrf, db, limiter, login_manager, migrate

    db.init_app(app)
    migrate.init_app(app, db, directory=str(ROOT_DIR / "migrations"))
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "account.login"
    login_manager.session_protection = "strong"

    from app.features.account.account_core import load_owner_from_session_id

    login_manager.user_loader(load_owner_from_session_id)


def _init_vault(app: Flask) -> None:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    from app.core.security.vault import Cipher, load_master_key

    if app.testing:
        key = AESGCM.generate_key(bit_length=256)
    else:
        key = load_master_key(app.config["CAIRN_DATA_DIR"], create=False).key
    app.extensions["cairn.cipher"] = Cipher(key)


def _register_blueprints(app: Flask) -> None:
    from app import jobs as _handlers  # noqa: F401  (registers every job handler)
    from app.features.about.about import about
    from app.features.account.account import account
    from app.features.changesets.changesets import changesets
    from app.features.claude.claude import claude
    from app.features.comments.comments import comments
    from app.features.connections.connections import connections
    from app.features.events.events import events
    from app.features.folder.folder import folder
    from app.features.graph.graph import graph
    from app.features.history.history import history
    from app.features.home.home import health, home
    from app.features.instances.instances import instances
    from app.features.jobs.jobs import jobs
    from app.features.projects.projects import projects
    from app.features.recap.recap import recap
    from app.features.resources.resources import resources
    from app.features.settings.settings import settings
    from app.features.tasks.tasks import tasks
    from app.features.trash.trash import trash

    for blueprint in (
        about,
        account,
        home,
        health,
        jobs,
        settings,
        events,
        projects,
        graph,
        tasks,
        recap,
        folder,
        resources,
        comments,
        changesets,
        claude,
        instances,
        connections,
        trash,
        history,
    ):
        app.register_blueprint(blueprint)
