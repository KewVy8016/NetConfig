# pytest fixtures สำหรับ NetConfig backend tests
# ใช้ fake Netmiko เพื่อให้ test ทำงานโดยไม่ต้องเชื่อมต่ออุปกรณ์จริง

from __future__ import annotations

import os
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

# สร้าง Fernet key สำหรับ test ก่อน import app (ต้องมีก่อน config โหลด)
TEST_FERNET_KEY = Fernet.generate_key().decode()


@pytest.fixture(scope="session", autouse=True)
def set_test_env(tmp_path_factory) -> Generator[None, None, None]:
    """ตั้ง environment variables สำหรับ test session ทั้งหมด

    ใช้ temp DB file เพื่อแยก test state จาก development DB
    """
    db_file = tmp_path_factory.mktemp("db") / "test_netconfig.db"
    os.environ["NETCONFIG_FERNET_KEY"] = TEST_FERNET_KEY
    os.environ["NETCONFIG_DB_PATH"] = str(db_file)
    os.environ["NETCONFIG_CORS_ORIGINS"] = '["http://localhost:5173"]'
    yield
    # cleanup env
    for key in ["NETCONFIG_FERNET_KEY", "NETCONFIG_DB_PATH", "NETCONFIG_CORS_ORIGINS"]:
        os.environ.pop(key, None)


@pytest.fixture(scope="session")
def client(set_test_env) -> Generator[TestClient, None, None]:
    """FastAPI TestClient สำหรับ API integration tests"""
    # import หลังตั้ง env เพื่อให้ config โหลดได้
    from backend.config import get_settings
    get_settings.cache_clear()

    from backend.database import init_db
    from backend.main import app
    init_db()

    with TestClient(app) as c:
        yield c


@pytest.fixture
def fake_netmiko_success():
    """Mock ConnectHandler ที่ login สำเร็จและคืน hostname 'R1'"""
    mock_conn = MagicMock()
    mock_conn.find_prompt.return_value = "R1#"
    mock_conn.send_command.return_value = "Cisco IOS Software..."
    mock_conn.disconnect.return_value = None

    with patch("backend.services.connection.ConnectHandler", return_value=mock_conn) as mock_cls:
        yield mock_cls


@pytest.fixture
def fake_netmiko_auth_fail():
    """Mock ConnectHandler ที่ raise NetmikoAuthenticationException"""
    from netmiko.exceptions import NetmikoAuthenticationException

    with patch(
        "backend.services.connection.ConnectHandler",
        side_effect=NetmikoAuthenticationException("Auth failed"),
    ) as mock_cls:
        yield mock_cls


@pytest.fixture
def fake_netmiko_timeout():
    """Mock ConnectHandler ที่ raise NetmikoTimeoutException"""
    from netmiko.exceptions import NetmikoTimeoutException

    with patch(
        "backend.services.connection.ConnectHandler",
        side_effect=NetmikoTimeoutException("Timeout"),
    ) as mock_cls:
        yield mock_cls


@pytest.fixture
def fake_ping_success():
    """Mock subprocess ping ที่ return code 0 (success)"""
    with patch("backend.services.connection._ping_host", return_value=True):
        yield


@pytest.fixture
def fake_ping_fail():
    """Mock subprocess ping ที่ return code 1 (fail)"""
    with patch("backend.services.connection._ping_host", return_value=False):
        yield


@pytest.fixture
def fake_port_open():
    """Mock TCP port check ที่ return True"""
    with patch("backend.services.connection._check_port", return_value=True):
        yield


@pytest.fixture
def fake_port_closed():
    """Mock TCP port check ที่ return False"""
    with patch("backend.services.connection._check_port", return_value=False):
        yield


# ---------------------------------------------------------------------------
# Sample payloads สำหรับ test
# ---------------------------------------------------------------------------

SSH_NODE_PAYLOAD: dict[str, Any] = {
    "hostname": "R1",
    "device_kind": "router",
    "transport_config": {
        "transport": "ssh",
        "host": "192.168.1.11",
        "port": 22,
        "username": "admin",
        "password": "cisco123",
        "secret": "enable123",
    },
}

TELNET_NODE_PAYLOAD: dict[str, Any] = {
    "hostname": "R2",
    "device_kind": "router",
    "transport_config": {
        "transport": "telnet",
        "host": "192.168.1.12",
        "port": 23,
        "username": "admin",
        "password": "cisco123",
    },
}

SERIAL_NODE_PAYLOAD: dict[str, Any] = {
    "hostname": "R3",
    "device_kind": "router",
    "transport_config": {
        "transport": "serial",
        "serial_port": "COM3",
        "baudrate": 9600,
        "username": "admin",
        "password": "cisco123",
    },
}
