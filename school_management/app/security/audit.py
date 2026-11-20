"""
EduManage Pro - Enterprise Audit Trail & Secret Redaction Engine
Guarantees every administrative & data mutation tracks:
  WHO | WHAT | WHEN | MODULE | RECORD | BEFORE | AFTER
While strictly ensuring passwords, passphrases, API keys, raw tokens, and secrets
are NEVER stored in audit logs, descriptions, alerts, or Python log files.
"""

from datetime import date, datetime
import json
import re
import socket
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from app.models.activity import ActivityLog
from app.models.base import utc_now
from app.models.user import SecurityAlert


SENSITIVE_KEY_TOKENS: Tuple[str, ...] = (
    "password",
    "passwd",
    "pwd",
    "passphrase",
    "secret",
    "token",
    "api_key",
    "apikey",
    "auth_key",
    "private_key",
    "master_key",
    "fernet_key",
    "credential",
    "authorization",
    "pin_code",
    "cvv",
)

# Patterns to scrub inline secrets from free-text descriptions or logs
_INLINE_SECRET_PATTERNS = [
    re.compile(r"(?i)(password|passwd|pwd|passphrase|secret|token|api_key|apikey|authorization)\s*[:=]\s*(['\"]?)([^\s,;'\"]+)\2"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}"),  # bcrypt hashes
    re.compile(r"gAAAAA[A-Za-z0-9\-_]{20,}={0,2}"),     # Fernet ciphertexts
]


def _is_sensitive_key(key: Any) -> bool:
    if key is None:
        return False
    low = str(key).strip().lower()
    if low in ("password_changed_at", "must_change_password", "is_default_password", "failed_login_attempts"):
        return False
    return any(tok in low for tok in SENSITIVE_KEY_TOKENS)


def redact_text_secrets(text: Optional[str]) -> str:
    """Scrub any accidental inline passwords, bearer tokens, bcrypt hashes, or secrets from strings."""
    if text is None:
        return ""
    s = str(text)
    for idx, pat in enumerate(_INLINE_SECRET_PATTERNS):
        if idx == 0:
            s = pat.sub(lambda m: f"{m.group(1)}=[REDACTED]", s)
        elif idx == 1:
            s = pat.sub("Bearer [REDACTED]", s)
        else:
            s = pat.sub("[REDACTED]", s)
    return s


def redact_secrets(value: Any, _depth: int = 0) -> Any:
    """Recursively sanitize dicts, lists, dates, and scalars before persistence in audit logs."""
    if _depth > 8:
        return "[TRUNCATED]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in value.items():
            if _is_sensitive_key(k):
                cleaned[str(k)] = "[REDACTED]"
            else:
                cleaned[str(k)] = redact_secrets(v, _depth + 1)
        return cleaned
    if isinstance(value, (list, tuple, set)):
        return [redact_secrets(item, _depth + 1) for item in value]
    if isinstance(value, bytes):
        return f"<bytes len={len(value)}>"
    return redact_text_secrets(str(value))


def compute_changed_fields(before: Any, after: Any) -> List[str]:
    """Return sorted field names whose values differ between before & after snapshots."""
    if isinstance(before, dict) and isinstance(after, dict):
        keys = set(before.keys()) | set(after.keys())
        return sorted(k for k in keys if before.get(k) != after.get(k))
    if isinstance(after, dict):
        return sorted(str(k) for k in after.keys())
    if isinstance(before, dict):
        return sorted(str(k) for k in before.keys())
    return []


def _get_workstation() -> str:
    try:
        return socket.gethostname()[:120]
    except Exception:
        return "localhost"


class AuditService:
    """Unified WHO/WHAT/WHEN/MODULE/RECORD/BEFORE/AFTER audit logger and suspicious alert emitter."""

    @staticmethod
    def record(
        db: Session,
        *,
        action: str,
        module: str,
        description: str,
        who_user: Optional[Any] = None,
        username: Optional[str] = None,
        actor_role: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[Any] = None,
        record_label: Optional[str] = None,
        before: Any = None,
        after: Any = None,
        severity: str = "INFO",
        ip_address: str = "127.0.0.1",
        workstation: Optional[str] = None,
        session_id: Optional[str] = None,
        is_admin_action: Optional[bool] = None,
        commit: bool = False,
    ) -> ActivityLog:
        user_id = getattr(who_user, "id", None) if who_user is not None else None
        uname = username or (getattr(who_user, "username", None) if who_user is not None else None) or "system"
        role_lbl = actor_role
        if not role_lbl and who_user is not None and getattr(who_user, "role", None) is not None:
            role_lbl = getattr(who_user.role, "name", None) or getattr(who_user.role, "display_name", None)

        safe_before = redact_secrets(before) if before is not None else None
        safe_after = redact_secrets(after) if after is not None else None
        changed = compute_changed_fields(safe_before, safe_after)

        if is_admin_action is None:
            is_admin_action = (
                module.upper() in ("SECURITY", "DATA_PROTECTION", "SETTINGS")
                or (role_lbl or "").lower() in ("super_admin", "administrator")
            )

        entry = ActivityLog(
            user_id=user_id,
            username=str(uname)[:60],
            actor_role=(str(role_lbl)[:80] if role_lbl else None),
            action=str(action)[:80],
            module=str(module).upper()[:60],
            entity_type=(str(entity_type)[:60] if entity_type else None),
            entity_id=(str(entity_id)[:60] if entity_id is not None else None),
            record_label=(redact_text_secrets(str(record_label))[:255] if record_label else None),
            description=redact_text_secrets(description),
            before_data=(json.dumps(safe_before, ensure_ascii=False, sort_keys=True) if safe_before is not None else None),
            after_data=(json.dumps(safe_after, ensure_ascii=False, sort_keys=True) if safe_after is not None else None),
            changed_fields=(json.dumps(changed, ensure_ascii=False) if changed else None),
            ip_address=ip_address,
            workstation=(workstation or _get_workstation())[:120],
            session_id=session_id,
            severity=severity,
            is_admin_action=bool(is_admin_action),
        )
        db.add(entry)
        if commit:
            db.commit()
            db.refresh(entry)
        else:
            db.flush()
        return entry

    @staticmethod
    def raise_alert(
        db: Session,
        *,
        alert_type: str,
        description: str,
        severity: str = "HIGH",
        module: str = "SECURITY",
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: str = "127.0.0.1",
        workstation: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
        commit: bool = False,
    ) -> SecurityAlert:
        code = f"SEC-{utc_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        safe_ev = redact_secrets(evidence) if evidence is not None else None
        ev_str = json.dumps(safe_ev, ensure_ascii=False, sort_keys=True)[:1990] if safe_ev is not None else None

        alert = SecurityAlert(
            alert_code=code,
            alert_type=str(alert_type)[:60],
            severity=str(severity).upper()[:20],
            module=str(module).upper()[:60],
            user_id=user_id,
            username=(str(username)[:120] if username else None),
            ip_address=ip_address,
            workstation=(workstation or _get_workstation())[:120],
            description=redact_text_secrets(description)[:500],
            evidence_json=ev_str,
            status="OPEN",
        )
        db.add(alert)
        if commit:
            db.commit()
            db.refresh(alert)
        else:
            db.flush()
        return alert
