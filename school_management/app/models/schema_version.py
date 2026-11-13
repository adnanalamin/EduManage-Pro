"""
EduManage Pro - Schema Version & Migration Tracking Model
Records applied schema versions and migration checksums across SQLite & PostgreSQL.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database.connection import Base
from app.models.base import TimestampMixin, utc_now


class SchemaVersion(Base, TimestampMixin):
    __tablename__ = "schema_versions"

    version = Column(Integer, unique=True, nullable=False, index=True)
    revision_id = Column(String(64), nullable=False, index=True)
    description = Column(String(255), nullable=False)
    dialect = Column(String(30), nullable=False, default="sqlite")
    applied_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    checksum = Column(String(64), nullable=True)
    status = Column(String(20), nullable=False, default="applied")  # applied, rolled_back, failed
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<SchemaVersion(v={self.version}, rev='{self.revision_id}', status='{self.status}')>"
