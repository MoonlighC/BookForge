from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bookforge.core.queue import ConversionQueue, QueueStatus, format_file_size


class ConversionQueueTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
