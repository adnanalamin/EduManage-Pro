"""
EduManage Pro - Timetable & Routine Unit Tests
Phase 9: Period Slots, Routine Allocation, Collision Detection & ReportLab PDF
"""

import os
import tempfile
import pytest
from app.models.timetable import PeriodSlot, TimetableEntry
from app.models.academic import SchoolClass, Section, Subject
from app.models.staff import Teacher
from app.repositories.timetable_repository import TimetableRepository
from app.services.timetable_service import TimetableService
from app.reports.class_timetable_pdf import ClassTimetablePDFGenerator
from app.reports.teacher_routine_pdf import TeacherRoutinePDFGenerator


def test_seed_default_periods(db_session):
    """Verify period slot seeding creates bell slots including tiffin break."""
    periods = TimetableService.seed_default_periods(db_session)
    assert len(periods) >= 8

    teaching = [p for p in periods if not p.is_break]
    breaks = [p for p in periods if p.is_break]

    assert len(teaching) == 7
    assert len(breaks) >= 1


def test_timetable_slot_assignment_and_conflicts(db_session):
    """Verify routine slot assignment and teacher/room conflict detection."""
    periods = TimetableService.seed_default_periods(db_session)
    period_1 = [p for p in periods if p.period_number == 1][0]

    # Create dummy classes, subjects, and teachers if not present
    cls_10 = db_session.query(SchoolClass).filter(SchoolClass.numeric_order == 10).first()
    if not cls_10:
        cls_10 = SchoolClass(name="Class 10", code="CLS-10", numeric_order=10, academic_year_id=1)
        db_session.add(cls_10)
        db_session.commit()

    cls_9 = db_session.query(SchoolClass).filter(SchoolClass.numeric_order == 9).first()
    if not cls_9:
        cls_9 = SchoolClass(name="Class 9", code="CLS-9", numeric_order=9, academic_year_id=1)
        db_session.add(cls_9)
        db_session.commit()

    teacher_1 = db_session.query(Teacher).first()
    if not teacher_1:
        teacher_1 = Teacher(employee_id="EMP-T-01", name="Mohammad Kabir", gender="Male", date_of_birth="1980-01-01", phone="+880170000001", email="kabir@school.local", qualification="M.Sc. Math", status="Active")
        db_session.add(teacher_1)
        db_session.commit()

    sub_math = db_session.query(Subject).filter(Subject.class_id == cls_10.id).first()
    if not sub_math:
        sub_math = Subject(subject_id="SUB-101", name="Mathematics", code="MAT-101", class_id=cls_10.id, full_marks=100, pass_marks=33)
        db_session.add(sub_math)
        db_session.commit()

    # 1. Assign Teacher 1 to Class 10 on Sunday Period 1 in Room 301
    entry, conflicts = TimetableService.assign_timetable_slot(
        session=db_session,
        academic_year_id=1,
        class_id=cls_10.id,
        day_of_week="Sunday",
        period_slot_id=period_1.id,
        subject_id=sub_math.id,
        teacher_id=teacher_1.id,
        room_number="Room 301"
    )
    assert entry is not None
    assert len(conflicts) == 0

    # 2. Attempt to assign SAME TEACHER to Class 9 on SAME Sunday Period 1 -> MUST CONFLICT
    entry_clash, teacher_conflicts = TimetableService.assign_timetable_slot(
        session=db_session,
        academic_year_id=1,
        class_id=cls_9.id,
        day_of_week="Sunday",
        period_slot_id=period_1.id,
        subject_id=sub_math.id,
        teacher_id=teacher_1.id,
        room_number="Room 302"
    )
    assert entry_clash is None
    assert len(teacher_conflicts) > 0
    assert "Teacher Conflict" in teacher_conflicts[0]

    # 3. Attempt to assign DIFFERENT TEACHER to Class 9 on SAME Sunday Period 1 in SAME Room 301 -> MUST CONFLICT
    teacher_2 = db_session.query(Teacher).filter(Teacher.id != teacher_1.id).first()
    if not teacher_2:
        teacher_2 = Teacher(employee_id="EMP-T-02", name="Nasreen Sultana", gender="Female", date_of_birth="1985-05-10", phone="+880170000002", email="nasreen@school.local", qualification="M.A. English", status="Active")
        db_session.add(teacher_2)
        db_session.commit()

    entry_room_clash, room_conflicts = TimetableService.assign_timetable_slot(
        session=db_session,
        academic_year_id=1,
        class_id=cls_9.id,
        day_of_week="Sunday",
        period_slot_id=period_1.id,
        subject_id=sub_math.id,
        teacher_id=teacher_2.id,
        room_number="Room 301"
    )
    assert entry_room_clash is None
    assert len(room_conflicts) > 0
    assert "Room Conflict" in room_conflicts[0]


def test_timetable_matrix_and_pdf_generation(db_session):
    """Verify matrix query and ReportLab landscape A4 timetable generation."""
    periods = TimetableService.seed_default_periods(db_session)
    cls_10 = db_session.query(SchoolClass).first()

    matrix = TimetableRepository.get_class_timetable_matrix(db_session, cls_10.id)
    assert isinstance(matrix, dict)

    school_info = {
        "school_name": "Test Academy",
        "eiin_number": "123456",
        "address": "Dhaka, Bangladesh"
    }
    period_dicts = [
        {"id": p.id, "name": p.name, "start_time": p.start_time, "end_time": p.end_time, "is_break": p.is_break}
        for p in periods
    ]
    matrix_formatted = {}
    for d, p_dict in matrix.items():
        matrix_formatted[d] = {}
        for pid, entry in p_dict.items():
            matrix_formatted[d][pid] = {
                "subject_name": entry.subject.name if entry.subject else "Subject",
                "teacher_name": entry.teacher.name if entry.teacher else "Teacher",
                "room_number": entry.room_number or "Room"
            }

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        out_path = tmp.name

    try:
        success = ClassTimetablePDFGenerator.generate_timetable(
            class_name="Class 10",
            section_name="Padma",
            shift_name="Morning",
            school_info=school_info,
            periods=period_dicts,
            matrix=matrix_formatted,
            output_path=out_path
        )
        assert success is True
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 1000
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)
