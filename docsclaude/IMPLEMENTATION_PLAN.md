# KẾ HOẠCH TRIỂN KHAI PHẦN MỀM — `ergometer_app`
### Bản chính thức · Cập nhật thời điểm hiện tại

> Tài liệu đặc tả (spec) cho phần việc phần mềm còn lại của đồ án tốt nghiệp:
> *"Thiết kế hệ thống điều khiển tải tự động trên xe đạp tập (Ergometer) dùng Fuzzy Logic dựa trên nhịp tim thời gian thực từ BIOPAC MP36."*
>
> Viết để: (1) Nhật đọc và làm theo từng bước; (2) giao từng module cho Claude Code.
> Bản này thay thế mọi bản nháp trước, và đã tích hợp đầy đủ các quyết định đã chốt (kiến trúc Arduino standalone + nút bấm, lựa chọn tự viết Mamdani).

---

## 0. Cách dùng tài liệu này

- Mỗi module là **một đơn vị làm-xong-test-được độc lập**. Không viết dở nhiều file cùng lúc.
- Làm theo **thứ tự milestone** ở Mục 2. Thứ tự đã sắp theo phụ thuộc; phần lớn test được ngay ở **Mock/Demo mode** (không cần phần cứng thật).
- Với Claude Code: giao **một module một lần**, kèm mục đặc tả tương ứng ở Mục 3, và cập nhật `PROJECT_CONTEXT.md` sau mỗi module xong.

**Quy ước bắt buộc (giữ nguyên xuyên suốt):**
- PowerShell: **mỗi lệnh một dòng**, **không dùng `&&`** (dùng `;` nếu buộc phải nối trên một dòng).
- Package tín hiệu là `signals/` (KHÔNG phải `signal/` — tránh che module chuẩn của `multiprocessing`).
- `recordings/` và `data/sessions/` luôn nằm trong `.gitignore`. Xuất CSV chỉ dùng `patient_id` (UUID ẩn danh), không ghi tên thật.
- `SHOW_DEBUG_INFO = False` ở bản production. HRmax tính ngầm, không hiển thị UI.
- Kỷ luật thuật ngữ: `HRR` = Heart Rate **Reserve** (đầu vào Karvonen). `HR_recovery` / `HRR1` = Heart Rate **Recovery** (sau gắng sức). **Không dùng lẫn** trong code lẫn báo cáo.

---

## 1. Nguyên lý kiến trúc cốt lõi (đọc trước khi code)

### 1.1 Vòng điều khiển kín
```
BIOPAC MP36 (ECG 1000 Hz) → Pan-Tompkins → HR thực tế
        → so với HR mục tiêu (Karvonen 60–80% HRR)
        → Fuzzy Logic → mức tải mong muốn (1–16)
        → serial USB → Arduino → motor phanh GENUS-249
        → HR thay đổi → đo lại → lặp
```
Biến điều khiển là **HR_actual vs HR_target**, KHÔNG phải ECG. ECG chỉ là phương thức thu nhận.

### 1.2 Quan hệ Arduino ↔ Python (RẤT QUAN TRỌNG — nền tảng của toàn bộ phần hardware)

- **Firmware Arduino nạp vĩnh viễn, luôn chạy độc lập**, thay thế hoàn toàn board hãng. Đây là **trạng thái vận hành bình thường, đầy đủ, tự thân** của thiết bị — KHÔNG phải "chế độ dự phòng khi mất PC".
- Standalone điều khiển bằng **nút bấm vật lý tăng/giảm level** (giống board hãng cũ). Người dùng luôn chỉnh tay được, có Python hay không.
- **Rút USB → xe vẫn chạy bình thường.** Cắm USB + Python gọi lệnh → mới có thêm điều khiển level **chính xác tự động** theo HR.
- Python **không tạo ra sự ổn định** của thiết bị. Python chỉ là **một kênh gọi lệnh thêm vào**, gọi đúng hàm đã cài sẵn trong firmware.
- **Điểm hội tụ duy nhất:** cả nút bấm lẫn lệnh serial đều phải gọi qua **một hàm firmware duy nhất** `applyLevel(n)`. Không có 2 nguồn sự thật về vị trí motor.
- **An toàn phần cứng độc lập với phần mềm:** nút bấm luôn sống, kể cả khi phiên tự động đang chạy. Đây mới là lớp "fail-safe" thật của hệ thống.

