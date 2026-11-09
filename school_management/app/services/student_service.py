"""
EduManage Pro - Student Service
Business logic, student ID/admission number generation, Excel import/export with openpyxl, and audit logs.
"""

from datetime import date, datetime
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from app.repositories.student_repository import StudentRepository
from app.models.student import Student, Guardian, StudentStatus
from app.models.academic import SchoolClass, Section, AcademicYear
from app.models.activity import ActivityLog
from app.config.logging_config import app_logger, error_logger


class StudentService:
    @staticmethod
    def generate_identifiers(db: Session) -> Tuple[str, str]:
        """Generate unique student_id and admission_number."""
        curr_year = date.today().year
        count = db.query(Student).count() + 1
        student_id = f"STU-{curr_year}-{count:04d}"
        adm_number = f"ADM-{curr_year}-{count:04d}"
        return student_id, adm_number

    @staticmethod
    def admit_student(
        db: Session,
        student_payload: Dict[str, Any],
        guardian_payload: Optional[Dict[str, Any]],
        current_username: str = "admin"
    ) -> Tuple[bool, Optional[Student], str]:
        """Admit a new student with validation and automatic ID generation."""
        try:
            # Auto-generate IDs if not provided
            if not student_payload.get("student_id") or not student_payload.get("admission_number"):
                stu_id, adm_no = StudentService.generate_identifiers(db)
                student_payload["student_id"] = student_payload.get("student_id") or stu_id
                student_payload["admission_number"] = student_payload.get("admission_number") or adm_no

            # Calculate full name
            fname = student_payload.get("first_name", "").strip()
            lname = student_payload.get("last_name", "").strip()
            student_payload["full_name"] = f"{fname} {lname}".strip()

            # Check duplicate admission number
            existing = StudentRepository.get_by_admission_number(db, student_payload["admission_number"])
            if existing:
                return False, None, f"Admission number '{student_payload['admission_number']}' is already in use."

            student = StudentRepository.create(db, student_payload, guardian_payload)

            # Audit log
            log = ActivityLog(
                username=current_username,
                action="STUDENT_ADMITTED",
                module="STUDENTS",
                description=f"Admitted student '{student.full_name}' (ID: {student.student_id}, Roll: {student.roll_number})",
                severity="INFO"
            )
            db.add(log)
            db.commit()

            app_logger.info(f"Student admitted successfully: {student.student_id} - {student.full_name}")
            return True, student, "Student admitted successfully."
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error admitting student: {exc}")
            return False, None, str(exc)

    @staticmethod
    def update_student(
        db: Session,
        student_id: int,
        student_payload: Dict[str, Any],
        guardian_payload: Optional[Dict[str, Any]],
        current_username: str = "admin"
    ) -> Tuple[bool, Optional[Student], str]:
        try:
            student = StudentRepository.get_by_id(db, student_id)
            if not student:
                return False, None, "Student not found."

            if "first_name" in student_payload or "last_name" in student_payload:
                fname = student_payload.get("first_name", student.first_name).strip()
                lname = student_payload.get("last_name", student.last_name).strip()
                student_payload["full_name"] = f"{fname} {lname}".strip()

            updated = StudentRepository.update(db, student, student_payload, guardian_payload)

            log = ActivityLog(
                username=current_username,
                action="STUDENT_UPDATED",
                module="STUDENTS",
                description=f"Updated profile for student '{updated.full_name}' (ID: {updated.student_id})",
                severity="INFO"
            )
            db.add(log)
            db.commit()

            return True, updated, "Student details updated successfully."
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error updating student {student_id}: {exc}")
            return False, None, str(exc)

    @staticmethod
    def export_students_to_excel(db: Session, file_path: str, class_id: Optional[int] = None) -> bool:
        """Export students roster to .xlsx using openpyxl."""
        students, _ = StudentRepository.search_and_filter(db, class_id=class_id, per_page=10000)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Student Directory"

        # Headers
        headers = [
            "Student ID", "Admission No", "Roll", "Full Name", "Gender",
            "Class", "Section", "Blood Group", "Date of Birth", "Phone",
            "Guardian Name", "Guardian Phone", "Status"
        ]
        ws.append(headers)

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Rows
        for stu in students:
            ws.append([
                stu.student_id,
                stu.admission_number,
                stu.roll_number,
                stu.full_name,
                stu.gender,
                stu.school_class.name if stu.school_class else "-",
                stu.section.name if stu.section else "-",
                stu.blood_group or "-",
                stu.date_of_birth.strftime("%Y-%m-%d") if stu.date_of_birth else "-",
                stu.phone or "-",
                stu.guardian.guardian_name if stu.guardian else "-",
                stu.guardian.guardian_phone if stu.guardian else "-",
                stu.status.capitalize()
            ])

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        wb.save(file_path)
        app_logger.info(f"Exported {len(students)} student records to Excel: {file_path}")
        return True

    @staticmethod
    def import_students_from_excel(db: Session, file_path: str, default_class_id: int, default_ay_id: int) -> Tuple[int, List[str]]:
        """Import students from .xlsx with validation. Returns (imported_count, error_messages)."""
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active

        imported = 0
        errors = []

        # Expected row format: [Roll, First Name, Last Name, Gender, DOB (YYYY-MM-DD), Phone, Guardian Name, Guardian Phone]
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not any(row):
                continue
            try:
                roll = int(row[0]) if row[0] is not None else row_idx
                first_name = str(row[1]).strip() if len(row) > 1 and row[1] else "Student"
                last_name = str(row[2]).strip() if len(row) > 2 and row[2] else str(row_idx)
                gender = str(row[3]).strip() if len(row) > 3 and row[3] else "Male"
                
                # DOB
                dob_val = row[4] if len(row) > 4 else None
                if isinstance(dob_val, (date, datetime)):
                    dob = dob_val.date() if isinstance(dob_val, datetime) else dob_val
                else:
                    dob = date(2010, 1, 1)

                phone = str(row[5]).strip() if len(row) > 5 and row[5] else None
                g_name = str(row[6]).strip() if len(row) > 6 and row[6] else f"Guardian of {first_name}"
                g_phone = str(row[7]).strip() if len(row) > 7 and row[7] else "+880 1700-000000"

                stu_id, adm_no = StudentService.generate_identifiers(db)

                stu_data = {
                    "student_id": stu_id,
                    "admission_number": adm_no,
                    "roll_number": roll,
                    "first_name": first_name,
                    "last_name": last_name,
                    "full_name": f"{first_name} {last_name}",
                    "gender": gender,
                    "date_of_birth": dob,
                    "phone": phone,
                    "class_id": default_class_id,
                    "academic_year_id": default_ay_id,
                    "status": StudentStatus.ACTIVE
                }
                g_data = {
                    "guardian_name": g_name,
                    "guardian_phone": g_phone,
                    "relation": "Parent"
                }

                StudentRepository.create(db, stu_data, g_data)
                imported += 1
            except Exception as e:
                errors.append(f"Row {row_idx}: {str(e)}")

        return imported, errors
