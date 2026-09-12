"""Sidebar navigation (spec section 6/7)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.components.icons import get_icon

# (group_label, [(key, label, icon_name, enabled)])
NAV_STRUCTURE = [
    (None, [("dashboard", "Dashboard", "dashboard", True)]),
    (
        "SYSTEM TOOLS",
        [
            ("inventory", "Application Inventory", "apps", True),
            ("leftovers", "App Leftovers Cleaner", "broom", True),
            ("tempcleaner", "Temp Files Cleaner", "trash", True),
        ],
    ),
    (
        "DEVELOPER TOOLS",
        [("projectgen", "Project Generator", "code", True)],
    ),
    (
        "UTILITIES",
        [
            ("file_utilities", "File Utilities", "folder", False),
            ("system_info", "System Information", "terminal", False),
        ],
    ),
    (
        None,
        [
            ("help", "Help / User Guide", "help", True),
            ("settings", "Settings", "settings", True),
            ("about", "About", "info", True),
        ],
    ),
]


class Sidebar(QWidget):
    navigate = Signal(str)

    def __init__(self, text_color: str = "#1b1f24"):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(230)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        title = QLabel("WinToolkit")
        title.setObjectName("appTitle")
        outer.addWidget(title)

        subtitle = QLabel("Windows Desktop Utility Suite")
        subtitle.setObjectName("appSubtitle")
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        container = QWidget()
        self._nav_layout = QVBoxLayout(container)
        self._nav_layout.setContentsMargins(0, 4, 0, 4)
        self._nav_layout.setSpacing(2)

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}

        for group_label, items in NAV_STRUCTURE:
            if group_label:
                label = QLabel(group_label)
                label.setObjectName("navGroupLabel")
                self._nav_layout.addWidget(label)
            for key, label_text, icon_name, enabled in items:
                self._nav_layout.addWidget(self._build_button(key, label_text, icon_name, enabled))

        self._nav_layout.addStretch(1)
        scroll.setWidget(container)
        outer.addWidget(scroll, 1)

    def _build_button(self, key: str, label: str, icon_name: str, enabled: bool) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        btn = QPushButton(f"  {label}")
        btn.setObjectName("navItem")
        btn.setCheckable(True)
        btn.setEnabled(enabled)
        btn.setIcon(get_icon(icon_name, "#5b6270"))
        if enabled:
            btn.clicked.connect(lambda checked, k=key: self.navigate.emit(k))
        layout.addWidget(btn, 1)

        if not enabled:
            badge = QLabel("SOON")
            badge.setObjectName("navBadge")
            layout.addWidget(badge)

        self.button_group.addButton(btn)
        self.buttons[key] = btn
        return row

    def set_active(self, key: str) -> None:
        btn = self.buttons.get(key)
        if btn:
            btn.setChecked(True)
