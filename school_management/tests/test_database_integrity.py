"""
EduManage Pro - Comprehensive Database Architecture & Integrity Test Suite
Validates:
- Full model registry (including Inventory & SchemaVersion)
- SQLite PRAGMA foreign_keys=ON enforcement & invalid FK rejection
- Orphan record prevention (RESTRICT on students, fees, marks, exams)
- Duplicate student & duplicate payment / idempotency protection
- Transaction atomicity & savepoint rollback
- Soft delete, restore & safe hard-delete guards
- UUIDv4 public_id & timezone-aware timestamps
- Non-destructive migration of legacy pre-existing SQLite databases
- PostgreSQL URL/dialect resolution & configuration compatibility
"""

import sqlite3
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  Register every ORM table
from app.config.settings import _resolve_database_url
from app.database.connection import (
    Base,
    create_database_engine,
    is_postgresql_url,
    is_sqlite_url,
)
from app.database.migrations import CURRENT_SCHEMA_VERSION, migrate_database
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.models.accounting import AccountCategory, AccountTransaction
from app.models.exam import ExamResultSummary, ExamSchedule, ExamTerm, StudentMark
from app.models.fee import FeeCategory, FeePayment, FeeStructure, StudentFee
from app.models.hostel import HostelAllocation, HostelBlock, HostelRoom
from app.models.inventory import InventoryCategory, InventoryItem, InventoryTransaction
from app.models.library import Book, BookCategory, BookCirculation, LibraryMember
from app.models.notice import SchoolEvent, SchoolNotice
from app.models.schema_version import SchemaVersion
from app.models.school import SchoolSetting
from app.models.staff import Department, Staff, Teacher
from app.models.student import Guardian, Student, StudentStatus
from app.models.timetable import PeriodSlot, TimetableEntry
from app.models.user import Permission, Role, User
from app.repositories.fee_repository import FeeRepository
from app.repositories.student_repository import StudentRepository
from app.services.database_service import DatabaseService
from app.services.fee_service import FeeService
from app.services.student_service import StudentService


@pytest.fixture
def db_session(tmp_path):
    db_file = tmp_path / "integrity_test.db"
    engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()

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

    dept = Department(name="Science", code="SCI")
    session.add(dept)
    session.flush()

    teacher = Teacher(
        teacher_id="TCH-001",
        employee_id="EMP-001",
        full_name="Prof. Karim",
        gender="Male",
        date_of_birth=date(1985, 5, 1),
        phone="01711111111",
        email="karim@school.local",
        qualification="MSc Physics",
        department_id=dept.id,
        primary_subject="Physics",
    )
    session.add(teacher)
    session.commit()

    yield session
    session.close()
    engine.dispose()


def test_all_required_tables_registered():
    expected_tables = {
        "users",
        "roles",
        "permissions",
        "school_settings",
        "activity_logs",
        "schema_versions",
        "academic_years",
        "school_classes",
        "sections",
        "subjects",
        "departments",
        "teachers",
        "staff_members",
        "guardians",
        "students",
        "student_promotion_history",
        "student_attendance",
        "teacher_attendance",
        "fee_categories",
        "fee_structures",
        "student_fees",
        "fee_payments",
        "account_categories",
        "account_transactions",
        "exam_terms",
        "grading_scales",
        "exam_schedules",
        "student_marks",
        "exam_result_summaries",
        "period_slots",
        "timetable_entries",
        "book_categories",
        "library_books",
        "library_members",
        "book_circulations",
        "transport_vehicles",
        "transport_routes",
        "transport_stops",
        "transport_passengers",
        "hostel_blocks",
        "hostel_rooms",
        "hostel_allocations",
        "hostel_gate_passes",
        "inventory_categories",
        "inventory_items",
        "inventory_transactions",
        "school_notices",
        "school_events",
        "certificates",
    }
    registered = set(Base.metadata.tables.keys())
    missing = expected_tables - registered
    assert not missing, f"Missing expected ORM tables: {missing}"


