# บริการเข้ารหัสและซ่อน credential สำหรับ NetConfig
# ใช้ Fernet (AES-128-CBC + HMAC-SHA256) — key มาจาก environment เท่านั้น

from __future__ import annotations

import re

from cryptography.fernet import Fernet

from backend.config import get_settings

# Pattern สำหรับ redact — ใช้กับ log และ error message
_SECRET_PATTERNS = [
    re.compile(r"(?i)(password|secret|passwd|pwd)(\s*[=:]\s*)\S+"),
    re.compile(r"(?i)(enable\s+secret)(\s+)\S+"),
]

# Placeholder แทน secret ใน log/response
REDACTED = "[REDACTED]"


def _get_fernet() -> Fernet:
    """สร้าง Fernet instance จาก key ใน settings

    Returns:
        Fernet instance พร้อมใช้งาน

    Raises:
        SystemExit: หาก key ไม่ถูกต้อง (จาก config validation)
    """
    return Fernet(get_settings().fernet_key.encode())


def encrypt(plaintext: str) -> str:
    """เข้ารหัสข้อความด้วย Fernet และคืน ciphertext เป็น string

    Parameters:
        plaintext: ข้อความที่ต้องการเข้ารหัส

    Returns:
        Ciphertext base64-encoded string
    """
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """ถอดรหัส ciphertext ที่เข้ารหัสด้วย Fernet

    Parameters:
        ciphertext: Ciphertext base64-encoded string

    Returns:
        Plaintext ที่ถอดรหัสแล้ว

    Raises:
        cryptography.fernet.InvalidToken: เมื่อ key ไม่ตรงหรือข้อมูลเสีย
    """
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def redact_text(text: str) -> str:
    """แทนที่ secret ที่อาจปรากฏในข้อความด้วย [REDACTED]

    ใช้กับ CLI output, error message และ log ก่อนส่งให้ผู้ใช้หรือบันทึก

    Parameters:
        text: ข้อความดิบที่อาจมี secret

    Returns:
        ข้อความที่ redact แล้ว — ปลอดภัยสำหรับ log/response
    """
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)
    return text


def redact_dict(data: dict) -> dict:
    """ซ่อน key ที่มีชื่อเกี่ยวกับ secret ใน dict

    Parameters:
        data: dict ที่อาจมี key ชื่อ password, secret ฯลฯ

    Returns:
        dict ใหม่ที่ value ของ key อันตรายถูก redact
    """
    sensitive = {"password", "secret", "passwd", "pwd", "enc_password", "enc_secret"}
    return {
        k: REDACTED if k.lower() in sensitive else v
        for k, v in data.items()
    }
