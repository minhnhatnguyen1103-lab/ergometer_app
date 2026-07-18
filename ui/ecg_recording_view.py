"""Standalone ECG streaming and recording workflow."""

import os
import time

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from ui.waveform_view import WaveformView
from ui.widgets import Card, StatusBadge, metric_card, page_header, set_variant


class _NameEntryPage(QWidget):
    start_requested = pyqtSignal(str)
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(64, 46, 64, 42)
        layout.setSpacing(20)
        layout.addWidget(page_header(
            "BIOPAC MP36 · REAL-TIME ACQUISITION",
            "ECG Recording",
            "Theo dõi ECG, nhịp tim và ghi đồng thời tín hiệu đã lọc cùng vị trí R-peak.",
        ))

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 22, 24, 24)
        card_layout.setSpacing(12)
        heading = QLabel("THÔNG TIN BẢN GHI")
        heading.setObjectName("sectionTitle")
        note = QLabel("Tên được dùng trong filename; ký tự không an toàn sẽ tự động được loại bỏ.")
        note.setObjectName("pageSubtitle")
        note.setWordWrap(True)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Tên hoặc mã đối tượng")
        card_layout.addWidget(heading)
        card_layout.addWidget(note)
        card_layout.addSpacing(8)
        card_layout.addWidget(QLabel("Tên đối tượng"))
        card_layout.addWidget(self.name_input)
        layout.addWidget(card, 1)

        actions = QHBoxLayout()
        btn_back = QPushButton("← Về menu")
        set_variant(btn_back, "ghost")
        btn_back.clicked.connect(self.back_requested.emit)
        btn_start = QPushButton("Mở live monitor  →")
        set_variant(btn_start, "primary")
        btn_start.clicked.connect(self._on_start)
        actions.addWidget(btn_back)
        actions.addStretch()
        actions.addWidget(btn_start)
        layout.addLayout(actions)

    def _on_start(self):
        self.start_requested.emit(self.name_input.text().strip() or "subject")

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
        self._saved_timer = QTimer(self)
        self._saved_timer.setSingleShot(True)
        self._saved_timer.timeout.connect(self._hide_saved)
        self._rec_t0 = None
        self._subject_name = "subject"
        self._last_data_path = None
        self._last_peak_path = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(page_header(
            "ECG MONITOR · 1000 HZ",
            "Live acquisition",
            "Giám sát chất lượng tín hiệu trước và trong khi ghi.",
        ), 1)
        self.lbl_status = StatusBadge("● CONNECTING", "warning")
        header.addWidget(self.lbl_status)
        layout.addLayout(header)

        top = QHBoxLayout()
        top.setSpacing(12)
        subject_card = Card(metric=True)
        subject_layout = QVBoxLayout(subject_card)
        subject_layout.setContentsMargins(14, 12, 14, 12)
        subject_label = QLabel("ĐỐI TƯỢNG")
        subject_label.setObjectName("eyebrow")
        self.lbl_name = QLabel("")
        self.lbl_name.setObjectName("sectionTitle")
        subject_layout.addWidget(subject_label)
        subject_layout.addWidget(self.lbl_name)
        bpm_card, self.lbl_bpm = metric_card("Nhịp tim", "—", "BPM", compact=True)
        rec_card, self.lbl_rec_time = metric_card("Recording", "IDLE", "", compact=True)
        top.addWidget(subject_card, 2)
        top.addWidget(bpm_card, 1)
        top.addWidget(rec_card, 1)
        layout.addLayout(top)

        self.lbl_saved = QLabel("")
        self.lbl_saved.setObjectName("successBanner")
        self.lbl_saved.setWordWrap(True)
        self.lbl_saved.hide()
        layout.addWidget(self.lbl_saved)

        plot_card = Card(object_name="plotCard")
        plot_layout = QVBoxLayout(plot_card)
        plot_layout.setContentsMargins(10, 10, 10, 10)
        plot_layout.addWidget(self.waveform)
        layout.addWidget(plot_card, 1)

        controls = QHBoxLayout()
        btn_finish = QPushButton("← Kết thúc và về menu")
        set_variant(btn_finish, "ghost")
        btn_finish.clicked.connect(self._on_finish)
        self.btn_rec = QPushButton("● Bắt đầu ghi")
        set_variant(self.btn_rec, "primary")
        self.btn_rec.clicked.connect(self._toggle_recording)
        controls.addWidget(btn_finish)
        controls.addStretch()
        controls.addWidget(self.btn_rec)
        layout.addLayout(controls)

    def start_streaming(self, subject_name: str):
        self._subject_name = subject_name
        self.lbl_name.setText(subject_name)
        self.waveform.start()

    def _on_hr_updated(self, bpm: float):
        self.lbl_bpm.setText(f"{bpm:.0f}")

    def _on_status_changed(self, is_connected: bool, is_demo: bool):
        if is_demo:
            self.lbl_status.set_status("● DEMO SIGNAL", "demo")
        elif is_connected:
            self.lbl_status.set_status("● LIVE · MP36", "live")
        else:
            self.lbl_status.set_status("● SIGNAL ERROR", "error")

    def _toggle_recording(self):
        if self.waveform.is_recording:
            self.waveform.stop_recording()
            self._rec_timer.stop()
            self.btn_rec.setText("● Bắt đầu ghi")
            set_variant(self.btn_rec, "primary")
            self.lbl_rec_time.setText("IDLE")
            self._notify_saved()
        else:
            data_path, peak_path = self.waveform.start_recording(self._subject_name)
            self._last_data_path = data_path
            self._last_peak_path = peak_path
            self._rec_t0 = time.perf_counter()
            self._rec_timer.start(1000)
            self.btn_rec.setText("■ Dừng và lưu")
            set_variant(self.btn_rec, "danger")
            self.lbl_rec_time.setText("REC 00:00")
            print(f"[REC] Bat dau ghi: {data_path}")

    def _notify_saved(self):
        if not self._last_data_path:
            return
        self.lbl_saved.setText(
            "✓ Đã lưu bản ghi vào recordings/  ·  "
            f"{os.path.basename(self._last_data_path)}  ·  "
            f"{os.path.basename(self._last_peak_path or '')}"
        )
        self.lbl_saved.show()
        self._saved_timer.start(8000)

    def _hide_saved(self):
        self.lbl_saved.hide()

    def _update_rec_time(self):
        if self._rec_t0 is None:
            return
        minutes, seconds = divmod(int(time.perf_counter() - self._rec_t0), 60)
        self.lbl_rec_time.setText(f"REC {minutes:02d}:{seconds:02d}")

    def _on_finish(self):
        if self.waveform.is_recording:
            self.waveform.stop_recording()
        self._rec_timer.stop()
        self.waveform.stop()
        self.back_requested.emit()

    def reset(self):
        self._saved_timer.stop()
        self.lbl_saved.hide()
        self.lbl_bpm.setText("—")
        self.lbl_status.set_status("● CONNECTING", "warning")
        self.lbl_rec_time.setText("IDLE")
        self.btn_rec.setText("● Bắt đầu ghi")
        set_variant(self.btn_rec, "primary")


class EcgRecordingView(QWidget):
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

    def _start_streaming(self, subject_name: str):
        self.stack.setCurrentWidget(self.streaming_page)
        self.streaming_page.start_streaming(subject_name)

    def _on_streaming_finished(self):
        self.streaming_page.reset()
        self.name_page.clear()
        self.stack.setCurrentWidget(self.name_page)
        self.back_to_menu.emit()

    def reset(self):
        self.stack.setCurrentWidget(self.name_page)
