from __future__ import annotations

import base64
from pathlib import Path
import tempfile
from threading import Event
import unittest

from bookforge.core.metadata import (
    BookMetadata,
    MetadataCancelled,
    MetadataExtraction,
    MetadataError,
    MetadataOverrides,
    MetadataService,
    _parse_opf,
    detect_cover_extension,
    effective_metadata,
    metadata_conversion_arguments,
)
from bookforge.ui.metadata_worker import MetadataLoadTask


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class FakeMetadataAdapter:
    is_available = True

    def __init__(self, extraction: MetadataExtraction) -> None:
        self.extraction = extraction

    def extract(self, _source_path: Path, *, cancel_event=None) -> MetadataExtraction:
        if cancel_event is not None and cancel_event.is_set():
            raise MetadataCancelled("cancelled")
        return self.extraction


class MetadataTests(unittest.TestCase):
    def test_opf_parses_multiple_authors_unicode_and_missing_values(self) -> None:
        opf = """<?xml version="1.0" encoding="utf-8"?>
        <package xmlns:dc="http://purl.org/dc/elements/1.1/">
          <metadata>
            <dc:title>Книга о море</dc:title>
            <dc:creator>Анна Иванова</dc:creator>
            <dc:creator>Stanisław Lem</dc:creator>
            <dc:language>ru</dc:language>
            <dc:subject>фантастика</dc:subject>
            <dc:subject>classic</dc:subject>
            <meta name="calibre:series" content="Звёзды" />
            <meta name="calibre:series_index" content="2.5" />
          </metadata>
        </package>"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "metadata.opf"
            path.write_text(opf, encoding="utf-8")
            metadata = _parse_opf(path)

        self.assertEqual(metadata.title, "Книга о море")
        self.assertEqual(metadata.authors, ("Анна Иванова", "Stanisław Lem"))
        self.assertEqual(metadata.language, "ru")
        self.assertIsNone(metadata.publisher)
        self.assertEqual(metadata.series, "Звёзды")
        self.assertEqual(metadata.series_index, 2.5)
        self.assertEqual(metadata.tags, ("фантастика", "classic"))

    def test_missing_metadata_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "metadata.opf"
            path.write_text("<package><metadata /></package>", encoding="utf-8")
            metadata = _parse_opf(path)

        self.assertEqual(metadata, BookMetadata())

    def test_per_item_cover_storage_is_isolated_and_removed(self) -> None:
        extraction = MetadataExtraction(
            BookMetadata(title="Test"), PNG_1X1, "metadata log"
        )
        service = MetadataService(FakeMetadataAdapter(extraction))  # type: ignore[arg-type]
        try:
            with tempfile.TemporaryDirectory() as folder:
                source = Path(folder) / "book.epub"
                source.write_bytes(b"book")
                first = service.load(source, "a" * 32)
                second = service.load(source, "b" * 32)

            self.assertIsNotNone(first.metadata.cover_path)
            self.assertIsNotNone(second.metadata.cover_path)
            self.assertNotEqual(first.metadata.cover_path, second.metadata.cover_path)
            assert first.metadata.cover_path is not None
            assert second.metadata.cover_path is not None
            self.assertTrue(first.metadata.cover_path.is_file())
            self.assertTrue(second.metadata.cover_path.is_file())

            service.cleanup_item("a" * 32)
            self.assertFalse(first.metadata.cover_path.exists())
            self.assertTrue(second.metadata.cover_path.exists())
        finally:
            service.close()

    def test_close_removes_all_temporary_metadata_resources(self) -> None:
        extraction = MetadataExtraction(BookMetadata(), PNG_1X1, "")
        service = MetadataService(FakeMetadataAdapter(extraction))  # type: ignore[arg-type]
        root = service._root
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "book.txt"
            source.write_text("book", encoding="utf-8")
            service.load(source, "c" * 32)
        self.assertTrue(root.is_dir())

        service.close()

        self.assertFalse(root.exists())

    def test_replacement_cover_is_validated_copied_and_clearable(self) -> None:
        extraction = MetadataExtraction(BookMetadata(), None, "")
        service = MetadataService(FakeMetadataAdapter(extraction))  # type: ignore[arg-type]
        try:
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                valid = root / "cover.png"
                valid.write_bytes(PNG_1X1)
                invalid = root / "broken.png"
                invalid.write_bytes(b"not an image")

                stored = service.store_replacement_cover("f" * 32, valid)
                self.assertTrue(stored.is_file())
                self.assertNotEqual(stored, valid)
                self.assertEqual(stored.read_bytes(), PNG_1X1)
                with self.assertRaisesRegex(MetadataError, "readable"):
                    service.store_replacement_cover("f" * 32, invalid)

                service.clear_replacement_cover("f" * 32)
                self.assertFalse(stored.exists())
        finally:
            service.close()

    def test_override_model_tracks_only_changed_fields(self) -> None:
        original = BookMetadata(
            title="Original", authors=("One",), language="en", tags=("old",)
        )
        edited = BookMetadata(
            title="Изменено",
            authors=("One", "Два"),
            language="en",
            tags=("new",),
        )
        overrides = MetadataOverrides.between(original, edited)

        self.assertEqual(
            overrides.changed_fields, frozenset({"title", "authors", "tags"})
        )
        self.assertEqual(effective_metadata(original, overrides), edited)
        self.assertEqual(
            metadata_conversion_arguments(overrides),
            ["--title=Изменено", "--authors=One & Два", "--tags=new"],
        )

    def test_valid_and_invalid_cover_bytes(self) -> None:
        self.assertEqual(detect_cover_extension(PNG_1X1), "png")
        self.assertIsNone(detect_cover_extension(b"not an image"))
        self.assertIsNone(detect_cover_extension(PNG_1X1[:24]))

    def test_metadata_worker_emits_loaded_and_cancelled(self) -> None:
        extraction = MetadataExtraction(BookMetadata(title="Loaded"), None, "")
        service = MetadataService(FakeMetadataAdapter(extraction))  # type: ignore[arg-type]
        try:
            loaded: list[object] = []
            cancelled: list[str] = []
            task = MetadataLoadTask(service, "d" * 32, Path("book.epub"), Event())
            task.signals.loaded.connect(lambda _item_id, result: loaded.append(result))
            task.run()
            self.assertEqual(loaded[0].metadata.title, "Loaded")

            event = Event()
            event.set()
            task = MetadataLoadTask(service, "e" * 32, Path("book.epub"), event)
            task.signals.cancelled.connect(cancelled.append)
            task.run()
            self.assertEqual(cancelled, ["e" * 32])
        finally:
            service.close()


if __name__ == "__main__":
    unittest.main()
