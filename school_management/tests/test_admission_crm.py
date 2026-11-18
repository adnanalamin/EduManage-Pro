"""
EduManage Pro - Admission CRM Automated Tests (Pytest)
Verifies:
- Application creation, Applicant ID generation & duplicate prevention
- All 8 application statuses & immutable status history
- Configurable admission fee schedules & payment receipts
- Document checklist submission & verification
- Entrance test scoring, Interview evaluation, Merit List ranking & Waitlist promotion
- Admission approval & atomic Student CRM conversion (+ duplicate conversion protection)
- PDF exports: Admission Form, Applicant Receipt, Admit Card, Merit List
- Excel export & bulk import + Admission statistics + RBAC checks
"""

import os
import tempfile
from datetime import date

import openpyxl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.connection import Base
from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.admission import (
    AdmissionApplication,
    AdmissionFeeConfig,
    AdmissionFeePayment,
    AdmissionStatus,
)
from app.models.school import SchoolSetting
from app.models.student import Student, StudentDocument
from app.models.user import Role, User
from app.repositories.admission_repository import AdmissionRepository
from app.security.hasher import PasswordHasher
from app.services.admission_service import AdmissionService
from app.services.auth_service import AuthService


@pytest.fixture(scope="function")
def adm_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    db.add(SchoolSetting(school_name="Ideal Model Academy", eiin_number="134211", currency_code="BDT", currency_symbol="৳"))
    ay = AcademicYear(name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True)
    db.add(ay)
    db.flush()

    cls6 = SchoolClass(name="Class 6", code="C6", numeric_order=6, academic_year_id=ay.id)
    cls7 = SchoolClass(name="Class 7", code="C7", numeric_order=7, academic_year_id=ay.id)
    db.add_all([cls6, cls7])
    db.flush()

    sec6a = Section(name="Section A", room_number="101", capacity=40, class_id=cls6.id)
    db.add(sec6a)
    db.commit()

    yield db
    db.close()


def _base_app(ay_id: int, cls_id: int, fname: str, lname: str, phone: str, gpa: float = 4.5, bc: str = None):
    return {
        "academic_year_id": ay_id,
        "applying_class_id": cls_id,
        "first_name": fname,
        "last_name": lname,
        "gender": "Male",
        "date_of_birth": date(2014, 4, 15),
        "birth_certificate_no": bc,
        "guardian_name": f"Guardian of {fname}",
        "guardian_phone": phone,
        "previous_school": "Greenfield Primary",
        "previous_gpa": gpa,
        "source_channel": "Website",
    }


def test_configurable_fees_intake_statuses_and_checklist(adm_db):
    db = adm_db
    ay = db.query(AcademicYear).first()
    cls6 = db.query(SchoolClass).filter_by(code="C6").first()

    # Configure class-specific fee schedule & quota
    ok, cfg, _ = AdmissionService.configure_fee_schedule(
        db,
        academic_year_id=ay.id,
        class_id=cls6.id,
        fee_name="Class 6 Entry Schedule 2026",
        application_fee=600.0,
        admission_test_fee=400.0,
        enrollment_fee=8000.0,
        seat_quota=2,
        test_pass_percentage=50.0,
        test_weight_pct=70.0,
        interview_weight_pct=30.0,
    )
    assert ok is True and cfg.seat_quota == 2

    # Submit application
    ok, app1, msg = AdmissionService.submit_application(
        db, _base_app(ay.id, cls6.id, "Zayan", "Ahmed", "+8801711000001", bc="BC-2014-001")
    )
    assert ok is True
    assert app1.applicant_id.startswith("APP-")
    assert app1.status == AdmissionStatus.APPLIED
    assert len(app1.checklist_items) == 6

    # Duplicate birth cert / identity rejected
    ok_dup, _, dup_msg = AdmissionService.submit_application(
        db, _base_app(ay.id, cls6.id, "Zayan", "Ahmed", "+8801711000001", bc="BC-2014-001")
    )
    assert ok_dup is False
    assert "Duplicate" in dup_msg

    # Update & verify required documents -> automatically moves Applied -> Under Review
    for code in ("BIRTH_CERT", "PHOTO", "PREV_MARKSHEET", "GUARDIAN_NID"):
        ok_chk, _, _ = AdmissionService.update_checklist_item(
            db, app1.id, code, is_submitted=True, is_verified=True, file_path=f"/vault/{code}.pdf"
        )
        assert ok_chk is True

    app1_refreshed = AdmissionRepository.get_by_id(db, app1.id)
    assert app1_refreshed.status == AdmissionStatus.UNDER_REVIEW
    chk_summary = AdmissionService.get_checklist_summary(app1_refreshed)
    assert chk_summary["all_required_verified"] is True

    # Collect configured Application Fee -> receipt generated using 600.0
    ok_pay, payment, _ = AdmissionService.record_fee_payment(
        db, app1.id, fee_type="Application Fee", payment_method="Card"
    )
    assert ok_pay is True
    assert payment.amount_due == 600.0
    assert payment.amount_paid == 600.0
    assert payment.payment_status == "Paid"
    assert payment.receipt_no.startswith("ADM-RCPT-")


