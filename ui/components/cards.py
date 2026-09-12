"""Reusable presentational widgets shared by the dashboard and feature pages."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.models import Confidence
from ui.components.icons import get_icon


class StatCard(QFrame):
    """A single dashboard metric card: big number, label, optional icon."""

    def __init__(self, label: str, value: str = "—", icon_name: str | None = None, accent: str = "#2f6fed"):
        super().__init__()
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        top = QHBoxLayout()
        if icon_name:
            icon_label = QLabel()
            icon_label.setPixmap(get_icon(icon_name, accent, size=22).pixmap(22, 22))
            top.addWidget(icon_label)
        top.addStretch(1)
        layout.addLayout(top)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")
        layout.addWidget(self.value_label)

        self.text_label = QLabel(label)
        self.text_label.setObjectName("statLabel")
        self.text_label.setWordWrap(True)
        layout.addWidget(self.text_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class InfoBanner(QFrame):
    """A dismissible informational/warning banner, used for read-only /
    destructive disclosures and first-use onboarding."""

    dismissed = Signal()

    def __init__(
        self,
        text: str,
        kind: str = "info",
        dismissible: bool = False,
        actions: list[tuple[str, "callable"]] | None = None,
    ):
        super().__init__()
        self.setObjectName("banner")

        colors = {"info": "#2f6fed", "warning": "#b3730a", "danger": "#c2372e", "success": "#1b8a5a"}
        color = colors.get(kind, colors["info"])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(get_icon(kind, color, size=18).pixmap(18, 18))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(icon_label)

        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setObjectName("mutedText")
        layout.addWidget(self.text_label, 1)

        for action_text, callback in actions or []:
            btn = QPushButton(action_text)
            btn.clicked.connect(callback)
            layout.addWidget(btn)

        if dismissible:
            close_btn = QPushButton("Dismiss")
            close_btn.clicked.connect(self._on_dismiss)
            layout.addWidget(close_btn)

    def _on_dismiss(self) -> None:
        self.dismissed.emit()
        self.hide()
        self.deleteLater()


class ClassificationBadge(QLabel):
    """Small colored pill used to mark an item Safe / Suspicious / Unknown."""

    def __init__(self, confidence: Confidence):
        super().__init__(confidence.value)
        colors = {
            Confidence.SAFE: ("#1b8a5a", "#e4f5ec"),
            Confidence.SUSPICIOUS: ("#b3730a", "#fbead2"),
            Confidence.UNKNOWN: ("#5b6270", "#eef0f3"),
        }
        fg, bg = colors.get(confidence, colors[Confidence.UNKNOWN])
        self.setStyleSheet(
            f"background: {bg}; color: {fg}; border-radius: 8px; padding: 2px 8px; font-weight: 600; font-size: 8pt;"
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class ReadOnlyBadge(QLabel):
    def __init__(self):
        super().__init__("READ-ONLY")
        self.setStyleSheet(
            "background: #e4f5ec; color: #1b8a5a; border-radius: 8px; padding: 2px 8px; font-weight: 700; font-size: 8pt;"
        )


class DestructiveBadge(QLabel):
    def __init__(self):
        super().__init__("CAN MODIFY YOUR SYSTEM")
        self.setStyleSheet(
            "background: #fdeceb; color: #c2372e; border-radius: 8px; padding: 2px 8px; font-weight: 700; font-size: 8pt;"
        )


class PageHeader(QWidget):
    """Standard title + description + badge + action-row header used at the
    top of every feature page (spec section 6/7)."""

    def __init__(self, title: str, description: str, read_only: bool | None = None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title_row = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("pageTitle")
        title_row.addWidget(title_label)

        if read_only is True:
            title_row.addWidget(ReadOnlyBadge())
        elif read_only is False:
            title_row.addWidget(DestructiveBadge())

        title_row.addStretch(1)
        self.actions_layout = QHBoxLayout()
        title_row.addLayout(self.actions_layout)
        layout.addLayout(title_row)

        desc_label = QLabel(description)
        desc_label.setObjectName("pageDescription")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

    def add_action(self, widget: QWidget) -> None:
        self.actions_layout.addWidget(widget)
