"""Visual row for one queued book conversion."""

from __future__ import annotations

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from bookforge.core.converter import OUTPUT_FORMATS, get_input_format
from bookforge.core.metadata import MetadataStatus
from bookforge.core.queue import QueueItem, QueueStatus, format_file_size


class QueueItemWidget(QFrame):
    output_format_changed = Signal(str, str)
    remove_requested = Signal(str)
    retry_requested = Signal(str)
    metadata_requested = Signal(str)
    open_file_requested = Signal(str)
    open_folder_requested = Signal(str)

    def __init__(self, item: QueueItem) -> None:
        super().__init__()
        self._item_id = item.item_id
        self._details_expanded = False
        self.setObjectName("queueItem")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 12, 12)
        root.setSpacing(7)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self._filename = QLabel()
        self._filename.setObjectName("queueFilename")
        self._status = QLabel()
        self._status.setObjectName("queueStatus")
        self._remove_button = QPushButton("×")
        self._remove_button.setObjectName("removeButton")
        self._remove_button.setToolTip("Remove from queue")
        self._remove_button.clicked.connect(self._request_remove)
        title_row.addWidget(self._filename, 1)
        title_row.addWidget(self._status)
        title_row.addWidget(self._remove_button)

        details_row = QHBoxLayout()
        details_row.setSpacing(9)
        self._source_details = QLabel()
        self._source_details.setObjectName("queueDetails")
        arrow = QLabel("→")
        arrow.setObjectName("conversionArrow")
        self._format_combo = QComboBox()
        self._format_combo.setObjectName("itemFormatCombo")
        for output_format in OUTPUT_FORMATS:
            self._format_combo.addItem(output_format.label, output_format.extension)
        self._format_combo.currentIndexChanged.connect(self._format_changed)
        self._retry = QPushButton("Retry")
        self._retry.setObjectName("compactButton")
        self._metadata = QPushButton("Metadata")
        self._metadata.setObjectName("compactButton")
        self._details_button = QPushButton("Details")
        self._details_button.setObjectName("compactButton")
        self._open_file = QPushButton("Open file")
        self._open_file.setObjectName("compactButton")
        self._open_folder = QPushButton("Open folder")
        self._open_folder.setObjectName("compactButton")
        self._retry.clicked.connect(self._request_retry)
        self._metadata.clicked.connect(self._request_metadata)
        self._details_button.clicked.connect(self._toggle_details)
        self._open_file.clicked.connect(self._request_open_file)
        self._open_folder.clicked.connect(self._request_open_folder)
        details_row.addWidget(self._source_details)
        details_row.addWidget(arrow)
        details_row.addWidget(self._format_combo)
        details_row.addStretch(1)
        details_row.addWidget(self._retry)
        details_row.addWidget(self._metadata)
        details_row.addWidget(self._details_button)
        details_row.addWidget(self._open_file)
        details_row.addWidget(self._open_folder)

        self._item_progress = QProgressBar()
        self._item_progress.setObjectName("itemProgress")
        self._item_progress.setTextVisible(True)

        self._error = QLabel()
        self._error.setObjectName("queueError")
        self._error.setWordWrap(True)

        self._log_view = QPlainTextEdit()
        self._log_view.setObjectName("logView")
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(1000)
        self._log_view.setMaximumHeight(130)
        self._log_view.hide()

        root.addLayout(title_row)
        root.addLayout(details_row)
        root.addWidget(self._item_progress)
        root.addWidget(self._error)
        root.addWidget(self._log_view)
        self.update_item(item)

    def update_item(self, item: QueueItem, *, batch_locked: bool = False) -> None:
        self._filename.setText(item.source_path.name)
        self._filename.setToolTip(str(item.source_path))
        try:
            size_text = format_file_size(item.source_path.stat().st_size)
        except OSError:
            size_text = "Unavailable"
        input_label = get_input_format(item.input_format).label
        self._source_details.setText(f"{size_text}  •  {input_label}")

        index = self._format_combo.findData(item.output_format)
        self._format_combo.blockSignals(True)
        self._format_combo.setCurrentIndex(index)
        self._format_combo.blockSignals(False)

        status_text = item.status.value
        if item.status is QueueStatus.CONVERTING and item.progress is not None:
            status_text = f"Converting · {item.progress}%"
        self._status.setText(status_text)
        self._status.setProperty("queueState", item.status.value.lower())
        self._status.setToolTip(item.error_message)
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)

        is_running = item.status is QueueStatus.CONVERTING
        self._format_combo.setDisabled(batch_locked or is_running)
        self._remove_button.setDisabled(batch_locked or is_running)

        self._item_progress.setVisible(is_running)
        if is_running and item.progress is not None:
            self._item_progress.setRange(0, 100)
            self._item_progress.setValue(item.progress)
            self._item_progress.setFormat("%p%")
        elif is_running:
            self._item_progress.setRange(0, 0)
            self._item_progress.setFormat("")

        completed = item.status is QueueStatus.COMPLETED
        retryable = item.status in (
            QueueStatus.FAILED,
            QueueStatus.CANCELLED,
            QueueStatus.SKIPPED,
        )
        self._retry.setVisible(retryable)
        self._retry.setEnabled(retryable and not batch_locked)
        metadata_text = "Metadata"
        if item.metadata_overrides.is_edited:
            metadata_text = "Metadata · Edited"
        elif item.metadata_status is MetadataStatus.LOADING:
            metadata_text = "Metadata · Loading…"
        elif item.metadata_status is MetadataStatus.UNAVAILABLE:
            metadata_text = "Metadata · Unavailable"
        self._metadata.setText(metadata_text)
        self._metadata.setToolTip(item.metadata_error)
        self._metadata.setEnabled(
            not batch_locked and item.metadata_status is not MetadataStatus.LOADING
        )
        self._open_file.setVisible(completed)
        self._open_folder.setVisible(completed)

        self._error.setText(item.error_message)
        self._error.setToolTip(item.error_message)
        self._error.setVisible(retryable and bool(item.error_message))

        detail_text = item.log or item.error_message or "No Calibre output captured."
        if self._log_view.toPlainText() != detail_text:
            self._log_view.setPlainText(detail_text)
        self._log_view.setVisible(self._details_expanded)
        self._details_button.setText(
            "Hide details" if self._details_expanded else "Details"
        )

    @Slot(int)
    def _format_changed(self, _index: int) -> None:
        output_format = self._format_combo.currentData()
        if output_format is not None:
            self.output_format_changed.emit(self._item_id, str(output_format))

    @Slot()
    def _toggle_details(self) -> None:
        self._details_expanded = not self._details_expanded
        self._log_view.setVisible(self._details_expanded)
        self._details_button.setText(
            "Hide details" if self._details_expanded else "Details"
        )

    @Slot()
    def _request_remove(self) -> None:
        self.remove_requested.emit(self._item_id)

    @Slot()
    def _request_retry(self) -> None:
        self.retry_requested.emit(self._item_id)

    @Slot()
    def _request_metadata(self) -> None:
        self.metadata_requested.emit(self._item_id)

    @Slot()
    def _request_open_file(self) -> None:
        self.open_file_requested.emit(self._item_id)

    @Slot()
    def _request_open_folder(self) -> None:
        self.open_folder_requested.emit(self._item_id)
