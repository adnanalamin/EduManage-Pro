"""
EduManage Pro - Professional Document Generation System Verification Suite
Tests all 10 official document types, school-agnostic Template Management,
custom logos/signatures, dynamic custom fields, sequential serial numbers,
QR verification, revocation, live preview, and ReportLab PDF generation.
"""

from datetime import date
import os
from pathlib import Path
import struct
import zlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.migrations import CURRENT_SCHEMA_VERSION, migrate_database
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.models.admission import AdmissionApplication, AdmissionFeePayment
from app.models.document import OFFICIAL_DOCUMENT_TYPES, DocumentTemplate, IssuedDocument
from app.models.exam import ExamResultSummary, ExamTerm, GradingSystem, StudentMark
from app.models.fee import FeeCategory, FeePayment, FeeStructure, StudentFee
from app.models.school import SchoolSetting
from app.models.staff import Department, Staff, Teacher
from app.models.student import Guardian, Student
from app.reports.universal_document_pdf import UniversalDocumentPDFGenerator
from app.services.document_service import DocumentService


def _write_minimal_png(path: Path, rgb: tuple = (30, 58, 138)) -> str:
    """Create a valid tiny 4x4 RGB PNG file without external dependencies."""
    w, h = 4, 4
    raw_scanlines = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack("!I", len(data)) + tag + data + struct.pack("!I", crc)

    ihdr = struct.pack("!IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw_scanlines))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png_bytes)
    return str(path)


@pytest.fixture()
def doc_env(tmp_path):
    db_file = tmp_path / "doc_test.db"
    eng = create_engine(f"sqlite:///{db_file.as_posix()}", future=True)
    res = migrate_database(eng)
    assert res["current_version"] == CURRENT_SCHEMA_VERSION

    Session = sessionmaker(bind=eng, autocommit=False, autoflush=False)
    db = Session()

    logo_file = _write_minimal_png(tmp_path / "school_logo.png", (16, 185, 129))
    sig_right_file = _write_minimal_png(tmp_path / "principal_sig.png", (15, 23, 42))
    sig_left_file = _write_minimal_png(tmp_path / "registrar_sig.png", (30, 41, 59))
    seal_file = _write_minimal_png(tmp_path / "seal.png", (180, 83, 9))
    photo_file = _write_minimal_png(tmp_path / "student_photo.png", (37, 99, 235))

    ay = AcademicYear(name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True)
    db.add(ay)
    db.flush()

    school = SchoolSetting(
        school_name="Horizon International Academy",
        motto="Knowledge, Integrity & Innovation",
        eiin_number="998877",
        address="100 Campus Boulevard, North City",
        city="Chattogram",
        country="Bangladesh",
        phone="+880-1800-112233",
        email="office@horizonacademy.edu",
        website="https://horizonacademy.edu",
        principal_name="Dr. Elena Rahman",
        logo_path=logo_file,
        principal_signature_path=sig_right_file,
        registrar_signature_path=sig_left_file,
        official_seal_path=seal_file,
        current_academic_year_id=ay.id,
        schema_version=CURRENT_SCHEMA_VERSION,
    )
    db.add(school)

    cls = SchoolClass(name="Class 10", numeric_level=10)
    db.add(cls)
    db.flush()
    sec = Section(name="Science-A", class_id=cls.id)
    db.add(sec)
    dept = Department(name="Science", code="SCI")
    db.add(dept)
    db.flush()

    guardian = Guardian(
        father_name="Tariqul Karim",
        mother_name="Nusrat Jahan",
        guardian_name="Tariqul Karim",
        relation="Father",
        guardian_phone="01711-000111",
    )
    db.add(guardian)
    db.flush()

    student = Student(
        student_id="STU-2026-001",
        admission_number="ADM-2026-001",
        roll_number=1,
        first_name="Ayan",
        last_name="Karim",
        full_name="Ayan Karim",
        gender="Male",
        date_of_birth=date(2010, 5, 14),
        blood_group="O+",
        photo_path=photo_file,
        class_id=cls.id,
        section_id=sec.id,
        guardian_id=guardian.id,
        academic_year_id=ay.id,
        admission_date=date(2024, 1, 10),
    )
    db.add(student)

    teacher = Teacher(
        teacher_id="TCH-001",
        employee_id="EMP-T-001",
        full_name="Farhana Ahmed",
        gender="Female",
        date_of_birth=date(1988, 3, 20),
        blood_group="A+",
        phone="01712-999888",
        email="farhana@horizonacademy.edu",
        qualification="M.Sc in Physics",
        designation="Senior Lecturer",
        department_id=dept.id,
        primary_subject="Physics",
    )
    db.add(teacher)

    staff = Staff(
        staff_id="STF-001",
        employee_id="EMP-S-001",
        full_name="Kamrul Hasan",
        gender="Male",
        date_of_birth=date(1985, 8, 5),
        phone="01713-777666",
        position="Senior Accountant",
        department_id=dept.id,
    )
    db.add(staff)

    # Admission Application + Payment
    adm_app = AdmissionApplication(
        applicant_id="APP-2026-010",
        form_number="FRM-010",
        academic_year_id=ay.id,
        applying_class_id=cls.id,
        first_name="Zara",
        last_name="Hossain",
        full_name="Zara Hossain",
        gender="Female",
        date_of_birth=date(2011, 2, 12),
        guardian_name="Mahmud Hossain",
        guardian_phone="01811-223344",
    )
    db.add(adm_app)
    db.flush()

    adm_pay = AdmissionFeePayment(
        application_id=adm_app.id,
        receipt_no="ADM-REC-2026-001",
        fee_type="Enrollment Fee",
        amount_due=5500.0,
        discount_amount=500.0,
        amount_paid=5000.0,
        payment_method="Bank Transfer",
        reference_no="TXN-ADM-881",
        collected_by="Admissions Desk",
    )
    db.add(adm_pay)

    # Fee Structure, Invoice & Fee Payment
    fcat = FeeCategory(name="Tuition")
    db.add(fcat)
    db.flush()
    fstruct = FeeStructure(
        title="Annual Tuition Fee",
        category_id=fcat.id,
        class_id=cls.id,
        academic_year_id=ay.id,
        amount=4000.0,
        due_date=date(2026, 4, 15),
    )
    db.add(fstruct)
    db.flush()
    sfee = StudentFee(
        invoice_no="INV-2026-0001",
        student_id=student.id,
        fee_structure_id=fstruct.id,
        academic_year_id=ay.id,
        title="March Monthly Tuition",
        total_amount=4000.0,
        discount_amount=500.0,
        net_amount=3500.0,
        paid_amount=3500.0,
        due_amount=0.0,
        status="Paid",
        due_date=date(2026, 3, 25),
    )
    db.add(sfee)
    db.flush()
    fee_pay = FeePayment(
        receipt_no="REC-2026-0001",
        student_fee_id=sfee.id,
        student_id=student.id,
        amount_paid=3500.0,
        payment_method="Mobile Banking",
        channel_detail="bKash",
        transaction_id="BKASH-90211",
        collected_by="Kamrul Hasan",
    )
    db.add(fee_pay)

    # Exam Term, Subjects, Marks & Result Summary
    gs = GradingSystem(name="National GPA 5.0", code="GPA5", max_gpa=5.0, pass_percentage=33.0)
    db.add(gs)
    db.flush()
    et = ExamTerm(
        name="Final Term Examination 2026",
        exam_code="FIN-2026",
        academic_year_id=ay.id,
        grading_system_id=gs.id,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 20),
        status="Published",
    )
    db.add(et)
    sub1 = Subject(name="Mathematics", code="MATH-101")
    sub2 = Subject(name="Physics", code="PHY-102")
    db.add_all([sub1, sub2])
    db.flush()

    db.add_all([
        StudentMark(
            exam_term_id=et.id,
            class_id=cls.id,
            subject_id=sub1.id,
            student_id=student.id,
            theory_marks=64.0,
            mcq_marks=27.0,
            practical_marks=0.0,
            viva_marks=0.0,
            attendance_marks=0.0,
            full_marks_snapshot=100.0,
            total_marks=91.0,
            grade_name="A+",
            grade_point=5.0,
            is_passed=True,
            is_locked=True,
        ),
        StudentMark(
            exam_term_id=et.id,
            class_id=cls.id,
            subject_id=sub2.id,
            student_id=student.id,
            theory_marks=48.0,
            mcq_marks=22.0,
            practical_marks=20.0,
            viva_marks=0.0,
            attendance_marks=0.0,
            full_marks_snapshot=100.0,
            total_marks=90.0,
            grade_name="A+",
            grade_point=5.0,
            is_passed=True,
            is_locked=True,
        ),
        ExamResultSummary(
            exam_term_id=et.id,
            student_id=student.id,
            class_id=cls.id,
            total_obtained=181.0,
            total_full_marks=200.0,
            percentage=90.5,
            gpa=5.0,
            cgpa=5.0,
            overall_grade="A+",
            class_rank=1,
            section_rank=1,
            attendance_percentage=96.5,
            passed_all=True,
            failed_subject_count=0,
            result_status="Published",
            is_published=True,
        ),
    ])

    db.commit()
    yield {
        "db": db,
        "tmp_path": tmp_path,
        "student": student,
        "teacher": teacher,
        "staff": staff,
        "adm_pay": adm_pay,
        "fee_pay": fee_pay,
        "exam_term": et,
    }
    db.close()


