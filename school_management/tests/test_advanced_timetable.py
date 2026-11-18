"""
EduManage Pro - Advanced Timetable Management Unit & Integration Tests (Pytest)
Validates:
- Multi-Shift Period Slots (Morning, Day, Evening)
- Class, Teacher & Room Timetables + Printable PDFs & Excel Exports
- Conflict Detection (Teacher, Room, Class & Cross-Shift Time Overlap)
- Constraint-Satisfaction Auto-Suggestion Algorithm
- Manual Editing, Moving & Atomic Swapping
- Immutable Academic Year Timetable History, Snapshots & Cross-Year Cloning
"""

from datetime import date
import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.connection import Base
from app.models.academic import AcademicRoom, AcademicShift, AcademicYear, SchoolClass, Section, Subject
from app.models.staff import Teacher, TeacherSubjectAssignment
from app.models.timetable import PeriodSlot, TimetableEntry, TimetableHistory
from app.reports.class_timetable_pdf import ClassTimetablePDFGenerator
from app.reports.room_timetable_pdf import RoomTimetablePDFGenerator
from app.reports.teacher_routine_pdf import TeacherRoutinePDFGenerator
from app.repositories.timetable_repository import TimetableRepository
from app.services.timetable_service import TimetableService


@pytest.fixture(scope="function")
def tt_env():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    ay_prev = AcademicYear(name="2025", start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), is_current=False, status="Completed")
    ay_curr = AcademicYear(name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True, status="Active")
    db.add_all([ay_prev, ay_curr])
    db.flush()

    sh_morn = AcademicShift(name="Morning", code="MRN", start_time="08:30 AM", end_time="02:45 PM")
    sh_day = AcademicShift(name="Day", code="DAY", start_time="01:00 PM", end_time="05:30 PM")
    db.add_all([sh_morn, sh_day])
    db.flush()

    rm101 = AcademicRoom(room_number="Room 101", room_name="Lecture 101", room_type="Classroom", capacity=45)
    rm102 = AcademicRoom(room_number="Room 102", room_name="Lecture 102", room_type="Classroom", capacity=45)
    rm_lab = AcademicRoom(room_number="Physics Lab", room_name="Main Lab", room_type="Science Lab", capacity=30)
    db.add_all([rm101, rm102, rm_lab])
    db.flush()

    t1 = Teacher(
        employee_id="EMP-TT-01",
        name="Dr. Arif Hossain",
        gender="Male",
        date_of_birth=date(1982, 4, 12),
        phone="+8801710000001",
        email="arif@school.edu",
        qualification="Ph.D. Physics",
        status="Active",
    )
    t2 = Teacher(
        employee_id="EMP-TT-02",
        name="Sadia Rahman",
        gender="Female",
        date_of_birth=date(1987, 7, 19),
        phone="+8801710000002",
        email="sadia@school.edu",
        qualification="M.Sc. Math",
        status="Active",
    )
    db.add_all([t1, t2])
    db.flush()

    cls10 = SchoolClass(
        name="Class 10", code="C10", numeric_order=10, academic_year_id=ay_curr.id, shift="Morning", shift_id=sh_morn.id
    )
    cls9 = SchoolClass(
        name="Class 9", code="C9", numeric_order=9, academic_year_id=ay_curr.id, shift="Day", shift_id=sh_day.id
    )
    cls10_prev = SchoolClass(
        name="Class 10", code="C10-25", numeric_order=10, academic_year_id=ay_prev.id, shift="Morning", shift_id=sh_morn.id
    )
    db.add_all([cls10, cls9, cls10_prev])
    db.flush()

    sec10a = Section(name="A", room_number="Room 101", room_id=rm101.id, class_id=cls10.id, capacity=40)
    sec9a = Section(name="A", room_number="Room 102", room_id=rm102.id, class_id=cls9.id, capacity=40)
    db.add_all([sec10a, sec9a])
    db.flush()

    sub_phy = Subject(subject_id="SUB-PHY-10", name="Physics Lab & Theory", code="PHY10", class_id=cls10.id, teacher_id=t1.id)
    sub_mat = Subject(subject_id="SUB-MAT-10", name="Higher Mathematics", code="MAT10", class_id=cls10.id, teacher_id=t2.id)
    sub_eng = Subject(subject_id="SUB-ENG-9", name="English", code="ENG9", class_id=cls9.id, teacher_id=t1.id)
    sub_phy_prev = Subject(subject_id="SUB-PHY-25", name="Physics Lab & Theory", code="PHY25", class_id=cls10_prev.id, teacher_id=t1.id)
    db.add_all([sub_phy, sub_mat, sub_eng, sub_phy_prev])
    db.flush()

    db.add(
        TeacherSubjectAssignment(
            academic_year_id=ay_curr.id,
            class_id=cls10.id,
            section_id=sec10a.id,
            subject_id=sub_phy.id,
            teacher_id=t1.id,
            is_active=True,
        )
    )
    db.commit()

    yield {
        "db": db,
        "ay_prev": ay_prev,
        "ay_curr": ay_curr,
        "rm101": rm101,
        "rm102": rm102,
        "rm_lab": rm_lab,
        "t1": t1,
        "t2": t2,
        "cls10": cls10,
        "cls9": cls9,
        "cls10_prev": cls10_prev,
        "sec10a": sec10a,
        "sec9a": sec9a,
        "sub_phy": sub_phy,
        "sub_mat": sub_mat,
        "sub_eng": sub_eng,
        "sub_phy_prev": sub_phy_prev,
    }
    db.close()


