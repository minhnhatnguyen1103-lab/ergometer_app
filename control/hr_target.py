"""
control/hr_target.py
---------------------
Tính HRR và target zone (Karvonen) SAU khi đã có HR_rest thực đo.

Layer boundary:
    - patient.py  : tính HRmax (Tanaka) + phân loại IPAQ ngay khi nhập liệu
    - hr_target.py: tính HRR + THR_low/high, CHỈ chạy được sau khi
                    PatientProfile.apply_hr_rest() đã được gọi.

Đây là bước "tính 1 lần trước session" (không phải runtime loop).
Runtime loop (Fuzzy controller) chỉ so sánh HR_actual vs [THR_low, THR_high].
"""

from dataclasses import dataclass
from data.patient import PatientProfile


class HRRestNotMeasuredError(Exception):
    """PatientProfile chưa gọi apply_hr_rest() trước khi tính target zone."""


@dataclass
class HRTargetZone:
    hr_rest: float
    hr_max: float
    hrr: float
    thr_low: float   # 60% HRR
    thr_high: float  # 80% HRR

    def contains(self, hr_actual: float) -> bool:
        """Dùng ở runtime loop để check HR có trong vùng mục tiêu không."""
        return self.thr_low <= hr_actual <= self.thr_high

    def to_dict(self) -> dict:
        return {
            "hr_rest": self.hr_rest,
            "hr_max": self.hr_max,
            "hrr": self.hrr,
            "thr_low": round(self.thr_low, 1),
            "thr_high": round(self.thr_high, 1),
        }


def compute_karvonen_zone(
    patient: PatientProfile,
    low_pct: float = 0.60,
    high_pct: float = 0.80,
) -> HRTargetZone:
    """
    THR = HR_rest + %HRR * (HR_max - HR_rest)

    MICT chuẩn của đồ án: low_pct=0.60, high_pct=0.80 (60-80% HRR).
    Tham số để mở, phòng khi hội đồng hỏi "nếu đổi cường độ thì sao".
    """
    if patient.hr_rest is None:
        raise HRRestNotMeasuredError(
            f"Patient {patient.patient_id} chưa đo HR_rest. "
            "Gọi PatientProfile.apply_hr_rest(hr_rest) trước."
        )

    hrr = patient.hr_max - patient.hr_rest
    thr_low = patient.hr_rest + low_pct * hrr
    thr_high = patient.hr_rest + high_pct * hrr

    return HRTargetZone(
        hr_rest=patient.hr_rest,
        hr_max=patient.hr_max,
        hrr=hrr,
        thr_low=thr_low,
        thr_high=thr_high,
    )
