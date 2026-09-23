# Unit tests สำหรับ encryption service
# ทดสอบ encrypt/decrypt และ redaction โดยไม่ต้องเชื่อมต่อ DB หรืออุปกรณ์

from __future__ import annotations

import pytest
from cryptography.fernet import InvalidToken

from backend.services.encryption import (
    REDACTED,
    decrypt,
    encrypt,
    redact_dict,
    redact_text,
)


class TestEncryptDecrypt:
    """ทดสอบการเข้ารหัสและถอดรหัส Fernet"""

    def test_encrypt_returns_string(self):
        """encrypt ต้องคืน string ที่ไม่ใช่ plaintext"""
        result = encrypt("cisco123")
        assert isinstance(result, str)
        assert "cisco123" not in result

    def test_decrypt_roundtrip(self):
        """decrypt ต้องคืน plaintext เดิมเมื่อใช้ key เดียวกัน"""
        plaintext = "enable_secret_456"
        assert decrypt(encrypt(plaintext)) == plaintext

    def test_encrypt_empty_string(self):
        """encrypt/decrypt ต้องทำงานกับ string ว่างได้"""
        assert decrypt(encrypt("")) == ""

    def test_encrypt_unicode(self):
        """encrypt/decrypt ต้องรองรับ Unicode (Thai, special chars)"""
        plaintext = "รหัสผ่าน!@#"
        assert decrypt(encrypt(plaintext)) == plaintext

    def test_decrypt_wrong_token_raises(self):
        """decrypt ด้วย token ผิดต้อง raise InvalidToken"""
        with pytest.raises(InvalidToken):
            decrypt("not-a-valid-fernet-token")

    def test_two_encryptions_different(self):
        """Fernet ใช้ IV แบบสุ่ม ดังนั้น encrypt ซ้ำต้องได้ผลต่างกัน"""
        enc1 = encrypt("same_password")
        enc2 = encrypt("same_password")
        assert enc1 != enc2


class TestRedactText:
    """ทดสอบ redact_text กับ CLI output และ error message"""

    def test_redact_password_equals(self):
        """ซ่อน password=xxx ใน text"""
        result = redact_text("password=cisco123 rest of line")
        assert "cisco123" not in result
        assert REDACTED in result

    def test_redact_password_colon(self):
        """ซ่อน password: xxx ใน text"""
        result = redact_text("password: secret_value")
        assert "secret_value" not in result

    def test_safe_text_unchanged(self):
        """Text ที่ไม่มี secret ต้องไม่เปลี่ยนแปลง"""
        safe = "show ip interface brief"
        assert redact_text(safe) == safe

    def test_redact_case_insensitive(self):
        """Pattern ต้องจับ Password, PASSWORD ฯลฯ"""
        result = redact_text("PASSWORD=TopSecret")
        assert "TopSecret" not in result


class TestRedactDict:
    """ทดสอบ redact_dict กับ dict ที่มี sensitive keys"""

    def test_password_key_redacted(self):
        """ต้อง redact value ของ key 'password'"""
        d = {"username": "admin", "password": "cisco123"}
        result = redact_dict(d)
        assert result["password"] == REDACTED
        assert result["username"] == "admin"

    def test_secret_key_redacted(self):
        """ต้อง redact value ของ key 'secret'"""
        d = {"secret": "enable_pass"}
        assert redact_dict(d)["secret"] == REDACTED

    def test_enc_password_redacted(self):
        """ต้อง redact key 'enc_password' (DB field)"""
        d = {"enc_password": "gAAAA...ciphertext"}
        assert redact_dict(d)["enc_password"] == REDACTED

    def test_non_sensitive_preserved(self):
        """Key ที่ไม่ sensitive ต้องไม่ถูก redact"""
        d = {"hostname": "R1", "host": "192.168.1.11"}
        result = redact_dict(d)
        assert result == d