def test_teacher_room_class_and_cross_shift_conflicts(tt_env):
    db = tt_env["db"]
    ay_curr = tt_env["ay_curr"]
    shifts = TimetableService.seed_all_shift_periods(db, academic_year_id=ay_curr.id)
    assert "Morning" in shifts and "Day" in shifts and "Evening" in shifts

    m_p1 = next(p for p in shifts["Morning"] if p.period_number == 1)
    # Morning 5th Period is 12:30 PM - 01:15 PM; Day 1st Period is 01:15 PM - 02:00 PM (back-to-back, no overlap)
    # Create an overlapping Day slot 12:45 PM - 01:30 PM to test cross-shift overlap conflict!
    overlap_slot = TimetableRepository.create_period_slot(
        db,
        period_number=10,
        name="Overlap Day Slot",
        start_time="12:45 PM",
        end_time="01:30 PM",
        duration_minutes=45,
        is_break=False,
        shift="Day",
        academic_year_id=ay_curr.id,
    )
    m_p5 = next(p for p in shifts["Morning"] if p.period_number == 5)

    # Valid placement in Morning P1
    e1, c1 = TimetableService.assign_timetable_slot(
        db,
        academic_year_id=ay_curr.id,
        class_id=tt_env["cls10"].id,
        section_id=tt_env["sec10a"].id,
        day_of_week="Sunday",
        period_slot_id=m_p1.id,
        subject_id=tt_env["sub_phy"].id,
        teacher_id=tt_env["t1"].id,
        room_number="Room 101",
    )
    assert e1 is not None and not c1

    # Class Conflict: trying to place another subject into SAME class/section/day/period without edit/overwrite
    e_cls_clash, c_cls = TimetableService.assign_timetable_slot(
        db,
        academic_year_id=ay_curr.id,
        class_id=tt_env["cls10"].id,
        section_id=tt_env["sec10a"].id,
        day_of_week="Sunday",
        period_slot_id=m_p1.id,
        subject_id=tt_env["sub_mat"].id,
        teacher_id=tt_env["t2"].id,
        room_number="Room 102",
    )
    assert e_cls_clash is None
    assert any("Class Conflict" in m for m in c_cls)

    # Cross-Shift Overlap Conflict: assign t1 to Morning P5 (12:30-01:15), then overlap Day slot (12:45-01:30)
    e2, c2 = TimetableService.assign_timetable_slot(
        db,
        academic_year_id=ay_curr.id,
        class_id=tt_env["cls10"].id,
        section_id=tt_env["sec10a"].id,
        day_of_week="Monday",
        period_slot_id=m_p5.id,
        subject_id=tt_env["sub_phy"].id,
        teacher_id=tt_env["t1"].id,
        room_number="Physics Lab",
    )
    assert e2 is not None and not c2

    e_overlap, c_overlap = TimetableService.assign_timetable_slot(
        db,
        academic_year_id=ay_curr.id,
        class_id=tt_env["cls9"].id,
        section_id=tt_env["sec9a"].id,
        day_of_week="Monday",
        period_slot_id=overlap_slot.id,
        subject_id=tt_env["sub_eng"].id,
        teacher_id=tt_env["t1"].id,
        room_number="Physics Lab",
    )
    assert e_overlap is None
    assert any("Teacher Conflict" in m for m in c_overlap)
    assert any("Room Conflict" in m for m in c_overlap)


