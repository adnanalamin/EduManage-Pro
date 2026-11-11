"""
EduManage Pro - Library Circulation Report PDF Generator
Phase 10: Landscape A4 ReportLab Circulation & Overdue Audit Statement
"""

import os
from datetime import date
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from app.models.library import BookCirculation
from app.models.school import SchoolSetting


class CirculationReportPDFGenerator:
    """Generates official landscape A4 circulation audit and overdue fine reports."""

    @classmethod
    def generate_report(
        cls,
        circulations: List[BookCirculation],
        stats: Dict[str, Any],
        school: Optional[SchoolSetting] = None,
        output_path: str = "circulation_audit_report.pdf"
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            leftMargin=36,
            rightMargin=36,
            topMargin=30,
            bottomMargin=30
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'SchoolTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            alignment=1,
            textColor=colors.HexColor('#0F172A')
        )

        sub_style = ParagraphStyle(
            'SchoolSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            alignment=1,
            textColor=colors.HexColor('#64748B')
        )

        meta_style = ParagraphStyle(
            'MetaStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            alignment=1,
            textColor=colors.HexColor('#065F46')
        )

        cell_style = ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#1E293B')
        )

        cell_bold = ParagraphStyle(
            'CellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#0F172A')
        )

        story = []

        # Header
        school_name = school.school_name if school else "Ideal Model High School & College"
        school_address = school.address if (school and school.address) else "Road 12, Dhanmondi, Dhaka-1209 • Contact: info@edumanage.edu"

        story.append(Paragraph(school_name.upper(), title_style))
        story.append(Paragraph(school_address, sub_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph("LIBRARY CIRCULATION & OVERDUE AUDIT STATEMENT", meta_style))
        story.append(Paragraph(f"Audit Date: {date.today().strftime('%B %d, %Y')} • Total Records: {len(circulations)}", sub_style))
        story.append(Spacer(1, 12))

        # KPI Metrics Table
        kpi_data = [
            [
                f"Total Catalog Titles: {stats.get('total_titles', 0)}",
                f"Total Copies: {stats.get('total_inventory_copies', 0)}",
                f"Currently Issued: {stats.get('currently_issued', 0)}",
                f"Overdue Loans: {stats.get('overdue_count', 0)}",
                f"Fines Collected: ${stats.get('total_fine_collected', 0.0):.2f}"
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[150, 150, 150, 150, 160])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ECFDF5')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#10B981')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#A7F3D0')),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#065F46')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 12))

        # Table Headers
        headers = [
            "Loan ID", "Accession No", "Book Title", "Borrower Name",
            "Member Type", "Issue Date", "Due Date", "Return Date", "Fine ($)", "Status"
        ]
        col_widths = [45, 65, 175, 140, 65, 60, 60, 60, 45, 55]

        table_data = [[Paragraph(f"<b>{h}</b>", cell_bold) for h in headers]]

        for circ in circulations:
            borrower_name = "Patron"
            if circ.member:
                if circ.member.student:
                    borrower_name = f"{circ.member.student.full_name} ({circ.member.member_id})"
                elif circ.member.teacher:
                    borrower_name = f"{circ.member.teacher.full_name} ({circ.member.member_id})"
                elif circ.member.staff:
                    borrower_name = f"{circ.member.staff.full_name} ({circ.member.member_id})"
                else:
                    borrower_name = circ.member.member_id

            book_acc = circ.book.accession_no if circ.book else "-"
            book_title = circ.book.title[:38] if circ.book else "Unknown Book"
            m_type = circ.member.member_type if circ.member else "-"

            status_color = "#047857" if circ.status == "Returned" else ("#DC2626" if circ.status == "Overdue" else "#2563EB")
            status_cell = Paragraph(f"<font color='{status_color}'><b>{circ.status}</b></font>", cell_style)

            row = [
                Paragraph(f"#{circ.id:04d}", cell_style),
                Paragraph(book_acc, cell_style),
                Paragraph(book_title, cell_style),
                Paragraph(borrower_name[:28], cell_style),
                Paragraph(m_type, cell_style),
                Paragraph(circ.issue_date, cell_style),
                Paragraph(circ.due_date, cell_style),
                Paragraph(circ.return_date or "—", cell_style),
                Paragraph(f"${circ.fine_amount:.2f}", cell_style),
                status_cell
            ]
            table_data.append(row)

        loan_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        loan_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#065F46')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(loan_table)
        story.append(Spacer(1, 24))

        # Signatures
        sig_data = [
            ["_______________________________", "_______________________________"],
            ["Chief Librarian / Officer In-Charge", "Principal / Head of Institution"]
        ]
        sig_table = Table(sig_data, colWidths=[385, 385])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#475569')),
        ]))
        story.append(sig_table)

        doc.build(story)
        return output_path
