"""
ui/main_window.py
-------------------
Cua so chinh cua app. Dung QStackedWidget de chua nhieu man hinh
(view) va chuyen doi giua chung.

Da noi: ModeSelectView -> EcgRecordingView (mode "ECG real-time")
                        -> PatientPanel (mode "Heart Rate Control", buoc 1)
Con lai: HrRestView, ArduinoCheckView, SessionView... chua viet.
"""

from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox

from ui.mode_select_view import ModeSelectView
from ui.ecg_recording_view import EcgRecordingView
from ui.patient_panel import PatientPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ergometer Control System")
        self.resize(900, 600)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self._setup_mode_select()
        self._setup_ecg_recording()
        self._setup_patient_panel()

    def _setup_mode_select(self):
        self.mode_select_view = ModeSelectView()
        self.mode_select_view.mode_selected.connect(self._on_mode_selected)
        self.stack.addWidget(self.mode_select_view)
        self.stack.setCurrentWidget(self.mode_select_view)

    def _setup_ecg_recording(self):
        self.ecg_recording_view = EcgRecordingView()
        self.ecg_recording_view.back_to_menu.connect(self._on_back_to_menu)
        self.stack.addWidget(self.ecg_recording_view)

    def _setup_patient_panel(self):
        self.patient_panel = PatientPanel()
        self.patient_panel.back_to_menu.connect(self._on_back_to_menu)
        self.patient_panel.patient_ready.connect(self._on_patient_ready)
        self.stack.addWidget(self.patient_panel)

    def _on_mode_selected(self, mode: str):
        if mode == "ecg_realtime":
            self.ecg_recording_view.reset()
            self.stack.setCurrentWidget(self.ecg_recording_view)
        elif mode == "heart_rate_control":
            self.patient_panel.reset()
            self.stack.setCurrentWidget(self.patient_panel)

    def _on_patient_ready(self, patient):
        # TAM THOI: HrRestView chua duoc viet
        QMessageBox.information(
            self, "OK",
            f"Da nhan PatientProfile cho {patient.name}.\n"
            "(HrRestView se duoc noi vao buoc tiep theo)"
        )

    def _on_back_to_menu(self):
        self.stack.setCurrentWidget(self.mode_select_view)
