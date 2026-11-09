"""
EduManage Pro - Activity Log Model
Audits security and administrative actions across the school management system.
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin


class ActivityLog(Base, TimestampMixin):
    __tablename__ = "activity_logs"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(60), nullable=False)
    action = Column(String(80), nullable=False, index=True)  # LOGIN, LOGOUT, SETUP_COMPLETE, PASSWORD_CHANGE, etc.
    module = Column(String(60), nullable=False, index=True)  # AUTH, SETTINGS, ACADEMICS, etc.
    description = Column(Text, nullable=False)
    ip_address = Column(String(50), default="127.0.0.1", nullable=True)
    severity = Column(String(20), default="INFO", nullable=False)  # INFO, WARNING, SECURITY

    user = relationship("User")

    def __repr__(self):
        return f"<ActivityLog(action='{self.action}', user='{self.username}')>"
