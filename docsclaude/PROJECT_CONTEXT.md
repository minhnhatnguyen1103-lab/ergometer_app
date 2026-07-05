# ergometer_app — Project Context & Roadmap

> Tài liệu này tổng hợp toàn bộ ngữ cảnh, quyết định thiết kế, và trạng thái xây dựng phần mềm tính đến hiện tại. Đưa file này cho Claude Code (VS Code) đọc để nó nắm đầy đủ bối cảnh trước khi code tiếp — tránh phải giải thích lại từ đầu.

---

## 1. Mục tiêu đồ án

Sinh viên kỹ thuật y sinh (HCMUT), đồ án tốt nghiệp: hệ thống điều khiển vòng kín nhịp tim (closed-loop heart rate control) trên xe đạp lực kế GENUS-249.

**Mục tiêu lâm sàng**: tự động duy trì nhịp tim đối tượng trong vùng MICT 60–80% HRR (Karvonen) suốt buổi tập chuẩn hóa 30 phút (5 phút khởi động → 20 phút tập chính → 5 phút hồi phục), thay thế việc chỉnh kháng lực thủ công.

**Phạm vi đồ án** (quan trọng khi viết báo cáo): hệ thống chứng minh khả năng *duy trì HR trong vùng mục tiêu*, KHÔNG chứng minh cải thiện sức khỏe tim mạch dài hạn (cần can thiệp nhiều tuần để chứng minh điều đó).

---

## 2. Kiến trúc phần mềm — 5 layer

```
UI layer        →  PyQt6 widgets, pyqtgraph. Chỉ hiển thị + nhận input, KHÔNG có logic nghiệp vụ.
Signal layer     →  Thu ECG (BHAPI/MP36), Pan-Tompkins, ước lượng HR. Chạy subprocess riêng.
Control layer    →  Karvonen, state machine session, Fuzzy (sau này). Tính toán, ra lệnh xuống Hardware.
Hardware layer   →  Giao tiếp Arduino. Tách hoàn toàn khỏi logic điều khiển.
Data layer       →  Lưu trữ, xuất báo cáo. Không có logic tính toán.
```

Nguyên tắc: mỗi layer chỉ nói chuyện với layer liền kề.

---

## 3. Cấu trúc folder hiện tại

```
ergometer_app/
├── venv/
├── .gitignore
├── requirements.txt          # PyQt6, pyqtgraph, scipy, numpy, pyserial
├── main.py                   # entry point QApplication -> MainWindow
├── CLAUDE.md                 # tự sinh bởi /init trong Claude Code
├── mpdev.dll                 # BHAPI DLL (không đầy đủ dependency - xem mục 9)
│
├── core/
│   └── config.py             # ✅ TẤT CẢ hằng số/ngưỡng của hệ thống — xem mục 6
│
├── data/
│   ├── patient.py            # ✅ PatientProfile — IPAQ-SF, Karvonen input
│   ├── pending_session_store.py  # ✅ lưu/khôi phục session dang dở (JSON)
│   ├── pending_sessions/     # (gitignored) file JSON session dang dở
│   ├── session_logger.py     # ⏳ CHƯA VIẾT
│   └── export_manager.py     # ⏳ CHƯA VIẾT
│
├── signals/                  # LƯU Ý: có "s" — tránh trùng module chuẩn `signal` của Python
│   ├── constants.py          # ✅ FS, BUF, CHUNK, MP36_GAIN, BPM_MIN/MAX...
│   ├── filters.py            # ✅ filter bank (HP/LP1/LP2/Notch + Pan-Tompkins BPF)
│   ├── pan_tompkins.py       # ✅ PanTompkinsRT — copy nguyên từ HRC.py, không sửa logic
│   └── acquisition.py        # ✅ AcquisitionWorker — multiprocessing + BHAPI, fallback Demo mode
│
├── control/
│   ├── hr_target.py          # ✅ Karvonen: compute_karvonen_zone()
│   ├── session_manager.py    # ⏳ CHƯA VIẾT — việc tiếp theo, xem mục 7
│   └── fuzzy_controller.py   # 🚫 SAU ranh giới dừng (mục 9)
│
├── hardware/
│   ├── port_scan.py          # ✅ find_likely_arduino_port() — chỉ dò cổng COM, KHÔNG gửi lệnh
│   ├── serial_controller_base.py  # ✅ interface trừu tượng cho Warmup/Main/Cooldown gửi level
│   └── mock_serial_controller.py  # ✅ giả lập, dùng cho SessionManager phát triển ngay bây giờ
│
├── ui/
│   ├── main_window.py        # ✅ MainWindow — điều hướng QStackedWidget
│   ├── mode_select_view.py   # ✅ màn hình đầu tiên
│   ├── ecg_recording_view.py # ✅ mode "ECG real-time" hoàn chỉnh
│   ├── waveform_view.py      # ✅ widget pyqtgraph ECG+HR, dùng chung nhiều màn hình
│   ├── patient_panel.py      # ✅ nhập info + IPAQ
│   ├── hr_rest_view.py       # ✅ đo HR_rest
│   ├── arduino_check_view.py # ✅ kiểm tra kết nối Arduino
│   ├── preflight_checklist_view.py  # ✅ checklist trước khi vào MICT
│   └── session_view.py       # 🚫 SAU ranh giới dừng — màn hình MICT thật
│
└── tests/                    # mỗi module đều có test tương ứng, chạy được KHÔNG cần phần cứng
    ├── smoke_test.py
    ├── test_signals_demo.py
    ├── test_waveform_view.py
    ├── test_full_ecg_flow.py
    ├── test_patient_panel_flow.py
    ├── test_hr_rest_flow.py
    ├── test_checklist_flow.py
    └── test_arduino_check_and_resume.py
```

