"""
signals/acquisition.py
-------------------------
Trích từ HRC.py: _acq_worker (chạy trong multiprocessing.Process) và
class _Demo (giả lập ECG khi không có mpdev.dll/MP36). Logic BÊN TRONG
2 phần này giữ nguyên không đổi.

Phần MỚI so với HRC.py: class AcquisitionWorker — bọc lại toàn bộ việc
tạo Process/Queue/quản lý trạng thái (trước đây nằm rải rác trong
ECGApp._start_acquisition, _drain, _start_recording...) thành 1 API gọn
để ui/ecg_recording_view.py gọi, không cần biết chi tiết multiprocessing
bên trong.

QUAN TRỌNG: file này (và mọi nơi dùng multiprocessing.Process) BẮT BUỘC
phải được gọi từ code có bọc `if __name__ == "__main__":` với
`multiprocessing.set_start_method('spawn', force=True)` — xem main.py.
"""

import multiprocessing as mp
import os
import sys
import time
import csv

import numpy as np

from signals.constants import FS, CHUNK, MP_TYPE, MP_COMM, MP_SN, MPOK


# ══════════════════════════════════════════════════════════════════
# ACQUISITION WORKER FUNCTION — chạy trong process riêng
# Copy nguyên từ HRC.py _acq_worker, không đổi logic.
# ══════════════════════════════════════════════════════════════════

def _acq_worker(data_q: mp.Queue,
                 cmd_q: mp.Queue,
                 status: dict,
                 dll_path: str,
                 rec_q: mp.Queue):
    """
    Worker process (daemon):
      1. Kết nối MP36 qua BHAPI
      2. receiveMPData loop -> push data_q
      3. Nếu rec_q nhận ('START', data_path, peak_path) -> mở CSV, ghi thẳng
      4. Nhận 'STOP' từ cmd_q để thoát
    """
    from ctypes import windll, c_int, c_double, byref
    from ctypes.wintypes import DWORD

    try:
        dll = windll.LoadLibrary(dll_path)
    except Exception as e:
        status['error'] = f"Cannot load mpdev.dll: {e}"
        status['connected'] = False
        return

    try:
        dll.stopAcquisition()
    except Exception:
        pass

    r = dll.connectMPDev(c_int(MP_TYPE), c_int(MP_COMM), MP_SN)
    if r not in MPOK:
        r = dll.connectMPDev(c_int(MP_TYPE), c_int(10), b'')
        if r not in MPOK:
            status['error'] = (f"connectMPDev failed code={r}. "
                                "Check USB / close AcqKnowledge / mpdev.dll v2.2")
            status['connected'] = False
            return

    chnls = [0] * 16
    chnls[0] = 1  # CH1 = ECG
    chnls = (c_int * 16)(*chnls)
    dll.setAcqChannels(byref(chnls))
    dll.setSampleRate(c_double(1.0))  # 1.0 ms/sample = 1000 Hz

    r2 = dll.startMPAcqDaemon()
    r3 = dll.startAcquisition()
    if r2 not in MPOK or r3 not in MPOK:
        status['error'] = f"daemon={r2} acq={r3}"
        status['connected'] = False
        return

    status['connected'] = True
    status['error'] = ''

    buf = (c_double * CHUNK)()
    nread = DWORD(0)
    t0 = time.perf_counter()

    f_data = None
    f_peak = None
    w_data = None
    w_peak = None
    rec_on = False

    def _open_csv(data_path, peak_path):
        nonlocal f_data, f_peak, w_data, w_peak, rec_on
        os.makedirs(os.path.dirname(data_path), exist_ok=True)
        f_data = open(data_path, 'w', newline='', buffering=1)
        f_peak = open(peak_path, 'w', newline='', buffering=1)
        w_data = csv.writer(f_data)
        w_peak = csv.writer(f_peak)
        w_data.writerow(['timestamp', 'ch1_ecg_V'])
        w_peak.writerow(['timestamp', 'amplitude_V', 'is_peak'])
        rec_on = True

    def _close_csv():
        nonlocal f_data, f_peak, w_data, w_peak, rec_on
        rec_on = False
        for fh in (f_data, f_peak):
            if fh:
                try:
                    fh.flush()
                    fh.close()
                except Exception:
                    pass
        f_data = f_peak = w_data = w_peak = None

    while True:
        if not cmd_q.empty():
            cmd = cmd_q.get_nowait()
            if cmd == 'STOP':
                break

        if not rec_q.empty():
            msg = rec_q.get_nowait()
            if msg[0] == 'START':
                if rec_on:
                    _close_csv()
                _open_csv(msg[1], msg[2])
            elif msg[0] == 'STOP_REC':
                _close_csv()

        ret = dll.receiveMPData(byref(buf), DWORD(CHUNK), byref(nread))
        if ret == 1 and nread.value > 0:
            n = nread.value
            raw = [buf[i] for i in range(n)]

            try:
                data_q.put_nowait(raw)
            except Exception:
                pass

            if rec_on and w_data is not None:
                t_now = time.perf_counter() - t0
                for i, v in enumerate(raw):
                    ts = t_now - (n - 1 - i) / FS
                    w_data.writerow([f'{ts:.6f}', f'{v:.8f}'])
        else:
            time.sleep(0.0005)

    _close_csv()
    try:
        dll.stopAcquisition()
    except Exception:
        pass
    try:
        dll.disconnectMPDev()
    except Exception:
        pass
    status['connected'] = False


