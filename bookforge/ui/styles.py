"""Application-wide Qt stylesheet."""

from bookforge.resources import resource_path

APP_STYLESHEET = """
QWidget {
    background: #f5f7fb;
    color: #182230;
    font-family: "Segoe UI";
    font-size: 14px;
}

QMainWindow {
    background: #f5f7fb;
}

QMenuBar {
    background: #ffffff;
    border-bottom: 1px solid #e4e7ec;
    padding: 2px 6px;
}

QMenuBar::item {
    background: transparent;
    border-radius: 5px;
    padding: 5px 9px;
}

QMenu {
    background: #ffffff;
    border: 1px solid #dfe4ec;
    padding: 5px;
}

QMenu::item {
    background: transparent;
    border-radius: 5px;
    padding: 7px 24px 7px 10px;
}

QMenu::separator {
    background: #e4e7ec;
    height: 1px;
    margin: 4px 8px;
}

QMenuBar::item:selected,
QMenu::item:selected {
    background: #edf3ff;
    color: #244f9f;
}

QLabel#appTitle {
    color: #101828;
    font-size: 30px;
    font-weight: 700;
}

QLabel#subtitle {
    color: #667085;
    font-size: 15px;
}

QLabel#sectionLabel {
    background: transparent;
    color: #344054;
    font-size: 13px;
    font-weight: 600;
}

QLabel#sectionTitle {
    color: #1d2939;
    font-size: 16px;
    font-weight: 700;
}

QLabel#formatDescription {
    background: transparent;
    color: #667085;
    font-size: 12px;
}

QLabel#selectedFile {
    background: #ffffff;
    border: 1px solid #dfe4ec;
    border-radius: 9px;
    color: #344054;
    padding: 11px 13px;
}

QLabel#warningBanner {
    background: #fff8e7;
    border: 1px solid #f4d58d;
    border-radius: 9px;
    color: #7a4f01;
    padding: 11px 13px;
}

QFrame#dropArea {
    background: #ffffff;
    border: 2px dashed #b8c2d3;
    border-radius: 16px;
}

QFrame#dropArea:hover,
QFrame#dropArea[dragActive="true"] {
    background: #f1f6ff;
    border-color: #4f7ee8;
}

QFrame#dropArea[dragActive="true"] {
    border-style: solid;
}

QFrame#controlsPanel,
QFrame#queueItem {
    background: #ffffff;
    border: 1px solid #dfe4ec;
    border-radius: 12px;
}

QFrame#queueItem:hover {
    border-color: #c2cad6;
}

QScrollArea#queueScroll,
QWidget#queueContainer,
QScrollArea#queueScroll > QWidget > QWidget {
    background: transparent;
    border: none;
}

QLabel#emptyQueue {
    color: #98a2b3;
    padding: 28px;
}

QLabel#queueFilename {
    background: transparent;
    color: #1d2939;
    font-size: 15px;
    font-weight: 650;
}

QLabel#queueDetails,
QLabel#subtleNote {
    background: transparent;
    color: #667085;
    font-size: 12px;
}

QLabel#conversionArrow {
    background: transparent;
    color: #4f7ee8;
    font-size: 17px;
    font-weight: 700;
}

QLabel#queueStatus {
    background: #eef2f7;
    border-radius: 11px;
    color: #475467;
    font-size: 12px;
    font-weight: 650;
    padding: 4px 9px;
}

QLabel#queueStatus[queueState="ready"] {
    background: #eef2f7;
    color: #475467;
}

QLabel#queueStatus[queueState="waiting"] {
    background: #fff5d9;
    color: #815b00;
}

QLabel#queueStatus[queueState="converting"] {
    background: #e9f0ff;
    color: #2859bd;
}

QLabel#queueStatus[queueState="completed"] {
    background: #e8f7ef;
    color: #18794e;
}

QLabel#queueStatus[queueState="failed"] {
    background: #ffebeb;
    color: #b42318;
}

QLabel#queueStatus[queueState="cancelled"] {
    background: #fff4e5;
    color: #854a0e;
}

QLabel#queueStatus[queueState="skipped"] {
    background: #fff5d9;
    color: #815b00;
}

QLabel#queueError {
    background: transparent;
    color: #b42318;
    font-size: 12px;
}

QLabel#dropIcon {
    background: transparent;
    color: #4f7ee8;
    font-size: 32px;
    font-weight: 300;
}

QLabel#dropTitle {
    background: transparent;
    color: #1d2939;
    font-size: 18px;
    font-weight: 650;
}

QLabel#dropHint {
    background: transparent;
    color: #667085;
}

QLabel#dropFormats {
    background: transparent;
    color: #4f6f9f;
    font-size: 12px;
    font-weight: 600;
}

QLabel#coverPreview {
    background: #eef2f7;
    border: 1px solid #d0d5dd;
    border-radius: 10px;
    color: #667085;
    font-size: 13px;
}

QLabel#inputFormat {
    background: transparent;
    color: #667085;
    font-size: 12px;
}

QComboBox,
QLineEdit {
    min-height: 40px;
    background: #ffffff;
    border: 1px solid #d0d5dd;
    border-radius: 8px;
    padding: 0 12px;
    selection-background-color: #4f7ee8;
}

QComboBox {
    padding-right: 34px;
}

QComboBox:focus,
QLineEdit:focus {
    border: 1px solid #4f7ee8;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    background: #f8fafc;
    border: none;
    border-left: 1px solid #e4e7ec;
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
}

QComboBox::down-arrow {
    image: url("__BOOKFORGE_COMBO_ARROW__");
    width: 10px;
    height: 7px;
}

QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #c7ced8;
    border-radius: 7px;
    outline: none;
    padding: 4px;
    selection-background-color: #e8f0ff;
    selection-color: #1d2939;
}

QComboBox#itemFormatCombo {
    min-height: 32px;
    max-height: 32px;
    min-width: 105px;
    padding-left: 10px;
}

QPushButton {
    min-height: 40px;
    background: #ffffff;
    border: 1px solid #d0d5dd;
    border-radius: 8px;
    color: #344054;
    font-weight: 600;
    padding: 0 17px;
}

QPushButton:hover {
    background: #f9fafb;
    border-color: #98a2b3;
}

QPushButton#primaryButton {
    min-height: 44px;
    background: #3568d4;
    border: 1px solid #3568d4;
    border-radius: 10px;
    color: #ffffff;
    font-size: 15px;
    padding: 0 30px;
}

QPushButton#primaryButton:hover {
    background: #2859bd;
}

QPushButton#primaryButton:disabled {
    background: #aebfe4;
    border-color: #aebfe4;
}

QPushButton#removeButton {
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    border: none;
    border-radius: 16px;
    color: #667085;
    font-size: 20px;
    padding: 0;
}

QPushButton#removeButton:hover {
    background: #feecec;
    color: #b42318;
}

QPushButton#compactButton {
    min-height: 30px;
    max-height: 30px;
    padding: 0 11px;
    font-size: 12px;
}

QPushButton#cancelButton {
    border-color: #f0b64d;
    color: #815b00;
}

QPushButton#cancelButton:hover {
    background: #fff8e7;
    border-color: #d79b2c;
}

QPushButton#dangerButton {
    border-color: #e5a4a0;
    color: #b42318;
}

QPushButton#dangerButton:hover {
    background: #fff0ef;
    border-color: #d46b63;
}

QProgressBar {
    min-height: 6px;
    max-height: 6px;
    background: #e4e7ec;
    border: none;
    border-radius: 3px;
    text-align: center;
}

QProgressBar::chunk {
    background: #4f7ee8;
    border-radius: 3px;
}

QProgressBar#itemProgress {
    min-height: 18px;
    max-height: 18px;
    background: #e9edf3;
    border-radius: 5px;
    color: #344054;
    font-size: 11px;
    font-weight: 600;
}

QProgressBar#itemProgress::chunk {
    background: #5a80d8;
    border-radius: 5px;
}

QProgressBar#batchProgress {
    min-height: 8px;
    max-height: 8px;
}

QPlainTextEdit#logView {
    background: #f8fafc;
    border: 1px solid #e1e6ed;
    border-radius: 7px;
    color: #344054;
    font-family: Consolas, "Courier New";
    font-size: 11px;
    padding: 7px;
}

QLabel#statusLabel {
    color: #475467;
    font-size: 13px;
}

QPushButton:pressed {
    background: #edf3ff;
    border-color: #4f7ee8;
}

QPushButton:disabled,
QComboBox:disabled,
QLineEdit:disabled {
    background: #eef2f7;
    border-color: #dfe4ec;
    color: #98a2b3;
}

QToolTip {
    background: #ffffff;
    border: 1px solid #c7ced8;
    border-radius: 5px;
    color: #344054;
    padding: 5px 7px;
}

QFrame#resultPanel {
    background: #ffffff;
    border: 1px solid #dfe4ec;
    border-radius: 12px;
}

QFrame#resultPanel QLabel {
    background: transparent;
    border: none;
}

QLabel#resultTitle {
    color: #18794e;
    font-size: 15px;
    font-weight: 700;
}

QLabel#resultName {
    color: #1d2939;
    font-size: 17px;
    font-weight: 650;
}

QLabel#resultLocation {
    color: #667085;
    font-size: 12px;
}
"""


