"""Metadata extraction, overrides, and temporary cover resources."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from enum import Enum
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from threading import Event, Lock
import xml.etree.ElementTree as ET

from bookforge.core.calibre import (
    CalibreAdapter,
    CalibreCancelledError,
    CalibreProcessError,
    find_ebook_meta,
)


class MetadataError(RuntimeError):
    def __init__(self, message: str, *, log: str = "") -> None:
        super().__init__(message)
        self.log = log


class MetadataCancelled(MetadataError):
    pass


class MetadataStatus(str, Enum):
    NOT_LOADED = "Not loaded"
    LOADING = "Loading"
    LOADED = "Loaded"
    UNAVAILABLE = "Unavailable"


@dataclass(frozen=True, slots=True)
class BookMetadata:
    title: str | None = None
    authors: tuple[str, ...] = ()
    language: str | None = None
    publisher: str | None = None
    series: str | None = None
    series_index: float | None = None
    tags: tuple[str, ...] = ()
    cover_path: Path | None = None


@dataclass(frozen=True, slots=True)
class MetadataOverrides:
    """An edited metadata snapshot plus exactly which fields changed."""

    metadata: BookMetadata | None = None
    changed_fields: frozenset[str] = frozenset()

    @property
    def is_edited(self) -> bool:
        return self.metadata is not None and bool(self.changed_fields)

    @classmethod
    def between(
        cls, original: BookMetadata, edited: BookMetadata
    ) -> MetadataOverrides:
        changed = frozenset(
            field.name
            for field in fields(BookMetadata)
            if getattr(original, field.name) != getattr(edited, field.name)
        )
        return cls(edited if changed else None, changed)


@dataclass(frozen=True, slots=True)
class MetadataExtraction:
    metadata: BookMetadata
    cover_bytes: bytes | None
    log: str


@dataclass(frozen=True, slots=True)
class MetadataLoadResult:
    metadata: BookMetadata
    log: str


def effective_metadata(
    original: BookMetadata | None, overrides: MetadataOverrides
) -> BookMetadata:
    if overrides.is_edited and overrides.metadata is not None:
        return overrides.metadata
    return original or BookMetadata()


def metadata_conversion_arguments(overrides: MetadataOverrides) -> list[str]:
    """Build only verified Calibre 9.14 metadata conversion arguments."""
    if not overrides.is_edited or overrides.metadata is None:
        return []
    metadata = overrides.metadata
    changed = overrides.changed_fields
    arguments: list[str] = []

    scalar_options = (
        ("title", "--title", metadata.title),
        ("language", "--language", metadata.language),
        ("publisher", "--publisher", metadata.publisher),
        ("series", "--series", metadata.series),
    )
    for field_name, option, value in scalar_options:
        if field_name in changed and value:
            arguments.append(f"{option}={value}")
    if "authors" in changed and metadata.authors:
        arguments.append(f"--authors={' & '.join(metadata.authors)}")
    if "series_index" in changed and metadata.series_index is not None:
        arguments.append(f"--series-index={metadata.series_index:g}")
    if "tags" in changed and metadata.tags:
        arguments.append(f"--tags={','.join(metadata.tags)}")
    if "cover_path" in changed and metadata.cover_path is not None:
        arguments.append(f"--cover={metadata.cover_path}")
    return arguments


class CalibreMetadataAdapter:
    """Read metadata and cover data using Calibre's ``ebook-meta`` tool."""

    def __init__(self, executable: Path | None = None) -> None:
        self._executable = executable or find_ebook_meta()

    @property
    def executable(self) -> Path | None:
        return self._executable

    @property
    def is_available(self) -> bool:
        return self._executable is not None and self._executable.is_file()

    def extract(
        self, source_path: Path, *, cancel_event: Event | None = None
    ) -> MetadataExtraction:
        if not self.is_available:
            raise MetadataError("Calibre's ebook-meta tool was not found.")
        source = source_path.expanduser().resolve()
        if not source.is_file():
            raise MetadataError("The source file is no longer available.")
        assert self._executable is not None

        with TemporaryDirectory(prefix="bookforge-extract-") as folder:
            temporary_folder = Path(folder)
            opf_path = temporary_folder / "metadata.opf"
            cover_path = temporary_folder / "cover.jpg"
            command = [
                str(self._executable),
                str(source),
                f"--to-opf={opf_path}",
                f"--get-cover={cover_path}",
            ]
            runner = CalibreAdapter(self._executable)
            try:
                result = runner.run_command(command, cancel_event=cancel_event)
            except CalibreCancelledError as exc:
                raise MetadataCancelled(
                    "Metadata loading was cancelled.", log=exc.output
                ) from exc
            except CalibreProcessError as exc:
                raise MetadataError(
                    "Metadata could not be read from this file.", log=exc.output
                ) from exc

            if not opf_path.is_file():
                raise MetadataError(
                    "Calibre did not produce readable metadata.", log=result.output
                )
            metadata = _parse_opf(opf_path)
            cover_bytes = (
                cover_path.read_bytes()
                if cover_path.is_file() and cover_path.stat().st_size > 0
                else None
            )
            return MetadataExtraction(metadata, cover_bytes, result.output)


