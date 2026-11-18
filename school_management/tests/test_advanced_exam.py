"""
EduManage Pro - Advanced Examination Engine Unit & Governance Tests (Pytest)
Validates:
- Configurable Exam Types & Schedules (Theory, MCQ, Practical, Viva, Attendance)
- Customizable Grading Systems & Rules (Component Pass, Grace Marks, Optional Subject Bonus, GPA-4/GPA-5)
- Attendance Percentage Sync into Exam Marks
- Multi-Term CGPA + Class Position & Section Position
- Question Bank, Written Papers & Auto-Graded MCQ Assessments with Mark Sync
- Verification -> Approval -> Publish Lock & Authorized Reopen + Immutable Result History
- Tabulation Excel/PDF, Official Mark Sheet PDF, Merit List PDF & Question Paper PDF
"""

from datetime import date
import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.database.init_db import SYSTEM_ROLES
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.models.attendance import StudentAttendance
from app.models.exam import (
    ExamPaper,
    ExamResultBatch,
    ExamResultHistory,
    ExamSchedule,
    ExamTerm,
    ExamType,
    GradingSystem,
    MCQAttempt,
    QuestionBankItem,
    ResultWorkflowStatus,
    StudentMark,
)
from app.models.student import Guardian, Student
from app.models.user import Role, User
from app.reports.exam_reports_pdf import ExamReportsPDFGenerator
from app.reports.report_card_pdf import ReportCardPDFGenerator
from app.repositories.exam_repository import ExamRepository
from app.services.auth_service import AuthService
from app.services.exam_service import ExamService


@pytest.fixture(scope="function")
def exam_env():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    for code, disp, desc, is_sys in SYSTEM_ROLES:
        db.add(Role(name=code, display_name=disp, description=desc, is_system_role=is_sys, is_active=True))
    db.commit()
    AuthService.sync_permission_catalog(db)
    ExamService.seed_default_grading_scale(db)
    ExamService.seed_default_exam_types(db)
    ExamService.seed_default_grading_system(db)

    admin_role = db.query(Role).filter_by(name="super_admin").first()
    teacher_role = db.query(Role).filter_by(name="teacher").first()

    admin_user = User(
        username="exam_admin",
        full_name="Controller Admin",
        password_hash="hashed",
        role="super_admin",
        role_id=admin_role.id if admin_role else None,
        is_active=True,
    )
    teacher_user = User(
        username="exam_teacher",
        full_name="Senior Teacher",
        password_hash="hashed",
        role="teacher",
        role_id=teacher_role.id if teacher_role else None,
        is_active=True,
    )
    db.add_all([admin_user, teacher_user])
    db.flush()

    ay = AcademicYear(name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True)
    db.add(ay)
    db.flush()

    cls_obj = SchoolClass(name="Class 10", code="C10", numeric_order=10, academic_year_id=ay.id)
    db.add(cls_obj)
    db.flush()

    sec_a = Section(name="Section A", class_id=cls_obj.id, capacity=40)
    sec_b = Section(name="Section B", class_id=cls_obj.id, capacity=40)
    db.add_all([sec_a, sec_b])
    db.flush()

    sub_phy = Subject(name="Physics", code="PHY10", class_id=cls_obj.id, full_marks=100, pass_marks=33)
    sub_chem = Subject(name="Chemistry", code="CHM10", class_id=cls_obj.id, full_marks=100, pass_marks=33)
    sub_bio = Subject(name="Biology (Opt)", code="BIO10", class_id=cls_obj.id, full_marks=100, pass_marks=33)
    db.add_all([sub_phy, sub_chem, sub_bio])
    db.flush()

    g = Guardian(guardian_name="Guardian X", relation="Father", guardian_phone="+8801711111111")
    db.add(g)
    db.flush()

    stu1 = Student(
        student_id="STU-ADV-001",
        admission_number="ADM-ADV-001",
        roll_number=1,
        first_name="Ayan",
        last_name="Rahman",
        full_name="Ayan Rahman",
        gender="Male",
        date_of_birth=date(2010, 3, 15),
        admission_date=date(2026, 1, 2),
        class_id=cls_obj.id,
        section_id=sec_a.id,
        academic_year_id=ay.id,
        guardian_id=g.id,
        status="Active",
    )
    stu2 = Student(
        student_id="STU-ADV-002",
        admission_number="ADM-ADV-002",
        roll_number=2,
        first_name="Mehnaz",
        last_name="Karim",
        full_name="Mehnaz Karim",
        gender="Female",
        date_of_birth=date(2010, 6, 10),
        admission_date=date(2026, 1, 2),
        class_id=cls_obj.id,
        section_id=sec_b.id,
        academic_year_id=ay.id,
        guardian_id=g.id,
        status="Active",
    )
    db.add_all([stu1, stu2])
    db.commit()

    yield {
        "db": db,
        "admin": admin_user,
        "teacher": teacher_user,
        "ay": ay,
        "cls": cls_obj,
        "sec_a": sec_a,
        "sec_b": sec_b,
        "phy": sub_phy,
        "chem": sub_chem,
        "bio": sub_bio,
        "stu1": stu1,
        "stu2": stu2,
    }
    db.close()


