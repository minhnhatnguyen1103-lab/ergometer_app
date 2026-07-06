"""
tests/test_session_manager.py
---------------------------------
Test M2 (control/session_manager.py) voi MockSerialController + FuzzyController
that + SessionLogger that (ghi CSV that roi xoa), NEN THOI GIAN (time_scale=60)
de chay tron 30 phut trong ~30 giay thuc te - dung ky thuat de xuat trong
IMPLEMENTATION_PLAN.md muc 3.2/5.

Kiem tra:
  - Di het 3 pha dung thu tu WARMUP -> MAIN -> COOLDOWN -> DONE
  - Level Warmup dat dung theo nhom IPAQ (Sedentary)
  - Phat hien dung 'manual_override' khi gia lap bam nut vat ly giua Main
  - An toan mat HR: safety_event 'hr_stale_short' RỒI 'hr_stale_long' khi
    dong bang HR gia lap, va level tu dong ve LEVEL_MIN khi long-stale
  - HRR1 duoc chot (hr_end_main, hr_at_1min_post, hrr1 khong None)
  - session_finished phat ra dung 1 lan voi summary hop le

Dung QTimer polling (khong singleShot co dinh cho phan cho hoan tat) theo
dung quy uoc test cua du an (xem CLAUDE.md / cac test UI flow khac).

Chay: python tests/test_session_manager.py
"""

import sys
import os
import random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QCoreApplication, QTimer

from core import config
from data.patient import PatientProfile, Sex, ActivityLevel
from control.hr_target import compute_karvonen_zone
from control.fuzzy_controller import FuzzyController
from control.session_manager import SessionManager
from data.session_logger import SessionLogger
from hardware.mock_serial_controller import MockSerialController

TIME_SCALE = 60.0  # nen 1800s (30p) thanh 30s thuc te
POLL_INTERVAL_MS = 200
MAX_WAIT_MS = 40_000  # 40s thuc te - du bien cho 30s session + overhead


class _FakeHrSource:
    """Gia lap WaveformView: chi can co thuoc tinh cur_bpm (duck-typed).

    QUAN TRONG: HR that luon dao dong nhe (khong bao gio phang tuyet doi),
    va SessionManager phat hien mat tin hieu bang "gia tri HR khong doi
    trong X giay". Vi vay fake source phai bien thien LIEN TUC (nhieu ngau
    nhien nho moi buoc) - neu chi dao dong giua 2 gia tri co dinh thi 2 tick
    lien tiep co the doc trung gia tri -> bao nham safety_event du khong co
    kich ban dong bang."""
    def __init__(self, start_bpm: float):
        self.cur_bpm = round(start_bpm, 2)
        self.frozen = False

    def drift_toward(self, target: float, step: float = 1.5):
        if self.frozen:
            return
        # Tien ve target + nhieu ngau nhien nho -> gia tri gan nhu khong bao
        # gio lap lai giua 2 tick lien tiep khi tin hieu "song".
        if self.cur_bpm < target:
            self.cur_bpm = min(target, self.cur_bpm + step)
        elif self.cur_bpm > target:
            self.cur_bpm = max(target, self.cur_bpm - step)
        self.cur_bpm = round(self.cur_bpm + random.uniform(-0.4, 0.4), 2)


