"""About page."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from help.content import ABOUT_TEXT
from ui.components.cards import PageHeader


class AboutView(QWidget):

    def __init__(self, open_help_callback=None):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        header = PageHeader(
            "About",
            "Version and safety information.",
        )
        layout.addWidget(header)

        browser = QTextBrowser()

        about_content = f"""
{ABOUT_TEXT}

---

### OctoKit

**Version:** 0.2.0

**Developed by:** Maysam Baradiya

[LinkedIn](https://www.linkedin.com/in/maysam-baradiya-589757347/)
"""

        browser.setMarkdown(about_content)
        browser.setOpenExternalLinks(True)

        layout.addWidget(browser, 1)

        if open_help_callback:
            row = QHBoxLayout()
            row.addStretch(1)

            btn = QPushButton("Open Full Help / User Guide")
            btn.setObjectName("primaryButton")
            btn.clicked.connect(open_help_callback)

            row.addWidget(btn)
            layout.addLayout(row)
