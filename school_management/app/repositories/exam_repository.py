"""
EduManage Pro - Examination & Grading Repository
Data access methods for Exam terms, routines, marks ledger, and class tabulation sheets.
"""

from typing import List, Optional, Tuple, Dict, Any
from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from app.models.exam import ExamTerm, GradingScale, ExamSchedule, StudentMark, ExamResultSummary
from app.models.student import Student
from app.models.academic import SchoolClass, Subject, AcademicYear


class ExamRepository:
    # -------------------------------------------------------------
    # Exam Terms
    # -------------------------------------------------------------
    @staticmethod
    def get_all_exam_terms(db: Session, academic_year_id: Optional[int] = None) -> List[ExamTerm]:
        query = db.query(ExamTerm).options(joinedload(ExamTerm.academic_year))
        if academic_year_id:
            query = query.filter(ExamTerm.academic_year_id == academic_year_id)
        return query.order_by(ExamTerm.start_date.desc()).all()

    @staticmethod
    def get_exam_term_by_id(db: Session, term_id: int) -> Optional[ExamTerm]:
        return db.query(ExamTerm).options(joinedload(ExamTerm.academic_year)).filter(ExamTerm.id == term_id).first()

    @staticmethod
    def create_exam_term(db: Session, data: Dict[str, Any]) -> ExamTerm:
        term = ExamTerm(
            name=data["name"].strip(),
            exam_code=data["exam_code"].strip().upper(),
            academic_year_id=data["academic_year_id"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            status=data.get("status", "Scheduled"),
            description=data.get("description")
        )
        db.add(term)
        db.commit()
        db.refresh(term)
        return term

    @staticmethod
    def update_exam_term(db: Session, term_id: int, data: Dict[str, Any]) -> Optional[ExamTerm]:
        term = db.query(ExamTerm).filter(ExamTerm.id == term_id).first()
        if not term:
            return None
        for key, val in data.items():
            if hasattr(term, key) and key not in ("id", "exam_code"):
                setattr(term, key, val)
        db.commit()
        db.refresh(term)
        return term

    # -------------------------------------------------------------
    # Grading Scales (GPA 5.0 System)
    # -------------------------------------------------------------
    @staticmethod
    def get_grading_scales(db: Session) -> List[GradingScale]:
        return db.query(GradingScale).order_by(GradingScale.grade_point.desc()).all()

    @staticmethod
    def get_grade_for_score(db: Session, percentage: float) -> Tuple[str, float, str]:
        """
        Determines grade_name, grade_point, and remarks from percentage marks.
        """
        scales = ExamRepository.get_grading_scales(db)
        for s in scales:
            if s.mark_from <= percentage <= s.mark_to:
                return s.grade_name, s.grade_point, s.remarks
        if percentage >= 80.0:
            return "A+", 5.0, "Outstanding"
        elif percentage >= 70.0:
            return "A", 4.0, "Excellent"
        elif percentage >= 60.0:
            return "A-", 3.5, "Very Good"
        elif percentage >= 50.0:
            return "B", 3.0, "Good"
        elif percentage >= 40.0:
            return "C", 2.0, "Satisfactory"
        elif percentage >= 33.0:
            return "D", 1.0, "Pass"
        return "F", 0.0, "Fail"

    # -------------------------------------------------------------
    # Exam Schedules / Routines
    # -------------------------------------------------------------
    @staticmethod
    def get_schedules_by_term(
        db: Session,
        term_id: int,
        class_id: Optional[int] = None
    ) -> List[ExamSchedule]:
        query = db.query(ExamSchedule).options(
            joinedload(ExamSchedule.school_class),
            joinedload(ExamSchedule.subject)
        ).filter(ExamSchedule.exam_term_id == term_id)
        if class_id:
            query = query.filter(ExamSchedule.class_id == class_id)
        return query.order_by(ExamSchedule.exam_date.asc(), ExamSchedule.start_time.asc()).all()

    @staticmethod
    def create_or_update_schedule(db: Session, data: Dict[str, Any]) -> ExamSchedule:
        existing = db.query(ExamSchedule).filter_by(
            exam_term_id=data["exam_term_id"],
            class_id=data["class_id"],
            subject_id=data["subject_id"]
        ).first()

        if existing:
            for k, v in data.items():
                if hasattr(existing, k) and k not in ("id", "exam_term_id", "class_id", "subject_id"):
                    setattr(existing, k, v)
            db.commit()
            db.refresh(existing)
            return existing

        schedule = ExamSchedule(
            exam_term_id=data["exam_term_id"],
            class_id=data["class_id"],
            subject_id=data["subject_id"],
            exam_date=data["exam_date"],
            start_time=data.get("start_time", "10:00 AM"),
            end_time=data.get("end_time", "01:00 PM"),
            room_number=data.get("room_number", "Room 101"),
            full_marks=float(data.get("full_marks", 100.0)),
            pass_marks=float(data.get("pass_marks", 33.0)),
            theory_full=float(data.get("theory_full", 70.0)),
            mcq_full=float(data.get("mcq_full", 30.0)),
            practical_full=float(data.get("practical_full", 0.0))
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    # -------------------------------------------------------------
    # Student Marks Register
    # -------------------------------------------------------------
    @staticmethod
    def get_marks_for_subject(
        db: Session,
        exam_term_id: int,
        class_id: int,
        subject_id: int
    ) -> List[StudentMark]:
        return db.query(StudentMark).options(
            joinedload(StudentMark.student)
        ).filter(
            StudentMark.exam_term_id == exam_term_id,
            StudentMark.class_id == class_id,
            StudentMark.subject_id == subject_id
        ).all()

    @staticmethod
    def get_marks_for_student(
        db: Session,
        exam_term_id: int,
        student_id: int
    ) -> List[StudentMark]:
        return db.query(StudentMark).options(
            joinedload(StudentMark.subject)
        ).filter(
            StudentMark.exam_term_id == exam_term_id,
            StudentMark.student_id == student_id
        ).all()

    @staticmethod
    def upsert_student_mark(db: Session, data: Dict[str, Any]) -> StudentMark:
        existing = db.query(StudentMark).filter_by(
            exam_term_id=data["exam_term_id"],
            student_id=data["student_id"],
            subject_id=data["subject_id"]
        ).first()

        theory = float(data.get("theory_marks", 0.0))
        mcq = float(data.get("mcq_marks", 0.0))
        practical = float(data.get("practical_marks", 0.0))
        ca = float(data.get("ca_marks", 0.0))
        is_absent = bool(data.get("is_absent", False))

        total = 0.0 if is_absent else (theory + mcq + practical + ca)

        # Calculate percentage (assuming 100 full marks standard unless specified)
        full_marks = float(data.get("full_marks", 100.0))
        pct = (total / full_marks * 100.0) if full_marks > 0 else 0.0

        pass_marks = float(data.get("pass_marks", 33.0))
        is_passed = (total >= pass_marks) and not is_absent

        if is_absent:
            grade_name, grade_point, remarks = "F", 0.0, "Absent in Examination"
        else:
            grade_name, grade_point, remarks = ExamRepository.get_grade_for_score(db, pct)
            if not is_passed:
                grade_name, grade_point, remarks = "F", 0.0, "Failed"

        if existing:
            existing.theory_marks = theory
            existing.mcq_marks = mcq
            existing.practical_marks = practical
            existing.ca_marks = ca
            existing.total_marks = total
            existing.is_absent = is_absent
            existing.grade_name = grade_name
            existing.grade_point = grade_point
            existing.is_passed = is_passed
            existing.remarks = data.get("remarks") or remarks
            db.commit()
            db.refresh(existing)
            return existing

        mark = StudentMark(
            exam_term_id=data["exam_term_id"],
            class_id=data["class_id"],
            subject_id=data["subject_id"],
            student_id=data["student_id"],
            theory_marks=theory,
            mcq_marks=mcq,
            practical_marks=practical,
            ca_marks=ca,
            total_marks=total,
            is_absent=is_absent,
            grade_name=grade_name,
            grade_point=grade_point,
            is_passed=is_passed,
            remarks=data.get("remarks") or remarks
        )
        db.add(mark)
        db.commit()
        db.refresh(mark)
        return mark

    # -------------------------------------------------------------
    # Tabulation & Result Compilation
    # -------------------------------------------------------------
    @staticmethod
    def get_class_result_summaries(
        db: Session,
        exam_term_id: int,
        class_id: int
    ) -> List[ExamResultSummary]:
        return db.query(ExamResultSummary).options(
            joinedload(ExamResultSummary.student),
            joinedload(ExamResultSummary.school_class)
        ).filter(
            ExamResultSummary.exam_term_id == exam_term_id,
            ExamResultSummary.class_id == class_id
        ).order_by(ExamResultSummary.class_rank.asc()).all()

    @staticmethod
    def get_student_result_summary(
        db: Session,
        exam_term_id: int,
        student_id: int
    ) -> Optional[ExamResultSummary]:
        return db.query(ExamResultSummary).options(
            joinedload(ExamResultSummary.student),
            joinedload(ExamResultSummary.school_class),
            joinedload(ExamResultSummary.exam_term)
        ).filter(
            ExamResultSummary.exam_term_id == exam_term_id,
            ExamResultSummary.student_id == student_id
        ).first()

    @staticmethod
    def save_result_summaries(db: Session, summaries: List[Dict[str, Any]]):
        for s in summaries:
            existing = db.query(ExamResultSummary).filter_by(
                exam_term_id=s["exam_term_id"],
                student_id=s["student_id"]
            ).first()

            if existing:
                existing.total_obtained = s["total_obtained"]
                existing.total_full_marks = s["total_full_marks"]
                existing.percentage = s["percentage"]
                existing.gpa = s["gpa"]
                existing.overall_grade = s["overall_grade"]
                existing.class_rank = s["class_rank"]
                existing.passed_all = s["passed_all"]
                existing.failed_subject_count = s["failed_subject_count"]
                existing.remarks = s.get("remarks")
            else:
                item = ExamResultSummary(
                    exam_term_id=s["exam_term_id"],
                    student_id=s["student_id"],
                    class_id=s["class_id"],
                    total_obtained=s["total_obtained"],
                    total_full_marks=s["total_full_marks"],
                    percentage=s["percentage"],
                    gpa=s["gpa"],
                    overall_grade=s["overall_grade"],
                    class_rank=s["class_rank"],
                    passed_all=s["passed_all"],
                    failed_subject_count=s["failed_subject_count"],
                    remarks=s.get("remarks")
                )
                db.add(item)
        db.commit()
