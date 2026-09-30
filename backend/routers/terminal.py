# WebSocket boundary สำหรับ CLI แยกจาก typed preview/apply
# บันทึกผลทุกคำสั่งลง History โดยไม่เก็บข้อความ CLI ที่อาจมีรหัสผ่าน

from __future__ import annotations

import asyncio
import json
import re
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from backend.database import get_db
from backend.services.connection import build_transport_from_row, get_node_lock
from backend.services.terminal import (
    close_terminal,
    open_terminal,
    send_terminal_line,
    terminal_prompt,
)

router = APIRouter(tags=["terminal"])
_MAX_COMMAND_LENGTH = 256
_SESSION_IDLE_SECONDS = 300
_CLI_FAILURE = re.compile(r"%\s*(?:Invalid|Incomplete|Ambiguous|Error)|^Error:", re.IGNORECASE | re.MULTILINE)


def _record_cli_result(node_id: str, hostname: str, correlation_id: str, status: str) -> None:
    """เก็บ audit ของการส่ง CLI โดยเว้นคำสั่งและ output ที่อาจมี secret"""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO command_history
               (id, correlation_id, node_id, node_hostname, operation_id, command_type,
                commands_json, result_json, overall_status, created_at)
               VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), correlation_id, node_id, hostname, "CLI Command",
             json.dumps(["[CLI command not stored]"]),
             json.dumps([{"command": "[CLI command not stored]", "status": status,
                          "output": "[CLI output not stored]", "error_code": "CLI_REJECTED" if status == "failed" else None}]),
             status, datetime.now(UTC).isoformat()),
        )


@router.websocket("/nodes/{node_id}/cli")
async def cli_session(websocket: WebSocket, node_id: str) -> None:
    """เปิด CLI แยก session, ส่งทีละบรรทัด และปล่อย lock เมื่อ socket ปิด"""
    await websocket.accept()
    with get_db() as db:
        row = db.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
    if row is None:
        await websocket.send_json({"type": "error", "message": "ไม่พบ Node นี้"})
        await websocket.close(code=4404)
        return

    lock = await get_node_lock(node_id)
    try:
        await asyncio.wait_for(lock.acquire(), timeout=30)
    except TimeoutError:
        await websocket.send_json({"type": "error", "message": "Node กำลังอ่านสถานะหรือทำงานอื่นอยู่ กรุณาลองเชื่อม CLI อีกครั้ง"})
        await websocket.close(code=4409)
        return

    connection: Any = None
    try:
        connection = await run_in_threadpool(open_terminal, build_transport_from_row(dict(row)))
        prompt = await run_in_threadpool(terminal_prompt, connection)
        await websocket.send_json({"type": "ready", "prompt": prompt})
        while True:
            payload = await asyncio.wait_for(websocket.receive_json(), timeout=_SESSION_IDLE_SECONDS)
            if isinstance(payload, dict) and payload.get("action") == "disconnect":
                break
            command = payload.get("command") if isinstance(payload, dict) else None
            if not isinstance(command, str) or not command.strip() or len(command) > _MAX_COMMAND_LENGTH or any(ch in command for ch in "\r\n\0"):
                await websocket.send_json({"type": "error", "message": "พิมพ์คำสั่งหนึ่งบรรทัด ความยาวไม่เกิน 256 ตัวอักษร"})
                continue
            correlation_id = str(uuid.uuid4())
            try:
                output, prompt = await run_in_threadpool(send_terminal_line, connection, command)
                result_status = "failed" if _CLI_FAILURE.search(output) else "success"
                _record_cli_result(node_id, row["hostname"], correlation_id, result_status)
                await websocket.send_json({"type": "result", "output": output, "prompt": prompt,
                                           "status": result_status, "correlation_id": correlation_id,
                                           "password_prompt": output.rstrip().lower().endswith("password:")})
            except Exception:
                _record_cli_result(node_id, row["hostname"], correlation_id, "failed")
                await websocket.send_json({"type": "error", "message": "ส่งคำสั่งไม่สำเร็จหรือการเชื่อมต่อหลุด กรุณาเชื่อมต่อใหม่",
                                           "correlation_id": correlation_id})
                break
    except (WebSocketDisconnect, TimeoutError):
        pass
    except Exception:
        with suppress(Exception):
            await websocket.send_json({"type": "error", "message": "เปิด CLI ไม่สำเร็จ กรุณาตรวจสอบการเชื่อมต่อ"})
    finally:
        if connection is not None:
            with suppress(Exception):
                await run_in_threadpool(close_terminal, connection)
        lock.release()
        with suppress(Exception):
            await websocket.close()
