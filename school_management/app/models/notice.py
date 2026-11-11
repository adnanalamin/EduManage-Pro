"""
EduManage Pro - Notice Board & Event Calendar ORM Models
Phase 13: School Notices, Official Circulars & Academic Calendar Events
"""

from sqlalchemy import Column, Integer, String, Date, Time, DateTime, Boolean, Text, ForeignKey
from datetime import datetime, date
from app.models.base import Base, TimestampMixin


class SchoolNotice(Base, TimestampMixin):
    """Official circular, bulletin memo, or notice for students, parents, or staff."""
    __tablename__ = "school_notices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reference_no = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(50), default="Academic")  # Academic, Exam, Holiday, Administrative, Sports, Fee
    target_audience = Column(String(50), default="All")  # All, Students, Teachers, Parents, Staff, Class-Specific
    target_class_id = Column(Integer, nullable=True)  # Optional class specific target
    priority = Column(String(20), default="Normal")  # Normal, Important, Urgent
    is_pinned = Column(Boolean, default=False)  # Pinned to top of bulletin board
    publish_date = Column(Date, default=date.today, nullable=False)
    expiry_date = Column(Date, nullable=True)
    content = Column(Text, nullable=False)
    attachment_name = Column(String(150), nullable=True)
    status = Column(String(20), default="Published")  # Published, Draft, Archived
    created_by = Column(String(100), default="Principal Office")

    def __repr__(self):
        return f"<SchoolNotice(ref='{self.reference_no}', title='{self.title}', priority='{self.priority}')>"


class SchoolEvent(Base, TimestampMixin):
    """Academic calendar event, holiday, exam period, or institutional ceremony."""
    __tablename__ = "school_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_title = Column(String(200), nullable=False)
    event_category = Column(String(50), default="Academic")  # Holiday, Exam, Sports, Cultural, PTM, Meeting, Tour
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False)
    start_time = Column(String(20), nullable=True)  # e.g., "09:00 AM"
    end_time = Column(String(20), nullable=True)    # e.g., "02:30 PM"
    venue = Column(String(150), default="Campus Main Auditorium")
    target_audience = Column(String(50), default="All")
    is_holiday = Column(Boolean, default=False)  # If True, triggers attendance auto-marking
    color_code = Column(String(20), default="#059669")
    description = Column(Text, nullable=True)
    organizer = Column(String(100), default="School Administration")

    def __repr__(self):
        return f"<SchoolEvent(id={self.id}, title='{self.event_title}', is_holiday={self.is_holiday})>"
