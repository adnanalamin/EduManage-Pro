"""
EduManage Pro - Advanced Timetable & Routine ORM Models
Supports:
- Multi-Shift Period Slots scoped by AcademicYear and AcademicShift
- Class, Teacher, and Room Timetables (AcademicRoom linked + backward-compatible room_number)
- Immutable Academic Year TimetableHistory with Snapshot Archive
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.base import PublicIdMixin, SoftDeleteMixin, TimestampMixin, utc_now


class PeriodSlot(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a scheduled period/bell time slot during a school day, scoped by shift and academic year."""
    __tablename__ = "period_slots"

    period_number = Column(Integer, nullable=False)  # 1, 2, 3, etc. 0 for Assembly, 99 for Break
    name = Column(String(50), nullable=False)        # "1st Period", "Tiffin Break", "Assembly"
    start_time = Column(String(15), nullable=False)  # "08:30 AM"
    end_time = Column(String(15), nullable=False)    # "09:15 AM"
    duration_minutes = Column(Integer, default=45, nullable=False)
    is_break = Column(Boolean, default=False, nullable=False)
    shift = Column(String(30), default="Morning", nullable=False, index=True)  # Morning, Day, Evening
    shift_id = Column(Integer, ForeignKey("academic_shifts.id", ondelete="SET NULL"), nullable=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    academic_year = relationship("AcademicYear")
    academic_shift = relationship("AcademicShift")
    timetable_entries = relationship("TimetableEntry", back_populates="period_slot")

    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="ck_period_duration_pos"),
        Index("idx_period_shift_year", "shift", "academic_year_id", "period_number"),
    )

    def __repr__(self):
        return f"<PeriodSlot #{self.period_number} '{self.name}' [{self.shift}] ({self.start_time}-{self.end_time})>"


class TimetableEntry(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a single classroom teaching allocation slot scoped by Academic Year and Shift."""
    __tablename__ = "timetable_entries"

    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)
    day_of_week = Column(String(20), nullable=False, index=True)
    period_slot_id = Column(Integer, ForeignKey("period_slots.id", ondelete="RESTRICT"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("academic_rooms.id", ondelete="SET NULL"), nullable=True, index=True)
    room_number = Column(String(50), nullable=False)  # "Room 301", "Lab 2"
    shift = Column(String(30), default="Morning", nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("academic_shifts.id", ondelete="SET NULL"), nullable=True, index=True)
    is_auto_generated = Column(Boolean, default=False, nullable=False)
    version_no = Column(Integer, default=1, nullable=False)
    notes = Column(String(200), nullable=True)

    # Relationships
    academic_year = relationship("AcademicYear")
    period_slot = relationship("PeriodSlot", back_populates="timetable_entries")
    school_class = relationship("SchoolClass")
    section = relationship("Section")
    subject = relationship("Subject")
    teacher = relationship("Teacher")
    room = relationship("AcademicRoom")
    academic_shift = relationship("AcademicShift")

    __table_args__ = (
        UniqueConstraint("class_id", "section_id", "day_of_week", "period_slot_id", name="uq_class_period_slot"),
        Index("idx_timetable_teacher_conflict", "academic_year_id", "day_of_week", "period_slot_id", "teacher_id"),
        Index("idx_timetable_room_conflict", "academic_year_id", "day_of_week", "period_slot_id", "room_number"),
        Index("idx_timetable_year_shift", "academic_year_id", "shift"),
    )

    def __repr__(self):
        return f"<TimetableEntry Year={self.academic_year_id} Class={self.class_id} {self.day_of_week} Period={self.period_slot_id}>"


class TimetableHistory(Base, PublicIdMixin):
    """
    Immutable audit & version archive keeping timetable history per Academic Year.
    Captures manual edits, slot moves/swaps, auto-suggestions, year-end archives, and cross-year clones.
    """
    __tablename__ = "timetable_history"

    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="SET NULL"), nullable=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)
    shift_name = Column(String(40), nullable=True, default="Morning", index=True)
    action = Column(String(40), nullable=False, index=True)
    version_no = Column(Integer, nullable=False, default=1)
    entry_summary = Column(String(255), nullable=True)
    snapshot_json = Column(Text, nullable=True)
    reason = Column(String(255), nullable=True)
    performed_by = Column(String(100), nullable=False, default="system")
    performed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    academic_year = relationship("AcademicYear")
    school_class = relationship("SchoolClass")
    section = relationship("Section")

    def __repr__(self):
        return f"<TimetableHistory Year={self.academic_year_id} Action='{self.action}' v={self.version_no}>"


def _prevent_timetable_history_delete(mapper, connection, target):
    raise ValueError(
        f"Permanent deletion of {type(target).__name__} is prohibited by academic archive policy."
    )


event.listen(TimetableHistory, "before_delete", _prevent_timetable_history_delete)
