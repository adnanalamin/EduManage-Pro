"""
EduManage Pro - Accounting & Expense Management Models
Defines AccountCategory and AccountTransaction for school cash book, vouchers, and P&L.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin


class AccountCategory(Base, TimestampMixin):
    """
    Chart of accounts categories classified into Income or Expense heads.
    """
    __tablename__ = "account_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(20), unique=True, nullable=False)
    type = Column(String(20), nullable=False)  # 'Income' | 'Expense'
    description = Column(String(255), nullable=True)
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    transactions = relationship("AccountTransaction", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AccountCategory(name='{self.name}', type='{self.type}', code='{self.code}')>"


class AccountTransaction(Base, TimestampMixin):
    """
    Individual debit/credit voucher recording financial income or expenditure.
    """
    __tablename__ = "account_transactions"

    id = Column(Integer, primary_key=True, index=True)
    voucher_no = Column(String(50), unique=True, nullable=False, index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    type = Column(String(20), nullable=False, index=True)  # 'Income' | 'Expense'
    category_id = Column(Integer, ForeignKey("account_categories.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(30), nullable=False, default="Cash")  # 'Cash' | 'Bank' | 'bKash' | 'Cheque'
    reference_no = Column(String(100), nullable=True)  # Cheque number, TrxID, Bank voucher #
    paid_to_received_from = Column(String(150), nullable=False)  # Payer or Beneficiary
    description = Column(Text, nullable=True)
    recorded_by = Column(String(100), nullable=False, default="Accountant")
    status = Column(String(20), nullable=False, default="Approved")  # 'Approved' | 'Pending' | 'Cancelled'

    category = relationship("AccountCategory", back_populates="transactions")

    def __repr__(self):
        return f"<AccountTransaction(voucher='{self.voucher_no}', type='{self.type}', amount={self.amount})>"