### 1.3 Kiến trúc 5 layer (giữ nguyên)
| Layer | Trách nhiệm | Nguyên tắc |
|-------|-------------|-----------|
| UI | PyQt6 widgets, waveform | Chỉ hiển thị + nhận input, không chứa logic |
| Signal | Thu ECG, Pan-Tompkins, HR | Chạy subprocess riêng (BHAPI giữ GIL) |
| Control | Karvonen, state machine, Fuzzy | Nhận HR → tính → ra lệnh Hardware |
| Hardware | Serial với Arduino | Chỉ gửi lệnh/nhận telemetry, không chứa logic điều khiển |
| Data | Lưu trữ, xuất báo cáo | Không tính toán, chỉ đọc/ghi |

Nguyên tắc: **mỗi layer chỉ nói chuyện với layer liền kề.**

---

## 2. Trạng thái codebase & lộ trình

### 2.1 Đã xong, đã test (Demo/Mock mode)
| Layer | Module |
|-------|--------|
| Core | `core/config.py` |
| Data | `data/patient.py` (có `to_raw_dict`/`from_raw_dict`), `data/pending_session_store.py` |
| Control | `control/hr_target.py` (Karvonen, Tanaka, THR) |
| Signal | `signals/constants.py`, `filters.py`, `pan_tompkins.py`, `acquisition.py` |
| Hardware | `hardware/port_scan.py`, `serial_controller_base.py`, `mock_serial_controller.py` |
| UI | `ModeSelectView`, `EcgRecordingView`, `WaveformView`, `PatientPanel`, `HrRestView`, `ArduinoCheckView`, `PreflightChecklistView` |

### 2.2 Còn thiếu (phạm vi bản kế hoạch này)
| ID | Module | Vai trò |
|----|--------|---------|
| **M1** | `control/fuzzy_controller.py` | Bộ suy luận mờ — trái tim pha Main |
| **M2** | `control/session_manager.py` | State machine 3 pha, nhạc trưởng vòng điều khiển |
| **M3** | `data/session_logger.py` | Ghi CSV time-series + event log |
| **M4** | `ui/session_view.py` | Màn hình MICT: HR/ECG/level/log/stop |
| **M5** | Giao thức Serial PC↔Arduino | Hợp đồng giao tiếp (thiết kế giấy) |
| **M6** | `hardware/real_serial_controller.py` | pyserial, hiện thực interface theo M5 |
| **M7** | Firmware Arduino (`ergometer_firmware/`) | 4 bước, PlatformIO |
| **M8** | `data/export_manager.py` | Báo cáo sau buổi tập (làm sau) |
| **M9** | `main.py` / `main_window.py` wiring | Nối SessionView vào luồng |

### 2.3 Sơ đồ phụ thuộc
```
config ─┬─> M1 fuzzy ─┐
        ├─> hr_target ─┼─> M2 session_manager ─┬─> M4 session_view ─> M9 wiring
        └─> M3 logger ─┘                        │
                                                │
M5 serial protocol (giấy) ─┬─> M6 real_serial ──┴─> Tích hợp phần cứng
                           └─> M7 firmware ─────────┘
```
**Đường tới hạn để có demo phần mềm hoàn chỉnh (không cần Arduino):** M1 → M3 → M2 → M4 → M9, chạy với `MockSerialController`.

### 2.4 Lộ trình milestone
| Bước | Nội dung | Test khi xong | Cần HW? |
|------|----------|---------------|:---:|
| 1 | **M1** Fuzzy controller | Unit test 15 ô bảng luật + biên | Không |
| 2 | **M3** Session logger | Ghi thử CSV, mở Excel kiểm tra cột | Không |
| 3 | **M2** Session manager | Chạy 1 session nén thời gian với Mock → kiểm tra pha/level/HRR1 | Không |
| 4 | **M4** Session view | HR/level/log cập nhật realtime với Mock | Không |
| 5 | **M9** Wiring | Đi hết luồng ModeSelect → Session không rơi | Không |
| — | ✅ **Mốc: phần mềm PC đóng vòng hoàn chỉnh (Mock)** | | |
| 6 | **M5** Chốt giao thức serial (giấy) | Review bảng lệnh/telemetry đủ 2 phía | Không |
| 7 | **M7-1..2** Firmware standalone | Nút bấm + home chạy độc lập, không cần PC | **Có** |
| 8 | **M7-3** Firmware serial | `SET/HOME` gọi chung `applyLevel()`, `TLM` báo đúng | **Có** |
| 9 | **M6** Real serial controller | Đổi 1 dòng khởi tạo, chạy Session với Arduino thật | **Có** |
| 10 | **M7-4** Hiệu chuẩn LUT | Dựng bảng Level↔V, chạy full 30 phút không đạp | **Có** |
| 11 | **M8** Export báo cáo | Xuất báo cáo 1 buổi mẫu | Không |

