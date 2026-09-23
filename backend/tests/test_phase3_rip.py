"""ทดสอบ Phase 3B: RIP schema, parser, renderer, preview/apply และ remove process"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.models import RipNetworkConfig, RipNetworkUpdate
from backend.services.parser import parse_rip_config
from backend.services.renderer import (
    render_rip_network,
    render_rip_network_remove,
    render_rip_network_update,
    render_rip_process_remove,
)
from backend.tests.conftest import SSH_NODE_PAYLOAD


def _create_node(client, suffix: str) -> str:
    """สร้าง node test ที่มี enable secret และคืน ID"""
    payload = {
        **SSH_NODE_PAYLOAD,
        "hostname": f"Rip{suffix}",
        "transport_config": {
            **SSH_NODE_PAYLOAD["transport_config"],
            "host": f"10.60.0.{len(suffix) + sum(ord(char) for char in suffix) % 150}",
        },
    }
    response = client.post("/nodes", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def _running_config(*networks: str, version: int = 2) -> str:
    """สร้าง running-config RIP fixture แบบ IOS"""
    commands = "\n".join(f" network {network}" for network in networks)
    return f"hostname R1\n!\nrouter rip\n version {version}\n{commands}\n no auto-summary\n!\nend"


def test_rip_validation_requires_classful_network_boundary() -> None:
    """RIP network ต้องเป็น major boundary และไม่รับ multicast/invalid IPv4"""
    assert RipNetworkConfig(version=2, network="10.0.0.0").network == "10.0.0.0"
    with pytest.raises(ValidationError):
        RipNetworkConfig(version=2, network="10.0.23.0")
    with pytest.raises(ValidationError):
        RipNetworkConfig(version=2, network="224.0.0.0")


def test_rip_parser_and_renderer_cover_add_update_remove() -> None:
    """Parser และ renderer ต้องรองรับ lifecycle ของ network/process ครบ"""
    state = parse_rip_config(_running_config("10.0.0.0", "172.16.0.0"))
    assert state == {
        "enabled": True,
        "version": 2,
        "networks": ["10.0.0.0", "172.16.0.0"],
        "no_auto_summary": True,
    }
    current = RipNetworkConfig(version=2, network="10.0.0.0")
    desired = RipNetworkConfig(version=1, network="172.16.0.0")
    assert render_rip_network(current) == ["router rip", " version 2", " network 10.0.0.0", " no auto-summary"]
    assert render_rip_network_remove(current) == ["router rip", " no network 10.0.0.0"]
    assert render_rip_network_update(RipNetworkUpdate(current=current, desired=desired)) == [
        "router rip", "version 1", "no network 10.0.0.0", "network 172.16.0.0", "no auto-summary",
    ]
    assert render_rip_process_remove() == ["no router rip"]


def test_rip_state_and_duplicate_preview_use_privileged_running_config(client) -> None:
    """GET state ต้องเข้า enable และ duplicate ต้องหยุดก่อนสร้าง preview"""
    node_id = _create_node(client, "State")
    connection = MagicMock()
    connection.check_enable_mode.return_value = False
    connection.send_command.return_value = _running_config("10.0.0.0")
    with patch("backend.services.connection.ConnectHandler", return_value=connection):
        state = client.get(f"/nodes/{node_id}/routing/rip")
        duplicate = client.post(
            f"/nodes/{node_id}/config/rip/network/preview",
            json={"version": 2, "network": "10.0.0.0"},
        )
    assert state.status_code == 200
    assert state.json()["enabled"] is True
    assert state.json()["networks"] == ["10.0.0.0"]
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "RIP_NETWORK_DUPLICATE"
    assert connection.enable.call_count == 2


def test_rip_preview_apply_and_history(client) -> None:
    """Add RIP network ต้องผ่าน typed preview/apply และสร้าง history"""
    node_id = _create_node(client, "Apply")
    show_connection = MagicMock()
    show_connection.check_enable_mode.return_value = True
    show_connection.send_command.return_value = "hostname R1\n!\nend"
    with patch("backend.services.connection.ConnectHandler", return_value=show_connection):
        preview = client.post(
            f"/nodes/{node_id}/config/rip/network/preview",
            json={"version": 2, "network": "10.0.0.0"},
        )
    assert preview.status_code == 200
    preview_data = preview.json()

    apply_connection = MagicMock()
    apply_connection.check_enable_mode.return_value = True
    apply_connection.send_config_set.return_value = "Configuration applied successfully."
    with patch("backend.services.connection.ConnectHandler", return_value=apply_connection):
        applied = client.post(
            f"/nodes/{node_id}/config/rip/apply",
            json={"operation_id": preview_data["operation_id"], "payload_hash": preview_data["payload_hash"]},
        )
    assert applied.status_code == 200
    assert applied.json()["overall_status"] == "success"
    assert [call.args[0][0] for call in apply_connection.send_config_set.call_args_list] == preview_data["commands"]
    history = client.get(f"/history?node_id={node_id}").json()
    assert history[0]["command_type"] == "RIP Configuration"


def test_rip_update_remove_and_remove_process_validate_actual_state(client) -> None:
    """Update/delete/process remove ต้องอ้าง current state และมี inverse command ชัดเจน"""
    node_id = _create_node(client, "Lifecycle")
    connection = MagicMock()
    connection.check_enable_mode.return_value = True
    connection.send_command.return_value = _running_config("10.0.0.0", "172.16.0.0")
    with patch("backend.services.connection.ConnectHandler", return_value=connection):
        updated = client.post(
            f"/nodes/{node_id}/config/rip/network/update/preview",
            json={
                "current": {"version": 2, "network": "10.0.0.0"},
                "desired": {"version": 2, "network": "192.168.8.0"},
            },
        )
        removed = client.post(
            f"/nodes/{node_id}/config/rip/network/remove/preview",
            json={"version": 2, "network": "172.16.0.0"},
        )
        process = client.post(
            f"/nodes/{node_id}/config/rip/process/remove/preview",
            json={"version": 2, "networks": ["10.0.0.0", "172.16.0.0"], "no_auto_summary": True},
        )
        stale = client.post(
            f"/nodes/{node_id}/config/rip/network/remove/preview",
            json={"version": 1, "network": "10.0.0.0"},
        )
    assert updated.status_code == 200
    assert "no network 10.0.0.0" in updated.json()["commands"]
    assert removed.status_code == 200
    assert removed.json()["commands"][-1].strip() == "no network 172.16.0.0"
    assert process.status_code == 200
    assert process.json()["commands"] == ["no router rip"]
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "RIP_STATE_CHANGED"
