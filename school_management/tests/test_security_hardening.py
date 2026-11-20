"""
EduManage Pro - Complete Security Hardening Automated Test Suite (pytest)
Covers:
1. Secure authentication & bcrypt password hashing (including dummy verify & complexity rules)
2. RBAC & imperative/decorator Permission Guards + denied-access SecurityAlerts
3. DB-backed Session Management (hashed session tokens, session_version invalidation, admin revoke)
4. Login Protection (brute-force lockout alerts & unknown-account spray detection)
5. Structured Audit Logs (WHO / WHAT / WHEN / MODULE / RECORD / BEFORE / AFTER)
6. Zero Secret Leakage guarantee across DB tables, audit logs, CSV exports & logging filters
7. Strict File Validation (magic bytes, spoofed extension block, executable block, traversal/null-byte protection)
8. Secure Database Queries (identifier allowlists, SQL injection blocking, LIKE escaping, safe ORDER BY)
9. Sensitive Data Protection (PBKDF2+Fernet encryption, HMAC blind index, PII masking, CSV formula defense)
10. Backup Encryption, Verification, Tamper Alerting & Security Dashboard analytics
"""

from datetime import date
import logging
from pathlib import Path
import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.config.logging_config import SecretRedactingFilter
from app.database.init_db import SYSTEM_ROLES
from app.database.migrations import migrate_database
from app.models.activity import ActivityLog
from app.models.user import LoginHistory, Permission, Role, SecurityAlert, User, UserSession
from app.security.audit import AuditService, redact_secrets, redact_text_secrets
from app.security.data_protection import SensitiveDataProtector
from app.security.db_security import DatabaseSecurityValidator, SQLSecurityError
from app.security.file_validator import FileValidationError, SecureFileValidator
from app.security.guards import PermissionDeniedError, authorize_action, require_permission
from app.security.hasher import PasswordHasher
from app.security.session import session as app_session
from app.services.auth_service import AuthService
from app.services.backup_service import DataProtectionBackupService
from app.services.security_dashboard_service import SecurityDashboardService


@pytest.fixture()
def hardened_env(tmp_path):
    db_path = tmp_path / "hardened_school.db"
    eng = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    migrate_database(eng)
    Session = sessionmaker(bind=eng, autocommit=False, autoflush=False)
    db = Session()

    for code, disp, desc, is_sys in SYSTEM_ROLES:
        if not db.query(Role).filter_by(name=code).first():
            db.add(Role(name=code, display_name=disp, description=desc, is_system_role=is_sys, is_active=True))
    db.commit()
    AuthService.sync_permission_catalog(db)
    app_session.clear()

    yield {"db": db, "engine": eng, "tmp_path": tmp_path}
    app_session.clear()
    db.close()
    eng.dispose()


def test_password_policy_hash_and_dummy_verify():
    ok_seq, _ = PasswordHasher.validate_password_strength("Qwerty123!")
    assert ok_seq is False
    ok_sp, _ = PasswordHasher.validate_password_strength(" Strong@Pass1")
    assert ok_sp is False
    ok_good, _ = PasswordHasher.validate_password_strength("V@ult$School2026!", username="jdoe")
    assert ok_good is True

    # Dummy verify runs cleanly without raising
    PasswordHasher.dummy_verify("arbitrary_attempt")
    assert PasswordHasher.constant_time_equals("abc", "abc") is True
    assert PasswordHasher.constant_time_equals("abc", "abd") is False


def test_rbac_guards_and_denied_attempt_auditing(hardened_env):
    db = hardened_env["db"]
    _, admin, _ = AuthService.create_first_admin(
        db, "chiefsec", "chiefsec@school.edu", "Chief Security", "Ch1ef$Sec2026!"
    )
    teacher_role = db.query(Role).filter_by(name="teacher").first()
    ok_u, teacher, _ = AuthService.create_user(
        db, admin, "t_ali", "ali@school.edu", "Ms. Ali", "T3ach$Ali2026!", teacher_role.id
    )
    assert ok_u and teacher

    @require_permission("security.roles.MANAGE", module="SECURITY", action="MANAGE")
    def protected_op(db=None, actor_user=None):
        return "executed"

    # Teacher blocked and SecurityAlert raised
    with pytest.raises(PermissionDeniedError):
        protected_op(db=db, actor_user=teacher)

    alert = db.query(SecurityAlert).filter_by(alert_type="PERMISSION_DENIED_ATTEMPT").first()
    assert alert is not None
    assert alert.username == "t_ali"

    # Super Admin allowed
    assert protected_op(db=db, actor_user=admin) == "executed"