def test_component_marks_pass_rules_grace_and_optional_bonus(exam_env):
    db = exam_env["db"]
    admin = exam_env["admin"]
    ay, cls_obj, phy, chem, bio = (
        exam_env["ay"],
        exam_env["cls"],
        exam_env["phy"],
        exam_env["chem"],
        exam_env["bio"],
    )
    stu1, stu2 = exam_env["stu1"], exam_env["stu2"]

    ok, custom_gs, msg = ExamService.create_grading_system(
        db,
        {
            "name": "Science Board + Grace 2",
            "code": "SCI-GR2",
            "max_gpa": 5.0,
            "pass_percentage": 33.0,
            "require_component_pass": True,
            "grace_marks_limit": 2.0,
            "optional_subject_enabled": True,
            "optional_subject_min_gp": 2.0,
            "cgpa_mode": "WeightedTerms",
        },
        [
            {"grade_name": "A+", "grade_point": 5.0, "mark_from": 80.0, "mark_to": 100.0, "is_passing": True, "remarks": "Outstanding"},
            {"grade_name": "A", "grade_point": 4.0, "mark_from": 70.0, "mark_to": 79.99, "is_passing": True, "remarks": "Excellent"},
            {"grade_name": "B", "grade_point": 3.0, "mark_from": 50.0, "mark_to": 69.99, "is_passing": True, "remarks": "Good"},
            {"grade_name": "D", "grade_point": 1.0, "mark_from": 33.0, "mark_to": 49.99, "is_passing": True, "remarks": "Pass"},
            {"grade_name": "F", "grade_point": 0.0, "mark_from": 0.0, "mark_to": 32.99, "is_passing": False, "remarks": "Fail"},
        ],
        actor_user=admin,
    )
    assert ok is True, msg

    mid_type = db.query(ExamType).filter_by(code="MID").first()
    term = ExamRepository.create_exam_term(
        db,
        {
            "name": "Half-Yearly Science 2026",
            "exam_code": "HY-SCI-26",
            "academic_year_id": ay.id,
            "exam_type_id": mid_type.id,
            "grading_system_id": custom_gs.id,
            "start_date": date(2026, 6, 1),
            "end_date": date(2026, 6, 15),
        },
    )

    # Physics schedule with Viva & Practical & Attendance and component pass
    ExamRepository.create_or_update_schedule(
        db,
        {
            "exam_term_id": term.id,
            "class_id": cls_obj.id,
            "subject_id": phy.id,
            "exam_date": date(2026, 6, 2),
            "full_marks": 100.0,
            "pass_marks": 33.0,
            "theory_full": 50.0,
            "mcq_full": 20.0,
            "practical_full": 15.0,
            "viva_full": 10.0,
            "attendance_full": 5.0,
            "theory_pass": 17.0,
            "practical_pass": 5.0,
            "viva_pass": 3.0,
            "require_component_pass": True,
        },
    )
    # Chemistry (no component fail trap, tests grace mark rule)
    ExamRepository.create_or_update_schedule(
        db,
        {
            "exam_term_id": term.id,
            "class_id": cls_obj.id,
            "subject_id": chem.id,
            "exam_date": date(2026, 6, 4),
            "full_marks": 100.0,
            "pass_marks": 33.0,
            "theory_full": 70.0,
            "mcq_full": 20.0,
            "viva_full": 5.0,
            "attendance_full": 5.0,
        },
    )
    # Biology Optional 4th subject
    ExamRepository.create_or_update_schedule(
        db,
        {
            "exam_term_id": term.id,
            "class_id": cls_obj.id,
            "subject_id": bio.id,
            "exam_date": date(2026, 6, 6),
            "full_marks": 100.0,
            "pass_marks": 33.0,
            "is_optional_eligible": True,
        },
    )

    # Student 1: Physics 72 (A, 4.0) across all components + Chemistry 31 -> receives +2 grace to 33 (D, 1.0) + Bio Optional 85 (A+, 5.0 -> +3.0 bonus)
    m_phy1 = ExamRepository.upsert_student_mark(
        db,
        {
            "exam_term_id": term.id,
            "class_id": cls_obj.id,
            "subject_id": phy.id,
            "student_id": stu1.id,
            "theory_marks": 35.0,
            "mcq_marks": 15.0,
            "practical_marks": 10.0,
            "viva_marks": 7.0,
            "attendance_marks": 5.0,
        },
        actor_user=admin,
    )
    assert m_phy1.total_marks == 72.0
    assert m_phy1.grade_name == "A"

    m_chem1 = ExamRepository.upsert_student_mark(
        db,
        {
            "exam_term_id": term.id,
            "class_id": cls_obj.id,
            "subject_id": chem.id,
            "student_id": stu1.id,
            "theory_marks": 31.0,
        },
        actor_user=admin,
    )
    assert m_chem1.grace_marks_applied == 2.0
    assert m_chem1.total_marks == 33.0
    assert m_chem1.is_passed is True
    assert m_chem1.grade_name == "D"

    ExamRepository.upsert_student_mark(
        db,
        {
            "exam_term_id": term.id,
            "class_id": cls_obj.id,
            "subject_id": bio.id,
            "student_id": stu1.id,
            "theory_marks": 85.0,
            "is_optional": True,
        },
        actor_user=admin,
    )

    # Student 2: fails Viva component rule in Physics (total 60 > 33, but viva=1 < viva_pass=3) -> Must fail!
    m_phy2 = ExamRepository.upsert_student_mark(
        db,
        {
            "exam_term_id": term.id,
            "class_id": cls_obj.id,
            "subject_id": phy.id,
            "student_id": stu2.id,
            "theory_marks": 40.0,
            "mcq_marks": 12.0,
            "practical_marks": 7.0,
            "viva_marks": 1.0,
            "attendance_marks": 0.0,
        },
        actor_user=admin,
    )
    assert m_phy2.total_marks == 60.0
    assert m_phy2.is_passed is False
    assert m_phy2.grade_name == "F"

    res = ExamService.compile_class_results(db, term.id, cls_obj.id, actor_user=admin)
    r1 = next(r for r in res if r["student_id"] == stu1.id)
    r2 = next(r for r in res if r["student_id"] == stu2.id)

    # Core GPs for stu1: (4.0 + 1.0 + optional bonus 3.0) / 2 = 4.00
    assert r1["passed_all"] is True
    assert r1["optional_bonus_gp"] == 3.0
    assert r1["gpa"] == 4.0
    assert r1["class_rank"] == 1
    assert r1["section_rank"] == 1

    assert r2["passed_all"] is False
    assert r2["gpa"] == 0.0
    assert r2["class_rank"] is None


