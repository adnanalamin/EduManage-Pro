"""
EduManage Pro - Teacher & Staff Service
Business logic, unique ID generators, payroll calculations, Excel export, and audit logs.
"""

from datetime import date
from typing import Dict, Any, Tuple, Optional, List
from sqlalchemy.orm import Session
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from app.repositories.staff_repository import StaffRepository
from app.models.staff import Teacher, Staff, Department
from app.models.activity import ActivityLog
from app.config.logging_config import app_logger, error_logger


class StaffService:
    @staticmethod
    def generate_teacher_ids(db: Session) -> Tuple[str, str]:
        year = date.today().year
        count = db.query(Teacher).count() + 1
        return f"TCH-{year}-{count:04d}", f"EMP-{year}-{1000 + count}"

    @staticmethod
    def generate_staff_ids(db: Session) -> Tuple[str, str]:
        year = date.today().year
        count = db.query(Staff).count() + 1
        return f"STF-{year}-{count:04d}", f"EMP-{year}-{2000 + count}"

    @staticmethod
    def add_teacher(
        db: Session,
        payload: Dict[str, Any],
        current_username: str = "admin"
    ) -> Tuple[bool, Optional[Teacher], str]:
        try:
            if not payload.get("teacher_id") or not payload.get("employee_id"):
                tch_id, emp_id = StaffService.generate_teacher_ids(db)
                payload["teacher_id"] = payload.get("teacher_id") or tch_id
                payload["employee_id"] = payload.get("employee_id") or emp_id

            # Duplicate email check
            existing = db.query(Teacher).filter(Teacher.email == payload.get("email")).first()
            if existing:
                return False, None, f"Teacher with email '{payload.get('email')}' already exists."

            teacher = StaffRepository.create_teacher(db, payload)

            log = ActivityLog(
                username=current_username,
                action="TEACHER_ADDED",
                module="TEACHERS",
                description=f"Added faculty member '{teacher.full_name}' ({teacher.teacher_id}, Subject: {teacher.primary_subject})",
                severity="INFO"
            )
            db.add(log)
            db.commit()

            app_logger.info(f"Teacher added: {teacher.teacher_id} - {teacher.full_name}")
            return True, teacher, "Teacher profile registered successfully."
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error adding teacher: {exc}")
            return False, None, str(exc)

    @staticmethod
    def update_teacher(
        db: Session,
        teacher_id: int,
        payload: Dict[str, Any],
        current_username: str = "admin"
    ) -> Tuple[bool, Optional[Teacher], str]:
        try:
            teacher = StaffRepository.get_teacher_by_id(db, teacher_id)
            if not teacher:
                return False, None, "Teacher not found."

            updated = StaffRepository.update_teacher(db, teacher, payload)

            log = ActivityLog(
                username=current_username,
                action="TEACHER_UPDATED",
                module="TEACHERS",
                description=f"Updated profile for teacher '{updated.full_name}' ({updated.teacher_id})",
                severity="INFO"
            )
            db.add(log)
            db.commit()

            return True, updated, "Teacher profile updated."
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error updating teacher {teacher_id}: {exc}")
            return False, None, str(exc)

    @staticmethod
    def add_staff(
        db: Session,
        payload: Dict[str, Any],
        current_username: str = "admin"
    ) -> Tuple[bool, Optional[Staff], str]:
        try:
            if not payload.get("staff_id") or not payload.get("employee_id"):
                stf_id, emp_id = StaffService.generate_staff_ids(db)
                payload["staff_id"] = payload.get("staff_id") or stf_id
                payload["employee_id"] = payload.get("employee_id") or emp_id

            staff_member = StaffRepository.create_staff(db, payload)

            log = ActivityLog(
                username=current_username,
                action="STAFF_ADDED",
                module="STAFF",
                description=f"Registered staff member '{staff_member.full_name}' ({staff_member.position})",
                severity="INFO"
            )
            db.add(log)
            db.commit()

            return True, staff_member, "Staff member registered successfully."
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error adding staff member: {exc}")
            return False, None, str(exc)

    @staticmethod
    def export_teachers_to_excel(db: Session, file_path: str) -> bool:
        teachers, _ = StaffRepository.search_and_filter_teachers(db, per_page=10000)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Faculty Directory"

        headers = [
            "Teacher ID", "Employee ID", "Full Name", "Gender", "Department",
            "Primary Subject", "Qualification", "Phone", "Email", "Monthly Salary (BDT)", "Status"
        ]
        ws.append(headers)

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for t in teachers:
            ws.append([
                t.teacher_id,
                t.employee_id,
                t.full_name,
                t.gender,
                t.department.name if t.department else "-",
                t.primary_subject,
                t.qualification,
                t.phone,
                t.email,
                t.salary,
                t.status.capitalize()
            ])

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(max_len + 3, 14)

        wb.save(file_path)
        app_logger.info(f"Exported {len(teachers)} teachers to Excel: {file_path}")
        return True
