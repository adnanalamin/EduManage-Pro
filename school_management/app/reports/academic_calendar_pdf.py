"""
EduManage Pro - Annual Academic Calendar & Holiday Planner PDF
Phase 13: Landscape A4 ReportLab Event Roster & Holiday Schedule
"""

import os
from datetime import date
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, colors


class AcademicCalendarPDFGenerator:
    """Generates official landscape annual event & holiday calendar PDF."""

    @classmethod
    def generate_calendar_pdf(cls, events, school, output_pdf_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_pdf_path,
            pagesize=landscape(letter),
            leftMargin=30,
            rightMargin=30,
            topMargin=30,
            bottomMargin=30
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CalTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=18,
            textColor=HexColor('#0F172A')
        )
        sub_style = ParagraphStyle(
            'CalSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=12,
            textColor=HexColor('#475569')
        )

        elements = []

        school_title = school.school_name if hasattr(school, 'school_name') and school.school_name else "Ideal Model High School & College"
        header_text = f"<b>{school_title}</b> — Annual Academic Calendar & Institutional Event Planner"
        elements.append(Paragraph(header_text, title_style))

        meta_text = f"Official Schedule for Academic Session {date.today().year} &bull; Generated on: {date.today().strftime('%B %d, %Y')}"
        elements.append(Paragraph(meta_text, sub_style))
        elements.append(Spacer(1, 14))

        # Table Headers
        table_data = [[
            "SL",
            "Event Title",
            "Category",
            "Start Date",
            "End Date",
            "Timing",
            "Venue",
            "Audience",
            "Holiday?",
            "Organizer"
        ]]

        for idx, ev in enumerate(events, 1):
            start_str = ev.start_date.strftime("%b %d, %Y")
            end_str = ev.end_date.strftime("%b %d, %Y")
            timing = f"{ev.start_time or ''} - {ev.end_time or ''}".strip(" -") or "All Day"
            is_hol_badge = "★ HOLIDAY" if ev.is_holiday else "Regular"

            table_data.append([
                str(idx),
                ev.event_title,
                ev.event_category,
                start_str,
                end_str,
                timing,
                ev.venue[:22],
                ev.target_audience,
                is_hol_badge,
                ev.organizer[:24]
            ])

        col_widths = [24, 150, 60, 65, 65, 75, 95, 60, 65, 85]
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1E3A8A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F8FAFC')]),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ]))

        elements.append(t)
        doc.build(elements)
        return output_pdf_path
