"""
EduManage Pro - Admission CRM Repository Layer
Data access operations for Admission Applications, Applicant Identifiers,
Configurable Fee Schedules, Checklist/Test/Interview lookup, and Merit List queries.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.admission import (
    AdmissionApplication,
    AdmissionDocumentChecklist,
    AdmissionFeeConfig,
    AdmissionFeePayment,
    AdmissionInterview,
    AdmissionStatus,
    AdmissionStatusHistory,
    AdmissionTestScore,
)


class AdmissionRepository:
    @staticmethod
    def generate_applicant_identifiers(db: Session) -> Tuple[str, str, str]:
        """Generate collision-free applicant_id, form_number, and admit_card_number."""
        yr = date.today().year
        rows = db.query(
            AdmissionApplication.applicant_id,
            AdmissionApplication.form_number,
            AdmissionApplication.admit_card_number,
        ).all()
        used_app = {r[0] for r in rows if r[0]}
        used_form = {r[1] for r in rows if r[1]}
        used_admit = {r[2] for r in rows if r[2]}

        seq = len(rows) + 1
        while True:
            app_id = f"APP-{yr}-{seq:04d}"
            form_no = f"FORM-{yr}-{seq:04d}"
            admit_no = f"ADMIT-{yr}-{seq:04d}"
            if app_id not in used_app and form_no not in used_form and admit_no not in used_admit:
                return app_id, form_no, admit_no
            seq += 1

    @staticmethod
    def generate_receipt_number(db: Session) -> str:
        yr = date.today().year
        existing = {r[0] for r in db.query(AdmissionFeePayment.receipt_no).all() if r[0]}
        seq = len(existing) + 1
        while True:
            rcpt = f"ADM-RCPT-{yr}-{seq:04d}"
            if rcpt not in existing:
                return rcpt
            seq += 1

    @staticmethod
    def get_by_id(db: Session, application_pk: int) -> Optional[AdmissionApplication]:
        return (
            db.query(AdmissionApplication)
            .options(
                joinedload(AdmissionApplication.academic_year),
                joinedload(AdmissionApplication.applying_class),
                joinedload(AdmissionApplication.preferred_section),
                joinedload(AdmissionApplication.fee_config),
                joinedload(AdmissionApplication.converted_student),
                joinedload(AdmissionApplication.checklist_items),
                joinedload(AdmissionApplication.interviews),
                joinedload(AdmissionApplication.test_scores),
                joinedload(AdmissionApplication.fee_payments),
                joinedload(AdmissionApplication.status_history),
            )
            .filter(AdmissionApplication.id == application_pk, AdmissionApplication.is_deleted == False)
            .first()
        )

    @staticmethod
    def get_by_applicant_id(db: Session, applicant_id: str) -> Optional[AdmissionApplication]:
        return (
            db.query(AdmissionApplication)
            .options(
                joinedload(AdmissionApplication.academic_year),
                joinedload(AdmissionApplication.applying_class),
                joinedload(AdmissionApplication.checklist_items),
                joinedload(AdmissionApplication.interviews),
                joinedload(AdmissionApplication.test_scores),
                joinedload(AdmissionApplication.fee_payments),
            )
            .filter(
                AdmissionApplication.applicant_id == applicant_id.strip(),
                AdmissionApplication.is_deleted == False,
            )
            .first()
        )

    @staticmethod
    def check_duplicate_applicant(
        db: Session,
        academic_year_id: int,
        full_name: str,
        date_of_birth: date,
        guardian_phone: str,
        birth_certificate_no: Optional[str] = None,
        exclude_id: Optional[int] = None,
    ) -> Optional[str]:
        base = db.query(AdmissionApplication).filter(
            AdmissionApplication.academic_year_id == academic_year_id,
            AdmissionApplication.is_deleted == False,
            AdmissionApplication.status != AdmissionStatus.REJECTED,
        )
        if exclude_id:
            base = base.filter(AdmissionApplication.id != exclude_id)

        if birth_certificate_no and birth_certificate_no.strip():
            dup_bc = base.filter(
                AdmissionApplication.birth_certificate_no == birth_certificate_no.strip()
            ).first()
            if dup_bc:
                return f"Duplicate birth certificate '{birth_certificate_no}' already registered on applicant {dup_bc.applicant_id}."

        dup_person = base.filter(
            func.lower(AdmissionApplication.full_name) == full_name.strip().lower(),
            AdmissionApplication.date_of_birth == date_of_birth,
            AdmissionApplication.guardian_phone == guardian_phone.strip(),
        ).first()
        if dup_person:
            return f"Duplicate application already exists for '{dup_person.full_name}' ({dup_person.applicant_id}) in this academic year."
        return None

    @staticmethod
    def search_applications(
        db: Session,
        search_query: Optional[str] = None,
        status: Optional[str] = None,
        class_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        source_channel: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Tuple[List[AdmissionApplication], int]:
        q = (
            db.query(AdmissionApplication)
            .options(
                joinedload(AdmissionApplication.academic_year),
                joinedload(AdmissionApplication.applying_class),
                joinedload(AdmissionApplication.preferred_section),
            )
            .filter(AdmissionApplication.is_deleted == False)
        )

        if search_query and search_query.strip():
            term = f"%{search_query.strip()}%"
            q = q.filter(
                or_(
                    AdmissionApplication.applicant_id.ilike(term),
                    AdmissionApplication.form_number.ilike(term),
                    AdmissionApplication.full_name.ilike(term),
                    AdmissionApplication.guardian_name.ilike(term),
                    AdmissionApplication.guardian_phone.ilike(term),
                    AdmissionApplication.phone.ilike(term),
                    AdmissionApplication.email.ilike(term),
                )
            )
        if status and status != "All":
            q = q.filter(AdmissionApplication.status == AdmissionStatus.normalize(status))
        if class_id:
            q = q.filter(AdmissionApplication.applying_class_id == class_id)
        if academic_year_id:
            q = q.filter(AdmissionApplication.academic_year_id == academic_year_id)
        if source_channel and source_channel != "All":
            q = q.filter(AdmissionApplication.source_channel == source_channel)

        total = q.count()
        offset = max(0, (page - 1) * per_page)
        items = q.order_by(desc(AdmissionApplication.id)).offset(offset).limit(per_page).all()
        return items, total

    @staticmethod
    def get_effective_fee_config(
        db: Session,
        academic_year_id: int,
        class_id: Optional[int] = None,
    ) -> Optional[AdmissionFeeConfig]:
        if class_id:
            specific = (
                db.query(AdmissionFeeConfig)
                .filter(
                    AdmissionFeeConfig.academic_year_id == academic_year_id,
                    AdmissionFeeConfig.class_id == class_id,
                    AdmissionFeeConfig.is_active == True,
                    AdmissionFeeConfig.is_deleted == False,
                )
                .order_by(desc(AdmissionFeeConfig.id))
                .first()
            )
            if specific:
                return specific

        return (
            db.query(AdmissionFeeConfig)
            .filter(
                AdmissionFeeConfig.academic_year_id == academic_year_id,
                AdmissionFeeConfig.class_id.is_(None),
                AdmissionFeeConfig.is_active == True,
                AdmissionFeeConfig.is_deleted == False,
            )
            .order_by(desc(AdmissionFeeConfig.id))
            .first()
        )

    @staticmethod
    def list_fee_configs(
        db: Session,
        academic_year_id: Optional[int] = None,
        active_only: bool = False,
    ) -> List[AdmissionFeeConfig]:
        q = (
            db.query(AdmissionFeeConfig)
            .options(joinedload(AdmissionFeeConfig.academic_year), joinedload(AdmissionFeeConfig.target_class))
            .filter(AdmissionFeeConfig.is_deleted == False)
        )
        if academic_year_id:
            q = q.filter(AdmissionFeeConfig.academic_year_id == academic_year_id)
        if active_only:
            q = q.filter(AdmissionFeeConfig.is_active == True)
        return q.order_by(desc(AdmissionFeeConfig.id)).all()

    @staticmethod
    def get_merit_list(
        db: Session,
        academic_year_id: Optional[int] = None,
        class_id: Optional[int] = None,
        include_statuses: Optional[List[str]] = None,
    ) -> List[AdmissionApplication]:
        q = (
            db.query(AdmissionApplication)
            .options(
                joinedload(AdmissionApplication.academic_year),
                joinedload(AdmissionApplication.applying_class),
                joinedload(AdmissionApplication.test_scores),
                joinedload(AdmissionApplication.interviews),
            )
            .filter(AdmissionApplication.is_deleted == False)
        )
        if academic_year_id:
            q = q.filter(AdmissionApplication.academic_year_id == academic_year_id)
        if class_id:
            q = q.filter(AdmissionApplication.applying_class_id == class_id)
        if include_statuses:
            q = q.filter(AdmissionApplication.status.in_(include_statuses))
        else:
            q = q.filter(
                AdmissionApplication.status.in_(
                    [AdmissionStatus.SELECTED, AdmissionStatus.WAITLISTED, AdmissionStatus.ADMITTED]
                )
            )
        return q.order_by(
            asc(func.coalesce(AdmissionApplication.merit_rank, 999999)),
            desc(func.coalesce(AdmissionApplication.combined_score, -1.0)),
            asc(AdmissionApplication.id),
        ).all()