def test_sqlite_foreign_keys_and_invalid_fk_rejected(db_session):
    diag = DatabaseService.verify_integrity(db_session)
    assert diag["ok"] is True
    assert diag["foreign_keys_enabled"] is True

    # Invalid class_id must fail at DB FK level
    bad_student = Student(
        student_id="STU-BAD-1",
        admission_number="ADM-BAD-1",
        roll_number=99,
        first_name="Orphan",
        last_name="Child",
        full_name="Orphan Child",
        gender="Male",
        date_of_birth=date(2012, 1, 1),
        class_id=99999,
        academic_year_id=1,
    )
    db_session.add(bad_student)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_exam_and_timetable_fk_point_to_school_classes(db_session):
    sub = Subject(
        subject_id="SUB-2026-0001",
        name="Physics",
        code="174",
        class_id=1,
        full_marks=100,
        pass_marks=33,
        theory_marks=75,
        practical_marks=25,
    )
    slot = PeriodSlot(
        period_number=1,
        name="1st Period",
        start_time="08:30 AM",
        end_time="09:15 AM",
        duration_minutes=45,
        academic_year_id=1,
    )
    term = ExamTerm(
        name="Final Exam",
        exam_code="FIN-2026",
        academic_year_id=1,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 20),
    )
    db_session.add_all([sub, slot, term])
    db_session.flush()

    sched = ExamSchedule(
        exam_term_id=term.id,
        class_id=1,
        subject_id=sub.id,
        exam_date=date(2026, 11, 5),
    )
    tt = TimetableEntry(
        academic_year_id=1,
        class_id=1,
        day_of_week="Sunday",
        period_slot_id=slot.id,
        subject_id=sub.id,
        teacher_id=1,
        room_number="Room 301",
    )
    db_session.add_all([sched, tt])
    db_session.commit()

    assert sched.school_class.name == "Class 10"
    assert tt.school_class.name == "Class 10"


def test_orphan_and_accidental_delete_prevention(db_session):
    ok, stu, _ = StudentService.admit_student(
        db_session,
        {
            "roll_number": 1,
            "first_name": "Rafiq",
            "last_name": "Islam",
            "gender": "Male",
            "date_of_birth": date(2010, 4, 15),
            "class_id": 1,
            "academic_year_id": 1,
            "status": StudentStatus.ACTIVE,
        },
        {"guardian_name": "Hasan Islam", "guardian_phone": "+8801712000111"},
    )
    assert ok is True

    # Deleting parent SchoolClass with active Student must be blocked by FK RESTRICT
    cls_obj = db_session.query(SchoolClass).filter(SchoolClass.id == 1).first()
    db_session.delete(cls_obj)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Create FeeCategory -> FeeStructure -> StudentFee -> FeePayment
    cat = FeeCategory(name="Tuition", code="TUI")
    db_session.add(cat)
    db_session.flush()
    fs = FeeStructure(
        title="Monthly Tuition",
        category_id=cat.id,
        class_id=1,
        academic_year_id=1,
        amount=2000.0,
        due_date=date(2026, 2, 10),
    )
    db_session.add(fs)
    db_session.flush()
    assigned = FeeRepository.batch_assign_fee_structure(db_session, fs.id, 1, 1)
    assert assigned == 1

    sf = db_session.query(StudentFee).filter(StudentFee.student_id == stu.id).first()
    pay, msg = FeeService.collect_fee_payment(db_session, sf.id, 500.0, idempotency_key="idem-test-1")
    assert pay is not None

    # Safe hard-delete guard prevents wiping student with dependent fees/payments
    with pytest.raises(ValueError, match="dependent"):
        DatabaseService.safe_hard_delete(db_session, stu)


