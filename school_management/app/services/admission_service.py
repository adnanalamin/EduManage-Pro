"""
EduManage Pro - Admission CRM Service Layer
Complete admissions pipeline:
- Application intake, Applicant IDs, duplicate prevention, 8 lifecycle statuses
- Configurable Admission Fee schedules & Applicant Fee Receipts
- Document checklist tracking & verification
- Admission Entrance Test scheduling, scoring & Admit Cards
- Interview scheduling & evaluation scoring
- Automated Merit List ranking, Seat Quota Selection & Waitlist promotion
- Principal Admission Approval & Atomic Conversion into Student CRM
- PDF generation (Admission Form, Applicant Receipt, Admit Card, Merit List)
- Excel (.xlsx / .csv) Import & Export + Admission Funnel Statistics
"""

import csv
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy.orm import Session, joinedload

from app.config.logging_config import app_logger
from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.activity import ActivityLog
from app.models.admission import (
    DEFAULT_CHECKLIST_ITEMS,
    AdmissionApplication,
    AdmissionDocumentChecklist,
    AdmissionFeeConfig,
    AdmissionFeePayment,
    AdmissionInterview,
    AdmissionStatus,
    AdmissionStatusHistory,
    AdmissionTestScore,
)
from app.models.base import utc_now
from app.models.school import SchoolSetting
from app.models.student import StudentDocument
from app.models.user import User
from app.reports.admission_pdf import AdmissionPDFGenerator
from app.repositories.admission_repository import AdmissionRepository
from app.security.session import session as app_session
from app.services.database_service import DatabaseService
from app.services.student_service import StudentService, _parse_date_flexible


def _resolve_actor(actor_user: Optional[User], fallback_username: str = "admin") -> Tuple[Optional[User], str]:
    user = actor_user or app_session.current_user
    username = user.username if user else (fallback_username or "admin")
    return user, username


def _require_adm_perm(perm_code: str, actor_user: Optional[User] = None) -> None:
    user = actor_user or app_session.current_user
    if user is None:
        return
    if user.is_super_admin:
        return
    if actor_user is not None:
        if not actor_user.has_permission(perm_code):
            raise PermissionError(f"Permission denied: missing '{perm_code}'.")
    elif not app_session.has_permission(perm_code):
        raise PermissionError(f"Permission denied: missing '{perm_code}'.")


def _get_school(db: Session) -> Dict[str, Any]:
    s = db.query(SchoolSetting).first()
    if s:
        return s
    return {
        "school_name": "EduManage Pro Model School",
        "eiin_number": "134211",
        "address": "Main Campus",
        "currency_symbol": "৳",
    }


