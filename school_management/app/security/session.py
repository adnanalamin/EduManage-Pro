"""
EduManage Pro - User Session Management
Maintains current authenticated desktop user session.
"""

from typing import Optional, List
from datetime import datetime
from app.models.user import User


class SessionManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
            cls._instance._current_user: Optional[User] = None
            cls._instance._login_time: Optional[datetime] = None
        return cls._instance

    @property
    def current_user(self) -> Optional[User]:
        return self._current_user

    @property
    def is_authenticated(self) -> bool:
        return self._current_user is not None

    def set_current_user(self, user: User):
        self._current_user = user
        self._login_time = datetime.utcnow()

    def clear(self):
        self._current_user = None
        self._login_time = None

    def has_role(self, role_name: str) -> bool:
        if not self._current_user or not self._current_user.role:
            return False
        return self._current_user.role.name.lower() == role_name.lower()

    def has_permission(self, permission_code: str) -> bool:
        if not self._current_user:
            return False
        return self._current_user.has_permission(permission_code)


session = SessionManager()
