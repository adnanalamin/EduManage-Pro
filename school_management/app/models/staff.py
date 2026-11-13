"""
EduManage Pro - Teacher, Staff & Complete HR Management Models (SQLAlchemy)
Normalized models for faculty, non-teaching personnel, qualifications, experience,
subject assignments, contracts, leave requests & approvals, documents,
salary history, performance evaluations, lifecycle events, and emergency contacts.
"""

from datetime import date
from typing import Dict, List

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


class EmployeeStatus:
    ACTIVE = "active"
    PROBATION = "probation"
    ON_LEAVE = "on_leave"
    SUSPENDED = "suspended"
    RESIGNED = "resigned"
    RETIRED = "retired"
    TERMINATED = "terminated"
    ARCHIVED = "archived"

    ALL: List[str] = [
        ACTIVE,
        PROBATION,
        ON_LEAVE,
        SUSPENDED,
        RESIGNED,
        RETIRED,
        TERMINATED,
        ARCHIVED,
    ]

    LABELS: Dict[str, str] = {
        ACTIVE: "Active",
        PROBATION: "Probation",
        ON_LEAVE: "On Leave",
        SUSPENDED: "Suspended",
        RESIGNED: "Resigned",
        RETIRED: "Retired",
        TERMINATED: "Terminated",
        ARCHIVED: "Archived",
    }


STAFF_ROLE_CATALOG: List[str] = [
    "Office Staff",
    "Office Assistant",
    "Accountant",
    "Receptionist",
    "Librarian",
    "Security Supervisor",
    "Security Guard",
    "Support Staff",
    "IT / Lab Technician",
    "Transport Supervisor",
    "Hostel Warden",
]


