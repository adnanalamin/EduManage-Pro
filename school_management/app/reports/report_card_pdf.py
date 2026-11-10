"""
EduManage Pro - Student Report Card & Academic Transcript PDF Generator
Produces official, printable A4 Student Academic Progress Reports using ReportLab.
"""

import os
from typing import Dict, Any, List
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


class ReportCardPDFGenerator:
    @staticmethod
    def generate_report_card(
        student: Any,
        exam_term: Any,
        summary: Any,
        subject_marks: List[Any],
        school_info: Dict[str, str],
        output_path: str
    ) -> bool:
        """
        Builds standard A4 official Student Progress Report / Academic Transcript.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                leftMargin=36,
                rightMargin=36,
                topMargin=36,
                bottomMargin=36
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "SchoolTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=16,
                leading=20,
                alignment=1,
                textColor=colors.HexColor("#1e3a8a")
            )
            subtitle_style = ParagraphStyle(
                "SchoolSubtitle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9,
                leading=12,
                alignment=1,
                textColor=colors.HexColor("#475569")
            )
            doc_badge_style = ParagraphStyle(
                "DocBadge",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=14,
                alignment=1,
                textColor=colors.HexColor("#0f172a")
            )
            cell_bold = ParagraphStyle("CellBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11)
            cell_norm = ParagraphStyle("CellNorm", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11)
            cell_center = ParagraphStyle("CellCenter", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, alignment=1)
            cell_center_bold = ParagraphStyle("CellCenterBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, alignment=1)

            story = []

            # 1. School Header
            school_name = school_info.get("name", "EduManage Pro Model High School")
            school_address = school_info.get("address", "Sector 7, Uttara, Dhaka-1230, Bangladesh")
            eiin = school_info.get("eiin", "134211")
            phone = school_info.get("phone", "+880 1712-345678")

            story.append(Paragraph(school_name.upper(), title_style))
            story.append(Paragraph(f"{school_address} &bull; EIIN: {eiin} &bull; Tel: {phone}", subtitle_style))
            story.append(Spacer(1, 8))
            story.append(Paragraph("ACADEMIC PROGRESS REPORT & OFFICIAL TRANSCRIPT", doc_badge_style))
            term_name = exam_term.name if exam_term else "Annual Examination"
            story.append(Paragraph(f"{term_name.upper()} | Generated: {datetime.now().strftime('%d-%b-%Y')}", subtitle_style))
            story.append(Spacer(1, 12))

            # 2. Student Dossier Box
            cls_name = getattr(student.school_class, "name", "Class 10") if hasattr(student, "school_class") and student.school_class else "Class 10"
            sec_name = getattr(student.section, "name", "Section A") if hasattr(student, "section") and student.section else "Section A"

            student_data = [
                [
                    Paragraph(f"<b>Student Name:</b> {student.full_name}", cell_norm),
                    Paragraph(f"<b>Class & Section:</b> {cls_name} ({sec_name})", cell_norm),
                ],
                [
                    Paragraph(f"<b>Student ID:</b> {student.student_id}", cell_norm),
                    Paragraph(f"<b>Roll Number:</b> {student.roll_number}", cell_norm),
                ],
                [
                    Paragraph(f"<b>Father's Name:</b> {student.guardian.father_name if student.guardian else 'Guardian'}", cell_norm),
                    Paragraph(f"<b>Academic Session:</b> 2025-2026", cell_norm),
                ]
            ]
            t_student = Table(student_data, colWidths=[260, 260])
            t_student.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t_student)
            story.append(Spacer(1, 10))

            # 3. Overall Result KPI Scoreboard
            gpa = summary.gpa if summary else 0.0
            grade = summary.overall_grade if summary else "F"
            rank = f"{summary.class_rank}" if summary and summary.class_rank else "—"
            status = "PASSED / PROMOTED" if (summary and summary.passed_all) else "FAILED / NOT PROMOTED"
            is_pass = summary.passed_all if summary else False

            kpi_data = [
                [
                    Paragraph("<b>GRADE POINT AVERAGE</b>", cell_center_bold),
                    Paragraph("<b>LETTER GRADE</b>", cell_center_bold),
                    Paragraph("<b>MERIT POSITION</b>", cell_center_bold),
                    Paragraph("<b>FINAL RESULT STATUS</b>", cell_center_bold),
                ],
                [
                    Paragraph(f"<font color='{'#047857' if is_pass else '#b91c1c'}' size='13'><b>{gpa:.2f} / 5.00</b></font>", cell_center_bold),
                    Paragraph(f"<font color='{'#047857' if is_pass else '#b91c1c'}' size='13'><b>{grade}</b></font>", cell_center_bold),
                    Paragraph(f"<font color='#1e3a8a' size='13'><b>{rank}</b></font>", cell_center_bold),
                    Paragraph(f"<font color='{'#047857' if is_pass else '#b91c1c'}' size='11'><b>{status}</b></font>", cell_center_bold),
                ]
            ]
            t_kpi = Table(kpi_data, colWidths=[130, 130, 130, 130])
            t_kpi.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor("#94a3b8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t_kpi)
            story.append(Spacer(1, 12))

            # 4. Itemized Subject Marks Table
            marks_rows = [[
                Paragraph("<b>Code</b>", cell_bold),
                Paragraph("<b>Subject Particulars</b>", cell_bold),
                Paragraph("<b>Full</b>", cell_center_bold),
                Paragraph("<b>Theory</b>", cell_center_bold),
                Paragraph("<b>MCQ</b>", cell_center_bold),
                Paragraph("<b>Prac</b>", cell_center_bold),
                Paragraph("<b>Total</b>", cell_center_bold),
                Paragraph("<b>GP</b>", cell_center_bold),
                Paragraph("<b>Grade</b>", cell_center_bold),
                Paragraph("<b>Status</b>", cell_center_bold),
            ]]

            total_obtained_all = 0.0
            total_full_all = 0.0

            for sm in subject_marks:
                sub_code = getattr(sm.subject, "code", "SUB") if hasattr(sm, "subject") and sm.subject else "101"
                sub_name = getattr(sm.subject, "name", "General Subject") if hasattr(sm, "subject") and sm.subject else "General Subject"
                total_obtained_all += sm.total_marks
                total_full_all += 100.0

                p_color = "#0f172a" if sm.is_passed else "#b91c1c"
                marks_rows.append([
                    Paragraph(sub_code, cell_norm),
                    Paragraph(sub_name, cell_norm),
                    Paragraph("100", cell_center),
                    Paragraph(f"{sm.theory_marks:.1f}", cell_center),
                    Paragraph(f"{sm.mcq_marks:.1f}", cell_center),
                    Paragraph(f"{sm.practical_marks:.1f}", cell_center),
                    Paragraph(f"<font color='{p_color}'><b>{sm.total_marks:.1f}</b></font>", cell_center_bold),
                    Paragraph(f"{sm.grade_point:.2f}", cell_center),
                    Paragraph(f"<font color='{p_color}'><b>{sm.grade_name}</b></font>", cell_center_bold),
                    Paragraph(f"<font color='{p_color}'>{ 'Pass' if sm.is_passed else 'Fail' }</font>", cell_center),
                ])

            # Total row
            marks_rows.append([
                Paragraph("", cell_bold),
                Paragraph("<b>GRAND TOTAL AGGREGATE</b>", cell_bold),
                Paragraph(f"<b>{int(total_full_all)}</b>", cell_center_bold),
                Paragraph("", cell_center),
                Paragraph("", cell_center),
                Paragraph("", cell_center),
                Paragraph(f"<b>{total_obtained_all:.1f}</b>", cell_center_bold),
                Paragraph(f"<b>{gpa:.2f}</b>", cell_center_bold),
                Paragraph(f"<b>{grade}</b>", cell_center_bold),
                Paragraph(f"<b>{ 'Pass' if is_pass else 'Fail' }</b>", cell_center_bold),
            ])

            t_marks = Table(marks_rows, colWidths=[45, 175, 40, 42, 42, 42, 46, 42, 42, 44])
            t_marks.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
            ]))
            story.append(t_marks)
            story.append(Spacer(1, 14))

            # 5. Grading Legend & Teacher Remarks
            legend_data = [
                [
                    Paragraph("<b>Official Grading Scale (GPA 5.0 Scale):</b>", cell_bold),
                    Paragraph("<b>Class Teacher's Evaluative Remarks:</b>", cell_bold)
                ],
                [
                    Paragraph(
                        "<b>80-100:</b> A+ (5.00) &nbsp;|&nbsp; <b>70-79:</b> A (4.00) &nbsp;|&nbsp; <b>60-69:</b> A- (3.50)<br/>"
                        "<b>50-59:</b> B (3.00) &nbsp;|&nbsp; <b>40-49:</b> C (2.00) &nbsp;|&nbsp; <b>33-39:</b> D (1.00) &nbsp;|&nbsp; <b>0-32:</b> F (0.00)",
                        cell_norm
                    ),
                    Paragraph(
                        f"<i>{summary.remarks if summary and summary.remarks else 'Consistent academic performance. Recommended for advanced curriculum.'}</i>",
                        cell_norm
                    )
                ]
            ]
            t_legend = Table(legend_data, colWidths=[310, 210])
            t_legend.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t_legend)
            story.append(Spacer(1, 26))

            # 6. Tri-Signatures
            signatures = [
                [
                    Paragraph("<b>Class Teacher</b><br/><br/><br/>______________________<br/>Signature & Date", cell_center),
                    Paragraph("<b>Exam Controller</b><br/><br/><br/>______________________<br/>Signature & Seal", cell_center),
                    Paragraph("<b>Principal / Head of School</b><br/><br/><br/>______________________<br/>Signature & Official Seal", cell_center)
                ]
            ]
            t_sig = Table(signatures, colWidths=[173, 173, 174])
            story.append(KeepTogether([t_sig]))

            doc.build(story)
            return True
        except Exception as e:
            print(f"[ReportCardPDF] Error compiling Report Card PDF: {e}")
            return False
