"""
Home screen (spec section 8). Shows real, current session state only —
never fabricated numbers. Every card reads "No scan yet" until the
corresponding feature has actually been run, either from the Dashboard's
own "Scan Now" quick actions or from visiting the feature page directly.

The Dashboard never triggers a destructive operation, and its own quick
"scan" actions only invoke the read-only scan half of each feature.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.app_state import AppState
from ui.components.cards import InfoBanner, StatCard
from ui.components.icons import get_icon


def _fmt_bytes(num: int | None) -> str:
    if num is None:
        return "—"
    value = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


def _fmt_time(dt) -> str:
    if dt is None:
        return "Never"
    return dt.strftime("%Y-%m-%d %H:%M")


class Dashboard(QWidget):
    navigate_requested = Signal(str)
    quick_scan_requested = Signal(str)  # feature key

    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        desc = QLabel(
            "An overview of what's on your system. Nothing here is changed "
            "automatically — every number reflects a scan you've actually run."
        )
        desc.setObjectName("pageDescription")
        desc.setWordWrap(True)
        outer.addWidget(desc)

        outer.addWidget(
            InfoBanner(
                "Scanning is always read-only. Nothing is deleted or modified from "
                "the Dashboard or from any Scan button anywhere in the app without "
                "your explicit confirmation.",
                kind="info",
            )
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        grid = QGridLayout()
        grid.setSpacing(14)

        self.inventory_card = StatCard("Applications Detected", icon_name="apps")
        self.broken_card = StatCard("Potential Broken Registrations", icon_name="warning", accent="#b3730a")
        self.temp_card = StatCard("Temp Files Recoverable Space", icon_name="trash")
        self.projects_card = StatCard("Projects Generated This Session", icon_name="code")

        grid.addWidget(self.inventory_card, 0, 0)
        grid.addWidget(self.broken_card, 0, 1)
        grid.addWidget(self.temp_card, 0, 2)
        grid.addWidget(self.projects_card, 0, 3)
        content_layout.addLayout(grid)

        self.status_label = QLabel()
        self.status_label.setObjectName("mutedText")
        self.status_label.setWordWrap(True)
        content_layout.addWidget(self.status_label)

        quick_label = QLabel("Quick Actions")
        quick_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
        content_layout.addWidget(quick_label)

        quick_row = QHBoxLayout()
        for key, label, icon_name in [
            ("inventory", "Scan Applications", "apps"),
            ("tempcleaner", "Scan Temp Files", "trash"),
            ("leftovers", "Clean Up a Program", "broom"),
            ("projectgen", "New Project", "code"),
        ]:
            btn = QPushButton(f"  {label}")
            btn.setIcon(get_icon(icon_name, "#2f6fed"))
            btn.clicked.connect(lambda checked, k=key: self.navigate_requested.emit(k))
            quick_row.addWidget(btn)
        content_layout.addLayout(quick_row)

        content_layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        self.app_state.changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        state = self.app_state

        if state.inventory_last_scan is not None:
            self.inventory_card.set_value(str(state.inventory_total_apps))
            self.broken_card.set_value(str(state.inventory_broken))
        else:
            self.inventory_card.set_value("—")
            self.broken_card.set_value("—")

        if state.temp_last_scan is not None:
            self.temp_card.set_value(_fmt_bytes(state.temp_scan_bytes))
        else:
            self.temp_card.set_value("—")

        self.projects_card.set_value(str(state.projects_generated_count))

        lines = [
            f"Last application scan: {_fmt_time(state.inventory_last_scan)}",
            f"Last temp files scan: {_fmt_time(state.temp_last_scan)}   ·   Last cleanup: {_fmt_time(state.temp_last_cleanup)}",
            f"Last leftovers scan: {_fmt_time(state.leftovers_last_scan)}",
        ]
        self.status_label.setText("\n".join(lines))
