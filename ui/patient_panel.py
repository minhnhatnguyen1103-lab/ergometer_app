"""Patient intake wizard: demographics, IPAQ-SF and confirmation."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)

from data.patient import PatientProfile, Sex
from ui.widgets import Card, StepRail, page_header, set_variant

SHOW_DEBUG_INFO = False


def _page_shell(widget: QWidget, title: str, subtitle: str) -> QVBoxLayout:
    root = QHBoxLayout(widget)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    root.addWidget(StepRail(0))

    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(34, 28, 38, 28)
    layout.setSpacing(18)
    layout.addWidget(page_header("BƯỚC 01 / 05 · PATIENT INTAKE", title, subtitle))
    root.addWidget(content, 1)
    return layout


def _action_row(back_text: str, next_text: str) -> tuple[QHBoxLayout, QPushButton, QPushButton]:
    row = QHBoxLayout()
    back = QPushButton(back_text)
    set_variant(back, "ghost")
    next_button = QPushButton(next_text)
    set_variant(next_button, "primary")
    row.addWidget(back)
    row.addStretch()
    row.addWidget(next_button)
    return row, back, next_button


class _BasicInfoPage(QWidget):
    next_requested = pyqtSignal(dict)
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = _page_shell(
            self, "Thông tin đối tượng",
            "Nhập dữ liệu nhận dạng cho protocol. HRmax được tính tự động và không hiển thị trên UI vận hành.",
        )

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 22)
        card_layout.setSpacing(14)
        heading = QLabel("THÔNG TIN CƠ BẢN")
        heading.setObjectName("sectionTitle")
        card_layout.addWidget(heading)

        form = QFormLayout()
        form.setHorizontalSpacing(22)
        form.setVerticalSpacing(14)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Họ và tên đối tượng")
        form.addRow("Tên đối tượng", self.name_input)

        self.age_input = QSpinBox()
        self.age_input.setRange(10, 100)
        self.age_input.setValue(22)
        form.addRow("Tuổi  ·  HRmax tự tính", self.age_input)

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
        self.debug_label.setObjectName("mutedText")
        card_layout.addLayout(form)
        if SHOW_DEBUG_INFO:
            card_layout.addWidget(self.debug_label)
        layout.addWidget(card, 1)

        actions, btn_back, btn_next = _action_row("← Về menu", "Tiếp tục · IPAQ  →")
        btn_back.clicked.connect(self.back_requested.emit)
        btn_next.clicked.connect(self._on_next)
        layout.addLayout(actions)

        self.age_input.valueChanged.connect(self._update_debug)
        self._update_debug()

    def _update_debug(self):
        if SHOW_DEBUG_INFO:
            self.debug_label.setText(f"[DEBUG] HRmax = {208 - 0.7 * self.age_input.value():.1f} bpm")

    def _on_next(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên đối tượng.")
            return
        self.next_requested.emit({
            "name": name,
            "age": self.age_input.value(),
            "sex": self.sex_input.currentData(),
            "height_cm": float(self.height_input.value()),
            "weight_kg": float(self.weight_input.value()),
        })

    def clear(self):
        self.name_input.clear()
        self.age_input.setValue(22)
        self.sex_input.setCurrentIndex(0)
        self.height_input.setValue(170)
        self.weight_input.setValue(65)


class _IpaqPage(QWidget):
    submit_requested = pyqtSignal(dict)
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = _page_shell(
            self, "Đánh giá vận động IPAQ-SF",
            "Trả lời theo 7 ngày gần nhất. Kết quả dùng để chọn mức tải khởi động phù hợp.",
        )

        columns = QHBoxLayout()
        columns.setSpacing(16)
        vigorous_card, self.vig_days, self.vig_min = self._activity_card(
            "CƯỜNG ĐỘ MẠNH", "Tim đập nhanh, thở gấp · tối thiểu 10 phút liên tục"
        )
        moderate_card, self.mod_days, self.mod_min = self._activity_card(
            "CƯỜNG ĐỘ VỪA", "Thở nhanh hơn bình thường · tối thiểu 10 phút liên tục"
        )
        columns.addWidget(vigorous_card, 1)
        columns.addWidget(moderate_card, 1)
        layout.addLayout(columns, 1)

        actions, btn_back, btn_submit = _action_row("← Thông tin cơ bản", "Tính nhóm IPAQ  →")
        btn_back.clicked.connect(self.back_requested.emit)
        btn_submit.clicked.connect(self._on_submit)
        layout.addLayout(actions)

    @staticmethod
    def _activity_card(title: str, helper: str) -> tuple[Card, QSpinBox, QSpinBox]:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        note = QLabel(helper)
        note.setObjectName("pageSubtitle")
        note.setWordWrap(True)
        days = QSpinBox()
        days.setRange(0, 7)
        days.setSuffix(" ngày / tuần")
        minutes = QSpinBox()
        minutes.setRange(0, 300)
        minutes.setSuffix(" phút / ngày")
        layout.addWidget(heading)
        layout.addWidget(note)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Số ngày thực hiện"))
        layout.addWidget(days)
        layout.addWidget(QLabel("Thời lượng trung bình"))
        layout.addWidget(minutes)
        layout.addStretch()
        return card, days, minutes

    def _on_submit(self):
        self.submit_requested.emit({
            "vigorous_days_per_week": self.vig_days.value(),
            "vigorous_min_per_day": self.vig_min.value(),
            "moderate_days_per_week": self.mod_days.value(),
            "moderate_min_per_day": self.mod_min.value(),
        })

    def clear(self):
        for field in (self.vig_days, self.vig_min, self.mod_days, self.mod_min):
            field.setValue(0)


class _ResultPage(QWidget):
    continue_requested = pyqtSignal()
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = _page_shell(
            self, "Hồ sơ sẵn sàng",
            "Kiểm tra phân nhóm trước khi chuyển sang phép đo HR nghỉ.",
        )
        card = Card(object_name="summaryHero")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 26, 28, 26)
        card_layout.setSpacing(10)
        self.title = QLabel("")
        self.title.setObjectName("pageTitle")
        self.summary = QLabel("")
        self.summary.setObjectName("pageSubtitle")
        self.summary.setWordWrap(True)
        card_layout.addWidget(QLabel("✓  PATIENT PROFILE CREATED"))
        card_layout.addWidget(self.title)
        card_layout.addWidget(self.summary)
        card_layout.addStretch()
        layout.addWidget(card, 1)

        actions, btn_back, btn_continue = _action_row("← Về menu", "Tiếp tục · Đo HR nghỉ  →")
        btn_back.clicked.connect(self.back_requested.emit)
        btn_continue.clicked.connect(self.continue_requested.emit)
        layout.addLayout(actions)

    def show_result(self, patient: PatientProfile):
        self.title.setText(patient.name)
        level_text = "VẬN ĐỘNG NHIỀU" if patient.ipaq_activity_level.value == "active" else "ÍT VẬN ĐỘNG"
        self.summary.setText(
            f"Nhóm IPAQ: {level_text}\n"
            f"MVPA 7 ngày: {patient.mvpa_min_per_week:.0f} phút / tuần\n\n"
            "Tiếp theo: đo nhịp tim nghỉ để tính vùng mục tiêu Karvonen."
        )


class PatientPanel(QWidget):
    back_to_menu = pyqtSignal()
    patient_ready = pyqtSignal(object)

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

        for page in (self.basic_page, self.ipaq_page, self.result_page):
            self.stack.addWidget(page)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

    def _on_basic_done(self, data: dict):
        self._basic_data = data
        self.stack.setCurrentWidget(self.ipaq_page)

    def _on_ipaq_submit(self, ipaq_data: dict):
        patient = PatientProfile(**{**self._basic_data, **ipaq_data})
        print(f"[DEBUG] Patient {patient.name}: HRmax={patient.hr_max} bpm "
              "(khong hien thi tren UI chinh thuc)")
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