def test_attendance_sync_and_multi_term_cgpa(exam_env):
    db = exam_env["db"]
    admin = exam_env["admin"]
    ay, cls_obj, phy = exam_env["ay"], exam_env["cls"], exam_env["phy"]
    stu1 = exam_env["stu1"]

    # Record 4 days attendance for stu1 (3 Present + 1 Absent = 75%)
    for idx, st in enumerate(["Present", "Present", "Present", "Absent"], 1):
        db.add(
            StudentAttendance(
                student_id=stu1.id,
                class_id=cls_obj.id,
                date=date(2026, 2, idx),
                status=st,
            )
        )
    db.commit()

    mid_type = db.query(ExamType).filter_by(code="MID").first()
    ann_type = db.query(ExamType).filter_by(code="ANN").first()

    t1 = ExamRepository.create_exam_term(
        db,
        {
            "name": "Term 1 Mid",
            "exam_code": "T1-MID-26",
            "academic_year_id": ay.id,
            "exam_type_id": mid_type.id,
            "weight_pct": 40.0,
            "start_date": date(2026, 5, 1),
            "end_date": date(2026, 5, 10),
        },
    )
    t2 = ExamRepository.create_exam_term(
        db,
        {
            "name": "Term 2 Annual",
            "exam_code": "T2-ANN-26",
            "academic_year_id": ay.id,
            "exam_type_id": ann_type.id,
            "weight_pct": 60.0,
            "start_date": date(2026, 11, 1),
            "end_date": date(2026, 11, 10),
        },
    )

    ExamRepository.create_or_update_schedule(
        db,
        {
            "exam_term_id": t1.id,
            "class_id": cls_obj.id,
            "subject_id": phy.id,
            "exam_date": date(2026, 5, 2),
            "full_marks": 100.0,
            "theory_full": 80.0,
            "mcq_full": 0.0,
            "attendance_full": 20.0,
        },
    )

    synced_cnt = ExamService.sync_attendance_marks_for_term(db, t1.id, cls_obj.id, actor_user=admin)
    assert synced_cnt == 1
    mark_t1 = ExamRepository.get_marks_for_student(db, t1.id, stu1.id)[0]
    assert mark_t1.attendance_marks == 15.0  # 75% of 20

    # Set Term 1 total = 70 (A -> 4.0)
    ExamRepository.upsert_student_mark(
        db,
        {
            "exam_term_id": t1.id,
            "class_id": cls_obj.id,
            "subject_id": phy.id,
            "student_id": stu1.id,
            "theory_marks": 55.0,
            "attendance_marks": 15.0,
        },
        actor_user=admin,
    )
    ExamService.compile_class_results(db, t1.id, cls_obj.id, actor_user=admin)

    # Term 2 total = 85 (A+ -> 5.0)
    ExamRepository.upsert_student_mark(
        db,
        {
            "exam_term_id": t2.id,
            "class_id": cls_obj.id,
            "subject_id": phy.id,
            "student_id": stu1.id,
            "theory_marks": 85.0,
        },
        actor_user=admin,
    )
    res2 = ExamService.compile_class_results(db, t2.id, cls_obj.id, actor_user=admin)
    r_stu1 = next(r for r in res2 if r["student_id"] == stu1.id)
    # Weighted CGPA: (4.0*40 + 5.0*60) / (40+60) = 460 / 100 = 4.60
    assert r_stu1["gpa"] == 5.0
    assert r_stu1["cgpa"] == 4.6