DARK_COLOR_MAP = {
    "#f5f7fb": "#111827", "#182230": "#e5e7eb", "#ffffff": "#182230",
    "#e4e7ec": "#354154", "#edf3ff": "#263b62", "#244f9f": "#a9c4ff",
    "#101828": "#f8fafc", "#667085": "#aab4c3", "#344054": "#d7dee8",
    "#1d2939": "#f1f5f9", "#dfe4ec": "#354154", "#fff8e7": "#3c3020",
    "#f4d58d": "#765c26", "#7a4f01": "#ffd781", "#b8c2d3": "#64748b",
    "#f1f6ff": "#20304b", "#4f7ee8": "#6f98f5", "#c2cad6": "#64748b",
    "#98a2b3": "#8390a3", "#eef2f7": "#263244", "#475467": "#c0cad8",
    "#fff5d9": "#3c3420", "#815b00": "#f5d06f", "#e9f0ff": "#243657",
    "#2859bd": "#9ab9ff", "#e8f7ef": "#1d3a31", "#18794e": "#7dd3ad",
    "#ffebeb": "#452829", "#b42318": "#ff9b93", "#fff4e5": "#423122",
    "#854a0e": "#ffc078", "#4f6f9f": "#9eb9e5", "#d0d5dd": "#526074",
    "#f8fafc": "#202b3b", "#c7ced8": "#526074", "#e8f0ff": "#2b436c",
    "#3568d4": "#517fe2", "#f9fafb": "#293547", "#aebfe4": "#43516a",
    "#feecec": "#48282b", "#f0b64d": "#c9913c", "#d79b2c": "#dea746",
    "#e5a4a0": "#9b5d5c", "#fff0ef": "#442729", "#d46b63": "#b86965",
    "#e9edf3": "#293547", "#5a80d8": "#7197ed", "#e1e6ed": "#354154",
}


def application_stylesheet(theme: str = "light") -> str:
    arrow_asset = (
        "assets/chevron-down-dark.svg"
        if theme == "dark"
        else "assets/chevron-down.svg"
    )
    arrow = resource_path(arrow_asset).as_posix()
    stylesheet = APP_STYLESHEET
    if theme == "dark":
        import re

        stylesheet = re.sub(
            r"#[0-9a-fA-F]{6}",
            lambda match: DARK_COLOR_MAP.get(match.group(0).lower(), match.group(0)),
            stylesheet,
        )
    return stylesheet.replace("__BOOKFORGE_COMBO_ARROW__", arrow)
