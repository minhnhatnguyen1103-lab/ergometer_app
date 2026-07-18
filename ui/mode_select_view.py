"""Landing screen for selecting an operator workflow."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.widgets import Card, FeatureButton, StatusBadge, page_header, set_variant


class ModeSelectView(QWidget):
    mode_selected = pyqtSignal(str)
    resume_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._pending_list = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(54, 42, 54, 34)
        layout.setSpacing(22)

        header_row = QHBoxLayout()
        header_row.addWidget(page_header(
            "GENUS-249 · CLOSED-LOOP LAB CONTROL",
            "Ergometer Control System",
            "Điều khiển MICT theo vùng Karvonen và ghi ECG thời gian thực.",
        ), 1)
        header_row.addWidget(StatusBadge("● APP READY", "live"), 0)
        layout.addLayout(header_row)

        section = QLabel("CHỌN LUỒNG LÀM VIỆC")
        section.setObjectName("eyebrow")
        layout.addWidget(section)

        modes = QHBoxLayout()
        modes.setSpacing(16)
        self.btn_hrc = FeatureButton(
            "♥", "HEART RATE CONTROL",
            "Chạy protocol MICT theo nhịp tim, có kiểm tra an toàn và điều khiển mức tải.",
            "Bắt đầu protocol",
        )
        self.btn_hrc.clicked.connect(lambda: self.mode_selected.emit("heart_rate_control"))
        self.btn_ecg = FeatureButton(
            "⌁", "ECG RECORDING",
            "Theo dõi tín hiệu BIOPAC MP36, nhịp tim và ghi dữ liệu ECG/R-peak.",
            "Mở màn hình ghi",
        )
        self.btn_ecg.clicked.connect(lambda: self.mode_selected.emit("ecg_realtime"))
        modes.addWidget(self.btn_hrc, 1)
        modes.addWidget(self.btn_ecg, 1)
        layout.addLayout(modes, 1)

        self.resume_card = Card()
        resume_layout = QHBoxLayout(self.resume_card)
        resume_layout.setContentsMargins(18, 14, 18, 14)
        resume_layout.setSpacing(14)
        resume_copy = QVBoxLayout()
        resume_title = QLabel("SESSION ĐANG TẠM DỪNG")
        resume_title.setObjectName("eyebrow")
        self.lbl_resume_detail = QLabel("")
        self.lbl_resume_detail.setObjectName("pageSubtitle")
        resume_copy.addWidget(resume_title)
        resume_copy.addWidget(self.lbl_resume_detail)
        self.btn_resume = QPushButton("Tiếp tục")
        self.btn_resume.clicked.connect(self._on_resume_clicked)
        set_variant(self.btn_resume, "primary")
        resume_layout.addLayout(resume_copy, 1)
        resume_layout.addWidget(self.btn_resume)
        self.resume_card.hide()
        layout.addWidget(self.resume_card)

        footer = QHBoxLayout()
        note = QLabel("SAFETY LAYER  ·  ECG SIGNAL MONITOR  ·  FUZZY CONTROL")
        note.setObjectName("monoText")
        footer.addWidget(note)
        footer.addStretch()
        footer.addWidget(StatusBadge("GENUS-249 · MICT", "neutral"))
        layout.addLayout(footer)

    def refresh_pending(self, pending_list: list[dict]):
        self._pending_list = pending_list
        if pending_list:
            latest = pending_list[0]
            suffix = f" và {len(pending_list) - 1} session khác" if len(pending_list) > 1 else ""
            self.lbl_resume_detail.setText(f'{latest["name"]} · {latest["created_at"]}{suffix}')
            self.btn_resume.setText(f"Tiếp tục ({len(pending_list)})")
            self.resume_card.show()
        else:
            self.resume_card.hide()

    def _on_resume_clicked(self):
        if not self._pending_list:
            return
        if len(self._pending_list) == 1:
            self.resume_requested.emit(self._pending_list[0]["patient_id"])
            return

        from PyQt6.QtWidgets import QInputDialog
        items = [f'{p["name"]} — {p["created_at"]}' for p in self._pending_list]
        chosen, ok = QInputDialog.getItem(
            self, "Chọn session", "Session đang dở:", items, 0, False
        )
        if ok and chosen:
            self.resume_requested.emit(self._pending_list[items.index(chosen)]["patient_id"])
