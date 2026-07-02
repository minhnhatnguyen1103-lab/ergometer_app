"""
ui/main_window.py
-------------------
Cua so chinh cua app. Dung QStackedWidget de chua nhieu man hinh
(view) va chuyen doi giua chung.

Da noi xong: ModeSelectView -> EcgRecordingView (mode "Do ECG real-time").
Con lai: PatientPanel... (mode "Heart Rate Control") van la placeholder.
"""

from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox

from ui.mode_select_view import ModeSelectView
from ui.ecg_recording_view import EcgRecordingView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ergometer Control System")
        self.resize(900, 600)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self._setup_mode_select()
        self._setup_ecg_recording()

    def _setup_mode_select(self):
        self.mode_select_view = ModeSelectView()
        self.mode_select_view.mode_selected.connect(self._on_mode_selected)
        self.stack.addWidget(self.mode_select_view)
        self.stack.setCurrentWidget(self.mode_select_view)

    def _setup_ecg_recording(self):
        self.ecg_recording_view = EcgRecordingView()
        self.ecg_recording_view.back_to_menu.connect(self._on_back_to_menu)
        self.stack.addWidget(self.ecg_recording_view)

    def _on_mode_selected(self, mode: str):
        if mode == "ecg_realtime":
            self.ecg_recording_view.reset()
            self.stack.setCurrentWidget(self.ecg_recording_view)
        elif mode == "heart_rate_control":
            # TAM THOI: PatientPanel chua duoc viet
            QMessageBox.information(
                self, "OK", "Da nhan lua chon: Heart Rate Control.\n"
                "(Man hinh that se duoc noi vao buoc tiep theo)"
            )

    def _on_back_to_menu(self):
        self.stack.setCurrentWidget(self.mode_select_view)
