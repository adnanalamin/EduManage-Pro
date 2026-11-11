"""
EduManage Pro - Hostel Night Roll Call & Curfew Report
Phase 12: Landscape A4 ReportLab Night Attendance & Inspection Manifest
"""

import os
from datetime import date
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, colors


class HostelRollCallPDFGenerator:
    """Generates official landscape Night Roll Call and Curfew inspection sheets for wardens."""

    @classmethod
    def generate_manifest(cls, block, allocations, school, output_pdf_path: str) -> str:
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
            'HostelTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=18,
            textColor=HexColor('#0F172A')
        )
        sub_style = ParagraphStyle(
            'HostelSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=12,
            textColor=HexColor('#475569')
        )

        elements = []

        school_title = school.school_name if hasattr(school, 'school_name') and school.school_name else "EduManage Residential Academy"
        block_name = block.block_name if block else "All Hostel Blocks"
        warden = block.warden_name if (block and block.warden_name) else "Hostel Warden"
        phone = block.warden_phone if (block and block.warden_phone) else "N/A"

        header_text = f"<b>{school_title}</b> — Hostel Night Roll Call & Curfew Register"
        elements.append(Paragraph(header_text, title_style))

        meta_text = (
            f"<b>Block:</b> {block_name} &nbsp;|&nbsp; "
            f"<b>Warden:</b> {warden} ({phone}) &nbsp;|&nbsp; "
            f"<b>Date:</b> {date.today().strftime('%A, %d %B %Y')} &nbsp;|&nbsp; "
            f"<b>Inspection Time:</b> 09:30 PM Curfew"
        )
        elements.append(Paragraph(meta_text, sub_style))
        elements.append(Spacer(1, 14))

        # Table Headers
        table_data = [[
            "SL",
            "Room No",
            "Bed",
            "Student ID",
            "Resident Name",
            "Class",
            "Guardian Contact",
            "Night Roll [P / A / Out]",
            "Warden Signature"
        ]]

        for idx, alloc in enumerate(allocations, 1):
            room_no = alloc.room.room_number if alloc.room else "N/A"
            bed_no = alloc.bed_number or "-"
            student_id = alloc.student.student_id if alloc.student else f"ID-{alloc.student_id}"
            student_name = f"{alloc.student.first_name} {alloc.student.last_name}" if alloc.student else "Unknown Student"
            class_name = alloc.student.current_class.name if (alloc.student and hasattr(alloc.student, 'current_class') and alloc.student.current_class) else "General"
            contact = alloc.emergency_phone or (alloc.student.emergency_contact if alloc.student else "") or "N/A"

            table_data.append([
                str(idx),
                room_no,
                bed_no,
                student_id,
                student_name,
                class_name,
                contact,
                "[  ] Present   [  ] Absent   [  ] Outpass",
                "____________________"
            ])

        col_widths = [26, 52, 40, 65, 130, 65, 105, 170, 95]
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#065F46')),  # Emerald 800
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (4, 1), (4, -1), 'LEFT'),
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
