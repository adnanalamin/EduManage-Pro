"""
EduManage Pro - Enterprise Authentication, Session, User & RBAC Service
Implements:
- First-run Super Admin creation (zero hardcoded production passwords)
- Constant-time bcrypt authentication with lockout protection & LoginHistory recording
- Secure password change & expiring single-use SHA-256 reset tokens
- Account activation/deactivation & lockout release (with last Super Admin safety)
- Hierarchical RBAC (Module -> Feature -> Action) with role creation, cloning, and permission toggles
- Never stores or logs plaintext passwords or raw reset tokens
"""

import re
import socket
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.config.logging_config import security_logger
from app.config.settings import settings
from app.models.activity import ActivityLog
from app.models.base import utc_now
from app.models.user import LoginHistory, PasswordResetToken, Permission, Role, User
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
                if not any(c.startswith("hr.") for c in existing_codes):
                    for hc in [c for c in preset_codes if c.startswith("hr.") and c in perm_map]:
                        if hc not in existing_codes:
                            role.permissions.append(perm_map[hc])
                            existing_codes.add(hc)
                if not any(c.startswith("academics.curriculum.") for c in existing_codes):
                    for ac in [c for c in preset_codes if c.startswith("academics.") and c in perm_map]:
                        if ac not in existing_codes:
                            role.permissions.append(perm_map[ac])
                            existing_codes.add(ac)
                if not any(c.startswith("attendance.corrections.") for c in existing_codes):
                    for attc in [c for c in preset_codes if c.startswith("attendance.") and c in perm_map]:
                        if attc not in existing_codes:
                            role.permissions.append(perm_map[attc])
                            existing_codes.add(attc)

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
            password, username=clean_user, email=clean_email
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

        # Ensure full permission catalog exists
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

        db.add(
            ActivityLog(
                user_id=admin_user.id,
                username=admin_user.username,
                action="FIRST_ADMIN_CREATED",
                module="SECURITY",
                entity_type="User",
                entity_id=str(admin_user.id),
                description=f"Initial Super Administrator '{admin_user.username}' provisioned via First-Run Setup.",
                ip_address=ip_address,
                severity="SECURITY",
            )
        )
        db.commit()
        db.refresh(admin_user)
        security_logger.info(
            f"First-Run Super Administrator provisioned: username='{admin_user.username}'"
        )
        return True, admin_user, "Super Administrator account created successfully."

    # ------------------------------------------------------------------
    # Authentication, Lockout & Login History
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
    def authenticate(
        db: Session,
        username_or_email: str,
        password: str,
        ip_address: str = "127.0.0.1",
        workstation: Optional[str] = None,
    ) -> Tuple[bool, Optional[User], str]:
        """
        Authenticate user with username or email, enforcing lockout protection,
        role/account active checks, bcrypt verification, and full LoginHistory audit.
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
            AuthService._record_login_history(
                db,
                user_id=user.id if user else None,
                username_attempted=identifier,
                status="FAILED_UNKNOWN",
                failure_reason="Unknown or deleted user account",
                ip_address=ip_address,
                workstation=workstation,
            )
            db.add(
                ActivityLog(
                    user_id=None,
                    username=identifier[:60],
                    action="LOGIN_FAILED",
                    module="AUTH",
                    description=f"Failed login attempt for unknown/deleted account '{identifier}'.",
                    ip_address=ip_address,
                    severity="WARNING",
                )
            )
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

        # If a previous lockout expired, clear locked_until cleanly
        if locked_until_utc and locked_until_utc <= now_utc:
            user.locked_until = None
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.failed_login_attempts = 0

        # Verify password using constant-time bcrypt
        if not PasswordHasher.verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = now_utc + timedelta(seconds=settings.LOCKOUT_DURATION_SECONDS)
                AuthService._record_login_history(
                    db,
                    user_id=user.id,
                    username_attempted=user.username,
                    status="FAILED_LOCKED",
                    failure_reason=f"Locked after {user.failed_login_attempts} failed attempts",
                    ip_address=ip_address,
                    workstation=workstation,
                )
                db.add(
                    ActivityLog(
                        user_id=user.id,
                        username=user.username,
                        action="ACCOUNT_LOCKED",
                        module="AUTH",
                        entity_type="User",
                        entity_id=str(user.id),
                        description=(
                            f"Account '{user.username}' locked for {settings.LOCKOUT_DURATION_SECONDS}s "
                            f"after {user.failed_login_attempts} consecutive failed logins."
                        ),
                        ip_address=ip_address,
                        severity="SECURITY",
                    )
                )
                db.commit()
                security_logger.critical(
                    f"User '{user.username}' locked out for {settings.LOCKOUT_DURATION_SECONDS}s "
                    f"after {user.failed_login_attempts} failed attempts"
                )
                return (
                    False,
                    None,
                    f"Account locked for {settings.LOCKOUT_DURATION_SECONDS} seconds due to too many failed attempts.",
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

        # Automatic bcrypt cost upgrade if legacy hash used fewer rounds
        if PasswordHasher.needs_rehash(user.password_hash):
            user.password_hash = PasswordHasher.hash_password(password)

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now_utc
        user.last_login_ip = ip_address

        session_id = app_session.set_current_user(user)
        hist = AuthService._record_login_history(
            db,
            user_id=user.id,
            username_attempted=user.username,
            status="SUCCESS",
            failure_reason=None,
            ip_address=ip_address,
            workstation=workstation,
            session_id=session_id,
        )
        db.add(
            ActivityLog(
                user_id=user.id,
                username=user.username,
                action="LOGIN_SUCCESS",
                module="AUTH",
                entity_type="User",
                entity_id=str(user.id),
                description=f"User '{user.username}' authenticated as {user.role.display_name}.",
                ip_address=ip_address,
                severity="INFO",
            )
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
        """Clear active session and stamp LoginHistory + ActivityLog."""
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

            action_code = "SESSION_TIMEOUT" if reason == "SESSION_TIMEOUT" else "LOGOUT"
            desc = (
                f"Session timed out automatically due to inactivity for user '{user.username}'."
                if reason == "SESSION_TIMEOUT"
                else f"User '{user.username}' signed out."
            )
            db.add(
                ActivityLog(
                    user_id=user.id,
                    username=user.username,
                    action=action_code,
                    module="AUTH",
                    entity_type="User",
                    entity_id=str(user.id),
                    description=desc,
                    ip_address=ip_address,
                    severity="SECURITY" if reason == "SESSION_TIMEOUT" else "INFO",
                )
            )
            db.commit()
            security_logger.info(f"User '{user.username}' ended session ({action_code})")

        app_session.clear()

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
        user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
        if not user:
            return False, "User not found."

        if not PasswordHasher.verify_password(old_password, user.password_hash):
            security_logger.warning(f"Password change denied (wrong current password) for '{user.username}'")
            return False, "Current password is incorrect."

        if old_password == new_password:
            return False, "New password must be different from your current password."

        valid_pw, msg = PasswordHasher.validate_password_strength(
            new_password, username=user.username, email=user.email
        )
        if not valid_pw:
            return False, msg

        user.password_hash = PasswordHasher.hash_password(new_password)
        user.is_default_password = False
        user.must_change_password = False
        user.password_changed_at = utc_now()
        user.session_version = (user.session_version or 1) + 1

        db.add(
            ActivityLog(
                user_id=user.id,
                username=user.username,
                action="PASSWORD_CHANGE",
                module="AUTH",
                entity_type="User",
                entity_id=str(user.id),
                description=f"User '{user.username}' changed account password.",
                ip_address=ip_address,
                severity="SECURITY",
            )
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

        # Revoke any previously unused tokens for this user
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
        db.add(
            ActivityLog(
                user_id=user.id,
                username=actor_username or user.username,
                action="PASSWORD_RESET_REQUEST",
                module="AUTH",
                entity_type="User",
                entity_id=str(user.id),
                description=f"Generated single-use password reset token for '{user.username}' (expires in {expires_minutes}m).",
                ip_address=ip_address,
                severity="SECURITY",
            )
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

        user = db.query(User).filter(User.id == token_rec.user_id, User.is_deleted == False).first()
        if not user or not user.is_active:
            return False, "Target account is unavailable or deactivated."

        valid_pw, pw_msg = PasswordHasher.validate_password_strength(
            new_password, username=user.username, email=user.email
        )
        if not valid_pw:
            return False, pw_msg

        user.password_hash = PasswordHasher.hash_password(new_password)
        user.is_default_password = False
        user.must_change_password = False
        user.password_changed_at = now_utc
        user.failed_login_attempts = 0
        user.locked_until = None
        user.session_version = (user.session_version or 1) + 1
        token_rec.used_at = now_utc

        db.add(
            ActivityLog(
                user_id=user.id,
                username=user.username,
                action="PASSWORD_RESET_COMPLETE",
                module="AUTH",
                entity_type="User",
                entity_id=str(user.id),
                description=f"Completed token-verified password reset for '{user.username}'.",
                ip_address=ip_address,
                severity="SECURITY",
            )
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

        target = db.query(User).filter(User.id == target_user_id, User.is_deleted == False).first()
        if not target:
            return False, None, "Target user not found."

        temp_pw = new_password if new_password else PasswordHasher.generate_temporary_password(14)
        valid_pw, pw_msg = PasswordHasher.validate_password_strength(
            temp_pw, username=target.username, email=target.email
        )
        if not valid_pw:
            return False, None, pw_msg

        target.password_hash = PasswordHasher.hash_password(temp_pw)
        target.is_default_password = False
        target.must_change_password = require_change
        target.password_changed_at = utc_now()
        target.failed_login_attempts = 0
        target.locked_until = None
        target.session_version = (target.session_version or 1) + 1

        # Revoke pending reset tokens
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == target.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.is_revoked == False,
        ).update({"is_revoked": True}, synchronize_session=False)

        db.add(
            ActivityLog(
                user_id=actor_user.id if actor_user else None,
                username=actor_user.username if actor_user else "system",
                action="ADMIN_PASSWORD_RESET",
                module="SECURITY",
                entity_type="User",
                entity_id=str(target.id),
                description=f"Administrator reset password for user '{target.username}' (must_change={require_change}).",
                ip_address=ip_address,
                severity="SECURITY",
            )
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
            return False, None, "Only an existing Super Admin may assign the Super Admin role."

        valid_pw, pw_msg = PasswordHasher.validate_password_strength(
            password, username=clean_user, email=clean_email
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

        db.add(
            ActivityLog(
                user_id=actor_user.id if actor_user else None,
                username=actor_user.username if actor_user else "system",
                action="USER_CREATED",
                module="SECURITY",
                entity_type="User",
                entity_id=str(new_user.id),
                description=f"Created user account '{new_user.username}' with role '{role.display_name}'.",
                ip_address=ip_address,
                severity="SECURITY",
            )
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

        target.is_active = is_active
        if not is_active:
            target.session_version = (target.session_version or 1) + 1
        else:
            target.failed_login_attempts = 0
            target.locked_until = None

        action = "USER_ACTIVATED" if is_active else "USER_DEACTIVATED"
        db.add(
            ActivityLog(
                user_id=actor_user.id if actor_user else None,
                username=actor_user.username if actor_user else "system",
                action=action,
                module="SECURITY",
                entity_type="User",
                entity_id=str(target.id),
                description=f"Account '{target.username}' was {'activated' if is_active else 'deactivated'}.",
                ip_address=ip_address,
                severity="SECURITY",
            )
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
        target = db.query(User).filter(User.id == target_user_id, User.is_deleted == False).first()
        if not target:
            return False, "User not found."

        target.failed_login_attempts = 0
        target.locked_until = None
        db.add(
            ActivityLog(
                user_id=actor_user.id if actor_user else None,
                username=actor_user.username if actor_user else "system",
                action="USER_UNLOCKED",
                module="SECURITY",
                entity_type="User",
                entity_id=str(target.id),
                description=f"Administrator unlocked account '{target.username}'.",
                ip_address=ip_address,
                severity="SECURITY",
            )
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

        db.add(
            ActivityLog(
                user_id=actor_user.id if actor_user else None,
                username=actor_user.username if actor_user else "system",
                action="ROLE_CREATED",
                module="SECURITY",
                entity_type="Role",
                entity_id=str(role.id),
                description=f"Created role '{role.display_name}' ({role.name}) with {len(perms)} permissions.",
                ip_address=ip_address,
                severity="SECURITY",
            )
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

        db.add(
            ActivityLog(
                user_id=actor_user.id if actor_user else None,
                username=actor_user.username if actor_user else "system",
                action="ROLE_CLONED",
                module="SECURITY",
                entity_type="Role",
                entity_id=str(cloned.id),
                description=(
                    f"Cloned role '{source.display_name}' -> '{cloned.display_name}' "
                    f"({len(cloned.permissions)} permissions copied)."
                ),
                ip_address=ip_address,
                severity="SECURITY",
            )
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

        perms = (
            db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
            if permission_ids
            else []
        )
        role.permissions = perms

        db.add(
            ActivityLog(
                user_id=actor_user.id if actor_user else None,
                username=actor_user.username if actor_user else "system",
                action="ROLE_PERMISSIONS_UPDATED",
                module="SECURITY",
                entity_type="Role",
                entity_id=str(role.id),
                description=f"Updated permissions on role '{role.display_name}' ({len(perms)} permissions assigned).",
                ip_address=ip_address,
                severity="SECURITY",
            )
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

        perm.is_active = is_active
        db.add(
            ActivityLog(
                user_id=actor_user.id if actor_user else None,
                username=actor_user.username if actor_user else "system",
                action="PERMISSION_TOGGLED",
                module="SECURITY",
                entity_type="Permission",
                entity_id=str(perm.id),
                description=f"Permission '{perm.code}' globally {'enabled' if is_active else 'disabled'}.",
                ip_address=ip_address,
                severity="SECURITY",
            )
        )
        db.commit()
        return True, f"Permission '{perm.code}' {'enabled' if is_active else 'disabled'}."

    # ------------------------------------------------------------------
    # Audit & Login History Queries
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
            term = f"%{username.strip()}%"
            q = q.filter(LoginHistory.username_attempted.ilike(term))
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
            q = q.filter(ActivityLog.username.ilike(f"%{username.strip()}%"))
        return q.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(limit).all()
