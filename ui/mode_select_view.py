"""
ui/mode_select_view.py
------------------------
Màn hình đầu tiên người dùng thấy khi mở app. Chỉ có 2 nút bấm,
chưa có logic phức tạp — đây là bước "làm quen" với PyQt6.

Khái niệm PyQt6 quan trọng dùng ở đây (giải thích cho người mới):
- QWidget: 1 "khung" chứa các thành phần giao diện (nút, chữ...)
- Layout (QVBoxLayout): sắp xếp các thành phần theo chiều dọc, tự động
  canh chỉnh — không cần tự tính toán vị trí pixel.
- Signal/Slot: khi bấm nút (signal "clicked"), 1 hàm sẽ tự chạy (slot).
  Đây là cách PyQt6 xử lý "khi người dùng làm gì đó thì chạy cái gì".
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal


class ModeSelectView(QWidget):
    # Signal tùy chỉnh: phát ra khi người dùng chọn 1 mode, kèm tên mode.
    # MainWindow sẽ "lắng nghe" signal này để biết chuyển sang màn hình nào.
    mode_selected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(24)
        layout.setContentsMargins(60, 80, 60, 80)

        title = QLabel("Ergometer Control System")
        title.setStyleSheet("font-size: 22px; font-weight: 500;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Chọn chế độ hoạt động")
        subtitle.setStyleSheet("font-size: 14px; color: gray;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_ecg = QPushButton("Đo ECG real-time")
        btn_ecg.setMinimumHeight(56)
        btn_ecg.setStyleSheet("font-size: 15px;")
        btn_ecg.clicked.connect(lambda: self.mode_selected.emit("ecg_realtime"))

        btn_hrc = QPushButton("Heart Rate Control")
        btn_hrc.setMinimumHeight(56)
        btn_hrc.setStyleSheet("font-size: 15px; font-weight: 500;")
        btn_hrc.clicked.connect(lambda: self.mode_selected.emit("heart_rate_control"))

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)
        layout.addWidget(btn_ecg)
        layout.addWidget(btn_hrc)

        self.setLayout(layout)
