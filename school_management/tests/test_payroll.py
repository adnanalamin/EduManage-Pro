"""
EduManage Pro - Enterprise Payroll Module Automated Tests (pytest)
Covers:
- Salary Structures (Basic, Allowances, PF, Insurance, Overtime Rate, Tax/TIN, Attendance & Leave Rules)
- Employee Loans & Salary Advances (with Accounting Voucher Issuance)
- Attendance-Based Deduction & Unpaid Leave Deduction Computation
- Monthly Payroll Batch Generation (Teachers & Staff) with Overtime, Bonuses & Installment Recovery
- Finalized Payroll Period Locking (Strict blocking of post-lock edits or regeneration)
- Accounting Integration (EXP-TSAL / EXP-SSAL Expense Vouchers, Cashbook Reconciliation & FinancialAuditLog)
- Audit-Safe Reversal Procedures (Contra-Voucher Creation, Loan Balance Restoration, Never Deleting Payroll Rows)
- Strict RBAC Confidentiality (Blocking Teacher/Receptionist access)
- Salary Slip PDF, Monthly Payroll Register PDF/Excel & Employee Payment History PDF
"""

from datetime import date
import openpyxl
import pytest
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.connection import Base, create_database_engine
from app.database.init_db import SYSTEM_ROLES
from app.models.accounting import AccountTransaction, FinancialAuditLog
from app.models.attendance import StaffAttendance, TeacherAttendance
from app.models.payroll import (
    EmployeeLoan,
    PayrollPayslip,
    PayrollPeriodRun,
    PayrollPeriodStatus,
    PayrollReversal,
    PayrollStructure,
)
from app.models.school import SchoolSetting
from app.models.staff import Department, EmployeeStatus
from app.models.user import Role
from app.reports.payroll_pdf import PayrollPDFGenerator
from app.repositories.payroll_repository import PayrollRepository
from app.repositories.staff_repository import StaffRepository
from app.security.session import session as app_session
from app.services.accounting_service import AccountingService
from app.services.auth_service import AuthService
from app.services.hr_service import HRService
from app.services.payroll_service import PayrollService


@pytest.fixture
def payroll_db():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()

    db.add(SchoolSetting(school_name="EduManage Pro Academy", currency_code="BDT", currency_symbol="৳"))
    StaffRepository.get_or_create_departments(db)
    AccountingService.seed_default_categories(db)
    for code, disp, desc, is_sys in SYSTEM_ROLES:
        db.add(
            Role(
                name=code,
                display_name=disp,
                description=desc,
                is_system_role=is_sys,
                is_active=True,
            )
        )
    db.commit()
    AuthService.sync_permission_catalog(db)
    app_session.clear()

    yield db
    app_session.clear()
    db.close()
    engine.dispose()


def _create_actor(db, role_name: str, username: str):
    if not AuthService.has_super_admin(db):
        ok, admin_u, msg = AuthService.create_first_admin(
            db, "root_payroll_admin", "root_pay@school.edu", "Root Payroll Admin", "V@ultPay#2026!"
        )
        assert ok, msg
    else:
        admin_u = db.query(Role).filter_by(name="super_admin").first().users[0]

    if role_name == "super_admin":
        return admin_u

    role = db.query(Role).filter_by(name=role_name).first()
    ok, user, msg = AuthService.create_user(
        db,
        actor_user=admin_u,
        username=username,
        email=f"{username}@school.edu",
        full_name=username.title(),
        password="Str0ngUser!2026",
        role_id=role.id,
        must_change_password=False,
    )
    assert ok, msg
    return user


def _seed_employees(db, admin):
    sci_dept = db.query(Department).filter_by(code="SCI").first()
    adm_dept = db.query(Department).filter_by(code="ADMIN").first()

    ok_t, teacher, msg_t = HRService.onboard_employee(
        db,
        "teacher",
        {
            "full_name": "Prof. Farhan Ahmed",
            "gender": "Male",
            "date_of_birth": date(1985, 3, 12),
            "phone": "+880 1711-445566",
            "email": "farhan.ahmed@school.edu",
            "qualification": "M.Sc in Mathematics",
            "designation": "Senior Lecturer",
            "department_id": sci_dept.id,
            "primary_subject": "Mathematics",
            "salary": 50000,
            "bank_name": "DBBL",
            "bank_account_no": "101-220-3344",
            "status": EmployeeStatus.ACTIVE,
        },
        actor_user=admin,
    )
    assert ok_t is True, msg_t

    ok_s, staff, msg_s = HRService.onboard_employee(
        db,
        "staff",
        {
            "full_name": "Karim Uddin",
            "gender": "Male",
            "date_of_birth": date(1992, 7, 18),
            "phone": "+880 1811-778899",
            "position": "Office Staff",
            "department_id": adm_dept.id,
            "salary": 26000,
            "bank_name": "Islami Bank",
            "bank_account_no": "205-880-1122",
            "status": EmployeeStatus.ACTIVE,
        },
        actor_user=admin,
    )
    assert ok_s is True, msg_s
    return teacher, staff


