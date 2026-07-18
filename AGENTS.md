# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## What this is

A PyQt6 desktop app controlling a cycle-ergometer (GENUS-249, brake board being replaced by an Arduino) for a
university thesis (đồ án tốt nghiệp) protocol combining ECG acquisition (BIOPAC MP36) and heart-rate-controlled
exercise (MICT: Karvonen HRR-based target zone). Comments and identifiers are mixed Vietnamese/English — Vietnamese
explains the clinical/thesis rationale, English is used for standard code terms. Match this style when editing.

## Running

```
python main.py
```

There is no build/lint/package step — this is a plain-script PyQt6 app run directly with the venv's Python
(`venv/Scripts/python.exe` or `.venv/Scripts/python.exe` on Windows).

## Tests

There is no pytest suite and no test runner config (no `pytest.ini`, no `conftest.py`). Every file under `tests/`
is a **standalone script**, run directly:

```
python tests/smoke_test.py
python tests/test_checklist_flow.py
```

Two different styles exist:
- Pure-logic scripts (`smoke_test.py`) — import domain modules directly, print results, no assertions framework.
- UI flow scripts (`test_checklist_flow.py`, `test_hr_rest_flow.py`, `test_arduino_check_and_resume.py`,
  `test_full_ecg_flow.py`, `test_waveform_view.py`, `test_patient_panel_flow.py`) — spin up a real `QApplication`
  and `MainWindow`, drive it via `QTimer.singleShot`/polling loops (to dodge race conditions instead of using
  `QTest`), patch hardware-detection functions (e.g. `ui.arduino_check_view.find_likely_arduino_port`) with
  `unittest.mock.patch`, assert on widget state, and end with `app.quit()` / `sys.exit(1)` on failure. When adding
  a new UI flow test, copy this pattern rather than introducing pytest-qt or a different framework.

## Architecture

### Layered module boundaries (deliberate, don't blur them)

- `core/config.py` — every tunable clinical/protocol number (Karvonen %, IPAQ thresholds, phase durations,
  level limits) lives here, nowhere else. New magic numbers for thresholds/durations must be added here, not
  inlined, so the whole protocol can be justified/defended from one file.
- `signals/constants.py` — separate from `core/config.py` on purpose: these are *hardware/algorithm* constants
  (MP36 device codes, sample rate, Pan-Tompkins tuning) that a thesis committee won't ask "why this number" about
  in clinical terms, unlike `core/config.py`.
- `data/patient.py` (`PatientProfile`) — demographics + HRmax (Tanaka formula) + IPAQ-SF activity classification,
  all computed in `__post_init__` at creation time, before any real measurement exists.
- `control/hr_target.py` — Karvonen HRR target-zone math (`compute_karvonen_zone`). Deliberately separated from
  `patient.py` because it depends on `hr_rest`, which only exists after `PatientProfile.apply_hr_rest()` is
  called (a real measurement taken later in the flow, not at intake). Calling it before `apply_hr_rest()` raises
  `HRRestNotMeasuredError`.
- `hardware/serial_controller_base.py` — abstract interface for the brake-control board. `MockSerialController`
  (time-based simulated motor movement via `time.monotonic()`, not instant) is the only implementation today;
  a future `RealSerialController` should be swappable in without touching any calling code. `hardware/port_scan.py`
  only enumerates COM ports/VID heuristics to guess "is this plugged in" — it never opens a connection or sends
  commands; that's a boundary intentionally left for later Arduino protocol work.
- `signals/` — the ECG acquisition + R-peak detection pipeline, ported near-verbatim from an earlier standalone
  script (`HRC.py`, no longer in the repo) and explicitly *not* to have its algorithm logic altered casually:
  - `acquisition.py`: `_acq_worker` runs in a separate `multiprocessing.Process` and talks to `mpdev.dll` (BIOPAC
    MP36) via `ctypes`. **Anything using `multiprocessing.Process` here requires the call site to guard with
    `if __name__ == "__main__":` and `multiprocessing.set_start_method('spawn', force=True)`** (see `main.py`
    pattern) or child-process spawning breaks on Windows. If `mpdev.dll`/hardware isn't available, everything
    transparently falls back to `_Demo`, a synthetic 72 BPM ECG generator — `AcquisitionWorker` hides this
    switch entirely behind one API (`start`/`drain`/`start_recording`/`stop_recording`/`write_peak`/`stop`), so
    UI code never branches on demo vs. real.
  - `filters.py`: two independent filter banks — a *display* chain (HP/LP/notch, tuned to match a BSL preset,
    used only for what gets plotted) and a separate Pan-Tompkins bandpass (`B_PT`/`A_PT`) used only for R-peak
    detection. Do not conflate the two or reuse display-filtered signal for detection math.
  - `pan_tompkins.py`: `PanTompkinsRT` is an **online/incremental** Pan-Tompkins detector (new samples only,
    ~25ms latency) with a 5s adaptive bootstrap/warmup for SPK/NPK thresholds — this is the single canonical
    implementation; there is no batch/offline variant to keep in sync.
