from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from bookforge.i18n import ENGLISH, GERMAN, RUSSIAN, Translator
from bookforge.theme import apply_theme
from bookforge.ui.preferences_dialog import PreferencesDialog


class LocalizationAndThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self) -> None:
        apply_theme(self.app, "light")

    def test_translation_catalogs_cover_every_english_key(self) -> None:
        self.assertFalse(set(ENGLISH) - set(GERMAN))
        self.assertFalse(set(ENGLISH) - set(RUSSIAN))

    def test_fallback_and_book_pluralization(self) -> None:
        self.assertEqual(Translator("unknown").language, "en")
        self.assertEqual(Translator("de").books(1), "1 Buch")
        self.assertEqual(Translator("ru").books(2), "2 книги")
        self.assertEqual(Translator("ru").books(5), "5 книг")

    def test_preferences_use_stable_values_and_native_language_names(self) -> None:
        dialog = PreferencesDialog(Translator("de"), "ru", "dark")
        self.assertEqual(dialog.windowTitle(), "Einstellungen")
        self.assertEqual(dialog.selected_language, "ru")
        self.assertEqual(dialog.language_combo.currentText(), "Русский")
        self.assertEqual(dialog.selected_theme, "dark")
        self.assertEqual(dialog.theme_combo.currentText(), "Dunkel")

    def test_light_and_dark_apply_distinct_real_palettes(self) -> None:
        apply_theme(self.app, "light")
        light = self.app.palette().color(QPalette.ColorRole.Window).name()
        light_sheet = self.app.styleSheet()
        apply_theme(self.app, "dark")
        dark = self.app.palette().color(QPalette.ColorRole.Window).name()
        dark_sheet = self.app.styleSheet()
        self.assertEqual(light, "#f5f7fb")
        self.assertEqual(dark, "#111827")
        self.assertNotEqual(light_sheet, dark_sheet)
        self.assertIn("chevron-down-dark.svg", dark_sheet)

    def test_system_theme_resolves_and_keeps_system_selection(self) -> None:
        resolved = apply_theme(self.app, "system")
        self.assertIn(resolved, {"light", "dark"})
        self.assertEqual(self.app.property("bookforgeThemeMode"), "system")

    def test_theme_palettes_have_readable_text_contrast(self) -> None:
        def luminance(hex_color: str) -> float:
            values = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in values]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        for theme in ("light", "dark"):
            apply_theme(self.app, theme)
            palette = self.app.palette()
            foreground = luminance(palette.color(QPalette.ColorRole.Text).name())
            background = luminance(palette.color(QPalette.ColorRole.Base).name())
            brighter, darker = max(foreground, background), min(foreground, background)
            self.assertGreaterEqual((brighter + 0.05) / (darker + 0.05), 4.5)


if __name__ == "__main__":
    unittest.main()
