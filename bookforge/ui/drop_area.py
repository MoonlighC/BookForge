"""Clickable drag-and-drop area for supported book formats."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from bookforge.core.converter import INPUT_FORMATS


class DropArea(QFrame):
    files_selected = Signal(object)
    browse_requested = Signal()
    file_rejected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dropArea")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(180)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        icon = QLabel("＋")
        icon.setObjectName("dropIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel("Drop books here")
        self._title.setObjectName("dropTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        formats = QLabel(" • ".join(item.label for item in INPUT_FORMATS))
        formats.setObjectName("dropFormats")
        formats.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("or click to browse")
        hint.setObjectName("dropHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(self._title)
        layout.addWidget(formats)
        layout.addWidget(hint)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._local_files_from_urls(event.mimeData().urls()):
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
        paths = self._local_files_from_urls(event.mimeData().urls())
        if not paths:
            self.file_rejected.emit("Please drop one or more local book files.")
            event.ignore()
            return
        event.acceptProposedAction()
        self.files_selected.emit(paths)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.browse_requested.emit()
        super().mouseReleaseEvent(event)

    def _clear_drag_state(self) -> None:
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_compact(self, compact: bool) -> None:
        self.setMinimumHeight(104 if compact else 180)
        self.setMaximumHeight(116 if compact else 16777215)
        self._title.setText("Drop more books here" if compact else "Drop books here")

    @staticmethod
    def _local_files_from_urls(urls) -> list[Path]:  # type: ignore[no-untyped-def]
        return [Path(url.toLocalFile()) for url in urls if url.isLocalFile()]
