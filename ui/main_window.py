"""
ui/main_window.py
-------------------
Cửa sổ chính của app. Dùng QStackedWidget để chứa nhiều màn hình
(view) và chuyển đổi giữa chúng — giống như "chuyển tab" nhưng
người dùng không thấy tab, chỉ thấy nội dung đổi.

Hiện tại chỉ có 1 màn hình (ModeSelectView). Khi PatientPanel,
HrRestView... được viết xong, chúng sẽ được add vào đây và
MainWindow sẽ quyết định lúc nào hiện màn hình nào.
"""

from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox

from ui.mode_select_view import ModeSelectView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ergometer Control System")
        self.resize(720, 480)

        # QStackedWidget: chứa nhiều "trang", chỉ hiện 1 trang tại 1 thời điểm
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self._setup_mode_select()

    def _setup_mode_select(self):
        self.mode_select_view = ModeSelectView()
        self.mode_select_view.mode_selected.connect(self._on_mode_selected)
        self.stack.addWidget(self.mode_select_view)
        self.stack.setCurrentWidget(self.mode_select_view)

    def _on_mode_selected(self, mode: str):
        # TẠM THỜI: các màn hình tiếp theo (EcgRecordingView, PatientPanel)
        # chưa được viết, nên chỉ hiện thông báo xác nhận signal hoạt động
        # đúng. Khi các view đó có, dòng QMessageBox này sẽ được thay bằng
        # self.stack.addWidget(...) + self.stack.setCurrentWidget(...).
        if mode == "ecg_realtime":
            QMessageBox.information(
                self, "OK", "Đã nhận lựa chọn: Đo ECG real-time.\n"
                "(Màn hình thật sẽ được nối vào bước tiếp theo)"
            )
        elif mode == "heart_rate_control":
            QMessageBox.information(
                self, "OK", "Đã nhận lựa chọn: Heart Rate Control.\n"
                "(Màn hình thật sẽ được nối vào bước tiếp theo)"
            )
