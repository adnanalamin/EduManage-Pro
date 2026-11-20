"""
EduManage Pro - Enterprise Authentication, Session, User & RBAC Service
Implements:
- First-run Super Admin creation (zero hardcoded production passwords)
- Constant-time bcrypt authentication with dummy timing equalization, progressive lockout & LoginHistory
- Brute-force & credential-stuffing suspicious activity detection (SecurityAlert)
- Persistent UserSession lifecycle with session_version invalidation & admin session revocation
- Secure password change & expiring single-use SHA-256 reset tokens
- Structured WHO/WHAT/WHEN/MODULE/RECORD/BEFORE/AFTER audit trail (zero plaintext secrets)
- Escaped LIKE queries against wildcard/SQL abuse
"""

from datetime import datetime, timedelta, timezone
import re
import socket
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session, joinedload

from app.config.logging_config import security_logger
from app.config.settings import settings
from app.models.activity import ActivityLog
from app.models.base import utc_now
from app.models.user import (
    LoginHistory,
    PasswordResetToken,
    Permission,
    Role,
    SecurityAlert,
    User,
    UserSession,
)
from app.security.audit import AuditService
from app.security.db_security import DatabaseSecurityValidator
from app.security.hasher import PasswordHasher
from app.security.permissions import (
    build_permission_catalog,
    default_permission_codes_for_role,
)
from app.security.session import session as app_session


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize SQLite naive datetimes or tz-aware datetimes into UTC aware objects."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _get_workstation_name() -> str:
    try:
        return socket.gethostname()[:120]
    except Exception:
        return "localhost"


def _user_snapshot(u: User) -> Dict[str, Any]:
    """Safe, secret-free snapshot of a User record for BEFORE/AFTER audit logging."""
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role.name if getattr(u, "role", None) else str(u.role_id),
        "is_active": bool(u.is_active),
        "must_change_password": bool(u.must_change_password),
        "failed_login_attempts": int(u.failed_login_attempts or 0),
        "locked_until": u.locked_until.isoformat() if u.locked_until else None,
        "session_version": int(u.session_version or 1),
    }


def _role_snapshot(r: Role) -> Dict[str, Any]:
    return {
        "id": r.id,
        "name": r.name,
        "display_name": r.display_name,
        "is_active": bool(r.is_active),
        "is_system_role": bool(r.is_system_role),
        "permission_count": len(r.permissions or []),
        "permission_codes": sorted(p.code for p in (r.permissions or []))[:100],
    }


