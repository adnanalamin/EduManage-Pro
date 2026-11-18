"""
EduManage Pro - Admission CRM Models (SQLAlchemy)
Complete normalized database architecture for Prospective Student Admission CRM:
- Admission Applications with unique Applicant ID & full form metadata
- Application Status Lifecycle (Applied, Under Review, Shortlisted, Interview,
  Selected, Waitlisted, Rejected, Admitted) & immutable status audit history
- Document Checklist items (required, submitted, verified, file vault)
- Entrance Admission Test scores, admit card numbers, & exam venues
- Interview scheduling, panel scoring, & recommendations
- Automated Merit List & Waiting List rank tracking
- Configurable Admission Fee schedules & Applicant Fee Payment receipts
- Direct atomic conversion into Student CRM records
"""

from datetime import date
from typing import Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, utc_now


class AdmissionStatus:
    APPLIED = "Applied"
    UNDER_REVIEW = "Under Review"
    SHORTLISTED = "Shortlisted"
    INTERVIEW = "Interview"
    SELECTED = "Selected"
    WAITLISTED = "Waitlisted"
    REJECTED = "Rejected"
    ADMITTED = "Admitted"

    ALL: List[str] = [
        APPLIED,
        UNDER_REVIEW,
        SHORTLISTED,
        INTERVIEW,
        SELECTED,
        WAITLISTED,
        REJECTED,
        ADMITTED,
    ]

    _CASE_MAP: Dict[str, str] = {s.lower(): s for s in ALL}

    @classmethod
    def normalize(cls, raw_status: Optional[str]) -> str:
        key = (raw_status or "").strip().lower()
        if key in cls._CASE_MAP:
            return cls._CASE_MAP[key]
        raise ValueError(
            f"Invalid admission status '{raw_status}'. Allowed: {', '.join(cls.ALL)}"
        )


DEFAULT_CHECKLIST_ITEMS: List[Dict[str, object]] = [
    {"document_code": "BIRTH_CERT", "document_name": "Birth Certificate Copy", "is_required": True},
    {"document_code": "PHOTO", "document_name": "Passport Size Photographs (2 copies)", "is_required": True},
    {"document_code": "PREV_MARKSHEET", "document_name": "Previous Academic Marksheet / Transcript", "is_required": True},
    {"document_code": "GUARDIAN_NID", "document_name": "Guardian National ID / Passport", "is_required": True},
    {"document_code": "TRANSFER_CERT", "document_name": "Transfer Certificate (TC)", "is_required": False},
    {"document_code": "MEDICAL_CERT", "document_name": "Medical Fitness / Immunization Record", "is_required": False},
]


