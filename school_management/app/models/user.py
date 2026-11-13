"""
EduManage Pro - User, Role, Hierarchical Permission, Login History, and Password Reset Models
"""

from typing import Optional
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, ForeignKey, Table, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin, SoftDeleteMixin, utc_now
from app.security.permissions import normalize_permission_code

# Many-to-Many association for Role and Permission
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    is_system_role = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

    def __repr__(self):
        return f"<Role(name='{self.name}', active={self.is_active})>"


class Permission(Base, TimestampMixin):
    """
    Hierarchical RBAC permission: Module -> Feature -> Action.
    Supports global enable/disable via `is_active`.
    """
    __tablename__ = "permissions"

    code = Column(String(100), unique=True, nullable=False, index=True)
    module = Column(String(50), nullable=False, index=True)
    feature = Column(String(100), nullable=False, default="General", index=True)
    action = Column(String(20), nullable=False, default="VIEW", index=True)
    name = Column(String(150), nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    __table_args__ = (
        UniqueConstraint("module", "feature", "action", name="uq_perm_module_feature_action"),
        Index("idx_perm_hierarchy", "module", "feature", "action"),
    )

    def __repr__(self):
        return f"<Permission(code='{self.code}', active={self.is_active})>"


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    username = Column(String(60), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=True)
    avatar_path = Column(String(255), nullable=True)

    role_id = Column(Integer, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    role = relationship("Role", back_populates="users")

    is_active = Column(Boolean, default=True, nullable=False)
    is_default_password = Column(Boolean, default=False, nullable=False)
    must_change_password = Column(Boolean, default=False, nullable=False)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(60), nullable=True)
    session_version = Column(Integer, default=1, nullable=False)

    # Security tracking
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(50), nullable=True)

    login_history = relationship("LoginHistory", back_populates="user")
    reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_user_role_active", "role_id", "is_active", "is_deleted"),
    )

    def has_permission(
        self,
        permission_code: str = "",
        *,
        module: Optional[str] = None,
        feature: Optional[str] = None,
        action: Optional[str] = None,
    ) -> bool:
        """
        Check authorization by exact permission code or Module -> Feature -> Action hierarchy.
        Enforces user active/not-deleted, role active, and permission `is_active`.
        """
        if not self.is_active or self.is_deleted or not self.role or not self.role.is_active:
            return False

        if self.role.name == "super_admin":
            return True

        active_perms = [p for p in (self.role.permissions or []) if getattr(p, "is_active", True)]

        if permission_code:
            normalized = normalize_permission_code(permission_code)
            return any(
                p.code == permission_code or p.code == normalized for p in active_perms
            )

        if module:
            mod_u = module.strip().upper()
            act_u = action.strip().upper() if action else None
            feat_l = feature.strip().lower() if feature else None
            for perm in active_perms:
                if (perm.module or "").upper() != mod_u:
                    continue
                if act_u and (perm.action or "").upper() != act_u:
                    continue
                if feat_l and feat_l not in (perm.feature or "").lower() and feat_l not in (perm.code or "").lower():
                    continue
                return True
        return False

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role.name if self.role else None}')>"


class LoginHistory(Base, TimestampMixin):
    """Records every authentication, failure, lockout, logout, and session timeout event."""
    __tablename__ = "login_history"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username_attempted = Column(String(120), nullable=False, index=True)
    status = Column(String(30), nullable=False, index=True)
    failure_reason = Column(String(255), nullable=True)
    ip_address = Column(String(50), default="127.0.0.1", nullable=True)
    workstation = Column(String(120), nullable=True)
    session_id = Column(String(64), nullable=True, index=True)
    login_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    logout_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="login_history")

    __table_args__ = (
        Index("idx_login_hist_user_time", "user_id", "login_at"),
        Index("idx_login_hist_status_time", "status", "login_at"),
    )

    def __repr__(self):
        return f"<LoginHistory(user='{self.username_attempted}', status='{self.status}')>"


class PasswordResetToken(Base, TimestampMixin):
    """Stores single-use, expiring password reset token hashes (never raw tokens)."""
    __tablename__ = "password_reset_tokens"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    issued_by = Column(String(60), default="self", nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    is_revoked = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="reset_tokens")

    def __repr__(self):
        return f"<PasswordResetToken(user_id={self.user_id}, used={self.used_at is not None})>"
