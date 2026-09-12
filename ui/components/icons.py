"""
Centralized, consistent icon system.

Every icon used in the UI comes from `get_icon(name, color)` here. Icons are
drawn procedurally with QPainter (simple stroked glyphs on a transparent
canvas) so the whole application shares one visual language, scales
cleanly at any size, and recolors correctly for light/dark themes without
shipping or hand-maintaining a raster asset per color per icon.

This intentionally replaces emoji as UI icons (spec section 25).
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPainterPath, QPen, QPixmap

_SIZE = 20


def get_icon(name: str, color: str, size: int = _SIZE) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color)
    pen.setWidthF(size * 0.09)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    drawer = _DRAWERS.get(name, _draw_dot)
    drawer(painter, size)

    painter.end()
    return QIcon(pixmap)


def _rect(size: int, margin_ratio: float) -> QRectF:
    m = size * margin_ratio
    return QRectF(m, m, size - 2 * m, size - 2 * m)


def _draw_dashboard(p: QPainter, s: int) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    m = s * 0.18
    gap = s * 0.10
    w = (s - 2 * m - gap) / 2
    h = w
    for row in range(2):
        for col in range(2):
            x = m + col * (w + gap)
            y = m + row * (h + gap)
            p.drawRoundedRect(QRectF(x, y, w, h), 2, 2)


def _draw_apps(p: QPainter, s: int) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(_rect(s, 0.15), 3, 3)
    p.drawLine(QPointF(s * 0.15, s * 0.42), QPointF(s * 0.85, s * 0.42))


def _draw_broom(p: QPainter, s: int) -> None:
    p.drawLine(QPointF(s * 0.75, s * 0.15), QPointF(s * 0.35, s * 0.55))
    path = QPainterPath()
    path.moveTo(s * 0.35, s * 0.55)
    path.lineTo(s * 0.12, s * 0.68)
    path.lineTo(s * 0.20, s * 0.85)
    path.lineTo(s * 0.45, s * 0.72)
    path.closeSubpath()
    p.drawPath(path)


def _draw_trash(p: QPainter, s: int) -> None:
    p.drawLine(QPointF(s * 0.22, s * 0.28), QPointF(s * 0.78, s * 0.28))
    p.drawLine(QPointF(s * 0.38, s * 0.28), QPointF(s * 0.40, s * 0.16))
    p.drawLine(QPointF(s * 0.62, s * 0.28), QPointF(s * 0.60, s * 0.16))
    p.drawLine(QPointF(s * 0.40, s * 0.16), QPointF(s * 0.60, s * 0.16))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(s * 0.28, s * 0.30)
    path.lineTo(s * 0.32, s * 0.85)
    path.lineTo(s * 0.68, s * 0.85)
    path.lineTo(s * 0.72, s * 0.30)
    p.drawPath(path)
    p.drawLine(QPointF(s * 0.42, s * 0.42), QPointF(s * 0.44, s * 0.75))
    p.drawLine(QPointF(s * 0.58, s * 0.42), QPointF(s * 0.56, s * 0.75))


def _draw_code(p: QPainter, s: int) -> None:
    path = QPainterPath()
    path.moveTo(s * 0.40, s * 0.25)
    path.lineTo(s * 0.15, s * 0.5)
    path.lineTo(s * 0.40, s * 0.75)
    p.drawPath(path)
    path2 = QPainterPath()
    path2.moveTo(s * 0.60, s * 0.25)
    path2.lineTo(s * 0.85, s * 0.5)
    path2.lineTo(s * 0.60, s * 0.75)
    p.drawPath(path2)


def _draw_terminal(p: QPainter, s: int) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(_rect(s, 0.12), 3, 3)
    p.drawLine(QPointF(s * 0.26, s * 0.40), QPointF(s * 0.42, s * 0.52))
    p.drawLine(QPointF(s * 0.26, s * 0.64), QPointF(s * 0.42, s * 0.52))
    p.drawLine(QPointF(s * 0.50, s * 0.66), QPointF(s * 0.72, s * 0.66))


def _draw_folder(p: QPainter, s: int) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(s * 0.15, s * 0.30)
    path.lineTo(s * 0.15, s * 0.78)
    path.lineTo(s * 0.85, s * 0.78)
    path.lineTo(s * 0.85, s * 0.38)
    path.lineTo(s * 0.48, s * 0.38)
    path.lineTo(s * 0.40, s * 0.28)
    path.lineTo(s * 0.15, s * 0.28)
    path.closeSubpath()
    p.drawPath(path)


def _draw_settings(p: QPainter, s: int) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    center = QPointF(s * 0.5, s * 0.5)
    p.drawEllipse(center, s * 0.14, s * 0.14)
    import math

    for i in range(8):
        angle = i * (360 / 8)
        rad = math.radians(angle)
        inner = QPointF(center.x() + s * 0.24 * math.cos(rad), center.y() + s * 0.24 * math.sin(rad))
        outer = QPointF(center.x() + s * 0.38 * math.cos(rad), center.y() + s * 0.38 * math.sin(rad))
        p.drawLine(inner, outer)


def _draw_help(p: QPainter, s: int) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(_rect(s, 0.13))
    path = QPainterPath()
    path.moveTo(s * 0.40, s * 0.40)
    path.cubicTo(s * 0.40, s * 0.28, s * 0.62, s * 0.28, s * 0.60, s * 0.42)
    path.cubicTo(s * 0.58, s * 0.52, s * 0.50, s * 0.50, s * 0.50, s * 0.60)
    p.drawPath(path)
    p.drawEllipse(QPointF(s * 0.50, s * 0.72), s * 0.02, s * 0.02)


def _draw_info(p: QPainter, s: int) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(_rect(s, 0.13))
    p.drawLine(QPointF(s * 0.5, s * 0.44), QPointF(s * 0.5, s * 0.70))
    p.drawEllipse(QPointF(s * 0.5, s * 0.32), s * 0.02, s * 0.02)


def _draw_warning(p: QPainter, s: int) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(s * 0.5, s * 0.16)
    path.lineTo(s * 0.86, s * 0.82)
    path.lineTo(s * 0.14, s * 0.82)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(s * 0.5, s * 0.42), QPointF(s * 0.5, s * 0.62))
    p.drawEllipse(QPointF(s * 0.5, s * 0.72), s * 0.02, s * 0.02)


def _draw_error(p: QPainter, s: int) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(_rect(s, 0.13))
    p.drawLine(QPointF(s * 0.38, s * 0.38), QPointF(s * 0.62, s * 0.62))
    p.drawLine(QPointF(s * 0.62, s * 0.38), QPointF(s * 0.38, s * 0.62))


def _draw_success(p: QPainter, s: int) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(_rect(s, 0.13))
    path = QPainterPath()
    path.moveTo(s * 0.34, s * 0.52)
    path.lineTo(s * 0.46, s * 0.65)
    path.lineTo(s * 0.68, s * 0.36)
    p.drawPath(path)


def _draw_refresh(p: QPainter, s: int) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    rect = _rect(s, 0.18)
    p.drawArc(rect, 20 * 16, 300 * 16)
    path = QPainterPath()
    path.moveTo(s * 0.78, s * 0.22)
    path.lineTo(s * 0.80, s * 0.38)
    path.lineTo(s * 0.64, s * 0.34)
    path.closeSubpath()
    p.setBrush(p.pen().color())
    p.drawPath(path)


def _draw_search(p: QPainter, s: int) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(s * 0.18, s * 0.18, s * 0.46, s * 0.46))
    p.drawLine(QPointF(s * 0.58, s * 0.58), QPointF(s * 0.82, s * 0.82))


def _draw_chevron(p: QPainter, s: int) -> None:
    path = QPainterPath()
    path.moveTo(s * 0.38, s * 0.28)
    path.lineTo(s * 0.64, s * 0.5)
    path.lineTo(s * 0.38, s * 0.72)
    p.drawPath(path)


def _draw_dot(p: QPainter, s: int) -> None:
    p.setBrush(p.pen().color())
    p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.08, s * 0.08)


_DRAWERS = {
    "dashboard": _draw_dashboard,
    "apps": _draw_apps,
    "broom": _draw_broom,
    "trash": _draw_trash,
    "delete": _draw_trash,
    "code": _draw_code,
    "terminal": _draw_terminal,
    "folder": _draw_folder,
    "settings": _draw_settings,
    "help": _draw_help,
    "info": _draw_info,
    "warning": _draw_warning,
    "error": _draw_error,
    "success": _draw_success,
    "refresh": _draw_refresh,
    "search": _draw_search,
    "chevron": _draw_chevron,
}
