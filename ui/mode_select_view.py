"""
ui/mode_select_view.py
------------------------
Man hinh dau tien nguoi dung thay khi mo app. 2 nut chinh, cong them
1 nut "Tiep tuc session dang do" CHI hien khi thuc su co session
dang do (kiem tra qua data/pending_session_store.py).
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal


class ModeSelectView(QWidget):
    mode_selected = pyqtSignal(str)
    # Phat ra kem patient_id duoc chon tu danh sach pending
    resume_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(60, 80, 60, 80)

        title = QLabel("Ergometer Control System")
        title.setStyleSheet("font-size: 22px; font-weight: 500;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Chọn chế độ hoạt động")
        subtitle.setStyleSheet("font-size: 14px; color: gray;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_ecg = QPushButton("Đo ECG real-time")
        btn_ecg.setMinimumHeight(56)
        btn_ecg.setStyleSheet("font-size: 15px;")
        btn_ecg.clicked.connect(lambda: self.mode_selected.emit("ecg_realtime"))

        btn_hrc = QPushButton("Heart Rate Control")
        btn_hrc.setMinimumHeight(56)
        btn_hrc.setStyleSheet("font-size: 15px; font-weight: 500;")
        btn_hrc.clicked.connect(lambda: self.mode_selected.emit("heart_rate_control"))

        self.btn_resume = QPushButton("Tiếp tục session dang dở")
        self.btn_resume.setMinimumHeight(44)
        self.btn_resume.setStyleSheet("font-size: 13px; color: #e65100;")
        self.btn_resume.clicked.connect(self._on_resume_clicked)
        self.btn_resume.hide()

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(16)
        layout.addWidget(btn_ecg)
        layout.addWidget(btn_hrc)
        layout.addWidget(self.btn_resume)

        self.setLayout(layout)

    def refresh_pending(self, pending_list: list[dict]):
        """MainWindow goi moi khi quay ve man hinh nay, truyen ket qua
        cua pending_session_store.list_pending()."""
        self._pending_list = pending_list
        if pending_list:
            self.btn_resume.setText(f"Tiếp tục session dang dở ({len(pending_list)})")
            self.btn_resume.show()
        else:
            self.btn_resume.hide()

    def _on_resume_clicked(self):
        if not self._pending_list:
            return
        if len(self._pending_list) == 1:
            self.resume_requested.emit(self._pending_list[0]["patient_id"])
            return

        from PyQt6.QtWidgets import QInputDialog
        items = [f'{p["name"]} — {p["created_at"]}' for p in self._pending_list]
        chosen, ok = QInputDialog.getItem(
            self, "Chọn session", "Session dang dở:", items, 0, False
        )
        if ok and chosen:
            idx = items.index(chosen)
            self.resume_requested.emit(self._pending_list[idx]["patient_id"])
