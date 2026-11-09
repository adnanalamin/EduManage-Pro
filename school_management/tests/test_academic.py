"""
EduManage Pro - Academic Module Unit Tests (Pytest)
Tests AcademicYear, SchoolClass, Section, Subject models, validation, and services.
"""

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.connection import Base
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.models.staff import Teacher, Department
from app.repositories.academic_repository import AcademicRepository
from app.services.academic_service import AcademicService


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed a department and teacher for testing assignments
    dept = Department(name="Science", code="SCI")
    session.add(dept)
    session.flush()

    teacher = Teacher(
        teacher_id="TCH-2026-0001",
        employee_id="EMP-1001",
        full_name="Prof. Nasir Uddin",
        gender="Male",
        date_of_birth=date(1985, 3, 15),
        phone="+8801711223344",
        email="nasir@school.edu.bd",
        qualification="M.Sc in Physics",
        department_id=dept.id,
        primary_subject="Physics",
        salary=45000,
        status="active"
    )
    session.add(teacher)
    session.commit()

    yield session
    session.close()


def test_academic_year_lifecycle(db_session):
    ay1 = AcademicRepository.create_academic_year(db_session, {
        "name": "2025-2026",
        "start_date": date(2025, 1, 1),
        "end_date": date(2025, 12, 31),
        "is_current": True,
        "status": "Active"
    })
    assert ay1.id is not None
    assert ay1.is_current is True

    ay2 = AcademicRepository.create_academic_year(db_session, {
        "name": "2026-2027",
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 12, 31),
        "is_current": True,
        "status": "Upcoming"
    })
    # Activating ay2 should auto-deactivate ay1
    db_session.refresh(ay1)
    assert ay2.is_current is True
    assert ay1.is_current is False


def test_class_creation_and_filters(db_session):
    ay = AcademicRepository.create_academic_year(db_session, {
        "name": "2025-2026",
        "start_date": date(2025, 1, 1),
        "end_date": date(2025, 12, 31),
        "is_current": True
    })

    cls_obj, msg = AcademicService.create_class(db_session, {
        "name": "Class 9",
        "code": "C9",
        "numeric_order": 9,
        "group": "Science",
        "shift": "Day",
        "academic_year_id": ay.id
    })
    assert cls_obj is not None
    assert cls_obj.name == "Class 9"

    # Duplicate in same academic year should fail
    dup, dup_msg = AcademicService.create_class(db_session, {
        "name": "Class 9",
        "academic_year_id": ay.id
    })
    assert dup is None
    assert "already exists" in dup_msg


def test_section_creation_with_class_teacher(db_session):
    ay = AcademicRepository.create_academic_year(db_session, {
        "name": "2025-2026",
        "start_date": date(2025, 1, 1),
        "end_date": date(2025, 12, 31),
        "is_current": True
    })
    cls_obj, _ = AcademicService.create_class(db_session, {
        "name": "Class 10",
        "code": "C10",
        "numeric_order": 10,
        "academic_year_id": ay.id
    })

    teacher = db_session.query(Teacher).first()
    sec, msg = AcademicService.create_section(db_session, {
        "name": "Section A",
        "room_number": "Room 301",
        "capacity": 45,
        "shift": "Morning",
        "group": "Science",
        "class_id": cls_obj.id,
        "class_teacher_id": teacher.id
    })
    assert sec is not None
    assert sec.room_number == "Room 301"
    assert sec.class_teacher.full_name == "Prof. Nasir Uddin"


def test_subject_validation_and_assignment(db_session):
    ay = AcademicRepository.create_academic_year(db_session, {
        "name": "2025-2026",
        "start_date": date(2025, 1, 1),
        "end_date": date(2025, 12, 31),
        "is_current": True
    })
    cls_obj, _ = AcademicService.create_class(db_session, {
        "name": "Class 10",
        "code": "C10",
        "numeric_order": 10,
        "academic_year_id": ay.id
    })
    teacher = db_session.query(Teacher).first()

    # Pass marks greater than full marks must fail
    invalid_sub, err = AcademicService.create_subject(db_session, {
        "name": "Invalid Subject",
        "code": "INV",
        "full_marks": 50,
        "pass_marks": 60,
        "class_id": cls_obj.id
    })
    assert invalid_sub is None
    assert "cannot exceed" in err

    # Valid subject creation
    valid_sub, msg = AcademicService.create_subject(db_session, {
        "name": "Physics 1st Paper",
        "code": "174",
        "full_marks": 100,
        "pass_marks": 33,
        "theory_marks": 75,
        "practical_marks": 25,
        "subject_type": "Mandatory",
        "class_id": cls_obj.id,
        "teacher_id": teacher.id
    })
    assert valid_sub is not None
    assert valid_sub.subject_id.startswith("SUB-")
    assert valid_sub.assigned_teacher.full_name == "Prof. Nasir Uddin"
