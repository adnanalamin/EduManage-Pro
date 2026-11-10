"""
EduManage Pro - Examination & Grading Service
Business logic for GPA 5.0 calculation, merit ranking, tabulation sheet compilation, and Excel export.
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import date, datetime
import os
from sqlalchemy.orm import Session
from app.models.exam import ExamTerm, GradingScale, ExamSchedule, StudentMark, ExamResultSummary
from app.models.student import Student
from app.models.academic import SchoolClass, Subject, AcademicYear
from app.repositories.exam_repository import ExamRepository


class ExamService:
    @staticmethod
    def seed_default_grading_scale(db: Session) -> int:
        """
        Seeds standard GPA 5.0 grading scale if table is empty.
        """
        existing = db.query(GradingScale).count()
        if existing > 0:
            return 0

        scales = [
            {"grade_name": "A+", "grade_point": 5.0, "mark_from": 80.0, "mark_to": 100.0, "remarks": "Outstanding"},
            {"grade_name": "A",  "grade_point": 4.0, "mark_from": 70.0, "mark_to": 79.99, "remarks": "Excellent"},
            {"grade_name": "A-", "grade_point": 3.5, "mark_from": 60.0, "mark_to": 69.99, "remarks": "Very Good"},
            {"grade_name": "B",  "grade_point": 3.0, "mark_from": 50.0, "mark_to": 59.99, "remarks": "Good"},
            {"grade_name": "C",  "grade_point": 2.0, "mark_from": 40.0, "mark_to": 49.99, "remarks": "Satisfactory"},
            {"grade_name": "D",  "grade_point": 1.0, "mark_from": 33.0, "mark_to": 39.99, "remarks": "Pass"},
            {"grade_name": "F",  "grade_point": 0.0, "mark_from": 0.0,  "mark_to": 32.99, "remarks": "Fail"},
        ]

        for s in scales:
            db.add(GradingScale(**s))
        db.commit()
        return len(scales)

    @staticmethod
    def get_letter_grade_from_gpa(gpa: float) -> str:
        """
        Determines final letter grade from aggregated Grade Point Average.
        """
        if gpa >= 5.0:
            return "A+"
        elif gpa >= 4.0:
            return "A"
        elif gpa >= 3.5:
            return "A-"
        elif gpa >= 3.0:
            return "B"
        elif gpa >= 2.0:
            return "C"
        elif gpa >= 1.0:
            return "D"
        return "F"

    @staticmethod
    def compile_class_results(
        db: Session,
        exam_term_id: int,
        class_id: int
    ) -> List[Dict[str, Any]]:
        """
        Calculates student GPAs, validates fail conditions, and assigns class merit rankings.
        """
        students = db.query(Student).filter(
            Student.class_id == class_id,
            Student.status == "Active"
        ).order_by(Student.roll_number.asc()).all()

        unranked_summaries = []

        for student in students:
            marks = ExamRepository.get_marks_for_student(db, exam_term_id, student.id)
            if not marks:
                continue

            total_obtained = sum(m.total_marks for m in marks)
            total_full = len(marks) * 100.0  # Standard 100 per subject
            percentage = (total_obtained / total_full * 100.0) if total_full > 0 else 0.0

            failed_count = sum(1 for m in marks if not m.is_passed or m.grade_name == "F")
            passed_all = (failed_count == 0) and len(marks) > 0

            if not passed_all:
                final_gpa = 0.0
                final_grade = "F"
            else:
                avg_gp = sum(m.grade_point for m in marks) / len(marks)
                final_gpa = round(min(5.0, avg_gp), 2)
                final_grade = ExamService.get_letter_grade_from_gpa(final_gpa)

            remarks = "Promoted with Distinction" if final_gpa == 5.0 else ("Passed" if passed_all else f"Failed in {failed_count} Subject(s)")

            unranked_summaries.append({
                "exam_term_id": exam_term_id,
                "student_id": student.id,
                "student_name": student.full_name,
                "roll_number": student.roll_number,
                "class_id": class_id,
                "total_obtained": total_obtained,
                "total_full_marks": total_full,
                "percentage": round(percentage, 2),
                "gpa": final_gpa,
                "overall_grade": final_grade,
                "passed_all": passed_all,
                "failed_subject_count": failed_count,
                "remarks": remarks,
            })

        # Sort: 1st priority: passed_all (True first), 2nd: GPA desc, 3rd: total_obtained desc
        unranked_summaries.sort(
            key=lambda x: (x["passed_all"], x["gpa"], x["total_obtained"]),
            reverse=True
        )

        # Assign class rank
        ranked_summaries = []
        for rank, item in enumerate(unranked_summaries, 1):
            item["class_rank"] = rank if item["passed_all"] else None
            ranked_summaries.append(item)

        # Persist to database
        ExamRepository.save_result_summaries(db, ranked_summaries)
        return ranked_summaries

    @staticmethod
    def export_tabulation_excel(
        db: Session,
        exam_term_id: int,
        class_id: int,
        output_file_path: str,
        school_info: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Generates complete academic Tabulation Sheet in openpyxl Excel format.
        """
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter

            term = ExamRepository.get_exam_term_by_id(db, exam_term_id)
            cls_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
            subjects = db.query(Subject).filter(Subject.class_id == class_id).order_by(Subject.numeric_order.asc()).all()

            summaries = ExamRepository.get_class_result_summaries(db, exam_term_id, class_id)
            if not summaries:
                # Compile first
                ExamService.compile_class_results(db, exam_term_id, class_id)
                summaries = ExamRepository.get_class_result_summaries(db, exam_term_id, class_id)

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Tabulation_Sheet"
            ws.views.sheetView[0].showGridLines = True

            school_name = school_info.get("name", "EduManage Pro Model High School") if school_info else "EduManage Pro High School"
            eiin = school_info.get("eiin", "134211") if school_info else "134211"

            # 1. Title Header
            total_cols = 5 + len(subjects) * 2 + 5
            last_col_letter = get_column_letter(total_cols)

            ws.merge_cells(f"A1:{last_col_letter}1")
            ws["A1"] = school_name.upper()
            ws["A1"].font = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
            ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

            ws.merge_cells(f"A2:{last_col_letter}2")
            term_name = term.name if term else "Term Exam"
            cls_name = cls_obj.name if cls_obj else "Class"
            ws["A2"] = f"OFFICIAL ACADEMIC TABULATION SHEET & MERIT REGISTER | {term_name} | {cls_name} | EIIN: {eiin}"
            ws["A2"].font = Font(name="Calibri", size=11, bold=True, color="475569")
            ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

            # 2. Table Headers
            # Row 4: Subject group headers
            # Row 5: Component headers
            fill_main = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            fill_sub = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
            font_white = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            thin_border = Border(
                left=Side(style="thin", color="CBD5E1"),
                right=Side(style="thin", color="CBD5E1"),
                top=Side(style="thin", color="CBD5E1"),
                bottom=Side(style="thin", color="CBD5E1")
            )

            # Static Columns
            ws.merge_cells("A4:A5")
            ws["A4"] = "Merit"
            ws["A4"].font = font_white
            ws["A4"].fill = fill_main
            ws["A4"].alignment = Alignment(horizontal="center", vertical="center")

            ws.merge_cells("B4:B5")
            ws["B4"] = "Roll"
            ws["B4"].font = font_white
            ws["B4"].fill = fill_main
            ws["B4"].alignment = Alignment(horizontal="center", vertical="center")

            ws.merge_cells("C4:C5")
            ws["C4"] = "Student ID"
            ws["C4"].font = font_white
            ws["C4"].fill = fill_main
            ws["C4"].alignment = Alignment(horizontal="center", vertical="center")

            ws.merge_cells("D4:D5")
            ws["D4"] = "Student Name"
            ws["D4"].font = font_white
            ws["D4"].fill = fill_main
            ws["D4"].alignment = Alignment(horizontal="center", vertical="center")

            col_pointer = 5
            for sub in subjects:
                c1 = get_column_letter(col_pointer)
                c2 = get_column_letter(col_pointer + 1)
                ws.merge_cells(f"{c1}4:{c2}4")
                ws[f"{c1}4"] = sub.name[:18]
                ws[f"{c1}4"].font = font_white
                ws[f"{c1}4"].fill = fill_sub
                ws[f"{c1}4"].alignment = Alignment(horizontal="center", vertical="center")

                ws.cell(row=5, column=col_pointer, value="Mark").font = font_white
                ws.cell(row=5, column=col_pointer).fill = fill_main
                ws.cell(row=5, column=col_pointer).alignment = Alignment(horizontal="center")

                ws.cell(row=5, column=col_pointer + 1, value="Grade").font = font_white
                ws.cell(row=5, column=col_pointer + 1).fill = fill_main
                ws.cell(row=5, column=col_pointer + 1).alignment = Alignment(horizontal="center")

                col_pointer += 2

            # End Aggregate Columns
            end_headers = ["Total Mark", "Percent %", "GPA", "Grade", "Status"]
            for h in end_headers:
                c_letter = get_column_letter(col_pointer)
                ws.merge_cells(f"{c_letter}4:{c_letter}5")
                ws[f"{c_letter}4"] = h
                ws[f"{c_letter}4"].font = font_white
                ws[f"{c_letter}4"].fill = fill_main
                ws[f"{c_letter}4"].alignment = Alignment(horizontal="center", vertical="center")
                col_pointer += 1

            # 3. Data Rows
            current_row = 6
            for res in summaries:
                stu = res.student
                ws.cell(row=current_row, column=1, value=res.class_rank or "-").alignment = Alignment(horizontal="center")
                ws.cell(row=current_row, column=2, value=stu.roll_number if stu else "-").alignment = Alignment(horizontal="center")
                ws.cell(row=current_row, column=3, value=stu.student_id if stu else "-").alignment = Alignment(horizontal="center")
                ws.cell(row=current_row, column=4, value=stu.full_name if stu else "Unknown")

                student_marks = ExamRepository.get_marks_for_student(db, exam_term_id, res.student_id)
                marks_by_sub = {m.subject_id: m for m in student_marks}

                sub_col = 5
                for sub in subjects:
                    m = marks_by_sub.get(sub.id)
                    mark_cell = ws.cell(row=current_row, column=sub_col)
                    grade_cell = ws.cell(row=current_row, column=sub_col + 1)

                    if m:
                        mark_cell.value = m.total_marks
                        grade_cell.value = f"{m.grade_name} ({m.grade_point})"
                        if not m.is_passed:
                            mark_cell.font = Font(color="B91C1C", bold=True)
                            grade_cell.font = Font(color="B91C1C", bold=True)
                    else:
                        mark_cell.value = "-"
                        grade_cell.value = "-"

                    mark_cell.alignment = Alignment(horizontal="center")
                    grade_cell.alignment = Alignment(horizontal="center")
                    sub_col += 2

                # Summary columns
                ws.cell(row=current_row, column=sub_col, value=res.total_obtained).alignment = Alignment(horizontal="right")
                ws.cell(row=current_row, column=sub_col + 1, value=f"{res.percentage}%").alignment = Alignment(horizontal="center")

                gpa_cell = ws.cell(row=current_row, column=sub_col + 2, value=f"{res.gpa:.2f}")
                gpa_cell.alignment = Alignment(horizontal="center")
                gpa_cell.font = Font(bold=True, color="047857" if res.passed_all else "B91C1C")

                grd_cell = ws.cell(row=current_row, column=sub_col + 3, value=res.overall_grade)
                grd_cell.alignment = Alignment(horizontal="center")
                grd_cell.font = Font(bold=True)

                status_cell = ws.cell(row=current_row, column=sub_col + 4, value="PASSED" if res.passed_all else "FAILED")
                status_cell.alignment = Alignment(horizontal="center")
                status_cell.font = Font(bold=True, color="047857" if res.passed_all else "B91C1C")

                for c in range(1, total_cols + 1):
                    ws.cell(row=current_row, column=c).border = thin_border

                current_row += 1

            # Auto-fit column widths
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

            os.makedirs(os.path.dirname(os.path.abspath(output_file_path)), exist_ok=True)
            wb.save(output_file_path)
            return True
        except Exception as e:
            print(f"[ExamService] Error exporting Tabulation Sheet Excel: {e}")
            return False