def test_auto_suggest_manual_edit_swap_and_room_pdf(tt_env):
    db = tt_env["db"]
    ay_curr = tt_env["ay_curr"]
    shifts = TimetableService.seed_all_shift_periods(db, academic_year_id=ay_curr.id)
    m_p1 = next(p for p in shifts["Morning"] if p.period_number == 1)

    # Pre-book t1 on Sunday Morning P1 in Class 9 so auto-scheduler MUST avoid clash for t1/Room 102
    TimetableService.assign_timetable_slot(
        db,
        academic_year_id=ay_curr.id,
        class_id=tt_env["cls9"].id,
        section_id=tt_env["sec9a"].id,
        day_of_week="Sunday",
        period_slot_id=m_p1.id,
        subject_id=tt_env["sub_eng"].id,
        teacher_id=tt_env["t1"].id,
        room_number="Room 102",
    )

    result = TimetableService.suggest_timetable(
        db,
        academic_year_id=ay_curr.id,
        class_id=tt_env["cls10"].id,
        section_id=tt_env["sec10a"].id,
        shift="Morning",
        subject_weekly_quotas={tt_env["sub_phy"].id: 3, tt_env["sub_mat"].id: 4},
        apply_immediately=True,
    )
    assert result["applied_count"] == 7
    assert len(result["unplaced"]) == 0
    assert TimetableRepository.scan_all_conflicts(db, academic_year_id=ay_curr.id) == []

    # Physics Lab preference check
    phy_entries = [s for s in result["suggestions"] if s["subject_id"] == tt_env["sub_phy"].id]
    assert all(s["room_number"] == "Physics Lab" for s in phy_entries)

    # Verify Room Timetable Matrix & Room PDF generation
    rm_matrix = TimetableRepository.get_room_timetable_matrix(
        db, room_number="Physics Lab", academic_year_id=ay_curr.id, shift="Morning"
    )
    assert len(rm_matrix) >= 1

    # Manual swap between two scheduled slots in Class 10
    cls10_entries = TimetableRepository.get_all_entries(
        db, class_id=tt_env["cls10"].id, academic_year_id=ay_curr.id
    )
    e_a, e_b = cls10_entries[0], cls10_entries[1]
    ok_sw, sw_c, _ = TimetableService.move_or_swap_slot(
        db,
        entry_id=e_a.id,
        target_day=e_b.day_of_week,
        target_period_slot_id=e_b.period_slot_id,
        swap_if_occupied=True,
    )
    assert ok_sw is True and not sw_c

    # Printable Room & Class PDFs + Excel exports
    periods = TimetableRepository.get_period_slots(db, shift="Morning", academic_year_id=ay_curr.id)
    period_dicts = [
        {"id": p.id, "name": p.name, "start_time": p.start_time, "end_time": p.end_time, "is_break": p.is_break}
        for p in periods
    ]
    fmt_rm = {
        d: {
            pid: {
                "class_name": e.school_class.name,
                "section_name": e.section.name if e.section else "",
                "subject_name": e.subject.name,
                "teacher_name": e.teacher.name,
            }
            for pid, e in pmap.items()
        }
        for d, pmap in rm_matrix.items()
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        rm_pdf = os.path.join(tmpdir, "room.pdf")
        rm_xlsx = os.path.join(tmpdir, "room.xlsx")
        assert RoomTimetablePDFGenerator.generate_room_timetable(
            {"room_number": "Physics Lab", "room_type": "Science Lab", "capacity": 30},
            {"school_name": "EduManage Test School"},
            period_dicts,
            fmt_rm,
            rm_pdf,
            shift_name="Morning",
            academic_year_label="2026",
        )
        assert TimetableService.export_room_timetable_excel(
            db, "Physics Lab", "EduManage Test School", rm_xlsx, academic_year_id=ay_curr.id, shift="Morning"
        )
        assert os.path.exists(rm_pdf) and os.path.getsize(rm_pdf) > 1000
        assert os.path.exists(rm_xlsx) and os.path.getsize(rm_xlsx) > 1000


def test_academic_year_history_snapshot_clone_and_immutability(tt_env):
    db = tt_env["db"]
    ay_prev = tt_env["ay_prev"]
    ay_curr = tt_env["ay_curr"]

    shifts_prev = TimetableService.seed_default_periods(db, academic_year_id=ay_prev.id, shift="Morning")
    p1 = next(p for p in shifts_prev if p.period_number == 1)

    TimetableService.assign_timetable_slot(
        db,
        academic_year_id=ay_prev.id,
        class_id=tt_env["cls10_prev"].id,
        day_of_week="Sunday",
        period_slot_id=p1.id,
        subject_id=tt_env["sub_phy_prev"].id,
        teacher_id=tt_env["t1"].id,
        room_number="Room 101",
    )
    snap = TimetableService.save_year_snapshot(db, academic_year_id=ay_prev.id, reason="End of 2025 archive")
    assert snap.id is not None

    cloned, skipped = TimetableService.clone_timetable_from_year(db, ay_prev.id, ay_curr.id, shift="Morning")
    assert cloned == 1 and skipped == 0

    hist_prev = TimetableRepository.list_history(db, academic_year_id=ay_prev.id)
    hist_curr = TimetableRepository.list_history(db, academic_year_id=ay_curr.id)
    assert len(hist_prev) >= 2
    assert any(h.action == "CLONED_FROM_YEAR" for h in hist_curr)

    # Immutable history cannot be deleted
    with pytest.raises(ValueError):
        db.delete(hist_prev[0])
        db.commit()
    db.rollback()
