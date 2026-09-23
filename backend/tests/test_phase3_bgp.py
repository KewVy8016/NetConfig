"""ทดสอบ Phase 3E: BGP validation, parser, preview/apply และ remove process"""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.models import BgpNeighborConfig, BgpNeighborUpdate, BgpNetworkConfig, BgpNetworkUpdate
from backend.services.parser import parse_bgp_config
from backend.services.renderer import (
    render_bgp_neighbor,
    render_bgp_neighbor_update,
    render_bgp_network,
    render_bgp_network_update,
)
from backend.tests.conftest import SSH_NODE_PAYLOAD


def _node(client) -> str:
    """สร้าง node test แยกและคืน ID"""
    response = client.post("/nodes", json={**SSH_NODE_PAYLOAD, "hostname": "BgpTest", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.72.0.20"}})
    assert response.status_code == 201
    return response.json()["id"]


def test_bgp_validation_parser_and_renderer() -> None:
    """BGP ต้อง validate network boundary และ parse neighbor/network ได้"""
    neighbor = BgpNeighborConfig(local_as=65002, router_id="2.2.2.2", neighbor_ip="10.0.23.2", remote_as=65003)
    network = BgpNetworkConfig(local_as=65002, network="2.2.2.2", subnet_mask="255.255.255.255")
    assert render_bgp_neighbor(neighbor)[-1] == " neighbor 10.0.23.2 remote-as 65003"
    assert render_bgp_network(network)[-1] == " network 2.2.2.2 mask 255.255.255.255"
    updated_neighbor = BgpNeighborConfig(local_as=65002, router_id="2.2.2.2", neighbor_ip="10.0.23.2", remote_as=65100)
    updated_network = BgpNetworkConfig(local_as=65002, network="10.0.23.0", subnet_mask="255.255.255.252")
    assert render_bgp_neighbor_update(BgpNeighborUpdate(current=neighbor, desired=updated_neighbor)) == [
        "router bgp 65002",
        "no neighbor 10.0.23.2",
        "bgp router-id 2.2.2.2",
        "neighbor 10.0.23.2 remote-as 65100",
    ]
    assert render_bgp_network_update(BgpNetworkUpdate(current=network, desired=updated_network)) == [
        "router bgp 65002",
        "no network 2.2.2.2 mask 255.255.255.255",
        "network 10.0.23.0 mask 255.255.255.252",
    ]
    parsed = parse_bgp_config("router bgp 65002\n bgp router-id 2.2.2.2\n neighbor 10.0.23.2 remote-as 65003\n network 2.2.2.2 mask 255.255.255.255\n!")
    neighbors = cast(list[dict[str, object]], parsed["neighbors"])
    assert parsed["local_as"] == 65002 and neighbors[0]["remote_as"] == 65003
    with pytest.raises(ValidationError):
        BgpNetworkConfig(local_as=65002, network="2.2.2.3", subnet_mask="255.255.255.252")


def test_bgp_neighbor_preview_apply(client) -> None:
    """API ต้องสร้าง BGP neighbor preview/apply และบันทึก history"""
    node_id = _node(client)
    reader = MagicMock()
    reader.check_enable_mode.return_value = True
    reader.send_command.return_value = "hostname R1\n!\nend"
    payload = {"local_as": 65002, "router_id": "2.2.2.2", "neighbor_ip": "10.0.23.2", "remote_as": 65003}
    with patch("backend.services.connection.ConnectHandler", return_value=reader):
        preview = client.post(f"/nodes/{node_id}/config/bgp/neighbor/preview", json=payload)
    assert preview.status_code == 200
    executor = MagicMock()
    executor.check_enable_mode.return_value = True
    executor.send_config_set.return_value = "Configuration applied successfully."
    with patch("backend.services.connection.ConnectHandler", return_value=executor):
        applied = client.post(f"/nodes/{node_id}/config/bgp/apply", json={"operation_id": preview.json()["operation_id"], "payload_hash": preview.json()["payload_hash"]})
    assert applied.status_code == 200
    assert client.get(f"/history?node_id={node_id}").json()[0]["command_type"] == "BGP Configuration"
