"""
tests/test_checklist_flow.py
--------------------------------
Test nhanh "da ket noi Arduino" (khong the test that vi sandbox khong
co Arduino) bang cach gia lap ham find_likely_arduino_port(). Xac nhan
ArduinoCheckView -> PreflightChecklistView -> nut Bat dau chi bat khi
tick het checklist -> phat ready_to_start dung.

Dung POLLING cho doan cho HR_rest do xong, tranh race condition do UI
thuc te co do tre khac nhau tuy may.

Chay: python tests/test_checklist_flow.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

from ui.main_window import MainWindow

# Phai LON HON warmup ~5s cua Pan-Tompkins, neu khong se khong co mau BPM
# nao -> HrRestView hien popup "Khong co du lieu" thay vi popup xac nhan,
# luong khong tien duoc sang ArduinoCheckView (giong test_hr_rest_flow dung 5s).
TEST_DURATION_SEC = 6
POLL_INTERVAL_MS = 150
MEASURE_TIMEOUT_MS = TEST_DURATION_SEC * 1000 + 6000


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    steps_done = []
    poll_state = {"elapsed_ms": 0, "done": False}

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

    patcher = patch("ui.arduino_check_view.find_likely_arduino_port", return_value="COM_FAKE")
    patcher.start()

    def step1_reach_arduino_check():
        print("[1] Di qua PatientPanel -> HrRestView, bat dau do (gia lap Arduino da ket noi)...")
        window.mode_select_view.mode_selected.emit("heart_rate_control")
        panel = window.patient_panel
        panel.basic_page.name_input.setText("Test Checklist")
        panel.basic_page._on_next()
        panel.ipaq_page._on_submit()
        panel._on_continue()
        window.hr_rest_view._duration_sec = TEST_DURATION_SEC
        window.hr_rest_view._start_measurement()
        steps_done.append("measuring")
        poll_timer.start(POLL_INTERVAL_MS)

    def _poll_measure():
        if poll_state["done"]:
            return
        poll_state["elapsed_ms"] += POLL_INTERVAL_MS

        if _click_modal(prefer_yes=True):
            return

        if window.stack.currentWidget() is window.arduino_check_view:
            poll_state["done"] = True
            poll_timer.stop()
            step3_check_connected()
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

    def step3_check_connected():
        print("[2] Kiem tra ArduinoCheckView bao da ket noi...")
        assert "Đã tìm thấy" in window.arduino_check_view.status_label.text()
        window.arduino_check_view._on_continue()
        assert window.stack.currentWidget() is window.checklist_view
        steps_done.append("connected_and_at_checklist")

        step4_test_checklist_gating()

    def step4_test_checklist_gating():
        print("[3] Kiem tra nut Bat dau chi bat khi tick het...")
        cl = window.checklist_view
        assert not cl.btn_start.isEnabled(), "Nut Bat dau khong duoc bat khi chua tick gi"
        for cb in cl._checkboxes[:-1]:
            cb.setChecked(True)
        assert not cl.btn_start.isEnabled(), "Chua tick het thi khong duoc bat"
        cl._checkboxes[-1].setChecked(True)
        assert cl.btn_start.isEnabled(), "Tick het roi phai bat nut"
        steps_done.append("checklist_gating_correct")

        QTimer.singleShot(200, step5_start)

    def step5_start():
        print("[4] Bam Bat dau -> phai mo SessionView (MICT that, M9 wiring)...")
        window.checklist_view._on_start()
        steps_done.append("started")

        QTimer.singleShot(800, finish)

    def finish():
        patcher.stop()
        expected = ["measuring", "connected_and_at_checklist",
                    "checklist_gating_correct", "started"]
        print(f"\nCac buoc da hoan thanh: {steps_done}")
        assert steps_done == expected, f"Thieu buoc! Ky vong {expected}"
        # Bam Bat dau gio mo SessionView that (khong con placeholder ve menu)
        assert window.stack.currentWidget() is window.session_view, \
            "Bam Bat dau phai mo SessionView"
        assert window._session_manager is not None, "SessionManager phai duoc tao"

        # Don dep phien dang chay (dung timer + waveform, dong + xoa CSV log tam)
        # de khong trigger modal tong ket / de lai file. Phai finalize() de dong
        # file handle truoc khi xoa (Windows khong cho xoa file dang mo).
        sm = window._session_manager
        sm._timer.stop()
        window.session_view.waveform.stop()
        sm.logger.finalize({})
        for p in (sm.logger.timeseries_path, sm.logger.events_path, sm.logger.summary_path):
            if os.path.exists(p):
                os.remove(p)

        print("\nOK - Checklist -> Bat dau mo SessionView (M9 wiring) hoat dong dung")
        app.quit()

    QTimer.singleShot(200, step1_reach_arduino_check)

    app.exec()


if __name__ == "__main__":
    main()
