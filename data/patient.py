"""
data/patient.py
----------------
PatientProfile: ho so doi tuong nhap tu PatientPanel (UI layer).
Chua thong tin tinh (demographic) + phan loai IPAQ-SF rut gon.

Phan loai IPAQ dua tren 2 domain chinh thuc cua IPAQ Short Form
(Craig et al. 2003): vigorous-intensity va moderate-intensity activity,
theo dung cau hoi goc "so ngay/tuan" + "so phut/ngay". Nguong phan loai
Active/Sedentary dung dichotomization method pho bien trong nghien cuu
lam sang ap dung IPAQ-SF, dua tren khuyen nghi WHO/ACSM (>=150 phut/tuan
MVPA hoac >=75 phut/tuan vigorous).

Khong chua logic Karvonen (HRR, target zone) - viec do thuoc ve
control/hr_target.py vi phu thuoc HR_rest do thuc nghiem, khong co san
tai thoi diem nhap lieu ban dau.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from core import config


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"       # it van dong
    ACTIVE = "active"             # van dong nhieu


@dataclass
class PatientProfile:
    # --- nhap tay tu PatientPanel ---
    name: str
    age: int
    sex: Sex
    height_cm: float
    weight_kg: float

    # --- IPAQ-SF rut gon: 2 domain vigorous + moderate (Craig et al. 2003) ---
    vigorous_days_per_week: int = 0     # so ngay/tuan hoat dong cuong do MANH (>=10 phut lien tuc)
    vigorous_min_per_day: int = 0       # so phut/ngay trung binh cho hoat dong do
    moderate_days_per_week: int = 0     # so ngay/tuan hoat dong cuong do VUA
    moderate_min_per_day: int = 0       # so phut/ngay trung binh

    # --- id & timestamp, tu sinh ---
    patient_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    # --- tinh toan ngay khi nhap xong (khong can HR_rest) ---
    hr_max: float = field(init=False)
    ipaq_activity_level: ActivityLevel = field(init=False)
    mvpa_min_per_week: float = field(init=False)

    # --- cac truong nay CHUA co tai thoi diem nhap lieu,
    #     duoc dien sau buoc do HR_rest (xem control/hr_target.py) ---
    hr_rest: float | None = None
    hr_rest_activity_level: ActivityLevel | None = None
    is_classification_consistent: bool | None = None

    def __post_init__(self):
        self.hr_max = self._compute_hr_max()
        self.mvpa_min_per_week, self.ipaq_activity_level = self._classify_ipaq()

    # ---------- cong thuc ----------

    def _compute_hr_max(self) -> float:
        """Tanaka formula: HRmax = 208 - 0.7 * age"""
        return round(208 - 0.7 * self.age, 1)

    def _classify_ipaq(self) -> tuple[float, ActivityLevel]:
        """
        IPAQ-SF rut gon, chi 2 domain vigorous + moderate.
        Data cleaning theo protocol IPAQ chinh thuc: cat ve toi da 7 ngay.

        MVPA_phut/tuan = (ngay_manh x phut_manh/ngay) + (ngay_vua x phut_vua/ngay)
        Active neu: MVPA_phut/tuan >= 150  HOAC  phut_manh/tuan >= 75
        """
        v_days = max(0, min(7, self.vigorous_days_per_week))
        m_days = max(0, min(7, self.moderate_days_per_week))
        v_min = max(0, self.vigorous_min_per_day)
        m_min = max(0, self.moderate_min_per_day)

        vigorous_min_per_week = v_days * v_min
        moderate_min_per_week = m_days * m_min
        mvpa = vigorous_min_per_week + moderate_min_per_week

        is_active = (
            mvpa >= config.MVPA_ACTIVE_THRESHOLD_MIN_PER_WEEK
            or vigorous_min_per_week >= config.VIGOROUS_ACTIVE_THRESHOLD_MIN_PER_WEEK
        )
        level = ActivityLevel.ACTIVE if is_active else ActivityLevel.SEDENTARY
        return float(mvpa), level

    # ---------- goi sau khi do HR_rest xong ----------

    def apply_hr_rest(self, hr_rest: float) -> None:
        """
        Dien HR_rest do duoc, tinh nhan cross-check, va co nhat quan.
        Goi ham nay ngay sau buoc do baseline (truoc warm-up).
        """
        self.hr_rest = hr_rest
        self.hr_rest_activity_level = (
            ActivityLevel.ACTIVE if hr_rest <= config.HR_REST_ACTIVE_THRESHOLD_BPM else ActivityLevel.SEDENTARY
        )
        self.is_classification_consistent = (
            self.hr_rest_activity_level == self.ipaq_activity_level
        )

    # ---------- xuat ra de luu CSV / log ----------

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
            "vigorous_days_per_week": self.vigorous_days_per_week,
            "vigorous_min_per_day": self.vigorous_min_per_day,
            "moderate_days_per_week": self.moderate_days_per_week,
            "moderate_min_per_day": self.moderate_min_per_day,
            "mvpa_min_per_week": self.mvpa_min_per_week,
            "ipaq_activity_level": self.ipaq_activity_level.value,
            "hr_rest": self.hr_rest,
            "hr_rest_activity_level": (
                self.hr_rest_activity_level.value if self.hr_rest_activity_level else None
            ),
            "is_classification_consistent": self.is_classification_consistent,
            # nhan cuoi dung de tach thu muc luu du lieu
            "final_group": self.ipaq_activity_level.value,
        }
