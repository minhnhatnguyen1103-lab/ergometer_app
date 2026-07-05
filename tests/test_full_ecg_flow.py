"""
tests/test_full_ecg_flow.py
-------------------------------
Test tự động toàn bộ luồng: mở app -> chọn "ECG real-time" -> nhập tên
-> streaming chạy vài giây -> bắt đầu ghi -> dừng ghi -> kết thúc ->
quay về menu. Không cần bấm tay, tất cả được giả lập bằng code.

Chạy: python tests/test_full_ecg_flow.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()

    def _dismiss_modal():
        """Tat hop thoai 'Da luu ban ghi' (modal) neu dang hien - neu khong
        _toggle_recording() se block mai o QMessageBox.exec()."""
        w = app.activeModalWidget()
        if isinstance(w, QMessageBox):
            btn = w.button(QMessageBox.StandardButton.Ok)
            if btn:
                btn.click()
    window.show()

    steps_done = []

    def step1_select_ecg_mode():
        print("[1] Chon mode ECG real-time...")
        window.mode_select_view.mode_selected.emit("ecg_realtime")
        assert window.stack.currentWidget() is window.ecg_recording_view
        steps_done.append("select_mode")

    def step2_enter_name_and_start():
        print("[2] Nhap ten va bat dau streaming...")
        ecg_view = window.ecg_recording_view
        ecg_view.name_page.name_input.setText("Nguyen Van A")
        ecg_view.name_page.start_requested.emit("Nguyen Van A")
        assert ecg_view.stack.currentWidget() is ecg_view.streaming_page
        steps_done.append("start_streaming")

    def step3_start_recording():
        print("[3] Bat dau ghi CSV...")
        streaming = window.ecg_recording_view.streaming_page
        streaming._toggle_recording()
        assert streaming.waveform.is_recording
        steps_done.append("start_recording")

    def step4_check_bpm_and_stop():
        print("[4] Kiem tra BPM da cap nhat, dung ghi...")
        streaming = window.ecg_recording_view.streaming_page
        bpm_text = streaming.lbl_bpm.text()
        print(f"    BPM hien tai: {bpm_text}")
        assert bpm_text != "---", "BPM chua duoc cap nhat sau warmup"
        # Dung ghi se hien modal 'Da luu' -> hen truoc mot cu click de tat no,
        # neu khong _toggle_recording() block mai trong QMessageBox.exec().
        QTimer.singleShot(200, _dismiss_modal)
        streaming._toggle_recording()
        assert not streaming.waveform.is_recording
        steps_done.append("stop_recording")

    def step5_finish_and_back():
        print("[5] Ket thuc, quay ve menu...")
        streaming = window.ecg_recording_view.streaming_page
        streaming._on_finish()
        assert window.stack.currentWidget() is window.mode_select_view
        steps_done.append("back_to_menu")

    def finish():
        expected = ["select_mode", "start_streaming", "start_recording",
                    "stop_recording", "back_to_menu"]
        print(f"\nCac buoc da hoan thanh: {steps_done}")
        assert steps_done == expected, f"Thieu buoc! Ky vong {expected}"
        print("\nOK - toan bo luong ECG real-time hoat dong dung, khong crash")
        app.quit()

    # Xep lich chay tuan tu, cach nhau du de warmup (5s) hoan tat
    QTimer.singleShot(500, step1_select_ecg_mode)
    QTimer.singleShot(1000, step2_enter_name_and_start)
    QTimer.singleShot(1500, step3_start_recording)
    QTimer.singleShot(7000, step4_check_bpm_and_stop)
    QTimer.singleShot(7500, step5_finish_and_back)
    QTimer.singleShot(8000, finish)

    app.exec()


if __name__ == "__main__":
    main()
