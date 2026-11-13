"""
EduManage Pro - Attendance Service Layer
Business logic for Student, Teacher, and Non-Teaching Staff Attendance,
Bulk/Individual Marking, Edit Audit Trails, Correction Approval Workflows,
HR Leave Integration, Date-Range/Monthly Excel Exports, Analytics, and
Optional Pluggable Capture (QR / RFID / Biometric / Face).
"""

from collections import defaultdict
from datetime import date, datetime, time as dt_time, timedelta
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from sqlalchemy.orm import Session, joinedload

from app.config.logging_config import app_logger
from app.models.academic import SchoolClass, Section
from app.models.activity import ActivityLog
from app.models.attendance import (
    AttendanceCorrectionRequest,
    AttendanceStatus,
    StaffAttendance,
    StudentAttendance,
    TeacherAttendance,
)
from app.models.base import utc_now
from app.models.staff import Department, EmployeeLeaveRequest, Staff, Teacher
from app.models.student import Student
from app.models.user import User
from app.repositories.attendance_repository import AttendanceRepository
from app.security.session import session as app_session
from app.services.attendance_integration import AttendanceIntegrationManager, ScanPayload
from app.services.database_service import DatabaseService


def _resolve_actor(actor_user: Optional[User], fallback_username: str = "admin") -> Tuple[Optional[User], str]:
    user = actor_user or app_session.current_user
    username = user.username if user else (fallback_username or "admin")
    return user, username


def _require_attendance_perm(perm_code: str, actor_user: Optional[User] = None) -> None:
    """Enforce RBAC when an authenticated user context is active."""
    user = actor_user or app_session.current_user
    if user is None:
        return  # Standalone unit tests or CLI batch jobs without GUI session
    if user.is_super_admin:
        return
    if actor_user is not None:
        if not actor_user.has_permission(perm_code):
            raise PermissionError(f"Permission denied: missing '{perm_code}'.")
    elif not app_session.has_permission(perm_code):
        raise PermissionError(f"Permission denied: missing '{perm_code}'.")


