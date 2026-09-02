"""Locate bundled and source-tree application resources."""

from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtGui import QIcon


def resource_path(relative_path: str | Path) -> Path:
    """Return a resource path in source and PyInstaller one-folder builds."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    root = Path(bundle_root) if bundle_root else Path(__file__).resolve().parents[1]
    return root / Path(relative_path)


def application_icon() -> QIcon:
    icon_path = resource_path(Path("assets") / "bookforge.ico")
    return QIcon(str(icon_path)) if icon_path.is_file() else QIcon()
