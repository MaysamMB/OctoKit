"""Top-level application window: sidebar + stacked feature pages."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QWidget

from core.app_state import AppState
from ui.dashboard import Dashboard
from ui.sidebar import Sidebar


class MainWindow(QWidget):
    def __init__(self, app_state: AppState):
        super().__init__()
        self.setWindowTitle("WinToolkit — Windows Desktop Utility Suite")
        self.resize(1180, 760)
        self.setMinimumSize(860, 560)

        self.app_state = app_state
        self._page_index: dict[str, int] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("pageHost")
        layout.addWidget(self.stack, 1)

        self.dashboard = Dashboard(app_state)
        self.dashboard.navigate_requested.connect(self.go_to)
        self.register_page("dashboard", self.dashboard)

        self.sidebar.navigate.connect(self.go_to)
        self.sidebar.set_active("dashboard")

    def register_page(self, key: str, widget: QWidget) -> None:
        index = self.stack.addWidget(widget)
        self._page_index[key] = index

    def go_to(self, key: str) -> None:
        index = self._page_index.get(key)
        if index is None:
            return
        self.stack.setCurrentIndex(index)
        self.sidebar.set_active(key)