def test_default_templates_seeded_for_all_10_document_types(doc_env):
    db = doc_env["db"]
    tpls = DocumentService.list_templates(db)
    covered_types = {t.document_type for t in tpls}
    assert set(OFFICIAL_DOCUMENT_TYPES) == covered_types
    assert len(tpls) >= 11  # includes 2 distinct ID Card presets


def test_template_management_custom_school_and_custom_fields(doc_env):
    db = doc_env["db"]
    student = doc_env["student"]
    tmp_path = doc_env["tmp_path"]

    custom_tpl = DocumentService.create_template(
        db,
        name="Greenfield Bilingual Bonafide",
        document_type="Bonafide Certificate",
        page_size="A4",
        orientation="Landscape",
        border_style="Modern",
        primary_color="#047857",
        secondary_color="#064E3B",
        accent_color="#F59E0B",
        use_school_profile=False,
        school_name_override="Greenfield Global School",
        school_subtitle_override="Empowering Future Leaders",
        header_text="CERTIFICATE OF ENROLLMENT",
        body_template="Student {{recipient_name}} ({{recipient_code}}) belongs to {{house_name}} at {{school_name}}.",
        custom_fields_schema=[
            {"key": "house_name", "label": "Campus House", "type": "text", "default_value": "Emerald House"},
            {"key": "advisor", "label": "Faculty Advisor", "type": "text", "default_value": "Ms. Clara"},
        ],
    )
    cloned = DocumentService.clone_template(db, custom_tpl.id, new_name="Greenfield Variant B")
    DocumentService.set_default_template(db, cloned.id)
    assert DocumentService.get_default_template(db, "Bonafide Certificate").id == cloned.id

    pdf_out = str(tmp_path / "custom_bonafide.pdf")
    issued = DocumentService.issue_document(
        db,
        document_type="Bonafide Certificate",
        template_id=custom_tpl.id,
        student_id=student.id,
        custom_fields_values={"house_name": "Sapphire House", "advisor": "Prof. Nadia"},
        output_pdf_path=pdf_out,
    )
    assert os.path.exists(pdf_out) and os.path.getsize(pdf_out) > 800
    assert "Greenfield Global School" in issued.rendered_body
    assert "Sapphire House" in issued.rendered_body
    assert DocumentService.delete_template(db, cloned.id) is True


