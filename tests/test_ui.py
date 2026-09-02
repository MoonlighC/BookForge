from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

from bookforge.core.converter import ConversionResult, ConverterService
from bookforge.core.queue import QueueStatus
from bookforge.ui.drop_area import DropArea
from bookforge.ui.main_window import MainWindow


class AvailableAdapter:
    is_available = True
    executable = Path(__file__)


class MainWindowQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        converter = ConverterService(AvailableAdapter())  # type: ignore[arg-type]
        self.window = MainWindow(converter)
        self.window._show_warning = lambda _message: None  # type: ignore[method-assign]

    def tearDown(self) -> None:
        self.window.close()

    def test_multiple_files_create_independent_scrollable_rows(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = [root / "First.epub", root / "Second.fb2"]
            for path in paths:
                path.write_bytes(b"book")

            self.window._add_files(paths)
            first, second = self.window._queue.items
            self.window._set_item_output_format(first.item_id, "pdf")

            self.assertEqual(len(self.window._row_widgets), 2)
            self.assertTrue(self.window._queue_scroll.widgetResizable())
            self.assertEqual(first.output_format, "pdf")
            self.assertEqual(second.output_format, "azw3")
            self.assertEqual(self.window._output_folder.text(), str(root))
            self.assertTrue(self.window._convert_button.isEnabled())

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
            self.window._item_failed(second.item_id, "Calibre failed")
            self.window._batch_finished(1, 1)

            self.assertEqual(first.status, QueueStatus.COMPLETED)
            self.assertEqual(second.status, QueueStatus.FAILED)
            self.assertEqual(second.error_message, "Calibre failed")
            self.assertEqual(self.window._summary.text(), "1 completed • 1 failed")


if __name__ == "__main__":
    unittest.main()