> **Nguyên tắc:** hoàn tất trọn vẹn bước 1–5 (toàn bộ Mock) **trước** khi động vào firmware.

---

## 3. Đặc tả chi tiết từng module

### 3.1 M1 — `control/fuzzy_controller.py`

**Mục đích:** cho biết cần **thay đổi mức tải bao nhiêu** (Δlevel) để kéo HR về vùng mục tiêu. Chỉ dùng trong pha Main.

**Quan hệ vật lý cốt lõi:** ở cadence cố định 60–70 RPM, **tăng level → tăng công suất → HR tăng**; giảm level → HR giảm. Do đó:
- HR **dưới** vùng mục tiêu → **tăng** level.
- HR **trên** vùng mục tiêu → **giảm** level.

**Hai đầu vào (cấu trúc PD mờ):**
1. `e = HR_target_center − HR_actual` (bpm), `HR_target_center` = trung điểm vùng = 70% HRR.
   - `e > 0` ⇒ HR thấp hơn mục tiêu ⇒ cần tăng level.
   - `e < 0` ⇒ HR cao hơn mục tiêu ⇒ cần giảm level.
2. `de = (HR_now − HR_prev) / Δt` — xu hướng HR trên cửa sổ update (5–8 s). Dùng đón đầu, tránh overshoot.

> **Dữ liệu:** `HR_actual` đưa vào fuzzy là **HR đã làm mượt** (median/trung bình trượt ~5–8 s), không phải giá trị tức thời từng nhịp — để loại outlier Pan-Tompkins.

**Đầu ra:** `Δlevel ∈ {−2, −1, 0, +1, +2}` (đã gồm rate-limiting: mỗi lần chỉnh tối đa 2 mức).

**Tập mờ `e` (bpm, vũ trụ ~[−30, +30]), 5 tập tam giác/hình thang:**
- `NB` (âm lớn, HR cao hơn nhiều): đỉnh ≈ −18
- `NS` (âm nhỏ): đỉnh ≈ −8
- `ZE` (vùng chết ±3 bpm): đỉnh 0, chân ±6
- `PS` (dương nhỏ): đỉnh ≈ +8
- `PB` (dương lớn, HR thấp hơn nhiều): đỉnh ≈ +18

**Tập mờ `de` (bpm/cửa sổ, vũ trụ ~[−10, +10]), 3 tập:**
- `FALL` (HR giảm): đỉnh ≈ −4
- `STEADY` (ổn định): đỉnh 0
- `RISE` (HR tăng): đỉnh ≈ +4

**Tập mờ ra `Δlevel` (singleton/tam giác trên [−2.5, +2.5]):** `NB=−2, NS=−1, ZE=0, PS=+1, PB=+2`.

**Bảng luật (15 luật; hàng = `e`, cột = `de`):**

| `e` \ `de` | RISE | STEADY | FALL |
|------------|:----:|:------:|:----:|
| **NB** (HR ≫ mục tiêu) | NB | NB | NS |
| **NS** | NS | NS | ZE |
| **ZE** (trong vùng) | NS | ZE | PS |
| **PS** | ZE | PS | PS |
| **PB** (HR ≪ mục tiêu) | PS | PB | PB |

*Tính chất (nêu khi bảo vệ):* **đơn điệu** theo `e`, **đối xứng** qua tâm, cột RISE/FALL dịch đầu ra một bậc để đón đầu overshoot; hàng `ZE` cho nhích nhẹ chống trôi khi HR tiến sát biên vùng.

**Suy luận & giải mờ:** Mamdani, hợp thành **min**, hợp luật **max**, giải mờ **centroid (COG)** → làm tròn về số nguyên gần nhất trong {−2..+2}.

**Chốt chặn sau fuzzy (bắt buộc):**
1. **Vùng chết cứng:** nếu `|e| ≤ HR_DEADBAND_BPM (3)` **và** `|de|` nhỏ → ép `Δlevel = 0` (chống rung, không phụ thuộc giải mờ).
2. `new_level = clamp(current_level + Δlevel, 1, 16)` — **hard clamp** 1..16.
3. `new_level` ngoài dải kỳ vọng [5, 10] → **chỉ ghi cảnh báo** (soft warn), không chặn.

**Interface:**
```python
class FuzzyController:
    def __init__(self, config): ...
    def compute(self, hr_actual: float, hr_target_center: float,
                hr_prev: float, dt: float, current_level: int) -> FuzzyResult: ...

@dataclass
class FuzzyResult:
    delta_level: int        # {-2..+2}
    new_level: int          # 1..16 sau clamp
    error: float            # e
    error_rate: float       # de
    crisp_output: float     # trước khi làm tròn (cho báo cáo)
    out_of_range: bool      # new_level ngoài [5,10]?
```