def test_question_bank_mcq_autograde_and_pdfs(exam_env):
    db = exam_env["db"]
    admin = exam_env["admin"]
    teacher = exam_env["teacher"]
    ay, cls_obj, phy, stu1 = exam_env["ay"], exam_env["cls"], exam_env["phy"], exam_env["stu1"]

    term = ExamRepository.create_exam_term(
        db,
        {
            "name": "Quarterly MCQ & Written",
            "exam_code": "QTR-26",
            "academic_year_id": ay.id,
            "start_date": date(2026, 8, 1),
            "end_date": date(2026, 8, 10),
        },
    )

    ok1, q1, _ = ExamService.add_question(
        db,
        {
            "subject_id": phy.id,
            "class_id": cls_obj.id,
            "question_type": "MCQ",
            "topic": "Kinematics",
            "question_text": "What is the SI unit of acceleration?",
            "options": {"A": "m/s", "B": "m/s^2", "C": "N", "D": "J"},
            "correct_option": "B",
            "marks": 5.0,
            "negative_marks": 1.0,
        },
        actor_user=teacher,
    )
    ok2, q2, _ = ExamService.add_question(
        db,
        {
            "subject_id": phy.id,
            "class_id": cls_obj.id,
            "question_type": "MCQ",
            "topic": "Dynamics",
            "question_text": "Newton's second law states F = ?",
            "options": {"A": "mv", "B": "ma", "C": "m/a", "D": "a/m"},
            "correct_option": "B",
            "marks": 5.0,
            "negative_marks": 1.0,
        },
        actor_user=teacher,
    )
    ok3, q3, _ = ExamService.add_question(
        db,
        {
            "subject_id": phy.id,
            "class_id": cls_obj.id,
            "question_type": "Written",
            "topic": "Work & Energy",
            "question_text": "Derive kinetic energy formula KE = 1/2 mv^2.",
            "model_answer": "Using v^2 = u^2 + 2as and W = F*s = mas.",
            "marks": 10.0,
        },
        actor_user=teacher,
    )
    assert ok1 and ok2 and ok3

    ok_p, paper, msg_p = ExamService.create_exam_paper(
        db,
        {
            "title": "Physics Mid Assessment Paper",
            "exam_term_id": term.id,
            "class_id": cls_obj.id,
            "subject_id": phy.id,
            "paper_type": "Combined",
            "duration_minutes": 45,
            "pass_marks": 4.0,
            "negative_marking": True,
        },
        question_entries=[
            {"question_id": q1.id, "section_label": "Part A (MCQ)", "marks": 5.0, "order_no": 1},
            {"question_id": q2.id, "section_label": "Part A (MCQ)", "marks": 5.0, "order_no": 2},
            {"question_id": q3.id, "section_label": "Part B (Written)", "marks": 10.0, "order_no": 3},
        ],
        actor_user=teacher,
    )
    assert ok_p is True, msg_p

    # Stu1 answers q1 right (+5) and q2 wrong (-1) -> net MCQ score = 4.0 synced to StudentMark.mcq_marks
    ok_att, attempt, msg_att = ExamService.submit_mcq_attempt(
        db,
        paper.id,
        stu1.id,
        {q1.id: "B", q2.id: "A"},
        auto_sync_to_marks=True,
        actor_user=teacher,
    )
    assert ok_att is True, msg_att
    assert attempt.correct_count == 1
    assert attempt.wrong_count == 1
    assert attempt.negative_deducted == 1.0
    assert attempt.net_score == 4.0
    assert attempt.synced_to_marks is True

    synced_mark = ExamRepository.get_marks_for_student(db, term.id, stu1.id)[0]
    assert synced_mark.mcq_marks == 4.0

    # Add theory marks & compile results, then generate all PDF & Excel reports
    ExamRepository.upsert_student_mark(
        db,
        {
            "exam_term_id": term.id,
            "class_id": cls_obj.id,
            "subject_id": phy.id,
            "student_id": stu1.id,
            "theory_marks": 76.0,
            "mcq_marks": 4.0,
        },
        actor_user=admin,
    )
    ExamService.compile_class_results(db, term.id, cls_obj.id, actor_user=admin)

    with tempfile.TemporaryDirectory() as tmpdir:
        qp_pdf = ExamReportsPDFGenerator.generate_question_paper_pdf(
            db, paper.id, os.path.join(tmpdir, "paper.pdf"), include_answer_key=True
        )
        ms_pdf = ExamReportsPDFGenerator.generate_mark_sheet_pdf(
            db, term.id, stu1.id, os.path.join(tmpdir, "marksheet.pdf")
        )
        ml_pdf = ExamReportsPDFGenerator.generate_merit_list_pdf(
            db, term.id, cls_obj.id, os.path.join(tmpdir, "merit.pdf")
        )
        tb_pdf = ExamReportsPDFGenerator.generate_tabulation_pdf(
            db, term.id, cls_obj.id, os.path.join(tmpdir, "tabulation.pdf")
        )
        for p in (qp_pdf, ms_pdf, ml_pdf, tb_pdf):
            assert os.path.exists(p) and os.path.getsize(p) > 1000


