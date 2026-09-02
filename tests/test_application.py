from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect, QSettings
from PySide6.QtWidgets import QApplication

from bookforge.core.batch import OverwritePolicy
from bookforge.core.converter import ConverterService
from bookforge.resources import application_icon, resource_path
from bookforge.settings import ApplicationSettings, geometry_is_visible
from bookforge.ui.main_window import MainWindow
from main import configure_application


class AvailableAdapter:
    is_available = True
    executable = Path(__file__)


class UnavailableMetadataService:
    available = False

    def cleanup_item(self, _item_id: str) -> None:
        pass

    def clear_replacement_cover(self, _item_id: str) -> None:
        pass

    def close(self) -> None:
        pass


class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _window(self, settings: QSettings) -> MainWindow:
        converter = ConverterService(AvailableAdapter())  # type: ignore[arg-type]
        return MainWindow(
            converter,
            metadata_service=UnavailableMetadataService(),  # type: ignore[arg-type]
            settings=settings,
        )

    def test_application_identity_version_and_icon(self) -> None:
        configure_application(self.app)
        self.assertEqual(self.app.applicationName(), "BookForge")
        self.assertEqual(self.app.applicationDisplayName(), "BookForge")
        self.assertEqual(self.app.organizationName(), "BookForge")
        self.assertEqual(self.app.applicationVersion(), "0.9.0")
        self.assertFalse(application_icon().isNull())

    def test_resource_path_uses_pyinstaller_bundle_root(self) -> None:
        with tempfile.TemporaryDirectory() as folder, patch.object(
            sys, "_MEIPASS", folder, create=True
        ):
            expected = Path(folder) / "assets" / "bookforge.ico"
            self.assertEqual(resource_path("assets/bookforge.ico"), expected)

    def test_settings_persist_geometry_folder_format_and_policy(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            settings_path = root / "bookforge.ini"
            settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
            first = self._window(settings)
            first.resize(790, 650)
            first.move(5, 20)
            first._output_folder.setText(str(root))
            first._output_folder_is_automatic = False
            first._set_all_combo.setCurrentIndex(
                first._set_all_combo.findData("mobi")
            )
            first._overwrite_combo.setCurrentIndex(
                first._overwrite_combo.findData(OverwritePolicy.SKIP_ALL.value)
            )
            expected_geometry = first.geometry()
            first.close()

            restored_settings = QSettings(
                str(settings_path), QSettings.Format.IniFormat
            )
            second = self._window(restored_settings)
            try:
                self.assertEqual(second._output_folder.text(), str(root.resolve()))
                self.assertFalse(second._output_folder_is_automatic)
                self.assertEqual(second._set_all_combo.currentData(), "mobi")
                self.assertEqual(
                    second._overwrite_combo.currentData(),
                    OverwritePolicy.SKIP_ALL.value,
                )
                self.assertEqual(second.geometry().size(), expected_geometry.size())
                self.assertEqual(len(second._queue), 0)
            finally:
                second.close()

    def test_missing_persisted_output_folder_returns_to_automatic_mode(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            settings = QSettings(
                str(Path(folder) / "bookforge.ini"), QSettings.Format.IniFormat
            )
            settings.setValue("conversion/outputFolder", str(Path(folder) / "gone"))
            window = self._window(settings)
            try:
                self.assertTrue(window._output_folder_is_automatic)
                self.assertEqual(window._output_folder.text(), "")
            finally:
                window.close()

    def test_offscreen_geometry_is_rejected(self) -> None:
        screens = (QRect(0, 0, 1920, 1080), QRect(1920, 0, 1920, 1080))
        self.assertTrue(geometry_is_visible(QRect(100, 100, 1100, 750), screens))
        self.assertFalse(
            geometry_is_visible(QRect(8000, 8000, 1100, 750), screens)
        )
        self.assertFalse(geometry_is_visible(QRect(1910, 1070, 1100, 750), screens))

    def test_canonical_spec_is_windowed_one_folder_build(self) -> None:
        spec = (Path(__file__).resolve().parents[1] / "BookForge.spec").read_text(
            encoding="utf-8"
        )
        self.assertIn("console=False", spec)
        self.assertIn("COLLECT(", spec)
        self.assertIn('"assets"', spec)
        self.assertIn('"icuuc.dll"', spec)
        self.assertNotIn("ebook-convert.exe", spec)
        self.assertNotIn("ebook-meta.exe", spec)


if __name__ == "__main__":
    unittest.main()