**Chọn thư viện — quyết định: TỰ VIẾT Mamdani (numpy, ~120–150 dòng) cho bản production.**

| Tiêu chí | Tự viết (numpy) | scikit-fuzzy | simpful |
|----------|:---:|:---:|:---:|
| Minh bạch / audit từng bước | Cao nhất | Trung bình | Cao (luật dạng câu chữ) |
| Rủi ro đóng gói `.exe` | Thấp nhất (0 dep ngoài numpy) | Cao (kéo theo `networkx`) | Thấp (chỉ numpy/scipy) |
| Được peer-review | Không | Có | Có (IJCIS 2020) |
| Phù hợp quy mô 2-input/15-luật | Vừa khít | Quá cỡ | Vừa |
| Tích hợp chốt an toàn | Trong cùng hàm | Phải bọc ngoài | Phải bọc ngoài |

Lý do chọn tự viết (trọng số cao nhất là **an toàn vận hành**, vì đây là bộ điều khiển chạy trên tải vật lý gắn với nhịp tim người thật):
1. Ít điểm hỏng nhất khi đóng `.exe` — tránh rủi ro hidden-import trên máy sạch mà Nhật từng gặp.
2. Chốt an toàn (vùng chết, clamp) nằm ngay trong cùng hàm, không ghép lên output thư viện.
3. Test được toàn bộ 15 ô — dễ chứng minh "đầu ra đúng thiết kế" với hội đồng.
4. Bài toán quá nhỏ để framework tổng quát có lợi ích thật.

**Kiểm chứng chéo (không đưa vào production):** dựng lại đúng hệ luật một lần bằng `simpful`, so output với bản tự viết trên cùng tập `(e, de)`. Khớp → dùng làm bằng chứng "đã kiểm chứng chéo với thư viện peer-reviewed" trong báo cáo, mà không gánh dependency lúc chạy thật. (Chọn `simpful` vì gọn hơn `scikit-fuzzy`, không kéo `networkx`, và bài báo gốc đã đối chiếu số học với scikit-fuzzy cho kết quả trùng khớp.)

**Definition of Done:** unit test đi qua **cả 15 ô** bảng luật (dựng `e`, `de` rơi đúng 1 tập, kiểm `delta_level`), test vùng chết, clamp biên (level 1 & 16), cảnh báo out-of-range. Script đối chiếu với `simpful` cho kết quả khớp.

---

### 3.2 M2 — `control/session_manager.py`

**Mục đích:** nhạc trưởng toàn buổi tập — chạy state machine 3 pha theo **đồng hồ tuyệt đối**, lấy HR từ Signal, gọi Fuzzy ở pha Main, ra lệnh level xuống Hardware (qua interface, không quan tâm Mock/Real), và ghi log.

**Phụ thuộc tiêm vào (dependency injection — để test được với Mock):**
`hr_source` (HR mới nhất từ subprocess), `controller` (FuzzyController), `hardware` (kiểu `SerialControllerBase`), `logger` (SessionLogger), `hr_target_result` (THR_low/high, HR_center từ Karvonen), `patient_group` (IPAQ), `config`.

**State machine (mốc thời gian tuyệt đối, `QElapsedTimer`/`time.monotonic()`):**
| Pha | Khung | Cơ chế |
|-----|-------|--------|
| WARMUP | 0:00–5:00 | Level cố định theo nhóm IPAQ (`WARMUP_LEVEL_SEDENTARY`/`ACTIVE`), set 1 lần |
| MAIN | 5:00–25:00 | Gọi Fuzzy mỗi `FUZZY_UPDATE_INTERVAL_SEC` (5–8 s) |
| COOLDOWN | 25:00–30:00 | Ramp tuyến tính level → 1 (KHÔNG Fuzzy) |

**Vòng lặp tick (`QTimer` ~250 ms, main thread; acquisition đã ở subprocess riêng):**
1. `elapsed = timer.elapsed()`; xác định pha bằng `_phase_for(elapsed)` (so mốc tuyệt đối, **không đếm số vòng Fuzzy**).
2. Lấy `hr_now` mới nhất; cập nhật cửa sổ làm mượt.
3. **Đọc telemetry trước** (`TLM`) → lấy `level` **thực tế** làm nguồn sự thật. Nếu khác level phần mềm nghĩ đang có (do kỹ thuật viên bấm nút vật lý) → ghi `manual_override`, cập nhật `current_level` theo thực tế; **không** cố "sửa lại".
4. Xử lý theo pha, luôn tính Δlevel **dựa trên `current_level` vừa đọc từ telemetry**, không dựa giá trị cache.
5. RPM trong telemetry ngoài 60–70 → phát cảnh báo cadence.
6. Ghi log time-series (gồm cả thay đổi do nút bấm); emit signal cập nhật UI.

