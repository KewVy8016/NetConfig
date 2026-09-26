"""ทดสอบ audit history, filter/pagination และ Show success/failure"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from backend.database import get_db
from backend.tests.conftest import SSH_NODE_PAYLOAD


def _node(client) -> str:
    """สร้าง Node สำหรับประวัติ โดยไม่เชื่อมอุปกรณ์จริง"""
    suffix = uuid.uuid4().hex[:8]
    host = f"10.74.{int(suffix[:2], 16)}.{int(suffix[2:4], 16)}"
    response = client.post(
        "/nodes",
        json={**SSH_NODE_PAYLOAD, "hostname": f"HistoryNode-{suffix}", "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": host}},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_history_filters_pages_and_keeps_node_options(client) -> None:
    """Filter และ pagination คืนยอดรวมถูกต้อง แต่ตัวเลือก Node ไม่ถูกจำกัดตามหน้า"""
    node_id = _node(client)
    other_id = _node(client)
    with get_db() as conn:
        for current_node, overall_status in [(node_id, "success"), (node_id, "failed"), (other_id, "success")]:
            conn.execute(
                """INSERT INTO command_history
                   (id, correlation_id, node_id, operation_id, command_type, commands_json, result_json, overall_status, created_at)
                   VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), str(uuid.uuid4()), current_node, "Test Command", json.dumps(["show version"]),
                 json.dumps([{"command": "show version", "status": overall_status, "output": "ok"}]), overall_status,
                 datetime.now(UTC).isoformat()),
            )
    response = client.get(f"/history?node_id={node_id}&limit=1&offset=1")
    assert response.status_code == 200
    assert response.headers["x-total-count"] == "2"
    assert len(response.json()) == 1
    assert response.json()[0]["node_hostname"].startswith("HistoryNode-")
    assert response.json()[0]["correlation_id"]
    assert len(client.get("/history/nodes").json()) >= 2
    assert client.get("/history?overall_status=unknown").status_code == 422
    assert client.get("/history?limit=101").status_code == 422


def test_history_time_range_filters_before_pagination(client) -> None:
    """ช่วงเวลาแบบ UTC กรองยอดรวมก่อนแบ่งหน้า และปฏิเสธช่วงกลับด้าน/ไม่มีเขตเวลา"""
    node_id = _node(client)
    with get_db() as conn:
        for hour in (8, 9, 10):
            conn.execute(
                """INSERT INTO command_history
                   (id, correlation_id, node_id, operation_id, command_type, commands_json, result_json, overall_status, created_at)
                   VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), str(uuid.uuid4()), node_id, "Test Command", json.dumps(["show version"]),
                 json.dumps([]), "success", datetime(2026, 9, 23, hour, tzinfo=UTC).isoformat()),
            )
    params = {"node_id": node_id, "created_from": "2026-09-23T09:00:00Z", "created_before": "2026-09-23T10:00:00Z", "limit": 1}
    response = client.get("/history", params=params)
    assert response.status_code == 200
    assert response.headers["x-total-count"] == "1"
    assert len(response.json()) == 1
    assert response.json()[0]["created_at"].startswith("2026-09-23T09:00")
    assert client.get("/history", params={**params, "created_from": "2026-09-23T10:00:00Z"}).status_code == 422
    assert client.get("/history", params={**params, "created_from": "2026-09-23T09:00:00"}).status_code == 422


def test_show_success_and_failure_are_audited(client) -> None:
    """Show ที่สำเร็จและล้มเหลวต้องมี audit และซ่อน secret ใน output"""
    node_id = _node(client)
    command = "show ip interface brief"
    with patch("backend.routers.config.send_show_command", return_value="password=hidden-value"):
        success = client.get(f"/nodes/{node_id}/show", params={"command": command})
    assert success.status_code == 200
    with patch("backend.routers.config.send_show_command", side_effect=RuntimeError("password=hidden-value")):
        failure = client.get(f"/nodes/{node_id}/show", params={"command": command})
    assert failure.status_code == 502
    entries = client.get(f"/history?node_id={node_id}").json()
    show_entries = [item for item in entries if item["command_type"] == "Show Command"]
    assert {item["overall_status"] for item in show_entries} == {"success", "failed"}
    assert all("hidden-value" not in json.dumps(item) for item in show_entries)
    hostname = show_entries[0]["node_hostname"]
    assert client.delete(f"/nodes/{node_id}").status_code == 204
    assert client.get(f"/history?node_id={node_id}").json()[0]["node_hostname"] == hostname
