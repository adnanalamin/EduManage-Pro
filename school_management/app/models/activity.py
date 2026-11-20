"""
EduManage Pro - Enterprise Activity & Security Audit Log Model
Tracks WHO, WHAT, WHEN, MODULE, RECORD, BEFORE, and AFTER snapshots safely.
Never persists plaintext passwords, tokens, API keys, or secrets.
"""

import json
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.base import TimestampMixin


class ActivityLog(Base, TimestampMixin):
    __tablename__ = "activity_logs"

    # WHO
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(60), nullable=False, index=True)
    actor_role = Column(String(80), nullable=True, index=True)

    # WHAT
    action = Column(String(80), nullable=False, index=True)
    description = Column(Text, nullable=False)
    severity = Column(String(20), default="INFO", nullable=False, index=True)  # INFO, WARNING, SECURITY, CRITICAL

    # MODULE & RECORD
    module = Column(String(60), nullable=False, index=True)
    entity_type = Column(String(60), nullable=True, index=True)
    entity_id = Column(String(60), nullable=True, index=True)
    record_label = Column(String(255), nullable=True)

    # BEFORE & AFTER Snapshots (JSON-encoded & secret-redacted)
    before_data = Column(Text, nullable=True)
    after_data = Column(Text, nullable=True)
    changed_fields = Column(Text, nullable=True)

    # Context metadata & classification
    ip_address = Column(String(50), default="127.0.0.1", nullable=True)
    workstation = Column(String(120), nullable=True)
    session_id = Column(String(64), nullable=True, index=True)
    is_admin_action = Column(Boolean, default=False, nullable=False, index=True)

    user = relationship("User")

    __table_args__ = (
        Index("idx_activity_module_created", "module", "created_at"),
        Index("idx_activity_entity", "entity_type", "entity_id"),
        Index("idx_activity_admin_created", "is_admin_action", "created_at"),
    )

    @property
    def who(self) -> str:
        return f"{self.username} ({self.actor_role})" if self.actor_role else self.username

    @property
    def what(self) -> str:
        return self.action

    @property
    def when(self):
        return self.created_at

    @property
    def record_ref(self) -> str:
        if self.record_label:
            return self.record_label
        if self.entity_type and self.entity_id:
            return f"{self.entity_type}#{self.entity_id}"
        return self.entity_type or "—"

    @property
    def before_snapshot(self) -> Optional[Dict[str, Any]]:
        if not self.before_data:
            return None
        try:
            return json.loads(self.before_data)
        except Exception:
            return {"raw": self.before_data}

    @property
    def after_snapshot(self) -> Optional[Dict[str, Any]]:
        if not self.after_data:
            return None
        try:
            return json.loads(self.after_data)
        except Exception:
            return {"raw": self.after_data}

    def __repr__(self):
        return f"<ActivityLog(action='{self.action}', user='{self.username}', module='{self.module}')>"