def test_test_interview_merit_waitlist_approval_and_student_conversion(adm_db):
    db = adm_db
    AuthService.sync_permission_catalog(db)
    ay = db.query(AcademicYear).first()
    cls6 = db.query(SchoolClass).filter_by(code="C6").first()
    sec6a = db.query(Section).filter_by(class_id=cls6.id).first()

    # Quota = 2 seats for Class 6
    AdmissionService.configure_fee_schedule(
        db, ay.id, cls6.id, seat_quota=2, test_pass_percentage=40.0, test_weight_pct=70.0, interview_weight_pct=30.0
    )

    _, a1, _ = AdmissionService.submit_application(db, _base_app(ay.id, cls6.id, "Rafi", "Khan", "+8801700000011", gpa=5.0))
    _, a2, _ = AdmissionService.submit_application(db, _base_app(ay.id, cls6.id, "Sara", "Noor", "+8801700000012", gpa=4.8))
    _, a3, _ = AdmissionService.submit_application(db, _base_app(ay.id, cls6.id, "Nabil", "Chowdhury", "+8801700000013", gpa=4.6))
    _, a4, _ = AdmissionService.submit_application(db, _base_app(ay.id, cls6.id, "Farhan", "Sadiq", "+8801700000014", gpa=4.0))

    # Entrance tests: a1=90%, a2=80%, a3=70%, a4=30% (Failed)
    AdmissionService.schedule_or_score_test(db, a1.id, exam_date=date.today(), obtained_marks=90, max_marks=100)
    AdmissionService.schedule_or_score_test(db, a2.id, exam_date=date.today(), obtained_marks=80, max_marks=100)
    AdmissionService.schedule_or_score_test(db, a3.id, exam_date=date.today(), obtained_marks=70, max_marks=100)
    _, t4, _ = AdmissionService.schedule_or_score_test(db, a4.id, exam_date=date.today(), obtained_marks=30, max_marks=100)
    assert t4.result_status == "Failed"

    db.refresh(a1)
    assert a1.status == AdmissionStatus.SHORTLISTED

    # Interviews: a1=90, a2=85, a3=75 -> advances status to Interview
    AdmissionService.schedule_or_record_interview(db, a1.id, communication_score=9.0, aptitude_score=9.0, recommendation="Recommended")
    AdmissionService.schedule_or_record_interview(db, a2.id, communication_score=8.5, aptitude_score=8.5, recommendation="Recommended")
    AdmissionService.schedule_or_record_interview(db, a3.id, communication_score=7.5, aptitude_score=7.5, recommendation="Waitlist")
    db.refresh(a1)
    assert a1.status == AdmissionStatus.INTERVIEW

    # Generate Merit List (quota=2 -> a1 & a2 Selected, a3 Waitlisted #1, a4 Failed excluded)
    ok_m, rows, _ = AdmissionService.generate_merit_list(db, ay.id, cls6.id, seat_quota=2)
    assert ok_m is True
    assert len(rows) == 3
    assert rows[0]["applicant_id"] == a1.applicant_id and rows[0]["status"] == AdmissionStatus.SELECTED
    assert rows[1]["applicant_id"] == a2.applicant_id and rows[1]["status"] == AdmissionStatus.SELECTED
    assert rows[2]["applicant_id"] == a3.applicant_id and rows[2]["status"] == AdmissionStatus.WAITLISTED
    assert rows[2]["waitlist_position"] == 1

    # Explicitly reject a4
    ok_rej, a4_upd, _ = AdmissionService.transition_status(db, a4.id, AdmissionStatus.REJECTED, remarks="Did not pass entrance test")
    assert ok_rej is True and a4_upd.status == AdmissionStatus.REJECTED

    # Promote waitlisted candidate a3 -> Selected
    ok_prom, promoted, _ = AdmissionService.promote_from_waitlist(db, ay.id, cls6.id, count=1)
    assert ok_prom is True and len(promoted) == 1 and promoted[0].id == a3.id
    db.refresh(a3)
    assert a3.status == AdmissionStatus.SELECTED

    # RBAC check: teacher cannot approve admission; super_admin can
    teacher_role = db.query(Role).filter_by(name="teacher").first()
    admin_role = db.query(Role).filter_by(name="super_admin").first()
    u_tch = User(
        username="adm_tch", email="admtch@school.local", full_name="Teacher",
        password_hash=PasswordHasher.hash_password("StrongPass!123"), role_id=teacher_role.id, is_active=True
    )
    u_adm = User(
        username="adm_principal", email="admprin@school.local", full_name="Principal",
        password_hash=PasswordHasher.hash_password("StrongPass!123"), role_id=admin_role.id, is_active=True
    )
    db.add_all([u_tch, u_adm])
    db.commit()

    with pytest.raises(PermissionError):
        AdmissionService.approve_admission(db, a1.id, actor_user=u_tch)

    # Mark checklist submitted for a1 to verify document transfer on student conversion
    AdmissionService.update_checklist_item(db, a1.id, "BIRTH_CERT", is_submitted=True, is_verified=True, file_path="/tmp/bc.pdf")

    ok_app, _, _ = AdmissionService.approve_admission(db, a1.id, actor_user=u_adm)
    assert ok_app is True

    # Convert a1 -> Student CRM
    ok_conv, student, _ = AdmissionService.convert_to_student(db, a1.id, section_id=sec6a.id, actor_user=u_adm)
    assert ok_conv is True and student is not None
    assert student.full_name == "Rafi Khan"
    assert student.class_id == cls6.id and student.section_id == sec6a.id
    db.refresh(a1)
    assert a1.status == AdmissionStatus.ADMITTED
    assert a1.converted_student_id == student.id
    assert db.query(StudentDocument).filter_by(student_id=student.id).count() >= 1

    # Double conversion blocked cleanly
    ok_conv2, _, msg_conv2 = AdmissionService.convert_to_student(db, a1.id, actor_user=u_adm)
    assert ok_conv2 is False and "already been converted" in msg_conv2

    # Generate all 4 PDFs cleanly
    _, pay, _ = AdmissionService.record_fee_payment(db, a1.id, fee_type="Enrollment Fee")
    with tempfile.TemporaryDirectory() as tmpdir:
        p_form = AdmissionService.export_admission_form_pdf(db, a1.id, os.path.join(tmpdir, "form.pdf"))
        p_rcpt = AdmissionService.export_applicant_receipt_pdf(db, pay.id, os.path.join(tmpdir, "receipt.pdf"))
        p_admit = AdmissionService.export_admit_card_pdf(db, a1.id, os.path.join(tmpdir, "admit_card.pdf"))
        p_merit = AdmissionService.export_merit_list_pdf(db, ay.id, cls6.id, os.path.join(tmpdir, "merit_list.pdf"))
        for p in (p_form, p_rcpt, p_admit, p_merit):
            assert os.path.exists(p) and os.path.getsize(p) > 800