**⚠️ TRẠNG THÁI GIT HIỆN TẠI**: các file trong bảng trên (ArduinoCheckView, PreflightChecklistView, pending_session_store, mock_serial_controller, port_scan, serial_controller_base) đã được code và test PASS, nhưng **CHƯA `git commit`**. Việc đầu tiên Claude Code nên làm khi mở project: chạy toàn bộ test trong `tests/`, nếu pass hết thì commit checkpoint này trước khi code tiếp.

---

## 4. Trạng thái module

| Module | Trạng thái | Ghi chú |
|---|---|---|
| `core/config.py` | ✅ | Tập trung toàn bộ hằng số |
| `data/patient.py` | ✅ | IPAQ-SF chuẩn (Craig et al. 2003), không phải ngưỡng tự đặt |
| `control/hr_target.py` | ✅ | Karvonen |
| `signals/*` (4 file) | ✅ | Test bằng Demo mode, detect đúng 72 BPM |
| `ui/mode_select_view.py` | ✅ | + nút resume session dang dở |
| `ui/ecg_recording_view.py` + `waveform_view.py` | ✅ | Test end-to-end, ghi CSV đúng |
| `ui/patient_panel.py` | ✅ | HRmax tính ngầm, KHÔNG hiện UI |
| `ui/hr_rest_view.py` | ✅ | Đếm ngược 2 phút, vòng lặp xác nhận |
| `hardware/port_scan.py`, `arduino_check_view.py` | ✅ | Retry thủ công, Quit + lưu pending |
| `data/pending_session_store.py` | ✅ | Resume đúng patient + hr_rest |
| `ui/preflight_checklist_view.py` | ✅ | 4 mục, nút Bắt đầu chỉ bật khi tick hết |
| `hardware/mock_serial_controller.py`, `serial_controller_base.py` | ✅ | Sẵn sàng, CHƯA được dùng (chờ SessionManager) |
| `control/session_manager.py` | ⏳ | **VIỆC TIẾP THEO** |
| `data/session_logger.py` | ⏳ | Chưa viết |
| `data/export_manager.py` | ⏳ | Chưa viết |
| `control/fuzzy_controller.py` | 🚫 | Sau ranh giới dừng |
| `ui/session_view.py` | 🚫 | Sau ranh giới dừng |
| Arduino firmware thật | 🚫 | Chưa có phần cứng để test |

---

## 5. Luồng màn hình chi tiết — mô tả từng nút bấm

### 5.1 `ModeSelectView` (màn hình đầu)
- Nút **"Đo ECG real-time"** → chuyển sang `EcgRecordingView`
- Nút **"Heart Rate Control"** → reset rồi chuyển sang `PatientPanel`
- Nút **"Tiếp tục session dang dở (N)"** → CHỈ hiện khi có file trong `data/pending_sessions/`. Bấm vào: nếu 1 session thì resume thẳng; nếu nhiều thì hiện `QInputDialog` chọn. Resume = load `PatientProfile` từ JSON (đã có `hr_rest`) → nhảy thẳng tới `ArduinoCheckView` (bỏ qua PatientPanel + HrRestView).

