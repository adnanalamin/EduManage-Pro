"""
EduManage Pro - Accounting & Expense Management Models
Defines AccountCategory and AccountTransaction for school cash book, vouchers, and P&L.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, Date, Text, ForeignKey, Numeric, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


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

    def __repr__(self):
        return f"<AccountCategory(name='{self.name}', type='{self.type}', code='{self.code}')>"


class AccountTransaction(Base, TimestampMixin, SoftDeleteMixin):
    """
    Individual debit/credit voucher recording financial income or expenditure.
    """
    __tablename__ = "account_transactions"

    voucher_no = Column(String(50), unique=True, nullable=False, index=True)
    idempotency_key = Column(String(64), unique=True, nullable=True, index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    type = Column(String(20), nullable=False, index=True)  # 'Income' | 'Expense'
    category_id = Column(Integer, ForeignKey("account_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    payment_method = Column(String(30), nullable=False, default="Cash")  # 'Cash' | 'Bank' | 'bKash' | 'Cheque'
    reference_no = Column(String(100), nullable=True, index=True)
    paid_to_received_from = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    recorded_by = Column(String(100), nullable=False, default="Accountant")
    status = Column(String(20), nullable=False, default="Approved", index=True)  # 'Approved' | 'Pending' | 'Cancelled'

    category = relationship("AccountCategory", back_populates="transactions")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_account_tx_amount_pos"),
        Index("idx_account_tx_type_date", "type", "transaction_date"),
        Index("idx_account_tx_status_date", "status", "transaction_date"),
    )

    def __repr__(self):
        return f"<AccountTransaction(voucher='{self.voucher_no}', type='{self.type}', amount={self.amount})>"
