"""
ui/hr_rest_view.py
----------------------
Man hinh do HR_rest - buoc bat buoc truoc khi vao Warmup. Tai su dung
WaveformView (da co) de vua do vua cho nguoi van hanh nhin thay chat
luong tin hieu ECG/HR truc tiep trong luc do (thay vi mot hop thoai
tru tuong khong co gi de kiem tra).

Luong: Huong dan + nut Bat dau -> dem nguoc (mac dinh 2 phut, config.py)
-> tu dong tinh HR_rest (median cua nua sau thoi gian do, de bo qua
doan dau chua on dinh) -> popup Co/Khong -> Khong: do lai tu dau,
Co: goi patient.apply_hr_rest() va phat signal hr_rest_confirmed.
"""

import statistics

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from ui.waveform_view import WaveformView
from core import config


class HrRestView(QWidget):
    back_to_menu = pyqtSignal()
    # Phat ra khi da co HR_rest duoc xac nhan, patient.hr_rest da duoc dien
    hr_rest_confirmed = pyqtSignal(object)  # PatientProfile

    def __init__(self, duration_sec: int | None = None):
        """
        duration_sec: cho phep ghi de thoi gian do (dung khi TEST, de
        khong phai cho that 2 phut). Khi dung that trong app, de None
        de lay tu config.HR_REST_DURATION_SEC.
        """
        super().__init__()
        self._duration_sec = duration_sec or config.HR_REST_DURATION_SEC
        self.patient = None
        self._remaining_sec = self._duration_sec
        self._bpm_samples = []

        self.waveform = WaveformView()
        self.waveform.hr_updated.connect(self._on_hr_updated)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        self.lbl_name = QLabel("")
        self.lbl_name.setStyleSheet("font-size: 15px; font-weight: 500;")

        self.lbl_instruction = QLabel(
            "Yêu cầu đối tượng ngồi yên, thư giãn, không nói chuyện.\n"
            f"Thời gian đo: {self._duration_sec // 60} phút {self._duration_sec % 60} giây."
        )
        self.lbl_instruction.setStyleSheet("font-size: 13px; color: gray;")
        self.lbl_instruction.setWordWrap(True)

        self.lbl_countdown = QLabel("")
        self.lbl_countdown.setStyleSheet("font-size: 32px; font-weight: 600;")
        self.lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_countdown.hide()

        self.btn_start = QPushButton("Bắt đầu đo HR_rest")
        self.btn_start.setMinimumHeight(46)
        self.btn_start.clicked.connect(self._start_measurement)

        btn_cancel = QPushButton("Hủy, quay về menu")
        btn_cancel.clicked.connect(self._on_cancel)

        controls = QHBoxLayout()
        controls.addWidget(self.btn_start)
        controls.addWidget(btn_cancel)

        layout.addWidget(self.lbl_name)
        layout.addWidget(self.lbl_instruction)
        layout.addWidget(self.lbl_countdown)
        layout.addWidget(self.waveform, stretch=1)
        layout.addLayout(controls)
        self.setLayout(layout)

    # ─── API cho MainWindow ─────────────────────────────────────

    def set_patient(self, patient):
        self.patient = patient
        self.lbl_name.setText(f"Đối tượng: {patient.name}")
        self.reset()

    def reset(self):
        """Đưa view về trạng thái ban đầu — gọi khi vào lại hoặc sau khi
        người dùng chọn 'Không' ở popup xác nhận."""
        self._timer.stop()
        self.waveform.stop()
        self._remaining_sec = self._duration_sec
        self._bpm_samples = []
        self.lbl_countdown.hide()
        self.btn_start.show()
        self.btn_start.setEnabled(True)

    # ─── Đo ─────────────────────────────────────────────────────

    def _start_measurement(self):
        self._remaining_sec = self._duration_sec
        self._bpm_samples = []
        self.btn_start.hide()
        self.lbl_countdown.show()
        self._update_countdown_label()
        self.waveform.start()
        self._timer.start(1000)

    def _on_hr_updated(self, bpm: float):
        self._bpm_samples.append(bpm)

    def _tick(self):
        self._remaining_sec -= 1
        self._update_countdown_label()
        if self._remaining_sec <= 0:
            self._finish_measurement()

    def _update_countdown_label(self):
        m, s = divmod(max(0, self._remaining_sec), 60)
        self.lbl_countdown.setText(f"{m:02d}:{s:02d}")

    def _finish_measurement(self):
        self._timer.stop()
        self.waveform.stop()

        if not self._bpm_samples:
            QMessageBox.warning(
                self, "Không có dữ liệu",
                "Không detect được nhịp tim nào trong lúc đo.\n"
                "Kiểm tra lại điện cực / kết nối rồi đo lại."
            )
            self.reset()
            return

        # Chi lay nua sau cua thoi gian do - bo qua doan dau chua on dinh
        half = len(self._bpm_samples) // 2
        recent = self._bpm_samples[half:] or self._bpm_samples
        hr_rest_candidate = statistics.median(recent)

        self._confirm_result(hr_rest_candidate)

    def _confirm_result(self, hr_rest_candidate: float):
        reply = QMessageBox.question(
            self, "Xác nhận HR_rest",
            f"HR_rest đo được: {hr_rest_candidate:.0f} bpm.\n\n"
            "Bạn có chấp nhận kết quả này không?\n"
            "(Chọn Không nếu nghi ngờ nhiễu, đối tượng cử động, hoặc đo chưa ổn định)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.patient.apply_hr_rest(hr_rest_candidate)
            self.hr_rest_confirmed.emit(self.patient)
        else:
            self.reset()

    def _on_cancel(self):
        self.reset()
        self.back_to_menu.emit()
