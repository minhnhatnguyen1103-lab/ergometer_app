"""Small reusable presentation widgets used by the PyQt6 views."""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from ui.theme import BORDER, BRAND, DANGER, MUTED, SUCCESS, WARNING


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def set_variant(widget: QWidget, variant: str) -> None:
    widget.setProperty("variant", variant)
    repolish(widget)


class Card(QFrame):
    def __init__(self, parent=None, metric: bool = False, object_name: str | None = None):
        super().__init__(parent)
        self.setObjectName(object_name or ("metricCard" if metric else "card"))


class StatusBadge(QLabel):
    def __init__(self, text: str = "● ĐANG KIỂM TRA", status: str = "neutral", parent=None):
        super().__init__(text, parent)
        self.setObjectName("statusBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.set_status(text, status)

    def set_status(self, text: str, status: str) -> None:
        self.setText(text)
        self.setProperty("status", status)
        repolish(self)


class StepRail(QFrame):
    STEPS = ("Thông tin", "HR nghỉ", "Thiết bị", "Checklist", "Buổi tập")

    def __init__(self, current: int, parent=None):
        super().__init__(parent)
        self.setObjectName("shellRail")
        self.setFixedWidth(190)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 28, 0, 22)
        layout.setSpacing(5)

        brand = QLabel("ERGOMETER\nCONTROL")
        brand.setObjectName("railBrand")
        layout.addWidget(brand)
        layout.addSpacing(28)

        for index, text in enumerate(self.STEPS):
            state = "done" if index < current else "current" if index == current else "upcoming"
            prefix = "✓" if state == "done" else f"{index + 1:02d}"
            label = QLabel(f"{prefix}   {text}")
            label.setObjectName("railStep")
            label.setProperty("state", state)
            layout.addWidget(label)
        layout.addStretch()

        protocol = QLabel("GENUS-249  ·  MICT\nSAFETY FIRST")
        protocol.setObjectName("mutedText")
        layout.addWidget(protocol)


class FeatureButton(QPushButton):
    def __init__(self, icon: str, title: str, description: str, action: str, parent=None):
        super().__init__(f"{icon}   {title}\n\n{description}\n\n{action}  →", parent)
        self.setObjectName("featureCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(title)


class ZoneBar(QWidget):
    """Glanceable current-HR marker around the target zone."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._low = 0.0
        self._high = 1.0
        self._current = None
        self.setMinimumHeight(38)

    def sizeHint(self) -> QSize:
        return QSize(260, 38)

    def set_zone(self, low: float, high: float) -> None:
        self._low, self._high = float(low), float(high)
        self.update()

    def set_value(self, value: float | None) -> None:
        self._current = None if value is None else float(value)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        left, right, y = 8, self.width() - 8, 15
        span = max(1.0, self._high - self._low)
        scale_min, scale_max = self._low - span, self._high + span

        painter.setPen(QPen(QColor(BORDER), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(left, y, right, y)
        zone_left = left + int((self._low - scale_min) / (scale_max - scale_min) * (right - left))
        zone_right = left + int((self._high - scale_min) / (scale_max - scale_min) * (right - left))
        painter.setPen(QPen(QColor(SUCCESS), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(zone_left, y, zone_right, y)

        if self._current is not None:
            ratio = (self._current - scale_min) / (scale_max - scale_min)
            x = left + int(max(0.0, min(1.0, ratio)) * (right - left))
            marker = SUCCESS if self._low <= self._current <= self._high else DANGER
            painter.setBrush(QColor(marker))
            painter.setPen(QPen(QColor("#0B0F14"), 2))
            painter.drawEllipse(x - 6, y - 6, 12, 12)

        painter.setPen(QColor(MUTED))
        painter.drawText(left, 36, f"{self._low:.0f}")
        painter.drawText(right - 30, 36, f"{self._high:.0f}")


def page_header(eyebrow: str, title: str, subtitle: str = "") -> QFrame:
    header = QFrame()
    header.setObjectName("pageHeader")
    layout = QVBoxLayout(header)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    if eyebrow:
        label = QLabel(eyebrow.upper())
        label.setObjectName("eyebrow")
        layout.addWidget(label)
    label = QLabel(title)
    label.setObjectName("pageTitle")
    layout.addWidget(label)
    if subtitle:
        label = QLabel(subtitle)
        label.setObjectName("pageSubtitle")
        label.setWordWrap(True)
        layout.addWidget(label)
    return header


def metric_card(label: str, value: str = "—", unit: str = "", compact: bool = False) -> tuple[Card, QLabel]:
    card = Card(metric=True)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(2)
    label_widget = QLabel(label.upper())
    label_widget.setObjectName("eyebrow")
    value_widget = QLabel(value)
    value_widget.setObjectName("metricValue")
    value_widget.setProperty("compact", compact)
    layout.addWidget(label_widget)
    row = QHBoxLayout()
    row.addWidget(value_widget)
    if unit:
        unit_widget = QLabel(unit)
        unit_widget.setObjectName("metricUnit")
        unit_widget.setAlignment(Qt.AlignmentFlag.AlignBottom)
        row.addWidget(unit_widget)
    row.addStretch()
    layout.addLayout(row)
    return card, value_widget
