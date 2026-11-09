"""
EduManage Pro - Attendance Models (SQLAlchemy)
Normalized models for Student and Teacher Daily & Register Attendance.
Supports Present, Absent, Late, and Leave states with timestamps, remarks, and audit trails.
"""

from datetime import date
from sqlalchemy import (
    Column, Integer, String, Date, ForeignKey, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin


class StudentAttendance(Base, TimestampMixin):
    __tablename__ = "student_attendances"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=True)
    date = Column(Date, default=date.today, nullable=False, index=True)
    
    # Status: 'Present', 'Absent', 'Late', 'Leave'
    status = Column(String(20), default="Present", nullable=False)
    check_in_time = Column(String(20), nullable=True)  # e.g., "08:15 AM"
    remarks = Column(String(255), nullable=True)       # e.g., "Approved Medical Leave"
    marked_by = Column(String(80), default="admin", nullable=False)

    # Relationships
    student = relationship("Student", backref="attendances")
    school_class = relationship("SchoolClass")
    section = relationship("Section")

    __table_args__ = (
        UniqueConstraint("student_id", "date", name="uq_student_daily_attendance"),
        Index("idx_student_att_class_date", "class_id", "date"),
    )

    def __repr__(self):
        return f"<StudentAttendance(student_id={self.student_id}, date={self.date}, status='{self.status}')>"


class TeacherAttendance(Base, TimestampMixin):
    __tablename__ = "teacher_attendances"

    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, default=date.today, nullable=False, index=True)

    # Status: 'Present', 'Absent', 'Late', 'Leave'
    status = Column(String(20), default="Present", nullable=False)
    check_in_time = Column(String(20), nullable=True)   # e.g., "07:50 AM"
    check_out_time = Column(String(20), nullable=True)  # e.g., "03:15 PM"
    remarks = Column(String(255), nullable=True)        # e.g., "Official Training Workshop"
    marked_by = Column(String(80), default="admin", nullable=False)

    # Relationships
    teacher = relationship("Teacher", backref="attendances")

    __table_args__ = (
        UniqueConstraint("teacher_id", "date", name="uq_teacher_daily_attendance"),
        Index("idx_teacher_att_date", "date"),
    )

    def __repr__(self):
        return f"<TeacherAttendance(teacher_id={self.teacher_id}, date={self.date}, status='{self.status}')>"
