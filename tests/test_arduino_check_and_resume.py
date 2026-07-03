"""
tests/test_arduino_check_and_resume.py
-------------------------------------------
Test: HrRestView xac nhan xong -> vao ArduinoCheckView -> (sandbox khong
co Arduino nen luon "chua tim thay") -> Quit + luu pending -> quay ve
menu -> nut resume xuat hien -> bam resume -> vao lai ArduinoCheckView
voi dung patient (hr_rest giu nguyen).

Dung POLLING cho doan cho HR_rest do xong + popup xac nhan (giong
cach da sua trong test_hr_rest_flow.py) de tranh race condition do
UI thuc te co do tre khac nhau tuy may.

Don dep file pending tao ra sau khi test xong.

Chay: python tests/test_arduino_check_and_resume.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

from ui.main_window import MainWindow
from data.pending_session_store import list_pending, delete_pending

TEST_DURATION_SEC = 3
POLL_INTERVAL_MS = 150
MEASURE_TIMEOUT_MS = TEST_DURATION_SEC * 1000 + 6000


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.hr_rest_view._duration_sec = TEST_DURATION_SEC

    steps_done = []
    saved_patient_id = {}
    poll_state = {"elapsed_ms": 0, "done": False}

    def _click_modal(prefer_yes=True):
        w = app.activeModalWidget()
        if isinstance(w, QMessageBox):
            btn = w.button(QMessageBox.StandardButton.Yes) if prefer_yes else None
            if btn is None:
                btn = w.button(QMessageBox.StandardButton.Ok)
            if btn:
                btn.click()
                return True
        return False

    def step1_go_to_hr_rest():
        print("[1] Di qua PatientPanel -> HrRestView...")
        window.mode_select_view.mode_selected.emit("heart_rate_control")
        panel = window.patient_panel
        panel.basic_page.name_input.setText("Test ArduinoCheck")
        panel.basic_page._on_next()
        panel.ipaq_page._on_submit()
        panel._on_continue()
        assert window.stack.currentWidget() is window.hr_rest_view
        steps_done.append("reached_hr_rest")

    def step2_start_measurement():
        print("[2] Bat dau do HR_rest (rut ngan), cho bang polling...")
        window.hr_rest_view._start_measurement()
        steps_done.append("hr_rest_measuring")
        poll_timer.start(POLL_INTERVAL_MS)

    def _poll_measure():
        if poll_state["done"]:
            return
        poll_state["elapsed_ms"] += POLL_INTERVAL_MS

        # Tu dong bam Yes cho popup xac nhan HR_rest neu dang mo
        if _click_modal(prefer_yes=True):
            return

        if window.stack.currentWidget() is window.arduino_check_view:
            poll_state["done"] = True
            poll_timer.stop()
            step3_and_beyond()
            return

        if poll_state["elapsed_ms"] >= MEASURE_TIMEOUT_MS:
            poll_state["done"] = True
            poll_timer.stop()
            print(f"\nTIMEOUT khi cho do HR_rest sau {MEASURE_TIMEOUT_MS}ms")
            print(f"Cac buoc da hoan thanh: {steps_done}")
            app.quit()
            sys.exit(1)

    poll_timer = QTimer()
    poll_timer.timeout.connect(_poll_measure)

    def step3_and_beyond():
        print("[3] Da vao ArduinoCheckView, kiem tra chua tim thay Arduino...")
        assert "Chưa tìm thấy" in window.arduino_check_view.status_label.text()
        steps_done.append("arduino_not_found")

        print("[4] Bam Quit, chon Co de luu pending...")
        QTimer.singleShot(300, lambda: _click_modal(prefer_yes=True))
        window.arduino_check_view._on_quit()

        QTimer.singleShot(800, step5_check_resume_button)

    def step5_check_resume_button():
        print("[5] Kiem tra nut resume da xuat hien tren ModeSelectView...")
        assert window.stack.currentWidget() is window.mode_select_view
        pending = list_pending()
        assert len(pending) >= 1, "Chua co pending session nao duoc luu"
        saved_patient_id['id'] = pending[-1]['patient_id']
        assert not window.mode_select_view.btn_resume.isHidden(), "Nut resume phai hien ra"
        steps_done.append("resume_button_visible")

        QTimer.singleShot(200, step6_click_resume)

    def step6_click_resume():
        print("[6] Bam resume, kiem tra quay lai dung ArduinoCheckView voi patient dung...")
        window.mode_select_view.resume_requested.emit(saved_patient_id['id'])
        assert window.stack.currentWidget() is window.arduino_check_view
        restored = window.arduino_check_view.patient
        assert restored is not None
        assert restored.patient_id == saved_patient_id['id']
        assert restored.hr_rest is not None, "hr_rest phai duoc giu lai sau khi resume"
        print(f"    Patient khoi phuc: {restored.name}, hr_rest={restored.hr_rest}")
        steps_done.append("resumed_correctly")

        QTimer.singleShot(200, cleanup_and_finish)

    def cleanup_and_finish():
        if saved_patient_id.get('id'):
            delete_pending(saved_patient_id['id'])
            print(f"[cleanup] Da xoa pending session {saved_patient_id['id']}")
        expected = ["reached_hr_rest", "hr_rest_measuring", "arduino_not_found",
                    "resume_button_visible", "resumed_correctly"]
        print(f"\nCac buoc da hoan thanh: {steps_done}")
        assert steps_done == expected, f"Thieu buoc! Ky vong {expected}"
        print("\nOK - toan bo luong ArduinoCheckView + resume hoat dong dung")
        app.quit()

    QTimer.singleShot(200, step1_go_to_hr_rest)
    QTimer.singleShot(400, step2_start_measurement)

    app.exec()


if __name__ == "__main__":
    main()