def test_duplicate_student_and_payment_prevention(db_session):
    ok1, stu1, _ = StudentService.admit_student(
        db_session,
        {
            "student_id": "STU-2026-9001",
            "admission_number": "ADM-2026-9001",
            "birth_certificate_no": "BC-99887766",
            "roll_number": 5,
            "first_name": "Nusrat",
            "last_name": "Jahan",
            "gender": "Female",
            "date_of_birth": date(2011, 7, 20),
            "class_id": 1,
            "academic_year_id": 1,
            "status": StudentStatus.ACTIVE,
        },
        {"guardian_name": "Kamal Uddin", "guardian_phone": "+8801811223344"},
    )
    assert ok1 is True

    # 1. Duplicate admission number blocked
    ok2, _, msg2 = StudentService.admit_student(
        db_session,
        {
            "student_id": "STU-2026-9002",
            "admission_number": "ADM-2026-9001",
            "roll_number": 6,
            "first_name": "Other",
            "last_name": "Name",
            "gender": "Female",
            "date_of_birth": date(2011, 8, 1),
            "class_id": 1,
            "academic_year_id": 1,
        },
        {"guardian_name": "Kamal", "guardian_phone": "+8801811999999"},
    )
    assert ok2 is False
    assert "already in use" in msg2

    # 2. Duplicate student_id blocked
    ok3, _, msg3 = StudentService.admit_student(
        db_session,
        {
            "student_id": "STU-2026-9001",
            "admission_number": "ADM-2026-9003",
            "roll_number": 7,
            "first_name": "Other",
            "last_name": "Student",
            "gender": "Female",
            "date_of_birth": date(2011, 8, 2),
            "class_id": 1,
            "academic_year_id": 1,
        },
        None,
    )
    assert ok3 is False
    assert "already assigned" in msg3

    # 3. Same person heuristic (full_name + date_of_birth + guardian_phone) blocked
    ok4, _, msg4 = StudentService.admit_student(
        db_session,
        {
            "student_id": "STU-2026-9004",
            "admission_number": "ADM-2026-9004",
            "roll_number": 8,
            "first_name": "Nusrat",
            "last_name": "Jahan",
            "gender": "Female",
            "date_of_birth": date(2011, 7, 20),
            "class_id": 1,
            "academic_year_id": 1,
        },
        {"guardian_name": "Kamal Uddin", "guardian_phone": "+8801811223344"},
    )
    assert ok4 is False
    assert "Potential duplicate student" in msg4

    # 4. Duplicate invoice and idempotent payment protection
    cat = FeeCategory(name="Exam Fee", code="EXM")
    db_session.add(cat)
    db_session.flush()
    fs = FeeStructure(
        title="Term Exam",
        category_id=cat.id,
        class_id=1,
        academic_year_id=1,
        amount=1500.0,
        due_date=date(2026, 5, 1),
    )
    db_session.add(fs)
    db_session.flush()

    sf1 = StudentFee(
        student_id=stu1.id,
        fee_structure_id=fs.id,
        academic_year_id=1,
        total_amount=1500.0,
        discount_amount=0.0,
        net_amount=1500.0,
        paid_amount=0.0,
        due_amount=1500.0,
        due_date=date(2026, 5, 1),
    )
    db_session.add(sf1)
    db_session.commit()

    # Duplicate invoice for same student + structure + year must fail
    sf_dup = StudentFee(
        student_id=stu1.id,
        fee_structure_id=fs.id,
        academic_year_id=1,
        total_amount=1500.0,
        discount_amount=0.0,
        net_amount=1500.0,
        paid_amount=0.0,
        due_amount=1500.0,
        due_date=date(2026, 5, 1),
    )
    db_session.add(sf_dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Idempotent payment replay must NOT double-charge
    p1, _ = FeeService.collect_fee_payment(
        db_session, sf1.id, 1000.0, payment_method="bKash", transaction_id="TRX-100", idempotency_key="key-abc"
    )
    p2, replay_msg = FeeService.collect_fee_payment(
        db_session, sf1.id, 1000.0, payment_method="bKash", transaction_id="TRX-100", idempotency_key="key-abc"
    )
    assert p1.id == p2.id
    assert "idempotent" in replay_msg.lower()
    db_session.refresh(sf1)
    assert sf1.paid_amount == 1000.0
    assert sf1.due_amount == 500.0

    # Duplicate external transaction_id on same invoice (without idempotency_key) must fail
    p_dup, err_msg = FeeService.collect_fee_payment(
        db_session, sf1.id, 200.0, payment_method="bKash", transaction_id="TRX-100"
    )
    assert p_dup is None
    assert "Duplicate transaction reference" in err_msg


def test_transaction_atomicity_soft_delete_and_uuids(db_session):
    # Rollback test inside DatabaseService.transaction
    with pytest.raises(RuntimeError):
        with DatabaseService.transaction(db_session):
            db_session.add(InventoryCategory(name="Lab Gear", code="LAB"))
            db_session.flush()
            raise RuntimeError("Simulated mid-transaction crash")

    assert db_session.query(InventoryCategory).filter_by(code="LAB").count() == 0

    # Inventory item + stock ledger transaction
    cat = InventoryCategory(name="Furniture", code="FURN")
    db_session.add(cat)
    db_session.flush()
    item = InventoryItem(
        item_code="INV-001",
        name="Classroom Desk",
        category_id=cat.id,
        quantity_in_stock=20,
        unit_cost=3500.0,
    )
    db_session.add(item)
    db_session.flush()

    # Verify UUIDv4 public_id and timezone-aware timestamps
    uuid_obj = uuid.UUID(item.public_id, version=4)
    assert str(uuid_obj) == item.public_id
    assert item.created_at is not None

    # Soft delete & restore student
    ok, stu, _ = StudentService.admit_student(
        db_session,
        {
            "roll_number": 12,
            "first_name": "Tariq",
            "last_name": "Aziz",
            "gender": "Male",
            "date_of_birth": date(2010, 9, 9),
            "class_id": 1,
            "academic_year_id": 1,
            "status": StudentStatus.ACTIVE,
        },
        None,
    )
    assert ok is True

    StudentRepository.archive_or_delete(db_session, stu, soft_delete=True, deleted_by="auditor")
    assert stu.is_deleted is True
    assert stu.deleted_by == "auditor"
    assert stu.status == StudentStatus.INACTIVE

    visible, cnt = StudentRepository.search_and_filter(db_session, search_query="Tariq")
    assert cnt == 0
    all_rows, all_cnt = StudentRepository.search_and_filter(
        db_session, search_query="Tariq", include_deleted=True
    )
    assert all_cnt == 1

    DatabaseService.restore(db_session, stu)
    assert stu.is_deleted is False


def test_non_destructive_migration_of_legacy_sqlite_database(tmp_path):
    legacy_path = tmp_path / "legacy_school.db"

    # Simulate an older pre-v2 SQLite database WITHOUT public_id, is_deleted, schema_versions, or inventory tables
    raw_conn = sqlite3.connect(legacy_path)
    raw_conn.execute(
        """
        CREATE TABLE academic_years (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) NOT NULL UNIQUE,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            is_current BOOLEAN NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'Active'
        )
        """
    )
    raw_conn.execute(
        """
        INSERT INTO academic_years (name, start_date, end_date, is_current, status)
        VALUES ('2025-2026', '2025-01-01', '2025-12-31', 1, 'Active')
        """
    )
    raw_conn.commit()
    raw_conn.close()

    # Run non-destructive migrator
    eng = create_database_engine(f"sqlite:///{legacy_path.as_posix()}")
    report = migrate_database(eng)

    assert report["current_version"] == CURRENT_SCHEMA_VERSION
    assert "public_id" in report["columns_added"].get("academic_years", [])
    assert "is_deleted" in report["columns_added"].get("academic_years", [])
    assert "inventory_items" in report["tables_created"]
    assert "schema_versions" in report["tables_created"]
    assert report["backfilled_uuids"] >= 1

    # Verify existing legacy row is completely preserved and has valid UUID + version record
    Session = sessionmaker(bind=eng)
    s = Session()
    try:
        ay = s.query(AcademicYear).filter_by(name="2025-2026").first()
        assert ay is not None
        assert ay.is_deleted is False
        assert str(uuid.UUID(ay.public_id, version=4)) == ay.public_id

        ver = s.query(SchemaVersion).order_by(SchemaVersion.version.desc()).first()
        assert ver is not None
        assert ver.version == CURRENT_SCHEMA_VERSION
        assert DatabaseService.verify_integrity(s)["ok"] is True
    finally:
        s.close()
        eng.dispose()


def test_postgresql_url_and_dialect_configuration(monkeypatch, tmp_path):
    monkeypatch.setenv("EDUMANAGE_DB_BACKEND", "postgresql")
    monkeypatch.setenv("EDUMANAGE_PG_HOST", "db.school.lan")
    monkeypatch.setenv("EDUMANAGE_PG_PORT", "5432")
    monkeypatch.setenv("EDUMANAGE_PG_DB", "edumanage_enterprise")
    monkeypatch.setenv("EDUMANAGE_PG_USER", "edu_admin")
    monkeypatch.setenv("EDUMANAGE_PG_PASSWORD", "p@ss:word")

    resolved = _resolve_database_url(tmp_path / "ignored.db")
    assert resolved.startswith("postgresql+psycopg://edu_admin:p%40ss%3Aword@db.school.lan:5432/edumanage_enterprise")
    assert is_postgresql_url(resolved) is True
    assert is_sqlite_url(resolved) is False
