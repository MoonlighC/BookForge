"""Generate BookForge's original development icon."""

from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication


def draw_icon(size: int = 256) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    tile = QRectF(size * 0.06, size * 0.06, size * 0.88, size * 0.88)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#3568d4"))
    painter.drawRoundedRect(tile, size * 0.19, size * 0.19)

    book = QPainterPath()
    book.moveTo(QPointF(size * 0.20, size * 0.31))
    book.quadTo(
        QPointF(size * 0.38, size * 0.26), QPointF(size * 0.50, size * 0.39)
    )
    book.quadTo(
        QPointF(size * 0.62, size * 0.26), QPointF(size * 0.80, size * 0.31)
    )
    book.lineTo(QPointF(size * 0.80, size * 0.72))
    book.quadTo(
        QPointF(size * 0.62, size * 0.67), QPointF(size * 0.50, size * 0.79)
    )
    book.quadTo(
        QPointF(size * 0.38, size * 0.67), QPointF(size * 0.20, size * 0.72)
    )
    book.closeSubpath()
    painter.setBrush(QColor("#ffffff"))
    painter.drawPath(book)

    painter.setPen(
        QPen(QColor("#a9c2f4"), size * 0.025, Qt.PenStyle.SolidLine)
    )
    painter.drawLine(
        QPointF(size * 0.50, size * 0.39), QPointF(size * 0.50, size * 0.79)
    )
    painter.end()
    return image


def main() -> int:
    QApplication.instance() or QApplication(sys.argv)
    destination = Path(__file__).resolve().parent / "assets" / "bookforge.ico"
    if not draw_icon().save(str(destination), "ICO"):
        raise RuntimeError("Qt could not write the BookForge ICO file.")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
