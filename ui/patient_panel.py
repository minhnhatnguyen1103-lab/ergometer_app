"""
ui/patient_panel.py
----------------------
Man hinh dau tien cua mode "Heart Rate Control": nhap thong tin co ban
-> IPAQ-SF rut gon -> tao PatientProfile.

QUAN TRONG: HRmax duoc TINH NGAM khi tao PatientProfile (trong
__post_init__ cua patient.py), nhung KHONG hien thi len UI o ban chinh
thuc - chi in ra console (print) de debug khi can. Neu can hien lai de
test nhanh, sua bien SHOW_DEBUG_INFO = True o duoi file nay.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QComboBox, QSpinBox, QPushButton, QStackedWidget, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from data.patient import PatientProfile, Sex

# Bat True khi dang test de xem HRmax/MVPA ngay tren UI cho de kiem tra.
# Ban chinh thuc PHAI de False.
SHOW_DEBUG_INFO = False


class _BasicInfoPage(QWidget):
    next_requested = pyqtSignal(dict)   # {"name":..., "age":..., "sex":..., "height_cm":..., "weight_kg":...}
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(60, 50, 60, 50)
        layout.setSpacing(16)

        title = QLabel("Thông tin đối tượng")
        title.setStyleSheet("font-size: 20px; font-weight: 500;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form = QFormLayout()
        form.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Họ tên...")
        form.addRow("Tên", self.name_input)

        self.age_input = QSpinBox()
        self.age_input.setRange(10, 100)
        self.age_input.setValue(22)
        form.addRow("Tuổi", self.age_input)

        self.sex_input = QComboBox()
        self.sex_input.addItem("Nam", Sex.MALE)
        self.sex_input.addItem("Nữ", Sex.FEMALE)
        form.addRow("Giới tính", self.sex_input)

        self.height_input = QSpinBox()
        self.height_input.setRange(100, 220)
        self.height_input.setValue(170)
        self.height_input.setSuffix(" cm")
        form.addRow("Chiều cao", self.height_input)

        self.weight_input = QSpinBox()
        self.weight_input.setRange(20, 200)
        self.weight_input.setValue(65)
        self.weight_input.setSuffix(" kg")
        form.addRow("Cân nặng", self.weight_input)

        self.debug_label = QLabel("")
        self.debug_label.setStyleSheet("font-size: 12px; color: gray;")

        btn_next = QPushButton("Tiếp tục → Đánh giá IPAQ")
        btn_next.setMinimumHeight(46)
        btn_next.clicked.connect(self._on_next)

        btn_back = QPushButton("Quay lại")
        btn_back.clicked.connect(self.back_requested.emit)

        layout.addWidget(title)
        layout.addLayout(form)
        if SHOW_DEBUG_INFO:
            layout.addWidget(self.debug_label)
        layout.addWidget(btn_next)
        layout.addWidget(btn_back)
        layout.addStretch()
        self.setLayout(layout)

        # Cap nhat debug label khi tuoi thay doi (chi de test, khong phai UI chinh thuc)
        self.age_input.valueChanged.connect(self._update_debug)
        self._update_debug()

    def _update_debug(self):
        if not SHOW_DEBUG_INFO:
            return
        age = self.age_input.value()
        hr_max = round(208 - 0.7 * age, 1)
        self.debug_label.setText(f"[DEBUG] HRmax = {hr_max} bpm")

    def _on_next(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên đối tượng.")
            return
        data = {
            "name": name,
            "age": self.age_input.value(),
            "sex": self.sex_input.currentData(),
            "height_cm": float(self.height_input.value()),
            "weight_kg": float(self.weight_input.value()),
        }
        self.next_requested.emit(data)

    def clear(self):
        self.name_input.clear()
        self.age_input.setValue(22)
        self.sex_input.setCurrentIndex(0)
        self.height_input.setValue(170)
        self.weight_input.setValue(65)


class _IpaqPage(QWidget):
    """
    IPAQ-SF rut gon: chi 2 domain vigorous + moderate (bo domain di bo va
    ngoi, vi khong can cho muc dich phan loai nhom cua do an).
    """
    submit_requested = pyqtSignal(dict)  # {"vigorous_days_per_week":..., ...}
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(60, 50, 60, 50)
        layout.setSpacing(16)

        title = QLabel("Đánh giá mức độ vận động (IPAQ)")
        title.setStyleSheet("font-size: 18px; font-weight: 500;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        note = QLabel("Trả lời dựa trên 7 ngày gần nhất")
        note.setStyleSheet("font-size: 12px; color: gray;")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form = QFormLayout()
        form.setSpacing(12)

        q1 = QLabel(
            "Bao nhiêu ngày bạn thực hiện hoạt động cường độ MẠNH\n"
            "(tim đập nhanh, thở gấp) ít nhất 10 phút liên tục?"
        )
        q1.setWordWrap(True)
        self.vig_days = QSpinBox()
        self.vig_days.setRange(0, 7)
        self.vig_days.setSuffix(" ngày/tuần")
        form.addRow(q1, self.vig_days)

        self.vig_min = QSpinBox()
        self.vig_min.setRange(0, 300)
        self.vig_min.setSuffix(" phút/ngày")
        form.addRow("Trung bình mỗi ngày đó", self.vig_min)

        q2 = QLabel(
            "Bao nhiêu ngày bạn thực hiện hoạt động cường độ VỪA\n"
            "(thở nhanh hơn bình thường) ít nhất 10 phút liên tục?"
        )
        q2.setWordWrap(True)
        self.mod_days = QSpinBox()
        self.mod_days.setRange(0, 7)
        self.mod_days.setSuffix(" ngày/tuần")
        form.addRow(q2, self.mod_days)

        self.mod_min = QSpinBox()
        self.mod_min.setRange(0, 300)
        self.mod_min.setSuffix(" phút/ngày")
        form.addRow("Trung bình mỗi ngày đó", self.mod_min)

        btn_submit = QPushButton("Hoàn tất")
        btn_submit.setMinimumHeight(46)
        btn_submit.clicked.connect(self._on_submit)

        btn_back = QPushButton("Quay lại")
        btn_back.clicked.connect(self.back_requested.emit)

        layout.addWidget(title)
        layout.addWidget(note)
        layout.addLayout(form)
        layout.addWidget(btn_submit)
        layout.addWidget(btn_back)
        layout.addStretch()
        self.setLayout(layout)

    def _on_submit(self):
        data = {
            "vigorous_days_per_week": self.vig_days.value(),
            "vigorous_min_per_day": self.vig_min.value(),
            "moderate_days_per_week": self.mod_days.value(),
            "moderate_min_per_day": self.mod_min.value(),
        }
        self.submit_requested.emit(data)

    def clear(self):
        self.vig_days.setValue(0)
        self.vig_min.setValue(0)
        self.mod_days.setValue(0)
        self.mod_min.setValue(0)


class _ResultPage(QWidget):
    """Xac nhan da tao PatientProfile - placeholder cho toi khi HrRestView co."""
    continue_requested = pyqtSignal()
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(60, 80, 60, 80)
        layout.setSpacing(16)

        self.title = QLabel("")
        self.title.setStyleSheet("font-size: 18px; font-weight: 500;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.summary = QLabel("")
        self.summary.setStyleSheet("font-size: 13px; color: gray;")
        self.summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary.setWordWrap(True)

        btn_continue = QPushButton("Tiếp tục → Đo HR_rest")
        btn_continue.setMinimumHeight(46)
        btn_continue.clicked.connect(self.continue_requested.emit)

        btn_back = QPushButton("Quay về menu")
        btn_back.clicked.connect(self.back_requested.emit)

        layout.addWidget(self.title)
        layout.addWidget(self.summary)
        layout.addWidget(btn_continue)
        layout.addWidget(btn_back)
        layout.addStretch()
        self.setLayout(layout)

    def show_result(self, patient: PatientProfile):
        self.title.setText(f"Đã ghi nhận: {patient.name}")
        level_text = "Vận động nhiều" if patient.ipaq_activity_level.value == "active" else "Ít vận động"
        self.summary.setText(
            f"Nhóm phân loại IPAQ: {level_text}\n"
            f"(MVPA: {patient.mvpa_min_per_week:.0f} phút/tuần)\n\n"
            f"Bước tiếp theo (đo HR_rest) sẽ được nối vào sau."
        )


class PatientPanel(QWidget):
    # MainWindow lang nghe de quay ve menu
    back_to_menu = pyqtSignal()
    # Phat ra khi PatientProfile da tao xong, mang du lieu cho buoc sau (HrRestView)
    patient_ready = pyqtSignal(object)  # PatientProfile

    def __init__(self):
        super().__init__()
        self.stack = QStackedWidget()
        self.basic_page = _BasicInfoPage()
        self.ipaq_page = _IpaqPage()
        self.result_page = _ResultPage()

        self._basic_data = {}
        self._current_patient = None

        self.basic_page.next_requested.connect(self._on_basic_done)
        self.basic_page.back_requested.connect(self.back_to_menu.emit)

        self.ipaq_page.submit_requested.connect(self._on_ipaq_submit)
        self.ipaq_page.back_requested.connect(lambda: self.stack.setCurrentWidget(self.basic_page))

        self.result_page.continue_requested.connect(self._on_continue)
        self.result_page.back_requested.connect(self._on_finish_back_to_menu)

        self.stack.addWidget(self.basic_page)
        self.stack.addWidget(self.ipaq_page)
        self.stack.addWidget(self.result_page)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

    def _on_basic_done(self, data: dict):
        self._basic_data = data
        self.stack.setCurrentWidget(self.ipaq_page)

    def _on_ipaq_submit(self, ipaq_data: dict):
        full_data = {**self._basic_data, **ipaq_data}
        patient = PatientProfile(**full_data)

        # HRmax tinh ngam - chi in console, KHONG hien UI (theo yeu cau ban chinh thuc)
        print(f"[DEBUG] Patient {patient.name}: HRmax={patient.hr_max} bpm "
              f"(khong hien thi tren UI chinh thuc)")

        self._current_patient = patient
        self.result_page.show_result(patient)
        self.stack.setCurrentWidget(self.result_page)

    def _on_continue(self):
        if self._current_patient:
            self.patient_ready.emit(self._current_patient)

    def _on_finish_back_to_menu(self):
        self.reset()
        self.back_to_menu.emit()

    def reset(self):
        self.basic_page.clear()
        self.ipaq_page.clear()
        self._current_patient = None
        self.stack.setCurrentWidget(self.basic_page)
