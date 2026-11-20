"""
EduManage Pro - Enterprise User Session Management
Maintains authenticated desktop user context, activity heartbeat, session timeout,
DB-backed session revocation validation, and RBAC permission checks.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import uuid

from app.config.settings import settings
from app.models.user import User
from app.security.permissions import SIDEBAR_MODULE_PERMISSION_MAP


class SessionManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
            cls._instance._current_user = None
            cls._instance._login_time = None
            cls._instance._last_activity_at = None
            cls._instance._session_id = None
            cls._instance._session_secret = None
            cls._instance._session_version = None
            cls._instance._login_history_id = None
            cls._instance._timeout_minutes = settings.SESSION_TIMEOUT_MINUTES
        return cls._instance

    @property
    def current_user(self) -> Optional[User]:
        return self._current_user

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    @property
    def session_secret(self) -> Optional[str]:
        return self._session_secret

    @property
    def session_version(self) -> Optional[int]:
        return self._session_version

    @property
    def login_history_id(self) -> Optional[int]:
        return self._login_history_id

    @property
    def login_time(self) -> Optional[datetime]:
        return self._login_time

    @property
    def last_activity_at(self) -> Optional[datetime]:
        return self._last_activity_at

    @property
    def timeout_minutes(self) -> int:
        return self._timeout_minutes

    @timeout_minutes.setter
    def timeout_minutes(self, minutes: int) -> None:
        self._timeout_minutes = max(0, int(minutes))

    @property
    def is_authenticated(self) -> bool:
        return self._current_user is not None and not self.is_expired()

    def set_current_user(
        self,
        user: User,
        session_id: Optional[str] = None,
        login_history_id: Optional[int] = None,
        timeout_minutes: Optional[int] = None,
        session_secret: Optional[str] = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        self._current_user = user
        self._login_time = now
        self._last_activity_at = now
        self._session_id = session_id or str(uuid.uuid4())
        self._session_secret = session_secret
        self._session_version = getattr(user, "session_version", 1)
        self._login_history_id = login_history_id
        if timeout_minutes is not None:
            self._timeout_minutes = max(0, int(timeout_minutes))
        else:
            self._timeout_minutes = settings.SESSION_TIMEOUT_MINUTES
        return self._session_id

    def touch(self) -> None:
        """Refresh activity timestamp when user interacts with the desktop UI."""
        if self._current_user is not None:
            self._last_activity_at = datetime.now(timezone.utc)

    def validate_against_db(self, db: Any) -> bool:
        """
        Verify current session is still active in DB:
        - Checks User.is_active, User.is_deleted, Role.is_active
        - Checks User.session_version matches session_version (rejects post-password-reset sessions)
        - Checks UserSession record has not been revoked or expired
        """
        if not self.is_authenticated or not self._current_user or not self._session_id:
            return False
        from app.models.user import UserSession, User as DbUser

        fresh_user = db.query(DbUser).filter(DbUser.id == self._current_user.id).first()
        if (
            not fresh_user
            or not fresh_user.is_active
            or fresh_user.is_deleted
            or not fresh_user.role
            or not fresh_user.role.is_active
        ):
            self.clear()
            return False

        if self._session_version is not None and (fresh_user.session_version or 1) != self._session_version:
            self.clear()
            return False

        sess_row = db.query(UserSession).filter(UserSession.session_id == self._session_id).first()
        if sess_row is not None:
            now = datetime.now(timezone.utc)
            exp = sess_row.expires_at
            if exp and exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if not sess_row.is_active or (exp and exp <= now):
                sess_row.is_active = False
                if not sess_row.revoked_at:
                    sess_row.revoked_at = now
                    sess_row.revoke_reason = sess_row.revoke_reason or "Expired"
                db.commit()
                self.clear()
                return False
            sess_row.last_activity_at = now
            if self._timeout_minutes > 0:
                sess_row.expires_at = now + timedelta(minutes=self._timeout_minutes)
            db.commit()
        return True

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if self._current_user is None:
            return False
        if self._timeout_minutes <= 0:
            return False
        if self._last_activity_at is None:
            return False
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        last = self._last_activity_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (current - last) >= timedelta(minutes=self._timeout_minutes)

    def remaining_seconds(self, now: Optional[datetime] = None) -> Optional[int]:
        if self._current_user is None or self._timeout_minutes <= 0 or self._last_activity_at is None:
            return None
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        last = self._last_activity_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        deadline = last + timedelta(minutes=self._timeout_minutes)
        return max(0, int((deadline - current).total_seconds()))

    def clear(self) -> None:
        self._current_user = None
        self._login_time = None
        self._last_activity_at = None
        self._session_id = None
        self._session_secret = None
        self._session_version = None
        self._login_history_id = None

    def is_super_admin(self) -> bool:
        if not self.is_authenticated or not self._current_user or not self._current_user.role:
            return False
        return self._current_user.role.name.lower() == "super_admin" and self._current_user.role.is_active

    def has_role(self, role_name: str) -> bool:
        if not self.is_authenticated or not self._current_user or not self._current_user.role:
            return False
        return self._current_user.role.name.lower() == role_name.lower()

    def has_permission(
        self,
        permission_code: str = "",
        *,
        module: Optional[str] = None,
        feature: Optional[str] = None,
        action: Optional[str] = None,
    ) -> bool:
        if not self.is_authenticated or not self._current_user:
            return False
        return self._current_user.has_permission(
            permission_code,
            module=module,
            feature=feature,
            action=action,
        )

    def can_access_sidebar_module(self, sidebar_key: str) -> bool:
        if not self.is_authenticated or not self._current_user:
            return False
        if self.is_super_admin():
            return True
        if sidebar_key == "settings":
            return (
                self.has_permission(module="SETTINGS", action="VIEW")
                or self.has_permission(module="SECURITY", action="VIEW")
            )
        module_name = SIDEBAR_MODULE_PERMISSION_MAP.get(sidebar_key)
        if not module_name:
            return False
        return self.has_permission(module=module_name, action="VIEW")


session = SessionManager()
