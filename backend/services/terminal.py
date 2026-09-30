# บริการ CLI แบบ session ชั่วคราวสำหรับอุปกรณ์ Cisco IOS
# เปิด connection ต่อแท็บเดียว ส่งทีละบรรทัด และปิดเมื่อผู้ใช้เลิกใช้งาน

from __future__ import annotations

from typing import Any

from netmiko import ConnectHandler

from backend.models import SerialConfig, SSHConfig, TelnetConfig
from backend.services.connection import build_device_dict
from backend.services.encryption import redact_text


def open_terminal(config: SSHConfig | TelnetConfig | SerialConfig) -> Any:
    """เปิด Netmiko session จากข้อมูล Node และคืน connection สำหรับ CLI ชั่วคราว"""
    return ConnectHandler(**build_device_dict(config))


def terminal_prompt(connection: Any) -> str:
    """อ่าน prompt ปัจจุบันจาก session ที่เชื่อมต่อแล้ว"""
    return redact_text(connection.find_prompt())


def send_terminal_line(connection: Any, command: str) -> tuple[str, str]:
    """ส่ง CLI หนึ่งบรรทัดใน session เดิมและคืน output กับ prompt ปัจจุบัน"""
    output = connection.send_command_timing(
        command, strip_command=True, strip_prompt=True, read_timeout=20,
    )
    safe_output = redact_text(output)
    if safe_output.rstrip().lower().endswith("password:"):
        return safe_output, "Password:"
    return safe_output, terminal_prompt(connection)


def close_terminal(connection: Any) -> None:
    """ปิด session Netmiko หลังผู้ใช้ Disconnect หรือ socket หลุด"""
    connection.disconnect()
