"""
tests/smoke_test.py
---------------------
File kiểm tra nhanh (không phải app thật): xác nhận config + patient +
hr_target hoạt động đúng với nhau. Giữ lại để chạy bất cứ khi nào nghi
ngờ 3 module này bị lỗi sau khi sửa code.

Chạy: python tests/smoke_test.py
Kỳ vọng: thấy dòng "OK - cau truc project da dung" ở cuối, không có lỗi đỏ.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.patient import PatientProfile, Sex
from control.hr_target import compute_karvonen_zone
from core import config


def main():
    print("=== Kiem tra cau truc project ===\n")

    print(f"Target zone Karvonen: {config.KARVONEN_LOW_PCT*100:.0f}-{config.KARVONEN_HIGH_PCT*100:.0f}% HRR")
    print(f"Timeline: Warmup {config.WARMUP_DURATION_SEC//60} phut | "
          f"Main {config.MAIN_DURATION_SEC//60} phut | "
          f"Cooldown {config.COOLDOWN_DURATION_SEC//60} phut\n")

    # Tạo 1 patient demo để test luồng tính toán
    patient = PatientProfile(
        name="Demo",
        age=22,
        sex=Sex.MALE,
        height_cm=170,
        weight_kg=65,
        moderate_vigorous_days_per_week=4,
    )
    print(f"Patient demo: HRmax = {patient.hr_max} bpm | nhom IPAQ = {patient.ipaq_activity_level.value}")

    # Giả lập đã đo HR_rest xong
    patient.apply_hr_rest(72)
    zone = compute_karvonen_zone(patient)
    print(f"Sau khi do HR_rest = 72 bpm:")
    print(f"  HRR = {zone.hrr}")
    print(f"  Target zone = [{zone.thr_low:.1f}, {zone.thr_high:.1f}] bpm")
    print(f"  Nhat quan voi phan loai IPAQ? {patient.is_classification_consistent}")

    print("\nOK - cau truc project da dung")


if __name__ == "__main__":
    main()
