"""
EduManage Pro - Attendance Module Unit Tests (Pytest)
Tests Student & Teacher attendance recording, stats calculation, monthly register matrix, and openpyxl export.
"""

import pytest
import os
import tempfile
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.connection import Base
from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.student import Student, Guardian
from app.models.staff import Teacher, Department
from app.models.attendance import StudentAttendance, TeacherAttendance
from app.repositories.attendance_repository import AttendanceRepository
from app.services.attendance_service import AttendanceService


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed Academic context
    ay = AcademicYear(name="2025-2026", start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), is_current=True)
    session.add(ay)
    session.flush()

    cls_obj = SchoolClass(name="Class 10", code="C10", numeric_order=10, academic_year_id=ay.id)
    session.add(cls_obj)
    session.flush()

    sec = Section(name="Section A", room_number="Room 301", capacity=50, class_id=cls_obj.id)
    session.add(sec)
    session.flush()

    # Seed Guardian and Students
    g = Guardian(father_name="Karim Khan", guardian_name="Karim Khan", relation="Father", guardian_phone="+8801700112233")
    session.add(g)
    session.flush()

    stu1 = Student(
        student_id="STU-2026-0001",
        admission_number="ADM-1001",
        roll_number=1,
        first_name="Rahim",
        last_name="Khan",
        full_name="Rahim Khan",
        gender="Male",
        date_of_birth=date(2010, 5, 1),
        phone="+8801700112233",
        email="rahim@school.local",
        admission_date=date(2024, 1, 1),
        class_id=cls_obj.id,
        section_id=sec.id,
        academic_year_id=ay.id,
        guardian_id=g.id,
        status="active"
    )
    stu2 = Student(
        student_id="STU-2026-0002",
        admission_number="ADM-1002",
        roll_number=2,
        first_name="Fatima",
        last_name="Zaman",
        full_name="Fatima Zaman",
        gender="Female",
        date_of_birth=date(2010, 8, 12),
        phone="+8801700112234",
        email="fatima@school.local",
        admission_date=date(2024, 1, 1),
        class_id=cls_obj.id,
        section_id=sec.id,
        academic_year_id=ay.id,
        guardian_id=g.id,
        status="active"
    )
    session.add_all([stu1, stu2])

    # Seed Teacher
    dept = Department(name="Science", code="SCI")
    session.add(dept)
    session.flush()

    teacher = Teacher(
        teacher_id="TCH-2026-0001",
        employee_id="EMP-1001",
        full_name="Dr. Shamsul Huda",
        gender="Male",
        date_of_birth=date(1982, 4, 10),
        phone="+8801711223344",
        email="shamsul@school.edu.bd",
        qualification="Ph.D in Physics",
        department_id=dept.id,
        primary_subject="Physics",
        salary=55000,
        status="active"
    )
    session.add(teacher)
    session.commit()

    yield session
    session.close()


def test_mark_and_upsert_student_attendance(db_session):
    today = date.today()
    students = db_session.query(Student).all()
    records = [
        {"student_id": students[0].id, "class_id": students[0].class_id, "date": today, "status": "Present", "check_in_time": "08:10 AM"},
        {"student_id": students[1].id, "class_id": students[1].class_id, "date": today, "status": "Absent", "remarks": "Sick with flu"}
    ]

    ok, msg = AttendanceService.mark_student_attendance(db_session, students[0].class_id, None, today, records)
    assert ok is True
    assert "2 students" in msg

    # Verify records in database
    stats = AttendanceRepository.get_student_daily_stats(db_session, class_id=students[0].class_id, att_date=today)
    assert stats["total_marked"] == 2
    assert stats["present"] == 1
    assert stats["absent"] == 1
    assert stats["attendance_rate"] == 50.0

    # Upsert test: change student[1] to Present
    records_updated = [
        {"student_id": students[1].id, "class_id": students[1].class_id, "date": today, "status": "Present", "check_in_time": "08:25 AM"}
    ]
    AttendanceService.mark_student_attendance(db_session, students[0].class_id, None, today, records_updated)

    stats_after = AttendanceRepository.get_student_daily_stats(db_session, class_id=students[0].class_id, att_date=today)
    assert stats_after["present"] == 2
    assert stats_after["absent"] == 0
    assert stats_after["attendance_rate"] == 100.0


def test_monthly_student_register_and_excel(db_session):
    cls_obj = db_session.query(SchoolClass).first()
    students = db_session.query(Student).all()

    # Mark attendance for first 3 days of current month
    now = date.today()
    for d in [1, 2, 3]:
        att_d = date(now.year, now.month, d)
        records = [
            {"student_id": students[0].id, "class_id": cls_obj.id, "date": att_d, "status": "Present"},
            {"student_id": students[1].id, "class_id": cls_obj.id, "date": att_d, "status": "Absent" if d == 2 else "Present"}
        ]
        AttendanceRepository.save_bulk_student_attendance(db_session, records)

    register_data = AttendanceRepository.get_monthly_student_register(db_session, cls_obj.id, now.year, now.month)
    assert register_data["days_count"] >= 28
    assert len(register_data["register"]) == 2

    # Check student 1 (3 present out of 3 recorded)
    stu1_row = next(r for r in register_data["register"] if r["student"].id == students[0].id)
    assert stu1_row["present_count"] == 3
    assert stu1_row["percentage"] == 100.0

    # Check student 2 (2 present, 1 absent -> 66.7%)
    stu2_row = next(r for r in register_data["register"] if r["student"].id == students[1].id)
    assert stu2_row["present_count"] == 2
    assert stu2_row["absent_count"] == 1
    assert round(stu2_row["percentage"], 1) == 66.7

    # Test openpyxl Excel export
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        out_path = AttendanceService.export_monthly_register_excel(db_session, cls_obj.id, now.year, now.month, tmp_path)
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 1000
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_teacher_attendance_marking(db_session):
    today = date.today()
    teacher = db_session.query(Teacher).first()
    records = [{
        "teacher_id": teacher.id,
        "date": today,
        "status": "Present",
        "check_in_time": "07:45 AM",
        "check_out_time": "03:30 PM",
        "remarks": "On morning gate duty"
    }]

    ok, msg = AttendanceService.mark_teacher_attendance(db_session, today, records)
    assert ok is True
    assert "1 faculty" in msg

    stats = AttendanceRepository.get_teacher_daily_stats(db_session, today)
    assert stats["total_faculty"] == 1
    assert stats["present"] == 1
    assert stats["attendance_rate"] == 100.0