class AuthService:
    # ------------------------------------------------------------------
    # Bootstrap & First-Run Super Admin Setup
    # ------------------------------------------------------------------
    @staticmethod
    def has_super_admin(db: Session) -> bool:
        """Return True if at least one active, non-deleted Super Admin user exists."""
        return (
            db.query(User.id)
            .join(User.role)
            .filter(
                Role.name == "super_admin",
                Role.is_active == True,
                User.is_active == True,
                User.is_deleted == False,
            )
            .first()
            is not None
        )

    @staticmethod
    def has_any_user(db: Session) -> bool:
        return db.query(User.id).filter(User.is_deleted == False).first() is not None

    @staticmethod
    def sync_permission_catalog(db: Session) -> int:
        """
        Seed or update all hierarchical Module -> Feature -> Action permissions
        and attach baseline defaults to built-in roles that have no permissions yet.
        """
        catalog = build_permission_catalog()
        perm_map: Dict[str, Permission] = {
            p.code: p for p in db.query(Permission).all()
        }
        added = 0

        for item in catalog:
            existing = perm_map.get(item["code"])
            if not existing:
                perm = Permission(
                    code=item["code"],
                    module=item["module"],
                    feature=item["feature"],
                    action=item["action"],
                    name=item["name"],
                    description=item["description"],
                    is_active=True,
                )
                db.add(perm)
                db.flush()
                perm_map[item["code"]] = perm
                added += 1
            else:
                existing.module = item["module"]
                existing.feature = item["feature"]
                existing.action = item["action"]
                existing.name = item["name"]
                existing.description = item["description"]

        all_codes = list(perm_map.keys())
        roles = db.query(Role).options(joinedload(Role.permissions)).all()
        for role in roles:
            if not role.permissions:
                preset_codes = default_permission_codes_for_role(role.name, all_codes)
                if preset_codes:
                    role.permissions = [perm_map[c] for c in preset_codes if c in perm_map]
            elif role.is_system_role:
                preset_codes = default_permission_codes_for_role(role.name, all_codes)
                existing_codes = {p.code for p in role.permissions}
                for prefix in ("hr.", "academics.", "attendance.", "admissions."):
                    for code in [c for c in preset_codes if c.startswith(prefix) and c in perm_map]:
                        if code not in existing_codes:
                            role.permissions.append(perm_map[code])
                            existing_codes.add(code)

        db.commit()
        return added

    @staticmethod
    def create_first_admin(
        db: Session,
        username: str,
        email: str,
        full_name: str,
        password: str,
        phone: Optional[str] = None,
        ip_address: str = "127.0.0.1",
    ) -> Tuple[bool, Optional[User], str]:
        """
        Secure First-Run Administrator creation.
        Blocks if an active Super Admin already exists in production.
        """
        if AuthService.has_super_admin(db):
            return False, None, "An active Super Administrator account already exists."

        clean_user = (username or "").strip()
        clean_email = (email or "").strip().lower()
        clean_name = (full_name or "").strip()

        if len(clean_user) < 3 or not re.match(r"^[A-Za-z0-9_.-]+$", clean_user):
            return (
                False,
                None,
                "Username must be at least 3 characters and contain only letters, numbers, '.', '-', or '_'.",
            )
        if not clean_name:
            return False, None, "Administrator full name is required."
        if "@" not in clean_email or "." not in clean_email.split("@")[-1]:
            return False, None, "Please provide a valid administrator email address."

        valid_pw, pw_msg = PasswordHasher.validate_password_strength(
            password, username=clean_user, email=clean_email, min_length=settings.MIN_PASSWORD_LENGTH
        )
        if not valid_pw:
            return False, None, pw_msg

        dup = (
            db.query(User)
            .filter((User.username == clean_user) | (User.email == clean_email))
            .first()
        )
        if dup:
            return False, None, "Username or email is already registered."

        super_role = db.query(Role).filter_by(name="super_admin").first()
        if not super_role:
            super_role = Role(
                name="super_admin",
                display_name="Super Admin",
                description="Full system access without restrictions",
                is_system_role=True,
                is_active=True,
            )
            db.add(super_role)
            db.flush()

        AuthService.sync_permission_catalog(db)

        admin_user = User(
            username=clean_user,
            email=clean_email,
            password_hash=PasswordHasher.hash_password(password),
            full_name=clean_name,
            phone=(phone or "").strip() or None,
            role_id=super_role.id,
            is_active=True,
            is_default_password=False,
            must_change_password=False,
            password_changed_at=utc_now(),
            created_by="setup_wizard",
        )
        db.add(admin_user)
        db.flush()
        db.refresh(admin_user)

        AuditService.record(
            db,
            action="FIRST_ADMIN_CREATED",
            module="SECURITY",
            description=f"Initial Super Administrator '{admin_user.username}' provisioned via First-Run Setup.",
            who_user=admin_user,
            actor_role="super_admin",
            entity_type="User",
            entity_id=admin_user.id,
            record_label=f"User:{admin_user.username}",
            before=None,
            after=_user_snapshot(admin_user),
            severity="SECURITY",
            ip_address=ip_address,
            is_admin_action=True,
        )
        db.commit()
        db.refresh(admin_user)
        security_logger.info(
            f"First-Run Super Administrator provisioned: username='{admin_user.username}'"
        )
        return True, admin_user, "Super Administrator account created successfully."

    # ------------------------------------------------------------------
    # Authentication, Progressive Lockout, Session DB Persistence & Alerts
    # ------------------------------------------------------------------
    @staticmethod
    def _record_login_history(
        db: Session,
        *,
        user_id: Optional[int],
        username_attempted: str,
        status: str,
        failure_reason: Optional[str] = None,
        ip_address: str = "127.0.0.1",
        workstation: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> LoginHistory:
        entry = LoginHistory(
            user_id=user_id,
            username_attempted=username_attempted[:120],
            status=status,
            failure_reason=failure_reason,
            ip_address=ip_address,
            workstation=workstation or _get_workstation_name(),
            session_id=session_id,
            login_at=utc_now(),
        )
        db.add(entry)
        db.flush()
        return entry

    @staticmethod
    def _check_unknown_spray_alert(
        db: Session,
        identifier: str,
        ip_address: str,
        workstation: Optional[str],
    ) -> None:
        """Detect credential stuffing / user enumeration bursts against unknown accounts."""
        cutoff = utc_now() - timedelta(minutes=15)
        recent_unknown = (
            db.query(LoginHistory.id)
            .filter(
                LoginHistory.status == "FAILED_UNKNOWN",
                LoginHistory.ip_address == ip_address,
                LoginHistory.login_at >= cutoff,
            )
            .count()
        )
        if recent_unknown >= 5:
            AuditService.raise_alert(
                db,
                alert_type="CREDENTIAL_STUFFING",
                severity="CRITICAL",
                module="AUTH",
                username=identifier[:120],
                ip_address=ip_address,
                workstation=workstation,
                description=(
                    f"Detected {recent_unknown} failed login attempts against unknown accounts "
                    f"from IP {ip_address} within 15 minutes (latest: '{identifier}')."
                ),
                evidence={"recent_unknown_failures": recent_unknown, "latest_identifier": identifier},
            )

    @staticmethod
    def _create_user_session_record(
        db: Session,
        user: User,
        session_id: str,
        session_secret: str,
        ip_address: str,
        workstation: Optional[str],
    ) -> UserSession:
        now = utc_now()
        timeout_mins = max(1, int(settings.SESSION_TIMEOUT_MINUTES or 120))
        ws = workstation or _get_workstation_name()

        active_sessions = (
            db.query(UserSession)
            .filter(UserSession.user_id == user.id, UserSession.is_active == True)
            .order_by(UserSession.started_at.asc())
            .all()
        )
        max_conc = max(1, int(getattr(settings, "MAX_CONCURRENT_SESSIONS", 3) or 3))
        if len(active_sessions) >= max_conc:
            # Auto-expire oldest session(s) above limit and emit an anomaly notice
            to_trim = active_sessions[: len(active_sessions) - max_conc + 1]
            for old_s in to_trim:
                old_s.is_active = False
                old_s.revoked_at = now
                old_s.revoked_by = "system_policy"
                old_s.revoke_reason = "Exceeded maximum concurrent session limit"
            AuditService.raise_alert(
                db,
                alert_type="CONCURRENT_SESSION_LIMIT",
                severity="MEDIUM",
                module="AUTH",
                user_id=user.id,
                username=user.username,
                ip_address=ip_address,
                workstation=ws,
                description=(
                    f"User '{user.username}' reached max concurrent sessions ({max_conc}); "
                    "oldest active session was terminated automatically."
                ),
            )

        sess_row = UserSession(
            session_id=session_id,
            session_token_hash=PasswordHasher.hash_token(session_secret),
            user_id=user.id,
            username=user.username,
            role_name=(user.role.name if user.role else None),
            session_version=int(user.session_version or 1),
            ip_address=ip_address,
            workstation=ws,
            started_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(minutes=timeout_mins),
            is_active=True,
        )
        db.add(sess_row)
        db.flush()
        return sess_row

    @staticmethod
    def authenticate(
        db: Session,
        username_or_email: str,
        password: str,
        ip_address: str = "127.0.0.1",
        workstation: Optional[str] = None,
    ) -> Tuple[bool, Optional[User], str]:
        """
        Authenticate user with username or email, enforcing constant-time timing,
        progressive lockout protection, role/account active checks, bcrypt verification,
        persistent UserSession issuance, and suspicious activity alerts.
        """
        identifier = (username_or_email or "").strip()
        if not identifier or not password:
            return False, None, "Username and password are required."

        user = (
            db.query(User)
            .options(joinedload(User.role).joinedload(Role.permissions))
            .filter(
                (User.username == identifier) | (User.email == identifier.lower())
            )
            .first()
        )

        if not user or user.is_deleted:
            # Equalize timing so attackers cannot enumerate valid usernames via response latency
            PasswordHasher.dummy_verify(password)
            AuthService._record_login_history(
                db,
                user_id=user.id if user else None,
                username_attempted=identifier,
                status="FAILED_UNKNOWN",
                failure_reason="Unknown or deleted user account",
                ip_address=ip_address,
                workstation=workstation,
            )
            AuditService.record(
                db,
                action="LOGIN_FAILED",
                module="AUTH",
                description=f"Failed login attempt for unknown/deleted account '{identifier}'.",
                username=identifier[:60],
                entity_type="User",
                record_label=f"Attempt:{identifier[:60]}",
                severity="WARNING",
                ip_address=ip_address,
                workstation=workstation,
                is_admin_action=False,
            )
            AuthService._check_unknown_spray_alert(db, identifier, ip_address, workstation)
            db.commit()
            security_logger.warning(
                f"Failed login attempt for unknown user '{identifier}' from IP {ip_address}"
            )
            return False, None, "Invalid username or password"

        if not user.is_active:
            AuthService._record_login_history(
                db,
                user_id=user.id,
                username_attempted=user.username,
                status="FAILED_INACTIVE",
                failure_reason="User account deactivated",
                ip_address=ip_address,
                workstation=workstation,
            )
            db.commit()
            security_logger.warning(
                f"Login blocked for deactivated user '{user.username}' from IP {ip_address}"
            )
            return False, None, "Account is deactivated. Contact your Super Administrator."

        if not user.role or not user.role.is_active:
            AuthService._record_login_history(
                db,
                user_id=user.id,
                username_attempted=user.username,
                status="FAILED_INACTIVE",
                failure_reason="Assigned role is inactive",
                ip_address=ip_address,
                workstation=workstation,
            )
            db.commit()
            return False, None, "Your assigned role is currently disabled. Contact Super Administrator."

        now_utc = utc_now()
        locked_until_utc = _ensure_utc(user.locked_until)
        if locked_until_utc and locked_until_utc > now_utc:
            remaining = max(1, int((locked_until_utc - now_utc).total_seconds()))
            AuthService._record_login_history(
                db,
                user_id=user.id,
                username_attempted=user.username,
                status="FAILED_LOCKED",
                failure_reason=f"Account locked ({remaining}s remaining)",
                ip_address=ip_address,
                workstation=workstation,
            )
            db.commit()
            security_logger.warning(
                f"Locked account login attempt for '{user.username}', {remaining}s remaining"
            )
            return (
                False,
                None,
                f"Account locked due to multiple failed attempts. Try again in {remaining} seconds.",
            )

        if locked_until_utc and locked_until_utc <= now_utc:
            user.locked_until = None
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.failed_login_attempts = 0

        if not PasswordHasher.verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                lock_secs = int(settings.LOCKOUT_DURATION_SECONDS)
                user.locked_until = now_utc + timedelta(seconds=lock_secs)
                AuthService._record_login_history(
                    db,
                    user_id=user.id,
                    username_attempted=user.username,
                    status="FAILED_LOCKED",
                    failure_reason=f"Locked after {user.failed_login_attempts} failed attempts",
                    ip_address=ip_address,
                    workstation=workstation,
                )
                AuditService.record(
                    db,
                    action="ACCOUNT_LOCKED",
                    module="AUTH",
                    description=(
                        f"Account '{user.username}' locked for {lock_secs}s "
                        f"after {user.failed_login_attempts} consecutive failed logins."
                    ),
                    who_user=user,
                    entity_type="User",
                    entity_id=user.id,
                    record_label=f"User:{user.username}",
                    before={"failed_login_attempts": user.failed_login_attempts - 1, "locked_until": None},
                    after={"failed_login_attempts": user.failed_login_attempts, "locked_until": user.locked_until.isoformat()},
                    severity="SECURITY",
                    ip_address=ip_address,
                    workstation=workstation,
                    is_admin_action=False,
                )
                AuditService.raise_alert(
                    db,
                    alert_type="BRUTE_FORCE_LOCKOUT",
                    severity="HIGH",
                    module="AUTH",
                    user_id=user.id,
                    username=user.username,
                    ip_address=ip_address,
                    workstation=workstation,
                    description=(
                        f"Brute-force protection triggered: account '{user.username}' locked for "
                        f"{lock_secs}s after {user.failed_login_attempts} invalid password attempts."
                    ),
                    evidence={"attempts": user.failed_login_attempts, "lockout_seconds": lock_secs},
                )
                db.commit()
                security_logger.critical(
                    f"User '{user.username}' locked out for {lock_secs}s "
                    f"after {user.failed_login_attempts} failed attempts"
                )
                return (
                    False,
                    None,
                    f"Account locked for {lock_secs} seconds due to too many failed attempts.",
                )

            remaining_attempts = settings.MAX_LOGIN_ATTEMPTS - user.failed_login_attempts
            AuthService._record_login_history(
                db,
                user_id=user.id,
                username_attempted=user.username,
                status="FAILED_PASSWORD",
                failure_reason=f"Invalid password ({user.failed_login_attempts}/{settings.MAX_LOGIN_ATTEMPTS})",
                ip_address=ip_address,
                workstation=workstation,
            )
            db.commit()
            security_logger.warning(
                f"Invalid password for '{user.username}'. Attempt {user.failed_login_attempts}/{settings.MAX_LOGIN_ATTEMPTS}"
            )
            return False, None, f"Invalid username or password. {remaining_attempts} attempts remaining."

        # Upgrade bcrypt cost factor transparently if configured rounds increased
        if PasswordHasher.needs_rehash(user.password_hash):
            user.password_hash = PasswordHasher.hash_password(password)

        # Anomaly check: new workstation / IP login for elevated roles
        ws_name = workstation or _get_workstation_name()
        if (
            user.last_login_ip
            and user.last_login_ip != ip_address
            and user.role.name in ("super_admin", "administrator")
        ):
            AuditService.raise_alert(
                db,
                alert_type="ADMIN_NEW_IP_LOGIN",
                severity="MEDIUM",
                module="AUTH",
                user_id=user.id,
                username=user.username,
                ip_address=ip_address,
                workstation=ws_name,
                description=(
                    f"Privileged account '{user.username}' signed in from IP {ip_address} "
                    f"(previous IP: {user.last_login_ip})."
                ),
            )

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now_utc
        user.last_login_ip = ip_address

        sess_secret = PasswordHasher.generate_secure_token(32)
        sess_uuid = str(uuid.uuid4())
        session_id = app_session.set_current_user(
            user,
            session_id=sess_uuid,
            session_secret=sess_secret,
        )
        AuthService._create_user_session_record(
            db, user, session_id=session_id, session_secret=sess_secret, ip_address=ip_address, workstation=ws_name
        )
        hist = AuthService._record_login_history(
            db,
            user_id=user.id,
            username_attempted=user.username,
            status="SUCCESS",
            failure_reason=None,
            ip_address=ip_address,
            workstation=ws_name,
            session_id=session_id,
        )
        AuditService.record(
            db,
            action="LOGIN_SUCCESS",
            module="AUTH",
            description=f"User '{user.username}' authenticated as {user.role.display_name}.",
            who_user=user,
            entity_type="UserSession",
            entity_id=session_id,
            record_label=f"User:{user.username}",
            after={"session_id": session_id, "ip_address": ip_address, "workstation": ws_name},
            severity="INFO",
            ip_address=ip_address,
            workstation=ws_name,
            session_id=session_id,
            is_admin_action=False,
        )
        db.commit()
        app_session._login_history_id = hist.id

        security_logger.info(f"User '{user.username}' authenticated successfully from {ip_address}")
        return True, user, "Login successful"

    @staticmethod
    def logout(
        db: Session,
        ip_address: str = "127.0.0.1",
        reason: str = "LOGOUT",
    ) -> None:
        """Clear active session, deactivate DB UserSession, and stamp LoginHistory + ActivityLog."""
        user = app_session.current_user
        hist_id = app_session.login_history_id
        session_id = app_session.session_id

        if user:
            now_utc = utc_now()
            hist = None
            if hist_id:
                hist = db.query(LoginHistory).filter(LoginHistory.id == hist_id).first()
            elif session_id:
                hist = db.query(LoginHistory).filter(LoginHistory.session_id == session_id).first()

            if hist:
                hist.logout_at = now_utc
                if reason == "SESSION_TIMEOUT":
                    hist.failure_reason = "Closed due to idle session timeout"

            if session_id:
                db_sess = db.query(UserSession).filter(UserSession.session_id == session_id).first()
                if db_sess and db_sess.is_active:
                    db_sess.is_active = False
                    db_sess.revoked_at = now_utc
                    db_sess.revoked_by = user.username
                    db_sess.revoke_reason = "Idle timeout" if reason == "SESSION_TIMEOUT" else "User logout"

            action_code = "SESSION_TIMEOUT" if reason == "SESSION_TIMEOUT" else "LOGOUT"
            desc = (
                f"Session timed out automatically due to inactivity for user '{user.username}'."
                if reason == "SESSION_TIMEOUT"
                else f"User '{user.username}' signed out."
            )
            AuditService.record(
                db,
                action=action_code,
                module="AUTH",
                description=desc,
                who_user=user,
                entity_type="UserSession",
                entity_id=session_id or str(user.id),
                record_label=f"User:{user.username}",
                before={"is_active": True},
                after={"is_active": False, "reason": reason},
                severity="SECURITY" if reason == "SESSION_TIMEOUT" else "INFO",
                ip_address=ip_address,
                session_id=session_id,
                is_admin_action=False,
            )
            db.commit()
            security_logger.info(f"User '{user.username}' ended session ({action_code})")

        app_session.clear()

    @staticmethod
    def _invalidate_user_sessions(db: Session, user_id: int, actor_username: str, reason: str) -> int:
        now_utc = utc_now()
        rows = (
            db.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.is_active == True)
            .all()
        )
        for s in rows:
            s.is_active = False
            s.revoked_at = now_utc
            s.revoked_by = actor_username
            s.revoke_reason = reason
        return len(rows)

    @staticmethod
    def revoke_session(
        db: Session,
        actor_user: User,
        target_session_id: str,
        reason: str = "Revoked by administrator",
        ip_address: str = "127.0.0.1",
    ) -> Tuple[bool, str]:
        if not AuthService._can_manage_users(actor_user):
            return False, "Permission denied: Security / User management privilege required."

        sess_row = db.query(UserSession).filter(UserSession.session_id == target_session_id).first()
        if not sess_row:
            return False, "Session not found."
        if not sess_row.is_active:
            return False, "Session is already terminated."

        before_state = {"session_id": sess_row.session_id, "username": sess_row.username, "is_active": True}
        now_utc = utc_now()
        sess_row.is_active = False
        sess_row.revoked_at = now_utc
        sess_row.revoked_by = actor_user.username
        sess_row.revoke_reason = reason[:255]

        hist = db.query(LoginHistory).filter(LoginHistory.session_id == sess_row.session_id).first()
        if hist and not hist.logout_at:
            hist.logout_at = now_utc
            hist.failure_reason = f"Session revoked by {actor_user.username}: {reason}"

        if app_session.session_id == sess_row.session_id:
            app_session.clear()

        AuditService.record(
            db,
            action="SESSION_REVOKED",
            module="SECURITY",
            description=f"Administrator '{actor_user.username}' revoked active session for '{sess_row.username}' ({reason}).",
            who_user=actor_user,
            entity_type="UserSession",
            entity_id=sess_row.session_id,
            record_label=f"Session:{sess_row.username}",
            before=before_state,
            after={"session_id": sess_row.session_id, "username": sess_row.username, "is_active": False, "revoke_reason": reason},
            severity="SECURITY",
            ip_address=ip_address,
            is_admin_action=True,
        )
        db.commit()
        security_logger.warning(
            f"Admin '{actor_user.username}' revoked session {sess_row.session_id} for '{sess_row.username}'"
        )
        return True, f"Session for '{sess_row.username}' terminated."

    # ------------------------------------------------------------------
    # Password Change & Reset Workflows (Zero Plaintext Storage/Logging)
    # ------------------------------------------------------------------
    @staticmethod
    def change_password(
        db: Session,
        user_id: int,
        old_password: str,
        new_password: str,
        ip_address: str = "127.0.0.1",
    ) -> Tuple[bool, str]:
        """Validate current password, enforce complexity, and update bcrypt hash."""
        user = (
            db.query(User)
            .options(joinedload(User.role))
            .filter(User.id == user_id, User.is_deleted == False)
            .first()
        )
        if not user:
            return False, "User not found."

        if not PasswordHasher.verify_password(old_password, user.password_hash):
            security_logger.warning(f"Password change denied (wrong current password) for '{user.username}'")
            return False, "Current password is incorrect."

        if old_password == new_password:
            return False, "New password must be different from your current password."

        valid_pw, msg = PasswordHasher.validate_password_strength(
            new_password, username=user.username, email=user.email, min_length=settings.MIN_PASSWORD_LENGTH
        )
        if not valid_pw:
            return False, msg

        before_snap = {"session_version": user.session_version, "must_change_password": user.must_change_password}
        user.password_hash = PasswordHasher.hash_password(new_password)
        user.is_default_password = False
        user.must_change_password = False
        user.password_changed_at = utc_now()
        user.session_version = (user.session_version or 1) + 1
        revoked_cnt = AuthService._invalidate_user_sessions(db, user.id, user.username, "Password changed")

        AuditService.record(
            db,
            action="PASSWORD_CHANGE",
            module="AUTH",
            description=f"User '{user.username}' changed account password ({revoked_cnt} active sessions invalidated).",
            who_user=user,
            entity_type="User",
            entity_id=user.id,
            record_label=f"User:{user.username}",
            before=before_snap,
            after={"session_version": user.session_version, "must_change_password": False, "password_updated": True},
            severity="SECURITY",
            ip_address=ip_address,
            is_admin_action=False,
        )
        db.commit()
        security_logger.info(f"Password changed successfully for user '{user.username}'")
        return True, "Password updated successfully."

    @staticmethod
    def request_password_reset(
        db: Session,
        username_or_email: str,
        actor_username: str = "self",
        ip_address: str = "127.0.0.1",
        expires_minutes: int = 30,
    ) -> Tuple[bool, Optional[str], str]:
        """
        Issue a cryptographically secure, time-limited, single-use reset token.
        Only the SHA-256 digest is persisted in DB; raw token is never logged.
        """
        identifier = (username_or_email or "").strip()
        user = (
            db.query(User)
            .filter(
                User.is_deleted == False,
                (User.username == identifier) | (User.email == identifier.lower()),
            )
            .first()
        )
        if not user:
            return False, None, "No matching active account found."
        if not user.is_active:
            return False, None, "Account is deactivated and cannot initiate a password reset."

        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.is_revoked == False,
        ).update({"is_revoked": True}, synchronize_session=False)

        raw_token = PasswordHasher.generate_secure_token(24)
        token_record = PasswordResetToken(
            user_id=user.id,
            token_hash=PasswordHasher.hash_token(raw_token),
            issued_by=actor_username or "self",
            expires_at=utc_now() + timedelta(minutes=max(5, expires_minutes)),
        )
        db.add(token_record)
        AuditService.record(
            db,
            action="PASSWORD_RESET_REQUEST",
            module="AUTH",
            description=f"Generated single-use password reset token for '{user.username}' (expires in {expires_minutes}m).",
            username=actor_username or user.username,
            entity_type="User",
            entity_id=user.id,
            record_label=f"User:{user.username}",
            after={"token_issued": True, "expires_minutes": expires_minutes},
            severity="SECURITY",
            ip_address=ip_address,
            is_admin_action=(actor_username != "self"),
        )
        db.commit()
        security_logger.info(f"Password reset token issued for user '{user.username}' (token hash stored)")
        return True, raw_token, f"Single-use reset token issued for '{user.username}'."

    @staticmethod
    def complete_password_reset(
        db: Session,
        raw_token: str,
        new_password: str,
        ip_address: str = "127.0.0.1",
    ) -> Tuple[bool, str]:
        """Validate reset token hash, check expiry & single-use, and set new password."""
        clean_token = (raw_token or "").strip()
        if not clean_token:
            return False, "Reset token is required."

        digest = PasswordHasher.hash_token(clean_token)
        token_rec = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.token_hash == digest)
            .first()
        )
        if not token_rec or token_rec.is_revoked or token_rec.used_at is not None:
            return False, "Invalid or already used password reset token."

        now_utc = utc_now()
        exp_utc = _ensure_utc(token_rec.expires_at)
        if exp_utc is None or exp_utc <= now_utc:
            token_rec.is_revoked = True
            db.commit()
            return False, "Password reset token has expired."

        user = (
            db.query(User)
            .options(joinedload(User.role))
            .filter(User.id == token_rec.user_id, User.is_deleted == False)
            .first()
        )
        if not user or not user.is_active:
            return False, "Target account is unavailable or deactivated."

        valid_pw, pw_msg = PasswordHasher.validate_password_strength(
            new_password, username=user.username, email=user.email, min_length=settings.MIN_PASSWORD_LENGTH
        )
        if not valid_pw:
            return False, pw_msg

        before_snap = {"session_version": user.session_version, "failed_login_attempts": user.failed_login_attempts}
        user.password_hash = PasswordHasher.hash_password(new_password)
        user.is_default_password = False
        user.must_change_password = False
        user.password_changed_at = now_utc
        user.failed_login_attempts = 0
        user.locked_until = None
        user.session_version = (user.session_version or 1) + 1
        token_rec.used_at = now_utc
        AuthService._invalidate_user_sessions(db, user.id, user.username, "Password reset completed")

        AuditService.record(
            db,
            action="PASSWORD_RESET_COMPLETE",
            module="AUTH",
            description=f"Completed token-verified password reset for '{user.username}'.",
            who_user=user,
            entity_type="User",
            entity_id=user.id,
            record_label=f"User:{user.username}",
            before=before_snap,
            after={"session_version": user.session_version, "failed_login_attempts": 0, "password_updated": True},
            severity="SECURITY",
            ip_address=ip_address,
            is_admin_action=False,
        )
        db.commit()
        security_logger.info(f"Password reset completed for user '{user.username}'")
        return True, "Password has been reset successfully. You may now sign in."

    @staticmethod
    def admin_reset_password(
        db: Session,
        actor_user: User,
        target_user_id: int,
        new_password: Optional[str] = None,
        require_change: bool = True,
        ip_address: str = "127.0.0.1",
    ) -> Tuple[bool, Optional[str], str]:
        """
        Allow Super Admin (or user with security.users.MANAGE) to reset another user's password.
        Generates a CSPRNG temporary password when `new_password` is omitted.
        Never stores or logs the plaintext password.
        """
        if not AuthService._can_manage_users(actor_user):
            return False, None, "Permission denied: Super Admin or User Management access required."

        target = (
            db.query(User)
            .options(joinedload(User.role))
            .filter(User.id == target_user_id, User.is_deleted == False)
            .first()
        )
        if not target:
            return False, None, "Target user not found."

        temp_pw = new_password if new_password else PasswordHasher.generate_temporary_password(14)
        valid_pw, pw_msg = PasswordHasher.validate_password_strength(
            temp_pw, username=target.username, email=target.email, min_length=settings.MIN_PASSWORD_LENGTH
        )
        if not valid_pw:
            return False, None, pw_msg

        before_snap = _user_snapshot(target)
        target.password_hash = PasswordHasher.hash_password(temp_pw)
        target.is_default_password = False
        target.must_change_password = require_change
        target.password_changed_at = utc_now()
        target.failed_login_attempts = 0
        target.locked_until = None
        target.session_version = (target.session_version or 1) + 1
        AuthService._invalidate_user_sessions(db, target.id, actor_user.username, "Admin password reset")

        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == target.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.is_revoked == False,
        ).update({"is_revoked": True}, synchronize_session=False)

        AuditService.record(
            db,
            action="ADMIN_PASSWORD_RESET",
            module="SECURITY",
            description=f"Administrator reset password for user '{target.username}' (must_change={require_change}).",
            who_user=actor_user,
            entity_type="User",
            entity_id=target.id,
            record_label=f"User:{target.username}",
            before=before_snap,
            after=_user_snapshot(target),
            severity="SECURITY",
            ip_address=ip_address,
            is_admin_action=True,
        )
        db.commit()
        security_logger.info(
            f"Admin '{actor_user.username}' reset password for user '{target.username}'"
        )
        return True, temp_pw, f"Password reset successfully for '{target.username}'."

    # ------------------------------------------------------------------
    # User & Account Lifecycle Management (Super Admin)
    # ------------------------------------------------------------------
    @staticmethod
    def _is_super_admin(actor_user: Optional[User]) -> bool:
        return bool(
            actor_user
            and actor_user.is_active
            and not actor_user.is_deleted
            and actor_user.role
            and actor_user.role.name == "super_admin"
            and actor_user.role.is_active
        )

    @staticmethod
    def _can_manage_users(actor_user: Optional[User]) -> bool:
        if AuthService._is_super_admin(actor_user):
            return True
        if not actor_user:
            return False
        return actor_user.has_permission("security.users.MANAGE") or actor_user.has_permission("security.users.CREATE")

    @staticmethod
    def _can_manage_roles(actor_user: Optional[User]) -> bool:
        if AuthService._is_super_admin(actor_user):
            return True
        if not actor_user:
            return False
        return actor_user.has_permission("security.roles.MANAGE")

    @staticmethod
    def create_user(
        db: Session,
        actor_user: User,
        username: str,
        email: str,
        full_name: str,
        password: str,
        role_id: int,
        phone: Optional[str] = None,
        must_change_password: bool = True,
        ip_address: str = "127.0.0.1",
    ) -> Tuple[bool, Optional[User], str]:
        if not AuthService._can_manage_users(actor_user):
            if actor_user:
                AuditService.raise_alert(
                    db,
                    alert_type="UNAUTHORIZED_USER_CREATE",
                    severity="HIGH",
                    module="SECURITY",
                    user_id=actor_user.id,
                    username=actor_user.username,
                    ip_address=ip_address,
                    description=f"Unauthorized attempt by '{actor_user.username}' to create user '{username}'.",
                )
                db.commit()
            return False, None, "Permission denied: User management privilege required."

        clean_user = (username or "").strip()
        clean_email = (email or "").strip().lower()
        clean_name = (full_name or "").strip()

        if len(clean_user) < 3 or not re.match(r"^[A-Za-z0-9_.-]+$", clean_user):
            return False, None, "Username must be >= 3 characters (letters, numbers, '.', '-', '_')."
        if not clean_name:
            return False, None, "Full name is required."
        if "@" not in clean_email or "." not in clean_email.split("@")[-1]:
            return False, None, "A valid email address is required."

        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            return False, None, "Selected role does not exist."
        if role.name == "super_admin" and not AuthService._is_super_admin(actor_user):
            AuditService.raise_alert(
                db,
                alert_type="PRIVILEGE_ESCALATION_ATTEMPT",
                severity="CRITICAL",
                module="SECURITY",
                user_id=actor_user.id,
                username=actor_user.username,
                ip_address=ip_address,
                description=f"Non-SuperAdmin '{actor_user.username}' attempted to create Super Admin '{clean_user}'.",
            )
            db.commit()
            return False, None, "Only an existing Super Admin may assign the Super Admin role."

        valid_pw, pw_msg = PasswordHasher.validate_password_strength(
            password, username=clean_user, email=clean_email, min_length=settings.MIN_PASSWORD_LENGTH
        )
        if not valid_pw:
            return False, None, pw_msg

        dup = (
            db.query(User)
            .filter((User.username == clean_user) | (User.email == clean_email))
            .first()
        )
        if dup:
            return False, None, "Username or email is already registered."

        new_user = User(
            username=clean_user,
            email=clean_email,
            password_hash=PasswordHasher.hash_password(password),
            full_name=clean_name,
            phone=(phone or "").strip() or None,
            role_id=role.id,
            is_active=True,
            is_default_password=False,
            must_change_password=must_change_password,
            password_changed_at=utc_now(),
            created_by=actor_user.username if actor_user else "system",
        )
        db.add(new_user)
        db.flush()
        db.refresh(new_user)

        AuditService.record(
            db,
            action="USER_CREATED",
            module="SECURITY",
            description=f"Created user account '{new_user.username}' with role '{role.display_name}'.",
            who_user=actor_user,
            entity_type="User",
            entity_id=new_user.id,
            record_label=f"User:{new_user.username}",
            before=None,
            after=_user_snapshot(new_user),
            severity="SECURITY",
            ip_address=ip_address,
            is_admin_action=True,
        )
        db.commit()
        db.refresh(new_user)
        security_logger.info(f"User '{new_user.username}' created by '{actor_user.username}'")
        return True, new_user, f"User '{new_user.username}' created successfully."

    @staticmethod
    def set_user_active(
        db: Session,
        actor_user: User,
        target_user_id: int,
        is_active: bool,
        ip_address: str = "127.0.0.1",
    ) -> Tuple[bool, str]:
        if not AuthService._can_manage_users(actor_user):
            return False, "Permission denied: User management privilege required."

        target = (
            db.query(User)
            .options(joinedload(User.role))
            .filter(User.id == target_user_id, User.is_deleted == False)
            .first()
        )
        if not target:
            return False, "User not found."

        if not is_active and actor_user and target.id == actor_user.id:
            return False, "You cannot deactivate your own active account."

        if not is_active and target.role and target.role.name == "super_admin":
            other_active_admins = (
                db.query(User.id)
                .join(User.role)
                .filter(
                    Role.name == "super_admin",
                    User.is_active == True,
                    User.is_deleted == False,
                    User.id != target.id,
                )
                .count()
            )
            if other_active_admins == 0:
                return False, "Cannot deactivate the last remaining active Super Administrator."

        before_snap = _user_snapshot(target)
        target.is_active = is_active
        if not is_active:
            target.session_version = (target.session_version or 1) + 1
            AuthService._invalidate_user_sessions(db, target.id, actor_user.username, "Account deactivated")
        else:
            target.failed_login_attempts = 0
            target.locked_until = None

        action = "USER_ACTIVATED" if is_active else "USER_DEACTIVATED"
        AuditService.record(
            db,
            action=action,
            module="SECURITY",
            description=f"Account '{target.username}' was {'activated' if is_active else 'deactivated'}.",
            who_user=actor_user,
            entity_type="User",
            entity_id=target.id,
            record_label=f"User:{target.username}",
            before=before_snap,
            after=_user_snapshot(target),
            severity="SECURITY",
            ip_address=ip_address,
            is_admin_action=True,
        )
        db.commit()
        security_logger.info(f"User '{target.username}' {action} by '{actor_user.username}'")
        return True, f"User '{target.username}' {'activated' if is_active else 'deactivated'}."

    @staticmethod
    def unlock_user(
        db: Session,
        actor_user: User,
        target_user_id: int,
        ip_address: str = "127.0.0.1",
    ) -> Tuple[bool, str]:
        if not AuthService._can_manage_users(actor_user):
            return False, "Permission denied."
        target = (
            db.query(User)
            .options(joinedload(User.role))
            .filter(User.id == target_user_id, User.is_deleted == False)
            .first()
        )
        if not target:
            return False, "User not found."

        before_snap = _user_snapshot(target)
        target.failed_login_attempts = 0
        target.locked_until = None
        AuditService.record(
            db,
            action="USER_UNLOCKED",
            module="SECURITY",
            description=f"Administrator unlocked account '{target.username}'.",
            who_user=actor_user,
            entity_type="User",
            entity_id=target.id,
            record_label=f"User:{target.username}",
            before=before_snap,
            after=_user_snapshot(target),
            severity="SECURITY",
            ip_address=ip_address,
            is_admin_action=True,
        )
        db.commit()
        return True, f"Account '{target.username}' unlocked."

    # ------------------------------------------------------------------
    # Role & Hierarchical Permission Matrix Management (Super Admin)
    # ------------------------------------------------------------------
    @staticmethod
    def create_role(
        db: Session,
        actor_user: User,
        name: str,
        display_name: str,
        description: str = "",
        permission_ids: Optional[List[int]] = None,
        ip_address: str = "127.0.0.1",
    ) -> Tuple[bool, Optional[Role], str]:
        if not AuthService._can_manage_roles(actor_user):
            return False, None, "Permission denied: Super Admin privilege required."

        slug = re.sub(r"[^a-z0-9_]+", "_", (name or "").strip().lower()).strip("_")
        disp = (display_name or "").strip()
        if len(slug) < 2 or not disp:
            return False, None, "Role code and display name are required."
        if db.query(Role).filter(Role.name == slug).first():
            return False, None, f"Role '{slug}' already exists."

        perms: List[Permission] = []
        if permission_ids:
            perms = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()

        role = Role(
            name=slug,
            display_name=disp,
            description=(description or "").strip() or None,
            is_system_role=False,
            is_active=True,
            permissions=perms,
        )
        db.add(role)
        db.flush()

        AuditService.record(
            db,
            action="ROLE_CREATED",
            module="SECURITY",
            description=f"Created role '{role.display_name}' ({role.name}) with {len(perms)} permissions.",
            who_user=actor_user,
            entity_type="Role",
            entity_id=role.id,
            record_label=f"Role:{role.name}",
            before=None,
            after=_role_snapshot(role),
            severity="SECURITY",
            ip_address=ip_address,
            is_admin_action=True,
        )
        db.commit()
        db.refresh(role)
        return True, role, f"Role '{role.display_name}' created successfully."

    @staticmethod
    def clone_role(
        db: Session,
        actor_user: User,
        source_role_id: int,
        new_name: str,
        new_display_name: str,
        description: Optional[str] = None,
        ip_address: str = "127.0.0.1",
    ) -> Tuple[bool, Optional[Role], str]:
        if not AuthService._can_manage_roles(actor_user):
            return False, None, "Permission denied: Super Admin privilege required."

        source = (
            db.query(Role)
            .options(joinedload(Role.permissions))
            .filter(Role.id == source_role_id)
            .first()
        )
        if not source:
            return False, None, "Source role not found."

        slug = re.sub(r"[^a-z0-9_]+", "_", (new_name or "").strip().lower()).strip("_")
        disp = (new_display_name or "").strip()
        if len(slug) < 2 or not disp:
            return False, None, "New role code and display name are required."
        if db.query(Role).filter(Role.name == slug).first():
            return False, None, f"Role '{slug}' already exists."

        cloned = Role(
            name=slug,
            display_name=disp,
            description=description if description is not None else f"Cloned from {source.display_name}",
            is_system_role=False,
            is_active=True,
            permissions=list(source.permissions),
        )
        db.add(cloned)
        db.flush()

        AuditService.record(
            db,
            action="ROLE_CLONED",
            module="SECURITY",
            description=(
                f"Cloned role '{source.display_name}' -> '{cloned.display_name}' "
                f"({len(cloned.permissions)} permissions copied)."
            ),
            who_user=actor_user,
            entity_type="Role",
            entity_id=cloned.id,
            record_label=f"Role:{cloned.name}",
            before={"cloned_from": source.name},
            after=_role_snapshot(cloned),
            severity="SECURITY",
            ip_address=ip_address,
            is_admin_action=True,
        )
        db.commit()
        db.refresh(cloned)
        return True, cloned, f"Role '{cloned.display_name}' cloned from '{source.display_name}'."

    @staticmethod
    def assign_role_permissions(
        db: Session,
        actor_user: User,
        role_id: int,
        permission_ids: List[int],
        ip_address: str = "127.0.0.1",
    ) -> Tuple[bool, str]:
        if not AuthService._can_manage_roles(actor_user):
            return False, "Permission denied: Super Admin privilege required."

        role = db.query(Role).options(joinedload(Role.permissions)).filter(Role.id == role_id).first()
        if not role:
            return False, "Role not found."

        before_snap = _role_snapshot(role)
        perms = (
            db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
            if permission_ids
            else []
        )
        role.permissions = perms

        AuditService.record(
            db,
            action="ROLE_PERMISSIONS_UPDATED",
            module="SECURITY",
            description=f"Updated permissions on role '{role.display_name}' ({len(perms)} permissions assigned).",
            who_user=actor_user,
            entity_type="Role",
            entity_id=role.id,
            record_label=f"Role:{role.name}",
            before=before_snap,
            after=_role_snapshot(role),
            severity="SECURITY",
            ip_address=ip_address,
            is_admin_action=True,
        )
        db.commit()
        return True, f"Updated {len(perms)} permissions for '{role.display_name}'."

    @staticmethod
    def set_permission_enabled(
        db: Session,
        actor_user: User,
        permission_id: int,
        is_active: bool,
        ip_address: str = "127.0.0.1",
    ) -> Tuple[bool, str]:
        """Globally enable or disable a permission across all non-super-admin roles."""
        if not AuthService._is_super_admin(actor_user):
            return False, "Permission denied: Only Super Admin can globally enable/disable permissions."

        perm = db.query(Permission).filter(Permission.id == permission_id).first()
        if not perm:
            return False, "Permission not found."

        before_snap = {"code": perm.code, "is_active": bool(perm.is_active)}
        perm.is_active = is_active
        AuditService.record(
            db,
            action="PERMISSION_TOGGLED",
            module="SECURITY",
            description=f"Permission '{perm.code}' globally {'enabled' if is_active else 'disabled'}.",
            who_user=actor_user,
            entity_type="Permission",
            entity_id=perm.id,
            record_label=f"Permission:{perm.code}",
            before=before_snap,
            after={"code": perm.code, "is_active": bool(is_active)},
            severity="SECURITY",
            ip_address=ip_address,
            is_admin_action=True,
        )
        db.commit()
        return True, f"Permission '{perm.code}' {'enabled' if is_active else 'disabled'}."

    # ------------------------------------------------------------------
    # Safe Parameterized Audit & Login History Queries
    # ------------------------------------------------------------------
    @staticmethod
    def get_login_history(
        db: Session,
        username: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200,
    ) -> List[LoginHistory]:
        q = db.query(LoginHistory)
        if username and username.strip():
            escaped = DatabaseSecurityValidator.escape_like_pattern(username.strip())
            q = q.filter(LoginHistory.username_attempted.ilike(f"%{escaped}%", escape="\\"))
        if status and status != "ALL":
            q = q.filter(LoginHistory.status == status)
        return q.order_by(LoginHistory.login_at.desc(), LoginHistory.id.desc()).limit(limit).all()

    @staticmethod
    def get_activity_logs(
        db: Session,
        module: Optional[str] = None,
        severity: Optional[str] = None,
        username: Optional[str] = None,
        limit: int = 200,
    ) -> List[ActivityLog]:
        q = db.query(ActivityLog)
        if module and module != "ALL":
            q = q.filter(ActivityLog.module == module)
        if severity and severity != "ALL":
            q = q.filter(ActivityLog.severity == severity)
        if username and username.strip():
            escaped = DatabaseSecurityValidator.escape_like_pattern(username.strip())
            q = q.filter(ActivityLog.username.ilike(f"%{escaped}%", escape="\\"))
        return q.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(limit).all()
