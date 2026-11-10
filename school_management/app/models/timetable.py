"""
EduManage Pro - Timetable & Routine ORM Models
Phase 9: Class Timetable, Teacher Routine, Period Slots & Room Allocation
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Time, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class PeriodSlot(Base):
    """Represents a scheduled period/bell time slot during a school day."""
    __tablename__ = "period_slots"

    id = Column(Integer, primary_key=True, index=True)
    period_number = Column(Integer, nullable=False)  # 1, 2, 3, etc. 0 for Assembly/Break
    name = Column(String(50), nullable=False)  # "1st Period", "Tiffin Break", "Assembly"
    start_time = Column(String(10), nullable=False)  # "08:30 AM"
    end_time = Column(String(10), nullable=False)  # "09:15 AM"
    duration_minutes = Column(Integer, default=45)
    is_break = Column(Boolean, default=False)
    shift = Column(String(20), default="Morning")  # Morning, Day
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=True)

    timetable_entries = relationship("TimetableEntry", back_populates="period_slot", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PeriodSlot #{self.period_number} '{self.name}' ({self.start_time}-{self.end_time})>"


class TimetableEntry(Base):
    """Represents a single classroom teaching allocation slot."""
    __tablename__ = "timetable_entries"

    id = Column(Integer, primary_key=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)
    day_of_week = Column(String(20), nullable=False)  # "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Saturday"
    period_slot_id = Column(Integer, ForeignKey("period_slots.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    room_number = Column(String(50), nullable=False)  # "Room 301", "Lab 2"
    notes = Column(String(200), nullable=True)

    # Relationships
    period_slot = relationship("PeriodSlot", back_populates="timetable_entries")
    school_class = relationship("SchoolClass")
    section = relationship("Section")
    subject = relationship("Subject")
    teacher = relationship("Teacher")

    __table_args__ = (
        # Ensure a class cannot have two subjects in the same period on the same day
        UniqueConstraint('class_id', 'section_id', 'day_of_week', 'period_slot_id', name='uq_class_period_slot'),
    )

    def __repr__(self):
        return f"<TimetableEntry Class {self.class_id} {self.day_of_week} Period {self.period_slot_id}>"
