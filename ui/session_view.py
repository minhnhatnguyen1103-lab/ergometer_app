"""Live MICT dashboard. Control logic remains entirely in SessionManager."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from ui.waveform_view import WaveformView
from ui.widgets import (
    Card, StatusBadge, ZoneBar, metric_card, page_header, repolish, set_variant,
)

_PHASE_LABEL_VI = {
    "WARMUP": "KHỞI ĐỘNG",
    "MAIN": "PHA CHÍNH · FUZZY",
    "COOLDOWN": "HẠ NHIỆT",
    "DONE": "HOÀN TẤT",
}

_STOP_REASON_VI = {
    "completed": "Hoàn thành protocol",
    "user": "Dừng bởi người vận hành",
    "safety": "Dừng bởi safety layer",
}


class SessionView(QWidget):
    session_closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.manager = None
        self._patient_name = ""
        self._has_real_log = False
        self.waveform = WaveformView()
        self.waveform.status_changed.connect(self._on_signal_status)
        self._build_ui()

    def _build_ui(self):
        self.pages = QStackedWidget()
        self.live_page = self._build_live_page()
        self.summary_page = self._build_summary_page()
        self.pages.addWidget(self.live_page)
        self.pages.addWidget(self.summary_page)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pages)

    def _build_live_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(11)

        header = QHBoxLayout()
        self.lbl_name = QLabel("")
        self.lbl_name.setObjectName("sectionTitle")
        self.signal_badge = StatusBadge("● CONNECTING", "warning")
        self.lbl_phase = QLabel("CHỜ BẮT ĐẦU")
        self.lbl_phase.setObjectName("phaseChip")
        self.lbl_phase.setProperty("phase", "WARMUP")
        self.lbl_clock = QLabel("00:00 / 30:00")
        self.lbl_clock.setObjectName("clock")
        header.addWidget(self.lbl_name)
        header.addSpacing(10)
        header.addWidget(self.signal_badge)
        header.addStretch()
        header.addWidget(self.lbl_phase)
        header.addSpacing(12)
        header.addWidget(self.lbl_clock)
        layout.addLayout(header)

        self.lbl_banner = QLabel("")
        self.lbl_banner.setObjectName("alertBanner")
        self.lbl_banner.setWordWrap(True)
        self.lbl_banner.hide()
        layout.addWidget(self.lbl_banner)

        body = QHBoxLayout()
        body.setSpacing(12)

        self.hr_card = Card(object_name="hrHero")
        self.hr_card.setProperty("zoneState", "idle")
        self.hr_card.setMinimumWidth(280)
        hr_layout = QVBoxLayout(self.hr_card)
        hr_layout.setContentsMargins(22, 18, 22, 18)
        hr_layout.setSpacing(8)
        hr_heading = QLabel("LIVE HEART RATE")
        hr_heading.setObjectName("eyebrow")
        self.lbl_hr = QLabel("---")
        self.lbl_hr.setObjectName("hrValue")
        self.lbl_hr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bpm = QLabel("BPM")
        bpm.setObjectName("metricUnit")
        bpm.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_zone = QLabel("Mục tiêu: —")
        self.lbl_zone.setObjectName("pageSubtitle")
        self.lbl_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zone_bar = ZoneBar()
        self.lbl_level = QLabel("Mức tải: —")
        self.lbl_level.setObjectName("metricValue")
        self.lbl_level.setProperty("compact", True)
        self.lbl_level.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_override = QLabel("")
        self.lbl_override.setObjectName("mutedText")
        self.lbl_override.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_override.setWordWrap(True)
        hr_layout.addWidget(hr_heading)
        hr_layout.addStretch()
        hr_layout.addWidget(self.lbl_hr)
        hr_layout.addWidget(bpm)
        hr_layout.addWidget(self.lbl_zone)
        hr_layout.addWidget(self.zone_bar)
        hr_layout.addSpacing(8)
        hr_layout.addWidget(self.lbl_level)
        hr_layout.addWidget(self.lbl_override)
        hr_layout.addStretch()
        body.addWidget(self.hr_card, 1)

        right = QVBoxLayout()
        plot_card = Card(object_name="plotCard")
        plot_layout = QVBoxLayout(plot_card)
        plot_layout.setContentsMargins(9, 9, 9, 9)
        plot_layout.addWidget(self.waveform)
        right.addWidget(plot_card, 3)

        log_card = Card()
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(12, 10, 12, 12)
        log_header = QHBoxLayout()
        log_title = QLabel("NHẬT KÝ SỰ KIỆN")
        log_title.setObjectName("eyebrow")
        log_header.addWidget(log_title)
        log_header.addStretch()
        log_header.addWidget(StatusBadge("AUTO-SCROLL", "neutral"))
        self.log_list = QListWidget()
        self.log_list.setMaximumHeight(130)
        log_layout.addLayout(log_header)
        log_layout.addWidget(self.log_list)
        right.addWidget(log_card, 1)
        body.addLayout(right, 3)
        layout.addLayout(body, 1)

        self.btn_stop = QPushButton("■  DỪNG AN TOÀN  ·  VỀ MỨC NHẸ NHẤT VÀ KẾT THÚC PHIÊN")
        self.btn_stop.setMinimumHeight(54)
        set_variant(self.btn_stop, "danger")
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self.btn_stop)
        return page

    def _build_summary_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(48, 34, 48, 34)
        layout.setSpacing(18)
        layout.addWidget(page_header(
            "SESSION COMPLETE · DATA SAVED",
            "Tổng kết buổi tập",
            "Các chỉ số hồi phục được lấy từ SessionManager và đã lưu cùng dữ liệu phiên.",
        ))

        self.lbl_summary_reason = StatusBadge("HOÀN TẤT", "live")
        layout.addWidget(self.lbl_summary_reason, 0, Qt.AlignmentFlag.AlignLeft)
        metrics = QHBoxLayout()
        end_card, self.lbl_summary_end = metric_card("HR cuối pha chính", "—", "BPM")
        post_card, self.lbl_summary_post = metric_card("HR sau 1 phút", "—", "BPM")
        hrr_card, self.lbl_summary_hrr = metric_card("HRR1", "—", "BPM")
        metrics.addWidget(end_card)
        metrics.addWidget(post_card)
        metrics.addWidget(hrr_card)
        layout.addLayout(metrics, 1)

        save_card = Card()
        save_layout = QVBoxLayout(save_card)
        save_layout.setContentsMargins(18, 16, 18, 16)
        save_title = QLabel("DỮ LIỆU PHIÊN")
        save_title.setObjectName("eyebrow")
        self.lbl_summary_path = QLabel("")
        self.lbl_summary_path.setObjectName("monoText")
        self.lbl_summary_path.setWordWrap(True)
        save_layout.addWidget(save_title)
        save_layout.addWidget(self.lbl_summary_path)
        layout.addWidget(save_card)

        actions = QHBoxLayout()
        actions.addStretch()
        self.btn_summary_home = QPushButton("Về menu chính  →")
        set_variant(self.btn_summary_home, "primary")
        self.btn_summary_home.clicked.connect(self._close_summary)
        actions.addWidget(self.btn_summary_home)
        layout.addLayout(actions)
        return page

    def begin(self, session_manager, patient_name: str = ""):
        self.manager = session_manager
        self._patient_name = patient_name
        self.pages.setCurrentWidget(self.live_page)
        self.lbl_name.setText(f"ĐỐI TƯỢNG  ·  {patient_name}" if patient_name else "LIVE SESSION")

        zone = session_manager.zone
        self.lbl_zone.setText(f"Mục tiêu: {zone.thr_low:.0f}–{zone.thr_high:.0f} BPM")
        self.zone_bar.set_zone(zone.thr_low, zone.thr_high)
        self.zone_bar.set_value(None)
        self.hr_card.setProperty("zoneState", "idle")
        repolish(self.hr_card)
        self.lbl_hr.setText("---")
        self.lbl_level.setText("Mức tải: —")
        self.lbl_banner.hide()
        self.lbl_override.setText("")
        self.log_list.clear()
        self.log_list.addItem("Chưa có sự kiện")
        self._has_real_log = False
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

    def _on_signal_status(self, is_connected: bool, is_demo: bool):
        if is_demo:
            self.signal_badge.set_status("● DEMO SIGNAL", "demo")
        elif is_connected:
            self.signal_badge.set_status("● LIVE · MP36", "live")
        else:
            self.signal_badge.set_status("● SIGNAL ERROR", "error")

    def _on_hr(self, hr: float):
        self.lbl_hr.setText(f"{hr:.0f}")
        in_zone = self.manager.zone.contains(hr) if self.manager else False
        self.hr_card.setProperty("zoneState", "in" if in_zone else "out")
        repolish(self.hr_card)
        self.zone_bar.set_value(hr)

    def _on_level(self, level: int, reason: str):
        self.lbl_level.setText(f"Mức tải: {level}")
        if reason == "manual_override":
            self.lbl_override.setText("⚠ Đã chỉnh tay bằng nút bấm vật lý")
        elif reason == "fuzzy":
            self.lbl_override.setText("")
        self._append_log(f"Level → {level}  ({reason})")

    def _on_phase(self, phase: str):
        self.lbl_phase.setText(_PHASE_LABEL_VI.get(phase, phase))
        self.lbl_phase.setProperty("phase", phase)
        repolish(self.lbl_phase)
        self._append_log(f"── Pha: {_PHASE_LABEL_VI.get(phase, phase)} ──")

    def _on_tick(self, elapsed_sec: int, remaining_sec: int):
        elapsed_minutes, elapsed_seconds = divmod(max(0, elapsed_sec), 60)
        total_minutes, total_seconds = divmod(max(0, elapsed_sec + remaining_sec), 60)
        self.lbl_clock.setText(
            f"{elapsed_minutes:02d}:{elapsed_seconds:02d} / {total_minutes:02d}:{total_seconds:02d}"
        )

    def _on_cadence_warning(self, rpm: float):
        self._show_banner(
            f"Nhịp đạp {rpm:.0f} RPM ngoài khoảng 60–70 · nhắc đối tượng giữ đều nhịp",
            danger=False,
        )
        self._append_log(f"⚠ Cadence {rpm:.0f} RPM ngoài 60–70")

    def _on_safety_event(self, kind: str):
        message = {
            "hr_stale_short": "Mất tín hiệu HR ngắn · giữ nguyên mức tải và kiểm tra điện cực",
            "hr_stale_long": "Mất tín hiệu HR kéo dài · đã tự động về mức nhẹ nhất",
        }.get(kind, kind)
        self._show_banner(message, danger=True)
        self._append_log(f"⚠ An toàn: {kind}")

    def _on_finished(self, summary: dict):
        self.waveform.stop()
        self._present_summary(summary)

    def _present_summary(self, summary: dict):
        self.lbl_summary_reason.set_status(
            _STOP_REASON_VI.get(summary.get("stop_reason"), summary.get("stop_reason", "HOÀN TẤT")),
            "live" if summary.get("stop_reason") == "completed" else "warning",
        )
        self.lbl_summary_end.setText(self._fmt(summary.get("hr_end_main")))
        self.lbl_summary_post.setText(self._fmt(summary.get("hr_at_1min_post")))
        self.lbl_summary_hrr.setText(self._fmt(summary.get("hrr1"), decimals=1))
        path = getattr(getattr(self.manager, "logger", None), "summary_path", "recordings/")
        self.lbl_summary_path.setText(f"Summary: {path}\nTimeseries và event log được lưu cùng thư mục.")
        self.pages.setCurrentWidget(self.summary_page)

    def _close_summary(self):
        self.manager = None
        self.session_closed.emit()

    def _on_stop_clicked(self):
        if not self.manager:
            self.session_closed.emit()
            return
        if self._confirm_stop():
            self.btn_stop.setEnabled(False)
            self.manager.stop("user")

    def _confirm_stop(self) -> bool:
        reply = QMessageBox.question(
            self, "Dừng buổi tập?",
            "Dừng ngay? Mức tải sẽ về nhẹ nhất và dữ liệu hiện có vẫn được lưu.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    @staticmethod
    def _fmt(value, decimals: int = 0):
        return f"{value:.{decimals}f}" if isinstance(value, (int, float)) else "—"

    def _append_log(self, text: str):
        if not self._has_real_log:
            self.log_list.clear()
            self._has_real_log = True
        self.log_list.addItem(text)
        self.log_list.scrollToBottom()

    def _show_banner(self, text: str, danger: bool):
        self.lbl_banner.setText(text)
        self.lbl_banner.setProperty("severity", "danger" if danger else "warning")
        repolish(self.lbl_banner)
        self.lbl_banner.show()
