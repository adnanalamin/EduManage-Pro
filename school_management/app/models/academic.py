"""
EduManage Pro - Academic Foundation Models
Defines AcademicYear, AcademicGroup, AcademicShift, AcademicRoom,
SchoolClass, Section, Subject, and StudentSubjectEnrollment models.
Supports custom class structures, departments, optional subjects,
class/subject teachers, rooms, and historical preservation across years.
"""

from datetime import date
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


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


class AcademicGroup(Base, TimestampMixin, SoftDeleteMixin):
    """Academic streams/groups (e.g., General, Science, Humanities, Business Studies, Vocational)."""
    __tablename__ = "academic_groups"

    name = Column(String(60), nullable=False, unique=True, index=True)
    code = Column(String(20), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    display_order = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    classes = relationship("SchoolClass", back_populates="academic_group")

    def __repr__(self):
        return f"<AcademicGroup(name='{self.name}', code='{self.code}')>"


class AcademicShift(Base, TimestampMixin, SoftDeleteMixin):
    """Institutional shifts (e.g., Morning, Day, Evening, Weekend)."""
    __tablename__ = "academic_shifts"

    name = Column(String(50), nullable=False, unique=True, index=True)
    code = Column(String(20), nullable=False, unique=True)
    start_time = Column(String(20), nullable=True)  # e.g., "07:30 AM"
    end_time = Column(String(20), nullable=True)    # e.g., "12:30 PM"
    description = Column(String(255), nullable=True)
    display_order = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    classes = relationship("SchoolClass", back_populates="academic_shift")

    def __repr__(self):
        return f"<AcademicShift(name='{self.name}', start='{self.start_time}')>"


class AcademicRoom(Base, TimestampMixin, SoftDeleteMixin):
    """Campus classrooms, laboratories, lecture halls, and activity rooms."""
    __tablename__ = "academic_rooms"

    room_number = Column(String(40), nullable=False, unique=True, index=True)
    room_name = Column(String(100), nullable=True)
    building = Column(String(80), default="Main Building", nullable=False)
    floor = Column(String(30), default="Ground", nullable=False)
    room_type = Column(String(40), default="Classroom", nullable=False)  # Classroom, Science Lab, Computer Lab, Auditorium
    capacity = Column(Integer, default=50, nullable=False)
    facilities = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    sections = relationship("Section", back_populates="room")

    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_academic_room_capacity_pos"),
    )

    def __repr__(self):
        return f"<AcademicRoom(number='{self.room_number}', type='{self.room_type}', cap={self.capacity})>"


class SchoolClass(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "school_classes"

    name = Column(String(60), nullable=False)  # e.g., "Class 9", "Class 10"
    code = Column(String(20), nullable=True)   # e.g., "C9", "C10"
    numeric_order = Column(Integer, default=1, nullable=False)
    group = Column(String(40), default="General", nullable=False)  # General, Science, Humanities, Business Studies
    shift = Column(String(30), default="Morning", nullable=False)  # Morning, Day, Evening
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)

    # Extended Academic Structure Links
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    group_id = Column(Integer, ForeignKey("academic_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    shift_id = Column(Integer, ForeignKey("academic_shifts.id", ondelete="SET NULL"), nullable=True, index=True)
    structure_profile = Column(String(60), default="Standard", nullable=False)  # Standard, Custom, Pre-Primary, Higher Secondary
    max_sections = Column(Integer, default=10, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    academic_year = relationship("AcademicYear", back_populates="classes")
    department = relationship("Department")
    academic_group = relationship("AcademicGroup", back_populates="classes")
    academic_shift = relationship("AcademicShift", back_populates="classes")
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

    # Extended Room/Group/Shift links
    room_id = Column(Integer, ForeignKey("academic_rooms.id", ondelete="SET NULL"), nullable=True, index=True)
    group_id = Column(Integer, ForeignKey("academic_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    shift_id = Column(Integer, ForeignKey("academic_shifts.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    school_class = relationship("SchoolClass", back_populates="sections")
    class_teacher = relationship("Teacher", foreign_keys=[class_teacher_id])
    room = relationship("AcademicRoom", back_populates="sections")
    academic_group = relationship("AcademicGroup")
    academic_shift = relationship("AcademicShift")

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
    subject_type = Column(String(20), default="Mandatory", nullable=False)  # Mandatory, Optional, Elective
    is_optional = Column(Boolean, default=False, nullable=False)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True, index=True)

    # Department & Stream Metadata
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    group_id = Column(Integer, ForeignKey("academic_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    credit_hours = Column(Float, default=1.0, nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    school_class = relationship("SchoolClass", back_populates="subjects")
    assigned_teacher = relationship("Teacher", foreign_keys=[teacher_id])
    department = relationship("Department")
    academic_group = relationship("AcademicGroup")

    __table_args__ = (
        UniqueConstraint("class_id", "code", name="uq_subject_class_code"),
        CheckConstraint("full_marks > 0 AND pass_marks >= 0 AND pass_marks <= full_marks", name="ck_subject_marks_valid"),
    )

    def __repr__(self):
        return f"<Subject(id='{self.subject_id}', name='{self.name}', code='{self.code}')>"


class StudentSubjectEnrollment(Base, TimestampMixin):
    """Per-academic-year student enrollment in Mandatory or Optional/Elective subjects."""
    __tablename__ = "student_subject_enrollments"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    is_optional = Column(Boolean, default=True, nullable=False)
    enrollment_status = Column(String(30), default="Active", nullable=False)  # Active, Completed, Dropped
    enrolled_date = Column(Date, default=date.today, nullable=False)
    remarks = Column(String(255), nullable=True)

    student = relationship("Student")
    academic_year = relationship("AcademicYear")
    school_class = relationship("SchoolClass")
    subject = relationship("Subject")

    __table_args__ = (
        UniqueConstraint("student_id", "academic_year_id", "subject_id", name="uq_student_year_subject"),
    )


