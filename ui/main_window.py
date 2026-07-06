"""
ui/main_window.py
-------------------
Cua so chinh. Da noi TRON VEN nhanh "Heart Rate Control" toi het (voi
MockSerialController - chua can Arduino that):

  ModeSelectView -> PatientPanel -> HrRestView -> ArduinoCheckView
                                                 -> PreflightChecklistView
                                                 -> SessionView (MICT that:
                                                    Fuzzy + 3 pha + log + STOP)

  ModeSelectView -> EcgRecordingView (nhanh rieng, da xong hoan chinh)

  ModeSelectView -> "Tiep tuc session dang do" -> ArduinoCheckView
  (bo qua PatientPanel + HrRestView vi da co san)

_on_ready_to_start (M9 wiring) tao SessionManager (Fuzzy + Mock hardware +
logger + Karvonen zone), tiem hr_source = SessionView.waveform, roi mo
SessionView. Doi sang Arduino that sau nay chi thay dong tao `hardware`.
"""

from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox

from ui.mode_select_view import ModeSelectView
from ui.ecg_recording_view import EcgRecordingView
from ui.patient_panel import PatientPanel
from ui.hr_rest_view import HrRestView
from ui.arduino_check_view import ArduinoCheckView
from ui.preflight_checklist_view import PreflightChecklistView
from ui.session_view import SessionView

from control.hr_target import compute_karvonen_zone
from control.fuzzy_controller import FuzzyController
from control.session_manager import SessionManager
from data.session_logger import SessionLogger
from hardware.mock_serial_controller import MockSerialController

from data.pending_session_store import list_pending, load_pending, delete_pending


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
        self._setup_hr_rest_view()
        self._setup_arduino_check()
        self._setup_checklist()
        self._setup_session_view()

        # SessionManager song trong luc mot phien dang chay (giu tham chieu de
        # khong bi thu gom rac); tao moi moi lan bat dau mot buoi tap.
        self._session_manager = None

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

    def _setup_session_view(self):
        self.session_view = SessionView()
        self.session_view.session_closed.connect(self._on_session_closed)
        self.stack.addWidget(self.session_view)

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
        """M9 wiring: khoi tao SessionManager (tiem Fuzzy + hardware Mock +
        logger + Karvonen zone + nhom IPAQ), tiem hr_source = waveform cua
        SessionView, roi mo man hinh MICT that.

        LUU Y: hardware hien la MockSerialController vi RealSerialController
        (M6) + firmware Arduino (M7) chua lam. Doi sang Arduino that sau nay
        chi can thay dong tao `hardware` o duoi (dung interface
        SerialControllerBase, khong sua logic SessionManager)."""
        try:
            zone = compute_karvonen_zone(patient)
        except Exception as e:
            QMessageBox.warning(self, "Loi", f"Khong tinh duoc vung muc tieu Karvonen:\n{e}")
            return

        hardware = MockSerialController()
        if not hardware.connect():
            QMessageBox.warning(self, "Loi", "Khong ket noi duoc board dieu khien (Mock).")
            return

        logger = SessionLogger(patient.patient_id)
        self._session_manager = SessionManager(
            hardware=hardware,
            controller=FuzzyController(),
            logger=logger,
            hr_target_result=zone,
            patient_group=patient.ipaq_activity_level,
            hr_source=self.session_view.waveform,
        )
        self.stack.setCurrentWidget(self.session_view)
        self.session_view.begin(self._session_manager, patient_name=patient.name)

    def _on_session_closed(self):
        self.checklist_view.reset()
        self._session_manager = None
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
