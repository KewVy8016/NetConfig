# Router สำหรับจัดการ Node — POST /nodes และ POST /nodes/{id}/test
# ทำหน้าที่เฉพาะ HTTP boundary: validate schema, เรียก service, map error

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, Response, status

from backend.database import get_db
from backend.models import (
    ConnectionStepStatus,
    DeviceKind,
    ErrorResponse,
    NodeCreate,
    NodeListResponse,
    NodeResponse,
    NodeStatus,
    ScanSubnetRequest,
    ScanSubnetResponse,
    SerialConfig,
    SSHConfig,
    TelnetConfig,
    TestConnectionResponse,
    TransportType,
)
from backend.services.connection import get_node_lock, test_connection
from backend.services.encryption import decrypt, encrypt
from backend.services.scanner import scan_subnet

router = APIRouter(prefix="/nodes", tags=["nodes"])


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _now_utc() -> str:
    """คืน timestamp UTC ปัจจุบันในรูปแบบ ISO 8601"""
    return datetime.now(UTC).isoformat()


def _new_correlation_id() -> str:
    """สร้าง correlation ID สำหรับ trace log"""
    return str(uuid.uuid4())


def _row_to_node_response(row: dict) -> NodeResponse:
    """แปลง SQLite row เป็น NodeResponse โดยไม่คืน secret

    Parameters:
        row: dict ของ SQLite Row

    Returns:
        NodeResponse ที่ปลอดภัย
    """
    transport = TransportType(row["transport"])
    return NodeResponse(
        id=row["id"],
        hostname=row["hostname"],
        host=row["host"] or None,
        transport=transport,
        port=row["port"] or None,
        serial_port=row["serial_port"] or None,
        device_kind=DeviceKind(row["device_type"]) if row.get("device_type") else DeviceKind.ROUTER,
        status=NodeStatus(row["status"]) if row.get("status") else NodeStatus.UNKNOWN,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _build_transport_for_test(row: dict) -> SSHConfig | TelnetConfig | SerialConfig:
    """สร้าง transport config จาก SQLite row สำหรับ test connection

    decrypt credential ณ จุดนี้เท่านั้น — ไม่เก็บ plaintext ใน memory นานกว่าจำเป็น

    Parameters:
        row: SQLite Row ของ node

    Returns:
        Transport config ที่มี plaintext credentials (ใช้แล้วทิ้ง)
    """
    transport = TransportType(row["transport"])
    username_plain = decrypt(row["enc_username"])
    password_plain = decrypt(row["enc_password"])
    secret_plain = decrypt(row["enc_secret"]) if row["enc_secret"] else None

    if transport == TransportType.SSH:
        return SSHConfig(
            host=row["host"],
            port=row["port"],
            username=username_plain,
            password=password_plain,
            secret=secret_plain,
        )
    if transport == TransportType.TELNET:
        return TelnetConfig(
            host=row["host"],
            port=row["port"],
            username=username_plain,
            password=password_plain,
            secret=secret_plain,
        )
    # Serial
    return SerialConfig(
        serial_port=row["serial_port"],
        baudrate=row["serial_baudrate"] or 9600,
        username=username_plain,
        password=password_plain,
        secret=secret_plain,
    )


# ---------------------------------------------------------------------------
# POST /nodes — สร้าง node ใหม่
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=NodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="สร้าง node ใหม่",
    responses={
        409: {"model": ErrorResponse, "description": "Node ซ้ำ (host/port หรือ serial_port เดียวกัน)"},
        422: {"description": "Validation error"},
    },
)
async def create_node(payload: NodeCreate) -> NodeResponse:
    """สร้าง node ใหม่และบันทึก credential ที่เข้ารหัสลง SQLite

    ห้ามคืน password หรือ secret ใน response
    ตรวจ duplicate ด้วย host+port หรือ serial_port ก่อนบันทึก
    Add Node flow เรียก endpoint นี้ได้หลัง pre-save test ผ่านแล้ว จึงบันทึกสถานะ
    เริ่มต้นเป็น connected เพื่อให้ผลทดสอบและสถานะบน Dashboard สอดคล้องกัน
    """
    correlation_id = _new_correlation_id()
    node_id = str(uuid.uuid4())
    now = _now_utc()
    cfg = payload.transport_config

    # เตรียมข้อมูลสำหรับบันทึก
    host = getattr(cfg, "host", None)
    port = getattr(cfg, "port", None)
    serial_port = getattr(cfg, "serial_port", None)
    serial_baudrate = getattr(cfg, "baudrate", None)
    username_plain = cfg.username
    password_plain = cfg.password
    secret_plain = cfg.secret

    with get_db() as conn:
        # ตรวจ duplicate endpoint
        if host and port:
            existing = conn.execute(
                "SELECT id FROM nodes WHERE host = ? AND port = ? AND transport = ?",
                (host, port, cfg.transport.value),
            ).fetchone()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "DUPLICATE_NODE",
                        "message_th": f"มี node ที่ใช้ {host}:{port} ({cfg.transport.value}) อยู่แล้ว",
                        "correlation_id": correlation_id,
                    },
                )
        if serial_port:
            existing = conn.execute(
                "SELECT id FROM nodes WHERE serial_port = ?",
                (serial_port,),
            ).fetchone()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "DUPLICATE_NODE",
                        "message_th": f"มี node ที่ใช้ serial port {serial_port} อยู่แล้ว",
                        "correlation_id": correlation_id,
                    },
                )

        # Encrypt credentials ก่อนบันทึก — plaintext อยู่ใน memory ชั่วคราวเท่านั้น
        enc_username = encrypt(username_plain)
        enc_password = encrypt(password_plain)
        enc_secret = encrypt(secret_plain) if secret_plain else None

        conn.execute(
            """INSERT INTO nodes
               (id, hostname, host, device_type, port, transport,
                enc_username, enc_password, enc_secret,
                serial_port, serial_baudrate, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node_id,
                payload.hostname,
                host,
                payload.device_kind.value,
                port,
                cfg.transport.value,
                enc_username,
                enc_password,
                enc_secret,
                serial_port,
                serial_baudrate,
                NodeStatus.CONNECTED.value,
                now,
                now,
            ),
        )

        row = conn.execute(
            "SELECT * FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()

    return _row_to_node_response(dict(row))


# ---------------------------------------------------------------------------
# POST /nodes/test — ทดสอบ connection ก่อนบันทึก node
# ---------------------------------------------------------------------------

@router.post(
    "/test",
    response_model=TestConnectionResponse,
    summary="ทดสอบ connection ก่อนบันทึก node",
)
async def test_node_connection_draft(payload: NodeCreate) -> TestConnectionResponse:
    """ทดสอบอุปกรณ์จาก typed payload โดยไม่เขียนข้อมูลลง SQLite

    ใช้ใน Add Node wizard เพื่อยืนยัน Ping/Port/Login/Hostname ก่อนบันทึก
    หากการทดสอบล้มเหลว จะไม่มี node หรือ credential ถูกสร้างในฐานข้อมูล
    """
    # ใช้ id ชั่วคราวสำหรับ trace/lock โดยไม่สร้าง entity ใน DB
    draft_id = f"draft:{uuid.uuid4()}"
    steps = await test_connection(draft_id, payload.transport_config)
    failed = any(s.status == ConnectionStepStatus.FAILED for s in steps)
    overall = ConnectionStepStatus.FAILED if failed else ConnectionStepStatus.SUCCESS
    hostname = next(
        (s.detail for s in steps if s.step == "hostname" and s.detail),
        None,
    )
    return TestConnectionResponse(
        node_id=draft_id,
        overall_status=overall,
        steps=steps,
        hostname_detected=hostname,
    )


@router.post("/scan", response_model=ScanSubnetResponse, summary="ค้นหา SSH/Telnet ใน subnet ขนาดเล็ก")
async def scan_nodes(payload: ScanSubnetRequest) -> ScanSubnetResponse:
    """probe เฉพาะ TCP 22/23 โดยไม่ login และไม่ scan subnet ขนาดใหญ่"""
    return ScanSubnetResponse(subnet=payload.subnet, results=await scan_subnet(payload.subnet))


# ---------------------------------------------------------------------------
# GET /nodes — รายการ nodes
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=NodeListResponse,
    summary="รายการ nodes ทั้งหมด",
)
async def list_nodes(
    q: str | None = Query(default=None, description="ค้นหาด้วย hostname หรือ IP"),
    status_filter: str | None = Query(default=None, alias="status"),
) -> NodeListResponse:
    """คืนรายการ nodes พร้อม hostname/IP/transport — ไม่มี credential"""
    with get_db() as conn:
        if q:
            rows = conn.execute(
                "SELECT * FROM nodes WHERE hostname LIKE ? OR host LIKE ? ORDER BY created_at DESC",
                (f"%{q}%", f"%{q}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM nodes ORDER BY created_at DESC"
            ).fetchall()

    nodes = [_row_to_node_response(dict(r)) for r in rows]
    return NodeListResponse(total=len(nodes), nodes=nodes)


# ---------------------------------------------------------------------------
# GET /nodes/{id} — ข้อมูล node เดียว
# ---------------------------------------------------------------------------

@router.get(
    "/{node_id}",
    response_model=NodeResponse,
    summary="ดูข้อมูล node",
)
async def get_node(node_id: str) -> NodeResponse:
    """คืนข้อมูล node ตาม ID — ไม่มี credential"""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NODE_NOT_FOUND",
                "message_th": f"ไม่พบ node ID: {node_id}",
                "correlation_id": _new_correlation_id(),
            },
        )
    return _row_to_node_response(dict(row))


# ---------------------------------------------------------------------------
# DELETE /nodes/{id} — ลบ node
# ---------------------------------------------------------------------------

@router.delete(
    "/{node_id}",
    summary="ลบ node",
    response_class=Response,
)
async def delete_node(node_id: str):
    """ลบ node ออกจาก DB — ต้องยืนยันจาก frontend ก่อนเรียก endpoint นี้"""
    with get_db() as conn:
        result = conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NODE_NOT_FOUND",
                "message_th": f"ไม่พบ node ID: {node_id}",
                "correlation_id": _new_correlation_id(),
            },
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# POST /nodes/{id}/test — ทดสอบ connection
# ---------------------------------------------------------------------------

@router.post(
    "/{node_id}/test",
    response_model=TestConnectionResponse,
    summary="ทดสอบ connection แบบ step-by-step",
    responses={
        404: {"model": ErrorResponse, "description": "ไม่พบ node"},
        409: {"model": ErrorResponse, "description": "Node กำลังใช้งานอยู่"},
    },
)
async def test_node_connection(node_id: str) -> TestConnectionResponse:
    """ทดสอบ: Ping → Port → Login → Hostname

    ใช้ per-node lock เพื่อป้องกันการ test ซ้อนกัน
    แต่ละขั้นส่งผลลัพธ์ภาษาไทย ไม่เผย secret/traceback
    """
    correlation_id = _new_correlation_id()

    # โหลด node จาก DB
    with get_db() as conn:
        row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NODE_NOT_FOUND",
                "message_th": f"ไม่พบ node ID: {node_id}",
                "correlation_id": correlation_id,
            },
        )

    node_lock = await get_node_lock(node_id)
    if node_lock.locked():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "NODE_BUSY",
                "message_th": "Node นี้กำลังถูกใช้งานอยู่ กรุณารอสักครู่",
                "correlation_id": correlation_id,
            },
        )

    async with node_lock:
        transport_config = _build_transport_for_test(dict(row))
        steps = await test_connection(node_id, transport_config)

    # สรุปผลรวม
    failed = any(s.status == ConnectionStepStatus.FAILED for s in steps)
    overall = ConnectionStepStatus.FAILED if failed else ConnectionStepStatus.SUCCESS
    hostname = next(
        (s.detail for s in steps if s.step == "hostname" and s.detail),
        None,
    )

    # เก็บสถานะล่าสุดไว้ให้ Dashboard แสดงผลสอดคล้องกับผล test connection
    with get_db() as conn:
        conn.execute(
            "UPDATE nodes SET status = ?, updated_at = ? WHERE id = ?",
            (NodeStatus.UNREACHABLE.value if failed else NodeStatus.CONNECTED.value, _now_utc(), node_id),
        )

    return TestConnectionResponse(
        node_id=node_id,
        overall_status=overall,
        steps=steps,
        hostname_detected=hostname,
    )
