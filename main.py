"""BookForge application entry point."""

from __future__ import annotations

import sys
import logging
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication, QMessageBox

from bookforge import __version__
from bookforge.resources import application_icon
from bookforge.i18n import LANGUAGES, Translator
from bookforge.settings import APPLICATION_NAME, ORGANIZATION_NAME, ApplicationSettings
from bookforge.theme import THEMES, apply_theme
from bookforge.ui.main_window import MainWindow


def configure_application(app: QApplication) -> None:
    """Set stable desktop and QSettings identity before creating windows."""
    app.setApplicationName(APPLICATION_NAME)
    app.setApplicationDisplayName(APPLICATION_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setDesktopFileName("BookForge")
    app.setWindowIcon(application_icon())
    app.setStyle("Fusion")
    settings = ApplicationSettings()
    apply_theme(app, settings.theme(THEMES))


def configure_runtime_logging() -> Path | None:
    """Prepare a delayed warning log for packaged startup diagnostics."""
    try:
        folder = Path(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppLocalDataLocation
            )
        )
        folder.mkdir(parents=True, exist_ok=True)
        log_path = folder / "bookforge.log"
        handler = logging.FileHandler(log_path, encoding="utf-8", delay=True)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.WARNING)
        root_logger.addHandler(handler)
        return log_path
    except OSError:
        return None


def main() -> int:
    app = QApplication(sys.argv)
    configure_application(app)
    log_path = configure_runtime_logging()
    try:
        window = MainWindow()
        window.show()
    except Exception:
        logging.exception("BookForge could not start")
        settings = ApplicationSettings()
        translator = Translator(settings.language(set(LANGUAGES)))
        location = (
            "\n\n" + translator.tr("startup.log", path=log_path)
            if log_path
            else ""
        )
        QMessageBox.critical(
            None,
            translator.tr("startup.title"),
            translator.tr("startup.message") + location,
        )
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
