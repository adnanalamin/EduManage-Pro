"""
EduManage Pro - User, Role, and Permission Models
"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin

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
    is_system_role = Column(Boolean, default=False)

    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

    def __repr__(self):
        return f"<Role(name='{self.name}')>"


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    code = Column(String(80), unique=True, nullable=False, index=True)
    module = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    def __repr__(self):
        return f"<Permission(code='{self.code}')>"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    username = Column(String(60), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=True)
    avatar_path = Column(String(255), nullable=True)
    
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    role = relationship("Role", back_populates="users")

    is_active = Column(Boolean, default=True, nullable=False)
    is_default_password = Column(Boolean, default=True, nullable=False)
    
    # Security tracking
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(50), nullable=True)

    def has_permission(self, permission_code: str) -> bool:
        if self.role and self.role.name == "super_admin":
            return True
        if not self.role:
            return False
        return any(perm.code == permission_code for perm in self.role.permissions)

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role.name if self.role else None}')>"
