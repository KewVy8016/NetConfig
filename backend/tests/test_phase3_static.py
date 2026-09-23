"""ทดสอบ Phase 3A: Static/Default route validation, renderer, preview/apply และ history"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.models import StaticRouteConfig, StaticRouteUpdate
from backend.services.parser import parse_static_routes
from backend.services.renderer import (
    render_static_route,
    render_static_route_remove,
    render_static_route_update,
)
from backend.tests.conftest import SSH_NODE_PAYLOAD


def _route_payload(**overrides: str) -> dict[str, str]:
    """สร้าง payload มาตรฐานสำหรับ test แล้วแทนค่าที่ระบุ"""
    payload = {
        "destination": "172.16.0.0",
        "subnet_mask": "255.255.0.0",
        "next_hop": "10.0.23.2",
    }
    payload.update(overrides)
    return payload


def _create_node(client, suffix: str) -> str:
    """สร้าง node แยกต่อ test และคืน ID"""
    payload = {
        **SSH_NODE_PAYLOAD,
        "hostname": f"Static{suffix}",
        "transport_config": {
            **SSH_NODE_PAYLOAD["transport_config"],
            "host": f"10.50.0.{len(suffix) + sum(ord(char) for char in suffix) % 150}",
        },
    }
    response = client.post("/nodes", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def test_static_route_renderer_add_remove_and_update() -> None:
    """Renderer ต้องสร้าง add/remove และ update ที่ลบค่าเดิมก่อนเพิ่มค่าใหม่"""
    current = StaticRouteConfig(**_route_payload())
    desired = StaticRouteConfig(**_route_payload(next_hop="10.0.23.1"))
    assert render_static_route(current) == ["ip route 172.16.0.0 255.255.0.0 10.0.23.2"]
    assert render_static_route_remove(current) == ["no ip route 172.16.0.0 255.255.0.0 10.0.23.2"]
    assert render_static_route_update(StaticRouteUpdate(current=current, desired=desired)) == [
        "no ip route 172.16.0.0 255.255.0.0 10.0.23.2",
        "ip route 172.16.0.0 255.255.0.0 10.0.23.1",
    ]


def test_static_route_validation_rejects_host_boundary_and_multiple_targets() -> None:
    """Schema ต้องปฏิเสธ boundary, mask, next-hop และ target ที่ไม่ตรง contract"""
    with pytest.raises(ValidationError):
        StaticRouteConfig(**_route_payload(destination="172.16.1.1"))
    with pytest.raises(ValidationError):
        StaticRouteConfig(**_route_payload(exit_interface="GigabitEthernet0/1"))
    with pytest.raises(ValidationError):
        StaticRouteConfig(**_route_payload(subnet_mask="255.0.255.0"))
    with pytest.raises(ValidationError):
        StaticRouteConfig(**_route_payload(next_hop="0.0.0.0"))


def test_static_route_parser_supports_next_hop_exit_and_default() -> None:
    """Parser ต้องแยก next-hop/exit interface และระบุ default route ได้"""
    routes = parse_static_routes(
        "ip route 0.0.0.0 0.0.0.0 192.168.8.2\n"
        "ip route 172.16.0.0 255.255.0.0 GigabitEthernet0/1\n"
        "ip route 10.10.0.0 255.255.0.0 10.0.23.2 5"
    )
    assert len(routes) == 2
    assert routes[0]["route_type"] == "default"
    assert routes[0]["next_hop"] == "192.168.8.2"
    assert routes[1]["exit_interface"] == "GigabitEthernet0/1"


def test_static_route_list_and_duplicate_preview(client) -> None:
    """List ต้องคืน actual route และ preview ต้องปฏิเสธ duplicate ก่อนสร้าง operation"""
    node_id = _create_node(client, "List")
    fake_connection = MagicMock()
    fake_connection.check_enable_mode.return_value = False
    fake_connection.send_command.return_value = "ip route 172.16.0.0 255.255.0.0 10.0.23.2"
    with patch("backend.services.connection.ConnectHandler", return_value=fake_connection):
        listed = client.get(f"/nodes/{node_id}/routes/static")
        duplicate = client.post(f"/nodes/{node_id}/config/static-route/preview", json=_route_payload())
    assert listed.status_code == 200
    assert listed.json()["routes"][0]["destination"] == "172.16.0.0"
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "ROUTE_DUPLICATE"
    assert fake_connection.enable.call_count == 2


def test_static_route_preview_apply_and_history(client) -> None:
    """Add preview/apply ต้องส่ง typed command และสร้าง Static Route history"""
    node_id = _create_node(client, "Apply")
    show_connection = MagicMock()
    show_connection.send_command.return_value = ""
    with patch("backend.services.connection.ConnectHandler", return_value=show_connection):
        preview = client.post(
            f"/nodes/{node_id}/config/static-route/preview",
            json=_route_payload(),
        )
    assert preview.status_code == 200
    preview_data = preview.json()
    apply_connection = MagicMock()
    apply_connection.check_enable_mode.return_value = True
    apply_connection.send_config_set.return_value = "Configuration applied successfully."
    with patch("backend.services.connection.ConnectHandler", return_value=apply_connection):
        applied = client.post(
            f"/nodes/{node_id}/config/static-route/apply",
            json={"operation_id": preview_data["operation_id"], "payload_hash": preview_data["payload_hash"]},
        )
    assert applied.status_code == 200
    assert applied.json()["overall_status"] == "success"
    assert [call.args[0][0] for call in apply_connection.send_config_set.call_args_list] == preview_data["commands"]
    history = client.get(f"/history?node_id={node_id}").json()
    assert history[0]["command_type"] == "Static Route Configuration"


def test_static_route_update_and_remove_require_current_route(client) -> None:
    """Update สร้าง remove+add ส่วน remove ที่หา route ไม่พบต้องหยุดก่อน Apply"""
    node_id = _create_node(client, "Update")
    current = _route_payload()
    desired = _route_payload(next_hop="10.0.23.1")
    fake_connection = MagicMock()
    fake_connection.send_command.return_value = "ip route 172.16.0.0 255.255.0.0 10.0.23.2"
    with patch("backend.services.connection.ConnectHandler", return_value=fake_connection):
        updated = client.post(
            f"/nodes/{node_id}/config/static-route/update/preview",
            json={"current": current, "desired": desired},
        )
        missing = client.post(
            f"/nodes/{node_id}/config/static-route/remove/preview",
            json=_route_payload(destination="10.99.0.0", subnet_mask="255.255.0.0"),
        )
    assert updated.status_code == 200
    assert updated.json()["commands"][0].startswith("no ip route")
    assert updated.json()["commands"][1].startswith("ip route")
    assert missing.status_code == 409
    assert missing.json()["detail"]["code"] == "ROUTE_NOT_FOUND"


def test_static_route_update_records_partial_cli_failure(client) -> None:
    """Update ที่คำสั่งแรกผ่านแต่คำสั่งถัดไปถูก IOS ปฏิเสธต้องเป็น partial_failed"""
    node_id = _create_node(client, "Partial")
    current = _route_payload()
    desired = _route_payload(next_hop="10.0.23.1")
    fake_connection = MagicMock()
    fake_connection.check_enable_mode.return_value = True
    fake_connection.send_command.return_value = "ip route 172.16.0.0 255.255.0.0 10.0.23.2"
    with patch("backend.services.connection.ConnectHandler", return_value=fake_connection):
        preview = client.post(
            f"/nodes/{node_id}/config/static-route/update/preview",
            json={"current": current, "desired": desired},
        ).json()

    results = [
        (preview["commands"][0], True, "คำสั่งลบสำเร็จ", None),
        (preview["commands"][1], False, "% Invalid input", "CLI_REJECTED"),
    ]
    with patch("backend.routers.config.send_config_commands", return_value=results):
        applied = client.post(
            f"/nodes/{node_id}/config/static-route/apply",
            json={"operation_id": preview["operation_id"], "payload_hash": preview["payload_hash"]},
        )

    assert applied.status_code == 200
    assert applied.json()["overall_status"] == "partial_failed"
    assert applied.json()["results"][1]["error_code"] == "CLI_REJECTED"
    history = client.get(f"/history?node_id={node_id}").json()
    assert history[0]["overall_status"] == "partial_failed"
