"""
ui/preflight_checklist_view.py
----------------------------------
Checklist tinh truoc khi vao SessionView (MICT). Chi bat "Bat dau"
khi tat ca da tick. SessionView THAT chua duoc viet (nam sau moc
Fuzzy/hardware) - man hinh nay hien tai la diem dung cuoi cua nhanh
Heart Rate Control.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QCheckBox, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal


class PreflightChecklistView(QWidget):
    back_to_menu = pyqtSignal()
    ready_to_start = pyqtSignal(object)  # PatientProfile

    CHECKLIST_ITEMS = [
        "Điện cực ECG đã dán đúng vị trí (Mason-Likar Lead II)",
        "Dây BIOPAC MP36 đã kết nối, đã kiểm tra tín hiệu ECG ổn định",
        "Board Arduino đã cấp nguồn, đèn báo hoạt động bình thường",
        "Đối tượng đã ngồi đúng tư thế trên ergometer",
    ]

    def __init__(self):
        super().__init__()
        self.patient = None
        self._checkboxes = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setSpacing(14)

        self.title = QLabel("Checklist trước khi bắt đầu")
        self.title.setStyleSheet("font-size: 18px; font-weight: 500;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.title)
        layout.addSpacing(10)

        for item_text in self.CHECKLIST_ITEMS:
            cb = QCheckBox(item_text)
            cb.setStyleSheet("font-size: 13px;")
            cb.stateChanged.connect(self._update_start_button)
            self._checkboxes.append(cb)
            layout.addWidget(cb)

        layout.addSpacing(10)

        self.btn_start = QPushButton("Bắt đầu chương trình MICT")
        self.btn_start.setMinimumHeight(46)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._on_start)

        btn_back = QPushButton("Quay về menu")
        btn_back.clicked.connect(self._on_back)

        layout.addWidget(self.btn_start)
        layout.addWidget(btn_back)
        layout.addStretch()
        self.setLayout(layout)

    def set_patient(self, patient):
        self.patient = patient
        self.reset()

    def _update_start_button(self):
        all_checked = all(cb.isChecked() for cb in self._checkboxes)
        self.btn_start.setEnabled(all_checked)

    def _on_start(self):
        self.ready_to_start.emit(self.patient)

    def _on_back(self):
        self.reset()
        self.back_to_menu.emit()

    def reset(self):
        for cb in self._checkboxes:
            cb.setChecked(False)