class MetadataService:
    """Coordinate extraction and own per-queue-item temporary cover files."""

    def __init__(self, adapter: CalibreMetadataAdapter | None = None) -> None:
        self._adapter = adapter or CalibreMetadataAdapter()
        self._temporary = TemporaryDirectory(prefix="bookforge-metadata-")
        self._root = Path(self._temporary.name)
        self._lock = Lock()
        self._closed = False

    @property
    def available(self) -> bool:
        return self._adapter.is_available

    def load(
        self,
        source_path: Path,
        item_id: str,
        *,
        cancel_event: Event | None = None,
    ) -> MetadataLoadResult:
        extraction = self._adapter.extract(source_path, cancel_event=cancel_event)
        if cancel_event is not None and cancel_event.is_set():
            raise MetadataCancelled("Metadata loading was cancelled.")
        metadata = extraction.metadata
        if extraction.cover_bytes:
            extension = detect_cover_extension(extraction.cover_bytes)
            if extension is not None:
                cover_path = self._write_cover(
                    item_id,
                    f"original.{extension}",
                    extraction.cover_bytes,
                    cancel_event,
                )
                metadata = replace(metadata, cover_path=cover_path)
        return MetadataLoadResult(metadata, extraction.log)

    def store_replacement_cover(self, item_id: str, source_path: Path) -> Path:
        source = source_path.expanduser().resolve()
        if not source.is_file():
            raise MetadataError("The selected cover image is no longer available.")
        data = source.read_bytes()
        extension = detect_cover_extension(data)
        if extension is None:
            raise MetadataError("Select a readable JPG, JPEG, or PNG image.")
        with self._lock:
            item_folder = self._item_folder(item_id)
            item_folder.mkdir(parents=True, exist_ok=True)
            for existing in item_folder.iterdir():
                if existing.name.startswith("replacement."):
                    existing.unlink(missing_ok=True)
            destination = item_folder / f"replacement.{extension}"
            shutil.copyfile(source, destination)
            return destination

    def clear_replacement_cover(self, item_id: str) -> None:
        with self._lock:
            item_folder = self._item_folder(item_id)
            if not item_folder.is_dir():
                return
            for existing in item_folder.iterdir():
                if existing.name.startswith("replacement."):
                    existing.unlink(missing_ok=True)

    def cleanup_item(self, item_id: str) -> None:
        with self._lock:
            item_folder = self._item_folder(item_id)
            if item_folder.is_dir():
                shutil.rmtree(item_folder, ignore_errors=True)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._temporary.cleanup()

    def _write_cover(
        self,
        item_id: str,
        name: str,
        data: bytes,
        cancel_event: Event | None = None,
    ) -> Path:
        with self._lock:
            if cancel_event is not None and cancel_event.is_set():
                raise MetadataCancelled("Metadata loading was cancelled.")
            item_folder = self._item_folder(item_id)
            item_folder.mkdir(parents=True, exist_ok=True)
            destination = item_folder / name
            destination.write_bytes(data)
            return destination

    def _item_folder(self, item_id: str) -> Path:
        if not item_id or any(character not in "0123456789abcdef" for character in item_id):
            raise MetadataError("Invalid queue item identifier.")
        return self._root / item_id


def detect_cover_extension(data: bytes) -> str | None:
    """Validate supported cover bytes and return a normalized extension."""
    if (
        len(data) >= 45
        and data.startswith(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
        and data[-12:-8] == b"\x00\x00\x00\x00"
        and data[-8:-4] == b"IEND"
    ):
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        return "png" if width > 0 and height > 0 else None
    if (
        len(data) >= 6
        and data.startswith(b"\xff\xd8\xff")
        and data.endswith(b"\xff\xd9")
    ):
        return "jpg" if _jpeg_has_dimensions(data) else None
    return None


def _jpeg_has_dimensions(data: bytes) -> bool:
    start_of_frame = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    position = 2
    while position + 4 <= len(data):
        if data[position] != 0xFF:
            position += 1
            continue
        while position < len(data) and data[position] == 0xFF:
            position += 1
        if position >= len(data):
            break
        marker = data[position]
        position += 1
        if marker in (0xD8, 0xD9):
            continue
        if marker == 0xDA or position + 2 > len(data):
            break
        segment_length = int.from_bytes(data[position : position + 2], "big")
        if segment_length < 2 or position + segment_length > len(data):
            return False
        if marker in start_of_frame and segment_length >= 7:
            height = int.from_bytes(data[position + 3 : position + 5], "big")
            width = int.from_bytes(data[position + 5 : position + 7], "big")
            return width > 0 and height > 0
        position += segment_length
    return False


def _parse_opf(path: Path) -> BookMetadata:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise MetadataError("Calibre produced invalid metadata output.") from exc

    def elements(local_name: str):
        return (
            element
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == local_name
        )

    def first_text(local_name: str) -> str | None:
        return next(
            (
                text
                for element in elements(local_name)
                if (text := (element.text or "").strip())
            ),
            None,
        )

    authors = tuple(
        text
        for element in elements("creator")
        if (text := (element.text or "").strip())
    )
    tags = tuple(
        text
        for element in elements("subject")
        if (text := (element.text or "").strip())
    )
    metadata_elements = list(elements("meta"))
    series = next(
        (
            (element.get("content") or "").strip() or None
            for element in metadata_elements
            if element.get("name") == "calibre:series"
        ),
        None,
    )
    raw_index = next(
        (
            (element.get("content") or "").strip()
            for element in metadata_elements
            if element.get("name") == "calibre:series_index"
        ),
        "",
    )
    try:
        series_index = float(raw_index) if raw_index else None
    except ValueError:
        series_index = None

    return BookMetadata(
        title=first_text("title"),
        authors=authors,
        language=first_text("language"),
        publisher=first_text("publisher"),
        series=series,
        series_index=series_index,
        tags=tags,
    )
