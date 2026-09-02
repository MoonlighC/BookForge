"""Main BookForge window and batch queue coordination."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from PySide6.QtCore import QThread, Qt, QUrl, Slot
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from bookforge.core.converter import (
    INPUT_FORMATS,
    OUTPUT_FORMATS,
    ConversionError,
    ConversionResult,
    ConverterService,
)
from bookforge.core.queue import ConversionQueue, QueueItem, QueueStatus, path_key
from bookforge.ui.batch_worker import BatchConversionWorker, BatchJob
from bookforge.ui.drop_area import DropArea
from bookforge.ui.queue_item_widget import QueueItemWidget


LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, converter: ConverterService | None = None) -> None:
        super().__init__()
        self._converter = converter or ConverterService()
        self._queue = ConversionQueue()
        self._row_widgets: dict[str, QueueItemWidget] = {}
        self._output_folder_is_automatic = True
        self._thread: QThread | None = None
        self._worker: BatchConversionWorker | None = None
        self._batch_active = False

        self.setWindowTitle("BookForge")
        self.resize(940, 820)
        self.setMinimumSize(760, 680)
        self._build_ui()
        self._show_calibre_state()
        self._update_queue_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(34, 24, 34, 24)
        root.setSpacing(12)

        title = QLabel("BookForge")
        title.setObjectName("appTitle")
        subtitle = QLabel("Convert a shelf of books, one reliable step at a time")
        subtitle.setObjectName("subtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        self._warning_banner = QLabel()
        self._warning_banner.setObjectName("warningBanner")
        self._warning_banner.setWordWrap(True)
        self._warning_banner.hide()
        root.addWidget(self._warning_banner)

        self._drop_area = DropArea()
        self._drop_area.browse_requested.connect(self._browse_input)
        self._drop_area.files_selected.connect(self._add_files)
        self._drop_area.file_rejected.connect(self._show_warning)
        root.addWidget(self._drop_area)

        queue_header = QHBoxLayout()
        self._queue_heading = QLabel("Conversion queue")
        self._queue_heading.setObjectName("sectionTitle")
        self._add_button = QPushButton("+ Add books")
        self._clear_button = QPushButton("Clear queue")
        self._add_button.clicked.connect(self._browse_input)
        self._clear_button.clicked.connect(self._clear_queue)
        queue_header.addWidget(self._queue_heading)
        queue_header.addStretch(1)
        queue_header.addWidget(self._add_button)
        queue_header.addWidget(self._clear_button)
        root.addLayout(queue_header)

        self._queue_scroll = QScrollArea()
        self._queue_scroll.setObjectName("queueScroll")
        self._queue_scroll.setWidgetResizable(True)
        self._queue_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._queue_scroll.setMinimumHeight(190)
        self._queue_container = QWidget()
        self._queue_container.setObjectName("queueContainer")
        self._queue_layout = QVBoxLayout(self._queue_container)
        self._queue_layout.setContentsMargins(0, 0, 5, 0)
        self._queue_layout.setSpacing(8)
        self._queue_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._empty_queue = QLabel("No books queued yet")
        self._empty_queue.setObjectName("emptyQueue")
        self._empty_queue.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._queue_layout.addWidget(self._empty_queue)
        self._queue_scroll.setWidget(self._queue_container)
        root.addWidget(self._queue_scroll, 1)

        controls = QFrame()
        controls.setObjectName("controlsPanel")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(16, 14, 16, 14)
        controls_layout.setSpacing(11)

        formats_row = QHBoxLayout()
        formats_label = QLabel("Set every book to")
        formats_label.setObjectName("sectionLabel")
        self._set_all_combo = QComboBox()
        for output_format in OUTPUT_FORMATS:
            self._set_all_combo.addItem(output_format.label, output_format.extension)
        self._apply_all_button = QPushButton("Apply")
        self._apply_all_button.clicked.connect(self._apply_format_to_all)
        overwrite_note = QLabel("Existing files: ask before replacing")
        overwrite_note.setObjectName("subtleNote")
        formats_row.addWidget(formats_label)
        formats_row.addWidget(self._set_all_combo)
        formats_row.addWidget(self._apply_all_button)
        formats_row.addStretch(1)
        formats_row.addWidget(overwrite_note)

        folder_row = QHBoxLayout()
        folder_label = QLabel("Output folder")
        folder_label.setObjectName("sectionLabel")
        self._output_folder = QLineEdit()
        self._output_folder.setReadOnly(True)
        self._output_folder.setPlaceholderText("Add a book to choose its folder")
        self._browse_folder_button = QPushButton("Browse")
        self._browse_folder_button.clicked.connect(self._browse_output_folder)
        folder_row.addWidget(folder_label)
        folder_row.addWidget(self._output_folder, 1)
        folder_row.addWidget(self._browse_folder_button)

        controls_layout.addLayout(formats_row)
        controls_layout.addLayout(folder_row)
        root.addWidget(controls)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setTextVisible(False)
        self._progress.hide()
        root.addWidget(self._progress)

        footer = QHBoxLayout()
        self._summary = QLabel("0 books • Ready")
        self._summary.setObjectName("statusLabel")
        self._convert_button = QPushButton("Convert all")
        self._convert_button.setObjectName("primaryButton")
        self._convert_button.clicked.connect(self._start_conversion)
        footer.addWidget(self._summary, 1)
        footer.addWidget(self._convert_button)
        root.addLayout(footer)

    def _show_calibre_state(self) -> None:
        if self._converter.calibre_available:
            executable = self._converter.calibre_executable
            self._warning_banner.hide()
            if executable is not None:
                self._warning_banner.setToolTip(str(executable))
            return

        self._warning_banner.setText(
            "Calibre was not found. BookForge uses Calibre's ebook-convert engine. "
            "Install Calibre before converting books."
        )
        self._warning_banner.show()

    @Slot()
    def _browse_input(self) -> None:
        patterns = " ".join(f"*.{item.extension}" for item in INPUT_FORMATS)
        queued_items = self._queue.items
        start_folder = queued_items[0].source_path.parent if queued_items else Path.home()
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Add books",
            str(start_folder),
            f"Supported books ({patterns});;All files (*.*)",
        )
        if filenames:
            self._add_files([Path(filename) for filename in filenames])

    @Slot(object)
    def _add_files(self, paths: object) -> None:
        if self._batch_active:
            return
        path_list = [Path(path) for path in paths]  # type: ignore[union-attr]
        queue_was_empty = len(self._queue) == 0
        result = self._queue.add_paths(path_list)

        for item in result.added:
            self._add_queue_row(item)

        if queue_was_empty and result.added and self._output_folder_is_automatic:
            self._output_folder.setText(str(result.added[0].source_path.parent))

        notices: list[str] = []
        if result.duplicate_count:
            noun = "file was" if result.duplicate_count == 1 else "files were"
            notices.append(
                f"{result.duplicate_count} {noun} already in the queue and skipped."
            )
        if result.rejected:
            first = result.rejected[0]
            notices.append(
                f"{len(result.rejected)} unsupported or unavailable file(s) were "
                f"skipped. {first.path.name}: {first.reason}"
            )
        if notices:
            self._show_warning("\n\n".join(notices))
        self._update_queue_ui()

    def _add_queue_row(self, item: QueueItem) -> None:
        row = QueueItemWidget(item)
        row.output_format_changed.connect(self._set_item_output_format)
        row.remove_requested.connect(self._remove_item)
        row.open_file_requested.connect(self._open_result_file)
        row.open_folder_requested.connect(self._open_result_folder)
        self._row_widgets[item.item_id] = row
        self._queue_layout.addWidget(row)

    @Slot(str, str)
    def _set_item_output_format(self, item_id: str, output_format: str) -> None:
        if self._batch_active:
            return
        try:
            changed = self._queue.set_output_format(item_id, output_format)
        except ConversionError as exc:
            self._show_warning(str(exc))
            return
        if changed:
            self._sync_row(item_id)
            self._update_queue_ui()

    @Slot()
    def _apply_format_to_all(self) -> None:
        if self._batch_active:
            return
        output_format = str(self._set_all_combo.currentData())
        for item in self._queue.items:
            self._queue.set_output_format(item.item_id, output_format)
            self._sync_row(item.item_id)
        self._update_queue_ui()

    @Slot(str)
    def _remove_item(self, item_id: str) -> None:
        if self._batch_active or not self._queue.remove(item_id):
            return
        row = self._row_widgets.pop(item_id, None)
        if row is not None:
            self._queue_layout.removeWidget(row)
            row.deleteLater()
        if len(self._queue) == 0 and self._output_folder_is_automatic:
            self._output_folder.clear()
        self._update_queue_ui()

    @Slot()
    def _clear_queue(self) -> None:
        if self._batch_active:
            return
        for item_id in self._queue.clear_non_running():
            row = self._row_widgets.pop(item_id, None)
            if row is not None:
                self._queue_layout.removeWidget(row)
                row.deleteLater()
        if self._output_folder_is_automatic:
            self._output_folder.clear()
        self._update_queue_ui()

    @Slot()
    def _browse_output_folder(self) -> None:
        if self._batch_active:
            return
        start_folder = self._output_folder.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(
            self, "Select output folder", start_folder
        )
        if folder:
            self._output_folder.setText(folder)
            self._output_folder_is_automatic = False
            self._update_queue_ui()

    @Slot()
    def _start_conversion(self) -> None:
        if self._batch_active or (self._thread is not None and self._thread.isRunning()):
            return
        candidates = [
            item
            for item in self._queue.items
            if item.status in (QueueStatus.READY, QueueStatus.FAILED)
        ]
        if not candidates:
            self._show_warning("There are no ready books to convert.")
            return
        if not self._converter.calibre_available:
            self._show_warning(
                "Calibre was not found. Install Calibre before converting books."
            )
            return
        if not self._output_folder.text():
            self._show_warning("Select an output folder before converting.")
            return

        output_folder = Path(self._output_folder.text()).expanduser()
        if not output_folder.exists() or not output_folder.is_dir():
            self._show_warning("The selected output folder is unavailable.")
            return
        if not os.access(output_folder, os.W_OK):
            self._show_warning("The selected output folder is not writable.")
            return

        jobs: list[BatchJob] = []
        claimed_outputs: set[str] = set()
        for item in candidates:
            item.status = QueueStatus.READY
            item.result_path = None
            item.error_message = ""
            try:
                output_path = self._converter.output_path_for(
                    item.source_path, output_folder, item.output_format
                )
            except ConversionError as exc:
                self._mark_failed(item, str(exc))
                continue

            output_key = path_key(output_path)
            if output_key in claimed_outputs:
                self._mark_failed(
                    item,
                    "Another queued book targets the same output filename.",
                )
                continue

            overwrite = False
            if output_path.exists():
                overwrite = self._confirm_replace(output_path)
                if not overwrite:
                    self._mark_failed(
                        item,
                        "Skipped because the existing output file was not replaced.",
                    )
                    continue

            claimed_outputs.add(output_key)
            item.status = QueueStatus.WAITING
            self._sync_row(item.item_id)
            jobs.append(
                BatchJob(
                    item.item_id,
                    item.source_path,
                    item.output_format,
                    overwrite,
                )
            )

        if not jobs:
            self._update_queue_ui()
            return

        self._batch_active = True
        self._progress.show()
        self._set_batch_locked(True)
        self._summary.setText(f"Preparing {len(jobs)} book(s)")

        self._thread = QThread(self)
        self._worker = BatchConversionWorker(
            self._converter, tuple(jobs), output_folder.resolve()
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.item_started.connect(self._item_started)
        self._worker.item_completed.connect(self._item_completed)
        self._worker.item_failed.connect(self._item_failed)
        self._worker.finished.connect(self._batch_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread_finished)
        self._thread.start()

    @Slot(str, int, int)
    def _item_started(self, item_id: str, position: int, total: int) -> None:
        item = self._queue.get(item_id)
        if item is None:
            return
        item.status = QueueStatus.CONVERTING
        item.error_message = ""
        self._sync_row(item_id)
        self._summary.setText(f"Converting {position} of {total}")

    @Slot(str, object)
    def _item_completed(self, item_id: str, result: ConversionResult) -> None:
        item = self._queue.get(item_id)
        if item is None:
            return
        item.status = QueueStatus.COMPLETED
        item.result_path = result.output_path.resolve()
        item.error_message = ""
        self._sync_row(item_id)

    @Slot(str, str)
    def _item_failed(self, item_id: str, message: str) -> None:
        item = self._queue.get(item_id)
        if item is not None:
            self._mark_failed(item, message)

    @Slot(int, int)
    def _batch_finished(self, _completed_count: int, _failed_count: int) -> None:
        self._batch_active = False
        self._progress.hide()
        self._set_batch_locked(False)
        self._update_queue_ui()

    @Slot()
    def _thread_finished(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None

    def _mark_failed(self, item: QueueItem, message: str) -> None:
        item.status = QueueStatus.FAILED
        item.result_path = None
        item.error_message = message
        self._sync_row(item.item_id)

    def _sync_row(self, item_id: str) -> None:
        item = self._queue.get(item_id)
        row = self._row_widgets.get(item_id)
        if item is not None and row is not None:
            row.update_item(item, batch_locked=self._batch_active)

    def _set_batch_locked(self, locked: bool) -> None:
        self._drop_area.setDisabled(locked)
        self._add_button.setDisabled(locked)
        self._clear_button.setDisabled(locked or len(self._queue) == 0)
        self._set_all_combo.setDisabled(locked or len(self._queue) == 0)
        self._apply_all_button.setDisabled(locked or len(self._queue) == 0)
        self._browse_folder_button.setDisabled(locked)
        self._convert_button.setDisabled(locked)
        for item in self._queue.items:
            self._sync_row(item.item_id)

    def _update_queue_ui(self) -> None:
        count = len(self._queue)
        self._queue_heading.setText(f"Conversion queue  ·  {count}")
        self._empty_queue.setVisible(count == 0)
        self._queue_scroll.setVisible(count > 0)
        self._drop_area.set_compact(count > 0)

        has_pending = any(
            item.status in (QueueStatus.READY, QueueStatus.FAILED)
            for item in self._queue.items
        )
        can_convert = (
            count > 0
            and has_pending
            and bool(self._output_folder.text())
            and self._converter.calibre_available
            and not self._batch_active
        )
        self._convert_button.setEnabled(can_convert)
        self._clear_button.setEnabled(count > 0 and not self._batch_active)
        self._set_all_combo.setEnabled(count > 0 and not self._batch_active)
        self._apply_all_button.setEnabled(count > 0 and not self._batch_active)
        self._browse_folder_button.setEnabled(not self._batch_active)
        self._add_button.setEnabled(not self._batch_active)
        self._drop_area.setEnabled(not self._batch_active)

        if not self._batch_active:
            self._summary.setText(self._idle_summary())

    def _idle_summary(self) -> str:
        items = self._queue.items
        count = len(items)
        if count == 0:
            return "0 books • Ready"

        completed = sum(item.status is QueueStatus.COMPLETED for item in items)
        failed = sum(item.status is QueueStatus.FAILED for item in items)
        ready = sum(item.status is QueueStatus.READY for item in items)
        if completed == count:
            noun = "book" if count == 1 else "books"
            return f"{count} {noun} converted successfully"
        if completed or failed:
            parts = []
            if completed:
                parts.append(f"{completed} completed")
            if failed:
                parts.append(f"{failed} failed")
            if ready:
                parts.append(f"{ready} ready")
            return " • ".join(parts)
        noun = "book" if count == 1 else "books"
        return f"{count} {noun} • Ready"

    def _confirm_replace(self, output_path: Path) -> bool:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("Replace existing file?")
        dialog.setText(output_path.name)
        dialog.setInformativeText(
            "A file with this name already exists. Replace it for this book?"
        )
        replace_button = dialog.addButton(
            "Replace", QMessageBox.ButtonRole.AcceptRole
        )
        skip_button = dialog.addButton("Skip", QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(skip_button)
        dialog.exec()
        return dialog.clickedButton() is replace_button

    @Slot(str)
    def _open_result_file(self, item_id: str) -> None:
        item = self._queue.get(item_id)
        if item is None or item.result_path is None or not item.result_path.is_file():
            self._show_warning("The converted file is no longer available.")
            return
        self._open_local_path(item.result_path, "file")

    @Slot(str)
    def _open_result_folder(self, item_id: str) -> None:
        item = self._queue.get(item_id)
        if (
            item is None
            or item.result_path is None
            or not item.result_path.parent.is_dir()
        ):
            self._show_warning("The output folder is no longer available.")
            return
        self._open_local_path(item.result_path.parent, "folder")

    def _open_local_path(self, path: Path, item_name: str) -> None:
        try:
            opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception:
            LOGGER.exception("Could not open result %s: %s", item_name, path)
            opened = False
        if not opened:
            self._show_warning(f"BookForge could not open the {item_name}.")

    def _show_warning(self, message: str) -> None:
        QMessageBox.warning(self, "BookForge", message)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.information(
                self,
                "Conversion in progress",
                "Please wait for the current batch to finish before closing BookForge.",
            )
            event.ignore()
            return
        super().closeEvent(event)
