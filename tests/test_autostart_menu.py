"""The server with the session, the page from the applications menu (D-100)."""

from app.core import autostart


def test_files(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    files = autostart._files(tmp_path / "cairn")
    menu = files[tmp_path / "data" / "applications" / "cairn.desktop"]
    assert 'manage.py" open' in menu and "Icon=" in menu and "Autostart" not in menu
    unit = files[tmp_path / "config" / "systemd" / "user" / "cairn-web.service"]
    assert "WantedBy=default.target" in unit and "graphical-session" not in unit
    assert not any("autostart" in str(path) for path in files)
