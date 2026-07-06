"""
data/session_logger.py
--------------------------
M3 theo docsclaude/IMPLEMENTATION_PLAN.md muc 3.3: ghi lai buoi tap MICT de
phan tich va lam bang chung do an. AN DANH - chi dung patient_id (UUID),
KHONG ghi ten that (patient.name khong duoc truyen vao day).

2 file CSV moi session, cung thu muc voi recordings ECG (signals/constants.LOG_DIR):
  - <patient_id>_<timestamp>_timeseries.csv : 1 dong/mau (~1 Hz)
  - <patient_id>_<timestamp>_events.csv     : 1 dong/su kien (doi level, chuyen
    pha, moc HRR1, manual_override, safety_event, cadence_warning...)

Day KHONG phai noi luu PatientProfile/pending session (xem
data/pending_session_store.py) - SessionLogger chi ghi du lieu buoi tap da
dien ra, khong phuc hoi lai duoc trang thai session tu file nay.
"""

import os
import csv
import json
from pathlib import Path
from datetime import datetime

from signals.constants import LOG_DIR

TIMESERIES_FIELDS = [
    "t_sec", "phase", "hr_actual", "hr_target_low", "hr_target_high",
    "level", "rpm", "source", "in_zone",
]
EVENT_FIELDS = ["t_sec", "kind", "detail_json"]


class SessionLogger:
    def __init__(self, patient_id: str, config=None, log_dir: str | None = None):
        self.patient_id = patient_id
        self._log_dir = log_dir or LOG_DIR
        os.makedirs(self._log_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.timeseries_path = os.path.join(self._log_dir, f"{patient_id}_{ts}_timeseries.csv")
        self.events_path = os.path.join(self._log_dir, f"{patient_id}_{ts}_events.csv")
        self.summary_path = os.path.join(self._log_dir, f"{patient_id}_{ts}_summary.json")

        self._f_ts = open(self.timeseries_path, "w", newline="", encoding="utf-8", buffering=1)
        self._w_ts = csv.writer(self._f_ts)
        self._w_ts.writerow(TIMESERIES_FIELDS)

        self._f_ev = open(self.events_path, "w", newline="", encoding="utf-8", buffering=1)
        self._w_ev = csv.writer(self._f_ev)
        self._w_ev.writerow(EVENT_FIELDS)

    def log_sample(self, t_sec: float, phase: str, hr: float, low: float, high: float,
                   level: int, rpm: float | None, source: str, in_zone: bool) -> None:
        self._w_ts.writerow([
            f"{t_sec:.1f}", phase, f"{hr:.1f}", f"{low:.1f}", f"{high:.1f}",
            level, ("" if rpm is None else f"{rpm:.1f}"), source, int(bool(in_zone)),
        ])

    def log_event(self, t_sec: float, kind: str, detail: dict | None = None) -> None:
        self._w_ev.writerow([f"{t_sec:.1f}", kind, json.dumps(detail or {}, ensure_ascii=False)])

    def finalize(self, summary: dict) -> Path:
        """Dong 2 file CSV, ghi summary.json (time-in-zone, HRR1...). Tra ve
        Path cua file summary de noi goi (vd. SessionView) hien thi/mo lai."""
        for fh in (self._f_ts, self._f_ev):
            try:
                fh.flush()
                fh.close()
            except Exception:
                pass

        summary_out = {"patient_id": self.patient_id, **summary}
        with open(self.summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_out, f, ensure_ascii=False, indent=2)

        return Path(self.summary_path)
