"""
EduManage Pro - Activity Log Model
Audits security and administrative actions across the school management system.
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin


class ActivityLog(Base, TimestampMixin):
    __tablename__ = "activity_logs"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(60), nullable=False, index=True)
    action = Column(String(80), nullable=False, index=True)
    module = Column(String(60), nullable=False, index=True)
    entity_type = Column(String(60), nullable=True, index=True)
    entity_id = Column(String(60), nullable=True, index=True)
    description = Column(Text, nullable=False)
    ip_address = Column(String(50), default="127.0.0.1", nullable=True)
    severity = Column(String(20), default="INFO", nullable=False, index=True)  # INFO, WARNING, SECURITY

    user = relationship("User")

    __table_args__ = (
        Index("idx_activity_module_created", "module", "created_at"),
        Index("idx_activity_entity", "entity_type", "entity_id"),
    )

    def __repr__(self):
        return f"<ActivityLog(action='{self.action}', user='{self.username}')>"

