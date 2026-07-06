"""
tests/test_session_view.py
------------------------------
Test M4 (ui/session_view.py) voi WaveformView Demo mode + MockSerialController
+ SessionManager that (time_scale nen thoi gian). Theo dung quy uoc test UI
cua du an: QTimer POLLING (~150ms), tu tat modal, khong singleShot co dinh
cho phan cho.

Kiem tra:
  - begin() ket noi tat ca signal; nhan HR/level/pha/dong ho CAP NHAT that
    (khong con gia tri khoi tao "---" / "Muc tai: —").
  - Di qua it nhat WARMUP -> MAIN (hien thi nhieu pha).
  - Nhat ky su kien co dong.
  - Nut STOP: bam -> xac nhan Yes -> SessionManager.stop -> hardware ve
    LEVEL_MIN -> hien tong ket -> phat session_closed.

Chay: python tests/test_session_view.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

from core import config
from data.patient import PatientProfile, Sex, ActivityLevel
from control.hr_target import compute_karvonen_zone
from control.fuzzy_controller import FuzzyController
from control.session_manager import SessionManager
from data.session_logger import SessionLogger
from hardware.mock_serial_controller import MockSerialController
from ui.session_view import SessionView

TIME_SCALE = 60.0        # 30 phut -> ~30s thuc te; warmup 5 phut -> ~5s
POLL_INTERVAL_MS = 150
MAX_WAIT_MS = 45_000


def main():
    app = QApplication(sys.argv)

    patient = PatientProfile(name="Test SessionView", age=25, sex=Sex.MALE,
                              height_cm=172, weight_kg=68)
    patient.apply_hr_rest(68.0)
    zone = compute_karvonen_zone(patient)

    # delay=0: bo mo phong tre dong co (test nay kiem tra binding UI + STOP,
    # khong phai dong luc hoc motor) -> current_level phan anh lenh ngay lap tuc.
    hardware = MockSerialController(level_change_delay_sec=0.0)
    hardware.connect()
    logger = SessionLogger(patient.patient_id)

    view = SessionView()
    view.resize(900, 700)
    view.show()

    sm = SessionManager(
        hardware=hardware, controller=FuzzyController(), logger=logger,
        hr_target_result=zone, patient_group=patient.ipaq_activity_level,
        hr_source=view.waveform, config=config, time_scale=TIME_SCALE,
    )

    state = {"phases": [], "closed": False, "elapsed_ms": 0, "stop_requested": False}
    sm.phase_changed.connect(lambda p: state["phases"].append(p))
    view.session_closed.connect(lambda: state.__setitem__("closed", True))

    view.begin(sm, patient_name=patient.name)

    def _click_modal(prefer_yes=False):
        w = app.activeModalWidget()
        if isinstance(w, QMessageBox):
            btn = w.button(QMessageBox.StandardButton.Yes) if prefer_yes else None
            if btn is None:
                btn = w.button(QMessageBox.StandardButton.Ok)
            if btn:
                btn.click()
                return True
        return False

    poll = QTimer()

    def _ready_to_stop() -> bool:
        return (
            "MAIN" in state["phases"]
            and view.lbl_hr.text() != "---"
            and view.lbl_level.text() != "Mức tải: —"
            and view.lbl_clock.text() != "00:00 / 30:00"
        )

    def _tick():
        state["elapsed_ms"] += POLL_INTERVAL_MS

        # Luon co gang tat modal xac nhan/tong ket khi chung xuat hien
        if _click_modal(prefer_yes=True):
            return

        if not state["stop_requested"] and _ready_to_stop():
            print(f"[1] Da vao MAIN, nhan cap nhat OK: HR={view.lbl_hr.text()} "
                  f"Level='{view.lbl_level.text()}' Clock='{view.lbl_clock.text()}'")
            print(f"    So dong log: {view.log_list.count()}")
            state["stop_requested"] = True
            print("[2] Bam STOP...")
            # Goi qua singleShot(0) de KHONG chan poll timer: modal xac nhan mo
            # tren stack cua singleShot, poll van fire duoc de bam Yes/Ok. QTimer
            # khong tu tai nhap slot cua chinh no khi bi modal dong bo chan.
            QTimer.singleShot(0, view.btn_stop.click)
            return

        if state["closed"]:
            poll.stop()
            _finish()
            return

        if state["elapsed_ms"] >= MAX_WAIT_MS:
            poll.stop()
            print(f"\nTIMEOUT. phases={state['phases']} closed={state['closed']}")
            _cleanup()
            app.quit()
            sys.exit(1)

    poll.timeout.connect(_tick)
    poll.start(POLL_INTERVAL_MS)

    def _finish():
        print(f"[3] session_closed da phat. Phases da qua: {state['phases']}")
        assert "WARMUP" in state["phases"] and "MAIN" in state["phases"], \
            f"Phai hien thi it nhat WARMUP + MAIN, co: {state['phases']}"
        assert view.log_list.count() > 0, "Nhat ky su kien phai co dong"
        assert hardware.current_level == config.LEVEL_MIN, \
            f"STOP phai dua hardware ve LEVEL_MIN, dang o {hardware.current_level}"
        assert state["closed"] is True
        print(f"    hardware.current_level sau STOP = {hardware.current_level} (LEVEL_MIN) OK")
        _cleanup()
        print("\nOK - SessionView: binding hien thi + nut STOP an toan hoat dong dung")
        app.quit()

    def _cleanup():
        try:
            view.waveform.stop()
        except Exception:
            pass
        for p in (logger.timeseries_path, logger.events_path, logger.summary_path):
            if os.path.exists(p):
                os.remove(p)

    app.exec()


if __name__ == "__main__":
    main()
