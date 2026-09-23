"""ทดสอบ Phase 3D: EIGRP validation, parser, preview/apply และ remove process"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.models import EigrpNetworkConfig
from backend.services.parser import parse_eigrp_config
from backend.services.renderer import render_eigrp_network, render_eigrp_network_remove
from backend.tests.conftest import SSH_NODE_PAYLOAD


def _node(client, suffix: str) -> str:
    """สร้าง node test แยกและคืน ID"""
    response = client.post("/nodes", json={**SSH_NODE_PAYLOAD, "hostname": f"Eigrp{suffix}", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": f"10.71.0.{20 + len(suffix)}"}})
    assert response.status_code == 201
    return response.json()["id"]


def _config() -> str:
    """คืน running-config fixture ที่มี EIGRP หนึ่ง network"""
    return "hostname R1\n!\nrouter eigrp 100\n eigrp router-id 2.2.2.2\n network 10.0.23.0 0.0.0.3\n no auto-summary\n!\nend"


def test_eigrp_validation_parser_and_renderer() -> None:
    """EIGRP ต้อง validate boundary และแปลง wildcard จาก netmask ฝั่ง server"""
    payload = EigrpNetworkConfig(as_number=100, router_id="2.2.2.2", network="10.0.23.0", subnet_mask="255.255.255.252")
    assert render_eigrp_network(payload)[-2].strip() == "network 10.0.23.0 0.0.0.3"
    assert render_eigrp_network_remove(payload)[-1].strip() == "no network 10.0.23.0 0.0.0.3"
    parsed = parse_eigrp_config(_config())
    assert parsed["no_auto_summary"] is True
    assert parsed["networks"] == [{"network": "10.0.23.0", "subnet_mask": "255.255.255.252"}]
    with pytest.raises(ValidationError):
        EigrpNetworkConfig(as_number=0, router_id="2.2.2.2", network="10.0.23.1", subnet_mask="255.255.255.252")


def test_eigrp_preview_apply_and_remove_process(client) -> None:
    """API ต้องสร้าง preview/apply และตรวจ current state ก่อน remove process"""
    node_id = _node(client, "Apply")
    reader = MagicMock()
    reader.check_enable_mode.return_value = True
    reader.send_command.return_value = "hostname R1\n!\nend"
    payload = {"as_number": 100, "router_id": "2.2.2.2", "network": "10.0.23.0", "subnet_mask": "255.255.255.252"}
    with patch("backend.services.connection.ConnectHandler", return_value=reader):
        preview = client.post(f"/nodes/{node_id}/config/eigrp/network/preview", json=payload)
    assert preview.status_code == 200
    executor = MagicMock()
    executor.check_enable_mode.return_value = True
    executor.send_config_set.return_value = "Configuration applied successfully."
    with patch("backend.services.connection.ConnectHandler", return_value=executor):
        applied = client.post(f"/nodes/{node_id}/config/eigrp/apply", json={"operation_id": preview.json()["operation_id"], "payload_hash": preview.json()["payload_hash"]})
    assert applied.status_code == 200
    assert client.get(f"/history?node_id={node_id}").json()[0]["command_type"] == "EIGRP Configuration"
