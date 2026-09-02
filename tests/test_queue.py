from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bookforge.core.metadata import BookMetadata, MetadataOverrides
from bookforge.core.queue import ConversionQueue, QueueStatus, format_file_size


class ConversionQueueTests(unittest.TestCase):
    def test_metadata_overrides_are_isolated_per_item(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first_source = root / "first.epub"
            second_source = root / "second.epub"
            first_source.write_bytes(b"first")
            second_source.write_bytes(b"second")
            queue = ConversionQueue()
            first, second = queue.add_paths([first_source, second_source]).added
            first.original_metadata = BookMetadata(title="First")
            second.original_metadata = BookMetadata(title="Second")
            first.metadata_overrides = MetadataOverrides.between(
                first.original_metadata, BookMetadata(title="Edited first")
            )

            self.assertEqual(first.effective_metadata.title, "Edited first")
            self.assertEqual(second.effective_metadata.title, "Second")
            self.assertFalse(second.metadata_overrides.is_edited)

    def test_metadata_overrides_survive_retry(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "book.epub"
            source.write_bytes(b"book")
            queue = ConversionQueue()
            item = queue.add_paths([source]).added[0]
            item.metadata_overrides = MetadataOverrides.between(
                BookMetadata(title="Original title"),
                BookMetadata(title="Edited title"),
            )
            item.status = QueueStatus.FAILED

            self.assertTrue(queue.retry(item.item_id))
            self.assertEqual(item.effective_metadata.title, "Edited title")
            self.assertTrue(item.metadata_overrides.is_edited)

    def test_adds_mixed_formats_and_uses_predictable_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            epub = root / "Novel.epub"
            azw3 = root / "Kindle.azw3"
            docx = root / "Notes.docx"
            for path in (epub, azw3, docx):
                path.write_bytes(b"book")

            queue = ConversionQueue()
            result = queue.add_paths([epub, azw3, docx])

            self.assertEqual(len(result.added), 3)
            self.assertEqual(
                [item.input_format for item in queue.items],
                ["epub", "azw3", "docx"],
            )
            self.assertEqual(
                [item.output_format for item in queue.items],
                ["azw3", "epub", "azw3"],
            )

    def test_skips_duplicate_physical_source(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "Book.epub"
            source.write_bytes(b"book")
            queue = ConversionQueue()

            first = queue.add_paths([source])
            second = queue.add_paths([source, source.resolve()])

            self.assertEqual(len(first.added), 1)
            self.assertEqual(second.duplicate_count, 2)
            self.assertEqual(len(queue), 1)

    def test_output_formats_remain_independent(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = [root / "One.epub", root / "Two.fb2"]
            for path in paths:
                path.write_bytes(b"book")
            queue = ConversionQueue()
            queue.add_paths(paths)
            first, second = queue.items

            queue.set_output_format(first.item_id, "pdf")

            self.assertEqual(first.output_format, "pdf")
            self.assertEqual(second.output_format, "azw3")

    def test_running_item_cannot_be_removed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "Book.epub"
            source.write_bytes(b"book")
            queue = ConversionQueue()
            item = queue.add_paths([source]).added[0]
            item.status = QueueStatus.CONVERTING

            self.assertFalse(queue.remove(item.item_id))
            self.assertEqual(len(queue), 1)

    def test_formats_human_readable_file_sizes(self) -> None:
        self.assertEqual(format_file_size(824 * 1024), "824 KB")
        self.assertEqual(format_file_size(round(1.2 * 1024 * 1024)), "1.2 MB")
        self.assertEqual(format_file_size(14 * 1024 * 1024), "14.0 MB")

    def test_retry_resets_failed_cancelled_and_skipped_state(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = [root / f"{name}.epub" for name in ("Failed", "Cancelled", "Skipped")]
            for path in paths:
                path.write_bytes(b"book")
            queue = ConversionQueue()
            queue.add_paths(paths)
            statuses = (
                QueueStatus.FAILED,
                QueueStatus.CANCELLED,
                QueueStatus.SKIPPED,
            )
            for item, status in zip(queue.items, statuses, strict=True):
                item.status = status
                item.error_message = "old error"
                item.log = "old log"
                item.progress = 42
                item.result_path = root / "old.azw3"

            retried = queue.retry_failed()

            self.assertEqual(len(retried), 3)
            for item in queue.items:
                self.assertEqual(item.status, QueueStatus.READY)
                self.assertEqual(item.error_message, "")
                self.assertEqual(item.log, "")
                self.assertIsNone(item.progress)
                self.assertIsNone(item.result_path)


if __name__ == "__main__":
    unittest.main()
