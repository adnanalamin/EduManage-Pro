"""
EduManage Pro - Notice Board & Event Calendar ORM Models
Phase 13: School Notices, Official Circulars & Academic Calendar Events
"""

from datetime import date
from sqlalchemy import (
    Column, Integer, String, Date, Boolean, Text, ForeignKey, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class SchoolNotice(Base, TimestampMixin, SoftDeleteMixin):
    """Official circular, bulletin memo, or notice for students, parents, or staff."""
    __tablename__ = "school_notices"

    reference_no = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(50), default="Academic", nullable=False)
    target_audience = Column(String(50), default="All", nullable=False)
    target_class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="SET NULL"), nullable=True, index=True)
    priority = Column(String(20), default="Normal", nullable=False)  # Normal, Important, Urgent
    is_pinned = Column(Boolean, default=False, nullable=False)
    publish_date = Column(Date, default=date.today, nullable=False, index=True)
    expiry_date = Column(Date, nullable=True)
    content = Column(Text, nullable=False)
    attachment_name = Column(String(150), nullable=True)
    status = Column(String(20), default="Published", nullable=False, index=True)  # Published, Draft, Archived
    created_by = Column(String(100), default="Principal Office", nullable=False)

    target_class = relationship("SchoolClass")

    __table_args__ = (
        Index("idx_notice_status_publish", "status", "publish_date"),
    )

    def __repr__(self):
        return f"<SchoolNotice(ref='{self.reference_no}', title='{self.title}', priority='{self.priority}')>"


class SchoolEvent(Base, TimestampMixin, SoftDeleteMixin):
    """Academic calendar event, holiday, exam period, or institutional ceremony."""
    __tablename__ = "school_events"

    event_title = Column(String(200), nullable=False)
    event_category = Column(String(50), default="Academic", nullable=False)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False)
    start_time = Column(String(20), nullable=True)
    end_time = Column(String(20), nullable=True)
    venue = Column(String(150), default="Campus Main Auditorium")
    target_audience = Column(String(50), default="All", nullable=False)
    is_holiday = Column(Boolean, default=False, nullable=False)
    color_code = Column(String(20), default="#059669")
    description = Column(Text, nullable=True)
    organizer = Column(String(100), default="School Administration")
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True)
    term_name = Column(String(60), nullable=True)

    academic_year = relationship("AcademicYear")

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_school_event_dates"),
        Index("idx_event_dates", "start_date", "end_date"),
    )

    def __repr__(self):
        return f"<SchoolEvent(id={self.id}, title='{self.event_title}', is_holiday={self.is_holiday})>"
