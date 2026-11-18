"""
EduManage Pro - Enterprise Payroll Processing, Compensation & Accounting Integration Service
Covers:
- Salary Structure Management (Basic Salary, Allowances, Overtime Rate, PF/Insurance, Tax/TIN, Attendance & Leave Policy)
- Employee Loans & Salary Advances (Issuance with Accounting Voucher, Auto-Recovery Installments, Reinstatement on Reversal)
- Attendance & Unpaid Leave Deduction Engine (Derived from TeacherAttendance, StaffAttendance & EmployeeLeaveRequest)
- Monthly Payroll Batch Generation (Teachers + Staff, Variable Overtime/Bonuses/Extra Deductions)
- Finalized Payroll Period Locking (Strict immutability once Finalized/Locked/Paid)
- Salary Disbursement Integration with School Accounting (EXP-TSAL / EXP-SSAL Vouchers + FinancialAuditLog)
- Audit-Safe Reversal Procedures (Non-destructive contra-entries, Loan restoration, PayrollReversal log)
- Payroll Reporting & Excel Export
"""

import calendar
from datetime import date, timedelta
import os
from typing import Any, Dict, List, Optional, Tuple
import uuid

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.logging_config import error_logger
from app.models.academic import AcademicYear
from app.models.attendance import StaffAttendance, TeacherAttendance
from app.models.base import utc_now
from app.models.fee import normalize_payment_channel
from app.models.payroll import (
    EmployeeLoan,
    PayrollLoanRepayment,
    PayrollPayslip,
    PayrollPeriodRun,
    PayrollPeriodStatus,
    PayrollReversal,
    PayrollStructure,
)
from app.models.staff import (
    EmployeeLeaveRequest,
    EmployeeSalaryHistory,
    EmployeeStatus,
    Staff,
    Teacher,
)
from app.models.user import User
from app.repositories.accounting_repository import AccountingRepository
from app.repositories.payroll_repository import PayrollRepository
from app.repositories.staff_repository import StaffRepository
from app.security.session import session as app_session
from app.services.accounting_service import AccountingService
from app.services.database_service import DatabaseService


UNPAID_LEAVE_KEYWORDS = {"unpaid", "lwp", "without pay", "leave without pay"}


class PayrollSecurityGuard:
    """Enforces strict RBAC confidentiality for all Payroll & Compensation operations."""

    @staticmethod
    def resolve_actor(actor_user: Optional[User] = None) -> Optional[User]:
        if actor_user is not None:
            return actor_user
        if app_session.is_authenticated and app_session.current_user is not None:
            return app_session.current_user
        return None

    @staticmethod
    def actor_username(actor_user: Optional[User] = None, fallback: str = "admin") -> str:
        user = PayrollSecurityGuard.resolve_actor(actor_user)
        return user.username if user else fallback

    @staticmethod
    def require_permission(
        permission_code: str,
        actor_user: Optional[User] = None,
        error_msg: Optional[str] = None,
    ) -> None:
        user = PayrollSecurityGuard.resolve_actor(actor_user)
        if user is not None and not user.has_permission(permission_code):
            raise PermissionError(
                error_msg or f"Access denied: missing confidential payroll permission '{permission_code}'."
            )

    @staticmethod
    def can_access_payroll(actor_user: Optional[User] = None) -> bool:
        user = PayrollSecurityGuard.resolve_actor(actor_user)
        if user is None:
            return True
        return user.has_permission(module="PAYROLL", action="VIEW") or user.has_permission("hr.salary.VIEW")


