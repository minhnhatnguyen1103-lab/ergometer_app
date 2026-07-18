"""
ui/waveform_view.py
----------------------
Widget hiển thị ECG + HR realtime bằng pyqtgraph (thay cho matplotlib/
Tkinter của HRC.py cũ). Widget này TỰ QUẢN LÝ acquisition + filter +
Pan-Tompkins bên trong — nơi khác chỉ cần add widget này vào layout và
gọi start()/stop()/start_recording()/stop_recording().

Vì cả mode "ECG real-time" và "Heart Rate Control" đều cần hiển thị
ECG+HR, widget này được thiết kế dùng chung cho cả 2 (đúng kiến trúc
đã thống nhất: waveform_view.py dùng chung 2 mode).
"""

import os
import time
import datetime
import collections

import numpy as np
from scipy.signal import lfilter
import pyqtgraph as pg

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QTimer, pyqtSignal

from signals.acquisition import AcquisitionWorker
from signals.pan_tompkins import PanTompkinsRT
from signals.filters import B_HP, A_HP, B_LP1, A_LP1, B_LP2, A_LP2, B_NT, A_NT
from signals.constants import FS, WIN_SEC, BUF, MP36_GAIN, LOG_DIR
from ui.theme import BG, BRAND, DANGER, MUTED

ANIM_MS = 25  # ~40 fps, giống HRC.py


