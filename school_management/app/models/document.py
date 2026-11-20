"""
EduManage Pro - Professional Document & Template Generation Models
Supports customizable multi-school templates, custom fields, serial numbering,
and QR-verifiable issued documents across all 10 official institutional document types.
"""

from datetime import date
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


OFFICIAL_DOCUMENT_TYPES = [
    "ID Card",
    "Character Certificate",
    "Transfer Certificate",
    "Bonafide Certificate",
    "Study Certificate",
    "Leaving Certificate",
    "Admission Receipt",
    "Fee Receipt",
    "Mark Sheet",
    "Report Card",
]

DOCUMENT_SERIAL_PREFIX = {
    "ID Card": "ID",
    "Character Certificate": "CC",
    "Transfer Certificate": "TC",
    "Bonafide Certificate": "BF",
    "Study Certificate": "SC",
    "Leaving Certificate": "LC",
    "Admission Receipt": "ADM",
    "Fee Receipt": "FEE",
    "Mark Sheet": "MS",
    "Report Card": "RC",
}

PAGE_SIZES = ["A4", "Letter", "A5", "CR80"]
ORIENTATIONS = ["Portrait", "Landscape"]
BORDER_STYLES = ["Double", "Classic", "Modern", "Minimal", "None"]
FONT_FAMILIES = ["Helvetica", "Times-Roman", "Courier"]


class DocumentTemplate(Base, TimestampMixin, SoftDeleteMixin):
    """
    Reusable, school-agnostic document layout & branding template.
    Schools can create, clone, edit colors, fonts, logos, signatures,
    custom fields, header/body/footer templates, and toggle visual elements.
    """

    __tablename__ = "document_templates"

    template_code = Column(String(60), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    document_type = Column(String(50), nullable=False, index=True)
    description = Column(String(255), nullable=True)
    is_default = Column(Boolean, default=False, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Page Setup
    page_size = Column(String(20), default="A4", nullable=False)
    orientation = Column(String(20), default="Portrait", nullable=False)
    border_style = Column(String(30), default="Double", nullable=False)
    font_family = Column(String(40), default="Helvetica", nullable=False)

    # Configurable Visual Theme (never hard-coded to one school)
    primary_color = Column(String(20), default="#1E3A8A", nullable=False)
    secondary_color = Column(String(20), default="#0F172A", nullable=False)
    accent_color = Column(String(20), default="#D97706", nullable=False)
    text_color = Column(String(20), default="#1E293B", nullable=False)
    background_color = Column(String(20), default="#FFFFFF", nullable=False)

    # School Info & Asset Overrides
    use_school_profile = Column(Boolean, default=True, nullable=False)
    school_name_override = Column(String(200), nullable=True)
    school_subtitle_override = Column(String(255), nullable=True)
    school_address_override = Column(String(255), nullable=True)
    logo_path = Column(String(255), nullable=True)
    watermark_text = Column(String(120), nullable=True)

    # Configurable Copy & Placeholder Templates
    header_text = Column(String(200), nullable=False, default="OFFICIAL DOCUMENT")
    subheader_text = Column(String(255), nullable=True)
    body_template = Column(Text, nullable=False, default="")
    footer_text = Column(Text, nullable=True)

    # Signatories & Signature / Seal Image Assets
    signature_left_label = Column(String(100), default="Academic Registrar", nullable=True)
    signature_left_name = Column(String(120), nullable=True)
    signature_left_image_path = Column(String(255), nullable=True)
    signature_right_label = Column(String(100), default="Principal", nullable=True)
    signature_right_name = Column(String(120), nullable=True)
    signature_right_image_path = Column(String(255), nullable=True)
    seal_image_path = Column(String(255), nullable=True)

    # Feature Visibility Toggles
    show_logo = Column(Boolean, default=True, nullable=False)
    show_qr = Column(Boolean, default=True, nullable=False)
    show_serial = Column(Boolean, default=True, nullable=False)
    show_photo = Column(Boolean, default=True, nullable=False)
    show_border = Column(Boolean, default=True, nullable=False)
    show_seal = Column(Boolean, default=True, nullable=False)
    show_signatures = Column(Boolean, default=True, nullable=False)
    show_custom_fields = Column(Boolean, default=True, nullable=False)

    # Dynamic Custom Fields Schema: JSON list of {"key", "label", "type", "required", "default_value"}
    custom_fields_schema_json = Column(Text, default="[]", nullable=False)

    issued_documents = relationship("IssuedDocument", back_populates="template")

    def __repr__(self):
        return f"<DocumentTemplate(code='{self.template_code}', type='{self.document_type}', default={self.is_default})>"


class IssuedDocument(Base, TimestampMixin, SoftDeleteMixin):
    """
    Immutable audit & verification record for every generated official document,
    certificate, ID card, receipt, mark sheet, and report card.
    """

    __tablename__ = "issued_documents"

    serial_number = Column(String(60), unique=True, nullable=False, index=True)
    verification_code = Column(String(40), unique=True, nullable=False, index=True)
    qr_payload = Column(Text, nullable=False)
    document_type = Column(String(50), nullable=False, index=True)
    template_id = Column(
        Integer,
        ForeignKey("document_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    recipient_type = Column(String(20), default="Student", nullable=False)  # Student | Teacher | Staff | Applicant
    recipient_name = Column(String(150), nullable=False, index=True)
    recipient_code = Column(String(60), nullable=False, index=True)

    # Optional Entity Foreign Keys
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="SET NULL"), nullable=True, index=True)
    admission_application_id = Column(
        Integer, ForeignKey("admission_applications.id", ondelete="SET NULL"), nullable=True, index=True
    )
    admission_payment_id = Column(
        Integer, ForeignKey("admission_fee_payments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fee_payment_id = Column(Integer, ForeignKey("fee_payments.id", ondelete="SET NULL"), nullable=True, index=True)
    exam_term_id = Column(Integer, ForeignKey("exam_terms.id", ondelete="SET NULL"), nullable=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True)

    issue_date = Column(Date, default=date.today, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    rendered_body = Column(Text, nullable=False, default="")

    # Frozen Snapshots for Authentic Reprinting & Offline Verification
    school_snapshot_json = Column(Text, default="{}", nullable=False)
    recipient_snapshot_json = Column(Text, default="{}", nullable=False)
    table_rows_json = Column(Text, default="[]", nullable=False)
    summary_metrics_json = Column(Text, default="{}", nullable=False)
    custom_fields_values_json = Column(Text, default="{}", nullable=False)

    pdf_path = Column(String(300), nullable=True)
    issued_by = Column(String(100), default="Admin Office", nullable=False)
    status = Column(String(20), default="Issued", nullable=False, index=True)  # Issued | Revoked
    revoked_reason = Column(String(255), nullable=True)
    revoked_by = Column(String(100), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    print_count = Column(Integer, default=0, nullable=False)

    template = relationship("DocumentTemplate", back_populates="issued_documents")
    student = relationship("Student")
    teacher = relationship("Teacher")
    staff = relationship("Staff")
    admission_application = relationship("AdmissionApplication")
    admission_payment = relationship("AdmissionFeePayment")
    fee_payment = relationship("FeePayment")
    exam_term = relationship("ExamTerm")
    academic_year = relationship("AcademicYear")

    def __repr__(self):
        return f"<IssuedDocument(serial='{self.serial_number}', type='{self.document_type}', status='{self.status}')>"
