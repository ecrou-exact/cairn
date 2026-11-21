import json

import pytest

from app.core.db_class.activity import Activity
from app.core.db_class.setting import SettingOverride
from app.core.extensions import db
from app.core.schema.settings import SETTING_TYPES
from app.core.utils import settings
from app.core.utils.settings import SettingError, get_setting, reset_setting, set_setting
from tests.conftest import load_owner
from tests.test_core import STATIC


def test_every_settings_file_has_a_type_and_a_valid_default():
    for key, definition in settings.definitions().items():
        assert key in SETTING_TYPES, key
        SETTING_TYPES[key].validate_python(definition.default)
    assert set(SETTING_TYPES) == set(settings.definitions())


def test_theme_setting_matches_the_stylesheet():
    css = (STATIC / "css" / "core" / "themes.css").read_text(encoding="utf-8")
    for key in settings.definitions()["ui.themes"].default:
        assert f'[data-theme="{key}"]' in css, key


def test_override_reset_and_history(ctx):
    assert get_setting("jobs.retention_days") == 30
    state = set_setting("jobs.retention_days", 7)
    assert (state.value, state.overridden, state.default_changed) == (7, True, False)
    assert get_setting("jobs.retention_days") == 7
    entry = db.session.query(Activity).filter_by(action="setting.update").one()
    assert entry.diff == {"value": [30, 7]}
    reset_setting("jobs.retention_days")
    assert get_setting("jobs.retention_days") == 30
    assert db.session.query(SettingOverride).count() == 0


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("jobs.retention_days", "7"),
        ("jobs.retention_days", True),
        ("jobs.retention_days", 0),
        ("jobs.lanes", {"agent": 2, "io": 4, "module": 2}),  # a lane left out would never run
        ("jobs.lanes", {"agent": 2, "io": 4, "module": 2, "system": 1, "extra": 1}),
        ("lists.per_page", []),
        ("ui.themes", {"neon": "Neon"}),
    ],
)
def test_invalid_overrides_are_refused(ctx, key, value):
    with pytest.raises(SettingError):
        set_setting(key, value)


def test_default_changed_is_detected(ctx):
    set_setting("jobs.retention_days", 7)
    row = db.session.query(SettingOverride).one()
    row.base_value = 90  # the shipped default was 90 when the override was saved
    db.session.commit()
    assert settings.setting_state("jobs.retention_days").default_changed


def test_settings_page_and_form(app, signed_in):
    page = signed_in.get("/settings")
    assert page.status_code == 200 and b"Rows per page" in page.data and b"<textarea" in page.data
    response = signed_in.post("/settings/jobs.retention_days", data={"value": "12"})
    assert response.status_code == 302 and response.location.endswith("#jobs.retention_days")
    bad = signed_in.post("/settings/jobs.retention_days", data={"value": "{oops"}, follow_redirects=True)
    assert b"Not valid JSON" in bad.data
    assert signed_in.post("/settings/no.such_key", data={"value": "1"}).status_code == 404
    with app.app_context():
        assert get_setting("jobs.retention_days") == 12
    signed_in.post("/settings/jobs.retention_days/reset")
    with app.app_context():
        assert get_setting("jobs.retention_days") == 30


def test_settings_api(app, signed_in):
    listing = signed_in.get("/api/settings").json
    assert {s["key"] for s in listing} == set(SETTING_TYPES)
    updated = signed_in.put("/api/settings/lists.per_page", json={"value": [10, 20]})
    assert updated.status_code == 200 and updated.json["value"] == [10, 20] and updated.json["overridden"]
    assert signed_in.put("/api/settings/lists.per_page", json={"value": [1]}).status_code == 422
    assert signed_in.put("/api/settings/missing.key", json={"value": 1}).status_code == 404
    assert signed_in.delete("/api/settings/lists.per_page").json["overridden"] is False


def test_theme_choice(app, signed_in):
    signed_in.post("/settings/appearance", data={"theme": "ember"})
    assert load_owner(app).theme == "ember"
    assert b'data-theme="ember"' in signed_in.get("/").data
    assert signed_in.put("/api/account/theme", json={"theme": "neon"}).status_code == 422
    assert signed_in.put("/api/account/theme", json={"theme": "moss"}).json == {"theme": "moss"}
    assert load_owner(app).theme == "moss"
    with app.app_context():
        diff = db.session.query(Activity).filter_by(action="owner.theme").all()[-1].diff
    assert json.dumps(diff) == json.dumps({"theme": ["ember", "moss"]})
