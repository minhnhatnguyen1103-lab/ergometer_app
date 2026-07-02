"""
tests/test_signals_demo.py
-----------------------------
Kiểm tra signals/filters.py + signals/pan_tompkins.py + Demo mode của
signals/acquisition.py hoạt động đúng với nhau — KHÔNG cần MP36/mpdev.dll/
Windows, vì Demo mode chỉ sinh tín hiệu ECG giả bằng numpy.

Test này verify: nếu đưa data giả ~72 BPM qua đúng chain filter + PT
detector, hệ thống phải detect ra BPM quanh 72 (sai số nhỏ vì Demo có
random noise).

Chạy: python tests/test_signals_demo.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from scipy.signal import lfilter

from signals.acquisition import AcquisitionWorker
from signals.pan_tompkins import PanTompkinsRT
from signals.filters import B_HP, A_HP, B_LP1, A_LP1, B_LP2, A_LP2, B_NT, A_NT
from signals.constants import MP36_GAIN


def main():
    print("=== Test signals layer (Demo mode, khong can phan cung) ===\n")

    # Ep AcquisitionWorker vao Demo mode bang duong dan DLL khong ton tai
    worker = AcquisitionWorker(dll_path="/duong_dan_khong_ton_tai/mpdev.dll")
    worker.start()
    assert worker.is_demo, "Phai roi vao Demo mode vi DLL khong ton tai"
    print("OK: AcquisitionWorker tu dong fallback sang Demo mode")

    detector = PanTompkinsRT()

    def _zi(b, a):
        return np.zeros(max(len(b), len(a)) - 1)
    zi_hp, zi_lp1, zi_lp2, zi_nt = _zi(B_HP, A_HP), _zi(B_LP1, A_LP1), _zi(B_LP2, A_LP2), _zi(B_NT, A_NT)

    all_bpm = []

    # Mo phong ~20 giay du lieu (CHUNK=100 samples/lan, FS=1000Hz -> 10 lan/giay)
    for _ in range(200):
        raw = worker.drain()
        if len(raw) == 0:
            continue

        y = raw
        y, zi_hp = lfilter(B_HP, A_HP, y, zi=zi_hp)
        y, zi_lp1 = lfilter(B_LP1, A_LP1, y, zi=zi_lp1)
        y, zi_lp2 = lfilter(B_LP2, A_LP2, y, zi=zi_lp2)
        y, zi_nt = lfilter(B_NT, A_NT, y, zi=zi_nt)
        y_mv = y * MP36_GAIN

        peaks = detector.push(y_mv)
        for _, bpm in peaks:
            if bpm > 0:
                all_bpm.append(bpm)

    print(f"\nSo R-peak detect duoc (sau warmup): {len(all_bpm)}")
    if all_bpm:
        median_bpm = float(np.median(all_bpm))
        print(f"BPM median: {median_bpm:.1f} (ky vong ~72)")
        assert 60 <= median_bpm <= 85, f"BPM ({median_bpm}) lech qua xa 72 -> co the loi filter/detector"
        print("\nOK - signals layer hoat dong dung, detect dung nhip tim gia lap")
    else:
        print("\nCANH BAO: khong detect duoc R-peak nao - kiem tra lai warmup/threshold")
        sys.exit(1)


if __name__ == "__main__":
    main()
