"""Main BookForge window and batch queue coordination."""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from threading import Event

from PySide6.QtCore import QSettings, QThread, QThreadPool, QTimer, Qt, QUrl, Slot
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QKeySequence
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

from bookforge import __version__
from bookforge.core.batch import (
    OverwriteDecision,
    OverwritePolicy,
    PreflightIssue,
    preflight_batch,
)
from bookforge.core.converter import (
    INPUT_FORMATS,
    OUTPUT_FORMATS,
    ConversionError,
    ConversionResult,
    ConverterService,
)
from bookforge.core.queue import ConversionQueue, QueueItem, QueueStatus
from bookforge.core.metadata import (
    BookMetadata,
    MetadataError,
    MetadataLoadResult,
    MetadataOverrides,
    MetadataService,
    MetadataStatus,
)
from bookforge.resources import application_icon
from bookforge.settings import ApplicationSettings
from bookforge.ui.batch_worker import (
    BatchCancellation,
    BatchConversionWorker,
)
from bookforge.ui.drop_area import DropArea
from bookforge.ui.metadata_dialog import MetadataDialog
from bookforge.ui.metadata_worker import MetadataLoadTask
from bookforge.ui.queue_item_widget import QueueItemWidget


LOGGER = logging.getLogger(__name__)
_RETRYABLE_STATUSES = (
    QueueStatus.FAILED,
    QueueStatus.CANCELLED,
    QueueStatus.SKIPPED,
)


