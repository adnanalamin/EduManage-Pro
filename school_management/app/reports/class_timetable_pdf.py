"""
EduManage Pro - Class Timetable PDF Generator
Phase 9: Landscape A4 ReportLab Timetable Generator
"""

import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


class ClassTimetablePDFGenerator:
    """Generates official landscape A4 class timetable sheets."""

    @staticmethod
    def generate_timetable(
        class_name: str,
        section_name: str,
        shift_name: str,
        school_info: dict,
        periods: list,
        matrix: dict,
        output_path: str
    ) -> bool:
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
            fontSize=15,
            leading=18,
            alignment=1,
            textColor=colors.HexColor('#1E293B')
        )

        sub_style = ParagraphStyle(
            'SchoolSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            alignment=1,
            textColor=colors.HexColor('#64748B')
        )

        badge_style = ParagraphStyle(
            'Badge',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=13,
            alignment=1,
            textColor=colors.HexColor('#2563EB')
        )

        cell_title_style = ParagraphStyle(
            'CellTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=colors.HexColor('#0F172A')
        )

        cell_sub_style = ParagraphStyle(
            'CellSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7,
            leading=9,
            alignment=1,
            textColor=colors.HexColor('#475569')
        )

        story = []

        # 1. School Header
        story.append(Paragraph(school_info.get("school_name", "IDEAL MODEL HIGH SCHOOL & COLLEGE").upper(), title_style))
        eiin = school_info.get("eiin_number", "134211")
        address = school_info.get("address", "Sector 7, Uttara, Dhaka, Bangladesh")
        story.append(Paragraph(f"EIIN: {eiin} | Address: {address}", sub_style))
        story.append(Spacer(1, 6))

        # Title Badge
        story.append(Paragraph(
            f"OFFICIAL CLASS TIMETABLE — {class_name.upper()} (SECTION: {section_name.upper()} | SHIFT: {shift_name.upper()})",
            badge_style
        ))
        story.append(Spacer(1, 10))

        # 2. Build Grid Data
        teaching_periods = [p for p in periods if not p.get("is_break", False) or "Tiffin" in p.get("name", "")]

        # Header Row
        header_row = [Paragraph("<b>Day \\ Period</b>", ParagraphStyle('H1', parent=cell_title_style, textColor=colors.white, fontSize=9))]
        for p in teaching_periods:
            p_text = f"<b>{p['name']}</b><br/><font size='7'>{p['start_time']} - {p['end_time']}</font>"
            header_row.append(Paragraph(p_text, ParagraphStyle('HP', parent=cell_title_style, textColor=colors.white, fontSize=8)))

        table_data = [header_row]

        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
        for day in days:
            row = [Paragraph(f"<b>{day}</b>", ParagraphStyle('DayP', parent=cell_title_style, textColor=colors.HexColor('#1E293B'), fontSize=9))]
            for p in teaching_periods:
                if p.get("is_break"):
                    row.append(Paragraph("<b>TIFFIN<br/>BREAK</b>", ParagraphStyle('Brk', parent=cell_sub_style, textColor=colors.HexColor('#D97706'), alignment=1)))
                else:
                    entry = matrix.get(day, {}).get(p["id"])
                    if entry:
                        sub = entry.get("subject_name", "Subject")
                        teacher = entry.get("teacher_name", "")
                        room = entry.get("room_number", "")
                        content = f"<b>{sub}</b><br/>{teacher}<br/><font color='#2563EB'>{room}</font>"
                        row.append(Paragraph(content, cell_sub_style))
                    else:
                        row.append(Paragraph("—", ParagraphStyle('Em', parent=cell_sub_style, textColor=colors.HexColor('#CBD5E1'))))
            table_data.append(row)

        # Columns sizing
        num_cols = len(header_row)
        avail_width = 770
        col_widths = [80] + [(avail_width - 80) / (num_cols - 1)] * (num_cols - 1)

        grid_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        grid_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#F8FAFC')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        story.append(grid_table)
        story.append(Spacer(1, 25))

        # Signatures
        sig_data = [
            [
                Paragraph("__________________________<br/>Class Teacher", cell_sub_style),
                Paragraph("__________________________<br/>Timetable & Routine Coordinator", cell_sub_style),
                Paragraph("__________________________<br/><b>Principal / Head of Institute</b>", cell_title_style)
            ]
        ]
        sig_table = Table(sig_data, colWidths=[250, 270, 250])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(sig_table)

        doc.build(story)
        return True
