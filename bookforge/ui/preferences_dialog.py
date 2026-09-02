"""Preferences dialog for language and appearance."""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)

from bookforge.i18n import LANGUAGES, Translator


class PreferencesDialog(QDialog):
    def __init__(
        self,
        translator: Translator,
        language: str,
        theme: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._translator = translator
        self.setWindowTitle(translator.tr("preferences.title"))
        self.setModal(True)
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(20)
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)
        self.language_combo = QComboBox()
        for code, native_name in LANGUAGES.items():
            self.language_combo.addItem(native_name, code)
        self.language_combo.setCurrentIndex(self.language_combo.findData(language))
        self.theme_combo = QComboBox()
        for mode in ("system", "light", "dark"):
            self.theme_combo.addItem(translator.tr(f"preferences.{mode}"), mode)
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(theme))
        form.addRow(translator.tr("preferences.language"), self.language_combo)
        form.addRow(translator.tr("preferences.theme"), self.theme_combo)
        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save = buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if save is not None:
            save.setText(translator.tr("preferences.save"))
            save.setDefault(True)
        if cancel is not None:
            cancel.setText(translator.tr("preferences.cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @property
    def selected_language(self) -> str:
        return str(self.language_combo.currentData())

    @property
    def selected_theme(self) -> str:
        return str(self.theme_combo.currentData())
