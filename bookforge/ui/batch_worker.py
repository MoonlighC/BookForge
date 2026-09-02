"""Qt worker that executes and controls one sequential conversion batch."""

from __future__ import annotations

import logging
from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from bookforge.core.batch import BatchJob
from bookforge.core.calibre import BoundedLog, parse_calibre_progress
from bookforge.core.converter import (
    ConversionCancelled,
    ConversionError,
    ConverterService,
)


LOGGER = logging.getLogger(__name__)


class BatchCancellation:
    """Thread-safe cancellation flags shared by the GUI and worker thread."""

    def __init__(self) -> None:
        self._current = Event()
        self._batch = Event()

    @property
    def current_event(self) -> Event:
        return self._current

    @property
    def batch_requested(self) -> bool:
        return self._batch.is_set()

    def begin_job(self) -> None:
        self._current.clear()
        if self._batch.is_set():
            self._current.set()

    def cancel_current(self) -> None:
        self._current.set()

    def cancel_batch(self) -> None:
        self._batch.set()
        self._current.set()


class BatchConversionWorker(QObject):
    """Process a fixed job snapshot in order without blocking the GUI thread."""

    item_started = Signal(str, int, int)
    item_progress = Signal(str, int)
    item_log_updated = Signal(str, str)
    item_completed = Signal(str, object)
    item_failed = Signal(str, str, str)
    item_cancelled = Signal(str, str, str)
    finished = Signal(int, int, int)

    def __init__(
        self,
        converter: ConverterService,
        jobs: tuple[BatchJob, ...],
        output_folder: Path,
        cancellation: BatchCancellation | None = None,
    ) -> None:
        super().__init__()
        self._converter = converter
        self._jobs = jobs
        self._output_folder = output_folder
        self._cancellation = cancellation or BatchCancellation()

    def cancel_current(self) -> None:
        """Request cancellation from any thread without touching Qt state."""
        self._cancellation.cancel_current()

    def cancel_batch(self) -> None:
        """Request whole-batch cancellation from any thread."""
        self._cancellation.cancel_batch()

    @Slot()
    def run(self) -> None:
        completed_count = 0
        failed_count = 0
        cancelled_count = 0
        total = len(self._jobs)

        for index, job in enumerate(self._jobs):
            if self._cancellation.batch_requested:
                cancelled_count += self._cancel_remaining(index)
                break

            self._cancellation.begin_job()
            if self._cancellation.batch_requested:
                cancelled_count += self._cancel_remaining(index)
                break

            position = index + 1
            item_log = BoundedLog()
            latest_progress: int | None = None
            self.item_started.emit(job.item_id, position, total)

            def handle_output(chunk: str) -> None:
                nonlocal latest_progress
                current_log = item_log.append(chunk)
                self.item_log_updated.emit(job.item_id, current_log)
                progress = parse_calibre_progress(chunk)
                if progress is not None and progress != latest_progress:
                    latest_progress = progress
                    self.item_progress.emit(job.item_id, progress)

            try:
                result = self._converter.convert(
                    job.source_path,
                    self._output_folder,
                    job.output_format,
                    overwrite=job.overwrite,
                    cancel_event=self._cancellation.current_event,
                    on_output=handle_output,
                )
            except ConversionCancelled as exc:
                cancelled_count += 1
                log = item_log.text or exc.log
                self.item_cancelled.emit(job.item_id, "Conversion cancelled.", log)
            except ConversionError as exc:
                LOGGER.warning("Conversion failed for %s: %s", job.source_path, exc)
                failed_count += 1
                log = item_log.text or exc.log
                self.item_failed.emit(job.item_id, str(exc), log)
            except Exception:
                LOGGER.exception("Unexpected conversion error for %s", job.source_path)
                failed_count += 1
                self.item_failed.emit(
                    job.item_id,
                    "An unexpected error occurred while converting this book.",
                    item_log.text,
                )
            else:
                completed_count += 1
                self.item_completed.emit(job.item_id, result)

        self.finished.emit(completed_count, failed_count, cancelled_count)

    def _cancel_remaining(self, start_index: int) -> int:
        remaining = self._jobs[start_index:]
        for job in remaining:
            self.item_cancelled.emit(
                job.item_id,
                "Cancelled because the batch was stopped.",
                "",
            )
        return len(remaining)
