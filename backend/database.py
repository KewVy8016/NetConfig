# โมดูลจัดการ SQLite database สำหรับ NetConfig
# สร้างตารางครั้งแรก (idempotent) และให้ connection ต่อ request

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from backend.config import get_settings

# SQL DDL สำหรับสร้างตารางครั้งแรก — idempotent ด้วย IF NOT EXISTS
_DDL = """
CREATE TABLE IF NOT EXISTS nodes (
    id          TEXT PRIMARY KEY,
    hostname    TEXT NOT NULL,
    host        TEXT,
    device_type TEXT NOT NULL,
    port        INTEGER,
    transport   TEXT NOT NULL CHECK(transport IN ('ssh', 'telnet', 'serial')),
    enc_username    TEXT NOT NULL,
    enc_password    TEXT NOT NULL,
    enc_secret      TEXT,
    serial_port     TEXT,
    serial_baudrate INTEGER,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
    ,status     TEXT NOT NULL DEFAULT 'unknown'
);

CREATE TABLE IF NOT EXISTS operations (
    id              TEXT PRIMARY KEY,
    correlation_id  TEXT NOT NULL,
    node_id         TEXT NOT NULL REFERENCES nodes(id),
    operation_type  TEXT NOT NULL,
    payload_hash    TEXT,
    status          TEXT NOT NULL,
    rendered_commands TEXT,
    result_json     TEXT,
    error_code      TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (node_id) REFERENCES nodes(id)
);

CREATE TABLE IF NOT EXISTS command_history (
    id              TEXT PRIMARY KEY,
    correlation_id  TEXT NOT NULL,
    node_id         TEXT NOT NULL,
    operation_id    TEXT,
    command_type    TEXT NOT NULL,
    commands_json   TEXT NOT NULL,
    result_json     TEXT NOT NULL,
    overall_status  TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
"""


def _get_db_path() -> Path:
    """คืน path ของไฟล์ SQLite จาก settings"""
    return Path(get_settings().db_path)


def init_db() -> None:
    """สร้างตารางทั้งหมดหากยังไม่มี — เรียกตอน startup เท่านั้น"""
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(_DDL)
        # รองรับฐานข้อมูลที่สร้างจาก Phase 1 ก่อนมีสถานะ node แบบ persistent
        columns = {row[1] for row in conn.execute("PRAGMA table_info(nodes)").fetchall()}
        if "status" not in columns:
            conn.execute("ALTER TABLE nodes ADD COLUMN status TEXT NOT NULL DEFAULT 'unknown'")
        conn.commit()


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager คืน SQLite connection พร้อม row_factory

    ใช้เป็น dependency ใน FastAPI route:
        with get_db() as conn: ...

    ไม่ใช้ connection pool เพราะ SQLite thread-safety ถูก enforce ที่ Netmiko layer
    """
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
