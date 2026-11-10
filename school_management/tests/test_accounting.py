"""
EduManage Pro - Accounting Module Unit Tests (Pytest)
Tests Chart of Accounts, Income & Expense Vouchers, Cash Book Ledger, P&L, and PDF/Excel Reports.
"""

import pytest
import os
import tempfile
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.connection import Base
from app.models.accounting import AccountCategory, AccountTransaction
from app.repositories.accounting_repository import AccountingRepository
from app.services.accounting_service import AccountingService
from app.reports.financial_statement_pdf import FinancialStatementPDFGenerator


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session
    session.close()


def test_seed_default_categories(db_session):
    count = AccountingService.seed_default_categories(db_session)
    assert count >= 10

    cats = AccountingRepository.get_all_categories(db_session)
    codes = [c.code for c in cats]
    assert "INC-FEES" in codes
    assert "EXP-TSAL" in codes
    assert "EXP-UTIL" in codes

    # Re-seeding must not create duplicates
    count_again = AccountingService.seed_default_categories(db_session)
    assert count_again == 0


def test_create_and_delete_custom_category(db_session):
    cat = AccountingRepository.create_category(db_session, {
        "name": "Robotics Lab Equipment",
        "code": "EXP-ROBO",
        "type": "Expense",
        "description": "Robotics components and 3D printing filament"
    })
    assert cat.id is not None
    assert cat.name == "Robotics Lab Equipment"

    # Delete without transactions should succeed
    ok, msg = AccountingRepository.delete_category(db_session, cat.id)
    assert ok is True


def test_record_income_and_expense_vouchers(db_session):
    AccountingService.seed_default_categories(db_session)
    inc_cat = AccountingRepository.get_category_by_code(db_session, "INC-FEES")
    exp_cat = AccountingRepository.get_category_by_code(db_session, "EXP-TSAL")

    # Record Income Voucher
    tx_inc, err_inc = AccountingService.record_transaction(db_session, {
        "type": "Income",
        "category_id": inc_cat.id,
        "amount": 75000.0,
        "transaction_date": date(2026, 3, 1),
        "payment_method": "Bank Transfer",
        "reference_no": "TRX-889900",
        "paid_to_received_from": "Student Fee Counter Batch March",
        "description": "Consolidated monthly tuition fee collections"
    })
    assert err_inc is None
    assert tx_inc is not None
    assert tx_inc.voucher_no.startswith("VCH-2026-INC-")
    assert tx_inc.amount == 75000.0

    # Record Expense Voucher
    tx_exp, err_exp = AccountingService.record_transaction(db_session, {
        "type": "Expense",
        "category_id": exp_cat.id,
        "amount": 45000.0,
        "transaction_date": date(2026, 3, 5),
        "payment_method": "Cash",
        "paid_to_received_from": "Kamal Hossain (Senior Faculty)",
        "description": "February 2026 salary disbursement"
    })
    assert err_exp is None
    assert tx_exp is not None
    assert tx_exp.voucher_no.startswith("VCH-2026-EXP-")
    assert tx_exp.amount == 45000.0

    # Invalid amount validation
    _, err_zero = AccountingService.record_transaction(db_session, {
        "type": "Expense",
        "category_id": exp_cat.id,
        "amount": -50.0,
        "paid_to_received_from": "Vendor"
    })
    assert err_zero is not None
    assert "greater than 0" in err_zero


def test_financial_summary_and_cash_book(db_session):
    AccountingService.seed_default_categories(db_session)
    inc_cat = AccountingRepository.get_category_by_code(db_session, "INC-FEES")
    exp_cat = AccountingRepository.get_category_by_code(db_session, "EXP-UTIL")

    # Income 1: 50,000 Cash
    AccountingService.record_transaction(db_session, {
        "type": "Income",
        "category_id": inc_cat.id,
        "amount": 50000.0,
        "payment_method": "Cash",
        "paid_to_received_from": "Donations"
    })

    # Income 2: 30,000 Bank
    AccountingService.record_transaction(db_session, {
        "type": "Income",
        "category_id": inc_cat.id,
        "amount": 30000.0,
        "payment_method": "Bank Transfer",
        "paid_to_received_from": "Govt Grant"
    })

    # Expense 1: 20,000 Cash
    AccountingService.record_transaction(db_session, {
        "type": "Expense",
        "category_id": exp_cat.id,
        "amount": 20000.0,
        "payment_method": "Cash",
        "paid_to_received_from": "DESCO Electric Utility"
    })

    summary = AccountingRepository.get_financial_summary(db_session)
    assert summary["total_income"] == 80000.0
    assert summary["total_expense"] == 20000.0
    assert summary["net_surplus"] == 60000.0
    assert summary["cash_in_hand"] == 30000.0  # 50,000 cash in - 20,000 cash out
    assert summary["is_profit"] is True


def test_export_cash_book_excel(db_session):
    AccountingService.seed_default_categories(db_session)
    inc_cat = AccountingRepository.get_category_by_code(db_session, "INC-FEES")
    exp_cat = AccountingRepository.get_category_by_code(db_session, "EXP-STAT")

    AccountingService.record_transaction(db_session, {
        "type": "Income",
        "category_id": inc_cat.id,
        "amount": 10000.0,
        "paid_to_received_from": "Admissions"
    })
    AccountingService.record_transaction(db_session, {
        "type": "Expense",
        "category_id": exp_cat.id,
        "amount": 3500.0,
        "paid_to_received_from": "Stationery Shop"
    })

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tf:
        out_excel = tf.name

    try:
        ok = AccountingService.export_cash_book_excel(db_session, out_excel)
        assert ok is True
        assert os.path.exists(out_excel)
        assert os.path.getsize(out_excel) > 1000
    finally:
        if os.path.exists(out_excel):
            os.remove(out_excel)


def test_generate_financial_statement_pdf(db_session):
    AccountingService.seed_default_categories(db_session)
    inc_cat = AccountingRepository.get_category_by_code(db_session, "INC-FEES")
    exp_cat = AccountingRepository.get_category_by_code(db_session, "EXP-TSAL")

    AccountingService.record_transaction(db_session, {
        "type": "Income",
        "category_id": inc_cat.id,
        "amount": 120000.0,
        "paid_to_received_from": "Tuition March"
    })
    AccountingService.record_transaction(db_session, {
        "type": "Expense",
        "category_id": exp_cat.id,
        "amount": 80000.0,
        "paid_to_received_from": "Teacher Payroll"
    })

    summary = AccountingRepository.get_financial_summary(db_session)
    inc_breakdown = AccountingRepository.get_category_breakdown(db_session, trans_type="Income")
    exp_breakdown = AccountingRepository.get_category_breakdown(db_session, trans_type="Expense")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        out_pdf = tf.name

    try:
        ok = FinancialStatementPDFGenerator.generate_statement(
            summary=summary,
            income_breakdown=inc_breakdown,
            expense_breakdown=exp_breakdown,
            school_info={"name": "Dhaka Residential Model High School", "eiin": "108254"},
            period_str="FY 2026",
            output_path=out_pdf
        )
        assert ok is True
        assert os.path.exists(out_pdf)
        assert os.path.getsize(out_pdf) > 2000
    finally:
        if os.path.exists(out_pdf):
            os.remove(out_pdf)
