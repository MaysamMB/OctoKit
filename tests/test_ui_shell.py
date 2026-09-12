import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from core.app_state import AppState
from ui.main_window import MainWindow
from ui.theme import ThemeManager


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_builds_and_navigates(qapp):
    state = AppState()
    window = MainWindow(state)
    assert window.stack.count() == 1  # only dashboard registered so far

    from PySide6.QtWidgets import QLabel

    window.register_page("placeholder", QLabel("hi"))
    window.go_to("placeholder")
    assert window.stack.currentWidget().text() == "hi"


def test_dashboard_shows_no_scan_yet_by_default(qapp):
    state = AppState()
    window = MainWindow(state)
    assert "Never" in window.dashboard.status_label.text()
    assert window.dashboard.inventory_card.value_label.text() == "—"


def test_dashboard_updates_on_state_change(qapp):
    state = AppState()
    window = MainWindow(state)
    state.record_inventory_scan(total=42, broken=3, orphans=1)
    assert window.dashboard.inventory_card.value_label.text() == "42"
    assert window.dashboard.broken_card.value_label.text() == "3"


def test_theme_manager_applies_without_error(qapp):
    manager = ThemeManager(qapp, initial_mode="dark")
    manager.apply()
    manager.apply("light")
    assert manager.palette.name == "light"
