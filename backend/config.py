# ไฟล์กำหนดค่า environment สำหรับ NetConfig backend
# โหลด Fernet key จาก environment เท่านั้น — ห้าม hardcode หรือ commit

from __future__ import annotations

import sys
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ค่าตั้งต้นของระบบ โหลดจาก environment variables หรือไฟล์ .env

    หาก NETCONFIG_FERNET_KEY ไม่ถูกตั้ง ระบบจะหยุดทำงานทันที
    เพื่อป้องกัน credential รั่วไหล
    """

    model_config = SettingsConfigDict(
        env_prefix="NETCONFIG_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    fernet_key: str = Field(..., description="Fernet key 32 bytes base64-encoded")
    db_path: str = Field(default="./netconfig.db", description="Path ไฟล์ SQLite")
    host: str = Field(default="127.0.0.1", description="Host ของ backend")
    port: int = Field(default=8000, description="Port ของ backend")
    cors_origins: list[str] = Field(
        default=["http://localhost:5173"],
        description="CORS origins ที่อนุญาต",
    )

    @field_validator("fernet_key")
    @classmethod
    def validate_fernet_key(cls, v: str) -> str:
        """ตรวจสอบว่า Fernet key มีรูปแบบที่ถูกต้อง ก่อน startup"""
        import base64

        try:
            raw = base64.urlsafe_b64decode(v)
            if len(raw) != 32:
                raise ValueError("Fernet key ต้องมีขนาด 32 bytes")
        except Exception as exc:
            print(
                f"[ERROR] NETCONFIG_FERNET_KEY ไม่ถูกต้อง: {exc}\n"
                "สร้าง key ใหม่ด้วย: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
                "แล้วตั้งค่าใน environment หรือไฟล์ .env",
                file=sys.stderr,
            )
            sys.exit(1)
        return v


@lru_cache
def get_settings() -> Settings:
    """คืน Settings singleton — ล้ม gracefully เมื่อ config ไม่ครบ"""
    return Settings()  # type: ignore[call-arg]