class Department(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "departments"

    name = Column(String(80), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    teachers = relationship("Teacher", back_populates="department")
    staff = relationship("Staff", back_populates="department")

    def __repr__(self):
        return f"<Department(name='{self.name}', code='{self.code}')>"


class Teacher(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "teachers"

    # Identifiers
    teacher_id = Column(String(40), unique=True, nullable=False, index=True)
    employee_id = Column(String(40), unique=True, nullable=False, index=True)

    # Personal Information
    full_name = Column(String(120), nullable=False, index=True)
    full_name_bn = Column(String(120), nullable=True)
    gender = Column(String(15), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    blood_group = Column(String(10), nullable=True)
    photo_path = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    address = Column(Text, nullable=True)
    nid_number = Column(String(50), unique=True, nullable=True)

    # Professional & Academic
    qualification = Column(String(150), nullable=False)
    designation = Column(String(80), default="Assistant Teacher", nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True)
    primary_subject = Column(String(80), nullable=False)
    joining_date = Column(Date, default=date.today, nullable=False)
    experience_years = Column(Float, default=0.0, nullable=False)
    contract_type = Column(String(40), default="Permanent", nullable=False)

    # Emergency Summary
    emergency_contact_name = Column(String(120), nullable=True)
    emergency_contact_phone = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)

    # Financial & Contract
    salary = Column(Integer, default=35000, nullable=False)
    bank_account_no = Column(String(60), nullable=True)
    bank_name = Column(String(100), nullable=True)

    # Status
    status = Column(String(20), default=EmployeeStatus.ACTIVE, nullable=False, index=True)

    # Relationships
    department = relationship("Department", back_populates="teachers")
    qualifications = relationship(
        "EmployeeQualification",
        back_populates="teacher",
        cascade="all, delete-orphan",
        order_by="EmployeeQualification.id.desc()",
    )
    experiences = relationship(
        "EmployeeExperience",
        back_populates="teacher",
        cascade="all, delete-orphan",
        order_by="EmployeeExperience.id.desc()",
    )
    subject_assignments = relationship(
        "TeacherSubjectAssignment",
        back_populates="teacher",
        cascade="all, delete-orphan",
        order_by="TeacherSubjectAssignment.id.desc()",
    )
    contracts = relationship(
        "EmployeeContract",
        back_populates="teacher",
        cascade="all, delete-orphan",
        order_by="EmployeeContract.start_date.desc()",
    )
    leave_requests = relationship(
        "EmployeeLeaveRequest",
        back_populates="teacher",
        cascade="all, delete-orphan",
        order_by="EmployeeLeaveRequest.id.desc()",
    )
    documents = relationship(
        "EmployeeDocument",
        back_populates="teacher",
        cascade="all, delete-orphan",
        order_by="EmployeeDocument.id.desc()",
    )
    salary_history = relationship(
        "EmployeeSalaryHistory",
        back_populates="teacher",
        cascade="all, delete-orphan",
        order_by="EmployeeSalaryHistory.effective_date.desc(), EmployeeSalaryHistory.id.desc()",
    )
    evaluations = relationship(
        "EmployeePerformanceEvaluation",
        back_populates="teacher",
        cascade="all, delete-orphan",
        order_by="EmployeePerformanceEvaluation.review_date.desc()",
    )
    lifecycle_events = relationship(
        "EmployeeLifecycleEvent",
        back_populates="teacher",
        cascade="all, delete-orphan",
        order_by="EmployeeLifecycleEvent.effective_date.desc(), EmployeeLifecycleEvent.id.desc()",
    )
    emergency_contacts = relationship(
        "EmployeeEmergencyContact",
        back_populates="teacher",
        cascade="all, delete-orphan",
        order_by="EmployeeEmergencyContact.priority_order",
    )

    __table_args__ = (
        CheckConstraint("salary >= 0", name="ck_teacher_salary_nonneg"),
        Index("idx_teacher_status_deleted", "status", "is_deleted"),
    )

    def __repr__(self):
        return f"<Teacher(id='{self.teacher_id}', name='{self.full_name}', dept='{self.primary_subject}')>"


class Staff(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "staff_members"

    # Identifiers
    staff_id = Column(String(40), unique=True, nullable=False, index=True)
    employee_id = Column(String(40), unique=True, nullable=False, index=True)

    # Personal
    full_name = Column(String(120), nullable=False, index=True)
    full_name_bn = Column(String(120), nullable=True)
    gender = Column(String(15), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    photo_path = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=False, index=True)
    email = Column(String(120), nullable=True, index=True)
    address = Column(Text, nullable=True)
    nid_number = Column(String(50), unique=True, nullable=True)

    # Role & Department
    position = Column(String(80), nullable=False, index=True)
    qualification = Column(String(150), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True)
    shift = Column(String(20), default="Day", nullable=False)
    joining_date = Column(Date, default=date.today, nullable=False)
    experience_years = Column(Float, default=0.0, nullable=False)
    contract_type = Column(String(40), default="Permanent", nullable=False)

    # Emergency Summary
    emergency_contact_name = Column(String(120), nullable=True)
    emergency_contact_phone = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)

    # Compensation
    salary = Column(Integer, default=22000, nullable=False)
    bank_account_no = Column(String(60), nullable=True)
    bank_name = Column(String(100), nullable=True)
    status = Column(String(20), default=EmployeeStatus.ACTIVE, nullable=False, index=True)

    # Relationships
    department = relationship("Department", back_populates="staff")
    qualifications = relationship(
        "EmployeeQualification",
        back_populates="staff",
        cascade="all, delete-orphan",
        order_by="EmployeeQualification.id.desc()",
    )
    experiences = relationship(
        "EmployeeExperience",
        back_populates="staff",
        cascade="all, delete-orphan",
        order_by="EmployeeExperience.id.desc()",
    )
    contracts = relationship(
        "EmployeeContract",
        back_populates="staff",
        cascade="all, delete-orphan",
        order_by="EmployeeContract.start_date.desc()",
    )
    leave_requests = relationship(
        "EmployeeLeaveRequest",
        back_populates="staff",
        cascade="all, delete-orphan",
        order_by="EmployeeLeaveRequest.id.desc()",
    )
    documents = relationship(
        "EmployeeDocument",
        back_populates="staff",
        cascade="all, delete-orphan",
        order_by="EmployeeDocument.id.desc()",
    )
    salary_history = relationship(
        "EmployeeSalaryHistory",
        back_populates="staff",
        cascade="all, delete-orphan",
        order_by="EmployeeSalaryHistory.effective_date.desc(), EmployeeSalaryHistory.id.desc()",
    )
    evaluations = relationship(
        "EmployeePerformanceEvaluation",
        back_populates="staff",
        cascade="all, delete-orphan",
        order_by="EmployeePerformanceEvaluation.review_date.desc()",
    )
    lifecycle_events = relationship(
        "EmployeeLifecycleEvent",
        back_populates="staff",
        cascade="all, delete-orphan",
        order_by="EmployeeLifecycleEvent.effective_date.desc(), EmployeeLifecycleEvent.id.desc()",
    )
    emergency_contacts = relationship(
        "EmployeeEmergencyContact",
        back_populates="staff",
        cascade="all, delete-orphan",
        order_by="EmployeeEmergencyContact.priority_order",
    )

    __table_args__ = (
        CheckConstraint("salary >= 0", name="ck_staff_salary_nonneg"),
        Index("idx_staff_status_deleted", "status", "is_deleted"),
    )

    def __repr__(self):
        return f"<Staff(id='{self.staff_id}', name='{self.full_name}', pos='{self.position}')>"


class EmployeeQualification(Base, TimestampMixin):
    __tablename__ = "hr_qualifications"

    employee_type = Column(String(20), nullable=False, index=True)  # "teacher" | "staff"
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="CASCADE"), nullable=True, index=True)
    degree_or_cert = Column(String(120), nullable=False)
    institution = Column(String(160), nullable=False)
    specialization = Column(String(120), nullable=True)
    completion_year = Column(Integer, nullable=True)
    grade_or_division = Column(String(40), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)

    teacher = relationship("Teacher", back_populates="qualifications")
    staff = relationship("Staff", back_populates="qualifications")

    __table_args__ = (
        CheckConstraint(
            "(teacher_id IS NOT NULL AND staff_id IS NULL) OR (teacher_id IS NULL AND staff_id IS NOT NULL)",
            name="ck_hr_qual_single_emp",
        ),
    )


class EmployeeExperience(Base, TimestampMixin):
    __tablename__ = "hr_experiences"

    employee_type = Column(String(20), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="CASCADE"), nullable=True, index=True)
    organization = Column(String(160), nullable=False)
    designation = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_current = Column(Boolean, default=False, nullable=False)
    responsibilities = Column(Text, nullable=True)

    teacher = relationship("Teacher", back_populates="experiences")
    staff = relationship("Staff", back_populates="experiences")

    __table_args__ = (
        CheckConstraint(
            "(teacher_id IS NOT NULL AND staff_id IS NULL) OR (teacher_id IS NULL AND staff_id IS NOT NULL)",
            name="ck_hr_exp_single_emp",
        ),
    )


