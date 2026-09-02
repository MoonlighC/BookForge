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
from bookforge.i18n import Translator


class MetadataDialog(QDialog):
    def __init__(
        self,
        filename: str,
        original: BookMetadata,
        current: BookMetadata,
        parent: QWidget | None = None,
        translator: Translator | None = None,
    ) -> None:
        super().__init__(parent)
        self._translator = translator or Translator()
        tr = self._translator.tr
        self._original = original
        self._selected_cover_path = current.cover_path
        self._saved_metadata: BookMetadata | None = None
        self.setWindowTitle(tr("metadata.dialog_title", filename=filename))
        self.setModal(True)
        self.resize(760, 570)
        self.setMinimumSize(680, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(16)

        note = QLabel(tr("metadata.note"))
        note.setObjectName("subtleNote")
        note.setWordWrap(True)
        root.addWidget(note)

        content = QHBoxLayout()
        content.setSpacing(22)
        cover_column = QVBoxLayout()
        cover_column.setSpacing(8)
        cover_label = QLabel(tr("metadata.cover"))
        cover_label.setObjectName("sectionLabel")
        self._cover_preview = QLabel(tr("metadata.no_cover"))
        self._cover_preview.setObjectName("coverPreview")
        self._cover_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover_preview.setFixedSize(220, 300)
        self._cover_preview.setAccessibleName(tr("metadata.cover_preview"))
        self._replace_cover = QPushButton(tr("metadata.replace_cover"))
        self._replace_cover.setAccessibleName(tr("metadata.choose_cover_accessible"))
        self._replace_cover.clicked.connect(self._choose_cover)
        cover_column.addWidget(cover_label)
        cover_column.addWidget(self._cover_preview)
        cover_column.addWidget(self._replace_cover)
        cover_column.addStretch(1)

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        self._title = QLineEdit()
        self._title.setAccessibleName(tr("metadata.title"))
        self._authors = QLineEdit()
        self._authors.setAccessibleName(tr("metadata.authors_accessible"))
        self._authors.setPlaceholderText(tr("metadata.authors_placeholder"))
        self._language = QLineEdit()
        self._language.setAccessibleName(tr("metadata.language"))
        self._language.setPlaceholderText(tr("metadata.language_placeholder"))
        self._publisher = QLineEdit()
        self._publisher.setAccessibleName(tr("metadata.publisher"))
        self._series = QLineEdit()
        self._series.setAccessibleName(tr("metadata.series"))
        self._series_index = QLineEdit()
        self._series_index.setAccessibleName(tr("metadata.series_index"))
        index_validator = QDoubleValidator(self)
        index_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        index_validator.setLocale(QLocale.c())
        self._series_index.setValidator(index_validator)
        self._tags = QLineEdit()
        self._tags.setAccessibleName(tr("metadata.tags"))
        self._tags.setPlaceholderText(tr("metadata.tags_placeholder"))
        form.addRow(tr("metadata.title"), self._title)
        form.addRow(tr("metadata.authors"), self._authors)
        form.addRow(tr("metadata.language"), self._language)
        form.addRow(tr("metadata.publisher"), self._publisher)
        form.addRow(tr("metadata.series"), self._series)
        form.addRow(tr("metadata.series_index"), self._series_index)
        form.addRow(tr("metadata.tags"), self._tags)

        content.addLayout(cover_column)
        content.addLayout(form, 1)
        root.addLayout(content, 1)

        actions = QHBoxLayout()
        reset_button = QPushButton(tr("metadata.reset"))
        reset_button.setAccessibleName(tr("metadata.reset_accessible"))
        reset_button.clicked.connect(self._reset_to_original)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_button is not None:
            save_button.setText(tr("metadata.save"))
            save_button.setDefault(True)
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button is not None:
            cancel_button.setText(tr("metadata.cancel"))
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
            self._translator.tr("metadata.select_cover"),
            start,
            f'{self._translator.tr("metadata.cover_images")} (*.jpg *.jpeg *.png)',
        )
        if not filename:
            return
        path = Path(filename)
        if not self._is_readable_cover(path):
            QMessageBox.warning(
                self,
                self._translator.tr("metadata.invalid_cover"),
                self._translator.tr("metadata.invalid_cover_text"),
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
                self._translator.tr("metadata.invalid_cover"),
                self._translator.tr("metadata.cover_unreadable"),
            )
            return
        try:
            metadata = self._metadata_from_fields()
        except ValueError:
            QMessageBox.warning(
                self,
                self._translator.tr("metadata.invalid_series"),
                self._translator.tr("metadata.invalid_series_text"),
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
            self._cover_preview.setText(self._translator.tr("metadata.no_cover"))
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._cover_preview.setPixmap(QPixmap())
            self._cover_preview.setText(self._translator.tr("metadata.no_cover"))
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
