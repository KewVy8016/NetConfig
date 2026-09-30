"""HTTP boundary สำหรับ interface preview/apply, Show allowlist และ command history"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal, NoReturn

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from backend.database import get_db
from backend.models import (
    AccessPortConfig,
    ApplyRequest,
    ApplyResponse,
    BgpNeighborConfig,
    BgpNeighborState,
    BgpNeighborUpdate,
    BgpNetworkConfig,
    BgpNetworkUpdate,
    BgpProcessConfig,
    BgpStateResponse,
    CommandResult,
    DeviceCapabilitiesResponse,
    EigrpNetworkConfig,
    EigrpNetworkState,
    EigrpNetworkUpdate,
    EigrpProcessConfig,
    EigrpStateResponse,
    ErrorResponse,
    HistoryEntry,
    HistoryNodeOption,
    InterfaceAdminConfig,
    InterfaceCapabilitiesResponse,
    InterfaceConfig,
    InterfaceCurrentResponse,
    LoopbackConfig,
    LoopbackRemoveConfig,
    OspfNetworkConfig,
    OspfNetworkState,
    OspfNetworkUpdate,
    OspfProcessConfig,
    OspfStateResponse,
    PreviewResponse,
    RipNetworkConfig,
    RipNetworkUpdate,
    RipProcessConfig,
    RipStateResponse,
    RoutedPortConfig,
    RoutedPortRestoreConfig,
    SaveConfigRequest,
    ShowResponse,
    StaticRouteConfig,
    StaticRouteListResponse,
    StaticRouteUpdate,
    SviConfig,
    SviRemoveConfig,
    VlanConfig,
    VlanListResponse,
    VlanRemoveConfig,
)
from backend.services.connection import (
    EnableSecretRequiredError,
    build_transport_from_row,
    get_node_lock,
    send_config_commands,
    send_show_command,
    send_show_commands,
)
from backend.services.encryption import redact_text
from backend.services.parser import (
    is_unsupported_ios_command,
    parse_bgp_config,
    parse_eigrp_config,
    parse_ospf_config,
    parse_rip_config,
    parse_show_interface_detail,
    parse_show_ip_interface_brief,
    parse_show_ip_route,
    parse_show_vlan_brief,
    parse_static_routes,
    parse_switchport_state,
)
from backend.services.renderer import (
    hash_payload,
    render_access_port_commands,
    render_bgp_neighbor,
    render_bgp_neighbor_remove,
    render_bgp_neighbor_update,
    render_bgp_network,
    render_bgp_network_remove,
    render_bgp_network_update,
    render_bgp_process_remove,
    render_eigrp_network,
    render_eigrp_network_remove,
    render_eigrp_network_update,
    render_eigrp_process_remove,
    render_interface_admin_commands,
    render_interface_commands,
    render_interface_remove,
    render_loopback_commands,
    render_loopback_remove,
    render_ospf_network,
    render_ospf_network_remove,
    render_ospf_network_update,
    render_ospf_process_remove,
    render_rip_network,
    render_rip_network_remove,
    render_rip_network_update,
    render_rip_process_remove,
    render_routed_port_commands,
    render_routed_port_restore,
    render_save_config,
    render_static_route,
    render_static_route_remove,
    render_static_route_update,
    render_svi_commands,
    render_svi_remove,
    render_vlan_commands,
    render_vlan_remove,
)

router = APIRouter(tags=["config"])

_PREVIEW_TTL = timedelta(minutes=5)
_SHOW_COMMANDS: dict[str, Literal["interface", "route"] | None] = {
    "show ip route": "route",
    "show ip interface brief": "interface",
    "show ip protocols": None,
    "show ip ospf neighbor": None,
    "show ip eigrp neighbors": None,
    "show ip bgp summary": None,
    "show running-config": None,
}
_INTERFACE_NAME_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9/_.-]{0,63}")


def _now() -> datetime:
    """คืนเวลาปัจจุบันแบบ UTC ที่มี timezone"""
    return datetime.now(UTC)


def _error(code: str, message_th: str, correlation_id: str, code_status: int, details: dict | None = None) -> NoReturn:
    """สร้าง HTTP error response มาตรฐานโดยไม่เผยรายละเอียดภายใน"""
    raise HTTPException(
        status_code=code_status,
        detail={
            "code": code,
            "message_th": message_th,
            "correlation_id": correlation_id,
            "details": details,
        },
    )


def _get_node_row(node_id: str, correlation_id: str):
    """โหลด node row หรือหยุดด้วย error ที่ผู้ใช้เข้าใจได้"""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
    if row is None:
        _error("NODE_NOT_FOUND", f"ไม่พบ node ID: {node_id}", correlation_id, status.HTTP_404_NOT_FOUND)
    return dict(row)


def _persist_preview(
    node_id: str,
    payload: BaseModel,
    commands: list[str],
    operation_type: str,
    warnings: list[str] | None = None,
) -> PreviewResponse:
    """บันทึก typed preview และคืน operation/hash ที่ใช้ Apply ได้ครั้งเดียว"""
    correlation_id = str(uuid.uuid4())
    _get_node_row(node_id, correlation_id)
    payload_digest = hash_payload(payload)
    operation_id = str(uuid.uuid4())
    created_at = _now()
    expires_at = created_at + _PREVIEW_TTL
    with get_db() as conn:
        conn.execute(
            """INSERT INTO operations
               (id, correlation_id, node_id, operation_type, payload_hash, status,
                rendered_commands, result_json, error_code, created_at)
               VALUES (?, ?, ?, ?, ?, 'previewed', ?, NULL, NULL, ?)""",
            (
                operation_id,
                correlation_id,
                node_id,
                operation_type,
                payload_digest,
                json.dumps({"commands": commands, "payload": payload.model_dump(), "expires_at": expires_at.isoformat()}),
                created_at.isoformat(),
            ),
        )
    return PreviewResponse(
        operation_id=operation_id,
        node_id=node_id,
        operation_type=operation_type,
        payload_hash=payload_digest,
        commands=commands,
        expires_at=expires_at.isoformat(),
        warnings=warnings or ["การ Apply จะเปลี่ยน running-config และยังไม่บันทึก NVRAM"],
    )


def _render_interface_preview(node_id: str, payload: InterfaceConfig, remove: bool) -> PreviewResponse:
    """ตรวจและ render interface preview โดยยังไม่เชื่อมต่ออุปกรณ์"""
    correlation_id = str(uuid.uuid4())
    try:
        commands = render_interface_remove(payload) if remove else render_interface_commands(payload)
    except ValueError as exc:
        _error("VALIDATION_ERROR", str(exc), correlation_id, status.HTTP_422_UNPROCESSABLE_ENTITY)
    operation_type = "interface_remove" if remove else "interface"
    return _persist_preview(node_id, payload, commands, operation_type)


@router.post(
    "/nodes/{node_id}/config/interface/preview",
    response_model=PreviewResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def preview_interface(node_id: str, payload: InterfaceConfig) -> PreviewResponse:
    """สร้าง preview interface โดยยังไม่เชื่อมต่อหรือส่งคำสั่งไป device"""
    return _render_interface_preview(node_id, payload, remove=False)


def _render_interface_admin_preview(node_id: str, payload: InterfaceAdminConfig) -> PreviewResponse:
    """สร้าง preview เปิด/ปิด interface โดยไม่เปลี่ยน IPv4 เดิม"""
    correlation_id = str(uuid.uuid4())
    try:
        commands = render_interface_admin_commands(payload)
    except ValueError as exc:
        _error("VALIDATION_ERROR", str(exc), correlation_id, status.HTTP_422_UNPROCESSABLE_ENTITY)
    return _persist_preview(node_id, payload, commands, "interface_admin")


@router.post(
    "/nodes/{node_id}/config/interface/admin/preview",
    response_model=PreviewResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def preview_interface_admin(node_id: str, payload: InterfaceAdminConfig) -> PreviewResponse:
    """สร้าง preview สำหรับ toggle admin state ของ interface"""
    return _render_interface_admin_preview(node_id, payload)


@router.post(
    "/nodes/{node_id}/config/interface/remove/preview",
    response_model=PreviewResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def preview_interface_remove(node_id: str, payload: InterfaceConfig) -> PreviewResponse:
    """สร้าง preview สำหรับลบ IP ของ interface เดิม"""
    return _render_interface_preview(node_id, payload, remove=True)


def _render_loopback_preview(
    node_id: str,
    payload: LoopbackConfig | LoopbackRemoveConfig,
    remove: bool,
) -> PreviewResponse:
    """ตรวจและ render Loopback preview โดยยังไม่เชื่อมต่ออุปกรณ์"""
    correlation_id = str(uuid.uuid4())
    try:
        if remove:
            if not isinstance(payload, LoopbackRemoveConfig):
                raise ValueError("ข้อมูลลบ Loopback ไม่ถูกต้อง")
            commands = render_loopback_remove(payload)
        else:
            if not isinstance(payload, LoopbackConfig):
                raise ValueError("ข้อมูลตั้งค่า Loopback ไม่ถูกต้อง")
            commands = render_loopback_commands(payload)
    except ValueError as exc:
        _error("VALIDATION_ERROR", str(exc), correlation_id, status.HTTP_422_UNPROCESSABLE_ENTITY)
    operation_type = "loopback_remove" if remove else "loopback"
    return _persist_preview(node_id, payload, commands, operation_type)


async def _validate_access_port_preconditions(
    node_id: str,
    node_row: dict,
    payload: AccessPortConfig,
    correlation_id: str,
) -> None:
    """ยืนยันว่า port เป็น L2 switchport และ VLAN มีอยู่ก่อน preview"""
    lock = await get_node_lock(node_id)
    async with lock:
        try:
            switchport_output, vlan_output = await run_in_threadpool(
                send_show_commands,
                build_transport_from_row(node_row),
                [f"show interfaces {payload.interface_name} switchport", "show vlan brief"],
            )
        except Exception as exc:
            _error(
                "ACCESS_PORT_READ_FAILED",
                "ตรวจสอบ port หรือ VLAN จากอุปกรณ์ไม่สำเร็จ",
                correlation_id,
                status.HTTP_502_BAD_GATEWAY,
                {"reason": redact_text(str(exc))},
            )
    if parse_switchport_state(switchport_output) != "enabled":
        _error(
            "ACCESS_PORT_UNSUPPORTED",
            "Interface นี้ไม่อยู่ในโหมด L2 switchport จึงตั้ง Access VLAN ไม่ได้",
            correlation_id,
            status.HTTP_409_CONFLICT,
        )
    if is_unsupported_ios_command(vlan_output):
        _error("VLAN_UNSUPPORTED", "อุปกรณ์นี้ไม่รองรับ VLAN configuration", correlation_id, status.HTTP_409_CONFLICT)
    vlans = parse_show_vlan_brief(vlan_output)
    if vlans is None:
        _error("VLAN_PARSE_FAILED", "อ่านรูปแบบ VLAN จากอุปกรณ์ไม่สำเร็จ", correlation_id, status.HTTP_502_BAD_GATEWAY)
    if not any(vlan["vlan_id"] == payload.vlan_id for vlan in vlans):
        _error("VLAN_NOT_FOUND", "ไม่พบ VLAN ที่เลือกบนอุปกรณ์ กรุณา Refresh", correlation_id, status.HTTP_409_CONFLICT)


@router.post(
    "/nodes/{node_id}/config/access-port/preview",
    response_model=PreviewResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
async def preview_access_port(node_id: str, payload: AccessPortConfig) -> PreviewResponse:
    """ตรวจ L2/VLAN actual state แล้วสร้าง preview access port โดยยังไม่เปลี่ยน device"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    await _validate_access_port_preconditions(node_id, node_row, payload, correlation_id)
    try:
        commands = render_access_port_commands(payload)
    except ValueError as exc:
        _error("VALIDATION_ERROR", str(exc), correlation_id, status.HTTP_422_UNPROCESSABLE_ENTITY)
    return _persist_preview(
        node_id,
        payload,
        commands,
        "access_port",
        ["การ Apply จะเปลี่ยนพอร์ตเป็น L2 access port และยังไม่บันทึก NVRAM"],
    )


