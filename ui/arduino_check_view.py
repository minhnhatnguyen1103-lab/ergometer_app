"""Operator-facing hardware gate before the preflight checklist."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from data.pending_session_store import save_pending
from hardware.port_scan import find_likely_arduino_port
from ui.widgets import Card, StatusBadge, StepRail, page_header, set_variant


class ArduinoCheckView(QWidget):
    back_to_menu = pyqtSignal()
    connected = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.patient = None
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(StepRail(2))

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(34, 28, 38, 28)
        layout.setSpacing(18)
        root.addWidget(content, 1)
        layout.addWidget(page_header(
            "BƯỚC 03 / 05 · SYSTEM CHECK",
            "Kiểm tra hệ thống",
            "Xác minh đường điều khiển mức tải trước khi cho phép bắt đầu protocol.",
        ))

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 22)
        card_layout.setSpacing(16)
        heading = QLabel("HARDWARE STATUS")
        heading.setObjectName("sectionTitle")
        card_layout.addWidget(heading)

        arduino_row = QHBoxLayout()
        arduino_copy = QVBoxLayout()
        arduino_title = QLabel("Arduino · brake controller")
        arduino_title.setObjectName("sectionTitle")
        self.status_label = QLabel("")
        self.status_label.setObjectName("pageSubtitle")
        self.status_label.setWordWrap(True)
        arduino_copy.addWidget(arduino_title)
        arduino_copy.addWidget(self.status_label)
        self.arduino_badge = StatusBadge("● ĐANG QUÉT", "neutral")
        arduino_row.addLayout(arduino_copy, 1)
        arduino_row.addWidget(self.arduino_badge)
        card_layout.addLayout(arduino_row)

        separator = QLabel("────────────────────────────────────────────────")
        separator.setObjectName("monoText")
        card_layout.addWidget(separator)
        biopac_row = QHBoxLayout()
        biopac_copy = QVBoxLayout()
        biopac_title = QLabel("BIOPAC MP36 · ECG source")
        biopac_title.setObjectName("sectionTitle")
        biopac_note = QLabel("Được xác minh trực tiếp qua tín hiệu ở bước HR nghỉ và live session.")
        biopac_note.setObjectName("pageSubtitle")
        biopac_copy.addWidget(biopac_title)
        biopac_copy.addWidget(biopac_note)
        biopac_row.addLayout(biopac_copy, 1)
        biopac_row.addWidget(StatusBadge("ECG PIPELINE", "neutral"))
        card_layout.addLayout(biopac_row)
        layout.addWidget(card, 1)

        actions = QHBoxLayout()
        btn_quit = QPushButton("← Thoát / lưu session")
        set_variant(btn_quit, "ghost")
        btn_quit.clicked.connect(self._on_quit)
        self.btn_retry = QPushButton("Quét lại cổng COM")
        self.btn_retry.clicked.connect(self._check_connection)
        self.btn_continue = QPushButton("Tiếp tục · Checklist  →")
        set_variant(self.btn_continue, "primary")
        self.btn_continue.clicked.connect(self._on_continue)
        self.btn_continue.hide()
        actions.addWidget(btn_quit)
        actions.addStretch()
        actions.addWidget(self.btn_retry)
        actions.addWidget(self.btn_continue)
        layout.addLayout(actions)

    def set_patient(self, patient):
        self.patient = patient
        self._check_connection()

    def _check_connection(self):
        port = find_likely_arduino_port()
        if port:
            self.status_label.setText(f"Đã tìm thấy thiết bị tại {port}. Đường điều khiển sẵn sàng.")
            self.arduino_badge.set_status(f"● READY · {port}", "live")
            self.btn_retry.hide()
            self.btn_continue.show()
        else:
            self.status_label.setText(
                "Chưa tìm thấy Arduino. Kiểm tra dây USB và nguồn board, sau đó quét lại."
            )
            self.arduino_badge.set_status("● NOT FOUND", "error")
            self.btn_retry.show()
            self.btn_continue.hide()

    def _on_continue(self):
        self.connected.emit(self.patient)

    def _on_quit(self):
        reply = QMessageBox.question(
            self, "Lưu session đang dở?",
            f"Chưa kết nối được Arduino cho {self.patient.name if self.patient else ''}.\n\n"
            "Lưu patient và HR nghỉ để tiếp tục sau?",
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
        self.arduino_badge.set_status("● ĐANG QUÉT", "neutral")
        self.btn_retry.show()
        self.btn_continue.hide()
