# Bộ điều khiển Fuzzy Logic (Mamdani) — Tổng hợp trình bày

> Tài liệu tổng hợp toàn bộ phần Fuzzy Logic của đồ án, viết lại dễ hiểu để
> trình bày/bảo vệ. Nội dung tổng hợp từ `docsclaude/IMPLEMENTATION_PLAN.md`
> (mục 3.1 — đặc tả kỹ thuật), `docsclaude/GIAI_THICH_DE_HIEU.md` (mục 4 — giải
> thích khái niệm), và code thật đã cài đặt tại `control/fuzzy_controller.py`
> (đã test PASS, xem `tests/test_fuzzy_controller.py`).

---

## 1. Tóm tắt trong một câu

Cứ mỗi 5–8 giây trong pha tập chính, bộ Fuzzy nhìn vào **nhịp tim hiện tại lệch
mục tiêu bao nhiêu** và **đang tăng hay giảm**, rồi quyết định **tăng/giảm độ
nặng bàn đạp bao nhiêu nấc** (tối đa ±2 trong 16 nấc) để kéo nhịp tim về đúng
vùng luyện tập.

---

## 2. Vị trí trong vòng điều khiển kín

```
BIOPAC MP36 (ECG 1000Hz) → Pan-Tompkins → HR thực tế
        → so với vùng mục tiêu (Karvonen 60–80% HRR)
        → FUZZY LOGIC → mức tải mới (1–16)
        → Serial → Arduino → motor phanh GENUS-249
        → HR thay đổi → đo lại → lặp
```

Fuzzy **chỉ hoạt động trong pha Chính (Main, phút 5–25)** của buổi tập 30 phút:

| Pha | Thời gian | Cách điều khiển |
|---|---|---|
| Khởi động (Warmup) | 0–5 phút | Mức tải **cố định** theo nhóm IPAQ (Sedentary/Active) — Fuzzy CHƯA chạy |
| **Chính (Main)** | **5–25 phút** | **Fuzzy Logic, tính lại mỗi 5–8 giây** |
| Hạ nhiệt (Cooldown) | 25–30 phút | Giảm tuyến tính về Level 1 — Fuzzy TẮT, để đo nhịp tim hồi phục (HRR1) sạch |

Lý do Fuzzy không chạy ở Warmup/Cooldown: Warmup thì nhịp tim còn "loạng
choạng" chưa ổn định để điều khiển tinh vi; Cooldown cần đo hồi phục tự nhiên,
Fuzzy can thiệp vào sẽ làm nhiễu phép đo.

Code triển khai vòng lặp này: `control/session_manager.py` (không phải file
Fuzzy) — file đó gọi `FuzzyController.compute()` mỗi khi tới chu kỳ cập nhật.

---

## 3. Fuzzy Logic là gì? (giải thích không cần biết lập trình)

Máy tính bình thường suy nghĩ kiểu **đen/trắng**: nhịp tim hoặc "cao" hoặc
"thấp". Con người suy nghĩ kiểu **mờ**: "hơi cao một chút", "thấp kha khá",
"gần đạt rồi". Fuzzy Logic cho máy suy nghĩ theo kiểu con người bằng các luật
dạng câu chữ, ví dụ:

- *"Nếu nhịp tim thấp hơn nhiều so với mục tiêu VÀ đang không tăng → tăng độ
  nặng nhiều."*
- *"Nếu nhịp tim đã đúng vùng → giữ nguyên."*
- *"Nếu nhịp tim cao hơn VÀ đang tăng tiếp → giảm độ nặng nhiều."*

Hệ thống dùng **15 luật** như vậy, dựa trên 2 điều quan sát:

1. **Nhịp tim đang lệch bao nhiêu** so với mục tiêu (ký hiệu `e`).
2. **Nhịp tim đang đi theo hướng nào** — tăng, giảm, hay ổn định (ký hiệu `de`)
   — để **đón đầu**, tránh chỉnh quá tay rồi phải sửa lại (giống người lái xe
   giỏi nhả ga sớm khi thấy xe trước đang chậm lại, không đợi tới sát đuôi).

### Vì sao Fuzzy mà không dùng công thức PID kinh điển?