class AdmissionService:
    @staticmethod
    def _log(
        db: Session,
        action: str,
        description: str,
        username: str = "admin",
        entity_id: Optional[int] = None,
        severity: str = "INFO",
    ) -> None:
        db.add(
            ActivityLog(
                user_id=DatabaseService.resolve_user_id(db, username),
                username=username,
                action=action,
                module="ADMISSIONS",
                entity_type="AdmissionApplication",
                entity_id=str(entity_id) if entity_id is not None else None,
                description=description,
                severity=severity,
            )
        )

    # ==================================================================
    # 1. CONFIGURABLE ADMISSION FEES & QUOTA SETTINGS
    # ==================================================================
    @staticmethod
    def configure_fee_schedule(
        db: Session,
        academic_year_id: int,
        class_id: Optional[int] = None,
        fee_name: str = "Standard Admission Fee Schedule",
        application_fee: float = 500.0,
        admission_test_fee: float = 300.0,
        enrollment_fee: float = 5000.0,
        late_fee: float = 0.0,
        seat_quota: int = 40,
        test_pass_percentage: float = 40.0,
        test_weight_pct: float = 70.0,
        interview_weight_pct: float = 30.0,
        currency: str = "BDT",
        notes: Optional[str] = None,
        actor_user: Optional[User] = None,
        current_user: str = "admin",
    ) -> Tuple[bool, Optional[AdmissionFeeConfig], str]:
        _require_adm_perm("admissions.fees.MANAGE", actor_user)
        if min(application_fee, admission_test_fee, enrollment_fee, late_fee) < 0:
            return False, None, "Admission fee amounts must be non-negative."
        if seat_quota <= 0:
            return False, None, "Seat quota must be greater than zero."
        if round(test_weight_pct + interview_weight_pct, 2) <= 0:
            return False, None, "Merit weights must sum to a positive percentage."

        _, username = _resolve_actor(actor_user, current_user)
        existing = (
            db.query(AdmissionFeeConfig)
            .filter(
                AdmissionFeeConfig.academic_year_id == academic_year_id,
                AdmissionFeeConfig.class_id == class_id if class_id is not None else AdmissionFeeConfig.class_id.is_(None),
                AdmissionFeeConfig.is_deleted == False,
            )
            .first()
        )
        if existing:
            existing.fee_name = fee_name.strip()
            existing.application_fee = float(application_fee)
            existing.admission_test_fee = float(admission_test_fee)
            existing.enrollment_fee = float(enrollment_fee)
            existing.late_fee = float(late_fee)
            existing.seat_quota = int(seat_quota)
            existing.test_pass_percentage = float(test_pass_percentage)
            existing.test_weight_pct = float(test_weight_pct)
            existing.interview_weight_pct = float(interview_weight_pct)
            existing.currency = currency.strip() or "BDT"
            existing.notes = notes
            existing.is_active = True
            cfg = existing
            action_msg = "Updated admission fee & quota configuration."
        else:
            cfg = AdmissionFeeConfig(
                academic_year_id=academic_year_id,
                class_id=class_id,
                fee_name=fee_name.strip(),
                application_fee=float(application_fee),
                admission_test_fee=float(admission_test_fee),
                enrollment_fee=float(enrollment_fee),
                late_fee=float(late_fee),
                seat_quota=int(seat_quota),
                test_pass_percentage=float(test_pass_percentage),
                test_weight_pct=float(test_weight_pct),
                interview_weight_pct=float(interview_weight_pct),
                currency=currency.strip() or "BDT",
                notes=notes,
                is_active=True,
            )
            db.add(cfg)
            db.flush()
            action_msg = "Created configurable admission fee schedule."

        AdmissionService._log(db, "ADMISSION_FEE_CONFIGURED", f"{action_msg} (Quota={seat_quota}, AppFee={application_fee})", username)
        db.commit()
        db.refresh(cfg)
        return True, cfg, action_msg

    # ==================================================================
    # 2. APPLICATION INTAKE & STATUS LIFECYCLE
    # ==================================================================
    @staticmethod
    def submit_application(
        db: Session,
        payload: Dict[str, Any],
        checklist_overrides: Optional[List[Dict[str, Any]]] = None,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[AdmissionApplication], str]:
        _require_adm_perm("admissions.applications.CREATE", actor_user)
        _, username = _resolve_actor(actor_user, current_user)

        try:
            data = dict(payload)
            fname = str(data.get("first_name") or "").strip()
            lname = str(data.get("last_name") or "").strip()
            full_name = str(data.get("full_name") or "").strip() or f"{fname} {lname}".strip()
            if not full_name:
                return False, None, "Applicant name is required."
            if not fname or not lname:
                parts = full_name.split(None, 1)
                fname = fname or parts[0]
                lname = lname or (parts[1] if len(parts) > 1 else parts[0])

            ay_id = data.get("academic_year_id")
            cls_id = data.get("applying_class_id")
            if not ay_id or not cls_id:
                return False, None, "Academic year and applying class are required."

            dob = _parse_date_flexible(data.get("date_of_birth"), fallback=None)
            if not dob:
                return False, None, "Valid date_of_birth is required."

            g_name = str(data.get("guardian_name") or data.get("father_name") or "").strip()
            g_phone = str(data.get("guardian_phone") or data.get("phone") or "").strip()
            if not g_name or not g_phone:
                return False, None, "Guardian name and guardian phone are required."

            dup_msg = AdmissionRepository.check_duplicate_applicant(
                db,
                academic_year_id=int(ay_id),
                full_name=full_name,
                date_of_birth=dob,
                guardian_phone=g_phone,
                birth_certificate_no=data.get("birth_certificate_no"),
            )
            if dup_msg:
                return False, None, dup_msg

            gen_app_id, gen_form_no, gen_admit_no = AdmissionRepository.generate_applicant_identifiers(db)
            applicant_id = (str(data.get("applicant_id") or "").strip()) or gen_app_id
            form_number = (str(data.get("form_number") or "").strip()) or gen_form_no
            admit_number = (str(data.get("admit_card_number") or "").strip()) or gen_admit_no

            if db.query(AdmissionApplication.id).filter_by(applicant_id=applicant_id).first():
                return False, None, f"Applicant ID '{applicant_id}' already exists."

            status = AdmissionStatus.normalize(data.get("status") or AdmissionStatus.APPLIED)
            fee_cfg = AdmissionRepository.get_effective_fee_config(db, int(ay_id), int(cls_id))

            app_obj = AdmissionApplication(
                applicant_id=applicant_id,
                form_number=form_number,
                admit_card_number=admit_number,
                academic_year_id=int(ay_id),
                applying_class_id=int(cls_id),
                preferred_section_id=data.get("preferred_section_id"),
                group_name=(data.get("group_name") or "General").strip(),
                shift_name=(data.get("shift_name") or "Morning").strip(),
                application_date=_parse_date_flexible(data.get("application_date"), fallback=date.today()),
                source_channel=(data.get("source_channel") or "Walk-in").strip(),
                first_name=fname,
                last_name=lname,
                full_name=full_name,
                gender=(data.get("gender") or "Male").strip(),
                date_of_birth=dob,
                blood_group=data.get("blood_group"),
                religion=data.get("religion") or "Islam",
                nationality=data.get("nationality") or "Bangladeshi",
                birth_certificate_no=(data.get("birth_certificate_no") or None),
                photo_path=data.get("photo_path"),
                phone=data.get("phone"),
                email=data.get("email"),
                address=data.get("address"),
                city=data.get("city") or "Dhaka",
                father_name=data.get("father_name"),
                mother_name=data.get("mother_name"),
                guardian_name=g_name,
                guardian_relation=(data.get("guardian_relation") or "Father").strip(),
                guardian_phone=g_phone,
                guardian_email=data.get("guardian_email"),
                guardian_occupation=data.get("guardian_occupation"),
                emergency_contact=data.get("emergency_contact") or g_phone,
                previous_school=data.get("previous_school"),
                previous_class=data.get("previous_class"),
                previous_gpa=float(data["previous_gpa"]) if data.get("previous_gpa") not in (None, "") else None,
                medical_notes=data.get("medical_notes"),
                status=status,
                fee_config_id=data.get("fee_config_id") or (fee_cfg.id if fee_cfg else None),
                remarks=data.get("remarks"),
            )
            db.add(app_obj)
            db.flush()

            # Seed Document Checklist
            items = checklist_overrides if checklist_overrides is not None else DEFAULT_CHECKLIST_ITEMS
            for c_item in items:
                db.add(
                    AdmissionDocumentChecklist(
                        application_id=app_obj.id,
                        document_code=str(c_item["document_code"]).strip().upper(),
                        document_name=str(c_item["document_name"]).strip(),
                        is_required=bool(c_item.get("is_required", True)),
                        is_submitted=bool(c_item.get("is_submitted", False)),
                        is_verified=bool(c_item.get("is_verified", False)),
                        file_path=c_item.get("file_path"),
                        remarks=c_item.get("remarks"),
                    )
                )

            db.add(
                AdmissionStatusHistory(
                    application_id=app_obj.id,
                    from_status=None,
                    to_status=status,
                    changed_by=username,
                    changed_at=utc_now(),
                    remarks="Admission application submitted",
                )
            )
            AdmissionService._log(
                db,
                "ADMISSION_APPLICATION_CREATED",
                f"Submitted admission application {app_obj.applicant_id} for '{app_obj.full_name}' (Status: {status})",
                username,
                entity_id=app_obj.id,
            )
            db.commit()
            db.refresh(app_obj)
            return True, app_obj, f"Application {app_obj.applicant_id} created ({status})."
        except ValueError as exc:
            db.rollback()
            return False, None, str(exc)
        except Exception as exc:
            db.rollback()
            return False, None, f"Failed to create application: {exc}"

    @staticmethod
    def transition_status(
        db: Session,
        application_pk: int,
        new_status: str,
        remarks: Optional[str] = None,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[AdmissionApplication], str]:
        _require_adm_perm("admissions.applications.EDIT", actor_user)
        app_obj = db.query(AdmissionApplication).filter_by(id=application_pk, is_deleted=False).first()
        if not app_obj:
            return False, None, "Admission application not found."

        target = AdmissionStatus.normalize(new_status)
        if app_obj.converted_student_id and target != AdmissionStatus.ADMITTED:
            return False, app_obj, f"Applicant {app_obj.applicant_id} has already been converted to Student #{app_obj.converted_student_id}."

        _, username = _resolve_actor(actor_user, current_user)
        prev = app_obj.status
        app_obj.status = target
        if target == AdmissionStatus.REJECTED:
            app_obj.merit_rank = None
            app_obj.waitlist_position = None
        if remarks:
            app_obj.decision_notes = remarks

        db.add(
            AdmissionStatusHistory(
                application_id=app_obj.id,
                from_status=prev,
                to_status=target,
                changed_by=username,
                changed_at=utc_now(),
                remarks=remarks or f"Status updated from '{prev}' to '{target}'",
            )
        )
        AdmissionService._log(
            db,
            "ADMISSION_STATUS_CHANGED",
            f"Updated {app_obj.applicant_id} status: '{prev}' -> '{target}'",
            username,
            entity_id=app_obj.id,
        )
        db.commit()
        db.refresh(app_obj)
        return True, app_obj, f"{app_obj.applicant_id} status updated to '{target}'."

    # ==================================================================
    # 3. DOCUMENT CHECKLIST WORKFLOW
    # ==================================================================
    @staticmethod
    def update_checklist_item(
        db: Session,
        application_pk: int,
        document_code: str,
        *,
        document_name: Optional[str] = None,
        is_required: Optional[bool] = None,
        is_submitted: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        file_path: Optional[str] = None,
        remarks: Optional[str] = None,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[AdmissionDocumentChecklist], str]:
        _require_adm_perm("admissions.applications.EDIT", actor_user)
        app_obj = db.query(AdmissionApplication).filter_by(id=application_pk, is_deleted=False).first()
        if not app_obj:
            return False, None, "Admission application not found."

        _, username = _resolve_actor(actor_user, current_user)
        code = document_code.strip().upper()
        item = (
            db.query(AdmissionDocumentChecklist)
            .filter_by(application_id=application_pk, document_code=code)
            .first()
        )
        if not item:
            item = AdmissionDocumentChecklist(
                application_id=application_pk,
                document_code=code,
                document_name=(document_name or code.replace("_", " ").title()).strip(),
                is_required=True if is_required is None else bool(is_required),
            )
            db.add(item)

        if document_name is not None:
            item.document_name = document_name.strip()
        if is_required is not None:
            item.is_required = bool(is_required)
        if file_path is not None:
            item.file_path = file_path
        if is_submitted is not None:
            item.is_submitted = bool(is_submitted)
        if is_verified is not None:
            item.is_verified = bool(is_verified)
            if item.is_verified:
                item.is_submitted = True
                item.verified_by = username
                item.verified_at = utc_now()
            else:
                item.verified_by = None
                item.verified_at = None
        if remarks is not None:
            item.remarks = remarks

        if app_obj.status == AdmissionStatus.APPLIED:
            app_obj.status = AdmissionStatus.UNDER_REVIEW
            db.add(
                AdmissionStatusHistory(
                    application_id=app_obj.id,
                    from_status=AdmissionStatus.APPLIED,
                    to_status=AdmissionStatus.UNDER_REVIEW,
                    changed_by=username,
                    changed_at=utc_now(),
                    remarks=f"Document checklist updated ({code})",
                )
            )

        db.commit()
        db.refresh(item)
        return True, item, f"Checklist item '{item.document_name}' updated."

    @staticmethod
    def get_checklist_summary(application: AdmissionApplication) -> Dict[str, Any]:
        items = list(application.checklist_items or [])
        req = [i for i in items if i.is_required]
        submitted_req = sum(1 for i in req if i.is_submitted)
        verified_req = sum(1 for i in req if i.is_verified)
        return {
            "total_items": len(items),
            "required_items": len(req),
            "required_submitted": submitted_req,
            "required_verified": verified_req,
            "all_required_submitted": submitted_req == len(req),
            "all_required_verified": verified_req == len(req),
        }

    # ==================================================================
    # 4. ADMISSION TEST & INTERVIEW EVALUATION
    # ==================================================================
    @staticmethod
    def schedule_or_score_test(
        db: Session,
        application_pk: int,
        *,
        exam_title: str = "Entrance Assessment Test",
        exam_date: Optional[date] = None,
        exam_time: str = "10:00 AM - 11:30 AM",
        venue_room: str = "Main Examination Hall",
        seat_number: Optional[str] = None,
        max_marks: float = 100.0,
        obtained_marks: Optional[float] = None,
        auto_shortlist: bool = True,
        remarks: Optional[str] = None,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[AdmissionTestScore], str]:
        _require_adm_perm("admissions.evaluation.CREATE", actor_user)
        app_obj = db.query(AdmissionApplication).filter_by(id=application_pk, is_deleted=False).first()
        if not app_obj:
            return False, None, "Admission application not found."
        if max_marks <= 0:
            return False, None, "max_marks must be positive."
        if obtained_marks is not None and (obtained_marks < 0 or obtained_marks > max_marks):
            return False, None, f"obtained_marks must be between 0 and {max_marks}."

        _, username = _resolve_actor(actor_user, current_user)
        test = (
            db.query(AdmissionTestScore)
            .filter_by(application_id=application_pk)
            .order_by(AdmissionTestScore.id.desc())
            .first()
        )
        if not test:
            test = AdmissionTestScore(
                application_id=application_pk,
                admit_card_no=app_obj.admit_card_number or app_obj.applicant_id,
                seat_number=seat_number or f"SEAT-{application_pk:03d}",
            )
            db.add(test)

        test.exam_title = exam_title.strip()
        if exam_date is not None:
            test.exam_date = exam_date
        test.exam_time = exam_time
        test.venue_room = venue_room
        if seat_number:
            test.seat_number = seat_number
        test.max_marks = float(max_marks)
        if remarks is not None:
            test.remarks = remarks

        if obtained_marks is not None:
            pct = round((float(obtained_marks) / float(max_marks)) * 100.0, 2)
            fee_cfg = AdmissionRepository.get_effective_fee_config(db, app_obj.academic_year_id, app_obj.applying_class_id)
            pass_pct = float(fee_cfg.test_pass_percentage) if fee_cfg else 40.0
            test.obtained_marks = float(obtained_marks)
            test.percentage = pct
            test.result_status = "Passed" if pct >= pass_pct else "Failed"
            test.evaluated_by = username
            test.evaluated_at = utc_now()

            if auto_shortlist and test.result_status == "Passed" and app_obj.status in (
                AdmissionStatus.APPLIED,
                AdmissionStatus.UNDER_REVIEW,
            ):
                prev = app_obj.status
                app_obj.status = AdmissionStatus.SHORTLISTED
                db.add(
                    AdmissionStatusHistory(
                        application_id=app_obj.id,
                        from_status=prev,
                        to_status=AdmissionStatus.SHORTLISTED,
                        changed_by=username,
                        changed_at=utc_now(),
                        remarks=f"Shortlisted after passing admission test ({pct:.1f}%)",
                    )
                )

        AdmissionService._log(
            db,
            "ADMISSION_TEST_UPDATED",
            f"Updated admission test for {app_obj.applicant_id}: status={test.result_status}, score={test.obtained_marks}/{test.max_marks}",
            username,
            entity_id=app_obj.id,
        )
        db.commit()
        db.refresh(test)
        return True, test, f"Admission test saved ({test.result_status})."

    @staticmethod
    def schedule_or_record_interview(
        db: Session,
        application_pk: int,
        *,
        interview_date: Optional[date] = None,
        interview_time: str = "10:30 AM",
        venue: str = "Principal Conference Room",
        interviewer_name: Optional[str] = None,
        interviewer_teacher_id: Optional[int] = None,
        communication_score: Optional[float] = None,
        aptitude_score: Optional[float] = None,
        overall_score: Optional[float] = None,
        recommendation: str = "Pending",
        status: Optional[str] = None,
        feedback: Optional[str] = None,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[AdmissionInterview], str]:
        _require_adm_perm("admissions.evaluation.CREATE", actor_user)
        app_obj = db.query(AdmissionApplication).filter_by(id=application_pk, is_deleted=False).first()
        if not app_obj:
            return False, None, "Admission application not found."

        _, username = _resolve_actor(actor_user, current_user)
        iv = (
            db.query(AdmissionInterview)
            .filter_by(application_id=application_pk)
            .order_by(AdmissionInterview.id.desc())
            .first()
        )
        if not iv:
            iv = AdmissionInterview(
                application_id=application_pk,
                interview_date=interview_date or date.today(),
                recorded_by=username,
            )
            db.add(iv)

        if interview_date is not None:
            iv.interview_date = interview_date
        iv.interview_time = interview_time
        iv.venue = venue
        if interviewer_name is not None:
            iv.interviewer_name = interviewer_name
        if interviewer_teacher_id is not None:
            iv.interviewer_teacher_id = interviewer_teacher_id

        if communication_score is not None:
            iv.communication_score = float(communication_score)
        if aptitude_score is not None:
            iv.aptitude_score = float(aptitude_score)

        # Compute overall_score cleanly out of 100 if component scores given and overall omitted
        if overall_score is not None:
            if overall_score < 0 or overall_score > 100:
                return False, None, "Interview overall_score must be between 0 and 100."
            iv.overall_score = float(overall_score)
        elif communication_score is not None or aptitude_score is not None:
            c = iv.communication_score or 0.0
            a = iv.aptitude_score or 0.0
            iv.overall_score = round(((c + a) / 20.0) * 100.0, 2)

        iv.recommendation = recommendation
        if status is not None:
            iv.status = status
        elif iv.overall_score is not None:
            iv.status = "Completed"
        if feedback is not None:
            iv.feedback = feedback
        iv.recorded_by = username

        if app_obj.status in (AdmissionStatus.APPLIED, AdmissionStatus.UNDER_REVIEW, AdmissionStatus.SHORTLISTED):
            prev = app_obj.status
            app_obj.status = AdmissionStatus.INTERVIEW
            db.add(
                AdmissionStatusHistory(
                    application_id=app_obj.id,
                    from_status=prev,
                    to_status=AdmissionStatus.INTERVIEW,
                    changed_by=username,
                    changed_at=utc_now(),
                    remarks=f"Interview scheduled/recorded ({iv.interview_date})",
                )
            )

        AdmissionService._log(
            db,
            "ADMISSION_INTERVIEW_RECORDED",
            f"Updated interview for {app_obj.applicant_id} ({iv.status}, score={iv.overall_score}, rec={iv.recommendation})",
            username,
            entity_id=app_obj.id,
        )
        db.commit()
        db.refresh(iv)
        return True, iv, f"Interview saved ({iv.status})."

    # ==================================================================
    # 5. MERIT LIST GENERATION, SELECTION & WAITING LIST
    # ==================================================================
    @staticmethod
    def generate_merit_list(
        db: Session,
        academic_year_id: int,
        class_id: int,
        seat_quota: Optional[int] = None,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Ranks eligible applicants for (academic_year_id, class_id) by weighted Test + Interview score,
        selects top `seat_quota` applicants as 'Selected', and places remaining eligible as 'Waitlisted'.
        """
        _require_adm_perm("admissions.evaluation.MANAGE", actor_user)
        _, username = _resolve_actor(actor_user, current_user)

        fee_cfg = AdmissionRepository.get_effective_fee_config(db, academic_year_id, class_id)
        quota = seat_quota if seat_quota is not None else (fee_cfg.seat_quota if fee_cfg else 40)
        if quota <= 0:
            return False, [], "seat_quota must be greater than zero."

        t_weight = float(fee_cfg.test_weight_pct) if fee_cfg else 70.0
        i_weight = float(fee_cfg.interview_weight_pct) if fee_cfg else 30.0
        total_w = t_weight + i_weight
        if total_w <= 0:
            t_weight, i_weight, total_w = 70.0, 30.0, 100.0

        eligible_statuses = [
            AdmissionStatus.SHORTLISTED,
            AdmissionStatus.INTERVIEW,
            AdmissionStatus.SELECTED,
            AdmissionStatus.WAITLISTED,
            AdmissionStatus.ADMITTED,
        ]
        apps = (
            db.query(AdmissionApplication)
            .options(
                joinedload(AdmissionApplication.test_scores),
                joinedload(AdmissionApplication.interviews),
            )
            .filter(
                AdmissionApplication.academic_year_id == academic_year_id,
                AdmissionApplication.applying_class_id == class_id,
                AdmissionApplication.is_deleted == False,
                AdmissionApplication.status.in_(eligible_statuses),
            )
            .all()
        )
        if not apps:
            return False, [], "No shortlisted/interviewed candidates found for merit ranking."

        scored: List[Tuple[float, float, int, AdmissionApplication, float, float]] = []
        for app_obj in apps:
            latest_test = app_obj.test_scores[0] if app_obj.test_scores else None
            latest_iv = app_obj.interviews[0] if app_obj.interviews else None

            # Exclude candidates explicitly marked Failed in test
            if latest_test and latest_test.result_status == "Failed":
                continue

            test_pct = float(latest_test.percentage) if (latest_test and latest_test.percentage is not None) else 0.0
            iv_score = float(latest_iv.overall_score) if (latest_iv and latest_iv.overall_score is not None) else 0.0
            combined = round(((test_pct * t_weight) + (iv_score * i_weight)) / total_w, 2)
            prev_gpa = float(app_obj.previous_gpa or 0.0)
            scored.append((combined, prev_gpa, -app_obj.id, app_obj, test_pct, iv_score))

        if not scored:
            return False, [], "No passing candidates eligible for merit ranking."

        scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)

        output_rows: List[Dict[str, Any]] = []
        selected_count = 0
        waitlist_seq = 0

        for rank_idx, (combined, _, _, app_obj, test_pct, iv_score) in enumerate(scored, start=1):
            app_obj.combined_score = combined
            app_obj.merit_rank = rank_idx
            prev_status = app_obj.status

            if app_obj.status == AdmissionStatus.ADMITTED:
                app_obj.waitlist_position = None
                selected_count += 1
            elif selected_count < quota:
                selected_count += 1
                app_obj.status = AdmissionStatus.SELECTED
                app_obj.waitlist_position = None
            else:
                waitlist_seq += 1
                app_obj.status = AdmissionStatus.WAITLISTED
                app_obj.waitlist_position = waitlist_seq

            if app_obj.status != prev_status:
                db.add(
                    AdmissionStatusHistory(
                        application_id=app_obj.id,
                        from_status=prev_status,
                        to_status=app_obj.status,
                        changed_by=username,
                        changed_at=utc_now(),
                        remarks=f"Merit list generated (Rank #{rank_idx}, Score={combined:.2f})",
                    )
                )

            output_rows.append(
                {
                    "id": app_obj.id,
                    "applicant_id": app_obj.applicant_id,
                    "full_name": app_obj.full_name,
                    "guardian_name": app_obj.guardian_name,
                    "test_pct": test_pct,
                    "interview_score": iv_score,
                    "combined_score": combined,
                    "merit_rank": rank_idx,
                    "waitlist_position": app_obj.waitlist_position,
                    "status": app_obj.status,
                }
            )

        AdmissionService._log(
            db,
            "ADMISSION_MERIT_LIST_GENERATED",
            f"Generated merit list for class #{class_id} ({len(output_rows)} ranked, quota={quota}, waitlisted={waitlist_seq})",
            username,
        )
        db.commit()
        return True, output_rows, f"Merit list published: {selected_count} selected/admitted, {waitlist_seq} waitlisted."

    @staticmethod
    def promote_from_waitlist(
        db: Session,
        academic_year_id: int,
        class_id: int,
        count: int = 1,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, List[AdmissionApplication], str]:
        _require_adm_perm("admissions.evaluation.APPROVE", actor_user)
        _, username = _resolve_actor(actor_user, current_user)

        waitlisted = (
            db.query(AdmissionApplication)
            .filter(
                AdmissionApplication.academic_year_id == academic_year_id,
                AdmissionApplication.applying_class_id == class_id,
                AdmissionApplication.status == AdmissionStatus.WAITLISTED,
                AdmissionApplication.is_deleted == False,
            )
            .order_by(AdmissionApplication.waitlist_position.asc(), AdmissionApplication.merit_rank.asc())
            .all()
        )
        if not waitlisted:
            return False, [], "No waitlisted candidates available for promotion."

        promoted: List[AdmissionApplication] = []
        for idx, app_obj in enumerate(waitlisted):
            if idx < count:
                app_obj.status = AdmissionStatus.SELECTED
                app_obj.waitlist_position = None
                db.add(
                    AdmissionStatusHistory(
                        application_id=app_obj.id,
                        from_status=AdmissionStatus.WAITLISTED,
                        to_status=AdmissionStatus.SELECTED,
                        changed_by=username,
                        changed_at=utc_now(),
                        remarks="Promoted from waiting list to Selected",
                    )
                )
                promoted.append(app_obj)
            else:
                app_obj.waitlist_position = (idx - count) + 1

        AdmissionService._log(
            db,
            "ADMISSION_WAITLIST_PROMOTED",
            f"Promoted {len(promoted)} waitlisted applicant(s) to Selected for class #{class_id}",
            username,
        )
        db.commit()
        return True, promoted, f"Promoted {len(promoted)} applicant(s) from the waiting list."

    # ==================================================================
    # 6. CONFIGURABLE ADMISSION FEE COLLECTION
    # ==================================================================
    @staticmethod
    def record_fee_payment(
        db: Session,
        application_pk: int,
        fee_type: str = "Application Fee",
        amount_paid: Optional[float] = None,
        discount_amount: float = 0.0,
        payment_method: str = "Cash",
        reference_no: Optional[str] = None,
        payment_date: Optional[date] = None,
        remarks: Optional[str] = None,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[AdmissionFeePayment], str]:
        _require_adm_perm("admissions.fees.CREATE", actor_user)
        app_obj = db.query(AdmissionApplication).filter_by(id=application_pk, is_deleted=False).first()
        if not app_obj:
            return False, None, "Admission application not found."

        _, username = _resolve_actor(actor_user, current_user)
        cfg = app_obj.fee_config or AdmissionRepository.get_effective_fee_config(
            db, app_obj.academic_year_id, app_obj.applying_class_id
        )

        # Resolve expected fee amount from configurable fee schedule
        ft = (fee_type or "Application Fee").strip()
        if cfg:
            fee_map = {
                "Application Fee": float(cfg.application_fee),
                "Admission Test Fee": float(cfg.admission_test_fee),
                "Enrollment Fee": float(cfg.enrollment_fee),
                "Combined Admission Fee": float(cfg.application_fee + cfg.admission_test_fee + cfg.enrollment_fee),
            }
            amount_due = fee_map.get(ft, float(cfg.application_fee))
        else:
            amount_due = float(amount_paid if amount_paid is not None else 500.0)

        disc = max(0.0, float(discount_amount or 0.0))
        net_due = max(0.0, amount_due - disc)
        paid = net_due if amount_paid is None else float(amount_paid)
        if paid < 0:
            return False, None, "Payment amount cannot be negative."

        if net_due == 0.0 and disc > 0:
            p_status = "Waived"
        elif paid >= net_due:
            p_status = "Paid"
        elif paid > 0:
            p_status = "Partial"
        else:
            p_status = "Unpaid"

        rcpt_no = AdmissionRepository.generate_receipt_number(db)
        payment = AdmissionFeePayment(
            application_id=app_obj.id,
            fee_config_id=cfg.id if cfg else None,
            receipt_no=rcpt_no,
            fee_type=ft,
            amount_due=amount_due,
            discount_amount=disc,
            amount_paid=paid,
            payment_method=payment_method.strip() or "Cash",
            reference_no=reference_no,
            payment_date=payment_date or date.today(),
            payment_status=p_status,
            collected_by=username,
            remarks=remarks,
        )
        db.add(payment)
        AdmissionService._log(
            db,
            "ADMISSION_FEE_COLLECTED",
            f"Collected {ft} ({paid:.2f}) for {app_obj.applicant_id} [Receipt: {rcpt_no}]",
            username,
            entity_id=app_obj.id,
        )
        db.commit()
        db.refresh(payment)
        return True, payment, f"Recorded {ft} payment (Receipt: {rcpt_no}, Status: {p_status})."

    # ==================================================================
    # 7. ADMISSION APPROVAL & STUDENT CONVERSION
    # ==================================================================
    @staticmethod
    def approve_admission(
        db: Session,
        application_pk: int,
        approval_remarks: str = "Approved for enrollment",
        require_required_docs_verified: bool = False,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[AdmissionApplication], str]:
        _require_adm_perm("admissions.evaluation.APPROVE", actor_user)
        app_obj = AdmissionRepository.get_by_id(db, application_pk)
        if not app_obj:
            return False, None, "Admission application not found."
        if app_obj.status == AdmissionStatus.REJECTED:
            return False, app_obj, "Rejected application cannot be approved directly."

        if require_required_docs_verified:
            chk = AdmissionService.get_checklist_summary(app_obj)
            if not chk["all_required_verified"]:
                return (
                    False,
                    app_obj,
                    f"Only {chk['required_verified']}/{chk['required_items']} required documents are verified.",
                )

        _, username = _resolve_actor(actor_user, current_user)
        prev = app_obj.status
        if app_obj.status not in (AdmissionStatus.SELECTED, AdmissionStatus.ADMITTED):
            app_obj.status = AdmissionStatus.SELECTED
            app_obj.waitlist_position = None
            db.add(
                AdmissionStatusHistory(
                    application_id=app_obj.id,
                    from_status=prev,
                    to_status=AdmissionStatus.SELECTED,
                    changed_by=username,
                    changed_at=utc_now(),
                    remarks=f"Admission approved: {approval_remarks}",
                )
            )

        app_obj.approved_by = username
        app_obj.approved_at = utc_now()
        app_obj.approval_remarks = approval_remarks
        AdmissionService._log(
            db,
            "ADMISSION_APPROVED",
            f"Approved admission for {app_obj.applicant_id} ({app_obj.full_name})",
            username,
            entity_id=app_obj.id,
        )
        db.commit()
        db.refresh(app_obj)
        return True, app_obj, f"Admission approved for {app_obj.applicant_id}."

    @staticmethod
    def convert_to_student(
        db: Session,
        application_pk: int,
        *,
        section_id: Optional[int] = None,
        roll_number: Optional[int] = None,
        auto_approve_if_needed: bool = False,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[Any], str]:
        """
        Atomically convert an approved/selected AdmissionApplication into a full Student CRM record,
        transferring guardian, academic placement, and submitted admission documents.
        """
        _require_adm_perm("admissions.evaluation.APPROVE", actor_user)
        app_obj = AdmissionRepository.get_by_id(db, application_pk)
        if not app_obj:
            return False, None, "Admission application not found."
        if app_obj.converted_student_id:
            return False, app_obj.converted_student, f"Applicant {app_obj.applicant_id} is already converted to Student #{app_obj.converted_student_id}."
        if app_obj.status == AdmissionStatus.REJECTED:
            return False, None, "Cannot convert a Rejected application."

        _, username = _resolve_actor(actor_user, current_user)

        if app_obj.status not in (AdmissionStatus.SELECTED, AdmissionStatus.ADMITTED) and not app_obj.approved_at:
            if not auto_approve_if_needed:
                return False, None, f"Applicant status is '{app_obj.status}'. Approve/Select the applicant before student conversion."
            ok_app, _, msg_app = AdmissionService.approve_admission(
                db, application_pk, approval_remarks="Auto-approved upon student conversion", current_user=username, actor_user=actor_user
            )
            if not ok_app:
                return False, None, msg_app
            app_obj = AdmissionRepository.get_by_id(db, application_pk)

        target_sec = section_id or app_obj.preferred_section_id
        if roll_number is None:
            from app.models.student import Student
            max_roll = (
                db.query(Student)
                .filter(Student.class_id == app_obj.applying_class_id, Student.academic_year_id == app_obj.academic_year_id)
                .count()
            )
            roll_number = max_roll + 1

        student_payload = {
            "roll_number": int(roll_number),
            "first_name": app_obj.first_name,
            "last_name": app_obj.last_name,
            "full_name": app_obj.full_name,
            "gender": app_obj.gender,
            "date_of_birth": app_obj.date_of_birth,
            "blood_group": app_obj.blood_group,
            "religion": app_obj.religion or "Islam",
            "nationality": app_obj.nationality or "Bangladeshi",
            "birth_certificate_no": app_obj.birth_certificate_no,
            "photo_path": app_obj.photo_path,
            "phone": app_obj.phone,
            "email": app_obj.email,
            "address": app_obj.address,
            "city": app_obj.city or "Dhaka",
            "admission_date": date.today(),
            "class_id": app_obj.applying_class_id,
            "section_id": target_sec,
            "academic_year_id": app_obj.academic_year_id,
            "group": app_obj.group_name,
            "shift": app_obj.shift_name,
            "previous_school": app_obj.previous_school,
            "previous_gpa": app_obj.previous_gpa,
            "admission_source": f"Admission CRM ({app_obj.applicant_id})",
            "emergency_contact": app_obj.emergency_contact or app_obj.guardian_phone,
            "medical_notes": app_obj.medical_notes,
            "status": "active",
        }
        guardian_payload = {
            "father_name": app_obj.father_name,
            "mother_name": app_obj.mother_name,
            "guardian_name": app_obj.guardian_name,
            "relation": app_obj.guardian_relation or "Father",
            "guardian_phone": app_obj.guardian_phone,
            "guardian_email": app_obj.guardian_email,
            "guardian_occupation": app_obj.guardian_occupation,
            "guardian_address": app_obj.address,
        }

        ok_stu, student, msg_stu = StudentService.admit_student(
            db,
            student_payload=student_payload,
            guardian_payload=guardian_payload,
            current_username=username,
            admission_type=f"Admission CRM ({app_obj.applicant_id})",
        )
        if not ok_stu or not student:
            return False, None, f"Student conversion failed: {msg_stu}"

        # Migrate submitted documents into StudentDocument vault
        for chk in app_obj.checklist_items or []:
            if chk.is_submitted:
                db.add(
                    StudentDocument(
                        student_id=student.id,
                        document_type=chk.document_code,
                        title=chk.document_name,
                        file_path=chk.file_path,
                        is_verified=chk.is_verified,
                        verified_by=chk.verified_by,
                        verified_at=chk.verified_at,
                        notes=f"Transferred from Admission Application {app_obj.applicant_id}",
                        uploaded_by=username,
                    )
                )

        prev_status = app_obj.status
        app_obj.converted_student_id = student.id
        app_obj.converted_at = utc_now()
        app_obj.converted_by = username
        app_obj.status = AdmissionStatus.ADMITTED
        if not app_obj.approved_at:
            app_obj.approved_by = username
            app_obj.approved_at = utc_now()

        db.add(
            AdmissionStatusHistory(
                application_id=app_obj.id,
                from_status=prev_status,
                to_status=AdmissionStatus.ADMITTED,
                changed_by=username,
                changed_at=utc_now(),
                remarks=f"Converted into Student CRM ({student.student_id})",
            )
        )
        AdmissionService._log(
            db,
            "ADMISSION_CONVERTED_TO_STUDENT",
            f"Converted {app_obj.applicant_id} -> Student {student.student_id} ({student.full_name})",
            username,
            entity_id=app_obj.id,
        )
        db.commit()
        db.refresh(app_obj)
        db.refresh(student)
        return True, student, f"Converted {app_obj.applicant_id} to Student {student.student_id}."

    # ==================================================================
    # 8. PDF DOCUMENT EXPORTS
    # ==================================================================
    @staticmethod
    def export_admission_form_pdf(db: Session, application_pk: int, output_path: str) -> str:
        app_obj = AdmissionRepository.get_by_id(db, application_pk)
        if not app_obj:
            raise ValueError("Admission application not found.")
        return AdmissionPDFGenerator.generate_admission_form(app_obj, _get_school(db), output_path)

    @staticmethod
    def export_applicant_receipt_pdf(db: Session, payment_id: int, output_path: str) -> str:
        payment = db.query(AdmissionFeePayment).filter_by(id=payment_id).first()
        if not payment:
            raise ValueError("Admission fee payment not found.")
        app_obj = AdmissionRepository.get_by_id(db, payment.application_id)
        if not app_obj:
            raise ValueError("Parent admission application not found.")
        return AdmissionPDFGenerator.generate_applicant_receipt(payment, app_obj, _get_school(db), output_path)

    @staticmethod
    def export_admit_card_pdf(db: Session, application_pk: int, output_path: str) -> str:
        app_obj = AdmissionRepository.get_by_id(db, application_pk)
        if not app_obj:
            raise ValueError("Admission application not found.")
        latest_test = app_obj.test_scores[0] if app_obj.test_scores else None
        return AdmissionPDFGenerator.generate_admit_card(app_obj, latest_test, _get_school(db), output_path)

    @staticmethod
    def export_merit_list_pdf(
        db: Session,
        academic_year_id: int,
        class_id: int,
        output_path: str,
    ) -> str:
        ay = db.query(AcademicYear).filter_by(id=academic_year_id).first()
        cls_obj = db.query(SchoolClass).filter_by(id=class_id).first()
        cfg = AdmissionRepository.get_effective_fee_config(db, academic_year_id, class_id)
        quota = cfg.seat_quota if cfg else 40
        apps = AdmissionRepository.get_merit_list(db, academic_year_id=academic_year_id, class_id=class_id)
        entries = []
        for a in apps:
            t = a.test_scores[0] if a.test_scores else None
            iv = a.interviews[0] if a.interviews else None
            entries.append(
                {
                    "applicant_id": a.applicant_id,
                    "full_name": a.full_name,
                    "guardian_name": a.guardian_name,
                    "test_pct": float(t.percentage or 0.0) if t else 0.0,
                    "interview_score": float(iv.overall_score or 0.0) if iv else 0.0,
                    "combined_score": float(a.combined_score or 0.0),
                    "merit_rank": a.merit_rank,
                    "waitlist_position": a.waitlist_position,
                    "status": a.status,
                }
            )
        return AdmissionPDFGenerator.generate_merit_list(
            entries,
            _get_school(db),
            ay.name if ay else str(academic_year_id),
            cls_obj.name if cls_obj else f"Class #{class_id}",
            quota,
            output_path,
        )

    # ==================================================================
    # 9. EXCEL IMPORT & EXPORT (.xlsx / .csv)
    # ==================================================================
    @staticmethod
    def export_applications_excel(
        db: Session,
        output_file_path: str,
        *,
        status: Optional[str] = None,
        class_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
    ) -> str:
        items, _ = AdmissionRepository.search_applications(
            db, status=status, class_id=class_id, academic_year_id=academic_year_id, page=1, per_page=5000
        )
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Admission_Applications"

        headers = [
            "Applicant ID", "Form No", "Full Name", "Gender", "DOB", "Applying Class",
            "Academic Year", "Guardian Name", "Guardian Phone", "Previous School",
            "Previous GPA", "Status", "Merit Rank", "Combined Score", "Source Channel", "Applied Date"
        ]
        fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        for idx, h in enumerate(headers, 1):
            c = ws.cell(row=1, column=idx, value=h)
            c.fill = fill
            c.font = font
            c.alignment = Alignment(horizontal="center")

        for r_idx, a in enumerate(items, 2):
            ws.cell(row=r_idx, column=1, value=a.applicant_id)
            ws.cell(row=r_idx, column=2, value=a.form_number or "")
            ws.cell(row=r_idx, column=3, value=a.full_name)
            ws.cell(row=r_idx, column=4, value=a.gender)
            ws.cell(row=r_idx, column=5, value=a.date_of_birth.isoformat() if a.date_of_birth else "")
            ws.cell(row=r_idx, column=6, value=a.applying_class.name if a.applying_class else a.applying_class_id)
            ws.cell(row=r_idx, column=7, value=a.academic_year.name if a.academic_year else a.academic_year_id)
            ws.cell(row=r_idx, column=8, value=a.guardian_name)
            ws.cell(row=r_idx, column=9, value=a.guardian_phone)
            ws.cell(row=r_idx, column=10, value=a.previous_school or "")
            ws.cell(row=r_idx, column=11, value=a.previous_gpa if a.previous_gpa is not None else "")
            ws.cell(row=r_idx, column=12, value=a.status)
            ws.cell(row=r_idx, column=13, value=a.merit_rank or "")
            ws.cell(row=r_idx, column=14, value=a.combined_score if a.combined_score is not None else "")
            ws.cell(row=r_idx, column=15, value=a.source_channel)
            ws.cell(row=r_idx, column=16, value=a.application_date.isoformat() if a.application_date else "")

        for col_idx in range(1, len(headers) + 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 18

        wb.save(output_file_path)
        return output_file_path

    @staticmethod
    def import_applications_excel(
        db: Session,
        file_path: str,
        default_academic_year_id: int,
        default_class_id: Optional[int] = None,
        current_user: str = "admin",
        actor_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        _require_adm_perm("admissions.applications.IMPORT", actor_user)
        _, username = _resolve_actor(actor_user, current_user)

        src = Path(file_path)
        if not src.exists():
            return {"imported": 0, "skipped": 0, "errors": [f"File not found: {file_path}"]}

        rows: List[Dict[str, Any]] = []
        if src.suffix.lower() == ".csv":
            with open(src, "r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    rows.append({(k or "").strip().lower().replace(" ", "_"): v for k, v in row.items()})
        else:
            wb = openpyxl.load_workbook(src, data_only=True)
            ws = wb.active
            all_vals = list(ws.iter_rows(values_only=True))
            if not all_vals:
                return {"imported": 0, "skipped": 0, "errors": ["Workbook is empty."]}
            headers = [str(h or "").strip().lower().replace(" ", "_") for h in all_vals[0]]
            for row_vals in all_vals[1:]:
                if not any(v is not None and str(v).strip() != "" for v in row_vals):
                    continue
                rows.append({headers[i]: row_vals[i] for i in range(min(len(headers), len(row_vals)))})

        # Class lookup by lowercase name or code
        class_lookup: Dict[str, int] = {}
        for c in db.query(SchoolClass).filter(SchoolClass.is_deleted == False).all():
            class_lookup[c.name.strip().lower()] = c.id
            if c.code:
                class_lookup[c.code.strip().lower()] = c.id

        imported = 0
        skipped = 0
        errors: List[str] = []

        for idx, raw in enumerate(rows, start=2):
            cls_val = str(raw.get("applying_class") or raw.get("class") or "").strip().lower()
            target_cls_id = class_lookup.get(cls_val) or default_class_id
            if not target_cls_id:
                skipped += 1
                errors.append(f"Row {idx}: Unrecognized class '{cls_val}'.")
                continue

            full_name = str(raw.get("full_name") or raw.get("name") or "").strip()
            first_name = str(raw.get("first_name") or "").strip()
            last_name = str(raw.get("last_name") or "").strip()
            dob = _parse_date_flexible(raw.get("dob") or raw.get("date_of_birth"), fallback=date(2012, 1, 1))

            payload = {
                "applicant_id": raw.get("applicant_id") or None,
                "full_name": full_name,
                "first_name": first_name,
                "last_name": last_name,
                "gender": str(raw.get("gender") or "Male").strip(),
                "date_of_birth": dob,
                "applying_class_id": target_cls_id,
                "academic_year_id": default_academic_year_id,
                "guardian_name": str(raw.get("guardian_name") or raw.get("guardian") or "Parent").strip(),
                "guardian_phone": str(raw.get("guardian_phone") or raw.get("phone") or "").strip(),
                "previous_school": str(raw.get("previous_school") or "").strip() or None,
                "previous_gpa": raw.get("previous_gpa"),
                "status": raw.get("status") or AdmissionStatus.APPLIED,
                "source_channel": str(raw.get("source_channel") or "Excel Import").strip(),
            }
            ok, _, msg = AdmissionService.submit_application(
                db, payload, current_user=username, actor_user=actor_user
            )
            if ok:
                imported += 1
            else:
                skipped += 1
                errors.append(f"Row {idx}: {msg}")

        return {"imported": imported, "skipped": skipped, "errors": errors}

    # ==================================================================
    # 10. ADMISSION STATISTICS & FUNNEL ANALYTICS
    # ==================================================================
    @staticmethod
    def get_admission_statistics(
        db: Session,
        academic_year_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        _require_adm_perm("admissions.reports.VIEW")
        q = (
            db.query(AdmissionApplication)
            .options(
                joinedload(AdmissionApplication.applying_class),
                joinedload(AdmissionApplication.checklist_items),
                joinedload(AdmissionApplication.test_scores),
                joinedload(AdmissionApplication.interviews),
                joinedload(AdmissionApplication.fee_payments),
            )
            .filter(AdmissionApplication.is_deleted == False)
        )
        if academic_year_id:
            q = q.filter(AdmissionApplication.academic_year_id == academic_year_id)
        apps = q.all()

        status_counts = {s: 0 for s in AdmissionStatus.ALL}
        source_counts: Dict[str, int] = defaultdict(int)
        gender_counts: Dict[str, int] = defaultdict(int)
        class_buckets: Dict[int, Dict[str, Any]] = {}

        test_scores_vals: List[float] = []
        iv_scores_vals: List[float] = []
        docs_complete_count = 0

        total_fee_due = 0.0
        total_fee_discount = 0.0
        total_fee_collected = 0.0

        for a in apps:
            if a.status in status_counts:
                status_counts[a.status] += 1
            source_counts[a.source_channel or "Walk-in"] += 1
            gender_counts[a.gender or "Other"] += 1

            cname = a.applying_class.name if a.applying_class else f"Class #{a.applying_class_id}"
            if a.applying_class_id not in class_buckets:
                cfg = AdmissionRepository.get_effective_fee_config(db, a.academic_year_id, a.applying_class_id)
                class_buckets[a.applying_class_id] = {
                    "class_id": a.applying_class_id,
                    "class_name": cname,
                    "seat_quota": cfg.seat_quota if cfg else 40,
                    "applications": 0,
                    "selected": 0,
                    "waitlisted": 0,
                    "admitted": 0,
                    "rejected": 0,
                }
            b = class_buckets[a.applying_class_id]
            b["applications"] += 1
            if a.status == AdmissionStatus.SELECTED:
                b["selected"] += 1
            elif a.status == AdmissionStatus.WAITLISTED:
                b["waitlisted"] += 1
            elif a.status == AdmissionStatus.ADMITTED:
                b["admitted"] += 1
            elif a.status == AdmissionStatus.REJECTED:
                b["rejected"] += 1

            chk = AdmissionService.get_checklist_summary(a)
            if chk["required_items"] > 0 and chk["all_required_verified"]:
                docs_complete_count += 1

            for t in a.test_scores or []:
                if t.percentage is not None:
                    test_scores_vals.append(float(t.percentage))
            for iv in a.interviews or []:
                if iv.overall_score is not None:
                    iv_scores_vals.append(float(iv.overall_score))
            for p in a.fee_payments or []:
                total_fee_due += float(p.amount_due or 0.0)
                total_fee_discount += float(p.discount_amount or 0.0)
                total_fee_collected += float(p.amount_paid or 0.0)

        total = len(apps)
        shortlisted_plus = sum(
            status_counts[s]
            for s in (
                AdmissionStatus.SHORTLISTED,
                AdmissionStatus.INTERVIEW,
                AdmissionStatus.SELECTED,
                AdmissionStatus.WAITLISTED,
                AdmissionStatus.ADMITTED,
            )
        )
        selected_plus = status_counts[AdmissionStatus.SELECTED] + status_counts[AdmissionStatus.ADMITTED]
        admitted_cnt = status_counts[AdmissionStatus.ADMITTED]

        return {
            "total_applications": total,
            "status_counts": status_counts,
            "source_breakdown": dict(source_counts),
            "gender_breakdown": dict(gender_counts),
            "class_breakdown": sorted(class_buckets.values(), key=lambda x: x["class_name"]),
            "shortlist_rate_pct": round((shortlisted_plus / total) * 100.0, 1) if total else 0.0,
            "selection_rate_pct": round((selected_plus / total) * 100.0, 1) if total else 0.0,
            "conversion_rate_pct": round((admitted_cnt / total) * 100.0, 1) if total else 0.0,
            "docs_verified_count": docs_complete_count,
            "avg_test_percentage": round(sum(test_scores_vals) / len(test_scores_vals), 1) if test_scores_vals else 0.0,
            "avg_interview_score": round(sum(iv_scores_vals) / len(iv_scores_vals), 1) if iv_scores_vals else 0.0,
            "financials": {
                "total_due": round(total_fee_due, 2),
                "total_discount": round(total_fee_discount, 2),
                "total_collected": round(total_fee_collected, 2),
                "outstanding": round(max(0.0, total_fee_due - total_fee_discount - total_fee_collected), 2),
            },
        }
