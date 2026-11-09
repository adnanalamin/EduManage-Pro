"""
EduManage Pro - Fees & Billing Module Unit Tests
Tests FeeCategory, FeeStructure, StudentFee invoices, payment collection,
partial payments, discounts, receipt generation, and ReportLab PDF voucher output.
"""

import pytest
import os
import tempfile
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.connection import Base
from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.student import Student
from app.models.fee import FeeCategory, FeeStructure, StudentFee, FeePayment
from app.repositories.fee_repository import FeeRepository
from app.services.fee_service import FeeService
from app.reports.fee_receipt_pdf import FeeReceiptPDFGenerator


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed academic year, class, section, and student
    ay = AcademicYear(name="2025-2026", start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), is_current=True)
    session.add(ay)
    session.flush()

    cls_obj = SchoolClass(name="Class 10", code="C10", numeric_order=10, academic_year_id=ay.id)
    session.add(cls_obj)
    session.flush()

    sec = Section(name="Section A", class_id=cls_obj.id, capacity=40)
    session.add(sec)
    session.flush()

    stu = Student(
        student_id="STU-2026-0001",
        admission_number="ADM-1001",
        roll_number="01",
        first_name="Rahim",
        last_name="Chowdhury",
        full_name="Rahim Chowdhury",
        gender="Male",
        date_of_birth=date(2010, 5, 20),
        admission_date=date(2025, 1, 10),
        class_id=cls_obj.id,
        section_id=sec.id,
        academic_year_id=ay.id,
        status="Active"
    )
    session.add(stu)
    session.commit()

    yield session
    session.close()


def test_seed_default_fee_categories(db_session):
    count = FeeService.seed_default_categories(db_session)
    assert count >= 7

    cats = FeeRepository.get_all_categories(db_session)
    names = [c.name for c in cats]
    assert "Tuition Fee" in names
    assert "Admission Fee" in names
    assert "Exam Fee" in names
    assert "Development Fee" in names


def test_fee_structure_creation(db_session):
    cat = FeeRepository.create_category(db_session, {
        "name": "ICT Lab Fee",
        "description": "Computer laboratory maintenance",
        "is_recurring": True
    })
    cls_obj = db_session.query(SchoolClass).first()
    ay = db_session.query(AcademicYear).first()

    structure, err = FeeService.create_fee_structure(db_session, {
        "category_id": cat.id,
        "class_id": cls_obj.id,
        "academic_year_id": ay.id,
        "title": "Class 10 Monthly ICT Lab Fee",
        "amount": 450.0,
        "due_date": date(2025, 3, 10)
    })
    assert err is None
    assert structure is not None
    assert structure.amount == 450.0
    assert structure.title == "Class 10 Monthly ICT Lab Fee"


def test_batch_assign_fee_to_class(db_session):
    cat = FeeRepository.create_category(db_session, {"name": "Tuition Fee", "is_recurring": True})
    cls_obj = db_session.query(SchoolClass).first()
    ay = db_session.query(AcademicYear).first()

    structure = FeeRepository.create_fee_structure(db_session, {
        "category_id": cat.id,
        "class_id": cls_obj.id,
        "academic_year_id": ay.id,
        "title": "March 2025 Tuition Fee",
        "amount": 2500.0,
        "due_date": date(2025, 3, 15)
    })

    created_count = FeeRepository.batch_assign_fee_to_class(db_session, structure.id, cls_obj.id)
    assert created_count == 1  # 1 student in class 10

    invoices = FeeRepository.get_student_fees(db_session, student_id=db_session.query(Student).first().id)
    assert len(invoices) == 1
    inv = invoices[0]
    assert inv.total_amount == 2500.0
    assert inv.due_amount == 2500.0
    assert inv.status == "Unpaid"


def test_payment_collection_workflow(db_session):
    cat = FeeRepository.create_category(db_session, {"name": "Annual Tuition", "is_recurring": False})
    cls_obj = db_session.query(SchoolClass).first()
    stu = db_session.query(Student).first()
    ay = db_session.query(AcademicYear).first()

    structure = FeeRepository.create_fee_structure(db_session, {
        "category_id": cat.id,
        "class_id": cls_obj.id,
        "academic_year_id": ay.id,
        "title": "Q1 Tuition",
        "amount": 3000.0,
        "due_date": date(2025, 3, 15)
    })
    FeeRepository.batch_assign_fee_to_class(db_session, structure.id, cls_obj.id)
    inv = FeeRepository.get_student_fees(db_session)[0]

    # Partial payment of 1000 with 200 scholarship discount
    pmt1, err1 = FeeService.collect_payment(db_session, {
        "student_fee_id": inv.id,
        "amount": 1000.0,
        "discount_amount": 200.0,
        "payment_method": "bKash",
        "transaction_ref": "TRX998877",
        "received_by": "Cashier Office"
    })
    assert err1 is None
    assert pmt1 is not None
    assert pmt1.receipt_number.startswith("REC-")
    
    db_session.refresh(inv)
    assert inv.discount_amount == 200.0
    assert inv.net_amount == 2800.0
    assert inv.paid_amount == 1000.0
    assert inv.due_amount == 1800.0
    assert inv.status == "Partial"

    # Attempt to overpay beyond due amount should fail
    pmt_over, err_over = FeeService.collect_payment(db_session, {
        "student_fee_id": inv.id,
        "amount": 2500.0,
        "payment_method": "Cash"
    })
    assert pmt_over is None
    assert "exceeds balance due" in err_over

    # Settle remaining 1800
    pmt2, err2 = FeeService.collect_payment(db_session, {
        "student_fee_id": inv.id,
        "amount": 1800.0,
        "payment_method": "Bank Transfer",
        "transaction_ref": "SLIP-4501",
        "received_by": "Accountant"
    })
    assert err2 is None
    assert pmt2 is not None

    db_session.refresh(inv)
    assert inv.paid_amount == 2800.0
    assert inv.due_amount == 0.0
    assert inv.status == "Paid"


def test_pdf_receipt_generation(db_session):
    cat = FeeRepository.create_category(db_session, {"name": "Admission Fee", "is_recurring": False})
    cls_obj = db_session.query(SchoolClass).first()
    stu = db_session.query(Student).first()
    ay = db_session.query(AcademicYear).first()

    structure = FeeRepository.create_fee_structure(db_session, {
        "category_id": cat.id,
        "class_id": cls_obj.id,
        "academic_year_id": ay.id,
        "title": "New Admission Session 2025",
        "amount": 5000.0,
        "due_date": date(2025, 1, 31)
    })
    FeeRepository.batch_assign_fee_to_class(db_session, structure.id, cls_obj.id)
    inv = FeeRepository.get_student_fees(db_session)[0]

    pmt, _ = FeeService.collect_payment(db_session, {
        "student_fee_id": inv.id,
        "amount": 5000.0,
        "payment_method": "Cash",
        "received_by": "Senior Accountant"
    })

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        out_path = tf.name

    try:
        success = FeeReceiptPDFGenerator.generate_receipt(
            payment=pmt,
            school_info={
                "name": "Dhaka Residential Model School",
                "eiin": "108254",
                "phone": "+880 2 9110000",
                "address": "Mohammadpur, Dhaka-1207"
            },
            output_path=out_path
        )
        assert success is True
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 1000
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)