def main():
    random.seed(42)  # deterministic - tranh flaky (ca drift HR lan chu ky Fuzzy)
    app = QCoreApplication(sys.argv)

    # --- Dung san: patient Sedentary, HR_rest = 70 ---
    patient = PatientProfile(name="Test Session", age=22, sex=Sex.MALE,
                              height_cm=170, weight_kg=65)
    patient.apply_hr_rest(70.0)
    assert patient.ipaq_activity_level == ActivityLevel.SEDENTARY
    zone = compute_karvonen_zone(patient)
    print(f"[setup] Target zone = [{zone.thr_low:.1f}, {zone.thr_high:.1f}] bpm, "
          f"trung diem = {(zone.thr_low + zone.thr_high) / 2:.1f}")

    hardware = MockSerialController()
    hardware.connect()
    controller = FuzzyController()
    logger = SessionLogger(patient.patient_id)
    hr_source = _FakeHrSource(start_bpm=patient.hr_rest)

    sm = SessionManager(
        hardware=hardware, controller=controller, logger=logger,
        hr_target_result=zone, patient_group=patient.ipaq_activity_level,
        hr_source=hr_source, config=config, time_scale=TIME_SCALE,
        # Nguong mat HR do bang GIAY THUC (doc lap time_scale) - tiem gia tri
        # nho de kich hoat an toan bang mot lan dong bang HR ~1.2s that.
        hr_stale_short_sec=0.3, hr_stale_long_sec=0.7,
    )

    center = (zone.thr_low + zone.thr_high) / 2
    events = {
        "phases": [], "level_changes": [], "safety_events": [],
        "cadence_warnings": [], "finished_summary": None,
        "phase": "WARMUP",
    }
    sm.phase_changed.connect(lambda p: events["phases"].append(p))
    sm.phase_changed.connect(lambda p: events.__setitem__("phase", p))
    sm.level_changed.connect(lambda lvl, reason: events["level_changes"].append((lvl, reason)))
    sm.safety_event.connect(lambda kind: events["safety_events"].append(kind))
    sm.cadence_warning.connect(lambda rpm: events["cadence_warnings"].append(rpm))

    def _on_finished(summary):
        events["finished_summary"] = summary
    sm.session_finished.connect(_on_finished)

    # --- HR drift: bam giua vung muc tieu o Warmup/Main; GIAM dan ve gan
    #     HR_rest o Cooldown de mo phong hoi phuc that -> HRR1 co y nghia
    #     (khong bang 0). Target doi theo pha hien tai.
    def _hr_target_now():
        if events["phase"] == "COOLDOWN":
            return patient.hr_rest + 12  # hoi phuc: HR tut ve gan nghi
        return center
    hr_drift_timer = QTimer()
    hr_drift_timer.timeout.connect(lambda: hr_source.drift_toward(_hr_target_now()))
    hr_drift_timer.start(150)

    # --- Kich ban: bam nut vat ly giua Main (~t=3s thuc te, chac chan da vao Main) ---
    def _simulate_manual_button():
        print("[kich ban] Gia lap bam nut vat ly -> level=12")
        hardware.simulate_manual_button(12)
    QTimer.singleShot(3000, _simulate_manual_button)

    # --- Kich ban: dong bang HR ~1.2s THUC de kich hoat ca 2 muc an toan
    #     (short 0.3s -> long 0.7s), do la thoi gian thuc doc lap time_scale ---
    def _freeze_hr():
        print("[kich ban] Dong bang HR gia lap de test an toan mat tin hieu...")
        hr_source.frozen = True
    def _unfreeze_hr():
        print("[kich ban] Mo dong bang HR")
        hr_source.frozen = False
    QTimer.singleShot(5000, _freeze_hr)
    QTimer.singleShot(6200, _unfreeze_hr)

    sm.start()

    poll_state = {"elapsed_ms": 0}
    poll_timer = QTimer()

    def _poll():
        poll_state["elapsed_ms"] += POLL_INTERVAL_MS
        if events["finished_summary"] is not None:
            poll_timer.stop()
            hr_drift_timer.stop()
            _finish()
            return
        if poll_state["elapsed_ms"] >= MAX_WAIT_MS:
            poll_timer.stop()
            hr_drift_timer.stop()
            print(f"\nTIMEOUT sau {MAX_WAIT_MS}ms. Phases da qua: {events['phases']}")
            app.quit()
            sys.exit(1)

    poll_timer.timeout.connect(_poll)
    poll_timer.start(POLL_INTERVAL_MS)

    def _finish():
        print(f"\n[ket qua] Phases: {events['phases']}")
        print(f"[ket qua] So lan doi level: {len(events['level_changes'])}")
        reasons = {reason for _, reason in events['level_changes']}
        print(f"[ket qua] Cac ly do doi level da xay ra: {reasons}")
        print(f"[ket qua] Safety events: {events['safety_events']}")
        print(f"[ket qua] Summary: {events['finished_summary']}")

        assert events["phases"] == ["WARMUP", "MAIN", "COOLDOWN", "DONE"], \
            f"Sai thu tu pha: {events['phases']}"

        warmup_entries = [lvl for lvl, reason in events["level_changes"] if reason == "warmup"]
        assert warmup_entries and warmup_entries[0] == config.WARMUP_LEVEL_SEDENTARY, \
            f"Level Warmup phai la {config.WARMUP_LEVEL_SEDENTARY} (Sedentary), duoc {warmup_entries}"

        assert "manual_override" in reasons, "Phai phat hien duoc manual_override khi gia lap bam nut"

        assert "hr_stale_short" in events["safety_events"], "Phai co canh bao mat HR ngan han"
        assert "hr_stale_long" in events["safety_events"], "Phai co canh bao mat HR dai han"
        assert "safety" in reasons, "Phai co lan doi level do safety (ve LEVEL_MIN khi mat HR lau)"

        summary = events["finished_summary"]
        assert summary is not None
        assert summary["stop_reason"] == "completed"
        assert summary["hrr1"] is not None, "HRR1 phai duoc tinh (hr_end_main va hr_at_1min_post da chot)"
        print(f"[ket qua] HRR1 = {summary['hrr1']:.2f}")

        # Don dep file CSV/json test tao ra
        for p in (logger.timeseries_path, logger.events_path, logger.summary_path):
            if os.path.exists(p):
                os.remove(p)

        print("\nOK - SessionManager: 3 pha dung thu tu, manual_override, an toan mat HR, HRR1 deu dung")
        app.quit()

    app.exec()


if __name__ == "__main__":
    main()
