"""
EduManage Pro - Advanced Examination PDF Reports Generator (ReportLab)
Produces:
1. Official Student Mark Sheet PDF
2. Class Merit List PDF
3. Full Academic Tabulation Sheet PDF
4. Printable Written / MCQ Question Paper & Answer Key PDF
"""

from datetime import datetime
import json
import os
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.academic import SchoolClass, Subject
from app.models.school import SchoolSetting
from app.reports.report_card_pdf import ReportCardPDFGenerator
from app.repositories.exam_repository import ExamRepository
from app.services.exam_service import ExamService


def _school_dict(db: Session) -> Dict[str, str]:
    school = db.query(SchoolSetting).first()
    return {
        "name": getattr(school, "school_name", None) or "EduManage Pro Model High School",
        "address": getattr(school, "address", None) or "Uttara, Dhaka, Bangladesh",
        "eiin": getattr(school, "eiin_number", None) or "134211",
        "phone": getattr(school, "phone", None) or "+880 1712-345678",
    }


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ExTitle", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=15, leading=19, alignment=1, textColor=colors.HexColor("#1E3A8A")
        ),
        "sub": ParagraphStyle(
            "ExSub", parent=base["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, alignment=1, textColor=colors.HexColor("#475569")
        ),
        "badge": ParagraphStyle(
            "ExBadge", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=11, leading=14, alignment=1, textColor=colors.HexColor("#0F172A")
        ),
        "cell_b": ParagraphStyle("ExCellB", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10.5),
        "cell_n": ParagraphStyle("ExCellN", parent=base["Normal"], fontName="Helvetica", fontSize=8, leading=10.5),
        "cell_c": ParagraphStyle("ExCellC", parent=base["Normal"], fontName="Helvetica", fontSize=8, leading=10.5, alignment=1),
        "cell_cb": ParagraphStyle("ExCellCB", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10.5, alignment=1),
    }


