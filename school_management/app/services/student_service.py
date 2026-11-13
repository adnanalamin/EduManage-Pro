"""
EduManage Pro - Student CRM Service
Complete lifecycle & CRM operations:
- Admission, duplicate prevention, Digital ID & QR payload generation
- Multiple guardians & family/sibling relationships
- Admission, Academic, Previous School & Status history tracking
- Document vault, Medical profile, Emergency contacts, Notes, Tags, Custom Fields
- 360° Timeline aggregation
- Promotion, Transfer, Withdrawal, Archive, Restore workflows
- Multi-format Excel (.xlsx) & CSV import wizard with column mapping + Excel export
"""

import csv
from datetime import date, datetime
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy.orm import Session

from app.config.logging_config import app_logger, error_logger
from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.activity import ActivityLog
from app.models.attendance import AttendanceStatus, StudentAttendance
from app.models.base import utc_now
from app.models.fee import FeePayment, StudentFee
from app.models.student import (
    Guardian,
    Student,
    StudentAcademicHistory,
    StudentAdmissionHistory,
    StudentDocument,
    StudentEmergencyContact,
    StudentFamilyRelationship,
    StudentGuardianLink,
    StudentMedicalProfile,
    StudentNote,
    StudentPreviousSchool,
    StudentStatus,
    StudentStatusHistory,
    StudentTag,
)
from app.repositories.student_repository import StudentRepository
from app.services.database_service import DatabaseService
from app.utils.qr_generator import (
    build_qr_payload,
    generate_digital_id,
    store_student_document,
    store_student_photo,
)


IMPORT_TARGET_FIELDS: List[Tuple[str, str]] = [
    ("ignore", "-- Skip Column --"),
    ("roll_number", "Roll Number"),
    ("first_name", "First Name*"),
    ("last_name", "Last Name*"),
    ("full_name", "Full Name (Auto-splits)"),
    ("gender", "Gender"),
    ("date_of_birth", "Date of Birth (YYYY-MM-DD)"),
    ("blood_group", "Blood Group"),
    ("phone", "Student Phone"),
    ("email", "Student Email"),
    ("address", "Address"),
    ("birth_certificate_no", "Birth Certificate No"),
    ("admission_number", "Admission Number"),
    ("student_id", "Student ID"),
    ("guardian_name", "Guardian Name"),
    ("guardian_phone", "Guardian Phone"),
    ("guardian_relation", "Guardian Relationship"),
    ("father_name", "Father Name"),
    ("mother_name", "Mother Name"),
    ("previous_school", "Previous School"),
    ("emergency_contact", "Emergency Phone"),
    ("tags", "Tags (comma-separated)"),
]

_HEADER_AUTO_MAP: Dict[str, str] = {
    "roll": "roll_number",
    "rollno": "roll_number",
    "rollnumber": "roll_number",
    "firstname": "first_name",
    "fname": "first_name",
    "lastname": "last_name",
    "lname": "last_name",
    "fullname": "full_name",
    "name": "full_name",
    "studentname": "full_name",
    "gender": "gender",
    "sex": "gender",
    "dob": "date_of_birth",
    "dateofbirth": "date_of_birth",
    "birthdate": "date_of_birth",
    "bloodgroup": "blood_group",
    "blood": "blood_group",
    "phone": "phone",
    "mobile": "phone",
    "studentphone": "phone",
    "email": "email",
    "studentemail": "email",
    "address": "address",
    "birthcertificateno": "birth_certificate_no",
    "birthcert": "birth_certificate_no",
    "admissionnumber": "admission_number",
    "admissionno": "admission_number",
    "studentid": "student_id",
    "id": "student_id",
    "guardianname": "guardian_name",
    "guardian": "guardian_name",
    "parentname": "guardian_name",
    "guardianphone": "guardian_phone",
    "parentphone": "guardian_phone",
    "guardianrelation": "guardian_relation",
    "relation": "guardian_relation",
    "fathername": "father_name",
    "mothername": "mother_name",
    "previousschool": "previous_school",
    "emergencycontact": "emergency_contact",
    "emergencyphone": "emergency_contact",
    "tags": "tags",
}


def _parse_date_flexible(val: Any, fallback: Optional[date] = None) -> Optional[date]:
    if val is None or str(val).strip() == "":
        return fallback
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    text_val = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text_val, fmt).date()
        except ValueError:
            continue
    return fallback