def test_full_payroll_lifecycle_deductions_locking_and_accounting(payroll_db, tmp_path):
    admin = _create_actor(payroll_db, "super_admin", "root_payroll_admin")
    accountant = _create_actor(payroll_db, "accountant", "pay_accountant")
    teacher, staff = _seed_employees(payroll_db, admin)

    # 1. Configure Salary Structures (26 working days/mo for clean math: 52000/26 = 2000/day, 26000/26 = 1000/day)
    ok_st1, st_t, msg_st1 = PayrollService.upsert_salary_structure(
        payroll_db,
        "teacher",
        teacher.id,
        {
            "basic_salary": 52000,
            "house_rent_allowance": 15000,
            "medical_allowance": 3000,
            "transport_allowance": 2000,
            "overtime_hourly_rate": 500,
            "provident_fund_pct": 5.0,  # 2600
            "insurance_deduction": 400,
            "tax_tin": "TIN-102938475",
            "monthly_tax_deduction": 2500,
            "working_days_per_month": 26,
            "late_days_per_absent": 3,
            "monthly_paid_leave_quota": 2,
            "payment_method": "Bank",
        },
        actor_user=accountant,
    )
    assert ok_st1 is True, msg_st1
    assert st_t.base_gross_salary == 72000.0
    assert st_t.computed_pf_amount == 2600.0

    ok_st2, st_s, msg_st2 = PayrollService.upsert_salary_structure(
        payroll_db,
        "staff",
        staff.id,
        {
            "basic_salary": 26000,
            "house_rent_allowance": 6000,
            "medical_allowance": 1500,
            "overtime_hourly_rate": 250,
            "provident_fund_pct": 0.0,
            "monthly_tax_deduction": 500,
            "working_days_per_month": 26,
            "late_days_per_absent": 3,
            "monthly_paid_leave_quota": 2,
            "payment_method": "Bank",
        },
        actor_user=accountant,
    )
    assert ok_st2 is True, msg_st2

    # 2. Issue Loan to Teacher (12,000 @ 3,000/mo) and Advance to Staff (4,000 @ 4,000 single recovery)
    ok_ln, loan_t, msg_ln = PayrollService.issue_loan_or_advance(
        payroll_db,
        "teacher",
        teacher.id,
        {
            "loan_type": "Loan",
            "principal_amount": 12000,
            "monthly_installment": 3000,
            "issue_date": date(2026, 3, 2),
            "repayment_start_year": 2026,
            "repayment_start_month": 3,
            "disbursement_method": "Bank",
            "reason": "Laptop Purchase Loan",
        },
        post_to_accounting=True,
        actor_user=accountant,
    )
    assert ok_ln is True, msg_ln
    assert loan_t.accounting_tx_id is not None
    assert loan_t.remaining_balance == 12000.0

    ok_adv, adv_s, msg_adv = PayrollService.issue_loan_or_advance(
        payroll_db,
        "staff",
        staff.id,
        {
            "loan_type": "Advance",
            "principal_amount": 4000,
            "monthly_installment": 4000,
            "issue_date": date(2026, 3, 5),
            "repayment_start_year": 2026,
            "repayment_start_month": 3,
            "disbursement_method": "Cash",
            "reason": "Salary Advance",
        },
        post_to_accounting=True,
        actor_user=accountant,
    )
    assert ok_adv is True, msg_adv

    # 3. Record Attendance Absences/Lates and Unpaid Leave for March 2026
    # Teacher: 1 Absent + 3 Lates (= 1 equiv absent => 2 absent days * 2000 = 4000 attendance ded)
    payroll_db.add_all(
        [
            TeacherAttendance(teacher_id=teacher.id, date=date(2026, 3, 4), status="Absent"),
            TeacherAttendance(teacher_id=teacher.id, date=date(2026, 3, 7), status="Late"),
            TeacherAttendance(teacher_id=teacher.id, date=date(2026, 3, 8), status="Late"),
            TeacherAttendance(teacher_id=teacher.id, date=date(2026, 3, 9), status="Late"),
        ]
    )
    # Staff: 1 approved Unpaid Leave day (1 day * 1000 = 1000 leave deduction)
    payroll_db.commit()
    ok_lv, req, _ = HRService.submit_leave_request(
        payroll_db, "staff", staff.id, "Unpaid", date(2026, 3, 10), date(2026, 3, 10), "Personal LWP", actor_user=admin
    )
    assert ok_lv is True
    ok_app, _, _ = HRService.approve_leave_request(payroll_db, req.id, remarks="Approved Unpaid", actor_user=admin)
    assert ok_app is True

    # 4. Generate Monthly Payroll Draft for March 2026 with Overtime & Bonus
    ok_gen, run, msg_gen = PayrollService.generate_monthly_payroll(
        payroll_db,
        2026,
        3,
        variable_inputs={
            ("teacher", teacher.id): {
                "overtime_hours": 4,
                "bonus_amount": 5000,
                "bonus_reason": "Board Exam Prep Bonus",
            },
            ("staff", staff.id): {
                "overtime_hours": 8,
                "bonus_amount": 1000,
                "bonus_reason": "Festival Allowance",
            },
        },
        actor_user=accountant,
    )
    assert ok_gen is True, msg_gen
    assert run.status == PayrollPeriodStatus.DRAFT
    assert run.is_locked is False
    assert run.total_employees == 2

    slips_by_type = {s.employee_type: s for s in run.payslips}
    t_slip = slips_by_type["teacher"]
    s_slip = slips_by_type["staff"]

    # Teacher expected: Basic 52000 + Allow 20000 + OT (4*500=2000) + Bonus 5000 = Gross 79,000
    assert t_slip.gross_earnings == 79000.0
    assert t_slip.attendance_deduction == 4000.0  # 1 absent + (3 lates -> 1 absent) = 2 * 2000
    assert t_slip.loan_deduction == 3000.0
    assert t_slip.provident_fund_deduction == 2600.0
    assert t_slip.tax_deduction == 2500.0
    # Total deductions: 4000 + 2600 + 400 + 2500 + 3000 = 12,500 => Net = 66,500
    assert t_slip.total_deductions == 12500.0
    assert t_slip.net_payable == 66500.0

    # Staff expected: Basic 26000 + Allow 7500 + OT (8*250=2000) + Bonus 1000 = Gross 36,500
    assert s_slip.gross_earnings == 36500.0
    assert s_slip.unpaid_leave_days == 1.0
    assert s_slip.leave_deduction == 1000.0
    assert s_slip.advance_deduction == 4000.0
    assert s_slip.tax_deduction == 500.0
    # Total deductions: 1000 + 500 + 4000 = 5,500 => Net = 31,000
    assert s_slip.total_deductions == 5500.0
    assert s_slip.net_payable == 31000.0

    # 5. Finalize & Lock Period -> Verify Draft Edits & Regeneration Strictly Blocked
    ok_lk, locked_run, msg_lk = PayrollService.finalize_and_lock_period(payroll_db, run.id, actor_user=admin)
    assert ok_lk is True, msg_lk
    assert locked_run.is_locked is True
    assert locked_run.status == PayrollPeriodStatus.LOCKED

    ok_edit_blk, _, msg_edit_blk = PayrollService.update_draft_payslip(
        payroll_db, t_slip.id, {"bonus_amount": 9999}, actor_user=admin
    )
    assert ok_edit_blk is False
    assert "locked" in msg_edit_blk.lower()

    ok_regen_blk, _, msg_regen_blk = PayrollService.generate_monthly_payroll(
        payroll_db, 2026, 3, actor_user=admin
    )
    assert ok_regen_blk is False
    assert "locked" in msg_regen_blk.lower()

    # 6. Disburse Batch -> Posts EXP-TSAL & EXP-SSAL to Accounting and Updates Loan/Advance Balances
    ok_pay, paid_run, msg_pay = PayrollService.disburse_payroll_run(
        payroll_db, run.id, payment_date=date(2026, 3, 31), actor_user=accountant
    )
    assert ok_pay is True, msg_pay
    assert paid_run.status == PayrollPeriodStatus.PAID

    payroll_db.refresh(t_slip)
    payroll_db.refresh(s_slip)
    payroll_db.refresh(loan_t)
    payroll_db.refresh(adv_s)

    assert t_slip.accounting_tx_id is not None
    assert s_slip.accounting_tx_id is not None
    assert t_slip.accounting_tx.category.code == "EXP-TSAL"
    assert t_slip.accounting_tx.amount == 66500.0
    assert s_slip.accounting_tx.category.code == "EXP-SSAL"
    assert s_slip.accounting_tx.amount == 31000.0

    assert loan_t.total_repaid == 3000.0
    assert loan_t.remaining_balance == 9000.0
    assert adv_s.total_repaid == 4000.0
    assert adv_s.remaining_balance == 0.0
    assert adv_s.status == "Settled"

    # 7. Generate Salary Slip PDF, Payroll Register PDF/Excel & Employee Payment History PDF
    slip_pdf = tmp_path / "slip_teacher.pdf"
    reg_pdf = tmp_path / "register_mar2026.pdf"
    reg_xlsx = tmp_path / "register_mar2026.xlsx"
    hist_pdf = tmp_path / "history_teacher.pdf"

    PayrollPDFGenerator.generate_salary_slip_pdf(payroll_db, t_slip.id, str(slip_pdf), actor_user=accountant)
    PayrollPDFGenerator.generate_payroll_report_pdf(payroll_db, run.id, str(reg_pdf), actor_user=accountant)
    PayrollService.export_payroll_report_excel(payroll_db, run.id, str(reg_xlsx), actor_user=accountant)
    PayrollPDFGenerator.generate_employee_payment_history_pdf(
        payroll_db, "teacher", teacher.id, str(hist_pdf), actor_user=accountant
    )
    for f in (slip_pdf, reg_pdf, reg_xlsx, hist_pdf):
        assert f.exists() and f.stat().st_size > 0
    wb = openpyxl.load_workbook(reg_xlsx)
    assert wb.active.max_row == 3

    # 8. Permanent Deletion Prohibited + Audit-Safe Reversal Procedure Restores Loans & Accounting
    with pytest.raises(ValueError):
        PayrollRepository.delete_payslip(t_slip)
    with pytest.raises(ValueError):
        payroll_db.delete(t_slip)
        payroll_db.flush()
    payroll_db.rollback()

    # Audit-safe reversal of Staff Payslip (requires mandatory reason)
    ok_no_reason, _, _ = PayrollService.reverse_payslip(payroll_db, s_slip.id, reason="  ", actor_user=admin)
    assert ok_no_reason is False

    ok_rev, rev_rec, msg_rev = PayrollService.reverse_payslip(
        payroll_db, s_slip.id, reason="Incorrect overtime hours approved", actor_user=admin
    )
    assert ok_rev is True, msg_rev
    assert rev_rec is not None
    assert rev_rec.accounting_reversal_tx_id is not None

    payroll_db.refresh(s_slip)
    payroll_db.refresh(adv_s)
    payroll_db.refresh(run)
    orig_vch = payroll_db.query(AccountTransaction).filter_by(id=s_slip.accounting_tx_id).first()
    contra_vch = payroll_db.query(AccountTransaction).filter_by(id=rev_rec.accounting_reversal_tx_id).first()

    assert s_slip.is_reversed is True
    assert s_slip.payment_status == PayrollPeriodStatus.REVERSED
    assert orig_vch.is_reversed is True
    assert contra_vch.entry_kind == "Reversal"
    assert contra_vch.amount == 31000.0
    # Advance reinstated back from Settled -> Active!
    assert adv_s.remaining_balance == 4000.0
    assert adv_s.total_repaid == 0.0
    assert adv_s.status == "Active"
    assert run.status == PayrollPeriodStatus.PARTIALLY_REVERSED


