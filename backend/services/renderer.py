"""บริการ validate และ render คำสั่ง interface ผ่าน Jinja2 แบบ allowlist"""

from __future__ import annotations

import hashlib
import ipaddress
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel

from backend.models import (
    AccessPortConfig,
    BgpNeighborConfig,
    BgpNeighborState,
    BgpNeighborUpdate,
    BgpNetworkConfig,
    BgpNetworkUpdate,
    EigrpNetworkConfig,
    EigrpNetworkState,
    EigrpNetworkUpdate,
    InterfaceAdminConfig,
    InterfaceConfig,
    LoopbackConfig,
    LoopbackRemoveConfig,
    OspfNetworkConfig,
    OspfNetworkState,
    OspfNetworkUpdate,
    RipNetworkConfig,
    RipNetworkUpdate,
    RoutedPortConfig,
    RoutedPortRestoreConfig,
    StaticRouteConfig,
    StaticRouteUpdate,
    SviConfig,
    SviRemoveConfig,
    VlanConfig,
    VlanRemoveConfig,
)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_ENVIRONMENT = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    undefined=StrictUndefined,
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


def calculate_wildcard(subnet_mask: str) -> str:
    """คำนวณ wildcard mask จาก dotted decimal subnet mask"""
    mask = ipaddress.IPv4Network(f"0.0.0.0/{subnet_mask}").netmask
    return str(ipaddress.IPv4Address(int(ipaddress.IPv4Address("255.255.255.255")) - int(mask)))


def normalize_interface_payload(payload: InterfaceConfig) -> InterfaceConfig:
    """ตรวจ network boundary และคืน payload ที่ normalize แล้ว"""
    address = ipaddress.IPv4Address(payload.ip_address)
    network = ipaddress.IPv4Network(f"{address}/{payload.subnet_mask}", strict=False)
    if address.is_multicast or address.is_unspecified:
        raise ValueError("ip_address ต้องเป็น unicast IPv4 ที่ใช้งานได้")
    if payload.description and any(char in payload.description for char in "\r\n"):
        raise ValueError("description ห้ามมีบรรทัดใหม่")
    # ใช้ network calculation เป็นการตรวจ mask contiguous; ไม่แก้ค่าที่ผู้ใช้กรอก
    if network.netmask != ipaddress.IPv4Address(payload.subnet_mask):
        raise ValueError("subnet_mask ต้องเป็น dotted decimal แบบ contiguous")
    return payload


