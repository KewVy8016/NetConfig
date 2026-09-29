# อ่านพอร์ต Serial จากระบบปฏิบัติการของเครื่องที่รัน backend
# ใช้ข้อมูลชื่อพอร์ตและคำอธิบายเพื่อช่วยเลือกสาย USB console

from __future__ import annotations

import re

from serial.tools import list_ports

from backend.models import SerialPortOption


def list_serial_ports() -> list[SerialPortOption]:
    """คืนพอร์ต COM/tty ที่ต่ออยู่ โดยเรียง USB ก่อนและไม่เปิดพอร์ตใช้งาน

    Returns:
        รายการพอร์ตและคำอธิบายจากระบบปฏิบัติการ; ว่างเมื่อไม่พบพอร์ต

    Raises:
        Exception: ระบบปฏิบัติการหรือไดรเวอร์อ่านรายการพอร์ตไม่สำเร็จ
    """
    found: list[SerialPortOption] = []
    for info in list_ports.comports():
        if not re.fullmatch(r"COM\d+|/dev/tty\w+", info.device, re.IGNORECASE):
            continue
        description = info.description or info.device
        hardware_id = info.hwid or ""
        is_usb = info.vid is not None or "USB" in hardware_id.upper() or "USB" in description.upper()
        found.append(SerialPortOption(port=info.device, description=description, is_usb=is_usb))

    def sort_key(item: SerialPortOption) -> tuple[bool, int, str]:
        """เรียง USB ก่อน แล้วเรียงหมายเลข COM ตามลำดับตัวเลข"""
        match = re.fullmatch(r"COM(\d+)", item.port, re.IGNORECASE)
        return (not item.is_usb, int(match.group(1)) if match else 1_000_000, item.port)

    return sorted(found, key=sort_key)
