"""
signals/pan_tompkins.py
--------------------------
Copy NGUYÊN VẸN class PanTompkinsRT từ HRC.py — không sửa 1 dòng logic
thuật toán. Đây là bộ phát hiện R-peak online (incremental), đã được
tune với warmup 5s, bootstrap threshold, adaptive SPK/NPK.

Nếu cần đổi tham số (warmup, refractory...), sửa trực tiếp trong class
này — đây LÀ bản chính thức duy nhất, không có bản sao nào khác.
"""

import sys
import collections
import numpy as np
from scipy.signal import lfilter

from signals.constants import FS, BPM_MIN, BPM_MAX, ECG_POLARITY_FIXED
from signals.filters import B_PT, A_PT


class PanTompkinsRT:
    """
    Online (incremental) Pan-Tompkins. Chỉ xử lý sample mới → latency
    ~25ms thay vì ~200ms như bản batch.
    """
    WIN_MWI = int(0.150 * FS)     # 150 ms integration window (paper)
    REF = int(0.300 * FS)         # 300 ms refractory — tránh T-wave
    BL_WIN = int(0.200 * FS)      # 200 ms baseline removal
    NOISE_REJ = 0.05              # 5% noise rejection (BSL setting)
    RR_BUF = 8                    # median over 8 RR intervals

    def __init__(self):
        self.spk = 0.0
        self.npk = 0.0
        self.thr = 0.0
        self.lp_global = -self.REF
        self.rr_buf = collections.deque(maxlen=self.RR_BUF)
        self.bpm = 0.0
        self.n_global = 0
        self.polarity = ECG_POLARITY_FIXED   # cố định, không auto-detect

        n_zi = max(len(B_PT), len(A_PT)) - 1
        self._zi_pt = np.zeros(n_zi)

        self._mwi_hist = collections.deque([0.0] * self.WIN_MWI, maxlen=self.WIN_MWI)

        # Warmup 5s: thu thập MWI values để bootstrap threshold chính xác
        self._warmup = 5 * FS
        self._mwi_warmup = []
        self._pol_buf = []

    def _remove_baseline(self, x: np.ndarray) -> np.ndarray:
        """Subtract local mean — dùng uniform_filter1d để tránh shape mismatch."""
        from scipy.ndimage import uniform_filter1d
        bl = uniform_filter1d(x.astype(np.float64), size=self.BL_WIN, mode='nearest')
        return x - bl

    def push(self, new_mv: np.ndarray) -> list[tuple[int, float]]:
        """
        Nhận samples mới (đã display-filtered, đơn vị mV).
        Trả về list (global_sample_idx, bpm) cho mỗi R-peak detected.
        """
        results = []
        n = len(new_mv)
        if n == 0:
            return results

        x_bl = self._remove_baseline(new_mv)
        sig, self._zi_pt = lfilter(B_PT, A_PT, x_bl, zi=self._zi_pt)

        h = np.array([1, 2, 0, -2, -1], dtype=np.float64) * (FS / 8.0)
        diff = np.convolve(sig, h, mode='same')
        sq = diff ** 2

        for i in range(n):
            self._mwi_hist.append(float(sq[i]))
            mwi_val = float(np.mean(self._mwi_hist))
            self.n_global += 1

            if self.n_global < self._warmup:
                if mwi_val > 0:
                    self._mwi_warmup.append(mwi_val)
                if self.n_global > self._warmup - 3 * FS:
                    self._pol_buf.append(float(new_mv[i]))
                continue

            if self.spk == 0 and len(self._mwi_warmup) > 100:
                mwi_arr = np.array(self._mwi_warmup)
                self.spk = float(np.percentile(mwi_arr, 75))
                self.npk = self.spk * self.NOISE_REJ
                self.thr = self.npk + 0.25 * (self.spk - self.npk)
                self._mwi_warmup = []
                print(f"[PT] Bootstrap: spk={self.spk:.4f} thr={self.thr:.4f}", file=sys.stderr)

            if self.polarity == 0 and len(self._pol_buf) > 500:
                arr = np.array(self._pol_buf)
                p01 = float(np.percentile(arr, 1))
                p50 = float(np.percentile(arr, 50))
                p99 = float(np.percentile(arr, 99))
                up = p99 - p50
                down = p50 - p01
                self.polarity = +1 if up >= down else -1
                self._pol_buf = []
                print(f"[PT] polarity={self.polarity:+d}  up={up:.3f}mV down={down:.3f}mV base={p50:.3f}mV", file=sys.stderr)
            elif self.polarity == 0:
                self.polarity = ECG_POLARITY_FIXED

            hist = list(self._mwi_hist)
            if len(hist) >= 6 and mwi_val < max(hist[-6:-1]):
                continue

            if self.n_global - self.lp_global < self.REF:
                continue

            if mwi_val >= self.thr:
                r_global = self.n_global

                rr_s = (r_global - self.lp_global) / FS
                if 60.0 / BPM_MAX < rr_s < 60.0 / BPM_MIN:
                    self.rr_buf.append(rr_s)
                    if len(self.rr_buf) >= 2:
                        self.bpm = 60.0 / float(np.median(self.rr_buf))

                self.spk = 0.25 * mwi_val + 0.75 * self.spk
                self.npk = max(self.npk * 0.75, self.spk * self.NOISE_REJ)
                self.thr = self.npk + 0.25 * (self.spk - self.npk)
                self.lp_global = r_global

                bpm = round(self.bpm, 1) if BPM_MIN <= self.bpm <= BPM_MAX else 0.0
                results.append((r_global, bpm))
            else:
                self.npk = max(0.25 * mwi_val + 0.75 * self.npk, self.spk * self.NOISE_REJ)
                self.thr = self.npk + 0.25 * (self.spk - self.npk)

        return results

    @property
    def warmup_remaining(self) -> float:
        return max(0.0, (self._warmup - self.n_global) / FS)
