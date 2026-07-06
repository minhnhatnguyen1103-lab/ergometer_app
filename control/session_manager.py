"""
control/session_manager.py
------------------------------
M2 theo docsclaude/IMPLEMENTATION_PLAN.md muc 3.2: "nhac truong" toan buoi
tap MICT - chay state machine 3 pha theo DONG HO TUYET DOI (khong dem so
vong Fuzzy, vi moi lan tinh cach nhau 5-8s, dem se sai lech dan), lay HR tu
nguon duoc tiem vao, goi FuzzyController o pha Main, ra lenh level xuong
SerialControllerBase (Mock hoac Real - khong quan tam ben trong), va ghi
log qua SessionLogger.

Nguyen tac quan trong nhat (xem IMPLEMENTATION_PLAN.md muc 1.2 va 3.5):
nut bam vat ly tren Arduino luon song song voi lenh serial. Vi vay MOI lan
tick BAT BUOC doc `hardware.current_level` (dai dien telemetry TLM.level khi
co Arduino that) LAM NGUON SU THAT truoc khi tinh Fuzzy - khong duoc dung
gia tri cache phan mem tu nghi la dang co. Neu khac ky vong -> ghi
`manual_override`, chap nhan gia tri thuc te, tinh tiep tu do (khong "sua lai").

Gioi han hien tai (trung thuc ve pham vi): giao thuc Serial that (M5) va
RealSerialController (M6) CHUA duoc hien thuc vi can Arduino that. RPM/
source (button vs serial) trong SerialControllerBase hien tai la duck-typed
optional (`getattr(hardware, "rpm", None)`) - MockSerialController co the
gan .rpm de test canh bao cadence, con "source" dung lai chinh chuoi ly do
(warmup/fuzzy/cooldown/manual_override/safety) thay vi phan biet button/
serial that (se can sua khi lam M6 that).
"""

import random
import time
import statistics
from collections import deque
from dataclasses import dataclass

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core import config as default_config
from data.patient import ActivityLevel


PHASE_WARMUP = "WARMUP"
PHASE_MAIN = "MAIN"
PHASE_COOLDOWN = "COOLDOWN"
PHASE_DONE = "DONE"


@dataclass
class _HrSample:
    t: float
    hr: float


