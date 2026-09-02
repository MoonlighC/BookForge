"""Small QSettings wrapper for non-sensitive application preferences."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from PySide6.QtCore import QByteArray, QRect, QSettings
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget


ORGANIZATION_NAME = "BookForge"
APPLICATION_NAME = "BookForge"
WINDOW_GEOMETRY_KEY = "window/geometry"
OUTPUT_FOLDER_KEY = "conversion/outputFolder"
GLOBAL_FORMAT_KEY = "conversion/globalFormat"
OVERWRITE_POLICY_KEY = "conversion/overwritePolicy"
LANGUAGE_KEY = "appearance/language"
THEME_KEY = "appearance/theme"


def geometry_is_visible(rect: QRect, screen_rects: Iterable[QRect]) -> bool:
    """Require a useful portion of a restored window to remain on-screen."""
    if rect.isEmpty():
        return False
    required_width = min(120, rect.width())
    required_height = min(80, rect.height())
    return any(
        (intersection := rect.intersected(screen)).width() >= required_width
        and intersection.height() >= required_height
        for screen in screen_rects
    )


class ApplicationSettings:
    """Read and write only the small set of preferences BookForge retains."""

    def __init__(self, backend: QSettings | None = None) -> None:
        self.backend = backend or QSettings()

    def restore_geometry(self, window: QWidget) -> bool:
        stored = self.backend.value(WINDOW_GEOMETRY_KEY)
        restored = isinstance(stored, QByteArray) and window.restoreGeometry(stored)
        screens = tuple(screen.availableGeometry() for screen in QGuiApplication.screens())
        if restored and geometry_is_visible(window.frameGeometry(), screens):
            return True
        self.center_window(window)
        return False

    def save_geometry(self, window: QWidget) -> None:
        self.backend.setValue(WINDOW_GEOMETRY_KEY, window.saveGeometry())

    def output_folder(self) -> Path | None:
        raw_value = str(self.backend.value(OUTPUT_FOLDER_KEY, "") or "").strip()
        if not raw_value:
            return None
        folder = Path(raw_value).expanduser()
        if folder.is_dir():
            return folder.resolve()
        self.backend.remove(OUTPUT_FOLDER_KEY)
        return None

    def save_output_folder(self, folder: Path | None) -> None:
        if folder is None:
            self.backend.remove(OUTPUT_FOLDER_KEY)
        else:
            self.backend.setValue(OUTPUT_FOLDER_KEY, str(folder))

    def global_format(self, valid_formats: set[str], default: str) -> str:
        value = str(self.backend.value(GLOBAL_FORMAT_KEY, default))
        return value if value in valid_formats else default

    def overwrite_policy(self, valid_policies: set[str], default: str) -> str:
        value = str(self.backend.value(OVERWRITE_POLICY_KEY, default))
        return value if value in valid_policies else default

    def save_conversion_choices(self, output_format: str, policy: str) -> None:
        self.backend.setValue(GLOBAL_FORMAT_KEY, output_format)
        self.backend.setValue(OVERWRITE_POLICY_KEY, policy)
        self.backend.sync()

    def language(self, valid_languages: set[str], default: str = "en") -> str:
        value = str(self.backend.value(LANGUAGE_KEY, default))
        return value if value in valid_languages else default

    def theme(self, valid_themes: set[str], default: str = "system") -> str:
        value = str(self.backend.value(THEME_KEY, default))
        return value if value in valid_themes else default

    def save_appearance(self, language: str, theme: str) -> None:
        self.backend.setValue(LANGUAGE_KEY, language)
        self.backend.setValue(THEME_KEY, theme)
        self.backend.sync()

    @staticmethod
    def center_window(window: QWidget) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        frame = window.frameGeometry()
        frame.moveCenter(available.center())
        window.move(frame.topLeft())
