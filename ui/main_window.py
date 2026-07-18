"""
ui/main_window.py
-------------------
Cua so chinh. Da noi day du nhanh "Heart Rate Control" toi truoc moc
Fuzzy/hardware:

  ModeSelectView -> PatientPanel -> HrRestView -> ArduinoCheckView
                                                 -> PreflightChecklistView
                                                 -> (SessionView: CHUA VIET,
                                                     nam sau moc Fuzzy)

  ModeSelectView -> EcgRecordingView (nhanh rieng, da xong hoan chinh)

  ModeSelectView -> "Tiep tuc session dang do" -> ArduinoCheckView
  (bo qua PatientPanel + HrRestView vi da co san)
"""

from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox

from ui.mode_select_view import ModeSelectView
from ui.ecg_recording_view import EcgRecordingView
from ui.patient_panel import PatientPanel
from ui.hr_rest_view import HrRestView
from ui.arduino_check_view import ArduinoCheckView
from ui.preflight_checklist_view import PreflightChecklistView

from data.pending_session_store import list_pending, load_pending, delete_pending


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ergometer Control System")
        self.resize(1180, 760)
        self.setMinimumSize(900, 620)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self._setup_mode_select()
        self._setup_ecg_recording()
        self._setup_patient_panel()
        self._setup_hr_rest_view()
        self._setup_arduino_check()
        self._setup_checklist()

        self._refresh_pending()

    # ─── Setup từng view ─────────────────────────────────────────

    def _setup_mode_select(self):
        self.mode_select_view = ModeSelectView()
        self.mode_select_view.mode_selected.connect(self._on_mode_selected)
        self.mode_select_view.resume_requested.connect(self._on_resume_requested)
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

    def _setup_hr_rest_view(self):
        self.hr_rest_view = HrRestView()
        self.hr_rest_view.back_to_menu.connect(self._on_back_to_menu)
        self.hr_rest_view.hr_rest_confirmed.connect(self._on_hr_rest_confirmed)
        self.stack.addWidget(self.hr_rest_view)

    def _setup_arduino_check(self):
        self.arduino_check_view = ArduinoCheckView()
        self.arduino_check_view.back_to_menu.connect(self._on_back_to_menu)
        self.arduino_check_view.connected.connect(self._on_arduino_connected)
        self.stack.addWidget(self.arduino_check_view)

    def _setup_checklist(self):
        self.checklist_view = PreflightChecklistView()
        self.checklist_view.back_to_menu.connect(self._on_back_to_menu)
        self.checklist_view.ready_to_start.connect(self._on_ready_to_start)
        self.stack.addWidget(self.checklist_view)

    # ─── Điều hướng ──────────────────────────────────────────────

    def _on_mode_selected(self, mode: str):
        if mode == "ecg_realtime":
            self.ecg_recording_view.reset()
            self.stack.setCurrentWidget(self.ecg_recording_view)
        elif mode == "heart_rate_control":
            self.patient_panel.reset()
            self.stack.setCurrentWidget(self.patient_panel)

    def _on_patient_ready(self, patient):
        self.hr_rest_view.set_patient(patient)
        self.stack.setCurrentWidget(self.hr_rest_view)

    def _on_hr_rest_confirmed(self, patient):
        self.hr_rest_view.reset()
        self.arduino_check_view.set_patient(patient)
        self.stack.setCurrentWidget(self.arduino_check_view)

    def _on_arduino_connected(self, patient):
        self.checklist_view.set_patient(patient)
        self.stack.setCurrentWidget(self.checklist_view)

    def _on_ready_to_start(self, patient):
        # TAM THOI: SessionView (MICT that) nam sau moc Fuzzy/hardware, chua viet
        QMessageBox.information(
            self, "OK",
            f"Checklist hoan tat cho {patient.name}.\n"
            f"HR_rest={patient.hr_rest} bpm, HRR={patient.hr_max - patient.hr_rest:.1f}\n\n"
            "SessionView (chuong trinh MICT that) se duoc noi khi lam toi "
            "moc Fuzzy + giao tiep Arduino."
        )
        self.checklist_view.reset()
        self._refresh_pending()
        self.stack.setCurrentWidget(self.mode_select_view)

    def _on_resume_requested(self, patient_id: str):
        patient = load_pending(patient_id)
        if patient is None:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy session này (có thể đã bị xóa).")
            self._refresh_pending()
            return
        self.arduino_check_view.set_patient(patient)
        self.stack.setCurrentWidget(self.arduino_check_view)

    def _on_back_to_menu(self):
        self._refresh_pending()
        self.stack.setCurrentWidget(self.mode_select_view)

    def _refresh_pending(self):
        self.mode_select_view.refresh_pending(list_pending())
