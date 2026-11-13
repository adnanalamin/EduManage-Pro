"""
EduManage Pro - Fees Management Models (SQLAlchemy)
Normalized models for Fee Categories, Fee Structures, Student Invoices, and Payment Receipts.
Supports partial payments, due tracking, scholarships, idempotency, and audit trails.
"""

from datetime import date
from sqlalchemy import (
    Column, Integer, String, Date, ForeignKey, Text, Boolean,
    UniqueConstraint, Index, Numeric, CheckConstraint
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class FeeCategory(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "fee_categories"

    name = Column(String(80), unique=True, nullable=False)  # e.g. "Tuition Fee", "Admission Fee"
    code = Column(String(20), unique=True, nullable=False)  # e.g. "TUI", "ADM", "EXM"
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    fee_structures = relationship("FeeStructure", back_populates="category")

    def __repr__(self):
        return f"<FeeCategory(name='{self.name}', code='{self.code}')>"


class FeeStructure(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "fee_structures"

    title = Column(String(120), nullable=False)  # e.g. "Class 10 Monthly Tuition Fee"
    category_id = Column(Integer, ForeignKey("fee_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    due_date = Column(Date, nullable=False)
    frequency = Column(String(30), default="Monthly", nullable=False)  # Monthly, Quarterly, Annual, One-Time

    category = relationship("FeeCategory", back_populates="fee_structures")
    school_class = relationship("SchoolClass")
    academic_year = relationship("AcademicYear")
    student_fees = relationship("StudentFee", back_populates="fee_structure")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_fee_structure_amount_nonneg"),
        Index("idx_fee_struct_class_year", "class_id", "academic_year_id"),
    )

    def __repr__(self):
        return f"<FeeStructure(title='{self.title}', amount={self.amount})>"


class StudentFee(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "student_fees"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    fee_structure_id = Column(Integer, ForeignKey("fee_structures.id", ondelete="RESTRICT"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)

    total_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    discount_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    discount_reason = Column(String(150), nullable=True)
    net_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    paid_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    due_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    status = Column(String(20), default="Unpaid", nullable=False, index=True)  # Paid, Partial, Unpaid, Refunded
    due_date = Column(Date, nullable=False)

    student = relationship("Student", backref="fees")
    fee_structure = relationship("FeeStructure", back_populates="student_fees")
    academic_year = relationship("AcademicYear")
    payments = relationship("FeePayment", back_populates="student_fee")

    __table_args__ = (
        UniqueConstraint("student_id", "fee_structure_id", "academic_year_id", name="uq_student_fee_structure_year"),
        CheckConstraint(
            "total_amount >= 0 AND discount_amount >= 0 AND net_amount >= 0 AND paid_amount >= 0 AND due_amount >= 0",
            name="ck_student_fee_amounts_nonneg",
        ),
        Index("idx_student_fee_status", "status"),
        Index("idx_student_fee_student", "student_id"),
    )

    def __repr__(self):
        return f"<StudentFee(student_id={self.student_id}, due={self.due_amount}, status='{self.status}')>"


class FeePayment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "fee_payments"

    receipt_no = Column(String(50), unique=True, nullable=False, index=True)  # e.g. "REC-2026-0001"
    idempotency_key = Column(String(64), unique=True, nullable=True, index=True)
    student_fee_id = Column(Integer, ForeignKey("student_fees.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount_paid = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    payment_method = Column(String(30), default="Cash", nullable=False)  # Cash, Bank, bKash, Nagad, Rocket, Card
    transaction_id = Column(String(80), nullable=True, index=True)
    payment_date = Column(Date, default=date.today, nullable=False, index=True)
    collected_by = Column(String(80), default="admin", nullable=False)
    remarks = Column(String(255), nullable=True)

    student_fee = relationship("StudentFee", back_populates="payments")
    student = relationship("Student")

    __table_args__ = (
        CheckConstraint("amount_paid > 0", name="ck_fee_payment_amount_pos"),
        Index("idx_fee_payment_student_date", "student_id", "payment_date"),
        Index("idx_fee_payment_fee_date", "student_fee_id", "payment_date"),
    )

    def __repr__(self):
        return f"<FeePayment(receipt_no='{self.receipt_no}', amount={self.amount_paid}, method='{self.payment_method}')>"
