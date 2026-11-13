"""
EduManage Pro - Student CRM Comprehensive Test Suite (pytest)
Covers:
- Student 360 profile, photo storage, Digital ID, and deterministic QR matrix generation
- Multiple guardians & bidirectional family/sibling relationships
- Admission history, academic history, previous schools, and status history
- Document vault upload & verification
- Medical dossier & emergency contacts
- Notes, tags, and custom JSON fields
- Chronological 360° CRM timeline aggregation
- All 7 student statuses & lifecycle transitions (promote, transfer, withdraw, archive, restore)
- All 10 advanced search filters (Name, Student ID, Admission #, Roll, Class, Section, Guardian, Phone, Status, Academic Year, Tags)
- Excel & CSV Import Wizard with column mapping + strict duplicate student rejection
"""

from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.connection import Base
from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.student import StudentStatus
from app.repositories.student_repository import StudentRepository
from app.services.student_service import StudentService
from app.utils.qr_generator import generate_qr_matrix


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _set_fk_pragma(dbapi_connection, _connection_record):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    ay1 = AcademicYear(name="2025", start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), is_current=True)
    ay2 = AcademicYear(name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=False)
    session.add_all([ay1, ay2])
    session.flush()

    c8 = SchoolClass(name="Class 8", code="C8", numeric_order=8, academic_year_id=ay1.id)
    c9 = SchoolClass(name="Class 9", code="C9", numeric_order=9, academic_year_id=ay1.id)
    session.add_all([c8, c9])
    session.flush()

    sec_a = Section(name="Section A", class_id=c8.id)
    sec_b = Section(name="Section B", class_id=c9.id)
    session.add_all([sec_a, sec_b])
    session.commit()

    yield session
    session.close()


def _admit_sample(db, roll=1, fname="Aryan", lname="Karim", dob=date(2011, 4, 15), phone="+8801711000001", class_id=1, section_id=1, ay_id=1):
    ok, stu, msg = StudentService.admit_student(
        db,
        {
            "roll_number": roll,
            "first_name": fname,
            "last_name": lname,
            "gender": "Male",
            "date_of_birth": dob,
            "blood_group": "O+",
            "phone": phone,
            "class_id": class_id,
            "section_id": section_id,
            "academic_year_id": ay_id,
            "previous_school": "Greenfield Primary",
            "emergency_contact": "+8801811000099",
            "status": StudentStatus.ACTIVE,
        },
        {
            "guardian_name": f"Mr. {lname}",
            "guardian_phone": f"+88019110000{roll:02d}",
            "relation": "Father",
            "father_name": f"Mr. {lname}",
            "mother_name": f"Mrs. {lname}",
        },
        tags=["Scholarship", "Science-Club"],
        custom_fields={"house": "Red", "bus_stop": "Mirpur-10"},
    )
    assert ok is True, msg
    return stu


def test_digital_id_qr_photo_and_initial_crm_histories(db_session, tmp_path):
    photo_src = tmp_path / "portrait.png"
    photo_src.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-content")

    ok, stu, msg = StudentService.admit_student(
        db_session,
        {
            "roll_number": 7,
            "first_name": "Nafisa",
            "last_name": "Islam",
            "gender": "Female",
            "date_of_birth": date(2011, 8, 22),
            "photo_path": str(photo_src),
            "class_id": 1,
            "section_id": 1,
            "academic_year_id": 1,
            "previous_school": "Sunshine Academy",
        },
        {"guardian_name": "Tariqul Islam", "guardian_phone": "+8801700112233", "relation": "Father"},
    )
    assert ok is True, msg
    assert stu.digital_id_code.startswith("DID-")
    assert stu.qr_payload and stu.student_id in stu.qr_payload
    assert stu.photo_path and Path(stu.photo_path).exists()

    matrix = generate_qr_matrix(stu.qr_payload)
    assert len(matrix) >= 21
    assert len(matrix) == len(matrix[0])

    assert len(stu.admission_history) == 1
    assert len(stu.academic_history) == 1
    assert len(stu.status_history) == 1
    assert len(stu.previous_schools) == 1


def test_multiple_guardians_and_family_relationships(db_session):
    stu1 = _admit_sample(db_session, roll=1, fname="Aryan", lname="Karim")
    stu2 = _admit_sample(db_session, roll=2, fname="Zara", lname="Karim", phone="+8801711000002")

    ok_g, link2, msg_g = StudentService.add_guardian(
        db_session,
        stu1.id,
        {"guardian_name": "Farhana Karim", "guardian_phone": "+8801611998877", "relation": "Mother"},
        relationship_type="Mother",
        is_primary=False,
        is_financial_payer=True,
    )
    assert ok_g is True, msg_g
    assert link2.relationship_type == "Mother"

    db_session.refresh(stu1)
    assert len(stu1.guardian_links) == 2

    ok_f, _rel, msg_f = StudentService.link_family_member(
        db_session, stu1.id, stu2.id, relation_type="Sibling", bidirectional=True
    )
    assert ok_f is True, msg_f
    db_session.refresh(stu1)
    db_session.refresh(stu2)
    assert len(stu1.family_links) == 1
    assert stu1.family_links[0].related_student_id == stu2.id
    assert len(stu2.family_links) == 1
    assert stu2.family_links[0].related_student_id == stu1.id


