"""
EduManage Pro - Timetable & Routine Service
Phase 9: Seeder, Scheduling Business Rules, Collision Resolution & openpyxl Exporters
"""

import os
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session
from app.models.timetable import PeriodSlot, TimetableEntry
from app.repositories.timetable_repository import TimetableRepository

STANDARD_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]

DEFAULT_PERIOD_DEFINITIONS = [
    {"period_number": 0, "name": "Assembly & Homeroom", "start_time": "08:30 AM", "end_time": "08:45 AM", "duration_minutes": 15, "is_break": True},
    {"period_number": 1, "name": "1st Period", "start_time": "08:45 AM", "end_time": "09:30 AM", "duration_minutes": 45, "is_break": False},
    {"period_number": 2, "name": "2nd Period", "start_time": "09:30 AM", "end_time": "10:15 AM", "duration_minutes": 45, "is_break": False},
    {"period_number": 3, "name": "3rd Period", "start_time": "10:15 AM", "end_time": "11:00 AM", "duration_minutes": 45, "is_break": False},
    {"period_number": 4, "name": "4th Period", "start_time": "11:00 AM", "end_time": "11:45 AM", "duration_minutes": 45, "is_break": False},
    {"period_number": 99, "name": "Tiffin & Refreshment", "start_time": "11:45 AM", "end_time": "12:30 PM", "duration_minutes": 45, "is_break": True},
    {"period_number": 5, "name": "5th Period", "start_time": "12:30 PM", "end_time": "01:15 PM", "duration_minutes": 45, "is_break": False},
    {"period_number": 6, "name": "6th Period", "start_time": "01:15 PM", "end_time": "02:00 PM", "duration_minutes": 45, "is_break": False},
    {"period_number": 7, "name": "7th Period", "start_time": "02:00 PM", "end_time": "02:45 PM", "duration_minutes": 45, "is_break": False},
]


