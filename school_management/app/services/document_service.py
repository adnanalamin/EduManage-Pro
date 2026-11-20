"""
EduManage Pro - Professional Document & Template Generation Service
Handles customizable template management (school-agnostic), dynamic custom fields,
real-DB context hydration across all 10 document types, sequential serial numbering,
QR verification payloads, and live preview / issuance workflows.
"""

from datetime import date
import json
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from app.models.academic import AcademicYear
from app.models.admission import AdmissionApplication, AdmissionFeePayment
from app.models.base import utc_now
from app.models.document import (
    DOCUMENT_SERIAL_PREFIX,
    OFFICIAL_DOCUMENT_TYPES,
    DocumentTemplate,
    IssuedDocument,
)
from app.models.exam import ExamResultSummary, ExamTerm, StudentMark
from app.models.fee import FeePayment
from app.models.school import SchoolSetting
from app.models.staff import Staff, Teacher
from app.models.student import Student


def _safe_json_loads(raw: Optional[str], fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except Exception:
        return fallback


def _fmt_date(val: Any) -> str:
    if not val:
        return "N/A"
    if hasattr(val, "strftime"):
        return val.strftime("%d %b %Y")
    return str(val)


DEFAULT_TEMPLATE_PRESETS: List[Dict[str, Any]] = [
    {
        "template_code": "TPL-ID-CLASSIC",
        "name": "ID Card — Classic Crest (CR80)",
        "document_type": "ID Card",
        "description": "Standard CR80 landscape identity card with photo, QR verification, and signatory strip.",
        "is_default": True,
        "page_size": "CR80",
        "orientation": "Landscape",
        "border_style": "Modern",
        "font_family": "Helvetica",
        "primary_color": "#1E3A8A",
        "secondary_color": "#0F172A",
        "accent_color": "#D97706",
        "text_color": "#0F172A",
        "background_color": "#FFFFFF",
        "header_text": "IDENTITY CARD",
        "subheader_text": "Authorized Institutional Credential • {{academic_year}}",
        "body_template": (
            "Name: {{recipient_name}}\n"
            "ID: {{recipient_code}} | Class/Role: {{class_or_designation}}\n"
            "Blood Group: {{blood_group}} | Emergency: {{emergency_contact}}"
        ),
        "footer_text": "If found, please return to {{school_name}} ({{school_phone}}).",
        "signature_left_label": "Holder Signature",
        "signature_right_label": "Principal / Authorized Signatory",
        "show_photo": True,
        "show_qr": True,
        "show_seal": False,
        "custom_fields_schema_json": json.dumps([
            {"key": "valid_until", "label": "Valid Until", "type": "text", "required": False, "default_value": "31 Dec 2026"},
            {"key": "transport_route", "label": "Route / House", "type": "text", "required": False, "default_value": "Main Campus"},
        ]),
    },
    {
        "template_code": "TPL-ID-EMERALD",
        "name": "ID Card — Modern Emerald (CR80)",
        "document_type": "ID Card",
        "description": "Alternative emerald/slate ID card theme demonstrating multi-school design customization.",
        "is_default": False,
        "page_size": "CR80",
        "orientation": "Landscape",
        "border_style": "Minimal",
        "font_family": "Helvetica",
        "primary_color": "#065F46",
        "secondary_color": "#064E3B",
        "accent_color": "#10B981",
        "text_color": "#0F172A",
        "background_color": "#F8FAFC",
        "header_text": "SMART CAMPUS ID PASS",
        "subheader_text": "{{academic_year}} Academic Session",
        "body_template": (
            "Holder: {{recipient_name}} ({{recipient_code}})\n"
            "Program / Dept: {{class_or_designation}}\n"
            "Guardian / Contact: {{guardian_name}} ({{guardian_phone}})"
        ),
        "footer_text": "Verified Digital Credential • {{school_website}}",
        "signature_left_label": "Cardholder",
        "signature_right_label": "Head of Institution",
        "show_photo": True,
        "show_qr": True,
        "show_seal": False,
        "custom_fields_schema_json": json.dumps([
            {"key": "valid_until", "label": "Valid Thru", "type": "text", "required": False, "default_value": "Dec 2026"},
            {"key": "card_category", "label": "Access Tier", "type": "text", "required": False, "default_value": "Full Campus & Library"},
        ]),
    },
    {
        "template_code": "TPL-CC-HERITAGE",
        "name": "Character Certificate — Heritage Gold",
        "document_type": "Character Certificate",
        "description": "Landscape A4 ornate character & moral conduct testimonial certificate.",
        "is_default": True,
        "page_size": "A4",
        "orientation": "Landscape",
        "border_style": "Double",
        "font_family": "Times-Roman",
        "primary_color": "#1E3A8A",
        "secondary_color": "#1E293B",
        "accent_color": "#B45309",
        "text_color": "#1E293B",
        "background_color": "#FFFDF7",
        "header_text": "CHARACTER CERTIFICATE",
        "subheader_text": "TO WHOM IT MAY CONCERN",
        "body_template": (
            "This is to certify that {{recipient_name}} (Student ID: {{recipient_code}}), "
            "Son/Daughter of {{father_name}} and {{mother_name}}, has been a bonafide student of "
            "{{class_or_designation}} at {{school_name}} during academic session {{academic_year}}.\n\n"
            "According to institutional records, his/her moral character, personal conduct, and "
            "disciplinary standing are rated as {{conduct_grade}}. He/She did not participate in any "
            "activity detrimental to academic harmony. This certificate is issued on {{issue_date}} "
            "for {{purpose}}."
        ),
        "footer_text": "Issued with institutional seal and QR authenticity verification.",
        "signature_left_label": "Class Teacher / Proctor",
        "signature_right_label": "Principal & Head of Institution",
        "show_photo": False,
        "show_qr": True,
        "show_seal": True,
        "custom_fields_schema_json": json.dumps([
            {"key": "conduct_grade", "label": "Character & Conduct Grade", "type": "text", "required": True, "default_value": "Exemplary"},
            {"key": "purpose", "label": "Purpose of Issuance", "type": "text", "required": True, "default_value": "Higher Education & Official Verification"},
        ]),
    },
    {
        "template_code": "TPL-TC-OFFICIAL",
        "name": "Transfer Certificate — Official Registrar",
        "document_type": "Transfer Certificate",
        "description": "Formal institutional Transfer Certificate (TC) with clearance, dues, and leaving details.",
        "is_default": True,
        "page_size": "A4",
        "orientation": "Landscape",
        "border_style": "Double",
        "font_family": "Times-Roman",
        "primary_color": "#7F1D1D",
        "secondary_color": "#450A0A",
        "accent_color": "#D97706",
        "text_color": "#1E293B",
        "background_color": "#FFFDF9",
        "header_text": "TRANSFER CERTIFICATE",
        "subheader_text": "OFFICIAL INSTITUTIONAL CLEARANCE & RELEASE",
        "body_template": (
            "This is to certify that {{recipient_name}} (Admission No: {{admission_number}}, "
            "Student ID: {{recipient_code}}), Son/Daughter of {{father_name}} & {{mother_name}}, "
            "Date of Birth {{date_of_birth}}, was enrolled in {{class_or_designation}} at {{school_name}}.\n\n"
            "All tuition fees, library books, hostel/transport dues, and laboratory clearances have been "
            "settled through {{leaving_date}}. Conduct during tenure is certified as {{conduct_grade}}. "
            "Reason for leaving: {{leaving_reason}}. Eligibility for next grade: {{promotion_status}}."
        ),
        "footer_text": "Verify online or via QR scan against {{serial_number}}.",
        "signature_left_label": "Academic Registrar",
        "signature_right_label": "Principal",
        "show_photo": True,
        "show_qr": True,
        "show_seal": True,
        "custom_fields_schema_json": json.dumps([
            {"key": "leaving_date", "label": "Effective Leaving Date", "type": "text", "required": True, "default_value": date.today().strftime("%d %b %Y")},
            {"key": "leaving_reason", "label": "Reason for Transfer", "type": "text", "required": True, "default_value": "Guardian Relocation / Transfer"},
            {"key": "conduct_grade", "label": "Conduct Standing", "type": "text", "required": True, "default_value": "Very Good"},
            {"key": "promotion_status", "label": "Promotion / Eligibility", "type": "text", "required": False, "default_value": "Qualified for Next Class"},
        ]),
    },
    {
        "template_code": "TPL-BF-STANDARD",
        "name": "Bonafide Certificate — Classic Blue",
        "document_type": "Bonafide Certificate",
        "description": "Portrait/Landscape confirmation of active student enrollment for visa, bank, or scholarship use.",
        "is_default": True,
        "page_size": "A4",
        "orientation": "Portrait",
        "border_style": "Classic",
        "font_family": "Times-Roman",
        "primary_color": "#1D4ED8",
        "secondary_color": "#1E3A8A",
        "accent_color": "#0284C7",
        "text_color": "#0F172A",
        "background_color": "#FFFFFF",
        "header_text": "BONAFIDE STUDENT CERTIFICATE",
        "subheader_text": "CERTIFICATE OF CURRENT ENROLLMENT",
        "body_template": (
            "This is to certify that {{recipient_name}} (Student ID: {{recipient_code}}, "
            "Admission No: {{admission_number}}), Son/Daughter of {{father_name}}, residing at {{address}}, "
            "is a bonafide regular student of this institution currently studying in {{class_or_designation}} "
            "for the academic year {{academic_year}}.\n\n"
            "According to the admission register, his/her date of birth is {{date_of_birth}}. "
            "This certificate is issued on {{issue_date}} upon request for {{purpose}}."
        ),
        "footer_text": "Valid for 90 days from date of issuance for stated verification purpose.",
        "signature_left_label": "Office Secretary / Registrar",
        "signature_right_label": "Principal",
        "show_photo": True,
        "show_qr": True,
        "show_seal": True,
        "custom_fields_schema_json": json.dumps([
            {"key": "purpose", "label": "Verification Purpose", "type": "text", "required": True, "default_value": "Passport / Scholarship / Bank Account"},
            {"key": "valid_days", "label": "Validity Period", "type": "text", "required": False, "default_value": "90 Days"},
        ]),
    },
    {
        "template_code": "TPL-SC-ACADEMIC",
        "name": "Study Certificate — Academic Indigo",
        "document_type": "Study Certificate",
        "description": "Official confirmation of years and classes studied at the institution.",
        "is_default": True,
        "page_size": "A4",
        "orientation": "Portrait",
        "border_style": "Classic",
        "font_family": "Times-Roman",
        "primary_color": "#312E81",
        "secondary_color": "#1E1B4B",
        "accent_color": "#6366F1",
        "text_color": "#1E293B",
        "background_color": "#FFFFFF",
        "header_text": "STUDY CERTIFICATE",
        "subheader_text": "ACADEMIC ATTENDANCE & TENURE RECORD",
        "body_template": (
            "This is to certify that {{recipient_name}} (Student ID: {{recipient_code}}), "
            "ward of {{father_name}}, studied as a regular student in {{school_name}} from "
            "{{study_period_from}} to {{study_period_to}} in {{class_or_designation}}.\n\n"
            "His/Her medium of instruction was {{medium_of_instruction}}, and his/her attendance and "
            "scholastic record during the stated tenure were verified as satisfactory. Issued on {{issue_date}}."
        ),
        "footer_text": "Certified true extract from the Academic Enrollment Register.",
        "signature_left_label": "Academic Coordinator",
        "signature_right_label": "Principal",
        "show_photo": False,
        "show_qr": True,
        "show_seal": True,
        "custom_fields_schema_json": json.dumps([
            {"key": "study_period_from", "label": "Studied From (Year/Date)", "type": "text", "required": True, "default_value": "Jan 2024"},
            {"key": "study_period_to", "label": "Studied To (Year/Date)", "type": "text", "required": True, "default_value": "Present"},
            {"key": "medium_of_instruction", "label": "Medium of Instruction", "type": "text", "required": False, "default_value": "English"},
        ]),
    },
    {
        "template_code": "TPL-LC-FORMAL",
        "name": "Leaving Certificate — Institutional Record",
        "document_type": "Leaving Certificate",
        "description": "Comprehensive School Leaving Certificate documenting tenure, final examination standing, and dues clearance.",
        "is_default": True,
        "page_size": "A4",
        "orientation": "Portrait",
        "border_style": "Double",
        "font_family": "Times-Roman",
        "primary_color": "#0F766E",
        "secondary_color": "#134E4A",
        "accent_color": "#D97706",
        "text_color": "#0F172A",
        "background_color": "#FFFFFF",
        "header_text": "SCHOOL LEAVING CERTIFICATE",
        "subheader_text": "FORMAL COMPLETION & DEPARTURE RECORD",
        "body_template": (
            "Certified that {{recipient_name}} (Admission No: {{admission_number}}, Student ID: {{recipient_code}}), "
            "Son/Daughter of {{father_name}} & {{mother_name}}, entered {{school_name}} on {{admission_date}} "
            "and left on {{leaving_date}} while enrolled in {{class_or_designation}}.\n\n"
            "Last Examination Result: {{last_exam_result}}. Fee & Library Clearance: {{dues_clearance}}. "
            "General Conduct: {{conduct_grade}}. Remarks: {{leaving_remarks}}."
        ),
        "footer_text": "No alteration in any entry of this Leaving Certificate shall be valid without seal.",
        "signature_left_label": "Head Clerk / Registrar",
        "signature_right_label": "Principal",
        "show_photo": True,
        "show_qr": True,
        "show_seal": True,
        "custom_fields_schema_json": json.dumps([
            {"key": "leaving_date", "label": "Date of Leaving", "type": "text", "required": True, "default_value": date.today().strftime("%d %b %Y")},
            {"key": "last_exam_result", "label": "Last Exam Result", "type": "text", "required": False, "default_value": "Promoted / Passed"},
            {"key": "dues_clearance", "label": "Dues Clearance Status", "type": "text", "required": True, "default_value": "All Institutional Dues Cleared"},
            {"key": "conduct_grade", "label": "Conduct Grade", "type": "text", "required": False, "default_value": "Good"},
            {"key": "leaving_remarks", "label": "Official Remarks", "type": "text", "required": False, "default_value": "Completed academic requirements cleanly."},
        ]),
    },
    {
        "template_code": "TPL-ADM-RECEIPT",
        "name": "Admission Receipt — Enrollment Voucher",
        "document_type": "Admission Receipt",
        "description": "A5 landscape official admission application, entrance test, and enrollment fee voucher.",
        "is_default": True,
        "page_size": "A5",
        "orientation": "Landscape",
        "border_style": "Modern",
        "font_family": "Helvetica",
        "primary_color": "#0369A1",
        "secondary_color": "#0C4A6E",
        "accent_color": "#059669",
        "text_color": "#0F172A",
        "background_color": "#FFFFFF",
        "header_text": "ADMISSION FEE RECEIPT",
        "subheader_text": "OFFICIAL ADMISSIONS OFFICE VOUCHER",
        "body_template": (
            "Received with thanks from {{recipient_name}} (Applicant ID: {{recipient_code}}) "
            "towards {{fee_description}} for admission into {{class_or_designation}} ({{academic_year}})."
        ),
        "footer_text": "Computer-verified admission receipt. Present QR code during seat confirmation.",
        "signature_left_label": "Applicant / Guardian",
        "signature_right_label": "Admissions Cashier",
        "show_photo": False,
        "show_qr": True,
        "show_seal": False,
        "custom_fields_schema_json": json.dumps([
            {"key": "counter_no", "label": "Admission Desk / Counter", "type": "text", "required": False, "default_value": "Admissions Counter 1"},
            {"key": "acknowledgement_note", "label": "Note", "type": "text", "required": False, "default_value": "Provisional subject to document verification."},
        ]),
    },
    {
        "template_code": "TPL-FEE-RECEIPT",
        "name": "Fee Receipt — Treasury Standard",
        "document_type": "Fee Receipt",
        "description": "A5 landscape itemized student tuition & fee payment voucher with concession and balance summary.",
        "is_default": True,
        "page_size": "A5",
        "orientation": "Landscape",
        "border_style": "Modern",
        "font_family": "Helvetica",
        "primary_color": "#1E3A8A",
        "secondary_color": "#0F172A",
        "accent_color": "#059669",
        "text_color": "#0F172A",
        "background_color": "#FFFFFF",
        "header_text": "OFFICIAL FEE PAYMENT RECEIPT",
        "subheader_text": "ACCOUNTS & TREASURY DEPARTMENT",
        "body_template": (
            "Payment received from {{recipient_name}} (Student ID: {{recipient_code}}, "
            "Class: {{class_or_designation}}) against Voucher {{receipt_no}} via {{payment_method}}."
        ),
        "footer_text": "Official electronic money receipt. Verify serial via institution QR portal.",
        "signature_left_label": "Depositor / Student",
        "signature_right_label": "Authorized Cashier / Accountant",
        "show_photo": False,
        "show_qr": True,
        "show_seal": False,
        "custom_fields_schema_json": json.dumps([
            {"key": "billing_note", "label": "Billing / Remarks Note", "type": "text", "required": False, "default_value": "Thank you for timely remittance."},
        ]),
    },
    {
        "template_code": "TPL-MS-TRANSCRIPT",
        "name": "Mark Sheet — Academic Transcript",
        "document_type": "Mark Sheet",
        "description": "Portrait A4 detailed subject-by-subject Mark Sheet with Theory, MCQ, Practical, Viva & Attendance breakdown.",
        "is_default": True,
        "page_size": "A4",
        "orientation": "Portrait",
        "border_style": "Classic",
        "font_family": "Helvetica",
        "primary_color": "#1E3A8A",
        "secondary_color": "#0F172A",
        "accent_color": "#2563EB",
        "text_color": "#0F172A",
        "background_color": "#FFFFFF",
        "header_text": "OFFICIAL MARK SHEET",
        "subheader_text": "ACADEMIC TRANSCRIPT & COMPONENT SCORE STATEMENT",
        "body_template": (
            "Statement of Marks secured by {{recipient_name}} (ID: {{recipient_code}}) of "
            "{{class_or_designation}} in {{exam_term_name}} ({{academic_year}})."
        ),
        "footer_text": "Published under Authority of Controller of Examinations. Scan QR to verify score integrity.",
        "signature_left_label": "Tabulator / Class Teacher",
        "signature_right_label": "Controller of Examinations",
        "show_photo": False,
        "show_qr": True,
        "show_seal": True,
        "custom_fields_schema_json": json.dumps([
            {"key": "controller_note", "label": "Examination Note", "type": "text", "required": False, "default_value": "Passed subjects calculated per institutional grading scale."},
        ]),
    },
    {
        "template_code": "TPL-RC-PROGRESS",
        "name": "Report Card — Executive Progress",
        "document_type": "Report Card",
        "description": "Portrait A4 student progress report card featuring GPA, CGPA, merit position, attendance & remarks.",
        "is_default": True,
        "page_size": "A4",
        "orientation": "Portrait",
        "border_style": "Double",
        "font_family": "Helvetica",
        "primary_color": "#0F172A",
        "secondary_color": "#1E3A8A",
        "accent_color": "#059669",
        "text_color": "#0F172A",
        "background_color": "#FFFFFF",
        "header_text": "STUDENT PROGRESS REPORT CARD",
        "subheader_text": "COMPREHENSIVE TERM EVALUATION & MERIT RECORD",
        "body_template": (
            "Academic Progress Report for {{recipient_name}} (ID: {{recipient_code}}, {{class_or_designation}}) "
            "for {{exam_term_name}} ({{academic_year}}). Teacher Observation: {{teacher_comment}}"
        ),
        "footer_text": "Parents/Guardians are requested to review progress and countersign.",
        "signature_left_label": "Class Teacher",
        "signature_right_label": "Principal",
        "show_photo": True,
        "show_qr": True,
        "show_seal": True,
        "custom_fields_schema_json": json.dumps([
            {"key": "teacher_comment", "label": "Class Teacher Observation", "type": "text", "required": False, "default_value": "Consistent effort and positive classroom engagement."},
            {"key": "next_term_reopens", "label": "Next Term Reopens On", "type": "text", "required": False, "default_value": "Next Scheduled Session"},
        ]),
    },
]


class DocumentService:
    DOCUMENT_TYPES = OFFICIAL_DOCUMENT_TYPES

    # ------------------------------------------------------------------ #
    # Template Management (Seed, CRUD, Clone, Set Default)
    # ------------------------------------------------------------------ #
    @staticmethod
    def seed_default_templates(db: Session) -> int:
        existing_codes = {
            row[0] for row in db.query(DocumentTemplate.template_code).all()
        }
        created = 0
        for preset in DEFAULT_TEMPLATE_PRESETS:
            if preset["template_code"] in existing_codes:
                continue
            has_default_for_type = (
                db.query(DocumentTemplate)
                .filter(
                    DocumentTemplate.document_type == preset["document_type"],
                    DocumentTemplate.is_default == True,  # noqa: E712
                    DocumentTemplate.is_deleted == False,  # noqa: E712
                )
                .first()
                is not None
            )
            data = dict(preset)
            if has_default_for_type:
                data["is_default"] = False
            tpl = DocumentTemplate(**data)
            db.add(tpl)
            created += 1

        if created:
            db.commit()
        return created

    @staticmethod
    def list_templates(
        db: Session,
        document_type: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[DocumentTemplate]:
        DocumentService.seed_default_templates(db)
        q = db.query(DocumentTemplate).filter(DocumentTemplate.is_deleted == False)  # noqa: E712
        if document_type and document_type != "All":
            q = q.filter(DocumentTemplate.document_type == document_type)
        if not include_inactive:
            q = q.filter(DocumentTemplate.is_active == True)  # noqa: E712
        return q.order_by(
            DocumentTemplate.document_type.asc(),
            DocumentTemplate.is_default.desc(),
            DocumentTemplate.name.asc(),
        ).all()

    @staticmethod
    def get_template(
        db: Session,
        template_id: Optional[int] = None,
        template_code: Optional[str] = None,
    ) -> Optional[DocumentTemplate]:
        q = db.query(DocumentTemplate).filter(DocumentTemplate.is_deleted == False)  # noqa: E712
        if template_id is not None:
            return q.filter(DocumentTemplate.id == template_id).first()
        if template_code:
            return q.filter(DocumentTemplate.template_code == template_code).first()
        return None

    @staticmethod
    def get_default_template(db: Session, document_type: str) -> DocumentTemplate:
        DocumentService.seed_default_templates(db)
        tpl = (
            db.query(DocumentTemplate)
            .filter(
                DocumentTemplate.document_type == document_type,
                DocumentTemplate.is_default == True,  # noqa: E712
                DocumentTemplate.is_active == True,  # noqa: E712
                DocumentTemplate.is_deleted == False,  # noqa: E712
            )
            .first()
        )
        if tpl:
            return tpl
        tpl = (
            db.query(DocumentTemplate)
            .filter(
                DocumentTemplate.document_type == document_type,
                DocumentTemplate.is_deleted == False,  # noqa: E712
            )
            .order_by(DocumentTemplate.id.asc())
            .first()
        )
        if not tpl:
            raise ValueError(f"No document template found for type '{document_type}'.")
        return tpl

    @staticmethod
    def create_template(db: Session, **kwargs) -> DocumentTemplate:
        doc_type = kwargs.get("document_type")
        if doc_type not in OFFICIAL_DOCUMENT_TYPES:
            raise ValueError(
                f"Unsupported document_type '{doc_type}'. Allowed: {', '.join(OFFICIAL_DOCUMENT_TYPES)}"
            )
        if not kwargs.get("template_code"):
            prefix = DOCUMENT_SERIAL_PREFIX.get(doc_type, "DOC")
            kwargs["template_code"] = f"TPL-{prefix}-{uuid.uuid4().hex[:6].upper()}"

        if "custom_fields_schema" in kwargs:
            kwargs["custom_fields_schema_json"] = json.dumps(kwargs.pop("custom_fields_schema") or [])

        is_default = bool(kwargs.get("is_default", False))
        if is_default:
            db.query(DocumentTemplate).filter(
                DocumentTemplate.document_type == doc_type
            ).update({"is_default": False})

        tpl = DocumentTemplate(**kwargs)
        db.add(tpl)
        db.commit()
        db.refresh(tpl)
        return tpl

    @staticmethod
    def update_template(db: Session, template_id: int, **kwargs) -> DocumentTemplate:
        tpl = DocumentService.get_template(db, template_id=template_id)
        if not tpl:
            raise ValueError(f"Template ID {template_id} not found.")

        if "custom_fields_schema" in kwargs:
            kwargs["custom_fields_schema_json"] = json.dumps(kwargs.pop("custom_fields_schema") or [])

        if kwargs.get("is_default"):
            target_type = kwargs.get("document_type", tpl.document_type)
            db.query(DocumentTemplate).filter(
                DocumentTemplate.document_type == target_type,
                DocumentTemplate.id != tpl.id,
            ).update({"is_default": False})

        for key, val in kwargs.items():
            if hasattr(tpl, key) and key not in ("id", "created_at"):
                setattr(tpl, key, val)

        db.commit()
        db.refresh(tpl)
        return tpl

    @staticmethod
    def clone_template(
        db: Session,
        template_id: int,
        new_name: Optional[str] = None,
        new_code: Optional[str] = None,
    ) -> DocumentTemplate:
        src = DocumentService.get_template(db, template_id=template_id)
        if not src:
            raise ValueError(f"Template ID {template_id} not found.")
        prefix = DOCUMENT_SERIAL_PREFIX.get(src.document_type, "DOC")
        cloned = DocumentTemplate(
            template_code=new_code or f"TPL-{prefix}-{uuid.uuid4().hex[:6].upper()}",
            name=new_name or f"{src.name} (Copy)",
            document_type=src.document_type,
            description=src.description,
            is_default=False,
            is_active=True,
            page_size=src.page_size,
            orientation=src.orientation,
            border_style=src.border_style,
            font_family=src.font_family,
            primary_color=src.primary_color,
            secondary_color=src.secondary_color,
            accent_color=src.accent_color,
            text_color=src.text_color,
            background_color=src.background_color,
            use_school_profile=src.use_school_profile,
            school_name_override=src.school_name_override,
            school_subtitle_override=src.school_subtitle_override,
            school_address_override=src.school_address_override,
            logo_path=src.logo_path,
            watermark_text=src.watermark_text,
            header_text=src.header_text,
            subheader_text=src.subheader_text,
            body_template=src.body_template,
            footer_text=src.footer_text,
            signature_left_label=src.signature_left_label,
            signature_left_name=src.signature_left_name,
            signature_left_image_path=src.signature_left_image_path,
            signature_right_label=src.signature_right_label,
            signature_right_name=src.signature_right_name,
            signature_right_image_path=src.signature_right_image_path,
            seal_image_path=src.seal_image_path,
            show_logo=src.show_logo,
            show_qr=src.show_qr,
            show_serial=src.show_serial,
            show_photo=src.show_photo,
            show_border=src.show_border,
            show_seal=src.show_seal,
            show_signatures=src.show_signatures,
            show_custom_fields=src.show_custom_fields,
            custom_fields_schema_json=src.custom_fields_schema_json,
        )
        db.add(cloned)
        db.commit()
        db.refresh(cloned)
        return cloned

    @staticmethod
    def set_default_template(db: Session, template_id: int) -> DocumentTemplate:
        tpl = DocumentService.get_template(db, template_id=template_id)
        if not tpl:
            raise ValueError(f"Template ID {template_id} not found.")
        db.query(DocumentTemplate).filter(
            DocumentTemplate.document_type == tpl.document_type
        ).update({"is_default": False})
        tpl.is_default = True
        tpl.is_active = True
        db.commit()
        db.refresh(tpl)
        return tpl

    @staticmethod
    def delete_template(db: Session, template_id: int) -> bool:
        tpl = DocumentService.get_template(db, template_id=template_id)
        if not tpl:
            return False
        doc_type = tpl.document_type
        was_default = tpl.is_default
        tpl.is_deleted = True
        tpl.is_active = False
        tpl.is_default = False
        db.flush()
        if was_default:
            fallback = (
                db.query(DocumentTemplate)
                .filter(
                    DocumentTemplate.document_type == doc_type,
                    DocumentTemplate.is_deleted == False,  # noqa: E712
                    DocumentTemplate.is_active == True,  # noqa: E712
                )
                .order_by(DocumentTemplate.id.asc())
                .first()
            )
            if fallback:
                fallback.is_default = True
        db.commit()
        return True

    # ------------------------------------------------------------------ #
    # School & Recipient Context Hydration (Zero hard-coded school)
    # ------------------------------------------------------------------ #
    @staticmethod
    def resolve_school_info(
        db: Session,
        template: Optional[DocumentTemplate] = None,
    ) -> Dict[str, Any]:
        school = db.query(SchoolSetting).first()
        use_profile = True if template is None else bool(template.use_school_profile)

        base_name = (school.school_name if school and school.school_name else "Institution Name") if use_profile else "Custom Institution"
        base_motto = (school.motto if school and school.motto else "") if use_profile else ""
        base_address = (
            ", ".join(p for p in [getattr(school, "address", None), getattr(school, "city", None), getattr(school, "country", None)] if p)
            if (use_profile and school)
            else ""
        )
        eiin = getattr(school, "eiin_number", "") if (use_profile and school) else ""
        reg_no = getattr(school, "registration_no", "") if (use_profile and school) else ""
        phone = getattr(school, "phone", "") if (use_profile and school) else ""
        email = getattr(school, "email", "") if (use_profile and school) else ""
        website = getattr(school, "website", "") if (use_profile and school) else ""
        principal_name = getattr(school, "principal_name", "") if (use_profile and school) else ""
        currency_symbol = getattr(school, "currency_symbol", "BDT") if school else "BDT"
        currency_code = getattr(school, "currency_code", "BDT") if school else "BDT"

        logo_path = (
            (template.logo_path if template and template.logo_path else None)
            or (getattr(school, "logo_path", None) if use_profile and school else None)
        )
        sig_left_img = (
            (template.signature_left_image_path if template and template.signature_left_image_path else None)
            or (getattr(school, "registrar_signature_path", None) if use_profile and school else None)
        )
        sig_right_img = (
            (template.signature_right_image_path if template and template.signature_right_image_path else None)
            or (getattr(school, "principal_signature_path", None) if use_profile and school else None)
        )
        seal_img = (
            (template.seal_image_path if template and template.seal_image_path else None)
            or (getattr(school, "official_seal_path", None) if use_profile and school else None)
        )

        final_name = (template.school_name_override if template and template.school_name_override else None) or base_name
        final_subtitle = (template.school_subtitle_override if template and template.school_subtitle_override else None) or base_motto
        final_address = (template.school_address_override if template and template.school_address_override else None) or base_address

        return {
            "school_name": final_name,
            "motto": final_subtitle,
            "address": final_address,
            "eiin_number": eiin or "",
            "registration_no": reg_no or "",
            "phone": phone or "",
            "email": email or "",
            "website": website or "",
            "principal_name": principal_name or "Principal",
            "currency_code": currency_code,
            "currency_symbol": currency_symbol,
            "logo_path": logo_path,
            "signature_left_image_path": sig_left_img,
            "signature_right_image_path": sig_right_img,
            "seal_image_path": seal_img,
        }

    @staticmethod
    def build_document_context(
        db: Session,
        document_type: str,
        template: Optional[DocumentTemplate] = None,
        recipient_type: str = "Student",
        student_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        staff_id: Optional[int] = None,
        admission_application_id: Optional[int] = None,
        admission_payment_id: Optional[int] = None,
        fee_payment_id: Optional[int] = None,
        exam_term_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        custom_fields_values: Optional[Dict[str, Any]] = None,
        issue_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        tpl = template or DocumentService.get_default_template(db, document_type)
        school_info = DocumentService.resolve_school_info(db, tpl)
        iss_dt = issue_date or date.today()

        ay_obj = None
        if academic_year_id:
            ay_obj = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
        if not ay_obj:
            ay_obj = db.query(AcademicYear).filter(AcademicYear.is_current == True).first()  # noqa: E712
        if not ay_obj:
            school_row = db.query(SchoolSetting).first()
            if school_row and school_row.current_academic_year:
                ay_obj = school_row.current_academic_year
        ay_name = ay_obj.name if ay_obj else str(iss_dt.year)

        student = None
        teacher = None
        staff_member = None
        adm_app = None
        adm_pay = None
        fee_pay = None
        exam_term = None

        if fee_payment_id:
            fee_pay = db.query(FeePayment).filter(FeePayment.id == fee_payment_id).first()
            if not fee_pay:
                raise ValueError(f"FeePayment ID {fee_payment_id} not found.")
            if not student_id:
                student_id = fee_pay.student_id

        if admission_payment_id:
            adm_pay = db.query(AdmissionFeePayment).filter(AdmissionFeePayment.id == admission_payment_id).first()
            if not adm_pay:
                raise ValueError(f"AdmissionFeePayment ID {admission_payment_id} not found.")
            if not admission_application_id:
                admission_application_id = adm_pay.application_id

        if admission_application_id:
            adm_app = db.query(AdmissionApplication).filter(AdmissionApplication.id == admission_application_id).first()
            if not adm_app:
                raise ValueError(f"AdmissionApplication ID {admission_application_id} not found.")
            recipient_type = "Applicant"

        if student_id:
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                raise ValueError(f"Student ID {student_id} not found.")
            recipient_type = "Student"
        elif teacher_id:
            teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
            if not teacher:
                raise ValueError(f"Teacher ID {teacher_id} not found.")
            recipient_type = "Teacher"
        elif staff_id:
            staff_member = db.query(Staff).filter(Staff.id == staff_id).first()
            if not staff_member:
                raise ValueError(f"Staff ID {staff_id} not found.")
            recipient_type = "Staff"

        if exam_term_id:
            exam_term = db.query(ExamTerm).filter(ExamTerm.id == exam_term_id).first()

        recipient_info: Dict[str, Any] = {
            "recipient_type": recipient_type,
            "recipient_name": "Recipient",
            "recipient_code": "N/A",
            "class_or_designation": "N/A",
            "class_name": "N/A",
            "section_name": "N/A",
            "roll_number": "N/A",
            "admission_number": "N/A",
            "father_name": "N/A",
            "mother_name": "N/A",
            "guardian_name": "N/A",
            "guardian_phone": "N/A",
            "date_of_birth": "N/A",
            "admission_date": "N/A",
            "blood_group": "N/A",
            "address": "N/A",
            "emergency_contact": "N/A",
            "photo_path": None,
        }

        if student is not None:
            cls_name = student.school_class.name if student.school_class else "Unassigned"
            sec_name = student.section.name if student.section else "A"
            g = student.guardian
            father = (g.father_name or g.guardian_name) if g else "N/A"
            mother = (g.mother_name or "N/A") if g else "N/A"
            g_name = g.guardian_name if g else "N/A"
            g_phone = g.guardian_phone if g else (student.phone or "N/A")
            recipient_info.update({
                "recipient_type": "Student",
                "recipient_name": student.full_name,
                "recipient_code": student.student_id,
                "class_or_designation": f"{cls_name} (Section {sec_name}, Roll #{student.roll_number})",
                "class_name": cls_name,
                "section_name": sec_name,
                "roll_number": str(student.roll_number),
                "admission_number": student.admission_number,
                "father_name": father,
                "mother_name": mother,
                "guardian_name": g_name,
                "guardian_phone": g_phone,
                "date_of_birth": _fmt_date(student.date_of_birth),
                "admission_date": _fmt_date(student.admission_date),
                "blood_group": student.blood_group or "N/A",
                "address": student.address or f"{student.city or ''}, {student.country or ''}".strip(", "),
                "emergency_contact": getattr(student, "emergency_contact", None) or g_phone,
                "photo_path": student.photo_path,
            })
            if student.academic_year:
                ay_name = student.academic_year.name
                academic_year_id = academic_year_id or student.academic_year_id
        elif adm_app is not None:
            cls_name = adm_app.applying_class.name if adm_app.applying_class else "Target Class"
            sec_name = adm_app.preferred_section.name if adm_app.preferred_section else "Unassigned"
            recipient_info.update({
                "recipient_type": "Applicant",
                "recipient_name": adm_app.full_name,
                "recipient_code": adm_app.applicant_id,
                "class_or_designation": f"Applying: {cls_name} ({adm_app.shift_name} Shift)",
                "class_name": cls_name,
                "section_name": sec_name,
                "roll_number": adm_app.form_number or "-",
                "admission_number": adm_app.applicant_id,
                "father_name": adm_app.father_name or adm_app.guardian_name,
                "mother_name": adm_app.mother_name or "N/A",
                "guardian_name": adm_app.guardian_name,
                "guardian_phone": adm_app.guardian_phone,
                "date_of_birth": _fmt_date(adm_app.date_of_birth),
                "admission_date": _fmt_date(adm_app.application_date),
                "blood_group": adm_app.blood_group or "N/A",
                "address": adm_app.address or (adm_app.city or "N/A"),
                "emergency_contact": adm_app.emergency_contact or adm_app.guardian_phone,
                "photo_path": adm_app.photo_path,
            })
            if adm_app.academic_year:
                ay_name = adm_app.academic_year.name
                academic_year_id = academic_year_id or adm_app.academic_year_id
        elif teacher is not None:
            dept_name = teacher.department.name if teacher.department else "Faculty"
            recipient_info.update({
                "recipient_type": "Teacher",
                "recipient_name": teacher.full_name,
                "recipient_code": teacher.teacher_id,
                "class_or_designation": f"{teacher.designation} • {dept_name}",
                "class_name": dept_name,
                "section_name": teacher.primary_subject,
                "roll_number": teacher.employee_id,
                "admission_number": teacher.employee_id,
                "date_of_birth": _fmt_date(teacher.date_of_birth),
                "admission_date": _fmt_date(teacher.joining_date),
                "blood_group": teacher.blood_group or "N/A",
                "address": teacher.address or "N/A",
                "guardian_name": teacher.emergency_contact_name or "Faculty Office",
                "guardian_phone": teacher.phone or "N/A",
                "emergency_contact": teacher.emergency_contact_phone or teacher.phone or "N/A",
                "photo_path": teacher.photo_path,
            })
        elif staff_member is not None:
            dept_name = staff_member.department.name if staff_member.department else "Administration"
            recipient_info.update({
                "recipient_type": "Staff",
                "recipient_name": staff_member.full_name,
                "recipient_code": staff_member.staff_id,
                "class_or_designation": f"{staff_member.position} • {dept_name}",
                "class_name": dept_name,
                "section_name": staff_member.shift,
                "roll_number": staff_member.employee_id,
                "admission_number": staff_member.employee_id,
                "date_of_birth": _fmt_date(staff_member.date_of_birth),
                "admission_date": _fmt_date(staff_member.joining_date),
                "blood_group": "N/A",
                "address": staff_member.address or "N/A",
                "guardian_name": staff_member.emergency_contact_name or "Admin Office",
                "guardian_phone": staff_member.phone or "N/A",
                "emergency_contact": staff_member.emergency_contact_phone or staff_member.phone or "N/A",
                "photo_path": staff_member.photo_path,
            })

        # Structured Table Rows & Metrics for Financial & Exam Documents
        table_rows: List[Dict[str, Any]] = []
        summary_metrics: Dict[str, Any] = {
            "currency_code": school_info["currency_code"],
            "currency_symbol": school_info["currency_symbol"],
        }
        receipt_no = "-"
        invoice_no = "-"
        amount_paid_str = "0.00"
        payment_method = "-"
        fee_description = "-"
        exam_term_name = exam_term.name if exam_term else "Annual Examination"

        if document_type == "Fee Receipt" and fee_pay is not None:
            s_fee = fee_pay.student_fee
            receipt_no = fee_pay.receipt_no
            invoice_no = s_fee.invoice_number if s_fee else "-"
            fee_description = s_fee.display_title if s_fee else "Student Fee"
            payment_method = fee_pay.payment_method
            tot_amt = float(s_fee.total_amount) if s_fee else float(fee_pay.amount_paid)
            disc_amt = float(s_fee.discount_amount) if s_fee else 0.0
            net_amt = float(s_fee.net_amount) if s_fee else float(fee_pay.amount_paid)
            paid_now = float(fee_pay.amount_paid or 0.0)
            rem_due = float(s_fee.due_amount) if s_fee else 0.0
            amount_paid_str = f"{paid_now:,.2f}"
            table_rows.append({
                "description": fee_description,
                "invoice_no": invoice_no,
                "original": round(tot_amt, 2),
                "discount": round(disc_amt, 2),
                "net_amount": round(net_amt, 2),
                "paid_now": round(paid_now, 2),
                "due_balance": round(rem_due, 2),
            })
            summary_metrics.update({
                "receipt_no": receipt_no,
                "invoice_no": invoice_no,
                "payment_method": payment_method,
                "payment_date": _fmt_date(fee_pay.payment_date),
                "transaction_id": fee_pay.transaction_id or "-",
                "collected_by": fee_pay.collected_by,
                "total_amount": round(tot_amt, 2),
                "discount_amount": round(disc_amt, 2),
                "net_amount": round(net_amt, 2),
                "amount_paid": round(paid_now, 2),
                "remaining_due": round(rem_due, 2),
                "status": fee_pay.status,
            })
        elif document_type == "Admission Receipt" and adm_pay is not None:
            receipt_no = adm_pay.receipt_no
            invoice_no = adm_pay.reference_no or adm_pay.receipt_no
            fee_description = adm_pay.fee_type
            payment_method = adm_pay.payment_method
            amt_due = float(adm_pay.amount_due or 0.0)
            disc_amt = float(adm_pay.discount_amount or 0.0)
            paid_now = float(adm_pay.amount_paid or 0.0)
            net_amt = max(0.0, amt_due - disc_amt)
            rem_due = max(0.0, net_amt - paid_now)
            amount_paid_str = f"{paid_now:,.2f}"
            table_rows.append({
                "description": adm_pay.fee_type,
                "invoice_no": adm_app.applicant_id if adm_app else "-",
                "original": round(amt_due, 2),
                "discount": round(disc_amt, 2),
                "net_amount": round(net_amt, 2),
                "paid_now": round(paid_now, 2),
                "due_balance": round(rem_due, 2),
            })
            summary_metrics.update({
                "receipt_no": receipt_no,
                "invoice_no": invoice_no,
                "payment_method": payment_method,
                "payment_date": _fmt_date(adm_pay.payment_date),
                "transaction_id": adm_pay.reference_no or "-",
                "collected_by": adm_pay.collected_by,
                "total_amount": round(amt_due, 2),
                "discount_amount": round(disc_amt, 2),
                "net_amount": round(net_amt, 2),
                "amount_paid": round(paid_now, 2),
                "remaining_due": round(rem_due, 2),
                "status": adm_pay.payment_status,
            })
        elif document_type in ("Mark Sheet", "Report Card") and student is not None:
            if not exam_term:
                latest_sum = (
                    db.query(ExamResultSummary)
                    .filter(ExamResultSummary.student_id == student.id)
                    .order_by(ExamResultSummary.id.desc())
                    .first()
                )
                if latest_sum:
                    exam_term = latest_sum.exam_term
                    exam_term_id = exam_term.id if exam_term else exam_term_id
                    exam_term_name = exam_term.name if exam_term else exam_term_name

            summary = None
            marks: List[StudentMark] = []
            if exam_term:
                summary = (
                    db.query(ExamResultSummary)
                    .filter(
                        ExamResultSummary.exam_term_id == exam_term.id,
                        ExamResultSummary.student_id == student.id,
                    )
                    .first()
                )
                marks = (
                    db.query(StudentMark)
                    .filter(
                        StudentMark.exam_term_id == exam_term.id,
                        StudentMark.student_id == student.id,
                    )
                    .order_by(StudentMark.subject_id.asc())
                    .all()
                )
                if exam_term.academic_year:
                    ay_name = exam_term.academic_year.name
                    academic_year_id = academic_year_id or exam_term.academic_year_id

            tot_full = 0.0
            tot_obt = 0.0
            for sm in marks:
                sub_code = sm.subject.code if sm.subject else "SUB"
                sub_name = sm.subject.name if sm.subject else f"Subject #{sm.subject_id}"
                if sm.is_optional:
                    sub_name = f"{sub_name} (Opt)"
                full_m = float(sm.full_marks_snapshot or 100.0)
                obt_m = float(sm.total_marks or 0.0)
                tot_full += full_m
                tot_obt += obt_m
                table_rows.append({
                    "code": sub_code,
                    "subject": sub_name,
                    "full_marks": round(full_m, 1),
                    "theory": round(float(sm.theory_marks or 0.0), 1),
                    "mcq": round(float(sm.mcq_marks or 0.0), 1),
                    "practical": round(float(sm.practical_marks or 0.0), 1),
                    "viva": round(float(sm.viva_marks or 0.0), 1),
                    "attendance": round(float(sm.attendance_marks or 0.0), 1),
                    "total": round(obt_m, 1),
                    "grade_point": round(float(sm.grade_point or 0.0), 2),
                    "grade_name": sm.grade_name,
                    "passed": bool(sm.is_passed),
                })

            gpa_val = float(summary.gpa) if summary else 0.0
            cgpa_val = float(summary.cgpa) if summary else gpa_val
            max_gpa = float(exam_term.grading_system.max_gpa) if (exam_term and exam_term.grading_system) else 5.0
            summary_metrics.update({
                "exam_term_name": exam_term_name,
                "result_status": (
                    "PUBLISHED & LOCKED" if (summary and summary.is_published) else (summary.result_status if summary else "Compiled")
                ),
                "gpa": round(gpa_val, 2),
                "cgpa": round(cgpa_val, 2),
                "max_gpa": round(max_gpa, 2),
                "overall_grade": summary.overall_grade if summary else ("N/A" if not marks else "F"),
                "class_rank": summary.class_rank if summary else None,
                "section_rank": summary.section_rank if summary else None,
                "total_obtained": round(float(summary.total_obtained) if summary else tot_obt, 1),
                "total_full_marks": round(float(summary.total_full_marks) if summary else tot_full, 1),
                "percentage": round(float(summary.percentage) if summary else ((tot_obt / tot_full * 100.0) if tot_full else 0.0), 2),
                "attendance_percentage": summary.attendance_percentage if summary else None,
                "passed_all": bool(summary.passed_all) if summary else False,
                "remarks": summary.remarks if summary and summary.remarks else "Keep striving for excellence.",
            })

        # Custom Fields Schema + Resolved Values
        schema_fields = _safe_json_loads(tpl.custom_fields_schema_json, [])
        merged_custom: Dict[str, Any] = {}
        custom_field_display: List[Dict[str, str]] = []
        provided_custom = custom_fields_values or {}
        seen_keys = set()
        for field_def in schema_fields:
            k = str(field_def.get("key", "")).strip()
            if not k:
                continue
            seen_keys.add(k)
            val = provided_custom.get(k, field_def.get("default_value", ""))
            merged_custom[k] = val
            custom_field_display.append({
                "key": k,
                "label": str(field_def.get("label") or k.replace("_", " ").title()),
                "value": str(val),
            })
        for extra_k, extra_v in provided_custom.items():
            if extra_k not in seen_keys:
                merged_custom[extra_k] = extra_v
                custom_field_display.append({
                    "key": extra_k,
                    "label": extra_k.replace("_", " ").title(),
                    "value": str(extra_v),
                })

        placeholders: Dict[str, Any] = {
            **school_info,
            "school_phone": school_info["phone"],
            "school_website": school_info["website"],
            **recipient_info,
            "academic_year": ay_name,
            "issue_date": _fmt_date(iss_dt),
            "receipt_no": receipt_no,
            "invoice_no": invoice_no,
            "amount_paid": amount_paid_str,
            "payment_method": payment_method,
            "fee_description": fee_description,
            "exam_term_name": exam_term_name,
            "gpa": f"{summary_metrics.get('gpa', 0.0):.2f}",
            "cgpa": f"{summary_metrics.get('cgpa', 0.0):.2f}",
            "overall_grade": summary_metrics.get("overall_grade", "N/A"),
            "class_rank": str(summary_metrics.get("class_rank") or "-"),
            "section_rank": str(summary_metrics.get("section_rank") or "-"),
            **merged_custom,
        }

        return {
            "template": tpl,
            "school_info": school_info,
            "recipient_info": recipient_info,
            "academic_year_id": academic_year_id,
            "academic_year_name": ay_name,
            "student_id": student.id if student else None,
            "teacher_id": teacher.id if teacher else None,
            "staff_id": staff_member.id if staff_member else None,
            "admission_application_id": adm_app.id if adm_app else None,
            "admission_payment_id": adm_pay.id if adm_pay else None,
            "fee_payment_id": fee_pay.id if fee_pay else None,
            "exam_term_id": exam_term.id if exam_term else exam_term_id,
            "table_rows": table_rows,
            "summary_metrics": summary_metrics,
            "custom_fields_values": merged_custom,
            "custom_fields_display": custom_field_display,
            "placeholders": placeholders,
            "issue_date": iss_dt,
        }

    @staticmethod
    def render_template_text(template_str: Optional[str], placeholders: Dict[str, Any]) -> str:
        text = template_str or ""
        for k, v in placeholders.items():
            text = text.replace("{{" + str(k) + "}}", str(v if v is not None else ""))
        return text

    # ------------------------------------------------------------------ #
    # Serial Numbering, QR Payloads, Live Preview & Issuance
    # ------------------------------------------------------------------ #
    @staticmethod
    def generate_serial_number(db: Session, document_type: str) -> str:
        prefix = DOCUMENT_SERIAL_PREFIX.get(document_type, "DOC")
        year = date.today().year
        pattern = f"DOC-{prefix}-{year}-%"
        existing = (
            db.query(IssuedDocument.serial_number)
            .filter(IssuedDocument.serial_number.like(pattern))
            .all()
        )
        max_seq = 0
        for (sn,) in existing:
            try:
                max_seq = max(max_seq, int(sn.rsplit("-", 1)[-1]))
            except Exception:
                pass
        return f"DOC-{prefix}-{year}-{max_seq + 1:05d}"

    @staticmethod
    def generate_verification_code() -> str:
        return f"VER-{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    def build_document_qr_payload(
        serial_number: str,
        verification_code: str,
        document_type: str,
        recipient_code: str,
        recipient_name: str,
        school_name: str = "",
    ) -> str:
        return (
            f"EDUMANAGE-DOC|SER:{serial_number}|VER:{verification_code}"
            f"|TYPE:{document_type}|ID:{recipient_code}|NAME:{recipient_name}"
            + (f"|ORG:{school_name}" if school_name else "")
        )

    @staticmethod
    def preview_document_data(
        db: Session,
        document_type: str,
        template_id: Optional[int] = None,
        recipient_type: str = "Student",
        student_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        staff_id: Optional[int] = None,
        admission_application_id: Optional[int] = None,
        admission_payment_id: Optional[int] = None,
        fee_payment_id: Optional[int] = None,
        exam_term_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        custom_fields_values: Optional[Dict[str, Any]] = None,
        issue_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        tpl = (
            DocumentService.get_template(db, template_id=template_id)
            if template_id
            else DocumentService.get_default_template(db, document_type)
        )
        if not tpl:
            tpl = DocumentService.get_default_template(db, document_type)

        ctx = DocumentService.build_document_context(
            db,
            document_type=document_type,
            template=tpl,
            recipient_type=recipient_type,
            student_id=student_id,
            teacher_id=teacher_id,
            staff_id=staff_id,
            admission_application_id=admission_application_id,
            admission_payment_id=admission_payment_id,
            fee_payment_id=fee_payment_id,
            exam_term_id=exam_term_id,
            academic_year_id=academic_year_id,
            custom_fields_values=custom_fields_values,
            issue_date=issue_date,
        )

        serial_preview = DocumentService.generate_serial_number(db, document_type)
        ver_preview = "VER-PREVIEW"
        placeholders = dict(ctx["placeholders"])
        placeholders["serial_number"] = serial_preview
        placeholders["verification_code"] = ver_preview

        rendered_header = DocumentService.render_template_text(tpl.header_text, placeholders)
        rendered_subheader = DocumentService.render_template_text(tpl.subheader_text, placeholders)
        rendered_body = DocumentService.render_template_text(tpl.body_template, placeholders)
        rendered_footer = DocumentService.render_template_text(tpl.footer_text, placeholders)
        qr_payload = DocumentService.build_document_qr_payload(
            serial_preview,
            ver_preview,
            document_type,
            ctx["recipient_info"]["recipient_code"],
            ctx["recipient_info"]["recipient_name"],
            ctx["school_info"]["school_name"],
        )

        return {
            **ctx,
            "serial_number": serial_preview,
            "verification_code": ver_preview,
            "qr_payload": qr_payload,
            "document_type": document_type,
            "title": rendered_header or document_type.upper(),
            "rendered_header": rendered_header,
            "rendered_subheader": rendered_subheader,
            "rendered_body": rendered_body,
            "rendered_footer": rendered_footer,
            "status": "Preview",
        }

    @staticmethod
    def document_to_render_payload(db: Session, doc: IssuedDocument) -> Dict[str, Any]:
        """Rebuild render payload from an immutable IssuedDocument snapshot + its Template."""
        tpl = doc.template or DocumentService.get_default_template(db, doc.document_type)
        school_info = _safe_json_loads(doc.school_snapshot_json, {}) or DocumentService.resolve_school_info(db, tpl)
        recipient_info = _safe_json_loads(doc.recipient_snapshot_json, {})
        table_rows = _safe_json_loads(doc.table_rows_json, [])
        summary_metrics = _safe_json_loads(doc.summary_metrics_json, {})
        custom_vals = _safe_json_loads(doc.custom_fields_values_json, {})

        schema_fields = _safe_json_loads(tpl.custom_fields_schema_json, []) if tpl else []
        custom_display: List[Dict[str, str]] = []
        seen = set()
        for fdef in schema_fields:
            k = str(fdef.get("key", ""))
            if k in custom_vals:
                seen.add(k)
                custom_display.append({
                    "key": k,
                    "label": str(fdef.get("label") or k.replace("_", " ").title()),
                    "value": str(custom_vals[k]),
                })
        for k, v in custom_vals.items():
            if k not in seen:
                custom_display.append({
                    "key": k,
                    "label": k.replace("_", " ").title(),
                    "value": str(v),
                })

        placeholders = {
            **school_info,
            "school_phone": school_info.get("phone", ""),
            "school_website": school_info.get("website", ""),
            **recipient_info,
            **summary_metrics,
            **custom_vals,
            "serial_number": doc.serial_number,
            "verification_code": doc.verification_code,
            "issue_date": _fmt_date(doc.issue_date),
        }

        return {
            "document": doc,
            "template": tpl,
            "school_info": school_info,
            "recipient_info": recipient_info,
            "table_rows": table_rows,
            "summary_metrics": summary_metrics,
            "custom_fields_values": custom_vals,
            "custom_fields_display": custom_display,
            "serial_number": doc.serial_number,
            "verification_code": doc.verification_code,
            "qr_payload": doc.qr_payload,
            "document_type": doc.document_type,
            "title": doc.title,
            "rendered_header": DocumentService.render_template_text(tpl.header_text, placeholders) if tpl else doc.title,
            "rendered_subheader": DocumentService.render_template_text(tpl.subheader_text, placeholders) if tpl else "",
            "rendered_body": doc.rendered_body,
            "rendered_footer": DocumentService.render_template_text(tpl.footer_text, placeholders) if tpl else "",
            "issue_date": doc.issue_date,
            "status": doc.status,
        }

    @staticmethod
    def issue_document(
        db: Session,
        document_type: str,
        template_id: Optional[int] = None,
        recipient_type: str = "Student",
        student_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        staff_id: Optional[int] = None,
        admission_application_id: Optional[int] = None,
        admission_payment_id: Optional[int] = None,
        fee_payment_id: Optional[int] = None,
        exam_term_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        custom_fields_values: Optional[Dict[str, Any]] = None,
        issue_date: Optional[date] = None,
        issued_by: str = "Admin Office",
        output_pdf_path: Optional[str] = None,
    ) -> IssuedDocument:
        if document_type not in OFFICIAL_DOCUMENT_TYPES:
            raise ValueError(f"Unsupported document type '{document_type}'.")

        tpl = (
            DocumentService.get_template(db, template_id=template_id)
            if template_id
            else DocumentService.get_default_template(db, document_type)
        )
        if not tpl:
            tpl = DocumentService.get_default_template(db, document_type)

        ctx = DocumentService.build_document_context(
            db,
            document_type=document_type,
            template=tpl,
            recipient_type=recipient_type,
            student_id=student_id,
            teacher_id=teacher_id,
            staff_id=staff_id,
            admission_application_id=admission_application_id,
            admission_payment_id=admission_payment_id,
            fee_payment_id=fee_payment_id,
            exam_term_id=exam_term_id,
            academic_year_id=academic_year_id,
            custom_fields_values=custom_fields_values,
            issue_date=issue_date,
        )

        serial_no = DocumentService.generate_serial_number(db, document_type)
        ver_code = DocumentService.generate_verification_code()
        placeholders = dict(ctx["placeholders"])
        placeholders["serial_number"] = serial_no
        placeholders["verification_code"] = ver_code

        rendered_header = DocumentService.render_template_text(tpl.header_text, placeholders)
        rendered_body = DocumentService.render_template_text(tpl.body_template, placeholders)
        qr_payload = DocumentService.build_document_qr_payload(
            serial_no,
            ver_code,
            document_type,
            ctx["recipient_info"]["recipient_code"],
            ctx["recipient_info"]["recipient_name"],
            ctx["school_info"]["school_name"],
        )

        doc = IssuedDocument(
            serial_number=serial_no,
            verification_code=ver_code,
            qr_payload=qr_payload,
            document_type=document_type,
            template_id=tpl.id,
            recipient_type=ctx["recipient_info"]["recipient_type"],
            recipient_name=ctx["recipient_info"]["recipient_name"],
            recipient_code=ctx["recipient_info"]["recipient_code"],
            student_id=ctx["student_id"],
            teacher_id=ctx["teacher_id"],
            staff_id=ctx["staff_id"],
            admission_application_id=ctx["admission_application_id"],
            admission_payment_id=ctx["admission_payment_id"],
            fee_payment_id=ctx["fee_payment_id"],
            exam_term_id=ctx["exam_term_id"],
            academic_year_id=ctx["academic_year_id"],
            issue_date=ctx["issue_date"],
            title=rendered_header or document_type,
            rendered_body=rendered_body,
            school_snapshot_json=json.dumps(ctx["school_info"], default=str),
            recipient_snapshot_json=json.dumps(ctx["recipient_info"], default=str),
            table_rows_json=json.dumps(ctx["table_rows"], default=str),
            summary_metrics_json=json.dumps(ctx["summary_metrics"], default=str),
            custom_fields_values_json=json.dumps(ctx["custom_fields_values"], default=str),
            pdf_path=output_pdf_path,
            issued_by=issued_by,
            status="Issued",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        if output_pdf_path:
            from app.reports.universal_document_pdf import UniversalDocumentPDFGenerator

            payload = DocumentService.document_to_render_payload(db, doc)
            UniversalDocumentPDFGenerator.generate_pdf(payload, output_pdf_path)

        return doc

    @staticmethod
    def list_issued_documents(
        db: Session,
        document_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 200,
    ) -> List[IssuedDocument]:
        q = db.query(IssuedDocument).filter(IssuedDocument.is_deleted == False)  # noqa: E712
        if document_type and document_type != "All":
            q = q.filter(IssuedDocument.document_type == document_type)
        if status and status != "All":
            q = q.filter(IssuedDocument.status == status)
        if search:
            term = f"%{search.strip()}%"
            q = q.filter(
                (IssuedDocument.serial_number.ilike(term))
                | (IssuedDocument.verification_code.ilike(term))
                | (IssuedDocument.recipient_name.ilike(term))
                | (IssuedDocument.recipient_code.ilike(term))
            )
        return q.order_by(IssuedDocument.id.desc()).limit(limit).all()

    @staticmethod
    def verify_document(db: Session, query: str) -> Optional[IssuedDocument]:
        clean = (query or "").strip()
        if not clean:
            return None

        # Support scanning full QR payload string: EDUMANAGE-DOC|SER:...|VER:...
        serial_candidate = clean
        ver_candidate = clean
        if "|" in clean:
            for part in clean.split("|"):
                if part.startswith("SER:"):
                    serial_candidate = part[4:].strip()
                elif part.startswith("VER:"):
                    ver_candidate = part[4:].strip()

        return (
            db.query(IssuedDocument)
            .filter(
                IssuedDocument.is_deleted == False,  # noqa: E712
                (IssuedDocument.serial_number == serial_candidate)
                | (IssuedDocument.verification_code == ver_candidate)
                | (IssuedDocument.qr_payload == clean),
            )
            .first()
        )

    @staticmethod
    def revoke_document(
        db: Session,
        document_id: int,
        reason: str = "Revoked by issuing authority",
        revoked_by: str = "Admin Office",
    ) -> Optional[IssuedDocument]:
        doc = db.query(IssuedDocument).filter(IssuedDocument.id == document_id).first()
        if not doc:
            return None
        doc.status = "Revoked"
        doc.revoked_reason = reason
        doc.revoked_by = revoked_by
        doc.revoked_at = utc_now()
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def increment_print_count(db: Session, document_id: int) -> int:
        doc = db.query(IssuedDocument).filter(IssuedDocument.id == document_id).first()
        if not doc:
            return 0
        doc.print_count = int(doc.print_count or 0) + 1
        db.commit()
        return doc.print_count

    @staticmethod
    def get_stats(db: Session) -> Dict[str, Any]:
        docs = db.query(IssuedDocument).filter(IssuedDocument.is_deleted == False).all()  # noqa: E712
        tpls = DocumentService.list_templates(db)
        issued = [d for d in docs if d.status == "Issued"]
        revoked = [d for d in docs if d.status == "Revoked"]
        return {
            "total_documents": len(docs),
            "issued": len(issued),
            "revoked": len(revoked),
            "templates": len(tpls),
            "certificates": len([d for d in issued if "Certificate" in d.document_type]),
            "receipts": len([d for d in issued if "Receipt" in d.document_type]),
            "academic_records": len([d for d in issued if d.document_type in ("Mark Sheet", "Report Card")]),
            "id_cards": len([d for d in issued if d.document_type == "ID Card"]),
        }
