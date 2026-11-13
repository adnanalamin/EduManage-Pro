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

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True)
    date = Column(Date, default=date.today, nullable=False, index=True)

    # Status: 'Present', 'Absent', 'Late', 'Leave'
    status = Column(String(20), default="Present", nullable=False)
    check_in_time = Column(String(20), nullable=True)
    remarks = Column(String(255), nullable=True)
    marked_by = Column(String(80), default="admin", nullable=False)

    # Relationships
    student = relationship("Student", backref="attendances")
    school_class = relationship("SchoolClass")
    section = relationship("Section")
    academic_year = relationship("AcademicYear")

    __table_args__ = (
        UniqueConstraint("student_id", "date", name="uq_student_daily_attendance"),
        Index("idx_student_att_class_date", "class_id", "date"),
        Index("idx_student_att_date_status", "date", "status"),
    )

    def __repr__(self):
        return f"<StudentAttendance(student_id={self.student_id}, date={self.date}, status='{self.status}')>"


class TeacherAttendance(Base, TimestampMixin):
    __tablename__ = "teacher_attendances"

    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, default=date.today, nullable=False, index=True)

    # Status: 'Present', 'Absent', 'Late', 'Leave'
    status = Column(String(20), default="Present", nullable=False)
    check_in_time = Column(String(20), nullable=True)
    check_out_time = Column(String(20), nullable=True)
    remarks = Column(String(255), nullable=True)
    marked_by = Column(String(80), default="admin", nullable=False)

    # Relationships
    teacher = relationship("Teacher", backref="attendances")

    __table_args__ = (
        UniqueConstraint("teacher_id", "date", name="uq_teacher_daily_attendance"),
        Index("idx_teacher_att_date", "date"),
        Index("idx_teacher_att_date_status", "date", "status"),
    )

    def __repr__(self):
        return f"<TeacherAttendance(teacher_id={self.teacher_id}, date={self.date}, status='{self.status}')>"


class StaffAttendance(Base, TimestampMixin):
    __tablename__ = "staff_attendances"

    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, default=date.today, nullable=False, index=True)

    # Status: 'Present', 'Absent', 'Late', 'Leave'
    status = Column(String(20), default="Present", nullable=False)
    check_in_time = Column(String(20), nullable=True)
    check_out_time = Column(String(20), nullable=True)
    remarks = Column(String(255), nullable=True)
    marked_by = Column(String(80), default="admin", nullable=False)

    staff = relationship("Staff", backref="attendances")

    __table_args__ = (
        UniqueConstraint("staff_id", "date", name="uq_staff_daily_attendance"),
        Index("idx_staff_att_date", "date"),
        Index("idx_staff_att_date_status", "date", "status"),
    )

    def __repr__(self):
        return f"<StaffAttendance(staff_id={self.staff_id}, date={self.date}, status='{self.status}')>"