class TimetableService:
    """Service layer managing periods, routine validation, collision checks, and excel output."""

    @staticmethod
    def seed_default_periods(session: Session, academic_year_id: Optional[int] = 1) -> List[PeriodSlot]:
        """Seeds default period schedule if table is empty."""
        existing = TimetableRepository.get_period_slots(session)
        if existing:
            return existing

        created = []
        for defn in DEFAULT_PERIOD_DEFINITIONS:
            slot = TimetableRepository.create_period_slot(
                session,
                period_number=defn["period_number"],
                name=defn["name"],
                start_time=defn["start_time"],
                end_time=defn["end_time"],
                duration_minutes=defn["duration_minutes"],
                is_break=defn["is_break"],
                shift="Morning",
                academic_year_id=academic_year_id
            )
            created.append(slot)
        return created

    @staticmethod
    def assign_timetable_slot(
        session: Session,
        academic_year_id: int,
        class_id: int,
        day_of_week: str,
        period_slot_id: int,
        subject_id: int,
        teacher_id: int,
        room_number: str,
        section_id: Optional[int] = None,
        notes: Optional[str] = None,
        entry_id: Optional[int] = None
    ) -> Tuple[Optional[TimetableEntry], List[str]]:
        """
        Validates constraints and checks for room/teacher double-booking clashes.
        Returns: (TimetableEntry, conflicts_list).
        If conflicts exist, returns (None, conflicts).
        """
        conflicts = TimetableRepository.check_conflicts(
            session=session,
            day_of_week=day_of_week,
            period_slot_id=period_slot_id,
            teacher_id=teacher_id,
            room_number=room_number,
            exclude_entry_id=entry_id
        )

        if conflicts:
            return None, conflicts

        # If editing existing
        if entry_id:
            entry = TimetableRepository.update_timetable_entry(
                session,
                entry_id=entry_id,
                academic_year_id=academic_year_id,
                class_id=class_id,
                section_id=section_id,
                day_of_week=day_of_week,
                period_slot_id=period_slot_id,
                subject_id=subject_id,
                teacher_id=teacher_id,
                room_number=room_number,
                notes=notes
            )
            return entry, []

        # If new slot, check if this class already has an assignment for this day+period
        existing_class_slot = session.query(TimetableEntry).filter(
            TimetableEntry.class_id == class_id,
            TimetableEntry.section_id == section_id,
            TimetableEntry.day_of_week == day_of_week,
            TimetableEntry.period_slot_id == period_slot_id
        ).first()

        if existing_class_slot:
            # Update existing slot
            entry = TimetableRepository.update_timetable_entry(
                session,
                entry_id=existing_class_slot.id,
                subject_id=subject_id,
                teacher_id=teacher_id,
                room_number=room_number,
                notes=notes
            )
            return entry, []

        # Create fresh slot
        entry = TimetableRepository.create_timetable_entry(
            session,
            academic_year_id=academic_year_id,
            class_id=class_id,
            section_id=section_id,
            day_of_week=day_of_week,
            period_slot_id=period_slot_id,
            subject_id=subject_id,
            teacher_id=teacher_id,
            room_number=room_number,
            notes=notes
        )
        return entry, []

    @staticmethod
    def export_class_timetable_excel(
        session: Session,
        class_id: int,
        class_name: str,
        section_name: str,
        school_name: str,
        output_path: str
    ) -> bool:
        """Exports class weekly timetable grid into a professional openpyxl Excel spreadsheet."""
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Class Timetable"

            # Colors
            header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            period_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
            break_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
            slot_fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")

            thin_border = Border(
                left=Side(style='thin', color='CBD5E1'),
                right=Side(style='thin', color='CBD5E1'),
                top=Side(style='thin', color='CBD5E1'),
                bottom=Side(style='thin', color='CBD5E1')
            )

            # Title
            ws.merge_cells("A1:H1")
            ws["A1"] = school_name.upper()
            ws["A1"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
            ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
            ws["A1"].fill = header_fill

            ws.merge_cells("A2:H2")
            ws["A2"] = f"WEEKLY CLASS TIMETABLE — {class_name.upper()} (SECTION: {section_name.upper()})"
            ws["A2"].font = Font(name="Arial", size=11, bold=True, color="1E3A8A")
            ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

            # Periods
            periods = TimetableRepository.get_period_slots(session)
            teaching_periods = [p for p in periods if not p.is_break or "Tiffin" in p.name]

            # Header Row 4: Day / Period
            ws.cell(row=4, column=1, value="Day \\ Period").font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
            ws.cell(row=4, column=1).fill = period_fill
            ws.cell(row=4, column=1).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=4, column=1).border = thin_border

            for col_idx, p in enumerate(teaching_periods, start=2):
                cell = ws.cell(row=4, column=col_idx)
                cell.value = f"{p.name}\n({p.start_time} - {p.end_time})"
                cell.font = Font(name="Arial", size=9, bold=True, color="FFFFFF")
                cell.fill = period_fill if not p.is_break else PatternFill(start_color="F59E0B", end_color="F59E0B", fill_type="solid")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = thin_border

            ws.row_dimensions[4].height = 32

            # Matrix Fill
            matrix = TimetableRepository.get_class_timetable_matrix(session, class_id)
            current_row = 5

            for day in STANDARD_DAYS:
                day_cell = ws.cell(row=current_row, column=1, value=day)
                day_cell.font = Font(name="Arial", size=10, bold=True, color="0F172A")
                day_cell.alignment = Alignment(horizontal="center", vertical="center")
                day_cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
                day_cell.border = thin_border

                for col_idx, p in enumerate(teaching_periods, start=2):
                    cell = ws.cell(row=current_row, column=col_idx)
                    cell.border = thin_border

                    if p.is_break:
                        cell.value = "TIFFIN BREAK"
                        cell.fill = break_fill
                        cell.font = Font(name="Arial", size=9, bold=True, color="94A3B8")
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    else:
                        entry = matrix.get(day, {}).get(p.id)
                        if entry:
                            sub_name = entry.subject.name if entry.subject else "Subject"
                            t_name = entry.teacher.name if entry.teacher else ""
                            room = entry.room_number or ""
                            cell.value = f"{sub_name}\n{t_name} | {room}"
                            cell.fill = slot_fill
                            cell.font = Font(name="Arial", size=9, bold=False, color="1E293B")
                            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                        else:
                            cell.value = "—"
                            cell.alignment = Alignment(horizontal="center", vertical="center")
                            cell.font = Font(name="Arial", size=9, color="CBD5E1")

                ws.row_dimensions[current_row].height = 36
                current_row += 1

            # Auto fit widths
            ws.column_dimensions["A"].width = 16
            for col_idx in range(2, len(teaching_periods) + 2):
                ws.column_dimensions[get_column_letter(col_idx)].width = 20

            wb.save(output_path)
            return True
        except Exception as e:
            print(f"[TimetableService] Error exporting Excel: {e}")
            return False
