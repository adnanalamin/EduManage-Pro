"""
EduManage Pro - Upgraded Academic Management Test Suite (Pytest)
Validates Academic Years, Groups, Shifts, Departments, Rooms, Custom Class Structures,
Configuration Wizard, Non-Destructive Year Cloning, Optional Subjects,
Class & Subject Teachers, Single/Bulk Promotion, Graduation, Class & Section Transfers,
Academic Calendar, and Strict Historical Record Preservation.
"""

from datetime import date
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.models.academic import (
    AcademicGroup,
    AcademicRoom,
    AcademicShift,
    AcademicYear,
    SchoolClass,
    Section,
    StudentSubjectEnrollment,
    Subject,
)
from app.models.staff import Department, Teacher, TeacherSubjectAssignment
from app.models.student import (
    Student,
    StudentAcademicHistory,
    StudentPromotionHistory,
    StudentStatus,
    StudentTransferHistory,
)
from app.repositories.academic_repository import AcademicRepository
from app.services.academic_service import AcademicService
from app.services.student_service import StudentService


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    AcademicService.ensure_academic_defaults(session)
    dept = session.query(Department).first()

    t1 = Teacher(
        teacher_id="TCH-2025-0001",
        employee_id="EMP-2001",
        full_name="Dr. Kamal Hossain",
        gender="Male",
        date_of_birth=date(1982, 5, 10),
        phone="+8801711000111",
        email="kamal@edumanage.local",
        qualification="Ph.D. in Mathematics",
        department_id=dept.id,
        primary_subject="Mathematics",
        salary=55000,
        status="active",
    )
    t2 = Teacher(
        teacher_id="TCH-2025-0002",
        employee_id="EMP-2002",
        full_name="Ms. Farhana Rahman",
        gender="Female",
        date_of_birth=date(1988, 9, 20),
        phone="+8801711000222",
        email="farhana@edumanage.local",
        qualification="M.Sc. in Computer Science",
        department_id=dept.id,
        primary_subject="ICT",
        salary=48000,
        status="active",
    )
    session.add_all([t1, t2])
    session.commit()

    yield session
    session.close()


def _admit_sample_student(db, *, roll: int, class_id: int, section_id: int, ay_id: int, fname: str, lname: str, phone_suffix: str):
    ok, stu, msg = StudentService.admit_student(
        db,
        {
            "roll_number": roll,
            "first_name": fname,
            "last_name": lname,
            "gender": "Male",
            "date_of_birth": date(2010, 2, 14),
            "class_id": class_id,
            "section_id": section_id,
            "academic_year_id": ay_id,
            "phone": f"+8801811{phone_suffix}",
        },
        {
            "guardian_name": f"Parent of {fname}",
            "guardian_phone": f"+8801911{phone_suffix}",
            "relation": "Father",
        },
        current_username="tester",
    )
    assert ok, msg
    return stu


