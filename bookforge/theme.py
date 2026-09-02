"""Application-wide light, dark, and system theme handling."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

from bookforge.ui.styles import application_stylesheet


THEMES = {"system", "light", "dark"}


def resolved_theme(mode: str) -> str:
    """Resolve System from Qt's current platform color scheme."""
    if mode == "dark":
        return "dark"
    if mode == "system":
        hints = QGuiApplication.styleHints()
        if hints.colorScheme() is Qt.ColorScheme.Dark:
            return "dark"
    return "light"


def apply_theme(app: QApplication, mode: str) -> str:
    """Apply an explicit Fusion palette and stylesheet to the whole app."""
    selected = mode if mode in THEMES else "system"
    resolved = resolved_theme(selected)
    palette = QPalette()
    colors = _DARK_PALETTE if resolved == "dark" else _LIGHT_PALETTE
    for role, value in colors.items():
        palette.setColor(role, QColor(value))
    disabled_text = "#728096" if resolved == "dark" else "#98a2b3"
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(disabled_text))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(disabled_text))
    app.setPalette(palette)
    app.setStyleSheet(application_stylesheet(resolved))
    app.setProperty("bookforgeThemeMode", selected)
    app.setProperty("bookforgeTheme", resolved)
    return resolved


_LIGHT_PALETTE = {
    QPalette.ColorRole.Window: "#f5f7fb",
    QPalette.ColorRole.WindowText: "#182230",
    QPalette.ColorRole.Base: "#ffffff",
    QPalette.ColorRole.AlternateBase: "#f8fafc",
    QPalette.ColorRole.ToolTipBase: "#ffffff",
    QPalette.ColorRole.ToolTipText: "#344054",
    QPalette.ColorRole.Text: "#182230",
    QPalette.ColorRole.Button: "#ffffff",
    QPalette.ColorRole.ButtonText: "#344054",
    QPalette.ColorRole.Highlight: "#4f7ee8",
    QPalette.ColorRole.HighlightedText: "#ffffff",
    QPalette.ColorRole.PlaceholderText: "#98a2b3",
}

_DARK_PALETTE = {
    QPalette.ColorRole.Window: "#111827",
    QPalette.ColorRole.WindowText: "#e5e7eb",
    QPalette.ColorRole.Base: "#182230",
    QPalette.ColorRole.AlternateBase: "#1f2937",
    QPalette.ColorRole.ToolTipBase: "#263244",
    QPalette.ColorRole.ToolTipText: "#f1f5f9",
    QPalette.ColorRole.Text: "#e5e7eb",
    QPalette.ColorRole.Button: "#202b3b",
    QPalette.ColorRole.ButtonText: "#e5e7eb",
    QPalette.ColorRole.Highlight: "#6f98f5",
    QPalette.ColorRole.HighlightedText: "#ffffff",
    QPalette.ColorRole.PlaceholderText: "#8390a3",
}
