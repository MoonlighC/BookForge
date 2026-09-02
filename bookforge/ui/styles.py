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
