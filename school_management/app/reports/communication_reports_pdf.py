"""
EduManage Pro - Communication Center PDF Report Generator
Generates printable A4 landscape audit statements of communication dispatches & in-app alerts.
"""

from datetime import date
import os
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.communication import CommunicationLog
from app.models.school import SchoolSetting


class CommunicationReportsPDFGenerator:
    """Generates clean printable PDF audit reports for multi-channel communication logs."""

    @classmethod
    def generate_communication_audit_pdf(
        cls,
        logs: List[CommunicationLog],
        school: Optional[SchoolSetting] = None,
        output_path: str = "communication_audit_report.pdf",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            leftMargin=26,
            rightMargin=26,
            topMargin=26,
            bottomMargin=26,
        )
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("ComH1", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=15, alignment=1, textColor=colors.HexColor("#0F172A"))
        h2 = ParagraphStyle("ComH2", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, alignment=1, textColor=colors.HexColor("#1E3A8A"))
        sub = ParagraphStyle("ComSub", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, alignment=1, textColor=colors.HexColor("#64748B"))

        school_name = school.school_name if school and getattr(school, "school_name", None) else "EduManage Pro School"
        sent_ok = sum(1 for l in logs if l.status in ("Sent", "Delivered", "Read"))
        failed = sum(1 for l in logs if l.status == "Failed")

        story = [
            Paragraph(school_name.upper(), h1),
            Paragraph("COMMUNICATION CENTER — MULTI-CHANNEL DISPATCH AUDIT REPORT", h2),
            Paragraph(
                f"Total Logs: {len(logs)} | Delivered/Sent: {sent_ok} | Failed: {failed} • Generated: {date.today().strftime('%B %d, %Y')}",
                sub,
            ),
            Spacer(1, 10),
        ]

        rows = [["Log Code", "Timestamp", "Channel", "Provider", "Scenario", "Recipient", "Contact", "Status", "Ext Ref"]]
        for l in logs[:250]:
            rows.append([
                l.log_code,
                str(l.sent_at)[:16] if l.sent_at else "-",
                l.channel,
                (l.provider_name or "-")[:22],
                (l.scenario_type or "-")[:20],
                (l.recipient_name or "-")[:22],
                (l.recipient_contact or "-")[:24],
                l.status,
                (l.external_message_id or "-")[:18],
            ])
        if len(rows) == 1:
            rows.append(["-", "-", "-", "No communication logs recorded", "-", "-", "-", "-", "-"])

        tbl = Table(rows, colWidths=[85, 82, 52, 115, 95, 105, 110, 56, 90], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        story.append(tbl)
        doc.build(story)
        return output_path
