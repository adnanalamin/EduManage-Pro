"""
EduManage Pro - Student Management Unit Tests (pytest)
Tests:
- Unique ID and admission number generation
- Student admission & validation with Guardian creation
- Profile update
- Search & multi-column filtering
- Student batch academic promotion
- Archiving / Soft deletion
"""

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.connection import Base
from app.models.academic import SchoolClass, AcademicYear
from app.models.student import Student, Guardian, StudentStatus
from app.repositories.student_repository import StudentRepository
from app.services.student_service import StudentService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed Academic Year & Classes
    ay = AcademicYear(name="2024-2025", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31), is_current=True)
    session.add(ay)
    session.flush()

    c9 = SchoolClass(name="Class 9", code="C9", numeric_order=9, academic_year_id=ay.id)
    c10 = SchoolClass(name="Class 10", code="C10", numeric_order=10, academic_year_id=ay.id)
    session.add_all([c9, c10])
    session.commit()

    yield session
    session.close()


def test_student_admission_and_id_generation(db_session):
    stu_data = {
        "roll_number": 101,
        "first_name": "Tahsin",
        "last_name": "Rahman",
        "gender": "Male",
        "date_of_birth": date(2009, 5, 14),
        "blood_group": "A+",
        "class_id": 1,
        "academic_year_id": 1,
        "status": StudentStatus.ACTIVE
    }
    g_data = {
        "guardian_name": "Dr. Lutfor Rahman",
        "guardian_phone": "+880 1711-223344",
        "relation": "Father"
    }

    success, student, msg = StudentService.admit_student(db_session, stu_data, g_data)
    assert success is True
    assert student is not None
    assert student.full_name == "Tahsin Rahman"
    assert student.student_id.startswith("STU-")
    assert student.admission_number.startswith("ADM-")
    assert student.guardian is not None
    assert student.guardian.guardian_name == "Dr. Lutfor Rahman"


def test_student_search_and_filter(db_session):
    # Admit two students
    StudentService.admit_student(db_session, {
        "roll_number": 1, "first_name": "Sadia", "last_name": "Afrin",
        "gender": "Female", "date_of_birth": date(2009, 2, 10),
        "class_id": 1, "academic_year_id": 1, "status": StudentStatus.ACTIVE
    }, {"guardian_name": "Jahangir Alam", "guardian_phone": "+880 1712-000000"})

    StudentService.admit_student(db_session, {
        "roll_number": 2, "first_name": "Mahmudul", "last_name": "Hasan",
        "gender": "Male", "date_of_birth": date(2009, 3, 12),
        "class_id": 1, "academic_year_id": 1, "status": StudentStatus.ACTIVE
    }, {"guardian_name": "Anwar Hossain", "guardian_phone": "+880 1713-000000"})

    # Search by name
    results, count = StudentRepository.search_and_filter(db_session, search_query="Sadia")
    assert count == 1
    assert results[0].first_name == "Sadia"

    # Filter by gender
    males, male_count = StudentRepository.search_and_filter(db_session, gender="Male")
    assert male_count == 1
    assert males[0].first_name == "Mahmudul"


def test_student_update_and_archive(db_session):
    _, stu, _ = StudentService.admit_student(db_session, {
        "roll_number": 5, "first_name": "Nabil", "last_name": "Ahmed",
        "gender": "Male", "date_of_birth": date(2010, 1, 1),
        "class_id": 1, "academic_year_id": 1, "status": StudentStatus.ACTIVE
    }, {"guardian_name": "Ahmed Ali", "guardian_phone": "+880 1714-000000"})

    # Update phone
    success, updated, _ = StudentService.update_student(db_session, stu.id, {"phone": "+880 1999-888777"}, None)
    assert success is True
    assert updated.phone == "+880 1999-888777"

    # Soft delete / Archive
    StudentRepository.archive_or_delete(db_session, updated, soft_delete=True)
    assert updated.status == StudentStatus.INACTIVE


def test_batch_promotion(db_session):
    _, stu1, _ = StudentService.admit_student(db_session, {
        "roll_number": 10, "first_name": "Student", "last_name": "One",
        "gender": "Male", "date_of_birth": date(2010, 1, 1),
        "class_id": 1, "academic_year_id": 1, "status": StudentStatus.ACTIVE
    }, {"guardian_name": "Guardian", "guardian_phone": "+880 1715-000000"})

    # Promote from Class 1 to Class 2 (id=2)
    promoted = StudentRepository.bulk_promote(db_session, [stu1.id], target_class_id=2, target_academic_year_id=1)
    assert promoted == 1
    assert stu1.class_id == 2