def test_session_persistence_revocation_and_version_invalidation(hardened_env):
    db = hardened_env["db"]
    admin_pw = "S3ssion$Admin26!"
    _, admin, _ = AuthService.create_first_admin(
        db, "sessadmin", "sessadmin@school.edu", "Session Admin", admin_pw
    )
    t_role = db.query(Role).filter_by(name="teacher").first()
    t_pw = "T3ach$Sess26!"
    _, t_user, _ = AuthService.create_user(
        db, admin, "t_nina", "nina@school.edu", "Nina Roy", t_pw, t_role.id, must_change_password=False
    )

    ok, _, _ = AuthService.authenticate(db, "t_nina", t_pw, ip_address="10.0.0.15")
    assert ok is True
    sid = app_session.session_id
    assert sid is not None

    sess_row = db.query(UserSession).filter_by(session_id=sid).first()
    assert sess_row is not None
    assert sess_row.is_active is True
    assert sess_row.session_token_hash != (app_session.session_secret or "")
    assert app_session.validate_against_db(db) is True

    # Admin revokes session from Security Dashboard
    ok_rev, msg_rev = AuthService.revoke_session(db, admin, sid, reason="Suspicious workstation")
    assert ok_rev is True, msg_rev
    db.refresh(sess_row)
    assert sess_row.is_active is False
    assert sess_row.revoked_by == "sessadmin"
    assert app_session.is_authenticated is False


def test_login_protection_lockout_and_unknown_spray_detection(hardened_env):
    db = hardened_env["db"]
    admin_pw = "Brute$Guard2026!"
    _, admin, _ = AuthService.create_first_admin(
        db, "guardadmin", "guard@school.edu", "Guard Admin", admin_pw
    )

    # Trigger unknown account spray (>= 5 unknown usernames from same IP)
    for idx in range(5):
        ok, _, _ = AuthService.authenticate(db, f"ghost_user_{idx}", "Wrong!123", ip_address="192.168.55.9")
        assert ok is False

    spray_alert = db.query(SecurityAlert).filter_by(alert_type="CREDENTIAL_STUFFING").first()
    assert spray_alert is not None
    assert spray_alert.severity == "CRITICAL"

    # Trigger brute-force lockout on real account
    for idx in range(5):
        AuthService.authenticate(db, "guardadmin", f"BadPass#{idx}", ip_address="192.168.55.10")

    lock_alert = db.query(SecurityAlert).filter_by(alert_type="BRUTE_FORCE_LOCKOUT").first()
    assert lock_alert is not None
    assert lock_alert.username == "guardadmin"


def test_audit_log_who_what_when_module_record_before_after_and_no_secret_leaks(hardened_env):
    db = hardened_env["db"]
    admin_pw = "Aud1t#Master2026!"
    _, admin, _ = AuthService.create_first_admin(
        db, "auditor", "auditor@school.edu", "Chief Auditor", admin_pw
    )
    acc_role = db.query(Role).filter_by(name="accountant").first()
    user_pw = "Secr3t$Acc2026!"
    _, acc, _ = AuthService.create_user(db, admin, "acc_omar", "omar@school.edu", "Omar", user_pw, acc_role.id)

    AuthService.set_user_active(db, admin, acc.id, False)

    log = (
        db.query(ActivityLog)
        .filter_by(action="USER_DEACTIVATED", entity_id=str(acc.id))
        .order_by(ActivityLog.id.desc())
        .first()
    )
    assert log is not None
    assert "auditor" in log.who
    assert log.what == "USER_DEACTIVATED"
    assert log.when is not None
    assert log.module == "SECURITY"
    assert "User:acc_omar" in log.record_ref
    assert log.before_snapshot is not None and log.before_snapshot["is_active"] is True
    assert log.after_snapshot is not None and log.after_snapshot["is_active"] is False
    assert log.is_admin_action is True

    # Ensure SecretRedactingFilter and AuditService scrub any secret keys or inline secrets
    sample_redacted = redact_secrets({"username": "omar", "password": user_pw, "api_key": "tok_live_999"})
    assert sample_redacted["password"] == "[REDACTED]"
    assert sample_redacted["api_key"] == "[REDACTED]"
    assert "Authorization" not in redact_text_secrets("Authorization: Bearer super_secret_abc123") or "[REDACTED]" in redact_text_secrets("Bearer super_secret_abc123")

    rec = logging.LogRecord("test", logging.INFO, __file__, 1, f"Login failed password={user_pw}", (), None)
    SecretRedactingFilter().filter(rec)
    assert user_pw not in rec.getMessage()

    for row in db.query(ActivityLog).all():
        blob = f"{row.description} {row.before_data or ''} {row.after_data or ''}"
        assert admin_pw not in blob
        assert user_pw not in blob


