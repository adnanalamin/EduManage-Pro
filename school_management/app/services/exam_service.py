"""
EduManage Pro - Advanced Examination, Grading, Question Bank & Result Governance Service
Covers:
- Configurable Exam Types & Customizable Grading Systems (GPA 5.0, GPA 4.0, Percentage, Component Pass, Grace Marks, Optional Subject Bonus, Attendance Weighting)
- Written & MCQ Question Bank, Exam Paper Builder, Auto-Graded MCQ Attempts with Mark Sync
- Attendance Mark Auto-Calculation from StudentAttendance
- Result Compilation (GPA, Weighted/Cumulative CGPA, Class & Section Merit Positions)
- Result Verification -> Approval -> Publication Lock (prevents unauthorized edits once published) & Immutable Result History
- Tabulation Sheet Excel Export
"""

import json
import os
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.academic import AcademicYear, SchoolClass, Subject
from app.models.attendance import StudentAttendance
from app.models.base import utc_now
from app.models.exam import (
    ExamPaper,
    ExamPaperQuestion,
    ExamResultBatch,
    ExamResultHistory,
    ExamResultSummary,
    ExamSchedule,
    ExamTerm,
    ExamType,
    GradingScale,
    GradingScaleRule,
    GradingSystem,
    MCQAttempt,
    MCQAttemptAnswer,
    QuestionBankItem,
    ResultWorkflowStatus,
    StudentMark,
)
from app.models.student import Student
from app.models.user import User
from app.repositories.exam_repository import ExamRepository
from app.security.session import session as app_session
from app.services.database_service import DatabaseService


class ExamSecurityGuard:
    """RBAC enforcement for Examination Engine operations & Result Publishing Lock."""

    @staticmethod
    def resolve_actor(actor_user: Optional[User] = None) -> Optional[User]:
        if actor_user is not None:
            return actor_user
        if app_session.is_authenticated and app_session.current_user is not None:
            return app_session.current_user
        return None

    @staticmethod
    def actor_username(actor_user: Optional[User] = None, fallback: str = "admin") -> str:
        user = ExamSecurityGuard.resolve_actor(actor_user)
        return user.username if user else fallback

    @staticmethod
    def require_permission(
        permission_code: str,
        actor_user: Optional[User] = None,
        error_msg: Optional[str] = None,
    ) -> None:
        user = ExamSecurityGuard.resolve_actor(actor_user)
        if user is not None and not user.has_permission(permission_code):
            raise PermissionError(
                error_msg or f"Access denied: missing examination permission '{permission_code}'."
            )


