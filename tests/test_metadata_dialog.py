from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from bookforge.core.metadata import BookMetadata, MetadataOverrides, MetadataStatus
from bookforge.core.queue import QueueItem
from bookforge.ui.metadata_dialog import MetadataDialog
from bookforge.ui.queue_item_widget import QueueItemWidget


class MetadataDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _cover(self, folder: Path, name: str = "cover.png") -> Path:
        path = folder / name
        image = QImage(100, 200, QImage.Format.Format_RGB32)
        image.fill(0x3368D4)
        self.assertTrue(image.save(str(path)))
        return path

    def test_dialog_constructs_and_previews_cover_without_distortion(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            cover = self._cover(Path(folder))
            metadata = BookMetadata(title="Dune", cover_path=cover)
            dialog = MetadataDialog("Dune.epub", metadata, metadata)

            pixmap = dialog._cover_preview.pixmap()
            self.assertIsNotNone(pixmap)
            assert pixmap is not None
            self.assertFalse(pixmap.isNull())
            self.assertEqual((pixmap.width(), pixmap.height()), (150, 300))
            self.assertEqual(dialog._title.text(), "Dune")

    def test_save_parses_multiple_authors_unicode_and_tags(self) -> None:
        original = BookMetadata(title="Original")
        dialog = MetadataDialog("book.epub", original, original)
        dialog._title.setText("Новая книга")
        dialog._authors.setText("Анна; Stanisław Lem")
        dialog._language.setText("ru")
        dialog._publisher.setText("Издатель")
        dialog._series.setText("Серия")
        dialog._series_index.setText("3.5")
        dialog._tags.setText("наука, classic")

        dialog.accept()

        self.assertEqual(
            dialog.saved_metadata,
            BookMetadata(
                title="Новая книга",
                authors=("Анна", "Stanisław Lem"),
                language="ru",
                publisher="Издатель",
                series="Серия",
                series_index=3.5,
                tags=("наука", "classic"),
            ),
        )

    def test_cancel_discards_dialog_edits(self) -> None:
        original = BookMetadata(title="Original")
        dialog = MetadataDialog("book.epub", original, original)
        dialog._title.setText("Unsaved")

        dialog.reject()

        self.assertIsNone(dialog.saved_metadata)
        self.assertEqual(original.title, "Original")

    def test_reset_restores_original_metadata_and_cover(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original_cover = self._cover(root, "original.png")
            replacement_cover = self._cover(root, "replacement.png")
            original = BookMetadata(
                title="Original", authors=("First",), cover_path=original_cover
            )
            current = BookMetadata(
                title="Edited", authors=("Second",), cover_path=replacement_cover
            )
            dialog = MetadataDialog("book.epub", original, current)

            dialog._reset_to_original()
            dialog.accept()

            self.assertEqual(dialog.saved_metadata, original)
            assert dialog.saved_metadata is not None
            self.assertFalse(
                MetadataOverrides.between(
                    original, dialog.saved_metadata
                ).is_edited
            )

    def test_cover_validation_rejects_invalid_image_content(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            invalid = Path(folder) / "cover.png"
            invalid.write_bytes(b"not actually an image")

            self.assertFalse(MetadataDialog._is_readable_cover(invalid))

    def test_cover_validation_accepts_jpg_jpeg_and_png(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("cover.jpg", "cover.jpeg", "cover.png"):
                cover = self._cover(root, name)
                self.assertTrue(MetadataDialog._is_readable_cover(cover), name)

    def test_queue_row_shows_loading_unavailable_and_edited_states(self) -> None:
        item = QueueItem(Path("book.epub"), "epub", "azw3")
        row = QueueItemWidget(item)
        item.metadata_status = MetadataStatus.LOADING
        row.update_item(item)
        self.assertEqual(row._metadata.text(), "Metadata · Loading…")
        self.assertFalse(row._metadata.isEnabled())

        item.metadata_status = MetadataStatus.UNAVAILABLE
        item.metadata_error = "Could not read metadata"
        row.update_item(item)
        self.assertEqual(row._metadata.text(), "Metadata · Unavailable")
        self.assertTrue(row._metadata.isEnabled())
        self.assertEqual(row._metadata.toolTip(), "Could not read metadata")

        item.metadata_overrides = MetadataOverrides.between(
            BookMetadata(), BookMetadata(title="Edited")
        )
        row.update_item(item)
        self.assertEqual(row._metadata.text(), "Metadata · Edited")


if __name__ == "__main__":
    unittest.main()
