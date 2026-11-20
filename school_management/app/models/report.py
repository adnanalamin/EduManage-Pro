"""
EduManage Pro - Saved Report Builder Definitions Model (SQLAlchemy)
Stores user-configured custom reports (domain, selected columns, filters, grouping,
sorting, date range, academic year) for one-click re-execution and export.
"""

import json
from typing import Any, Dict, List

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.base import PublicIdMixin, SoftDeleteMixin, TimestampMixin


class SavedReportDefinition(Base, PublicIdMixin, TimestampMixin, SoftDeleteMixin):
    """Persisted configuration created in the Professional Report Builder."""

    __tablename__ = "saved_report_definitions"

    name = Column(String(140), unique=True, nullable=False, index=True)
    domain_key = Column(String(40), nullable=False, index=True)
    description = Column(String(255), nullable=True)

    columns_json = Column(Text, nullable=False, default="[]")
    filters_json = Column(Text, nullable=False, default="[]")
    group_by = Column(String(60), nullable=True)
    sort_by = Column(String(60), nullable=True)
    sort_desc = Column(Boolean, default=False, nullable=False)

    date_from = Column(String(20), nullable=True)  # YYYY-MM-DD
    date_to = Column(String(20), nullable=True)    # YYYY-MM-DD
    academic_year_id = Column(
        Integer,
        ForeignKey("academic_years.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_shared = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(80), default="admin", nullable=False)

    academic_year = relationship("AcademicYear", foreign_keys=[academic_year_id])

    def get_columns(self) -> List[str]:
        try:
            parsed = json.loads(self.columns_json or "[]")
            return [str(c) for c in parsed] if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []

    def get_filters(self) -> List[Dict[str, Any]]:
        try:
            parsed = json.loads(self.filters_json or "[]")
            return [f for f in parsed if isinstance(f, dict)] if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []

    def __repr__(self) -> str:
        return f"<SavedReportDefinition(name='{self.name}', domain='{self.domain_key}')>"