PID cần 3 thứ mà cơ thể người không có: (1) một công thức cố định
"độ nặng → nhịp tim" — nhưng mỗi người phản ứng khác nhau, cùng một người lúc
khỏe lúc mệt cũng khác; (2) bộ tham số tối ưu dùng chung cho mọi người — không
tồn tại; (3) đầu ra liên tục — nhưng tải ở đây chỉ có 16 nấc rời rạc. Fuzzy
điều khiển bằng **kinh nghiệm dạng luật** (giống huấn luyện viên chỉnh tải
bằng cảm nhận), không cần công thức chính xác — hợp lý hơn cho bài toán sinh
lý học có tính cá thể hoá cao này.

---

## 4. Thiết kế chi tiết (khớp code thật trong `control/fuzzy_controller.py`)

### 4.1 Hai đầu vào — cấu trúc "PD mờ"

| Ký hiệu | Công thức | Ý nghĩa |
|---|---|---|
| `e` (sai số) | `HR_target_center − HR_actual` (bpm) | `e > 0`: HR thấp hơn mục tiêu → cần tăng level. `e < 0`: HR cao hơn → cần giảm |
| `de` (tốc độ đổi) | `(HR_now − HR_prev) / dt` (bpm/giây) | HR đang tăng hay giảm — dùng đón đầu, tránh vọt lố (overshoot) |

- `HR_target_center` = trung điểm vùng mục tiêu Karvonen = 70% HRR (chính giữa
  60–80%), tính từ `(thr_low + thr_high) / 2`.
- `HR_actual` đưa vào Fuzzy là **HR đã làm mượt** (median trên cửa sổ 6 giây,
  `control/session_manager.py`), không phải giá trị tức thời từng nhịp — để
  loại nhiễu/outlier của Pan-Tompkins.

### 4.2 Tập mờ đầu vào `e` — 5 tập, vũ trụ [−30, +30] bpm

| Tập | Ý nghĩa | Dạng | Đỉnh/vùng bão hoà |
|---|---|---|---|
| `NB` | HR cao hơn mục tiêu **nhiều** | Hình thang (vai bão hoà) | ≤ −18 |
| `NS` | HR cao hơn **một chút** | Tam giác | đỉnh −8 |
| `ZE` | **Trong vùng mục tiêu** | Tam giác | đỉnh 0, chân ±6 |
| `PS` | HR thấp hơn **một chút** | Tam giác | đỉnh +8 |
| `PB` | HR thấp hơn mục tiêu **nhiều** | Hình thang (vai bão hoà) | ≥ +18 |

(`ZE` có chân ±6 = gấp đôi ngưỡng vùng chết cứng `HR_DEADBAND_BPM = 3` — chọn
vậy để tập mờ và chốt an toàn nhất quán với nhau.)

### 4.3 Tập mờ đầu vào `de` — 3 tập, vũ trụ [−10, +10] bpm/giây

| Tập | Ý nghĩa | Đỉnh/vùng bão hoà |
|---|---|---|
| `FALL` | HR đang giảm | ≤ −4 |
| `STEADY` | HR ổn định | đỉnh 0 |
| `RISE` | HR đang tăng | ≥ +4 |

### 4.4 Tập mờ đầu ra `Δlevel` — 5 tập, vũ trụ [−2.5, +2.5]

`NB = −2`, `NS = −1`, `ZE = 0`, `PS = +1`, `PB = +2` — tức là **mỗi lần Fuzzy
cập nhật chỉ được đổi tối đa ±2 nấc** (rate-limiting tự nhiên, tránh giật cục).

### 4.5 Bảng 15 luật (5 hàng `e` × 3 cột `de`)

| `e` \ `de` | RISE (đang tăng) | STEADY (ổn định) | FALL (đang giảm) |
|---|:---:|:---:|:---:|
| **NB** (HR ≫ mục tiêu) | NB | NB | NS |
| **NS** | NS | NS | ZE |
| **ZE** (đã đúng vùng) | NS | ZE | PS |
| **PS** | ZE | PS | PS |
| **PB** (HR ≪ mục tiêu) | PS | PB | PB |

