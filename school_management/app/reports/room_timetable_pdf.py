"""
EduManage Pro - Printable Room Timetable & Utilization PDF Generator (ReportLab)
Generates landscape A4 room occupancy schedules with weekly utilization percentage.
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class RoomTimetablePDFGenerator:
    """Generates official landscape A4 printable Room / Laboratory timetable sheets."""

    @staticmethod
    def generate_room_timetable(
        room_info: dict,
        school_info: dict,
        periods: list,
        matrix: dict,
        output_path: str,
        shift_name: str = "Morning",
        academic_year_label: str = "",
    ) -> bool:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            leftMargin=36,
            rightMargin=36,
            topMargin=30,
            bottomMargin=30,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "RmTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=15, leading=18, alignment=1, textColor=colors.HexColor("#1E293B")
        )
        badge_style = ParagraphStyle(
            "RmBadge", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=13, alignment=1, textColor=colors.HexColor("#0284C7")
        )
        cell_title_style = ParagraphStyle(
            "RmCellTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, alignment=1, textColor=colors.HexColor("#0F172A")
        )
        cell_sub_style = ParagraphStyle(
            "RmCellSub", parent=styles["Normal"], fontName="Helvetica", fontSize=7, leading=9, alignment=1, textColor=colors.HexColor("#475569")
        )

        story = [
            Paragraph(school_info.get("school_name", "EDUMANAGE PRO MODEL HIGH SCHOOL").upper(), title_style),
            Spacer(1, 4),
            Paragraph(
                f"OFFICIAL ROOM & LABORATORY TIMETABLE — {room_info.get('room_number', 'Room')} "
                f"(SHIFT: {shift_name.upper()}"
                + (f" | YEAR: {academic_year_label}" if academic_year_label else "")
                + ")",
                badge_style,
            ),
            Spacer(1, 8),
        ]

        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
        teaching_periods = [p for p in periods if not p.get("is_break", False) or "Tiffin" in p.get("name", "") or "Break" in p.get("name", "")]
        if not teaching_periods:
            teaching_periods = [
                {"id": 1, "name": "1st Period", "start_time": "08:45 AM", "end_time": "09:30 AM", "is_break": False}
            ]

        total_slots = sum(1 for p in teaching_periods if not p.get("is_break")) * len(days)
        occupied_slots = sum(
            1
            for d in days
            for p in teaching_periods
            if not p.get("is_break") and matrix.get(d, {}).get(p["id"])
        )
        util_pct = round((occupied_slots / total_slots) * 100.0, 1) if total_slots > 0 else 0.0

        info_data = [[
            Paragraph(f"<b>Room / Hall:</b> {room_info.get('room_number', '-')}", cell_sub_style),
            Paragraph(f"<b>Type:</b> {room_info.get('room_type', 'Classroom')}", cell_sub_style),
            Paragraph(f"<b>Capacity:</b> {room_info.get('capacity', 40)} Seats", cell_sub_style),
            Paragraph(f"<b>Weekly Utilization:</b> <font color='#0284C7'><b>{occupied_slots}/{total_slots} ({util_pct}%)</b></font>", cell_sub_style),
        ]]
        info_tbl = Table(info_data, colWidths=[190, 190, 180, 210])
        info_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F9FF")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BAE6FD")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([info_tbl, Spacer(1, 10)])

        header_row = [Paragraph("<b>Day \\ Period</b>", ParagraphStyle("RH", parent=cell_title_style, textColor=colors.white, fontSize=9))]
        for p in teaching_periods:
            header_row.append(
                Paragraph(
                    f"<b>{p['name']}</b><br/><font size='7'>{p['start_time']} - {p['end_time']}</font>",
                    ParagraphStyle("RHP", parent=cell_title_style, textColor=colors.white, fontSize=8),
                )
            )

        table_data = [header_row]
        for day in days:
            row = [Paragraph(f"<b>{day}</b>", cell_title_style)]
            for p in teaching_periods:
                if p.get("is_break"):
                    row.append(Paragraph("<b>BREAK</b>", ParagraphStyle("RBrk", parent=cell_sub_style, textColor=colors.HexColor("#D97706"))))
                else:
                    entry = matrix.get(day, {}).get(p["id"])
                    if entry:
                        cls_n = entry.get("class_name", "Class")
                        sec_n = entry.get("section_name", "")
                        sub_n = entry.get("subject_name", "")
                        t_n = entry.get("teacher_name", "")
                        sec_tag = f" ({sec_n})" if sec_n else ""
                        row.append(Paragraph(f"<b>{cls_n}{sec_tag}</b><br/>{sub_n}<br/><font color='#0284C7'>{t_n}</font>", cell_sub_style))
                    else:
                        row.append(Paragraph("Available", ParagraphStyle("REm", parent=cell_sub_style, textColor=colors.HexColor("#94A3B8"))))
            table_data.append(row)

        num_cols = len(header_row)
        col_widths = [80] + [(770 - 80) / max(1, num_cols - 1)] * max(1, num_cols - 1)
        grid = Table(table_data, colWidths=col_widths, repeatRows=1)
        grid.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0369A1")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#F8FAFC")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(grid)
        doc.build(story)
        return True