class SessionManager(QObject):
    phase_changed = pyqtSignal(str)
    level_changed = pyqtSignal(int, str)          # level, ly do
    hr_updated = pyqtSignal(float)
    tick = pyqtSignal(int, int)                    # elapsed_sec, remaining_sec
    cadence_warning = pyqtSignal(float)
    safety_event = pyqtSignal(str)
    session_finished = pyqtSignal(dict)            # summary

    def __init__(self, hardware, controller, logger, hr_target_result,
                 patient_group: ActivityLevel, hr_source,
                 config=default_config, time_scale: float = 1.0,
                 hr_stale_short_sec: float | None = None,
                 hr_stale_long_sec: float | None = None):
        """
        hardware        : SerialControllerBase (Mock hoac Real sau nay)
        controller      : FuzzyController (M1)
        logger          : SessionLogger (M3)
        hr_target_result: HRTargetZone (control/hr_target.compute_karvonen_zone)
        patient_group   : ActivityLevel.SEDENTARY/ACTIVE - quyet dinh level Warmup
        hr_source       : bat ky object nao co thuoc tinh .cur_bpm (float) -
                          thuc te la WaveformView dang chay trong SessionView (M4).
                          Duck-typed de test khong can dung QWidget/pyqtgraph that.
        time_scale      : CHI dung khi test - nhan voi thoi gian thuc da troi de
                          nen 30 phut thanh vai chuc giay. San xuat luon = 1.0.
                          LUU Y: time_scale CHI nen lich trinh giao thuc (3 pha,
                          chu ky Fuzzy, moc HRR1). No KHONG ap dung cho phat hien
                          mat tin hieu HR - do la su kien thoi gian thuc (tin hieu
                          mat bao nhieu GIAY THAT), do bang time.monotonic() truc
                          tiep, doc lap time_scale.
        hr_stale_short/long_sec: nguong (GIAY THUC) mat HR ngan/dai. Mac dinh lay
                          tu config; cho phep tiem gia tri nho khi test de kich
                          hoat an toan bang mot lan dong bang HR ngan.
        """
        super().__init__()
        self.hardware = hardware
        self.controller = controller
        self.logger = logger
        self.zone = hr_target_result
        self.patient_group = patient_group
        self.hr_source = hr_source
        self.config = config
        self.time_scale = time_scale
        self._hr_stale_short_sec = (hr_stale_short_sec if hr_stale_short_sec is not None
                                    else config.HR_STALE_SHORT_TIMEOUT_SEC)
        self._hr_stale_long_sec = (hr_stale_long_sec if hr_stale_long_sec is not None
                                   else config.HR_STALE_LONG_TIMEOUT_SEC)

        self.hr_target_center = (hr_target_result.thr_low + hr_target_result.thr_high) / 2.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

        self._t0 = 0.0
        self._phase = None
        self._expected_level = config.LEVEL_MIN
        self._stopped = False

        self._hr_window: deque[_HrSample] = deque()
        self._last_hr_raw = None
        self._last_hr_change_real_t = 0.0   # dong ho THUC (monotonic), khong scaled
        self._short_stale_warned = False
        self._long_stale_triggered = False
        self._cadence_warned = False

        self._last_fuzzy_t = None
        self._next_fuzzy_interval = None
        self._hr_prev_for_fuzzy = None

        self._level_at_cooldown_start = None
        self._hr_end_main = None
        self._hr_at_1min_post = None
        self._last_level_source = "warmup"

        self._warmup_end = config.WARMUP_DURATION_SEC
        self._main_end = config.WARMUP_DURATION_SEC + config.MAIN_DURATION_SEC
        self._total_duration = self._main_end + config.COOLDOWN_DURATION_SEC

    # ─── Vong doi ────────────────────────────────────────────────

    def start(self):
        self._t0 = time.monotonic()
        self._stopped = False
        warmup_level = (
            self.config.WARMUP_LEVEL_ACTIVE
            if self.patient_group == ActivityLevel.ACTIVE
            else self.config.WARMUP_LEVEL_SEDENTARY
        )
        self.hardware.send_level(warmup_level)
        self._expected_level = warmup_level
        self._set_phase(PHASE_WARMUP)
        self.level_changed.emit(warmup_level, "warmup")
        self.logger.log_event(0.0, "level_changed", {"level": warmup_level, "reason": "warmup"})
        self._timer.start(self.config.SESSION_TICK_MS)

    def stop(self, reason: str):
        if self._stopped:
            return
        self._stopped = True
        self._timer.stop()
        self.hardware.send_level(self.config.LEVEL_MIN)
        elapsed = self._elapsed()
        self.logger.log_event(elapsed, "stopped", {"reason": reason})

        summary = self._build_summary(reason)
        self.logger.finalize(summary)
        self.session_finished.emit(summary)

    # ─── Vong lap tick ───────────────────────────────────────────

    def _elapsed(self) -> float:
        return (time.monotonic() - self._t0) * self.time_scale

    def _phase_for(self, elapsed: float) -> str:
        if elapsed < self._warmup_end:
            return PHASE_WARMUP
        if elapsed < self._main_end:
            return PHASE_MAIN
        if elapsed < self._total_duration:
            return PHASE_COOLDOWN
        return PHASE_DONE

    def _set_phase(self, phase: str):
        self._phase = phase
        self.phase_changed.emit(phase)
        self.logger.log_event(self._elapsed(), "phase_changed", {"phase": phase})

    def _on_tick(self):
        elapsed = self._elapsed()
        phase = self._phase_for(elapsed)

        # Tinh HR mượt TRUOC khi xu ly vao-pha, de moc HR_end_main (chot khi
        # vao Cooldown) va HR_at_1min_post cung dung mot loai gia tri (HR
        # muot) - neu mot thô mot muot thi HRR1 = hieu 2 loai khac nhau, sai.
        hr_now = self._read_hr_raw()
        smoothed_hr = self._smoothed_hr(elapsed, hr_now)

        if phase != self._phase:
            self._on_phase_enter(phase, elapsed, smoothed_hr)

        self.hr_updated.emit(smoothed_hr)

        telemetry_level = self.hardware.current_level
        if telemetry_level != self._expected_level:
            self.logger.log_event(elapsed, "manual_override", {
                "expected": self._expected_level, "actual": telemetry_level,
            })
            self._expected_level = telemetry_level
            self.level_changed.emit(telemetry_level, "manual_override")

        self._check_hr_staleness(elapsed, hr_now)
        self._check_cadence(elapsed)

        in_zone = self.zone.contains(smoothed_hr)
        self.logger.log_sample(
            elapsed, phase, smoothed_hr, self.zone.thr_low, self.zone.thr_high,
            telemetry_level, getattr(self.hardware, "rpm", None),
            self._last_level_source, in_zone,
        )

        if phase == PHASE_MAIN:
            self._run_main(elapsed, smoothed_hr, telemetry_level)
        elif phase == PHASE_COOLDOWN:
            self._run_cooldown(elapsed, telemetry_level)
            self._mark_hrr1_if_due(elapsed, smoothed_hr)

        remaining = max(0.0, self._total_duration - elapsed)
        self.tick.emit(int(elapsed), int(remaining))

        if phase == PHASE_DONE:
            self.stop("completed")

    def _on_phase_enter(self, new_phase: str, elapsed: float, smoothed_hr: float):
        self._set_phase(new_phase)
        if new_phase == PHASE_MAIN:
            self._last_fuzzy_t = elapsed
            self._next_fuzzy_interval = random.uniform(
                self.config.FUZZY_UPDATE_INTERVAL_SEC_MIN,
                self.config.FUZZY_UPDATE_INTERVAL_SEC_MAX,
            )
            self._hr_prev_for_fuzzy = smoothed_hr
        elif new_phase == PHASE_COOLDOWN:
            self._level_at_cooldown_start = self.hardware.current_level
            self._hr_end_main = smoothed_hr
            self.logger.log_event(elapsed, "hrr1_mark", {"kind": "hr_end_main", "hr": self._hr_end_main})

    # ─── HR: doc tho + lam muot ─────────────────────────────────

    def _read_hr_raw(self) -> float:
        return float(getattr(self.hr_source, "cur_bpm", 0.0))

    def _smoothed_hr(self, elapsed: float, hr_now: float) -> float:
        self._hr_window.append(_HrSample(elapsed, hr_now))
        cutoff = elapsed - self.config.HR_SMOOTHING_WINDOW_SEC
        while self._hr_window and self._hr_window[0].t < cutoff:
            self._hr_window.popleft()
        values = [s.hr for s in self._hr_window]
        return statistics.median(values) if values else hr_now

    def _check_hr_staleness(self, elapsed: float, hr_now: float):
        """Heuristic: neu gia tri HR tho khong doi trong X GIAY THUC, coi nhu
        mat tin hieu (khong co peak moi duoc detect). Do bang time.monotonic()
        - KHONG dung `elapsed` (da nhan time_scale) vi mat tin hieu la su kien
        vat ly thoi gian thuc, khong lien quan toc do nen lich trinh giao thuc.
        `elapsed` o day chi dung lam moc thoi gian ghi log.

        Han che da biet: neu HR that su dung im o cung gia tri trong X giay
        (thuc te rat hiem voi ECG that) se bi bao nham - chap nhan duoc o muc
        do an toan (tha bao nham con hon bo sot)."""
        now = time.monotonic()
        if self._last_hr_raw is None or hr_now != self._last_hr_raw:
            self._last_hr_raw = hr_now
            self._last_hr_change_real_t = now
            self._short_stale_warned = False
            self._long_stale_triggered = False
            return

        stale_duration = now - self._last_hr_change_real_t
        if stale_duration >= self._hr_stale_long_sec and not self._long_stale_triggered:
            self._long_stale_triggered = True
            self.hardware.send_level(self.config.LEVEL_MIN)
            self._expected_level = self.config.LEVEL_MIN
            self.logger.log_event(elapsed, "safety_event", {"kind": "hr_stale_long", "duration": round(stale_duration, 2)})
            self.safety_event.emit("hr_stale_long")
            self.level_changed.emit(self.config.LEVEL_MIN, "safety")
        elif stale_duration >= self._hr_stale_short_sec and not self._short_stale_warned:
            self._short_stale_warned = True
            self.logger.log_event(elapsed, "safety_event", {"kind": "hr_stale_short", "duration": round(stale_duration, 2)})
            self.safety_event.emit("hr_stale_short")

    def _check_cadence(self, elapsed: float):
        rpm = getattr(self.hardware, "rpm", None)
        if rpm is None:
            return
        out_of_range = not (self.config.CADENCE_MIN_RPM <= rpm <= self.config.CADENCE_MAX_RPM)
        if out_of_range and not self._cadence_warned:
            self._cadence_warned = True
            self.logger.log_event(elapsed, "cadence_warning", {"rpm": rpm})
            self.cadence_warning.emit(rpm)
        elif not out_of_range:
            self._cadence_warned = False

    # ─── Xu ly tung pha ──────────────────────────────────────────

    def _run_main(self, elapsed: float, smoothed_hr: float, current_level: int):
        if elapsed - self._last_fuzzy_t < self._next_fuzzy_interval:
            return

        dt = elapsed - self._last_fuzzy_t
        result = self.controller.compute(
            hr_actual=smoothed_hr, hr_target_center=self.hr_target_center,
            hr_prev=self._hr_prev_for_fuzzy, dt=dt, current_level=current_level,
        )
        self.logger.log_event(elapsed, "fuzzy_compute", {
            "error": round(result.error, 2), "error_rate": round(result.error_rate, 3),
            "crisp_output": round(result.crisp_output, 3), "delta_level": result.delta_level,
            "new_level": result.new_level, "out_of_range": result.out_of_range,
        })
        if result.out_of_range:
            self.logger.log_event(elapsed, "level_out_of_expected_range", {"level": result.new_level})

        if result.new_level != current_level:
            self.hardware.send_level(result.new_level)
            self._expected_level = result.new_level
            self._last_level_source = "fuzzy"
            self.level_changed.emit(result.new_level, "fuzzy")

        self._last_fuzzy_t = elapsed
        self._next_fuzzy_interval = random.uniform(
            self.config.FUZZY_UPDATE_INTERVAL_SEC_MIN, self.config.FUZZY_UPDATE_INTERVAL_SEC_MAX,
        )
        self._hr_prev_for_fuzzy = smoothed_hr

    def _run_cooldown(self, elapsed: float, current_level: int):
        progress = (elapsed - self._main_end) / self.config.COOLDOWN_DURATION_SEC
        progress = max(0.0, min(1.0, progress))
        start_level = self._level_at_cooldown_start or current_level
        target = round(start_level + (self.config.LEVEL_MIN - start_level) * progress)
        target = max(self.config.LEVEL_MIN, min(self.config.LEVEL_MAX, target))

        if target != self._expected_level:
            self.hardware.send_level(target)
            self._expected_level = target
            self._last_level_source = "cooldown"
            self.level_changed.emit(target, "cooldown")

    def _mark_hrr1_if_due(self, elapsed: float, smoothed_hr: float):
        mark_t = self._main_end + self.config.HRR1_MARK_OFFSET_SEC
        if self._hr_at_1min_post is None and elapsed >= mark_t:
            self._hr_at_1min_post = smoothed_hr
            hrr1 = (self._hr_end_main or 0.0) - smoothed_hr
            self.logger.log_event(elapsed, "hrr1_mark", {
                "kind": "hr_at_1min_post", "hr": smoothed_hr, "hrr1": hrr1,
            })

    # ─── Tong ket ────────────────────────────────────────────────

    def _build_summary(self, stop_reason: str) -> dict:
        hrr1 = None
        if self._hr_end_main is not None and self._hr_at_1min_post is not None:
            hrr1 = self._hr_end_main - self._hr_at_1min_post
        return {
            "stop_reason": stop_reason,
            "elapsed_sec": self._elapsed(),
            "hr_end_main": self._hr_end_main,
            "hr_at_1min_post": self._hr_at_1min_post,
            "hrr1": hrr1,
        }