class WaveformView(QWidget):
    # Phát ra mỗi khi có BPM mới — màn hình cha (EcgRecordingView,
    # SessionView...) lắng nghe để cập nhật label BPM riêng của mình.
    hr_updated = pyqtSignal(float)
    # Phát ra khi trạng thái connected/demo thay đổi (dùng để hiện "● LIVE" / "● DEMO")
    status_changed = pyqtSignal(bool, bool)  # (is_connected, is_demo)

    def __init__(self):
        super().__init__()

        self.worker = AcquisitionWorker()
        self._run_n = 0
        self._recording = False

        self.reset_state()

        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)

    def reset_state(self):
        """Xoa TOAN BO trang thai nhan dang noi bo: detector (ke ca warmup
        5s), buffer ECG/HR, bo loc, bo dem mau, BPM hien tai. Goi moi khi
        bat dau mot lan do/streaming MOI de khong dung lai warmup cu va du
        lieu BPM cu tu lan truoc (vd. bam 'Khong' o popup HR_rest roi do lai,
        hoac doi tuong moi vao lai man hinh). Neu khong reset, lan do sau se
        bo qua warmup va tinh HR_rest tren du lieu con sot lai."""
        self.detector = PanTompkinsRT()

        self.ecg_buf = collections.deque([0.0] * BUF, maxlen=BUF)
        self.hr_buf = collections.deque([0.0] * BUF, maxlen=BUF)
        self.n = 0
        self.cur_bpm = 0.0
        self.t0_perf = time.perf_counter()

        def _zi(b, a):
            return np.zeros(max(len(b), len(a)) - 1)
        self._zi_hp = _zi(B_HP, A_HP)
        self._zi_lp1 = _zi(B_LP1, A_LP1)
        self._zi_lp2 = _zi(B_LP2, A_LP2)
        self._zi_nt = _zi(B_NT, A_NT)

    # ─── UI ───────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        pg.setConfigOptions(antialias=True, background=BG, foreground=MUTED)
        glw = pg.GraphicsLayoutWidget()
        glw.setBackground(BG)

        self.ecg_plot = glw.addPlot(row=0, col=0)
        self.ecg_plot.setLabel('left', 'mV')
        self.ecg_plot.showGrid(x=True, y=True, alpha=0.2)
        self.ecg_plot.setMouseEnabled(x=False, y=False)
        self.line_ecg = self.ecg_plot.plot(pen=pg.mkPen(color=BRAND, width=1.2))
        self.scat_r = pg.ScatterPlotItem(size=8, brush=pg.mkBrush(DANGER), symbol='t1')
        self.ecg_plot.addItem(self.scat_r)

        glw.nextRow()
        self.hr_plot = glw.addPlot(row=1, col=0)
        self.hr_plot.setLabel('left', 'BPM')
        self.hr_plot.setLabel('bottom', 'Time (s)')
        self.hr_plot.showGrid(x=True, y=True, alpha=0.2)
        self.hr_plot.setMouseEnabled(x=False, y=False)
        self.hr_plot.setYRange(30, 190)
        self.line_hr = self.hr_plot.plot(pen=pg.mkPen(color=DANGER, width=2))

        layout.addWidget(glw)
        self.setLayout(layout)

    # ─── Điều khiển từ bên ngoài ─────────────────────────────────

    def start(self):
        self.reset_state()   # moi lan start la mot lan do/streaming hoan toan moi
        self.worker.start()
        self.status_changed.emit(self.worker.is_connected, self.worker.is_demo)
        self._timer.start(ANIM_MS)

    def stop(self):
        self._timer.stop()
        self.worker.stop()

    def start_recording(self, subject_name: str = "subject") -> tuple[str, str]:
        """Bắt đầu ghi CSV. Trả về (data_path, peak_path) để nơi gọi biết
        file nào vừa được tạo (vd. hiện lên UI, hoặc lưu vào SessionLogger)."""
        self._run_n += 1
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = "".join(c for c in subject_name if c.isalnum() or c in ("_", "-")) or "subject"
        data_path = os.path.join(LOG_DIR, f'ecg_{safe_name}_run{self._run_n}_{ts}_data.csv')
        peak_path = os.path.join(LOG_DIR, f'ecg_{safe_name}_run{self._run_n}_{ts}_peaks.csv')

        self.worker.start_recording(data_path, peak_path)
        self._recording = True
        self._rec_t0 = time.perf_counter()
        return data_path, peak_path

    def stop_recording(self):
        self.worker.stop_recording()
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    # ─── Vòng lặp update (thay cho matplotlib FuncAnimation) ───────

    def _update(self):
        raw = self.worker.drain()
        if len(raw) == 0:
            return

        y = raw
        y, self._zi_hp = lfilter(B_HP, A_HP, y, zi=self._zi_hp)
        y, self._zi_lp1 = lfilter(B_LP1, A_LP1, y, zi=self._zi_lp1)
        y, self._zi_lp2 = lfilter(B_LP2, A_LP2, y, zi=self._zi_lp2)
        y, self._zi_nt = lfilter(B_NT, A_NT, y, zi=self._zi_nt)
        y_mv = y * MP36_GAIN

        for s in y_mv:
            self.n += 1
            self.ecg_buf.append(float(s))
            self.hr_buf.append(self.cur_bpm)

        peaks = self.detector.push(y_mv)

        if peaks:
            _, bpm_last = peaks[-1]
            if bpm_last > 0:
                self.cur_bpm = bpm_last
                self.hr_updated.emit(self.cur_bpm)
                for j in range(BUF - len(y_mv), BUF):
                    self.hr_buf[j] = self.cur_bpm

            if self._recording:
                ecg_snap = np.array(self.ecg_buf)
                for g_idx, _ in peaks:
                    b_i = g_idx - (self.n - BUF)
                    amp_v = (float(ecg_snap[b_i]) / MP36_GAIN if 0 <= b_i < BUF else 0.0)
                    ts = (self.t0_perf + g_idx / FS) - self.t0_perf
                    self.worker.write_peak(ts, amp_v)

        t_end = self.n / FS
        t_start = t_end - WIN_SEC
        t_arr = np.linspace(t_start, t_end, BUF)
        ecg_arr = np.array(self.ecg_buf)

        self.line_ecg.setData(t_arr, ecg_arr)
        self.ecg_plot.setXRange(t_start, t_end, padding=0)

        if peaks:
            px, py = [], []
            for g, _ in peaks:
                b = g - (self.n - BUF)
                if not (0 <= b < BUF):
                    continue
                lo = max(0, b - 100)
                hi = min(BUF, b + 5)
                if hi > lo:
                    seg = ecg_arr[lo:hi]
                    r_off = int(np.argmax(np.abs(seg)))
                    r_b = lo + r_off
                    px.append(t_arr[r_b])
                    py.append(ecg_arr[r_b])
            self.scat_r.setData(px, py)
        else:
            self.scat_r.setData([], [])

        hr_arr = np.array(self.hr_buf)
        self.line_hr.setData(t_arr, hr_arr)
        self.hr_plot.setXRange(t_start, t_end, padding=0)

    @property
    def warmup_remaining(self) -> float:
        return self.detector.warmup_remaining