**Xử lý từng pha:**
- `_run_warmup()`: chưa set → `hardware.send_level(warmup_level)`, log, set cờ. (Nút bấm đổi trong pha này thì cứ để nguyên, chỉ log.)
- `_run_main()`: nếu `elapsed − last_fuzzy_t ≥ interval` → `controller.compute(hr_now, hr_target_center, hr_prev, dt, current_level_from_telemetry)`; nếu `new_level != current_level` → `send_level`, log kèm `error/error_rate/crisp_output`; cập nhật `last_fuzzy_t`, `hr_prev`.
- `_run_cooldown()`: `target = round(interp(current→1 theo tiến độ))`; đổi → `send_level`.

> **Vì sao đọc telemetry trước khi tính Fuzzy là bắt buộc:** nút bấm vật lý luôn sống song song (Mục 3.5). Coi `TLM.level` là chân lý duy nhất giúp vòng điều khiển tự phục hồi đúng hướng ở lần tính kế tiếp, không cần logic xử lý "xung đột".

**Hai mốc HRR1 (bắt buộc):**
- `t = 25:00` (hết Main): chốt `HR_end_main`.
- `t = 26:00` (Main + `HRR1_MARK_OFFSET_SEC`): chốt `HR_at_1min_post`.
- `HRR1 = HR_end_main − HR_at_1min_post` → summary. (Đây là lý do cool-down không dùng Fuzzy — giữ phép đo hồi phục sạch.)

**An toàn khi mất/nhiễu HR:**
- Không có HR hợp lệ quá `HR_STALE_TIMEOUT_SEC` (đề xuất thêm config, ~8 s): **giữ level**, phát `safety_event`.
- Kéo dài quá ngưỡng dài hơn (~20 s): gửi `SET 1` (ramp về Level 1) + cảnh báo UI. (Nút bấm vẫn luôn sẵn sàng nếu kỹ thuật viên muốn khác.)

**Qt signals:**
```python
class SessionManager(QObject):
    phase_changed    = pyqtSignal(str)        # WARMUP/MAIN/COOLDOWN/DONE
    level_changed    = pyqtSignal(int, str)   # level, lý do (warmup/fuzzy/cooldown/manual_override/safety)
    hr_updated       = pyqtSignal(float)
    tick             = pyqtSignal(int, int)   # elapsed_sec, remaining_sec
    cadence_warning  = pyqtSignal(float)
    safety_event     = pyqtSignal(str)
    session_finished = pyqtSignal(dict)       # summary: time-in-zone, HRR1, ...
    def start(self): ...
    def stop(self, reason: str): ...          # gửi SET 1 rồi kết thúc an toàn
```

**Test không cần phần cứng:** cờ **nén thời gian** (`time_scale`, chỉ để test) — chạy trọn 30 phút trong ~30 giây với `MockSerialController` random-walk. Kiểm tra: đủ 3 pha đúng mốc, level đổi ≤2 bậc/lần trong Main, HRR1 được chốt, log đủ dòng, phát hiện `manual_override` khi Mock giả lập nút bấm.

**Definition of Done:** chạy 1 session Mock trọn vẹn từ test (chưa cần UI), sinh file log hợp lệ + summary có HRR1.

---

### 3.3 M3 — `data/session_logger.py`

**Mục đích:** ghi lại buổi tập để phân tích và làm bằng chứng đồ án. **Ẩn danh** (chỉ `patient_id`).

**Time-series** (~1 Hz), `recordings/<patient_id>_<timestamp>_timeseries.csv`:
| Cột | Ý nghĩa |
|-----|---------|
| `t_sec` | giây từ khi bắt đầu |
| `phase` | WARMUP/MAIN/COOLDOWN |
| `hr_actual` | HR đã làm mượt (bpm) |
| `hr_target_low`/`hr_target_high` | biên vùng (60/80% HRR) |
| `level` | mức tải thực tế (từ telemetry) |
| `rpm` | cadence từ telemetry |
| `source` | button/serial (nguồn đổi level gần nhất) |
| `in_zone` | HR trong vùng? (0/1) |

**Event log**, `..._events.csv`: mỗi dòng một sự kiện (đổi level kèm `error/error_rate/crisp_output`, chuyển pha, mốc HRR1, `manual_override`, `safety_event`, `cadence_warning`) + timestamp.

