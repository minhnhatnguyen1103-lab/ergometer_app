"""
signals/constants.py
----------------------
Hằng số kỹ thuật của tầng thu tín hiệu (khác với core/config.py — nơi
chứa ngưỡng lâm sàng/nghiệp vụ). Các giá trị ở đây gắn chặt với phần cứng
BIOPAC MP36 và thuật toán Pan-Tompkins, không phải thứ hội đồng sẽ hỏi
"tại sao chọn số này" theo kiểu lâm sàng.

Trích nguyên từ HRC.py — KHÔNG đổi giá trị.
"""

import os

FS = 1000              # Hz — tần số lấy mẫu
WIN_SEC = 8             # giây hiển thị trên waveform
BUF = FS * WIN_SEC       # số sample trong buffer hiển thị
CHUNK = 100              # số sample mỗi lần gọi receiveMPData

# BHAPI — mã thiết bị (từ rtpeaks mpdev.py)
MP_TYPE = 103            # MP36
MP_COMM = 11             # USB auto
MP_SN = b'auto'
MPOK = {1, 11}

# MP36 ECG gain x1000 → output đơn vị mV trực tiếp
MP36_GAIN = 1000.0

# Giới hạn hợp lệ khi tính BPM (theo chuẩn BSL)
BPM_MIN, BPM_MAX = 40.0, 180.0

# Lead II chuẩn (VIN+ LL − VIN− RA) → R-wave luôn dương với dây SS2LB đúng chuẩn
ECG_POLARITY_AUTO = False
ECG_POLARITY_FIXED = +1

LOG_DIR = os.path.join(os.getcwd(), "recordings")