class ExamService:
    # -------------------------------------------------------------
    # 1. Seeders & Customizable Grading Systems
    # -------------------------------------------------------------
    @staticmethod
    def seed_default_grading_scale(db: Session) -> int:
        """
        Seeds baseline GPA 5.0 grading scale if empty + ensures default ExamTypes & GradingSystem.
        """
        existing = db.query(GradingScale).count()
        created = 0
        if existing == 0:
            scales = [
                {"grade_name": "A+", "grade_point": 5.0, "mark_from": 80.0, "mark_to": 100.0, "remarks": "Outstanding"},
                {"grade_name": "A", "grade_point": 4.0, "mark_from": 70.0, "mark_to": 79.99, "remarks": "Excellent"},
                {"grade_name": "A-", "grade_point": 3.5, "mark_from": 60.0, "mark_to": 69.99, "remarks": "Very Good"},
                {"grade_name": "B", "grade_point": 3.0, "mark_from": 50.0, "mark_to": 59.99, "remarks": "Good"},
                {"grade_name": "C", "grade_point": 2.0, "mark_from": 40.0, "mark_to": 49.99, "remarks": "Satisfactory"},
                {"grade_name": "D", "grade_point": 1.0, "mark_from": 33.0, "mark_to": 39.99, "remarks": "Pass"},
                {"grade_name": "F", "grade_point": 0.0, "mark_from": 0.0, "mark_to": 32.99, "remarks": "Fail"},
            ]
            for s in scales:
                db.add(GradingScale(**s))
            db.commit()
            created = len(scales)
        return created

    @staticmethod
    def seed_default_exam_types(db: Session) -> int:
        if db.query(ExamType).count() > 0:
            return 0
        defaults = [
            {
                "name": "Class Test / Weekly Quiz",
                "code": "CT",
                "category": "Formative",
                "default_weight_pct": 10.0,
                "counts_for_cgpa": True,
                "default_full_marks": 25.0,
                "default_pass_marks": 8.0,
                "description": "Short formative class assessment",
            },
            {
                "name": "Half-Yearly / Mid-Term Exam",
                "code": "MID",
                "category": "Summative",
                "default_weight_pct": 40.0,
                "counts_for_cgpa": True,
                "default_full_marks": 100.0,
                "default_pass_marks": 33.0,
                "description": "Mid-session comprehensive examination",
            },
            {
                "name": "Annual / Final Examination",
                "code": "ANN",
                "category": "Summative",
                "default_weight_pct": 50.0,
                "counts_for_cgpa": True,
                "default_full_marks": 100.0,
                "default_pass_marks": 33.0,
                "description": "Year-end promotional final examination",
            },
            {
                "name": "Practical & Viva Assessment",
                "code": "PRAC",
                "category": "Practical",
                "default_weight_pct": 20.0,
                "counts_for_cgpa": False,
                "default_full_marks": 50.0,
                "default_pass_marks": 17.0,
                "description": "Laboratory practical and oral viva voce evaluation",
            },
            {
                "name": "Online / OMR MCQ Test",
                "code": "MCQ",
                "category": "MCQ",
                "default_weight_pct": 10.0,
                "counts_for_cgpa": False,
                "default_full_marks": 30.0,
                "default_pass_marks": 10.0,
                "description": "Objective multiple-choice assessment",
            },
        ]
        for item in defaults:
            db.add(ExamType(**item))
        db.commit()
        return len(defaults)

    @staticmethod
    def seed_default_grading_system(db: Session) -> int:
        if db.query(GradingSystem).count() > 0:
            return 0

        gs5 = GradingSystem(
            name="Standard GPA 5.0 (Board Scale)",
            code="GPA-5",
            max_gpa=5.0,
            pass_percentage=33.0,
            require_component_pass=False,
            grace_marks_limit=0.0,
            optional_subject_enabled=True,
            optional_subject_min_gp=2.0,
            attendance_weight_pct=0.0,
            cgpa_mode="WeightedTerms",
            fail_grade_name="F",
            is_default=True,
            is_active=True,
            description="Official 7-band GPA 5.0 board grading scale",
        )
        db.add(gs5)
        db.flush()
        for r in [
            ("A+", 5.0, 80.0, 100.0, True, "Outstanding"),
            ("A", 4.0, 70.0, 79.99, True, "Excellent"),
            ("A-", 3.5, 60.0, 69.99, True, "Very Good"),
            ("B", 3.0, 50.0, 59.99, True, "Good"),
            ("C", 2.0, 40.0, 49.99, True, "Satisfactory"),
            ("D", 1.0, 33.0, 39.99, True, "Pass"),
            ("F", 0.0, 0.0, 32.99, False, "Fail"),
        ]:
            db.add(
                GradingScaleRule(
                    grading_system_id=gs5.id,
                    grade_name=r[0],
                    grade_point=r[1],
                    mark_from=r[2],
                    mark_to=r[3],
                    is_passing=r[4],
                    remarks=r[5],
                )
            )

        gs4 = GradingSystem(
            name="International GPA 4.0 Scale",
            code="GPA-4",
            max_gpa=4.0,
            pass_percentage=40.0,
            require_component_pass=False,
            grace_marks_limit=0.0,
            optional_subject_enabled=False,
            optional_subject_min_gp=0.0,
            attendance_weight_pct=5.0,
            cgpa_mode="EqualAverage",
            fail_grade_name="F",
            is_default=False,
            is_active=True,
            description="International 4.0 GPA scale (40% pass threshold)",
        )
        db.add(gs4)
        db.flush()
        for r in [
            ("A+", 4.0, 90.0, 100.0, True, "Distinction"),
            ("A", 3.7, 80.0, 89.99, True, "Excellent"),
            ("B+", 3.3, 70.0, 79.99, True, "Very Good"),
            ("B", 3.0, 60.0, 69.99, True, "Good"),
            ("C+", 2.5, 50.0, 59.99, True, "Above Average"),
            ("C", 2.0, 40.0, 49.99, True, "Satisfactory"),
            ("F", 0.0, 0.0, 39.99, False, "Fail"),
        ]:
            db.add(
                GradingScaleRule(
                    grading_system_id=gs4.id,
                    grade_name=r[0],
                    grade_point=r[1],
                    mark_from=r[2],
                    mark_to=r[3],
                    is_passing=r[4],
                    remarks=r[5],
                )
            )
        db.commit()
        return 2

    @staticmethod
    def create_grading_system(
        db: Session,
        data: Dict[str, Any],
        rules: List[Dict[str, Any]],
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[GradingSystem], str]:
        try:
            ExamSecurityGuard.require_permission("exams.grading.CREATE", actor_user)
            if not rules:
                return False, None, "At least one grade scale rule is required."

            code = (data.get("code") or f"GS-{uuid.uuid4().hex[:6].upper()}").strip().upper()
            if db.query(GradingSystem).filter(GradingSystem.code == code).first():
                return False, None, f"Grading system code '{code}' already exists."

            is_def = bool(data.get("is_default", False))
            if is_def:
                db.query(GradingSystem).update({"is_default": False})

            gs = GradingSystem(
                name=data["name"].strip(),
                code=code,
                max_gpa=float(data.get("max_gpa", 5.0)),
                pass_percentage=float(data.get("pass_percentage", 33.0)),
                require_component_pass=bool(data.get("require_component_pass", False)),
                grace_marks_limit=float(data.get("grace_marks_limit", 0.0)),
                optional_subject_enabled=bool(data.get("optional_subject_enabled", True)),
                optional_subject_min_gp=float(data.get("optional_subject_min_gp", 2.0)),
                attendance_weight_pct=float(data.get("attendance_weight_pct", 0.0)),
                cgpa_mode=data.get("cgpa_mode", "WeightedTerms"),
                fail_grade_name=data.get("fail_grade_name", "F"),
                round_decimals=int(data.get("round_decimals", 2)),
                is_default=is_def,
                is_active=True,
                description=data.get("description"),
            )
            db.add(gs)
            db.flush()

            for rule in rules:
                db.add(
                    GradingScaleRule(
                        grading_system_id=gs.id,
                        grade_name=rule["grade_name"].strip(),
                        grade_point=float(rule["grade_point"]),
                        mark_from=float(rule["mark_from"]),
                        mark_to=float(rule["mark_to"]),
                        is_passing=bool(rule.get("is_passing", float(rule["grade_point"]) > 0)),
                        remarks=rule.get("remarks", ""),
                    )
                )

            db.commit()
            db.refresh(gs)
            return True, gs, f"Grading system '{gs.name}' created with {len(rules)} rules."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def get_letter_grade_from_gpa(
        gpa: float,
        db: Optional[Session] = None,
        grading_system_id: Optional[int] = None,
    ) -> str:
        """
        Determines final letter grade from aggregated GPA using custom GradingSystem rules
        if provided, or standard GPA 5.0 scale.
        """
        if db is not None and grading_system_id is not None:
            sys_obj = ExamRepository.get_grading_system_by_id(db, grading_system_id)
            if sys_obj and sys_obj.rules:
                for rule in sorted(sys_obj.rules, key=lambda r: r.grade_point, reverse=True):
                    if gpa >= float(rule.grade_point):
                        return rule.grade_name
                return sys_obj.fail_grade_name or "F"

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

    # -------------------------------------------------------------
    # 2. Student Attendance Integration for Exam Marks
    # -------------------------------------------------------------
    @staticmethod
    def calculate_student_attendance_pct(
        db: Session,
        student_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[float]:
        q = db.query(StudentAttendance).filter(StudentAttendance.student_id == student_id)
        if start_date:
            q = q.filter(StudentAttendance.date >= start_date)
        if end_date:
            q = q.filter(StudentAttendance.date <= end_date)
        rows = q.all()
        if not rows:
            return None
        present_like = sum(1 for r in rows if r.status in ("Present", "Late", "Excused"))
        return round((present_like / len(rows)) * 100.0, 2)

    @staticmethod
    def sync_attendance_marks_for_term(
        db: Session,
        exam_term_id: int,
        class_id: int,
        actor_user: Optional[User] = None,
    ) -> int:
        """
        Populates StudentMark.attendance_marks proportionally from StudentAttendance
        for scheduled subjects having attendance_full > 0.
        """
        ExamSecurityGuard.require_permission("exams.marks.EDIT", actor_user)
        ExamRepository.assert_results_editable(db, exam_term_id, class_id)

        term = ExamRepository.get_exam_term_by_id(db, exam_term_id)
        if not term:
            return 0
        schedules = [
            sc
            for sc in ExamRepository.get_schedules_by_term(db, exam_term_id, class_id=class_id)
            if float(sc.attendance_full or 0.0) > 0
        ]
        if not schedules:
            return 0

        students = (
            db.query(Student)
            .filter(Student.class_id == class_id, Student.status == "Active")
            .all()
        )
        updated = 0
        for stu in students:
            pct = ExamService.calculate_student_attendance_pct(
                db, stu.id, start_date=None, end_date=term.start_date
            )
            if pct is None:
                continue
            for sc in schedules:
                att_mark = round(float(sc.attendance_full) * (pct / 100.0), 2)
                existing = (
                    db.query(StudentMark)
                    .filter_by(exam_term_id=exam_term_id, student_id=stu.id, subject_id=sc.subject_id)
                    .first()
                )
                ExamRepository.upsert_student_mark(
                    db,
                    {
                        "exam_term_id": exam_term_id,
                        "class_id": class_id,
                        "subject_id": sc.subject_id,
                        "student_id": stu.id,
                        "theory_marks": existing.theory_marks if existing else 0.0,
                        "mcq_marks": existing.mcq_marks if existing else 0.0,
                        "practical_marks": existing.practical_marks if existing else 0.0,
                        "viva_marks": existing.viva_marks if existing else 0.0,
                        "ca_marks": existing.ca_marks if existing else 0.0,
                        "attendance_marks": att_mark,
                        "is_absent": existing.is_absent if existing else False,
                    },
                    actor_user=actor_user,
                )
                updated += 1
        return updated

    # -------------------------------------------------------------
    # 3. Result Compilation: GPA, CGPA, Class & Section Position
    # -------------------------------------------------------------
    @staticmethod
    def compute_student_cgpa(
        db: Session,
        student_id: int,
        academic_year_id: int,
        cgpa_mode: str = "WeightedTerms",
        max_gpa: float = 5.0,
    ) -> float:
        """
        Computes cumulative CGPA across all CGPA-eligible exam terms within the academic year.
        """
        summaries = (
            db.query(ExamResultSummary, ExamTerm)
            .join(ExamTerm, ExamResultSummary.exam_term_id == ExamTerm.id)
            .filter(
                ExamResultSummary.student_id == student_id,
                ExamTerm.academic_year_id == academic_year_id,
                ExamTerm.counts_for_cgpa == True,
            )
            .all()
        )
        if not summaries:
            return 0.0

        if cgpa_mode == "EqualAverage":
            vals = [float(s.gpa or 0.0) for s, _ in summaries]
            return round(min(max_gpa, sum(vals) / len(vals)), 2)

        weighted_sum = 0.0
        total_weight = 0.0
        for s, t in summaries:
            w = float(t.weight_pct if t.weight_pct is not None else 100.0)
            if w <= 0:
                w = 100.0
            weighted_sum += float(s.gpa or 0.0) * w
            total_weight += w

        if total_weight <= 0:
            return 0.0
        return round(min(max_gpa, weighted_sum / total_weight), 2)

    @staticmethod
    def compile_class_results(
        db: Session,
        exam_term_id: int,
        class_id: int,
        grading_system_id: Optional[int] = None,
        actor_user: Optional[User] = None,
    ) -> List[Dict[str, Any]]:
        """
        Calculates student GPAs, optional subject bonus, CGPA across academic-year terms,
        attaches attendance percentages, validates fail conditions, and assigns Class & Section ranks.
        Strictly blocks recompiling once results are Published & Locked.
        """
        ExamSecurityGuard.require_permission("exams.marks.VIEW", actor_user)
        ExamRepository.assert_results_editable(db, exam_term_id, class_id)

        term = ExamRepository.get_exam_term_by_id(db, exam_term_id)
        eff_gs_id = grading_system_id or (term.grading_system_id if term else None)
        gs_obj = ExamRepository.get_grading_system_by_id(db, eff_gs_id) if eff_gs_id else None

        max_gpa = float(gs_obj.max_gpa) if gs_obj else 5.0
        opt_enabled = bool(gs_obj.optional_subject_enabled) if gs_obj else True
        opt_min_gp = float(gs_obj.optional_subject_min_gp) if gs_obj else 2.0
        cgpa_mode = gs_obj.cgpa_mode if gs_obj else "WeightedTerms"
        fail_lbl = (gs_obj.fail_grade_name if gs_obj else "F") or "F"

        schedules = {
            sc.subject_id: sc
            for sc in ExamRepository.get_schedules_by_term(db, exam_term_id, class_id=class_id)
        }

        students = (
            db.query(Student)
            .filter(Student.class_id == class_id, Student.status == "Active")
            .order_by(Student.roll_number.asc())
            .all()
        )

        unranked_summaries: List[Dict[str, Any]] = []
        for student in students:
            marks = ExamRepository.get_marks_for_student(db, exam_term_id, student.id)
            if not marks:
                continue

            core_marks = [m for m in marks if not m.is_optional] or marks
            opt_marks = [m for m in marks if m.is_optional] if len(core_marks) < len(marks) else []

            total_obtained = round(sum(float(m.total_marks or 0.0) for m in marks), 2)
            total_full = round(
                sum(
                    float(
                        m.full_marks_snapshot
                        or (schedules[m.subject_id].full_marks if m.subject_id in schedules else 100.0)
                    )
                    for m in marks
                ),
                2,
            )
            percentage = (total_obtained / total_full * 100.0) if total_full > 0 else 0.0

            failed_count = sum(1 for m in core_marks if not m.is_passed or m.grade_name == fail_lbl)
            passed_all = (failed_count == 0) and len(core_marks) > 0

            opt_bonus = 0.0
            if not passed_all:
                final_gpa = 0.0
                final_grade = fail_lbl
            else:
                if opt_enabled and opt_marks:
                    opt_bonus = round(sum(max(0.0, float(m.grade_point or 0.0) - opt_min_gp) for m in opt_marks), 2)
                avg_gp = (sum(float(m.grade_point or 0.0) for m in core_marks) + opt_bonus) / len(core_marks)
                final_gpa = round(min(max_gpa, avg_gp), 2)
                final_grade = ExamService.get_letter_grade_from_gpa(
                    final_gpa, db=db, grading_system_id=eff_gs_id
                )

            att_pct = ExamService.calculate_student_attendance_pct(db, student.id)
            remarks = (
                "Promoted with Distinction"
                if final_gpa >= max_gpa and passed_all
                else ("Passed" if passed_all else f"Failed in {failed_count} Subject(s)")
            )

            unranked_summaries.append(
                {
                    "exam_term_id": exam_term_id,
                    "student_id": student.id,
                    "student_name": student.full_name,
                    "roll_number": student.roll_number,
                    "section_id": student.section_id,
                    "class_id": class_id,
                    "total_obtained": total_obtained,
                    "total_full_marks": total_full,
                    "percentage": round(percentage, 2),
                    "gpa": final_gpa,
                    "optional_bonus_gp": opt_bonus,
                    "overall_grade": final_grade,
                    "attendance_percentage": att_pct,
                    "passed_all": passed_all,
                    "failed_subject_count": failed_count,
                    "result_status": ResultWorkflowStatus.COMPILED,
                    "remarks": remarks,
                }
            )

        # Sort by Pass status, GPA, Total Obtained, Roll No (asc)
        unranked_summaries.sort(
            key=lambda x: (x["passed_all"], x["gpa"], x["total_obtained"], -int(x["roll_number"] or 0)),
            reverse=True,
        )

        # Assign Class Rank & Section Rank
        section_counters: Dict[Optional[int], int] = {}
        ranked_summaries: List[Dict[str, Any]] = []
        for rank, item in enumerate(unranked_summaries, 1):
            if item["passed_all"]:
                item["class_rank"] = rank
                sec_id = item["section_id"]
                section_counters[sec_id] = section_counters.get(sec_id, 0) + 1
                item["section_rank"] = section_counters[sec_id]
            else:
                item["class_rank"] = None
                item["section_rank"] = None
            ranked_summaries.append(item)

        username = ExamSecurityGuard.actor_username(actor_user)
        batch = ExamRepository.get_result_batch(db, exam_term_id, class_id)
        if not batch:
            batch = ExamResultBatch(
                exam_term_id=exam_term_id,
                class_id=class_id,
                grading_system_id=eff_gs_id,
                status=ResultWorkflowStatus.COMPILED,
                is_published=False,
                is_locked=False,
                version_no=1,
                compiled_by=username,
                compiled_at=utc_now(),
            )
            db.add(batch)
            db.flush()
        else:
            batch.grading_system_id = eff_gs_id
            batch.status = ResultWorkflowStatus.COMPILED
            batch.compiled_by = username
            batch.compiled_at = utc_now()

        # Persist current summary first, then compute CGPA across terms including this term
        ExamRepository.save_result_summaries(db, ranked_summaries, version_no=batch.version_no)

        if term and term.academic_year_id:
            for item in ranked_summaries:
                cgpa_val = ExamService.compute_student_cgpa(
                    db, item["student_id"], term.academic_year_id, cgpa_mode=cgpa_mode, max_gpa=max_gpa
                )
                item["cgpa"] = cgpa_val
                row = (
                    db.query(ExamResultSummary)
                    .filter_by(exam_term_id=exam_term_id, student_id=item["student_id"])
                    .first()
                )
                if row:
                    row.cgpa = cgpa_val

        ExamRepository.record_result_history(
            db,
            exam_term_id,
            class_id,
            action="COMPILED",
            version_no=batch.version_no,
            new_status=ResultWorkflowStatus.COMPILED,
            snapshot={
                "students_compiled": len(ranked_summaries),
                "passed": sum(1 for r in ranked_summaries if r["passed_all"]),
                "top_student": ranked_summaries[0]["student_name"] if ranked_summaries else None,
            },
            reason="Compiled GPA, CGPA & Merit Positions",
            performed_by=username,
            commit=False,
        )
        db.commit()
        return ranked_summaries

    # -------------------------------------------------------------
    # 4. Result Verification, Approval, Publishing Lock & Reopen
    # -------------------------------------------------------------
    @staticmethod
    def verify_class_results(
        db: Session,
        exam_term_id: int,
        class_id: int,
        notes: str = "",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[ExamResultBatch], str]:
        ExamSecurityGuard.require_permission("exams.verification.CREATE", actor_user)
        batch = ExamRepository.get_result_batch(db, exam_term_id, class_id)
        if not batch:
            return False, None, "Compile class results first before verification."
        if batch.is_published or batch.status == ResultWorkflowStatus.PUBLISHED:
            return False, batch, "Results are already published."

        username = ExamSecurityGuard.actor_username(actor_user)
        prev = batch.status
        batch.status = ResultWorkflowStatus.VERIFIED
        batch.verified_by = username
        batch.verified_at = utc_now()
        batch.verification_notes = notes or "Marks and tabulation verified."

        summaries = ExamRepository.get_class_result_summaries(db, exam_term_id, class_id)
        for s in summaries:
            s.result_status = ResultWorkflowStatus.VERIFIED
            s.verified_by = username
            s.verified_at = batch.verified_at

        ExamRepository.record_result_history(
            db,
            exam_term_id,
            class_id,
            action="VERIFIED",
            version_no=batch.version_no,
            previous_status=prev,
            new_status=ResultWorkflowStatus.VERIFIED,
            reason=batch.verification_notes,
            performed_by=username,
            commit=False,
        )
        DatabaseService.log_activity(
            db,
            action="EXAM_RESULTS_VERIFIED",
            module="EXAMS",
            description=f"Verified results for term_id={exam_term_id}, class_id={class_id} (v{batch.version_no})",
            username=username,
            commit=False,
        )
        db.commit()
        db.refresh(batch)
        return True, batch, "Class results marked as Verified."

    @staticmethod
    def approve_class_results(
        db: Session,
        exam_term_id: int,
        class_id: int,
        notes: str = "",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[ExamResultBatch], str]:
        ExamSecurityGuard.require_permission(
            "exams.verification.APPROVE",
            actor_user,
            error_msg="Access denied: only authorized Exam Controllers/Admins may approve results.",
        )
        batch = ExamRepository.get_result_batch(db, exam_term_id, class_id)
        if not batch:
            return False, None, "Compile and verify results before approval."
        if batch.status not in (ResultWorkflowStatus.VERIFIED, ResultWorkflowStatus.APPROVED):
            return False, batch, f"Results must be Verified first (current status: '{batch.status}')."

        username = ExamSecurityGuard.actor_username(actor_user)
        prev = batch.status
        batch.status = ResultWorkflowStatus.APPROVED
        batch.approved_by = username
        batch.approved_at = utc_now()
        batch.approval_notes = notes or "Approved for publication."

        summaries = ExamRepository.get_class_result_summaries(db, exam_term_id, class_id)
        for s in summaries:
            s.result_status = ResultWorkflowStatus.APPROVED
            s.approved_by = username
            s.approved_at = batch.approved_at

        ExamRepository.record_result_history(
            db,
            exam_term_id,
            class_id,
            action="APPROVED",
            version_no=batch.version_no,
            previous_status=prev,
            new_status=ResultWorkflowStatus.APPROVED,
            reason=batch.approval_notes,
            performed_by=username,
            commit=False,
        )
        db.commit()
        db.refresh(batch)
        return True, batch, "Class results approved for publishing."

    @staticmethod
    def publish_class_results(
        db: Session,
        exam_term_id: int,
        class_id: int,
        notes: str = "",
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[ExamResultBatch], str]:
        """
        Publishes verified & approved results, locking all StudentMark & ExamResultSummary records
        against unauthorized post-publication modifications.
        """
        ExamSecurityGuard.require_permission(
            "exams.verification.APPROVE",
            actor_user,
            error_msg="Access denied: only authorized administrators may publish official results.",
        )
        batch = ExamRepository.get_result_batch(db, exam_term_id, class_id)
        if not batch:
            return False, None, "Result batch not found."
        if batch.is_published:
            return False, batch, "Results are already published and locked."
        if batch.status != ResultWorkflowStatus.APPROVED:
            return (
                False,
                batch,
                f"Results must be Verified and Approved prior to publishing (current status: '{batch.status}').",
            )

        username = ExamSecurityGuard.actor_username(actor_user)
        now_ts = utc_now()
        prev = batch.status
        batch.status = ResultWorkflowStatus.PUBLISHED
        batch.is_published = True
        batch.is_locked = True
        batch.published_by = username
        batch.published_at = now_ts

        summaries = ExamRepository.get_class_result_summaries(db, exam_term_id, class_id)
        snap_rows = []
        for s in summaries:
            s.result_status = ResultWorkflowStatus.PUBLISHED
            s.is_published = True
            s.published_by = username
            s.published_at = now_ts
            snap_rows.append(
                {
                    "student_id": s.student_id,
                    "total_obtained": s.total_obtained,
                    "gpa": s.gpa,
                    "cgpa": s.cgpa,
                    "grade": s.overall_grade,
                    "rank": s.class_rank,
                }
            )

        db.query(StudentMark).filter(
            StudentMark.exam_term_id == exam_term_id,
            StudentMark.class_id == class_id,
        ).update({"is_locked": True, "verified_by": batch.verified_by or username}, synchronize_session=False)

        ExamRepository.record_result_history(
            db,
            exam_term_id,
            class_id,
            action="PUBLISHED",
            version_no=batch.version_no,
            previous_status=prev,
            new_status=ResultWorkflowStatus.PUBLISHED,
            snapshot={"results": snap_rows},
            reason=notes or "Official result publication & lock",
            performed_by=username,
            commit=False,
        )
        DatabaseService.log_activity(
            db,
            action="EXAM_RESULTS_PUBLISHED",
            module="EXAMS",
            description=f"Published & locked official results for term_id={exam_term_id}, class_id={class_id} (v{batch.version_no})",
            username=username,
            commit=False,
        )
        db.commit()
        db.refresh(batch)
        return True, batch, f"Results published and locked (Version {batch.version_no})."

    @staticmethod
    def reopen_published_results(
        db: Session,
        exam_term_id: int,
        class_id: int,
        reason: str,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[ExamResultBatch], str]:
        """
        Controlled governance procedure allowing Super Admin / authorized Exam Controller
        to reopen published results for an audited correction, incrementing version_no
        and preserving previous snapshots in ExamResultHistory.
        """
        ExamSecurityGuard.require_permission(
            "exams.verification.MANAGE",
            actor_user,
            error_msg="Access denied: only Super Admin / authorized Exam Controller may reopen published results.",
        )
        if not reason or not reason.strip():
            return False, None, "A mandatory audit reason is required to reopen published results."

        batch = ExamRepository.get_result_batch(db, exam_term_id, class_id)
        if not batch or not batch.is_published:
            return False, batch, "No published result batch found to reopen."

        username = ExamSecurityGuard.actor_username(actor_user)
        prev_ver = batch.version_no
        batch.status = ResultWorkflowStatus.REOPENED
        batch.is_published = False
        batch.is_locked = False
        batch.version_no = prev_ver + 1

        db.query(StudentMark).filter(
            StudentMark.exam_term_id == exam_term_id,
            StudentMark.class_id == class_id,
        ).update({"is_locked": False}, synchronize_session=False)

        for s in ExamRepository.get_class_result_summaries(db, exam_term_id, class_id):
            s.result_status = ResultWorkflowStatus.REOPENED
            s.is_published = False

        ExamRepository.record_result_history(
            db,
            exam_term_id,
            class_id,
            action="REOPENED",
            version_no=batch.version_no,
            previous_status=ResultWorkflowStatus.PUBLISHED,
            new_status=ResultWorkflowStatus.REOPENED,
            snapshot={"previous_version": prev_ver, "new_version": batch.version_no},
            reason=reason.strip(),
            performed_by=username,
            commit=False,
        )
        DatabaseService.log_activity(
            db,
            action="EXAM_RESULTS_REOPENED",
            module="EXAMS",
            description=f"Reopened published results term_id={exam_term_id}, class_id={class_id} -> v{batch.version_no}: {reason.strip()}",
            username=username,
            severity="WARNING",
            commit=False,
        )
        db.commit()
        db.refresh(batch)
        return True, batch, f"Published results reopened for correction (v{batch.version_no})."

    # -------------------------------------------------------------
    # 5. Question Bank, Written Papers & MCQ Auto-Grading Engine
    # -------------------------------------------------------------
    @staticmethod
    def add_question(
        db: Session,
        data: Dict[str, Any],
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[QuestionBankItem], str]:
        try:
            ExamSecurityGuard.require_permission("exams.question_bank.CREATE", actor_user)
            username = ExamSecurityGuard.actor_username(actor_user)
            q_type = data.get("question_type", "MCQ")
            if q_type not in ("MCQ", "Written", "ShortAnswer", "Practical", "Viva"):
                return False, None, f"Unsupported question_type '{q_type}'."

            cnt = db.query(func.count(QuestionBankItem.id)).scalar() or 0
            q_code = data.get("question_code") or f"QB-{date.today().year}-{cnt + 1:05d}"
            while db.query(QuestionBankItem).filter(QuestionBankItem.question_code == q_code).first():
                cnt += 1
                q_code = f"QB-{date.today().year}-{cnt + 1:05d}"

            options_val = data.get("options")
            if options_val is None:
                options_json = data.get("options_json")
            elif isinstance(options_val, str):
                options_json = options_val
            else:
                options_json = json.dumps(options_val)

            item = QuestionBankItem(
                question_code=q_code,
                subject_id=data["subject_id"],
                class_id=data.get("class_id"),
                topic=data.get("topic"),
                question_type=q_type,
                difficulty=data.get("difficulty", "Medium"),
                bloom_level=data.get("bloom_level", "Understand"),
                question_text=data["question_text"].strip(),
                options_json=options_json,
                correct_option=(data.get("correct_option") or "").strip().upper() or None,
                model_answer=data.get("model_answer"),
                marks=float(data.get("marks", 1.0)),
                negative_marks=float(data.get("negative_marks", 0.0)),
                created_by=username,
                is_active=True,
            )
            db.add(item)
            db.commit()
            db.refresh(item)
            return True, item, f"Question '{item.question_code}' added to Question Bank."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def create_exam_paper(
        db: Session,
        data: Dict[str, Any],
        question_entries: Optional[List[Dict[str, Any]]] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[ExamPaper], str]:
        try:
            ExamSecurityGuard.require_permission("exams.question_bank.CREATE", actor_user)
            username = ExamSecurityGuard.actor_username(actor_user)
            cnt = db.query(func.count(ExamPaper.id)).scalar() or 0
            p_code = data.get("paper_code") or f"PPR-{date.today().year}-{cnt + 1:04d}"
            while db.query(ExamPaper).filter(ExamPaper.paper_code == p_code).first():
                cnt += 1
                p_code = f"PPR-{date.today().year}-{cnt + 1:04d}"

            q_items = question_entries or []
            computed_total = 0.0
            for qi in q_items:
                q_obj = db.query(QuestionBankItem).filter(QuestionBankItem.id == qi["question_id"]).first()
                if q_obj:
                    computed_total += float(qi.get("marks", q_obj.marks))

            total_marks = float(data.get("total_marks") or computed_total or 100.0)
            pass_marks = float(data.get("pass_marks") or round(total_marks * 0.33, 2))

            paper = ExamPaper(
                paper_code=p_code,
                title=data["title"].strip(),
                exam_term_id=data.get("exam_term_id"),
                class_id=data["class_id"],
                subject_id=data["subject_id"],
                paper_type=data.get("paper_type", "Written"),
                duration_minutes=int(data.get("duration_minutes", 60)),
                total_marks=total_marks,
                pass_marks=pass_marks,
                negative_marking=bool(data.get("negative_marking", False)),
                instructions=data.get("instructions"),
                status=data.get("status", "Approved"),
                created_by=username,
            )
            db.add(paper)
            db.flush()

            for idx, qi in enumerate(q_items, 1):
                q_obj = db.query(QuestionBankItem).filter(QuestionBankItem.id == qi["question_id"]).first()
                if not q_obj:
                    continue
                db.add(
                    ExamPaperQuestion(
                        exam_paper_id=paper.id,
                        question_id=q_obj.id,
                        order_no=int(qi.get("order_no", idx)),
                        section_label=qi.get("section_label", "Section A"),
                        marks=float(qi.get("marks", q_obj.marks)),
                    )
                )

            db.commit()
            db.refresh(paper)
            return True, paper, f"Exam paper '{paper.paper_code}' created ({len(q_items)} questions)."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def submit_mcq_attempt(
        db: Session,
        exam_paper_id: int,
        student_id: int,
        answers_map: Dict[int, Optional[str]],
        auto_sync_to_marks: bool = True,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[MCQAttempt], str]:
        """
        Auto-grades a student's MCQ ExamPaper responses (with optional negative marking)
        and syncs the resulting score into StudentMark.mcq_marks when linked to an ExamTerm.
        """
        try:
            ExamSecurityGuard.require_permission("exams.marks.CREATE", actor_user)
            paper = ExamRepository.get_exam_paper_by_id(db, exam_paper_id)
            if not paper:
                return False, None, "Exam paper not found."
            if not paper.questions:
                return False, None, "Exam paper contains no questions."

            existing = (
                db.query(MCQAttempt)
                .filter(MCQAttempt.exam_paper_id == exam_paper_id, MCQAttempt.student_id == student_id)
                .first()
            )
            if existing:
                return False, existing, "Student has already submitted an attempt for this MCQ paper."

            correct = 0
            wrong = 0
            unanswered = 0
            raw_score = 0.0
            neg_ded = 0.0
            ans_rows: List[MCQAttemptAnswer] = []

            for pq in paper.questions:
                q_item = pq.question
                if q_item.question_type != "MCQ":
                    continue
                selected = answers_map.get(q_item.id)
                sel_clean = selected.strip().upper() if isinstance(selected, str) and selected.strip() else None
                expected = (q_item.correct_option or "").strip().upper()

                if not sel_clean:
                    unanswered += 1
                    is_ok = False
                    awarded = 0.0
                elif sel_clean == expected:
                    correct += 1
                    is_ok = True
                    awarded = float(pq.marks)
                    raw_score += awarded
                else:
                    wrong += 1
                    is_ok = False
                    penalty = float(q_item.negative_marks or 0.0) if paper.negative_marking else 0.0
                    neg_ded += penalty
                    awarded = -penalty

                ans_rows.append(
                    MCQAttemptAnswer(
                        question_id=q_item.id,
                        selected_option=sel_clean,
                        is_correct=is_ok,
                        marks_awarded=round(awarded, 2),
                    )
                )

            net_score = round(max(0.0, raw_score - neg_ded), 2)
            total_mcq_marks = sum(float(pq.marks) for pq in paper.questions if pq.question.question_type == "MCQ") or float(paper.total_marks)
            pct = round((net_score / total_mcq_marks) * 100.0, 2) if total_mcq_marks > 0 else 0.0
            is_passed = net_score >= float(paper.pass_marks or 0.0)

            cnt = db.query(func.count(MCQAttempt.id)).scalar() or 0
            attempt_code = f"MCQ-{date.today().year}-{cnt + 1:05d}"

            synced = False
            attempt = MCQAttempt(
                attempt_code=attempt_code,
                exam_paper_id=paper.id,
                student_id=student_id,
                total_questions=len(ans_rows),
                correct_count=correct,
                wrong_count=wrong,
                unanswered_count=unanswered,
                raw_score=round(raw_score, 2),
                negative_deducted=round(neg_ded, 2),
                net_score=net_score,
                percentage=pct,
                is_passed=is_passed,
                synced_to_marks=False,
            )
            db.add(attempt)
            db.flush()
            for ar in ans_rows:
                ar.attempt_id = attempt.id
                db.add(ar)
            db.commit()

            if auto_sync_to_marks and paper.exam_term_id:
                existing_mark = (
                    db.query(StudentMark)
                    .filter_by(
                        exam_term_id=paper.exam_term_id,
                        student_id=student_id,
                        subject_id=paper.subject_id,
                    )
                    .first()
                )
                ExamRepository.upsert_student_mark(
                    db,
                    {
                        "exam_term_id": paper.exam_term_id,
                        "class_id": paper.class_id,
                        "subject_id": paper.subject_id,
                        "student_id": student_id,
                        "theory_marks": existing_mark.theory_marks if existing_mark else 0.0,
                        "mcq_marks": net_score,
                        "practical_marks": existing_mark.practical_marks if existing_mark else 0.0,
                        "viva_marks": existing_mark.viva_marks if existing_mark else 0.0,
                        "attendance_marks": existing_mark.attendance_marks if existing_mark else 0.0,
                        "ca_marks": existing_mark.ca_marks if existing_mark else 0.0,
                    },
                    actor_user=actor_user,
                )
                attempt.synced_to_marks = True
                synced = True
                db.commit()

            db.refresh(attempt)
            return True, attempt, f"MCQ graded ({correct}/{len(ans_rows)} correct, Score: {net_score}, Synced={synced})."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    # -------------------------------------------------------------
    # 6. Tabulation Sheet Excel Export
    # -------------------------------------------------------------
    @staticmethod
    def export_tabulation_excel(
        db: Session,
        exam_term_id: int,
        class_id: int,
        output_file_path: str,
        school_info: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Generates complete academic Tabulation Sheet in openpyxl Excel format
        including component breakdown, GPA, CGPA, and Class/Section positions.
        """
        try:
            import openpyxl
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
            from openpyxl.utils import get_column_letter

            term = ExamRepository.get_exam_term_by_id(db, exam_term_id)
            cls_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
            subjects = (
                db.query(Subject)
                .filter(Subject.class_id == class_id)
                .order_by(Subject.numeric_order.asc())
                .all()
            )

            summaries = ExamRepository.get_class_result_summaries(db, exam_term_id, class_id)
            if not summaries:
                ExamService.compile_class_results(db, exam_term_id, class_id)
                summaries = ExamRepository.get_class_result_summaries(db, exam_term_id, class_id)

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Tabulation_Sheet"
            ws.views.sheetView[0].showGridLines = True

            school_name = school_info.get("name", "EduManage Pro Model High School") if school_info else "EduManage Pro High School"
            eiin = school_info.get("eiin", "134211") if school_info else "134211"

            total_cols = 4 + len(subjects) * 2 + 7
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

            fill_main = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            fill_sub = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
            font_white = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            thin_border = Border(
                left=Side(style="thin", color="CBD5E1"),
                right=Side(style="thin", color="CBD5E1"),
                top=Side(style="thin", color="CBD5E1"),
                bottom=Side(style="thin", color="CBD5E1"),
            )

            for idx, col_title in enumerate(["Merit", "Roll", "Student ID", "Student Name"], 1):
                col_l = get_column_letter(idx)
                ws.merge_cells(f"{col_l}4:{col_l}5")
                ws[f"{col_l}4"] = col_title
                ws[f"{col_l}4"].font = font_white
                ws[f"{col_l}4"].fill = fill_main
                ws[f"{col_l}4"].alignment = Alignment(horizontal="center", vertical="center")

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

            for h in ["Total Mark", "Percent %", "GPA", "CGPA", "Grade", "Sec. Pos", "Status"]:
                c_letter = get_column_letter(col_pointer)
                ws.merge_cells(f"{c_letter}4:{c_letter}5")
                ws[f"{c_letter}4"] = h
                ws[f"{c_letter}4"].font = font_white
                ws[f"{c_letter}4"].fill = fill_main
                ws[f"{c_letter}4"].alignment = Alignment(horizontal="center", vertical="center")
                col_pointer += 1

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

                ws.cell(row=current_row, column=sub_col, value=res.total_obtained).alignment = Alignment(horizontal="right")
                ws.cell(row=current_row, column=sub_col + 1, value=f"{res.percentage}%").alignment = Alignment(horizontal="center")

                gpa_cell = ws.cell(row=current_row, column=sub_col + 2, value=f"{res.gpa:.2f}")
                gpa_cell.alignment = Alignment(horizontal="center")
                gpa_cell.font = Font(bold=True, color="047857" if res.passed_all else "B91C1C")

                cgpa_cell = ws.cell(row=current_row, column=sub_col + 3, value=f"{float(res.cgpa or res.gpa):.2f}")
                cgpa_cell.alignment = Alignment(horizontal="center")

                grd_cell = ws.cell(row=current_row, column=sub_col + 4, value=res.overall_grade)
                grd_cell.alignment = Alignment(horizontal="center")
                grd_cell.font = Font(bold=True)

                ws.cell(row=current_row, column=sub_col + 5, value=res.section_rank or "-").alignment = Alignment(horizontal="center")

                status_text = res.result_status if res.is_published else ("PASSED" if res.passed_all else "FAILED")
                status_cell = ws.cell(row=current_row, column=sub_col + 6, value=status_text)
                status_cell.alignment = Alignment(horizontal="center")
                status_cell.font = Font(bold=True, color="047857" if res.passed_all else "B91C1C")

                for c in range(1, total_cols + 1):
                    ws.cell(row=current_row, column=c).border = thin_border
                current_row += 1

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