class PayrollService:
    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _emp_filter(employee_type: str, emp_pk: int) -> Dict[str, Any]:
        etype = employee_type.strip().lower()
        return {
            "employee_type": etype,
            "teacher_id": emp_pk if etype == "teacher" else None,
            "staff_id": emp_pk if etype == "staff" else None,
        }

    @staticmethod
    def _employee_identity(employee_type: str, emp: Any) -> Tuple[str, str, str, str]:
        etype = employee_type.strip().lower()
        if etype == "teacher":
            code = emp.teacher_id or emp.employee_id or f"T-{emp.id}"
            role = emp.designation or "Teacher"
        else:
            code = emp.staff_id or emp.employee_id or f"S-{emp.id}"
            role = emp.position or "Staff"
        dept_name = emp.department.name if getattr(emp, "department", None) else "-"
        return code, emp.full_name, role, dept_name

    @staticmethod
    def _ensure_category(db: Session, code: str, fallback_code: str) -> int:
        cat = AccountingRepository.get_category_by_code(db, code)
        if not cat:
            AccountingService.seed_default_categories(db)
            cat = AccountingRepository.get_category_by_code(db, code)
        if not cat:
            cat = AccountingRepository.get_category_by_code(db, fallback_code)
        if not cat:
            raise ValueError(f"Required accounting expense category '{code}' not found.")
        return cat.id

    @staticmethod
    def _recalculate_run_totals(db: Session, run: PayrollPeriodRun) -> None:
        slips = (
            db.query(PayrollPayslip)
            .filter(PayrollPayslip.payroll_run_id == run.id, PayrollPayslip.is_deleted == False)
            .all()
        )
        active_slips = [s for s in slips if not s.is_reversed]
        run.total_employees = len(active_slips)
        run.total_gross = round(sum(float(s.gross_earnings or 0.0) for s in active_slips), 2)
        run.total_deductions = round(sum(float(s.total_deductions or 0.0) for s in active_slips), 2)
        run.total_tax = round(sum(float(s.tax_deduction or 0.0) for s in active_slips), 2)
        run.total_net_payable = round(sum(float(s.net_payable or 0.0) for s in active_slips), 2)
        run.total_paid_amount = round(
            sum(float(s.net_payable or 0.0) for s in active_slips if s.payment_status == "Paid"),
            2,
        )

    @staticmethod
    def _apply_payslip_math(slip: PayrollPayslip) -> None:
        gross = (
            float(slip.basic_salary or 0.0)
            + float(slip.house_rent_allowance or 0.0)
            + float(slip.medical_allowance or 0.0)
            + float(slip.transport_allowance or 0.0)
            + float(slip.special_allowance or 0.0)
            + float(slip.other_allowance or 0.0)
            + float(slip.overtime_amount or 0.0)
            + float(slip.bonus_amount or 0.0)
        )
        deductions = (
            float(slip.attendance_deduction or 0.0)
            + float(slip.leave_deduction or 0.0)
            + float(slip.provident_fund_deduction or 0.0)
            + float(slip.insurance_deduction or 0.0)
            + float(slip.tax_deduction or 0.0)
            + float(slip.loan_deduction or 0.0)
            + float(slip.advance_deduction or 0.0)
            + float(slip.other_deduction or 0.0)
        )
        slip.gross_earnings = round(max(0.0, gross), 2)
        slip.total_deductions = round(max(0.0, deductions), 2)
        slip.net_payable = round(max(0.0, slip.gross_earnings - slip.total_deductions), 2)

    # ------------------------------------------------------------------
    # 1. Salary Structure Management
    # ------------------------------------------------------------------
    @staticmethod
    def upsert_salary_structure(
        db: Session,
        employee_type: str,
        employee_pk: int,
        data: Dict[str, Any],
        sync_employee_salary: bool = True,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[PayrollStructure], str]:
        try:
            PayrollSecurityGuard.require_permission("payroll.structures.EDIT", actor_user)
            etype = (employee_type or "").strip().lower()
            if etype not in ("teacher", "staff"):
                return False, None, "employee_type must be 'teacher' or 'staff'."

            emp = StaffRepository.get_employee(db, etype, employee_pk)
            if not emp:
                return False, None, "Employee not found."

            basic = float(data.get("basic_salary", 0.0) or 0.0)
            if basic < 0:
                return False, None, "Basic salary cannot be negative."

            eff_from = data.get("effective_from") or date.today()
            username = PayrollSecurityGuard.actor_username(actor_user)

            # Deactivate existing active structure cleanly
            prev = PayrollRepository.get_active_structure(db, etype, employee_pk)
            old_basic = float(emp.salary or 0.0)
            if prev:
                old_basic = float(prev.basic_salary or old_basic)
                prev.is_active = False
                prev.effective_to = eff_from - timedelta(days=1) if eff_from > prev.effective_from else eff_from

            version_num = PayrollRepository.count_structures_for_employee(db, etype, employee_pk) + 1
            emp_code = (emp.employee_id or f"{etype[:1].upper()}{emp.id}").replace(" ", "")
            struct_code = data.get("structure_code") or f"STR-{emp_code}-V{version_num}"
            while db.query(PayrollStructure).filter(PayrollStructure.structure_code == struct_code).first():
                struct_code = f"STR-{emp_code}-V{version_num}-{uuid.uuid4().hex[:3].upper()}"

            norm_method, _ = normalize_payment_channel(data.get("payment_method", "Bank"))

            struct = PayrollStructure(
                structure_code=struct_code,
                **PayrollService._emp_filter(etype, emp.id),
                effective_from=eff_from,
                is_active=True,
                pay_basis=data.get("pay_basis", "Monthly"),
                basic_salary=round(basic, 2),
                house_rent_allowance=round(float(data.get("house_rent_allowance", 0.0) or 0.0), 2),
                medical_allowance=round(float(data.get("medical_allowance", 0.0) or 0.0), 2),
                transport_allowance=round(float(data.get("transport_allowance", 0.0) or 0.0), 2),
                special_allowance=round(float(data.get("special_allowance", 0.0) or 0.0), 2),
                other_allowance=round(float(data.get("other_allowance", 0.0) or 0.0), 2),
                overtime_hourly_rate=round(float(data.get("overtime_hourly_rate", 0.0) or 0.0), 2),
                provident_fund_pct=round(float(data.get("provident_fund_pct", 0.0) or 0.0), 2),
                provident_fund_fixed=round(float(data.get("provident_fund_fixed", 0.0) or 0.0), 2),
                insurance_deduction=round(float(data.get("insurance_deduction", 0.0) or 0.0), 2),
                other_fixed_deduction=round(float(data.get("other_fixed_deduction", 0.0) or 0.0), 2),
                tax_tin=(data.get("tax_tin") or "").strip() or None,
                tax_category=data.get("tax_category", "Standard"),
                tax_rate_pct=round(float(data.get("tax_rate_pct", 0.0) or 0.0), 2),
                monthly_tax_deduction=round(float(data.get("monthly_tax_deduction", 0.0) or 0.0), 2),
                working_days_per_month=int(data.get("working_days_per_month", 26)),
                deduct_for_absent=bool(data.get("deduct_for_absent", True)),
                late_days_per_absent=int(data.get("late_days_per_absent", 3)),
                deduct_unpaid_leave=bool(data.get("deduct_unpaid_leave", True)),
                monthly_paid_leave_quota=int(data.get("monthly_paid_leave_quota", 2)),
                payment_method=norm_method,
                bank_name=(data.get("bank_name") or emp.bank_name or "").strip() or None,
                bank_account_no=(data.get("bank_account_no") or emp.bank_account_no or "").strip() or None,
                notes=data.get("notes"),
                created_by=username,
            )
            db.add(struct)
            db.flush()

            if sync_employee_salary:
                emp.salary = int(round(struct.basic_salary))
                if struct.bank_name:
                    emp.bank_name = struct.bank_name
                if struct.bank_account_no:
                    emp.bank_account_no = struct.bank_account_no
                if int(round(old_basic)) != int(round(struct.basic_salary)) or struct.total_allowances > 0:
                    db.add(
                        EmployeeSalaryHistory(
                            **PayrollService._emp_filter(etype, emp.id),
                            previous_salary=int(round(old_basic)),
                            new_salary=int(round(struct.basic_salary)),
                            allowances=int(round(struct.total_allowances)),
                            effective_date=eff_from,
                            change_reason=data.get("change_reason") or f"Payroll Structure {struct_code}",
                            reference_no=struct_code,
                            approved_by=username,
                        )
                    )

            AccountingService.record_audit_log(
                db,
                module="PAYROLL",
                entity_type="PayrollStructure",
                entity_id=struct.id,
                reference_no=struct.structure_code,
                action="PAYROLL_STRUCTURE_SAVED",
                amount=struct.base_gross_salary,
                after_snapshot={
                    "employee": emp.full_name,
                    "basic": float(struct.basic_salary),
                    "allowances": struct.total_allowances,
                    "gross": struct.base_gross_salary,
                    "tax_tin": struct.tax_tin,
                },
                reason=data.get("change_reason") or "Salary Structure Configuration",
                actor_username=username,
                commit=False,
            )
            DatabaseService.log_activity(
                db,
                action="PAYROLL_STRUCTURE_SAVED",
                module="PAYROLL",
                description=f"Configured salary structure '{struct.structure_code}' for '{emp.full_name}' (Gross: {struct.base_gross_salary:,.2f})",
                username=username,
                entity_type="PayrollStructure",
                entity_id=str(struct.id),
                commit=False,
            )
            db.commit()
            db.refresh(struct)
            return True, struct, f"Salary structure '{struct.structure_code}' saved for {emp.full_name}."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Failed saving salary structure: {exc}")
            return False, None, str(exc)

    # ------------------------------------------------------------------
    # 2. Employee Loans & Salary Advances
    # ------------------------------------------------------------------
    @staticmethod
    def issue_loan_or_advance(
        db: Session,
        employee_type: str,
        employee_pk: int,
        data: Dict[str, Any],
        post_to_accounting: bool = True,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[EmployeeLoan], str]:
        try:
            PayrollSecurityGuard.require_permission("payroll.loans.CREATE", actor_user)
            etype = (employee_type or "").strip().lower()
            if etype not in ("teacher", "staff"):
                return False, None, "employee_type must be 'teacher' or 'staff'."

            emp = StaffRepository.get_employee(db, etype, employee_pk)
            if not emp:
                return False, None, "Employee not found."

            loan_type = (data.get("loan_type") or "Loan").strip().title()
            if loan_type not in ("Loan", "Advance"):
                return False, None, "loan_type must be 'Loan' or 'Advance'."

            principal = round(float(data.get("principal_amount", 0.0) or 0.0), 2)
            if principal <= 0:
                return False, None, "Principal amount must be greater than zero."

            default_inst = principal if loan_type == "Advance" else round(principal / 6.0, 2)
            installment = round(float(data.get("monthly_installment") or default_inst), 2)
            if installment <= 0:
                return False, None, "Monthly installment must be greater than zero."
            if installment > principal:
                installment = principal

            issue_dt = data.get("issue_date") or date.today()
            start_year = int(data.get("repayment_start_year") or issue_dt.year)
            start_month = int(data.get("repayment_start_month") or issue_dt.month)
            if not (1 <= start_month <= 12):
                return False, None, "Repayment start month must be between 1 and 12."

            reason = (data.get("reason") or f"{loan_type} disbursement").strip()
            username = PayrollSecurityGuard.actor_username(actor_user)
            norm_method, norm_detail = normalize_payment_channel(
                data.get("disbursement_method", "Bank"), data.get("channel_detail")
            )

            prefix = "ADV-SAL" if loan_type == "Advance" else "LON"
            seq = db.query(func.count(EmployeeLoan.id)).scalar() or 0
            loan_code = f"{prefix}-{issue_dt.year}-{seq + 1:04d}"
            while db.query(EmployeeLoan).filter(EmployeeLoan.loan_code == loan_code).first():
                seq += 1
                loan_code = f"{prefix}-{issue_dt.year}-{seq + 1:04d}"

            acc_tx_id = None
            if post_to_accounting:
                cat_id = PayrollService._ensure_category(
                    db, "EXP-LOAN", "EXP-TSAL" if etype == "teacher" else "EXP-SSAL"
                )
                tx, tx_err = AccountingService.record_transaction(
                    db,
                    {
                        "transaction_date": issue_dt,
                        "type": "Expense",
                        "entry_kind": "PayrollLoan",
                        "category_id": cat_id,
                        "amount": principal,
                        "payment_method": norm_method,
                        "channel_detail": norm_detail,
                        "reference_no": loan_code,
                        "paid_to_received_from": emp.full_name,
                        "description": f"Employee {loan_type} disbursement ({loan_code}): {reason}",
                        "idempotency_key": f"PAYROLL-LOAN-{loan_code}",
                    },
                    actor_username=username,
                    commit=False,
                )
                if tx_err or not tx:
                    db.rollback()
                    return False, None, tx_err or "Failed posting loan accounting voucher."
                acc_tx_id = tx.id

            loan = EmployeeLoan(
                loan_code=loan_code,
                loan_type=loan_type,
                **PayrollService._emp_filter(etype, emp.id),
                issue_date=issue_dt,
                repayment_start_year=start_year,
                repayment_start_month=start_month,
                principal_amount=principal,
                monthly_installment=installment,
                total_repaid=0.0,
                remaining_balance=principal,
                disbursement_method=norm_method,
                channel_detail=norm_detail,
                reason=reason,
                status="Active",
                accounting_tx_id=acc_tx_id,
                issued_by=username,
                approved_by=username,
            )
            db.add(loan)
            db.flush()

            AccountingService.record_audit_log(
                db,
                module="PAYROLL",
                entity_type="EmployeeLoan",
                entity_id=loan.id,
                reference_no=loan.loan_code,
                action=f"PAYROLL_{loan_type.upper()}_ISSUED",
                amount=principal,
                after_snapshot={
                    "loan_code": loan.loan_code,
                    "employee": emp.full_name,
                    "principal": principal,
                    "installment": installment,
                    "accounting_tx_id": acc_tx_id,
                },
                reason=reason,
                actor_username=username,
                commit=False,
            )
            DatabaseService.log_activity(
                db,
                action=f"PAYROLL_{loan_type.upper()}_ISSUED",
                module="PAYROLL",
                description=f"Issued {loan_type} '{loan.loan_code}' of {principal:,.2f} to '{emp.full_name}' (Inst: {installment:,.2f}/mo)",
                username=username,
                entity_type="EmployeeLoan",
                entity_id=str(loan.id),
                commit=False,
            )
            db.commit()
            db.refresh(loan)
            return True, loan, f"{loan_type} '{loan.loan_code}' issued to {emp.full_name}."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error issuing loan/advance: {exc}")
            return False, None, str(exc)

    # ------------------------------------------------------------------
    # 3. Attendance & Leave Deduction Calculation Engine
    # ------------------------------------------------------------------
    @staticmethod
    def calculate_attendance_and_leave_metrics(
        db: Session,
        employee_type: str,
        employee_pk: int,
        year: int,
        month: int,
        basic_salary: float,
        structure: Optional[PayrollStructure] = None,
    ) -> Dict[str, Any]:
        _, days_in_month = calendar.monthrange(year, month)
        period_start = date(year, month, 1)
        period_end = date(year, month, days_in_month)

        etype = employee_type.strip().lower()
        if etype == "teacher":
            att_rows = (
                db.query(TeacherAttendance)
                .filter(
                    TeacherAttendance.teacher_id == employee_pk,
                    TeacherAttendance.date >= period_start,
                    TeacherAttendance.date <= period_end,
                )
                .all()
            )
            leave_q = db.query(EmployeeLeaveRequest).filter(
                EmployeeLeaveRequest.employee_type == "teacher",
                EmployeeLeaveRequest.teacher_id == employee_pk,
                EmployeeLeaveRequest.status == "Approved",
                EmployeeLeaveRequest.start_date <= period_end,
                EmployeeLeaveRequest.end_date >= period_start,
            )
        else:
            att_rows = (
                db.query(StaffAttendance)
                .filter(
                    StaffAttendance.staff_id == employee_pk,
                    StaffAttendance.date >= period_start,
                    StaffAttendance.date <= period_end,
                )
                .all()
            )
            leave_q = db.query(EmployeeLeaveRequest).filter(
                EmployeeLeaveRequest.employee_type == "staff",
                EmployeeLeaveRequest.staff_id == employee_pk,
                EmployeeLeaveRequest.status == "Approved",
                EmployeeLeaveRequest.start_date <= period_end,
                EmployeeLeaveRequest.end_date >= period_start,
            )

        present_days = sum(1 for r in att_rows if r.status == "Present")
        late_days = sum(1 for r in att_rows if r.status == "Late")
        absent_days = sum(1 for r in att_rows if r.status == "Absent")
        att_leave_days = sum(1 for r in att_rows if r.status == "Leave")

        # Count approved overlapping leave requests clipped to month
        paid_leave_days = 0
        unpaid_leave_days = 0
        leave_requests = leave_q.all()
        counted_leave_dates = set()
        for lr in leave_requests:
            cur = max(lr.start_date, period_start)
            end_d = min(lr.end_date, period_end)
            is_unpaid = (lr.leave_type or "").strip().lower() in UNPAID_LEAVE_KEYWORDS
            while cur <= end_d:
                counted_leave_dates.add(cur)
                if is_unpaid:
                    unpaid_leave_days += 1
                else:
                    paid_leave_days += 1
                cur += timedelta(days=1)

        # Include attendance-marked Leave days not already tied to leave request rows
        unlinked_att_leaves = max(0, att_leave_days - len(counted_leave_dates))
        paid_leave_days += unlinked_att_leaves

        # Policy parameters from structure (or sensible defaults)
        wdays_cfg = int(structure.working_days_per_month) if structure else 26
        effective_wdays = wdays_cfg if wdays_cfg > 0 else days_in_month
        deduct_absent = bool(structure.deduct_for_absent) if structure else True
        late_ratio = int(structure.late_days_per_absent) if structure else 3
        deduct_unpaid = bool(structure.deduct_unpaid_leave) if structure else True
        paid_quota = int(structure.monthly_paid_leave_quota) if structure else 2

        if paid_quota >= 0 and paid_leave_days > paid_quota:
            excess = paid_leave_days - paid_quota
            unpaid_leave_days += excess
            paid_leave_days = paid_quota

        daily_rate = round(float(basic_salary) / float(effective_wdays), 4) if effective_wdays > 0 else 0.0
        late_equiv_absent = (late_days // late_ratio) if (late_ratio > 0 and deduct_absent) else 0
        effective_absent_days = round(float(absent_days + late_equiv_absent), 2)

        attendance_deduction = round(effective_absent_days * daily_rate, 2) if deduct_absent else 0.0
        leave_deduction = round(float(unpaid_leave_days) * daily_rate, 2) if deduct_unpaid else 0.0

        return {
            "working_days": effective_wdays,
            "present_days": present_days,
            "late_days": late_days,
            "absent_days": effective_absent_days,
            "paid_leave_days": float(paid_leave_days),
            "unpaid_leave_days": float(unpaid_leave_days),
            "attendance_deduction": attendance_deduction,
            "leave_deduction": leave_deduction,
        }

    # ------------------------------------------------------------------
    # 4. Monthly Payroll Batch Generation
    # ------------------------------------------------------------------
    @staticmethod
    def generate_monthly_payroll(
        db: Session,
        payroll_year: int,
        payroll_month: int,
        *,
        run_type: str = "Monthly",
        include_inactive: bool = False,
        variable_inputs: Optional[Dict[Any, Dict[str, Any]]] = None,
        notes: Optional[str] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[PayrollPeriodRun], str]:
        """
        Generates or refreshes a Draft monthly payroll batch for all active Teachers and Staff.
        Strictly blocks regenerating/modifying if that period is already Finalized, Locked, or Paid.
        """
        try:
            PayrollSecurityGuard.require_permission("payroll.processing.CREATE", actor_user)
            if not (1 <= int(payroll_month) <= 12):
                return False, None, "Payroll month must be between 1 and 12."

            username = PayrollSecurityGuard.actor_username(actor_user)
            _, last_day = calendar.monthrange(payroll_year, payroll_month)
            period_start = date(payroll_year, payroll_month, 1)
            period_end = date(payroll_year, payroll_month, last_day)

            existing_run = PayrollRepository.get_active_period_run(db, payroll_year, payroll_month, run_type=run_type)
            if existing_run:
                if existing_run.is_locked or existing_run.status in PayrollPeriodStatus.LOCKED_STATES:
                    return (
                        False,
                        existing_run,
                        f"Payroll period {existing_run.period_label} ({existing_run.run_code}) is "
                        f"{existing_run.status}/Locked and cannot be modified or regenerated. "
                        f"Use an authorized audit-safe reversal if corrections are required.",
                    )
                # Refresh Draft run cleanly (remove scheduled loan repayments & rebuild draft payslips)
                run = existing_run
                draft_slip_ids = [s.id for s in run.payslips]
                if draft_slip_ids:
                    db.query(PayrollLoanRepayment).filter(
                        PayrollLoanRepayment.payslip_id.in_(draft_slip_ids),
                        PayrollLoanRepayment.status == "Scheduled",
                    ).delete(synchronize_session=False)
                    db.query(PayrollPayslip).filter(PayrollPayslip.payroll_run_id == run.id).delete(
                        synchronize_session=False
                    )
                db.flush()
            else:
                # Determine next revision number (supports re-running cleanly if prior run was Reversed)
                max_rev = (
                    db.query(func.max(PayrollPeriodRun.revision_no))
                    .filter(
                        PayrollPeriodRun.payroll_year == payroll_year,
                        PayrollPeriodRun.payroll_month == payroll_month,
                        PayrollPeriodRun.run_type == run_type,
                    )
                    .scalar()
                    or 0
                )
                revision_no = int(max_rev) + 1
                suffix = f"-R{revision_no}" if revision_no > 1 else ""
                type_tag = "-BON" if run_type == "Bonus" else ("-ADJ" if run_type == "Adjustment" else "")
                run_code = f"PAY-{payroll_year}-{payroll_month:02d}{type_tag}{suffix}"

                cur_ay = db.query(AcademicYear).filter(AcademicYear.is_current == True).first()
                run = PayrollPeriodRun(
                    run_code=run_code,
                    payroll_year=payroll_year,
                    payroll_month=payroll_month,
                    run_type=run_type,
                    revision_no=revision_no,
                    academic_year_id=cur_ay.id if cur_ay else None,
                    period_start=period_start,
                    period_end=period_end,
                    status=PayrollPeriodStatus.DRAFT,
                    is_locked=False,
                    generated_by=username,
                    notes=notes,
                )
                db.add(run)
                db.flush()

            allowed_statuses = (
                EmployeeStatus.ALL if include_inactive else (EmployeeStatus.ACTIVE, EmployeeStatus.PROBATION, EmployeeStatus.ON_LEAVE)
            )
            teachers = (
                db.query(Teacher)
                .filter(Teacher.is_deleted == False, Teacher.status.in_(allowed_statuses))
                .order_by(Teacher.id.asc())
                .all()
            )
            staff_members = (
                db.query(Staff)
                .filter(Staff.is_deleted == False, Staff.status.in_(allowed_statuses))
                .order_by(Staff.id.asc())
                .all()
            )

            var_map = variable_inputs or {}
            employees: List[Tuple[str, Any]] = [("teacher", t) for t in teachers] + [("staff", s) for s in staff_members]

            slip_seq = 0
            for etype, emp in employees:
                struct = PayrollRepository.get_active_structure(db, etype, emp.id)
                emp_code, emp_name, role_title, dept_name = PayrollService._employee_identity(etype, emp)

                basic = float(struct.basic_salary if struct else (emp.salary or 0.0))
                if basic <= 0 and not struct:
                    continue

                v_in = (
                    var_map.get((etype, emp.id))
                    or var_map.get(emp_code)
                    or var_map.get(f"{etype}:{emp.id}")
                    or {}
                )

                hra = float(struct.house_rent_allowance or 0.0) if struct else 0.0
                med = float(struct.medical_allowance or 0.0) if struct else 0.0
                trn = float(struct.transport_allowance or 0.0) if struct else 0.0
                spc = float(struct.special_allowance or 0.0) if struct else 0.0
                oth_allow = float(struct.other_allowance or 0.0) if struct else 0.0

                ot_hours = round(float(v_in.get("overtime_hours", 0.0) or 0.0), 2)
                ot_rate = float(v_in.get("overtime_rate") or (struct.overtime_hourly_rate if struct else 0.0) or 0.0)
                if "overtime_amount" in v_in and v_in["overtime_amount"] is not None:
                    ot_amount = round(float(v_in["overtime_amount"] or 0.0), 2)
                else:
                    ot_amount = round(ot_hours * ot_rate, 2)

                bonus_amt = round(float(v_in.get("bonus_amount", 0.0) or 0.0), 2)
                bonus_reason = v_in.get("bonus_reason")

                # Attendance & Leave Deductions
                att_metrics = PayrollService.calculate_attendance_and_leave_metrics(
                    db, etype, emp.id, payroll_year, payroll_month, basic, struct
                )

                # Statutory Deductions
                pf_ded = struct.computed_pf_amount if struct else 0.0
                ins_ded = float(struct.insurance_deduction or 0.0) if struct else 0.0
                fixed_other_ded = float(struct.other_fixed_deduction or 0.0) if struct else 0.0
                other_ded = round(fixed_other_ded + float(v_in.get("other_deduction", 0.0) or 0.0), 2)
                other_ded_reason = v_in.get("other_deduction_reason")

                if "tax_deduction" in v_in and v_in["tax_deduction"] is not None:
                    tax_ded = round(float(v_in["tax_deduction"] or 0.0), 2)
                elif struct:
                    if float(struct.monthly_tax_deduction or 0.0) > 0:
                        tax_ded = round(float(struct.monthly_tax_deduction), 2)
                    elif float(struct.tax_rate_pct or 0.0) > 0:
                        taxable_base = basic + hra + med + trn + spc + oth_allow + ot_amount + bonus_amt
                        tax_ded = round(taxable_base * float(struct.tax_rate_pct) / 100.0, 2)
                    else:
                        tax_ded = 0.0
                else:
                    tax_ded = 0.0

                # Loans & Advances Auto-Installments
                due_loans = PayrollRepository.get_due_active_loans(db, etype, emp.id, payroll_year, payroll_month)
                loan_ded = 0.0
                advance_ded = 0.0
                scheduled_repays: List[Tuple[EmployeeLoan, float]] = []
                for ln in due_loans:
                    installment_due = round(min(float(ln.remaining_balance), float(ln.monthly_installment)), 2)
                    if installment_due <= 0:
                        continue
                    if ln.loan_type == "Advance":
                        advance_ded = round(advance_ded + installment_due, 2)
                    else:
                        loan_ded = round(loan_ded + installment_due, 2)
                    scheduled_repays.append((ln, installment_due))

                slip_seq += 1
                slip_no = f"SLP-{payroll_year}{payroll_month:02d}{'-R' + str(run.revision_no) if run.revision_no > 1 else ''}-{slip_seq:04d}"
                while db.query(PayrollPayslip).filter(PayrollPayslip.slip_no == slip_no).first():
                    slip_seq += 1
                    slip_no = f"SLP-{payroll_year}{payroll_month:02d}-{uuid.uuid4().hex[:4].upper()}"

                norm_method, _ = normalize_payment_channel(
                    struct.payment_method if struct else ("Bank" if emp.bank_account_no else "Cash")
                )

                slip = PayrollPayslip(
                    slip_no=slip_no,
                    payroll_run_id=run.id,
                    structure_id=struct.id if struct else None,
                    **PayrollService._emp_filter(etype, emp.id),
                    employee_code=emp_code,
                    employee_name=emp_name,
                    designation=role_title,
                    department_name=dept_name,
                    tax_tin=struct.tax_tin if struct else None,
                    payroll_year=payroll_year,
                    payroll_month=payroll_month,
                    basic_salary=round(basic, 2),
                    house_rent_allowance=hra,
                    medical_allowance=med,
                    transport_allowance=trn,
                    special_allowance=spc,
                    other_allowance=oth_allow,
                    overtime_hours=ot_hours,
                    overtime_rate=ot_rate,
                    overtime_amount=ot_amount,
                    bonus_amount=bonus_amt,
                    bonus_reason=bonus_reason,
                    working_days=att_metrics["working_days"],
                    present_days=att_metrics["present_days"],
                    late_days=att_metrics["late_days"],
                    absent_days=att_metrics["absent_days"],
                    paid_leave_days=att_metrics["paid_leave_days"],
                    unpaid_leave_days=att_metrics["unpaid_leave_days"],
                    attendance_deduction=att_metrics["attendance_deduction"],
                    leave_deduction=att_metrics["leave_deduction"],
                    provident_fund_deduction=pf_ded,
                    insurance_deduction=ins_ded,
                    tax_deduction=tax_ded,
                    loan_deduction=loan_ded,
                    advance_deduction=advance_ded,
                    other_deduction=other_ded,
                    other_deduction_reason=other_ded_reason,
                    payment_method=norm_method,
                    bank_name=(struct.bank_name if struct else emp.bank_name),
                    bank_account_no=(struct.bank_account_no if struct else emp.bank_account_no),
                    payment_status=PayrollPeriodStatus.DRAFT,
                )
                PayrollService._apply_payslip_math(slip)
                db.add(slip)
                db.flush()

                for ln, r_amt in scheduled_repays:
                    db.add(
                        PayrollLoanRepayment(
                            loan_id=ln.id,
                            payslip_id=slip.id,
                            repayment_date=period_end,
                            amount=r_amt,
                            status="Scheduled",
                        )
                    )

            PayrollService._recalculate_run_totals(db, run)
            AccountingService.record_audit_log(
                db,
                module="PAYROLL",
                entity_type="PayrollPeriodRun",
                entity_id=run.id,
                reference_no=run.run_code,
                action="PAYROLL_RUN_GENERATED",
                amount=float(run.total_net_payable or 0.0),
                after_snapshot={
                    "run_code": run.run_code,
                    "period": run.period_label,
                    "employees": run.total_employees,
                    "gross": float(run.total_gross or 0.0),
                    "net": float(run.total_net_payable or 0.0),
                },
                reason=f"Generated monthly payroll draft for {run.period_label}",
                actor_username=username,
                commit=False,
            )
            DatabaseService.log_activity(
                db,
                action="PAYROLL_RUN_GENERATED",
                module="PAYROLL",
                description=f"Generated payroll run '{run.run_code}' ({run.total_employees} employees, Net: {run.total_net_payable:,.2f})",
                username=username,
                entity_type="PayrollPeriodRun",
                entity_id=str(run.id),
                commit=False,
            )
            db.commit()
            db.refresh(run)
            return True, run, f"Payroll run '{run.run_code}' generated ({run.total_employees} employee slips)."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error generating monthly payroll: {exc}")
            return False, None, str(exc)

    # ------------------------------------------------------------------
    # 5. Draft Adjustments (Strictly Blocked After Lock)
    # ------------------------------------------------------------------
    @staticmethod
    def update_draft_payslip(
        db: Session,
        payslip_id: int,
        updates: Dict[str, Any],
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[PayrollPayslip], str]:
        try:
            PayrollSecurityGuard.require_permission("payroll.processing.EDIT", actor_user)
            slip = PayrollRepository.get_payslip_by_id(db, payslip_id)
            if not slip:
                return False, None, "Payslip not found."

            run = slip.payroll_run
            if run.is_locked or run.status in PayrollPeriodStatus.LOCKED_STATES or slip.payment_status != PayrollPeriodStatus.DRAFT:
                return (
                    False,
                    slip,
                    f"Payslip '{slip.slip_no}' belongs to finalized/locked payroll period '{run.run_code}' and cannot be edited. "
                    f"Use audit-safe payroll reversal for post-lock corrections.",
                )

            if "overtime_hours" in updates:
                slip.overtime_hours = round(float(updates["overtime_hours"] or 0.0), 2)
            if "overtime_rate" in updates:
                slip.overtime_rate = round(float(updates["overtime_rate"] or 0.0), 2)
            if "overtime_amount" in updates and updates["overtime_amount"] is not None:
                slip.overtime_amount = round(float(updates["overtime_amount"] or 0.0), 2)
            elif "overtime_hours" in updates or "overtime_rate" in updates:
                slip.overtime_amount = round(float(slip.overtime_hours or 0.0) * float(slip.overtime_rate or 0.0), 2)

            if "bonus_amount" in updates:
                slip.bonus_amount = round(float(updates["bonus_amount"] or 0.0), 2)
            if "bonus_reason" in updates:
                slip.bonus_reason = updates["bonus_reason"]
            if "tax_deduction" in updates:
                slip.tax_deduction = round(float(updates["tax_deduction"] or 0.0), 2)
            if "other_deduction" in updates:
                slip.other_deduction = round(float(updates["other_deduction"] or 0.0), 2)
            if "other_deduction_reason" in updates:
                slip.other_deduction_reason = updates["other_deduction_reason"]
            if "attendance_deduction" in updates:
                slip.attendance_deduction = round(float(updates["attendance_deduction"] or 0.0), 2)
            if "leave_deduction" in updates:
                slip.leave_deduction = round(float(updates["leave_deduction"] or 0.0), 2)
            if "payment_method" in updates:
                norm_m, _ = normalize_payment_channel(updates["payment_method"])
                slip.payment_method = norm_m
            if "notes" in updates:
                slip.notes = updates["notes"]

            PayrollService._apply_payslip_math(slip)
            PayrollService._recalculate_run_totals(db, run)
            db.commit()
            db.refresh(slip)
            return True, slip, f"Draft payslip '{slip.slip_no}' updated (Net: {slip.net_payable:,.2f})."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    # ------------------------------------------------------------------
    # 6. Finalize & Lock Payroll Period
    # ------------------------------------------------------------------
    @staticmethod
    def finalize_and_lock_period(
        db: Session,
        run_id: int,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[PayrollPeriodRun], str]:
        try:
            PayrollSecurityGuard.require_permission("payroll.processing.APPROVE", actor_user)
            run = PayrollRepository.get_run_by_id(db, run_id)
            if not run:
                return False, None, "Payroll period run not found."
            if run.is_locked or run.status in PayrollPeriodStatus.LOCKED_STATES:
                return False, run, f"Payroll period '{run.run_code}' is already {run.status}/Locked."
            if not run.payslips:
                return False, run, "Cannot finalize an empty payroll period with zero payslips."

            username = PayrollSecurityGuard.actor_username(actor_user)
            now_ts = utc_now()
            run.status = PayrollPeriodStatus.LOCKED
            run.is_locked = True
            run.finalized_by = username
            run.finalized_at = now_ts
            run.locked_by = username
            run.locked_at = now_ts

            for slip in run.payslips:
                if not slip.is_reversed and slip.payment_status == PayrollPeriodStatus.DRAFT:
                    slip.payment_status = PayrollPeriodStatus.FINALIZED

            PayrollService._recalculate_run_totals(db, run)
            AccountingService.record_audit_log(
                db,
                module="PAYROLL",
                entity_type="PayrollPeriodRun",
                entity_id=run.id,
                reference_no=run.run_code,
                action="PAYROLL_PERIOD_LOCKED",
                amount=float(run.total_net_payable or 0.0),
                after_snapshot={"run_code": run.run_code, "status": run.status, "is_locked": True},
                reason=f"Finalized and locked payroll period {run.period_label}",
                actor_username=username,
                commit=False,
            )
            DatabaseService.log_activity(
                db,
                action="PAYROLL_PERIOD_LOCKED",
                module="PAYROLL",
                description=f"Finalized and locked payroll period '{run.run_code}' ({run.period_label})",
                username=username,
                entity_type="PayrollPeriodRun",
                entity_id=str(run.id),
                commit=False,
            )
            db.commit()
            db.refresh(run)
            return True, run, f"Payroll period '{run.run_code}' finalized and locked."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    # ------------------------------------------------------------------
    # 7. Payroll Disbursement & Accounting Integration
    # ------------------------------------------------------------------
    @staticmethod
    def _disburse_single_payslip_in_tx(
        db: Session,
        slip: PayrollPayslip,
        payment_date: date,
        payment_method_override: Optional[str],
        channel_detail: Optional[str],
        username: str,
    ) -> Tuple[bool, str]:
        if slip.is_reversed or slip.payment_status == PayrollPeriodStatus.REVERSED:
            return False, f"Payslip '{slip.slip_no}' is reversed."
        if slip.payment_status == PayrollPeriodStatus.PAID:
            return True, "Already paid."
        if not slip.payroll_run.is_locked:
            return False, f"Payroll period '{slip.payroll_run.run_code}' must be finalized/locked before disbursement."

        norm_method, norm_detail = normalize_payment_channel(
            payment_method_override or slip.payment_method,
            channel_detail or slip.channel_detail or slip.bank_account_no,
        )
        net_amt = round(float(slip.net_payable or 0.0), 2)

        if net_amt > 0:
            cat_code = "EXP-TSAL" if slip.employee_type == "teacher" else "EXP-SSAL"
            cat_id = PayrollService._ensure_category(db, cat_code, "EXP-SSAL")
            tx, tx_err = AccountingService.record_transaction(
                db,
                {
                    "transaction_date": payment_date,
                    "type": "Expense",
                    "entry_kind": "Payroll",
                    "category_id": cat_id,
                    "academic_year_id": slip.payroll_run.academic_year_id,
                    "amount": net_amt,
                    "payment_method": norm_method,
                    "channel_detail": norm_detail,
                    "reference_no": slip.slip_no,
                    "paid_to_received_from": slip.employee_name,
                    "description": f"Salary disbursement {slip.slip_no} ({slip.payroll_run.period_label}) — {slip.employee_name} [{slip.employee_code}]",
                    "idempotency_key": f"PAYSLIP-{slip.slip_no}",
                },
                actor_username=username,
                commit=False,
            )
            if tx_err or not tx:
                return False, tx_err or f"Failed creating accounting voucher for '{slip.slip_no}'."
            slip.accounting_tx_id = tx.id

        # Apply scheduled loan/advance repayments to EmployeeLoan balances
        scheduled_repays = (
            db.query(PayrollLoanRepayment)
            .filter(PayrollLoanRepayment.payslip_id == slip.id, PayrollLoanRepayment.status == "Scheduled")
            .all()
        )
        for rep in scheduled_repays:
            loan = db.query(EmployeeLoan).filter(EmployeeLoan.id == rep.loan_id).first()
            if loan and loan.status == "Active":
                apply_amt = round(min(float(loan.remaining_balance), float(rep.amount)), 2)
                loan.total_repaid = round(float(loan.total_repaid or 0.0) + apply_amt, 2)
                loan.remaining_balance = round(max(0.0, float(loan.remaining_balance) - apply_amt), 2)
                if loan.remaining_balance <= 0.005:
                    loan.remaining_balance = 0.0
                    loan.status = "Settled"
                rep.status = "Applied"
                rep.repayment_date = payment_date

        slip.payment_method = norm_method
        slip.channel_detail = norm_detail
        slip.payment_status = PayrollPeriodStatus.PAID
        slip.paid_date = payment_date
        slip.paid_by = username
        return True, "Disbursed"

    @staticmethod
    def disburse_payslip(
        db: Session,
        payslip_id: int,
        payment_date: Optional[date] = None,
        payment_method: Optional[str] = None,
        channel_detail: Optional[str] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[PayrollPayslip], str]:
        try:
            PayrollSecurityGuard.require_permission("payroll.disbursement.APPROVE", actor_user)
            slip = PayrollRepository.get_payslip_by_id(db, payslip_id)
            if not slip:
                return False, None, "Payslip not found."

            username = PayrollSecurityGuard.actor_username(actor_user)
            pay_dt = payment_date or date.today()
            ok, msg = PayrollService._disburse_single_payslip_in_tx(
                db, slip, pay_dt, payment_method, channel_detail, username
            )
            if not ok:
                db.rollback()
                return False, slip, msg

            run = slip.payroll_run
            PayrollService._recalculate_run_totals(db, run)
            active_slips = [s for s in run.payslips if not s.is_reversed]
            if active_slips and all(s.payment_status == PayrollPeriodStatus.PAID for s in active_slips):
                run.status = PayrollPeriodStatus.PAID
                run.paid_at = utc_now()

            AccountingService.record_audit_log(
                db,
                module="PAYROLL",
                entity_type="PayrollPayslip",
                entity_id=slip.id,
                reference_no=slip.slip_no,
                action="PAYROLL_PAYSLIP_PAID",
                amount=float(slip.net_payable or 0.0),
                after_snapshot={
                    "slip_no": slip.slip_no,
                    "employee": slip.employee_name,
                    "net": float(slip.net_payable or 0.0),
                    "accounting_tx_id": slip.accounting_tx_id,
                },
                reason=f"Salary disbursement for {run.period_label}",
                actor_username=username,
                commit=False,
            )
            db.commit()
            db.refresh(slip)
            return True, slip, f"Disbursed salary {slip.slip_no} ({slip.net_payable:,.2f}) and posted accounting voucher."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def disburse_payroll_run(
        db: Session,
        run_id: int,
        payment_date: Optional[date] = None,
        payment_method: Optional[str] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[PayrollPeriodRun], str]:
        try:
            PayrollSecurityGuard.require_permission("payroll.disbursement.APPROVE", actor_user)
            run = PayrollRepository.get_run_by_id(db, run_id)
            if not run:
                return False, None, "Payroll period run not found."
            if not run.is_locked:
                return (
                    False,
                    run,
                    f"Payroll period '{run.run_code}' must be Finalized & Locked before batch disbursement.",
                )

            username = PayrollSecurityGuard.actor_username(actor_user)
            pay_dt = payment_date or date.today()
            paid_count = 0
            for slip in run.payslips:
                if slip.is_reversed or slip.payment_status == PayrollPeriodStatus.PAID:
                    continue
                ok, msg = PayrollService._disburse_single_payslip_in_tx(
                    db, slip, pay_dt, payment_method, None, username
                )
                if not ok:
                    db.rollback()
                    return False, run, msg
                paid_count += 1

            PayrollService._recalculate_run_totals(db, run)
            active_slips = [s for s in run.payslips if not s.is_reversed]
            if active_slips and all(s.payment_status == PayrollPeriodStatus.PAID for s in active_slips):
                run.status = PayrollPeriodStatus.PAID
                run.paid_at = utc_now()

            AccountingService.record_audit_log(
                db,
                module="PAYROLL",
                entity_type="PayrollPeriodRun",
                entity_id=run.id,
                reference_no=run.run_code,
                action="PAYROLL_BATCH_DISBURSED",
                amount=float(run.total_paid_amount or 0.0),
                after_snapshot={
                    "run_code": run.run_code,
                    "paid_count": paid_count,
                    "total_paid": float(run.total_paid_amount or 0.0),
                },
                reason=f"Batch payroll disbursement for {run.period_label}",
                actor_username=username,
                commit=False,
            )
            DatabaseService.log_activity(
                db,
                action="PAYROLL_BATCH_DISBURSED",
                module="PAYROLL",
                description=f"Disbursed {paid_count} payslip(s) in '{run.run_code}' (Total Paid: {run.total_paid_amount:,.2f})",
                username=username,
                entity_type="PayrollPeriodRun",
                entity_id=str(run.id),
                commit=False,
            )
            db.commit()
            db.refresh(run)
            return True, run, f"Disbursed {paid_count} payslip(s) for '{run.run_code}' and integrated with Accounting."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error disbursing payroll run: {exc}")
            return False, None, str(exc)

    # ------------------------------------------------------------------
    # 8. Audit-Safe Reversal Procedures
    # ------------------------------------------------------------------
    @staticmethod
    def _next_reversal_no(db: Session, rev_date: date) -> str:
        cnt = db.query(func.count(PayrollReversal.id)).scalar() or 0
        seq = int(cnt) + 1
        while True:
            cand = f"PREV-{rev_date.year}-{seq:05d}"
            if not db.query(PayrollReversal).filter(PayrollReversal.reversal_no == cand).first():
                return cand
            seq += 1

    @staticmethod
    def reverse_payslip(
        db: Session,
        payslip_id: int,
        reason: str,
        reversal_date: Optional[date] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[PayrollReversal], str]:
        """
        Audit-safe payslip reversal:
        - Preserves the original PayrollPayslip intact (never deleted).
        - If already posted to Accounting, creates a compensating contra-entry voucher via AccountingService.reverse_transaction.
        - Restores any deducted loan/advance installments back to EmployeeLoan.remaining_balance.
        - Creates an immutable PayrollReversal audit record.
        """
        try:
            PayrollSecurityGuard.require_permission("payroll.reversals.APPROVE", actor_user)
            if not reason or not reason.strip():
                return False, None, "A mandatory audit reason is required for payroll reversal."

            slip = PayrollRepository.get_payslip_by_id(db, payslip_id)
            if not slip:
                return False, None, "Payslip not found."
            if slip.is_reversed or slip.payment_status == PayrollPeriodStatus.REVERSED:
                return False, None, f"Payslip '{slip.slip_no}' is already reversed."

            username = PayrollSecurityGuard.actor_username(actor_user)
            rev_dt = reversal_date or date.today()
            clean_reason = reason.strip()

            rev_acc_tx_id = None
            if slip.accounting_tx_id:
                contra_tx, rev_err = AccountingService.reverse_transaction(
                    db,
                    slip.accounting_tx_id,
                    reason=f"Payroll reversal ({slip.slip_no}): {clean_reason}",
                    actor_username=username,
                    reversal_date=rev_dt,
                    commit=False,
                )
                if not contra_tx:
                    db.rollback()
                    return False, None, rev_err
                rev_acc_tx_id = contra_tx.id

            # Reinstate loan/advance deductions if applied (or cancel scheduled ones)
            repayments = db.query(PayrollLoanRepayment).filter(PayrollLoanRepayment.payslip_id == slip.id).all()
            for rep in repayments:
                if rep.status == "Applied":
                    loan = db.query(EmployeeLoan).filter(EmployeeLoan.id == rep.loan_id).first()
                    if loan:
                        loan.total_repaid = round(max(0.0, float(loan.total_repaid or 0.0) - float(rep.amount)), 2)
                        loan.remaining_balance = round(float(loan.remaining_balance or 0.0) + float(rep.amount), 2)
                        if loan.remaining_balance > 0 and loan.status == "Settled":
                            loan.status = "Active"
                rep.status = "Reversed"
                rep.reversed_by = username
                rep.reversed_at = utc_now()

            slip.is_reversed = True
            slip.payment_status = PayrollPeriodStatus.REVERSED
            slip.reversed_by = username
            slip.reversed_at = utc_now()
            slip.reversal_reason = clean_reason

            rev_rec = PayrollReversal(
                reversal_no=PayrollService._next_reversal_no(db, rev_dt),
                payroll_run_id=slip.payroll_run_id,
                payslip_id=slip.id,
                reversal_scope="Payslip",
                original_amount=float(slip.net_payable or 0.0),
                reversed_amount=float(slip.net_payable or 0.0),
                reason=clean_reason,
                authorized_by=username,
                reversal_date=rev_dt,
                accounting_reversal_tx_id=rev_acc_tx_id,
            )
            db.add(rev_rec)
            db.flush()

            run = slip.payroll_run
            PayrollService._recalculate_run_totals(db, run)
            all_slips = db.query(PayrollPayslip).filter(PayrollPayslip.payroll_run_id == run.id).all()
            if all_slips and all(s.is_reversed for s in all_slips):
                run.status = PayrollPeriodStatus.REVERSED
                run.reversed_by = username
                run.reversed_at = utc_now()
                run.reversal_reason = clean_reason
            elif any(s.is_reversed for s in all_slips):
                run.status = PayrollPeriodStatus.PARTIALLY_REVERSED

            AccountingService.record_audit_log(
                db,
                module="PAYROLL",
                entity_type="PayrollPayslip",
                entity_id=slip.id,
                reference_no=rev_rec.reversal_no,
                action="PAYROLL_PAYSLIP_REVERSED",
                amount=float(slip.net_payable or 0.0),
                before_snapshot={"slip_no": slip.slip_no, "accounting_tx_id": slip.accounting_tx_id},
                after_snapshot={"status": "Reversed", "accounting_reversal_tx_id": rev_acc_tx_id},
                reason=clean_reason,
                actor_username=username,
                commit=False,
            )
            DatabaseService.log_activity(
                db,
                action="PAYROLL_PAYSLIP_REVERSED",
                module="PAYROLL",
                description=f"Audit-safe reversal '{rev_rec.reversal_no}' on payslip '{slip.slip_no}': {clean_reason}",
                username=username,
                entity_type="PayrollReversal",
                entity_id=str(rev_rec.id),
                commit=False,
            )
            db.commit()
            db.refresh(rev_rec)
            return True, rev_rec, f"Payslip '{slip.slip_no}' reversed safely under audit ref '{rev_rec.reversal_no}'."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error reversing payslip: {exc}")
            return False, None, str(exc)

    @staticmethod
    def reverse_payroll_run(
        db: Session,
        run_id: int,
        reason: str,
        reversal_date: Optional[date] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, List[PayrollReversal], str]:
        """Audit-safe full-period reversal across all active payslips in a PayrollPeriodRun."""
        try:
            PayrollSecurityGuard.require_permission("payroll.reversals.APPROVE", actor_user)
            if not reason or not reason.strip():
                return False, [], "A mandatory audit reason is required to reverse a payroll period."

            run = PayrollRepository.get_run_by_id(db, run_id)
            if not run:
                return False, [], "Payroll period run not found."
            if run.status == PayrollPeriodStatus.REVERSED:
                return False, [], f"Payroll period '{run.run_code}' is already reversed."

            reversals: List[PayrollReversal] = []
            for slip in list(run.payslips):
                if slip.is_reversed:
                    continue
                ok, rev, msg = PayrollService.reverse_payslip(
                    db,
                    slip.id,
                    reason=f"Period Run {run.run_code}: {reason.strip()}",
                    reversal_date=reversal_date,
                    actor_user=actor_user,
                )
                if not ok:
                    return False, reversals, msg
                if rev:
                    reversals.append(rev)

            return True, reversals, f"Reversed payroll period '{run.run_code}' ({len(reversals)} payslip(s))."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, [], str(exc)

    # ------------------------------------------------------------------
    # 9. Reporting & Employee Payment History Queries
    # ------------------------------------------------------------------
    @staticmethod
    def get_employee_payment_history(
        db: Session,
        employee_type: str,
        employee_pk: int,
        actor_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        PayrollSecurityGuard.require_permission("payroll.reports.VIEW", actor_user)
        emp = StaffRepository.get_employee(db, employee_type, employee_pk)
        if not emp:
            raise ValueError("Employee not found.")

        slips = PayrollRepository.list_payslips(
            db, employee_type=employee_type, employee_pk=employee_pk
        )
        loans = PayrollRepository.list_loans(
            db, employee_type=employee_type, employee_pk=employee_pk
        )
        paid_slips = [s for s in slips if s.payment_status == PayrollPeriodStatus.PAID and not s.is_reversed]
        emp_code, emp_name, role_title, dept_name = PayrollService._employee_identity(employee_type, emp)
        return {
            "employee_type": employee_type.lower(),
            "employee_id": emp.id,
            "employee_code": emp_code,
            "employee_name": emp_name,
            "designation": role_title,
            "department": dept_name,
            "payslips": slips,
            "loans": loans,
            "total_gross_paid": round(sum(float(s.gross_earnings or 0.0) for s in paid_slips), 2),
            "total_tax_paid": round(sum(float(s.tax_deduction or 0.0) for s in paid_slips), 2),
            "total_deductions": round(sum(float(s.total_deductions or 0.0) for s in paid_slips), 2),
            "total_net_paid": round(sum(float(s.net_payable or 0.0) for s in paid_slips), 2),
            "active_loan_balance": round(
                sum(float(l.remaining_balance or 0.0) for l in loans if l.status == "Active"), 2
            ),
        }

    @staticmethod
    def get_monthly_payroll_summary(
        db: Session,
        run_id: int,
        actor_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        PayrollSecurityGuard.require_permission("payroll.reports.VIEW", actor_user)
        run = PayrollRepository.get_run_by_id(db, run_id)
        if not run:
            raise ValueError("Payroll period run not found.")

        active_slips = [s for s in run.payslips if not s.is_reversed]
        teacher_slips = [s for s in active_slips if s.employee_type == "teacher"]
        staff_slips = [s for s in active_slips if s.employee_type == "staff"]
        return {
            "run": run,
            "payslips": run.payslips,
            "active_count": len(active_slips),
            "reversed_count": sum(1 for s in run.payslips if s.is_reversed),
            "teacher_net": round(sum(float(s.net_payable or 0.0) for s in teacher_slips), 2),
            "staff_net": round(sum(float(s.net_payable or 0.0) for s in staff_slips), 2),
            "total_basic": round(sum(float(s.basic_salary or 0.0) for s in active_slips), 2),
            "total_allowances": round(sum(s.total_allowances for s in active_slips), 2),
            "total_overtime": round(sum(float(s.overtime_amount or 0.0) for s in active_slips), 2),
            "total_bonus": round(sum(float(s.bonus_amount or 0.0) for s in active_slips), 2),
            "total_gross": round(sum(float(s.gross_earnings or 0.0) for s in active_slips), 2),
            "total_att_leave_ded": round(
                sum(float(s.attendance_deduction or 0.0) + float(s.leave_deduction or 0.0) for s in active_slips), 2
            ),
            "total_tax": round(sum(float(s.tax_deduction or 0.0) for s in active_slips), 2),
            "total_loan_adv_ded": round(
                sum(float(s.loan_deduction or 0.0) + float(s.advance_deduction or 0.0) for s in active_slips), 2
            ),
            "total_deductions": round(sum(float(s.total_deductions or 0.0) for s in active_slips), 2),
            "total_net": round(sum(float(s.net_payable or 0.0) for s in active_slips), 2),
        }

    @staticmethod
    def export_payroll_report_excel(
        db: Session,
        run_id: int,
        output_path: str,
        actor_user: Optional[User] = None,
    ) -> str:
        PayrollSecurityGuard.require_permission("payroll.reports.EXPORT", actor_user)
        summary = PayrollService.get_monthly_payroll_summary(db, run_id, actor_user=actor_user)
        run = summary["run"]

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Payroll_{run.payroll_year}_{run.payroll_month:02d}"

        headers = [
            "Slip No",
            "Emp Code",
            "Employee Name",
            "Type",
            "Department",
            "Basic",
            "Allowances",
            "Overtime",
            "Bonus",
            "Gross Earnings",
            "Att. Deduction",
            "Leave Deduction",
            "PF & Ins.",
            "Tax (TDS)",
            "Loan & Adv.",
            "Other Ded.",
            "Total Deductions",
            "Net Payable",
            "Method",
            "Status",
            "Accounting Voucher",
        ]
        ws.append(headers)

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        for col_idx in range(1, len(headers) + 1):
            c = ws.cell(row=1, column=col_idx)
            c.font = header_font
            c.fill = header_fill
            c.alignment = Alignment(horizontal="center", vertical="center")

        for s in summary["payslips"]:
            voucher_no = s.accounting_tx.voucher_no if s.accounting_tx else "-"
            ws.append(
                [
                    s.slip_no,
                    s.employee_code,
                    s.employee_name,
                    s.employee_type.title(),
                    s.department_name or "-",
                    float(s.basic_salary or 0.0),
                    s.total_allowances,
                    float(s.overtime_amount or 0.0),
                    float(s.bonus_amount or 0.0),
                    float(s.gross_earnings or 0.0),
                    float(s.attendance_deduction or 0.0),
                    float(s.leave_deduction or 0.0),
                    round(float(s.provident_fund_deduction or 0.0) + float(s.insurance_deduction or 0.0), 2),
                    float(s.tax_deduction or 0.0),
                    round(float(s.loan_deduction or 0.0) + float(s.advance_deduction or 0.0), 2),
                    float(s.other_deduction or 0.0),
                    float(s.total_deductions or 0.0),
                    float(s.net_payable or 0.0),
                    s.payment_method,
                    s.payment_status,
                    voucher_no,
                ]
            )

        for col in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max(max_len + 3, 12), 40)

        wb.save(output_path)
        return output_path
