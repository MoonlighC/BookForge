from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from bookforge.core.converter import ConversionResult, ConverterService
from bookforge.core.metadata import MetadataStatus
from bookforge.core.queue import QueueStatus
from bookforge.ui.drop_area import DropArea
from bookforge.ui.batch_worker import BatchCancellation
from bookforge.ui.main_window import MainWindow


class AvailableAdapter:
    is_available = True
    executable = Path(__file__)


class UnavailableMetadataService:
    available = False

    def __init__(self) -> None:
        self.cleaned: list[str] = []
        self.closed = False

    def cleanup_item(self, item_id: str) -> None:
        self.cleaned.append(item_id)

    def clear_replacement_cover(self, _item_id: str) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class MainWindowQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        converter = ConverterService(AvailableAdapter())  # type: ignore[arg-type]
        self.metadata_service = UnavailableMetadataService()
        self.window = MainWindow(
            converter, metadata_service=self.metadata_service  # type: ignore[arg-type]
        )
        self.window._show_warning = lambda _message: None  # type: ignore[method-assign]

    def tearDown(self) -> None:
        self.window.close()

    def test_multiple_files_create_independent_scrollable_rows(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = [root / "First.epub", root / "Second.fb2"]
            for path in paths:
                path.write_bytes(b"book")

            self.assertEqual(self.window._drop_area._title.text(), "Drop books here")
            self.window._add_files(paths)
            first, second = self.window._queue.items
            self.window._set_item_output_format(first.item_id, "pdf")

            self.assertEqual(len(self.window._row_widgets), 2)
            self.assertTrue(self.window._queue_scroll.widgetResizable())
            self.assertEqual(first.output_format, "pdf")
            self.assertEqual(second.output_format, "azw3")
            self.assertEqual(self.window._output_folder.text(), str(root))
            self.assertTrue(self.window._convert_button.isEnabled())
            self.assertEqual(
                self.window._drop_area._title.text(), "Drop more books here"
            )

    def test_metadata_failure_does_not_block_conversion(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "Book.epub"
            source.write_bytes(b"book")

            self.window._add_files([source])

            item = self.window._queue.items[0]
            item.metadata_status = MetadataStatus.LOADING
            self.window._metadata_failed(item.item_id, "Calibre could not read it")
            self.assertEqual(item.metadata_status.value, "Unavailable")
            self.assertTrue(self.window._convert_button.isEnabled())
            self.assertEqual(
                self.window._row_widgets[item.item_id]._metadata.toolTip(),
                "Calibre could not read it",
            )

    def test_remove_and_clear_clean_only_their_metadata_resources(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            sources = [root / "First.epub", root / "Second.fb2"]
            for source in sources:
                source.write_bytes(b"book")
            self.window._add_files(sources)
            first_id, second_id = (
                item.item_id for item in self.window._queue.items
            )

            self.window._remove_item(first_id)
            self.assertEqual(self.metadata_service.cleaned, [first_id])
            self.assertIsNotNone(self.window._queue.get(second_id))

            self.window._clear_queue()
            self.assertEqual(
                self.metadata_service.cleaned, [first_id, second_id]
            )
            self.assertEqual(len(self.window._queue), 0)

    def test_global_format_and_duplicate_skip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = [root / "First.epub", root / "Second.fb2"]
            for path in paths:
                path.write_bytes(b"book")
            self.window._add_files(paths)
            self.window._add_files([paths[0]])
            self.window._set_all_combo.setCurrentIndex(
                self.window._set_all_combo.findData("txt")
            )
            self.window._apply_format_to_all()

            self.assertEqual(len(self.window._queue), 2)
            self.assertEqual(
                [item.output_format for item in self.window._queue.items],
                ["txt", "txt"],
            )

    def test_drop_area_extracts_multiple_local_files(self) -> None:
        urls = [
            QUrl.fromLocalFile("C:/Books/One.epub"),
            QUrl.fromLocalFile("C:/Books/Two.pdf"),
        ]
        self.assertEqual(len(DropArea._local_files_from_urls(urls)), 2)

    def test_drop_area_browse_signal_keeps_multi_file_picker(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = [root / "First.epub", root / "Second.pdf"]
            for path in paths:
                path.write_bytes(b"book")
            with patch(
                "bookforge.ui.main_window.QFileDialog.getOpenFileNames",
                return_value=([str(path) for path in paths], ""),
            ):
                self.window._drop_area.browse_requested.emit()
            self.assertEqual(len(self.window._queue), 2)

    def test_item_states_and_batch_summary_update_independently(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = [root / "First.epub", root / "Second.fb2"]
            for path in paths:
                path.write_bytes(b"book")
            self.window._add_files(paths)
            first, second = self.window._queue.items
            first.status = QueueStatus.WAITING
            second.status = QueueStatus.WAITING
            self.window._batch_active = True

            self.window._item_started(first.item_id, 1, 2)
            result_path = root / "First.azw3"
            result_path.write_bytes(b"converted")
            self.window._item_completed(
                first.item_id, ConversionResult(result_path, "")
            )
            self.window._item_started(second.item_id, 2, 2)
            self.window._item_failed(second.item_id, "Calibre failed", "technical log")
            self.window._batch_finished(1, 1, 0)

            self.assertEqual(first.status, QueueStatus.COMPLETED)
            self.assertEqual(second.status, QueueStatus.FAILED)
            self.assertEqual(second.error_message, "Calibre failed")
            self.assertEqual(self.window._summary.text(), "1 completed • 1 failed")

    def test_progress_log_and_control_lock_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "Book.epub"
            source.write_bytes(b"book")
            self.window._add_files([source])
            item = self.window._queue.items[0]
            item.status = QueueStatus.WAITING
            self.window._batch_active = True
            self.window._set_batch_locked(True)

            self.assertFalse(self.window._drop_area.isEnabled())
            self.assertFalse(self.window._overwrite_combo.isEnabled())
            self.assertTrue(self.window._cancel_batch_button.isEnabled())

            self.window._item_started(item.item_id, 1, 1)
            self.window._item_progress(item.item_id, 37)
            self.window._item_log_updated(item.item_id, "37% converting\n")
            row = self.window._row_widgets[item.item_id]
            self.assertEqual(item.progress, 37)
            self.assertEqual(item.log, "37% converting\n")
            self.assertEqual(row._item_progress.value(), 37)
            self.assertIn("37%", self.window._summary.text())

            self.window._batch_finished(0, 0, 0)
            self.assertTrue(self.window._drop_area.isEnabled())
            self.assertTrue(self.window._overwrite_combo.isEnabled())

    def test_retry_action_resets_cancelled_item(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "Book.epub"
            source.write_bytes(b"book")
            self.window._add_files([source])
            item = self.window._queue.items[0]
            self.assertTrue(self.window._retry_failed_button.isHidden())
            item.progress = 20

            self.window._item_cancelled(
                item.item_id, "Conversion cancelled.", "partial output"
            )
            self.assertEqual(item.status, QueueStatus.CANCELLED)
            self.window._update_queue_ui()
            self.assertFalse(self.window._retry_failed_button.isHidden())

            self.window._retry_item(item.item_id)

            self.assertEqual(item.status, QueueStatus.READY)
            self.assertEqual(item.error_message, "")
            self.assertEqual(item.log, "")
            self.assertIsNone(item.progress)
            self.assertTrue(self.window._retry_failed_button.isHidden())

    def test_close_decline_keeps_window_and_confirm_requests_batch_cancel(self) -> None:
        class RunningThread:
            @staticmethod
            def isRunning() -> bool:
                return True

        self.window._thread = RunningThread()  # type: ignore[assignment]
        self.window._batch_active = True
        self.window._cancellation = BatchCancellation()
        declined = QCloseEvent()
        with patch.object(
            QMessageBox,
            "question",
            return_value=QMessageBox.StandardButton.No,
        ):
            self.window.closeEvent(declined)
        self.assertFalse(declined.isAccepted())
        self.assertFalse(self.window._cancellation.batch_requested)

        confirmed = QCloseEvent()
        with patch.object(
            QMessageBox,
            "question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window.closeEvent(confirmed)
        self.assertFalse(confirmed.isAccepted())
        self.assertTrue(self.window._closing_after_cancel)
        self.assertTrue(self.window._cancellation.batch_requested)
        self.window._thread = None
        self.window._batch_active = False
        self.window._closing_after_cancel = False


if __name__ == "__main__":
    unittest.main()