**Đọc bảng theo trực giác:**
- Đường chéo chính là "phản ứng thuận" — HR cao thì giảm, HR thấp thì tăng.
- Cột `RISE`/`FALL` **dịch đầu ra lệch đi một bậc** so với cột `STEADY` để đón
  đầu xu hướng: ví dụ hàng `PB` (HR thấp nhiều) — nếu HR **đang tự tăng lên rồi**
  (`RISE`) thì chỉ cần tăng nhẹ (`PS`) thay vì tăng mạnh (`PB`), vì xu hướng tự
  nhiên đã đang đi đúng hướng.
- Hàng `ZE` (đã trong vùng) vẫn có phản ứng nhẹ ở cột `RISE`/`FALL` (`NS`/`PS`)
  để **chống trôi ra khỏi vùng** khi HR đang di chuyển, không đợi ra khỏi vùng
  mới phản ứng.

### 4.6 Quy trình suy luận (Mamdani chuẩn)

1. **Fuzzy hoá**: tính độ thuộc (membership) của `e` vào cả 5 tập, của `de`
   vào cả 3 tập.
2. **Hợp thành từng luật = MIN** (phép AND mờ): độ mạnh mỗi luật =
   `min(độ_thuộc_e, độ_thuộc_de)`.
3. **Hợp luật = MAX**: nếu nhiều luật cùng trỏ về một nhãn đầu ra (ví dụ cả
   `(NS,RISE)` và `(NS,STEADY)` đều ra `NS`), độ mạnh của nhãn đó lấy giá trị
   lớn nhất trong các luật.
4. **Giải mờ = Centroid (trọng tâm)**: cắt các tập mờ đầu ra theo độ mạnh đã
   hợp, chồng lên nhau, rồi tính trọng tâm diện tích trên vũ trụ liên tục — ra
   một số thực (`crisp_output`).
5. **Làm tròn** về số nguyên gần nhất trong {−2, −1, 0, +1, +2}.

### 4.7 Ba chốt an toàn sau khi tính Fuzzy (bắt buộc theo đặc tả)

| # | Chốt | Điều kiện | Hành động |
|---|---|---|---|
| 1 | **Vùng chết cứng** | `\|e\| ≤ 3 bpm` (HR_DEADBAND_BPM) **và** `\|de\| ≤ 2` | Ép `Δlevel = 0` — chống rung quanh mục tiêu, không phụ thuộc kết quả giải mờ |
| 2 | **Hard clamp** | luôn luôn | `new_level = clamp(current_level + Δlevel, 1, 16)` — không bao giờ ra ngoài 16 nấc |
| 3 | **Cảnh báo out-of-range** | `new_level` ngoài [5, 10] | Chỉ ghi log/cảnh báo (soft warn), **không chặn** — vì tải quá nhẹ/nặng có thể vẫn hợp lý với người đó |

> Lưu ý minh bạch: ngưỡng `|de| ≤ 2` ở chốt #1 là giá trị **tự suy ra** (bằng
> nửa bề rộng tập `STEADY`) vì đặc tả gốc chỉ nói "|de| nhỏ" mà không cho số cụ
> thể — cần nêu rõ điều này nếu hội đồng hỏi.

---

## 5. Vì sao tự viết Mamdani thay vì dùng thư viện có sẵn?

| Tiêu chí | Tự viết (numpy) | scikit-fuzzy | simpful |
|---|:---:|:---:|:---:|
| Minh bạch / audit từng bước | Cao nhất | Trung bình | Cao |
| Rủi ro khi đóng gói `.exe` | Thấp nhất (0 dependency ngoài numpy) | Cao (kéo theo `networkx`) | Thấp |
| Đã qua bình duyệt khoa học | Không | Có | Có (IJCIS 2020) |
| Phù hợp quy mô 2 input / 15 luật | Vừa khít | Quá cỡ | Vừa |

**Lý do chọn tự viết** (ưu tiên cao nhất là **an toàn vận hành**, vì đây là bộ
điều khiển chạy trên tải vật lý gắn với nhịp tim người thật):

1. Ít điểm hỏng nhất khi đóng gói `.exe` — tránh rủi ro thiếu linh kiện
   (hidden-import) trên máy lạ.
