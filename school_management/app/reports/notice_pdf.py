"""
EduManage Pro - Official School Circular & Notice Letterhead Generator
Phase 13: Portrait A4 ReportLab Memo & Circular Document
"""

import os
from datetime import date
from reportlab.lib.pagesizes import letter, portrait
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, colors


class NoticeLetterheadGenerator:
    """Generates official school circular memo PDFs with institutional branding and signature blocks."""

    @classmethod
    def generate_notice_pdf(cls, notice, school, output_pdf_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_pdf_path,
            pagesize=portrait(letter),
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()

        school_title_style = ParagraphStyle(
            'SchoolHeader',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            alignment=1,  # Centered
            textColor=HexColor('#1E3A8A')
        )
        sub_header_style = ParagraphStyle(
            'SchoolSubHeader',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            alignment=1,
            textColor=HexColor('#475569')
        )
        memo_title_style = ParagraphStyle(
            'MemoTitle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            alignment=1,
            textColor=HexColor('#0F172A')
        )
        body_style = ParagraphStyle(
            'NoticeBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10.5,
            leading=15,
            textColor=HexColor('#1E293B')
        )
        meta_label_style = ParagraphStyle(
            'MetaLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=HexColor('#334155')
        )

        elements = []

        # 1. Header Letterhead
        school_name = school.school_name if hasattr(school, 'school_name') and school.school_name else "IDEAL MODEL HIGH SCHOOL & COLLEGE"
        eiin = school.eiin_number if hasattr(school, 'eiin_number') and school.eiin_number else "EIIN: 134211"
        address = school.address if hasattr(school, 'address') and school.address else "Plot 12, Sector 7, Uttara, Dhaka, Bangladesh"
        contact = f"Phone: {school.phone if hasattr(school, 'phone') else '+880 1712-345678'} | Email: {school.email if hasattr(school, 'email') else 'contact@idealmodel.edu.bd'}"

        elements.append(Paragraph(school_name.upper(), school_title_style))
        elements.append(Paragraph(f"{address} &bull; {eiin}", sub_header_style))
        elements.append(Paragraph(contact, sub_header_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=HexColor('#1E3A8A'), spaceAfter=12))

        # 2. Circular Meta Details Table
        pub_date_str = notice.publish_date.strftime("%B %d, %Y") if notice.publish_date else date.today().strftime("%B %d, %Y")
        priority_color = "#DC2626" if notice.priority == "Urgent" else "#D97706" if notice.priority == "Important" else "#059669"

        meta_data = [
            [
                Paragraph(f"<b>Circular Ref No:</b> <font color='#1E3A8A'>{notice.reference_no}</font>", meta_label_style),
                Paragraph(f"<b>Date:</b> {pub_date_str}", meta_label_style)
            ],
            [
                Paragraph(f"<b>Target Audience:</b> {notice.target_audience}", meta_label_style),
                Paragraph(f"<b>Priority:</b> <font color='{priority_color}'>{notice.priority.upper()}</font>", meta_label_style)
            ],
            [
                Paragraph(f"<b>Category:</b> {notice.category}", meta_label_style),
                Paragraph(f"<b>Issued By:</b> {notice.created_by}", meta_label_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[270, 270])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

        # 3. Notice Subject / Heading
        subject_text = f"<u>SUBJECT: {notice.title.upper()}</u>"
        elements.append(Paragraph(subject_text, memo_title_style))
        elements.append(Spacer(1, 14))

        # 4. Notice Body
        # Split lines to preserve paragraphs
        paragraphs = notice.content.split('\n')
        for p in paragraphs:
            if p.strip():
                elements.append(Paragraph(p.strip(), body_style))
                elements.append(Spacer(1, 8))

        elements.append(Spacer(1, 35))

        # 5. Signature Section
        sig_data = [
            [
                Paragraph("<b>Prepared by:</b><br/>Executive Office Assistant<br/>General Administration", meta_label_style),
                Paragraph("<b>Approved & Issued by:</b><br/>___________________________<br/><b>Prof. Dr. Mohammad Rafiqul Islam</b><br/>Principal & Secretary of Governing Body", meta_label_style)
            ]
        ]
        sig_table = Table(sig_data, colWidths=[270, 270])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ]))
        elements.append(sig_table)

        doc.build(elements)
        return output_pdf_path
