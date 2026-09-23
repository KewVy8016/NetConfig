"""ทดสอบ Phase 4: scanner ที่จำกัด scope และ explicit Save Config"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from backend.models import SSHConfig
from backend.services.connection import send_config_commands
from backend.tests.conftest import SSH_NODE_PAYLOAD


def _node(client) -> str:
    """สร้าง node test แยกสำหรับ preview/apply"""
    response = client.post(
        "/nodes",
        json={
            **SSH_NODE_PAYLOAD,
            "hostname": "Phase4Node",
            "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.73.0.20"},
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_scan_allows_only_small_subnet_and_returns_open_management_ports(client) -> None:
    """Scanner ต้องปฏิเสธ subnet ใหญ่และคืนเฉพาะผล TCP 22/23"""
    rejected = client.post("/nodes/scan", json={"subnet": "192.168.8.0/24"})
    assert rejected.status_code == 422
    with patch("backend.routers.nodes.scan_subnet", new_callable=AsyncMock, return_value=[{"host": "192.168.8.135", "open_ports": [23]}]):
        response = client.post("/nodes/scan", json={"subnet": "192.168.8.128/28"})
    assert response.status_code == 200
    assert response.json()["results"] == [{"host": "192.168.8.135", "open_ports": [23]}]


def test_save_config_requires_preview_then_apply_and_records_history(client) -> None:
    """Save Config ต้องบังคับ confirm/preview และเขียน history เมื่อ apply"""
    node_id = _node(client)
    denied = client.post(f"/nodes/{node_id}/config/save/preview", json={})
    assert denied.status_code == 422
    preview = client.post(f"/nodes/{node_id}/config/save/preview", json={"confirm": True})
    assert preview.status_code == 200
    assert preview.json()["commands"] == ["write memory"]
    connection = MagicMock()
    connection.check_enable_mode.return_value = True
    connection.send_command.return_value = "Building configuration...\n[OK]"
    with patch("backend.services.connection.ConnectHandler", return_value=connection):
        applied = client.post(
            f"/nodes/{node_id}/config/save/apply",
            json={"operation_id": preview.json()["operation_id"], "payload_hash": preview.json()["payload_hash"]},
        )
    assert applied.status_code == 200
    connection.send_command.assert_called_once_with("write memory", use_textfsm=False)
    assert client.get(f"/history?node_id={node_id}").json()[0]["command_type"] == "Save Configuration"


def test_config_commands_stop_on_first_ios_error_and_keep_per_command_output() -> None:
    """Apply ต้องหยุดหลัง CLI error และไม่รายงาน command ถัดไปว่าสำเร็จ"""
    connection = MagicMock()
    connection.check_enable_mode.return_value = True
    connection.send_config_set.side_effect = ["", "% Invalid input detected at '^' marker."]
    transport = SSHConfig(host="10.0.0.1", port=22, username="user", password="password")
    with patch("backend.services.connection.ConnectHandler", return_value=connection):
        results = send_config_commands(transport, ["router ospf 1", "network invalid", "network 10.0.0.0 0.0.0.255 area 0"])
    assert [item[0] for item in results] == ["router ospf 1", "network invalid"]
    assert results[0][1] is True and results[1][1] is False
    assert results[1][3] == "CLI_REJECTED"
