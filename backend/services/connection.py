# บริการเชื่อมต่ออุปกรณ์ Cisco IOS ผ่าน Netmiko สำหรับ NetConfig
# รันใน threadpool เพื่อไม่ block event loop และใช้ per-node lock ป้องกัน race condition

from __future__ import annotations

import asyncio
import socket
import subprocess
import sys
from collections.abc import Callable
from typing import Any, TypeVar

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)

# Paramiko ถูก pin เป็น 3.x ใน requirements เพื่อรองรับ legacy SSH ของ IOSv lab
from backend.models import (
    ConnectionStep,
    ConnectionStepStatus,
    SerialConfig,
    SSHConfig,
    TelnetConfig,
    TransportType,
)
from backend.services.encryption import decrypt, redact_text

# ---------------------------------------------------------------------------
# Per-node lock registry
# ---------------------------------------------------------------------------

# dict[node_id, asyncio.Lock] — สร้างเมื่อต้องการและเก็บตลอด lifetime ของ process
_node_locks: dict[str, asyncio.Lock] = {}
_lock_registry_lock = asyncio.Lock()


async def get_node_lock(node_id: str) -> asyncio.Lock:
    """คืน asyncio.Lock สำหรับ node_id นั้น สร้างใหม่หากยังไม่มี

    Parameters:
        node_id: ID ของ node ที่ต้องการ lock

    Returns:
        asyncio.Lock เฉพาะของ node นั้น
    """
    async with _lock_registry_lock:
        if node_id not in _node_locks:
            _node_locks[node_id] = asyncio.Lock()
        return _node_locks[node_id]


# ---------------------------------------------------------------------------
# Netmiko device dict builder
# ---------------------------------------------------------------------------

def build_device_dict(
    transport_config: SSHConfig | TelnetConfig | SerialConfig,
) -> dict[str, Any]:
    """แปลง transport config เป็น dict สำหรับ Netmiko ConnectHandler

    Parameters:
        transport_config: config ของ transport ที่เลือก (SSH/Telnet/Serial)

    Returns:
        dict ที่พร้อมส่งให้ ConnectHandler — password ถูก decrypt ณ จุดนี้เท่านั้น

    Raises:
        ValueError: หาก transport type ไม่รู้จัก
    """
    cfg = transport_config

    if isinstance(cfg, SSHConfig):
        return {
            "device_type": "cisco_ios",
            "host": cfg.host,
            "port": cfg.port,
            "username": cfg.username,
            "password": cfg.password,
            "secret": cfg.secret or "",
            # IOSv รุ่นเก่าใน EVE อาจตอบ SSH banner/prompt ช้ากว่า TCP port check มาก
            "conn_timeout": 15,
            "auth_timeout": 30,
            "banner_timeout": 30,
            "blocking_timeout": 30,
            "read_timeout_override": 30,
            "fast_cli": False,
        }

    if isinstance(cfg, TelnetConfig):
        return {
            "device_type": "cisco_ios_telnet",
            "host": cfg.host,
            "port": cfg.port,
            "username": cfg.username,
            "password": cfg.password,
            "secret": cfg.secret or "",
            "timeout": 15,
            "auth_timeout": 15,
        }

    if isinstance(cfg, SerialConfig):
        return {
            "device_type": "cisco_ios_serial",
            "serial_settings": {
                "port": cfg.serial_port,
                "baudrate": cfg.baudrate,
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
            },
            "username": cfg.username,
            "password": cfg.password,
            "secret": cfg.secret or "",
            "timeout": 30,
        }

    raise ValueError(f"transport type ไม่รู้จัก: {type(cfg)}")


def build_transport_from_row(row: dict[str, Any]) -> SSHConfig | TelnetConfig | SerialConfig:
    """สร้าง typed transport config จาก SQLite row โดย decrypt เฉพาะตอนใช้งาน"""
    transport = TransportType(row["transport"])
    username = decrypt(row["enc_username"])
    password = decrypt(row["enc_password"])
    secret = decrypt(row["enc_secret"]) if row.get("enc_secret") else None
    if transport == TransportType.SSH:
        return SSHConfig(host=row["host"], port=row["port"], username=username, password=password, secret=secret)
    if transport == TransportType.TELNET:
        return TelnetConfig(host=row["host"], port=row["port"], username=username, password=password, secret=secret)
    return SerialConfig(
        serial_port=row["serial_port"],
        baudrate=row.get("serial_baudrate") or 9600,
        username=username,
        password=password,
        secret=secret,
    )


