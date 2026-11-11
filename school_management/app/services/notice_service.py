"""
EduManage Pro - Notice & Event Calendar Service
Phase 13: Data Seeder & openpyxl Calendar Excel Exporter
"""

import os
from typing import Dict, Any, List
from datetime import date, timedelta
from sqlalchemy.orm import Session
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from app.models.notice import SchoolNotice, SchoolEvent
from app.repositories.notice_repository import NoticeRepository


class NoticeService:
    """Service layer for default circular/event seeding and spreadsheet generation."""

    @staticmethod
    def seed_default_notices_and_events(session: Session) -> Dict[str, Any]:
        """Seeds standard administrative circulars, holiday calendars, and academic events."""
        notices_seeded = 0
        events_seeded = 0

        # Check if already seeded
        if session.query(SchoolNotice).count() > 0 and session.query(SchoolEvent).count() > 0:
            return {
                "message": "Notices and events already seeded.",
                "notices_seeded": session.query(SchoolNotice).count(),
                "events_seeded": session.query(SchoolEvent).count()
            }

        today = date.today()

        # 1. Circulars & Bulletins
        n1 = NoticeRepository.create_notice(
            session=session,
            title="Commencement of Academic Session 2026 & Orientation Protocol",
            content=(
                "We are delighted to welcome all students, faculty, and guardians to Academic Session 2026.\n"
                "1. Regular classes for Classes 1 to 10 will begin promptly at 08:00 AM.\n"
                "2. Standard school uniform and student ID cards are mandatory for campus entry.\n"
                "3. School transport routes and bus passes will be activated from Monday.\n"
                "We look forward to an inspiring year of academic and personal growth."
            ),
            category="Academic",
            target_audience="All",
            priority="Important",
            is_pinned=True,
            publish_date=today - timedelta(days=20),
            expiry_date=today + timedelta(days=90),
            attachment_name="Orientation_Guide_2026.pdf",
            created_by="Principal Office"
        )
        notices_seeded += 1

        n2 = NoticeRepository.create_notice(
            session=session,
            title="URGENT: Half-Yearly Examination Routine & Admit Card Distribution",
            content=(
                "All Class Teachers and Subject Instructors are requested to submit final question papers by March 15.\n"
                "Admit Cards with candidate examination roll numbers and seating allocations will be released on March 20.\n"
                "Students with outstanding tuition fees are advised to clear accounts prior to admit card issuance."
            ),
            category="Exam",
            target_audience="Students",
            priority="Urgent",
            is_pinned=True,
            publish_date=today - timedelta(days=5),
            expiry_date=today + timedelta(days=25),
            attachment_name="Half_Yearly_Routine_2026.pdf",
            created_by="Exam Controller Board"
        )
        notices_seeded += 1

        n3 = NoticeRepository.create_notice(
            session=session,
            title="Annual Inter-House Sports & Athletic Championship 2026",
            content=(
                "The Annual Athletics Meet will be hosted at the main playground.\n"
                "House captains (Sher-e-Bangla, Fazlul Huq, Nazrul, and Begum Rokeya) must submit athlete rosters\n"
                "for track and field events (100m sprint, relay, long jump, badminton) to the Sports Coordinator."
            ),
            category="Sports",
            target_audience="Students",
            priority="Normal",
            is_pinned=False,
            publish_date=today - timedelta(days=8),
            expiry_date=today + timedelta(days=30),
            attachment_name="Sports_Schedule.pdf",
            created_by="Physical Education Dept"
        )
        notices_seeded += 1

        n4 = NoticeRepository.create_notice(
            session=session,
            title="Faculty Development Seminar on AI in K-12 STEM Curriculum",
            content=(
                "A mandatory professional development seminar for all Senior Science and Mathematics teachers.\n"
                "Keynote address by Dr. Kazi M. Rahman on integrating practical coding and robotics labs.\n"
                "Attendance will be recorded in the biometric staff register."
            ),
            category="Administrative",
            target_audience="Teachers",
            priority="Important",
            is_pinned=False,
            publish_date=today - timedelta(days=3),
            expiry_date=today + timedelta(days=15),
            created_by="Academic Vice Principal"
        )
        notices_seeded += 1

        n5 = NoticeRepository.create_notice(
            session=session,
            title="School Closure Notice on Account of National Mourning & Public Holiday",
            content=(
                "In observance of the official National Holiday, all academic lectures, library services, and\n"
                "administrative offices will remain closed. Regular classes resume the following working day."
            ),
            category="Holiday",
            target_audience="All",
            priority="Normal",
            is_pinned=False,
            publish_date=today - timedelta(days=12),
            expiry_date=today + timedelta(days=10),
            created_by="General Administration"
        )
        notices_seeded += 1

        # 2. Calendar Events & Holidays
        NoticeRepository.create_event(
            session=session,
            event_title="Independence Day & National Cultural Exhibition",
            start_date=date(today.year, 3, 26),
            end_date=date(today.year, 3, 26),
            event_category="Holiday",
            start_time="08:30 AM",
            end_time="01:00 PM",
            venue="Campus Main Grounds",
            target_audience="All",
            is_holiday=True,
            color_code="#DC2626",
            description="Flag hoisting ceremony followed by patriotic songs and student drama exhibition.",
            organizer="Cultural Affairs Committee"
        )
        events_seeded += 1

        NoticeRepository.create_event(
            session=session,
            event_title="Half-Yearly Examination Period (All Classes)",
            start_date=date(today.year, 4, 15),
            end_date=date(today.year, 4, 28),
            event_category="Exam",
            start_time="09:00 AM",
            end_time="12:00 PM",
            venue="Exam Halls A, B & C",
            target_audience="Students",
            is_holiday=False,
            color_code="#D97706",
            description="Official term examinations covering first semester syllabus for Class 1 to 10.",
            organizer="Examination Board"
        )
        events_seeded += 1

        NoticeRepository.create_event(
            session=session,
            event_title="Annual Science & Robotics Tech Fair 2026",
            start_date=date(today.year, 5, 10),
            end_date=date(today.year, 5, 11),
            event_category="Academic",
            start_time="10:00 AM",
            end_time="04:30 PM",
            venue="Science Building Quadrangle",
            target_audience="All",
            is_holiday=False,
            color_code="#059669",
            description="Inter-school science competition with 40+ innovative student project displays.",
            organizer="Young Scientists Club"
        )
        events_seeded += 1

        NoticeRepository.create_event(
            session=session,
            event_title="Eid-ul-Fitr Vacation (Institutional Recess)",
            start_date=date(today.year, 3, 30),
            end_date=date(today.year, 4, 6),
            event_category="Holiday",
            start_time="Full Day",
            end_time="Full Day",
            venue="School-wide",
            target_audience="All",
            is_holiday=True,
            color_code="#DC2626",
            description="Annual religious festival recess. Hostel boarders may apply for home visit outpasses.",
            organizer="School Administration"
        )
        events_seeded += 1

        NoticeRepository.create_event(
            session=session,
            event_title="Parent-Teacher Conference & Progress Report Meeting (PTM)",
            start_date=date(today.year, 5, 20),
            end_date=date(today.year, 5, 20),
            event_category="PTM",
            start_time="09:00 AM",
            end_time="02:00 PM",
            venue="Respective Classrooms",
            target_audience="Parents",
            is_holiday=False,
            color_code="#7C3AED",
            description="One-on-one progress review between guardians and Class Teachers regarding student GPA.",
            organizer="Academic Council"
        )
        events_seeded += 1

        NoticeRepository.create_event(
            session=session,
            event_title="Inter-School Football Championship Finals",
            start_date=date(today.year, 6, 5),
            end_date=date(today.year, 6, 5),
            event_category="Sports",
            start_time="03:00 PM",
            end_time="06:00 PM",
            venue="Outer Football Stadium",
            target_audience="All",
            is_holiday=False,
            color_code="#2563EB",
            description="Final championship match between Ideal Model High School and St. Joseph College.",
            organizer="Sports Committee"
        )
        events_seeded += 1

        return {
            "message": "Notices and Events seeded successfully.",
            "notices_seeded": notices_seeded,
            "events_seeded": events_seeded
        }

    @staticmethod
    def export_events_excel(session: Session, file_path: str) -> str:
        """Exports annual academic calendar, events, and holidays to an openpyxl Excel spreadsheet."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Academic Calendar & Events"

        # Styles
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        holiday_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
        sub_font = Font(name="Calibri", size=10, italic=True, color="475569")
        data_font = Font(name="Calibri", size=10)
        border_thin = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        # Title Block
        ws.merge_cells("A1:H1")
        ws["A1"] = "EduManage Pro - Annual Academic Calendar & Holiday Planner"
        ws["A1"].font = title_font
        ws["A1"].alignment = Alignment(horizontal="left", vertical="center")

        ws.merge_cells("A2:H2")
        ws["A2"] = f"Generated on: {date.today().strftime('%B %d, %Y')} | Official Institutional Schedule"
        ws["A2"].font = sub_font
        ws["A2"].alignment = Alignment(horizontal="left", vertical="center")

        ws.append([])  # Blank row 3

        # Headers
        headers = [
            "SL",
            "Event Title",
            "Category",
            "Start Date",
            "End Date",
            "Timing",
            "Venue / Location",
            "Target Audience",
            "Holiday?",
            "Organizer"
        ]
        ws.append(headers)
        row_num = 4
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=row_num, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        events = NoticeRepository.get_all_events(session)
        for idx, ev in enumerate(events, 1):
            row_num += 1
            start_str = ev.start_date.strftime("%Y-%m-%d")
            end_str = ev.end_date.strftime("%Y-%m-%d")
            time_str = f"{ev.start_time or ''} - {ev.end_time or ''}".strip(" -") or "All Day"
            is_hol_str = "YES (Holiday)" if ev.is_holiday else "No"

            row_data = [
                idx,
                ev.event_title,
                ev.event_category,
                start_str,
                end_str,
                time_str,
                ev.venue,
                ev.target_audience,
                is_hol_str,
                ev.organizer
            ]
            ws.append(row_data)

            for col_idx in range(1, len(row_data) + 1):
                cell = ws.cell(row=row_num, column=col_idx)
                cell.font = data_font
                cell.border = border_thin
                if ev.is_holiday:
                    cell.fill = holiday_fill
                if col_idx in [1, 3, 4, 5, 8, 9]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                val = str(cell.value or "")
                if len(val) > max_len and cell.row > 2:
                    max_len = len(val)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 11)

        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        wb.save(file_path)
        return file_path
