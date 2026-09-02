from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bookforge.core.batch import (
    OverwriteDecision,
    OverwritePolicy,
    preflight_batch,
)
from bookforge.core.converter import ConverterService
from bookforge.core.queue import ConversionQueue, QueueStatus


class AvailableAdapter:
    is_available = True
    executable = Path(__file__)


class BatchPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.converter = ConverterService(AvailableAdapter())  # type: ignore[arg-type]

    def _queue_one(self, root: Path, name: str = "Book.epub"):
        source = root / name
        source.write_bytes(b"book")
        queue = ConversionQueue()
        item = queue.add_paths([source]).added[0]
        return item

    def test_skip_all_marks_existing_output_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            item = self._queue_one(root)
            (root / "Book.azw3").write_bytes(b"existing")
            result = preflight_batch(
                self.converter, (item,), root, OverwritePolicy.SKIP_ALL
            )
            self.assertFalse(result.jobs)
            self.assertEqual(result.issues[0].status, QueueStatus.SKIPPED)

    def test_replace_all_authorizes_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            item = self._queue_one(root)
            (root / "Book.azw3").write_bytes(b"existing")
            result = preflight_batch(
                self.converter, (item,), root, OverwritePolicy.REPLACE_ALL
            )
            self.assertEqual(len(result.jobs), 1)
            self.assertTrue(result.jobs[0].overwrite)

    def test_ask_uses_replace_and_skip_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            item = self._queue_one(root)
            (root / "Book.azw3").write_bytes(b"existing")
            replaced = preflight_batch(
                self.converter,
                (item,),
                root,
                OverwritePolicy.ASK,
                lambda _path: OverwriteDecision.REPLACE,
            )
            skipped = preflight_batch(
                self.converter,
                (item,),
                root,
                OverwritePolicy.ASK,
                lambda _path: OverwriteDecision.SKIP,
            )
            self.assertTrue(replaced.jobs[0].overwrite)
            self.assertEqual(skipped.issues[0].status, QueueStatus.SKIPPED)

    def test_ask_can_cancel_preflight_batch(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = self._queue_one(root, "First.epub")
            second = self._queue_one(root, "Second.epub")
            (root / "Second.azw3").write_bytes(b"existing")
            result = preflight_batch(
                self.converter,
                (first, second),
                root,
                OverwritePolicy.ASK,
                lambda _path: OverwriteDecision.CANCEL_BATCH,
            )
            self.assertTrue(result.batch_cancelled)
            self.assertFalse(result.jobs)
            self.assertEqual(
                [issue.status for issue in result.issues],
                [QueueStatus.CANCELLED, QueueStatus.CANCELLED],
            )

    def test_internal_output_collision_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            left = root / "left"
            right = root / "right"
            output = root / "output"
            left.mkdir()
            right.mkdir()
            output.mkdir()
            first = self._queue_one(left, "Book.epub")
            second = self._queue_one(right, "Book.fb2")
            result = preflight_batch(
                self.converter,
                (first, second),
                output,
                OverwritePolicy.REPLACE_ALL,
            )
            self.assertEqual(len(result.jobs), 1)
            self.assertEqual(result.issues[0].item_id, second.item_id)
            self.assertEqual(result.issues[0].status, QueueStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
