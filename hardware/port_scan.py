"""
hardware/port_scan.py
------------------------
Chi lam 1 viec: liet ke cong COM dang co tren may -> tra ve co "co ve
la Arduino" hay khong. KHONG mo ket noi, KHONG gui/nhan lenh gi -
day la ranh gioi truoc "giao tiep dieu khien voi xe" (ArduinoProtocol,
SerialController se lam viec do sau nay, chua lam bay gio).

GHI CHU: hien tai chua biet chinh xac VID/PID cua board Arduino Uno R3
da thay the board goc GENUS-249 (can do dac tren may that). Tam thoi
dung heuristic pho bien (Arduino chinh hang hoac clone dung chip CH340/
CP2102) - can dieu chinh khi co Arduino that de test.
"""

import serial.tools.list_ports

# VID pho bien cua Arduino Uno (chinh hang) va cac chip USB-serial clone
# thuong dung (CH340, CP2102, FTDI)
_KNOWN_VIDS = {0x2341, 0x1A86, 0x10C4, 0x0403}


def list_ports() -> list[dict]:
    """Tra ve toan bo cong COM hien co, kem thong tin de debug."""
    out = []
    for p in serial.tools.list_ports.comports():
        out.append({
            "device": p.device,
            "description": p.description or "",
            "vid": p.vid,
            "pid": p.pid,
        })
    return out


def find_likely_arduino_port() -> str | None:
    """Tra ve ten cong (vd 'COM5') neu tim thay thiet bi giong Arduino,
    None neu khong tim thay cong nao phu hop."""
    for p in list_ports():
        if p["vid"] in _KNOWN_VIDS:
            return p["device"]
    return None
