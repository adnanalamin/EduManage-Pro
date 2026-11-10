"""
EduManage Pro - Examination & Grading Module Unit Tests (Pytest)
Tests GPA 5.0 scale, Exam terms, marks entry, merit rankings, Tabulation Sheets, and Report Cards.
"""

import pytest
import os
import tempfile
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.connection import Base
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.models.student import Student, Guardian
from app.models.exam import ExamTerm, GradingScale, ExamSchedule, StudentMark, ExamResultSummary
from app.repositories.exam_repository import ExamRepository
from app.services.exam_service import ExamService
from app.reports.report_card_pdf import ReportCardPDFGenerator
from app.reports.admit_card_pdf import AdmitCardPDFGenerator


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed academic year, class, and 2 subjects
    ay = AcademicYear(name="2025-2026", start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), is_current=True)
    session.add(ay)
    session.flush()

    cls_obj = SchoolClass(name="Class 10", code="C10", numeric_order=10, academic_year_id=ay.id)
    session.add(cls_obj)
    session.flush()

    sec = Section(name="Section A", class_id=cls_obj.id, capacity=40)
    session.add(sec)
    session.flush()

    sub1 = Subject(name="General Mathematics", code="109", class_id=cls_obj.id, full_marks=100, pass_marks=33)
    sub2 = Subject(name="English 1st Paper", code="107", class_id=cls_obj.id, full_marks=100, pass_marks=33)
    session.add_all([sub1, sub2])
    session.flush()

    # Seed 2 Students
    g1 = Guardian(guardian_name="Kabir Hossain", relation="Father", guardian_phone="+8801700000001")
    session.add(g1)
    session.flush()

    s1 = Student(
        student_id="STU-2026-0001",
        admission_number="ADM-1001",
        roll_number=1,
        first_name="Tahmid",
        last_name="Hasan",
        full_name="Tahmid Hasan",
        gender="Male",
        date_of_birth=date(2010, 5, 12),
        admission_date=date(2025, 1, 1),
        class_id=cls_obj.id,
        section_id=sec.id,
        academic_year_id=ay.id,
        guardian_id=g1.id,
        status="Active"
    )
    s2 = Student(
        student_id="STU-2026-0002",
        admission_number="ADM-1002",
        roll_number=2,
        first_name="Nabila",
        last_name="Khatun",
        full_name="Nabila Khatun",
        gender="Female",
        date_of_birth=date(2010, 8, 20),
        admission_date=date(2025, 1, 1),
        class_id=cls_obj.id,
        section_id=sec.id,
        academic_year_id=ay.id,
        guardian_id=g1.id,
        status="Active"
    )
    session.add_all([s1, s2])
    session.commit()

    yield session
    session.close()


def test_grading_scale_seeder(db_session):
    count = ExamService.seed_default_grading_scale(db_session)
    assert count == 7

    grade_name, gp, _ = ExamRepository.get_grade_for_score(db_session, 85.0)
    assert grade_name == "A+"
    assert gp == 5.0

    grade_name2, gp2, _ = ExamRepository.get_grade_for_score(db_session, 65.0)
    assert grade_name2 == "A-"
    assert gp2 == 3.5

    grade_name_fail, gp_fail, _ = ExamRepository.get_grade_for_score(db_session, 28.0)
    assert grade_name_fail == "F"
    assert gp_fail == 0.0


def test_exam_term_and_routine_creation(db_session):
    ay = db_session.query(AcademicYear).first()
    cls_obj = db_session.query(SchoolClass).first()
    sub1 = db_session.query(Subject).first()

    term = ExamRepository.create_exam_term(db_session, {
        "name": "First Terminal Examination 2026",
        "exam_code": "EXM-2026-T1",
        "academic_year_id": ay.id,
        "start_date": date(2026, 4, 1),
        "end_date": date(2026, 4, 15),
        "status": "Scheduled"
    })
    assert term.id is not None
    assert term.exam_code == "EXM-2026-T1"

    schedule = ExamRepository.create_or_update_schedule(db_session, {
        "exam_term_id": term.id,
        "class_id": cls_obj.id,
        "subject_id": sub1.id,
        "exam_date": date(2026, 4, 2),
        "start_time": "10:00 AM",
        "end_time": "01:00 PM",
        "room_number": "Auditorium Hall"
    })
    assert schedule.id is not None
    assert schedule.room_number == "Auditorium Hall"


def test_student_marks_entry_and_pass_fail(db_session):
    ExamService.seed_default_grading_scale(db_session)
    ay = db_session.query(AcademicYear).first()
    cls_obj = db_session.query(SchoolClass).first()
    sub1 = db_session.query(Subject).first()
    s1 = db_session.query(Student).filter(Student.roll_number == 1).first()

    term = ExamRepository.create_exam_term(db_session, {
        "name": "Mid Term 2026",
        "exam_code": "MID-2026",
        "academic_year_id": ay.id,
        "start_date": date(2026, 6, 1),
        "end_date": date(2026, 6, 10)
    })

    # Student 1 scores 88 in Math
    mark = ExamRepository.upsert_student_mark(db_session, {
        "exam_term_id": term.id,
        "class_id": cls_obj.id,
        "subject_id": sub1.id,
        "student_id": s1.id,
        "theory_marks": 58.0,
        "mcq_marks": 30.0,
        "is_absent": False
    })
    assert mark.total_marks == 88.0
    assert mark.grade_name == "A+"
    assert mark.grade_point == 5.0
    assert mark.is_passed is True


