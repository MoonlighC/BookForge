"""Native dialog for previewing and editing one book's metadata."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QLocale, Qt, Slot
from PySide6.QtGui import QDoubleValidator, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bookforge.core.metadata import BookMetadata, detect_cover_extension


class MetadataDialog(QDialog):
    def __init__(
        self,
        filename: str,
        original: BookMetadata,
        current: BookMetadata,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._original = original
        self._selected_cover_path = current.cover_path
        self._saved_metadata: BookMetadata | None = None
        self.setWindowTitle(f"Edit metadata — {filename}")
        self.setModal(True)
        self.resize(720, 540)
        self.setMinimumSize(650, 500)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(15)

        content = QHBoxLayout()
        content.setSpacing(22)
        cover_column = QVBoxLayout()
        cover_column.setSpacing(8)
        self._cover_preview = QLabel("No cover")
        self._cover_preview.setObjectName("coverPreview")
        self._cover_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover_preview.setFixedSize(220, 300)
        replace_cover = QPushButton("Replace cover")
        replace_cover.clicked.connect(self._choose_cover)
        cover_column.addWidget(self._cover_preview)
        cover_column.addWidget(replace_cover)
        cover_column.addStretch(1)

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        self._title = QLineEdit()
        self._authors = QLineEdit()
        self._authors.setPlaceholderText("Separate multiple authors with semicolons")
        self._language = QLineEdit()
        self._publisher = QLineEdit()
        self._series = QLineEdit()
        self._series_index = QLineEdit()
        index_validator = QDoubleValidator(self)
        index_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        index_validator.setLocale(QLocale.c())
        self._series_index.setValidator(index_validator)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("Comma-separated")
        form.addRow("Title", self._title)
        form.addRow("Author(s)", self._authors)
        form.addRow("Language", self._language)
        form.addRow("Publisher", self._publisher)
        form.addRow("Series", self._series)
        form.addRow("Series index", self._series_index)
        form.addRow("Tags", self._tags)

        content.addLayout(cover_column)
        content.addLayout(form, 1)
        root.addLayout(content, 1)

        actions = QHBoxLayout()
        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self._reset_to_original)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        actions.addWidget(reset_button)
        actions.addStretch(1)
        actions.addWidget(buttons)
        root.addLayout(actions)

        self._populate(current)

    @property
    def saved_metadata(self) -> BookMetadata | None:
        return self._saved_metadata

    @Slot()
    def _choose_cover(self) -> None:
        start = (
            str(self._selected_cover_path.parent)
            if self._selected_cover_path is not None
            else str(Path.home())
        )
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select cover image",
            start,
            "Cover images (*.jpg *.jpeg *.png)",
        )
        if not filename:
            return
        path = Path(filename)
        if not self._is_readable_cover(path):
            QMessageBox.warning(
                self, "Invalid cover", "Select a readable JPG, JPEG, or PNG image."
            )
            return
        self._selected_cover_path = path.resolve()
        self._show_cover(self._selected_cover_path)

    @Slot()
    def _reset_to_original(self) -> None:
        self._selected_cover_path = self._original.cover_path
        self._populate(self._original)

    def accept(self) -> None:
        if (
            self._selected_cover_path is not None
            and self._selected_cover_path != self._original.cover_path
            and not self._is_readable_cover(self._selected_cover_path)
        ):
            QMessageBox.warning(
                self,
                "Invalid cover",
                "The selected replacement cover is no longer readable.",
            )
            return
        try:
            metadata = self._metadata_from_fields()
        except ValueError:
            QMessageBox.warning(
                self, "Invalid series index", "Series index must be a number."
            )
            return
        self._saved_metadata = metadata
        super().accept()

    def _populate(self, metadata: BookMetadata) -> None:
        self._title.setText(metadata.title or "")
        self._authors.setText("; ".join(metadata.authors))
        self._language.setText(metadata.language or "")
        self._publisher.setText(metadata.publisher or "")
        self._series.setText(metadata.series or "")
        self._series_index.setText(
            f"{metadata.series_index:g}"
            if metadata.series_index is not None
            else ""
        )
        self._tags.setText(", ".join(metadata.tags))
        self._show_cover(self._selected_cover_path)

    def _metadata_from_fields(self) -> BookMetadata:
        index_text = self._series_index.text().strip()
        series_index = float(index_text) if index_text else None
        authors = tuple(
            author.strip()
            for author in self._authors.text().split(";")
            if author.strip()
        )
        tags = tuple(
            tag.strip() for tag in self._tags.text().split(",") if tag.strip()
        )
        return BookMetadata(
            title=self._text_or_none(self._title),
            authors=authors,
            language=self._text_or_none(self._language),
            publisher=self._text_or_none(self._publisher),
            series=self._text_or_none(self._series),
            series_index=series_index,
            tags=tags,
            cover_path=self._selected_cover_path,
        )

    @staticmethod
    def _text_or_none(field: QLineEdit) -> str | None:
        value = field.text().strip()
        return value or None

    def _show_cover(self, path: Path | None) -> None:
        if path is None or not path.is_file():
            self._cover_preview.setPixmap(QPixmap())
            self._cover_preview.setText("No cover")
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._cover_preview.setPixmap(QPixmap())
            self._cover_preview.setText("No cover")
            return
        scaled = pixmap.scaled(
            self._cover_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._cover_preview.setText("")
        self._cover_preview.setPixmap(scaled)

    @staticmethod
    def _is_readable_cover(path: Path) -> bool:
        try:
            if path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                return False
            if detect_cover_extension(path.read_bytes()) is None:
                return False
            return not QPixmap(str(path)).isNull()
        except OSError:
            return False
