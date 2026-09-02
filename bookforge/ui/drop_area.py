"""Clickable EPUB drag-and-drop area."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class DropArea(QFrame):
    file_selected = Signal(object)
    browse_requested = Signal()
    file_rejected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dropArea")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(200)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        icon = QLabel("＋")
        icon.setObjectName("dropIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Drop your EPUB here")
        title.setObjectName("dropTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("or click to browse")
        hint.setObjectName("dropHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(hint)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._epub_from_urls(event.mimeData().urls()) is not None:
            event.acceptProposedAction()
            self.setProperty("dragActive", True)
            self.style().unpolish(self)
            self.style().polish(self)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._clear_drag_state()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._clear_drag_state()
        path = self._epub_from_urls(event.mimeData().urls())
        if path is None:
            self.file_rejected.emit("Please drop a single EPUB file.")
            event.ignore()
            return
        event.acceptProposedAction()
        self.file_selected.emit(path)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.browse_requested.emit()
        super().mouseReleaseEvent(event)

    def _clear_drag_state(self) -> None:
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)

    @staticmethod
    def _epub_from_urls(urls) -> Path | None:  # type: ignore[no-untyped-def]
        local_paths = [Path(url.toLocalFile()) for url in urls if url.isLocalFile()]
        if len(local_paths) != 1:
            return None
        path = local_paths[0]
        return path if path.suffix.lower() == ".epub" and path.is_file() else None
