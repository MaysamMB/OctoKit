"""
Friendly error dialog with an expandable technical-details section
(spec section 12/19). Every ToolkitError caught anywhere in the UI layer
should be shown through this, never as a raw traceback.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from core.exceptions import ToolkitError
from ui.components.icons import get_icon


class ErrorDialog(QDialog):
    def __init__(self, parent, error: Exception, next_step: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Something went wrong")
        self.setMinimumWidth(460)

        if isinstance(error, ToolkitError):
            user_message = error.user_message
            technical = error.technical_details or str(error)
        else:
            user_message = "An unexpected error occurred."
            technical = f"{type(error).__name__}: {error}"

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(get_icon("error", "#c2372e", size=28).pixmap(28, 28))
        header.addWidget(icon_label)
        message_label = QLabel(user_message)
        message_label.setWordWrap(True)
        header.addWidget(message_label, 1)
        layout.addLayout(header)

        if next_step:
            next_label = QLabel(next_step)
            next_label.setObjectName("mutedText")
            next_label.setWordWrap(True)
            layout.addWidget(next_label)

        self.details_toggle = QPushButton("Show Technical Details")
        self.details_toggle.clicked.connect(self._toggle_details)
        layout.addWidget(self.details_toggle)

        self.details_view = QPlainTextEdit(technical)
        self.details_view.setReadOnly(True)
        self.details_view.setMaximumHeight(140)
        self.details_view.hide()
        layout.addWidget(self.details_view)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    def _toggle_details(self) -> None:
        visible = self.details_view.isVisible()
        self.details_view.setVisible(not visible)
        self.details_toggle.setText(
            "Hide Technical Details" if not visible else "Show Technical Details"
        )
