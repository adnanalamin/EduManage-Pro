"""
EduManage Pro - Advanced Examination & Grading Repository
Data access layer for ExamTypes, ExamTerms, Customizable GradingSystems/Rules,
ExamSchedules, StudentMarks (with publish-lock enforcement), QuestionBank, ExamPapers,
MCQAttempts, ResultBatches, and immutable ResultHistory.
"""

from datetime import date
import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.models.academic import AcademicYear, SchoolClass, Subject
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
    QuestionBankItem,
    ResultWorkflowStatus,
    StudentMark,
)
from app.models.user import User
from app.security.session import session as app_session


def _resolve_actor_username(actor_user: Optional[User] = None, fallback: str = "system") -> str:
    if actor_user is not None:
        return actor_user.username
    if app_session.is_authenticated and app_session.current_user is not None:
        return app_session.current_user.username
    return fallback


class ExamRepository:
    # -------------------------------------------------------------
    # Exam Types
    # -------------------------------------------------------------
    @staticmethod
    def get_all_exam_types(db: Session, active_only: bool = True) -> List[ExamType]:
        q = db.query(ExamType).filter(ExamType.is_deleted == False)
        if active_only:
            q = q.filter(ExamType.is_active == True)
        return q.order_by(ExamType.id.asc()).all()

    @staticmethod
    def create_exam_type(db: Session, data: Dict[str, Any]) -> ExamType:
        et = ExamType(
            name=data["name"].strip(),
            code=data["code"].strip().upper(),
            category=data.get("category", "Summative"),
            default_weight_pct=float(data.get("default_weight_pct", 100.0)),
            counts_for_cgpa=bool(data.get("counts_for_cgpa", True)),
            default_full_marks=float(data.get("default_full_marks", 100.0)),
            default_pass_marks=float(data.get("default_pass_marks", 33.0)),
            is_active=bool(data.get("is_active", True)),
            description=data.get("description"),
        )
        db.add(et)
        db.commit()
        db.refresh(et)
        return et

    # -------------------------------------------------------------
    # Exam Terms
    # -------------------------------------------------------------
    @staticmethod
    def get_all_exam_terms(db: Session, academic_year_id: Optional[int] = None) -> List[ExamTerm]:
        query = (
            db.query(ExamTerm)
            .options(
                joinedload(ExamTerm.academic_year),
                joinedload(ExamTerm.exam_type),
                joinedload(ExamTerm.grading_system),
            )
            .filter(ExamTerm.is_deleted == False)
        )
        if academic_year_id:
            query = query.filter(ExamTerm.academic_year_id == academic_year_id)
        return query.order_by(ExamTerm.start_date.desc()).all()

    @staticmethod
    def get_exam_term_by_id(db: Session, term_id: int) -> Optional[ExamTerm]:
        return (
            db.query(ExamTerm)
            .options(
                joinedload(ExamTerm.academic_year),
                joinedload(ExamTerm.exam_type),
                joinedload(ExamTerm.grading_system).joinedload(GradingSystem.rules),
            )
            .filter(ExamTerm.id == term_id, ExamTerm.is_deleted == False)
            .first()
        )

    @staticmethod
    def create_exam_term(db: Session, data: Dict[str, Any]) -> ExamTerm:
        et_id = data.get("exam_type_id")
        weight_pct = data.get("weight_pct")
        counts_cgpa = data.get("counts_for_cgpa")
        if et_id and (weight_pct is None or counts_cgpa is None):
            et = db.query(ExamType).filter(ExamType.id == et_id).first()
            if et:
                if weight_pct is None:
                    weight_pct = et.default_weight_pct
                if counts_cgpa is None:
                    counts_cgpa = et.counts_for_cgpa

        term = ExamTerm(
            name=data["name"].strip(),
            exam_code=data["exam_code"].strip().upper(),
            academic_year_id=data["academic_year_id"],
            exam_type_id=et_id,
            grading_system_id=data.get("grading_system_id"),
            start_date=data["start_date"],
            end_date=data["end_date"],
            weight_pct=float(weight_pct if weight_pct is not None else 100.0),
            counts_for_cgpa=bool(True if counts_cgpa is None else counts_cgpa),
            status=data.get("status", "Scheduled"),
            description=data.get("description"),
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
    # Customizable Grading Systems & Scales
    # -------------------------------------------------------------
    @staticmethod
    def get_all_grading_systems(db: Session, active_only: bool = True) -> List[GradingSystem]:
        q = (
            db.query(GradingSystem)
            .options(joinedload(GradingSystem.rules))
            .filter(GradingSystem.is_deleted == False)
        )
        if active_only:
            q = q.filter(GradingSystem.is_active == True)
        return q.order_by(GradingSystem.is_default.desc(), GradingSystem.id.asc()).all()

    @staticmethod
    def get_grading_system_by_id(db: Session, system_id: int) -> Optional[GradingSystem]:
        return (
            db.query(GradingSystem)
            .options(joinedload(GradingSystem.rules))
            .filter(GradingSystem.id == system_id, GradingSystem.is_deleted == False)
            .first()
        )

    @staticmethod
    def get_default_grading_system(db: Session) -> Optional[GradingSystem]:
        sys_obj = (
            db.query(GradingSystem)
            .options(joinedload(GradingSystem.rules))
            .filter(GradingSystem.is_deleted == False, GradingSystem.is_default == True, GradingSystem.is_active == True)
            .first()
        )
        if not sys_obj:
            sys_obj = (
                db.query(GradingSystem)
                .options(joinedload(GradingSystem.rules))
                .filter(GradingSystem.is_deleted == False, GradingSystem.is_active == True)
                .order_by(GradingSystem.id.asc())
                .first()
            )
        return sys_obj

    @staticmethod
    def get_grading_scales(db: Session) -> List[GradingScale]:
        return db.query(GradingScale).order_by(GradingScale.grade_point.desc()).all()

    @staticmethod
    def get_grade_for_score(
        db: Session,
        percentage: float,
        grading_system_id: Optional[int] = None,
    ) -> Tuple[str, float, str]:
        """
        Determines grade_name, grade_point, and remarks from percentage marks.
        Checks custom GradingSystem rules when specified (or system default),
        and preserves full fallback compatibility with baseline GPA 5.0 GradingScale.
        """
        if grading_system_id is not None:
            sys_obj = ExamRepository.get_grading_system_by_id(db, grading_system_id)
            if sys_obj and sys_obj.rules:
                for rule in sorted(sys_obj.rules, key=lambda r: r.grade_point, reverse=True):
                    if rule.mark_from <= percentage <= rule.mark_to:
                        return rule.grade_name, float(rule.grade_point), rule.remarks
                fail_lbl = sys_obj.fail_grade_name or "F"
                return fail_lbl, 0.0, "Fail"

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
        class_id: Optional[int] = None,
    ) -> List[ExamSchedule]:
        query = (
            db.query(ExamSchedule)
            .options(
                joinedload(ExamSchedule.school_class),
                joinedload(ExamSchedule.subject),
                joinedload(ExamSchedule.section),
            )
            .filter(ExamSchedule.exam_term_id == term_id, ExamSchedule.is_deleted == False)
        )
        if class_id:
            query = query.filter(ExamSchedule.class_id == class_id)
        return query.order_by(ExamSchedule.exam_date.asc(), ExamSchedule.start_time.asc()).all()

    @staticmethod
    def get_schedule_for_subject(
        db: Session,
        term_id: int,
        class_id: int,
        subject_id: int,
    ) -> Optional[ExamSchedule]:
        return (
            db.query(ExamSchedule)
            .filter(
                ExamSchedule.exam_term_id == term_id,
                ExamSchedule.class_id == class_id,
                ExamSchedule.subject_id == subject_id,
                ExamSchedule.is_deleted == False,
            )
            .first()
        )

    @staticmethod
    def create_or_update_schedule(db: Session, data: Dict[str, Any]) -> ExamSchedule:
        existing = (
            db.query(ExamSchedule)
            .filter_by(
                exam_term_id=data["exam_term_id"],
                class_id=data["class_id"],
                subject_id=data["subject_id"],
            )
            .first()
        )

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
            section_id=data.get("section_id"),
            subject_id=data["subject_id"],
            exam_date=data["exam_date"],
            start_time=data.get("start_time", "10:00 AM"),
            end_time=data.get("end_time", "01:00 PM"),
            room_number=data.get("room_number", "Room 101"),
            full_marks=float(data.get("full_marks", 100.0)),
            pass_marks=float(data.get("pass_marks", 33.0)),
            theory_full=float(data.get("theory_full", 70.0)),
            mcq_full=float(data.get("mcq_full", 30.0)),
            practical_full=float(data.get("practical_full", 0.0)),
            viva_full=float(data.get("viva_full", 0.0)),
            attendance_full=float(data.get("attendance_full", 0.0)),
            ca_full=float(data.get("ca_full", 0.0)),
            theory_pass=float(data.get("theory_pass", 0.0)),
            mcq_pass=float(data.get("mcq_pass", 0.0)),
            practical_pass=float(data.get("practical_pass", 0.0)),
            viva_pass=float(data.get("viva_pass", 0.0)),
            attendance_pass=float(data.get("attendance_pass", 0.0)),
            require_component_pass=bool(data.get("require_component_pass", False)),
            subject_credit=float(data.get("subject_credit", 1.0)),
            is_optional_eligible=bool(data.get("is_optional_eligible", False)),
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    # -------------------------------------------------------------
    # Result Lock & Governance Helpers
    # -------------------------------------------------------------
    @staticmethod
    def get_result_batch(db: Session, exam_term_id: int, class_id: int) -> Optional[ExamResultBatch]:
        return (
            db.query(ExamResultBatch)
            .filter(
                ExamResultBatch.exam_term_id == exam_term_id,
                ExamResultBatch.class_id == class_id,
                ExamResultBatch.is_deleted == False,
            )
            .first()
        )

    @staticmethod
    def assert_results_editable(db: Session, exam_term_id: int, class_id: int) -> None:
        batch = ExamRepository.get_result_batch(db, exam_term_id, class_id)
        if batch and (batch.is_published or batch.is_locked or batch.status == ResultWorkflowStatus.PUBLISHED):
            raise PermissionError(
                f"Result for term={exam_term_id}, class={class_id} is already Published/Locked (v{batch.version_no}). "
                f"Unauthorized modification is prohibited; an authorized administrator must reopen it with an audit reason."
            )

    @staticmethod
    def record_result_history(
        db: Session,
        exam_term_id: int,
        class_id: int,
        action: str,
        *,
        student_id: Optional[int] = None,
        version_no: int = 1,
        previous_status: Optional[str] = None,
        new_status: Optional[str] = None,
        snapshot: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        performed_by: str = "system",
        commit: bool = False,
    ) -> ExamResultHistory:
        rec = ExamResultHistory(
            exam_term_id=exam_term_id,
            class_id=class_id,
            student_id=student_id,
            version_no=version_no,
            action=action,
            previous_status=previous_status,
            new_status=new_status,
            snapshot_json=json.dumps(snapshot, default=str) if snapshot is not None else None,
            reason=reason,
            performed_by=performed_by or "system",
        )
        db.add(rec)
        if commit:
            db.commit()
            db.refresh(rec)
        else:
            db.flush()
        return rec

    @staticmethod
    def list_result_history(
        db: Session,
        exam_term_id: Optional[int] = None,
        class_id: Optional[int] = None,
        student_id: Optional[int] = None,
    ) -> List[ExamResultHistory]:
        q = db.query(ExamResultHistory)
        if exam_term_id is not None:
            q = q.filter(ExamResultHistory.exam_term_id == exam_term_id)
        if class_id is not None:
            q = q.filter(ExamResultHistory.class_id == class_id)
        if student_id is not None:
            q = q.filter(ExamResultHistory.student_id == student_id)
        return q.order_by(ExamResultHistory.performed_at.desc(), ExamResultHistory.id.desc()).all()

    # -------------------------------------------------------------
    # Student Marks Register (Granular Components + Lock Guard)
    # -------------------------------------------------------------
    @staticmethod
    def get_marks_for_subject(
        db: Session,
        exam_term_id: int,
        class_id: int,
        subject_id: int,
    ) -> List[StudentMark]:
        return (
            db.query(StudentMark)
            .options(joinedload(StudentMark.student))
            .filter(
                StudentMark.exam_term_id == exam_term_id,
                StudentMark.class_id == class_id,
                StudentMark.subject_id == subject_id,
            )
            .all()
        )

    @staticmethod
    def get_marks_for_student(
        db: Session,
        exam_term_id: int,
        student_id: int,
    ) -> List[StudentMark]:
        return (
            db.query(StudentMark)
            .options(joinedload(StudentMark.subject))
            .filter(
                StudentMark.exam_term_id == exam_term_id,
                StudentMark.student_id == student_id,
            )
            .all()
        )

    @staticmethod
    def upsert_student_mark(
        db: Session,
        data: Dict[str, Any],
        actor_user: Optional[User] = None,
    ) -> StudentMark:
        exam_term_id = data["exam_term_id"]
        class_id = data["class_id"]
        subject_id = data["subject_id"]
        student_id = data["student_id"]

        # Block modification once result batch is published & locked
        ExamRepository.assert_results_editable(db, exam_term_id, class_id)

        existing = (
            db.query(StudentMark)
            .filter_by(
                exam_term_id=exam_term_id,
                student_id=student_id,
                subject_id=subject_id,
            )
            .first()
        )
        if existing and existing.is_locked:
            raise PermissionError(
                f"Mark entry for student_id={student_id}, subject_id={subject_id} is locked."
            )

        term = ExamRepository.get_exam_term_by_id(db, exam_term_id)
        schedule = ExamRepository.get_schedule_for_subject(db, exam_term_id, class_id, subject_id)
        grading_sys_id = data.get("grading_system_id") or (term.grading_system_id if term else None)
        grading_sys = (
            ExamRepository.get_grading_system_by_id(db, grading_sys_id)
            if grading_sys_id
            else None
        )

        theory = float(data.get("theory_marks", 0.0))
        mcq = float(data.get("mcq_marks", 0.0))
        practical = float(data.get("practical_marks", 0.0))
        viva = float(data.get("viva_marks", 0.0))
        attendance = float(data.get("attendance_marks", 0.0))
        ca = float(data.get("ca_marks", 0.0))
        is_absent = bool(data.get("is_absent", False))
        is_optional = bool(data.get("is_optional", schedule.is_optional_eligible if schedule else False))

        full_marks = float(data.get("full_marks") or (schedule.full_marks if schedule else 100.0))
        if "pass_marks" in data and data["pass_marks"] is not None:
            pass_marks = float(data["pass_marks"])
        elif schedule:
            pass_marks = float(schedule.pass_marks)
        elif grading_sys:
            pass_marks = round(full_marks * float(grading_sys.pass_percentage) / 100.0, 2)
        else:
            pass_marks = round(full_marks * 0.33, 2)

        raw_total = 0.0 if is_absent else round(theory + mcq + practical + viva + attendance + ca, 2)

        # Component-wise pass enforcement if configured on schedule or grading system
        req_comp_pass = bool(
            data.get("require_component_pass")
            if "require_component_pass" in data
            else (
                (schedule.require_component_pass if schedule else False)
                or (grading_sys.require_component_pass if grading_sys else False)
            )
        )
        comp_failed = False
        if req_comp_pass and schedule and not is_absent:
            if schedule.theory_pass > 0 and theory < schedule.theory_pass:
                comp_failed = True
            if schedule.mcq_pass > 0 and mcq < schedule.mcq_pass:
                comp_failed = True
            if schedule.practical_pass > 0 and practical < schedule.practical_pass:
                comp_failed = True
            if schedule.viva_pass > 0 and viva < schedule.viva_pass:
                comp_failed = True
            if schedule.attendance_pass > 0 and attendance < schedule.attendance_pass:
                comp_failed = True

        # Optional configurable Grace Marks rule
        grace_applied = float(data.get("grace_marks_applied", 0.0) or 0.0)
        grace_limit = float(grading_sys.grace_marks_limit) if grading_sys else 0.0
        if (
            not is_absent
            and not comp_failed
            and grace_limit > 0
            and grace_applied == 0.0
            and raw_total < pass_marks
            and (pass_marks - raw_total) <= grace_limit
        ):
            grace_applied = round(pass_marks - raw_total, 2)

        total = 0.0 if is_absent else round(min(full_marks, raw_total + grace_applied), 2)
        pct = (total / full_marks * 100.0) if full_marks > 0 else 0.0
        is_passed = (total >= pass_marks) and (not comp_failed) and (not is_absent)

        fail_label = (grading_sys.fail_grade_name if grading_sys else "F") or "F"
        if is_absent:
            grade_name, grade_point, remarks = fail_label, 0.0, "Absent in Examination"
        elif comp_failed:
            grade_name, grade_point, remarks = fail_label, 0.0, "Failed Component Pass Rule"
        else:
            grade_name, grade_point, remarks = ExamRepository.get_grade_for_score(
                db, pct, grading_system_id=grading_sys_id
            )
            if not is_passed:
                grade_name, grade_point, remarks = fail_label, 0.0, "Failed"
            elif grace_applied > 0:
                remarks = f"{remarks} (+{grace_applied:g} Grace)"

        username = _resolve_actor_username(actor_user, fallback=data.get("entered_by") or "teacher")

        if existing:
            prev_total = existing.total_marks
            prev_grade = existing.grade_name
            existing.theory_marks = theory
            existing.mcq_marks = mcq
            existing.practical_marks = practical
            existing.viva_marks = viva
            existing.attendance_marks = attendance
            existing.ca_marks = ca
            existing.grace_marks_applied = grace_applied
            existing.full_marks_snapshot = full_marks
            existing.total_marks = total
            existing.is_absent = is_absent
            existing.is_optional = is_optional
            existing.grade_name = grade_name
            existing.grade_point = grade_point
            existing.is_passed = is_passed
            existing.entered_by = username
            existing.remarks = data.get("remarks") or remarks

            if prev_total != total or prev_grade != grade_name:
                ExamRepository.record_result_history(
                    db,
                    exam_term_id,
                    class_id,
                    action="MARK_UPDATED",
                    student_id=student_id,
                    snapshot={
                        "subject_id": subject_id,
                        "previous_total": prev_total,
                        "new_total": total,
                        "previous_grade": prev_grade,
                        "new_grade": grade_name,
                    },
                    reason=data.get("reason") or "Mark revision prior to publish",
                    performed_by=username,
                    commit=False,
                )

            db.commit()
            db.refresh(existing)
            return existing

        mark = StudentMark(
            exam_term_id=exam_term_id,
            class_id=class_id,
            subject_id=subject_id,
            student_id=student_id,
            theory_marks=theory,
            mcq_marks=mcq,
            practical_marks=practical,
            viva_marks=viva,
            attendance_marks=attendance,
            ca_marks=ca,
            grace_marks_applied=grace_applied,
            full_marks_snapshot=full_marks,
            total_marks=total,
            is_absent=is_absent,
            is_optional=is_optional,
            grade_name=grade_name,
            grade_point=grade_point,
            is_passed=is_passed,
            entered_by=username,
            remarks=data.get("remarks") or remarks,
        )
        db.add(mark)
        db.commit()
        db.refresh(mark)
        return mark

    # -------------------------------------------------------------
    # Tabulation & Result Compilation Storage
    # -------------------------------------------------------------
    @staticmethod
    def get_class_result_summaries(
        db: Session,
        exam_term_id: int,
        class_id: int,
    ) -> List[ExamResultSummary]:
        return (
            db.query(ExamResultSummary)
            .options(joinedload(ExamResultSummary.student), joinedload(ExamResultSummary.school_class))
            .filter(ExamResultSummary.exam_term_id == exam_term_id, ExamResultSummary.class_id == class_id)
            .order_by(ExamResultSummary.class_rank.asc(), ExamResultSummary.total_obtained.desc())
            .all()
        )

    @staticmethod
    def get_student_result_summary(
        db: Session,
        exam_term_id: int,
        student_id: int,
    ) -> Optional[ExamResultSummary]:
        return (
            db.query(ExamResultSummary)
            .options(
                joinedload(ExamResultSummary.student),
                joinedload(ExamResultSummary.school_class),
                joinedload(ExamResultSummary.exam_term),
            )
            .filter(ExamResultSummary.exam_term_id == exam_term_id, ExamResultSummary.student_id == student_id)
            .first()
        )

    @staticmethod
    def save_result_summaries(db: Session, summaries: List[Dict[str, Any]], version_no: int = 1):
        for s in summaries:
            existing = (
                db.query(ExamResultSummary)
                .filter_by(exam_term_id=s["exam_term_id"], student_id=s["student_id"])
                .first()
            )
            if existing:
                existing.total_obtained = s["total_obtained"]
                existing.total_full_marks = s["total_full_marks"]
                existing.percentage = s["percentage"]
                existing.gpa = s["gpa"]
                existing.cgpa = s.get("cgpa", s["gpa"])
                existing.optional_bonus_gp = s.get("optional_bonus_gp", 0.0)
                existing.overall_grade = s["overall_grade"]
                existing.class_rank = s["class_rank"]
                existing.section_rank = s.get("section_rank")
                existing.attendance_percentage = s.get("attendance_percentage")
                existing.passed_all = s["passed_all"]
                existing.failed_subject_count = s["failed_subject_count"]
                existing.result_status = s.get("result_status", ResultWorkflowStatus.COMPILED)
                existing.version_no = version_no
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
                    cgpa=s.get("cgpa", s["gpa"]),
                    optional_bonus_gp=s.get("optional_bonus_gp", 0.0),
                    overall_grade=s["overall_grade"],
                    class_rank=s["class_rank"],
                    section_rank=s.get("section_rank"),
                    attendance_percentage=s.get("attendance_percentage"),
                    passed_all=s["passed_all"],
                    failed_subject_count=s["failed_subject_count"],
                    result_status=s.get("result_status", ResultWorkflowStatus.COMPILED),
                    version_no=version_no,
                    remarks=s.get("remarks"),
                )
                db.add(item)
        db.commit()

    # -------------------------------------------------------------
    # Question Bank & Exam Papers
    # -------------------------------------------------------------
    @staticmethod
    def list_questions(
        db: Session,
        subject_id: Optional[int] = None,
        class_id: Optional[int] = None,
        question_type: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> List[QuestionBankItem]:
        q = (
            db.query(QuestionBankItem)
            .options(joinedload(QuestionBankItem.subject), joinedload(QuestionBankItem.school_class))
            .filter(QuestionBankItem.is_deleted == False, QuestionBankItem.is_active == True)
        )
        if subject_id is not None:
            q = q.filter(QuestionBankItem.subject_id == subject_id)
        if class_id is not None:
            q = q.filter(QuestionBankItem.class_id == class_id)
        if question_type and question_type != "All":
            q = q.filter(QuestionBankItem.question_type == question_type)
        if difficulty and difficulty != "All":
            q = q.filter(QuestionBankItem.difficulty == difficulty)
        return q.order_by(QuestionBankItem.id.desc()).all()

    @staticmethod
    def list_exam_papers(
        db: Session,
        class_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        paper_type: Optional[str] = None,
    ) -> List[ExamPaper]:
        q = (
            db.query(ExamPaper)
            .options(
                joinedload(ExamPaper.school_class),
                joinedload(ExamPaper.subject),
                joinedload(ExamPaper.exam_term),
                joinedload(ExamPaper.questions).joinedload(ExamPaperQuestion.question),
            )
            .filter(ExamPaper.is_deleted == False)
        )
        if class_id is not None:
            q = q.filter(ExamPaper.class_id == class_id)
        if subject_id is not None:
            q = q.filter(ExamPaper.subject_id == subject_id)
        if paper_type and paper_type != "All":
            q = q.filter(ExamPaper.paper_type == paper_type)
        return q.order_by(ExamPaper.id.desc()).all()

    @staticmethod
    def get_exam_paper_by_id(db: Session, paper_id: int) -> Optional[ExamPaper]:
        return (
            db.query(ExamPaper)
            .options(
                joinedload(ExamPaper.school_class),
                joinedload(ExamPaper.subject),
                joinedload(ExamPaper.exam_term),
                joinedload(ExamPaper.questions).joinedload(ExamPaperQuestion.question),
            )
            .filter(ExamPaper.id == paper_id, ExamPaper.is_deleted == False)
            .first()
        )