- `ui/` — PyQt6 views wired together as pages of one `QStackedWidget` inside `MainWindow`; navigation between
  views happens purely through Qt signals emitted by each view and connected in `main_window.py`, never by a view
  reaching into another view directly. Some views (`patient_panel.py`, `ecg_recording_view.py`) are themselves a
  wizard of internal pages on their own private `QStackedWidget` (e.g. `_BasicInfoPage`, `_NameEntryPage`) that
  don't leak outside the containing view.
- `data/pending_session_store.py` — persists an in-progress `PatientProfile` (intake + HR_rest already measured)
  as one JSON file per patient under `data/pending_sessions/`, used only when Arduino isn't connected yet, so the
  operator doesn't have to redo the 2-minute HR_rest measurement. This is explicitly *not* where final trial
  results get logged (a future `session_logger.py` owns that) — don't conflate the two persistence layers.

### The full navigation flow (see `ui/main_window.py` docstring)

```
ModeSelectView -> PatientPanel -> HrRestView -> ArduinoCheckView -> PreflightChecklistView -> SessionView (full MICT runner, works today with MockSerialController)
ModeSelectView -> EcgRecordingView (independent, fully finished flow)
ModeSelectView -> "Tiếp tục session dang dở" -> ArduinoCheckView (skips PatientPanel + HrRestView, loads saved pending session)
```

`SessionView` (the actual MICT session runner) is now implemented and wired. `_on_ready_to_start` in
`main_window.py` builds a `SessionManager` (injecting `FuzzyController`, a `MockSerialController`, a
`SessionLogger`, the Karvonen zone, and the IPAQ group) with `hr_source = session_view.waveform`, then calls
`session_view.begin(...)`. The whole Heart Rate Control loop runs end-to-end **without any real hardware** (ECG via
Demo mode, resistance via Mock). The remaining hardware-dependent work is `hardware/real_serial_controller.py` +
the Arduino firmware + the serial protocol — swapping Mock→Real is a one-line change at the `hardware = ...`
construction in `_on_ready_to_start` because everything goes through the `SerialControllerBase` interface.

Control-layer specifics worth knowing before touching them:
- `control/session_manager.py` runs a 3-phase state machine on **absolute** monotonic time (never counts loop
  iterations). Each tick it reads `hardware.current_level` FIRST (telemetry as source of truth) so a physical
  button press mid-session is detected as `manual_override` rather than fought. HR-loss safety is measured in
  **real wall-clock** seconds (via `time.monotonic()`), deliberately NOT scaled by the `time_scale` test knob —
  signal loss is a physical event. `time_scale` only compresses the protocol schedule for tests.
- `control/fuzzy_controller.py` is a hand-written Mamdani controller (no scikit-fuzzy/simpful dependency), 5×3
  rule table → 15 rules, centroid defuzzification, then hard deadband + clamp to `[LEVEL_MIN, LEVEL_MAX]`.

### Data flow for a full Heart Rate Control run

1. `PatientPanel` collects demographics + IPAQ-SF answers → constructs `PatientProfile` (HRmax + IPAQ class
   computed immediately).
2. `HrRestView` streams live ECG (reusing `WaveformView`/the `signals/` pipeline) for `HR_REST_DURATION_SEC`,
   takes the median BPM of the second half of the window, then calls `patient.apply_hr_rest()`.
3. `ArduinoCheckView` gates progress on `hardware/port_scan.find_likely_arduino_port()` finding a plausible port;
   "Quit" before success offers to persist the patient via `pending_session_store.save_pending()`.
4. `PreflightChecklistView` requires every checkbox ticked before enabling start.
5. `SessionManager` calls `control/hr_target.compute_karvonen_zone(patient)` once, then runs Warmup (fixed level
   by IPAQ group) → Main (Fuzzy every 5–8 s, comparing smoothed HR to the zone) → Cooldown (linear ramp to
   Level 1, no Fuzzy), marks `HR_end_main` and `HR_at_1min_post` for HRR1, and streams both to `SessionLogger`
   (anonymised CSVs under `recordings/`). `SessionView` only renders the signals it emits and owns the STOP button.

## Data & gitignore notes

- `data/sessions/`, `data/patient_lookup.*`, `data/pending_sessions/`, and `recordings/` are gitignored — they
  hold real experimental-subject data and must never be committed.
- `mpdev.dll` (BIOPAC driver) lives at repo root and is loaded via `ctypes.windll.LoadLibrary` at a path resolved
  relative to `os.getcwd()` — the app must be launched from the repo root for hardware mode to find it (demo mode
  is unaffected). `mpdev.dll` (64-bit) depends on `xerces-c_3_1.dll` (Apache Xerces-C++) which **must also sit at
  repo root, same 64-bit architecture** — without it, `LoadLibrary` fails with "could not find … dependencies" and
  everything silently falls back to demo. Both DLLs are now present and verified against a real MP36 (connects,
  streams 1000 Hz ECG, records data+peak CSVs). Only one process can hold the MP36 at a time, so the demo-mode UI
  tests under `tests/` will grab the real device (and may fail on their ~72 BPM assumption) when an MP36 is plugged
  in — unplug it (or accept live capture) before running the suite.
