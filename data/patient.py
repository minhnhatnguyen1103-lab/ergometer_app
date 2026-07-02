"""
data/patient.py
----------------
PatientProfile: hồ sơ đối tượng nhập từ PatientPanel (UI layer).
Chứa thông tin tĩnh (demographic) + phân loại IPAQ/ACSM rút gọn.

Không chứa logic Karvonen (HRR, target zone) — việc đó thuộc về
control/hr_target.py vì phụ thuộc HR_rest đo thực nghiệm, không có
sẵn tại thời điểm nhập liệu ban đầu.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"       # ít vận động
    ACTIVE = "active"             # vận động nhiều


@dataclass
class PatientProfile:
    # --- nhập tay từ PatientPanel ---
    name: str
    age: int
    sex: Sex
    height_cm: float
    weight_kg: float

    # --- input cho IPAQ/ACSM rút gọn ---
    # số ngày/tuần tập cường độ vừa-mạnh, mỗi lần >= 30 phút
    moderate_vigorous_days_per_week: int = 0

    # --- id & timestamp, tự sinh ---
    patient_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    # --- tính toán ngay khi nhập xong (không cần HR_rest) ---
    hr_max: float = field(init=False)
    ipaq_activity_level: ActivityLevel = field(init=False)

    # --- các trường này CHƯA có tại thời điểm nhập liệu,
    #     được điền sau bước đo HR_rest (xem control/hr_target.py) ---
    hr_rest: float | None = None
    hr_rest_activity_level: ActivityLevel | None = None
    is_classification_consistent: bool | None = None

    def __post_init__(self):
        self.hr_max = self._compute_hr_max()
        self.ipaq_activity_level = self._classify_ipaq()

    # ---------- công thức ----------

    def _compute_hr_max(self) -> float:
        """Tanaka formula: HRmax = 208 - 0.7 * age"""
        return round(208 - 0.7 * self.age, 1)

    def _classify_ipaq(self) -> ActivityLevel:
        """
        ACSM rút gọn: >=3 ngày/tuần hoạt động vừa-mạnh (>=30 phút/lần)
        => Active. Ngược lại => Sedentary.
        Ngưỡng có thể chỉnh trong file config nếu hội đồng yêu cầu
        thang đo chi tiết hơn (MET-minutes/week theo IPAQ đầy đủ).
        """
        if self.moderate_vigorous_days_per_week >= 3:
            return ActivityLevel.ACTIVE
        return ActivityLevel.SEDENTARY

    # ---------- gọi sau khi đo HR_rest xong ----------

    def apply_hr_rest(self, hr_rest: float) -> None:
        """
        Điền HR_rest đo được, tính nhãn cross-check, và cờ nhất quán.
        Gọi hàm này ngay sau bước đo baseline (trước warm-up).
        """
        self.hr_rest = hr_rest
        self.hr_rest_activity_level = (
            ActivityLevel.ACTIVE if hr_rest <= 70 else ActivityLevel.SEDENTARY
        )
        self.is_classification_consistent = (
            self.hr_rest_activity_level == self.ipaq_activity_level
        )

    # ---------- xuất ra để lưu CSV / log ----------

    def to_dict(self) -> dict:
        return {
            "patient_id": self.patient_id,
            "created_at": self.created_at,
            "name": self.name,
            "age": self.age,
            "sex": self.sex.value,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "hr_max": self.hr_max,
            "moderate_vigorous_days_per_week": self.moderate_vigorous_days_per_week,
            "ipaq_activity_level": self.ipaq_activity_level.value,
            "hr_rest": self.hr_rest,
            "hr_rest_activity_level": (
                self.hr_rest_activity_level.value if self.hr_rest_activity_level else None
            ),
            "is_classification_consistent": self.is_classification_consistent,
            # nhãn cuối dùng để tách thư mục lưu dữ liệu
            "final_group": self.ipaq_activity_level.value,
        }
