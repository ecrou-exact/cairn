"""Runtime configuration, selected with the CAIRN_ENV environment variable.

Values come from the environment (a `.env` file at the repository root is loaded
if present). Nothing secret has a default: the secret key is generated on first
setup by `manage.py setup` and stored in `.env`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

from platformdirs import user_data_path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _data_dir() -> Path:
    """Where Cairn keeps its database (SQLite), uploads and worktrees."""
    configured = os.environ.get("CAIRN_DATA_DIR")
    path = Path(configured).expanduser() if configured else user_data_path("cairn", appauthor=False)
    path.mkdir(parents=True, exist_ok=True)
    return path


class BaseConfig:
    ENV_NAME = "base"
    SECRET_KEY = os.environ.get("CAIRN_SECRET_KEY")
    HOST = os.environ.get("CAIRN_HOST", "127.0.0.1")
    PORT = int(os.environ.get("CAIRN_PORT", "7010"))

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict] = {"pool_pre_ping": True}

    SESSION_COOKIE_NAME = "cairn_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    SESSION_COOKIE_SECURE = os.environ.get("CAIRN_HTTPS", "0") == "1"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Strict"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 12

    WTF_CSRF_TIME_LIMIT = None
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024

    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_HEADERS_ENABLED = True

    TESTING = False
    DEBUG = False

    @classmethod
    def database_uri(cls) -> str:
        return os.environ.get("CAIRN_DATABASE_URL") or f"sqlite:///{_data_dir() / 'cairn.db'}"

    @classmethod
    def data_dir(cls) -> Path:
        return _data_dir()


class DevelopmentConfig(BaseConfig):
    ENV_NAME = "development"
    DEBUG = True


class TestingConfig(BaseConfig):
    ENV_NAME = "testing"
    TESTING = True
    # Test configuration only, never used to run Cairn.
    SECRET_KEY = "testing-only-not-secret"  # noqa: S105  # nosec B105
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False

    @classmethod
    def database_uri(cls) -> str:
        return "sqlite://"


class ProductionConfig(BaseConfig):
    ENV_NAME = "production"


CONFIGS: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None) -> type[BaseConfig]:
    name = name or os.environ.get("CAIRN_ENV", "development")
    try:
        return CONFIGS[name]
    except KeyError as exc:
        raise RuntimeError(f"Unknown CAIRN_ENV '{name}'. Use one of: {', '.join(CONFIGS)}.") from exc
