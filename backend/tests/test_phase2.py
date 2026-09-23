"""Unit และ API tests สำหรับ interface preview/apply และ Show allowlist"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

from backend.services.parser import (
    parse_show_interface_detail,
    parse_show_ip_interface_brief,
    parse_show_ip_route,
)
from backend.services.renderer import calculate_wildcard, render_interface_admin_commands, render_interface_commands
from backend.tests.conftest import SSH_NODE_PAYLOAD


def test_renderer_validates_and_keeps_ios_context() -> None:
    """คำสั่งต้องเป็นชุด interface context และคำนวณ wildcard ได้ถูกต้อง"""
    from backend.models import InterfaceConfig

    payload = InterfaceConfig(
        interface_name="GigabitEthernet0/0",
        ip_address="192.168.1.1",
        subnet_mask="255.255.255.0",
        description="Uplink",
        admin_up=True,
    )
    assert render_interface_commands(payload) == [
        "interface GigabitEthernet0/0",
        " ip address 192.168.1.1 255.255.255.0",
        " description Uplink",
        " no shutdown",
    ]
    assert calculate_wildcard("255.255.255.0") == "0.0.0.255"


def test_renderer_admin_toggle_keeps_interface_context() -> None:
    """Toggle ต้อง render เฉพาะ interface และ admin state โดยไม่แตะ IPv4"""
    from backend.models import InterfaceAdminConfig

    assert render_interface_admin_commands(InterfaceAdminConfig(interface_name="GigabitEthernet0/1", admin_up=False)) == [
        "interface GigabitEthernet0/1",
        " shutdown",
    ]
    assert render_interface_admin_commands(InterfaceAdminConfig(interface_name="GigabitEthernet0/1", admin_up=True)) == [
        "interface GigabitEthernet0/1",
        " no shutdown",
    ]


def test_show_parsers_fall_back_when_output_is_unknown() -> None:
    """Parser ต้องคืน None เมื่อไม่มั่นใจ เพื่อไม่แสดงข้อมูลผิด"""
    assert parse_show_ip_interface_brief("unexpected output") is None
    assert parse_show_ip_route("unexpected output") is None


def test_interface_parser_keeps_administratively_down_rows() -> None:
    """Parser ต้องอ่าน interface ที่ status มีช่องว่างและคั่น protocol เพียงหนึ่งช่อง"""
    output = (
        "Interface                  IP-Address      OK? Method Status                Protocol\n"
        "GigabitEthernet0/0         192.168.8.135   YES manual up                    up\n"
        "GigabitEthernet0/1         unassigned      YES unset  administratively down down\n"
    )
    rows = parse_show_ip_interface_brief(output)
    assert rows is not None
    assert [row["interface"] for row in rows] == ["GigabitEthernet0/0", "GigabitEthernet0/1"]
    assert rows[1]["status"] == "administratively down"
    assert rows[1]["protocol"] == "down"


def test_interface_detail_parser_returns_prefill_values() -> None:
    """Parser ต้องแปลง prefix เป็น mask และคืนค่าที่ใช้ prefill ได้ครบ"""
    output = (
        "GigabitEthernet0/1 is administratively down, line protocol is down\n"
        "  Description: Link to R3\n"
        "  Internet address is 10.0.23.1/30\n"
    )
    parsed = parse_show_interface_detail(output, "GigabitEthernet0/1")
    assert parsed == {
        "interface_name": "GigabitEthernet0/1",
        "ip_address": "10.0.23.1",
        "subnet_mask": "255.255.255.252",
        "description": "Link to R3",
        "admin_up": False,
        "status": "administratively down",
        "protocol": "down",
    }


def test_interface_preview_does_not_connect(client) -> None:
    """Preview ต้อง render/persist operation โดยไม่เรียก Netmiko"""
    node = client.post("/nodes", json={**SSH_NODE_PAYLOAD, "hostname": "Phase2Preview", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.0.52"}})
    assert node.status_code == 201
    node_id = node.json()["id"]
    with patch("backend.services.connection.ConnectHandler") as connect_handler:
        response = client.post(
            f"/nodes/{node_id}/config/interface/preview",
            json={
                "interface_name": "GigabitEthernet0/0",
                "ip_address": "192.168.1.1",
                "subnet_mask": "255.255.255.0",
                "description": "Uplink",
                "admin_up": True,
            },
        )
    assert response.status_code == 200
    assert response.json()["commands"][0] == "interface GigabitEthernet0/0"
    connect_handler.assert_not_called()


def test_interface_admin_preview_supports_ip_unassigned_port(client) -> None:
    """Admin toggle ต้อง preview ได้แม้พอร์ตไม่มี IPv4 เช่น switchport L2"""
    node = client.post("/nodes", json={**SSH_NODE_PAYLOAD, "hostname": "Phase2AdminToggle", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.0.59"}})
    node_id = node.json()["id"]
    with patch("backend.services.connection.ConnectHandler") as connect_handler:
        response = client.post(
            f"/nodes/{node_id}/config/interface/admin/preview",
            json={"interface_name": "GigabitEthernet0/1", "admin_up": False},
        )
    assert response.status_code == 200
    assert response.json()["operation_type"] == "interface_admin"
    assert response.json()["commands"] == ["interface GigabitEthernet0/1", " shutdown"]
    connect_handler.assert_not_called()


def test_interface_apply_and_history(client) -> None:
    """Apply ต้องส่งชุดคำสั่งใน session เดียวและสร้าง history"""
    node = client.post("/nodes", json={**SSH_NODE_PAYLOAD, "hostname": "Phase2Apply", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.0.53"}})
    node_id = node.json()["id"]
    payload = {
        "interface_name": "GigabitEthernet0/1",
        "ip_address": "10.0.1.1",
        "subnet_mask": "255.255.255.0",
        "description": "Transit",
        "admin_up": False,
    }
    preview = client.post(f"/nodes/{node_id}/config/interface/preview", json=payload).json()
    fake_connection = MagicMock()
    fake_connection.send_config_set.return_value = "Configuration applied successfully."
    with patch("backend.services.connection.ConnectHandler", return_value=fake_connection):
        response = client.post(
            f"/nodes/{node_id}/config/interface/apply",
            json={"operation_id": preview["operation_id"], "payload_hash": preview["payload_hash"]},
        )
    assert response.status_code == 200
    assert response.json()["overall_status"] == "success"
    assert [call.args[0][0] for call in fake_connection.send_config_set.call_args_list] == preview["commands"]
    history = client.get(f"/history?node_id={node_id}")
    assert history.status_code == 200
    assert history.json()[0]["overall_status"] == "success"


def test_show_rejects_arbitrary_command(client) -> None:
    """Show ที่ไม่อยู่ allowlist ต้องไม่ถูกส่งไป device"""
    node = client.post("/nodes", json={**SSH_NODE_PAYLOAD, "hostname": "Phase2Show", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.0.54"}})
    node_id = node.json()["id"]
    response = client.get(f"/nodes/{node_id}/show", params={"command": "configure terminal"})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "COMMAND_NOT_ALLOWED"


def test_show_interface_returns_raw_and_parsed_output(client) -> None:
    """Show interface ต้องคืน raw/parsed output โดยไม่บังคับเข้า enable mode"""
    node = client.post("/nodes", json={**SSH_NODE_PAYLOAD, "hostname": "Phase2ShowOk", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.0.55"}})
    node_id = node.json()["id"]
    fake_connection = MagicMock()
    fake_connection.send_command.return_value = (
        "Interface                  IP-Address      OK? Method Status                Protocol\n"
        "GigabitEthernet0/0         192.168.1.1    YES manual up                    up"
    )
    with patch("backend.services.connection.ConnectHandler", return_value=fake_connection):
        response = client.get(f"/nodes/{node_id}/show", params={"command": "show ip interface brief"})
    assert response.status_code == 200
    assert response.json()["parsed"][0]["interface"] == "GigabitEthernet0/0"
    assert "192.168.1.1" in response.json()["output"]
    fake_connection.enable.assert_not_called()


def test_get_interface_current_returns_typed_prefill(client) -> None:
    """Typed interface endpoint ต้อง parse actual state โดย browser ไม่ส่ง CLI"""
    node = client.post("/nodes", json={**SSH_NODE_PAYLOAD, "hostname": "Phase2Current", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.0.57"}})
    node_id = node.json()["id"]
    fake_connection = MagicMock()
    fake_connection.send_command.side_effect = [
        "GigabitEthernet0/1 is up, line protocol is up\n  Description: Transit to R2\n",
        "GigabitEthernet0/1 is up, line protocol is up\n  Internet address is 10.0.12.1/24\n",
    ]
    with patch("backend.services.connection.ConnectHandler", return_value=fake_connection):
        response = client.get(f"/nodes/{node_id}/interfaces/GigabitEthernet0/1")
    assert response.status_code == 200
    assert response.json()["ip_address"] == "10.0.12.1"
    assert response.json()["subnet_mask"] == "255.255.255.0"
    assert response.json()["description"] == "Transit to R2"
    assert response.json()["admin_up"] is True
    assert fake_connection.send_command.call_args_list == [
        call("show interfaces GigabitEthernet0/1", use_textfsm=False),
        call("show ip interface GigabitEthernet0/1", use_textfsm=False),
    ]


def test_get_interface_current_rejects_command_injection(client) -> None:
    """ชื่อ interface ที่มีอักขระคำสั่งต้องถูกปฏิเสธก่อนเชื่อมต่ออุปกรณ์"""
    node = client.post("/nodes", json={**SSH_NODE_PAYLOAD, "hostname": "Phase2UnsafeName", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.0.58"}})
    node_id = node.json()["id"]
    with patch("backend.services.connection.ConnectHandler") as connect_handler:
        response = client.get(f"/nodes/{node_id}/interfaces/GigabitEthernet0%2F1%3Breload")
    assert response.status_code == 422
    connect_handler.assert_not_called()


def test_config_apply_without_enable_secret_returns_specific_error(client) -> None:
    """Apply จาก user EXEC โดยไม่มี enable secret ต้องคืน error ที่แก้ไขได้ชัดเจน"""
    node_payload = {
        **SSH_NODE_PAYLOAD,
        "hostname": "Phase2EnableRequired",
        "transport_config": {
            **SSH_NODE_PAYLOAD["transport_config"],
            "host": "10.0.0.56",
            "secret": "",
        },
    }
    node_id = client.post("/nodes", json=node_payload).json()["id"]
    payload = {
        "interface_name": "GigabitEthernet0/1",
        "ip_address": "10.0.2.1",
        "subnet_mask": "255.255.255.0",
        "description": "Requires privilege",
        "admin_up": True,
    }
    preview = client.post(f"/nodes/{node_id}/config/interface/preview", json=payload).json()
    fake_connection = MagicMock()
    fake_connection.check_enable_mode.return_value = False
    with patch("backend.services.connection.ConnectHandler", return_value=fake_connection):
        response = client.post(
            f"/nodes/{node_id}/config/interface/apply",
            json={"operation_id": preview["operation_id"], "payload_hash": preview["payload_hash"]},
        )
    assert response.status_code == 200
    assert response.json()["overall_status"] == "failed"
    assert response.json()["results"][0]["error_code"] == "ENABLE_SECRET_REQUIRED"
    fake_connection.disconnect.assert_called_once()
