"""
ui/session_view.py
----------------------
M4 theo docsclaude/IMPLEMENTATION_PLAN.md muc 3.4: man hinh MICT that - noi
ky thuat vien theo doi buoi tap. CHI hien thi + nhan input (nut STOP); moi
logic dieu khien nam o control/session_manager.py.

SessionView SO HUU WaveformView (chay ECG realtime, cung cap .cur_bpm lam
nguon HR cho SessionManager). SessionManager duoc TAO BEN NGOAI (main_window
wiring M9, hoac test) roi truyen vao qua begin() - vi SessionManager can
tham chieu waveform lam hr_source, nen nguoi tao phai lay session_view.waveform
truoc. SessionView chi subscribe signal cua manager de cap nhat nhan, khong
tu ra quyet dinh gi.

Luong: begin(session_manager) -> ket noi signal, waveform.start(), manager.start()
-> chay 3 pha -> session_finished -> hien tong ket -> phat session_closed cho
main_window quay ve menu.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from ui.waveform_view import WaveformView

_PHASE_LABEL_VI = {
    "WARMUP": "Khởi động",
    "MAIN": "Chính (Fuzzy)",
    "COOLDOWN": "Hạ nhiệt",
    "DONE": "Hoàn tất",
}


class SessionView(QWidget):
    # main_window lang nghe de quay ve ModeSelectView sau khi session xong/dung
    session_closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.manager = None
        self._patient_name = ""
        self.waveform = WaveformView()
        self._build_ui()

    # ─── UI ───────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Header: ten + pha + dong ho
        header = QHBoxLayout()
        self.lbl_name = QLabel("")
        self.lbl_name.setStyleSheet("font-size: 15px; font-weight: 500;")
        self.lbl_phase = QLabel("—")
        self.lbl_phase.setStyleSheet("font-size: 14px; color: #1565c0; font-weight: 500;")
        self.lbl_clock = QLabel("00:00 / 30:00")
        self.lbl_clock.setStyleSheet("font-size: 14px; color: #424242;")
        header.addWidget(self.lbl_name)
        header.addStretch()
        header.addWidget(self.lbl_phase)
        header.addSpacing(20)
        header.addWidget(self.lbl_clock)

        # Metrics: HR lon + vung muc tieu + level
        metrics = QHBoxLayout()
        self.lbl_hr = QLabel("---")
        self.lbl_hr.setStyleSheet("font-size: 44px; font-weight: 600; color: #616161;")
        hr_unit = QLabel("BPM")
        hr_unit.setStyleSheet("font-size: 12px; color: gray; padding-top: 22px;")
        self.lbl_zone = QLabel("Mục tiêu: —")
        self.lbl_zone.setStyleSheet("font-size: 13px; color: #616161;")
        metrics.addWidget(self.lbl_hr)
        metrics.addWidget(hr_unit)
        metrics.addSpacing(24)
        metrics.addWidget(self.lbl_zone)
        metrics.addStretch()

        self.lbl_level = QLabel("Mức tải: —")
        self.lbl_level.setStyleSheet("font-size: 20px; font-weight: 600;")
        metrics.addWidget(self.lbl_level)

        # Nhan nho manual_override (an mac dinh)
        self.lbl_override = QLabel("")
        self.lbl_override.setStyleSheet("font-size: 12px; color: #e65100;")
        self.lbl_override.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Banner canh bao (an mac dinh)
        self.lbl_banner = QLabel("")
        self.lbl_banner.setStyleSheet(
            "font-size: 13px; color: white; background-color: #e53935; padding: 6px; border-radius: 4px;"
        )
        self.lbl_banner.hide()

        # Log su kien cuon
        self.log_list = QListWidget()
        self.log_list.setStyleSheet("font-size: 12px;")
        self.log_list.setMaximumHeight(140)

        # Nut STOP an toan
        self.btn_stop = QPushButton("■ DỪNG (về mức nhẹ nhất, kết thúc)")
        self.btn_stop.setMinimumHeight(48)
        self.btn_stop.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: white; background-color: #c62828;"
        )
        self.btn_stop.clicked.connect(self._on_stop_clicked)

        layout.addLayout(header)
        layout.addLayout(metrics)
        layout.addWidget(self.lbl_override)
        layout.addWidget(self.lbl_banner)
        layout.addWidget(self.waveform, stretch=1)
        layout.addWidget(QLabel("Nhật ký sự kiện:"))
        layout.addWidget(self.log_list)
        layout.addWidget(self.btn_stop)
        self.setLayout(layout)

    # ─── Ket noi & khoi dong ─────────────────────────────────────

    def begin(self, session_manager, patient_name: str = ""):
        """Nhan SessionManager da tao san (voi hr_source = self.waveform),
        ket noi signal, roi bat dau ca waveform lan phien tap."""
        self.manager = session_manager
        self._patient_name = patient_name
        self.lbl_name.setText(f"Đối tượng: {patient_name}" if patient_name else "")

        zone = session_manager.zone
        self.lbl_zone.setText(f"Mục tiêu: {zone.thr_low:.0f}–{zone.thr_high:.0f} BPM")

        self.lbl_banner.hide()
        self.lbl_override.setText("")
        self.log_list.clear()
        self.btn_stop.setEnabled(True)

        session_manager.hr_updated.connect(self._on_hr)
        session_manager.level_changed.connect(self._on_level)
        session_manager.phase_changed.connect(self._on_phase)
        session_manager.tick.connect(self._on_tick)
        session_manager.cadence_warning.connect(self._on_cadence_warning)
        session_manager.safety_event.connect(self._on_safety_event)
        session_manager.session_finished.connect(self._on_finished)

        self.waveform.start()
        session_manager.start()

    # ─── Cap nhat tu signal (chi hien thi) ───────────────────────

    def _on_hr(self, hr: float):
        self.lbl_hr.setText(f"{hr:.0f}")
        in_zone = self.manager.zone.contains(hr) if self.manager else False
        color = "#2e7d32" if in_zone else "#e53935"
        self.lbl_hr.setStyleSheet(f"font-size: 44px; font-weight: 600; color: {color};")

    def _on_level(self, level: int, reason: str):
        self.lbl_level.setText(f"Mức tải: {level}")
        if reason == "manual_override":
            self.lbl_override.setText("⚠ Vừa chỉnh tay bằng nút bấm vật lý")
        elif reason == "fuzzy":
            self.lbl_override.setText("")
        self._append_log(f"Level → {level}  ({reason})")

    def _on_phase(self, phase: str):
        self.lbl_phase.setText(_PHASE_LABEL_VI.get(phase, phase))
        self._append_log(f"── Pha: {_PHASE_LABEL_VI.get(phase, phase)} ──")

    def _on_tick(self, elapsed_sec: int, remaining_sec: int):
        em, es = divmod(max(0, elapsed_sec), 60)
        total = elapsed_sec + remaining_sec
        tm, ts = divmod(max(0, total), 60)
        self.lbl_clock.setText(f"{em:02d}:{es:02d} / {tm:02d}:{ts:02d}")

    def _on_cadence_warning(self, rpm: float):
        self._show_banner(f"Nhịp đạp {rpm:.0f} RPM ngoài khoảng 60–70 — nhắc đối tượng giữ đều nhịp")
        self._append_log(f"⚠ Cadence {rpm:.0f} RPM ngoài 60–70")

    def _on_safety_event(self, kind: str):
        msg = {
            "hr_stale_short": "Mất tín hiệu nhịp tim ngắn — giữ nguyên mức tải, kiểm tra điện cực",
            "hr_stale_long": "Mất tín hiệu nhịp tim kéo dài — tự động về mức nhẹ nhất",
        }.get(kind, kind)
        self._show_banner(msg)
        self._append_log(f"⚠ An toàn: {kind}")

    def _on_finished(self, summary: dict):
        self.waveform.stop()
        # Hoan modal tong ket sang vong lap su kien KE TIEP: _on_finished duoc
        # goi DONG BO tu trong SessionManager.stop()/_on_tick (callback cua QTimer).
        # Mo QMessageBox ngay tai day se chan callback timer dang chay va gay
        # tai nhap (deadlock voi cac timer khac). singleShot(0) cho chuoi stop()
        # thoat het roi moi hien tong ket tren stack sach.
        QTimer.singleShot(0, lambda: self._present_summary(summary))

    def _present_summary(self, summary: dict):
        hrr1 = summary.get("hrr1")
        hrr1_txt = f"{hrr1:.1f} bpm" if hrr1 is not None else "không đủ dữ liệu"
        QMessageBox.information(
            self, "Kết thúc buổi tập",
            f"Buổi tập đã kết thúc ({summary.get('stop_reason', '')}).\n\n"
            f"HR cuối pha chính: {self._fmt(summary.get('hr_end_main'))} bpm\n"
            f"HR sau 1 phút hồi phục: {self._fmt(summary.get('hr_at_1min_post'))} bpm\n"
            f"HRR1 (hồi phục nhịp tim): {hrr1_txt}\n\n"
            "Dữ liệu đã được lưu vào thư mục recordings/.",
        )
        self.session_closed.emit()

    # ─── Nut STOP ─────────────────────────────────────────────────

    def _on_stop_clicked(self):
        if not self.manager:
            self.session_closed.emit()
            return
        reply = QMessageBox.question(
            self, "Dừng buổi tập?",
            "Dừng buổi tập ngay bây giờ? Mức tải sẽ về nhẹ nhất và buổi tập kết thúc.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.btn_stop.setEnabled(False)
            self.manager.stop("user")  # -> session_finished -> _on_finished -> session_closed

    # ─── Tien ich ─────────────────────────────────────────────────

    @staticmethod
    def _fmt(v):
        return f"{v:.0f}" if isinstance(v, (int, float)) else "—"

    def _append_log(self, text: str):
        self.log_list.addItem(text)
        self.log_list.scrollToBottom()

    def _show_banner(self, text: str):
        self.lbl_banner.setText(text)
        self.lbl_banner.show()
