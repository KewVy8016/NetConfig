# จุดเข้าหลักของ NetConfig backend — FastAPI app, lifecycle และ exception handlers
# ห้ามใส่ business logic ที่นี่ ทุก logic อยู่ใน service/router

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.database import init_db
from backend.routers import config, nodes

# ---------------------------------------------------------------------------
# Lifespan — startup และ shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """รัน startup tasks ก่อน serve request และ cleanup เมื่อปิด

    Startup: ตรวจ Fernet key (จาก config validation) และ init SQLite schema
    Shutdown: ไม่มี async resource ที่ต้อง close (Netmiko connection อายุสั้น)
    """
    # get_settings() จะ fail fast หาก key ไม่ถูกต้อง
    settings = get_settings()
    init_db()
    print(f"[NetConfig] Backend พร้อมทำงาน — DB: {settings.db_path}")
    yield
    print("[NetConfig] Backend ปิดแล้ว")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NetConfig API",
    version="0.1.0",
    description="Web API สำหรับตั้งค่า Cisco IOS ผ่าน SSH/Telnet/Serial",
    lifespan=lifespan,
    # ปิด /docs ใน production ได้ด้วยการตั้ง docs_url=None
)

# CORS — อนุญาตเฉพาะ origin ที่ตั้งใน settings
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(nodes.router)
app.include_router(config.router)


# ---------------------------------------------------------------------------
# Global exception handlers — ห้ามให้ traceback หรือ secret รั่ว
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """จับ exception ที่ไม่ได้ handle — คืน error code ทั่วไปโดยไม่เผย internal detail"""
    correlation_id = str(uuid.uuid4())
    # Log รายละเอียดสำหรับ developer (ไม่ส่งให้ client)
    print(f"[ERROR] Unhandled exception | correlation_id={correlation_id} | {exc!r}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "INTERNAL_ERROR",
            "message_th": "เกิดข้อผิดพลาดภายในระบบ กรุณาลองใหม่หรือติดต่อผู้ดูแล",
            "correlation_id": correlation_id,
        },
    )


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """ตรวจสอบว่า backend ทำงานปกติ"""
    return {"status": "ok", "service": "netconfig"}
