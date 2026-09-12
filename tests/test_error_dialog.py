import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from core.exceptions import PathSafetyError
from ui.dialogs.error_dialog import ErrorDialog


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def test_error_dialog_shows_user_message_not_raw_exception(qapp):
    error = PathSafetyError(technical_details="raw stack trace stuff")
    dialog = ErrorDialog(None, error)
    assert dialog.details_view.isHidden() is True  # hidden until toggled


def test_error_dialog_details_toggle(qapp):
    error = PathSafetyError(technical_details="raw stack trace stuff")
    dialog = ErrorDialog(None, error)
    dialog._toggle_details()
    assert dialog.details_view.isHidden() is False
    assert "raw stack trace stuff" in dialog.details_view.toPlainText()


def test_error_dialog_handles_generic_exception(qapp):
    dialog = ErrorDialog(None, ValueError("boom"))
    assert "unexpected error" in dialog.layout().itemAt(0).layout().itemAt(1).widget().text().lower()
