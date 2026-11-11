"""
EduManage Pro - Notice & Event Calendar Unit Tests
Phase 13: Circulars, Priority Pinning, Event Scheduling, Holiday Detection & PDF Letterheads
"""

import os
import tempfile
from datetime import date, timedelta
import pytest
from app.models.notice import SchoolNotice, SchoolEvent
from app.repositories.notice_repository import NoticeRepository
from app.services.notice_service import NoticeService
from app.reports.notice_pdf import NoticeLetterheadGenerator
from app.reports.academic_calendar_pdf import AcademicCalendarPDFGenerator


def test_seed_notices_and_events(db_session):
    """Verify default administrative circulars and calendar events seed cleanly."""
    res = NoticeService.seed_default_notices_and_events(db_session)
    assert res["notices_seeded"] >= 4 or db_session.query(SchoolNotice).count() >= 4
    assert res["events_seeded"] >= 4 or db_session.query(SchoolEvent).count() >= 4

    urgent_notice = db_session.query(SchoolNotice).filter(SchoolNotice.priority == "Urgent").first()
    assert urgent_notice is not None
    assert urgent_notice.is_pinned is True


def test_notice_crud_and_priority_pinning(db_session):
    """Verify circular creation, priority auto-pinning, and status updates."""
    n = NoticeRepository.create_notice(
        session=db_session,
        title="Emergency Closure Due to Heavy Rainfall",
        content="All classes are suspended tomorrow as per city warning.",
        category="Emergency",
        target_audience="All",
        priority="Urgent",
        is_pinned=True,
        created_by="Principal Office"
    )
    assert n.id is not None
    assert n.reference_no.startswith("CIR-")
    assert n.is_pinned is True

    # Pinned notice must appear first
    all_notices = NoticeRepository.get_all_notices(db_session)
    assert all_notices[0].id == n.id or all_notices[0].is_pinned is True

    # Update
    updated = NoticeRepository.update_notice(db_session, n.id, priority="Normal", is_pinned=False)
    assert updated.priority == "Normal"
    assert updated.is_pinned is False


def test_notice_target_audience_filtering(db_session):
    """Verify audience segregation (Teachers only, Students only, All)."""
    NoticeRepository.create_notice(
        db_session,
        title="Teacher Meeting",
        content="Faculty council meet in room 204.",
        target_audience="Teachers"
    )
    NoticeRepository.create_notice(
        db_session,
        title="Student Assembly",
        content="All students in auditorium.",
        target_audience="Students"
    )

    teacher_notices = NoticeRepository.get_all_notices(db_session, audience="Teachers")
    assert all(n.target_audience in ["Teachers", "All"] for n in teacher_notices)

    student_notices = NoticeRepository.get_all_notices(db_session, audience="Students")
    assert all(n.target_audience in ["Students", "All"] for n in student_notices)


def test_event_scheduling_and_holiday_detection(db_session):
    """Verify event scheduling and automatic holiday detection on given date."""
    today = date.today()
    hol_date = today + timedelta(days=5)

    ev = NoticeRepository.create_event(
        session=db_session,
        event_title="Victory Day Holiday",
        start_date=hol_date,
        end_date=hol_date,
        event_category="Holiday",
        is_holiday=True
    )
    assert ev.id is not None
    assert ev.is_holiday is True

    # Verify holiday query
    assert NoticeRepository.is_date_holiday(db_session, hol_date) is True
    assert NoticeRepository.is_date_holiday(db_session, hol_date + timedelta(days=10)) is False


def test_openpyxl_export_and_reportlab_notice_letterhead(db_session):
    """Verify openpyxl calendar export and ReportLab official memo letterhead generation."""
    NoticeService.seed_default_notices_and_events(db_session)
    notice = NoticeRepository.get_all_notices(db_session)[0]
    events = NoticeRepository.get_all_events(db_session)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Calendar Excel
        xlsx_path = os.path.join(tmpdir, "academic_calendar.xlsx")
        NoticeService.export_events_excel(db_session, xlsx_path)
        assert os.path.exists(xlsx_path)
        assert os.path.getsize(xlsx_path) > 1000

        # 2. Notice Memo PDF
        from app.models.school import SchoolSetting
        school = db_session.query(SchoolSetting).first()
        memo_pdf = os.path.join(tmpdir, "circular_letterhead.pdf")
        NoticeLetterheadGenerator.generate_notice_pdf(notice, school, memo_pdf)
        assert os.path.exists(memo_pdf)
        assert os.path.getsize(memo_pdf) > 1000

        # 3. Calendar Planner PDF
        cal_pdf = os.path.join(tmpdir, "academic_calendar.pdf")
        AcademicCalendarPDFGenerator.generate_calendar_pdf(events, school, cal_pdf)
        assert os.path.exists(cal_pdf)
        assert os.path.getsize(cal_pdf) > 1000
