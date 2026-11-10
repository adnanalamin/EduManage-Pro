"""
EduManage Pro - Student Examination Admit Card PDF Generator
Generates clean, landscape A5 Admit Cards with exam timetable routines using ReportLab.
"""

import os
from typing import Dict, Any, List
from datetime import datetime
from reportlab.lib.pagesizes import A5, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


class AdmitCardPDFGenerator:
    @staticmethod
    def generate_admit_card(
        student: Any,
        exam_term: Any,
        schedules: List[Any],
        school_info: Dict[str, str],
        output_path: str
    ) -> bool:
        """
        Builds printable Landscape A5 Student Exam Admit Card.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            doc = SimpleDocTemplate(
                output_path,
                pagesize=landscape(A5),
                leftMargin=25,
                rightMargin=25,
                topMargin=25,
                bottomMargin=25
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "SchoolTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=14,
                leading=17,
                alignment=1,
                textColor=colors.HexColor("#1e3a8a")
            )
            subtitle_style = ParagraphStyle(
                "SchoolSubtitle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=8.5,
                leading=11,
                alignment=1,
                textColor=colors.HexColor("#475569")
            )
            badge_style = ParagraphStyle(
                "Badge",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=13,
                alignment=1,
                textColor=colors.HexColor("#0f172a")
            )
            cell_bold = ParagraphStyle("CellBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10)
            cell_norm = ParagraphStyle("CellNorm", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10)
            cell_center = ParagraphStyle("CellCenter", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10, alignment=1)

            story = []

            # 1. School Header
            school_name = school_info.get("name", "EduManage Pro Model High School")
            eiin = school_info.get("eiin", "134211")
            story.append(Paragraph(school_name.upper(), title_style))
            story.append(Paragraph(f"EIIN: {eiin} &bull; Official Examination Hall Admit Card", subtitle_style))
            story.append(Spacer(1, 4))
            term_name = exam_term.name if exam_term else "Terminal Examination 2026"
            story.append(Paragraph(f"ADMIT CARD &bull; {term_name.upper()}", badge_style))
            story.append(Spacer(1, 8))

            # 2. Student Info Table
            cls_name = getattr(student.school_class, "name", "Class 10") if hasattr(student, "school_class") and student.school_class else "Class 10"
            sec_name = getattr(student.section, "name", "Section A") if hasattr(student, "section") and student.section else "Section A"

            info_data = [
                [
                    Paragraph(f"<b>Candidate Name:</b> {student.full_name}", cell_norm),
                    Paragraph(f"<b>Class & Section:</b> {cls_name} ({sec_name})", cell_norm),
                    Paragraph(f"<b>Roll No:</b> {student.roll_number}", cell_norm),
                ],
                [
                    Paragraph(f"<b>Student ID:</b> {student.student_id}", cell_norm),
                    Paragraph(f"<b>Exam Center / Campus:</b> Main Campus", cell_norm),
                    Paragraph(f"<b>Session:</b> 2025-2026", cell_norm),
                ]
            ]
            t_info = Table(info_data, colWidths=[200, 200, 140])
            t_info.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t_info)
            story.append(Spacer(1, 8))

            # 3. Exam Schedule Table
            sched_rows = [[
                Paragraph("<b>Date</b>", cell_bold),
                Paragraph("<b>Time Slot</b>", cell_center),
                Paragraph("<b>Subject Code & Name</b>", cell_bold),
                Paragraph("<b>Allocated Room</b>", cell_center),
                Paragraph("<b>Invigilator Sign</b>", cell_center),
            ]]

            for sc in schedules[:8]:  # Limit to fit comfortably on A5
                sub_name = getattr(sc.subject, "name", "Subject") if hasattr(sc, "subject") and sc.subject else "Subject"
                sub_code = getattr(sc.subject, "code", "101") if hasattr(sc, "subject") and sc.subject else "101"
                sched_rows.append([
                    Paragraph(str(sc.exam_date), cell_norm),
                    Paragraph(f"{sc.start_time} - {sc.end_time}", cell_center),
                    Paragraph(f"[{sub_code}] {sub_name}", cell_norm),
                    Paragraph(sc.room_number or "Room 101", cell_center),
                    Paragraph("_____________", cell_center),
                ])

            t_sched = Table(sched_rows, colWidths=[70, 110, 200, 75, 85])
            t_sched.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(t_sched)
            story.append(Spacer(1, 14))

            # 4. Instructions & Signatures
            sig_data = [
                [
                    Paragraph("<i>Instructions: Candidates must bring this admit card and arrive 15 minutes before exam. Mobile phones and unauthorized materials strictly prohibited.</i>", subtitle_style),
                    Paragraph("<b>Controller of Examinations</b><br/><br/>______________________<br/>Authorized Signature", cell_center)
                ]
            ]
            t_sig = Table(sig_data, colWidths=[380, 160])
            story.append(KeepTogether([t_sig]))

            doc.build(story)
            return True
        except Exception as e:
            print(f"[AdmitCardPDF] Error generating Admit Card PDF: {e}")
            return False