def test_verification_approval_publish_lock_and_immutable_history(exam_env):
    db = exam_env["db"]
    admin = exam_env["admin"]
    teacher = exam_env["teacher"]
    ay, cls_obj, phy, stu1 = exam_env["ay"], exam_env["cls"], exam_env["phy"], exam_env["stu1"]

    term = ExamRepository.create_exam_term(
        db,
        {
            "name": "Locked Final Exam 2026",
            "exam_code": "LOCK-FIN-26",
            "academic_year_id": ay.id,
            "start_date": date(2026, 12, 1),
            "end_date": date(2026, 12, 10),
        },
    )

    ExamRepository.upsert_student_mark(
        db,
        {
            "exam_term_id": term.id,
            "class_id": cls_obj.id,
            "subject_id": phy.id,
            "student_id": stu1.id,
            "theory_marks": 82.0,
        },
        actor_user=teacher,
    )
    ExamService.compile_class_results(db, term.id, cls_obj.id, actor_user=teacher)

    # Teacher can verify, but MUST be blocked from approving or publishing
    ok_v, batch, _ = ExamService.verify_class_results(db, term.id, cls_obj.id, notes="Checked totals", actor_user=teacher)
    assert ok_v is True
    assert batch.status == ResultWorkflowStatus.VERIFIED

    with pytest.raises(PermissionError):
        ExamService.approve_class_results(db, term.id, cls_obj.id, actor_user=teacher)

    with pytest.raises(PermissionError):
        ExamService.publish_class_results(db, term.id, cls_obj.id, actor_user=teacher)

    # Super Admin approves & publishes
    ok_a, batch, _ = ExamService.approve_class_results(db, term.id, cls_obj.id, actor_user=admin)
    assert ok_a is True
    assert batch.status == ResultWorkflowStatus.APPROVED

    ok_p, batch, _ = ExamService.publish_class_results(db, term.id, cls_obj.id, actor_user=admin)
    assert ok_p is True
    assert batch.status == ResultWorkflowStatus.PUBLISHED
    assert batch.is_published is True
    assert batch.is_locked is True

    # Once published, modifying marks OR recompiling must fail cleanly with PermissionError
    with pytest.raises(PermissionError):
        ExamRepository.upsert_student_mark(
            db,
            {
                "exam_term_id": term.id,
                "class_id": cls_obj.id,
                "subject_id": phy.id,
                "student_id": stu1.id,
                "theory_marks": 99.0,
            },
            actor_user=admin,
        )

    with pytest.raises(PermissionError):
        ExamService.compile_class_results(db, term.id, cls_obj.id, actor_user=admin)

    # Unauthorized reopen by teacher fails
    with pytest.raises(PermissionError):
        ExamService.reopen_published_results(db, term.id, cls_obj.id, reason="Fix", actor_user=teacher)

    # Super Admin controlled reopen with mandatory audit reason succeeds and bumps version
    ok_re, batch, _ = ExamService.reopen_published_results(
        db, term.id, cls_obj.id, reason="Re-evaluation board correction approved", actor_user=admin
    )
    assert ok_re is True
    assert batch.status == ResultWorkflowStatus.REOPENED
    assert batch.is_published is False
    assert batch.version_no == 2

    # Marks can now be corrected after audited reopen
    updated_mark = ExamRepository.upsert_student_mark(
        db,
        {
            "exam_term_id": term.id,
            "class_id": cls_obj.id,
            "subject_id": phy.id,
            "student_id": stu1.id,
            "theory_marks": 86.0,
            "reason": "Approved script scrutiny",
        },
        actor_user=admin,
    )
    assert updated_mark.total_marks == 86.0

    # History is immutable (cannot be deleted)
    history_rows = ExamRepository.list_result_history(db, exam_term_id=term.id, class_id=cls_obj.id)
    assert len(history_rows) >= 5  # COMPILED, VERIFIED, APPROVED, PUBLISHED, REOPENED, MARK_UPDATED
    with pytest.raises(ValueError):
        db.delete(history_rows[0])
        db.commit()
    db.rollback()