**Interface:**
```python
class SessionLogger:
    def __init__(self, patient_id: str, config): ...
    def log_sample(self, t_sec, phase, hr, low, high, level, rpm, source, in_zone): ...
    def log_event(self, t_sec, kind: str, detail: dict): ...
    def finalize(self, summary: dict) -> Path: ...
```

**Definition of Done:** tạo được 2 CSV, mở Excel thấy cột đúng, không có tên thật.

---

### 3.4 M4 — `ui/session_view.py`

**Mục đích:** màn hình MICT — nơi kỹ thuật viên theo dõi buổi tập. Chỉ hiển thị + nhận input; logic ở SessionManager.

**Hiển thị:**
- Waveform ECG realtime (tái dùng `WaveformView`).
- Số HR lớn + dải vùng mục tiêu (band THR_low..THR_high), đổi màu khi HR ra ngoài.
- Level hiện tại (1–16) + chỉ báo pha; hiển thị nhãn nhỏ nếu level vừa bị đổi do nút bấm (`manual_override`).
- Đồng hồ: đã trôi / còn lại.
- Bảng event log cuộn.
- Nút STOP an toàn (đỏ, to): gọi `session_manager.stop("user")` → `SET 1` → kết thúc.

**Kết nối signal (chỉ subscribe):**
```
hr_updated       -> số HR + band
level_changed    -> level + append log (phân biệt lý do fuzzy/manual_override/...)
phase_changed    -> nhãn pha
tick             -> đồng hồ
cadence_warning  -> cảnh báo "giữ 60–70 RPM"
safety_event     -> banner cảnh báo
session_finished -> chuyển màn hình tổng kết
```

> Test UI: dùng **`QTimer` polling ~150 ms** kiểm tra điều kiện, **không** dùng `singleShot` cố định (render UI Windows có độ trễ biến thiên → race condition).

**Definition of Done:** mở SessionView với `MockSerialController`, thấy HR/level/log/đồng hồ chạy mượt suốt 3 pha, nút STOP hoạt động.

---

### 3.5 M5 — Giao thức Serial PC ↔ Arduino

> Thiết kế **trên giấy trước**, vì cả M6 và M7 phải tuân cùng hợp đồng. Xem nền tảng ở Mục 1.2.

**Tầng vật lý:** USB serial, **115200 baud**, dòng ASCII kết thúc `\n`.

**PC → Arduino (Python chỉ gọi thêm, không chiếm quyền):**
| Lệnh | Ý nghĩa |
|------|---------|
| `SET <1..16>` | Gọi `applyLevel(n)` — set mức chính xác |
| `HOME` | Home routine về Level 1 (công tắc ZERO) |
| `PING` | (tùy chọn) Python tự kiểm tra kết nối — không phải điều kiện để thiết bị chạy |

**Arduino → PC:**
| Dòng | Ý nghĩa |
|------|---------|
| `ACK SET <level>` | Đã thực thi `applyLevel` |
| `TLM <level> <rpm> <posV> <source>` | Telemetry ~2 Hz: level **thực tế** (dù do nút hay serial), RPM bàn đạp, điện áp biến trở thô, `source`=button/serial |
| `HOMED` | Home xong |
| `PONG` | Trả lời PING |
| `ERR <code>` | Lỗi |

**Điểm hội tụ duy nhất:** cả nút bấm và `SET` đều gọi `applyLevel(n)`. Nút tăng → `applyLevel(current+1)`, nút giảm → `applyLevel(current−1)` (có debounce, clamp 1–16). Nút bấm **không bị vô hiệu hóa** khi có Python.

**Hệ quả cho PC (M2):** `SessionManager` **luôn đọc `TLM.level` làm nguồn sự thật** trước mỗi lần tính Fuzzy; lệch kỳ vọng → log `manual_override`, tính tiếp từ thực tế.

**Không cần "MODE PC"/watchdog-tự-về-standalone:** standalone không phải trạng thái khẩn cấp mà là nền vốn đã an toàn (nút bấm). Mất Python/USB → thiết bị không "rơi vào nguy hiểm", chỉ là không còn ai gọi `SET`.

**Điều khiển vị trí trên Arduino:** `level` → V mục tiêu qua **LUT Level→V thực nghiệm**; motor bước chạy theo phản hồi chân **V** (vòng kín trên Arduino) tới dung sai; **ZERO** hiệu chuẩn Level 1.

**Definition of Done:** duyệt bảng lệnh/telemetry; xác nhận `applyLevel()` là điểm hội tụ duy nhất của 2 nguồn (nút + serial).

---

### 3.6 M6 — `hardware/real_serial_controller.py`

