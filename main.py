"""
main.py
--------
Entry point THẬT của app. Chạy file này để mở cửa sổ ứng dụng.

Chạy: python main.py   (PHẢI chạy từ thư mục gốc repo để tìm thấy mpdev.dll
                        + xerces-c_3_1.dll khi dùng phần cứng MP36 thật)
"""

import sys
import multiprocessing as mp
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    # BAT BUOC cho tang thu tin hieu: signals/acquisition.py chay _acq_worker
    # trong multiprocessing.Process de noi chuyen voi mpdev.dll (BIOPAC MP36).
    # Tren Windows spawn la mac dinh, nhung dat tuong minh de dam bao child
    # process spawn dung (khong fork) - neu khong, viec spawn co the loi khi
    # dong goi .exe hoac chay o moi truong khac. force=True de goi lai an toan.
    mp.set_start_method('spawn', force=True)

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
        QLineEdit {
            background-color: white;
            border: 1px solid #bdbdbd;
            border-radius: 3px;
            padding: 3px 6px;
        }
        /* KHONG style QComboBox/QSpinBox bang border+padding: lam Qt chuyen
           sang che do ve-bang-stylesheet khien mui ten tang/giam mat chuc nang
           va con tro thanh I-beam. De native, van tu trang tren nen trang. */
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