class AttendanceService:
    # ==================== MARKING & EDITING ====================
    @staticmethod
    def mark_student_attendance(
        db: Session,
        class_id: int,
        section_id: Optional[int],
        att_date: date,
        records: List[Dict[str, Any]],
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, str]:
        _require_attendance_perm("attendance.register.CREATE", actor_user)
        if att_date > date.today():
            return False, "Cannot record attendance for future dates."

        _, username = _resolve_actor(actor_user, current_user)
        try:
            saved_count = AttendanceRepository.save_bulk_student_attendance(
                db, records, marked_by=username
            )
        except ValueError as exc:
            db.rollback()
            return False, str(exc)

        present_count = sum(1 for r in records if AttendanceStatus.normalize(r.get("status", "Present")) == AttendanceStatus.PRESENT)
        absent_count = sum(1 for r in records if AttendanceStatus.normalize(r.get("status", "Present")) == AttendanceStatus.ABSENT)
        cls_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        cls_name = cls_obj.name if cls_obj else f"Class {class_id}"

        log = ActivityLog(
            user_id=DatabaseService.resolve_user_id(db, username),
            username=username,
            action="ATTENDANCE_MARKED",
            module="ATTENDANCE",
            description=(
                f"Recorded daily attendance for {cls_name} on {att_date.isoformat()} "
                f"({present_count} Present, {absent_count} Absent, {saved_count} total)"
            ),
            severity="INFO",
        )
        db.add(log)
        db.commit()

        app_logger.info(f"Attendance recorded for {cls_name} ({saved_count} records) by {username}")
        return True, f"Successfully recorded attendance for {saved_count} students."

    @staticmethod
    def mark_teacher_attendance(
        db: Session,
        att_date: date,
        records: List[Dict[str, Any]],
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, str]:
        _require_attendance_perm("attendance.register.CREATE", actor_user)
        if att_date > date.today():
            return False, "Cannot record faculty attendance for future dates."

        _, username = _resolve_actor(actor_user, current_user)
        try:
            saved_count = AttendanceRepository.save_bulk_teacher_attendance(
                db, records, marked_by=username
            )
        except ValueError as exc:
            db.rollback()
            return False, str(exc)

        present_count = sum(1 for r in records if AttendanceStatus.normalize(r.get("status", "Present")) == AttendanceStatus.PRESENT)
        absent_count = sum(1 for r in records if AttendanceStatus.normalize(r.get("status", "Present")) == AttendanceStatus.ABSENT)

        log = ActivityLog(
            user_id=DatabaseService.resolve_user_id(db, username),
            username=username,
            action="TEACHER_ATTENDANCE_MARKED",
            module="ATTENDANCE",
            description=(
                f"Recorded faculty attendance on {att_date.isoformat()} "
                f"({present_count} Present, {absent_count} Absent, {saved_count} total)"
            ),
            severity="INFO",
        )
        db.add(log)
        db.commit()

        app_logger.info(f"Faculty attendance saved ({saved_count} staff) by {username}")
        return True, f"Successfully recorded attendance for {saved_count} faculty members."

    @staticmethod
    def mark_staff_attendance(
        db: Session,
        att_date: date,
        records: List[Dict[str, Any]],
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, str]:
        _require_attendance_perm("attendance.register.CREATE", actor_user)
        if att_date > date.today():
            return False, "Cannot record staff attendance for future dates."

        _, username = _resolve_actor(actor_user, current_user)
        try:
            saved_count = AttendanceRepository.save_bulk_staff_attendance(
                db, records, marked_by=username
            )
        except ValueError as exc:
            db.rollback()
            return False, str(exc)

        present_count = sum(1 for r in records if AttendanceStatus.normalize(r.get("status", "Present")) == AttendanceStatus.PRESENT)
        absent_count = sum(1 for r in records if AttendanceStatus.normalize(r.get("status", "Present")) == AttendanceStatus.ABSENT)

        log = ActivityLog(
            user_id=DatabaseService.resolve_user_id(db, username),
            username=username,
            action="STAFF_ATTENDANCE_MARKED",
            module="ATTENDANCE",
            description=(
                f"Recorded non-teaching staff attendance on {att_date.isoformat()} "
                f"({present_count} Present, {absent_count} Absent, {saved_count} total)"
            ),
            severity="INFO",
        )
        db.add(log)
        db.commit()

        return True, f"Successfully recorded attendance for {saved_count} staff members."

    @staticmethod
    def mark_individual_attendance(
        db: Session,
        target_type: str,
        entity_pk: int,
        att_date: date,
        status: str,
        check_in_time: Optional[str] = None,
        check_out_time: Optional[str] = None,
        remarks: Optional[str] = None,
        excuse_reason: Optional[str] = None,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, str]:
        _require_attendance_perm("attendance.register.CREATE", actor_user)
        if att_date > date.today():
            return False, "Cannot record attendance for future dates."

        ttype = (target_type or "").strip().lower()
        norm_status = AttendanceStatus.normalize(status)
        _, username = _resolve_actor(actor_user, current_user)

        if ttype == "student":
            stu = db.query(Student).filter(Student.id == entity_pk, Student.is_deleted == False).first()
            if not stu:
                return False, "Student not found."
            return AttendanceService.mark_student_attendance(
                db,
                class_id=stu.class_id,
                section_id=stu.section_id,
                att_date=att_date,
                records=[
                    {
                        "student_id": stu.id,
                        "class_id": stu.class_id,
                        "section_id": stu.section_id,
                        "academic_year_id": stu.academic_year_id,
                        "date": att_date,
                        "status": norm_status,
                        "check_in_time": check_in_time,
                        "check_out_time": check_out_time,
                        "remarks": remarks,
                        "excuse_reason": excuse_reason,
                    }
                ],
                current_user=username,
                actor_user=actor_user,
            )

        if ttype == "teacher":
            tch = db.query(Teacher).filter(Teacher.id == entity_pk, Teacher.is_deleted == False).first()
            if not tch:
                return False, "Teacher not found."
            return AttendanceService.mark_teacher_attendance(
                db,
                att_date=att_date,
                records=[
                    {
                        "teacher_id": tch.id,
                        "date": att_date,
                        "status": norm_status,
                        "check_in_time": check_in_time,
                        "check_out_time": check_out_time,
                        "remarks": remarks,
                        "excuse_reason": excuse_reason,
                    }
                ],
                current_user=username,
                actor_user=actor_user,
            )

        if ttype == "staff":
            stf = db.query(Staff).filter(Staff.id == entity_pk, Staff.is_deleted == False).first()
            if not stf:
                return False, "Staff member not found."
            return AttendanceService.mark_staff_attendance(
                db,
                att_date=att_date,
                records=[
                    {
                        "staff_id": stf.id,
                        "date": att_date,
                        "status": norm_status,
                        "check_in_time": check_in_time,
                        "check_out_time": check_out_time,
                        "remarks": remarks,
                        "excuse_reason": excuse_reason,
                    }
                ],
                current_user=username,
                actor_user=actor_user,
            )

        return False, "target_type must be 'student', 'teacher', or 'staff'."

    @staticmethod
    def bulk_set_status(
        db: Session,
        target_type: str,
        att_date: date,
        status: str,
        class_id: Optional[int] = None,
        section_id: Optional[int] = None,
        department_id: Optional[int] = None,
        remarks: Optional[str] = None,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, str]:
        """Bulk mark all active Students (by class/section) or Teachers/Staff (by department)."""
        _require_attendance_perm("attendance.register.CREATE", actor_user)
        if att_date > date.today():
            return False, "Cannot record attendance for future dates."

        ttype = (target_type or "").strip().lower()
        norm_status = AttendanceStatus.normalize(status)
        _, username = _resolve_actor(actor_user, current_user)

        if ttype == "student":
            if not class_id:
                return False, "class_id is required for bulk student attendance."
            roster = AttendanceRepository.get_class_students_with_attendance(
                db, class_id=class_id, section_id=section_id, att_date=att_date
            )
            if not roster:
                return False, "No active students found for the selected class/section."
            payload = [
                {
                    "student_id": item["student"].id,
                    "class_id": item["student"].class_id,
                    "section_id": item["student"].section_id,
                    "academic_year_id": item["student"].academic_year_id,
                    "date": att_date,
                    "status": norm_status,
                    "check_in_time": "08:15 AM" if norm_status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE) else None,
                    "remarks": remarks if remarks is not None else item["remarks"],
                }
                for item in roster
            ]
            return AttendanceService.mark_student_attendance(
                db, class_id, section_id, att_date, payload, current_user=username, actor_user=actor_user
            )

        if ttype == "teacher":
            roster = AttendanceRepository.get_teachers_with_attendance(
                db, att_date=att_date, department_id=department_id
            )
            if not roster:
                return False, "No active teachers found."
            payload = [
                {
                    "teacher_id": item["teacher"].id,
                    "date": att_date,
                    "status": norm_status,
                    "check_in_time": "07:50 AM" if norm_status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE) else None,
                    "check_out_time": "03:15 PM" if norm_status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE) else None,
                    "remarks": remarks if remarks is not None else item["remarks"],
                }
                for item in roster
            ]
            return AttendanceService.mark_teacher_attendance(
                db, att_date, payload, current_user=username, actor_user=actor_user
            )

        if ttype == "staff":
            roster = AttendanceRepository.get_staff_with_attendance(
                db, att_date=att_date, department_id=department_id
            )
            if not roster:
                return False, "No active staff members found."
            payload = [
                {
                    "staff_id": item["staff"].id,
                    "date": att_date,
                    "status": norm_status,
                    "check_in_time": "08:00 AM" if norm_status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE) else None,
                    "check_out_time": "04:00 PM" if norm_status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE) else None,
                    "remarks": remarks if remarks is not None else item["remarks"],
                }
                for item in roster
            ]
            return AttendanceService.mark_staff_attendance(
                db, att_date, payload, current_user=username, actor_user=actor_user
            )

        return False, "target_type must be 'student', 'teacher', or 'staff'."

    @staticmethod
    def edit_attendance_record(
        db: Session,
        target_type: str,
        attendance_id: int,
        new_status: str,
        check_in_time: Optional[str] = None,
        check_out_time: Optional[str] = None,
        remarks: Optional[str] = None,
        excuse_reason: Optional[str] = None,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, str]:
        _require_attendance_perm("attendance.register.EDIT", actor_user)
        ttype = (target_type or "").strip().lower()
        norm_status = AttendanceStatus.normalize(new_status)
        _, username = _resolve_actor(actor_user, current_user)

        model_cls = {
            "student": StudentAttendance,
            "teacher": TeacherAttendance,
            "staff": StaffAttendance,
        }.get(ttype)
        if not model_cls:
            return False, "target_type must be 'student', 'teacher', or 'staff'."

        row = db.query(model_cls).filter(model_cls.id == attendance_id).first()
        if not row:
            return False, "Attendance record not found."

        prev_status = row.status
        row.status = norm_status
        if check_in_time is not None:
            row.check_in_time = check_in_time
        if check_out_time is not None:
            row.check_out_time = check_out_time
        if remarks is not None:
            row.remarks = remarks
        if excuse_reason is not None:
            row.excuse_reason = excuse_reason
        row.is_edited = True
        row.edited_by = username
        row.edited_at = utc_now()

        db.add(
            ActivityLog(
                user_id=DatabaseService.resolve_user_id(db, username),
                username=username,
                action="ATTENDANCE_EDITED",
                module="ATTENDANCE",
                entity_type=ttype.capitalize(),
                entity_id=str(attendance_id),
                description=f"Edited {ttype} attendance #{attendance_id} ({row.date}): '{prev_status}' -> '{norm_status}'",
                severity="INFO",
            )
        )
        db.commit()
        return True, f"Attendance updated from '{prev_status}' to '{norm_status}'."

    # ==================== CORRECTION REQUEST & APPROVAL WORKFLOW ====================
    @staticmethod
    def submit_correction_request(
        db: Session,
        target_type: str,
        entity_pk: int,
        att_date: date,
        requested_status: str,
        reason: str,
        requested_check_in: Optional[str] = None,
        requested_check_out: Optional[str] = None,
        supporting_doc: Optional[str] = None,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[AttendanceCorrectionRequest], str]:
        _require_attendance_perm("attendance.corrections.CREATE", actor_user)
        ttype = (target_type or "").strip().lower()
        if ttype not in ("student", "teacher", "staff"):
            return False, None, "target_type must be 'student', 'teacher', or 'staff'."
        if att_date > date.today():
            return False, None, "Cannot submit a correction request for a future date."
        clean_reason = (reason or "").strip()
        if not clean_reason:
            return False, None, "A correction reason is required."

        norm_status = AttendanceStatus.normalize(requested_status)
        _, username = _resolve_actor(actor_user, current_user)

        existing_att = None
        if ttype == "student":
            subj = db.query(Student).filter(Student.id == entity_pk, Student.is_deleted == False).first()
            if not subj:
                return False, None, "Student not found."
            existing_att = (
                db.query(StudentAttendance)
                .filter(StudentAttendance.student_id == entity_pk, StudentAttendance.date == att_date)
                .first()
            )
        elif ttype == "teacher":
            subj = db.query(Teacher).filter(Teacher.id == entity_pk, Teacher.is_deleted == False).first()
            if not subj:
                return False, None, "Teacher not found."
            existing_att = (
                db.query(TeacherAttendance)
                .filter(TeacherAttendance.teacher_id == entity_pk, TeacherAttendance.date == att_date)
                .first()
            )
        else:
            subj = db.query(Staff).filter(Staff.id == entity_pk, Staff.is_deleted == False).first()
            if not subj:
                return False, None, "Staff member not found."
            existing_att = (
                db.query(StaffAttendance)
                .filter(StaffAttendance.staff_id == entity_pk, StaffAttendance.date == att_date)
                .first()
            )

        req = AttendanceCorrectionRequest(
            target_type=ttype,
            student_id=entity_pk if ttype == "student" else None,
            teacher_id=entity_pk if ttype == "teacher" else None,
            staff_id=entity_pk if ttype == "staff" else None,
            student_attendance_id=existing_att.id if (ttype == "student" and existing_att) else None,
            teacher_attendance_id=existing_att.id if (ttype == "teacher" and existing_att) else None,
            staff_attendance_id=existing_att.id if (ttype == "staff" and existing_att) else None,
            attendance_date=att_date,
            original_status=existing_att.status if existing_att else "Unmarked",
            requested_status=norm_status,
            requested_check_in=requested_check_in,
            requested_check_out=requested_check_out,
            reason=clean_reason,
            supporting_doc=supporting_doc,
            approval_status="Pending",
            requested_by=username,
            requested_at=utc_now(),
        )
        db.add(req)
        db.flush()

        db.add(
            ActivityLog(
                user_id=DatabaseService.resolve_user_id(db, username),
                username=username,
                action="ATTENDANCE_CORRECTION_SUBMITTED",
                module="ATTENDANCE",
                entity_type=ttype.capitalize(),
                entity_id=str(entity_pk),
                description=(
                    f"Submitted correction #{req.id} for {subj.full_name} on {att_date.isoformat()}: "
                    f"'{req.original_status}' -> '{norm_status}'"
                ),
                severity="INFO",
            )
        )
        db.commit()
        db.refresh(req)
        return True, req, f"Correction request #{req.id} submitted for approval."

    @staticmethod
    def review_correction_request(
        db: Session,
        request_id: int,
        approve: bool,
        review_notes: str = "",
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[AttendanceCorrectionRequest], str]:
        _require_attendance_perm("attendance.corrections.APPROVE", actor_user)
        req = db.query(AttendanceCorrectionRequest).filter_by(id=request_id).first()
        if not req:
            return False, None, "Correction request not found."
        if req.approval_status != "Pending":
            return False, req, f"Correction request #{req.id} is already '{req.approval_status}'."

        _, username = _resolve_actor(actor_user, current_user)
        now_ts = utc_now()
        req.reviewed_by = username
        req.reviewed_at = now_ts
        req.review_notes = (review_notes or ("Approved" if approve else "Rejected")).strip()

        if not approve:
            req.approval_status = "Rejected"
            db.add(
                ActivityLog(
                    user_id=DatabaseService.resolve_user_id(db, username),
                    username=username,
                    action="ATTENDANCE_CORRECTION_REJECTED",
                    module="ATTENDANCE",
                    description=f"Rejected correction #{req.id} ({req.target_type}, {req.attendance_date}): {req.review_notes}",
                    severity="INFO",
                )
            )
            db.commit()
            db.refresh(req)
            return True, req, f"Correction request #{req.id} rejected."

        # Approve and apply atomically to the underlying attendance table
        req.approval_status = "Approved"
        note_text = f"Correction Approved (#{req.id}): {req.reason}"[:255]

        if req.target_type == "student" and req.student_id:
            stu = db.query(Student).filter_by(id=req.student_id).first()
            if not stu:
                db.rollback()
                return False, None, "Target student no longer exists."
            att = (
                db.query(StudentAttendance)
                .filter(StudentAttendance.student_id == stu.id, StudentAttendance.date == req.attendance_date)
                .first()
            )
            if att:
                att.status = req.requested_status
                if req.requested_check_in is not None:
                    att.check_in_time = req.requested_check_in
                if req.requested_check_out is not None:
                    att.check_out_time = req.requested_check_out
                att.remarks = note_text
                if req.requested_status == AttendanceStatus.EXCUSED:
                    att.excuse_reason = req.reason[:255]
                att.capture_source = "Correction"
                att.is_edited = True
                att.edited_by = username
                att.edited_at = now_ts
            else:
                att = StudentAttendance(
                    student_id=stu.id,
                    class_id=stu.class_id,
                    section_id=stu.section_id,
                    academic_year_id=stu.academic_year_id,
                    date=req.attendance_date,
                    status=req.requested_status,
                    check_in_time=req.requested_check_in,
                    check_out_time=req.requested_check_out,
                    remarks=note_text,
                    excuse_reason=req.reason[:255] if req.requested_status == AttendanceStatus.EXCUSED else None,
                    marked_by=username,
                    capture_source="Correction",
                    is_edited=True,
                    edited_by=username,
                    edited_at=now_ts,
                )
                db.add(att)
                db.flush()
            req.student_attendance_id = att.id

        elif req.target_type == "teacher" and req.teacher_id:
            att = (
                db.query(TeacherAttendance)
                .filter(TeacherAttendance.teacher_id == req.teacher_id, TeacherAttendance.date == req.attendance_date)
                .first()
            )
            if att:
                att.status = req.requested_status
                if req.requested_check_in is not None:
                    att.check_in_time = req.requested_check_in
                if req.requested_check_out is not None:
                    att.check_out_time = req.requested_check_out
                att.remarks = note_text
                if req.requested_status == AttendanceStatus.EXCUSED:
                    att.excuse_reason = req.reason[:255]
                att.capture_source = "Correction"
                att.is_edited = True
                att.edited_by = username
                att.edited_at = now_ts
            else:
                att = TeacherAttendance(
                    teacher_id=req.teacher_id,
                    date=req.attendance_date,
                    status=req.requested_status,
                    check_in_time=req.requested_check_in,
                    check_out_time=req.requested_check_out,
                    remarks=note_text,
                    excuse_reason=req.reason[:255] if req.requested_status == AttendanceStatus.EXCUSED else None,
                    marked_by=username,
                    capture_source="Correction",
                    is_edited=True,
                    edited_by=username,
                    edited_at=now_ts,
                )
                db.add(att)
                db.flush()
            req.teacher_attendance_id = att.id

        elif req.target_type == "staff" and req.staff_id:
            att = (
                db.query(StaffAttendance)
                .filter(StaffAttendance.staff_id == req.staff_id, StaffAttendance.date == req.attendance_date)
                .first()
            )
            if att:
                att.status = req.requested_status
                if req.requested_check_in is not None:
                    att.check_in_time = req.requested_check_in
                if req.requested_check_out is not None:
                    att.check_out_time = req.requested_check_out
                att.remarks = note_text
                if req.requested_status == AttendanceStatus.EXCUSED:
                    att.excuse_reason = req.reason[:255]
                att.capture_source = "Correction"
                att.is_edited = True
                att.edited_by = username
                att.edited_at = now_ts
            else:
                att = StaffAttendance(
                    staff_id=req.staff_id,
                    date=req.attendance_date,
                    status=req.requested_status,
                    check_in_time=req.requested_check_in,
                    check_out_time=req.requested_check_out,
                    remarks=note_text,
                    excuse_reason=req.reason[:255] if req.requested_status == AttendanceStatus.EXCUSED else None,
                    marked_by=username,
                    capture_source="Correction",
                    is_edited=True,
                    edited_by=username,
                    edited_at=now_ts,
                )
                db.add(att)
                db.flush()
            req.staff_attendance_id = att.id

        db.add(
            ActivityLog(
                user_id=DatabaseService.resolve_user_id(db, username),
                username=username,
                action="ATTENDANCE_CORRECTION_APPROVED",
                module="ATTENDANCE",
                description=(
                    f"Approved correction #{req.id} ({req.target_type}, {req.attendance_date}): "
                    f"'{req.original_status}' -> '{req.requested_status}'"
                ),
                severity="INFO",
            )
        )
        db.commit()
        db.refresh(req)
        return True, req, f"Correction request #{req.id} approved and attendance updated to '{req.requested_status}'."

    # ==================== HR LEAVE INTEGRATION ====================
    @staticmethod
    def sync_approved_hr_leaves_to_attendance(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, int, str]:
        """
        Synchronizes Approved HR EmployeeLeaveRequest entries into TeacherAttendance and StaffAttendance
        within [start_date, end_date] (defaulting to current month up to today).
        """
        _require_attendance_perm("attendance.register.CREATE", actor_user)
        today = date.today()
        s_date = start_date or date(today.year, today.month, 1)
        e_date = min(end_date or today, today)
        if s_date > e_date:
            return True, 0, "No past/current dates in selected range to sync."

        _, username = _resolve_actor(actor_user, current_user)
        leaves = (
            db.query(EmployeeLeaveRequest)
            .filter(
                EmployeeLeaveRequest.status == "Approved",
                EmployeeLeaveRequest.start_date <= e_date,
                EmployeeLeaveRequest.end_date >= s_date,
            )
            .all()
        )

        synced = 0
        for lv in leaves:
            cur = max(lv.start_date, s_date)
            stop = min(lv.end_date, e_date)
            remark_txt = f"{lv.leave_type} Leave (HR Approved #{lv.id})"
            while cur <= stop:
                if lv.employee_type == "teacher" and lv.teacher_id:
                    existing = (
                        db.query(TeacherAttendance)
                        .filter(TeacherAttendance.teacher_id == lv.teacher_id, TeacherAttendance.date == cur)
                        .first()
                    )
                    if not existing:
                        db.add(
                            TeacherAttendance(
                                teacher_id=lv.teacher_id,
                                date=cur,
                                status=AttendanceStatus.LEAVE,
                                remarks=remark_txt,
                                marked_by=username,
                                capture_source="LeaveSync",
                                leave_request_id=lv.id,
                            )
                        )
                        synced += 1
                    elif existing.capture_source == "LeaveSync" and existing.status != AttendanceStatus.LEAVE:
                        existing.status = AttendanceStatus.LEAVE
                        existing.remarks = remark_txt
                        existing.leave_request_id = lv.id
                        synced += 1
                elif lv.employee_type == "staff" and lv.staff_id:
                    existing = (
                        db.query(StaffAttendance)
                        .filter(StaffAttendance.staff_id == lv.staff_id, StaffAttendance.date == cur)
                        .first()
                    )
                    if not existing:
                        db.add(
                            StaffAttendance(
                                staff_id=lv.staff_id,
                                date=cur,
                                status=AttendanceStatus.LEAVE,
                                remarks=remark_txt,
                                marked_by=username,
                                capture_source="LeaveSync",
                                leave_request_id=lv.id,
                            )
                        )
                        synced += 1
                    elif existing.capture_source == "LeaveSync" and existing.status != AttendanceStatus.LEAVE:
                        existing.status = AttendanceStatus.LEAVE
                        existing.remarks = remark_txt
                        existing.leave_request_id = lv.id
                        synced += 1
                cur += timedelta(days=1)

        if synced > 0:
            db.add(
                ActivityLog(
                    user_id=DatabaseService.resolve_user_id(db, username),
                    username=username,
                    action="HR_LEAVE_ATTENDANCE_SYNC",
                    module="ATTENDANCE",
                    description=f"Synced {synced} approved HR leave day(s) ({s_date} to {e_date}) into attendance registers.",
                    severity="INFO",
                )
            )
        db.commit()
        return True, synced, f"Synchronized {synced} approved HR leave record(s) into attendance."

    # ==================== PERCENTAGE & REPORTING ====================
    @staticmethod
    def calculate_attendance_percentage(
        present: int,
        absent: int,
        late: int = 0,
        leave: int = 0,
        excused: int = 0,
        include_late_as_present: bool = False,
        include_excused_as_present: bool = False,
    ) -> float:
        total = present + absent + late + leave + excused
        if total <= 0:
            return 0.0
        credit = present + (late if include_late_as_present else 0) + (excused if include_excused_as_present else 0)
        return round((credit / total) * 100.0, 1)

    @staticmethod
    def get_date_range_report(
        db: Session,
        target_type: str,
        start_date: date,
        end_date: date,
        class_id: Optional[int] = None,
        section_id: Optional[int] = None,
        department_id: Optional[int] = None,
        entity_pk: Optional[int] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        ttype = (target_type or "student").strip().lower()
        if ttype == "student":
            rows = AttendanceRepository.get_student_attendance_range(
                db, start_date, end_date, class_id=class_id, section_id=section_id, student_id=entity_pk, status=status
            )
        elif ttype in ("teacher", "staff"):
            rows = AttendanceRepository.get_employee_attendance_range(
                db, ttype, start_date, end_date, department_id=department_id, employee_pk=entity_pk, status=status
            )
        else:
            raise ValueError("target_type must be 'student', 'teacher', or 'staff'.")

        counts = {s: 0 for s in AttendanceStatus.ALL}
        for r in rows:
            if r.status in counts:
                counts[r.status] += 1
        total = len(rows)
        return {
            "target_type": ttype,
            "start_date": start_date,
            "end_date": end_date,
            "records": rows,
            "total": total,
            "present": counts[AttendanceStatus.PRESENT],
            "absent": counts[AttendanceStatus.ABSENT],
            "late": counts[AttendanceStatus.LATE],
            "leave": counts[AttendanceStatus.LEAVE],
            "excused": counts[AttendanceStatus.EXCUSED],
            "percentage": AttendanceService.calculate_attendance_percentage(
                counts[AttendanceStatus.PRESENT],
                counts[AttendanceStatus.ABSENT],
                counts[AttendanceStatus.LATE],
                counts[AttendanceStatus.LEAVE],
                counts[AttendanceStatus.EXCUSED],
            ),
            "effective_percentage": AttendanceService.calculate_attendance_percentage(
                counts[AttendanceStatus.PRESENT],
                counts[AttendanceStatus.ABSENT],
                counts[AttendanceStatus.LATE],
                counts[AttendanceStatus.LEAVE],
                counts[AttendanceStatus.EXCUSED],
                include_late_as_present=True,
                include_excused_as_present=True,
            ),
        }

    # ==================== ANALYTICS ENGINE ====================
    @staticmethod
    def get_attendance_analytics(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        class_id: Optional[int] = None,
        section_id: Optional[int] = None,
        department_id: Optional[int] = None,
        chronic_threshold_pct: float = 75.0,
    ) -> Dict[str, Any]:
        _require_attendance_perm("attendance.analytics.VIEW")
        today = date.today()
        e_date = end_date or today
        s_date = start_date or (e_date - timedelta(days=29))

        # Student records in range
        stu_q = (
            db.query(StudentAttendance)
            .options(joinedload(StudentAttendance.student), joinedload(StudentAttendance.school_class))
            .filter(StudentAttendance.date >= s_date, StudentAttendance.date <= e_date)
        )
        if class_id:
            stu_q = stu_q.filter(StudentAttendance.class_id == class_id)
        if section_id:
            stu_q = stu_q.filter(StudentAttendance.section_id == section_id)
        stu_rows = stu_q.all()

        # Teacher records in range
        tch_q = (
            db.query(TeacherAttendance)
            .options(joinedload(TeacherAttendance.teacher).joinedload(Teacher.department))
            .filter(TeacherAttendance.date >= s_date, TeacherAttendance.date <= e_date)
        )
        if department_id:
            tch_q = tch_q.join(Teacher).filter(Teacher.department_id == department_id)
        tch_rows = tch_q.all()

        # Staff records in range
        stf_q = (
            db.query(StaffAttendance)
            .options(joinedload(StaffAttendance.staff).joinedload(Staff.department))
            .filter(StaffAttendance.date >= s_date, StaffAttendance.date <= e_date)
        )
        if department_id:
            stf_q = stf_q.join(Staff).filter(Staff.department_id == department_id)
        stf_rows = stf_q.all()

        def _summarize(rows: List[Any]) -> Dict[str, Any]:
            c = {s: 0 for s in AttendanceStatus.ALL}
            for r in rows:
                if r.status in c:
                    c[r.status] += 1
            tot = sum(c.values())
            pct = AttendanceService.calculate_attendance_percentage(
                c[AttendanceStatus.PRESENT],
                c[AttendanceStatus.ABSENT],
                c[AttendanceStatus.LATE],
                c[AttendanceStatus.LEAVE],
                c[AttendanceStatus.EXCUSED],
            )
            eff = AttendanceService.calculate_attendance_percentage(
                c[AttendanceStatus.PRESENT],
                c[AttendanceStatus.ABSENT],
                c[AttendanceStatus.LATE],
                c[AttendanceStatus.LEAVE],
                c[AttendanceStatus.EXCUSED],
                include_late_as_present=True,
                include_excused_as_present=True,
            )
            return {
                "total": tot,
                "present": c[AttendanceStatus.PRESENT],
                "absent": c[AttendanceStatus.ABSENT],
                "late": c[AttendanceStatus.LATE],
                "leave": c[AttendanceStatus.LEAVE],
                "excused": c[AttendanceStatus.EXCUSED],
                "attendance_rate": pct,
                "effective_rate": eff,
            }

        stu_summary = _summarize(stu_rows)
        tch_summary = _summarize(tch_rows)
        stf_summary = _summarize(stf_rows)
        all_rows = stu_rows + tch_rows + stf_rows
        overall_summary = _summarize(all_rows)

        # Capture source breakdown
        source_breakdown: Dict[str, int] = defaultdict(int)
        for r in all_rows:
            source_breakdown[getattr(r, "capture_source", None) or "Manual"] += 1

        # Class breakdown
        cls_buckets: Dict[str, List[StudentAttendance]] = defaultdict(list)
        for r in stu_rows:
            cls_name = r.school_class.name if r.school_class else f"Class {r.class_id}"
            cls_buckets[cls_name].append(r)
        class_breakdown = [
            {"class_name": cname, **_summarize(crows)}
            for cname, crows in sorted(cls_buckets.items())
        ]

        # Department breakdown (Teachers + Staff)
        dept_buckets: Dict[str, List[Any]] = defaultdict(list)
        for r in tch_rows:
            dname = r.teacher.department.name if (r.teacher and r.teacher.department) else "Unassigned"
            dept_buckets[dname].append(r)
        for r in stf_rows:
            dname = r.staff.department.name if (r.staff and r.staff.department) else "Support / Admin"
            dept_buckets[dname].append(r)
        department_breakdown = [
            {"department_name": dname, **_summarize(drows)}
            for dname, drows in sorted(dept_buckets.items())
        ]

        # Daily Trend
        stu_by_day: Dict[date, List[StudentAttendance]] = defaultdict(list)
        tch_by_day: Dict[date, List[TeacherAttendance]] = defaultdict(list)
        stf_by_day: Dict[date, List[StaffAttendance]] = defaultdict(list)
        for r in stu_rows:
            stu_by_day[r.date].append(r)
        for r in tch_rows:
            tch_by_day[r.date].append(r)
        for r in stf_rows:
            stf_by_day[r.date].append(r)

        active_dates = sorted(set(stu_by_day.keys()) | set(tch_by_day.keys()) | set(stf_by_day.keys()))
        daily_trend = []
        for d in active_dates:
            ss = _summarize(stu_by_day[d])
            ts = _summarize(tch_by_day[d])
            fs = _summarize(stf_by_day[d])
            daily_trend.append(
                {
                    "date": d.isoformat(),
                    "student_marked": ss["total"],
                    "student_rate": ss["attendance_rate"],
                    "teacher_marked": ts["total"],
                    "teacher_rate": ts["attendance_rate"],
                    "staff_marked": fs["total"],
                    "staff_rate": fs["attendance_rate"],
                }
            )

        # Chronic absenteeism / low attendance alerts
        stu_person_buckets: Dict[int, List[StudentAttendance]] = defaultdict(list)
        for r in stu_rows:
            stu_person_buckets[r.student_id].append(r)
        chronic_absentee_students = []
        for sid, srows in stu_person_buckets.items():
            sm = _summarize(srows)
            if sm["total"] > 0 and sm["attendance_rate"] < chronic_threshold_pct:
                stu_obj = srows[0].student
                chronic_absentee_students.append(
                    {
                        "student_id": sid,
                        "student_code": stu_obj.student_id if stu_obj else str(sid),
                        "full_name": stu_obj.full_name if stu_obj else f"Student #{sid}",
                        "class_name": srows[0].school_class.name if srows[0].school_class else "-",
                        **sm,
                    }
                )
        chronic_absentee_students.sort(key=lambda x: x["attendance_rate"])

        emp_alerts = []
        tch_buckets: Dict[int, List[TeacherAttendance]] = defaultdict(list)
        for r in tch_rows:
            tch_buckets[r.teacher_id].append(r)
        for tid, trows in tch_buckets.items():
            sm = _summarize(trows)
            if sm["total"] > 0 and sm["attendance_rate"] < chronic_threshold_pct:
                t_obj = trows[0].teacher
                emp_alerts.append(
                    {
                        "employee_type": "teacher",
                        "employee_id": t_obj.employee_id if t_obj else str(tid),
                        "full_name": t_obj.full_name if t_obj else f"Teacher #{tid}",
                        "department": t_obj.department.name if (t_obj and t_obj.department) else "-",
                        **sm,
                    }
                )
        stf_buckets: Dict[int, List[StaffAttendance]] = defaultdict(list)
        for r in stf_rows:
            stf_buckets[r.staff_id].append(r)
        for fid, frows in stf_buckets.items():
            sm = _summarize(frows)
            if sm["total"] > 0 and sm["attendance_rate"] < chronic_threshold_pct:
                s_obj = frows[0].staff
                emp_alerts.append(
                    {
                        "employee_type": "staff",
                        "employee_id": s_obj.employee_id if s_obj else str(fid),
                        "full_name": s_obj.full_name if s_obj else f"Staff #{fid}",
                        "department": s_obj.department.name if (s_obj and s_obj.department) else "-",
                        **sm,
                    }
                )
        emp_alerts.sort(key=lambda x: x["attendance_rate"])

        pending_corrections = (
            db.query(AttendanceCorrectionRequest)
            .filter(AttendanceCorrectionRequest.approval_status == "Pending")
            .count()
        )

        return {
            "period": {"start_date": s_date.isoformat(), "end_date": e_date.isoformat()},
            "threshold_pct": chronic_threshold_pct,
            "overall": overall_summary,
            "students": stu_summary,
            "teachers": tch_summary,
            "staff": stf_summary,
            "status_breakdown": {
                s: overall_summary[s.lower()] for s in AttendanceStatus.ALL
            },
            "source_breakdown": dict(source_breakdown),
            "class_breakdown": class_breakdown,
            "department_breakdown": department_breakdown,
            "daily_trend": daily_trend,
            "chronic_absentee_students": chronic_absentee_students,
            "at_risk_employees": emp_alerts,
            "pending_corrections": pending_corrections,
        }

    # ==================== OPTIONAL SCAN / HARDWARE INTEGRATION PROXIES ====================
    @staticmethod
    def process_scan_event(
        db: Session,
        adapter_type: str,
        raw_identifier: str,
        device_code: Optional[str] = None,
        direction: str = "CHECK_IN",
        scan_timestamp: Optional[datetime] = None,
        confidence_score: Optional[float] = None,
        late_cutoff: dt_time = dt_time(8, 30),
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        _require_attendance_perm("attendance.register.CREATE", actor_user)
        _, username = _resolve_actor(actor_user, "scan_gateway")
        payload = ScanPayload(
            adapter_type=adapter_type,
            raw_identifier=raw_identifier,
            device_code=device_code,
            direction=direction,
            scan_timestamp=scan_timestamp,
            confidence_score=confidence_score,
        )
        return AttendanceIntegrationManager.ingest_scan(
            db, payload, late_cutoff=late_cutoff, actor=username
        )

    @staticmethod
    def register_capture_device(
        db: Session,
        device_code: str,
        name: str,
        adapter_type: str,
        connection_mode: str = "Simulated",
        endpoint_or_port: Optional[str] = None,
        location: Optional[str] = None,
        is_enabled: bool = True,
        config: Optional[Dict[str, Any]] = None,
        actor_user: Optional[User] = None,
    ):
        _require_attendance_perm("attendance.devices.MANAGE", actor_user)
        return AttendanceIntegrationManager.register_device(
            db,
            device_code=device_code,
            name=name,
            adapter_type=adapter_type,
            connection_mode=connection_mode,
            endpoint_or_port=endpoint_or_port,
            location=location,
            is_enabled=is_enabled,
            config=config,
        )

    @staticmethod
    def bind_capture_credential(
        db: Session,
        subject_type: str,
        subject_pk: int,
        qr_code_value: Optional[str] = None,
        rfid_uid: Optional[str] = None,
        biometric_template_id: Optional[str] = None,
        face_profile_id: Optional[str] = None,
        notes: Optional[str] = None,
        actor_user: Optional[User] = None,
    ):
        _require_attendance_perm("attendance.devices.EDIT", actor_user)
        return AttendanceIntegrationManager.bind_credential(
            db,
            subject_type=subject_type,
            subject_pk=subject_pk,
            qr_code_value=qr_code_value,
            rfid_uid=rfid_uid,
            biometric_template_id=biometric_template_id,
            face_profile_id=face_profile_id,
            notes=notes,
        )

    # ==================== EXCEL EXPORTS ====================
    @staticmethod
    def export_monthly_register_excel(
        db: Session,
        class_id: int,
        year: int,
        month: int,
        output_file_path: str,
        section_id: Optional[int] = None,
    ) -> str:
        """
        Exports monthly student class attendance register as a stylized Excel workbook (.xlsx).
        Supports all 5 statuses: Present (P), Absent (A), Late (L), Leave (Lv), Excused (Ex).
        """
        data = AttendanceRepository.get_monthly_student_register(db, class_id, year, month, section_id)
        days_count = data["days_count"]
        register = data["register"]

        cls_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        class_name = cls_obj.name if cls_obj else f"Class {class_id}"

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Attendance_{month}_{year}"

        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=days_count + 7)
        title_cell = ws.cell(row=1, column=1)
        title_cell.value = f"MONTHLY ATTENDANCE REGISTER — {class_name.upper()} ({month:02d}/{year})"
        title_cell.font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 30

        headers = (
            ["Roll", "Student ID", "Student Name"]
            + [str(d) for d in range(1, days_count + 1)]
            + ["P", "A", "L/Lv", "Ex", "%"]
        )
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")

        for col_idx, h_text in enumerate(headers, 1):
            cell = ws.cell(row=2, column=col_idx, value=h_text)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        ws.row_dimensions[2].height = 24

        green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
        red_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
        yellow_fill = PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid")
        blue_fill = PatternFill(start_color="E0E7FF", end_color="E0E7FF", fill_type="solid")
        teal_fill = PatternFill(start_color="CCFBF1", end_color="CCFBF1", fill_type="solid")

        thin_border = Border(
            left=Side(style="thin", color="D1D5DB"),
            right=Side(style="thin", color="D1D5DB"),
            top=Side(style="thin", color="D1D5DB"),
            bottom=Side(style="thin", color="D1D5DB"),
        )

        for row_idx, item in enumerate(register, 3):
            stu = item["student"]
            ws.cell(row=row_idx, column=1, value=stu.roll_number).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=2, value=stu.student_id).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=3, value=stu.full_name).alignment = Alignment(horizontal="left")

            for day in range(1, days_count + 1):
                st = item["days"].get(day, "-")
                short_code = AttendanceStatus.SHORT_CODES.get(st, "-")
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
                elif short_code == "Ex":
                    c.fill = teal_fill

            col_p = 3 + days_count + 1
            ws.cell(row=row_idx, column=col_p, value=item["present_count"]).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=col_p + 1, value=item["absent_count"]).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=col_p + 2, value=item["late_count"] + item["leave_count"]).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=col_p + 3, value=item.get("excused_count", 0)).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=col_p + 4, value=f"{item['percentage']}%").alignment = Alignment(horizontal="center")

        ws.column_dimensions["A"].width = 8
        ws.column_dimensions["B"].width = 16
        ws.column_dimensions["C"].width = 24
        for d in range(1, days_count + 1):
            col_letter = openpyxl.utils.get_column_letter(3 + d)
            ws.column_dimensions[col_letter].width = 4.5

        wb.save(output_file_path)
        return output_file_path

    @staticmethod
    def export_employee_monthly_register_excel(
        db: Session,
        target_type: str,
        year: int,
        month: int,
        output_file_path: str,
        department_id: Optional[int] = None,
    ) -> str:
        """Export monthly attendance register for Teachers or Non-Teaching Staff."""
        data = AttendanceRepository.get_monthly_employee_register(
            db, target_type=target_type, year=year, month=month, department_id=department_id
        )
        days_count = data["days_count"]
        register = data["register"]
        label = "FACULTY / TEACHERS" if data["employee_type"] == "teacher" else "NON-TEACHING STAFF"

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{data['employee_type'].capitalize()}_{month}_{year}"

        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=days_count + 8)
        title_cell = ws.cell(row=1, column=1)
        title_cell.value = f"MONTHLY ATTENDANCE REGISTER — {label} ({month:02d}/{year})"
        title_cell.font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 30

        headers = (
            ["Employee ID", "Full Name", "Department"]
            + [str(d) for d in range(1, days_count + 1)]
            + ["P", "A", "L", "Lv", "Ex", "%"]
        )
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        for col_idx, h_text in enumerate(headers, 1):
            cell = ws.cell(row=2, column=col_idx, value=h_text)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for row_idx, item in enumerate(register, 3):
            emp = item["employee"]
            ws.cell(row=row_idx, column=1, value=emp.employee_id)
            ws.cell(row=row_idx, column=2, value=emp.full_name)
            ws.cell(row=row_idx, column=3, value=emp.department.name if emp.department else "-")
            for day in range(1, days_count + 1):
                st = item["days"].get(day, "-")
                c = ws.cell(row=row_idx, column=3 + day, value=AttendanceStatus.SHORT_CODES.get(st, "-"))
                c.alignment = Alignment(horizontal="center")

            col_p = 3 + days_count + 1
            ws.cell(row=row_idx, column=col_p, value=item["present_count"])
            ws.cell(row=row_idx, column=col_p + 1, value=item["absent_count"])
            ws.cell(row=row_idx, column=col_p + 2, value=item["late_count"])
            ws.cell(row=row_idx, column=col_p + 3, value=item["leave_count"])
            ws.cell(row=row_idx, column=col_p + 4, value=item["excused_count"])
            ws.cell(row=row_idx, column=col_p + 5, value=f"{item['percentage']}%")

        wb.save(output_file_path)
        return output_file_path
