"""
EduManage Pro - Enterprise Communication Center Service
Orchestrates real database event-driven notifications & multi-channel alerts:
- Attendance Alert (absent/late students -> guardian SMS/WhatsApp/Email + In-App Alert)
- Fee Due Alert (overdue/unpaid student invoices -> guardian & student notification)
- Result Notification (compiled/published exam GPA/CGPA/Grade/Rank notices)
- Admission Notification (applicant status, test/interview/merit updates)
- Emergency Notification (campus-wide critical alerts across Guardians, Teachers, Staff)
- Multi-Sheet Excel Audit Export
"""

from datetime import date
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session, joinedload

from app.models.admission import AdmissionApplication
from app.models.attendance import StudentAttendance
from app.models.base import utc_now
from app.models.communication import (
    CommunicationProviderConfig,
    CommunicationTemplate,
)
from app.models.exam import ExamResultSummary, ExamTerm
from app.models.fee import StudentFee
from app.models.school import SchoolSetting
from app.models.staff import EmployeeStatus, Staff, Teacher
from app.models.student import Student, StudentStatus
from app.repositories.communication_repository import CommunicationRepository


class CommunicationService:
    """High-level orchestration for Communication Center triggers, templates, providers, and exports."""

    DEFAULT_PROVIDER_PROFILES = [
        {
            "provider_code": "PRV-INAPP-CORE",
            "provider_name": "EduManage Built-In In-App Feed",
            "channel": "InApp",
            "driver_key": "in_app_feed",
            "is_default": True,
            "sandbox_mode": False,
            "sender_id": "EduManage Pro",
            "notes": "Native desktop Notification, Announcement, Notice & Alert engine.",
        },
        {
            "provider_code": "PRV-SMS-TWILIO",
            "provider_name": "Twilio Programmable SMS (Configurable)",
            "channel": "SMS",
            "driver_key": "twilio_sms",
            "is_default": True,
            "sandbox_mode": True,
            "sender_id": "EDUMANAGE",
            "endpoint_url": "https://api.twilio.com/2010-04-01/Accounts/YOUR_SID/Messages.json",
            "credentials_env_key": "TWILIO_AUTH_TOKEN",
            "notes": "Switchable SMS adapter; add SSL Wireless or Generic Webhook in Providers tab.",
        },
        {
            "provider_code": "PRV-EML-SMTP",
            "provider_name": "Institutional SMTP Email Relay",
            "channel": "Email",
            "driver_key": "smtp_email",
            "is_default": True,
            "sandbox_mode": True,
            "sender_id": "noreply@edumanage.school",
            "endpoint_url": "smtp.gmail.com",
            "credentials_env_key": "SMTP_PASSWORD",
            "config_json": '{"port": 587, "use_tls": true}',
            "notes": "Supports any TLS SMTP server or SendGrid REST adapter.",
        },
        {
            "provider_code": "PRV-WA-META",
            "provider_name": "Meta WhatsApp Business Cloud API",
            "channel": "WhatsApp",
            "driver_key": "meta_whatsapp_cloud",
            "is_default": True,
            "sandbox_mode": True,
            "sender_id": "WABA-PHONE-NUMBER-ID",
            "endpoint_url": "https://graph.facebook.com/v19.0/PHONE_NUMBER_ID/messages",
            "credentials_env_key": "WHATSAPP_CLOUD_TOKEN",
            "notes": "Supports Meta Cloud API, Twilio WhatsApp, or custom BSP webhook.",
        },
    ]

    DEFAULT_TEMPLATES = [
        {
            "template_code": "TPL-ATT-ABSENT",
            "name": "Student Attendance Alert",
            "scenario_type": "Attendance Alert",
            "channel": "SMS",
            "subject_template": "Attendance Alert: {student_name}",
            "body_template": (
                "{school_name}: Dear {guardian_name}, your ward {student_name} ({student_id}) "
                "was marked {status} on {attendance_date}. Please contact the school office if needed."
            ),
            "variables_hint": "{school_name}, {guardian_name}, {student_name}, {student_id}, {status}, {attendance_date}",
        },
        {
            "template_code": "TPL-FEE-DUE",
            "name": "Fee Payment Reminder Alert",
            "scenario_type": "Fee Due Alert",
            "channel": "SMS",
            "subject_template": "Fee Due Reminder: {invoice_no}",
            "body_template": (
                "{school_name}: Dear {guardian_name}, fee invoice {invoice_no} for {student_name} "
                "has an outstanding due of {currency} {due_amount:.2f} (Due Date: {due_date})."
            ),
            "variables_hint": "{school_name}, {guardian_name}, {student_name}, {invoice_no}, {due_amount}, {due_date}, {currency}",
        },
        {
            "template_code": "TPL-RES-PUB",
            "name": "Exam Result Notification",
            "scenario_type": "Result Notification",
            "channel": "Email",
            "subject_template": "{exam_name} Result Published - {student_name}",
            "body_template": (
                "Dear {guardian_name},\n\nThe result for {exam_name} of {student_name} ({student_id}) is now available.\n"
                "Total: {total_obtained}/{total_full_marks} | Grade: {overall_grade} | GPA: {gpa:.2f} | Class Rank: {class_rank}.\n\n"
                "Regards,\n{school_name}"
            ),
            "variables_hint": "{school_name}, {guardian_name}, {student_name}, {student_id}, {exam_name}, {gpa}, {overall_grade}, {class_rank}",
        },
        {
            "template_code": "TPL-ADM-UPD",
            "name": "Admission Application Notification",
            "scenario_type": "Admission Notification",
            "channel": "Email",
            "subject_template": "Admission Update [{applicant_id}] - {status}",
            "body_template": (
                "Dear {guardian_name},\n\nApplication {applicant_id} for {applicant_name} is currently '{status}'. "
                "{details}\n\nRegards,\nAdmissions Office, {school_name}"
            ),
            "variables_hint": "{school_name}, {guardian_name}, {applicant_name}, {applicant_id}, {status}, {details}",
        },
        {
            "template_code": "TPL-EMG-ALERT",
            "name": "Emergency Campus Notification",
            "scenario_type": "Emergency Notification",
            "channel": "WhatsApp",
            "subject_template": "URGENT EMERGENCY ALERT: {title}",
            "body_template": "[URGENT - {school_name}] {title}: {message}",
            "whatsapp_template_name": "school_emergency_alert",
            "variables_hint": "{school_name}, {title}, {message}",
        },
    ]

    @classmethod
    def seed_defaults_if_empty(cls, session: Session) -> Dict[str, int]:
        """Idempotently initializes starter configurable provider adapters and templates if missing."""
        p_added = 0
        for p in cls.DEFAULT_PROVIDER_PROFILES:
            exists = session.query(CommunicationProviderConfig).filter(
                CommunicationProviderConfig.provider_code == p["provider_code"]
            ).first()
            if not exists:
                CommunicationRepository.create_provider(session, **p)
                p_added += 1

        t_added = 0
        for t in cls.DEFAULT_TEMPLATES:
            exists = session.query(CommunicationTemplate).filter(
                CommunicationTemplate.template_code == t["template_code"]
            ).first()
            if not exists:
                CommunicationRepository.create_template(session, **t)
                t_added += 1
        return {"providers_added": p_added, "templates_added": t_added}

    @staticmethod
    def _school_context(session: Session) -> Dict[str, str]:
        setting = session.query(SchoolSetting).first()
        return {
            "school_name": setting.school_name if setting and setting.school_name else "EduManage Pro School",
            "currency": setting.currency_symbol if setting and getattr(setting, "currency_symbol", None) else "৳",
        }

    @staticmethod
    def _contact_for_student(student: Student, channel: str) -> Tuple[str, str, str]:
        """Returns (recipient_name, contact_value, recipient_type) best matched to requested channel."""
        guardian = student.guardian
        g_name = guardian.guardian_name if guardian else student.full_name
        if channel == "Email":
            email = (guardian.guardian_email if guardian and guardian.guardian_email else None) or student.email or ""
            return g_name, email, "Guardian" if guardian else "Student"
        if channel in ("SMS", "WhatsApp"):
            phone = (
                (guardian.guardian_phone if guardian and guardian.guardian_phone else None)
                or student.phone
                or student.emergency_contact
                or ""
            )
            return g_name, phone, "Guardian" if guardian else "Student"
        return student.full_name, student.student_id, "Parents"

    @classmethod
    def _finalize_campaign(cls, session: Session, campaign_id: int, total: int, sent: int, failed: int) -> None:
        from app.models.communication import CommunicationCampaign

        camp = session.query(CommunicationCampaign).filter(CommunicationCampaign.id == campaign_id).first()
        if camp:
            camp.total_recipients = total
            camp.sent_count = sent
            camp.failed_count = failed
            camp.status = "Completed" if failed == 0 else ("Partial" if sent > 0 else "Failed")
            camp.completed_at = utc_now()
            session.commit()

    # -------------------------------------------------------------
    # 1. Automated Attendance Alert Trigger
    # -------------------------------------------------------------
    @classmethod
    def dispatch_attendance_alerts(
        cls,
        session: Session,
        target_date: Optional[date] = None,
        class_id: Optional[int] = None,
        statuses: Sequence[str] = ("Absent", "Late"),
        channels: Sequence[str] = ("InApp", "SMS"),
        triggered_by: str = "admin",
        custom_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        att_date = target_date or date.today()
        ctx = cls._school_context(session)
        q = session.query(StudentAttendance).options(
            joinedload(StudentAttendance.student).joinedload(Student.guardian)
        ).filter(
            StudentAttendance.attendance_date == att_date,
            StudentAttendance.status.in_(list(statuses)),
        )
        if class_id:
            q = q.filter(StudentAttendance.class_id == class_id)
        records = q.all()

        camp = CommunicationRepository.create_campaign(
            session,
            title=f"Attendance Alert ({att_date.isoformat()})",
            scenario_type="Attendance Alert",
            channels=list(channels),
            target_summary=f"{len(records)} student attendance records",
            triggered_by=triggered_by,
        )

        sent = 0
        failed = 0
        total = 0
        for rec in records:
            stu = rec.student
            if not stu:
                continue
            g_name = stu.guardian.guardian_name if stu.guardian else "Guardian"
            body = (
                f"{ctx['school_name']}: Dear {g_name}, {stu.full_name} ({stu.student_id}) "
                f"was marked {rec.status} on {att_date.isoformat()}."
                + (f" Note: {custom_note}" if custom_note else "")
            )
            subj = f"Attendance Alert: {stu.full_name} ({rec.status})"
            for ch in channels:
                r_name, r_contact, r_type = cls._contact_for_student(stu, ch)
                total += 1
                log = CommunicationRepository.send_message(
                    session,
                    channel=ch,
                    recipient_name=r_name,
                    recipient_contact=r_contact,
                    subject=subj,
                    message_body=body,
                    scenario_type="Attendance Alert",
                    recipient_type=r_type,
                    recipient_id=stu.id,
                    student_id=stu.id,
                    campaign_id=camp.id,
                    in_app_item_type="Alert",
                    severity="Warning",
                    action_module="attendance",
                    triggered_by=triggered_by,
                    commit=False,
                )
                if log.status in ("Sent", "Delivered", "Read"):
                    sent += 1
                else:
                    failed += 1

        session.commit()
        cls._finalize_campaign(session, camp.id, total, sent, failed)
        return {"campaign_id": camp.id, "matched_records": len(records), "dispatched": total, "sent": sent, "failed": failed}

    # -------------------------------------------------------------
    # 2. Automated Fee Due Alert Trigger
    # -------------------------------------------------------------
    @classmethod
    def dispatch_fee_due_alerts(
        cls,
        session: Session,
        class_id: Optional[int] = None,
        overdue_only: bool = False,
        min_due: float = 1.0,
        channels: Sequence[str] = ("InApp", "SMS", "Email"),
        triggered_by: str = "admin",
    ) -> Dict[str, Any]:
        ctx = cls._school_context(session)
        q = session.query(StudentFee).options(
            joinedload(StudentFee.student).joinedload(Student.guardian)
        ).filter(
            StudentFee.is_deleted == False,
            StudentFee.due_amount >= min_due,
            StudentFee.status.in_(["Unpaid", "Partial", "Overdue"]),
        )
        if overdue_only:
            q = q.filter(StudentFee.due_date < date.today())
        if class_id:
            q = q.join(StudentFee.student).filter(Student.class_id == class_id)
        fees = q.all()

        camp = CommunicationRepository.create_campaign(
            session,
            title=f"Fee Due Alert ({date.today().isoformat()})",
            scenario_type="Fee Due Alert",
            channels=list(channels),
            target_summary=f"{len(fees)} unpaid/overdue student invoices",
            triggered_by=triggered_by,
        )

        sent = 0
        failed = 0
        total = 0
        for sf in fees:
            stu = sf.student
            if not stu:
                continue
            g_name = stu.guardian.guardian_name if stu.guardian else "Guardian"
            inv_label = sf.invoice_no or f"FEE-{sf.id}"
            subj = f"Fee Due Reminder: {inv_label} ({stu.full_name})"
            body = (
                f"{ctx['school_name']}: Dear {g_name}, invoice {inv_label} for {stu.full_name} ({stu.student_id}) "
                f"has a pending due of {ctx['currency']} {float(sf.due_amount):.2f} (Due Date: {sf.due_date})."
            )
            for ch in channels:
                r_name, r_contact, r_type = cls._contact_for_student(stu, ch)
                total += 1
                log = CommunicationRepository.send_message(
                    session,
                    channel=ch,
                    recipient_name=r_name,
                    recipient_contact=r_contact,
                    subject=subj,
                    message_body=body,
                    scenario_type="Fee Due Alert",
                    recipient_type=r_type,
                    recipient_id=stu.id,
                    student_id=stu.id,
                    campaign_id=camp.id,
                    in_app_item_type="Alert",
                    severity="Warning",
                    action_module="fees",
                    triggered_by=triggered_by,
                    commit=False,
                )
                if log.status in ("Sent", "Delivered", "Read"):
                    sent += 1
                else:
                    failed += 1

        session.commit()
        cls._finalize_campaign(session, camp.id, total, sent, failed)
        return {"campaign_id": camp.id, "matched_invoices": len(fees), "dispatched": total, "sent": sent, "failed": failed}

    # -------------------------------------------------------------
    # 3. Result Notification Trigger
    # -------------------------------------------------------------
    @classmethod
    def dispatch_result_notifications(
        cls,
        session: Session,
        exam_term_id: int,
        class_id: Optional[int] = None,
        published_only: bool = True,
        channels: Sequence[str] = ("InApp", "Email", "SMS"),
        triggered_by: str = "admin",
    ) -> Dict[str, Any]:
        ctx = cls._school_context(session)
        term = session.query(ExamTerm).filter(ExamTerm.id == exam_term_id).first()
        exam_name = term.name if term else f"Exam Term #{exam_term_id}"

        q = session.query(ExamResultSummary).options(
            joinedload(ExamResultSummary.student).joinedload(Student.guardian)
        ).filter(
            ExamResultSummary.is_deleted == False,
            ExamResultSummary.exam_term_id == exam_term_id,
        )
        if published_only:
            q = q.filter(ExamResultSummary.is_published == True)
        if class_id:
            q = q.filter(ExamResultSummary.class_id == class_id)
        summaries = q.all()

        camp = CommunicationRepository.create_campaign(
            session,
            title=f"Result Notification: {exam_name}",
            scenario_type="Result Notification",
            channels=list(channels),
            target_summary=f"{len(summaries)} student result summaries",
            triggered_by=triggered_by,
        )

        sent = 0
        failed = 0
        total = 0
        for res in summaries:
            stu = res.student
            if not stu:
                continue
            g_name = stu.guardian.guardian_name if stu.guardian else "Guardian"
            subj = f"Result Published: {exam_name} - {stu.full_name}"
            body = (
                f"{ctx['school_name']}: Dear {g_name}, {exam_name} result for {stu.full_name} ({stu.student_id}) "
                f"is ready. Marks: {res.total_obtained:.1f}/{res.total_full_marks:.1f}, "
                f"Grade: {res.overall_grade}, GPA: {res.gpa:.2f}, CGPA: {res.cgpa:.2f}, Rank: {res.class_rank or '-'}."
            )
            for ch in channels:
                r_name, r_contact, r_type = cls._contact_for_student(stu, ch)
                total += 1
                log = CommunicationRepository.send_message(
                    session,
                    channel=ch,
                    recipient_name=r_name,
                    recipient_contact=r_contact,
                    subject=subj,
                    message_body=body,
                    scenario_type="Result Notification",
                    recipient_type=r_type,
                    recipient_id=stu.id,
                    student_id=stu.id,
                    campaign_id=camp.id,
                    in_app_item_type="Notification",
                    severity="Success" if res.passed_all else "Info",
                    action_module="exams",
                    triggered_by=triggered_by,
                    commit=False,
                )
                if log.status in ("Sent", "Delivered", "Read"):
                    sent += 1
                else:
                    failed += 1

        session.commit()
        cls._finalize_campaign(session, camp.id, total, sent, failed)
        return {"campaign_id": camp.id, "matched_results": len(summaries), "dispatched": total, "sent": sent, "failed": failed}

    # -------------------------------------------------------------
    # 4. Admission Notification Trigger
    # -------------------------------------------------------------
    @classmethod
    def dispatch_admission_notifications(
        cls,
        session: Session,
        status_filter: Optional[str] = None,
        application_ids: Optional[List[int]] = None,
        channels: Sequence[str] = ("InApp", "Email", "SMS"),
        custom_message: Optional[str] = None,
        triggered_by: str = "admin",
    ) -> Dict[str, Any]:
        ctx = cls._school_context(session)
        q = session.query(AdmissionApplication).filter(AdmissionApplication.is_deleted == False)
        if status_filter and status_filter != "All":
            q = q.filter(AdmissionApplication.status == status_filter)
        if application_ids:
            q = q.filter(AdmissionApplication.id.in_(application_ids))
        apps = q.all()

        camp = CommunicationRepository.create_campaign(
            session,
            title=f"Admission Notification ({status_filter or 'Filtered'})",
            scenario_type="Admission Notification",
            channels=list(channels),
            target_summary=f"{len(apps)} admission applicants",
            triggered_by=triggered_by,
        )

        sent = 0
        failed = 0
        total = 0
        for app_row in apps:
            g_name = app_row.guardian_name or app_row.full_name
            extra = f" Merit Rank: #{app_row.merit_rank}." if app_row.merit_rank else ""
            if custom_message:
                extra = f" {custom_message}"
            subj = f"Admission Status Update [{app_row.applicant_id}]: {app_row.status}"
            body = (
                f"{ctx['school_name']}: Dear {g_name}, admission application {app_row.applicant_id} "
                f"for {app_row.full_name} is now '{app_row.status}'.{extra}"
            )
            for ch in channels:
                if ch == "Email":
                    contact = app_row.guardian_email or app_row.email or ""
                elif ch in ("SMS", "WhatsApp"):
                    contact = app_row.guardian_phone or app_row.phone or app_row.emergency_contact or ""
                else:
                    contact = app_row.applicant_id
                total += 1
                log = CommunicationRepository.send_message(
                    session,
                    channel=ch,
                    recipient_name=g_name,
                    recipient_contact=contact,
                    subject=subj,
                    message_body=body,
                    scenario_type="Admission Notification",
                    recipient_type="Applicant",
                    recipient_id=app_row.id,
                    campaign_id=camp.id,
                    in_app_item_type="Notification",
                    severity="Success" if app_row.status in ("Selected", "Admitted") else "Info",
                    action_module="admissions",
                    triggered_by=triggered_by,
                    commit=False,
                )
                if log.status in ("Sent", "Delivered", "Read"):
                    sent += 1
                else:
                    failed += 1

        session.commit()
        cls._finalize_campaign(session, camp.id, total, sent, failed)
        return {"campaign_id": camp.id, "matched_applications": len(apps), "dispatched": total, "sent": sent, "failed": failed}

    # -------------------------------------------------------------
    # 5. Emergency Notification Broadcast
    # -------------------------------------------------------------
    @classmethod
    def dispatch_emergency_notification(
        cls,
        session: Session,
        title: str,
        message: str,
        target_audience: str = "All",  # All, Parents, Teachers, Staff
        class_id: Optional[int] = None,
        channels: Sequence[str] = ("InApp", "SMS", "WhatsApp", "Email"),
        triggered_by: str = "admin",
    ) -> Dict[str, Any]:
        ctx = cls._school_context(session)
        recipients: List[Dict[str, Any]] = []

        if target_audience in ("All", "Parents", "Students"):
            sq = session.query(Student).options(joinedload(Student.guardian)).filter(
                Student.is_deleted == False,
                Student.status == StudentStatus.ACTIVE,
            )
            if class_id:
                sq = sq.filter(Student.class_id == class_id)
            for s in sq.all():
                recipients.append(
                    {
                        "type": "Guardian" if s.guardian else "Student",
                        "id": s.id,
                        "student_id": s.id,
                        "name": s.guardian.guardian_name if s.guardian else s.full_name,
                        "phone": (s.guardian.guardian_phone if s.guardian else None) or s.emergency_contact or s.phone or "",
                        "email": (s.guardian.guardian_email if s.guardian else None) or s.email or "",
                    }
                )

        if target_audience in ("All", "Teachers"):
            teachers = session.query(Teacher).filter(
                Teacher.is_deleted == False,
                Teacher.status == EmployeeStatus.ACTIVE,
            ).all()
            for t in teachers:
                recipients.append(
                    {"type": "Teacher", "id": t.id, "student_id": None, "name": t.full_name, "phone": t.phone or "", "email": t.email or ""}
                )

        if target_audience in ("All", "Staff"):
            staff_rows = session.query(Staff).filter(
                Staff.is_deleted == False,
                Staff.status == EmployeeStatus.ACTIVE,
            ).all()
            for st in staff_rows:
                recipients.append(
                    {"type": "Staff", "id": st.id, "student_id": None, "name": st.full_name, "phone": st.phone or "", "email": st.email or ""}
                )

        camp = CommunicationRepository.create_campaign(
            session,
            title=f"EMERGENCY: {title}",
            scenario_type="Emergency Notification",
            channels=list(channels),
            target_summary=f"{target_audience} ({len(recipients)} contacts)",
            triggered_by=triggered_by,
        )

        full_body = f"[EMERGENCY - {ctx['school_name']}] {title}: {message}"
        sent = 0
        failed = 0
        total = 0

        # Always create a single pinned institutional In-App Emergency Alert if InApp is included
        in_app_posted = False
        if "InApp" in channels:
            total += 1
            log = CommunicationRepository.send_message(
                session,
                channel="InApp",
                recipient_name=f"{target_audience} Campus Feed",
                recipient_contact="in-app-broadcast",
                subject=f"EMERGENCY: {title}",
                message_body=full_body,
                scenario_type="Emergency Notification",
                recipient_type="All" if target_audience == "All" else target_audience,
                campaign_id=camp.id,
                in_app_item_type="Alert",
                severity="Critical",
                action_module="communications",
                triggered_by=triggered_by,
                commit=False,
            )
            in_app_posted = True
            if log.status in ("Sent", "Delivered", "Read"):
                sent += 1
            else:
                failed += 1

        ext_channels = [c for c in channels if c != "InApp"]
        for r in recipients:
            for ch in ext_channels:
                contact = r["email"] if ch == "Email" else r["phone"]
                total += 1
                log = CommunicationRepository.send_message(
                    session,
                    channel=ch,
                    recipient_name=r["name"],
                    recipient_contact=contact,
                    subject=f"URGENT EMERGENCY: {title}",
                    message_body=full_body,
                    scenario_type="Emergency Notification",
                    recipient_type=r["type"],
                    recipient_id=r["id"],
                    student_id=r["student_id"],
                    campaign_id=camp.id,
                    whatsapp_template_name="school_emergency_alert",
                    triggered_by=triggered_by,
                    commit=False,
                )
                if log.status in ("Sent", "Delivered", "Read"):
                    sent += 1
                else:
                    failed += 1

        session.commit()
        cls._finalize_campaign(session, camp.id, total, sent, failed)
        return {
            "campaign_id": camp.id,
            "recipients_targeted": len(recipients),
            "in_app_alert_created": in_app_posted,
            "dispatched": total,
            "sent": sent,
            "failed": failed,
        }

    # -------------------------------------------------------------
    # 6. Multi-Sheet Excel Export
    # -------------------------------------------------------------
    @staticmethod
    def _style_headers(ws, headers: List[str], row_idx: int = 3, fill_hex: str = "1E3A8A") -> Border:
        fill = PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid")
        font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )
        for c_idx, title in enumerate(headers, 1):
            cell = ws.cell(row=row_idx, column=c_idx, value=title)
            cell.fill = fill
            cell.font = font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border
        ws.row_dimensions[row_idx].height = 24
        return border

    @staticmethod
    def _autofit(ws):
        for col in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col), default=10)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(max_len + 3, 12), 48)

    @staticmethod
    def export_communication_logs_excel(session: Session, file_path: str) -> str:
        logs = CommunicationRepository.get_communication_logs(session, limit=2000)
        inapp = CommunicationRepository.get_in_app_feed(session, limit=1000)
        providers = CommunicationRepository.get_providers(session)
        templates = CommunicationRepository.get_templates(session)

        wb = Workbook()

        # Sheet 1: Communication Audit Logs
        ws1 = wb.active
        ws1.title = "Communication Logs"
        ws1["A1"] = f"EDUMANAGE PRO - COMMUNICATION DISPATCH AUDIT LOG ({date.today().isoformat()})"
        ws1["A1"].font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
        b1 = CommunicationService._style_headers(
            ws1,
            ["Log Code", "Sent At", "Channel", "Provider", "Driver", "Scenario", "Recipient Type", "Recipient", "Contact", "Status", "Ext Message ID", "Error"],
            row_idx=3,
            fill_hex="1E3A8A",
        )
        for r_idx, l in enumerate(logs, start=4):
            vals = [
                l.log_code, str(l.sent_at or ""), l.channel, l.provider_name, l.driver_used,
                l.scenario_type, l.recipient_type, l.recipient_name, l.recipient_contact,
                l.status, l.external_message_id or "-", l.error_message or "-",
            ]
            for c_idx, v in enumerate(vals, 1):
                ws1.cell(row=r_idx, column=c_idx, value=v).border = b1
        CommunicationService._autofit(ws1)

        # Sheet 2: In-App Notifications / Announcements / Notices / Alerts
        ws2 = wb.create_sheet("In-App Feed")
        ws2["A1"] = "IN-APP NOTIFICATIONS, ANNOUNCEMENTS, NOTICES & ALERTS"
        b2 = CommunicationService._style_headers(
            ws2,
            ["Ref No", "Type", "Scenario", "Severity", "Audience", "Title", "Message", "Read", "Created By", "Created At"],
            row_idx=3,
            fill_hex="0F766E",
        )
        for r_idx, item in enumerate(inapp, start=4):
            vals = [
                item.reference_no, item.item_type, item.scenario_type, item.severity,
                item.target_audience, item.title, item.message, "Yes" if item.is_read else "Unread",
                item.created_by, str(item.created_at),
            ]
            for c_idx, v in enumerate(vals, 1):
                ws2.cell(row=r_idx, column=c_idx, value=v).border = b2
        CommunicationService._autofit(ws2)

        # Sheet 3: Configured Provider Adapters
        ws3 = wb.create_sheet("Provider Adapters")
        ws3["A1"] = "CONFIGURED SMS / EMAIL / WHATSAPP BUSINESS PROVIDER INTERFACES"
        b3 = CommunicationService._style_headers(
            ws3,
            ["Code", "Channel", "Provider Name", "Driver Key", "Default", "Active", "Sandbox", "Sender ID", "Endpoint", "Last Test"],
            row_idx=3,
            fill_hex="4338CA",
        )
        for r_idx, p in enumerate(providers, start=4):
            vals = [
                p.provider_code, p.channel, p.provider_name, p.driver_key,
                "Yes" if p.is_default else "No", "Active" if p.is_active else "Inactive",
                "Sandbox" if p.sandbox_mode else "Live", p.sender_id or "-",
                p.endpoint_url or "-", p.last_test_status or "-",
            ]
            for c_idx, v in enumerate(vals, 1):
                ws3.cell(row=r_idx, column=c_idx, value=v).border = b3
        CommunicationService._autofit(ws3)

        # Sheet 4: Templates
        ws4 = wb.create_sheet("Templates")
        ws4["A1"] = "COMMUNICATION SCENARIO TEMPLATES"
        b4 = CommunicationService._style_headers(
            ws4,
            ["Code", "Name", "Scenario", "Channel", "Subject", "Body Template", "WhatsApp Template"],
            row_idx=3,
            fill_hex="0F172A",
        )
        for r_idx, t in enumerate(templates, start=4):
            vals = [
                t.template_code, t.name, t.scenario_type, t.channel,
                t.subject_template or "-", t.body_template, t.whatsapp_template_name or "-",
            ]
            for c_idx, v in enumerate(vals, 1):
                ws4.cell(row=r_idx, column=c_idx, value=v).border = b4
        CommunicationService._autofit(ws4)

        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        wb.save(file_path)
        return file_path
