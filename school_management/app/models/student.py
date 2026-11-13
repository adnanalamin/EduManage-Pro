"""
EduManage Pro - Student & Guardian CRM Models (SQLAlchemy)
Complete normalized schemas for Student 360 CRM profiles, multiple guardians,
family/sibling links, admission & academic history, previous schools, documents,
medical profiles, emergency contacts, notes, tags, custom fields, and status history.
"""

from datetime import date
import json
from typing import Any, Dict, List

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
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, utc_now


class StudentStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRANSFERRED = "transferred"
    GRADUATED = "graduated"
    WITHDRAWN = "withdrawn"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"

    ALL: List[str] = [
        ACTIVE,
        INACTIVE,
        TRANSFERRED,
        GRADUATED,
        WITHDRAWN,
        SUSPENDED,
        ARCHIVED,
    ]

    LABELS: Dict[str, str] = {
        ACTIVE: "Active",
        INACTIVE: "Inactive",
        TRANSFERRED: "Transferred",
        GRADUATED: "Graduated",
        WITHDRAWN: "Withdrawn",
        SUSPENDED: "Suspended",
        ARCHIVED: "Archived",
    }


student_tag_assignments = Table(
    "student_tag_assignments",
    Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("student_tags.id", ondelete="CASCADE"), primary_key=True),
)


