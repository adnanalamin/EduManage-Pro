"""
EduManage Pro - Enterprise Accounting, Budget & Financial Audit Models
Defines AccountCategory, AccountTransaction (with non-destructive reversal chains),
AccountBudget, and FinancialAuditLog for institutional cashbook, ledger, budgets, and P&L.
"""

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
    event,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, utc_now


class AccountCategory(Base, TimestampMixin, SoftDeleteMixin):
    """
    Chart of accounts categories classified into Income or Expense heads.
    """
    __tablename__ = "account_categories"

    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(20), unique=True, nullable=False)
    type = Column(String(20), nullable=False, index=True)  # 'Income' | 'Expense'
    description = Column(String(255), nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    transactions = relationship("AccountTransaction", back_populates="category")
    budgets = relationship("AccountBudget", back_populates="category")

    def __repr__(self):
        return f"<AccountCategory(name='{self.name}', type='{self.type}', code='{self.code}')>"


class AccountTransaction(Base, TimestampMixin, SoftDeleteMixin):
    """
    Individual immutable debit/credit voucher recording financial income, expenditure, or reversal.
    Transactions are NEVER hard-deleted; corrections use compensating Reversal entries.
    """
    __tablename__ = "account_transactions"

    voucher_no = Column(String(50), unique=True, nullable=False, index=True)
    idempotency_key = Column(String(64), unique=True, nullable=True, index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    type = Column(String(20), nullable=False, index=True)  # 'Income' | 'Expense'
    entry_kind = Column(String(30), nullable=False, default="Standard", index=True)  # Standard, FeeCollection, AdvanceDeposit, FeeRefund, Reversal, Payroll
    category_id = Column(Integer, ForeignKey("account_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    payment_method = Column(String(30), nullable=False, default="Cash", index=True)  # Cash, Bank, Card, Mobile Banking, Other
    channel_detail = Column(String(80), nullable=True)
    reference_no = Column(String(100), nullable=True, index=True)
    paid_to_received_from = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    recorded_by = Column(String(100), nullable=False, default="Accountant")
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="Approved", index=True)  # Approved, Pending, Reversed, Voided

    is_reversed = Column(Boolean, default=False, nullable=False, index=True)
    reversal_of_id = Column(Integer, ForeignKey("account_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    reversed_by = Column(String(100), nullable=True)
    reversed_at = Column(DateTime, nullable=True)
    reversal_reason = Column(String(255), nullable=True)

    category = relationship("AccountCategory", back_populates="transactions")
    academic_year = relationship("AcademicYear")
    reversed_original = relationship("AccountTransaction", remote_side="AccountTransaction.id", foreign_keys=[reversal_of_id])

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_account_tx_amount_pos"),
        Index("idx_account_tx_type_date", "type", "transaction_date"),
        Index("idx_account_tx_status_date", "status", "transaction_date"),
    )

    def __repr__(self):
        return f"<AccountTransaction(voucher='{self.voucher_no}', type='{self.type}', amount={self.amount}, status='{self.status}')>"


class AccountBudget(Base, TimestampMixin, SoftDeleteMixin):
    """
    Institutional budget allocations by AccountCategory, fiscal year, and period.
    """
    __tablename__ = "account_budgets"

    budget_code = Column(String(50), unique=True, nullable=False, index=True)  # BDG-2026-0001
    title = Column(String(140), nullable=False)
    fiscal_year = Column(Integer, nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("account_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    period_type = Column(String(20), default="Annual", nullable=False)  # Annual, Quarterly, Monthly
    period_month = Column(Integer, nullable=True)
    allocated_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    alert_threshold_pct = Column(Numeric(5, 2, asdecimal=False), nullable=False, default=80.0)
    status = Column(String(20), default="Active", nullable=False, index=True)  # Active, Closed, Draft
    created_by = Column(String(100), default="admin", nullable=False)
    approved_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    category = relationship("AccountCategory", back_populates="budgets")
    academic_year = relationship("AcademicYear")

    __table_args__ = (
        CheckConstraint("allocated_amount >= 0", name="ck_account_budget_amt_nonneg"),
    )

    def __repr__(self):
        return f"<AccountBudget(code='{self.budget_code}', title='{self.title}', allocated={self.allocated_amount})>"


class FinancialAuditLog(Base):
    """
    Tamper-evident financial audit trail capturing every billing, payment, waiver,
    advance wallet, refund, cancellation, accounting voucher, reversal, and budget event.
    """
    __tablename__ = "financial_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    module = Column(String(30), nullable=False, index=True)  # FEES, ACCOUNTING, BUDGET
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    reference_no = Column(String(80), nullable=True, index=True)
    action = Column(String(60), nullable=False, index=True)
    amount = Column(Numeric(12, 2, asdecimal=False), nullable=True)
    before_snapshot = Column(Text, nullable=True)
    after_snapshot = Column(Text, nullable=True)
    reason = Column(String(255), nullable=True)
    actor_username = Column(String(100), nullable=False, default="system", index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    def __repr__(self):
        return f"<FinancialAuditLog(module='{self.module}', action='{self.action}', ref='{self.reference_no}')>"


def _prevent_accounting_delete(mapper, connection, target):
    raise ValueError(
        f"Permanent deletion of {type(target).__name__} is prohibited by financial audit policy. "
        f"Use voucher reversal instead."
    )


for _immutable_acc_model in (AccountTransaction, FinancialAuditLog):
    event.listen(_immutable_acc_model, "before_delete", _prevent_accounting_delete)
