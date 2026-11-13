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
from app.models.staff import (
    Teacher,
    Staff,
    Department,
    EmployeeLifecycleEvent,
    EmployeeSalaryHistory,
)
from app.models.activity import ActivityLog
from app.models.user import User
from app.services.hr_service import HRSecurityGuard
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
        current_username: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[Teacher], str]:
        try:
            HRSecurityGuard.require_permission("hr.directory.CREATE", actor_user)
            data = dict(payload)
            if "salary" in data and not HRSecurityGuard.can_manage_salary(actor_user):
                return False, None, "Access denied: unauthorized to set or modify salary information."

            if not data.get("teacher_id") or not data.get("employee_id"):
                tch_id, emp_id = StaffService.generate_teacher_ids(db)
                data["teacher_id"] = data.get("teacher_id") or tch_id
                data["employee_id"] = data.get("employee_id") or emp_id

            # Duplicate email check
            existing = db.query(Teacher).filter(Teacher.email == data.get("email")).first()
            if existing:
                return False, None, f"Teacher with email '{data.get('email')}' already exists."

            teacher = StaffRepository.create_teacher(db, data)
            actor_name = HRSecurityGuard.actor_username(actor_user, current_username)

            db.add(
                EmployeeLifecycleEvent(
                    employee_type="teacher",
                    teacher_id=teacher.id,
                    event_type="Joined",
                    effective_date=teacher.joining_date or date.today(),
                    to_designation=teacher.designation,
                    to_department_id=teacher.department_id,
                    to_status=teacher.status,
                    reason=f"Registered as {teacher.designation} ({teacher.primary_subject})",
                    recorded_by=actor_name,
                )
            )
            db.add(
                EmployeeSalaryHistory(
                    employee_type="teacher",
                    teacher_id=teacher.id,
                    previous_salary=0,
                    new_salary=teacher.salary or 0,
                    allowances=0,
                    effective_date=teacher.joining_date or date.today(),
                    change_reason="Initial Hiring",
                    approved_by=actor_name,
                )
            )

            log = ActivityLog(
                username=actor_name,
                action="TEACHER_ADDED",
                module="TEACHERS",
                description=f"Added faculty member '{teacher.full_name}' ({teacher.teacher_id}, Subject: {teacher.primary_subject})",
                severity="INFO",
            )
            db.add(log)
            db.commit()

            app_logger.info(f"Teacher added: {teacher.teacher_id} - {teacher.full_name}")
            return True, teacher, "Teacher profile registered successfully."
        except PermissionError as exc:
            db.rollback()
            return False, None, str(exc)
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error adding teacher: {exc}")
            return False, None, str(exc)

    @staticmethod
    def update_teacher(
        db: Session,
        teacher_id: int,
        payload: Dict[str, Any],
        current_username: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[Teacher], str]:
        try:
            HRSecurityGuard.require_permission("hr.directory.EDIT", actor_user)
            teacher = StaffRepository.get_teacher_by_id(db, teacher_id)
            if not teacher:
                return False, None, "Teacher not found."

            data = dict(payload)
            if "salary" in data and data["salary"] != teacher.salary:
                if not HRSecurityGuard.can_manage_salary(actor_user):
                    return False, None, "Access denied: unauthorized to modify salary information."

            old_salary = teacher.salary
            updated = StaffRepository.update_teacher(db, teacher, data)
            actor_name = HRSecurityGuard.actor_username(actor_user, current_username)

            if "salary" in data and updated.salary != old_salary:
                db.add(
                    EmployeeSalaryHistory(
                        employee_type="teacher",
                        teacher_id=updated.id,
                        previous_salary=old_salary or 0,
                        new_salary=updated.salary,
                        allowances=0,
                        effective_date=date.today(),
                        change_reason="Profile Salary Update",
                        approved_by=actor_name,
                    )
                )

            log = ActivityLog(
                username=actor_name,
                action="TEACHER_UPDATED",
                module="TEACHERS",
                description=f"Updated profile for teacher '{updated.full_name}' ({updated.teacher_id})",
                severity="INFO",
            )
            db.add(log)
            db.commit()

            return True, updated, "Teacher profile updated."
        except PermissionError as exc:
            db.rollback()
            return False, None, str(exc)
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error updating teacher {teacher_id}: {exc}")
            return False, None, str(exc)

    @staticmethod
    def add_staff(
        db: Session,
        payload: Dict[str, Any],
        current_username: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[Staff], str]:
        try:
            HRSecurityGuard.require_permission("hr.directory.CREATE", actor_user)
            data = dict(payload)
            if "salary" in data and not HRSecurityGuard.can_manage_salary(actor_user):
                return False, None, "Access denied: unauthorized to set or modify salary information."

            if not data.get("staff_id") or not data.get("employee_id"):
                stf_id, emp_id = StaffService.generate_staff_ids(db)
                data["staff_id"] = data.get("staff_id") or stf_id
                data["employee_id"] = data.get("employee_id") or emp_id

            staff_member = StaffRepository.create_staff(db, data)
            actor_name = HRSecurityGuard.actor_username(actor_user, current_username)

            db.add(
                EmployeeLifecycleEvent(
                    employee_type="staff",
                    staff_id=staff_member.id,
                    event_type="Joined",
                    effective_date=staff_member.joining_date or date.today(),
                    to_designation=staff_member.position,
                    to_department_id=staff_member.department_id,
                    to_status=staff_member.status,
                    reason=f"Registered as {staff_member.position}",
                    recorded_by=actor_name,
                )
            )
            db.add(
                EmployeeSalaryHistory(
                    employee_type="staff",
                    staff_id=staff_member.id,
                    previous_salary=0,
                    new_salary=staff_member.salary or 0,
                    allowances=0,
                    effective_date=staff_member.joining_date or date.today(),
                    change_reason="Initial Hiring",
                    approved_by=actor_name,
                )
            )

            log = ActivityLog(
                username=actor_name,
                action="STAFF_ADDED",
                module="STAFF",
                description=f"Registered staff member '{staff_member.full_name}' ({staff_member.position})",
                severity="INFO",
            )
            db.add(log)
            db.commit()

            return True, staff_member, "Staff member registered successfully."
        except PermissionError as exc:
            db.rollback()
            return False, None, str(exc)
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error adding staff member: {exc}")
            return False, None, str(exc)

    @staticmethod
    def update_staff(
        db: Session,
        staff_id: int,
        payload: Dict[str, Any],
        current_username: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[Staff], str]:
        try:
            HRSecurityGuard.require_permission("hr.directory.EDIT", actor_user)
            staff_obj = StaffRepository.get_staff_by_id(db, staff_id)
            if not staff_obj:
                return False, None, "Staff member not found."

            data = dict(payload)
            if "salary" in data and data["salary"] != staff_obj.salary:
                if not HRSecurityGuard.can_manage_salary(actor_user):
                    return False, None, "Access denied: unauthorized to modify salary information."

            old_salary = staff_obj.salary
            updated = StaffRepository.update_staff(db, staff_obj, data)
            actor_name = HRSecurityGuard.actor_username(actor_user, current_username)

            if "salary" in data and updated.salary != old_salary:
                db.add(
                    EmployeeSalaryHistory(
                        employee_type="staff",
                        staff_id=updated.id,
                        previous_salary=old_salary or 0,
                        new_salary=updated.salary,
                        allowances=0,
                        effective_date=date.today(),
                        change_reason="Profile Salary Update",
                        approved_by=actor_name,
                    )
                )

            log = ActivityLog(
                username=actor_name,
                action="STAFF_UPDATED",
                module="STAFF",
                description=f"Updated profile for staff member '{updated.full_name}' ({updated.staff_id})",
                severity="INFO",
            )
            db.add(log)
            db.commit()
            return True, updated, "Staff profile updated."
        except PermissionError as exc:
            db.rollback()
            return False, None, str(exc)
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error updating staff {staff_id}: {exc}")
            return False, None, str(exc)

    @staticmethod
    def export_teachers_to_excel(
        db: Session,
        file_path: str,
        actor_user: Optional[User] = None,
    ) -> bool:
        can_salary = HRSecurityGuard.can_view_salary(actor_user=actor_user, allow_when_no_session=True)
        teachers, _ = StaffRepository.search_and_filter_teachers(db, per_page=10000)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Faculty Directory"

        headers = [
            "Teacher ID", "Employee ID", "Full Name", "Gender", "Department",
            "Primary Subject", "Qualification", "Phone", "Email",
        ]
        if can_salary:
            headers.append("Monthly Salary (BDT)")
        headers.append("Status")
        ws.append(headers)

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for t in teachers:
            row = [
                t.teacher_id,
                t.employee_id,
                t.full_name,
                t.gender,
                t.department.name if t.department else "-",
                t.primary_subject,
                t.qualification,
                t.phone,
                t.email,
            ]
            if can_salary:
                row.append(t.salary)
            row.append(t.status.capitalize())
            ws.append(row)

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(max_len + 3, 14)

        wb.save(file_path)
        app_logger.info(f"Exported {len(teachers)} teachers to Excel: {file_path}")
        return True

    @staticmethod
    def export_staff_to_excel(
        db: Session,
        file_path: str,
        actor_user: Optional[User] = None,
    ) -> bool:
        can_salary = HRSecurityGuard.can_view_salary(actor_user=actor_user, allow_when_no_session=True)
        staff_list, _ = StaffRepository.search_and_filter_staff(db, per_page=10000)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Staff Directory"

        headers = [
            "Staff ID", "Employee ID", "Full Name", "Gender", "Position",
            "Department", "Shift", "Phone", "Email",
        ]
        if can_salary:
            headers.append("Monthly Salary (BDT)")
        headers.append("Status")
        ws.append(headers)

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="312E81", end_color="312E81", fill_type="solid")

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for s in staff_list:
            row = [
                s.staff_id,
                s.employee_id,
                s.full_name,
                s.gender,
                s.position,
                s.department.name if s.department else "-",
                s.shift,
                s.phone,
                s.email or "-",
            ]
            if can_salary:
                row.append(s.salary)
            row.append(s.status.capitalize())
            ws.append(row)

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(max_len + 3, 14)

        wb.save(file_path)
        app_logger.info(f"Exported {len(staff_list)} staff records to Excel: {file_path}")
        return True

