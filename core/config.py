"""
core/config.py
----------------
TẤT CẢ con số có thể thay đổi (ngưỡng, thời gian, hệ số) đều nằm ở đây.
Không hard-code số trực tiếp trong các file khác — luôn import từ config.py.

Lý do: khi bảo vệ đồ án, nếu hội đồng hỏi "tại sao chọn 60-80%" hay
"tại sao 3 ngày/tuần", bạn chỉ cần trỏ vào 1 file duy nhất, không phải
tìm khắp project.
"""

# --- Công thức Karvonen (% Heart Rate Reserve) ---
KARVONEN_LOW_PCT = 0.60   # 60% HRR
KARVONEN_HIGH_PCT = 0.80  # 80% HRR

# --- Phân loại IPAQ-SF (Craig et al. 2003) rút gọn: chỉ domain vigorous + moderate ---
# Nguồn: WHO/ACSM physical activity guideline - dung trong nhieu nghien cuu lam sang
# ap dung IPAQ-SF (vd. dichotomization method cho MVPA-minutes/week)
MVPA_ACTIVE_THRESHOLD_MIN_PER_WEEK = 150   # >=150 phut/tuan (vua+manh cong lai) => Active
VIGOROUS_ACTIVE_THRESHOLD_MIN_PER_WEEK = 75  # hoac >=75 phut/tuan rieng cuong do manh => Active
HR_REST_ACTIVE_THRESHOLD_BPM = 70     # HR_rest <=70 => goi y Active (cross-check)

# --- Do HR_rest (baseline truoc khi vao Warmup) ---
HR_REST_DURATION_SEC = 120   # 2 phut - co the chinh neu can
WARMUP_DURATION_SEC = 5 * 60
MAIN_DURATION_SEC = 20 * 60
COOLDOWN_DURATION_SEC = 5 * 60
HRR1_MARK_OFFSET_SEC = 60   # đo HR_recovery tại đúng 1 phút sau khi kết thúc Main

# --- Warm-up: level cố định theo nhóm (KHÔNG dùng Fuzzy ở pha này) ---
WARMUP_LEVEL_SEDENTARY = 2
WARMUP_LEVEL_ACTIVE = 4

# --- Fuzzy controller (dùng khi viết fuzzy_controller.py sau này) ---
FUZZY_UPDATE_INTERVAL_SEC_MIN = 5
FUZZY_UPDATE_INTERVAL_SEC_MAX = 8
HR_DEADBAND_BPM = 3

# --- Giới hạn số level của ergometer GENUS-249 ---
LEVEL_MIN = 1
LEVEL_MAX = 16
LEVEL_EXPECTED_MIN = 5     # dai ky vong khi Fuzzy dang chay dung (chi canh bao, khong chan)
LEVEL_EXPECTED_MAX = 10

# --- MockSerialController: mo phong thoi gian motor di chuyen giua 2 level ---
# (tham chieu boi hardware/mock_serial_controller.py - truoc day thieu hang so
# nay trong config.py, se crash ngay khi khoi tao MockSerialController() khong
# truyen level_change_delay_sec tuong minh)
MOCK_LEVEL_CHANGE_DELAY_SEC = 1.5

# --- SessionManager: nhac truong vong dieu khien (control/session_manager.py) ---
SESSION_TICK_MS = 250                  # chu ky vong lap chinh, khong phu thuoc time_scale
HR_SMOOTHING_WINDOW_SEC = 6            # cua so lam muot HR truoc khi dua vao Fuzzy (5-8s theo dac ta)
HR_STALE_SHORT_TIMEOUT_SEC = 8         # mat HR ngan: giu nguyen level, chi canh bao
HR_STALE_LONG_TIMEOUT_SEC = 20         # mat HR keo dai: chu dong SET 1 (an toan)
CADENCE_MIN_RPM = 60
CADENCE_MAX_RPM = 70