def test_all_10_document_types_generation_preview_and_qr_verification(doc_env):
    db = doc_env["db"]
    tmp_path = doc_env["tmp_path"]
    student = doc_env["student"]
    teacher = doc_env["teacher"]
    staff = doc_env["staff"]
    adm_pay = doc_env["adm_pay"]
    fee_pay = doc_env["fee_pay"]
    exam_term = doc_env["exam_term"]

    specs = [
        ("ID Card", {"student_id": student.id, "custom_fields_values": {"valid_until": "31 Dec 2027"}}),
        ("Character Certificate", {"student_id": student.id, "custom_fields_values": {"conduct_grade": "Exemplary"}}),
        ("Transfer Certificate", {"student_id": student.id, "custom_fields_values": {"leaving_reason": "Parent Relocation"}}),
        ("Bonafide Certificate", {"student_id": student.id, "custom_fields_values": {"purpose": "Embassy Visa"}}),
        ("Study Certificate", {"student_id": student.id, "custom_fields_values": {"study_period_from": "Jan 2024"}}),
        ("Leaving Certificate", {"student_id": student.id, "custom_fields_values": {"dues_clearance": "Cleared 100%"}}),
        ("Admission Receipt", {"admission_payment_id": adm_pay.id}),
        ("Fee Receipt", {"fee_payment_id": fee_pay.id}),
        ("Mark Sheet", {"student_id": student.id, "exam_term_id": exam_term.id}),
        ("Report Card", {"student_id": student.id, "exam_term_id": exam_term.id}),
    ]

    issued_serials = set()
    for doc_type, kwargs in specs:
        # 1. Non-mutating live Print Preview check
        preview_payload = DocumentService.preview_document_data(db, document_type=doc_type, **kwargs)
        assert preview_payload["document_type"] == doc_type
        assert preview_payload["school_info"]["school_name"] == "Horizon International Academy"

        # 2. Issue & Export PDF
        out_pdf = str(tmp_path / f"{doc_type.replace(' ', '_')}.pdf")
        doc = DocumentService.issue_document(db, document_type=doc_type, output_pdf_path=out_pdf, **kwargs)
        assert doc.serial_number not in issued_serials
        issued_serials.add(doc.serial_number)
        assert os.path.exists(out_pdf) and os.path.getsize(out_pdf) > 800

        # 3. Verify via serial, verification token, AND full QR payload
        assert DocumentService.verify_document(db, doc.serial_number).id == doc.id
        assert DocumentService.verify_document(db, doc.verification_code).id == doc.id
        assert DocumentService.verify_document(db, doc.qr_payload).id == doc.id

    # Also test Teacher/Staff ID Card + Batch A4 ID Sheet + Revocation
    t_id = DocumentService.issue_document(db, document_type="ID Card", recipient_type="Teacher", teacher_id=teacher.id)
    s_id = DocumentService.issue_document(db, document_type="ID Card", recipient_type="Staff", staff_id=staff.id)
    assert t_id.serial_number != s_id.serial_number

    batch_pdf = str(tmp_path / "batch_ids.pdf")
    UniversalDocumentPDFGenerator.generate_batch_id_sheet(
        [DocumentService.document_to_render_payload(db, t_id), DocumentService.document_to_render_payload(db, s_id)],
        batch_pdf,
    )
    assert os.path.exists(batch_pdf) and os.path.getsize(batch_pdf) > 800

    revoked = DocumentService.revoke_document(db, s_id.id, reason="Replaced by new smart card")
    assert revoked.status == "Revoked"
    assert DocumentService.verify_document(db, s_id.serial_number).status == "Revoked"