class AdmissionFeeConfig(Base, TimestampMixin, SoftDeleteMixin):
    """Configurable admission fee schedule per Academic Year & Target Class."""
    __tablename__ = "admission_fee_configs"

    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="SET NULL"), nullable=True, index=True)
    fee_name = Column(String(120), default="Standard Admission Fee Schedule", nullable=False)
    application_fee = Column(Float, default=500.0, nullable=False)
    admission_test_fee = Column(Float, default=300.0, nullable=False)
    enrollment_fee = Column(Float, default=5000.0, nullable=False)
    late_fee = Column(Float, default=0.0, nullable=False)
    seat_quota = Column(Integer, default=40, nullable=False)
    test_pass_percentage = Column(Float, default=40.0, nullable=False)
    test_weight_pct = Column(Float, default=70.0, nullable=False)
    interview_weight_pct = Column(Float, default=30.0, nullable=False)
    currency = Column(String(10), default="BDT", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    notes = Column(String(255), nullable=True)

    academic_year = relationship("AcademicYear")
    target_class = relationship("SchoolClass")

    __table_args__ = (
        CheckConstraint("application_fee >= 0", name="ck_adm_fee_app_nonneg"),
        CheckConstraint("admission_test_fee >= 0", name="ck_adm_fee_test_nonneg"),
        CheckConstraint("enrollment_fee >= 0", name="ck_adm_fee_enroll_nonneg"),
        CheckConstraint("seat_quota > 0", name="ck_adm_fee_quota_pos"),
        Index("idx_adm_fee_year_class", "academic_year_id", "class_id"),
    )

    @property
    def total_pre_admission_fee(self) -> float:
        return round(float(self.application_fee or 0.0) + float(self.admission_test_fee or 0.0), 2)


class AdmissionApplication(Base, TimestampMixin, SoftDeleteMixin):
    """Master Admission CRM Application Record."""
    __tablename__ = "admission_applications"

    # Identifiers
    applicant_id = Column(String(40), unique=True, nullable=False, index=True)
    form_number = Column(String(40), unique=True, nullable=True, index=True)
    admit_card_number = Column(String(40), unique=True, nullable=True, index=True)

    # Academic Target
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)
    applying_class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False, index=True)
    preferred_section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)
    group_name = Column(String(40), default="General", nullable=False)
    shift_name = Column(String(30), default="Morning", nullable=False)
    application_date = Column(Date, default=date.today, nullable=False, index=True)
    source_channel = Column(String(50), default="Walk-in", nullable=False)  # Walk-in, Website, Referral, Campaign, Excel Import

    # Applicant Personal Info
    first_name = Column(String(60), nullable=False)
    last_name = Column(String(60), nullable=False)
    full_name = Column(String(120), nullable=False, index=True)
    gender = Column(String(15), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    blood_group = Column(String(10), nullable=True)
    religion = Column(String(40), default="Islam", nullable=True)
    nationality = Column(String(50), default="Bangladeshi", nullable=True)
    birth_certificate_no = Column(String(60), nullable=True, index=True)
    photo_path = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=True, index=True)
    email = Column(String(120), nullable=True, index=True)
    address = Column(Text, nullable=True)
    city = Column(String(80), default="Dhaka", nullable=True)

    # Guardian & Previous Academics
    father_name = Column(String(120), nullable=True)
    mother_name = Column(String(120), nullable=True)
    guardian_name = Column(String(120), nullable=False)
    guardian_relation = Column(String(50), default="Father", nullable=False)
    guardian_phone = Column(String(30), nullable=False, index=True)
    guardian_email = Column(String(120), nullable=True)
    guardian_occupation = Column(String(100), nullable=True)
    emergency_contact = Column(String(30), nullable=True)
    previous_school = Column(String(160), nullable=True)
    previous_class = Column(String(60), nullable=True)
    previous_gpa = Column(Float, nullable=True)
    medical_notes = Column(Text, nullable=True)

    # Lifecycle & Evaluation
    status = Column(String(30), default=AdmissionStatus.APPLIED, nullable=False, index=True)
    fee_config_id = Column(Integer, ForeignKey("admission_fee_configs.id", ondelete="SET NULL"), nullable=True)
    merit_rank = Column(Integer, nullable=True, index=True)
    waitlist_position = Column(Integer, nullable=True, index=True)
    combined_score = Column(Float, nullable=True)
    decision_notes = Column(Text, nullable=True)

    # Approval & Student Conversion
    approved_by = Column(String(80), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_remarks = Column(String(255), nullable=True)
    converted_student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)
    converted_by = Column(String(80), nullable=True)
    remarks = Column(Text, nullable=True)

    # Relationships
    academic_year = relationship("AcademicYear")
    applying_class = relationship("SchoolClass")
    preferred_section = relationship("Section")
    fee_config = relationship("AdmissionFeeConfig")
    converted_student = relationship("Student")

    checklist_items = relationship(
        "AdmissionDocumentChecklist",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="AdmissionDocumentChecklist.id.asc()",
    )
    interviews = relationship(
        "AdmissionInterview",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="AdmissionInterview.id.desc()",
    )
    test_scores = relationship(
        "AdmissionTestScore",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="AdmissionTestScore.id.desc()",
    )
    fee_payments = relationship(
        "AdmissionFeePayment",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="AdmissionFeePayment.id.desc()",
    )
    status_history = relationship(
        "AdmissionStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="AdmissionStatusHistory.id.desc()",
    )

    __table_args__ = (
        Index("idx_adm_app_class_status", "applying_class_id", "status"),
        Index("idx_adm_app_year_status", "academic_year_id", "status"),
    )

    def __repr__(self):
        return f"<AdmissionApplication(applicant_id='{self.applicant_id}', name='{self.full_name}', status='{self.status}')>"


