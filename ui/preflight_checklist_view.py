"""Safety checklist gate immediately before a MICT session."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.widgets import Card, StatusBadge, StepRail, page_header, set_variant


class PreflightChecklistView(QWidget):
    back_to_menu = pyqtSignal()
    ready_to_start = pyqtSignal(object)

    CHECKLIST_ITEMS = [
        "Điện cực ECG đã dán đúng vị trí · Mason-Likar Lead II",
        "BIOPAC MP36 đã kết nối · tín hiệu ECG ổn định",
        "Board Arduino đã cấp nguồn · đèn báo hoạt động bình thường",
        "Đối tượng đã ngồi đúng tư thế trên ergometer",
    ]

    def __init__(self):
        super().__init__()
        self.patient = None
        self._checkboxes = []
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(StepRail(3))

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(34, 28, 38, 28)
        layout.setSpacing(16)
        root.addWidget(content, 1)

        header = QHBoxLayout()
        header.addWidget(page_header(
            "BƯỚC 04 / 05 · SAFETY GATE",
            "Checklist trước buổi tập",
            "Phải xác nhận đủ 4 điều kiện trước khi hệ thống cho phép chạy MICT.",
        ), 1)
        self.progress_badge = StatusBadge("0 / 4", "warning")
        header.addWidget(self.progress_badge)
        layout.addLayout(header)

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(10)
        for item_text in self.CHECKLIST_ITEMS:
            checkbox = QCheckBox(item_text)
            checkbox.setObjectName("toggleCard")
            checkbox.stateChanged.connect(self._update_start_button)
            self._checkboxes.append(checkbox)
            card_layout.addWidget(checkbox)
        layout.addWidget(card, 1)

        actions = QHBoxLayout()
        btn_back = QPushButton("← Quay về menu")
        set_variant(btn_back, "ghost")
        btn_back.clicked.connect(self._on_back)
        self.btn_start = QPushButton("Bắt đầu chương trình MICT  →")
        set_variant(self.btn_start, "primary")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._on_start)
        actions.addWidget(btn_back)
        actions.addStretch()
        actions.addWidget(self.btn_start)
        layout.addLayout(actions)

    def set_patient(self, patient):
        self.patient = patient
        self.reset()

    def _update_start_button(self, *_):
        completed = sum(checkbox.isChecked() for checkbox in self._checkboxes)
        all_checked = completed == len(self._checkboxes)
        self.btn_start.setEnabled(all_checked)
        self.progress_badge.set_status(
            f"{completed} / {len(self._checkboxes)}",
            "live" if all_checked else "warning",
        )

    def _on_start(self):
        self.ready_to_start.emit(self.patient)

    def _on_back(self):
        self.reset()
        self.back_to_menu.emit()

    def reset(self):
        for checkbox in self._checkboxes:
            checkbox.setChecked(False)
        self._update_start_button()