class TeacherSubjectAssignment(Base, TimestampMixin):
    __tablename__ = "hr_teacher_subject_assignments"

    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_primary = Column(Boolean, default=True, nullable=False)
    weekly_periods = Column(Integer, default=5, nullable=False)
    remarks = Column(String(255), nullable=True)

    teacher = relationship("Teacher", back_populates="subject_assignments")
    subject = relationship("Subject")
    school_class = relationship("SchoolClass")
    section = relationship("Section")
    academic_year = relationship("AcademicYear")

    __table_args__ = (
        UniqueConstraint(
            "teacher_id", "subject_id", "class_id", "section_id", "academic_year_id",
            name="uq_hr_teacher_subject_class",
        ),
    )


class EmployeeContract(Base, TimestampMixin):
    __tablename__ = "hr_contracts"

    employee_type = Column(String(20), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="CASCADE"), nullable=True, index=True)
    contract_number = Column(String(50), unique=True, nullable=False, index=True)
    contract_type = Column(String(40), default="Permanent", nullable=False)  # Permanent / Probation / Fixed-Term / Part-Time
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    probation_end_date = Column(Date, nullable=True)
    basic_salary = Column(Integer, default=0, nullable=False)
    allowances = Column(Integer, default=0, nullable=False)
    working_hours_per_week = Column(Integer, default=40, nullable=False)
    status = Column(String(30), default="Active", nullable=False, index=True)  # Active / Expired / Terminated / Renewed
    signed_date = Column(Date, nullable=True)
    terms_summary = Column(Text, nullable=True)
    created_by = Column(String(80), default="admin", nullable=False)

    teacher = relationship("Teacher", back_populates="contracts")
    staff = relationship("Staff", back_populates="contracts")

    __table_args__ = (
        CheckConstraint("basic_salary >= 0 AND allowances >= 0", name="ck_hr_contract_sal_nonneg"),
        CheckConstraint(
            "(teacher_id IS NOT NULL AND staff_id IS NULL) OR (teacher_id IS NULL AND staff_id IS NOT NULL)",
            name="ck_hr_contract_single_emp",
        ),
    )