class StudentService:
    @staticmethod
    def generate_identifiers(db: Session) -> Tuple[str, str]:
        """Generate collision-free student_id and admission_number."""
        curr_year = date.today().year
        existing_students = db.query(Student.student_id, Student.admission_number).all()
        used_sids = {row[0] for row in existing_students if row[0]}
        used_adms = {row[1] for row in existing_students if row[1]}

        seq = len(existing_students) + 1
        while True:
            student_id = f"STU-{curr_year}-{seq:04d}"
            adm_number = f"ADM-{curr_year}-{seq:04d}"
            if student_id not in used_sids and adm_number not in used_adms:
                return student_id, adm_number
            seq += 1

    @staticmethod
    def _validate_status(status_val: Optional[str]) -> str:
        val = (status_val or StudentStatus.ACTIVE).strip().lower()
        if val not in StudentStatus.ALL:
            raise ValueError(
                f"Invalid student status '{status_val}'. Allowed: {', '.join(StudentStatus.ALL)}"
            )
        return val

    @staticmethod
    def _log(
        db: Session,
        action: str,
        description: str,
        username: str = "admin",
        entity_id: Optional[int] = None,
        severity: str = "INFO",
    ) -> None:
        DatabaseService.log_activity(
            db,
            action=action,
            module="STUDENTS",
            description=description,
            username=username,
            severity=severity,
            entity_type="Student",
            entity_id=str(entity_id) if entity_id is not None else None,
            commit=False,
        )

    @staticmethod
    def admit_student(
        db: Session,
        student_payload: Dict[str, Any],
        guardian_payload: Optional[Dict[str, Any]],
        current_username: str = "admin",
        # Optional extended CRM inputs
        tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        medical_data: Optional[Dict[str, Any]] = None,
        admission_type: str = "New Admission",
        copy_photo_file: bool = True,
    ) -> Tuple[bool, Optional[Student], str]:
        """Admit a new student with duplicate rejection, Digital ID/QR generation, and initial CRM histories."""
        try:
            payload = dict(student_payload)
            tags_arg = tags if tags is not None else payload.pop("tags", None)
            custom_fields_arg = (
                custom_fields if custom_fields is not None else payload.pop("custom_fields", None)
            )
            medical_arg = medical_data if medical_data is not None else payload.pop("medical_data", None)

            # Normalize status
            payload["status"] = StudentService._validate_status(payload.get("status"))

            # Auto-generate identifiers if omitted
            if not payload.get("student_id") or not payload.get("admission_number"):
                stu_id, adm_no = StudentService.generate_identifiers(db)
                payload["student_id"] = payload.get("student_id") or stu_id
                payload["admission_number"] = payload.get("admission_number") or adm_no

            if not payload.get("digital_id_code"):
                payload["digital_id_code"] = generate_digital_id(
                    payload["student_id"],
                    payload.get("admission_date"),
                )

            # Calculate full name
            fname = str(payload.get("first_name", "")).strip()
            lname = str(payload.get("last_name", "")).strip()
            payload["full_name"] = f"{fname} {lname}".strip() or str(payload.get("full_name", "")).strip()

            # Check duplicates across IDs, birth cert, Digital ID, and identity tuples
            guardian_phone = guardian_payload.get("guardian_phone") if guardian_payload else None
            dup_msg = DatabaseService.check_duplicate_student(
                db,
                student_id=payload.get("student_id"),
                admission_number=payload.get("admission_number"),
                birth_certificate_no=payload.get("birth_certificate_no"),
                digital_id_code=payload.get("digital_id_code"),
                full_name=payload.get("full_name"),
                date_of_birth=payload.get("date_of_birth"),
                guardian_phone=guardian_phone,
                student_phone=payload.get("phone"),
            )
            if dup_msg:
                return False, None, dup_msg

            # Copy local photo into managed vault if requested and exists
            if copy_photo_file and payload.get("photo_path"):
                src_photo = Path(str(payload["photo_path"]))
                if src_photo.exists() and src_photo.is_file():
                    payload["photo_path"] = store_student_photo(payload["student_id"], str(src_photo))

            student = StudentRepository.create(db, payload, guardian_payload)

            if custom_fields_arg:
                student.set_custom_fields(custom_fields_arg)

            # Record initial Admission History
            db.add(
                StudentAdmissionHistory(
                    student_id=student.id,
                    academic_year_id=student.academic_year_id,
                    admitted_class_id=student.class_id,
                    admitted_section_id=student.section_id,
                    admission_number=student.admission_number,
                    admission_date=student.admission_date or date.today(),
                    admission_type=admission_type,
                    admission_source=student.admission_source,
                    previous_school=student.previous_school,
                    remarks="Initial student admission",
                    recorded_by=current_username,
                )
            )

            # Record initial Academic History
            db.add(
                StudentAcademicHistory(
                    student_id=student.id,
                    academic_year_id=student.academic_year_id,
                    class_id=student.class_id,
                    section_id=student.section_id,
                    roll_number=student.roll_number,
                    group=student.group,
                    shift=student.shift,
                    result_status="Enrolled",
                    start_date=student.admission_date or date.today(),
                    remarks="Enrolled upon admission",
                )
            )

            # Record initial Status History
            db.add(
                StudentStatusHistory(
                    student_id=student.id,
                    from_status=None,
                    to_status=student.status,
                    effective_date=student.admission_date or date.today(),
                    reason="Initial admission",
                    changed_by=current_username,
                    changed_at=utc_now(),
                )
            )

            # Optional Previous School structured record
            if student.previous_school and student.previous_school.strip():
                db.add(
                    StudentPreviousSchool(
                        student_id=student.id,
                        school_name=student.previous_school.strip(),
                        reason_for_leaving="Transferred upon new admission",
                    )
                )

            # Optional Medical Profile record
            if medical_arg or student.blood_group or student.medical_notes:
                med_payload = dict(medical_arg or {})
                med_payload.setdefault("blood_group", student.blood_group)
                if student.medical_notes and not med_payload.get("emergency_protocol"):
                    med_payload["allergies"] = med_payload.get("allergies") or student.medical_notes
                db.add(StudentMedicalProfile(student_id=student.id, **med_payload))

            # Optional initial Emergency Contact if provided on student
            if student.emergency_contact and student.emergency_contact.strip():
                db.add(
                    StudentEmergencyContact(
                        student_id=student.id,
                        contact_name=(guardian_payload or {}).get("guardian_name") or "Primary Emergency Contact",
                        relationship_label=(guardian_payload or {}).get("relation") or "Guardian",
                        primary_phone=student.emergency_contact.strip(),
                        priority_order=1,
                        can_pickup=True,
                    )
                )

            db.flush()
            if tags_arg:
                StudentService._apply_tags(db, student, tags_arg)

            StudentService._log(
                db,
                action="STUDENT_ADMITTED",
                description=(
                    f"Admitted student '{student.full_name}' "
                    f"(ID: {student.student_id}, Digital ID: {student.digital_id_code}, Roll: {student.roll_number})"
                ),
                username=current_username,
                entity_id=student.id,
            )
            db.commit()
            db.refresh(student)

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
        current_username: str = "admin",
        tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        copy_photo_file: bool = True,
    ) -> Tuple[bool, Optional[Student], str]:
        try:
            student = StudentRepository.get_by_id(db, student_id)
            if not student:
                return False, None, "Student not found."

            payload = dict(student_payload)
            tags_arg = tags if tags is not None else payload.pop("tags", None)
            custom_fields_arg = (
                custom_fields if custom_fields is not None else payload.pop("custom_fields", None)
            )

            if "status" in payload and payload["status"] is not None:
                payload["status"] = StudentService._validate_status(payload["status"])

            if "first_name" in payload or "last_name" in payload:
                fname = str(payload.get("first_name", student.first_name)).strip()
                lname = str(payload.get("last_name", student.last_name)).strip()
                payload["full_name"] = f"{fname} {lname}".strip()

            guardian_phone = (
                guardian_payload.get("guardian_phone")
                if guardian_payload
                else (student.guardian.guardian_phone if student.guardian else None)
            )
            dup_msg = DatabaseService.check_duplicate_student(
                db,
                student_id=payload.get("student_id"),
                admission_number=payload.get("admission_number"),
                birth_certificate_no=payload.get("birth_certificate_no"),
                digital_id_code=payload.get("digital_id_code"),
                full_name=payload.get("full_name", student.full_name),
                date_of_birth=payload.get("date_of_birth", student.date_of_birth),
                guardian_phone=guardian_phone,
                student_phone=payload.get("phone", student.phone),
                exclude_student_pk=student.id,
            )
            if dup_msg:
                return False, None, dup_msg

            if copy_photo_file and payload.get("photo_path") and payload["photo_path"] != student.photo_path:
                src_photo = Path(str(payload["photo_path"]))
                if src_photo.exists() and src_photo.is_file():
                    payload["photo_path"] = store_student_photo(student.student_id, str(src_photo))

            old_status = student.status
            updated = StudentRepository.update(db, student, payload, guardian_payload)

            if "status" in payload and payload["status"] != old_status:
                db.add(
                    StudentStatusHistory(
                        student_id=updated.id,
                        from_status=old_status,
                        to_status=updated.status,
                        effective_date=date.today(),
                        reason="Profile status updated",
                        changed_by=current_username,
                        changed_at=utc_now(),
                    )
                )

            if custom_fields_arg is not None:
                updated.set_custom_fields(custom_fields_arg)
            if tags_arg is not None:
                StudentService._apply_tags(db, updated, tags_arg)

            StudentService._log(
                db,
                action="STUDENT_UPDATED",
                description=f"Updated profile for student '{updated.full_name}' (ID: {updated.student_id})",
                username=current_username,
                entity_id=updated.id,
            )
            db.commit()
            db.refresh(updated)
            return True, updated, "Student details updated successfully."
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error updating student {student_id}: {exc}")
            return False, None, str(exc)

    # ------------------------------------------------------------------
    # Lifecycle Workflows (Promote, Transfer, Withdraw, Archive, Restore)
    # ------------------------------------------------------------------
    @staticmethod
    def change_status(
        db: Session,
        student_pk: int,
        new_status: str,
        reason: Optional[str] = None,
        effective_date: Optional[date] = None,
        reference_no: Optional[str] = None,
        destination_school: Optional[str] = None,
        actor: str = "admin",
    ) -> Tuple[bool, Optional[Student], str]:
        try:
            target_status = StudentService._validate_status(new_status)
            student = StudentRepository.get_by_id(db, student_pk)
            if not student:
                return False, None, "Student not found."

            eff_date = effective_date or date.today()
            old_status = student.status

            student.status = target_status
            if target_status == StudentStatus.TRANSFERRED:
                student.transfer_date = eff_date
                student.transfer_school = destination_school
                student.transfer_tc_number = reference_no
            elif target_status == StudentStatus.WITHDRAWN:
                student.withdrawal_date = eff_date
                student.withdrawal_reason = reason
            elif target_status == StudentStatus.ARCHIVED:
                student.archived_at = utc_now()
                student.archived_by = actor
            elif target_status == StudentStatus.ACTIVE:
                student.is_deleted = False
                student.deleted_at = None
                student.deleted_by = None
                student.archived_at = None
                student.archived_by = None

            db.add(
                StudentStatusHistory(
                    student_id=student.id,
                    from_status=old_status,
                    to_status=target_status,
                    effective_date=eff_date,
                    reason=reason,
                    reference_no=reference_no,
                    destination_school=destination_school,
                    changed_by=actor,
                    changed_at=utc_now(),
                )
            )
            StudentService._log(
                db,
                action=f"STUDENT_STATUS_{target_status.upper()}",
                description=(
                    f"Changed status for '{student.full_name}' ({student.student_id}) "
                    f"from '{old_status}' to '{target_status}'"
                    + (f": {reason}" if reason else "")
                ),
                username=actor,
                entity_id=student.id,
            )
            db.commit()
            db.refresh(student)
            return True, student, f"Student status updated to '{StudentStatus.LABELS.get(target_status, target_status)}'."
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error changing status for student {student_pk}: {exc}")
            return False, None, str(exc)

    @staticmethod
    def promote_students(
        db: Session,
        student_ids: List[int],
        to_class_id: int,
        to_academic_year_id: int,
        to_section_id: Optional[int] = None,
        remarks: str = "Year-end batch promotion",
        actor: str = "admin",
    ) -> Tuple[bool, int, str]:
        if not student_ids:
            return False, 0, "No students selected for promotion."
        try:
            count = StudentRepository.bulk_promote(
                db,
                student_ids=student_ids,
                target_class_id=to_class_id,
                target_academic_year_id=to_academic_year_id,
                remarks=remarks,
                target_section_id=to_section_id,
                promoted_by=actor,
            )
            StudentService._log(
                db,
                action="STUDENTS_PROMOTED",
                description=f"Promoted {count} student(s) to class_id={to_class_id}, academic_year_id={to_academic_year_id}",
                username=actor,
            )
            db.commit()
            return True, count, f"Promoted {count} student(s) successfully."
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error promoting students: {exc}")
            return False, 0, str(exc)

    @staticmethod
    def transfer_student(
        db: Session,
        student_pk: int,
        destination_school: str,
        tc_number: Optional[str] = None,
        reason: Optional[str] = "Student Transfer Out",
        effective_date: Optional[date] = None,
        actor: str = "admin",
    ) -> Tuple[bool, Optional[Student], str]:
        if not destination_school or not destination_school.strip():
            return False, None, "Destination school name is required for transfer."
        return StudentService.change_status(
            db,
            student_pk=student_pk,
            new_status=StudentStatus.TRANSFERRED,
            reason=reason,
            effective_date=effective_date,
            reference_no=tc_number,
            destination_school=destination_school.strip(),
            actor=actor,
        )

    @staticmethod
    def withdraw_student(
        db: Session,
        student_pk: int,
        reason: str,
        effective_date: Optional[date] = None,
        actor: str = "admin",
    ) -> Tuple[bool, Optional[Student], str]:
        if not reason or not reason.strip():
            return False, None, "Withdrawal reason is required."
        return StudentService.change_status(
            db,
            student_pk=student_pk,
            new_status=StudentStatus.WITHDRAWN,
            reason=reason.strip(),
            effective_date=effective_date,
            actor=actor,
        )

    @staticmethod
    def archive_student(
        db: Session,
        student_pk: int,
        reason: str = "Archived by administrator",
        actor: str = "admin",
    ) -> Tuple[bool, Optional[Student], str]:
        return StudentService.change_status(
            db,
            student_pk=student_pk,
            new_status=StudentStatus.ARCHIVED,
            reason=reason,
            effective_date=date.today(),
            actor=actor,
        )

    @staticmethod
    def restore_student(
        db: Session,
        student_pk: int,
        reason: str = "Restored to active enrollment",
        actor: str = "admin",
    ) -> Tuple[bool, Optional[Student], str]:
        return StudentService.change_status(
            db,
            student_pk=student_pk,
            new_status=StudentStatus.ACTIVE,
            reason=reason,
            effective_date=date.today(),
            actor=actor,
        )

    # ------------------------------------------------------------------
    # Student CRM Sub-Entity Operations
    # ------------------------------------------------------------------
    @staticmethod
    def add_guardian(
        db: Session,
        student_pk: int,
        guardian_data: Dict[str, Any],
        relationship_type: str = "Guardian",
        is_primary: bool = False,
        is_emergency_contact: bool = True,
        is_financial_payer: bool = False,
        can_pickup: bool = True,
        priority_order: Optional[int] = None,
        notes: Optional[str] = None,
        actor: str = "admin",
    ) -> Tuple[bool, Optional[StudentGuardianLink], str]:
        try:
            student = StudentRepository.get_by_id(db, student_pk)
            if not student:
                return False, None, "Student not found."
            if not guardian_data.get("guardian_name") or not guardian_data.get("guardian_phone"):
                return False, None, "Guardian name and phone are required."

            g_payload = dict(guardian_data)
            g_payload.setdefault("relation", relationship_type)
            guardian = Guardian(**g_payload)
            db.add(guardian)
            db.flush()

            if is_primary:
                db.query(StudentGuardianLink).filter_by(student_id=student.id).update({"is_primary": False})
                student.guardian_id = guardian.id

            order = priority_order
            if order is None:
                order = db.query(StudentGuardianLink).filter_by(student_id=student.id).count() + 1

            link = StudentGuardianLink(
                student_id=student.id,
                guardian_id=guardian.id,
                relationship_type=relationship_type,
                is_primary=is_primary,
                is_emergency_contact=is_emergency_contact,
                is_financial_payer=is_financial_payer,
                can_pickup=can_pickup,
                priority_order=order,
                notes=notes,
            )
            db.add(link)
            StudentService._log(
                db,
                action="STUDENT_GUARDIAN_ADDED",
                description=f"Linked {relationship_type} '{guardian.guardian_name}' to '{student.full_name}'",
                username=actor,
                entity_id=student.id,
            )
            db.commit()
            db.refresh(link)
            return True, link, "Guardian added to student profile."
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def link_family_member(
        db: Session,
        student_pk: int,
        related_student_pk: int,
        relation_type: str = "Sibling",
        notes: Optional[str] = None,
        bidirectional: bool = True,
        actor: str = "admin",
    ) -> Tuple[bool, Optional[StudentFamilyRelationship], str]:
        try:
            if student_pk == related_student_pk:
                return False, None, "Cannot link a student to themselves."
            stu_a = StudentRepository.get_by_id(db, student_pk)
            stu_b = StudentRepository.get_by_id(db, related_student_pk)
            if not stu_a or not stu_b:
                return False, None, "One or both students not found."

            existing = (
                db.query(StudentFamilyRelationship)
                .filter_by(student_id=student_pk, related_student_id=related_student_pk)
                .first()
            )
            if existing:
                return False, existing, "Family relationship already linked."

            rel = StudentFamilyRelationship(
                student_id=student_pk,
                related_student_id=related_student_pk,
                relation_type=relation_type,
                notes=notes,
            )
            db.add(rel)

            if bidirectional:
                rev = (
                    db.query(StudentFamilyRelationship)
                    .filter_by(student_id=related_student_pk, related_student_id=student_pk)
                    .first()
                )
                if not rev:
                    db.add(
                        StudentFamilyRelationship(
                            student_id=related_student_pk,
                            related_student_id=student_pk,
                            relation_type=relation_type,
                            notes=notes,
                        )
                    )

            StudentService._log(
                db,
                action="STUDENT_FAMILY_LINKED",
                description=f"Linked {relation_type}: '{stu_a.full_name}' <-> '{stu_b.full_name}'",
                username=actor,
                entity_id=student_pk,
            )
            db.commit()
            db.refresh(rel)
            return True, rel, "Family relationship linked successfully."
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def add_previous_school(
        db: Session,
        student_pk: int,
        school_data: Dict[str, Any],
        actor: str = "admin",
    ) -> Tuple[bool, Optional[StudentPreviousSchool], str]:
        try:
            student = StudentRepository.get_by_id(db, student_pk)
            if not student:
                return False, None, "Student not found."
            if not school_data.get("school_name"):
                return False, None, "School name is required."

            rec = StudentPreviousSchool(student_id=student.id, **school_data)
            db.add(rec)
            if not student.previous_school:
                student.previous_school = school_data["school_name"]
            StudentService._log(
                db,
                action="STUDENT_PREV_SCHOOL_ADDED",
                description=f"Added previous school '{school_data['school_name']}' for '{student.full_name}'",
                username=actor,
                entity_id=student.id,
            )
            db.commit()
            db.refresh(rec)
            return True, rec, "Previous school record added."
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def add_document(
        db: Session,
        student_pk: int,
        doc_type: str,
        title: str,
        source_file_path: Optional[str] = None,
        copy_to_vault: bool = True,
        issued_date: Optional[date] = None,
        expiry_date: Optional[date] = None,
        notes: Optional[str] = None,
        is_verified: bool = False,
        actor: str = "admin",
    ) -> Tuple[bool, Optional[StudentDocument], str]:
        try:
            student = StudentRepository.get_by_id(db, student_pk)
            if not student:
                return False, None, "Student not found."

            stored_path = source_file_path
            file_name = Path(source_file_path).name if source_file_path else None
            file_size = 0
            mime_type = None

            if source_file_path:
                src = Path(source_file_path)
                if src.exists() and src.is_file():
                    if copy_to_vault:
                        stored_path, file_name, file_size = store_student_document(student.student_id, source_file_path)
                    else:
                        file_size = src.stat().st_size
                    ext = src.suffix.lower()
                    mime_type = {
                        ".pdf": "application/pdf",
                        ".png": "image/png",
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    }.get(ext, "application/octet-stream")

            doc = StudentDocument(
                student_id=student.id,
                document_type=doc_type.strip(),
                title=title.strip(),
                file_name=file_name,
                file_path=stored_path,
                mime_type=mime_type,
                file_size_bytes=file_size,
                is_verified=is_verified,
                verified_by=actor if is_verified else None,
                verified_at=utc_now() if is_verified else None,
                issued_date=issued_date,
                expiry_date=expiry_date,
                notes=notes,
                uploaded_by=actor,
            )
            db.add(doc)
            StudentService._log(
                db,
                action="STUDENT_DOCUMENT_ADDED",
                description=f"Added document [{doc_type}] '{title}' for '{student.full_name}'",
                username=actor,
                entity_id=student.id,
            )
            db.commit()
            db.refresh(doc)
            return True, doc, "Document recorded successfully."
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def verify_document(
        db: Session, doc_id: int, verified: bool = True, actor: str = "admin"
    ) -> Tuple[bool, str]:
        doc = db.query(StudentDocument).filter_by(id=doc_id).first()
        if not doc:
            return False, "Document record not found."
        doc.is_verified = verified
        doc.verified_by = actor if verified else None
        doc.verified_at = utc_now() if verified else None
        db.commit()
        return True, "Document verification updated."

    @staticmethod
    def upsert_medical_profile(
        db: Session,
        student_pk: int,
        medical_data: Dict[str, Any],
        actor: str = "admin",
    ) -> Tuple[bool, Optional[StudentMedicalProfile], str]:
        try:
            student = StudentRepository.get_by_id(db, student_pk)
            if not student:
                return False, None, "Student not found."

            profile = db.query(StudentMedicalProfile).filter_by(student_id=student.id).first()
            if profile:
                for k, v in medical_data.items():
                    if hasattr(profile, k):
                        setattr(profile, k, v)
            else:
                filtered = {k: v for k, v in medical_data.items() if hasattr(StudentMedicalProfile, k)}
                profile = StudentMedicalProfile(student_id=student.id, **filtered)
                db.add(profile)

            if medical_data.get("blood_group"):
                student.blood_group = medical_data["blood_group"]

            StudentService._log(
                db,
                action="STUDENT_MEDICAL_UPDATED",
                description=f"Updated medical dossier for '{student.full_name}'",
                username=actor,
                entity_id=student.id,
            )
            db.commit()
            db.refresh(profile)
            return True, profile, "Medical dossier saved."
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def add_emergency_contact(
        db: Session,
        student_pk: int,
        contact_data: Dict[str, Any],
        actor: str = "admin",
    ) -> Tuple[bool, Optional[StudentEmergencyContact], str]:
        try:
            student = StudentRepository.get_by_id(db, student_pk)
            if not student:
                return False, None, "Student not found."
            if not contact_data.get("contact_name") or not contact_data.get("primary_phone"):
                return False, None, "Emergency contact name and primary phone are required."

            priority = contact_data.get("priority_order")
            if priority is None:
                priority = db.query(StudentEmergencyContact).filter_by(student_id=student.id).count() + 1

            payload = dict(contact_data)
            payload["priority_order"] = priority
            payload.setdefault("relationship_label", "Relative")
            contact = StudentEmergencyContact(student_id=student.id, **payload)
            db.add(contact)
            if not student.emergency_contact:
                student.emergency_contact = payload["primary_phone"]

            StudentService._log(
                db,
                action="STUDENT_EMERGENCY_CONTACT_ADDED",
                description=f"Added emergency contact '{payload['contact_name']}' for '{student.full_name}'",
                username=actor,
                entity_id=student.id,
            )
            db.commit()
            db.refresh(contact)
            return True, contact, "Emergency contact added."
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def add_note(
        db: Session,
        student_pk: int,
        title: str,
        content: str,
        category: str = "General",
        is_pinned: bool = False,
        is_confidential: bool = False,
        actor: str = "admin",
    ) -> Tuple[bool, Optional[StudentNote], str]:
        try:
            student = StudentRepository.get_by_id(db, student_pk)
            if not student:
                return False, None, "Student not found."
            if not title.strip() or not content.strip():
                return False, None, "Note title and content are required."

            note = StudentNote(
                student_id=student.id,
                category=category.strip() or "General",
                title=title.strip(),
                content=content.strip(),
                is_pinned=is_pinned,
                is_confidential=is_confidential,
                author_username=actor,
            )
            db.add(note)
            StudentService._log(
                db,
                action="STUDENT_NOTE_ADDED",
                description=f"Added CRM note [{category}] '{title}' for '{student.full_name}'",
                username=actor,
                entity_id=student.id,
            )
            db.commit()
            db.refresh(note)
            return True, note, "CRM note added."
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def _apply_tags(db: Session, student: Student, tag_names: List[str]) -> List[str]:
        normalized: List[str] = []
        seen = set()
        for raw in tag_names:
            cleaned = str(raw).strip()
            if not cleaned:
                continue
            key = cleaned.lower()
            if key not in seen:
                seen.add(key)
                normalized.append(cleaned)

        tag_objs: List[StudentTag] = []
        for name in normalized:
            existing = db.query(StudentTag).filter(StudentTag.name.ilike(name)).first()
            if not existing:
                existing = StudentTag(name=name)
                db.add(existing)
                db.flush()
            tag_objs.append(existing)

        student.tags = tag_objs
        student.tags_text = ("|" + "|".join(t.name for t in tag_objs) + "|") if tag_objs else None
        return [t.name for t in tag_objs]

    @staticmethod
    def set_tags(
        db: Session, student_pk: int, tag_names: List[str], actor: str = "admin"
    ) -> Tuple[bool, List[str], str]:
        try:
            student = StudentRepository.get_by_id(db, student_pk)
            if not student:
                return False, [], "Student not found."
            applied = StudentService._apply_tags(db, student, tag_names)
            StudentService._log(
                db,
                action="STUDENT_TAGS_UPDATED",
                description=f"Updated tags for '{student.full_name}': {', '.join(applied) or 'None'}",
                username=actor,
                entity_id=student.id,
            )
            db.commit()
            return True, applied, "Student tags updated."
        except Exception as exc:
            db.rollback()
            return False, [], str(exc)

    @staticmethod
    def update_custom_fields(
        db: Session, student_pk: int, fields: Dict[str, Any], actor: str = "admin"
    ) -> Tuple[bool, Dict[str, Any], str]:
        try:
            student = StudentRepository.get_by_id(db, student_pk)
            if not student:
                return False, {}, "Student not found."
            student.set_custom_fields(fields)
            StudentService._log(
                db,
                action="STUDENT_CUSTOM_FIELDS_UPDATED",
                description=f"Updated custom CRM fields for '{student.full_name}'",
                username=actor,
                entity_id=student.id,
            )
            db.commit()
            return True, student.get_custom_fields(), "Custom fields saved."
        except Exception as exc:
            db.rollback()
            return False, {}, str(exc)

    @staticmethod
    def get_student_timeline(db: Session, student_pk: int) -> List[Dict[str, Any]]:
        """Build a chronological 360° CRM timeline across admissions, statuses, academics, docs, notes, and fees."""
            # noqa
        student = StudentRepository.get_by_id(db, student_pk)
        if not student:
            return []

        events: List[Dict[str, Any]] = []

        for adm in student.admission_history:
            events.append({
                "timestamp": datetime.combine(adm.admission_date, datetime.min.time()),
                "category": "Admission",
                "title": f"{adm.admission_type} (#{adm.admission_number})",
                "details": (
                    f"Class: {adm.admitted_class.name if adm.admitted_class else '-'} | "
                    f"Session: {adm.academic_year.name if adm.academic_year else '-'}"
                    + (f" | {adm.remarks}" if adm.remarks else "")
                ),
                "actor": adm.recorded_by,
            })

        for st in student.status_history:
            ts = st.changed_at.replace(tzinfo=None) if st.changed_at else datetime.combine(st.effective_date, datetime.min.time())
            events.append({
                "timestamp": ts,
                "category": "Status",
                "title": f"Status: {(st.from_status or 'New').title()} -> {st.to_status.title()}",
                "details": (st.reason or "") + (f" | Ref: {st.reference_no}" if st.reference_no else "") + (f" | Dest: {st.destination_school}" if st.destination_school else ""),
                "actor": st.changed_by,
            })

        for prom in student.promotion_history:
            events.append({
                "timestamp": datetime.combine(prom.promoted_date, datetime.min.time()),
                "category": "Promotion",
                "title": (
                    f"{prom.promotion_type or 'Promoted'}: "
                    f"{prom.from_class.name if prom.from_class else '-'} "
                    f"-> {prom.to_class.name if prom.to_class else '-'}"
                ),
                "details": prom.remarks or "Academic promotion",
                "actor": prom.promoted_by or "system",
            })

        for xfer in student.transfer_history:
            events.append({
                "timestamp": datetime.combine(xfer.effective_date, datetime.min.time()),
                "category": "Academic Transfer",
                "title": (
                    f"{xfer.transfer_type.replace('_', ' ').title()}: "
                    f"{xfer.from_class.name if xfer.from_class else '-'} "
                    f"({xfer.from_section.name if xfer.from_section else '-'}) -> "
                    f"{xfer.to_class.name if xfer.to_class else '-'} "
                    f"({xfer.to_section.name if xfer.to_section else '-'})"
                ),
                "details": xfer.reason or "Internal class/section transfer",
                "actor": xfer.transferred_by or "system",
            })

        for doc in student.documents:
            ts = doc.created_at.replace(tzinfo=None) if doc.created_at else datetime.now()
            events.append({
                "timestamp": ts,
                "category": "Document",
                "title": f"Document Uploaded: {doc.title} ({doc.document_type})",
                "details": "Verified" if doc.is_verified else "Pending Verification",
                "actor": doc.uploaded_by,
            })

        for note in student.notes:
            ts = note.created_at.replace(tzinfo=None) if note.created_at else datetime.now()
            events.append({
                "timestamp": ts,
                "category": f"Note ({note.category})",
                "title": note.title,
                "details": note.content,
                "actor": note.author_username,
            })

        payments = (
            db.query(FeePayment)
            .join(StudentFee, FeePayment.student_fee_id == StudentFee.id)
            .filter(StudentFee.student_id == student.id, FeePayment.is_deleted == False)
            .all()
        )
        for pay in payments:
            ts = pay.payment_date.replace(tzinfo=None) if pay.payment_date else datetime.now()
            events.append({
                "timestamp": ts,
                "category": "Fee Payment",
                "title": f"Payment Receipt {pay.receipt_no}",
                "details": f"Amount: {float(pay.amount_paid):,.2f} via {pay.payment_method}",
                "actor": pay.collected_by or "cashier",
            })

        # Attendance snapshot summary
        att_rows = db.query(StudentAttendance).filter_by(student_id=student.id).all()
        if att_rows:
            present = sum(1 for a in att_rows if a.status == AttendanceStatus.PRESENT)
            latest_att = max(a.date for a in att_rows)
            events.append({
                "timestamp": datetime.combine(latest_att, datetime.min.time()),
                "category": "Attendance",
                "title": f"Attendance Summary ({present}/{len(att_rows)} Present)",
                "details": f"Rate: {(present / len(att_rows)) * 100:.1f}%",
                "actor": "system",
            })

        events.sort(key=lambda e: e["timestamp"], reverse=True)
        return events

    # ------------------------------------------------------------------
    # Excel / CSV Import Wizard & Export
    # ------------------------------------------------------------------
    @staticmethod
    def _read_tabular_rows(file_path: str) -> Tuple[List[str], List[List[Any]]]:
        path = Path(file_path)
        ext = path.suffix.lower()
        if ext == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = list(csv.reader(fh))
            if not reader:
                return [], []
            headers = [str(h or f"Column {idx + 1}").strip() for idx, h in enumerate(reader[0])]
            rows = [r for r in reader[1:] if any(str(c or "").strip() for c in r)]
            return headers, rows

        if ext in (".xlsx", ".xlsm"):
            wb = openpyxl.load_workbook(str(path), data_only=True)
            ws = wb.active
            all_rows = list(ws.iter_rows(values_only=True))
            if not all_rows:
                return [], []
            headers = [str(h or f"Column {idx + 1}").strip() for idx, h in enumerate(all_rows[0])]
            rows = [list(r) for r in all_rows[1:] if r and any(r)]
            return headers, rows

        raise ValueError(f"Unsupported file format '{ext}'. Use .xlsx or .csv.")

    @staticmethod
    def suggest_column_mapping(headers: List[str]) -> Dict[int, str]:
        """Auto-map spreadsheet header names to CRM fields."""
        mapping: Dict[int, str] = {}
        for idx, h in enumerate(headers):
            key = re.sub(r"[^a-z0-9]", "", h.lower())
            mapping[idx] = _HEADER_AUTO_MAP.get(key, "ignore")
        return mapping

    @staticmethod
    def inspect_import_file(file_path: str, preview_rows: int = 10) -> Dict[str, Any]:
        headers, rows = StudentService._read_tabular_rows(file_path)
        return {
            "headers": headers,
            "preview_rows": rows[:preview_rows],
            "total_rows": len(rows),
            "suggested_mapping": StudentService.suggest_column_mapping(headers),
        }

    @staticmethod
    def import_students_with_mapping(
        db: Session,
        file_path: str,
        column_mapping: Dict[int, str],
        default_class_id: int,
        default_ay_id: int,
        default_section_id: Optional[int] = None,
        duplicate_policy: str = "skip",  # "skip" or "error"
        current_username: str = "admin",
    ) -> Dict[str, Any]:
        """
        Import CSV/Excel records using explicit column mapping (`col_index -> crm_field`),
        strictly preventing duplicate students across every row.
        """
        headers, rows = StudentService._read_tabular_rows(file_path)
        imported = 0
        skipped = 0
        errors: List[str] = []

        for row_idx, row in enumerate(rows, start=2):
            row_vals: Dict[str, Any] = {}
            for col_idx, target_field in column_mapping.items():
                if not target_field or target_field == "ignore":
                    continue
                if col_idx < len(row):
                    val = row[col_idx]
                    if val is not None and str(val).strip() != "":
                        row_vals[target_field] = val

            if not row_vals:
                continue

            try:
                # Split full_name if first/last missing
                fname = str(row_vals.get("first_name", "")).strip()
                lname = str(row_vals.get("last_name", "")).strip()
                if (not fname or not lname) and row_vals.get("full_name"):
                    parts = str(row_vals["full_name"]).strip().split(None, 1)
                    fname = fname or parts[0]
                    lname = lname or (parts[1] if len(parts) > 1 else "-")

                if not fname:
                    raise ValueError("Missing student first name / full name.")
                lname = lname or "-"

                raw_roll = row_vals.get("roll_number")
                try:
                    roll = int(float(str(raw_roll).strip())) if raw_roll is not None else row_idx
                except ValueError:
                    raise ValueError(f"Invalid roll number '{raw_roll}'.")

                dob = _parse_date_flexible(row_vals.get("date_of_birth"), fallback=date(2010, 1, 1))
                gender = str(row_vals.get("gender") or "Male").strip().title()
                if gender not in ("Male", "Female", "Other"):
                    gender = "Male"

                g_name = str(row_vals.get("guardian_name") or f"Guardian of {fname}").strip()
                g_phone = str(row_vals.get("guardian_phone") or "+880 1700-000000").strip()

                tags_raw = str(row_vals.get("tags") or "")
                tag_list = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else None

                stu_payload: Dict[str, Any] = {
                    "student_id": str(row_vals["student_id"]).strip() if row_vals.get("student_id") else None,
                    "admission_number": (
                        str(row_vals["admission_number"]).strip()
                        if row_vals.get("admission_number")
                        else None
                    ),
                    "birth_certificate_no": (
                        str(row_vals["birth_certificate_no"]).strip()
                        if row_vals.get("birth_certificate_no")
                        else None
                    ),
                    "roll_number": roll,
                    "first_name": fname,
                    "last_name": lname,
                    "gender": gender,
                    "date_of_birth": dob,
                    "blood_group": str(row_vals["blood_group"]).strip() if row_vals.get("blood_group") else None,
                    "phone": str(row_vals["phone"]).strip() if row_vals.get("phone") else None,
                    "email": str(row_vals["email"]).strip() if row_vals.get("email") else None,
                    "address": str(row_vals["address"]).strip() if row_vals.get("address") else None,
                    "previous_school": (
                        str(row_vals["previous_school"]).strip() if row_vals.get("previous_school") else None
                    ),
                    "emergency_contact": (
                        str(row_vals["emergency_contact"]).strip()
                        if row_vals.get("emergency_contact")
                        else None
                    ),
                    "class_id": default_class_id,
                    "section_id": default_section_id,
                    "academic_year_id": default_ay_id,
                    "status": StudentStatus.ACTIVE,
                }
                g_payload: Dict[str, Any] = {
                    "guardian_name": g_name,
                    "guardian_phone": g_phone,
                    "relation": str(row_vals.get("guardian_relation") or "Parent").strip(),
                    "father_name": str(row_vals["father_name"]).strip() if row_vals.get("father_name") else None,
                    "mother_name": str(row_vals["mother_name"]).strip() if row_vals.get("mother_name") else None,
                }

                # Check duplicate before calling admit_student to honor skip vs error policy cleanly
                dup_msg = DatabaseService.check_duplicate_student(
                    db,
                    student_id=stu_payload.get("student_id"),
                    admission_number=stu_payload.get("admission_number"),
                    birth_certificate_no=stu_payload.get("birth_certificate_no"),
                    full_name=f"{fname} {lname}".strip(),
                    date_of_birth=dob,
                    guardian_phone=g_phone,
                    student_phone=stu_payload.get("phone"),
                )
                if dup_msg:
                    if duplicate_policy == "skip":
                        skipped += 1
                        errors.append(f"Row {row_idx} (Skipped duplicate): {dup_msg}")
                        continue
                    errors.append(f"Row {row_idx}: {dup_msg}")
                    continue

                ok, _stu, msg = StudentService.admit_student(
                    db,
                    stu_payload,
                    g_payload,
                    current_username=current_username,
                    tags=tag_list,
                    admission_type="Batch Import",
                    copy_photo_file=False,
                )
                if ok:
                    imported += 1
                else:
                    errors.append(f"Row {row_idx}: {msg}")
            except Exception as exc:
                errors.append(f"Row {row_idx}: {str(exc)}")

        return {
            "total_rows": len(rows),
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
        }

    @staticmethod
    def export_students_to_excel(
        db: Session,
        file_path: str,
        class_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> bool:
        """Export students roster to .xlsx using openpyxl."""
        students, _ = StudentRepository.search_and_filter(
            db, class_id=class_id, status=status, per_page=10000
        )

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Student Directory"

        headers = [
            "Student ID", "Admission No", "Digital ID", "Roll", "Full Name", "Gender",
            "Class", "Section", "Academic Year", "Blood Group", "Date of Birth",
            "Phone", "Guardian Name", "Guardian Phone", "Tags", "Status",
        ]
        ws.append(headers)

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for stu in students:
            ws.append([
                stu.student_id,
                stu.admission_number,
                stu.digital_id_code or "-",
                stu.roll_number,
                stu.full_name,
                stu.gender,
                stu.school_class.name if stu.school_class else "-",
                stu.section.name if stu.section else "-",
                stu.academic_year.name if stu.academic_year else "-",
                stu.blood_group or "-",
                stu.date_of_birth.strftime("%Y-%m-%d") if stu.date_of_birth else "-",
                stu.phone or "-",
                stu.guardian.guardian_name if stu.guardian else "-",
                stu.guardian.guardian_phone if stu.guardian else "-",
                ", ".join(stu.get_tag_names()) or "-",
                stu.status.capitalize(),
            ])

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        wb.save(file_path)
        app_logger.info(f"Exported {len(students)} student records to Excel: {file_path}")
        return True

    @staticmethod
    def import_students_from_excel(
        db: Session,
        file_path: str,
        default_class_id: int,
        default_ay_id: int,
    ) -> Tuple[int, List[str]]:
        """
        Legacy positional .xlsx/.csv import preserving existing API:
        [Roll, First Name, Last Name, Gender, DOB (YYYY-MM-DD), Phone, Guardian Name, Guardian Phone]
        Enforces duplicate student checks per row.
        """
        positional_map: Dict[int, str] = {
            0: "roll_number",
            1: "first_name",
            2: "last_name",
            3: "gender",
            4: "date_of_birth",
            5: "phone",
            6: "guardian_name",
            7: "guardian_phone",
        }
        result = StudentService.import_students_with_mapping(
            db,
            file_path=file_path,
            column_mapping=positional_map,
            default_class_id=default_class_id,
            default_ay_id=default_ay_id,
            duplicate_policy="error",
        )
        return result["imported"], result["errors"]
