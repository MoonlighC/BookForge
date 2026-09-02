"""Application-wide Qt stylesheet."""

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
    background: #f3f7ff;
    border-color: #4f7ee8;
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
    background: #f2f4f7;
    color: #475467;
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
    font-size: 38px;
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

QComboBox:focus,
QLineEdit:focus {
    border: 1px solid #4f7ee8;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
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
    min-height: 48px;
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
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    border: none;
    border-radius: 14px;
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