def test_class_results_compilation_and_gpa(db_session):
    ExamService.seed_default_grading_scale(db_session)
    ay = db_session.query(AcademicYear).first()
    cls_obj = db_session.query(SchoolClass).first()
    subjects = db_session.query(Subject).all()
    s1 = db_session.query(Student).filter(Student.roll_number == 1).first()
    s2 = db_session.query(Student).filter(Student.roll_number == 2).first()

    term = ExamRepository.create_exam_term(db_session, {
        "name": "Final Term 2026",
        "exam_code": "FIN-2026",
        "academic_year_id": ay.id,
        "start_date": date(2026, 11, 1),
        "end_date": date(2026, 11, 15)
    })

    # Student 1 passes both: Math 85 (A+, 5.0), English 75 (A, 4.0) -> GPA = 4.50
    ExamRepository.upsert_student_mark(db_session, {
        "exam_term_id": term.id,
        "class_id": cls_obj.id,
        "subject_id": subjects[0].id,
        "student_id": s1.id,
        "theory_marks": 85.0
    })
    ExamRepository.upsert_student_mark(db_session, {
        "exam_term_id": term.id,
        "class_id": cls_obj.id,
        "subject_id": subjects[1].id,
        "student_id": s1.id,
        "theory_marks": 75.0
    })

    # Student 2: Math 90 (A+, 5.0), English 25 (Fail, 0.0) -> Overall GPA must be 0.0 / F
    ExamRepository.upsert_student_mark(db_session, {
        "exam_term_id": term.id,
        "class_id": cls_obj.id,
        "subject_id": subjects[0].id,
        "student_id": s2.id,
        "theory_marks": 90.0
    })
    ExamRepository.upsert_student_mark(db_session, {
        "exam_term_id": term.id,
        "class_id": cls_obj.id,
        "subject_id": subjects[1].id,
        "student_id": s2.id,
        "theory_marks": 25.0
    })

    results = ExamService.compile_class_results(db_session, term.id, cls_obj.id)
    assert len(results) == 2

    # Tahmid (s1) must be Rank 1
    tahmid_res = next(r for r in results if r["student_id"] == s1.id)
    assert tahmid_res["passed_all"] is True
    assert tahmid_res["gpa"] == 4.5
    assert tahmid_res["overall_grade"] == "A"
    assert tahmid_res["class_rank"] == 1

    # Nabila (s2) failed 1 subject -> GPA 0.0, Grade F
    nabila_res = next(r for r in results if r["student_id"] == s2.id)
    assert nabila_res["passed_all"] is False
    assert nabila_res["gpa"] == 0.0
    assert nabila_res["overall_grade"] == "F"
    assert nabila_res["class_rank"] is None


def test_export_tabulation_excel(db_session):
    ExamService.seed_default_grading_scale(db_session)
    ay = db_session.query(AcademicYear).first()
    cls_obj = db_session.query(SchoolClass).first()
    sub1 = db_session.query(Subject).first()
    s1 = db_session.query(Student).first()

    term = ExamRepository.create_exam_term(db_session, {
        "name": "Model Test 2026",
        "exam_code": "MDL-2026",
        "academic_year_id": ay.id,
        "start_date": date(2026, 9, 1),
        "end_date": date(2026, 9, 10)
    })
    ExamRepository.upsert_student_mark(db_session, {
        "exam_term_id": term.id,
        "class_id": cls_obj.id,
        "subject_id": sub1.id,
        "student_id": s1.id,
        "theory_marks": 80.0
    })

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tf:
        out_excel = tf.name

    try:
        ok = ExamService.export_tabulation_excel(db_session, term.id, cls_obj.id, out_excel)
        assert ok is True
        assert os.path.exists(out_excel)
        assert os.path.getsize(out_excel) > 1000
    finally:
        if os.path.exists(out_excel):
            os.remove(out_excel)


def test_report_card_pdf_generation(db_session):
    ExamService.seed_default_grading_scale(db_session)
    ay = db_session.query(AcademicYear).first()
    cls_obj = db_session.query(SchoolClass).first()
    sub1 = db_session.query(Subject).first()
    s1 = db_session.query(Student).first()

    term = ExamRepository.create_exam_term(db_session, {
        "name": "Annual Exam 2026",
        "exam_code": "ANN-2026",
        "academic_year_id": ay.id,
        "start_date": date(2026, 11, 1),
        "end_date": date(2026, 11, 15)
    })
    ExamRepository.upsert_student_mark(db_session, {
        "exam_term_id": term.id,
        "class_id": cls_obj.id,
        "subject_id": sub1.id,
        "student_id": s1.id,
        "theory_marks": 78.0,
        "mcq_marks": 18.0
    })
    ExamService.compile_class_results(db_session, term.id, cls_obj.id)

    summary = ExamRepository.get_student_result_summary(db_session, term.id, s1.id)
    marks = ExamRepository.get_marks_for_student(db_session, term.id, s1.id)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        out_pdf = tf.name

    try:
        ok = ReportCardPDFGenerator.generate_report_card(
            student=s1,
            exam_term=term,
            summary=summary,
            subject_marks=marks,
            school_info={"name": "Dhaka Residential Model High School", "eiin": "108254"},
            output_path=out_pdf
        )
        assert ok is True
        assert os.path.exists(out_pdf)
        assert os.path.getsize(out_pdf) > 2000
    finally:
        if os.path.exists(out_pdf):
            os.remove(out_pdf)
