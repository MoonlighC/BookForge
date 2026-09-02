"""Clickable drag-and-drop area for supported book formats."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from bookforge.core.converter import INPUT_FORMATS
from bookforge.i18n import Translator


class DropArea(QFrame):
    files_selected = Signal(object)
    browse_requested = Signal()
    file_rejected = Signal(str)

    def __init__(self, translator: Translator | None = None) -> None:
        super().__init__()
        self._translator = translator or Translator()
        self._compact = False
        self.setObjectName("dropArea")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(148)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        self._icon = QLabel("＋")
        self._icon.setObjectName("dropIcon")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel("Drop books here")
        self._title.setObjectName("dropTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._formats = QLabel(" • ".join(item.label for item in INPUT_FORMATS))
        self._formats.setObjectName("dropFormats")
        self._formats.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._hint = QLabel()
        self._hint.setObjectName("dropHint")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._icon)
        layout.addWidget(self._title)
        layout.addWidget(self._formats)
        layout.addWidget(self._hint)
        self.retranslate()

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
            self.file_rejected.emit(self._translator.tr("drop.invalid"))
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
        self._compact = compact
        self.setMinimumHeight(88 if compact else 148)
        self.setMaximumHeight(96 if compact else 158)
        self.retranslate()

    def retranslate(self, translator: Translator | None = None) -> None:
        if translator is not None:
            self._translator = translator
        self.setAccessibleName(self._translator.tr("drop.accessible"))
        self.setAccessibleDescription(self._translator.tr("drop.description"))
        self.setToolTip(self._translator.tr("drop.tooltip"))
        self._title.setText(
            self._translator.tr("drop.more" if self._compact else "drop.empty")
        )
        self._hint.setText(self._translator.tr("drop.browse"))

    @staticmethod
    def _local_files_from_urls(urls) -> list[Path]:  # type: ignore[no-untyped-def]
        return [Path(url.toLocalFile()) for url in urls if url.isLocalFile()]
