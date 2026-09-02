"""In-memory conversion queue state for BookForge."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import os
from pathlib import Path
from uuid import uuid4

from bookforge.core.converter import ConversionError, get_input_format, get_output_format


class QueueStatus(str, Enum):
    READY = "Ready"
    WAITING = "Waiting"
    CONVERTING = "Converting"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    SKIPPED = "Skipped"


@dataclass(slots=True)
class QueueItem:
    source_path: Path
    input_format: str
    output_format: str
    status: QueueStatus = QueueStatus.READY
    result_path: Path | None = None
    error_message: str = ""
    progress: int | None = None
    log: str = ""
    item_id: str = field(default_factory=lambda: uuid4().hex)


@dataclass(frozen=True, slots=True)
class RejectedPath:
    path: Path
    reason: str


@dataclass(frozen=True, slots=True)
class QueueAddResult:
    added: tuple[QueueItem, ...]
    duplicate_count: int
    rejected: tuple[RejectedPath, ...]


class ConversionQueue:
    """Own a small, process-local collection of queued conversions."""

    def __init__(self) -> None:
        self._items: list[QueueItem] = []

    @property
    def items(self) -> tuple[QueueItem, ...]:
        return tuple(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def add_paths(self, paths: list[Path] | tuple[Path, ...]) -> QueueAddResult:
        added: list[QueueItem] = []
        rejected: list[RejectedPath] = []
        duplicate_count = 0

        for raw_path in paths:
            path = raw_path.expanduser()
            if not path.is_file():
                rejected.append(RejectedPath(path, "The file is no longer available."))
                continue
            try:
                input_format = get_input_format(path.suffix).extension
            except ConversionError as exc:
                rejected.append(RejectedPath(path, str(exc)))
                continue

            source_path = path.resolve()
            if any(paths_are_same(source_path, item.source_path) for item in self._items):
                duplicate_count += 1
                continue

            output_format = "epub" if input_format == "azw3" else "azw3"
            item = QueueItem(source_path, input_format, output_format)
            self._items.append(item)
            added.append(item)

        return QueueAddResult(tuple(added), duplicate_count, tuple(rejected))

    def get(self, item_id: str) -> QueueItem | None:
        return next((item for item in self._items if item.item_id == item_id), None)

    def remove(self, item_id: str) -> bool:
        item = self.get(item_id)
        if item is None or item.status is QueueStatus.CONVERTING:
            return False
        self._items.remove(item)
        return True

    def clear_non_running(self) -> tuple[str, ...]:
        removed_ids = tuple(
            item.item_id
            for item in self._items
            if item.status is not QueueStatus.CONVERTING
        )
        self._items = [
            item for item in self._items if item.status is QueueStatus.CONVERTING
        ]
        return removed_ids

    def set_output_format(self, item_id: str, output_format: str) -> bool:
        item = self.get(item_id)
        if item is None or item.status is QueueStatus.CONVERTING:
            return False
        normalized_format = get_output_format(output_format).extension
        if item.output_format == normalized_format:
            return True
        item.output_format = normalized_format
        item.status = QueueStatus.READY
        item.result_path = None
        item.error_message = ""
        item.progress = None
        item.log = ""
        return True

    def retry(self, item_id: str) -> bool:
        item = self.get(item_id)
        if item is None or item.status not in (
            QueueStatus.FAILED,
            QueueStatus.CANCELLED,
            QueueStatus.SKIPPED,
        ):
            return False
        self._reset_item(item)
        return True

    def retry_failed(self) -> tuple[str, ...]:
        retried: list[str] = []
        for item in self._items:
            if item.status in (
                QueueStatus.FAILED,
                QueueStatus.CANCELLED,
                QueueStatus.SKIPPED,
            ):
                self._reset_item(item)
                retried.append(item.item_id)
        return tuple(retried)

    @staticmethod
    def _reset_item(item: QueueItem) -> None:
        item.status = QueueStatus.READY
        item.result_path = None
        item.error_message = ""
        item.progress = None
        item.log = ""


def paths_are_same(first: Path, second: Path) -> bool:
    """Compare source paths safely, including hard links when they exist."""
    try:
        return first.samefile(second)
    except OSError:
        return path_key(first) == path_key(second)


def path_key(path: Path) -> str:
    """Return a stable comparison key for a path on the current platform."""
    return os.path.normcase(str(path.expanduser().resolve(strict=False)))


def format_file_size(size: int) -> str:
    """Format a byte count without requiring an external dependency."""
    if size < 1024:
        return f"{size} B"
    value = float(size)
    units = ("KB", "MB", "GB", "TB")
    for unit in units:
        value /= 1024
        if value < 1024 or unit == units[-1]:
            precision = 0 if value >= 100 else 1
            return f"{value:.{precision}f} {unit}"
    return f"{size} B"
