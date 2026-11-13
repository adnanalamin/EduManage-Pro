"""
EduManage Pro - Base ORM Mixins
Provides dialect-neutral UUID public identifiers, timezone-aware timestamps, and soft-delete fields.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database.connection import Base


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp (compatible with SQLite and PostgreSQL)."""
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    """Generate a standard UUIDv4 string (36 chars, portable across SQLite & PostgreSQL)."""
    return str(uuid.uuid4())


class PublicIdMixin:
    """Adds a globally unique UUIDv4 public identifier suitable for APIs and sync."""
    public_id = Column(String(36), unique=True, nullable=False, index=True, default=generate_uuid)


class TimestampMixin(PublicIdMixin):
    """Standard primary key, public UUID, and timezone-aware audit timestamps."""
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class SoftDeleteMixin:
    """Adds reversible soft-delete tracking to prevent accidental data loss."""
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(80), nullable=True)

    def mark_deleted(self, deleted_by: Optional[str] = "system") -> None:
        self.is_deleted = True
        self.deleted_at = utc_now()
        self.deleted_by = deleted_by

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None


__all__ = [
    "Base",
    "utc_now",
    "generate_uuid",
    "PublicIdMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
]