async def _validate_routed_port_state(
    node_id: str,
    node_row: dict,
    interface_name: str,
    expected_state: str,
    correlation_id: str,
) -> None:
    """ยืนยัน switchport current state ก่อนแปลงหรือ restore routed port"""
    lock = await get_node_lock(node_id)
    async with lock:
        try:
            output = await run_in_threadpool(
                send_show_command,
                build_transport_from_row(node_row),
                f"show interfaces {interface_name} switchport",
            )
        except Exception as exc:
            _error("ROUTED_PORT_READ_FAILED", "ตรวจสอบ Switchport จากอุปกรณ์ไม่สำเร็จ", correlation_id, status.HTTP_502_BAD_GATEWAY, {"reason": redact_text(str(exc))})
    state = parse_switchport_state(output)
    if state != expected_state:
        if state == "unsupported":
            message = "อุปกรณ์หรือ Interface นี้ไม่รองรับ switchport/routed-port workflow"
        elif expected_state == "enabled":
            message = "Interface นี้ไม่ได้อยู่ในโหมด L2 switchport จึงแปลงเป็น L3 routed port ไม่ได้"
        else:
            message = "Interface นี้ไม่ได้อยู่ในโหมด L3 routed port จึง Restore เป็น switchport ไม่ได้"
        _error("ROUTED_PORT_UNSUPPORTED", message, correlation_id, status.HTTP_409_CONFLICT)


@router.post("/nodes/{node_id}/config/routed-port/preview", response_model=PreviewResponse)
async def preview_routed_port(node_id: str, payload: RoutedPortConfig) -> PreviewResponse:
    """ตรวจ L2 switchport แล้วสร้าง preview แปลงเป็น L3 routed port"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    await _validate_routed_port_state(node_id, node_row, payload.interface_name, "enabled", correlation_id)
    try:
        commands = render_routed_port_commands(payload)
    except ValueError as exc:
        _error("VALIDATION_ERROR", str(exc), correlation_id, status.HTTP_422_UNPROCESSABLE_ENTITY)
    return _persist_preview(
        node_id,
        payload,
        commands,
        "routed_port",
        ["การ Apply จะเปลี่ยน L2 switchport เป็น L3 routed port และยังไม่บันทึก NVRAM"],
    )


@router.post("/nodes/{node_id}/config/routed-port/restore/preview", response_model=PreviewResponse)
async def preview_routed_port_restore(node_id: str, payload: RoutedPortRestoreConfig) -> PreviewResponse:
    """สร้าง preview คืน L3 routed port เป็น L2 switchport พื้นฐานตาม ADR-026"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    await _validate_routed_port_state(node_id, node_row, payload.interface_name, "disabled", correlation_id)
    return _persist_preview(
        node_id,
        payload,
        render_routed_port_restore(payload),
        "routed_port_restore",
        ["การ Apply จะลบ IPv4 แล้วคืน switchport พื้นฐาน โดยไม่ restore VLAN/trunk/description/admin state เดิม"],
    )


async def _read_vlan_state(node_id: str, node_row: dict, correlation_id: str) -> list[dict[str, object]]:
    """อ่าน VLAN actual state ด้วย command ตายตัวก่อน create/remove SVI/VLAN"""
    lock = await get_node_lock(node_id)
    async with lock:
        try:
            output = await run_in_threadpool(
                send_show_command,
                build_transport_from_row(node_row),
                "show vlan brief",
            )
        except Exception as exc:
            _error("VLAN_READ_FAILED", "อ่าน VLAN จากอุปกรณ์ไม่สำเร็จ", correlation_id, status.HTTP_502_BAD_GATEWAY, {"reason": redact_text(str(exc))})
    if is_unsupported_ios_command(output):
        _error("VLAN_UNSUPPORTED", "อุปกรณ์นี้ไม่รองรับ VLAN configuration", correlation_id, status.HTTP_409_CONFLICT)
    vlans = parse_show_vlan_brief(output)
    if vlans is None:
        _error("VLAN_PARSE_FAILED", "อ่านรูปแบบ VLAN จากอุปกรณ์ไม่สำเร็จ", correlation_id, status.HTTP_502_BAD_GATEWAY)
    return vlans


async def _read_interface_inventory(node_id: str, node_row: dict, correlation_id: str) -> list[dict[str, str]]:
    """อ่าน inventory ที่ parser ยืนยันได้ก่อนจัดการ SVI"""
    lock = await get_node_lock(node_id)
    async with lock:
        try:
            output = await run_in_threadpool(
                send_show_command,
                build_transport_from_row(node_row),
                "show ip interface brief",
            )
        except Exception as exc:
            _error("INTERFACE_READ_FAILED", "อ่าน Interface จากอุปกรณ์ไม่สำเร็จ", correlation_id, status.HTTP_502_BAD_GATEWAY, {"reason": redact_text(str(exc))})
    interfaces = parse_show_ip_interface_brief(output)
    if interfaces is None:
        _error("INTERFACE_PARSE_FAILED", "อ่านรูปแบบ Interface จากอุปกรณ์ไม่สำเร็จ", correlation_id, status.HTTP_502_BAD_GATEWAY)
    return interfaces


