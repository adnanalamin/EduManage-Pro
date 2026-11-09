"""
EduManage Pro - Student & Guardian Models (SQLAlchemy)
Complete normalized schemas for Student profiles, Guardians, and Promotion records.
"""

from datetime import date, datetime
from sqlalchemy import (
    Column, String, Integer, Date, Boolean, ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin


class StudentStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRANSFERRED = "transferred"
    GRADUATED = "graduated"
    SUSPENDED = "suspended"


class Guardian(Base, TimestampMixin):
    __tablename__ = "guardians"

    father_name = Column(String(120), nullable=True)
    mother_name = Column(String(120), nullable=True)
    guardian_name = Column(String(120), nullable=False)
    relation = Column(String(50), default="Father", nullable=False)  # Father, Mother, Uncle, Legal Guardian
    guardian_phone = Column(String(30), nullable=False, index=True)
    guardian_email = Column(String(120), nullable=True)
    guardian_occupation = Column(String(100), nullable=True)
    guardian_nid = Column(String(50), nullable=True)
    guardian_address = Column(Text, nullable=True)

    students = relationship("Student", back_populates="guardian")

    def __repr__(self):
        return f"<Guardian(name='{self.guardian_name}', phone='{self.guardian_phone}')>"


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    # Identifiers
    student_id = Column(String(40), unique=True, nullable=False, index=True)  # e.g. STU-2024-001
    admission_number = Column(String(40), unique=True, nullable=False, index=True)  # e.g. ADM-2024-0101
    roll_number = Column(Integer, nullable=False, index=True)

    # Personal Information
    first_name = Column(String(60), nullable=False)
    last_name = Column(String(60), nullable=False)
    full_name = Column(String(120), nullable=False, index=True)
    full_name_bn = Column(String(120), nullable=True)
    gender = Column(String(15), nullable=False)  # Male, Female, Other
    date_of_birth = Column(Date, nullable=False)
    blood_group = Column(String(10), nullable=True)  # A+, A-, B+, B-, O+, O-, AB+, AB-
    photo_path = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)

    # Address & Nationality
    address = Column(Text, nullable=True)
    city = Column(String(80), default="Dhaka", nullable=True)
    district = Column(String(80), default="Dhaka", nullable=True)
    division = Column(String(80), default="Dhaka", nullable=True)
    country = Column(String(80), default="Bangladesh", nullable=True)
    religion = Column(String(40), default="Islam", nullable=True)
    nationality = Column(String(50), default="Bangladeshi", nullable=True)
    birth_certificate_no = Column(String(60), nullable=True)

    # Academic Enrollment
    admission_date = Column(Date, default=date.today, nullable=False)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False, index=True)
    group = Column(String(40), default="General", nullable=True)  # Science, Humanities, Business Studies, General
    shift = Column(String(20), default="Day", nullable=True)      # Morning, Day

    # Status
    status = Column(String(20), default=StudentStatus.ACTIVE, nullable=False, index=True)

    # Guardian Relationship
    guardian_id = Column(Integer, ForeignKey("guardians.id", ondelete="SET NULL"), nullable=True)
    guardian = relationship("Guardian", back_populates="students")

    # Additional Details
    previous_school = Column(String(150), nullable=True)
    emergency_contact = Column(String(30), nullable=True)
    medical_notes = Column(Text, nullable=True)

    # Foreign Key Relationships
    school_class = relationship("SchoolClass")
    section = relationship("Section")
    academic_year = relationship("AcademicYear")

    def __repr__(self):
        return f"<Student(id='{self.student_id}', name='{self.full_name}', roll={self.roll_number})>"


class StudentPromotionHistory(Base, TimestampMixin):
    __tablename__ = "student_promotion_history"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    from_class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    to_class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    from_academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    to_academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    promoted_date = Column(Date, default=date.today, nullable=False)
    remarks = Column(String(255), nullable=True)

    student = relationship("Student")
