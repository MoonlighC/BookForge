from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bookforge.core.converter import ConversionError, ConversionResult
from bookforge.ui.batch_worker import BatchConversionWorker, BatchJob


class RecordingConverter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def convert(
        self,
        source_path: Path,
        output_folder: Path,
        output_format: str,
        *,
        overwrite: bool = False,
    ) -> ConversionResult:
        self.calls.append(source_path.name)
        if source_path.stem == "bad":
            raise ConversionError("Calibre could not convert this book.")
        return ConversionResult(output_folder / f"{source_path.stem}.{output_format}", "")


class BatchConversionWorkerTests(unittest.TestCase):
    def test_processes_in_order_and_continues_after_failure(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            jobs = tuple(
                BatchJob(name, root / f"{name}.epub", "pdf")
                for name in ("first", "bad", "last")
            )
            converter = RecordingConverter()
            worker = BatchConversionWorker(converter, jobs, root)  # type: ignore[arg-type]
            started: list[str] = []
            completed: list[str] = []
            failed: list[str] = []
            summary: list[tuple[int, int]] = []
            worker.item_started.connect(lambda item_id, _n, _t: started.append(item_id))
            worker.item_completed.connect(lambda item_id, _result: completed.append(item_id))
            worker.item_failed.connect(lambda item_id, _message: failed.append(item_id))
            worker.finished.connect(lambda done, errors: summary.append((done, errors)))

            worker.run()

            self.assertEqual(converter.calls, ["first.epub", "bad.epub", "last.epub"])
            self.assertEqual(started, ["first", "bad", "last"])
            self.assertEqual(completed, ["first", "last"])
            self.assertEqual(failed, ["bad"])
            self.assertEqual(summary, [(2, 1)])


if __name__ == "__main__":
    unittest.main()
