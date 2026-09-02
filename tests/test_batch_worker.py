from __future__ import annotations

from pathlib import Path
import tempfile
from threading import Event, Thread
import unittest

from bookforge.core.batch import BatchJob
from bookforge.core.converter import (
    ConversionCancelled,
    ConversionError,
    ConversionResult,
)
from bookforge.ui.batch_worker import BatchConversionWorker


class RecordingConverter:
    def __init__(self, *, emit_output: bool = True) -> None:
        self.calls: list[str] = []
        self.emit_output = emit_output

    def convert(
        self,
        source_path: Path,
        output_folder: Path,
        output_format: str,
        *,
        overwrite: bool = False,
        cancel_event=None,
        on_output=None,
    ) -> ConversionResult:
        self.calls.append(source_path.name)
        if self.emit_output and on_output is not None:
            on_output("Calibre started\n")
            on_output("42% converting\n")
        if source_path.stem == "bad":
            raise ConversionError("Calibre failed.", log="technical failure")
        return ConversionResult(
            output_folder / f"{source_path.stem}.{output_format}",
            "Calibre started\n42% converting\n" if self.emit_output else "",
        )


class BlockingConverter(RecordingConverter):
    def __init__(self) -> None:
        super().__init__()
        self.started = Event()

    def convert(self, source_path: Path, output_folder: Path, output_format: str, **kwargs):
        self.calls.append(source_path.name)
        cancel_event = kwargs["cancel_event"]
        on_output = kwargs["on_output"]
        if source_path.stem == "first":
            on_output("10% waiting for cancellation\n")
            self.started.set()
            cancel_event.wait(timeout=3.0)
            if cancel_event.is_set():
                raise ConversionCancelled("Conversion cancelled.", log="cancelled log")
        return ConversionResult(
            output_folder / f"{source_path.stem}.{output_format}", "done"
        )


class BatchConversionWorkerTests(unittest.TestCase):
    def _jobs(self, root: Path, names: tuple[str, ...]) -> tuple[BatchJob, ...]:
        return tuple(
            BatchJob(name, root / f"{name}.epub", "pdf") for name in names
        )

    def test_processes_in_order_and_continues_after_failure(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            converter = RecordingConverter()
            worker = BatchConversionWorker(
                converter, self._jobs(root, ("first", "bad", "last")), root
            )  # type: ignore[arg-type]
            completed: list[str] = []
            failed: list[tuple[str, str]] = []
            summary: list[tuple[int, int, int]] = []
            worker.item_completed.connect(lambda item_id, _result: completed.append(item_id))
            worker.item_failed.connect(
                lambda item_id, _message, log: failed.append((item_id, log))
            )
            worker.finished.connect(
                lambda done, errors, cancelled: summary.append(
                    (done, errors, cancelled)
                )
            )

            worker.run()

            self.assertEqual(converter.calls, ["first.epub", "bad.epub", "last.epub"])
            self.assertEqual(completed, ["first", "last"])
            self.assertEqual(failed, [("bad", "Calibre started\n42% converting\n")])
            self.assertEqual(summary, [(2, 1, 0)])

    def test_current_only_cancellation_continues_batch(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            converter = BlockingConverter()
            worker = BatchConversionWorker(
                converter, self._jobs(root, ("first", "second")), root
            )  # type: ignore[arg-type]
            cancelled: list[str] = []
            completed: list[str] = []
            worker.item_cancelled.connect(
                lambda item_id, _message, _log: cancelled.append(item_id)
            )
            worker.item_completed.connect(lambda item_id, _result: completed.append(item_id))
            canceller = Thread(
                target=lambda: (converter.started.wait(2.0), worker.cancel_current())
            )
            canceller.start()
            worker.run()
            canceller.join()

            self.assertEqual(cancelled, ["first"])
            self.assertEqual(completed, ["second"])
            self.assertEqual(converter.calls, ["first.epub", "second.epub"])

    def test_batch_cancellation_stops_later_items(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            converter = BlockingConverter()
            worker = BatchConversionWorker(
                converter,
                self._jobs(root, ("first", "second", "third")),
                root,
            )  # type: ignore[arg-type]
            cancelled: list[str] = []
            summary: list[tuple[int, int, int]] = []
            worker.item_cancelled.connect(
                lambda item_id, _message, _log: cancelled.append(item_id)
            )
            worker.finished.connect(
                lambda done, failed, stopped: summary.append((done, failed, stopped))
            )
            canceller = Thread(
                target=lambda: (converter.started.wait(2.0), worker.cancel_batch())
            )
            canceller.start()
            worker.run()
            canceller.join()

            self.assertEqual(converter.calls, ["first.epub"])
            self.assertEqual(cancelled, ["first", "second", "third"])
            self.assertEqual(summary, [(0, 0, 3)])

    def test_emits_real_progress_and_bounded_log_updates(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            worker = BatchConversionWorker(
                RecordingConverter(), self._jobs(root, ("first",)), root
            )  # type: ignore[arg-type]
            progress: list[int] = []
            logs: list[str] = []
            worker.item_progress.connect(lambda _item_id, value: progress.append(value))
            worker.item_log_updated.connect(lambda _item_id, log: logs.append(log))
            worker.run()
            self.assertEqual(progress, [42])
            self.assertTrue(logs[-1].endswith("42% converting\n"))

    def test_does_not_emit_fabricated_progress(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            worker = BatchConversionWorker(
                RecordingConverter(emit_output=False),
                self._jobs(root, ("first",)),
                root,
            )  # type: ignore[arg-type]
            progress: list[int] = []
            worker.item_progress.connect(lambda _item_id, value: progress.append(value))
            worker.run()
            self.assertEqual(progress, [])


if __name__ == "__main__":
    unittest.main()
