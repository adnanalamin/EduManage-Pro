"""
EduManage Pro - Base Model with Timestamp mixins
"""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from app.database.connection import Base


class TimestampMixin:
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