def test_documents_medical_emergency_notes_tags_custom_fields_and_timeline(db_session, tmp_path):
    stu = _admit_sample(db_session, roll=3, fname="Rohan", lname="Mia")

    doc_src = tmp_path / "birth_cert.pdf"
    doc_src.write_bytes(b"%PDF-1.4\n%test-document")
    ok_d, doc, msg_d = StudentService.add_document(
        db_session,
        stu.id,
        doc_type="Birth Certificate",
        title="National Birth Registration",
        source_file_path=str(doc_src),
        copy_to_vault=True,
    )
    assert ok_d is True, msg_d
    assert Path(doc.file_path).exists()
    assert doc.is_verified is False

    ok_v, _ = StudentService.verify_document(db_session, doc.id, verified=True, actor="registrar")
    assert ok_v is True
    db_session.refresh(doc)
    assert doc.is_verified is True
    assert doc.verified_by == "registrar"

    ok_m, med, _ = StudentService.upsert_medical_profile(
        db_session,
        stu.id,
        {
            "blood_group": "AB+",
            "allergies": "Peanuts",
            "chronic_conditions": "Mild Asthma",
            "physician_name": "Dr. Mahmud",
            "physician_phone": "+8801755001122",
        },
    )
    assert ok_m is True
    assert med.allergies == "Peanuts"

    ok_e, ec, _ = StudentService.add_emergency_contact(
        db_session,
        stu.id,
        {"contact_name": "Uncle Hasan", "relationship_label": "Uncle", "primary_phone": "+8801822334455"},
    )
    assert ok_e is True
    assert ec.priority_order >= 1

    ok_n, _note, _ = StudentService.add_note(
        db_session, stu.id, title="Orientation Feedback", content="Very engaged in math lab.", category="Academic", is_pinned=True
    )
    assert ok_n is True

    ok_t, tags, _ = StudentService.set_tags(db_session, stu.id, ["Honor-Roll", "Debate-Team"])
    assert ok_t is True
    assert set(tags) == {"Honor-Roll", "Debate-Team"}

    ok_cf, cf, _ = StudentService.update_custom_fields(db_session, stu.id, {"locker_no": "L-42", "diet": "Vegetarian"})
    assert ok_cf is True
    assert cf["locker_no"] == "L-42"

    timeline = StudentService.get_student_timeline(db_session, stu.id)
    categories = {ev["category"] for ev in timeline}
    assert "Admission" in categories
    assert "Status" in categories
    assert "Document" in categories
    assert "Note (Academic)" in categories


def test_all_seven_statuses_and_lifecycle_workflows(db_session):
    assert set(StudentStatus.ALL) == {
        "active", "inactive", "transferred", "graduated", "withdrawn", "suspended", "archived"
    }
    stu = _admit_sample(db_session, roll=4, fname="Tanvir", lname="Hossain")

    # Promote
    ok_p, p_cnt, _ = StudentService.promote_students(
        db_session, [stu.id], to_class_id=2, to_academic_year_id=2, to_section_id=2, remarks="Promoted to C9"
    )
    assert ok_p is True and p_cnt == 1
    db_session.refresh(stu)
    assert stu.class_id == 2
    assert stu.academic_year_id == 2
    assert len(stu.promotion_history) == 1
    assert len(stu.academic_history) == 2

    # Suspend
    ok_s, stu, _ = StudentService.change_status(db_session, stu.id, StudentStatus.SUSPENDED, reason="Disciplinary review")
    assert ok_s is True and stu.status == StudentStatus.SUSPENDED

    # Graduate
    ok_gr, stu, _ = StudentService.change_status(db_session, stu.id, StudentStatus.GRADUATED, reason="Completed SSC")
    assert ok_gr is True and stu.status == StudentStatus.GRADUATED

    # Transfer
    ok_tr, stu, _ = StudentService.transfer_student(
        db_session, stu.id, destination_school="City Model College", tc_number="TC-2026-09", reason="Relocated"
    )
    assert ok_tr is True
    assert stu.status == StudentStatus.TRANSFERRED
    assert stu.transfer_school == "City Model College"
    assert stu.transfer_tc_number == "TC-2026-09"

    # Withdraw
    ok_w, stu, _ = StudentService.withdraw_student(db_session, stu.id, reason="Guardian request")
    assert ok_w is True
    assert stu.status == StudentStatus.WITHDRAWN

    # Archive & Restore
    ok_a, stu, _ = StudentService.archive_student(db_session, stu.id, reason="End of cycle archive")
    assert ok_a is True
    assert stu.status == StudentStatus.ARCHIVED
    assert stu.archived_at is not None

    ok_r, stu, _ = StudentService.restore_student(db_session, stu.id, reason="Re-enrolled")
    assert ok_r is True
    assert stu.status == StudentStatus.ACTIVE
    assert stu.archived_at is None
    assert len(stu.status_history) >= 6