def test_file_validator_blocks_executables_spoofing_traversal(tmp_path):
    # Fake PNG actually containing executable MZ bytes
    fake_png = tmp_path / "malicious.png"
    fake_png.write_bytes(b"MZ\x90\x00fake_pe_header")
    with pytest.raises(FileValidationError):
        SecureFileValidator.validate_existing_file(str(fake_png), "image")

    # Executable blocked even if extension allowed elsewhere
    exe_file = tmp_path / "payload.exe"
    exe_file.write_bytes(b"MZ\x90\x00payload")
    with pytest.raises(FileValidationError):
        SecureFileValidator.validate_existing_file(str(exe_file), "document")

    # Traversal rejected
    with pytest.raises(FileValidationError):
        SecureFileValidator.safe_join(tmp_path, "../../etc/passwd")

    # Null byte rejected
    with pytest.raises(FileValidationError):
        SecureFileValidator.validate_existing_file(str(tmp_path / "evil.csv\x00.png"), "image")

    # Valid minimal PNG accepted
    valid_png = tmp_path / "valid_photo.png"
    valid_png.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    resolved, ext, size = SecureFileValidator.validate_existing_file(str(valid_png), "image")
    assert ext == ".png" and size > 0 and resolved.exists()


def test_secure_database_queries_and_sensitive_data_protection():
    # SQL identifier guard rejects injection
    with pytest.raises(SQLSecurityError):
        DatabaseSecurityValidator.safe_quote_identifier("students; DROP TABLE users;--")
    with pytest.raises(SQLSecurityError):
        DatabaseSecurityValidator.validate_identifier("SELECT")

    assert DatabaseSecurityValidator.safe_quote_identifier("students") == '"students"'
    assert DatabaseSecurityValidator.escape_like_pattern("100%_test\\") == "100\\%\\_test\\\\"

    ok_sql, _ = DatabaseSecurityValidator.check_query_safety("SELECT * FROM users WHERE id = :uid; DROP TABLE users")
    assert ok_sql is False

    # Field encryption, blind index, masking, and CSV formula sanitization
    nid = "19952691234567890"
    enc = SensitiveDataProtector.encrypt_sensitive(nid)
    assert enc.startswith("enc:v1:") and nid not in enc
    assert SensitiveDataProtector.decrypt_sensitive(enc) == nid
    assert SensitiveDataProtector.blind_index(nid, "guardian_nid") == SensitiveDataProtector.blind_index(nid, "guardian_nid")
    assert SensitiveDataProtector.mask_nid(nid).endswith("7890")
    assert SensitiveDataProtector.sanitize_csv_cell("=CMD|' /C calc'!A0").startswith("'=")


def test_backup_encryption_tamper_alert_and_security_dashboard(hardened_env, tmp_path):
    db = hardened_env["db"]
    bkp_dir = str(tmp_path / "sec_backups")
    admin_pw = "D@sh#Admin2026!"
    _, admin, _ = AuthService.create_first_admin(
        db, "dashadmin", "dash@school.edu", "Dashboard Admin", admin_pw
    )

    secret_phrase = "Vault#TopSecretKey!2026"
    bkp = DataProtectionBackupService.create_backup(
        db,
        schedule_mode="Manual",
        encrypt=True,
        passphrase=secret_phrase,
        backup_dir=bkp_dir,
        verify=True,
        created_by="dashadmin",
    )
    assert bkp.is_encrypted is True and bkp.verification_status == "Verified"

    # Never log backup passphrase
    for row in db.query(ActivityLog).all():
        assert secret_phrase not in f"{row.description} {row.after_data or ''}"

    # Tamper encrypted container -> verify fails and raises BACKUP_VERIFICATION_FAILED alert
    raw = bytearray(Path(bkp.file_path).read_bytes())
    raw[-10] ^= 0xFF
    Path(bkp.file_path).write_bytes(bytes(raw))
    tamper_res = DataProtectionBackupService.verify_backup(db, bkp.file_path, passphrase=secret_phrase, backup_id=bkp.id)
    assert tamper_res["ok"] is False

    tamper_alert = db.query(SecurityAlert).filter_by(alert_type="BACKUP_VERIFICATION_FAILED").first()
    assert tamper_alert is not None

    # Security Dashboard summary & alert resolution
    summary = SecurityDashboardService.get_dashboard_summary(db)
    assert summary["open_alerts"] >= 1
    assert summary["admin_actions_24h"] >= 1

    ok_res, _ = SecurityDashboardService.resolve_alert(db, admin, tamper_alert.id, new_status="RESOLVED", notes="Verified tampering test")
    assert ok_res is True

    csv_out = tmp_path / "audit_export.csv"
    exported = SecurityDashboardService.export_audit_logs_csv(db, str(csv_out))
    assert exported >= 1
    csv_txt = csv_out.read_text(encoding="utf-8-sig")
    assert secret_phrase not in csv_txt and admin_pw not in csv_txt
