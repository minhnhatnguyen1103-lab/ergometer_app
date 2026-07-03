"""
main.py
--------
Entry point THẬT của app. Chạy file này để mở cửa sổ ứng dụng.

Chạy: python main.py
"""

import sys
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { background-color: white; color: #212121; }
        QPushButton {
            background-color: #f0f0f0;
            border: 1px solid #bdbdbd;
            border-radius: 4px;
            padding: 4px 10px;
        }
        QPushButton:hover { background-color: #e0e0e0; }
        QPushButton:pressed { background-color: #d0d0d0; }
        QPushButton:disabled { background-color: #f5f5f5; color: #9e9e9e; border-color: #dddddd; }
        QLineEdit, QComboBox, QSpinBox {
            background-color: white;
            border: 1px solid #bdbdbd;
            border-radius: 3px;
            padding: 3px 6px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #9e9e9e;
            border-radius: 3px;
            background-color: white;
        }
        QCheckBox::indicator:checked {
            background-color: #1565c0;
            border-color: #1565c0;
        }
    """)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