2. Chốt an toàn (vùng chết, clamp) nằm ngay trong cùng hàm `compute()`, không
   phải ghép thêm lên output của thư viện ngoài.
3. Test được **toàn bộ 15 ô** một cách tường minh — dễ chứng minh "đầu ra
   đúng như thiết kế" với hội đồng.
4. Bài toán chỉ có 15 luật — quá nhỏ để một framework tổng quát mang lại lợi
   ích thật.

**Mẹo kiểm chứng chéo** (không dùng trong production): dựng lại đúng bộ luật
này một lần bằng thư viện `simpful` (nhẹ, đã công bố khoa học), so kết quả với
bản tự viết trên cùng tập `(e, de)`. Nếu khớp → dùng làm bằng chứng "đã kiểm
chứng chéo với thư viện đã qua bình duyệt" trong báo cáo mà không phải gánh
dependency lúc chạy thật. *(Bước này chưa thực hiện trong code hiện tại —
mang tính khuyến nghị khi viết báo cáo.)*

---

## 6. Interface & cách gọi trong hệ thống

```python
# control/fuzzy_controller.py
class FuzzyController:
    def compute(self, hr_actual: float, hr_target_center: float,
                hr_prev: float, dt: float, current_level: int) -> FuzzyResult: ...

@dataclass
class FuzzyResult:
    delta_level: int        # {-2..+2}, đã qua deadband + làm tròn
    new_level: int           # 1..16, đã hard clamp
    error: float              # e
    error_rate: float         # de
    crisp_output: float       # giá trị centroid THÔ trước deadband/làm tròn (để báo cáo)
    out_of_range: bool        # new_level ngoài [5,10]?
```

`control/session_manager.py` là nơi **gọi** `FuzzyController.compute()` — mỗi
chu kỳ 5–8 giây trong pha Main, luôn truyền `current_level` **đọc trực tiếp từ
telemetry phần cứng** (không dùng giá trị phần mềm tự nhớ), vì nút bấm vật lý
trên Arduino luôn có thể thay đổi level bất cứ lúc nào song song với phần mềm
(xem `docsclaude/PROJECT_CONTEXT.md` phần nguyên tắc hội tụ `applyLevel()`).

---

## 7. Đã kiểm thử gì? (`tests/test_fuzzy_controller.py`, PASS)

1. **Cả 15 ô bảng luật** — dựng `(e, de)` đúng tại điểm đỉnh/vùng bão hoà của
   từng tập để đảm bảo mỗi ô chỉ kích hoạt đúng 1 cặp tập mờ, kiểm `delta_level`
   khớp nhãn kỳ vọng.
2. **Vùng chết cứng** — `e=1, de=0.5` → `delta_level` phải ép về 0.
3. **Hard clamp biên** — `current_level=16` với `delta=+2` phải giữ nguyên 16;
   `current_level=1` với `delta=-2` phải giữ nguyên 1.
4. **Cảnh báo out-of-range** — `new_level=3` (ngoài [5,10]) phải bật cờ;
   `new_level=7` (trong khoảng) thì không.

Chạy: `python tests/test_fuzzy_controller.py` → `OK - FuzzyController hoat
dong dung thiet ke (15 luat + deadband + clamp + warning)`.

---

## 8. Giới hạn cần biết khi trình bày

- Bộ điều khiển chỉ được kiểm chứng **với dữ liệu HR giả lập (Mock/Demo)**,
  chưa có phản hồi HR thật từ đối tượng thật qua Arduino thật — đây là ranh
  giới đồ án hiện tại (xem `docsclaude/PROJECT_CONTEXT.md` mục "Ranh giới
  dừng").
- Ngưỡng `DEADBAND_DE_THRESHOLD = 2.0` là giá trị tự suy ra, chưa có căn cứ
  thực nghiệm — nên nói rõ đây là lựa chọn thiết kế hợp lý chứ không phải số
  đo được.
- Hệ thống chứng minh được **duy trì HR trong vùng mục tiêu trong một buổi
  tập**, không chứng minh cải thiện sức khỏe tim mạch dài hạn (cần nhiều tuần,
  nhiều đối tượng — ngoài phạm vi đồ án).
