"""
Generic destructive-action confirmation dialog (spec section 8/9/20).

Every destructive operation in the application routes through this dialog
before anything is executed. It always:
  * lists exactly what will be affected (type, location, reason detected),
  * states plainly whether the action can be undone (never claims recovery
    unless the caller explicitly says so — and nothing in this app
    currently implements real recovery, so callers should not pass
    `reversible=True` unless that changes),
  * disables the confirm button until any required extra confirmation
    (a typed phrase) is satisfied.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from ui.components.cards import ClassificationBadge


@dataclass
class ConfirmItem:
    kind: str  # "File" | "Folder" | "Registry" | ...
    path: str
    reason: str
    classification: object  # core.models.Confidence


class DestructiveConfirmDialog(QDialog):
    def __init__(
        self,
        parent,
        title: str,
        summary: str,
        items: list[ConfirmItem],
        reversible: bool = False,
        required_phrase: str | None = None,
        confirm_label: str = "Delete Selected",
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(560, 440)
        self._required_phrase = required_phrase

        layout = QVBoxLayout(self)

        summary_label = QLabel(summary)
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        reversibility = QLabel(
            "This action can be undone."
            if reversible
            else "This action cannot be undone. Review the list carefully before continuing."
        )
        reversibility.setWordWrap(True)
        reversibility.setStyleSheet("font-weight: 600;" if not reversible else "")
        layout.addWidget(reversibility)

        self.list_widget = QListWidget()
        for item in items:
            row = QListWidgetItem()
            widget = _build_item_row(item)
            row.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(row)
            self.list_widget.setItemWidget(row, widget)
        layout.addWidget(self.list_widget, 1)

        count_label = QLabel(f"{len(items)} item(s) selected for this action.")
        count_label.setObjectName("mutedText")
        layout.addWidget(count_label)

        self.phrase_input: QLineEdit | None = None
        if required_phrase:
            phrase_label = QLabel(
                f"Type {required_phrase!r} to confirm this includes Registry changes:"
            )
            layout.addWidget(phrase_label)
            self.phrase_input = QLineEdit()
            self.phrase_input.textChanged.connect(self._update_confirm_state)
            layout.addWidget(self.phrase_input)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        self.confirm_btn = QPushButton(confirm_label)
        self.confirm_btn.setObjectName("dangerButton")
        self.confirm_btn.clicked.connect(self.accept)
        button_row.addWidget(self.confirm_btn)
        layout.addLayout(button_row)

        self._update_confirm_state()

    def _update_confirm_state(self) -> None:
        if self._required_phrase and self.phrase_input:
            self.confirm_btn.setEnabled(
                self.phrase_input.text().strip() == self._required_phrase
            )
        else:
            self.confirm_btn.setEnabled(True)


def _build_item_row(item: ConfirmItem):
    from PySide6.QtWidgets import QWidget

    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(6, 4, 6, 4)

    kind_label = QLabel(item.kind)
    kind_label.setFixedWidth(60)
    kind_label.setStyleSheet("font-weight: 600;")
    layout.addWidget(kind_label)

    text_col = QVBoxLayout()
    path_label = QLabel(item.path)
    path_label.setWordWrap(True)
    text_col.addWidget(path_label)
    reason_label = QLabel(item.reason)
    reason_label.setObjectName("mutedText")
    reason_label.setWordWrap(True)
    text_col.addWidget(reason_label)
    layout.addLayout(text_col, 1)

    layout.addWidget(ClassificationBadge(item.classification))
    return widget