class EmployeeLeaveRequest(Base, TimestampMixin):
    __tablename__ = "hr_leave_requests"

    employee_type = Column(String(20), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="CASCADE"), nullable=True, index=True)
    leave_type = Column(String(40), default="Casual", nullable=False, index=True)  # Casual, Sick, Annual, Maternity/Paternity, Study, Unpaid
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_days = Column(Integer, default=1, nullable=False)
    reason = Column(Text, nullable=False)
    backup_assignee = Column(String(120), nullable=True)
    status = Column(String(20), default="Pending", nullable=False, index=True)  # Pending / Approved / Rejected / Cancelled
    reviewed_by = Column(String(80), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_remarks = Column(String(255), nullable=True)

    teacher = relationship("Teacher", back_populates="leave_requests")
    staff = relationship("Staff", back_populates="leave_requests")

    __table_args__ = (
        CheckConstraint("total_days >= 1", name="ck_hr_leave_days_pos"),
        CheckConstraint(
            "(teacher_id IS NOT NULL AND staff_id IS NULL) OR (teacher_id IS NULL AND staff_id IS NOT NULL)",
            name="ck_hr_leave_single_emp",
        ),
    )


class EmployeeDocument(Base, TimestampMixin):
    __tablename__ = "hr_documents"

    employee_type = Column(String(20), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="CASCADE"), nullable=True, index=True)
    document_type = Column(String(60), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    file_name = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, default=0, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_by = Column(String(80), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    issued_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    notes = Column(String(255), nullable=True)
    uploaded_by = Column(String(80), default="admin", nullable=False)

    teacher = relationship("Teacher", back_populates="documents")
    staff = relationship("Staff", back_populates="documents")

    __table_args__ = (
        CheckConstraint(
            "(teacher_id IS NOT NULL AND staff_id IS NULL) OR (teacher_id IS NULL AND staff_id IS NOT NULL)",
            name="ck_hr_doc_single_emp",
        ),
    )


class EmployeeSalaryHistory(Base, TimestampMixin):
    __tablename__ = "hr_salary_history"

    employee_type = Column(String(20), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="CASCADE"), nullable=True, index=True)
    previous_salary = Column(Integer, default=0, nullable=False)
    new_salary = Column(Integer, nullable=False)
    allowances = Column(Integer, default=0, nullable=False)
    effective_date = Column(Date, default=date.today, nullable=False)
    change_reason = Column(String(80), default="Initial Hiring", nullable=False)
    reference_no = Column(String(60), nullable=True)
    remarks = Column(String(255), nullable=True)
    approved_by = Column(String(80), default="admin", nullable=False)

    teacher = relationship("Teacher", back_populates="salary_history")
    staff = relationship("Staff", back_populates="salary_history")

    __table_args__ = (
        CheckConstraint("previous_salary >= 0 AND new_salary >= 0 AND allowances >= 0", name="ck_hr_salhist_nonneg"),
        CheckConstraint(
            "(teacher_id IS NOT NULL AND staff_id IS NULL) OR (teacher_id IS NULL AND staff_id IS NOT NULL)",
            name="ck_hr_salhist_single_emp",
        ),
    )


class EmployeePerformanceEvaluation(Base, TimestampMixin):
    __tablename__ = "hr_evaluations"

    employee_type = Column(String(20), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="CASCADE"), nullable=True, index=True)
    review_period = Column(String(60), nullable=False)  # e.g., "2025 Annual", "2026 Q1"
    review_date = Column(Date, default=date.today, nullable=False)
    reviewer_name = Column(String(120), nullable=False)
    punctuality_score = Column(Float, default=4.0, nullable=False)
    competency_score = Column(Float, default=4.0, nullable=False)
    teamwork_score = Column(Float, default=4.0, nullable=False)
    compliance_score = Column(Float, default=4.0, nullable=False)
    overall_rating = Column(Float, default=4.0, nullable=False)
    rating_band = Column(String(40), default="Exceeds Expectations", nullable=False)
    strengths = Column(Text, nullable=True)
    areas_for_improvement = Column(Text, nullable=True)
    goals = Column(Text, nullable=True)
    status = Column(String(30), default="Finalized", nullable=False)

    teacher = relationship("Teacher", back_populates="evaluations")
    staff = relationship("Staff", back_populates="evaluations")

    __table_args__ = (
        CheckConstraint("overall_rating >= 0 AND overall_rating <= 5", name="ck_hr_eval_rating_range"),
        CheckConstraint(
            "(teacher_id IS NOT NULL AND staff_id IS NULL) OR (teacher_id IS NULL AND staff_id IS NOT NULL)",
            name="ck_hr_eval_single_emp",
        ),
    )


