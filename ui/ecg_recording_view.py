"""
ui/ecg_recording_view.py
---------------------------
Màn hình hoàn chỉnh cho mode "Đo ECG real-time":
  1. _NameEntryPage: nhập tên đối tượng
  2. _StreamingPage: hiển thị WaveformView + nút Bắt đầu/Dừng ghi + Kết thúc

2 page nội bộ dùng QStackedWidget riêng, không lộ ra ngoài. Bên ngoài
(MainWindow) chỉ cần biết EcgRecordingView có signal back_to_menu.
"""

import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from ui.waveform_view import WaveformView


class _NameEntryPage(QWidget):
    start_requested = pyqtSignal(str)
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(60, 80, 60, 80)
        layout.setSpacing(18)

        title = QLabel("Đo ECG real-time")
        title.setStyleSheet("font-size: 20px; font-weight: 500;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel("Tên đối tượng")
        label.setStyleSheet("font-size: 13px; color: gray;")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nhập tên...")
        self.name_input.setMinimumHeight(40)

        btn_start = QPushButton("Bắt đầu streaming")
        btn_start.setMinimumHeight(48)
        btn_start.setStyleSheet("font-size: 14px; font-weight: 500;")
        btn_start.clicked.connect(self._on_start)

        btn_back = QPushButton("Quay lại")
        btn_back.setMinimumHeight(36)
        btn_back.clicked.connect(self.back_requested.emit)

        layout.addWidget(title)
        layout.addSpacing(10)
        layout.addWidget(label)
        layout.addWidget(self.name_input)
        layout.addWidget(btn_start)
        layout.addWidget(btn_back)
        layout.addStretch()
        self.setLayout(layout)

    def _on_start(self):
        name = self.name_input.text().strip() or "subject"
        self.start_requested.emit(name)

    def clear(self):
        self.name_input.clear()


class _StreamingPage(QWidget):
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.waveform = WaveformView()
        self.waveform.hr_updated.connect(self._on_hr_updated)
        self.waveform.status_changed.connect(self._on_status_changed)

        self._rec_timer = QTimer(self)
        self._rec_timer.timeout.connect(self._update_rec_time)
        self._rec_t0 = None
        self._subject_name = "subject"

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)

        header = QHBoxLayout()
        self.lbl_name = QLabel("")
        self.lbl_name.setStyleSheet("font-size: 15px; font-weight: 500;")
        self.lbl_status = QLabel("● CONNECTING")
        self.lbl_status.setStyleSheet("font-size: 12px; color: orange;")
        header.addWidget(self.lbl_name)
        header.addStretch()
        header.addWidget(self.lbl_status)

        metrics = QHBoxLayout()
        self.lbl_bpm = QLabel("---")
        self.lbl_bpm.setStyleSheet("font-size: 40px; font-weight: 600; color: #c62828;")
        bpm_unit = QLabel("BPM")
        bpm_unit.setStyleSheet("font-size: 12px; color: gray; padding-top: 18px;")
        metrics.addWidget(self.lbl_bpm)
        metrics.addWidget(bpm_unit)
        metrics.addStretch()
        self.lbl_rec_time = QLabel("")
        self.lbl_rec_time.setStyleSheet("font-size: 13px; color: gray;")
        metrics.addWidget(self.lbl_rec_time)

        controls = QHBoxLayout()
        self.btn_rec = QPushButton("⏺ Bắt đầu ghi")
        self.btn_rec.setMinimumHeight(44)
        self.btn_rec.clicked.connect(self._toggle_recording)
        btn_finish = QPushButton("Kết thúc, quay về menu")
        btn_finish.setMinimumHeight(44)
        btn_finish.clicked.connect(self._on_finish)
        controls.addWidget(self.btn_rec)
        controls.addWidget(btn_finish)

        layout.addLayout(header)
        layout.addLayout(metrics)
        layout.addWidget(self.waveform, stretch=1)
        layout.addLayout(controls)
        self.setLayout(layout)

    def start_streaming(self, subject_name: str):
        self._subject_name = subject_name
        self.lbl_name.setText(f"Đối tượng: {subject_name}")
        self.waveform.start()

    def _on_hr_updated(self, bpm: float):
        self.lbl_bpm.setText(f"{bpm:.0f}")

    def _on_status_changed(self, is_connected: bool, is_demo: bool):
        if is_demo:
            self.lbl_status.setText("● DEMO")
            self.lbl_status.setStyleSheet("font-size: 12px; color: #e65100;")
        elif is_connected:
            self.lbl_status.setText("● LIVE")
            self.lbl_status.setStyleSheet("font-size: 12px; color: #2e7d32;")
        else:
            self.lbl_status.setText("● ERROR")
            self.lbl_status.setStyleSheet("font-size: 12px; color: #e53935;")

    def _toggle_recording(self):
        if self.waveform.is_recording:
            self.waveform.stop_recording()
            self._rec_timer.stop()
            self.btn_rec.setText("⏺ Bắt đầu ghi")
            self.lbl_rec_time.setText("")
        else:
            data_path, peak_path = self.waveform.start_recording(self._subject_name)
            self._rec_t0 = time.perf_counter()
            self._rec_timer.start(1000)
            self.btn_rec.setText("⏹ Dừng ghi")
            print(f"[REC] Bat dau ghi: {data_path}")

    def _update_rec_time(self):
        if self._rec_t0 is None:
            return
        elapsed = int(time.perf_counter() - self._rec_t0)
        m, s = divmod(elapsed, 60)
        self.lbl_rec_time.setText(f"● REC {m:02d}:{s:02d}")

    def _on_finish(self):
        if self.waveform.is_recording:
            self.waveform.stop_recording()
        self._rec_timer.stop()
        self.waveform.stop()
        self.back_requested.emit()

    def reset(self):
        """Gọi khi rời màn hình, đảm bảo lần sau vào lại sạch."""
        self.lbl_bpm.setText("---")
        self.lbl_status.setText("● CONNECTING")
        self.lbl_rec_time.setText("")
        self.btn_rec.setText("⏺ Bắt đầu ghi")


class EcgRecordingView(QWidget):
    # MainWindow lắng nghe signal này để quay lại ModeSelectView
    back_to_menu = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.stack = QStackedWidget()
        self.name_page = _NameEntryPage()
        self.streaming_page = _StreamingPage()

        self.name_page.start_requested.connect(self._start_streaming)
        self.name_page.back_requested.connect(self.back_to_menu.emit)
        self.streaming_page.back_requested.connect(self._on_streaming_finished)

        self.stack.addWidget(self.name_page)
        self.stack.addWidget(self.streaming_page)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

    def _start_streaming(self, subject_name: str):
        self.stack.setCurrentWidget(self.streaming_page)
        self.streaming_page.start_streaming(subject_name)

    def _on_streaming_finished(self):
        self.streaming_page.reset()
        self.name_page.clear()
        self.stack.setCurrentWidget(self.name_page)
        self.back_to_menu.emit()

    def reset(self):
        """MainWindow gọi khi cần đảm bảo quay vào lại từ đầu (page nhập tên)."""
        self.stack.setCurrentWidget(self.name_page)
