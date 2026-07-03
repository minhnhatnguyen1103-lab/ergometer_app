"""
ui/arduino_check_view.py
----------------------------
Man hinh kiem tra ket noi Arduino - buoc bat buoc truoc khi vao
PreflightChecklistView. Retry chi kiem tra lai danh sach cong COM
(khong tu dong polling ngam) - dung nhu da thong nhat: nguoi van hanh
phai thuc su cam day USB thi lan bam Retry tiep theo moi qua duoc.

Neu Quit ma chua ket noi duoc: hoi co muon luu session dang do khong
(patient + HR_rest da co, chi thieu Arduino) - de lan sau khoi phai do
lai HR_rest tu dau.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from hardware.port_scan import find_likely_arduino_port
from data.pending_session_store import save_pending


class ArduinoCheckView(QWidget):
    back_to_menu = pyqtSignal()
    # Phat ra khi da tim thay Arduino - mang theo patient de man hinh sau dung
    connected = pyqtSignal(object)  # PatientProfile

    def __init__(self):
        super().__init__()
        self.patient = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(60, 80, 60, 80)
        layout.setSpacing(18)

        self.title = QLabel("Kiểm tra kết nối Arduino")
        self.title.setStyleSheet("font-size: 18px; font-weight: 500;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 14px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)

        self.btn_retry = QPushButton("Kiểm tra lại")
        self.btn_retry.setMinimumHeight(44)
        self.btn_retry.clicked.connect(self._check_connection)

        self.btn_continue = QPushButton("Tiếp tục →")
        self.btn_continue.setMinimumHeight(44)
        self.btn_continue.clicked.connect(self._on_continue)
        self.btn_continue.hide()

        btn_quit = QPushButton("Quit (thoát, lưu tạm nếu cần)")
        btn_quit.clicked.connect(self._on_quit)

        layout.addWidget(self.title)
        layout.addWidget(self.status_label)
        layout.addWidget(self.btn_retry)
        layout.addWidget(self.btn_continue)
        layout.addWidget(btn_quit)
        layout.addStretch()
        self.setLayout(layout)

    def set_patient(self, patient):
        self.patient = patient
        self._check_connection()

    def _check_connection(self):
        port = find_likely_arduino_port()
        if port:
            self.status_label.setText(f"● Đã tìm thấy thiết bị tại {port}")
            self.status_label.setStyleSheet("font-size: 14px; color: #2e7d32;")
            self.btn_retry.hide()
            self.btn_continue.show()
        else:
            self.status_label.setText(
                "● Chưa tìm thấy Arduino.\n\n"
                "Kiểm tra: dây USB đã cắm chưa? Board đã cấp nguồn chưa?\n"
                "Cắm/kiểm tra xong, bấm \"Kiểm tra lại\"."
            )
            self.status_label.setStyleSheet("font-size: 14px; color: #e53935;")
            self.btn_retry.show()
            self.btn_continue.hide()

    def _on_continue(self):
        self.connected.emit(self.patient)

    def _on_quit(self):
        reply = QMessageBox.question(
            self, "Lưu session dang dở?",
            f"Chưa kết nối được Arduino cho {self.patient.name if self.patient else ''}.\n\n"
            "Lưu session này lại (đã có HR_rest) để tiếp tục sau,\n"
            "không cần đo lại HR_rest từ đầu?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes and self.patient:
            path = save_pending(self.patient)
            print(f"[INFO] Da luu session dang do: {path}")
        self.reset()
        self.back_to_menu.emit()

    def reset(self):
        self.patient = None
        self.status_label.setText("")
        self.btn_retry.show()
        self.btn_continue.hide()