class AdmissionDocumentChecklist(Base, TimestampMixin):
    """Per-application admission document checklist & verification status."""
    __tablename__ = "admission_document_checklists"

    application_id = Column(Integer, ForeignKey("admission_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    document_code = Column(String(40), nullable=False)
    document_name = Column(String(120), nullable=False)
    is_required = Column(Boolean, default=True, nullable=False)
    is_submitted = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    file_path = Column(String(255), nullable=True)
    verified_by = Column(String(80), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    remarks = Column(String(255), nullable=True)

    application = relationship("AdmissionApplication", back_populates="checklist_items")

    __table_args__ = (
        UniqueConstraint("application_id", "document_code", name="uq_adm_checklist_code"),
    )


class AdmissionTestScore(Base, TimestampMixin):
    """Admission entrance examination schedule, seat/admit card & evaluation scores."""
    __tablename__ = "admission_test_scores"

    application_id = Column(Integer, ForeignKey("admission_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_title = Column(String(120), default="Entrance Assessment Test", nullable=False)
    exam_date = Column(Date, nullable=True, index=True)
    exam_time = Column(String(40), default="10:00 AM - 11:30 AM", nullable=True)
    venue_room = Column(String(100), default="Main Examination Hall", nullable=True)
    seat_number = Column(String(30), nullable=True)
    admit_card_no = Column(String(40), nullable=True, index=True)

    max_marks = Column(Float, default=100.0, nullable=False)
    obtained_marks = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True)
    subject_breakdown_json = Column(Text, nullable=True)
    result_status = Column(String(20), default="Scheduled", nullable=False)  # Scheduled | Passed | Failed | Absent
    evaluated_by = Column(String(80), nullable=True)
    evaluated_at = Column(DateTime(timezone=True), nullable=True)
    remarks = Column(String(255), nullable=True)

    application = relationship("AdmissionApplication", back_populates="test_scores")


class AdmissionInterview(Base, TimestampMixin):
    """Applicant interview scheduling, panel evaluation & recommendation."""
    __tablename__ = "admission_interviews"

    application_id = Column(Integer, ForeignKey("admission_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    interview_date = Column(Date, nullable=False, index=True)
    interview_time = Column(String(30), default="10:30 AM", nullable=False)
    venue = Column(String(100), default="Principal Conference Room", nullable=True)
    interviewer_name = Column(String(120), nullable=True)
    interviewer_teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)

    communication_score = Column(Float, nullable=True)  # out of 10
    aptitude_score = Column(Float, nullable=True)       # out of 10
    overall_score = Column(Float, nullable=True)        # normalized out of 100
    max_score = Column(Float, default=100.0, nullable=False)
    recommendation = Column(String(30), default="Pending", nullable=False)  # Pending | Recommended | Waitlist | Not Recommended
    status = Column(String(20), default="Scheduled", nullable=False)        # Scheduled | Completed | Cancelled | No-Show
    feedback = Column(Text, nullable=True)
    recorded_by = Column(String(80), default="admin", nullable=False)

    application = relationship("AdmissionApplication", back_populates="interviews")
    interviewer_teacher = relationship("Teacher")


class AdmissionFeePayment(Base, TimestampMixin):
    """Fee collection receipts for Application, Entrance Test, and Admission Enrollment fees."""
    __tablename__ = "admission_fee_payments"

    application_id = Column(Integer, ForeignKey("admission_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    fee_config_id = Column(Integer, ForeignKey("admission_fee_configs.id", ondelete="SET NULL"), nullable=True)
    receipt_no = Column(String(50), unique=True, nullable=False, index=True)
    fee_type = Column(String(40), default="Application Fee", nullable=False)  # Application Fee | Admission Test Fee | Enrollment Fee | Combined Admission Fee
    amount_due = Column(Float, default=0.0, nullable=False)
    discount_amount = Column(Float, default=0.0, nullable=False)
    amount_paid = Column(Float, default=0.0, nullable=False)
    payment_method = Column(String(40), default="Cash", nullable=False)  # Cash | Card | Bank Transfer | Mobile Banking
    reference_no = Column(String(80), nullable=True)
    payment_date = Column(Date, default=date.today, nullable=False, index=True)
    payment_status = Column(String(20), default="Paid", nullable=False)  # Paid | Partial | Waived | Refunded
    collected_by = Column(String(80), default="admin", nullable=False)
    remarks = Column(String(255), nullable=True)

    application = relationship("AdmissionApplication", back_populates="fee_payments")
    fee_config = relationship("AdmissionFeeConfig")

    __table_args__ = (
        CheckConstraint("amount_paid >= 0", name="ck_adm_pay_nonneg"),
        CheckConstraint("discount_amount >= 0", name="ck_adm_disc_nonneg"),
    )


class AdmissionStatusHistory(Base, TimestampMixin):
    """Immutable audit trail for application workflow status transitions."""
    __tablename__ = "admission_status_histories"

    application_id = Column(Integer, ForeignKey("admission_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=False)
    changed_by = Column(String(80), default="admin", nullable=False)
    changed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    remarks = Column(String(255), nullable=True)

    application = relationship("AdmissionApplication", back_populates="status_history")
