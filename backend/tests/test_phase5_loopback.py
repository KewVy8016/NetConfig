"""Unit และ API tests ขั้นต่ำสำหรับ Loopback vertical slice"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

from backend.models import (
    AccessPortConfig,
    LoopbackConfig,
    LoopbackRemoveConfig,
    RoutedPortConfig,
    RoutedPortRestoreConfig,
    SviConfig,
    SviRemoveConfig,
    VlanConfig,
    VlanRemoveConfig,
)
from backend.services.renderer import (
    render_access_port_commands,
    render_loopback_commands,
    render_loopback_remove,
    render_routed_port_commands,
    render_routed_port_restore,
    render_svi_commands,
    render_svi_remove,
    render_vlan_commands,
    render_vlan_remove,
)
from backend.tests.conftest import SSH_NODE_PAYLOAD


def test_loopback_renderer_create_and_remove() -> None:
    """Loopback ต้อง render เป็น IOS context ที่ตายตัวและมี inverse ชัดเจน"""
    payload = LoopbackConfig(
        loopback_id=10,
        ip_address="10.10.10.10",
        subnet_mask="255.255.255.255",
        description="Router ID",
        admin_up=True,
    )
    assert render_loopback_commands(payload) == [
        "interface Loopback10",
        " ip address 10.10.10.10 255.255.255.255",
        " description Router ID",
        " no shutdown",
    ]
    assert render_loopback_remove(LoopbackRemoveConfig(loopback_id=10)) == ["no interface Loopback10"]


def test_loopback_preview_rejects_unsafe_address_without_connection(client) -> None:
    """Preview ต้องปฏิเสธ multicast ก่อนเชื่อมต่อหรือบันทึก operation"""
    node_id = client.post(
        "/nodes",
        json={**SSH_NODE_PAYLOAD, "hostname": "Phase5Reject", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.5.1"}},
    ).json()["id"]
    with patch("backend.services.connection.ConnectHandler") as connect_handler:
        response = client.post(
            f"/nodes/{node_id}/config/loopback/preview",
            json={"loopback_id": 0, "ip_address": "224.0.0.1", "subnet_mask": "255.255.255.255", "admin_up": True},
        )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
    connect_handler.assert_not_called()


def test_loopback_apply_and_history(client) -> None:
    """Apply ต้องใช้ preview hash เดิม ส่ง CLI และสร้าง history อย่างครบถ้วน"""
    node_id = client.post(
        "/nodes",
        json={**SSH_NODE_PAYLOAD, "hostname": "Phase5Loopback", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.5.2"}},
    ).json()["id"]
    preview = client.post(
        f"/nodes/{node_id}/config/loopback/preview",
        json={"loopback_id": 5, "ip_address": "5.5.5.5", "subnet_mask": "255.255.255.255", "description": "Lab", "admin_up": True},
    ).json()
    fake_connection = MagicMock()
    fake_connection.send_config_set.return_value = "Configuration applied successfully."
    with patch("backend.services.connection.ConnectHandler", return_value=fake_connection):
        response = client.post(
            f"/nodes/{node_id}/config/loopback/apply",
            json={"operation_id": preview["operation_id"], "payload_hash": preview["payload_hash"]},
        )
    assert response.status_code == 200
    assert response.json()["overall_status"] == "success"
    assert [entry.args[0][0] for entry in fake_connection.send_config_set.call_args_list] == preview["commands"]
    history = client.get(f"/history?node_id={node_id}")
    assert history.status_code == 200
    assert history.json()[0]["command_type"] == "Loopback Configuration"


def test_capabilities_are_read_from_ios_output_not_node_name(client) -> None:
    """Router-like output ต้องรายงาน capability ไม่รองรับโดยไม่อ้าง hostname"""
    node_id = client.post(
        "/nodes",
        json={**SSH_NODE_PAYLOAD, "hostname": "CouldBeASwitch", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.5.3"}},
    ).json()["id"]
    fake_connection = MagicMock()
    fake_connection.send_command.side_effect = [
        "% Invalid input detected at '^' marker.",
        "% Invalid input detected at '^' marker.",
    ]
    with patch("backend.services.connection.ConnectHandler", return_value=fake_connection):
        response = client.get(f"/nodes/{node_id}/capabilities")
    assert response.status_code == 200
    assert response.json()["switchport_supported"] is False
    assert response.json()["vlan_supported"] is False
    assert fake_connection.send_command.call_args_list == [
        call("show interfaces switchport", use_textfsm=False),
        call("show vlan brief", use_textfsm=False),
    ]


def test_interface_capability_reads_switchport_state(client) -> None:
    """สถานะ L2/L3 ต้องได้จาก show ของพอร์ตนั้น ไม่ใช่ชื่อ node หรือชื่อ interface"""
    node_id = client.post(
        "/nodes",
        json={**SSH_NODE_PAYLOAD, "hostname": "Neutral", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.5.4"}},
    ).json()["id"]
    fake_connection = MagicMock()
    fake_connection.send_command.return_value = "Name: Gi0/1\nSwitchport: Disabled\nAdministrative Mode: static access\n"
    with patch("backend.services.connection.ConnectHandler", return_value=fake_connection):
        response = client.get(f"/nodes/{node_id}/interfaces/GigabitEthernet0/1/capabilities")
    assert response.status_code == 200
    assert response.json()["interface_name"] == "GigabitEthernet0/1"
    assert response.json()["switchport_state"] == "disabled"
    fake_connection.send_command.assert_called_once_with(
        "show interfaces GigabitEthernet0/1 switchport",
        use_textfsm=False,
    )


def test_list_vlans_returns_typed_actual_state(client) -> None:
    """VLAN list ต้องอ่านจาก IOS และคืน VLAN ID/name/ports ที่ parser ยืนยันได้"""
    node_id = client.post(
        "/nodes",
        json={**SSH_NODE_PAYLOAD, "hostname": "Layer2", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.5.5"}},
    ).json()["id"]
    fake_connection = MagicMock()
    fake_connection.send_command.return_value = (
        "VLAN Name                             Status    Ports\n"
        "---- -------------------------------- --------- -------------------------------\n"
        "1    default                          active    Gi0/1, Gi0/2\n"
        "20   USERS                            active    Gi0/3\n"
    )
    with patch("backend.services.connection.ConnectHandler", return_value=fake_connection):
        response = client.get(f"/nodes/{node_id}/vlans")
    assert response.status_code == 200
    assert response.json()["vlans"] == [
        {"vlan_id": 1, "name": "default", "status": "active", "ports": ["Gi0/1", "Gi0/2"]},
        {"vlan_id": 20, "name": "USERS", "status": "active", "ports": ["Gi0/3"]},
    ]


def test_access_port_preview_apply_and_history(client) -> None:
    """L2 access port ต้องยืนยัน switchport/VLAN ก่อน preview แล้วจึง apply ได้"""
    node_id = client.post(
        "/nodes",
        json={**SSH_NODE_PAYLOAD, "hostname": "AccessSwitch", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.5.6"}},
    ).json()["id"]
    payload = {"interface_name": "GigabitEthernet0/1", "vlan_id": 20, "description": "Users", "admin_up": True}
    assert render_access_port_commands(AccessPortConfig(**payload)) == [
        "interface GigabitEthernet0/1",
        " switchport mode access",
        " switchport access vlan 20",
        " description Users",
        " no shutdown",
    ]
    preflight_connection = MagicMock()
    preflight_connection.send_command.side_effect = [
        "Name: Gi0/1\nSwitchport: Enabled\n",
        "VLAN Name                             Status    Ports\n20   USERS                            active    Gi0/1\n",
    ]
    with patch("backend.services.connection.ConnectHandler", return_value=preflight_connection):
        preview_response = client.post(f"/nodes/{node_id}/config/access-port/preview", json=payload)
    assert preview_response.status_code == 200
    preview = preview_response.json()
    apply_connection = MagicMock()
    apply_connection.send_config_set.return_value = "Configuration applied successfully."
    with patch("backend.services.connection.ConnectHandler", return_value=apply_connection):
        apply_response = client.post(
            f"/nodes/{node_id}/config/access-port/apply",
            json={"operation_id": preview["operation_id"], "payload_hash": preview["payload_hash"]},
        )
    assert apply_response.json()["overall_status"] == "success"
    history = client.get(f"/history?node_id={node_id}").json()
    assert history[0]["command_type"] == "L2 Access Port Configuration"


def test_access_port_preview_rejects_non_l2_port(client) -> None:
    """L3/Router port ต้องไม่สร้าง preview access VLAN แม้ browser ส่ง payload มาเอง"""
    node_id = client.post(
        "/nodes",
        json={**SSH_NODE_PAYLOAD, "hostname": "Router", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.5.7"}},
    ).json()["id"]
    fake_connection = MagicMock()
    fake_connection.send_command.side_effect = [
        "% Invalid input detected at '^' marker.",
        "VLAN Name                             Status    Ports\n20   USERS                            active\n",
    ]
    with patch("backend.services.connection.ConnectHandler", return_value=fake_connection):
        response = client.post(
            f"/nodes/{node_id}/config/access-port/preview",
            json={"interface_name": "GigabitEthernet0/1", "vlan_id": 20, "admin_up": True},
        )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ACCESS_PORT_UNSUPPORTED"


def test_vlan_and_svi_renderers_have_separate_inverse_scope() -> None:
    """VLAN กับ SVI ต้อง render/remove เป็น resource แยก ไม่ลบกันโดยปริยาย"""
    assert render_vlan_commands(VlanConfig(vlan_id=20, name="USERS")) == ["vlan 20", " name USERS"]
    assert render_vlan_remove(VlanRemoveConfig(vlan_id=20)) == ["no vlan 20"]
    assert render_svi_commands(SviConfig(vlan_id=20, ip_address="192.168.20.1", subnet_mask="255.255.255.0", admin_up=True)) == [
        "interface Vlan20",
        " ip address 192.168.20.1 255.255.255.0",
        " no shutdown",
    ]
    assert render_svi_remove(SviRemoveConfig(vlan_id=20)) == ["no interface Vlan20"]


def test_vlan_preview_apply_and_history(client) -> None:
    """VLAN ใหม่ต้องตรวจ duplicate ก่อน preview แล้ว apply/history ผ่าน contract เดียวกัน"""
    node_id = client.post(
        "/nodes",
        json={**SSH_NODE_PAYLOAD, "hostname": "VlanSwitch", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.5.8"}},
    ).json()["id"]
    preflight_connection = MagicMock()
    preflight_connection.send_command.return_value = "VLAN Name                             Status    Ports\n1    default                          active\n"
    with patch("backend.services.connection.ConnectHandler", return_value=preflight_connection):
        preview_response = client.post(f"/nodes/{node_id}/config/vlan/preview", json={"vlan_id": 20, "name": "USERS"})
    assert preview_response.status_code == 200
    preview = preview_response.json()
    apply_connection = MagicMock()
    apply_connection.send_config_set.return_value = "Configuration applied successfully."
    with patch("backend.services.connection.ConnectHandler", return_value=apply_connection):
        apply_response = client.post(
            f"/nodes/{node_id}/config/vlan-svi/apply",
            json={"operation_id": preview["operation_id"], "payload_hash": preview["payload_hash"]},
        )
    assert apply_response.json()["overall_status"] == "success"
    assert client.get(f"/history?node_id={node_id}").json()[0]["command_type"] == "VLAN/SVI Configuration"


def test_svi_preview_requires_existing_vlan(client) -> None:
    """Browser ต้องไม่สร้าง SVI บน VLAN ที่ไม่มีอยู่จริง"""
    node_id = client.post(
        "/nodes",
        json={**SSH_NODE_PAYLOAD, "hostname": "NoVlan", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.5.9"}},
    ).json()["id"]
    fake_connection = MagicMock()
    fake_connection.send_command.return_value = "VLAN Name                             Status    Ports\n1    default                          active\n"
    with patch("backend.services.connection.ConnectHandler", return_value=fake_connection):
        response = client.post(
            f"/nodes/{node_id}/config/svi/preview",
            json={"vlan_id": 20, "ip_address": "192.168.20.1", "subnet_mask": "255.255.255.0", "admin_up": True},
        )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "VLAN_NOT_FOUND"


def test_routed_port_preview_apply_and_basic_restore_renderer(client) -> None:
    """L3 workflow ต้องยืนยัน L2 state ก่อน apply และ restore ไม่คืนค่า L2 เดิม"""
    payload = {
        "interface_name": "GigabitEthernet0/2",
        "ip_address": "10.0.0.1",
        "subnet_mask": "255.255.255.252",
        "description": "Routed uplink",
        "admin_up": True,
    }
    assert render_routed_port_commands(RoutedPortConfig(**payload)) == [
        "interface GigabitEthernet0/2",
        " no switchport",
        " ip address 10.0.0.1 255.255.255.252",
        " description Routed uplink",
        " no shutdown",
    ]
    assert render_routed_port_restore(RoutedPortRestoreConfig(interface_name="GigabitEthernet0/2")) == [
        "interface GigabitEthernet0/2",
        " no ip address",
        " switchport",
    ]
    node_id = client.post(
        "/nodes",
        json={**SSH_NODE_PAYLOAD, "hostname": "L3Switch", "device_kind": "switch", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.5.10"}},
    ).json()["id"]
    preflight_connection = MagicMock()
    preflight_connection.send_command.return_value = "Name: Gi0/2\nSwitchport: Enabled\n"
    with patch("backend.services.connection.ConnectHandler", return_value=preflight_connection):
        preview_response = client.post(f"/nodes/{node_id}/config/routed-port/preview", json=payload)
    assert preview_response.status_code == 200
    preview = preview_response.json()
    apply_connection = MagicMock()
    apply_connection.send_config_set.return_value = "Configuration applied successfully."
    with patch("backend.services.connection.ConnectHandler", return_value=apply_connection):
        apply_response = client.post(
            f"/nodes/{node_id}/config/routed-port/apply",
            json={"operation_id": preview["operation_id"], "payload_hash": preview["payload_hash"]},
        )
    assert apply_response.json()["overall_status"] == "success"
    assert client.get(f"/history?node_id={node_id}").json()[0]["command_type"] == "L3 Routed Port Configuration"


def test_routed_port_restore_preview_and_router_rejection(client) -> None:
    """Restore ใช้ได้เฉพาะ L3 state และ Router ต้องถูกปฏิเสธก่อนมี preview"""
    restore_node = client.post(
        "/nodes",
        json={**SSH_NODE_PAYLOAD, "hostname": "RestoreSwitch", "device_kind": "switch", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.5.11"}},
    ).json()["id"]
    l3_connection = MagicMock()
    l3_connection.send_command.return_value = "Name: Gi0/2\nSwitchport: Disabled\n"
    with patch("backend.services.connection.ConnectHandler", return_value=l3_connection):
        restore = client.post(
            f"/nodes/{restore_node}/config/routed-port/restore/preview",
            json={"interface_name": "GigabitEthernet0/2"},
        )
    assert restore.status_code == 200
    assert restore.json()["commands"] == ["interface GigabitEthernet0/2", " no ip address", " switchport"]

    router_node = client.post(
        "/nodes",
        json={**SSH_NODE_PAYLOAD, "hostname": "Router", "device_kind": "router", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.5.12"}},
    ).json()["id"]
    router_connection = MagicMock()
    router_connection.send_command.return_value = "% Invalid input detected at '^' marker."
    with patch("backend.services.connection.ConnectHandler", return_value=router_connection):
        rejected = client.post(
            f"/nodes/{router_node}/config/routed-port/preview",
            json={"interface_name": "GigabitEthernet0/1", "ip_address": "10.0.0.1", "subnet_mask": "255.255.255.252", "admin_up": True},
        )
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "ROUTED_PORT_UNSUPPORTED"


def test_routed_port_partial_cli_failure_is_recorded(client) -> None:
    """CLI ที่ล้มหลัง no switchport ต้องคืน partial_failed และเก็บ history ตามจริง"""
    node_id = client.post(
        "/nodes",
        json={**SSH_NODE_PAYLOAD, "hostname": "PartialL3", "device_kind": "switch", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "10.0.5.13"}},
    ).json()["id"]
    preflight_connection = MagicMock()
    preflight_connection.send_command.return_value = "Name: Gi0/1\nSwitchport: Enabled\n"
    payload = {"interface_name": "GigabitEthernet0/1", "ip_address": "10.0.0.1", "subnet_mask": "255.255.255.252", "admin_up": True}
    with patch("backend.services.connection.ConnectHandler", return_value=preflight_connection):
        preview = client.post(f"/nodes/{node_id}/config/routed-port/preview", json=payload).json()
    results = [
        (preview["commands"][0], True, "interface accepted", None),
        (preview["commands"][1], True, "no switchport accepted", None),
        (preview["commands"][2], False, "% Invalid input", "CLI_REJECTED"),
    ]
    with patch("backend.routers.config.send_config_commands", return_value=results):
        applied = client.post(
            f"/nodes/{node_id}/config/routed-port/apply",
            json={"operation_id": preview["operation_id"], "payload_hash": preview["payload_hash"]},
        )
    assert applied.status_code == 200
    assert applied.json()["overall_status"] == "partial_failed"
    assert applied.json()["results"][-1]["error_code"] == "CLI_REJECTED"
    assert client.get(f"/history?node_id={node_id}").json()[0]["overall_status"] == "partial_failed"
