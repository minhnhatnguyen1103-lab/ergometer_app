"""
main.py
--------
Entry point THẬT của app. Chạy file này để mở cửa sổ ứng dụng.

Chạy: python main.py
"""

import sys
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.theme import application_stylesheet


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(application_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