def test_payroll_rbac_confidentiality(payroll_db, tmp_path):
    admin = _create_actor(payroll_db, "super_admin", "root_payroll_admin")
    teacher_user = _create_actor(payroll_db, "teacher", "unauth_teacher")
    receptionist_user = _create_actor(payroll_db, "receptionist", "unauth_receptionist")
    teacher, _ = _seed_employees(payroll_db, admin)

    # Admin sets up a payroll run
    PayrollService.upsert_salary_structure(
        payroll_db, "teacher", teacher.id, {"basic_salary": 45000}, actor_user=admin
    )
    ok_gen, run, _ = PayrollService.generate_monthly_payroll(payroll_db, 2026, 4, actor_user=admin)
    assert ok_gen is True

    # Unauthorized roles MUST be blocked from all payroll operations & reports
    for unauth in (teacher_user, receptionist_user):
        with pytest.raises(PermissionError):
            PayrollService.upsert_salary_structure(
                payroll_db, "teacher", teacher.id, {"basic_salary": 90000}, actor_user=unauth
            )
        with pytest.raises(PermissionError):
            PayrollService.generate_monthly_payroll(payroll_db, 2026, 5, actor_user=unauth)
        with pytest.raises(PermissionError):
            PayrollService.finalize_and_lock_period(payroll_db, run.id, actor_user=unauth)
        with pytest.raises(PermissionError):
            PayrollService.disburse_payroll_run(payroll_db, run.id, actor_user=unauth)
        with pytest.raises(PermissionError):
            PayrollService.reverse_payroll_run(payroll_db, run.id, reason="Attempt", actor_user=unauth)
        with pytest.raises(PermissionError):
            PayrollService.get_employee_payment_history(payroll_db, "teacher", teacher.id, actor_user=unauth)
        with pytest.raises(PermissionError):
            PayrollPDFGenerator.generate_payroll_report_pdf(
                payroll_db, run.id, str(tmp_path / "blocked.pdf"), actor_user=unauth
            )