class ExamReportsPDFGenerator:
    @staticmethod
    def generate_mark_sheet_pdf(
        db: Session,
        exam_term_id: int,
        student_id: int,
        output_path: str,
    ) -> str:
        from app.models.student import Student

        student = db.query(Student).filter(Student.id == student_id).first()
        term = ExamRepository.get_exam_term_by_id(db, exam_term_id)
        summary = ExamRepository.get_student_result_summary(db, exam_term_id, student_id)
        marks = ExamRepository.get_marks_for_student(db, exam_term_id, student_id)
        if not student or not term:
            raise ValueError("Student or Exam Term not found.")

        ok = ReportCardPDFGenerator.generate_report_card(
            student=student,
            exam_term=term,
            summary=summary,
            subject_marks=marks,
            school_info=_school_dict(db),
            output_path=output_path,
            doc_heading="OFFICIAL ACADEMIC MARK SHEET & STATEMENT OF MARKS",
        )
        if not ok:
            raise RuntimeError("Failed building Mark Sheet PDF.")
        return output_path

    @staticmethod
    def generate_merit_list_pdf(
        db: Session,
        exam_term_id: int,
        class_id: int,
        output_path: str,
    ) -> str:
        term = ExamRepository.get_exam_term_by_id(db, exam_term_id)
        cls_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        summaries = ExamRepository.get_class_result_summaries(db, exam_term_id, class_id)
        if not summaries:
            ExamService.compile_class_results(db, exam_term_id, class_id)
            summaries = ExamRepository.get_class_result_summaries(db, exam_term_id, class_id)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        meta = _school_dict(db)
        st = _styles()

        doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
        story: List[Any] = [
            Paragraph(meta["name"].upper(), st["title"]),
            Paragraph(f"{meta['address']} &bull; EIIN: {meta['eiin']}", st["sub"]),
            Spacer(1, 6),
            Paragraph(f"OFFICIAL MERIT LIST — {term.name.upper() if term else 'EXAM'} ({cls_obj.name if cls_obj else ''})", st["badge"]),
            Paragraph(f"Generated: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}", st["sub"]),
            Spacer(1, 10),
        ]

        headers = ["Class Pos", "Sec Pos", "Roll", "Student ID", "Candidate Name", "Obtained", "%", "GPA", "CGPA", "Grade", "Status"]
        rows = [[Paragraph(f"<b>{h}</b>", st["cell_cb"]) for h in headers]]
        for r in summaries:
            stu = r.student
            rows.append(
                [
                    Paragraph(str(r.class_rank or "-"), st["cell_cb"]),
                    Paragraph(str(getattr(r, "section_rank", None) or "-"), st["cell_c"]),
                    Paragraph(str(stu.roll_number if stu else "-"), st["cell_c"]),
                    Paragraph(stu.student_id if stu else "-", st["cell_n"]),
                    Paragraph(stu.full_name if stu else "-", st["cell_n"]),
                    Paragraph(f"{r.total_obtained:.1f}/{r.total_full_marks:.0f}", st["cell_c"]),
                    Paragraph(f"{r.percentage:.1f}%", st["cell_c"]),
                    Paragraph(f"<b>{r.gpa:.2f}</b>", st["cell_cb"]),
                    Paragraph(f"{float(getattr(r, 'cgpa', r.gpa) or r.gpa):.2f}", st["cell_c"]),
                    Paragraph(f"<b>{r.overall_grade}</b>", st["cell_cb"]),
                    Paragraph("PASS" if r.passed_all else "FAIL", st["cell_c"]),
                ]
            )

        tbl = Table(rows, colWidths=[42, 40, 32, 74, 128, 60, 36, 36, 36, 36, 38], repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(tbl)
        doc.build(story)
        return output_path

    @staticmethod
    def generate_tabulation_pdf(
        db: Session,
        exam_term_id: int,
        class_id: int,
        output_path: str,
    ) -> str:
        term = ExamRepository.get_exam_term_by_id(db, exam_term_id)
        cls_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        subjects = db.query(Subject).filter(Subject.class_id == class_id).order_by(Subject.numeric_order.asc()).all()
        summaries = ExamRepository.get_class_result_summaries(db, exam_term_id, class_id)
        if not summaries:
            ExamService.compile_class_results(db, exam_term_id, class_id)
            summaries = ExamRepository.get_class_result_summaries(db, exam_term_id, class_id)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        meta = _school_dict(db)
        st = _styles()

        doc = SimpleDocTemplate(
            output_path, pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=22, bottomMargin=22
        )
        story: List[Any] = [
            Paragraph(meta["name"].upper(), st["title"]),
            Paragraph(f"ACADEMIC TABULATION SHEET — {term.name.upper() if term else ''} | {cls_obj.name if cls_obj else ''}", st["badge"]),
            Spacer(1, 8),
        ]

        headers = ["Rank", "Roll", "Student Name"] + [s.name[:12] for s in subjects] + ["Total", "GPA", "CGPA", "Grd", "Status"]
        rows = [[Paragraph(f"<b>{h}</b>", st["cell_cb"]) for h in headers]]
        for r in summaries:
            stu = r.student
            marks_map = {m.subject_id: m for m in ExamRepository.get_marks_for_student(db, exam_term_id, r.student_id)}
            sub_cells = []
            for s in subjects:
                m = marks_map.get(s.id)
                sub_cells.append(Paragraph(f"{m.total_marks:.0f} ({m.grade_name})" if m else "-", st["cell_c"]))
            row = (
                [
                    Paragraph(str(r.class_rank or "-"), st["cell_cb"]),
                    Paragraph(str(stu.roll_number if stu else "-"), st["cell_c"]),
                    Paragraph(stu.full_name if stu else "-", st["cell_n"]),
                ]
                + sub_cells
                + [
                    Paragraph(f"{r.total_obtained:.0f}", st["cell_cb"]),
                    Paragraph(f"{r.gpa:.2f}", st["cell_cb"]),
                    Paragraph(f"{float(getattr(r, 'cgpa', r.gpa) or r.gpa):.2f}", st["cell_c"]),
                    Paragraph(r.overall_grade, st["cell_cb"]),
                    Paragraph("PASS" if r.passed_all else "FAIL", st["cell_c"]),
                ]
            )
            rows.append(row)

        fixed_w = 34 + 30 + 115 + 42 + 38 + 38 + 34 + 40
        sub_count = max(1, len(subjects))
        sub_w = max(48.0, (780.0 - fixed_w) / sub_count)
        col_widths = [34, 30, 115] + [sub_w] * len(subjects) + [42, 38, 38, 34, 40]

        tbl = Table(rows, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(tbl)
        doc.build(story)
        return output_path

    @staticmethod
    def generate_question_paper_pdf(
        db: Session,
        paper_id: int,
        output_path: str,
        include_answer_key: bool = False,
    ) -> str:
        paper = ExamRepository.get_exam_paper_by_id(db, paper_id)
        if not paper:
            raise ValueError("Exam paper not found.")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        meta = _school_dict(db)
        st = _styles()

        doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=32, bottomMargin=32)
        story: List[Any] = [
            Paragraph(meta["name"].upper(), st["title"]),
            Paragraph(
                f"{paper.title.upper()} ({paper.paper_code}) — {paper.paper_type.upper()}",
                st["badge"],
            ),
            Paragraph(
                f"Class: {paper.school_class.name if paper.school_class else '-'} | "
                f"Subject: {paper.subject.name if paper.subject else '-'} | "
                f"Duration: {paper.duration_minutes} mins | Total Marks: {paper.total_marks:g} | Pass Marks: {paper.pass_marks:g}",
                st["sub"],
            ),
            Spacer(1, 10),
        ]
        if paper.instructions:
            story.append(Paragraph(f"<b>Instructions:</b> {paper.instructions}", st["cell_n"]))
            story.append(Spacer(1, 8))

        for idx, pq in enumerate(paper.questions, 1):
            q = pq.question
            story.append(
                Paragraph(
                    f"<b>Q{idx}. [{pq.section_label or q.question_type} — {pq.marks:g} Marks]</b> {q.question_text}",
                    st["cell_n"],
                )
            )
            if q.options_json:
                try:
                    opts = json.loads(q.options_json)
                    if isinstance(opts, dict):
                        opt_str = " &nbsp;&nbsp; ".join(f"({k}) {v}" for k, v in opts.items())
                    elif isinstance(opts, list):
                        letters = ["A", "B", "C", "D", "E"]
                        opt_str = " &nbsp;&nbsp; ".join(
                            f"({letters[i] if i < len(letters) else i + 1}) {val}" for i, val in enumerate(opts)
                        )
                    else:
                        opt_str = str(opts)
                    story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{opt_str}", st["cell_n"]))
                except Exception:
                    pass
            if include_answer_key:
                ans = q.correct_option or q.model_answer or "-"
                story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;<i>Answer Key: {ans}</i>", st["cell_b"]))
            story.append(Spacer(1, 6))

        doc.build(story)
        return output_path