### 5.2 `EcgRecordingView` (mode phụ, không cần Arduino)
Có 2 trang nội bộ (`QStackedWidget`):
- **Trang nhập tên**: `QLineEdit` tên đối tượng → nút "Bắt đầu streaming" (nếu tên rỗng thì mặc định "subject") → nút "Quay lại" về menu.
- **Trang streaming**: nhúng `WaveformView` (ECG + HR realtime, tự bắt đầu acquisition). Nút **"⏺ Bắt đầu ghi"** toggle thành **"⏹ Dừng ghi"** — gọi `waveform.start_recording()`/`stop_recording()`, ghi 2 file CSV (`..._data.csv`, `..._peaks.csv`) vào `recordings/`. Khi bấm **Dừng ghi** (hoặc **Kết thúc** trong lúc đang ghi), hiện `QMessageBox` thông báo đã lưu kèm đường dẫn 2 file. Label BPM lớn cập nhật realtime. Label trạng thái `● LIVE`/`● DEMO`/`● ERROR`. Nút **"Kết thúc, quay về menu"** → dừng ghi nếu đang ghi, dừng acquisition, quay `ModeSelectView`.
- **Reset giữa các lần**: `WaveformView.start()` gọi `reset_state()` — tạo lại detector (kể cả warmup 5s), xóa buffer ECG/HR + bộ lọc — nên mỗi lần bắt đầu streaming/đo là hoàn toàn mới, không dùng lại trạng thái cũ.

### 5.3 `PatientPanel` (bước 1 của Heart Rate Control)
3 trang nội bộ:
- **`_BasicInfoPage`**: tên, tuổi (`QSpinBox` 10–100), giới tính (`QComboBox` Nam/Nữ), chiều cao (100–220cm), cân nặng (20–200kg). Nút **"Tiếp tục → Đánh giá IPAQ"**: validate tên không rỗng, sang trang IPAQ. **HRmax được tính ngay lúc này nhưng KHÔNG hiển thị lên UI** (chỉ `print()` debug console — biến `SHOW_DEBUG_INFO` trong file, để `False` ở bản chính thức).
- **`_IpaqPage`**: IPAQ-SF rút gọn, 2 domain (Craig et al. 2003) — KHÔNG hỏi domain đi bộ/ngồi:
  - Số ngày/tuần cường độ MẠNH (≥10 phút liên tục) + phút/ngày trung bình
  - Số ngày/tuần cường độ VỪA + phút/ngày trung bình
  - Nút **"Hoàn tất"** → tạo `PatientProfile`, tính `mvpa_min_per_week` và phân loại.
- **`_ResultPage`**: hiện tên + nhóm phân loại (Active/Sedentary) + số MVPA phút/tuần. Nút **"Tiếp tục → Đo HR_rest"** → phát signal `patient_ready` → `MainWindow` chuyển sang `HrRestView`. Nút **"Quay về menu"**.

**Công thức phân loại** (xem `core/config.py`):
```
MVPA_phút/tuần = (ngày_mạnh × phút_mạnh/ngày) + (ngày_vừa × phút_vừa/ngày)
Active nếu: MVPA_phút/tuần ≥ 150  HOẶC  phút_mạnh/tuần ≥ 75
```
Nguồn: khuyến nghị WHO/ACSM, dichotomization method phổ biến trong nghiên cứu lâm sàng áp dụng IPAQ-SF.

### 5.4 `HrRestView` (bước 2)
- Hiện tên đối tượng, hướng dẫn ("ngồi yên, thư giãn"), thời lượng đo (mặc định `config.HR_REST_DURATION_SEC = 120`).
- Nút **"Bắt đầu đo HR_rest"** → ẩn nút, hiện đồng hồ đếm ngược `mm:ss`, nhúng `WaveformView` chạy realtime để người vận hành nhìn thấy chất lượng tín hiệu trong lúc đo.
- Hết giờ: tự động tính `HR_rest` = median của **nửa sau** thời gian đo (bỏ đoạn đầu chưa ổn định) → popup `QMessageBox.question`: "HR_rest đo được: X bpm. Chấp nhận?"
  - **Không** → reset, quay lại nút "Bắt đầu đo" (đo lại từ đầu)
  - **Có** → `patient.apply_hr_rest()` (tính HRR, cross-check với nhãn IPAQ) → phát `hr_rest_confirmed` → `MainWindow` chuyển sang `ArduinoCheckView`
- Nút **"Hủy, quay về menu"** luôn có sẵn.

