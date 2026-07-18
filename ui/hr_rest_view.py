"""Focused HR-rest capture screen backed by the shared WaveformView."""

import statistics

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from core import config
from ui.waveform_view import WaveformView
from ui.widgets import Card, StatusBadge, StepRail, metric_card, page_header, set_variant


class HrRestView(QWidget):
    back_to_menu = pyqtSignal()
    hr_rest_confirmed = pyqtSignal(object)

    def __init__(self, duration_sec: int | None = None):
        super().__init__()
        self._duration_sec = duration_sec or config.HR_REST_DURATION_SEC
        self.patient = None
        self._remaining_sec = self._duration_sec
        self._bpm_samples = []

        self.waveform = WaveformView()
        self.waveform.hr_updated.connect(self._on_hr_updated)
        self.waveform.status_changed.connect(self._on_status_changed)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(StepRail(1))

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 32, 24)
        layout.setSpacing(14)
        root.addWidget(content, 1)

        header = QHBoxLayout()
        header.addWidget(page_header(
            "BƯỚC 02 / 05 · BASELINE CAPTURE",
            "Đo nhịp tim nghỉ",
            "Giữ đối tượng ngồi yên, thư giãn và không nói chuyện trong suốt phép đo.",
        ), 1)
        self.status_badge = StatusBadge("● CHƯA BẮT ĐẦU", "neutral")
        header.addWidget(self.status_badge)
        layout.addLayout(header)

        self.lbl_name = QLabel("")
        self.lbl_name.setObjectName("sectionTitle")
        layout.addWidget(self.lbl_name)

        body = QHBoxLayout()
        body.setSpacing(14)
        plot_card = Card(object_name="plotCard")
        plot_layout = QVBoxLayout(plot_card)
        plot_layout.setContentsMargins(10, 10, 10, 10)
        plot_layout.addWidget(self.waveform)
        body.addWidget(plot_card, 3)

        side = QVBoxLayout()
        bpm_card, self.lbl_current_bpm = metric_card("Nhịp tim hiện tại", "—", "BPM")
        side.addWidget(bpm_card)
        timer_card = Card()
        timer_layout = QVBoxLayout(timer_card)
        timer_layout.setContentsMargins(18, 16, 18, 16)
        label = QLabel("THỜI GIAN ĐO")
        label.setObjectName("eyebrow")
        self.lbl_countdown = QLabel("")
        self.lbl_countdown.setObjectName("metricValue")
        self.lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        timer_layout.addWidget(label)
        timer_layout.addWidget(self.lbl_countdown)
        timer_layout.addWidget(self.progress_bar)
        self.lbl_instruction = QLabel(
            f"Kết quả = trung vị BPM của nửa sau khoảng đo "
            f"{self._duration_sec // 60:02d}:{self._duration_sec % 60:02d}."
        )
        self.lbl_instruction.setObjectName("pageSubtitle")
        self.lbl_instruction.setWordWrap(True)
        timer_layout.addWidget(self.lbl_instruction)
        side.addWidget(timer_card, 1)
        body.addLayout(side, 1)
        layout.addLayout(body, 1)

        actions = QHBoxLayout()
        btn_cancel = QPushButton("← Hủy và về menu")
        set_variant(btn_cancel, "ghost")
        btn_cancel.clicked.connect(self._on_cancel)
        self.btn_start = QPushButton("Bắt đầu đo HR nghỉ")
        set_variant(self.btn_start, "primary")
        self.btn_start.clicked.connect(self._start_measurement)
        actions.addWidget(btn_cancel)
        actions.addStretch()
        actions.addWidget(self.btn_start)
        layout.addLayout(actions)

    def set_patient(self, patient):
        self.patient = patient
        self.lbl_name.setText(f"Đối tượng  ·  {patient.name}")
        self.reset()

    def reset(self):
        self._timer.stop()
        self.waveform.stop()
        self._remaining_sec = self._duration_sec
        self._bpm_samples = []
        self._update_countdown_label()
        self.lbl_current_bpm.setText("—")
        self.progress_bar.setValue(0)
        self.status_badge.set_status("● CHƯA BẮT ĐẦU", "neutral")
        self.btn_start.show()
        self.btn_start.setEnabled(True)

    def _start_measurement(self):
        self._remaining_sec = self._duration_sec
        self._bpm_samples = []
        self.btn_start.hide()
        self.status_badge.set_status("● ĐANG KHỞI TẠO", "neutral")
        self._update_countdown_label()
        self.waveform.start()
        self._timer.start(1000)

    def _on_hr_updated(self, bpm: float):
        self._bpm_samples.append(bpm)
        self.lbl_current_bpm.setText(f"{bpm:.0f}")

    def _on_status_changed(self, is_connected: bool, is_demo: bool):
        if is_demo:
            self.status_badge.set_status("● DEMO SIGNAL", "demo")
        elif is_connected:
            self.status_badge.set_status("● LIVE · MP36", "live")
        else:
            self.status_badge.set_status("● SIGNAL ERROR", "error")

    def _tick(self):
        self._remaining_sec -= 1
        self._update_countdown_label()
        elapsed = self._duration_sec - max(0, self._remaining_sec)
        self.progress_bar.setValue(int(elapsed / max(1, self._duration_sec) * 100))
        if self._remaining_sec <= 0:
            self._finish_measurement()

    def _update_countdown_label(self):
        minutes, seconds = divmod(max(0, self._remaining_sec), 60)
        self.lbl_countdown.setText(f"{minutes:02d}:{seconds:02d}")

    def _finish_measurement(self):
        self._timer.stop()
        self.waveform.stop()
        if not self._bpm_samples:
            QMessageBox.warning(
                self, "Không có dữ liệu",
                "Không detect được nhịp tim nào trong lúc đo.\n"
                "Kiểm tra lại điện cực / kết nối rồi đo lại.",
            )
            self.reset()
            return

        half = len(self._bpm_samples) // 2
        recent = self._bpm_samples[half:] or self._bpm_samples
        self._confirm_result(statistics.median(recent))

    def _confirm_result(self, hr_rest_candidate: float):
        reply = QMessageBox.question(
            self, "Xác nhận HR nghỉ",
            f"HR nghỉ đo được: {hr_rest_candidate:.0f} BPM.\n\n"
            "Chấp nhận kết quả này? Chọn Không nếu có nhiễu hoặc đối tượng cử động.",
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
