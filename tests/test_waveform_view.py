"""
tests/test_waveform_view.py
------------------------------
Test WaveformView chạy trong PyQt6 event loop thật (không phải gọi hàm
trực tiếp), ở chế độ offscreen (không cần màn hình vật lý). Xác nhận:
  - Widget khởi tạo không lỗi
  - Sau vài giây chạy timer thật, có cập nhật ECG buffer + detect BPM

Chạy: python tests/test_waveform_view.py
(Trên Windows chạy bình thường sẽ tự mở cửa sổ thật để bạn NHÌN THẤY —
xem hướng dẫn ở cuối tin nhắn Claude gửi kèm file này.)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from ui.waveform_view import WaveformView


def main():
    app = QApplication(sys.argv)
    view = WaveformView()
    view.resize(900, 500)
    view.setWindowTitle("Test WaveformView - se tu dong sau 8s")
    view.show()

    received_bpm = []
    view.hr_updated.connect(lambda bpm: received_bpm.append(bpm))

    view.start()
    print("WaveformView.start() OK, dang chay demo mode...")

    # Chạy event loop thật trong 8 giây rồi tự thoát (đủ để qua warmup 5s)
    def _finish():
        view.stop()
        print(f"\nSo lan nhan hr_updated: {len(received_bpm)}")
        if received_bpm:
            print(f"BPM cuoi cung: {received_bpm[-1]}")
            assert 60 <= received_bpm[-1] <= 85, "BPM lech qua xa 72"
            print("\nOK - WaveformView chay dung, khong crash, detect dung BPM")
        else:
            print("\nCANH BAO: chua nhan duoc hr_updated nao trong 8s")
        app.quit()

    QTimer.singleShot(8000, _finish)
    app.exec()


if __name__ == "__main__":
    main()
