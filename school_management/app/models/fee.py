"""
EduManage Pro - Enterprise Fees Management Models (SQLAlchemy)
Normalized, immutable-ledger models for Fee Categories, Fee Structures,
Monthly/Custom Student Invoices, Partial Payments, Adjustments (Discount /
Scholarship / Waiver), Advance Credit Wallets, Refunds, and Cancellations.
"""

from datetime import date, datetime
from typing import Optional, Tuple

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, utc_now


PAYMENT_CHANNELS = ("Cash", "Bank", "Card", "Mobile Banking", "Other")


def normalize_payment_channel(raw_method: Optional[str], explicit_detail: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Normalize payment method to enterprise standard channels:
    Cash | Bank | Card | Mobile Banking | Other
    Preserves specific provider/instrument names (e.g. bKash, Nagad, Bank Transfer, Cheque)
    in `channel_detail`.
    """
    raw = (raw_method or "Cash").strip()
    low = raw.lower()
    detail = explicit_detail.strip() if explicit_detail and explicit_detail.strip() else None

    if low == "cash":
        return "Cash", detail
    if low in ("bank", "bank transfer", "cheque", "wire", "eft", "beftn", "rtgs", "npsb"):
        return "Bank", detail or (raw if low != "bank" else None)
    if low in ("card", "debit card", "credit card", "debit/credit card", "visa", "mastercard", "pos"):
        return "Card", detail or (raw if low != "card" else None)
    if low in ("mobile banking", "bkash", "nagad", "rocket", "upay", "mfs", "mobile"):
        return "Mobile Banking", detail or (raw if low not in ("mobile banking", "mobile") else None)
    if low == "advance wallet":
        return "Other", detail or "Advance Wallet"
    if low == "other":
        return "Other", detail
    return "Other", detail or raw


class FeeCategory(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "fee_categories"

    name = Column(String(80), unique=True, nullable=False)  # Tuition Fee, Admission Fee, Exam Fee, etc.
    code = Column(String(20), unique=True, nullable=False)  # TUI, ADM, EXM, LIB, TRN, HST, DEV, OTH
    description = Column(String(255), nullable=True)
    is_recurring = Column(Boolean, default=False, nullable=False)
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
    billing_month = Column(Integer, nullable=True, index=True)  # 1..12 for monthly billing structures
    billing_year = Column(Integer, nullable=True, index=True)
    description = Column(String(255), nullable=True)

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
    """
    Student Fee Invoice.
    Supports Discount, Scholarship, Waiver, Partial Payments, Advance Allocation,
    Refund tracking, and Non-Destructive Cancellation.
    """
    __tablename__ = "student_fees"

    invoice_no = Column(String(50), unique=True, nullable=True, index=True)  # INV-2026-00001
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    fee_structure_id = Column(Integer, ForeignKey("fee_structures.id", ondelete="RESTRICT"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)
    title = Column(String(150), nullable=True)

    total_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    discount_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)  # Combined total concessions (legacy + breakdown)
    discount_type = Column(String(30), default="Discount", nullable=True)  # Discount, Scholarship, Waiver
    scholarship_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    waiver_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    discount_reason = Column(String(150), nullable=True)
    net_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    paid_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    refunded_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    advance_applied_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    due_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    status = Column(String(25), default="Unpaid", nullable=False, index=True)  # Unpaid, Partial, Paid, Overdue, Cancelled, Refunded, Partially Refunded
    due_date = Column(Date, nullable=False)
    billing_month = Column(Integer, nullable=True)
    billing_year = Column(Integer, nullable=True)

    cancelled_at = Column(DateTime, nullable=True)
    cancelled_by = Column(String(80), nullable=True)
    cancellation_reason = Column(String(255), nullable=True)

    student = relationship("Student", backref="fees")
    fee_structure = relationship("FeeStructure", back_populates="student_fees")
    academic_year = relationship("AcademicYear")
    payments = relationship("FeePayment", back_populates="student_fee", order_by="FeePayment.id.desc()")
    adjustments = relationship("FeeAdjustment", back_populates="student_fee", order_by="FeeAdjustment.id.desc()")
    refunds = relationship("FeeRefund", back_populates="student_fee", order_by="FeeRefund.id.desc()")

    __table_args__ = (
        UniqueConstraint("student_id", "fee_structure_id", "academic_year_id", name="uq_student_fee_structure_year"),
        CheckConstraint(
            "total_amount >= 0 AND discount_amount >= 0 AND net_amount >= 0 AND paid_amount >= 0 AND due_amount >= 0",
            name="ck_student_fee_amounts_nonneg",
        ),
        Index("idx_student_fee_status", "status"),
        Index("idx_student_fee_student", "student_id"),
    )

    @property
    def invoice_number(self) -> str:
        return self.invoice_no or f"INV-{self.id or 0:06d}"

    @property
    def display_title(self) -> str:
        if self.title:
            return self.title
        if self.fee_structure:
            return self.fee_structure.title
        return "School Fee"

    def __repr__(self):
        return f"<StudentFee(invoice='{self.invoice_number}', student_id={self.student_id}, due={self.due_amount}, status='{self.status}')>"


class FeePayment(Base, TimestampMixin, SoftDeleteMixin):
    """
    Immutable Payment Receipt Voucher.
    Never permanently deleted; refunds/reversals are recorded via FeeRefund.
    """
    __tablename__ = "fee_payments"

    receipt_no = Column(String(50), unique=True, nullable=False, index=True)  # e.g. "REC-2026-00001"
    idempotency_key = Column(String(64), unique=True, nullable=True, index=True)
    student_fee_id = Column(Integer, ForeignKey("student_fees.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount_paid = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    payment_method = Column(String(30), default="Cash", nullable=False, index=True)  # Cash, Bank, Card, Mobile Banking, Other
    channel_detail = Column(String(80), nullable=True)  # bKash, Nagad, Rocket, City Bank, VISA, etc.
    transaction_id = Column(String(80), nullable=True, index=True)
    payment_date = Column(Date, default=date.today, nullable=False, index=True)
    collected_by = Column(String(80), default="admin", nullable=False)
    remarks = Column(String(255), nullable=True)
    status = Column(String(30), default="Completed", nullable=False, index=True)  # Completed, Partially Refunded, Refunded, Reversed
    refunded_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    is_advance_allocation = Column(Boolean, default=False, nullable=False)
    accounting_tx_id = Column(Integer, ForeignKey("account_transactions.id", ondelete="SET NULL"), nullable=True, index=True)

    student_fee = relationship("StudentFee", back_populates="payments")
    student = relationship("Student")
    refunds = relationship("FeeRefund", back_populates="fee_payment", order_by="FeeRefund.id.desc()")
    accounting_tx = relationship("AccountTransaction", foreign_keys=[accounting_tx_id])

    __table_args__ = (
        CheckConstraint("amount_paid > 0", name="ck_fee_payment_amount_pos"),
        Index("idx_fee_payment_student_date", "student_id", "payment_date"),
        Index("idx_fee_payment_fee_date", "student_fee_id", "payment_date"),
    )

    @property
    def receipt_number(self) -> str:
        return self.receipt_no

    @property
    def refundable_balance(self) -> float:
        return max(0.0, float(self.amount_paid or 0.0) - float(self.refunded_amount or 0.0))

    def __repr__(self):
        return f"<FeePayment(receipt_no='{self.receipt_no}', amount={self.amount_paid}, method='{self.payment_method}')>"


class FeeAdjustment(Base, TimestampMixin):
    """
    Immutable audit log of fee concessions: Discount, Scholarship, Waiver.
    """
    __tablename__ = "fee_adjustments"

    student_fee_id = Column(Integer, ForeignKey("student_fees.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    adjustment_type = Column(String(30), nullable=False, index=True)  # Discount, Scholarship, Waiver
    amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    reason = Column(String(255), nullable=False)
    approved_by = Column(String(80), nullable=True)
    applied_by = Column(String(80), default="admin", nullable=False)
    applied_at = Column(DateTime, default=utc_now, nullable=False)

    student_fee = relationship("StudentFee", back_populates="adjustments")
    student = relationship("Student")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_fee_adjustment_amount_pos"),
    )

    def __repr__(self):
        return f"<FeeAdjustment(type='{self.adjustment_type}', amount={self.amount}, fee_id={self.student_fee_id})>"


class FeeRefund(Base, TimestampMixin):
    """
    Immutable Refund & Reversal Voucher linked to an original FeePayment and StudentFee invoice.
    """
    __tablename__ = "fee_refunds"

    refund_no = Column(String(50), unique=True, nullable=False, index=True)  # RFD-2026-00001
    fee_payment_id = Column(Integer, ForeignKey("fee_payments.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_fee_id = Column(Integer, ForeignKey("student_fees.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    refund_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    refund_method = Column(String(30), default="Cash", nullable=False)  # Cash, Bank, Card, Mobile Banking, Other
    channel_detail = Column(String(80), nullable=True)
    reference_no = Column(String(100), nullable=True)
    refund_date = Column(Date, default=date.today, nullable=False, index=True)
    reason = Column(String(255), nullable=False)
    processed_by = Column(String(80), default="admin", nullable=False)
    approved_by = Column(String(80), nullable=True)
    status = Column(String(25), default="Completed", nullable=False)
    accounting_tx_id = Column(Integer, ForeignKey("account_transactions.id", ondelete="SET NULL"), nullable=True, index=True)

    fee_payment = relationship("FeePayment", back_populates="refunds")
    student_fee = relationship("StudentFee", back_populates="refunds")
    student = relationship("Student")
    accounting_tx = relationship("AccountTransaction", foreign_keys=[accounting_tx_id])

    __table_args__ = (
        CheckConstraint("refund_amount > 0", name="ck_fee_refund_amount_pos"),
        Index("idx_fee_refund_student_date", "student_id", "refund_date"),
    )

    def __repr__(self):
        return f"<FeeRefund(refund_no='{self.refund_no}', amount={self.refund_amount})>"


class StudentAdvanceCredit(Base, TimestampMixin):
    """
    Immutable Student Advance Payment & Credit Wallet Ledger.
    Tracks deposits, invoice allocations, and advance refunds with running balance.
    """
    __tablename__ = "student_advance_credits"

    receipt_no = Column(String(50), unique=True, nullable=False, index=True)  # ADV-2026-00001
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    transaction_type = Column(String(30), nullable=False, index=True)  # Deposit, AppliedToInvoice, Refunded, Reversed
    amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    signed_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    balance_after = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    payment_method = Column(String(30), default="Cash", nullable=False)
    channel_detail = Column(String(80), nullable=True)
    reference_no = Column(String(100), nullable=True)
    transaction_date = Column(Date, default=date.today, nullable=False, index=True)
    student_fee_id = Column(Integer, ForeignKey("student_fees.id", ondelete="SET NULL"), nullable=True, index=True)
    related_credit_id = Column(Integer, ForeignKey("student_advance_credits.id", ondelete="SET NULL"), nullable=True)
    accounting_tx_id = Column(Integer, ForeignKey("account_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    recorded_by = Column(String(80), default="admin", nullable=False)
    remarks = Column(String(255), nullable=True)

    student = relationship("Student")
    student_fee = relationship("StudentFee")
    accounting_tx = relationship("AccountTransaction", foreign_keys=[accounting_tx_id])

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_adv_credit_amount_pos"),
        CheckConstraint("balance_after >= 0", name="ck_adv_credit_balance_nonneg"),
    )

    def __repr__(self):
        return f"<StudentAdvanceCredit(receipt='{self.receipt_no}', type='{self.transaction_type}', amount={self.amount})>"


def _prevent_financial_delete(mapper, connection, target):
    raise ValueError(
        f"Permanent deletion of {type(target).__name__} is prohibited by financial audit policy. "
        f"Use reversal, refund, or invoice cancellation instead."
    )


for _immutable_fee_model in (FeePayment, FeeAdjustment, FeeRefund, StudentAdvanceCredit):
    event.listen(_immutable_fee_model, "before_delete", _prevent_financial_delete)
