import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")


def test_build_application_wires_all_pages(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))

    from main import build_application

    app, window = build_application()

    expected_pages = {
        "dashboard",
        "inventory",
        "leftovers",
        "tempcleaner",
        "projectgen",
        "settings",
        "help",
        "about",
    }
    assert expected_pages.issubset(window._page_index.keys())

    for key in expected_pages:
        window.go_to(key)
        assert window.stack.currentWidget() is not None


def test_build_application_creates_default_templates(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))

    from main import build_application

    build_application()

    templates_dir = tmp_path / "localappdata" / "WinToolkit" / "Templates"
    assert (templates_dir / "Python Project").exists()
    assert (templates_dir / "React").exists()
