"""
EduManage Pro - Teacher Workload & Routine PDF Generator
Phase 9: Landscape A4 ReportLab Individual Faculty Timetable
"""

import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


class TeacherRoutinePDFGenerator:
    """Generates official landscape A4 individual teacher timetable & duty schedules."""

    @staticmethod
    def generate_routine(
        teacher_info: dict,
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

        badge_style = ParagraphStyle(
            'Badge',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=13,
            alignment=1,
            textColor=colors.HexColor('#059669')
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
        story.append(Spacer(1, 4))
        story.append(Paragraph("FACULTY WEEKLY TEACHING WORKLOAD & ROUTINE", badge_style))
        story.append(Spacer(1, 8))

        # Teacher Profile Banner
        t_name = teacher_info.get("name", "Faculty Member")
        emp_id = teacher_info.get("employee_id", "EMP-000")
        dept = teacher_info.get("department", "General")
        designation = teacher_info.get("designation", "Lecturer")
        total_load = teacher_info.get("total_weekly_periods", 18)

        prof_data = [
            [
                Paragraph(f"<b>Teacher Name:</b> {t_name}", cell_sub_style),
                Paragraph(f"<b>Employee ID:</b> {emp_id}", cell_sub_style),
                Paragraph(f"<b>Department:</b> {dept}", cell_sub_style),
                Paragraph(f"<b>Weekly Periods:</b> <font color='#059669'><b>{total_load} Slots</b></font>", cell_sub_style)
            ]
        ]
        prof_table = Table(prof_data, colWidths=[200, 180, 200, 190])
        prof_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0FDF4')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BBF7D0')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(prof_table)
        story.append(Spacer(1, 10))

        # 2. Build Grid Data
        teaching_periods = [p for p in periods if not p.get("is_break", False) or "Tiffin" in p.get("name", "")]

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
                        cls_name = entry.get("class_name", "Class")
                        sec = entry.get("section_name", "")
                        sub = entry.get("subject_name", "")
                        room = entry.get("room_number", "")
                        content = f"<b>{cls_name} ({sec})</b><br/>{sub}<br/><font color='#059669'>{room}</font>"
                        row.append(Paragraph(content, cell_sub_style))
                    else:
                        row.append(Paragraph("Off", ParagraphStyle('Em', parent=cell_sub_style, textColor=colors.HexColor('#94A3B8'))))
            table_data.append(row)

        num_cols = len(header_row)
        avail_width = 770
        col_widths = [80] + [(avail_width - 80) / (num_cols - 1)] * (num_cols - 1)

        grid_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        grid_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#064E3B')),
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
                Paragraph("__________________________<br/>Teacher's Signature", cell_sub_style),
                Paragraph("__________________________<br/>Academic In-Charge", cell_sub_style),
                Paragraph("__________________________<br/><b>Principal Signature & Seal</b>", cell_title_style)
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