# ══════════════════════════════════════════════════════════════════
# DEMO SOURCE — copy nguyên từ HRC.py class _Demo
# ══════════════════════════════════════════════════════════════════

class _Demo:
    """Synthetic ECG 72 BPM để test khi không có MP36/mpdev.dll."""

    def __init__(self):
        self._t = 0.0
        self._bpm = 72.0

    def drain(self):
        n = CHUNK
        dt = 1.0 / FS
        t = np.arange(n) * dt + self._t
        self._t += n * dt
        rr = 60.0 / self._bpm
        ph = (t % rr) / rr
        ecg = (0.08 * np.exp(-((ph - 0.14) ** 2) / 0.003)
               + 1.20 * np.exp(-((ph - 0.40) ** 2) / 0.00018)
               - 0.28 * np.exp(-((ph - 0.43) ** 2) / 0.0003)
               + 0.22 * np.exp(-((ph - 0.56) ** 2) / 0.005)
               + 0.03 * np.random.randn(n))
        return list(ecg * 0.001)  # V (giống MP36 output)

    def stop(self):
        pass


# ══════════════════════════════════════════════════════════════════
# API GỌN CHO UI — MỚI, không có trong HRC.py gốc
# ══════════════════════════════════════════════════════════════════

class AcquisitionWorker:
    """
    Bọc toàn bộ việc quản lý multiprocessing.Process + Queue thành API
    đơn giản. ui/ecg_recording_view.py chỉ cần gọi các hàm này, không
    cần biết bên trong dùng mp.Process hay _Demo.

    Cách dùng:
        worker = AcquisitionWorker()
        worker.start()              # tự động fallback sang Demo nếu không có DLL/MP36
        raw = worker.drain()        # gọi liên tục trong vòng lặp UI (mỗi frame)
        worker.start_recording(data_path, peak_path)
        ...
        worker.stop_recording()
        worker.stop()
    """

    def __init__(self, dll_path: str | None = None):
        self.dll_path = dll_path or os.path.join(os.getcwd(), 'mpdev.dll')
        self.is_demo = False
        self._proc = None
        self._data_q = None
        self._cmd_q = None
        self._rec_q = None
        self._status = None
        self._demo_src = None
        self._manager = None

        # Ghi CSV ở demo mode: phải làm từ main process (worker giả không ghi được)
        self._demo_data_f = None
        self._demo_data_w = None
        self._demo_peak_f = None
        self._demo_peak_w = None
        self._recording = False
        self._rec_t0 = 0.0

    def start(self, connect_timeout_sec: float = 4.0):
        """Thử kết nối MP36 thật. Nếu không có DLL hoặc kết nối thất bại
        trong connect_timeout_sec giây -> tự động chuyển sang Demo mode."""
        # Worker duoc tai su dung khi do lai HR_rest / doi patient. Don sach
        # process lan truoc truoc khi tao MP36 process moi.
        self.stop()
        self.is_demo = False
        self._demo_src = None
        if not os.path.exists(self.dll_path):
            print(f"[INFO] mpdev.dll not found tai {self.dll_path} -> DEMO mode", file=sys.stderr)
            self.is_demo = True
            self._demo_src = _Demo()
            return

        self._data_q = mp.Queue(maxsize=500)
        self._cmd_q = mp.Queue()
        self._rec_q = mp.Queue()
        self._manager = mp.Manager()
        self._status = self._manager.dict({'connected': False, 'error': ''})

        self._proc = mp.Process(
            target=_acq_worker,
            args=(self._data_q, self._cmd_q, self._status, self.dll_path, self._rec_q),
            daemon=True,
        )
        self._proc.start()

        t0 = time.time()
        while time.time() - t0 < connect_timeout_sec:
            if self._status.get('connected', False):
                break
            err = self._status.get('error', '')
            if err:
                break
            time.sleep(0.05)

        if not self._status.get('connected', False):
            print(f"[WARN] {self._status.get('error', '?')} -> DEMO", file=sys.stderr)
            self.is_demo = True
            self._demo_src = _Demo()
            try:
                self._proc.terminate()
            except Exception:
                pass

    def drain(self) -> np.ndarray:
        """Lấy toàn bộ sample mới có từ lần gọi trước. Gọi liên tục (mỗi
        frame animation/timer) để không bị đầy queue."""
        if self.is_demo:
            raw = self._demo_src.drain()
            self._maybe_write_demo_data(raw)
            return np.array(raw, dtype=np.float64)

        out = []
        while not self._data_q.empty():
            try:
                out.extend(self._data_q.get_nowait())
            except Exception:
                break
        raw = out if out else []
        self._maybe_write_demo_data(raw)  # no-op nếu không phải demo
        return np.array(out, dtype=np.float64) if out else np.array([])

    def start_recording(self, data_path: str, peak_path: str):
        if self._recording:
            return
        self._recording = True
        self._rec_t0 = time.perf_counter()

        if not self.is_demo:
            self._rec_q.put(('START', data_path, peak_path))
        else:
            os.makedirs(os.path.dirname(data_path), exist_ok=True)
            self._demo_data_f = open(data_path, 'w', newline='', buffering=1)
            self._demo_data_w = csv.writer(self._demo_data_f)
            self._demo_data_w.writerow(['timestamp', 'ch1_ecg_V'])
            self._demo_peak_f = open(peak_path, 'w', newline='', buffering=1)
            self._demo_peak_w = csv.writer(self._demo_peak_f)
            self._demo_peak_w.writerow(['timestamp', 'amplitude_V', 'is_peak'])

        self._peak_path = peak_path

    def stop_recording(self):
        if not self._recording:
            return
        self._recording = False

        if not self.is_demo:
            self._rec_q.put(('STOP_REC',))
        else:
            for fh in (self._demo_data_f, self._demo_peak_f):
                if fh:
                    try:
                        fh.flush()
                        fh.close()
                    except Exception:
                        pass
            self._demo_data_f = self._demo_peak_f = None
            self._demo_data_w = self._demo_peak_w = None

    def write_peak(self, timestamp_sec: float, amplitude_v: float):
        """Gọi mỗi khi Pan-Tompkins detect 1 R-peak, để ghi vào peaks CSV."""
        if not self._recording:
            return
        if self.is_demo:
            if self._demo_peak_w:
                try:
                    self._demo_peak_w.writerow([f'{timestamp_sec:.6f}', f'{amplitude_v:.8f}', '1'])
                except Exception:
                    pass
        else:
            try:
                with open(self._peak_path, 'a', newline='') as f:
                    csv.writer(f).writerow([f'{timestamp_sec:.6f}', f'{amplitude_v:.8f}', '1'])
            except Exception:
                pass

    def _maybe_write_demo_data(self, raw):
        if not (self.is_demo and self._recording and self._demo_data_w and raw):
            return
        t_now = time.perf_counter() - self._rec_t0
        n = len(raw)
        for i, v in enumerate(raw):
            ts = t_now - (n - 1 - i) / FS
            try:
                self._demo_data_w.writerow([f'{ts:.6f}', f'{v:.8f}'])
            except Exception:
                break

    def stop(self):
        self.stop_recording()
        if self._proc is not None:
            try:
                if self._proc.is_alive() and self._cmd_q is not None:
                    self._cmd_q.put('STOP')
                self._proc.join(timeout=2.0)
                if self._proc.is_alive():
                    self._proc.terminate()
                    self._proc.join(timeout=1.0)
            except Exception:
                pass
        self._proc = None

        for queue in (self._data_q, self._cmd_q, self._rec_q):
            if queue is not None:
                try:
                    queue.close()
                    queue.join_thread()
                except Exception:
                    pass
        self._data_q = self._cmd_q = self._rec_q = None

        if self._manager is not None:
            try:
                self._manager.shutdown()
            except Exception:
                pass
        self._manager = None
        self._status = None

    @property
    def is_connected(self) -> bool:
        if self.is_demo:
            return True
        return bool(self._status.get('connected', False)) if self._status else False

    @property
    def last_error(self) -> str:
        if self.is_demo or not self._status:
            return ''
        return self._status.get('error', '')
