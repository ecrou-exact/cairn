import re
from pathlib import Path

import pytest

from app.core.db_class.activity import Activity
from app.core.extensions import db
from app.core.utils.actor import acting_as, current_actor
from app.core.utils.logger import log_action

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"


def test_actor_defaults_to_user_and_can_be_scoped():
    assert current_actor() == "user"
    with acting_as("claude:run-42"):
        assert current_actor() == "claude:run-42"
    assert current_actor() == "user"
    with pytest.raises(ValueError), acting_as("root; drop table"):
        pass


def test_log_action_records_actor_and_diff(ctx):
    with acting_as("module:validate-pr"):
        log_action("task.update", target_type="task", target_id=7, diff={"status": ["todo", "done"]})
    db.session.commit()
    entry = db.session.query(Activity).one()
    assert (entry.actor, entry.target_id, entry.diff) == (
        "module:validate-pr",
        "7",
        {"status": ["todo", "done"]},
    )


def test_log_action_refuses_unknown_level(ctx):
    with pytest.raises(ValueError):
        log_action("x.y", level="loud")


def _block(css: str, selector: str) -> dict[str, str]:
    start = css.index(selector)
    body = css[css.index("{", start) + 1 :]
    if selector.startswith("@media"):
        body = body[body.index("{") + 1 :]
    body = body[: body.index("}")]
    return dict(re.findall(r"(--cn-[\w-]+):\s*([^;]+);", body))


def test_auto_dark_theme_matches_basalt():
    css = (STATIC / "css" / "core" / "themes.css").read_text(encoding="utf-8")
    assert _block(css, '[data-theme="basalt"]') == _block(css, "@media (prefers-color-scheme: dark)")


def test_every_theme_defines_the_same_tokens():
    css = (STATIC / "css" / "core" / "themes.css").read_text(encoding="utf-8")
    reference = set(_block(css, '[data-theme="stone"]'))
    for theme in ("basalt", "moss", "ember"):
        assert set(_block(css, f'[data-theme="{theme}"]')) == reference, theme
