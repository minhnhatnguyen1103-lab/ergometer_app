"""
hardware/mock_serial_controller.py
--------------------------------------
Giả lập board điều khiển phanh. Dùng cho toàn bộ phát triển/test hiện
tại (chưa có Arduino thật đã thay board GENUS-249). Mô phỏng độ trễ
motor di chuyển giữa các level bằng thời gian thực (time.monotonic),
KHÔNG tức thời — để SessionManager/FuzzyController code đúng theo thực
tế, dễ chuyển sang RealSerialController sau này mà không cần sửa logic.
"""

import time

from hardware.serial_controller_base import SerialControllerBase
from core import config


class MockSerialController(SerialControllerBase):
    def __init__(self, fail_first_n_attempts: int = 0,
                 level_change_delay_sec: float | None = None):
        """
        fail_first_n_attempts: so lan connect() dau tien se THAT BAI co
            y (dung de test man hinh ArduinoCheckView / nut Retry).
            Mac dinh 0 = luon thanh cong ngay lan dau (dung khi chi can
            chay demo xuyen suot).
        level_change_delay_sec: ghi de thoi gian mo phong doi level,
            mac dinh lay tu config.MOCK_LEVEL_CHANGE_DELAY_SEC.
        """
        self._fail_first_n = fail_first_n_attempts
        self._connect_attempts = 0
        self._connected = False
        self._delay = level_change_delay_sec if level_change_delay_sec is not None \
            else config.MOCK_LEVEL_CHANGE_DELAY_SEC

        self._current_level = config.LEVEL_MIN
        self._target_level = config.LEVEL_MIN
        self._move_start_t = 0.0
        self._move_start_level = config.LEVEL_MIN

    def connect(self) -> bool:
        self._connect_attempts += 1
        if self._connect_attempts <= self._fail_first_n:
            self._connected = False
            return False
        self._connected = True
        return True

    @property
    def is_connected(self) -> bool:
        return self._connected

    def send_level(self, level: int) -> bool:
        if not self._connected:
            return False
        level = max(config.LEVEL_MIN, min(config.LEVEL_MAX, level))
        if level == self._target_level:
            return True
        self._update_current_level()  # chot vi tri hien tai truoc khi doi target moi
        self._move_start_level = self._current_level
        self._move_start_t = time.monotonic()
        self._target_level = level
        return True

    @property
    def current_level(self) -> int:
        self._update_current_level()
        return self._current_level

    def _update_current_level(self):
        """Mo phong motor di chuyen tuyen tinh theo thoi gian thuc toi target."""
        if self._current_level == self._target_level:
            return
        elapsed = time.monotonic() - self._move_start_t
        if elapsed >= self._delay:
            self._current_level = self._target_level
        # Neu chua toi, cu giu nguyen _current_level = _move_start_level
        # (mo phong don gian: nhay thang khi du thoi gian, khong noi suy
        # tung buoc nho - du chi tiet cho SessionManager/UI hien thi dung)

    def disconnect(self) -> None:
        self._connected = False
