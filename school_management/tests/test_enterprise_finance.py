"""
EduManage Pro - Enterprise School Finance & Accounting Test Suite
Validates:
- All 8 Fee Categories (Tuition, Admission, Exam, Library, Transport, Hostel, Development, Other)
- Fee Structures & Monthly Batch Billing (duplicate-safe)
- Discounts, Scholarships & Waivers with audit trail
- Partial & Full Payments across Cash, Bank, Card, Mobile Banking, Other
- Advance Payment Credit Wallet deposit & invoice settlement
- Non-Destructive Refunds & Invoice Cancellation guards
- Immutability & Prohibition of permanent financial deletion (ORM + Repository guards)
- Non-Destructive Accounting Voucher Reversals balancing P&L & Running Ledger
- General Ledger, Cashbook, Budgets & Variance Alerts, Financial Summary, Audit Trail
- ReportLab PDFs (Invoice, Receipt, Refund, Due, Collection, Cashbook, Budget, Statement) & openpyxl Excel exports
"""

from datetime import date, timedelta
import os
import tempfile

import pytest
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.connection import Base, create_database_engine
from app.database.migrations import CURRENT_SCHEMA_VERSION, migrate_database
from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.accounting import (
    AccountBudget,
    AccountCategory,
    AccountTransaction,
    FinancialAuditLog,
)
from app.models.fee import (
    PAYMENT_CHANNELS,
    FeeAdjustment,
    FeeCategory,
    FeePayment,
    FeeRefund,
    FeeStructure,
    StudentAdvanceCredit,
    StudentFee,
)
from app.models.school import SchoolSetting
from app.models.student import Student, StudentStatus
from app.reports.fee_receipt_pdf import FeeReceiptPDFGenerator
from app.reports.finance_pdf import FinancePDFGenerator
from app.reports.financial_statement_pdf import FinancialStatementPDFGenerator
from app.repositories.accounting_repository import AccountingRepository
from app.repositories.fee_repository import FeeRepository
from app.services.accounting_service import AccountingService
from app.services.fee_service import FeeService