def test_advanced_search_ten_criteria(db_session):
    s1 = _admit_sample(db_session, roll=101, fname="Sumaiya", lname="Akter", phone="+8801710000101", class_id=1, section_id=1, ay_id=1)
    s2 = _admit_sample(db_session, roll=202, fname="Mehedi", lname="Hasan", phone="+8801720000202", class_id=2, section_id=2, ay_id=2)
    StudentService.archive_student(db_session, s2.id)

    # Search by Name
    rows, cnt = StudentRepository.search_and_filter(db_session, name="Sumaiya")
    assert cnt == 1 and rows[0].id == s1.id

    # Search by Student ID
    rows, cnt = StudentRepository.search_and_filter(db_session, student_id_code=s1.student_id)
    assert cnt == 1 and rows[0].id == s1.id

    # Search by Admission Number
    rows, cnt = StudentRepository.search_and_filter(db_session, admission_number=s2.admission_number)
    assert cnt == 1 and rows[0].id == s2.id

    # Search by Roll
    rows, cnt = StudentRepository.search_and_filter(db_session, roll_number=101)
    assert cnt == 1 and rows[0].id == s1.id

    # Search by Class & Section & Academic Year
    rows, cnt = StudentRepository.search_and_filter(db_session, class_id=1, section_id=1, academic_year_id=1)
    assert cnt == 1 and rows[0].id == s1.id

    # Search by Guardian & Phone
    rows, cnt = StudentRepository.search_and_filter(db_session, guardian="Akter", phone="01710000101")
    assert cnt == 1 and rows[0].id == s1.id

    # Search by Status & Tag
    rows, cnt = StudentRepository.search_and_filter(db_session, status=StudentStatus.ARCHIVED, tag="Scholarship")
    assert cnt == 1 and rows[0].id == s2.id


def test_duplicate_prevention_and_csv_import_wizard(db_session, tmp_path):
    # First direct admission
    _admit_sample(
        db_session,
        roll=11,
        fname="Samir",
        lname="Uddin",
        dob=date(2012, 6, 10),
        phone="+8801799001122",
    )

    # Attempt duplicate identity (same name + dob + guardian phone)
    ok_dup, _stu, err_msg = StudentService.admit_student(
        db_session,
        {
            "roll_number": 12,
            "first_name": "Samir",
            "last_name": "Uddin",
            "gender": "Male",
            "date_of_birth": date(2012, 6, 10),
            "class_id": 1,
            "academic_year_id": 1,
        },
        {"guardian_name": "Mr. Uddin", "guardian_phone": "+8801911000011", "relation": "Father"},
    )
    assert ok_dup is False
    assert "duplicate" in err_msg.lower()

    # Build a CSV import file containing 1 new student + 1 duplicate row
    csv_file = tmp_path / "students_import.csv"
    csv_file.write_text(
        "Roll,Full Name,Gender,DOB,Phone,Guardian Name,Guardian Phone,Tags\n"
        "11,Samir Uddin,Male,2012-06-10,+8801799001122,Mr. Uddin,+8801911000011,Science\n"
        "15,Lamiya Chowdhury,Female,2012-09-05,+8801788990011,Mrs. Chowdhury,+8801988776655,\"Honors,Debate\"\n",
        encoding="utf-8",
    )

    info = StudentService.inspect_import_file(str(csv_file))
    assert info["total_rows"] == 2
    suggested = info["suggested_mapping"]
    assert suggested[0] == "roll_number"
    assert suggested[1] == "full_name"

    res = StudentService.import_students_with_mapping(
        db_session,
        file_path=str(csv_file),
        column_mapping=suggested,
        default_class_id=1,
        default_ay_id=1,
        default_section_id=1,
        duplicate_policy="skip",
    )
    assert res["imported"] == 1
    assert res["skipped"] == 1
    found_rows, found_cnt = StudentRepository.search_and_filter(db_session, name="Lamiya Chowdhury", tag="Debate")
    assert found_cnt == 1
    assert found_rows[0].roll_number == 15