**Mục đích:** hiện thực `SerialControllerBase` bằng `pyserial` theo M5. **Không chứa logic điều khiển** — chỉ dịch method ↔ dòng serial.
```python
class RealSerialController(SerialControllerBase):
    def connect(self) -> bool:          # mở cổng, đọc thử 1 TLM để xác nhận sống
    def send_level(self, level: int):   # gửi "SET <level>", chờ ACK (timeout)
    def home(self):                     # gửi "HOME", chờ HOMED
    def ping(self):                     # gửi "PING" — chỉ để Python kiểm tra kết nối
    def read_telemetry(self) -> Telemetry | None:  # parse TLM: level thực tế + rpm + source
    def stop(self):                     # gửi "SET 1"
    def disconnect(self): ...
```
- Đọc serial **non-blocking** (thread đọc riêng / `in_waiting`), tránh chặn UI thread.
- Parse phòng thủ: dòng méo → bỏ qua, không crash.
- Cổng lấy từ `hardware/port_scan.py`.
- Không có bước "chuyển mode" khi connect.

**Chuyển Mock↔Real:** đổi **1 dòng khởi tạo** trong `main.py`/config. Logic M2 không đổi.

**Definition of Done:** với firmware M7-3, `send_level` nhận `ACK`, `read_telemetry` trả `TLM` hợp lệ.

---

### 3.7 M7 — Firmware Arduino (`ergometer_firmware/`, PlatformIO)

> **Thư mục/repo riêng**, không gộp vào `ergometer_app`. 4 bước, mỗi bước test độc lập.

**Bước 1 — Setup PlatformIO:** `platformio.ini` (`board = uno`, `framework = arduino`), khung `src/main.cpp`, biên dịch chạy.

**Bước 2 — Standalone (bộ điều khiển vĩnh viễn thay board hãng):**
- Đọc **V** (biến trở vị trí), **ZERO** (limit), **COUNT** (RPM), **2 nút bấm** tăng/giảm level.
- Viết **hàm hội tụ duy nhất** `applyLevel(int n)`: level → tra LUT Level→V → chạy motor bước tới dung sai quanh V mục tiêu. Mọi nguồn (nút, serial) **chỉ được gọi qua hàm này**.
- Nút tăng → `applyLevel(current+1)`; nút giảm → `applyLevel(current−1)`; debounce + clamp 1–16.
- **Home routine:** về ZERO → Level 1, gán `current = 1`.
- *Mục tiêu:* toàn bộ vòng điều khiển vị trí chạy ổn định **độc lập hoàn toàn với PC**.

**Bước 3 — Thêm lớp serial (theo M5):**
- Command parser: `SET n` → gọi **cùng** `applyLevel(n)`; `HOME` → home routine; phát `ACK/TLM/HOMED/PONG/ERR`.
- `TLM` ~2 Hz, luôn phản ánh `current` thực tế + `source`.
- **Không phải chuyển mode** — vòng lặp chính (đọc nút, giữ vị trí) vẫn chạy như Bước 2; parser serial chỉ là một nguồn gọi `applyLevel()` nữa, không tắt nút bấm.

**Bước 4 — Tích hợp + hiệu chuẩn LUT:**
- Dựng **LUT Level↔V thực nghiệm**: chạy tới từng mức (bằng nút hoặc Serial Monitor), ghi V ổn định → bảng 16 phần tử nạp cứng vào firmware.
- Ghép `RealSerialController` (M6), chạy full 30 phút **không đạp**, thử gửi `SET` **và** bấm nút xen kẽ, xác nhận `TLM.level` luôn đúng và `SessionManager` phát hiện đúng `manual_override`.

---

### 3.8 M8 — `data/export_manager.py` (làm sau cùng)

**Mục đích:** báo cáo sau buổi tập, làm hình/bảng cho đồ án.
**Tính từ log:** tổng thời gian, **% time-in-zone**, HR trung bình/đỉnh, **HRR1**, histogram phân bố level, đồ thị HR(t) kèm dải vùng + dấu mốc chuyển pha.
**Đầu ra:** HTML/PDF + ảnh PNG đồ thị (matplotlib / export pyqtgraph). Ẩn danh.
**Definition of Done:** xuất 1 báo cáo từ log session Mock, đồ thị đọc được.

---

### 3.9 M9 — `main.py` / `main_window.py` wiring

**Mục đích:** nối `SessionView` vào cuối luồng: `PreflightChecklistView` → khởi tạo `SessionManager` (tiêm Fuzzy + hardware Mock/Real + logger + hr_target_result + nhóm IPAQ) → mở `SessionView`.
- Chọn Mock/Real qua config/flag khởi động.
- Thoát giữa chừng: gọi `stop`, đóng logger, lưu pending session (`pending_session_store` đã có).

