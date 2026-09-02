"""Main BookForge window."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, QUrl, Signal, Slot
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
    QVBoxLayout,
    QWidget,
)

from bookforge.core.converter import (
    OUTPUT_FORMATS,
    ConversionError,
    ConversionResult,
    ConverterService,
)
from bookforge.ui.drop_area import DropArea


LOGGER = logging.getLogger(__name__)


class ConversionWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        converter: ConverterService,
        input_path: Path,
        output_folder: Path,
        output_format: str,
    ) -> None:
        super().__init__()
        self._converter = converter
        self._input_path = input_path
        self._output_folder = output_folder
        self._output_format = output_format

    @Slot()
    def run(self) -> None:
        try:
            result = self._converter.convert(
                self._input_path,
                self._output_folder,
                self._output_format,
            )
        except ConversionError as exc:
            LOGGER.warning("Conversion failed: %s", exc, exc_info=True)
            self.failed.emit(str(exc))
        except Exception:
            LOGGER.exception("Unexpected conversion error")
            self.failed.emit("An unexpected error occurred while converting the book.")
        else:
            self.completed.emit(result)


class MainWindow(QMainWindow):
    def __init__(self, converter: ConverterService | None = None) -> None:
        super().__init__()
        self._converter = converter or ConverterService()
        self._input_path: Path | None = None
        self._output_folder_is_automatic = True
        self._result_path: Path | None = None
        self._thread: QThread | None = None
        self._worker: ConversionWorker | None = None

        self.setWindowTitle("BookForge")
        self.resize(800, 820)
        self.setMinimumSize(700, 760)
        self._build_ui()
        self._show_calibre_state()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(44, 26, 44, 24)
        root.setSpacing(12)

        title = QLabel("BookForge")
        title.setObjectName("appTitle")
        subtitle = QLabel("E-book converter for Kindle & more")
        subtitle.setObjectName("subtitle")
        header = QVBoxLayout()
        header.setSpacing(3)
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        self._warning_banner = QLabel()
        self._warning_banner.setObjectName("warningBanner")
        self._warning_banner.setWordWrap(True)
        self._warning_banner.hide()
        root.addWidget(self._warning_banner)

        self._drop_area = DropArea()
        self._drop_area.browse_requested.connect(self._browse_input)
        self._drop_area.file_selected.connect(self._select_input)
        self._drop_area.file_rejected.connect(self._show_warning)
        root.addWidget(self._drop_area)

        selected_label = QLabel("Selected file")
        selected_label.setObjectName("sectionLabel")
        self._selected_file = QLabel("No EPUB selected")
        self._selected_file.setObjectName("selectedFile")
        self._selected_file.setToolTip("No EPUB selected")
        root.addWidget(selected_label)
        root.addWidget(self._selected_file)

        options_row = QHBoxLayout()
        options_row.setSpacing(18)

        format_column = QVBoxLayout()
        format_column.setSpacing(7)
        format_label = QLabel("Convert to")
        format_label.setObjectName("sectionLabel")
        self._format_combo = QComboBox()
        for output_format in OUTPUT_FORMATS:
            self._format_combo.addItem(output_format.label, output_format.extension)
        self._format_combo.setMinimumWidth(135)
        self._format_combo.currentIndexChanged.connect(self._update_format_ui)
        self._format_description = QLabel()
        self._format_description.setObjectName("formatDescription")
        format_column.addWidget(format_label)
        format_column.addWidget(self._format_combo)
        format_column.addWidget(self._format_description)

        folder_column = QVBoxLayout()
        folder_column.setSpacing(7)
        folder_label = QLabel("Output folder")
        folder_label.setObjectName("sectionLabel")
        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self._output_folder = QLineEdit()
        self._output_folder.setReadOnly(True)
        self._output_folder.setPlaceholderText("Select an EPUB first")
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_output_folder)
        folder_row.addWidget(self._output_folder, 1)
        folder_row.addWidget(browse_button)
        folder_column.addWidget(folder_label)
        folder_column.addLayout(folder_row)

        options_row.addLayout(format_column)
        options_row.addLayout(folder_column, 1)
        root.addLayout(options_row)

        root.addStretch(1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self._convert_button = QPushButton("Convert to AZW3")
        self._convert_button.setObjectName("primaryButton")
        self._convert_button.clicked.connect(self._start_conversion)
        button_row.addWidget(self._convert_button)
        button_row.addStretch(1)
        root.addLayout(button_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setTextVisible(False)
        self._progress.hide()
        root.addWidget(self._progress)

        self._status = QLabel("Status: Ready")
        self._status.setObjectName("statusLabel")
        root.addWidget(self._status)

        self._result_panel = QFrame()
        self._result_panel.setObjectName("resultPanel")
        result_layout = QVBoxLayout(self._result_panel)
        result_layout.setContentsMargins(18, 16, 18, 16)
        result_layout.setSpacing(8)

        result_title = QLabel("Conversion completed")
        result_title.setObjectName("resultTitle")
        self._result_name = QLabel()
        self._result_name.setObjectName("resultName")
        self._result_location = QLabel()
        self._result_location.setObjectName("resultLocation")
        self._result_location.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._result_location.setWordWrap(True)

        result_actions = QHBoxLayout()
        self._open_file_button = QPushButton("Open file")
        self._open_folder_button = QPushButton("Open folder")
        self._open_file_button.clicked.connect(self._open_result_file)
        self._open_folder_button.clicked.connect(self._open_result_folder)
        result_actions.addWidget(self._open_file_button)
        result_actions.addWidget(self._open_folder_button)
        result_actions.addStretch(1)

        result_layout.addWidget(result_title)
        result_layout.addWidget(self._result_name)
        result_layout.addWidget(self._result_location)
        result_layout.addLayout(result_actions)
        root.addWidget(self._result_panel)

        self._update_format_ui(self._format_combo.currentIndex())
        self._clear_result()

    def _show_calibre_state(self) -> None:
        if self._converter.calibre_available:
            executable = self._converter.calibre_executable
            self._warning_banner.hide()
            if executable is not None:
                self._warning_banner.setToolTip(str(executable))
            return

        self._warning_banner.setText(
            "Calibre was not found. BookForge uses Calibre's ebook-convert engine. "
            "Please install Calibre before converting books."
        )
        self._warning_banner.show()
        self._status.setText("Status: Calibre not found")

    @Slot()
    def _browse_input(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select an EPUB",
            str(self._input_path.parent if self._input_path else Path.home()),
            "EPUB books (*.epub)",
        )
        if filename:
            self._select_input(Path(filename))

    @Slot(object)
    def _select_input(self, path: Path) -> None:
        if path.suffix.lower() != ".epub" or not path.is_file():
            self._show_warning("Please select an existing EPUB file.")
            return

        self._input_path = path.resolve()
        self._clear_result()
        self._selected_file.setText(self._input_path.name)
        self._selected_file.setToolTip(str(self._input_path))
        if self._output_folder_is_automatic:
            self._output_folder.setText(str(self._input_path.parent))
        self._status.setText("Status: Ready")
        if not self._converter.calibre_available:
            self._status.setText("Status: Ready — Calibre required")

    @Slot()
    def _browse_output_folder(self) -> None:
        start_folder = self._output_folder.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(
            self, "Select output folder", start_folder
        )
        if folder:
            self._output_folder.setText(folder)
            self._output_folder_is_automatic = False

    @Slot()
    def _start_conversion(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        if self._input_path is None:
            self._show_warning("Select an EPUB file before converting.")
            return
        if not self._input_path.is_file():
            self._show_warning("The selected EPUB file no longer exists.")
            return
        if not self._output_folder.text():
            self._show_warning("Select an output folder before converting.")
            return
        if not self._converter.calibre_available:
            self._show_warning(
                "Calibre was not found. Install Calibre before converting books."
            )
            return

        output_folder = Path(self._output_folder.text())
        output_format = self._selected_output_format()
        try:
            output_path = self._converter.output_path_for(
                self._input_path, output_folder, output_format
            )
        except ConversionError as exc:
            self._show_warning(str(exc))
            return

        if output_path.exists():
            if not self._confirm_replace(output_path):
                return

        self._clear_result()
        self._set_converting(True)
        self._thread = QThread(self)
        self._worker = ConversionWorker(
            self._converter,
            self._input_path,
            output_folder,
            output_format,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.completed.connect(self._conversion_completed)
        self._worker.failed.connect(self._conversion_failed)
        self._worker.completed.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread_finished)
        self._thread.start()

    @Slot(object)
    def _conversion_completed(self, result: ConversionResult) -> None:
        self._set_converting(False)
        self._status.setText(f"Status: Conversion completed — {result.output_path.name}")
        self._show_result(result.output_path)

    @Slot(str)
    def _conversion_failed(self, message: str) -> None:
        self._set_converting(False)
        self._status.setText("Status: Conversion failed")
        QMessageBox.critical(self, "Conversion failed", message)

    @Slot()
    def _thread_finished(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None

    def _set_converting(self, converting: bool) -> None:
        self._convert_button.setDisabled(converting)
        self._drop_area.setDisabled(converting)
        self._format_combo.setDisabled(converting)
        self._progress.setVisible(converting)
        if converting:
            self._status.setText("Status: Converting...")

    @Slot(int)
    def _update_format_ui(self, index: int) -> None:
        if index < 0:
            return
        output_format = OUTPUT_FORMATS[index]
        self._format_description.setText(output_format.description)
        self._convert_button.setText(f"Convert to {output_format.label}")

    def _selected_output_format(self) -> str:
        output_format = self._format_combo.currentData()
        return str(output_format)

    def _confirm_replace(self, output_path: Path) -> bool:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("Replace existing file?")
        dialog.setText(output_path.name)
        dialog.setInformativeText(
            "A file with this name already exists and will be replaced."
        )
        replace_button = dialog.addButton(
            "Replace", QMessageBox.ButtonRole.AcceptRole
        )
        cancel_button = dialog.addButton(
            "Cancel", QMessageBox.ButtonRole.RejectRole
        )
        dialog.setDefaultButton(cancel_button)
        dialog.exec()
        return dialog.clickedButton() is replace_button

    def _show_result(self, output_path: Path) -> None:
        self._result_path = output_path.resolve()
        self._result_name.setText(self._result_path.name)
        self._result_location.setText(str(self._result_path))
        self._result_location.setToolTip(str(self._result_path))
        self._open_file_button.setEnabled(True)
        self._open_folder_button.setEnabled(True)
        self._result_panel.show()

    def _clear_result(self) -> None:
        self._result_path = None
        self._result_name.clear()
        self._result_location.clear()
        self._result_location.setToolTip("")
        self._open_file_button.setEnabled(False)
        self._open_folder_button.setEnabled(False)
        self._result_panel.hide()

    @Slot()
    def _open_result_file(self) -> None:
        if self._result_path is None or not self._result_path.is_file():
            self._show_warning("The converted file is no longer available.")
            return
        self._open_local_path(self._result_path, "file")

    @Slot()
    def _open_result_folder(self) -> None:
        if self._result_path is None or not self._result_path.parent.is_dir():
            self._show_warning("The output folder is no longer available.")
            return
        self._open_local_path(self._result_path.parent, "folder")

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
                "Please wait for the current conversion to finish before closing BookForge.",
            )
            event.ignore()
            return
        super().closeEvent(event)