### 5.5 `ArduinoCheckView` (bước 3)
- Tự động gọi `find_likely_arduino_port()` (dò VID quen thuộc: Arduino chính hãng 0x2341, CH340 0x1A86, CP2102 0x10C4, FTDI 0x0403) ngay khi `set_patient()`.
- **Chưa tìm thấy**: label đỏ hướng dẫn kiểm tra dây/nguồn, nút **"Kiểm tra lại"** hiện (chỉ dò lại danh sách cổng COM tại thời điểm bấm, KHÔNG polling nền — người dùng phải thực sự cắm dây trước khi bấm lại mới qua được).
- **Đã tìm thấy**: label xanh, nút **"Tiếp tục →"** hiện (nút Retry ẩn) → phát `connected` → sang `PreflightChecklistView`.
- Nút **"Quit (thoát, lưu tạm nếu cần)"**: hỏi popup có lưu session dang dở không (Yes → `save_pending()` ghi JSON) → về menu.

### 5.6 `PreflightChecklistView` (bước 4 — điểm dừng hiện tại của nhánh Heart Rate Control)
4 checkbox: điện cực đúng vị trí, BIOPAC MP36 kết nối, Arduino cấp nguồn, đối tượng ngồi đúng tư thế. Nút **"Bắt đầu chương trình MICT"** CHỈ bật khi tick hết 4 ô. Bấm vào → phát `ready_to_start` → hiện tại (`MainWindow._on_ready_to_start`) chỉ show `QMessageBox` tạm thông báo "sẽ nối SessionView khi tới mốc Fuzzy/hardware" rồi quay menu — **đây là placeholder, sẽ thay bằng chuyển thật sang `SessionView` khi module đó được viết.**

---

## 6. Data model & công thức quan trọng

### `PatientProfile` (data/patient.py)
Trường nhập: `name, age, sex, height_cm, weight_kg, vigorous_days_per_week, vigorous_min_per_day, moderate_days_per_week, moderate_min_per_day`

Tự tính (`__post_init__`): `hr_max` (Tanaka: `208 − 0.7×age`), `mvpa_min_per_week`, `ipaq_activity_level`.

Điền sau khi đo HR_rest (`apply_hr_rest()`): `hr_rest, hr_rest_activity_level` (cross-check, ngưỡng `HR_REST_ACTIVE_THRESHOLD_BPM=70`), `is_classification_consistent`.

`to_raw_dict()`/`from_raw_dict()`: khôi phục nguyên object cho tính năng resume — KHÁC với `to_dict()` (dùng xuất CSV phân tích, có thêm `hr_max`, `final_group`...).

### ⚠️ QUY ƯỚC ĐẶT TÊN QUAN TRỌNG — không được nhầm lẫn

| Ký hiệu | Ý nghĩa | Dùng ở đâu |
|---|---|---|
| `HRR` | Heart Rate **Reserve** = HRmax − HRrest | `hr_target.py`, Karvonen |
| `HR_recovery` / `HRR1` | Heart Rate **Recovery** tại phút 1 sau gắng sức | Cool-down, phân tích sau buổi tập — **CHƯA implement, sẽ cần khi viết SessionManager** |

Đây là 2 đại lượng khác nhau, dễ gây nhầm lẫn học thuật nếu code dùng chung 1 tên.

---

## 7. Thiết kế `SessionManager` (module tiếp theo, CHƯA VIẾT)

State machine theo **thời gian tuyệt đối** (bắt buộc dùng `time.monotonic()`, KHÔNG đếm số vòng lặp — vì Fuzzy update mỗi 5-8s sẽ tích lũy sai số nếu đếm tick):

| Pha | Khung giờ | Kháng lực | Vì sao |
|---|---|---|---|
| Warm-up | 0:00–5:00 | **Cố định** theo nhóm IPAQ (`WARMUP_LEVEL_SEDENTARY=2`, `WARMUP_LEVEL_ACTIVE=4`) | Fuzzy không phù hợp giai đoạn transient (error quá lớn, chưa ổn định) |
| Main | 5:00–25:00 | **Fuzzy Loop**, update mỗi 5–8s | Đúng bài toán Fuzzy được thiết kế |
| Cool-down | 25:00–30:00 | **Ramp tuyến tính giảm dần** | Tránh confound phép đo HR_recovery — KHÔNG dùng Fuzzy vì mục đích là quan sát tự nhiên, không phải giữ vùng |

2 mốc bắt buộc ghi log để tính HRR1 sau này:
- `HR_end_main` tại t=25:00
- `HR_at_1min_post` tại t=26:00 (`HRR1_MARK_OFFSET_SEC=60` trong config)
- `HRR1 = HR_end_main − HR_at_1min_post`