**Definition of Done:** đi hết luồng ModeSelect → PatientPanel → HrRest → ArduinoCheck → Preflight → Session → tổng kết, không rơi (Mock mode).

---

## 4. An toàn & failsafe (xuyên suốt, ưu tiên cao nhất)

**Nền tảng:** an toàn phần cứng **không phụ thuộc Python còn sống hay không** — nút bấm vật lý luôn là lớp an toàn độc lập. Vai trò phần mềm: (1) tự động hóa chỉnh level theo HR khi bình thường; (2) **phát hiện đúng** khi có can thiệp tay để không đấu ngược kỹ thuật viên.

| Tình huống | Hành vi |
|------------|---------|
| PC/USB rớt kết nối giữa phiên | Thiết bị **chạy bình thường** ở level hiện tại; nút bấm dùng được ngay. Không phải sự cố khẩn cấp. |
| Kỹ thuật viên bấm nút giữa Main | Phát hiện qua `TLM.level` lệch → log `manual_override`; Fuzzy tính tiếp từ level thực tế (không tranh chấp) |
| Mất HR ngắn (>8 s) | **Giữ level**, cảnh báo, không hành động trên HR cũ |
| Mất HR kéo dài (>20 s) | Gửi `SET 1` + cảnh báo UI; nút bấm vẫn sẵn sàng |
| Bấm STOP trên UI | Gửi `SET 1` + kết thúc session an toàn |
| Level tính ngoài 1–16 | **Hard clamp** 1–16 (cả Fuzzy lẫn `applyLevel()` firmware) |
| Level ngoài dải 5–10 | Chỉ cảnh báo/log, không chặn |
| Cadence ngoài 60–70 RPM | Cảnh báo UI |

**Nguyên tắc vàng:** khi **phần mềm chủ động hành động** trong tình huống bất định → **quy về Level 1**. Nhưng lớp "fail-safe" thật của hệ thống là **nút bấm vật lý độc lập**, luôn dùng được, không phụ thuộc phần mềm.

---

## 5. Chiến lược kiểm thử

**Unit test (không HW):**
- `fuzzy_controller`: 15 ô bảng luật + vùng chết + clamp biên; đối chiếu `simpful`.
- `session_manager`: clock giả → 3 pha đúng mốc, HRR1, `manual_override`.
- `hr_target`: đã có.

**Integration Mock (không HW):** full session **nén thời gian** với `MockSerialController` random-walk → xác minh pha, ≤2 level/lần Main, log đầy đủ, HRR1, `manual_override` (Mock giả lập nút), failsafe khi cắt HR giả.

**UI test:** `QTimer` polling ~150 ms (không `singleShot`).

**Bring-up phần cứng (giảm rủi ro theo thứ tự):** firmware bước 2 (nút + home độc lập) → 3 (serial) → 4 (LUT) → `RealSerialController` → chạy 30 phút **không đạp** → mới cho người tập.

**Windows/PowerShell:** mỗi lệnh một dòng, không `&&`. Test `.exe` trên máy **không cài Python** sớm.

---

## 6. Checklist Definition-of-Done tổng

- [ ] M1 Fuzzy — 15 ô + biên + đối chiếu simpful
- [ ] M3 Logger — 2 CSV hợp lệ, ẩn danh
- [ ] M2 SessionManager — session Mock nén thời gian trọn vẹn, có HRR1 + manual_override
- [ ] M4 SessionView — realtime 3 pha với Mock, STOP hoạt động
- [ ] M9 Wiring — đi hết luồng không rơi (Mock) ✅ **mốc: phần mềm PC đóng vòng hoàn chỉnh**
- [ ] M5 Giao thức serial — chốt bảng lệnh/telemetry, xác nhận `applyLevel()` hội tụ
- [ ] M7-1..2 Firmware standalone — nút bấm + home chạy độc lập không cần PC
- [ ] M7-3 Firmware serial — `SET/HOME` gọi chung `applyLevel()`, `TLM` đúng level + source
- [ ] M6 RealSerialController — `ACK`/`TLM` với Arduino thật
- [ ] M7-4 Hiệu chuẩn LUT + chạy 30 phút không đạp, thử xen kẽ SET/nút
- [ ] M8 Export báo cáo — 1 báo cáo mẫu có đồ thị
- [ ] Test `.exe` trên máy không cài Python

---

*Ưu tiên: hoàn tất M1→M3→M2→M4→M9 (toàn bộ Mock) trước — phần bảo vệ được logic điều khiển mà không phụ thuộc lịch phần cứng.*