def test_academic_wizard_custom_structure_and_non_destructive_clone(db_session):
    # 1. Run Academic Configuration Wizard for 2025-2026 with custom multi-stream classes, custom shift & rooms
    cfg = {
        "academic_year": {
            "name": "2025-2026",
            "start_date": date(2025, 1, 1),
            "end_date": date(2025, 12, 31),
            "is_current": True,
            "status": "Active",
        },
        "groups": [{"name": "Technical", "code": "TECH", "description": "Vocational track"}],
        "shifts": [{"name": "Weekend", "code": "WKD", "start_time": "09:00 AM", "end_time": "01:00 PM"}],
        "rooms": [
            {"room_number": "R-301", "room_name": "Physics Wing", "room_type": "Classroom", "capacity": 45},
            {"room_number": "LAB-1", "room_name": "Computer Lab", "room_type": "Computer Lab", "capacity": 30},
        ],
        "structure_profile": "Secondary Streams",
        "classes": [
            {
                "name": "Class 9",
                "code": "C09-SCI",
                "numeric_order": 9,
                "group": "Science",
                "shift": "Morning",
                "sections": [
                    {"name": "A", "room_number": "R-301", "capacity": 45},
                    {"name": "B", "room_number": "LAB-1", "capacity": 30},
                ],
                "subjects": [
                    {"name": "Higher Math", "code": "HM101", "subject_type": "Mandatory", "full_marks": 100, "pass_marks": 33},
                    {"name": "Computer Studies", "code": "CS102", "subject_type": "Optional", "full_marks": 100, "pass_marks": 33},
                ],
            },
            {
                "name": "Class 9",
                "code": "C09-HUM",
                "numeric_order": 9,
                "group": "Humanities",
                "shift": "Day",
                "sections": [{"name": "A", "capacity": 40}],
                "subjects": [{"name": "Civics", "code": "CIV101", "subject_type": "Mandatory"}],
            },
        ],
    }

    ok, summary, msg = AcademicService.apply_academic_configuration_wizard(db_session, cfg, current_user="admin")
    assert ok, msg
    assert summary["classes_created"] == 2
    assert summary["sections_created"] == 3
    assert summary["subjects_created"] == 3
    assert summary["rooms_created"] == 2

    ay_2025_id = summary["academic_year_id"]
    cls_sci_2025 = (
        db_session.query(SchoolClass)
        .filter_by(academic_year_id=ay_2025_id, name="Class 9", group="Science")
        .first()
    )
    assert cls_sci_2025 is not None
    sec_a = db_session.query(Section).filter_by(class_id=cls_sci_2025.id, name="A").first()
    assert sec_a.room_id is not None
    assert sec_a.room_number == "R-301"

    # 2. Clone structure into new 2026-2027 session non-destructively
    ay_2026, ay_msg = AcademicService.create_academic_year(
        db_session,
        {
            "name": "2026-2027",
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "is_current": False,
            "status": "Upcoming",
        },
    )
    assert ay_2026 is not None, ay_msg

    ok_clone, clone_cnt, c_msg = AcademicService.clone_academic_structure(
        db_session, source_year_id=ay_2025_id, target_year_id=ay_2026.id
    )
    assert ok_clone, c_msg
    assert clone_cnt["classes_created"] == 2
    assert clone_cnt["sections_created"] == 3
    assert clone_cnt["subjects_created"] == 3

    # Verify original 2025-2026 records remain completely intact & distinct IDs
    classes_2025 = AcademicRepository.get_classes(db_session, academic_year_id=ay_2025_id)
    classes_2026 = AcademicRepository.get_classes(db_session, academic_year_id=ay_2026.id)
    assert len(classes_2025) == 2
    assert len(classes_2026) == 2
    assert {c.id for c in classes_2025}.isdisjoint({c.id for c in classes_2026})


def test_teachers_optional_subjects_and_calendar(db_session):
    ay, _ = AcademicService.create_academic_year(
        db_session,
        {"name": "2025-2026", "start_date": date(2025, 1, 1), "end_date": date(2025, 12, 31), "is_current": True},
    )
    cls_10, _ = AcademicService.create_class(
        db_session,
        {"name": "Class 10", "code": "C10", "numeric_order": 10, "group": "Science", "academic_year_id": ay.id},
    )
    sec_a, _ = AcademicService.create_section(
        db_session, {"name": "Alpha", "class_id": cls_10.id, "capacity": 40}
    )
    sub_opt, _ = AcademicService.create_subject(
        db_session,
        {
            "name": "Higher Biology",
            "code": "BIO4",
            "subject_type": "Optional",
            "full_marks": 100,
            "pass_marks": 33,
            "class_id": cls_10.id,
        },
    )
    assert sub_opt.is_optional is True

    t1, t2 = db_session.query(Teacher).order_by(Teacher.id).all()
    sec_updated, _ = AcademicService.assign_class_teacher(db_session, sec_a.id, t1.id)
    assert sec_updated.class_teacher_id == t1.id

    sub_updated, _ = AcademicService.assign_subject_teacher(db_session, sub_opt.id, t2.id, weekly_periods=4)
    assert sub_updated.teacher_id == t2.id
    hr_link = db_session.query(TeacherSubjectAssignment).filter_by(teacher_id=t2.id, subject_id=sub_opt.id).first()
    assert hr_link is not None and hr_link.weekly_periods == 4

    stu = _admit_sample_student(
        db_session, roll=1, class_id=cls_10.id, section_id=sec_a.id, ay_id=ay.id, fname="Arif", lname="Islam", phone_suffix="0001"
    )
    enr, enr_msg = AcademicService.enroll_student_subject(db_session, stu.id, sub_opt.id)
    assert enr is not None, enr_msg
    assert enr.is_optional is True and enr.enrollment_status == "Active"

    # Academic Calendar Event
    ev, ev_msg = AcademicService.create_calendar_event(
        db_session,
        event_title="Annual Science Fair",
        start_date=date(2025, 8, 12),
        end_date=date(2025, 8, 13),
        event_category="Academic",
        academic_year_id=ay.id,
        term_name="Term 2",
    )
    assert ev is not None, ev_msg
    events = AcademicRepository.list_calendar_events(db_session, academic_year_id=ay.id)
    assert len(events) == 1 and events[0].term_name == "Term 2"


