"""
EduManage Pro - Sensitive Data Protection, Field Encryption & Masking
Provides:
- Authenticated field-level encryption (PBKDF2-SHA256 + Fernet AES-128-CBC + HMAC-SHA256)
- Keyed deterministic HMAC-SHA256 blind indexing for encrypted lookups
- Role-aware display & report masking (phone, email, NID, bank account, salary)
- CSV / Excel Formula Injection neutralizer (`sanitize_csv_cell`)
"""

import base64
import hashlib
import hmac
import os
from pathlib import Path
import secrets
from typing import Any, Dict, Iterable, Optional

from app.config.settings import DATA_DIR


DATA_KEY_FILE = DATA_DIR / ".data_protection.key"
ENC_PREFIX = "enc:v1:"
_DANGEROUS_CSV_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _load_or_create_data_key() -> bytes:
    """Resolve institutional data-protection key from env var or 0600 local keyfile."""
    env_key = os.getenv("EDUMANAGE_DATA_KEY", "").strip()
    if env_key:
        return hashlib.sha256(env_key.encode("utf-8")).digest()

    DATA_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if DATA_KEY_FILE.exists():
        raw = DATA_KEY_FILE.read_text(encoding="utf-8").strip()
        if raw:
            return hashlib.sha256(raw.encode("utf-8")).digest()

    generated = secrets.token_urlsafe(48)
    DATA_KEY_FILE.write_text(generated, encoding="utf-8")
    try:
        os.chmod(DATA_KEY_FILE, 0o600)
    except Exception:
        pass
    return hashlib.sha256(generated.encode("utf-8")).digest()


class SensitiveDataProtector:
    """Field-level encryption, blind indexing, PII masking, and export formula sanitization."""

    @staticmethod
    def _derive_fernet_key(salt: bytes) -> bytes:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        master = _load_or_create_data_key()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=200_000,
        )
        return base64.urlsafe_b64encode(kdf.derive(master))

    @classmethod
    def encrypt_sensitive(cls, plaintext: Optional[str]) -> Optional[str]:
        if plaintext is None:
            return None
        s = str(plaintext)
        if not s:
            return ""
        if s.startswith(ENC_PREFIX):
            return s
        from cryptography.fernet import Fernet

        salt = secrets.token_bytes(16)
        token = Fernet(cls._derive_fernet_key(salt)).encrypt(s.encode("utf-8"))
        blob = base64.urlsafe_b64encode(salt + token).decode("ascii")
        return f"{ENC_PREFIX}{blob}"

    @classmethod
    def decrypt_sensitive(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        s = str(value)
        if not s.startswith(ENC_PREFIX):
            return s
        from cryptography.fernet import Fernet

        raw = base64.urlsafe_b64decode(s[len(ENC_PREFIX):].encode("ascii"))
        salt, token = raw[:16], raw[16:]
        plain = Fernet(cls._derive_fernet_key(salt)).decrypt(token)
        return plain.decode("utf-8")

    @staticmethod
    def blind_index(value: Optional[str], context: str = "default") -> str:
        """Compute deterministic keyed HMAC-SHA256 digest for equality search on encrypted columns."""
        if not value:
            return ""
        master = _load_or_create_data_key()
        msg = f"{context}:{str(value).strip().lower()}".encode("utf-8")
        return hmac.new(master, msg, hashlib.sha256).hexdigest()

    @staticmethod
    def mask_phone(phone: Optional[str]) -> str:
        if not phone:
            return "—"
        s = str(phone).strip()
        if len(s) <= 4:
            return "*" * len(s)
        return f"{s[:3]}{'*' * max(2, len(s) - 5)}{s[-2:]}"

    @staticmethod
    def mask_email(email: Optional[str]) -> str:
        if not email or "@" not in str(email):
            return "—" if not email else "***"
        local, domain = str(email).strip().split("@", 1)
        vis = local[:2] if len(local) >= 2 else local[:1]
        return f"{vis}***@{domain}"

    @staticmethod
    def mask_nid(nid: Optional[str]) -> str:
        if not nid:
            return "—"
        s = str(nid).strip()
        if len(s) <= 4:
            return "*" * len(s)
        return f"{'*' * (len(s) - 4)}{s[-4:]}"

    @staticmethod
    def mask_bank_account(acct: Optional[str]) -> str:
        return SensitiveDataProtector.mask_nid(acct)

    @staticmethod
    def mask_sensitive_dict(
        row: Dict[str, Any],
        *,
        can_view_pii: bool = False,
        pii_fields: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        if can_view_pii:
            return dict(row)
        targets = set(pii_fields or ("phone", "guardian_phone", "email", "guardian_email", "nid", "guardian_nid", "bank_account", "basic_salary"))
        out = dict(row)
        for k, v in list(out.items()):
            if k not in targets or v is None:
                continue
            kl = k.lower()
            if "email" in kl:
                out[k] = SensitiveDataProtector.mask_email(str(v))
            elif "phone" in kl:
                out[k] = SensitiveDataProtector.mask_phone(str(v))
            elif "nid" in kl or "bank" in kl:
                out[k] = SensitiveDataProtector.mask_nid(str(v))
            elif "salary" in kl:
                out[k] = "[RESTRICTED]"
        return out

    @staticmethod
    def sanitize_csv_cell(value: Any) -> str:
        """Prevent spreadsheet formula injection (=, +, -, @, tab, CR) on CSV/Excel export."""
        if value is None:
            return ""
        text = str(value)
        if text and text[0] in _DANGEROUS_CSV_PREFIXES:
            return "'" + text
        return text
