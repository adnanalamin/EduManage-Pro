"""
EduManage Pro - Teacher, Staff, and Department Models (SQLAlchemy)
Normalized models for academic faculty and administrative non-teaching employees.
"""

from datetime import date
from sqlalchemy import Column, String, Integer, Date, Boolean, ForeignKey, Text, Numeric, CheckConstraint, Index
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class Department(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "departments"

    name = Column(String(80), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    teachers = relationship("Teacher", back_populates="department")
    staff = relationship("Staff", back_populates="department")

    def __repr__(self):
        return f"<Department(name='{self.name}', code='{self.code}')>"


class Teacher(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "teachers"

    # Identifiers
    teacher_id = Column(String(40), unique=True, nullable=False, index=True)
    employee_id = Column(String(40), unique=True, nullable=False, index=True)

    # Personal Information
    full_name = Column(String(120), nullable=False, index=True)
    full_name_bn = Column(String(120), nullable=True)
    gender = Column(String(15), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    blood_group = Column(String(10), nullable=True)
    photo_path = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    address = Column(Text, nullable=True)
    nid_number = Column(String(50), unique=True, nullable=True)

    # Professional & Academic
    qualification = Column(String(150), nullable=False)
    designation = Column(String(80), default="Assistant Teacher", nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True)
    primary_subject = Column(String(80), nullable=False)
    joining_date = Column(Date, default=date.today, nullable=False)

    # Financial & Contract
    salary = Column(Integer, default=35000, nullable=False)
    bank_account_no = Column(String(60), nullable=True)
    bank_name = Column(String(100), nullable=True)

    # Status & Attendance Tracking
    status = Column(String(20), default="active", nullable=False, index=True)

    # Relationships
    department = relationship("Department", back_populates="teachers")

    __table_args__ = (
        CheckConstraint("salary >= 0", name="ck_teacher_salary_nonneg"),
        Index("idx_teacher_status_deleted", "status", "is_deleted"),
    )

    def __repr__(self):
        return f"<Teacher(id='{self.teacher_id}', name='{self.full_name}', dept='{self.primary_subject}')>"


class Staff(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "staff_members"

    # Identifiers
    staff_id = Column(String(40), unique=True, nullable=False, index=True)
    employee_id = Column(String(40), unique=True, nullable=False, index=True)

    # Personal
    full_name = Column(String(120), nullable=False, index=True)
    full_name_bn = Column(String(120), nullable=True)
    gender = Column(String(15), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    phone = Column(String(30), nullable=False, index=True)
    email = Column(String(120), nullable=True, index=True)
    address = Column(Text, nullable=True)

    # Role & Department
    position = Column(String(80), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True)
    shift = Column(String(20), default="Day", nullable=False)
    joining_date = Column(Date, default=date.today, nullable=False)

    # Compensation
    salary = Column(Integer, default=22000, nullable=False)
    status = Column(String(20), default="active", nullable=False, index=True)

    # Relationships
    department = relationship("Department", back_populates="staff")

    __table_args__ = (
        CheckConstraint("salary >= 0", name="ck_staff_salary_nonneg"),
        Index("idx_staff_status_deleted", "status", "is_deleted"),
    )

    def __repr__(self):
        return f"<Staff(id='{self.staff_id}', name='{self.full_name}', pos='{self.position}')>"

