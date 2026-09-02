"""Qt worker that executes one conversion queue sequentially."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from bookforge.core.converter import ConversionError, ConverterService


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BatchJob:
    item_id: str
    source_path: Path
    output_format: str
    overwrite: bool = False


class BatchConversionWorker(QObject):
    """Process a fixed job snapshot in order without blocking the GUI thread."""

    item_started = Signal(str, int, int)
    item_completed = Signal(str, object)
    item_failed = Signal(str, str)
    finished = Signal(int, int)

    def __init__(
        self,
        converter: ConverterService,
        jobs: tuple[BatchJob, ...],
        output_folder: Path,
    ) -> None:
        super().__init__()
        self._converter = converter
        self._jobs = jobs
        self._output_folder = output_folder

    @Slot()
    def run(self) -> None:
        completed_count = 0
        failed_count = 0
        total = len(self._jobs)

        for position, job in enumerate(self._jobs, start=1):
            self.item_started.emit(job.item_id, position, total)
            try:
                result = self._converter.convert(
                    job.source_path,
                    self._output_folder,
                    job.output_format,
                    overwrite=job.overwrite,
                )
            except ConversionError as exc:
                LOGGER.warning("Conversion failed for %s: %s", job.source_path, exc)
                failed_count += 1
                self.item_failed.emit(job.item_id, str(exc))
            except Exception:
                LOGGER.exception("Unexpected conversion error for %s", job.source_path)
                failed_count += 1
                self.item_failed.emit(
                    job.item_id,
                    "An unexpected error occurred while converting this book.",
                )
            else:
                completed_count += 1
                self.item_completed.emit(job.item_id, result)

        self.finished.emit(completed_count, failed_count)
