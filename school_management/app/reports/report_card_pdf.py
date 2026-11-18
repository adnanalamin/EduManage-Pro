"""
EduManage Pro - Student Report Card & Official Mark Sheet PDF Generator
Produces official, printable A4 Student Progress Reports / Academic Transcripts using ReportLab
with granular Theory, MCQ, Practical, Viva & Attendance components, GPA, CGPA, Merit Positions,
and Verification/Approval/Publication seals.
"""

from datetime import datetime
import os
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class ReportCardPDFGenerator:
    @staticmethod
    def generate_report_card(
        student: Any,
        exam_term: Any,
        summary: Any,
        subject_marks: List[Any],
        school_info: Dict[str, str],
        output_path: str,
        doc_heading: str = "ACADEMIC PROGRESS REPORT & OFFICIAL TRANSCRIPT",
    ) -> bool:
        """
        Builds standard A4 official Student Progress Report / Mark Sheet / Academic Transcript.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                leftMargin=30,
                rightMargin=30,
                topMargin=30,
                bottomMargin=30,
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "SchoolTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=15,
                leading=19,
                alignment=1,
                textColor=colors.HexColor("#1e3a8a"),
            )
            subtitle_style = ParagraphStyle(
                "SchoolSubtitle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=8.5,
                leading=11,
                alignment=1,
                textColor=colors.HexColor("#475569"),
            )
            doc_badge_style = ParagraphStyle(
                "DocBadge",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=14,
                alignment=1,
                textColor=colors.HexColor("#0f172a"),
            )
            cell_bold = ParagraphStyle("CellBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10.5)
            cell_norm = ParagraphStyle("CellNorm", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10.5)
            cell_center = ParagraphStyle(
                "CellCenter", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10.5, alignment=1
            )
            cell_center_bold = ParagraphStyle(
                "CellCenterBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10.5, alignment=1
            )

            story = []

            school_name = school_info.get("name", "EduManage Pro Model High School")
            school_address = school_info.get("address", "Sector 7, Uttara, Dhaka-1230, Bangladesh")
            eiin = school_info.get("eiin", "134211")
            phone = school_info.get("phone", "+880 1712-345678")

            story.append(Paragraph(school_name.upper(), title_style))
            story.append(Paragraph(f"{school_address} &bull; EIIN: {eiin} &bull; Tel: {phone}", subtitle_style))
            story.append(Spacer(1, 6))
            story.append(Paragraph(doc_heading, doc_badge_style))
            term_name = exam_term.name if exam_term else "Annual Examination"
            pub_tag = "PUBLISHED & LOCKED" if (summary and getattr(summary, "is_published", False)) else (
                getattr(summary, "result_status", "Compiled") if summary else "Draft"
            )
            story.append(
                Paragraph(
                    f"{term_name.upper()} &bull; Result Status: {pub_tag} &bull; Generated: {datetime.now().strftime('%d-%b-%Y')}",
                    subtitle_style,
                )
            )
            story.append(Spacer(1, 10))

            cls_name = getattr(student.school_class, "name", "Class") if hasattr(student, "school_class") and student.school_class else "-"
            sec_name = getattr(student.section, "name", "Section") if hasattr(student, "section") and student.section else "-"
            ay_name = getattr(exam_term.academic_year, "name", "2026") if exam_term and getattr(exam_term, "academic_year", None) else "2026"

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
                    Paragraph(f"<b>Father's Name:</b> {student.guardian.father_name if getattr(student, 'guardian', None) else 'Guardian'}", cell_norm),
                    Paragraph(f"<b>Academic Session:</b> {ay_name}", cell_norm),
                ],
            ]
            t_student = Table(student_data, colWidths=[268, 267])
            t_student.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                        ("BOX", (0, 0), (-1, -1), 0.9, colors.HexColor("#cbd5e1")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(t_student)
            story.append(Spacer(1, 9))

            gpa = float(summary.gpa) if summary else 0.0
            cgpa = float(getattr(summary, "cgpa", gpa) or gpa) if summary else 0.0
            grade = summary.overall_grade if summary else "F"
            c_rank = f"#{summary.class_rank}" if summary and summary.class_rank else "—"
            s_rank = f"#{summary.section_rank}" if summary and getattr(summary, "section_rank", None) else "—"
            is_pass = summary.passed_all if summary else False
            status_lbl = "PASSED" if is_pass else "FAILED"
            max_gpa = (
                float(exam_term.grading_system.max_gpa)
                if exam_term and getattr(exam_term, "grading_system", None)
                else 5.0
            )

            kpi_data = [
                [
                    Paragraph("<b>TERM GPA</b>", cell_center_bold),
                    Paragraph("<b>CUMULATIVE CGPA</b>", cell_center_bold),
                    Paragraph("<b>LETTER GRADE</b>", cell_center_bold),
                    Paragraph("<b>CLASS / SEC POS</b>", cell_center_bold),
                    Paragraph("<b>RESULT</b>", cell_center_bold),
                ],
                [
                    Paragraph(f"<font color='{'#047857' if is_pass else '#b91c1c'}' size='12'><b>{gpa:.2f} / {max_gpa:.2f}</b></font>", cell_center_bold),
                    Paragraph(f"<font color='#1e3a8a' size='12'><b>{cgpa:.2f} / {max_gpa:.2f}</b></font>", cell_center_bold),
                    Paragraph(f"<font color='{'#047857' if is_pass else '#b91c1c'}' size='12'><b>{grade}</b></font>", cell_center_bold),
                    Paragraph(f"<font color='#1e3a8a' size='11'><b>{c_rank} / {s_rank}</b></font>", cell_center_bold),
                    Paragraph(f"<font color='{'#047857' if is_pass else '#b91c1c'}' size='11'><b>{status_lbl}</b></font>", cell_center_bold),
                ],
            ]
            t_kpi = Table(kpi_data, colWidths=[107, 115, 95, 118, 100])
            t_kpi.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                        ("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor("#94a3b8")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(t_kpi)
            story.append(Spacer(1, 10))

            # Itemized Subject Marks Table (Code, Subject, Full, Theory, MCQ, Prac, Viva, Att, Total, GP, Grade, Status)
            marks_rows = [
                [
                    Paragraph("<b>Code</b>", cell_bold),
                    Paragraph("<b>Subject</b>", cell_bold),
                    Paragraph("<b>Full</b>", cell_center_bold),
                    Paragraph("<b>Th</b>", cell_center_bold),
                    Paragraph("<b>MCQ</b>", cell_center_bold),
                    Paragraph("<b>Prac</b>", cell_center_bold),
                    Paragraph("<b>Viva</b>", cell_center_bold),
                    Paragraph("<b>Att</b>", cell_center_bold),
                    Paragraph("<b>Total</b>", cell_center_bold),
                    Paragraph("<b>GP</b>", cell_center_bold),
                    Paragraph("<b>Grd</b>", cell_center_bold),
                    Paragraph("<b>Res</b>", cell_center_bold),
                ]
            ]

            total_obtained_all = 0.0
            total_full_all = 0.0
            for sm in subject_marks:
                sub_code = getattr(sm.subject, "code", "SUB") if hasattr(sm, "subject") and sm.subject else "SUB"
                sub_name = getattr(sm.subject, "name", "Subject") if hasattr(sm, "subject") and sm.subject else "Subject"
                if getattr(sm, "is_optional", False):
                    sub_name = f"{sub_name} (Opt)"
                sub_full = float(getattr(sm, "full_marks_snapshot", 100.0) or 100.0)
                viva_m = float(getattr(sm, "viva_marks", 0.0) or 0.0)
                att_m = float(getattr(sm, "attendance_marks", 0.0) or 0.0)
                total_obtained_all += float(sm.total_marks or 0.0)
                total_full_all += sub_full

                p_color = "#0f172a" if sm.is_passed else "#b91c1c"
                marks_rows.append(
                    [
                        Paragraph(str(sub_code), cell_norm),
                        Paragraph(sub_name, cell_norm),
                        Paragraph(f"{sub_full:.0f}", cell_center),
                        Paragraph(f"{float(sm.theory_marks or 0):.1f}", cell_center),
                        Paragraph(f"{float(sm.mcq_marks or 0):.1f}", cell_center),
                        Paragraph(f"{float(sm.practical_marks or 0):.1f}", cell_center),
                        Paragraph(f"{viva_m:.1f}", cell_center),
                        Paragraph(f"{att_m:.1f}", cell_center),
                        Paragraph(f"<font color='{p_color}'><b>{float(sm.total_marks or 0):.1f}</b></font>", cell_center_bold),
                        Paragraph(f"{float(sm.grade_point or 0):.2f}", cell_center),
                        Paragraph(f"<font color='{p_color}'><b>{sm.grade_name}</b></font>", cell_center_bold),
                        Paragraph(f"<font color='{p_color}'>{'P' if sm.is_passed else 'F'}</font>", cell_center),
                    ]
                )

            marks_rows.append(
                [
                    Paragraph("", cell_bold),
                    Paragraph("<b>GRAND TOTAL</b>", cell_bold),
                    Paragraph(f"<b>{total_full_all:.0f}</b>", cell_center_bold),
                    Paragraph("", cell_center),
                    Paragraph("", cell_center),
                    Paragraph("", cell_center),
                    Paragraph("", cell_center),
                    Paragraph("", cell_center),
                    Paragraph(f"<b>{total_obtained_all:.1f}</b>", cell_center_bold),
                    Paragraph(f"<b>{gpa:.2f}</b>", cell_center_bold),
                    Paragraph(f"<b>{grade}</b>", cell_center_bold),
                    Paragraph(f"<b>{status_lbl}</b>", cell_center_bold),
                ]
            )

            t_marks = Table(marks_rows, colWidths=[34, 150, 34, 34, 34, 34, 34, 33, 40, 34, 34, 40], repeatRows=1)
            t_marks.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
                    ]
                )
            )
            story.append(t_marks)
            story.append(Spacer(1, 12))

            # Remarks & Governance Box
            att_info = (
                f" | Attendance: {summary.attendance_percentage:.1f}%"
                if summary and getattr(summary, "attendance_percentage", None) is not None
                else ""
            )
            ver_info = (
                f"Verified: {getattr(summary, 'verified_by', '-') or '-'} | "
                f"Approved: {getattr(summary, 'approved_by', '-') or '-'}"
                if summary
                else ""
            )
            legend_data = [
                [
                    Paragraph("<b>Grading Scale & Attendance:</b>", cell_bold),
                    Paragraph("<b>Remarks & Verification:</b>", cell_bold),
                ],
                [
                    Paragraph(
                        "80-100: A+ (5.0) | 70-79: A (4.0) | 60-69: A- (3.5) | "
                        f"50-59: B (3.0) | 40-49: C (2.0) | 33-39: D (1.0) | <33: F (0.0){att_info}",
                        cell_norm,
                    ),
                    Paragraph(
                        f"<i>{summary.remarks if summary and summary.remarks else 'Consistent academic performance.'}</i><br/>{ver_info}",
                        cell_norm,
                    ),
                ],
            ]
            t_legend = Table(legend_data, colWidths=[295, 240])
            t_legend.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(t_legend)
            story.append(Spacer(1, 24))

            signatures = [
                [
                    Paragraph("<b>Class Teacher</b><br/><br/><br/>__________________<br/>Signature & Date", cell_center),
                    Paragraph("<b>Exam Controller</b><br/><br/><br/>__________________<br/>Signature & Seal", cell_center),
                    Paragraph("<b>Principal</b><br/><br/><br/>__________________<br/>Official Seal", cell_center),
                ]
            ]
            t_sig = Table(signatures, colWidths=[178, 178, 179])
            story.append(KeepTogether([t_sig]))

            doc.build(story)
            return True
        except Exception as e:
            print(f"[ReportCardPDF] Error compiling Report Card PDF: {e}")
            return False