@pytest.fixture
def db_session(tmp_path):
    db_file = tmp_path / "finance_enterprise.db"
    engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()

    school = SchoolSetting(
        school_name="EduManage International School",
        eiin_number="134211",
        phone="+8801712345678",
        address="Sector 7, Uttara, Dhaka",
    )
    session.add(school)

    ay = AcademicYear(
        name="2026-2027",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    session.add(ay)
    session.flush()

    cls10 = SchoolClass(
        name="Class 10",
        code="C10",
        numeric_order=10,
        group="Science",
        shift="Morning",
        academic_year_id=ay.id,
    )
    session.add(cls10)
    session.flush()

    sec = Section(name="A", class_id=cls10.id, capacity=40)
    session.add(sec)
    session.flush()

    s1 = Student(
        student_id="STU-2026-0001",
        admission_number="ADM-2026-0001",
        roll_number=1,
        first_name="Amina",
        last_name="Rahman",
        full_name="Amina Rahman",
        gender="Female",
        date_of_birth=date(2010, 4, 15),
        admission_date=date(2026, 1, 5),
        class_id=cls10.id,
        section_id=sec.id,
        academic_year_id=ay.id,
        status=StudentStatus.ACTIVE,
        phone="+8801711000001",
    )
    s2 = Student(
        student_id="STU-2026-0002",
        admission_number="ADM-2026-0002",
        roll_number=2,
        first_name="Tanvir",
        last_name="Ahmed",
        full_name="Tanvir Ahmed",
        gender="Male",
        date_of_birth=date(2010, 8, 20),
        admission_date=date(2026, 1, 5),
        class_id=cls10.id,
        section_id=sec.id,
        academic_year_id=ay.id,
        status=StudentStatus.ACTIVE,
        phone="+8801711000002",
    )
    session.add_all([s1, s2])
    session.commit()

    FeeService.seed_default_fee_categories(session)
    AccountingService.seed_default_categories(session)

    yield session
    session.close()
    engine.dispose()


def test_fee_categories_monthly_batch_and_concessions(db_session):
    assert CURRENT_SCHEMA_VERSION >= 9
    cats = FeeRepository.get_categories(db_session)
    codes = {c.code for c in cats}
    assert {"TUI", "ADM", "EXM", "LIB", "TRN", "HST", "DEV", "OTH"}.issubset(codes)

    tui = FeeRepository.get_category_by_code(db_session, "TUI")
    cls10 = db_session.query(SchoolClass).first()
    ay = db_session.query(AcademicYear).first()

    # Batch generate March 2026 monthly tuition fees
    struct, count, msg = FeeService.generate_monthly_fees(
        db_session,
        category_id=tui.id,
        class_id=cls10.id,
        academic_year_id=ay.id,
        month=3,
        year=2026,
        amount=3000.0,
        due_date=date(2026, 3, 10),
        current_user="bursar",
    )
    assert struct is not None
    assert count == 2

    # Re-running same month must not duplicate invoices
    _, count_again, _ = FeeService.generate_monthly_fees(
        db_session,
        category_id=tui.id,
        class_id=cls10.id,
        academic_year_id=ay.id,
        month=3,
        year=2026,
        amount=3000.0,
        current_user="bursar",
    )
    assert count_again == 0

    invoices, total = FeeRepository.get_student_fees(db_session, class_id=cls10.id)
    assert total == 2
    inv1, inv2 = invoices[0], invoices[1]
    assert inv1.invoice_number.startswith("INV-")

    # Apply Discount + Scholarship + Waiver on inv1
    inv1, err1 = FeeService.apply_adjustment(
        db_session, inv1.id, "Scholarship", 500.0, "Merit Board Top 5%", current_user="principal"
    )
    assert inv1 is not None
    inv1, err2 = FeeService.apply_adjustment(
        db_session, inv1.id, "Waiver", 250.0, "Sibling concession", current_user="principal"
    )
    inv1, err3 = FeeService.apply_adjustment(
        db_session, inv1.id, "Discount", 250.0, "Early bird pay", current_user="bursar"
    )
    assert inv1.scholarship_amount == 500.0
    assert inv1.waiver_amount == 250.0
    assert inv1.discount_amount == 1000.0
    assert inv1.net_amount == 2000.0
    assert inv1.due_amount == 2000.0
    assert db_session.query(FeeAdjustment).filter_by(student_fee_id=inv1.id).count() == 3


def test_all_payment_channels_partial_advance_refund_and_cancellation(db_session):
    stu = db_session.query(Student).filter_by(student_id="STU-2026-0001").first()
    tr_cat = FeeRepository.get_category_by_code(db_session, "TRN")
    hst_cat = FeeRepository.get_category_by_code(db_session, "HST")

    # Individual invoices for Transport and Hostel
    inv_trn, _ = FeeService.create_student_invoice(
        db_session, stu.id, tr_cat.id, 1500.0, due_date=date(2026, 2, 1), title="Feb Transport Fee"
    )
    inv_hst, _ = FeeService.create_student_invoice(
        db_session, stu.id, hst_cat.id, 4000.0, due_date=date(2026, 3, 1), title="March Hostel Fee"
    )

    # Partial payment via Mobile Banking (bKash alias normalized) and Card
    p1, _ = FeeService.collect_fee_payment(
        db_session, inv_trn.id, 500.0, payment_method="bKash", transaction_id="BK-1001", current_user="cashier"
    )
    assert p1.payment_method == "Mobile Banking"
    assert p1.channel_detail == "bKash"

    p2, _ = FeeService.collect_fee_payment(
        db_session, inv_trn.id, 500.0, payment_method="Card", channel_detail="VISA", transaction_id="CARD-22", current_user="cashier"
    )
    assert p2.payment_method == "Card"

    # Advance Credit Wallet Deposit (Bank) + Partial Allocation
    adv_dep, _ = FeeService.record_advance_payment(
        db_session, stu.id, 2000.0, payment_method="Bank", reference_no="SLIP-778", current_user="cashier"
    )
    assert adv_dep is not None
    assert FeeRepository.get_student_advance_balance(db_session, stu.id) == 2000.0

    # Settle remaining 500 of Transport invoice from Advance Wallet
    p_adv, _ = FeeService.apply_advance_to_invoice(db_session, inv_trn.id, current_user="cashier")
    assert p_adv is not None
    assert p_adv.is_advance_allocation is True
    assert FeeRepository.get_student_advance_balance(db_session, stu.id) == 1500.0

    db_session.refresh(inv_trn)
    assert inv_trn.status == "Paid"
    assert inv_trn.due_amount == 0.0

    # Invoice cancellation must be BLOCKED while net payments remain unrefunded
    cancelled_blocked, blk_msg = FeeService.cancel_invoice(
        db_session, inv_trn.id, "Duplicate billing", current_user="admin"
    )
    assert cancelled_blocked is None
    assert "unrefunded" in blk_msg.lower()

    # Refund p1 (500) -> Payment becomes Refunded and accounting Expense reversal posted
    refund, r_msg = FeeService.process_refund(
        db_session, p1.id, 500.0, refund_method="Cash", reason="Overcharged route tier", current_user="bursar"
    )
    assert refund is not None
    assert refund.refund_no.startswith("RFD-")
    db_session.refresh(p1)
    assert p1.status == "Refunded"
    assert p1.refunded_amount == 500.0

    # Cancel completely unpaid inv_hst cleanly
    cancelled_hst, _ = FeeService.cancel_invoice(
        db_session, inv_hst.id, "Student opted out of hostel", current_user="admin"
    )
    assert cancelled_hst is not None
    assert cancelled_hst.status == "Cancelled"
    assert cancelled_hst.due_amount == 0.0


def test_immutability_prohibits_deletion_and_reversal_balances_ledger(db_session):
    inc_cat = AccountingRepository.get_category_by_code(db_session, "INC-DONT")
    exp_cat = AccountingRepository.get_category_by_code(db_session, "EXP-UTIL")

    tx_in, err = AccountingService.record_transaction(
        db_session,
        {
            "type": "Income",
            "category_id": inc_cat.id,
            "amount": 25000.0,
            "transaction_date": date(2026, 4, 5),
            "payment_method": "Bank",
            "paid_to_received_from": "Alumni Endowment",
            "description": "Library grant",
        },
        actor_username="accountant",
    )
    assert err is None

    tx_err, _ = AccountingService.record_transaction(
        db_session,
        {
            "type": "Expense",
            "category_id": exp_cat.id,
            "amount": 10000.0,
            "transaction_date": date(2026, 4, 6),
            "payment_method": "Cash",
            "paid_to_received_from": "Mistaken Utility Entry",
        },
        actor_username="accountant",
    )

    # Permanent deletion MUST fail at repository AND ORM levels
    with pytest.raises(ValueError, match="prohibited"):
        AccountingRepository.delete_transaction(db_session, tx_err.id)
    with pytest.raises(ValueError, match="prohibited"):
        FeeRepository.delete_invoice(db_session, 1)
    with pytest.raises(ValueError, match="prohibited"):
        FeeRepository.delete_payment(db_session, 1)

    db_session.delete(tx_err)
    with pytest.raises(ValueError, match="prohibited"):
        db_session.commit()
    db_session.rollback()

    # Reverse the mistaken 10,000 Cash Expense cleanly
    contra, rev_msg = AccountingService.reverse_transaction(
        db_session, tx_err.id, reason="Duplicate electric bill entry", actor_username="auditor"
    )
    assert contra is not None
    assert contra.entry_kind == "Reversal"
    assert contra.type == "Income"
    assert contra.reversal_of_id == tx_err.id

    db_session.refresh(tx_err)
    assert tx_err.is_reversed is True
    assert tx_err.status == "Reversed"

    # Reversal must balance Summary & General Ledger cleanly to 25,000 Bank / 0 Cash
    summary = AccountingRepository.get_financial_summary(db_session)
    assert summary["total_income"] == 25000.0
    assert summary["total_expense"] == 0.0
    assert summary["net_surplus"] == 25000.0
    assert summary["cash_in_hand"] == 0.0
    assert summary["channel_balances"]["Bank"] == 25000.0

    ledger = AccountingService.get_general_ledger(db_session)
    assert ledger["closing_balance"] == 25000.0
    assert ledger["entry_count"] == 3  # Original Income + Mistaken Expense + Contra Reversal


def test_budgets_due_collection_audit_and_all_pdfs_excel(db_session, tmp_path):
    stu = db_session.query(Student).first()
    exm_cat = FeeRepository.get_category_by_code(db_session, "EXM")
    exp_cat = AccountingRepository.get_category_by_code(db_session, "EXP-EXAM")
    school = db_session.query(SchoolSetting).first()

    # Create overdue invoice + collect partial payment
    inv, _ = FeeService.create_student_invoice(
        db_session, stu.id, exm_cat.id, 2000.0, due_date=date.today() - timedelta(days=45), title="Midterm Exam Fee"
    )
    pmt, _ = FeeService.collect_fee_payment(
        db_session, inv.id, 800.0, payment_method="Other", channel_detail="PayOrder", current_user="cashier"
    )

    # Budget setup + overspend alert
    budget, _ = AccountingService.create_or_update_budget(
        db_session,
        {"category_id": exp_cat.id, "title": "Exam Logistics FY26", "fiscal_year": date.today().year, "allocated_amount": 5000.0},
        actor_username="principal",
    )
    assert budget is not None
    AccountingService.record_transaction(
        db_session,
        {"type": "Expense", "category_id": exp_cat.id, "amount": 6200.0, "payment_method": "Cash", "paid_to_received_from": "Press"},
        actor_username="accountant",
    )

    b_rep = AccountingService.get_budget_variance_report(db_session, fiscal_year=date.today().year)
    assert b_rep["over_budget_count"] == 1
    assert b_rep["rows"][0]["alert_status"] == "Over Budget"

    due_rep = FeeRepository.get_due_report(db_session, overdue_only=True)
    assert due_rep["total_due"] == 1200.0
    assert due_rep["aging_summary"]["31-60 Days"] == 1200.0

    col_rep = FeeRepository.get_collection_report(db_session)
    assert col_rep["net_collected"] == 800.0
    assert col_rep["by_channel"]["Other"] == 800.0

    comp_sum = AccountingService.get_comprehensive_financial_summary(db_session)
    assert comp_sum["fee_receivables"]["outstanding_due"] == 1200.0
    assert db_session.query(FinancialAuditLog).count() >= 5

    # Generate all PDFs & Excel files
    inv_pdf = str(tmp_path / "invoice.pdf")
    rec_pdf = str(tmp_path / "receipt.pdf")
    due_pdf = str(tmp_path / "due.pdf")
    col_pdf = str(tmp_path / "collection.pdf")
    cb_pdf = str(tmp_path / "cashbook.pdf")
    bdg_pdf = str(tmp_path / "budget.pdf")
    stmt_pdf = str(tmp_path / "statement.pdf")
    due_xlsx = str(tmp_path / "due.xlsx")
    col_xlsx = str(tmp_path / "collection.xlsx")
    cb_xlsx = str(tmp_path / "cashbook.xlsx")

    assert FinancePDFGenerator.generate_invoice_pdf(inv, school, inv_pdf) is True
    assert FeeReceiptPDFGenerator.generate_receipt(pmt, school, rec_pdf) is True
    assert FinancePDFGenerator.generate_due_report_pdf(due_rep, school, due_pdf) is True
    assert FinancePDFGenerator.generate_collection_report_pdf(col_rep, school, col_pdf) is True
    assert FinancePDFGenerator.generate_cashbook_pdf(AccountingService.get_general_ledger(db_session), school, cb_pdf) is True
    assert FinancePDFGenerator.generate_budget_report_pdf(b_rep, school, bdg_pdf) is True
    assert FinancialStatementPDFGenerator.generate_statement(
        comp_sum, comp_sum["income_breakdown"], comp_sum["expense_breakdown"],
        {"name": school.school_name, "eiin": school.eiin_number}, f"FY {date.today().year}", stmt_pdf
    ) is True
    assert FeeService.export_due_report_excel(db_session, due_xlsx) is True
    assert FeeService.export_collection_report_excel(db_session, col_xlsx) is True
    assert AccountingService.export_cash_book_excel(db_session, cb_xlsx) is True

    for fpath in (inv_pdf, rec_pdf, due_pdf, col_pdf, cb_pdf, bdg_pdf, stmt_pdf, due_xlsx, col_xlsx, cb_xlsx):
        assert os.path.exists(fpath) and os.path.getsize(fpath) > 500