def test_promotions_transfers_and_strict_historical_preservation(db_session):
    # Setup Year 2025 and Year 2026
    ay_2025, _ = AcademicService.create_academic_year(
        db_session,
        {"name": "2025", "start_date": date(2025, 1, 1), "end_date": date(2025, 12, 31), "is_current": True},
    )
    ay_2026, _ = AcademicService.create_academic_year(
        db_session,
        {"name": "2026", "start_date": date(2026, 1, 1), "end_date": date(2026, 12, 31), "is_current": False, "status": "Upcoming"},
    )

    c9_25, _ = AcademicService.create_class(
        db_session, {"name": "Class 9", "code": "C9", "numeric_order": 9, "group": "Science", "academic_year_id": ay_2025.id}
    )
    c9_hum_25, _ = AcademicService.create_class(
        db_session,
        {"name": "Class 9", "code": "C9-H", "numeric_order": 9, "group": "Humanities", "academic_year_id": ay_2025.id},
        allow_multi_stream=True,
    )
    s9a, _ = AcademicService.create_section(db_session, {"name": "A", "class_id": c9_25.id, "capacity": 40})
    s9b, _ = AcademicService.create_section(db_session, {"name": "B", "class_id": c9_25.id, "capacity": 40})
    s9h, _ = AcademicService.create_section(db_session, {"name": "A", "class_id": c9_hum_25.id, "capacity": 40})

    c10_26, _ = AcademicService.create_class(
        db_session, {"name": "Class 10", "code": "C10", "numeric_order": 10, "group": "Science", "academic_year_id": ay_2026.id}
    )
    s10a, _ = AcademicService.create_section(db_session, {"name": "A", "class_id": c10_26.id, "capacity": 40})

    s1 = _admit_sample_student(db_session, roll=10, class_id=c9_25.id, section_id=s9a.id, ay_id=ay_2025.id, fname="Tariq", lname="Aziz", phone_suffix="1111")
    s2 = _admit_sample_student(db_session, roll=11, class_id=c9_25.id, section_id=s9a.id, ay_id=ay_2025.id, fname="Nadia", lname="Karim", phone_suffix="2222")
    s3 = _admit_sample_student(db_session, roll=12, class_id=c9_25.id, section_id=s9a.id, ay_id=ay_2025.id, fname="Sajid", lname="Khan", phone_suffix="3333")

    # 1. Section Transfer for s1: Section A -> Section B inside Class 9 (2025)
    ok_st, s1, st_msg = AcademicService.transfer_student_section(
        db_session, s1.id, to_section_id=s9b.id, new_roll_number=3, reason="Lab group rebalance"
    )
    assert ok_st, st_msg
    assert s1.section_id == s9b.id and s1.roll_number == 3

    # 2. Class Transfer for s2: Class 9 Science -> Class 9 Humanities (2025)
    ok_ct, s2, ct_msg = AcademicService.transfer_student_class(
        db_session, s2.id, to_class_id=c9_hum_25.id, to_section_id=s9h.id, new_roll_number=1, reason="Stream change"
    )
    assert ok_ct, ct_msg
    assert s2.class_id == c9_hum_25.id and s2.group == "Humanities"

    # Verify s1 and s2 previous history rows were NOT overwritten!
    s1_hist = db_session.query(StudentAcademicHistory).filter_by(student_id=s1.id).order_by(StudentAcademicHistory.id.asc()).all()
    assert len(s1_hist) == 2
    assert s1_hist[0].section_id == s9a.id and s1_hist[0].roll_number == 10 and s1_hist[0].result_status == "Section Transferred"
    assert s1_hist[1].section_id == s9b.id and s1_hist[1].roll_number == 3 and s1_hist[1].result_status == "Enrolled"

    # 3. Single Promotion for s1 (2025 Class 9 -> 2026 Class 10) with GPA capture
    ok_sp, s1, sp_msg = AcademicService.promote_single_student(
        db_session,
        s1.id,
        to_class_id=c10_26.id,
        to_academic_year_id=ay_2026.id,
        to_section_id=s10a.id,
        new_roll_number=1,
        gpa=4.85,
        final_grade="A+",
    )
    assert ok_sp, sp_msg
    assert s1.academic_year_id == ay_2026.id and s1.class_id == c10_26.id

    # Verify 2025 records remain untouched on s1!
    s1_hist_after = db_session.query(StudentAcademicHistory).filter_by(student_id=s1.id).order_by(StudentAcademicHistory.id.asc()).all()
    assert len(s1_hist_after) == 3
    assert s1_hist_after[0].academic_year_id == ay_2025.id and s1_hist_after[0].section_id == s9a.id
    assert s1_hist_after[1].academic_year_id == ay_2025.id and s1_hist_after[1].result_status == "Promoted" and s1_hist_after[1].gpa == 4.85
    assert s1_hist_after[2].academic_year_id == ay_2026.id and s1_hist_after[2].class_id == c10_26.id and s1_hist_after[2].result_status == "Enrolled"

    # 4. Bulk Promotion for s2 -> 2026 Class 10
    ok_bp, bp_cnt, bp_msg = AcademicService.bulk_promote_students(
        db_session,
        student_ids=[s2.id],
        to_class_id=c10_26.id,
        to_academic_year_id=ay_2026.id,
        to_section_id=s10a.id,
        auto_assign_rolls=True,
        starting_roll=2,
        gpas_by_student={s2.id: 4.50},
    )
    assert ok_bp and bp_cnt == 1, bp_msg
    db_session.refresh(s2)
    assert s2.roll_number == 2 and s2.class_id == c10_26.id

    # 5. Graduation via bulk_promote_students for s3
    ok_grad, grad_cnt, grad_msg = AcademicService.bulk_promote_students(
        db_session,
        student_ids=[s3.id],
        to_class_id=None,
        to_academic_year_id=None,
        mark_graduated=True,
        gpas_by_student={s3.id: 5.00},
    )
    assert ok_grad and grad_cnt == 1, grad_msg
    db_session.refresh(s3)
    assert s3.status == StudentStatus.GRADUATED

    # 6. Historical protection guard: deleting Class 9 (2025) must fail cleanly
    del_ok, del_msg = AcademicService.safe_delete_class(db_session, c9_25.id)
    assert del_ok is False
    assert "historical" in del_msg.lower() or "depend" in del_msg.lower()

    # 7. Full academic history viewer returns complete non-overwritten timeline
    hist_bundle = AcademicService.get_student_academic_history(db_session, s1.id)
    assert len(hist_bundle["academic_history"]) == 3
    assert len(hist_bundle["transfers"]) == 1
    assert len(hist_bundle["promotions"]) == 1
