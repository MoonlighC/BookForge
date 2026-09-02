"""Controlled asynchronous metadata extraction tasks."""

from __future__ import annotations

from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from bookforge.core.metadata import (
    MetadataCancelled,
    MetadataError,
    MetadataService,
)


class MetadataTaskSignals(QObject):
    loaded = Signal(str, object)
    failed = Signal(str, str)
    cancelled = Signal(str)
    finished = Signal(str)


class MetadataLoadTask(QRunnable):
    """Load one item's metadata on a bounded ``QThreadPool``."""

    def __init__(
        self,
        service: MetadataService,
        item_id: str,
        source_path: Path,
        cancel_event: Event,
    ) -> None:
        super().__init__()
        self.signals = MetadataTaskSignals()
        self._service = service
        self._item_id = item_id
        self._source_path = source_path
        self._cancel_event = cancel_event

    @Slot()
    def run(self) -> None:
        try:
            result = self._service.load(
                self._source_path,
                self._item_id,
                cancel_event=self._cancel_event,
            )
        except MetadataCancelled:
            self.signals.cancelled.emit(self._item_id)
        except MetadataError as exc:
            self.signals.failed.emit(self._item_id, str(exc))
        except Exception:
            self.signals.failed.emit(
                self._item_id, "Metadata could not be loaded for this book."
            )
        else:
            self.signals.loaded.emit(self._item_id, result)
        finally:
            self.signals.finished.emit(self._item_id)
