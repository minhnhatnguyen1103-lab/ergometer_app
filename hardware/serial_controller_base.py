"""
hardware/serial_controller_base.py
--------------------------------------
Interface trừu tượng cho việc giao tiếp với board điều khiển phanh
(Arduino thay thế board gốc GENUS-249). SessionManager chỉ nói chuyện
với interface này — không quan tâm bên dưới là MockSerialController
(giả lập, dùng bây giờ) hay RealSerialController (dùng khi firmware
Arduino xong).

Đổi giữa Mock <-> Real chỉ là đổi 1 dòng khởi tạo, không sửa logic
điều khiển ở SessionManager/FuzzyController.
"""

from abc import ABC, abstractmethod


class SerialControllerBase(ABC):
    @abstractmethod
    def connect(self) -> bool:
        """Thử kết nối. Trả về True nếu thành công."""
        raise NotImplementedError

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def send_level(self, level: int) -> bool:
        """Gửi lệnh đổi sang level (1-16). Trả về True nếu lệnh được gửi
        thành công (KHÔNG có nghĩa là motor đã tới nơi ngay — xem
        current_level để biết vị trí thực tế)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def current_level(self) -> int:
        """Level thực tế hiện tại của motor (có thể khác target_level
        nếu đang trong quá trình di chuyển)."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError
