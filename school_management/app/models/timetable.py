"""
EduManage Pro - Timetable & Routine ORM Models
Phase 9: Class Timetable, Teacher Routine, Period Slots & Room Allocation
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class PeriodSlot(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a scheduled period/bell time slot during a school day."""
    __tablename__ = "period_slots"

    period_number = Column(Integer, nullable=False)  # 1, 2, 3, etc. 0 for Assembly/Break
    name = Column(String(50), nullable=False)  # "1st Period", "Tiffin Break", "Assembly"
    start_time = Column(String(10), nullable=False)  # "08:30 AM"
    end_time = Column(String(10), nullable=False)  # "09:15 AM"
    duration_minutes = Column(Integer, default=45, nullable=False)
    is_break = Column(Boolean, default=False, nullable=False)
    shift = Column(String(20), default="Morning", nullable=False, index=True)  # Morning, Day
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=True, index=True)

    academic_year = relationship("AcademicYear")
    timetable_entries = relationship("TimetableEntry", back_populates="period_slot")

    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="ck_period_duration_pos"),
    )

    def __repr__(self):
        return f"<PeriodSlot #{self.period_number} '{self.name}' ({self.start_time}-{self.end_time})>"


class TimetableEntry(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a single classroom teaching allocation slot."""
    __tablename__ = "timetable_entries"

    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)
    day_of_week = Column(String(20), nullable=False, index=True)
    period_slot_id = Column(Integer, ForeignKey("period_slots.id", ondelete="RESTRICT"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False, index=True)
    room_number = Column(String(50), nullable=False)  # "Room 301", "Lab 2"
    notes = Column(String(200), nullable=True)

    # Relationships
    academic_year = relationship("AcademicYear")
    period_slot = relationship("PeriodSlot", back_populates="timetable_entries")
    school_class = relationship("SchoolClass")
    section = relationship("Section")
    subject = relationship("Subject")
    teacher = relationship("Teacher")

    __table_args__ = (
        UniqueConstraint("class_id", "section_id", "day_of_week", "period_slot_id", name="uq_class_period_slot"),
        Index("idx_timetable_teacher_conflict", "academic_year_id", "day_of_week", "period_slot_id", "teacher_id"),
        Index("idx_timetable_room_conflict", "academic_year_id", "day_of_week", "period_slot_id", "room_number"),
    )

    def __repr__(self):
        return f"<TimetableEntry Class {self.class_id} {self.day_of_week} Period {self.period_slot_id}>"