@router.post("/nodes/{node_id}/config/vlan/preview", response_model=PreviewResponse)
async def preview_vlan(node_id: str, payload: VlanConfig) -> PreviewResponse:
    """ตรวจ VLAN ซ้ำจาก actual state แล้วสร้าง preview create VLAN"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    vlans = await _read_vlan_state(node_id, node_row, correlation_id)
    if any(vlan["vlan_id"] == payload.vlan_id for vlan in vlans):
        _error("VLAN_DUPLICATE", "VLAN นี้มีอยู่แล้ว กรุณาเลือกหมายเลขอื่น", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_vlan_commands(payload), "vlan", ["การ Apply จะสร้าง VLAN ใหม่และยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/vlan/remove/preview", response_model=PreviewResponse)
async def preview_vlan_remove(node_id: str, payload: VlanRemoveConfig) -> PreviewResponse:
    """ตรวจว่าไม่มี SVI อ้าง VLAN ก่อนสร้าง preview ลบ VLAN"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    vlans = await _read_vlan_state(node_id, node_row, correlation_id)
    if not any(vlan["vlan_id"] == payload.vlan_id for vlan in vlans):
        _error("VLAN_NOT_FOUND", "ไม่พบ VLAN ที่ต้องการลบ", correlation_id, status.HTTP_409_CONFLICT)
    interfaces = await _read_interface_inventory(node_id, node_row, correlation_id)
    if any(interface["interface"].lower() == f"vlan{payload.vlan_id}".lower() for interface in interfaces):
        _error("SVI_EXISTS", "ต้องลบ SVI ของ VLAN นี้ก่อนลบ VLAN", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_vlan_remove(payload), "vlan_remove", ["การ Apply จะลบ VLAN นี้และยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/svi/preview", response_model=PreviewResponse)
async def preview_svi(node_id: str, payload: SviConfig) -> PreviewResponse:
    """ตรวจ VLAN/SVI actual state แล้วสร้าง preview SVI ใหม่"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    vlans = await _read_vlan_state(node_id, node_row, correlation_id)
    if not any(vlan["vlan_id"] == payload.vlan_id for vlan in vlans):
        _error("VLAN_NOT_FOUND", "ต้องสร้างหรือเลือก VLAN ที่มีอยู่ก่อนตั้ง SVI", correlation_id, status.HTTP_409_CONFLICT)
    interfaces = await _read_interface_inventory(node_id, node_row, correlation_id)
    if any(interface["interface"].lower() == f"vlan{payload.vlan_id}".lower() for interface in interfaces):
        _error("SVI_DUPLICATE", "SVI ของ VLAN นี้มีอยู่แล้ว กรุณา Refresh", correlation_id, status.HTTP_409_CONFLICT)
    try:
        commands = render_svi_commands(payload)
    except ValueError as exc:
        _error("VALIDATION_ERROR", str(exc), correlation_id, status.HTTP_422_UNPROCESSABLE_ENTITY)
    return _persist_preview(node_id, payload, commands, "svi", ["การ Apply จะสร้าง SVI ใหม่และยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/svi/remove/preview", response_model=PreviewResponse)
async def preview_svi_remove(node_id: str, payload: SviRemoveConfig) -> PreviewResponse:
    """ยืนยัน SVI มีอยู่จริงก่อนสร้าง preview ลบ resource นี้"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    interfaces = await _read_interface_inventory(node_id, node_row, correlation_id)
    if not any(interface["interface"].lower() == f"vlan{payload.vlan_id}".lower() for interface in interfaces):
        _error("SVI_NOT_FOUND", "ไม่พบ SVI ที่ต้องการลบ", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_svi_remove(payload), "svi_remove", ["การ Apply จะลบ SVI นี้และยังไม่บันทึก NVRAM"])


@router.post(
    "/nodes/{node_id}/config/loopback/preview",
    response_model=PreviewResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def preview_loopback(node_id: str, payload: LoopbackConfig) -> PreviewResponse:
    """สร้าง preview Loopback ใหม่โดยยังไม่ส่งคำสั่งไป device"""
    return _render_loopback_preview(node_id, payload, remove=False)


@router.post(
    "/nodes/{node_id}/config/loopback/remove/preview",
    response_model=PreviewResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def preview_loopback_remove(node_id: str, payload: LoopbackRemoveConfig) -> PreviewResponse:
    """สร้าง preview สำหรับลบ Loopback ที่ระบุ"""
    return _render_loopback_preview(node_id, payload, remove=True)


def _load_preview_operation(
    node_id: str,
    request: ApplyRequest,
    correlation_id: str,
    allowed_types: set[str],
) -> tuple[dict, dict]:
    """โหลดและตรวจชนิด, hash, สถานะ และ TTL ของ preview ก่อน Apply"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM operations WHERE id = ? AND node_id = ?",
            (request.operation_id, node_id),
        ).fetchone()
    if row is None or row["operation_type"] not in allowed_types:
        _error("PREVIEW_NOT_FOUND", "ไม่พบ preview ที่ขอ apply", correlation_id, status.HTTP_404_NOT_FOUND)
    operation = dict(row)
    if operation["status"] != "previewed":
        _error("PREVIEW_EXPIRED", "preview นี้ถูกใช้ไปแล้วหรือหมดอายุ", correlation_id, status.HTTP_409_CONFLICT)
    if operation["payload_hash"] != request.payload_hash:
        _error("PREVIEW_HASH_MISMATCH", "ข้อมูลเปลี่ยนหลัง preview กรุณาสร้าง preview ใหม่", correlation_id, status.HTTP_409_CONFLICT)
    rendered = json.loads(operation["rendered_commands"])
    if _now() >= datetime.fromisoformat(rendered["expires_at"]):
        _error("PREVIEW_EXPIRED", "preview หมดอายุ กรุณาสร้าง preview ใหม่", correlation_id, status.HTTP_409_CONFLICT)
    return operation, rendered


async def _execute_config_commands(
    node_id: str,
    node_row: dict,
    commands: list[str],
    correlation_id: str,
) -> tuple[list[CommandResult], Literal["success", "failed", "partial_failed"]]:
    """ส่ง config ภายใต้ node lock และแปลงผลลัพธ์เป็น domain status"""
    lock = await get_node_lock(node_id)
    if lock.locked():
        _error("NODE_BUSY", "Node นี้กำลังถูกใช้งานอยู่ กรุณารอสักครู่", correlation_id, status.HTTP_409_CONFLICT)
    async with lock:
        try:
            transport = build_transport_from_row(node_row)
            raw_results = await run_in_threadpool(send_config_commands, transport, commands)
            results = [
                CommandResult(command=command, status="success" if ok else "failed", output=output, error_code=error_code)
                for command, ok, output, error_code in raw_results
            ]
        except EnableSecretRequiredError as exc:
            results = [CommandResult(command=commands[0], status="failed", output=redact_text(str(exc)), error_code="ENABLE_SECRET_REQUIRED")]
        except Exception as exc:
            results = [CommandResult(command=commands[0], status="failed", output=redact_text(str(exc)), error_code="CONNECTION_ERROR")]
    if not results or all(item.status == "success" for item in results):
        return results, "success"
    if results[0].status == "failed":
        return results, "failed"
    return results, "partial_failed"


def _record_apply_result(
    node_id: str,
    request: ApplyRequest,
    correlation_id: str,
    command_type: str,
    commands: list[str],
    results: list[CommandResult],
    overall_status: str,
) -> None:
    """ปิด operation และเพิ่ม immutable command history สำหรับ config mutation"""
    result_json = json.dumps([item.model_dump() for item in results], ensure_ascii=False)
    failed_result = next((item for item in results if item.status == "failed"), None)
    error_code = None if failed_result is None else failed_result.error_code or "CONFIG_APPLY_FAILED"
    with get_db() as conn:
        node_hostname = conn.execute("SELECT hostname FROM nodes WHERE id = ?", (node_id,)).fetchone()[0]
        conn.execute(
            "UPDATE operations SET status = ?, result_json = ?, error_code = ? WHERE id = ?",
            (overall_status, result_json, error_code, request.operation_id),
        )
        conn.execute(
            """INSERT INTO command_history
               (id, correlation_id, node_id, node_hostname, operation_id, command_type, commands_json,
                result_json, overall_status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()), correlation_id, node_id, node_hostname, request.operation_id,
                command_type, json.dumps(commands, ensure_ascii=False),
                result_json, overall_status, _now().isoformat(),
            ),
        )


async def _apply_preview(
    node_id: str,
    request: ApplyRequest,
    allowed_types: set[str],
    command_type: str,
) -> ApplyResponse:
    """ใช้ preview ที่ตรวจครบแล้วส่ง config และบันทึก audit แบบใช้ร่วมทุก feature"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    _, rendered = _load_preview_operation(node_id, request, correlation_id, allowed_types)
    commands = rendered["commands"]
    results, overall_status = await _execute_config_commands(node_id, node_row, commands, correlation_id)
    _record_apply_result(node_id, request, correlation_id, command_type, commands, results, overall_status)
    return ApplyResponse(
        operation_id=request.operation_id,
        node_id=node_id,
        correlation_id=correlation_id,
        overall_status=overall_status,
        results=results,
    )


@router.post(
    "/nodes/{node_id}/config/interface/apply",
    response_model=ApplyResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def apply_interface(node_id: str, request: ApplyRequest) -> ApplyResponse:
    """ตรวจ preview TTL/hash แล้วส่งคำสั่งทีละบรรทัดพร้อมบันทึก history"""
    return await _apply_preview(
        node_id,
        request,
        {"interface", "interface_remove"},
        "Interface Configuration",
    )


@router.post(
    "/nodes/{node_id}/config/interface/admin/apply",
    response_model=ApplyResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def apply_interface_admin(node_id: str, request: ApplyRequest) -> ApplyResponse:
    """Apply preview ของ admin state พร้อมบันทึกผลรายคำสั่ง"""
    return await _apply_preview(
        node_id,
        request,
        {"interface_admin"},
        "Interface Admin State",
    )


@router.post(
    "/nodes/{node_id}/config/loopback/apply",
    response_model=ApplyResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def apply_loopback(node_id: str, request: ApplyRequest) -> ApplyResponse:
    """Apply Loopback preview ที่ยังมี hash และ TTL ถูกต้อง พร้อมบันทึก history"""
    return await _apply_preview(
        node_id,
        request,
        {"loopback", "loopback_remove"},
        "Loopback Configuration",
    )


@router.post(
    "/nodes/{node_id}/config/access-port/apply",
    response_model=ApplyResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def apply_access_port(node_id: str, request: ApplyRequest) -> ApplyResponse:
    """Apply access-port preview ที่ผ่าน TTL/hash และบันทึก history"""
    return await _apply_preview(
        node_id,
        request,
        {"access_port"},
        "L2 Access Port Configuration",
    )


@router.post("/nodes/{node_id}/config/routed-port/apply", response_model=ApplyResponse)
async def apply_routed_port(node_id: str, request: ApplyRequest) -> ApplyResponse:
    """Apply routed-port preview หรือ basic-L2 restore พร้อม history"""
    return await _apply_preview(
        node_id,
        request,
        {"routed_port", "routed_port_restore"},
        "L3 Routed Port Configuration",
    )


@router.post("/nodes/{node_id}/config/vlan-svi/apply", response_model=ApplyResponse)
async def apply_vlan_svi(node_id: str, request: ApplyRequest) -> ApplyResponse:
    """Apply preview ของ VLAN/SVI พร้อม history แยกจาก L2 access port"""
    return await _apply_preview(
        node_id,
        request,
        {"vlan", "vlan_remove", "svi", "svi_remove"},
        "VLAN/SVI Configuration",
    )


def _route_signature(route: dict) -> tuple[str, str, str]:
    """คืน identity ของ Static route เพื่อเทียบ duplicate โดยไม่พึ่งลำดับ field"""
    target = route.get("next_hop") or route.get("exit_interface") or ""
    return str(route["destination"]), str(route["subnet_mask"]), str(target)


async def _read_static_routes(node_id: str, node_row: dict, correlation_id: str) -> list[dict]:
    """อ่าน Static route ปัจจุบันผ่านคำสั่งภายในที่ browser ไม่สามารถกำหนดเอง"""
    lock = await get_node_lock(node_id)
    # Read/preview รอ heartbeat จบได้; ไม่ควรทำให้ผู้ใช้แก้ config ไม่ได้เพราะ polling
    async with lock:
        try:
            transport = build_transport_from_row(node_row)
            output = await run_in_threadpool(
                send_show_command,
                transport,
                "show running-config",
                require_enable=True,
            )
        except Exception as exc:
            _error(
                "STATIC_ROUTE_READ_FAILED",
                "อ่าน Static route จากอุปกรณ์ไม่สำเร็จ",
                correlation_id,
                status.HTTP_502_BAD_GATEWAY,
                {"reason": redact_text(str(exc))},
            )
    return parse_static_routes(output)


def _route_conflict_warnings(candidate: dict, current_routes: list[dict]) -> list[str]:
    """แจ้งเมื่อ prefix เดิมมี target อื่นซึ่งอาจเกิด equal-cost route"""
    same_prefix = [
        route for route in current_routes
        if route["destination"] == candidate["destination"]
        and route["subnet_mask"] == candidate["subnet_mask"]
        and _route_signature(route) != _route_signature(candidate)
    ]
    warnings = ["การ Apply จะเปลี่ยน running-config และยังไม่บันทึก NVRAM"]
    if same_prefix:
        warnings.append("พบ route prefix เดียวกันที่ใช้ target อื่น อาจเกิดหลายเส้นทางพร้อมกัน")
    return warnings


@router.get(
    "/nodes/{node_id}/routes/static",
    response_model=StaticRouteListResponse,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
async def list_static_routes(node_id: str) -> StaticRouteListResponse:
    """คืน Static/Default route ที่อ่านจาก running-config จริง"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    routes = await _read_static_routes(node_id, node_row, correlation_id)
    return StaticRouteListResponse.model_validate(
        {"node_id": node_id, "routes": routes, "collected_at": _now().isoformat()}
    )


@router.post(
    "/nodes/{node_id}/config/static-route/preview",
    response_model=PreviewResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def preview_static_route(node_id: str, payload: StaticRouteConfig) -> PreviewResponse:
    """ตรวจ duplicate/conflict แล้วสร้าง preview สำหรับเพิ่ม Static/Default route"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    current_routes = await _read_static_routes(node_id, node_row, correlation_id)
    candidate = payload.model_dump()
    if any(_route_signature(route) == _route_signature(candidate) for route in current_routes):
        _error("ROUTE_DUPLICATE", "Static route นี้มีอยู่แล้ว", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(
        node_id,
        payload,
        render_static_route(payload),
        "static_route",
        _route_conflict_warnings(candidate, current_routes),
    )


@router.post(
    "/nodes/{node_id}/config/static-route/remove/preview",
    response_model=PreviewResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def preview_static_route_remove(node_id: str, payload: StaticRouteConfig) -> PreviewResponse:
    """ยืนยันว่า route เดิมยังมีอยู่ก่อนสร้าง inverse preview"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    current_routes = await _read_static_routes(node_id, node_row, correlation_id)
    candidate = payload.model_dump()
    if not any(_route_signature(route) == _route_signature(candidate) for route in current_routes):
        _error("ROUTE_NOT_FOUND", "ไม่พบ Static route ที่ต้องการลบ", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(
        node_id,
        payload,
        render_static_route_remove(payload),
        "static_route_remove",
        ["การ Apply จะลบ route นี้จาก running-config และยังไม่บันทึก NVRAM"],
    )


@router.post(
    "/nodes/{node_id}/config/static-route/update/preview",
    response_model=PreviewResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def preview_static_route_update(node_id: str, payload: StaticRouteUpdate) -> PreviewResponse:
    """สร้าง preview แก้ route แบบ remove ค่าเดิมก่อน add ค่าใหม่"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    current_routes = await _read_static_routes(node_id, node_row, correlation_id)
    current = payload.current.model_dump()
    desired = payload.desired.model_dump()
    if not any(_route_signature(route) == _route_signature(current) for route in current_routes):
        _error("ROUTE_NOT_FOUND", "route เดิมเปลี่ยนไปแล้ว กรุณา Refresh", correlation_id, status.HTTP_409_CONFLICT)
    remaining = [route for route in current_routes if _route_signature(route) != _route_signature(current)]
    if any(_route_signature(route) == _route_signature(desired) for route in remaining):
        _error("ROUTE_DUPLICATE", "Static route ใหม่มีอยู่แล้ว", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(
        node_id,
        payload,
        render_static_route_update(payload),
        "static_route_update",
        _route_conflict_warnings(desired, remaining),
    )


@router.post(
    "/nodes/{node_id}/config/static-route/apply",
    response_model=ApplyResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def apply_static_route(node_id: str, request: ApplyRequest) -> ApplyResponse:
    """Apply Static route preview ที่ยัง valid และบันทึกผลลง history"""
    return await _apply_preview(
        node_id,
        request,
        {"static_route", "static_route_remove", "static_route_update"},
        "Static Route Configuration",
    )


async def _read_rip_state(node_id: str, node_row: dict, correlation_id: str) -> dict:
    """อ่าน RIP process ปัจจุบันจาก running-config ด้วย privileged read"""
    lock = await get_node_lock(node_id)
    # Read/preview รอ heartbeat จบได้; Apply mutation ยังมี lock แยกเพื่อกัน config ซ้อน
    async with lock:
        try:
            transport = build_transport_from_row(node_row)
            output = await run_in_threadpool(
                send_show_command,
                transport,
                "show running-config",
                require_enable=True,
            )
        except Exception as exc:
            _error(
                "RIP_READ_FAILED",
                "อ่านค่า RIP จากอุปกรณ์ไม่สำเร็จ",
                correlation_id,
                status.HTTP_502_BAD_GATEWAY,
                {"reason": redact_text(str(exc))},
            )
    return parse_rip_config(output)


@router.get(
    "/nodes/{node_id}/routing/rip",
    response_model=RipStateResponse,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
async def get_rip_state(node_id: str) -> RipStateResponse:
    """คืนสถานะ RIP actual state ที่อ่านจาก running-config"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    state = await _read_rip_state(node_id, node_row, correlation_id)
    return RipStateResponse.model_validate(
        {"node_id": node_id, "collected_at": _now().isoformat(), **state}
    )


@router.post(
    "/nodes/{node_id}/config/rip/network/preview",
    response_model=PreviewResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def preview_rip_network(node_id: str, payload: RipNetworkConfig) -> PreviewResponse:
    """สร้าง preview เปิด RIP หรือเพิ่ม network โดยไม่ส่งคำสั่งทันที"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    current = await _read_rip_state(node_id, node_row, correlation_id)
    if payload.network in current["networks"]:
        _error("RIP_NETWORK_DUPLICATE", "RIP network นี้มีอยู่แล้ว", correlation_id, status.HTTP_409_CONFLICT)
    warnings = ["การ Apply จะเปลี่ยน running-config และยังไม่บันทึก NVRAM"]
    if current["enabled"] and current["version"] != payload.version:
        warnings.append(f"RIP version จะเปลี่ยนจาก {current['version']} เป็น {payload.version} สำหรับทั้ง process")
    return _persist_preview(node_id, payload, render_rip_network(payload), "rip_network", warnings)


@router.post(
    "/nodes/{node_id}/config/rip/network/remove/preview",
    response_model=PreviewResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def preview_rip_network_remove(node_id: str, payload: RipNetworkConfig) -> PreviewResponse:
    """ยืนยัน actual state แล้วสร้าง preview ลบ RIP network"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    current = await _read_rip_state(node_id, node_row, correlation_id)
    if not current["enabled"] or payload.network not in current["networks"]:
        _error("RIP_NETWORK_NOT_FOUND", "ไม่พบ RIP network ที่ต้องการลบ", correlation_id, status.HTTP_409_CONFLICT)
    if payload.version != current["version"]:
        _error("RIP_STATE_CHANGED", "RIP version เปลี่ยนไปแล้ว กรุณา Refresh", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(
        node_id,
        payload,
        render_rip_network_remove(payload),
        "rip_network_remove",
        ["การ Apply จะลบ network นี้ออกจาก RIP และยังไม่บันทึก NVRAM"],
    )


@router.post(
    "/nodes/{node_id}/config/rip/network/update/preview",
    response_model=PreviewResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def preview_rip_network_update(node_id: str, payload: RipNetworkUpdate) -> PreviewResponse:
    """สร้าง preview แก้ RIP network โดยตรวจค่าเดิมก่อน"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    current = await _read_rip_state(node_id, node_row, correlation_id)
    if (
        not current["enabled"]
        or payload.current.network not in current["networks"]
        or payload.current.version != current["version"]
    ):
        _error("RIP_STATE_CHANGED", "ค่า RIP เดิมเปลี่ยนไปแล้ว กรุณา Refresh", correlation_id, status.HTTP_409_CONFLICT)
    remaining = [network for network in current["networks"] if network != payload.current.network]
    if payload.desired.network in remaining:
        _error("RIP_NETWORK_DUPLICATE", "RIP network ใหม่มีอยู่แล้ว", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(
        node_id,
        payload,
        render_rip_network_update(payload),
        "rip_network_update",
        ["การ Apply จะเปลี่ยน RIP process และยังไม่บันทึก NVRAM"],
    )


@router.post(
    "/nodes/{node_id}/config/rip/process/remove/preview",
    response_model=PreviewResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def preview_rip_process_remove(node_id: str, payload: RipProcessConfig) -> PreviewResponse:
    """สร้าง preview ลบ RIP ทั้ง process เมื่อ snapshot ยังตรง actual state"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    current = await _read_rip_state(node_id, node_row, correlation_id)
    if not current["enabled"]:
        _error("RIP_NOT_CONFIGURED", "อุปกรณ์ยังไม่ได้เปิด RIP", correlation_id, status.HTTP_409_CONFLICT)
    if (
        payload.version != current["version"]
        or set(payload.networks) != set(current["networks"])
        or payload.no_auto_summary != current["no_auto_summary"]
    ):
        _error("RIP_STATE_CHANGED", "ค่า RIP เปลี่ยนไปแล้ว กรุณา Refresh", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(
        node_id,
        payload,
        render_rip_process_remove(),
        "rip_process_remove",
        ["การ Apply จะลบ RIP process และ network ทั้งหมด แต่ยังไม่บันทึก NVRAM"],
    )


@router.post(
    "/nodes/{node_id}/config/rip/apply",
    response_model=ApplyResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def apply_rip(node_id: str, request: ApplyRequest) -> ApplyResponse:
    """Apply RIP preview ที่ผ่าน TTL/hash และบันทึก per-command history"""
    return await _apply_preview(
        node_id,
        request,
        {"rip_network", "rip_network_remove", "rip_network_update", "rip_process_remove"},
        "RIP Configuration",
    )


async def _read_ospf_state(node_id: str, node_row: dict, correlation_id: str) -> dict:
    """อ่าน OSPF actual state จาก privileged running-config"""
    lock = await get_node_lock(node_id)
    async with lock:
        try:
            transport = build_transport_from_row(node_row)
            output = await run_in_threadpool(send_show_command, transport, "show running-config", require_enable=True)
        except Exception as exc:
            _error("OSPF_READ_FAILED", "อ่านค่า OSPF จากอุปกรณ์ไม่สำเร็จ", correlation_id, status.HTTP_502_BAD_GATEWAY, {"reason": redact_text(str(exc))})
    return parse_ospf_config(output)


def _ospf_signature(payload: OspfNetworkConfig | OspfNetworkState) -> tuple[str, str, int]:
    """คืน identity ของ OSPF network โดยไม่รวม process/router ID"""
    return payload.network, payload.subnet_mask, payload.area


def _ospf_entries(state: dict) -> list[OspfNetworkState]:
    """แปลง parser state เป็น typed OSPF entries สำหรับ response/compare"""
    if not state["enabled"]:
        return []
    process_id = int(state["process_id"])
    return [OspfNetworkState(process_id=process_id, router_id=state["router_id"], **entry) for entry in state["networks"]]


@router.get("/nodes/{node_id}/routing/ospf", response_model=OspfStateResponse)
async def get_ospf_state(node_id: str) -> OspfStateResponse:
    """คืน OSPF process และ network ที่อ่านจากอุปกรณ์จริง"""
    correlation_id = str(uuid.uuid4())
    state = await _read_ospf_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    return OspfStateResponse.model_validate({"node_id": node_id, "collected_at": _now().isoformat(), **state, "networks": _ospf_entries(state)})


@router.post("/nodes/{node_id}/config/ospf/network/preview", response_model=PreviewResponse)
async def preview_ospf_network(node_id: str, payload: OspfNetworkConfig) -> PreviewResponse:
    """สร้าง preview เพิ่ม OSPF network หรือเปิด process ใหม่"""
    correlation_id = str(uuid.uuid4())
    state = await _read_ospf_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    entries = _ospf_entries(state)
    if state["enabled"] and payload.process_id != state["process_id"]:
        _error("OSPF_PROCESS_CONFLICT", "มี OSPF process อื่นอยู่แล้ว กรุณา Remove ก่อน", correlation_id, status.HTTP_409_CONFLICT)
    if any(_ospf_signature(item) == _ospf_signature(payload) for item in entries):
        _error("OSPF_NETWORK_DUPLICATE", "OSPF network นี้มีอยู่แล้ว", correlation_id, status.HTTP_409_CONFLICT)
    warnings = ["การ Apply จะเปลี่ยน running-config และยังไม่บันทึก NVRAM"]
    if state["enabled"] and state["router_id"] != payload.router_id:
        warnings.append("router-id ที่เปลี่ยนอาจมีผลหลัง clear/restart OSPF process")
    return _persist_preview(node_id, payload, render_ospf_network(payload), "ospf_network", warnings)


@router.post("/nodes/{node_id}/config/ospf/network/remove/preview", response_model=PreviewResponse)
async def preview_ospf_network_remove(node_id: str, payload: OspfNetworkState) -> PreviewResponse:
    """ยืนยัน actual OSPF state ก่อนสร้าง inverse preview"""
    correlation_id = str(uuid.uuid4())
    state = await _read_ospf_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    if not state["enabled"] or payload.process_id != state["process_id"] or not any(_ospf_signature(item) == _ospf_signature(payload) for item in _ospf_entries(state)):
        _error("OSPF_NETWORK_NOT_FOUND", "ไม่พบ OSPF network ที่ต้องการลบ", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_ospf_network_remove(payload), "ospf_network_remove", ["การ Apply จะลบ OSPF network นี้และยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/ospf/network/update/preview", response_model=PreviewResponse)
async def preview_ospf_network_update(node_id: str, payload: OspfNetworkUpdate) -> PreviewResponse:
    """สร้าง preview update OSPF แบบลบ entry เดิมก่อนเพิ่มใหม่"""
    correlation_id = str(uuid.uuid4())
    state = await _read_ospf_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    entries = _ospf_entries(state)
    if not state["enabled"] or payload.current.process_id != state["process_id"] or not any(_ospf_signature(item) == _ospf_signature(payload.current) for item in entries):
        _error("OSPF_STATE_CHANGED", "ค่า OSPF เดิมเปลี่ยนไปแล้ว กรุณา Refresh", correlation_id, status.HTTP_409_CONFLICT)
    remaining = [item for item in entries if _ospf_signature(item) != _ospf_signature(payload.current)]
    if payload.desired.process_id != state["process_id"] or any(_ospf_signature(item) == _ospf_signature(payload.desired) for item in remaining):
        _error("OSPF_NETWORK_DUPLICATE", "OSPF network ใหม่ซ้ำหรือ process ไม่ตรง", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_ospf_network_update(payload), "ospf_network_update", ["การ Apply จะเปลี่ยน OSPF running-config และยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/ospf/process/remove/preview", response_model=PreviewResponse)
async def preview_ospf_process_remove(node_id: str, payload: OspfProcessConfig) -> PreviewResponse:
    """สร้าง preview Remove Protocol เมื่อ process snapshot ยังตรง actual state"""
    correlation_id = str(uuid.uuid4())
    state = await _read_ospf_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    current = _ospf_entries(state)
    if not state["enabled"] or payload.process_id != state["process_id"] or payload.router_id != state["router_id"] or {_ospf_signature(item) for item in payload.networks} != {_ospf_signature(item) for item in current}:
        _error("OSPF_STATE_CHANGED", "ค่า OSPF เปลี่ยนไปแล้ว กรุณา Refresh", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_ospf_process_remove(payload.process_id), "ospf_process_remove", ["การ Apply จะลบ OSPF process และ network ทั้งหมด แต่ยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/ospf/apply", response_model=ApplyResponse)
async def apply_ospf(node_id: str, request: ApplyRequest) -> ApplyResponse:
    """Apply OSPF preview ที่ผ่าน TTL/hash และบันทึก audit history"""
    return await _apply_preview(node_id, request, {"ospf_network", "ospf_network_remove", "ospf_network_update", "ospf_process_remove"}, "OSPF Configuration")


async def _read_eigrp_state(node_id: str, node_row: dict, correlation_id: str) -> dict:
    """อ่าน EIGRP actual state จาก privileged running-config"""
    lock = await get_node_lock(node_id)
    async with lock:
        try:
            transport = build_transport_from_row(node_row)
            output = await run_in_threadpool(send_show_command, transport, "show running-config", require_enable=True)
        except Exception as exc:
            _error("EIGRP_READ_FAILED", "อ่านค่า EIGRP จากอุปกรณ์ไม่สำเร็จ", correlation_id, status.HTTP_502_BAD_GATEWAY, {"reason": redact_text(str(exc))})
    return parse_eigrp_config(output)


def _eigrp_signature(payload: EigrpNetworkConfig | EigrpNetworkState) -> tuple[str, str]:
    """คืน identity ของ EIGRP network โดยไม่รวม process/router ID"""
    return payload.network, payload.subnet_mask


def _eigrp_entries(state: dict) -> list[EigrpNetworkState]:
    """แปลง parser state เป็น typed EIGRP entries สำหรับ response/compare"""
    if not state["enabled"]:
        return []
    as_number = int(state["as_number"])
    return [EigrpNetworkState(as_number=as_number, router_id=state["router_id"], **entry) for entry in state["networks"]]


@router.get("/nodes/{node_id}/routing/eigrp", response_model=EigrpStateResponse)
async def get_eigrp_state(node_id: str) -> EigrpStateResponse:
    """คืน EIGRP process และ network ที่อ่านจากอุปกรณ์จริง"""
    correlation_id = str(uuid.uuid4())
    state = await _read_eigrp_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    return EigrpStateResponse.model_validate({"node_id": node_id, "collected_at": _now().isoformat(), **state, "networks": _eigrp_entries(state)})


@router.post("/nodes/{node_id}/config/eigrp/network/preview", response_model=PreviewResponse)
async def preview_eigrp_network(node_id: str, payload: EigrpNetworkConfig) -> PreviewResponse:
    """สร้าง preview เพิ่ม EIGRP network หรือเปิด process ใหม่"""
    correlation_id = str(uuid.uuid4())
    state = await _read_eigrp_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    entries = _eigrp_entries(state)
    if state["enabled"] and payload.as_number != state["as_number"]:
        _error("EIGRP_AS_CONFLICT", "มี EIGRP AS อื่นอยู่แล้ว กรุณา Remove ก่อน", correlation_id, status.HTTP_409_CONFLICT)
    if any(_eigrp_signature(item) == _eigrp_signature(payload) for item in entries):
        _error("EIGRP_NETWORK_DUPLICATE", "EIGRP network นี้มีอยู่แล้ว", correlation_id, status.HTTP_409_CONFLICT)
    warnings = ["การ Apply จะเปลี่ยน running-config และยังไม่บันทึก NVRAM"]
    if state["enabled"] and state["router_id"] != payload.router_id:
        warnings.append("router-id ที่เปลี่ยนอาจมีผลหลัง clear/restart EIGRP process")
    return _persist_preview(node_id, payload, render_eigrp_network(payload), "eigrp_network", warnings)


@router.post("/nodes/{node_id}/config/eigrp/network/remove/preview", response_model=PreviewResponse)
async def preview_eigrp_network_remove(node_id: str, payload: EigrpNetworkState) -> PreviewResponse:
    """ยืนยัน actual EIGRP state ก่อนสร้าง inverse preview"""
    correlation_id = str(uuid.uuid4())
    state = await _read_eigrp_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    if not state["enabled"] or payload.as_number != state["as_number"] or not any(_eigrp_signature(item) == _eigrp_signature(payload) for item in _eigrp_entries(state)):
        _error("EIGRP_NETWORK_NOT_FOUND", "ไม่พบ EIGRP network ที่ต้องการลบ", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_eigrp_network_remove(payload), "eigrp_network_remove", ["การ Apply จะลบ EIGRP network นี้และยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/eigrp/network/update/preview", response_model=PreviewResponse)
async def preview_eigrp_network_update(node_id: str, payload: EigrpNetworkUpdate) -> PreviewResponse:
    """สร้าง preview update EIGRP แบบลบ entry เดิมก่อนเพิ่มใหม่"""
    correlation_id = str(uuid.uuid4())
    state = await _read_eigrp_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    entries = _eigrp_entries(state)
    if not state["enabled"] or payload.current.as_number != state["as_number"] or not any(_eigrp_signature(item) == _eigrp_signature(payload.current) for item in entries):
        _error("EIGRP_STATE_CHANGED", "ค่า EIGRP เดิมเปลี่ยนไปแล้ว กรุณา Refresh", correlation_id, status.HTTP_409_CONFLICT)
    remaining = [item for item in entries if _eigrp_signature(item) != _eigrp_signature(payload.current)]
    if payload.desired.as_number != state["as_number"] or any(_eigrp_signature(item) == _eigrp_signature(payload.desired) for item in remaining):
        _error("EIGRP_NETWORK_DUPLICATE", "EIGRP network ใหม่ซ้ำหรือ AS ไม่ตรง", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_eigrp_network_update(payload), "eigrp_network_update", ["การ Apply จะเปลี่ยน EIGRP running-config และยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/eigrp/process/remove/preview", response_model=PreviewResponse)
async def preview_eigrp_process_remove(node_id: str, payload: EigrpProcessConfig) -> PreviewResponse:
    """สร้าง preview Remove Protocol เมื่อ process snapshot ยังตรง actual state"""
    correlation_id = str(uuid.uuid4())
    state = await _read_eigrp_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    current = _eigrp_entries(state)
    if not state["enabled"] or payload.as_number != state["as_number"] or payload.router_id != state["router_id"] or {_eigrp_signature(item) for item in payload.networks} != {_eigrp_signature(item) for item in current} or payload.no_auto_summary != state["no_auto_summary"]:
        _error("EIGRP_STATE_CHANGED", "ค่า EIGRP เปลี่ยนไปแล้ว กรุณา Refresh", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_eigrp_process_remove(payload.as_number), "eigrp_process_remove", ["การ Apply จะลบ EIGRP process และ network ทั้งหมด แต่ยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/eigrp/apply", response_model=ApplyResponse)
async def apply_eigrp(node_id: str, request: ApplyRequest) -> ApplyResponse:
    """Apply EIGRP preview ที่ผ่าน TTL/hash และบันทึก audit history"""
    return await _apply_preview(node_id, request, {"eigrp_network", "eigrp_network_remove", "eigrp_network_update", "eigrp_process_remove"}, "EIGRP Configuration")


async def _read_bgp_state(node_id: str, node_row: dict, correlation_id: str) -> dict:
    """อ่าน BGP actual state จาก privileged running-config"""
    lock = await get_node_lock(node_id)
    async with lock:
        try:
            transport = build_transport_from_row(node_row)
            output = await run_in_threadpool(send_show_command, transport, "show running-config", require_enable=True)
        except Exception as exc:
            _error("BGP_READ_FAILED", "อ่านค่า BGP จากอุปกรณ์ไม่สำเร็จ", correlation_id, status.HTTP_502_BAD_GATEWAY, {"reason": redact_text(str(exc))})
    return parse_bgp_config(output)


def _bgp_state_response(node_id: str, state: dict) -> BgpStateResponse:
    """แปลง parser state เป็น typed BGP response โดยคืนเฉพาะ resource ที่ parser ยืนยันได้"""
    local_as = state["local_as"]
    router_id = state["router_id"]
    neighbors = [] if not state["enabled"] or local_as is None else [BgpNeighborState(local_as=int(local_as), router_id=router_id, **entry) for entry in state["neighbors"]]
    networks = [] if not state["enabled"] or local_as is None else [BgpNetworkConfig(local_as=int(local_as), **entry) for entry in state["networks"]]
    return BgpStateResponse.model_validate({"node_id": node_id, "collected_at": _now().isoformat(), **state, "neighbors": neighbors, "networks": networks})


@router.get("/nodes/{node_id}/routing/bgp", response_model=BgpStateResponse)
async def get_bgp_state(node_id: str) -> BgpStateResponse:
    """คืน BGP process, neighbor และ network ที่อ่านจากอุปกรณ์จริง"""
    correlation_id = str(uuid.uuid4())
    return _bgp_state_response(node_id, await _read_bgp_state(node_id, _get_node_row(node_id, correlation_id), correlation_id))


def _check_bgp_as(state: dict, local_as: int, correlation_id: str) -> None:
    """ปฏิเสธการแก้ BGP ด้วย local AS อื่นจาก process ที่มีอยู่"""
    if state["enabled"] and local_as != state["local_as"]:
        _error("BGP_AS_CONFLICT", "มี BGP local AS อื่นอยู่แล้ว กรุณา Remove ก่อน", correlation_id, status.HTTP_409_CONFLICT)


@router.post("/nodes/{node_id}/config/bgp/neighbor/preview", response_model=PreviewResponse)
async def preview_bgp_neighbor(node_id: str, payload: BgpNeighborConfig) -> PreviewResponse:
    """สร้าง preview เพิ่ม BGP neighbor หรือเปิด process ใหม่"""
    correlation_id = str(uuid.uuid4())
    state = await _read_bgp_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    _check_bgp_as(state, payload.local_as, correlation_id)
    current = _bgp_state_response(node_id, state).neighbors
    if any(item.neighbor_ip == payload.neighbor_ip for item in current):
        _error("BGP_NEIGHBOR_DUPLICATE", "BGP neighbor นี้มีอยู่แล้ว", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_bgp_neighbor(payload), "bgp_neighbor", ["การ Apply จะเปลี่ยน running-config และยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/bgp/neighbor/remove/preview", response_model=PreviewResponse)
async def preview_bgp_neighbor_remove(node_id: str, payload: BgpNeighborState) -> PreviewResponse:
    """ยืนยัน actual BGP state ก่อนสร้าง inverse preview ของ neighbor"""
    correlation_id = str(uuid.uuid4())
    state = await _read_bgp_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    _check_bgp_as(state, payload.local_as, correlation_id)
    if not any(item.neighbor_ip == payload.neighbor_ip for item in _bgp_state_response(node_id, state).neighbors):
        _error("BGP_NEIGHBOR_NOT_FOUND", "ไม่พบ BGP neighbor ที่ต้องการลบ", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_bgp_neighbor_remove(payload), "bgp_neighbor_remove", ["การ Apply จะลบ BGP neighbor นี้และยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/bgp/neighbor/update/preview", response_model=PreviewResponse)
async def preview_bgp_neighbor_update(node_id: str, payload: BgpNeighborUpdate) -> PreviewResponse:
    """สร้าง preview แก้ neighbor แบบลบค่าเดิมก่อนเพิ่มค่าใหม่"""
    correlation_id = str(uuid.uuid4())
    state = await _read_bgp_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    _check_bgp_as(state, payload.current.local_as, correlation_id)
    current = _bgp_state_response(node_id, state).neighbors
    if not any(item.neighbor_ip == payload.current.neighbor_ip for item in current):
        _error("BGP_NEIGHBOR_NOT_FOUND", "BGP neighbor เดิมเปลี่ยนไปแล้ว กรุณา Refresh", correlation_id, status.HTTP_409_CONFLICT)
    if payload.desired.local_as != state["local_as"]:
        _error("BGP_AS_CONFLICT", "BGP local AS ใหม่ไม่ตรงกับ process ปัจจุบัน", correlation_id, status.HTTP_409_CONFLICT)
    if payload.desired.neighbor_ip != payload.current.neighbor_ip and any(item.neighbor_ip == payload.desired.neighbor_ip for item in current):
        _error("BGP_NEIGHBOR_DUPLICATE", "BGP neighbor ใหม่มีอยู่แล้ว", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_bgp_neighbor_update(payload), "bgp_neighbor_update", ["การ Apply จะลบ neighbor เดิมก่อนเพิ่มค่าใหม่ และยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/bgp/network/preview", response_model=PreviewResponse)
async def preview_bgp_network(node_id: str, payload: BgpNetworkConfig) -> PreviewResponse:
    """สร้าง preview เพิ่ม advertised network ใน BGP process ที่มีอยู่"""
    correlation_id = str(uuid.uuid4())
    state = await _read_bgp_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    _check_bgp_as(state, payload.local_as, correlation_id)
    if not state["enabled"]:
        _error("BGP_NOT_CONFIGURED", "ต้องสร้าง BGP neighbor ก่อนเพิ่ม advertised network", correlation_id, status.HTTP_409_CONFLICT)
    if any(item.network == payload.network and item.subnet_mask == payload.subnet_mask for item in _bgp_state_response(node_id, state).networks):
        _error("BGP_NETWORK_DUPLICATE", "BGP network นี้มีอยู่แล้ว", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_bgp_network(payload), "bgp_network")


@router.post("/nodes/{node_id}/config/bgp/network/remove/preview", response_model=PreviewResponse)
async def preview_bgp_network_remove(node_id: str, payload: BgpNetworkConfig) -> PreviewResponse:
    """ยืนยัน actual BGP state ก่อนสร้าง inverse preview ของ network"""
    correlation_id = str(uuid.uuid4())
    state = await _read_bgp_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    _check_bgp_as(state, payload.local_as, correlation_id)
    if not any(item.network == payload.network and item.subnet_mask == payload.subnet_mask for item in _bgp_state_response(node_id, state).networks):
        _error("BGP_NETWORK_NOT_FOUND", "ไม่พบ BGP network ที่ต้องการลบ", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_bgp_network_remove(payload), "bgp_network_remove", ["การ Apply จะลบ BGP advertised network นี้และยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/bgp/network/update/preview", response_model=PreviewResponse)
async def preview_bgp_network_update(node_id: str, payload: BgpNetworkUpdate) -> PreviewResponse:
    """สร้าง preview แก้ advertised network แบบลบค่าเดิมก่อนเพิ่มใหม่"""
    correlation_id = str(uuid.uuid4())
    state = await _read_bgp_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    _check_bgp_as(state, payload.current.local_as, correlation_id)
    current = _bgp_state_response(node_id, state).networks
    if not any(item.network == payload.current.network and item.subnet_mask == payload.current.subnet_mask for item in current):
        _error("BGP_NETWORK_NOT_FOUND", "BGP network เดิมเปลี่ยนไปแล้ว กรุณา Refresh", correlation_id, status.HTTP_409_CONFLICT)
    if payload.desired.local_as != state["local_as"]:
        _error("BGP_AS_CONFLICT", "BGP local AS ใหม่ไม่ตรงกับ process ปัจจุบัน", correlation_id, status.HTTP_409_CONFLICT)
    if (payload.desired.network, payload.desired.subnet_mask) != (payload.current.network, payload.current.subnet_mask) and any(item.network == payload.desired.network and item.subnet_mask == payload.desired.subnet_mask for item in current):
        _error("BGP_NETWORK_DUPLICATE", "BGP network ใหม่มีอยู่แล้ว", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_bgp_network_update(payload), "bgp_network_update", ["การ Apply จะลบ BGP network เดิมก่อนเพิ่มค่าใหม่ และยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/bgp/process/remove/preview", response_model=PreviewResponse)
async def preview_bgp_process_remove(node_id: str, payload: BgpProcessConfig) -> PreviewResponse:
    """สร้าง preview Remove Protocol เมื่อ BGP snapshot ยังตรง actual state"""
    correlation_id = str(uuid.uuid4())
    state = await _read_bgp_state(node_id, _get_node_row(node_id, correlation_id), correlation_id)
    current = _bgp_state_response(node_id, state)
    if not state["enabled"] or payload != BgpProcessConfig(local_as=current.local_as or 1, router_id=current.router_id, neighbors=current.neighbors, networks=current.networks):
        _error("BGP_STATE_CHANGED", "ค่า BGP เปลี่ยนไปแล้ว กรุณา Refresh", correlation_id, status.HTTP_409_CONFLICT)
    return _persist_preview(node_id, payload, render_bgp_process_remove(payload.local_as), "bgp_process_remove", ["การ Apply จะลบ BGP process, neighbor และ network ทั้งหมด แต่ยังไม่บันทึก NVRAM"])


@router.post("/nodes/{node_id}/config/bgp/apply", response_model=ApplyResponse)
async def apply_bgp(node_id: str, request: ApplyRequest) -> ApplyResponse:
    """Apply BGP preview ที่ผ่าน TTL/hash และบันทึก audit history"""
    return await _apply_preview(node_id, request, {"bgp_neighbor", "bgp_neighbor_remove", "bgp_neighbor_update", "bgp_network", "bgp_network_remove", "bgp_network_update", "bgp_process_remove"}, "BGP Configuration")


@router.post("/nodes/{node_id}/config/save/preview", response_model=PreviewResponse)
async def preview_save_config(node_id: str, payload: SaveConfigRequest) -> PreviewResponse:
    """สร้าง preview write memory เฉพาะเมื่อ frontend ส่งการยืนยันชัดเจน"""
    return _persist_preview(node_id, payload, render_save_config(), "save_config", ["คำสั่งนี้จะบันทึก running-config ปัจจุบันลง startup-config (NVRAM)"])


@router.post("/nodes/{node_id}/config/save/apply", response_model=ApplyResponse)
async def apply_save_config(node_id: str, request: ApplyRequest) -> ApplyResponse:
    """Apply save preview ที่ผู้ใช้ยืนยันและบันทึก audit history"""
    return await _apply_preview(node_id, request, {"save_config"}, "Save Configuration")


@router.get("/nodes/{node_id}/show", response_model=ShowResponse)
async def show_command(
    node_id: str,
    command: str = Query(..., description="คำสั่ง show ใน allowlist เท่านั้น"),
) -> ShowResponse:
    """เรียก show command ที่อนุญาตและคืนทั้ง raw output กับ parsed data บางคำสั่ง"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    if command not in _SHOW_COMMANDS:
        _error("COMMAND_NOT_ALLOWED", "คำสั่ง show นี้ไม่อยู่ใน allowlist", correlation_id, status.HTTP_422_UNPROCESSABLE_ENTITY)
    lock = await get_node_lock(node_id)
    async with lock:
        try:
            transport = build_transport_from_row(node_row)
            output = await run_in_threadpool(
                send_show_command,
                transport,
                command,
                require_enable=command == "show running-config",
            )
        except Exception as exc:
            _record_show_result(node_id, command, correlation_id, "failed", redact_text(str(exc)))
            _error("SHOW_FAILED", "อ่านข้อมูลจากอุปกรณ์ไม่สำเร็จ", correlation_id, status.HTTP_502_BAD_GATEWAY, {"reason": redact_text(str(exc))})
    _record_show_result(node_id, command, correlation_id, "success", output)
    parser_kind = _SHOW_COMMANDS[command]
    parsed = parse_show_ip_interface_brief(output) if parser_kind == "interface" else parse_show_ip_route(output) if parser_kind == "route" else None
    return ShowResponse(node_id=node_id, command=command, output=output, parsed=parsed, collected_at=_now().isoformat())


def _record_show_result(node_id: str, command: str, correlation_id: str, result_status: Literal["success", "failed"], output: str) -> None:
    """เพิ่ม audit สำหรับ Show ที่ผู้ใช้เรียกโดยตรง โดยซ่อน secret ในผลลัพธ์"""
    safe_output = redact_text(output)
    result = CommandResult(command=command, status=result_status, output=safe_output, error_code="SHOW_FAILED" if result_status == "failed" else None)
    with get_db() as conn:
        node_hostname = conn.execute("SELECT hostname FROM nodes WHERE id = ?", (node_id,)).fetchone()[0]
        conn.execute(
            """INSERT INTO command_history
               (id, correlation_id, node_id, node_hostname, operation_id, command_type, commands_json,
                result_json, overall_status, created_at)
               VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), correlation_id, node_id, node_hostname, "Show Command", json.dumps([command]),
             json.dumps([result.model_dump()], ensure_ascii=False), result_status, _now().isoformat()),
        )


@router.get(
    "/nodes/{node_id}/interfaces/{interface_name:path}/capabilities",
    response_model=InterfaceCapabilitiesResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
async def get_interface_capabilities(node_id: str, interface_name: str) -> InterfaceCapabilitiesResponse:
    """อ่านสถานะ switchport ของ interface ที่ระบุด้วย command ฝั่ง server"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    interface_name = interface_name.strip()
    if not _INTERFACE_NAME_PATTERN.fullmatch(interface_name):
        _error("VALIDATION_ERROR", "ชื่อ interface ไม่ถูกต้อง", correlation_id, status.HTTP_422_UNPROCESSABLE_ENTITY)

    lock = await get_node_lock(node_id)
    async with lock:
        try:
            output = await run_in_threadpool(
                send_show_command,
                build_transport_from_row(node_row),
                f"show interfaces {interface_name} switchport",
            )
        except Exception as exc:
            _error(
                "INTERFACE_CAPABILITY_READ_FAILED",
                "อ่านความสามารถของ Interface ไม่สำเร็จ",
                correlation_id,
                status.HTTP_502_BAD_GATEWAY,
                {"reason": redact_text(str(exc))},
            )
    return InterfaceCapabilitiesResponse(
        node_id=node_id,
        interface_name=interface_name,
        switchport_state=parse_switchport_state(output),
        collected_at=_now().isoformat(),
    )


@router.get(
    "/nodes/{node_id}/interfaces/{interface_name:path}",
    response_model=InterfaceCurrentResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
async def get_interface_current(node_id: str, interface_name: str) -> InterfaceCurrentResponse:
    """อ่านค่าปัจจุบันของ interface เพื่อ prefill โดยสร้าง Show command ฝั่ง server เท่านั้น"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    interface_name = interface_name.strip()
    if not _INTERFACE_NAME_PATTERN.fullmatch(interface_name):
        _error("VALIDATION_ERROR", "ชื่อ interface ไม่ถูกต้อง", correlation_id, status.HTTP_422_UNPROCESSABLE_ENTITY)

    lock = await get_node_lock(node_id)
    async with lock:
        try:
            transport = build_transport_from_row(node_row)
            outputs = await run_in_threadpool(
                send_show_commands,
                transport,
                [
                    f"show interfaces {interface_name}",
                    f"show ip interface {interface_name}",
                ],
            )
        except Exception as exc:
            _error("INTERFACE_READ_FAILED", "อ่านค่า Interface ไม่สำเร็จ", correlation_id, status.HTTP_502_BAD_GATEWAY, {"reason": redact_text(str(exc))})

    parsed = parse_show_interface_detail("\n".join(outputs), interface_name)
    if parsed is None:
        _error("INTERFACE_PARSE_FAILED", "อ่านรูปแบบค่าของ Interface ไม่สำเร็จ", correlation_id, status.HTTP_502_BAD_GATEWAY)
    return InterfaceCurrentResponse.model_validate({
        "node_id": node_id,
        "collected_at": _now().isoformat(),
        **parsed,
    })


@router.get(
    "/nodes/{node_id}/capabilities",
    response_model=DeviceCapabilitiesResponse,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
async def get_device_capabilities(node_id: str) -> DeviceCapabilitiesResponse:
    """อ่าน capability จากชุด show command ที่ backend กำหนด ไม่เดาจากชื่อ node"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    lock = await get_node_lock(node_id)
    async with lock:
        try:
            outputs = await run_in_threadpool(
                send_show_commands,
                build_transport_from_row(node_row),
                ["show interfaces switchport", "show vlan brief"],
            )
        except Exception as exc:
            _error(
                "CAPABILITY_READ_FAILED",
                "อ่านความสามารถของอุปกรณ์ไม่สำเร็จ",
                correlation_id,
                status.HTTP_502_BAD_GATEWAY,
                {"reason": redact_text(str(exc))},
            )
    return DeviceCapabilitiesResponse(
        node_id=node_id,
        switchport_supported=not is_unsupported_ios_command(outputs[0]),
        vlan_supported=not is_unsupported_ios_command(outputs[1]),
        collected_at=_now().isoformat(),
    )


@router.get(
    "/nodes/{node_id}/vlans",
    response_model=VlanListResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
async def list_vlans(node_id: str) -> VlanListResponse:
    """อ่าน VLAN actual state เพื่อให้ browser ไม่เดา VLAN ที่มีอยู่"""
    correlation_id = str(uuid.uuid4())
    node_row = _get_node_row(node_id, correlation_id)
    lock = await get_node_lock(node_id)
    async with lock:
        try:
            output = await run_in_threadpool(
                send_show_command,
                build_transport_from_row(node_row),
                "show vlan brief",
            )
        except Exception as exc:
            _error(
                "VLAN_READ_FAILED",
                "อ่าน VLAN จากอุปกรณ์ไม่สำเร็จ",
                correlation_id,
                status.HTTP_502_BAD_GATEWAY,
                {"reason": redact_text(str(exc))},
            )
    if is_unsupported_ios_command(output):
        _error("VLAN_UNSUPPORTED", "อุปกรณ์นี้ไม่รองรับ VLAN configuration", correlation_id, status.HTTP_409_CONFLICT)
    vlans = parse_show_vlan_brief(output)
    if vlans is None:
        _error("VLAN_PARSE_FAILED", "อ่านรูปแบบ VLAN จากอุปกรณ์ไม่สำเร็จ", correlation_id, status.HTTP_502_BAD_GATEWAY)
    return VlanListResponse(node_id=node_id, vlans=vlans, collected_at=_now().isoformat())


@router.get("/history/nodes", response_model=list[HistoryNodeOption])
async def list_history_nodes() -> list[HistoryNodeOption]:
    """คืนรายการ Node ที่มี history โดยไม่ขึ้นกับตัวกรองหรือหน้าปัจจุบัน"""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT h.node_id, COALESCE(h.node_hostname, n.hostname) AS hostname FROM command_history h
               LEFT JOIN nodes n ON n.id = h.node_id
               GROUP BY h.node_id ORDER BY COALESCE(h.node_hostname, n.hostname, h.node_id) COLLATE NOCASE"""
        ).fetchall()
    return [HistoryNodeOption(id=row["node_id"], hostname=row["hostname"]) for row in rows]


@router.get("/history", response_model=list[HistoryEntry])
async def list_history(
    response: Response,
    node_id: str | None = Query(default=None),
    overall_status: Literal["success", "failed", "partial_failed"] | None = Query(default=None),
    created_from: datetime | None = None,
    created_before: datetime | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[HistoryEntry]:
    """คืน audit newest-first พร้อมตัวกรอง UTC ช่วง [created_from, created_before) และยอดรวม"""
    if any(value is not None and value.utcoffset() is None for value in (created_from, created_before)):
        raise HTTPException(status_code=422, detail="กรุณาระบุเขตเวลาในช่วงที่กรอง")
    if created_from and created_before and created_from >= created_before:
        raise HTTPException(status_code=422, detail="เวลาสิ้นสุดต้องอยู่หลังเวลาเริ่มต้น")
    where = " WHERE 1=1"
    params: list[str] = []
    if node_id:
        where += " AND h.node_id = ?"
        params.append(node_id)
    if overall_status:
        where += " AND h.overall_status = ?"
        params.append(overall_status)
    if created_from:
        where += " AND h.created_at >= ?"
        params.append(created_from.astimezone(UTC).isoformat())
    if created_before:
        where += " AND h.created_at < ?"
        params.append(created_before.astimezone(UTC).isoformat())
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM command_history h" + where, params).fetchone()[0]
        rows = conn.execute(
            """SELECT h.*, COALESCE(h.node_hostname, n.hostname) AS display_hostname FROM command_history h
               LEFT JOIN nodes n ON n.id = h.node_id""" + where +
            " ORDER BY h.created_at DESC, h.id DESC LIMIT ? OFFSET ?", [*params, limit, offset],
        ).fetchall()
    response.headers["X-Total-Count"] = str(total)
    return [
        HistoryEntry(
            id=row["id"],
            node_id=row["node_id"],
            node_hostname=row["display_hostname"],
            correlation_id=row["correlation_id"],
            operation_id=row["operation_id"],
            command_type=row["command_type"],
            commands=json.loads(row["commands_json"]),
            results=json.loads(row["result_json"]),
            overall_status=row["overall_status"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
