"""ทดสอบ Console ไม่ใช้ Enable Secret, CLI session และการลบ Node ที่มี preview"""

from __future__ import annotations

from threading import Event
from unittest.mock import MagicMock, patch

import pytest
from starlette.websockets import WebSocketDisconnect

from backend.database import get_db
from backend.routers.config import _bgp_state_response, _eigrp_entries, _ospf_entries
from backend.services.parser import parse_bgp_config, parse_eigrp_config, parse_ospf_config
from backend.tests.conftest import SERIAL_NODE_PAYLOAD, SSH_NODE_PAYLOAD


def _create_test_node(client, hostname: str, host: str) -> str:
    """สร้าง Node ทดสอบ IP เฉพาะและคืน ID ที่สร้าง"""
    payload = {**SSH_NODE_PAYLOAD, "hostname": hostname,
               "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": host}}
    response = client.post("/nodes", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def test_console_routing_reads_config_without_ip_or_enable_secret(client) -> None:
    """Console ที่เข้า enable โดยไม่ถามรหัสต้องตรวจ RIP จาก running-config ได้แม้ไม่มี IP"""
    payload = {**SERIAL_NODE_PAYLOAD, "hostname": "ConsoleRoutingNoIp",
               "transport_config": {**SERIAL_NODE_PAYLOAD["transport_config"], "serial_port": "COM91"}}
    payload["transport_config"].pop("secret", None)
    node_id = client.post("/nodes", json=payload).json()["id"]
    connection = MagicMock()
    connection.check_enable_mode.return_value = False
    connection.send_command.return_value = "router rip\n version 2\n network 10.0.0.0\n!"
    with patch("backend.services.connection.ConnectHandler", return_value=connection):
        response = client.get(f"/nodes/{node_id}/routing/rip")
    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert response.json()["networks"] == ["10.0.0.0"]
    connection.enable.assert_called_once()
    connection.disconnect.assert_called_once()


def test_console_reports_enable_needed_only_after_attempt(client) -> None:
    """เมื่อ enable ปฏิเสธจริงและไม่มี secret จึงแจ้งสาเหตุโดยไม่คืน Off ปลอม"""
    payload = {**SERIAL_NODE_PAYLOAD, "hostname": "ConsoleEnablePrompt",
               "transport_config": {**SERIAL_NODE_PAYLOAD["transport_config"], "serial_port": "COM92"}}
    payload["transport_config"].pop("secret", None)
    node_id = client.post("/nodes", json=payload).json()["id"]
    connection = MagicMock()
    connection.check_enable_mode.return_value = False
    connection.enable.side_effect = ValueError("Failed to enter enable mode")
    with patch("backend.services.connection.ConnectHandler", return_value=connection):
        response = client.get(f"/nodes/{node_id}/routing/ospf")
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "OSPF_READ_FAILED"
    assert "Enable Secret" in response.json()["detail"]["details"]["reason"]
    connection.disconnect.assert_called_once()


def test_routing_state_preserves_process_without_interface_ip_or_router_id() -> None:
    """อ่าน OSPF/EIGRP/BGP จาก running-config โดยไม่ประดิษฐ์ Router ID หรือทิ้ง neighbor"""
    ospf = parse_ospf_config("router ospf 1\n network 10.0.0.0 0.0.0.255 area 0\n!")
    eigrp = parse_eigrp_config("router eigrp 100\n network 10.0.0.0 0.0.0.255\n!")
    bgp = parse_bgp_config("router bgp 65001\n neighbor 10.0.0.2 remote-as 65002\n!")
    assert _ospf_entries(ospf)[0].router_id is None
    assert _eigrp_entries(eigrp)[0].router_id is None
    state = _bgp_state_response("node-id", bgp)
    assert state.enabled is True
    assert len(state.neighbors) == 1
    assert state.neighbors[0].router_id is None


def test_cli_session_sends_lines_and_audits_without_contents(client) -> None:
    """CLI ใช้ session เดียวและ History เก็บผลโดยไม่เก็บ command/output ดิบ"""
    node_id = _create_test_node(client, "CliSession", "10.0.0.201")
    connection = MagicMock()
    connection.find_prompt.return_value = "R1#"
    connection.send_command_timing.return_value = "Cisco IOS Software"
    disconnected = Event()
    connection.disconnect.side_effect = disconnected.set
    with patch("backend.services.terminal.ConnectHandler", return_value=connection), client.websocket_connect(f"/nodes/{node_id}/cli") as socket:
        assert socket.receive_json()["type"] == "ready"
        socket.send_json({"command": "show version"})
        result = socket.receive_json()
        assert result["type"] == "result"
        assert result["status"] == "success"
        assert "Cisco IOS" in result["output"]
        socket.send_json({"action": "disconnect"})
        with pytest.raises(WebSocketDisconnect):
            socket.receive_json()
    assert disconnected.wait(2)
    connection.disconnect.assert_called_once()
    records = client.get("/history", params={"node_id": node_id}).json()
    record = next(item for item in records if item["command_type"] == "CLI Command")
    assert "show version" not in str(record)
    assert "Cisco IOS" not in str(record)


def test_delete_node_with_preview_keeps_history(client) -> None:
    """ลบ Node ที่มี pending operation ได้และเก็บ audit snapshot หลังลบ"""
    node_id = _create_test_node(client, "DeleteWithPreview", "10.0.0.202")
    preview = client.post(f"/nodes/{node_id}/config/interface/admin/preview",
                          json={"interface_name": "GigabitEthernet0/1", "admin_up": True})
    assert preview.status_code == 200
    assert client.delete(f"/nodes/{node_id}").status_code == 204
    with get_db() as db:
        assert db.execute("SELECT id FROM operations WHERE node_id = ?", (node_id,)).fetchone() is None
    records = client.get("/history", params={"node_id": node_id}).json()
    assert any(item["command_type"] == "Node Delete" for item in records)
    assert client.get(f"/nodes/{node_id}").status_code == 404