class Guardian(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "guardians"

    father_name = Column(String(120), nullable=True)
    mother_name = Column(String(120), nullable=True)
    guardian_name = Column(String(120), nullable=False, index=True)
    relation = Column(String(50), default="Father", nullable=False)
    guardian_phone = Column(String(30), nullable=False, index=True)
    guardian_email = Column(String(120), nullable=True)
    guardian_occupation = Column(String(100), nullable=True)
    guardian_nid = Column(String(50), nullable=True, index=True)
    guardian_address = Column(Text, nullable=True)

    students = relationship("Student", back_populates="guardian")
    student_links = relationship(
        "StudentGuardianLink",
        back_populates="guardian",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Guardian(name='{self.guardian_name}', phone='{self.guardian_phone}')>"


class Student(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "students"

    # Identifiers
    student_id = Column(String(40), unique=True, nullable=False, index=True)
    admission_number = Column(String(40), unique=True, nullable=False, index=True)
    digital_id_code = Column(String(64), unique=True, nullable=True, index=True)
    qr_payload = Column(String(255), nullable=True)
    roll_number = Column(Integer, nullable=False, index=True)

    # Personal Information
    first_name = Column(String(60), nullable=False)
    last_name = Column(String(60), nullable=False)
    full_name = Column(String(120), nullable=False, index=True)
    full_name_bn = Column(String(120), nullable=True)
    gender = Column(String(15), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    blood_group = Column(String(10), nullable=True)
    photo_path = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=True, index=True)
    email = Column(String(120), nullable=True, index=True)

    # Address & Nationality
    address = Column(Text, nullable=True)
    city = Column(String(80), default="Dhaka", nullable=True)
    district = Column(String(80), default="Dhaka", nullable=True)
    division = Column(String(80), default="Dhaka", nullable=True)
    country = Column(String(80), default="Bangladesh", nullable=True)
    religion = Column(String(40), default="Islam", nullable=True)
    nationality = Column(String(50), default="Bangladeshi", nullable=True)
    birth_certificate_no = Column(String(60), unique=True, nullable=True, index=True)

    # Academic Enrollment
    admission_date = Column(Date, default=date.today, nullable=False)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)
    group = Column(String(40), default="General", nullable=True)
    shift = Column(String(20), default="Day", nullable=True)

    # Status & Lifecycle Metadata
    status = Column(String(20), default=StudentStatus.ACTIVE, nullable=False, index=True)
    admission_source = Column(String(80), nullable=True)
    transfer_date = Column(Date, nullable=True)
    transfer_school = Column(String(180), nullable=True)
    transfer_tc_number = Column(String(60), nullable=True)
    withdrawal_date = Column(Date, nullable=True)
    withdrawal_reason = Column(String(255), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    archived_by = Column(String(80), nullable=True)

    # Guardian Relationship (primary backward-compatible FK)
    guardian_id = Column(Integer, ForeignKey("guardians.id", ondelete="SET NULL"), nullable=True, index=True)
    guardian = relationship("Guardian", back_populates="students")

    # Additional Details & CRM Metadata
    previous_school = Column(String(150), nullable=True)
    emergency_contact = Column(String(30), nullable=True)
    medical_notes = Column(Text, nullable=True)
    tags_text = Column(String(500), nullable=True)
    custom_fields_json = Column(Text, default="{}", nullable=False)

    # Academic FK Relationships
    school_class = relationship("SchoolClass")
    section = relationship("Section")
    academic_year = relationship("AcademicYear")

    # CRM Sub-Entity Relationships
    guardian_links = relationship(
        "StudentGuardianLink",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="StudentGuardianLink.priority_order",
    )
    family_links = relationship(
        "StudentFamilyRelationship",
        foreign_keys="[StudentFamilyRelationship.student_id]",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    admission_history = relationship(
        "StudentAdmissionHistory",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="StudentAdmissionHistory.admission_date.desc()",
    )
    academic_history = relationship(
        "StudentAcademicHistory",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="StudentAcademicHistory.id.desc()",
    )
    previous_schools = relationship(
        "StudentPreviousSchool",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="StudentPreviousSchool.id.desc()",
    )
    documents = relationship(
        "StudentDocument",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="StudentDocument.id.desc()",
    )
    medical_profile = relationship(
        "StudentMedicalProfile",
        back_populates="student",
        uselist=False,
        cascade="all, delete-orphan",
    )
    emergency_contacts = relationship(
        "StudentEmergencyContact",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="StudentEmergencyContact.priority_order",
    )
    notes = relationship(
        "StudentNote",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="StudentNote.is_pinned.desc(), StudentNote.id.desc()",
    )
    status_history = relationship(
        "StudentStatusHistory",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="StudentStatusHistory.id.desc()",
    )
    promotion_history = relationship(
        "StudentPromotionHistory",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="StudentPromotionHistory.id.desc()",
    )
    tags = relationship(
        "StudentTag",
        secondary=student_tag_assignments,
        back_populates="students",
    )

    __table_args__ = (
        CheckConstraint("roll_number >= 0", name="ck_student_roll_nonneg"),
        Index("idx_student_enrollment", "academic_year_id", "class_id", "section_id", "roll_number"),
        Index("idx_student_class_status", "class_id", "status", "is_deleted"),
    )

    def get_custom_fields(self) -> Dict[str, Any]:
        """Parse custom_fields_json safely into a Python dict."""
        if not self.custom_fields_json:
            return {}
        try:
            parsed = json.loads(self.custom_fields_json)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}

    def set_custom_fields(self, data: Dict[str, Any]) -> None:
        """Serialize a dict cleanly into custom_fields_json."""
        clean = {str(k).strip(): v for k, v in (data or {}).items() if str(k).strip()}
        self.custom_fields_json = json.dumps(clean, ensure_ascii=False)

    def get_tag_names(self) -> List[str]:
        if self.tags:
            return [t.name for t in self.tags]
        if self.tags_text:
            return [part for part in self.tags_text.split("|") if part]
        return []

    def __repr__(self):
        return f"<Student(id='{self.student_id}', name='{self.full_name}', roll={self.roll_number})>"


class StudentGuardianLink(Base, TimestampMixin):
    """Multiple guardians/authorized relatives linked to a student with roles & priority."""
    __tablename__ = "student_guardian_links"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    guardian_id = Column(Integer, ForeignKey("guardians.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(50), default="Father", nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    is_emergency_contact = Column(Boolean, default=True, nullable=False)
    is_financial_payer = Column(Boolean, default=False, nullable=False)
    can_pickup = Column(Boolean, default=True, nullable=False)
    priority_order = Column(Integer, default=1, nullable=False)
    notes = Column(String(255), nullable=True)

    student = relationship("Student", back_populates="guardian_links")
    guardian = relationship("Guardian", back_populates="student_links")

    __table_args__ = (
        UniqueConstraint("student_id", "guardian_id", name="uq_student_guardian_link"),
    )


class StudentFamilyRelationship(Base, TimestampMixin):
    """Sibling / relative relationships between enrolled students."""
    __tablename__ = "student_family_relationships"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    related_student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    relation_type = Column(String(40), default="Sibling", nullable=False)
    notes = Column(String(255), nullable=True)

    student = relationship("Student", foreign_keys=[student_id], back_populates="family_links")
    related_student = relationship("Student", foreign_keys=[related_student_id])

    __table_args__ = (
        CheckConstraint("student_id != related_student_id", name="ck_family_not_self"),
        UniqueConstraint("student_id", "related_student_id", name="uq_student_family_pair"),
    )


class StudentAdmissionHistory(Base, TimestampMixin):
    """Chronological admission & re-admission records per student."""
    __tablename__ = "student_admission_history"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False)
    admitted_class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False)
    admitted_section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    admission_number = Column(String(40), nullable=False)
    admission_date = Column(Date, default=date.today, nullable=False)
    admission_type = Column(String(40), default="New Admission", nullable=False)  # New Admission / Transfer-In / Readmission
    application_no = Column(String(50), nullable=True)
    admission_source = Column(String(80), nullable=True)
    previous_school = Column(String(180), nullable=True)
    entrance_score = Column(Float, nullable=True)
    remarks = Column(Text, nullable=True)
    recorded_by = Column(String(80), default="system", nullable=False)

    student = relationship("Student", back_populates="admission_history")
    academic_year = relationship("AcademicYear")
    admitted_class = relationship("SchoolClass")
    admitted_section = relationship("Section")


class StudentAcademicHistory(Base, TimestampMixin):
    """Per-academic-year enrollment, class/section/roll placement & final academic outcome."""
    __tablename__ = "student_academic_history"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    roll_number = Column(Integer, nullable=True)
    group = Column(String(40), nullable=True)
    shift = Column(String(20), nullable=True)
    gpa = Column(Float, nullable=True)
    final_grade = Column(String(15), nullable=True)
    attendance_percentage = Column(Float, nullable=True)
    result_status = Column(String(40), default="Enrolled", nullable=False)  # Enrolled / Promoted / Detained / Graduated / Transferred / Withdrawn
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    remarks = Column(String(255), nullable=True)

    student = relationship("Student", back_populates="academic_history")
    academic_year = relationship("AcademicYear")
    school_class = relationship("SchoolClass")
    section = relationship("Section")


class StudentPreviousSchool(Base, TimestampMixin):
    """Prior schools attended before admission to the institution."""
    __tablename__ = "student_previous_schools"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    school_name = Column(String(180), nullable=False)
    board_or_curriculum = Column(String(80), nullable=True)
    last_class_attended = Column(String(60), nullable=True)
    year_from = Column(Integer, nullable=True)
    year_to = Column(Integer, nullable=True)
    leaving_date = Column(Date, nullable=True)
    tc_number = Column(String(60), nullable=True)
    gpa_or_score = Column(String(30), nullable=True)
    reason_for_leaving = Column(String(255), nullable=True)
    school_address = Column(String(255), nullable=True)

    student = relationship("Student", back_populates="previous_schools")


class StudentDocument(Base, TimestampMixin):
    """Student document vault metadata (birth certificate, TC, marksheets, photos, medical reports)."""
    __tablename__ = "student_documents"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(String(60), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    file_name = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    mime_type = Column(String(80), nullable=True)
    file_size_bytes = Column(Integer, default=0, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_by = Column(String(80), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    issued_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    notes = Column(String(255), nullable=True)
    uploaded_by = Column(String(80), default="system", nullable=False)

    student = relationship("Student", back_populates="documents")


class StudentMedicalProfile(Base, TimestampMixin):
    """Dedicated 1:1 clinical/health dossier for each student."""
    __tablename__ = "student_medical_profiles"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    blood_group = Column(String(10), nullable=True)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    allergies = Column(Text, nullable=True)
    chronic_conditions = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    dietary_restrictions = Column(Text, nullable=True)
    immunization_status = Column(String(120), nullable=True)
    vision_notes = Column(String(255), nullable=True)
    disability_or_accommodation = Column(Text, nullable=True)
    physician_name = Column(String(120), nullable=True)
    physician_phone = Column(String(30), nullable=True)
    insurance_provider = Column(String(120), nullable=True)
    insurance_policy_no = Column(String(80), nullable=True)
    emergency_protocol = Column(Text, nullable=True)

    student = relationship("Student", back_populates="medical_profile")


class StudentEmergencyContact(Base, TimestampMixin):
    """Prioritized list of authorized emergency & pickup contacts."""
    __tablename__ = "student_emergency_contacts"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_name = Column(String(120), nullable=False)
    relationship_label = Column(String(60), nullable=False)
    primary_phone = Column(String(30), nullable=False)
    secondary_phone = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)
    priority_order = Column(Integer, default=1, nullable=False)
    can_pickup = Column(Boolean, default=True, nullable=False)
    notes = Column(String(255), nullable=True)

    student = relationship("Student", back_populates="emergency_contacts")


class StudentNote(Base, TimestampMixin):
    """Counselor, academic, behavioral, medical & guardian communication CRM notes."""
    __tablename__ = "student_notes"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), default="General", nullable=False, index=True)
    title = Column(String(150), nullable=False)
    content = Column(Text, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)
    is_confidential = Column(Boolean, default=False, nullable=False)
    author_username = Column(String(80), default="system", nullable=False)

    student = relationship("Student", back_populates="notes")


class StudentTag(Base, TimestampMixin):
    """Reusable CRM segmentation tags (e.g. Scholarship, Honors, Bus-Route-A, IEP)."""
    __tablename__ = "student_tags"

    name = Column(String(50), unique=True, nullable=False, index=True)
    color = Column(String(16), default="#3b82f6", nullable=False)
    description = Column(String(255), nullable=True)

    students = relationship(
        "Student",
        secondary=student_tag_assignments,
        back_populates="tags",
    )


class StudentStatusHistory(Base, TimestampMixin):
    """Audit trail of every student lifecycle status transition."""
    __tablename__ = "student_status_history"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=False, index=True)
    effective_date = Column(Date, default=date.today, nullable=False)
    reason = Column(String(255), nullable=True)
    reference_no = Column(String(80), nullable=True)
    destination_school = Column(String(180), nullable=True)
    changed_by = Column(String(80), default="system", nullable=False)
    changed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    student = relationship("Student", back_populates="status_history")


class StudentPromotionHistory(Base, TimestampMixin):
    __tablename__ = "student_promotion_history"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    from_class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False)
    to_class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False)
    from_academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False)
    to_academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False)
    promoted_date = Column(Date, default=date.today, nullable=False)
    remarks = Column(String(255), nullable=True)

    student = relationship("Student", back_populates="promotion_history")
    from_class = relationship("SchoolClass", foreign_keys=[from_class_id])
    to_class = relationship("SchoolClass", foreign_keys=[to_class_id])
    from_academic_year = relationship("AcademicYear", foreign_keys=[from_academic_year_id])
    to_academic_year = relationship("AcademicYear", foreign_keys=[to_academic_year_id])
