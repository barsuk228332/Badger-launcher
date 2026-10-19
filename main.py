import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

GRUVBOX_QSS = """
QWidget {
    background-color: #282828;
    color: #ebdbb2;
    font-family: "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #504945;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    color: #fe8019;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QLineEdit, QComboBox, QListWidget, QTextEdit, QTableWidget {
    background-color: #1d2021;
    border: 1px solid #504945;
    border-radius: 4px;
    padding: 5px;
    color: #ebdbb2;
    selection-background-color: #d65d0e;
    selection-color: #282828;
}
QPushButton {
    background-color: #3c3836;
    border: 1px solid #504945;
    border-radius: 4px;
    padding: 6px 12px;
    color: #ebdbb2;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #504945;
    border-color: #fabd2f;
}
QPushButton:pressed {
    background-color: #d65d0e;
    color: #282828;
}
QPushButton:disabled {
    background-color: #282828;
    color: #7c6f64;
    border-color: #3c3836;
}
QTabWidget::pane {
    border: 1px solid #504945;
    border-radius: 4px;
}
QTabBar::tab {
    background-color: #1d2021;
    border: 1px solid #504945;
    padding: 7px 14px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #3c3836;
    border-bottom: 2px solid #fabd2f;
    color: #fabd2f;
    font-weight: bold;
}
QProgressBar {
    border: 1px solid #504945;
    border-radius: 4px;
    text-align: center;
    background-color: #1d2021;
}
QProgressBar::chunk {
    background-color: #b8bb26;
}
QHeaderView::section {
    background-color: #3c3836;
    color: #fabd2f;
    padding: 4px;
    border: 1px solid #504945;
}
"""


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(GRUVBOX_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()