"""
EduManage Pro - Attendance Service Layer
Business logic, automated batch marking (Mark All Present/Absent), validations, and Excel export via openpyxl.
"""

from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.repositories.attendance_repository import AttendanceRepository
from app.models.activity import ActivityLog
from app.models.academic import SchoolClass, Section
from app.services.database_service import DatabaseService
from app.config.logging_config import app_logger
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


class AttendanceService:
    @staticmethod
    def mark_student_attendance(
        db: Session,
        class_id: int,
        section_id: Optional[int],
        att_date: date,
        records: List[Dict[str, Any]],
        current_user: str = "admin"
    ) -> Tuple[bool, str]:
        if att_date > date.today():
            return False, "Cannot record attendance for future dates."

        saved_count = AttendanceRepository.save_bulk_student_attendance(db, records, marked_by=current_user)

        # Count summary for audit log
        present_count = sum(1 for r in records if r.get("status") == "Present")
        absent_count = sum(1 for r in records if r.get("status") == "Absent")
        cls_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        cls_name = cls_obj.name if cls_obj else f"Class {class_id}"

        log = ActivityLog(
            user_id=DatabaseService.resolve_user_id(db, current_user),
            username=current_user,
            action="ATTENDANCE_MARKED",
            module="ATTENDANCE",
            description=f"Recorded daily attendance for {cls_name} on {att_date.isoformat()} ({present_count} Present, {absent_count} Absent)",
            severity="INFO"
        )
        db.add(log)
        db.commit()

        app_logger.info(f"Attendance recorded for {cls_name} ({saved_count} records) by {current_user}")
        return True, f"Successfully recorded attendance for {saved_count} students."

    @staticmethod
    def mark_teacher_attendance(
        db: Session,
        att_date: date,
        records: List[Dict[str, Any]],
        current_user: str = "admin"
    ) -> Tuple[bool, str]:
        if att_date > date.today():
            return False, "Cannot record faculty attendance for future dates."

        saved_count = AttendanceRepository.save_bulk_teacher_attendance(db, records, marked_by=current_user)

        present_count = sum(1 for r in records if r.get("status") == "Present")
        absent_count = sum(1 for r in records if r.get("status") == "Absent")

        log = ActivityLog(
            user_id=DatabaseService.resolve_user_id(db, current_user),
            username=current_user,
            action="TEACHER_ATTENDANCE_MARKED",
            module="ATTENDANCE",
            description=f"Recorded faculty attendance on {att_date.isoformat()} ({present_count} Present, {absent_count} Absent)",
            severity="INFO"
        )
        db.add(log)
        db.commit()

        app_logger.info(f"Faculty attendance saved ({saved_count} staff) by {current_user}")
        return True, f"Successfully recorded attendance for {saved_count} faculty members."

    @staticmethod
    def export_monthly_register_excel(
        db: Session,
        class_id: int,
        year: int,
        month: int,
        output_file_path: str,
        section_id: Optional[int] = None
    ) -> str:
        """
        Exports monthly class attendance register as a stylized Excel workbook (.xlsx).
        """
        data = AttendanceRepository.get_monthly_student_register(db, class_id, year, month, section_id)
        days_count = data["days_count"]
        register = data["register"]

        cls_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        class_name = cls_obj.name if cls_obj else f"Class {class_id}"

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Attendance_{month}_{year}"

        # Title Styling
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=days_count + 6)
        title_cell = ws.cell(row=1, column=1)
        title_cell.value = f"MONTHLY ATTENDANCE REGISTER — {class_name.upper()} ({month:02d}/{year})"
        title_cell.font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 30

        # Header Row
        headers = ["Roll", "Student ID", "Student Name"] + [str(d) for d in range(1, days_count + 1)] + ["P", "A", "L", "%"]
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")

        for col_idx, h_text in enumerate(headers, 1):
            cell = ws.cell(row=2, column=col_idx, value=h_text)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        ws.row_dimensions[2].height = 24

        # Fills for statuses
        green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid") # P
        red_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")   # A
        yellow_fill = PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid") # L
        blue_fill = PatternFill(start_color="E0E7FF", end_color="E0E7FF", fill_type="solid")  # Leave

        thin_border = Border(
            left=Side(style="thin", color="D1D5DB"),
            right=Side(style="thin", color="D1D5DB"),
            top=Side(style="thin", color="D1D5DB"),
            bottom=Side(style="thin", color="D1D5DB")
        )

        for row_idx, item in enumerate(register, 3):
            stu = item["student"]
            ws.cell(row=row_idx, column=1, value=stu.roll_number).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=2, value=stu.student_id).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=3, value=stu.full_name).alignment = Alignment(horizontal="left")

            for day in range(1, days_count + 1):
                st = item["days"].get(day, "-")
                short_code = "P" if st == "Present" else "A" if st == "Absent" else "L" if st == "Late" else "Lv" if st == "Leave" else "-"
                c = ws.cell(row=row_idx, column=3 + day, value=short_code)
                c.alignment = Alignment(horizontal="center")
                c.border = thin_border
                if short_code == "P":
                    c.fill = green_fill
                elif short_code == "A":
                    c.fill = red_fill
                elif short_code == "L":
                    c.fill = yellow_fill
                elif short_code == "Lv":
                    c.fill = blue_fill

            # Totals
            col_p = 3 + days_count + 1
            ws.cell(row=row_idx, column=col_p, value=item["present_count"]).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=col_p + 1, value=item["absent_count"]).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=col_p + 2, value=item["late_count"] + item["leave_count"]).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=col_p + 3, value=f"{item['percentage']}%").alignment = Alignment(horizontal="center")

        # Column widths
        ws.column_dimensions["A"].width = 8
        ws.column_dimensions["B"].width = 16
        ws.column_dimensions["C"].width = 24
        for d in range(1, days_count + 1):
            col_letter = openpyxl.utils.get_column_letter(3 + d)
            ws.column_dimensions[col_letter].width = 4.5

        wb.save(output_file_path)
        return output_file_path