def render_interface_commands(payload: InterfaceConfig) -> list[str]:
    """render interface config จาก typed payload เป็นรายการคำสั่ง IOS"""
    normalized = normalize_interface_payload(payload)
    rendered = _ENVIRONMENT.get_template("interface.j2").render(**normalized.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_interface_admin_commands(payload: InterfaceAdminConfig) -> list[str]:
    """สร้างคำสั่งเปิดหรือปิด interface โดยคงค่า IPv4 และ description เดิม"""
    rendered = _ENVIRONMENT.get_template("interface_admin.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_interface_remove(payload: InterfaceConfig) -> list[str]:
    """สร้างคำสั่งลบ IP ของ interface ที่ตรงกับ payload"""
    normalized = normalize_interface_payload(payload)
    rendered = _ENVIRONMENT.get_template("interface_remove.j2").render(**normalized.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def normalize_loopback_payload(payload: LoopbackConfig) -> LoopbackConfig:
    """ตรวจเงื่อนไข IPv4/description ของ Loopback ก่อนสร้าง CLI"""
    address = ipaddress.IPv4Address(payload.ip_address)
    network = ipaddress.IPv4Network(f"{address}/{payload.subnet_mask}", strict=False)
    if address.is_multicast or address.is_unspecified:
        raise ValueError("ip_address ต้องเป็น unicast IPv4 ที่ใช้งานได้")
    if payload.description and any(char in payload.description for char in "\r\n"):
        raise ValueError("description ห้ามมีบรรทัดใหม่")
    if network.netmask != ipaddress.IPv4Address(payload.subnet_mask):
        raise ValueError("subnet_mask ต้องเป็น dotted decimal แบบ contiguous")
    return payload


def render_loopback_commands(payload: LoopbackConfig) -> list[str]:
    """render Loopback ใหม่จาก typed payload เป็นรายการคำสั่ง IOS"""
    normalized = normalize_loopback_payload(payload)
    rendered = _ENVIRONMENT.get_template("loopback.j2").render(**normalized.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_loopback_remove(payload: LoopbackRemoveConfig) -> list[str]:
    """render คำสั่งลบ Loopback ที่ระบุอย่างชัดเจน"""
    rendered = _ENVIRONMENT.get_template("loopback_remove.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_access_port_commands(payload: AccessPortConfig) -> list[str]:
    """render L2 access port ที่ผ่าน precondition จาก router เป็น CLI IOS"""
    if payload.description and any(char in payload.description for char in "\r\n"):
        raise ValueError("description ห้ามมีบรรทัดใหม่")
    rendered = _ENVIRONMENT.get_template("access_port.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_vlan_commands(payload: VlanConfig) -> list[str]:
    """render การสร้าง VLAN resource จาก typed payload"""
    rendered = _ENVIRONMENT.get_template("vlan.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_vlan_remove(payload: VlanRemoveConfig) -> list[str]:
    """render คำสั่งลบ VLAN resource ที่ระบุ"""
    rendered = _ENVIRONMENT.get_template("vlan_remove.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_svi_commands(payload: SviConfig) -> list[str]:
    """render SVI IPv4 จาก typed payload เป็นชุด IOS command"""
    address = ipaddress.IPv4Address(payload.ip_address)
    network = ipaddress.IPv4Network(f"{address}/{payload.subnet_mask}", strict=False)
    if address.is_multicast or address.is_unspecified:
        raise ValueError("ip_address ต้องเป็น unicast IPv4 ที่ใช้งานได้")
    if payload.description and any(char in payload.description for char in "\r\n"):
        raise ValueError("description ห้ามมีบรรทัดใหม่")
    if network.netmask != ipaddress.IPv4Address(payload.subnet_mask):
        raise ValueError("subnet_mask ต้องเป็น dotted decimal แบบ contiguous")
    rendered = _ENVIRONMENT.get_template("svi.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_svi_remove(payload: SviRemoveConfig) -> list[str]:
    """render คำสั่งลบ SVI ที่ระบุโดยไม่ลบ VLAN resource ตามไปเอง"""
    rendered = _ENVIRONMENT.get_template("svi_remove.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_routed_port_commands(payload: RoutedPortConfig) -> list[str]:
    """render การแปลง L2 port เป็น L3 routed port ตาม typed payload"""
    address = ipaddress.IPv4Address(payload.ip_address)
    network = ipaddress.IPv4Network(f"{address}/{payload.subnet_mask}", strict=False)
    if address.is_multicast or address.is_unspecified:
        raise ValueError("ip_address ต้องเป็น unicast IPv4 ที่ใช้งานได้")
    if payload.description and any(char in payload.description for char in "\r\n"):
        raise ValueError("description ห้ามมีบรรทัดใหม่")
    if network.netmask != ipaddress.IPv4Address(payload.subnet_mask):
        raise ValueError("subnet_mask ต้องเป็น dotted decimal แบบ contiguous")
    rendered = _ENVIRONMENT.get_template("routed_port.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_routed_port_restore(payload: RoutedPortRestoreConfig) -> list[str]:
    """render inverse แบบ L2 พื้นฐานตาม ADR-026 โดยไม่ restore ค่าเดิม"""
    rendered = _ENVIRONMENT.get_template("routed_port_restore.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_static_route(payload: StaticRouteConfig) -> list[str]:
    """render คำสั่งเพิ่ม Static/Default route จาก typed payload"""
    rendered = _ENVIRONMENT.get_template("static_route.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_static_route_remove(payload: StaticRouteConfig) -> list[str]:
    """render inverse command ที่ลบ Static/Default route แบบระบุ target เดิมครบถ้วน"""
    rendered = _ENVIRONMENT.get_template("static_route_remove.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_static_route_update(payload: StaticRouteUpdate) -> list[str]:
    """render การแก้ route แบบลบค่าเดิมก่อนเพิ่มค่าใหม่เพื่อไม่สร้าง ECMP โดยไม่ตั้งใจ"""
    return render_static_route_remove(payload.current) + render_static_route(payload.desired)


def render_rip_network(payload: RipNetworkConfig) -> list[str]:
    """render การเปิด/ตั้ง version และเพิ่ม RIP network พร้อมปิด auto-summary"""
    rendered = _ENVIRONMENT.get_template("rip_network.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_rip_network_remove(payload: RipNetworkConfig) -> list[str]:
    """render inverse command สำหรับลบ RIP network ที่ระบุ"""
    rendered = _ENVIRONMENT.get_template("rip_network_remove.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_rip_network_update(payload: RipNetworkUpdate) -> list[str]:
    """render การแก้ RIP network/version ภายใน router rip context เดียว"""
    commands = [
        "router rip",
        f"version {payload.desired.version}",
        f"no network {payload.current.network}",
        f"network {payload.desired.network}",
        "no auto-summary",
    ]
    return commands


def render_rip_process_remove() -> list[str]:
    """render การลบ RIP process ทั้งหมด"""
    rendered = _ENVIRONMENT.get_template("rip_process_remove.j2").render()
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def _ospf_template_values(payload: OspfNetworkConfig | OspfNetworkState) -> dict[str, str | int | None]:
    """คืนค่า OSPF พร้อม wildcard ที่คำนวณจาก netmask ฝั่ง server"""
    return {**payload.model_dump(), "wildcard": calculate_wildcard(payload.subnet_mask)}


def render_ospf_network(payload: OspfNetworkConfig) -> list[str]:
    """render OSPF process/router ID/network จาก typed payload"""
    rendered = _ENVIRONMENT.get_template("ospf_network.j2").render(**_ospf_template_values(payload))
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_ospf_network_remove(payload: OspfNetworkState) -> list[str]:
    """render inverse command สำหรับ OSPF network เดิม"""
    rendered = _ENVIRONMENT.get_template("ospf_network_remove.j2").render(**_ospf_template_values(payload))
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_ospf_network_update(payload: OspfNetworkUpdate) -> list[str]:
    """render OSPF update โดยลบ network เดิมก่อนเพิ่ม network ใหม่"""
    current = _ospf_template_values(payload.current)
    desired = _ospf_template_values(payload.desired)
    return [
        f"router ospf {desired['process_id']}",
        f"router-id {desired['router_id']}",
        f"no network {current['network']} {current['wildcard']} area {current['area']}",
        f"network {desired['network']} {desired['wildcard']} area {desired['area']}",
    ]


def render_ospf_process_remove(process_id: int) -> list[str]:
    """render การลบ OSPF process ทั้งหมดตาม process ID"""
    rendered = _ENVIRONMENT.get_template("ospf_process_remove.j2").render(process_id=process_id)
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def _eigrp_template_values(payload: EigrpNetworkConfig | EigrpNetworkState) -> dict[str, str | int | None]:
    """คืนค่า EIGRP พร้อม wildcard ที่คำนวณจาก netmask ฝั่ง server"""
    return {**payload.model_dump(), "wildcard": calculate_wildcard(payload.subnet_mask)}


def render_eigrp_network(payload: EigrpNetworkConfig) -> list[str]:
    """render EIGRP process/router ID/network/no auto-summary"""
    rendered = _ENVIRONMENT.get_template("eigrp_network.j2").render(**_eigrp_template_values(payload))
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_eigrp_network_remove(payload: EigrpNetworkState) -> list[str]:
    """render inverse EIGRP network command"""
    rendered = _ENVIRONMENT.get_template("eigrp_network_remove.j2").render(**_eigrp_template_values(payload))
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_eigrp_network_update(payload: EigrpNetworkUpdate) -> list[str]:
    """render EIGRP update แบบ remove ก่อน add"""
    current = _eigrp_template_values(payload.current)
    desired = _eigrp_template_values(payload.desired)
    return [f"router eigrp {desired['as_number']}", f"eigrp router-id {desired['router_id']}", f"no network {current['network']} {current['wildcard']}", f"network {desired['network']} {desired['wildcard']}", "no auto-summary"]


def render_eigrp_process_remove(as_number: int) -> list[str]:
    """render การลบ EIGRP process ตาม AS"""
    rendered = _ENVIRONMENT.get_template("eigrp_process_remove.j2").render(as_number=as_number)
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_bgp_neighbor(payload: BgpNeighborConfig) -> list[str]:
    """render BGP process/router ID และ neighbor จาก typed payload"""
    rendered = _ENVIRONMENT.get_template("bgp_neighbor.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_bgp_neighbor_remove(payload: BgpNeighborState) -> list[str]:
    """render inverse command ที่ลบ BGP neighbor ที่ระบุเท่านั้น"""
    rendered = _ENVIRONMENT.get_template("bgp_neighbor_remove.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_bgp_network(payload: BgpNetworkConfig) -> list[str]:
    """render BGP advertised network จาก typed payload"""
    rendered = _ENVIRONMENT.get_template("bgp_network.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_bgp_network_remove(payload: BgpNetworkConfig) -> list[str]:
    """render inverse command ที่ลบ BGP advertised network ที่ระบุ"""
    rendered = _ENVIRONMENT.get_template("bgp_network_remove.j2").render(**payload.model_dump())
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_bgp_neighbor_update(payload: BgpNeighborUpdate) -> list[str]:
    """render BGP neighbor update ใน router submode เดียวเพื่อไม่ให้ IOS error"""
    desired = payload.desired
    commands = [
        f"router bgp {desired.local_as}",
        f"no neighbor {payload.current.neighbor_ip}",
        f"bgp router-id {desired.router_id}",
        f"neighbor {desired.neighbor_ip} remote-as {desired.remote_as}",
    ]
    if desired.description:
        commands.append(f"neighbor {desired.neighbor_ip} description {desired.description}")
    return commands


def render_bgp_network_update(payload: BgpNetworkUpdate) -> list[str]:
    """render BGP network update ใน router submode เดียวเพื่อไม่ให้ IOS error"""
    desired = payload.desired
    return [
        f"router bgp {desired.local_as}",
        f"no network {payload.current.network} mask {payload.current.subnet_mask}",
        f"network {desired.network} mask {desired.subnet_mask}",
    ]


def render_bgp_process_remove(local_as: int) -> list[str]:
    """render การลบ BGP process ทั้งหมดตาม local AS"""
    rendered = _ENVIRONMENT.get_template("bgp_process_remove.j2").render(local_as=local_as)
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def render_save_config() -> list[str]:
    """render คำสั่งบันทึก config จาก template ที่ server ควบคุม"""
    rendered = _ENVIRONMENT.get_template("save_config.j2").render()
    return [line.rstrip() for line in rendered.splitlines() if line.strip()]


def hash_payload(payload: BaseModel) -> str:
    """สร้าง hash deterministic สำหรับผูก Apply กับ Preview เดิม"""
    encoded = json.dumps(
        payload.model_dump(), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
