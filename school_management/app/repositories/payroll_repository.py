"""
EduManage Pro - Enterprise Payroll Repository
Data access & non-destructive query layer for Salary Structures, Loans/Advances,
Monthly Payroll Runs, Payslips, Loan Repayments, Employee Payment History, and Reversals.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.payroll import (
    EmployeeLoan,
    PayrollLoanRepayment,
    PayrollPayslip,
    PayrollPeriodRun,
    PayrollReversal,
    PayrollStructure,
)


class PayrollRepository:
    # ------------------------------------------------------------------
    # Salary Structures
    # ------------------------------------------------------------------
    @staticmethod
    def get_active_structure(
        db: Session, employee_type: str, employee_pk: int
    ) -> Optional[PayrollStructure]:
        etype = (employee_type or "").strip().lower()
        q = db.query(PayrollStructure).filter(
            PayrollStructure.is_deleted == False,
            PayrollStructure.is_active == True,
            PayrollStructure.employee_type == etype,
        )
        if etype == "teacher":
            q = q.filter(PayrollStructure.teacher_id == employee_pk)
        else:
            q = q.filter(PayrollStructure.staff_id == employee_pk)
        return q.order_by(PayrollStructure.effective_from.desc(), PayrollStructure.id.desc()).first()

    @staticmethod
    def list_structures(
        db: Session,
        active_only: bool = True,
        employee_type: Optional[str] = None,
    ) -> List[PayrollStructure]:
        q = (
            db.query(PayrollStructure)
            .options(joinedload(PayrollStructure.teacher), joinedload(PayrollStructure.staff))
            .filter(PayrollStructure.is_deleted == False)
        )
        if active_only:
            q = q.filter(PayrollStructure.is_active == True)
        if employee_type and employee_type.lower() in ("teacher", "staff"):
            q = q.filter(PayrollStructure.employee_type == employee_type.lower())
        return q.order_by(PayrollStructure.employee_type.asc(), PayrollStructure.id.desc()).all()

    @staticmethod
    def count_structures_for_employee(
        db: Session, employee_type: str, employee_pk: int
    ) -> int:
        etype = employee_type.strip().lower()
        q = db.query(func.count(PayrollStructure.id)).filter(PayrollStructure.employee_type == etype)
        if etype == "teacher":
            q = q.filter(PayrollStructure.teacher_id == employee_pk)
        else:
            q = q.filter(PayrollStructure.staff_id == employee_pk)
        return int(q.scalar() or 0)

    # ------------------------------------------------------------------
    # Loans & Advances
    # ------------------------------------------------------------------
    @staticmethod
    def list_loans(
        db: Session,
        employee_type: Optional[str] = None,
        employee_pk: Optional[int] = None,
        status: Optional[str] = None,
        loan_type: Optional[str] = None,
    ) -> List[EmployeeLoan]:
        q = (
            db.query(EmployeeLoan)
            .options(joinedload(EmployeeLoan.teacher), joinedload(EmployeeLoan.staff))
            .filter(EmployeeLoan.is_deleted == False)
        )
        if employee_type and employee_type.lower() in ("teacher", "staff"):
            etype = employee_type.lower()
            q = q.filter(EmployeeLoan.employee_type == etype)
            if employee_pk is not None:
                if etype == "teacher":
                    q = q.filter(EmployeeLoan.teacher_id == employee_pk)
                else:
                    q = q.filter(EmployeeLoan.staff_id == employee_pk)
        if status and status != "All":
            q = q.filter(EmployeeLoan.status == status)
        if loan_type and loan_type != "All":
            q = q.filter(EmployeeLoan.loan_type == loan_type)
        return q.order_by(EmployeeLoan.issue_date.desc(), EmployeeLoan.id.desc()).all()

    @staticmethod
    def get_due_active_loans(
        db: Session,
        employee_type: str,
        employee_pk: int,
        payroll_year: int,
        payroll_month: int,
    ) -> List[EmployeeLoan]:
        etype = employee_type.strip().lower()
        q = db.query(EmployeeLoan).filter(
            EmployeeLoan.is_deleted == False,
            EmployeeLoan.status == "Active",
            EmployeeLoan.remaining_balance > 0,
            EmployeeLoan.employee_type == etype,
            (
                (EmployeeLoan.repayment_start_year < payroll_year)
                | (
                    (EmployeeLoan.repayment_start_year == payroll_year)
                    & (EmployeeLoan.repayment_start_month <= payroll_month)
                )
            ),
        )
        if etype == "teacher":
            q = q.filter(EmployeeLoan.teacher_id == employee_pk)
        else:
            q = q.filter(EmployeeLoan.staff_id == employee_pk)
        return q.order_by(EmployeeLoan.issue_date.asc(), EmployeeLoan.id.asc()).all()

    # ------------------------------------------------------------------
    # Payroll Period Runs & Payslips
    # ------------------------------------------------------------------
    @staticmethod
    def list_period_runs(db: Session, year: Optional[int] = None) -> List[PayrollPeriodRun]:
        q = db.query(PayrollPeriodRun).filter(PayrollPeriodRun.is_deleted == False)
        if year is not None:
            q = q.filter(PayrollPeriodRun.payroll_year == year)
        return q.order_by(
            PayrollPeriodRun.payroll_year.desc(),
            PayrollPeriodRun.payroll_month.desc(),
            PayrollPeriodRun.revision_no.desc(),
        ).all()

    @staticmethod
    def get_run_by_id(db: Session, run_id: int) -> Optional[PayrollPeriodRun]:
        return (
            db.query(PayrollPeriodRun)
            .options(
                joinedload(PayrollPeriodRun.payslips).joinedload(PayrollPayslip.accounting_tx),
                joinedload(PayrollPeriodRun.reversals),
            )
            .filter(PayrollPeriodRun.id == run_id, PayrollPeriodRun.is_deleted == False)
            .first()
        )

    @staticmethod
    def get_active_period_run(
        db: Session, year: int, month: int, run_type: str = "Monthly"
    ) -> Optional[PayrollPeriodRun]:
        return (
            db.query(PayrollPeriodRun)
            .filter(
                PayrollPeriodRun.is_deleted == False,
                PayrollPeriodRun.payroll_year == year,
                PayrollPeriodRun.payroll_month == month,
                PayrollPeriodRun.run_type == run_type,
                PayrollPeriodRun.status != "Reversed",
            )
            .order_by(PayrollPeriodRun.revision_no.desc())
            .first()
        )

    @staticmethod
    def get_payslip_by_id(db: Session, payslip_id: int) -> Optional[PayrollPayslip]:
        return (
            db.query(PayrollPayslip)
            .options(
                joinedload(PayrollPayslip.payroll_run),
                joinedload(PayrollPayslip.teacher),
                joinedload(PayrollPayslip.staff),
                joinedload(PayrollPayslip.accounting_tx),
                joinedload(PayrollPayslip.loan_repayments).joinedload(PayrollLoanRepayment.loan),
            )
            .filter(PayrollPayslip.id == payslip_id, PayrollPayslip.is_deleted == False)
            .first()
        )

    @staticmethod
    def list_payslips(
        db: Session,
        run_id: Optional[int] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        employee_type: Optional[str] = None,
        employee_pk: Optional[int] = None,
        payment_status: Optional[str] = None,
    ) -> List[PayrollPayslip]:
        q = (
            db.query(PayrollPayslip)
            .options(
                joinedload(PayrollPayslip.payroll_run),
                joinedload(PayrollPayslip.accounting_tx),
            )
            .filter(PayrollPayslip.is_deleted == False)
        )
        if run_id is not None:
            q = q.filter(PayrollPayslip.payroll_run_id == run_id)
        if year is not None:
            q = q.filter(PayrollPayslip.payroll_year == year)
        if month is not None:
            q = q.filter(PayrollPayslip.payroll_month == month)
        if employee_type and employee_type.lower() in ("teacher", "staff"):
            etype = employee_type.lower()
            q = q.filter(PayrollPayslip.employee_type == etype)
            if employee_pk is not None:
                if etype == "teacher":
                    q = q.filter(PayrollPayslip.teacher_id == employee_pk)
                else:
                    q = q.filter(PayrollPayslip.staff_id == employee_pk)
        if payment_status and payment_status != "All":
            q = q.filter(PayrollPayslip.payment_status == payment_status)
        return q.order_by(
            PayrollPayslip.payroll_year.desc(),
            PayrollPayslip.payroll_month.desc(),
            PayrollPayslip.id.asc(),
        ).all()

    @staticmethod
    def list_reversals(db: Session, run_id: Optional[int] = None) -> List[PayrollReversal]:
        q = db.query(PayrollReversal).options(
            joinedload(PayrollReversal.payroll_run),
            joinedload(PayrollReversal.payslip),
            joinedload(PayrollReversal.accounting_reversal_tx),
        )
        if run_id is not None:
            q = q.filter(PayrollReversal.payroll_run_id == run_id)
        return q.order_by(PayrollReversal.created_at.desc(), PayrollReversal.id.desc()).all()

    # ------------------------------------------------------------------
    # Deletion Prevention Guards
    # ------------------------------------------------------------------
    @staticmethod
    def delete_payroll_run(*_args: Any, **_kwargs: Any) -> None:
        raise ValueError("Permanent deletion of PayrollPeriodRun is prohibited. Use audit-safe reversal.")

    @staticmethod
    def delete_payslip(*_args: Any, **_kwargs: Any) -> None:
        raise ValueError("Permanent deletion of PayrollPayslip is prohibited. Use audit-safe reversal.")

    @staticmethod
    def delete_loan(*_args: Any, **_kwargs: Any) -> None:
        raise ValueError("Permanent deletion of EmployeeLoan is prohibited. Use audit-safe reversal.")
