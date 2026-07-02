"""
signals/filters.py
---------------------
Filter bank — trích nguyên từ HRC.py _make_filters(), KHÔNG đổi hệ số.

2 nhóm filter riêng biệt:
- Display filter chain (HP/LP1/LP2/Notch): dùng để VẼ waveform cho đẹp,
  align với preset BSL "ECG (.5-35 Hz)"
- Pan-Tompkins BPF (B_PT/A_PT): dùng RIÊNG trong pan_tompkins.py để
  detect R-peak, không dùng chung với display filter
"""

from scipy.signal import butter, iirnotch
from signals.constants import FS


def _make_filters(fs: int = FS):
    nyq = fs / 2.0

    # HP 1.0 Hz — order 2 Butterworth (loại baseline drift nhanh hơn)
    b_hp, a_hp = butter(2, 1.0 / nyq, btype='high')

    # LP 66.5 Hz — order 2, Q≈0.5
    b_lp1, a_lp1 = butter(2, 66.5 / nyq, btype='low')

    # LP 38.5 Hz — order 2, Q≈1
    b_lp2, a_lp2 = butter(2, 38.5 / nyq, btype='low')

    # Notch 50 Hz, Q=1 (BSL default)
    b_nt, a_nt = iirnotch(50.0, 1.0, fs)

    # Pan-Tompkins BPF 5-15 Hz (paper gốc — isolate QRS)
    b_pt, a_pt = butter(2, [5.0 / nyq, 15.0 / nyq], btype='band')

    return (b_hp, a_hp), (b_lp1, a_lp1), (b_lp2, a_lp2), \
           (b_nt, a_nt), (b_pt, a_pt)


# Tính sẵn 1 lần khi module được import (giống bản gốc)
_filters = _make_filters()
B_HP, A_HP = _filters[0]
B_LP1, A_LP1 = _filters[1]
B_LP2, A_LP2 = _filters[2]
B_NT, A_NT = _filters[3]
B_PT, A_PT = _filters[4]
