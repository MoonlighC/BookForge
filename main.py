"""BookForge application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from bookforge.ui.main_window import MainWindow
from bookforge.ui.styles import APP_STYLESHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("BookForge")
    app.setOrganizationName("BookForge")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
