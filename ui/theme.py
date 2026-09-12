"""
Centralized theme system. No widget in the application hardcodes a color —
everything is expressed through the `Palette` returned here and the
stylesheet produced by `build_stylesheet`.

Supports Light, Dark, and System (follows the OS setting, re-checked at
startup and whenever Qt reports a palette change).
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class Palette:
    name: str
    window: str
    surface: str
    surface_alt: str
    border: str
    text: str
    text_muted: str
    accent: str
    accent_text: str
    success: str
    warning: str
    danger: str
    info: str
    hover: str
    selected: str


LIGHT = Palette(
    name="light",
    window="#f5f6f8",
    surface="#ffffff",
    surface_alt="#f0f1f4",
    border="#dde1e6",
    text="#1b1f24",
    text_muted="#5b6270",
    accent="#2f6fed",
    accent_text="#ffffff",
    success="#1b8a5a",
    warning="#b3730a",
    danger="#c2372e",
    info="#2f6fed",
    hover="#eef1f8",
    selected="#e3ecff",
)

DARK = Palette(
    name="dark",
    window="#15181d",
    surface="#1c2027",
    surface_alt="#20242c",
    border="#2c313a",
    text="#e7eaee",
    text_muted="#9aa2b1",
    accent="#5b8def",
    accent_text="#0c1116",
    success="#3fbf82",
    warning="#e0a53c",
    danger="#e5645b",
    info="#5b8def",
    hover="#242932",
    selected="#233252",
)


def detect_system_is_dark() -> bool:
    try:
        hints = QGuiApplication.styleHints()
        scheme = hints.colorScheme()
        # Qt.ColorScheme.Dark == 2 in PySide6; compare by name to stay
        # forward compatible.
        return scheme.name.lower() == "dark"
    except Exception:  # noqa: BLE001
        return False


def resolve_palette(mode: str) -> Palette:
    if mode == "dark":
        return DARK
    if mode == "light":
        return LIGHT
    # "system"
    return DARK if detect_system_is_dark() else LIGHT


def build_stylesheet(palette: Palette) -> str:
    return f"""
    * {{
        font-family: "Segoe UI", "Inter", sans-serif;
        font-size: 10.5pt;
        color: {palette.text};
    }}

    QMainWindow, QWidget#pageHost {{
        background: {palette.window};
    }}

    QWidget#sidebar {{
        background: {palette.surface};
        border-right: 1px solid {palette.border};
    }}

    QLabel#appTitle {{
        font-size: 13pt;
        font-weight: 600;
        padding: 18px 16px 4px 16px;
    }}

    QLabel#appSubtitle {{
        color: {palette.text_muted};
        font-size: 8.5pt;
        padding: 0px 16px 16px 16px;
    }}

    QLabel#navGroupLabel {{
        color: {palette.text_muted};
        font-size: 8pt;
        font-weight: 600;
        letter-spacing: 1px;
        padding: 14px 16px 4px 16px;
    }}

    QPushButton#navItem {{
        text-align: left;
        padding: 9px 16px;
        border: none;
        border-radius: 6px;
        margin: 1px 8px;
        background: transparent;
        color: {palette.text};
    }}

    QPushButton#navItem:hover {{
        background: {palette.hover};
    }}

    QPushButton#navItem:checked {{
        background: {palette.selected};
        color: {palette.accent};
        font-weight: 600;
    }}

    QPushButton#navItem:disabled {{
        color: {palette.text_muted};
    }}

    QLabel#navBadge {{
        color: {palette.text_muted};
        font-size: 7.5pt;
        background: {palette.surface_alt};
        border-radius: 8px;
        padding: 1px 7px;
    }}

    QFrame#card {{
        background: {palette.surface};
        border: 1px solid {palette.border};
        border-radius: 10px;
    }}

    QFrame#banner {{
        background: {palette.surface_alt};
        border: 1px solid {palette.border};
        border-radius: 8px;
    }}

    QLabel#pageTitle {{
        font-size: 18pt;
        font-weight: 700;
    }}

    QLabel#pageDescription {{
        color: {palette.text_muted};
        font-size: 9.5pt;
    }}

    QLabel#statValue {{
        font-size: 22pt;
        font-weight: 700;
    }}

    QLabel#statLabel {{
        color: {palette.text_muted};
        font-size: 9pt;
    }}

    QLabel#mutedText {{
        color: {palette.text_muted};
    }}

    QPushButton {{
        background: {palette.surface_alt};
        border: 1px solid {palette.border};
        border-radius: 6px;
        padding: 7px 14px;
    }}

    QPushButton:hover {{
        background: {palette.hover};
    }}

    QPushButton:disabled {{
        color: {palette.text_muted};
    }}

    QPushButton#primaryButton {{
        background: {palette.accent};
        color: {palette.accent_text};
        border: none;
        font-weight: 600;
    }}

    QPushButton#primaryButton:hover {{
        background: {palette.accent};
    }}

    QPushButton#dangerButton {{
        background: {palette.danger};
        color: white;
        border: none;
        font-weight: 600;
    }}

    QPushButton#dangerButton:disabled {{
        background: {palette.surface_alt};
        color: {palette.text_muted};
    }}

    QTableWidget, QTreeWidget, QListWidget {{
        background: {palette.surface};
        border: 1px solid {palette.border};
        border-radius: 8px;
        gridline-color: {palette.border};
        alternate-background-color: {palette.surface_alt};
    }}

    QHeaderView::section {{
        background: {palette.surface_alt};
        border: none;
        border-bottom: 1px solid {palette.border};
        padding: 6px;
        font-weight: 600;
    }}

    QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit {{
        background: {palette.surface};
        border: 1px solid {palette.border};
        border-radius: 6px;
        padding: 6px 8px;
        selection-background-color: {palette.selected};
    }}

    QProgressBar {{
        border: 1px solid {palette.border};
        border-radius: 6px;
        background: {palette.surface_alt};
        text-align: center;
        height: 16px;
    }}

    QProgressBar::chunk {{
        background: {palette.accent};
        border-radius: 6px;
    }}

    QTabWidget::pane {{
        border: 1px solid {palette.border};
        border-radius: 8px;
        top: -1px;
    }}

    QTabBar::tab {{
        padding: 7px 14px;
        margin-right: 2px;
        background: transparent;
        color: {palette.text_muted};
    }}

    QTabBar::tab:selected {{
        color: {palette.accent};
        font-weight: 600;
        border-bottom: 2px solid {palette.accent};
    }}

    QScrollArea {{
        border: none;
        background: transparent;
    }}

    QToolTip {{
        background: {palette.surface};
        color: {palette.text};
        border: 1px solid {palette.border};
        padding: 4px 6px;
    }}
    """


class ThemeManager:
    def __init__(self, app: QApplication, initial_mode: str = "system"):
        self.app = app
        self.mode = initial_mode
        self.palette = resolve_palette(initial_mode)

    def apply(self, mode: str | None = None) -> None:
        if mode:
            self.mode = mode
        self.palette = resolve_palette(self.mode)
        self.app.setStyleSheet(build_stylesheet(self.palette))
