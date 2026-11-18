"""
EduManage Pro - Enterprise Payroll ORM Models
Covers:
- PayrollStructure: Salary components (Basic, Allowances, PF/Insurance, Overtime rate, Tax/TIN, Attendance & Leave deduction rules)
- EmployeeLoan: Staff & Teacher Loans and Salary Advances with installment tracking & accounting voucher link
- PayrollLoanRepayment: Per-payslip loan/advance recovery ledger (with reversal tracking)
- PayrollPeriodRun: Monthly payroll batch runs with Draft -> Finalized/Locked -> Paid -> Reversed lifecycle
- PayrollPayslip: Immutable-once-locked individual employee monthly payslips with full earnings/deductions snapshot
- PayrollReversal: Audit-safe compensating reversal & correction log linked to Accounting contra-vouchers
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
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.base import PublicIdMixin, SoftDeleteMixin, TimestampMixin, utc_now


class PayrollPeriodStatus:
    DRAFT = "Draft"
    FINALIZED = "Finalized"
    LOCKED = "Locked"
    PAID = "Paid"
    PARTIALLY_REVERSED = "Partially Reversed"
    REVERSED = "Reversed"

    LOCKED_STATES = (FINALIZED, LOCKED, PAID, PARTIALLY_REVERSED, REVERSED)
    ALL = (DRAFT, FINALIZED, LOCKED, PAID, PARTIALLY_REVERSED, REVERSED)


class PayrollStructure(Base, PublicIdMixin, TimestampMixin, SoftDeleteMixin):
    """
    Configured compensation structure & statutory/deduction policy for a Teacher or Staff member.
    Supports effective dates and maintains historical structure snapshots.
    """

    __tablename__ = "payroll_structures"

    structure_code = Column(String(40), unique=True, nullable=False, index=True)  # STR-EMP-0001-V1
    employee_type = Column(String(20), nullable=False, index=True)  # "teacher" | "staff"
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="RESTRICT"), nullable=True, index=True)

    effective_from = Column(Date, nullable=False, index=True)
    effective_to = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    pay_basis = Column(String(20), default="Monthly", nullable=False)  # Monthly | Contract

    # Core Earnings
    basic_salary = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    house_rent_allowance = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    medical_allowance = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    transport_allowance = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    special_allowance = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    other_allowance = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    overtime_hourly_rate = Column(Numeric(10, 2, asdecimal=False), nullable=False, default=0.0)

    # Recurring Statutory & Fixed Deductions
    provident_fund_pct = Column(Numeric(5, 2, asdecimal=False), nullable=False, default=0.0)
    provident_fund_fixed = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    insurance_deduction = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    other_fixed_deduction = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)

    # Tax / TIN Fields
    tax_tin = Column(String(60), nullable=True, index=True)
    tax_category = Column(String(40), default="Standard", nullable=False)  # Standard | Exempt | Reduced
    tax_rate_pct = Column(Numeric(5, 2, asdecimal=False), nullable=False, default=0.0)
    monthly_tax_deduction = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)

    # Attendance & Leave Deduction Policies
    working_days_per_month = Column(Integer, nullable=False, default=26)  # 0 => calendar days of month
    deduct_for_absent = Column(Boolean, default=True, nullable=False)
    late_days_per_absent = Column(Integer, nullable=False, default=3)  # e.g., 3 late days = 1 absent day; 0 = disabled
    deduct_unpaid_leave = Column(Boolean, default=True, nullable=False)
    monthly_paid_leave_quota = Column(Integer, nullable=False, default=2)

    # Disbursement Preference
    payment_method = Column(String(30), default="Bank", nullable=False)  # Cash, Bank, Card, Mobile Banking, Other
    bank_name = Column(String(120), nullable=True)
    bank_account_no = Column(String(80), nullable=True)

    notes = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=False, default="admin")

    teacher = relationship("Teacher", foreign_keys=[teacher_id])
    staff = relationship("Staff", foreign_keys=[staff_id])
    payslips = relationship("PayrollPayslip", back_populates="structure")

    __table_args__ = (
        CheckConstraint(
            "(teacher_id IS NOT NULL AND staff_id IS NULL) OR (teacher_id IS NULL AND staff_id IS NOT NULL)",
            name="ck_payroll_structure_single_emp",
        ),
        CheckConstraint("basic_salary >= 0", name="ck_payroll_struct_basic_nonneg"),
        CheckConstraint("working_days_per_month >= 0 AND working_days_per_month <= 31", name="ck_payroll_struct_wdays"),
    )

    @property
    def total_allowances(self) -> float:
        return round(
            float(self.house_rent_allowance or 0.0)
            + float(self.medical_allowance or 0.0)
            + float(self.transport_allowance or 0.0)
            + float(self.special_allowance or 0.0)
            + float(self.other_allowance or 0.0),
            2,
        )

    @property
    def base_gross_salary(self) -> float:
        return round(float(self.basic_salary or 0.0) + self.total_allowances, 2)

    @property
    def computed_pf_amount(self) -> float:
        pct = float(self.provident_fund_pct or 0.0)
        fixed = float(self.provident_fund_fixed or 0.0)
        if pct > 0:
            return round((float(self.basic_salary or 0.0) * pct / 100.0) + fixed, 2)
        return round(fixed, 2)

    def __repr__(self):
        return f"<PayrollStructure(code='{self.structure_code}', basic={self.basic_salary}, active={self.is_active})>"


class EmployeeLoan(Base, PublicIdMixin, TimestampMixin, SoftDeleteMixin):
    """
    Tracks Employee Loans & Salary Advances disbursed to Teachers or Staff members.
    Never permanently deleted; reversed entries remain audited.
    """

    __tablename__ = "payroll_loans"

    loan_code = Column(String(40), unique=True, nullable=False, index=True)  # LON-2026-0001 / ADV-SAL-2026-0001
    loan_type = Column(String(20), nullable=False, default="Loan", index=True)  # "Loan" | "Advance"
    employee_type = Column(String(20), nullable=False, index=True)  # "teacher" | "staff"
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="RESTRICT"), nullable=True, index=True)

    issue_date = Column(Date, nullable=False, index=True)
    repayment_start_year = Column(Integer, nullable=False, index=True)
    repayment_start_month = Column(Integer, nullable=False, index=True)

    principal_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    monthly_installment = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    total_repaid = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    remaining_balance = Column(Numeric(12, 2, asdecimal=False), nullable=False)

    disbursement_method = Column(String(30), nullable=False, default="Bank")
    channel_detail = Column(String(80), nullable=True)
    reason = Column(String(255), nullable=False)
    status = Column(String(25), nullable=False, default="Active", index=True)  # Active | Settled | Reversed

    accounting_tx_id = Column(Integer, ForeignKey("account_transactions.id", ondelete="RESTRICT"), nullable=True, index=True)
    issued_by = Column(String(100), nullable=False, default="admin")
    approved_by = Column(String(100), nullable=True)
    reversed_by = Column(String(100), nullable=True)
    reversed_at = Column(DateTime(timezone=True), nullable=True)
    reversal_reason = Column(String(255), nullable=True)

    teacher = relationship("Teacher", foreign_keys=[teacher_id])
    staff = relationship("Staff", foreign_keys=[staff_id])
    accounting_tx = relationship("AccountTransaction", foreign_keys=[accounting_tx_id])
    repayments = relationship("PayrollLoanRepayment", back_populates="loan", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "(teacher_id IS NOT NULL AND staff_id IS NULL) OR (teacher_id IS NULL AND staff_id IS NOT NULL)",
            name="ck_payroll_loan_single_emp",
        ),
        CheckConstraint("principal_amount > 0", name="ck_payroll_loan_principal_pos"),
        CheckConstraint("monthly_installment > 0", name="ck_payroll_loan_inst_pos"),
        CheckConstraint("remaining_balance >= 0", name="ck_payroll_loan_rem_nonneg"),
    )

    def __repr__(self):
        return f"<EmployeeLoan(code='{self.loan_code}', type='{self.loan_type}', rem={self.remaining_balance}, status='{self.status}')>"


class PayrollPeriodRun(Base, PublicIdMixin, TimestampMixin, SoftDeleteMixin):
    """
    Monthly payroll batch run with strict locking semantics.
    Once `is_locked` is True (Finalized / Locked / Paid / Reversed), payslips cannot be modified or regenerated.
    """

    __tablename__ = "payroll_period_runs"

    run_code = Column(String(40), unique=True, nullable=False, index=True)  # PAY-2026-03
    payroll_year = Column(Integer, nullable=False, index=True)
    payroll_month = Column(Integer, nullable=False, index=True)
    run_type = Column(String(20), nullable=False, default="Monthly", index=True)  # Monthly | Bonus | Adjustment
    revision_no = Column(Integer, nullable=False, default=1)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True)

    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(String(30), nullable=False, default=PayrollPeriodStatus.DRAFT, index=True)
    is_locked = Column(Boolean, default=False, nullable=False, index=True)

    total_employees = Column(Integer, nullable=False, default=0)
    total_gross = Column(Numeric(14, 2, asdecimal=False), nullable=False, default=0.0)
    total_deductions = Column(Numeric(14, 2, asdecimal=False), nullable=False, default=0.0)
    total_tax = Column(Numeric(14, 2, asdecimal=False), nullable=False, default=0.0)
    total_net_payable = Column(Numeric(14, 2, asdecimal=False), nullable=False, default=0.0)
    total_paid_amount = Column(Numeric(14, 2, asdecimal=False), nullable=False, default=0.0)

    generated_by = Column(String(100), nullable=False, default="admin")
    finalized_by = Column(String(100), nullable=True)
    finalized_at = Column(DateTime(timezone=True), nullable=True)
    locked_by = Column(String(100), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    reversed_by = Column(String(100), nullable=True)
    reversed_at = Column(DateTime(timezone=True), nullable=True)
    reversal_reason = Column(String(255), nullable=True)

    notes = Column(Text, nullable=True)

    academic_year = relationship("AcademicYear", foreign_keys=[academic_year_id])
    payslips = relationship("PayrollPayslip", back_populates="payroll_run", order_by="PayrollPayslip.id")
    reversals = relationship("PayrollReversal", back_populates="payroll_run", order_by="PayrollReversal.id")

    __table_args__ = (
        CheckConstraint("payroll_month >= 1 AND payroll_month <= 12", name="ck_payroll_run_month"),
        UniqueConstraint("payroll_year", "payroll_month", "run_type", "revision_no", name="uq_payroll_period_revision"),
        Index("idx_payroll_period_ym_status", "payroll_year", "payroll_month", "status"),
    )

    @property
    def period_label(self) -> str:
        from calendar import month_name

        mname = month_name[self.payroll_month] if 1 <= (self.payroll_month or 0) <= 12 else str(self.payroll_month)
        return f"{mname} {self.payroll_year}"

    def __repr__(self):
        return f"<PayrollPeriodRun(code='{self.run_code}', status='{self.status}', locked={self.is_locked})>"


class PayrollPayslip(Base, PublicIdMixin, TimestampMixin, SoftDeleteMixin):
    """
    Individual employee monthly payslip storing complete immutable calculation snapshot:
    - Basic Salary & Itemized Allowances
    - Overtime Hours & Amount + Bonus Amount & Reason
    - Attendance Metrics (Present, Late, Absent, Attendance Deduction)
    - Leave Metrics (Paid Leave, Unpaid Leave, Leave Deduction)
    - Provident Fund, Insurance, Income Tax (TDS/TIN), Loan & Advance Recoveries
    - Accounting Voucher Link & Audit-Safe Reversal Metadata
    """

    __tablename__ = "payroll_payslips"

    slip_no = Column(String(50), unique=True, nullable=False, index=True)  # SLP-202603-0001
    payroll_run_id = Column(Integer, ForeignKey("payroll_period_runs.id", ondelete="RESTRICT"), nullable=False, index=True)
    structure_id = Column(Integer, ForeignKey("payroll_structures.id", ondelete="RESTRICT"), nullable=True, index=True)

    employee_type = Column(String(20), nullable=False, index=True)  # "teacher" | "staff"
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="RESTRICT"), nullable=True, index=True)

    # Snapshot descriptors (remain historically accurate even if employee changes department/title later)
    employee_code = Column(String(40), nullable=False, index=True)
    employee_name = Column(String(150), nullable=False)
    designation = Column(String(100), nullable=True)
    department_name = Column(String(100), nullable=True)
    tax_tin = Column(String(60), nullable=True)

    payroll_year = Column(Integer, nullable=False, index=True)
    payroll_month = Column(Integer, nullable=False, index=True)

    # Earnings
    basic_salary = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    house_rent_allowance = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    medical_allowance = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    transport_allowance = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    special_allowance = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    other_allowance = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    overtime_hours = Column(Numeric(8, 2, asdecimal=False), nullable=False, default=0.0)
    overtime_rate = Column(Numeric(10, 2, asdecimal=False), nullable=False, default=0.0)
    overtime_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    bonus_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    bonus_reason = Column(String(200), nullable=True)
    gross_earnings = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)

    # Attendance & Leave Snapshot
    working_days = Column(Integer, nullable=False, default=26)
    present_days = Column(Integer, nullable=False, default=0)
    late_days = Column(Integer, nullable=False, default=0)
    absent_days = Column(Numeric(6, 2, asdecimal=False), nullable=False, default=0.0)
    paid_leave_days = Column(Numeric(6, 2, asdecimal=False), nullable=False, default=0.0)
    unpaid_leave_days = Column(Numeric(6, 2, asdecimal=False), nullable=False, default=0.0)

    # Deductions
    attendance_deduction = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    leave_deduction = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    provident_fund_deduction = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    insurance_deduction = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    tax_deduction = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    loan_deduction = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    advance_deduction = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    other_deduction = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    other_deduction_reason = Column(String(200), nullable=True)
    total_deductions = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)

    net_payable = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)

    # Disbursement & Accounting Linkage
    payment_method = Column(String(30), nullable=False, default="Bank")
    channel_detail = Column(String(120), nullable=True)
    bank_name = Column(String(120), nullable=True)
    bank_account_no = Column(String(80), nullable=True)
    payment_status = Column(String(25), nullable=False, default=PayrollPeriodStatus.DRAFT, index=True)  # Draft | Finalized | Paid | Reversed
    paid_date = Column(Date, nullable=True, index=True)
    paid_by = Column(String(100), nullable=True)
    accounting_tx_id = Column(Integer, ForeignKey("account_transactions.id", ondelete="RESTRICT"), nullable=True, index=True)

    # Reversal Metadata
    is_reversed = Column(Boolean, default=False, nullable=False, index=True)
    reversed_by = Column(String(100), nullable=True)
    reversed_at = Column(DateTime(timezone=True), nullable=True)
    reversal_reason = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    payroll_run = relationship("PayrollPeriodRun", back_populates="payslips")
    structure = relationship("PayrollStructure", back_populates="payslips")
    teacher = relationship("Teacher", foreign_keys=[teacher_id])
    staff = relationship("Staff", foreign_keys=[staff_id])
    accounting_tx = relationship("AccountTransaction", foreign_keys=[accounting_tx_id])
    loan_repayments = relationship("PayrollLoanRepayment", back_populates="payslip")
    reversals = relationship("PayrollReversal", back_populates="payslip")

    __table_args__ = (
        CheckConstraint(
            "(teacher_id IS NOT NULL AND staff_id IS NULL) OR (teacher_id IS NULL AND staff_id IS NOT NULL)",
            name="ck_payroll_payslip_single_emp",
        ),
        CheckConstraint("gross_earnings >= 0 AND total_deductions >= 0 AND net_payable >= 0", name="ck_payroll_payslip_nonneg"),
        UniqueConstraint("payroll_run_id", "employee_type", "employee_code", name="uq_payroll_run_employee"),
        Index("idx_payroll_slip_emp_ym", "employee_type", "payroll_year", "payroll_month"),
    )

    @property
    def total_allowances(self) -> float:
        return round(
            float(self.house_rent_allowance or 0.0)
            + float(self.medical_allowance or 0.0)
            + float(self.transport_allowance or 0.0)
            + float(self.special_allowance or 0.0)
            + float(self.other_allowance or 0.0),
            2,
        )

    def __repr__(self):
        return f"<PayrollPayslip(slip='{self.slip_no}', emp='{self.employee_name}', net={self.net_payable}, status='{self.payment_status}')>"


class PayrollLoanRepayment(Base, PublicIdMixin, TimestampMixin):
    """
    Links an installment deducted on a PayrollPayslip back to its EmployeeLoan / Advance.
    Tracks whether the deduction has been applied (upon disbursement) or reversed.
    """

    __tablename__ = "payroll_loan_repayments"

    loan_id = Column(Integer, ForeignKey("payroll_loans.id", ondelete="RESTRICT"), nullable=False, index=True)
    payslip_id = Column(Integer, ForeignKey("payroll_payslips.id", ondelete="RESTRICT"), nullable=False, index=True)
    repayment_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    status = Column(String(20), nullable=False, default="Scheduled", index=True)  # Scheduled | Applied | Reversed
    reversed_by = Column(String(100), nullable=True)
    reversed_at = Column(DateTime(timezone=True), nullable=True)

    loan = relationship("EmployeeLoan", back_populates="repayments")
    payslip = relationship("PayrollPayslip", back_populates="loan_repayments")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payroll_repay_amt_pos"),
    )

    def __repr__(self):
        return f"<PayrollLoanRepayment(loan_id={self.loan_id}, payslip_id={self.payslip_id}, amt={self.amount}, status='{self.status}')>"


class PayrollReversal(Base, PublicIdMixin, TimestampMixin):
    """
    Audit-safe reversal & correction register for finalized/locked/paid payroll entries.
    Preserves original records intact while documenting compensating Accounting contra-vouchers
    and loan/balance reinstatements.
    """

    __tablename__ = "payroll_reversals"

    reversal_no = Column(String(50), unique=True, nullable=False, index=True)  # PREV-2026-00001
    payroll_run_id = Column(Integer, ForeignKey("payroll_period_runs.id", ondelete="RESTRICT"), nullable=False, index=True)
    payslip_id = Column(Integer, ForeignKey("payroll_payslips.id", ondelete="RESTRICT"), nullable=True, index=True)
    reversal_scope = Column(String(25), nullable=False, default="Payslip", index=True)  # Payslip | PeriodRun | Loan

    original_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    reversed_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False, default=0.0)
    reason = Column(String(255), nullable=False)
    authorized_by = Column(String(100), nullable=False)
    reversal_date = Column(Date, nullable=False, index=True)
    accounting_reversal_tx_id = Column(Integer, ForeignKey("account_transactions.id", ondelete="RESTRICT"), nullable=True, index=True)

    payroll_run = relationship("PayrollPeriodRun", back_populates="reversals")
    payslip = relationship("PayrollPayslip", back_populates="reversals")
    accounting_reversal_tx = relationship("AccountTransaction", foreign_keys=[accounting_reversal_tx_id])

    def __repr__(self):
        return f"<PayrollReversal(no='{self.reversal_no}', scope='{self.reversal_scope}', amt={self.reversed_amount})>"


def _prevent_payroll_hard_delete(mapper, connection, target):
    raise ValueError(
        f"Permanent deletion of {type(target).__name__} is prohibited by payroll & financial audit policy. "
        f"Use audit-safe payroll reversal procedures instead."
    )


for _immutable_payroll_model in (
    PayrollPeriodRun,
    PayrollPayslip,
    EmployeeLoan,
    PayrollLoanRepayment,
    PayrollReversal,
):
    event.listen(_immutable_payroll_model, "before_delete", _prevent_payroll_hard_delete)