def test_excel_import_export_and_admission_statistics(adm_db):
    db = adm_db
    ay = db.query(AcademicYear).first()
    cls6 = db.query(SchoolClass).filter_by(code="C6").first()

    with tempfile.TemporaryDirectory() as tmpdir:
        in_xlsx = os.path.join(tmpdir, "import_apps.xlsx")
        out_xlsx = os.path.join(tmpdir, "export_apps.xlsx")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Full Name", "Gender", "DOB", "Applying Class", "Guardian Name", "Guardian Phone", "Previous GPA"])
        ws.append(["Imran Hossain", "Male", "2014-05-10", "Class 6", "Mizan Hossain", "+8801722000001", 4.7])
        ws.append(["Tania Akter", "Female", "2014-08-22", "Class 6", "Karim Akter", "+8801722000002", 4.9])
        # Duplicate row in same sheet should be skipped gracefully
        ws.append(["Imran Hossain", "Male", "2014-05-10", "Class 6", "Mizan Hossain", "+8801722000001", 4.7])
        wb.save(in_xlsx)

        res = AdmissionService.import_applications_excel(db, in_xlsx, default_academic_year_id=ay.id, default_class_id=cls6.id)
        assert res["imported"] == 2
        assert res["skipped"] == 1

        exported = AdmissionService.export_applications_excel(db, out_xlsx)
        assert os.path.exists(exported) and os.path.getsize(exported) > 1000

    stats = AdmissionService.get_admission_statistics(db, academic_year_id=ay.id)
    assert stats["total_applications"] == 2
    assert stats["status_counts"][AdmissionStatus.APPLIED] == 2
    assert stats["source_breakdown"].get("Excel Import") == 2
    assert stats["gender_breakdown"].get("Male") == 1
    assert stats["gender_breakdown"].get("Female") == 1
