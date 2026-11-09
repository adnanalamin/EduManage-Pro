"""
EduManage Pro - Teacher & Staff Unit Tests (pytest)
Tests:
- Automatic Teacher & Staff ID generation (TCH-YYYY-XXXX, STF-YYYY-XXXX, EMP-YYYY-XXXX)
- Teacher registration and profile update
- Duplicate email prevention
- Staff member registration and position filtering
- Payroll summary calculations
"""

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.connection import Base
from app.models.staff import Teacher, Staff, Department
from app.repositories.staff_repository import StaffRepository
from app.services.staff_service import StaffService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed Departments
    StaffRepository.get_or_create_departments(session)

    yield session
    session.close()


def test_add_teacher_and_id_generation(db_session):
    dept = db_session.query(Department).filter_by(code="SCI").first()
    assert dept is not None

    payload = {
        "full_name": "Kamal Hossain",
        "gender": "Male",
        "date_of_birth": date(1985, 3, 20),
        "phone": "+880 1819-334455",
        "email": "kamal.hossain@school.local",
        "qualification": "M.Sc. in Physics, B.Ed",
        "designation": "Senior Teacher",
        "department_id": dept.id,
        "primary_subject": "Physics",
        "salary": 45000,
        "status": "active"
    }

    success, teacher, msg = StaffService.add_teacher(db_session, payload)
    assert success is True
    assert teacher is not None
    assert teacher.teacher_id.startswith("TCH-")
    assert teacher.employee_id.startswith("EMP-")
    assert teacher.primary_subject == "Physics"
    assert teacher.salary == 45000


def test_duplicate_teacher_email(db_session):
    dept = db_session.query(Department).first()
    payload = {
        "full_name": "First Teacher", "gender": "Male",
        "date_of_birth": date(1990, 1, 1), "phone": "+880 1711-000001",
        "email": "duplicate@school.local", "qualification": "B.Sc",
        "designation": "Teacher", "department_id": dept.id,
        "primary_subject": "Math", "salary": 30000, "status": "active"
    }
    StaffService.add_teacher(db_session, payload)

    # Attempt same email
    payload2 = {
        "full_name": "Second Teacher", "gender": "Female",
        "date_of_birth": date(1992, 1, 1), "phone": "+880 1711-000002",
        "email": "duplicate@school.local", "qualification": "B.A",
        "designation": "Teacher", "department_id": dept.id,
        "primary_subject": "English", "salary": 30000, "status": "active"
    }
    success, _, msg = StaffService.add_teacher(db_session, payload2)
    assert success is False
    assert "already exists" in msg.lower()


def test_add_staff_and_search(db_session):
    admin_dept = db_session.query(Department).filter_by(code="ADMIN").first()

    payload = {
        "full_name": "Shafiqul Alam",
        "gender": "Male",
        "date_of_birth": date(1987, 8, 12),
        "phone": "+880 1912-778899",
        "email": "shafiq@school.local",
        "position": "Accountant",
        "department_id": admin_dept.id,
        "shift": "Day",
        "salary": 28000,
        "status": "active"
    }

    success, staff, msg = StaffService.add_staff(db_session, payload)
    assert success is True
    assert staff.staff_id.startswith("STF-")
    assert staff.position == "Accountant"

    # Search
    results, count = StaffRepository.search_and_filter_staff(db_session, position="Accountant")
    assert count == 1
    assert results[0].full_name == "Shafiqul Alam"


def test_payroll_overview_calculation(db_session):
    dept = db_session.query(Department).first()

    # Teacher salary 40k
    StaffService.add_teacher(db_session, {
        "full_name": "T1", "gender": "Male", "date_of_birth": date(1990, 1, 1),
        "phone": "017", "email": "t1@test.local", "qualification": "M.Sc",
        "designation": "Teacher", "department_id": dept.id,
        "primary_subject": "Math", "salary": 40000, "status": "active"
    })

    # Staff salary 25k
    StaffService.add_staff(db_session, {
        "full_name": "S1", "gender": "Male", "date_of_birth": date(1990, 1, 1),
        "phone": "018", "position": "Librarian", "department_id": dept.id,
        "shift": "Day", "salary": 25000, "status": "active"
    })

    stats = StaffRepository.get_overview_statistics(db_session)
    assert stats["total_teachers"] == 1
    assert stats["total_staff"] == 1
    assert stats["monthly_payroll"] == 65000