`SessionManager` giao tiếp với `hardware/mock_serial_controller.py` (interface `serial_controller_base.py`) — CHƯA cần Arduino thật để phát triển/test module này.

---

## 8. Nguyên tắc coding đã thống nhất

1. **`core/config.py` là single source of truth** cho mọi ngưỡng/hằng số — không hard-code số trong file khác.
2. **Mock hardware pattern**: `hardware/serial_controller_base.py` (interface) + `mock_serial_controller.py` (giả lập) + `real_serial_controller.py` (sau này, chưa viết) — để Control layer phát triển độc lập với tiến độ firmware Arduino.
3. **Testing**: dùng **polling** (QTimer lặp, kiểm tra điều kiện mỗi ~150ms) thay vì tính thời điểm cố định (`QTimer.singleShot` với delay đoán trước) — bài học rút ra từ lỗi thực tế: UI thật trên Windows có độ trễ khác với môi trường test, timing cố định gây race condition ngẫu nhiên.
4. **Package `signals/` có "s"**: tránh trùng module chuẩn `signal` của Python (dùng bởi `multiprocessing`).
5. **PowerShell**: không dùng `&&` để nối lệnh (gây `ParserError`) — mỗi lệnh 1 dòng riêng, hoặc dùng `;`.
6. **Bảo vệ dữ liệu đối tượng thí nghiệm**: `.gitignore` loại trừ `recordings/`, `data/sessions/`, `data/pending_sessions/`, `data/patient_lookup.*`. Khi xuất CSV phân tích chính thức, không ghi tên thật, chỉ dùng `patient_id` (UUID).
7. **Git workflow**: sau mỗi module hoàn chỉnh + test pass → `git add .` + `git commit`. Không cần dọn lịch sử — nhiều commit nhỏ là bình thường. Khi có bản nộp bảo vệ chính thức, dùng `git tag` để đánh dấu, không cần làm ngay bây giờ.
8. **Không tạo file/folder rỗng trước khi thật sự cần.**

---

## 9. Ranh giới dừng hiện tại

Mọi thứ **TRƯỚC** mốc này đã/đang làm được mà KHÔNG cần Arduino/BIOPAC thật (Demo mode + Mock hardware):
- Toàn bộ luồng UI (mục 5)
- `SessionManager` (Warmup cố định + Cooldown ramp dùng Mock; Main dùng Fuzzy cũng test được với Mock)
- `session_logger.py`, `export_manager.py`

**SAU** mốc này cần phần cứng thật, đang chờ:
- `control/fuzzy_controller.py` chạy với phản hồi HR thật từ đối tượng thật
- `hardware/real_serial_controller.py` — giao tiếp UART thật với Arduino Uno R3 đã thay thế board GENUS-249 gốc
- Firmware Arduino (4 phase: PlatformIO setup → standalone mode → serial protocol → tích hợp) — hiện CHƯA làm
- Calibrate STEPS_PER_LEVEL bằng feeler gauge
- `mpdev.dll` hiện load lỗi ("could not find dependency") — cần copy toàn bộ file `.dll` khác cùng chỗ với `HRC.py` cũ sang, chưa xử lý (không chặn tiến độ vì Demo mode tự động fallback).

---

## 10. Việc tiếp theo (thứ tự ưu tiên)

1. **Chạy toàn bộ `tests/*.py`, xác nhận PASS hết, rồi `git commit` checkpoint update7** (ArduinoCheckView, PreflightChecklistView, resume session) — CHƯA COMMIT, làm trước tiên.
2. `control/session_manager.py` — state machine 3 pha (mục 7), dùng `MockSerialController`.
3. `data/session_logger.py` — ghi log liên tục dạng "tăng/giảm level tại phút...", lưu CSV tách 2 nhóm sedentary/active.
4. `data/export_manager.py` — xuất báo cáo sau buổi tập.
5. Nối `SessionManager` vào `ui/session_view.py` (màn hình MICT thật) — thay placeholder `QMessageBox` hiện tại ở `PreflightChecklistView.ready_to_start`.
6. Song song (không phụ thuộc phần mềm): bắt đầu firmware Arduino thật.

---

## 11. Lưu ý khi Claude Code bắt đầu phiên làm việc

- Đọc file này + `CLAUDE.md` trước khi code.
- Kiểm tra `git status` — nếu có thay đổi chưa commit từ trước, hỏi người dùng trước khi tiếp tục.
- Người dùng KHÔNG có nền tảng IT — giải thích ngắn gọn, từng bước, tránh thuật ngữ không cần thiết khi tương tác.
- Terminal là PowerShell trên Windows — không dùng `&&`.
