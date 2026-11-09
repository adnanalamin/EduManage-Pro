"""
EduManage Pro - Fees Management Models (SQLAlchemy)
Normalized models for Fee Categories, Fee Structures, Student Invoices, and Payment Receipts.
Supports partial payments, due tracking, scholarships, multiple payment channels, and audit trails.
"""

from datetime import date
from sqlalchemy import (
    Column, Integer, String, Float, Date, ForeignKey, Text, Boolean, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin


class FeeCategory(Base, TimestampMixin):
    __tablename__ = "fee_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False) # e.g. "Tuition Fee", "Admission Fee"
    code = Column(String(20), unique=True, nullable=False) # e.g. "TUI", "ADM", "EXM"
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    fee_structures = relationship("FeeStructure", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FeeCategory(name='{self.name}', code='{self.code}')>"


class FeeStructure(Base, TimestampMixin):
    __tablename__ = "fee_structures"

    id = Column(Integer, primary_key=True)
    title = Column(String(120), nullable=False) # e.g. "Class 10 Monthly Tuition Fee"
    category_id = Column(Integer, ForeignKey("fee_categories.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    amount = Column(Float, default=0.0, nullable=False)
    due_date = Column(Date, nullable=False)
    frequency = Column(String(30), default="Monthly", nullable=False) # Monthly, Quarterly, Annual, One-Time

    category = relationship("FeeCategory", back_populates="fee_structures")
    school_class = relationship("SchoolClass")
    academic_year = relationship("AcademicYear")
    student_fees = relationship("StudentFee", back_populates="fee_structure", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FeeStructure(title='{self.title}', amount={self.amount})>"


class StudentFee(Base, TimestampMixin):
    __tablename__ = "student_fees"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    fee_structure_id = Column(Integer, ForeignKey("fee_structures.id"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)

    total_amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0, nullable=False) # Scholarship or financial aid
    discount_reason = Column(String(150), nullable=True)        # e.g. "Merit Waiver 20%"
    net_amount = Column(Float, nullable=False)                  # total_amount - discount_amount
    paid_amount = Column(Float, default=0.0, nullable=False)
    due_amount = Column(Float, nullable=False)                   # net_amount - paid_amount
    status = Column(String(20), default="Unpaid", nullable=False, index=True) # Paid, Partial, Unpaid, Refunded
    due_date = Column(Date, nullable=False)

    student = relationship("Student", backref="fees")
    fee_structure = relationship("FeeStructure", back_populates="student_fees")
    payments = relationship("FeePayment", back_populates="student_fee", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_student_fee_status", "status"),
        Index("idx_student_fee_student", "student_id"),
    )

    def __repr__(self):
        return f"<StudentFee(student_id={self.student_id}, due={self.due_amount}, status='{self.status}')>"


class FeePayment(Base, TimestampMixin):
    __tablename__ = "fee_payments"

    id = Column(Integer, primary_key=True)
    receipt_no = Column(String(50), unique=True, nullable=False, index=True) # e.g. "REC-2026-0001"
    student_fee_id = Column(Integer, ForeignKey("student_fees.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    amount_paid = Column(Float, nullable=False)
    payment_method = Column(String(30), default="Cash", nullable=False) # Cash, Bank, bKash, Nagad, Rocket, Card
    transaction_id = Column(String(80), nullable=True)                  # e.g. Bank slip or mobile TrxID
    payment_date = Column(Date, default=date.today, nullable=False, index=True)
    collected_by = Column(String(80), default="admin", nullable=False)
    remarks = Column(String(255), nullable=True)

    student_fee = relationship("StudentFee", back_populates="payments")
    student = relationship("Student")

    def __repr__(self):
        return f"<FeePayment(receipt_no='{self.receipt_no}', amount={self.amount_paid}, method='{self.payment_method}')>"
