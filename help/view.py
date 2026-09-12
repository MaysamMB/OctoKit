"""Help / User Guide page (spec section 36)."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QListWidget, QTextBrowser, QVBoxLayout, QWidget

from help.content import SECTIONS
from ui.components.cards import PageHeader


class HelpView(QWidget):
    def __init__(self, initial_topic: str | None = None):
        super().__init__()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(14)

        header = PageHeader(
            "Help / User Guide",
            "Everything below describes what this application actually does — "
            "nothing here claims a feature is safe, read-only, or reversible "
            "unless the implementation guarantees it.",
        )
        outer.addWidget(header)

        body = QHBoxLayout()

        self.topic_list = QListWidget()
        self.topic_list.setFixedWidth(240)
        for key, (title, _) in SECTIONS.items():
            self.topic_list.addItem(title)
        self._keys = list(SECTIONS.keys())
        self.topic_list.currentRowChanged.connect(self._on_topic_selected)
        body.addWidget(self.topic_list)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        body.addWidget(self.browser, 1)

        outer.addLayout(body, 1)

        start_index = 0
        if initial_topic and initial_topic in self._keys:
            start_index = self._keys.index(initial_topic)
        self.topic_list.setCurrentRow(start_index)

    def _on_topic_selected(self, index: int) -> None:
        if index < 0 or index >= len(self._keys):
            return
        key = self._keys[index]
        _, content = SECTIONS[key]
        self.browser.setMarkdown(content)

    def show_topic(self, key: str) -> None:
        if key in self._keys:
            self.topic_list.setCurrentRow(self._keys.index(key))