class MainWindow(QMainWindow):
    def __init__(
        self,
        converter: ConverterService | None = None,
        metadata_service: MetadataService | None = None,
        settings: QSettings | None = None,
    ) -> None:
        super().__init__()
        self._converter = converter or ConverterService()
        self._settings = ApplicationSettings(settings)
        self._queue = ConversionQueue()
        self._metadata_service = metadata_service or MetadataService()
        self._metadata_pool = QThreadPool(self)
        self._metadata_pool.setMaxThreadCount(2)
        self._metadata_events: dict[str, Event] = {}
        self._metadata_tasks: dict[str, MetadataLoadTask] = {}
        self._metadata_closed = False
        self._row_widgets: dict[str, QueueItemWidget] = {}
        self._output_folder_is_automatic = True
        self._thread: QThread | None = None
        self._worker: BatchConversionWorker | None = None
        self._cancellation: BatchCancellation | None = None
        self._batch_active = False
        self._batch_cancel_requested = False
        self._closing_after_cancel = False
        self._current_position = 0
        self._current_total = 0

        self.setWindowTitle("BookForge")
        self.setWindowIcon(application_icon())
        self.resize(1100, 750)
        self.setMinimumSize(780, 620)
        self._build_menu()
        self._build_ui()
        self._restore_settings()
        self._show_calibre_state()
        self._update_queue_ui()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        self._add_books_action = QAction("Add books…", self)
        self._add_books_action.setShortcut(QKeySequence("Ctrl+O"))
        self._add_books_action.setStatusTip("Add one or more books to the queue")
        self._add_books_action.triggered.connect(self._browse_input)
        self._exit_action = QAction("Exit", self)
        self._exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self._exit_action.triggered.connect(self.close)
        file_menu.addAction(self._add_books_action)
        file_menu.addSeparator()
        file_menu.addAction(self._exit_action)

        help_menu = self.menuBar().addMenu("&Help")
        self._about_action = QAction("About BookForge", self)
        self._about_action.triggered.connect(self._show_about)
        help_menu.addAction(self._about_action)

        self._convert_action = QAction("Convert all", self)
        self._convert_action.setShortcut(QKeySequence("Ctrl+Enter"))
        self._convert_action.triggered.connect(self._start_conversion)
        self.addAction(self._convert_action)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(28, 20, 28, 20)
        root.setSpacing(10)

        title = QLabel("BookForge")
        title.setObjectName("appTitle")
        subtitle = QLabel("Simple e-book conversion for Kindle & more")
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
        self._retry_failed_button = QPushButton("Retry failed")
        self._clear_button = QPushButton("Clear queue")
        self._retry_failed_button.setAccessibleName("Retry failed books")
        self._clear_button.setAccessibleName("Clear conversion queue")
        self._retry_failed_button.clicked.connect(self._retry_failed)
        self._clear_button.clicked.connect(self._clear_queue)
        queue_header.addWidget(self._queue_heading)
        queue_header.addStretch(1)
        queue_header.addWidget(self._retry_failed_button)
        queue_header.addWidget(self._clear_button)
        root.addLayout(queue_header)

        self._queue_scroll = QScrollArea()
        self._queue_scroll.setObjectName("queueScroll")
        self._queue_scroll.setWidgetResizable(True)
        self._queue_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._queue_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
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
        self._set_all_combo.setObjectName("globalFormatCombo")
        self._set_all_combo.setAccessibleName("Format for every book")
        for index, output_format in enumerate(OUTPUT_FORMATS):
            self._set_all_combo.addItem(output_format.label, output_format.extension)
            self._set_all_combo.setItemData(
                index,
                output_format.description,
                Qt.ItemDataRole.ToolTipRole,
            )
        self._set_all_combo.currentIndexChanged.connect(
            self._update_global_format_tooltip
        )
        self._apply_all_button = QPushButton("Apply")
        self._apply_all_button.clicked.connect(self._apply_format_to_all)
        overwrite_label = QLabel("Existing files")
        overwrite_label.setObjectName("sectionLabel")
        self._overwrite_combo = QComboBox()
        self._overwrite_combo.setObjectName("overwritePolicyCombo")
        self._overwrite_combo.setAccessibleName("Existing files policy")
        policy_hints = {
            OverwritePolicy.ASK: "Ask before replacing each existing output",
            OverwritePolicy.REPLACE_ALL: "Replace existing outputs in this batch",
            OverwritePolicy.SKIP_ALL: "Skip books whose outputs already exist",
        }
        for index, policy in enumerate(OverwritePolicy):
            self._overwrite_combo.addItem(policy.value, policy.value)
            self._overwrite_combo.setItemData(
                index, policy_hints[policy], Qt.ItemDataRole.ToolTipRole
            )
        formats_row.addWidget(formats_label)
        formats_row.addWidget(self._set_all_combo)
        formats_row.addWidget(self._apply_all_button)
        formats_row.addStretch(1)
        formats_row.addWidget(overwrite_label)
        formats_row.addWidget(self._overwrite_combo)

        folder_row = QHBoxLayout()
        folder_label = QLabel("Output folder")
        folder_label.setObjectName("sectionLabel")
        self._output_folder = QLineEdit()
        self._output_folder.setReadOnly(True)
        self._output_folder.setAccessibleName("Output folder")
        self._output_folder.setPlaceholderText("Add a book to choose its folder")
        self._browse_folder_button = QPushButton("Browse")
        self._browse_folder_button.setAccessibleName("Browse for output folder")
        self._browse_folder_button.clicked.connect(self._browse_output_folder)
        folder_row.addWidget(folder_label)
        folder_row.addWidget(self._output_folder, 1)
        folder_row.addWidget(self._browse_folder_button)

        controls_layout.addLayout(formats_row)
        controls_layout.addLayout(folder_row)
        root.addWidget(controls)

        self._progress = QProgressBar()
        self._progress.setObjectName("batchProgress")
        self._progress.setTextVisible(True)
        self._progress.hide()
        root.addWidget(self._progress)

        footer = QHBoxLayout()
        self._summary = QLabel("0 books • Ready")
        self._summary.setObjectName("statusLabel")
        self._cancel_current_button = QPushButton("Cancel current")
        self._cancel_current_button.setObjectName("cancelButton")
        self._cancel_batch_button = QPushButton("Cancel batch")
        self._cancel_batch_button.setObjectName("dangerButton")
        self._convert_button = QPushButton("Convert all")
        self._convert_button.setObjectName("primaryButton")
        self._convert_button.setAccessibleName("Convert all ready books")
        self._cancel_current_button.clicked.connect(self._cancel_current)
        self._cancel_batch_button.clicked.connect(self._cancel_batch)
        self._convert_button.clicked.connect(self._start_conversion)
        footer.addWidget(self._summary, 1)
        footer.addWidget(self._cancel_current_button)
        footer.addWidget(self._cancel_batch_button)
        footer.addWidget(self._convert_button)
        root.addLayout(footer)
        self._update_global_format_tooltip()

    @Slot(int)
    def _update_global_format_tooltip(self, _index: int = -1) -> None:
        index = self._set_all_combo.currentIndex()
        description = self._set_all_combo.itemData(
            index, Qt.ItemDataRole.ToolTipRole
        )
        self._set_all_combo.setToolTip(str(description or "Choose an output format"))

    def _restore_settings(self) -> None:
        valid_formats = {output_format.extension for output_format in OUTPUT_FORMATS}
        output_format = self._settings.global_format(valid_formats, "azw3")
        format_index = self._set_all_combo.findData(output_format)
        if format_index >= 0:
            self._set_all_combo.setCurrentIndex(format_index)

        valid_policies = {policy.value for policy in OverwritePolicy}
        policy_value = self._settings.overwrite_policy(
            valid_policies, OverwritePolicy.ASK.value
        )
        policy_index = self._overwrite_combo.findData(policy_value)
        if policy_index >= 0:
            self._overwrite_combo.setCurrentIndex(policy_index)

        output_folder = self._settings.output_folder()
        if output_folder is not None:
            self._output_folder.setText(str(output_folder))
            self._output_folder_is_automatic = False

        self._settings.restore_geometry(self)

    def _save_settings(self) -> None:
        self._settings.save_geometry(self)
        output_folder: Path | None = None
        if not self._output_folder_is_automatic and self._output_folder.text():
            candidate = Path(self._output_folder.text()).expanduser()
            if candidate.is_dir():
                output_folder = candidate.resolve()
        self._settings.save_output_folder(output_folder)
        policy_value = str(self._overwrite_combo.currentData())
        self._settings.save_conversion_choices(
            str(self._set_all_combo.currentData()), policy_value
        )

    @Slot()
    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About BookForge",
            f"<b>BookForge</b><br>Version {__version__}<br><br>"
            "A simple personal desktop e-book converter built with Python, "
            "PySide6, and Calibre.<br><br>"
            "Calibre is a separate dependency.",
        )

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
            self._start_metadata_load(item)

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
        row.retry_requested.connect(self._retry_item)
        row.metadata_requested.connect(self._open_metadata)
        row.open_file_requested.connect(self._open_result_file)
        row.open_folder_requested.connect(self._open_result_folder)
        self._row_widgets[item.item_id] = row
        self._queue_layout.addWidget(row)

    def _start_metadata_load(self, item: QueueItem) -> None:
        if not self._metadata_service.available:
            item.metadata_status = MetadataStatus.UNAVAILABLE
            item.metadata_error = "Calibre's ebook-meta tool was not found."
            self._sync_row(item.item_id)
            return
        item.metadata_status = MetadataStatus.LOADING
        item.metadata_error = ""
        cancel_event = Event()
        task = MetadataLoadTask(
            self._metadata_service,
            item.item_id,
            item.source_path,
            cancel_event,
        )
        task.signals.loaded.connect(self._metadata_loaded)
        task.signals.failed.connect(self._metadata_failed)
        task.signals.finished.connect(self._metadata_task_finished)
        self._metadata_events[item.item_id] = cancel_event
        self._metadata_tasks[item.item_id] = task
        self._sync_row(item.item_id)
        self._metadata_pool.start(task)

    @Slot(str, object)
    def _metadata_loaded(self, item_id: str, result: MetadataLoadResult) -> None:
        item = self._queue.get(item_id)
        event = self._metadata_events.get(item_id)
        if item is None or (event is not None and event.is_set()):
            return
        item.original_metadata = result.metadata
        item.metadata_status = MetadataStatus.LOADED
        item.metadata_error = ""
        self._sync_row(item_id)

    @Slot(str, str)
    def _metadata_failed(self, item_id: str, message: str) -> None:
        item = self._queue.get(item_id)
        event = self._metadata_events.get(item_id)
        if item is None or (event is not None and event.is_set()):
            return
        item.metadata_status = MetadataStatus.UNAVAILABLE
        item.metadata_error = message
        self._sync_row(item_id)

    @Slot(str)
    def _metadata_task_finished(self, item_id: str) -> None:
        self._metadata_events.pop(item_id, None)
        self._metadata_tasks.pop(item_id, None)

    def _cancel_metadata_item(self, item_id: str) -> None:
        cancel_event = self._metadata_events.get(item_id)
        if cancel_event is not None:
            cancel_event.set()
        self._metadata_service.cleanup_item(item_id)

    def _shutdown_metadata(self) -> None:
        if self._metadata_closed:
            return
        self._metadata_closed = True
        for cancel_event in self._metadata_events.values():
            cancel_event.set()
        self._metadata_pool.clear()
        self._metadata_pool.waitForDone()
        self._metadata_events.clear()
        self._metadata_tasks.clear()
        self._metadata_service.close()

    @Slot(str)
    def _open_metadata(self, item_id: str) -> None:
        if self._batch_active:
            return
        item = self._queue.get(item_id)
        if item is None or item.metadata_status is MetadataStatus.LOADING:
            return
        original = item.original_metadata or BookMetadata()
        current = item.effective_metadata
        dialog = MetadataDialog(item.source_path.name, original, current, self)
        if dialog.exec() != MetadataDialog.DialogCode.Accepted:
            return
        edited = dialog.saved_metadata
        if edited is None:
            return

        if edited.cover_path == original.cover_path:
            self._metadata_service.clear_replacement_cover(item_id)
        elif edited.cover_path is not None and edited.cover_path != current.cover_path:
            try:
                stored_cover = self._metadata_service.store_replacement_cover(
                    item_id, edited.cover_path
                )
            except MetadataError as exc:
                self._show_warning(str(exc))
                return
            edited = replace(edited, cover_path=stored_cover)

        item.metadata_overrides = MetadataOverrides.between(original, edited)
        self._sync_row(item_id)

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
    def _retry_item(self, item_id: str) -> None:
        if not self._batch_active and self._queue.retry(item_id):
            self._sync_row(item_id)
            self._update_queue_ui()

    @Slot()
    def _retry_failed(self) -> None:
        if self._batch_active:
            return
        for item_id in self._queue.retry_failed():
            self._sync_row(item_id)
        self._update_queue_ui()

    @Slot(str)
    def _remove_item(self, item_id: str) -> None:
        if self._batch_active or not self._queue.remove(item_id):
            return
        self._cancel_metadata_item(item_id)
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
            self._cancel_metadata_item(item_id)
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
        candidates = tuple(
            item for item in self._queue.items if item.status is QueueStatus.READY
        )
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

        for item in candidates:
            item.error_message = ""
            item.log = ""
            item.progress = None
            item.result_path = None

        output_folder = Path(self._output_folder.text()).expanduser()
        policy = self._selected_overwrite_policy()
        preflight = preflight_batch(
            self._converter,
            candidates,
            output_folder,
            policy,
            self._ask_overwrite,
        )
        for issue in preflight.issues:
            self._apply_preflight_issue(issue)
        if preflight.batch_cancelled:
            self._update_queue_ui()
            return

        for job in preflight.jobs:
            item = self._queue.get(job.item_id)
            if item is not None:
                item.status = QueueStatus.WAITING
                self._sync_row(item.item_id)
        if not preflight.jobs:
            self._update_queue_ui()
            return

        self._batch_active = True
        self._batch_cancel_requested = False
        self._current_position = 0
        self._current_total = len(preflight.jobs)
        self._progress.setRange(0, 0)
        self._progress.setFormat("")
        self._progress.show()
        self._set_batch_locked(True)
        self._summary.setText(f"Preparing {len(preflight.jobs)} book(s)")

        self._thread = QThread(self)
        self._cancellation = BatchCancellation()
        self._worker = BatchConversionWorker(
            self._converter,
            preflight.jobs,
            output_folder.resolve(),
            self._cancellation,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.item_started.connect(self._item_started)
        self._worker.item_progress.connect(self._item_progress)
        self._worker.item_log_updated.connect(self._item_log_updated)
        self._worker.item_completed.connect(self._item_completed)
        self._worker.item_failed.connect(self._item_failed)
        self._worker.item_cancelled.connect(self._item_cancelled)
        self._worker.finished.connect(self._batch_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread_finished)
        self._thread.start()

    def _apply_preflight_issue(self, issue: PreflightIssue) -> None:
        item = self._queue.get(issue.item_id)
        if item is None:
            return
        item.status = issue.status
        item.result_path = None
        item.progress = None
        item.error_message = issue.message
        item.log = issue.message
        self._sync_row(item.item_id)

    def _selected_overwrite_policy(self) -> OverwritePolicy:
        try:
            return OverwritePolicy(str(self._overwrite_combo.currentData()))
        except ValueError:
            return OverwritePolicy.ASK

    def _ask_overwrite(self, output_path: Path) -> OverwriteDecision:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("Output file exists")
        dialog.setText(output_path.name)
        dialog.setInformativeText(
            "Choose whether to replace this output, skip the book, or stop the batch."
        )
        replace_button = dialog.addButton(
            "Replace", QMessageBox.ButtonRole.AcceptRole
        )
        skip_button = dialog.addButton("Skip", QMessageBox.ButtonRole.RejectRole)
        cancel_button = dialog.addButton(
            "Cancel batch", QMessageBox.ButtonRole.DestructiveRole
        )
        dialog.setDefaultButton(skip_button)
        dialog.exec()
        if dialog.clickedButton() is replace_button:
            return OverwriteDecision.REPLACE
        if dialog.clickedButton() is cancel_button:
            return OverwriteDecision.CANCEL_BATCH
        return OverwriteDecision.SKIP

    @Slot(str, int, int)
    def _item_started(self, item_id: str, position: int, total: int) -> None:
        item = self._queue.get(item_id)
        if item is None:
            return
        self._current_position = position
        self._current_total = total
        item.status = QueueStatus.CONVERTING
        item.error_message = ""
        item.progress = None
        item.log = ""
        self._progress.setRange(0, 0)
        self._progress.setFormat("")
        self._cancel_current_button.setEnabled(not self._batch_cancel_requested)
        self._sync_row(item_id)
        self._summary.setText(f"Converting {position} of {total}")

    @Slot(str, int)
    def _item_progress(self, item_id: str, progress: int) -> None:
        item = self._queue.get(item_id)
        if item is None or item.status is not QueueStatus.CONVERTING:
            return
        item.progress = progress
        self._progress.setRange(0, 100)
        self._progress.setValue(progress)
        self._progress.setFormat("Current book · %p%")
        self._summary.setText(
            f"Converting {self._current_position} of {self._current_total} · {progress}%"
        )
        self._sync_row(item_id)

    @Slot(str, str)
    def _item_log_updated(self, item_id: str, log: str) -> None:
        item = self._queue.get(item_id)
        if item is None:
            return
        item.log = log
        self._sync_row(item_id)

    @Slot(str, object)
    def _item_completed(self, item_id: str, result: ConversionResult) -> None:
        item = self._queue.get(item_id)
        if item is None:
            return
        item.status = QueueStatus.COMPLETED
        item.result_path = result.output_path.resolve()
        item.error_message = ""
        item.progress = None
        item.log = result.log
        self._sync_row(item_id)

    @Slot(str, str, str)
    def _item_failed(self, item_id: str, message: str, log: str) -> None:
        item = self._queue.get(item_id)
        if item is not None:
            self._set_terminal_item(item, QueueStatus.FAILED, message, log)

    @Slot(str, str, str)
    def _item_cancelled(self, item_id: str, message: str, log: str) -> None:
        item = self._queue.get(item_id)
        if item is not None:
            self._set_terminal_item(item, QueueStatus.CANCELLED, message, log)

    def _set_terminal_item(
        self, item: QueueItem, status: QueueStatus, message: str, log: str
    ) -> None:
        item.status = status
        item.result_path = None
        item.progress = None
        item.error_message = message
        item.log = log or message
        self._sync_row(item.item_id)

    @Slot(int, int, int)
    def _batch_finished(
        self, _completed_count: int, _failed_count: int, _cancelled_count: int
    ) -> None:
        self._batch_active = False
        self._progress.hide()
        self._set_batch_locked(False)
        self._update_queue_ui()

    @Slot()
    def _cancel_current(self) -> None:
        if not self._batch_active or self._cancellation is None:
            return
        self._cancellation.cancel_current()
        self._cancel_current_button.setDisabled(True)
        self._summary.setText("Cancelling current conversion...")

    @Slot()
    def _cancel_batch(self) -> None:
        if not self._batch_active or self._cancellation is None:
            return
        self._batch_cancel_requested = True
        self._cancellation.cancel_batch()
        self._cancel_current_button.setDisabled(True)
        self._cancel_batch_button.setDisabled(True)
        self._summary.setText("Cancelling batch...")

    @Slot()
    def _thread_finished(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self._cancellation = None
        if self._closing_after_cancel:
            QTimer.singleShot(0, self.close)

    def _sync_row(self, item_id: str) -> None:
        item = self._queue.get(item_id)
        row = self._row_widgets.get(item_id)
        if item is not None and row is not None:
            row.update_item(item, batch_locked=self._batch_active)

    def _set_batch_locked(self, locked: bool) -> None:
        self._drop_area.setDisabled(locked)
        self._add_books_action.setDisabled(locked)
        has_retryable = any(
            item.status in _RETRYABLE_STATUSES for item in self._queue.items
        )
        self._retry_failed_button.setVisible(has_retryable)
        self._retry_failed_button.setEnabled(has_retryable and not locked)
        self._clear_button.setDisabled(locked or len(self._queue) == 0)
        self._set_all_combo.setDisabled(locked or len(self._queue) == 0)
        self._apply_all_button.setDisabled(locked or len(self._queue) == 0)
        self._overwrite_combo.setDisabled(locked or len(self._queue) == 0)
        self._browse_folder_button.setDisabled(locked)
        self._convert_button.setDisabled(locked)
        self._convert_action.setDisabled(locked)
        self._cancel_current_button.setVisible(locked)
        self._cancel_batch_button.setVisible(locked)
        self._cancel_current_button.setEnabled(locked and not self._batch_cancel_requested)
        self._cancel_batch_button.setEnabled(locked and not self._batch_cancel_requested)
        for item in self._queue.items:
            self._sync_row(item.item_id)

    def _update_queue_ui(self) -> None:
        count = len(self._queue)
        self._queue_heading.setText(f"Conversion queue  ·  {count}")
        self._empty_queue.setVisible(count == 0)
        self._queue_scroll.setVisible(count > 0)
        self._drop_area.set_compact(count > 0)

        has_ready = any(item.status is QueueStatus.READY for item in self._queue.items)
        has_retryable = any(
            item.status in _RETRYABLE_STATUSES for item in self._queue.items
        )
        can_convert = (
            count > 0
            and has_ready
            and bool(self._output_folder.text())
            and self._converter.calibre_available
            and not self._batch_active
        )
        self._convert_button.setEnabled(can_convert)
        self._convert_action.setEnabled(can_convert)
        self._clear_button.setEnabled(count > 0 and not self._batch_active)
        self._clear_button.setVisible(count > 0)
        self._retry_failed_button.setEnabled(has_retryable and not self._batch_active)
        self._retry_failed_button.setVisible(has_retryable)
        self._set_all_combo.setEnabled(count > 0 and not self._batch_active)
        self._apply_all_button.setEnabled(count > 0 and not self._batch_active)
        self._overwrite_combo.setEnabled(count > 0 and not self._batch_active)
        self._browse_folder_button.setEnabled(not self._batch_active)
        self._drop_area.setEnabled(not self._batch_active)
        self._add_books_action.setEnabled(not self._batch_active)
        self._cancel_current_button.setVisible(self._batch_active)
        self._cancel_batch_button.setVisible(self._batch_active)

        if not self._batch_active:
            self._summary.setText(self._idle_summary())

    def _idle_summary(self) -> str:
        items = self._queue.items
        count = len(items)
        if count == 0:
            return "0 books • Ready"
        completed = sum(item.status is QueueStatus.COMPLETED for item in items)
        if completed == count:
            noun = "book" if count == 1 else "books"
            return f"{count} {noun} converted successfully"

        labels = (
            (QueueStatus.COMPLETED, "completed"),
            (QueueStatus.FAILED, "failed"),
            (QueueStatus.CANCELLED, "cancelled"),
            (QueueStatus.SKIPPED, "skipped"),
            (QueueStatus.READY, "ready"),
            (QueueStatus.WAITING, "waiting"),
        )
        parts = [
            f"{amount} {label}"
            for status, label in labels
            if (amount := sum(item.status is status for item in items))
        ]
        return " • ".join(parts)

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
            answer = QMessageBox.question(
                self,
                "Conversion in progress",
                "A conversion is still running.\n\nCancel the batch and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._closing_after_cancel = True
                self._cancel_batch()
            event.ignore()
            return
        self._save_settings()
        self._shutdown_metadata()
        super().closeEvent(event)