# ---------------------------------------------------------------------------
# Async wrappers รอบ blocking Netmiko calls
# ---------------------------------------------------------------------------

T = TypeVar("T")


class EnableSecretRequiredError(RuntimeError):
    """แจ้งว่าอุปกรณ์ถามรหัส enable แต่ Node ยังไม่มี secret ที่ใช้ได้"""


async def _run_in_executor(fn: Callable[[], T]) -> T:
    """รัน blocking function ใน default threadpool โดยไม่ block event loop

    Parameters:
        fn: callable ที่ไม่มี argument (ใช้ lambda หรือ partial)

    Returns:
        ผลลัพธ์จาก fn
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn)


def _ping_host(host: str) -> bool:
    """ส่ง ICMP ping ไปที่ host และคืน True เมื่อ reachable

    Parameters:
        host: IP address หรือ hostname

    Returns:
        True หากตอบสนอง, False หากไม่ตอบ
    """
    param = "-n" if sys.platform.startswith("win") else "-c"
    result = subprocess.run(
        ["ping", param, "1", "-w", "1000", host],
        capture_output=True,
        timeout=5,
    )
    return result.returncode == 0


def _check_port(host: str, port: int) -> bool:
    """ตรวจว่า TCP port เปิดอยู่หรือไม่

    Parameters:
        host: IP address หรือ hostname
        port: TCP port number

    Returns:
        True หาก port เปิด, False หากไม่ได้
    """
    try:
        with socket.create_connection((host, port), timeout=5):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Test connection steps
# ---------------------------------------------------------------------------

async def test_connection(
    node_id: str,
    transport_config: SSHConfig | TelnetConfig | SerialConfig,
) -> list[ConnectionStep]:
    """ทดสอบ connection แบบ step-by-step: Ping → Port → Login → Hostname

    แต่ละขั้นจะ skip ขั้นถัดไปเมื่อล้มเหลว เพื่อไม่ให้ error ซ้อนกัน
    Serial transport ข้าม Ping/Port ไปทดสอบ Login โดยตรง

    Parameters:
        node_id: ID ของ node (ใช้สำหรับ log)
        transport_config: config ของ transport

    Returns:
        รายการ ConnectionStep พร้อม status และ message ภาษาไทย
    """
    steps: list[ConnectionStep] = []
    is_serial = isinstance(transport_config, SerialConfig)

    # --- Step 1: Ping ---
    if not is_serial:
        host = transport_config.host  # type: ignore[union-attr]
        try:
            reachable = await _run_in_executor(lambda: _ping_host(host))
            steps.append(ConnectionStep(
                step="ping",
                status=ConnectionStepStatus.SUCCESS if reachable else ConnectionStepStatus.FAILED,
                message="เครื่อง reachable" if reachable else "ไม่สามารถ ping ได้",
            ))
        except Exception as exc:
            steps.append(ConnectionStep(
                step="ping",
                status=ConnectionStepStatus.FAILED,
                message="ตรวจสอบ ping ไม่ได้",
                detail=redact_text(str(exc)),
            ))
        if steps[-1].status == ConnectionStepStatus.FAILED:
            steps += _skip_remaining(["port", "login", "hostname"])
            return steps
    else:
        steps.append(ConnectionStep(
            step="ping", status=ConnectionStepStatus.SKIPPED, message="ข้าม (Serial)"
        ))

    # --- Step 2: Port ---
    if not is_serial:
        port = transport_config.port  # type: ignore[union-attr]
        try:
            open_port = await _run_in_executor(lambda: _check_port(host, port))
            steps.append(ConnectionStep(
                step="port",
                status=ConnectionStepStatus.SUCCESS if open_port else ConnectionStepStatus.FAILED,
                message=f"Port {port} เปิดอยู่" if open_port else f"Port {port} ปิดหรือ filtered",
            ))
        except Exception as exc:
            steps.append(ConnectionStep(
                step="port",
                status=ConnectionStepStatus.FAILED,
                message="ตรวจ port ไม่ได้",
                detail=redact_text(str(exc)),
            ))
        if steps[-1].status == ConnectionStepStatus.FAILED:
            steps += _skip_remaining(["login", "hostname"])
            return steps
    else:
        steps.append(ConnectionStep(
            step="port", status=ConnectionStepStatus.SKIPPED, message="ข้าม (Serial)"
        ))

    # --- Step 3: Login ---
    device_dict = build_device_dict(transport_config)
    hostname_detected: str | None = None

    def _login_and_read() -> str:
        """ยืนยัน login และอ่าน hostname — รันใน threadpool

        ห้ามเรียก enable ในขั้นทดสอบนี้ เพราะสัญญา API ตรวจเพียง login/hostname
        และ IOS อาจตั้ง enable secret แยกจาก credential ของ SSH/Telnet. การ Apply
        configuration จะเรียก enable ใน send_config_commands ตามเดิม.
        """
        conn = ConnectHandler(**device_dict)
        try:
            # show version ใช้ได้จาก user EXEC mode; ไม่ควรทำให้ login test
            # ล้มเหลวเพียงเพราะไม่ได้กรอก enable secret
            conn.send_command("show version", use_textfsm=False)
            # อ่าน hostname จาก prompt
            hostname = conn.find_prompt().rstrip("#>").strip()
            return hostname
        finally:
            conn.disconnect()

    try:
        hostname_detected = await _run_in_executor(_login_and_read)
        steps.append(ConnectionStep(
            step="login",
            status=ConnectionStepStatus.SUCCESS,
            message="เข้าสู่ระบบสำเร็จ",
        ))
    except NetmikoAuthenticationException:
        steps.append(ConnectionStep(
            step="login",
            status=ConnectionStepStatus.FAILED,
            message="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง",
        ))
        steps += _skip_remaining(["hostname"])
        return steps
    except NetmikoTimeoutException:
        steps.append(ConnectionStep(
            step="login",
            status=ConnectionStepStatus.FAILED,
            message="SSH/Telnet เปิดอยู่แต่หมดเวลารอ login หรือ IOS prompt",
        ))
        steps += _skip_remaining(["hostname"])
        return steps
    except Exception as exc:
        steps.append(ConnectionStep(
            step="login",
            status=ConnectionStepStatus.FAILED,
            message="เชื่อมต่อไม่สำเร็จ",
            detail=redact_text(str(exc)),
        ))
        steps += _skip_remaining(["hostname"])
        return steps

    # --- Step 4: Hostname ---
    if hostname_detected:
        steps.append(ConnectionStep(
            step="hostname",
            status=ConnectionStepStatus.SUCCESS,
            message=f"อ่าน hostname ได้: {hostname_detected}",
            detail=hostname_detected,
        ))
    else:
        steps.append(ConnectionStep(
            step="hostname",
            status=ConnectionStepStatus.FAILED,
            message="อ่าน hostname ไม่ได้",
        ))

    return steps


def _skip_remaining(step_names: list[str]) -> list[ConnectionStep]:
    """สร้าง ConnectionStep ที่ SKIPPED สำหรับขั้นที่ไม่ได้ทดสอบ"""
    return [
        ConnectionStep(step=name, status=ConnectionStepStatus.SKIPPED, message="ข้ามเพราะขั้นก่อนล้มเหลว")
        for name in step_names
    ]


_CLI_ERROR_MARKERS = (
    "% Invalid input",
    "% Incomplete command",
    "% Ambiguous command",
    "% Unrecognized command",
    "% Privileged command",
    "% Authorization failed",
    "% Permission denied",
    "% Error",
    "Error:",
)


def _contains_cli_error(output: str) -> bool:
    """ตรวจ marker error ของ Cisco IOS จาก output ที่คืนโดย Netmiko"""
    lowered = output.lower()
    return any(marker.lower() in lowered for marker in _CLI_ERROR_MARKERS)


def _open_connection(
    transport_config: SSHConfig | TelnetConfig | SerialConfig,
    *,
    require_enable: bool,
):
    """เปิด connection สำหรับ operation เดียวและเข้า enable เฉพาะเมื่อจำเป็น

    Parameters:
        transport_config: ค่าเชื่อมต่อที่ decrypt แล้วสำหรับ session นี้
        require_enable: True เฉพาะ operation ที่แก้ configuration

    Raises:
        EnableSecretRequiredError: เมื่อจำเป็นต้องเข้า enable แต่ไม่ได้ระบุ secret
    """
    connection = ConnectHandler(**build_device_dict(transport_config))
    try:
        if require_enable and not connection.check_enable_mode():
            # Console หลายตัวเข้า enable ได้โดยไม่ใช้รหัส จึงต้องลองจริงก่อนสรุปว่าขาด secret.
            try:
                connection.enable()
            except (NetmikoAuthenticationException, NetmikoTimeoutException, ValueError) as exc:
                if not transport_config.secret:
                    raise EnableSecretRequiredError(
                        "อุปกรณ์ขอรหัส Enable; เพิ่ม Node ใหม่พร้อม Enable Secret แล้วลองอีกครั้ง"
                    ) from exc
                raise
        return connection
    except Exception:
        connection.disconnect()
        raise


def send_config_commands(
    transport_config: SSHConfig | TelnetConfig | SerialConfig,
    commands: list[str],
) -> list[tuple[str, bool, str, str | None]]:
    """ส่ง config ตามลำดับและคืน output จริงต่อ command

    รักษา config submode ใน session เดียว (เช่น interface/router) แต่เรียก Netmiko หนึ่งครั้ง
    ต่อ command เพื่อหยุดทันทีที่ IOS ตอบ error และให้ history ระบุ partial state ได้จริง.
    """
    connection = _open_connection(transport_config, require_enable=True)
    results: list[tuple[str, bool, str, str | None]] = []
    try:
        for index, command in enumerate(commands):
            # ``write memory`` เป็น privileged EXEC command ไม่ใช่ global-config
            # command จึงห้ามส่งผ่าน send_config_set เพราะ IOS จะตอบ CLI error.
            if command == "write memory":
                output = redact_text(connection.send_command(command, use_textfsm=False))
            else:
                output = redact_text(
                    connection.send_config_set(
                        [command],
                        enter_config_mode=index == 0,
                        exit_config_mode=False,
                    )
                )
            failed = _contains_cli_error(output)
            results.append((command, not failed, output, "CLI_REJECTED" if failed else None))
            if failed:
                break
    finally:
        connection.disconnect()
    return results


def send_show_command(
    transport_config: SSHConfig | TelnetConfig | SerialConfig,
    command: str,
    *,
    require_enable: bool = False,
) -> str:
    """ส่งคำสั่ง show ใน allowlist และคืน output ที่ redact แล้ว

    คำสั่งทั่วไปใช้ user EXEC ได้ ส่วนคำสั่งอ่าน running-config ภายในระบบต้องส่ง
    ``require_enable=True`` เพื่อเข้า privileged EXEC อย่างชัดเจน.
    """
    connection = _open_connection(transport_config, require_enable=require_enable)
    try:
        output = redact_text(connection.send_command(command, use_textfsm=False))
        if require_enable and (not output.strip() or _contains_cli_error(output)):
            raise RuntimeError("อุปกรณ์ปฏิเสธการอ่าน running-config")
        return output
    finally:
        connection.disconnect()


def send_show_commands(
    transport_config: SSHConfig | TelnetConfig | SerialConfig,
    commands: list[str],
) -> list[str]:
    """ส่งชุดคำสั่ง Show ที่ backend สร้างใน session เดียวและคืน output ตามลำดับ

    Parameters:
        transport_config: ค่าเชื่อมต่อที่ decrypt แล้ว
        commands: คำสั่ง read-only ที่ผ่าน allowlist/typed validation ฝั่ง server

    Returns:
        Output ที่ redact แล้วเรียงตรงกับ commands
    """
    connection = _open_connection(transport_config, require_enable=False)
    try:
        return [
            redact_text(connection.send_command(command, use_textfsm=False))
            for command in commands
        ]
    finally:
        connection.disconnect()
