"""
tests/test_hr_rest_flow.py
------------------------------
Test toan bo luong: chon Heart Rate Control -> nhap patient -> IPAQ ->
tiep tuc -> vao HrRestView -> bat dau do -> dem nguoc -> tu dong hien
popup xac nhan -> bam Co -> hr_rest_confirmed phat dung, patient.hr_rest
da duoc dien.

De KHONG phai cho that 2 phut, test nay ghi de _duration_sec = 5 giay.

Dung POLLING (kiem tra lien tuc moi 150ms) thay vi doan thoi diem co
dinh, vi UI thuc te (khong phai che do offscreen) co do tre khac nhau
tuy may - doan thoi diem co dinh de bi race condition.

Chay: python tests/test_hr_rest_flow.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

from ui.main_window import MainWindow

TEST_DURATION_SEC = 5
POLL_INTERVAL_MS = 150
TIMEOUT_MS = TEST_DURATION_SEC * 1000 + 8000


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # Ghi de thoi gian do de test nhanh (KHONG lam trong code that)
    window.hr_rest_view._duration_sec = TEST_DURATION_SEC

    steps_done = []
    poll_state = {"elapsed_ms": 0, "done": False}

    def step1_select_hrc():
        print("[1] Chon Heart Rate Control...")
        window.mode_select_view.mode_selected.emit("heart_rate_control")
        steps_done.append("select_mode")

    def step2_fill_patient():
        print("[2] Nhap patient + IPAQ...")
        panel = window.patient_panel
        panel.basic_page.name_input.setText("Test HrRest")
        panel.basic_page.age_input.setValue(30)
        panel.basic_page._on_next()
        panel.ipaq_page.vig_days.setValue(0)
        panel.ipaq_page.mod_days.setValue(0)
        panel.ipaq_page._on_submit()
        steps_done.append("patient_filled")

    def step3_continue_to_hr_rest():
        print("[3] Tiep tuc -> vao HrRestView...")
        window.patient_panel._on_continue()
        assert window.stack.currentWidget() is window.hr_rest_view
        assert window.hr_rest_view.patient is not None
        steps_done.append("entered_hr_rest_view")

    def step4_start_measurement():
        print(f"[4] Bat dau do (rut ngan con {TEST_DURATION_SEC}s de test)...")
        window.hr_rest_view._start_measurement()
        assert window.hr_rest_view._timer.isActive()
        steps_done.append("measurement_started")
        poll_timer.start(POLL_INTERVAL_MS)

    def finish(success: bool):
        expected = ["select_mode", "patient_filled", "entered_hr_rest_view",
                    "measurement_started", "hr_rest_confirmed_and_applied"]
        print(f"\nCac buoc da hoan thanh: {steps_done}")
        if success:
            assert steps_done == expected, f"Thieu buoc! Ky vong {expected}"
            print("\nOK - toan bo luong HrRestView hoat dong dung")
            app.quit()
        else:
            print(f"\nTIMEOUT sau {TIMEOUT_MS}ms - chua hoan tat luong")
            app.quit()
            sys.exit(1)

    def _poll():
        if poll_state["done"]:
            return
        poll_state["elapsed_ms"] += POLL_INTERVAL_MS

        if poll_state["elapsed_ms"] % 1000 == 0:
            w_dbg = app.activeModalWidget()
            print(f"    [poll] t={poll_state['elapsed_ms']}ms modal={type(w_dbg).__name__ if w_dbg else None} "
                  f"stack={type(window.stack.currentWidget()).__name__} "
                  f"hr_rest={window.patient_panel._current_patient.hr_rest if window.patient_panel._current_patient else None}",
                  flush=True)

        # Neu co popup dang mo, tu dong bam (Yes truoc, khong co thi Ok)
        w = app.activeModalWidget()
        if isinstance(w, QMessageBox):
            btn = w.button(QMessageBox.StandardButton.Yes)
            if btn is None:
                btn = w.button(QMessageBox.StandardButton.Ok)
            if btn:
                btn.click()
            return  # cho tick sau moi kiem tra tiep

        patient = window.patient_panel._current_patient
        if (window.stack.currentWidget() is window.arduino_check_view
                and patient is not None and patient.hr_rest is not None):
            poll_state["done"] = True
            poll_timer.stop()
            print("[5] Da xac nhan HR_rest, chuyen sang ArduinoCheckView.")
            print(f"    patient.hr_rest = {patient.hr_rest}")
            assert 40 <= patient.hr_rest <= 180, "hr_rest ngoai khoang hop ly"
            steps_done.append("hr_rest_confirmed_and_applied")
            finish(True)
            return

        if poll_state["elapsed_ms"] >= TIMEOUT_MS:
            poll_state["done"] = True
            poll_timer.stop()
            finish(False)

    poll_timer = QTimer()
    poll_timer.timeout.connect(_poll)

    QTimer.singleShot(200, step1_select_hrc)
    QTimer.singleShot(400, step2_fill_patient)
    QTimer.singleShot(600, step3_continue_to_hr_rest)
    QTimer.singleShot(800, step4_start_measurement)

    app.exec()


if __name__ == "__main__":
    main()