class EmployeeLifecycleEvent(Base, TimestampMixin):
    """Audit trail of Joining, Promotion, Transfer, Status Changes, and Separation."""
    __tablename__ = "hr_lifecycle_events"

    employee_type = Column(String(20), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="CASCADE"), nullable=True, index=True)
    event_type = Column(String(40), nullable=False, index=True)  # Joined, Promotion, Transfer, Status Change, Contract Renewed
    effective_date = Column(Date, default=date.today, nullable=False)
    from_designation = Column(String(100), nullable=True)
    to_designation = Column(String(100), nullable=True)
    from_department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    to_department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=True)
    reference_no = Column(String(60), nullable=True)
    reason = Column(String(255), nullable=True)
    recorded_by = Column(String(80), default="admin", nullable=False)
    recorded_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    teacher = relationship("Teacher", back_populates="lifecycle_events")
    staff = relationship("Staff", back_populates="lifecycle_events")
    from_department = relationship("Department", foreign_keys=[from_department_id])
    to_department = relationship("Department", foreign_keys=[to_department_id])

    __table_args__ = (
        CheckConstraint(
            "(teacher_id IS NOT NULL AND staff_id IS NULL) OR (teacher_id IS NULL AND staff_id IS NOT NULL)",
            name="ck_hr_event_single_emp",
        ),
    )


class EmployeeEmergencyContact(Base, TimestampMixin):
    __tablename__ = "hr_emergency_contacts"

    employee_type = Column(String(20), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="CASCADE"), nullable=True, index=True)
    contact_name = Column(String(120), nullable=False)
    relationship_label = Column(String(60), nullable=False)
    primary_phone = Column(String(30), nullable=False)
    secondary_phone = Column(String(30), nullable=True)
    address = Column(String(255), nullable=True)
    priority_order = Column(Integer, default=1, nullable=False)
    is_primary = Column(Boolean, default=True, nullable=False)

    teacher = relationship("Teacher", back_populates="emergency_contacts")
    staff = relationship("Staff", back_populates="emergency_contacts")

    __table_args__ = (
        CheckConstraint(
            "(teacher_id IS NOT NULL AND staff_id IS NULL) OR (teacher_id IS NULL AND staff_id IS NOT NULL)",
            name="ck_hr_ec_single_emp",
        ),
    )
