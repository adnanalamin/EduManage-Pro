"""
EduManage Pro - Academic Foundation Models
Defines AcademicYear, SchoolClass, Section, and Subject models.
Full integration with Teacher assignments, shifts, rooms, marks and group streams.
"""

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Date, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class AcademicYear(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "academic_years"

    name = Column(String(50), nullable=False, unique=True)  # e.g., "2025-2026"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_current = Column(Boolean, default=False, nullable=False, index=True)
    status = Column(String(20), default="Active", nullable=False, index=True)  # Active, Upcoming, Completed

    classes = relationship("SchoolClass", back_populates="academic_year")

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_academic_year_dates"),
    )

    def __repr__(self):
        return f"<AcademicYear(name='{self.name}', current={self.is_current})>"


class SchoolClass(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "school_classes"

    name = Column(String(60), nullable=False)  # e.g., "Class 9", "Class 10"
    code = Column(String(20), nullable=True)   # e.g., "C9", "C10"
    numeric_order = Column(Integer, default=1, nullable=False)
    group = Column(String(40), default="General", nullable=False)  # General, Science, Humanities, Business Studies
    shift = Column(String(30), default="Morning", nullable=False)  # Morning, Day, Evening
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)

    academic_year = relationship("AcademicYear", back_populates="classes")
    sections = relationship("Section", back_populates="school_class", cascade="all, delete-orphan")
    subjects = relationship("Subject", back_populates="school_class", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("academic_year_id", "name", "group", "shift", name="uq_class_year_name_group_shift"),
        Index("idx_class_year_order", "academic_year_id", "numeric_order"),
    )

    def __repr__(self):
        return f"<SchoolClass(name='{self.name}', group='{self.group}')>"


class Section(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sections"

    name = Column(String(40), nullable=False)  # e.g. "Section A", "Padma", "Morning Star"
    room_number = Column(String(40), nullable=True)  # e.g. "Room 204", "Building B - Lab 1"
    capacity = Column(Integer, default=50, nullable=False)
    shift = Column(String(30), default="Morning", nullable=False)
    group = Column(String(40), default="General", nullable=False)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    class_teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True, index=True)

    school_class = relationship("SchoolClass", back_populates="sections")
    class_teacher = relationship("Teacher", foreign_keys=[class_teacher_id])

    __table_args__ = (
        UniqueConstraint("class_id", "name", name="uq_section_class_name"),
        CheckConstraint("capacity > 0", name="ck_section_capacity_pos"),
    )

    def __repr__(self):
        return f"<Section(name='{self.name}', room='{self.room_number}')>"


class Subject(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "subjects"

    subject_id = Column(String(40), unique=True, nullable=False, index=True)  # e.g. "SUB-2026-001"
    name = Column(String(100), nullable=False)  # e.g. "Higher Mathematics"
    code = Column(String(30), nullable=False)  # e.g. "126"
    full_marks = Column(Integer, default=100, nullable=False)
    pass_marks = Column(Integer, default=33, nullable=False)
    theory_marks = Column(Integer, default=75, nullable=False)
    practical_marks = Column(Integer, default=25, nullable=False)
    subject_type = Column(String(20), default="Mandatory", nullable=False)  # Mandatory, Optional
    is_optional = Column(Boolean, default=False, nullable=False)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True, index=True)

    school_class = relationship("SchoolClass", back_populates="subjects")
    assigned_teacher = relationship("Teacher", foreign_keys=[teacher_id])

    __table_args__ = (
        UniqueConstraint("class_id", "code", name="uq_subject_class_code"),
        CheckConstraint("full_marks > 0 AND pass_marks >= 0 AND pass_marks <= full_marks", name="ck_subject_marks_valid"),
    )

    def __repr__(self):
        return f"<Subject(id='{self.subject_id}', name='{self.name}', code='{self.code}')>"

