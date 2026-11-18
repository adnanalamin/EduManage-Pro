"""
EduManage Pro - Advanced Examination, Grading, Question Bank & Result Governance Models
Covers:
- ExamType: Configurable exam categories & CGPA weighting
- GradingSystem & GradingScaleRule + GradingScale: Customizable grading scales & configurable pass/grace/optional/attendance rules
- ExamTerm: Examination sessions linked to ExamType & GradingSystem
- ExamSchedule: Subject-wise routines with Theory, MCQ, Practical, Viva & Attendance component breakdown + component pass rules
- StudentMark: Granular marks (Theory, MCQ, Practical, Viva, Attendance, CA, Grace) with publish lock & snapshot
- ExamResultSummary, ExamResultBatch, ExamResultHistory: GPA, CGPA, Class & Section Position, Verify -> Approve -> Publish lock & immutable history
- QuestionBankItem, ExamPaper, ExamPaperQuestion, MCQAttempt, MCQAttemptAnswer: Written & MCQ assessment engine
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.base import PublicIdMixin, SoftDeleteMixin, TimestampMixin, utc_now


class ResultWorkflowStatus:
    DRAFT = "Draft"
    COMPILED = "Compiled"
    VERIFIED = "Verified"
    APPROVED = "Approved"
    PUBLISHED = "Published"
    REOPENED = "Reopened"
    ALL = (DRAFT, COMPILED, VERIFIED, APPROVED, PUBLISHED, REOPENED)


class ExamType(Base, PublicIdMixin, TimestampMixin, SoftDeleteMixin):
    """
    Configurable exam type (Class Test, Mid-Term, Annual, Practical/Viva, Model Test, Online MCQ).
    Defines weightage for cumulative CGPA across terms.
    """

    __tablename__ = "exam_types"

    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False, index=True)
    category = Column(String(30), nullable=False, default="Summative")  # Formative | Summative | Practical | MCQ
    default_weight_pct = Column(Float, nullable=False, default=100.0)
    counts_for_cgpa = Column(Boolean, default=True, nullable=False)
    default_full_marks = Column(Float, nullable=False, default=100.0)
    default_pass_marks = Column(Float, nullable=False, default=33.0)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(String(255), nullable=True)

    exam_terms = relationship("ExamTerm", back_populates="exam_type")

    __table_args__ = (
        CheckConstraint("default_weight_pct >= 0 AND default_full_marks > 0", name="ck_exam_type_valid"),
    )

    def __repr__(self):
        return f"<ExamType(code='{self.code}', name='{self.name}', weight={self.default_weight_pct}%)>"


class GradingSystem(Base, PublicIdMixin, TimestampMixin, SoftDeleteMixin):
    """
    Customizable grading scheme with configurable grading rules (component pass, grace marks,
    optional 4th-subject bonus, attendance weighting, and CGPA aggregation mode).
    """

    __tablename__ = "grading_systems"

    name = Column(String(120), unique=True, nullable=False)
    code = Column(String(30), unique=True, nullable=False, index=True)
    max_gpa = Column(Float, nullable=False, default=5.0)
    pass_percentage = Column(Float, nullable=False, default=33.0)
    require_component_pass = Column(Boolean, default=False, nullable=False)
    grace_marks_limit = Column(Float, nullable=False, default=0.0)
    optional_subject_enabled = Column(Boolean, default=True, nullable=False)
    optional_subject_min_gp = Column(Float, nullable=False, default=2.0)
    attendance_weight_pct = Column(Float, nullable=False, default=0.0)
    cgpa_mode = Column(String(30), nullable=False, default="WeightedTerms")  # EqualAverage | WeightedTerms
    fail_grade_name = Column(String(10), nullable=False, default="F")
    round_decimals = Column(Integer, nullable=False, default=2)
    is_default = Column(Boolean, default=False, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(String(255), nullable=True)

    rules = relationship(
        "GradingScaleRule",
        back_populates="grading_system",
        cascade="all, delete-orphan",
        order_by="GradingScaleRule.grade_point.desc()",
    )
    exam_terms = relationship("ExamTerm", back_populates="grading_system")

    __table_args__ = (
        CheckConstraint("max_gpa > 0 AND pass_percentage >= 0 AND grace_marks_limit >= 0", name="ck_grading_sys_valid"),
    )

    def __repr__(self):
        return f"<GradingSystem(code='{self.code}', name='{self.name}', max_gpa={self.max_gpa})>"


class GradingScaleRule(Base, TimestampMixin):
    """Individual grade band inside a customizable GradingSystem."""

    __tablename__ = "grading_scale_rules"

    grading_system_id = Column(Integer, ForeignKey("grading_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    grade_name = Column(String(15), nullable=False)
    grade_point = Column(Float, nullable=False)
    mark_from = Column(Float, nullable=False)
    mark_to = Column(Float, nullable=False)
    is_passing = Column(Boolean, default=True, nullable=False)
    remarks = Column(String(80), nullable=False, default="")

    grading_system = relationship("GradingSystem", back_populates="rules")

    __table_args__ = (
        UniqueConstraint("grading_system_id", "grade_name", name="uq_grading_rule_sys_grade"),
        CheckConstraint("grade_point >= 0 AND mark_to >= mark_from", name="ck_grading_rule_range"),
    )

    def __repr__(self):
        return f"<GradingScaleRule(grade='{self.grade_name}', gp={self.grade_point}, {self.mark_from}-{self.mark_to})>"


class GradingScale(Base, TimestampMixin, SoftDeleteMixin):
    """
    Default baseline GPA 5.0 grading table (preserved for backward compatibility).
    """

    __tablename__ = "grading_scales"

    grade_name = Column(String(10), unique=True, nullable=False)
    grade_point = Column(Float, nullable=False)
    mark_from = Column(Float, nullable=False)
    mark_to = Column(Float, nullable=False)
    remarks = Column(String(50), nullable=False)

    __table_args__ = (
        CheckConstraint("grade_point >= 0 AND mark_to >= mark_from", name="ck_grading_scale_valid"),
    )

    def __repr__(self):
        return f"<GradingScale(grade='{self.grade_name}', point={self.grade_point}, range={self.mark_from}-{self.mark_to})>"


class ExamTerm(Base, TimestampMixin, SoftDeleteMixin):
    """
    Examination session or term (e.g. First Term, Half-Yearly, Final Term, SSC Model Test).
    """

    __tablename__ = "exam_terms"

    name = Column(String(120), nullable=False)
    exam_code = Column(String(30), unique=True, nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)
    exam_type_id = Column(Integer, ForeignKey("exam_types.id", ondelete="SET NULL"), nullable=True, index=True)
    grading_system_id = Column(Integer, ForeignKey("grading_systems.id", ondelete="SET NULL"), nullable=True, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    weight_pct = Column(Float, nullable=True, default=100.0)
    counts_for_cgpa = Column(Boolean, nullable=False, default=True)
    status = Column(String(30), default="Scheduled", nullable=False, index=True)
    description = Column(String(255), nullable=True)

    academic_year = relationship("AcademicYear")
    exam_type = relationship("ExamType", back_populates="exam_terms")
    grading_system = relationship("GradingSystem", back_populates="exam_terms")
    schedules = relationship("ExamSchedule", back_populates="exam_term", cascade="all, delete-orphan")
    marks = relationship("StudentMark", back_populates="exam_term")
    summaries = relationship("ExamResultSummary", back_populates="exam_term")
    result_batches = relationship("ExamResultBatch", back_populates="exam_term")

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_exam_term_dates"),
        Index("idx_exam_term_year_status", "academic_year_id", "status"),
    )

    def __repr__(self):
        return f"<ExamTerm(name='{self.name}', code='{self.exam_code}', status='{self.status}')>"


class ExamSchedule(Base, TimestampMixin, SoftDeleteMixin):
    """
    Subject-wise exam timetable routine, room allocation, and granular component marks/pass rules.
    """

    __tablename__ = "exam_schedules"

    exam_term_id = Column(Integer, ForeignKey("exam_terms.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    exam_date = Column(Date, nullable=False, index=True)
    start_time = Column(String(20), nullable=False, default="10:00 AM")
    end_time = Column(String(20), nullable=False, default="01:00 PM")
    room_number = Column(String(50), nullable=True, default="Room 101")

    full_marks = Column(Float, nullable=False, default=100.0)
    pass_marks = Column(Float, nullable=False, default=33.0)
    theory_full = Column(Float, nullable=False, default=70.0)
    mcq_full = Column(Float, nullable=False, default=30.0)
    practical_full = Column(Float, nullable=False, default=0.0)
    viva_full = Column(Float, nullable=False, default=0.0)
    attendance_full = Column(Float, nullable=False, default=0.0)
    ca_full = Column(Float, nullable=False, default=0.0)

    # Component-level pass rules
    theory_pass = Column(Float, nullable=False, default=0.0)
    mcq_pass = Column(Float, nullable=False, default=0.0)
    practical_pass = Column(Float, nullable=False, default=0.0)
    viva_pass = Column(Float, nullable=False, default=0.0)
    attendance_pass = Column(Float, nullable=False, default=0.0)
    require_component_pass = Column(Boolean, nullable=False, default=False)

    subject_credit = Column(Float, nullable=False, default=1.0)
    is_optional_eligible = Column(Boolean, nullable=False, default=False)

    exam_term = relationship("ExamTerm", back_populates="schedules")
    school_class = relationship("SchoolClass")
    section = relationship("Section")
    subject = relationship("Subject")

    __table_args__ = (
        UniqueConstraint("exam_term_id", "class_id", "subject_id", name="uq_exam_schedule_term_class_sub"),
        CheckConstraint("full_marks > 0 AND pass_marks >= 0 AND pass_marks <= full_marks", name="ck_exam_schedule_marks"),
        Index("idx_exam_schedule_term_class", "exam_term_id", "class_id"),
    )

    def __repr__(self):
        return f"<ExamSchedule(term_id={self.exam_term_id}, class_id={self.class_id}, subject_id={self.subject_id})>"


class StudentMark(Base, TimestampMixin, SoftDeleteMixin):
    """
    Component-wise exam marks obtained by an individual student (Theory, MCQ, Practical, Viva, Attendance, CA, Grace).
    Protected against unauthorized modification once the parent result batch is Published.
    """

    __tablename__ = "student_marks"

    exam_term_id = Column(Integer, ForeignKey("exam_terms.id", ondelete="RESTRICT"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)

    theory_marks = Column(Float, default=0.0, nullable=False)
    mcq_marks = Column(Float, default=0.0, nullable=False)
    practical_marks = Column(Float, default=0.0, nullable=False)
    viva_marks = Column(Float, default=0.0, nullable=False)
    attendance_marks = Column(Float, default=0.0, nullable=False)
    ca_marks = Column(Float, default=0.0, nullable=False)
    grace_marks_applied = Column(Float, default=0.0, nullable=False)
    full_marks_snapshot = Column(Float, default=100.0, nullable=False)
    total_marks = Column(Float, nullable=False, default=0.0)
    is_absent = Column(Boolean, default=False, nullable=False)
    is_optional = Column(Boolean, default=False, nullable=False)

    grade_name = Column(String(10), nullable=False, default="F")
    grade_point = Column(Float, nullable=False, default=0.0)
    is_passed = Column(Boolean, default=False, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False, index=True)
    entered_by = Column(String(100), nullable=True)
    verified_by = Column(String(100), nullable=True)
    remarks = Column(String(120), nullable=True)

    exam_term = relationship("ExamTerm", back_populates="marks")
    school_class = relationship("SchoolClass")
    subject = relationship("Subject")
    student = relationship("Student")

    __table_args__ = (
        UniqueConstraint("exam_term_id", "student_id", "subject_id", name="uq_student_exam_subject_mark"),
        CheckConstraint(
            "theory_marks >= 0 AND mcq_marks >= 0 AND practical_marks >= 0 AND viva_marks >= 0 "
            "AND attendance_marks >= 0 AND ca_marks >= 0 AND total_marks >= 0",
            name="ck_student_mark_nonneg",
        ),
        Index("idx_student_mark_term_class_sub", "exam_term_id", "class_id", "subject_id"),
    )

    def __repr__(self):
        return f"<StudentMark(student_id={self.student_id}, subject_id={self.subject_id}, total={self.total_marks}, grade='{self.grade_name}')>"


class ExamResultSummary(Base, TimestampMixin, SoftDeleteMixin):
    """
    Compiled term result summary, final GPA, cumulative CGPA, class & section positions, and governance state.
    """

    __tablename__ = "exam_result_summaries"

    exam_term_id = Column(Integer, ForeignKey("exam_terms.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False, index=True)

    total_obtained = Column(Float, nullable=False, default=0.0)
    total_full_marks = Column(Float, nullable=False, default=0.0)
    percentage = Column(Float, nullable=False, default=0.0)
    gpa = Column(Float, nullable=False, default=0.0)
    cgpa = Column(Float, nullable=False, default=0.0)
    optional_bonus_gp = Column(Float, nullable=False, default=0.0)
    overall_grade = Column(String(10), nullable=False, default="F")
    class_rank = Column(Integer, nullable=True)
    section_rank = Column(Integer, nullable=True)
    attendance_percentage = Column(Float, nullable=True)
    passed_all = Column(Boolean, default=False, nullable=False)
    failed_subject_count = Column(Integer, default=0, nullable=False)
    remarks = Column(String(180), nullable=True)

    # Governance & Publishing Lock
    result_status = Column(String(30), nullable=False, default=ResultWorkflowStatus.COMPILED, index=True)
    is_published = Column(Boolean, default=False, nullable=False, index=True)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(String(100), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    version_no = Column(Integer, nullable=False, default=1)

    exam_term = relationship("ExamTerm", back_populates="summaries")
    student = relationship("Student")
    school_class = relationship("SchoolClass")

    __table_args__ = (
        UniqueConstraint("exam_term_id", "student_id", name="uq_exam_result_summary_term_student"),
        CheckConstraint(
            "total_obtained >= 0 AND total_full_marks >= 0 AND gpa >= 0 AND failed_subject_count >= 0",
            name="ck_exam_summary_nonneg",
        ),
        Index("idx_exam_summary_rank", "exam_term_id", "class_id", "class_rank"),
    )

    def __repr__(self):
        return f"<ExamResultSummary(student_id={self.student_id}, gpa={self.gpa}, cgpa={self.cgpa}, grade='{self.overall_grade}', rank={self.class_rank})>"


class ExamResultBatch(Base, PublicIdMixin, TimestampMixin, SoftDeleteMixin):
    """
    Result publication governance record per (exam_term_id, class_id).
    Tracks Draft -> Compiled -> Verified -> Approved -> Published -> Reopened workflow and publishing lock.
    """

    __tablename__ = "exam_result_batches"

    exam_term_id = Column(Integer, ForeignKey("exam_terms.id", ondelete="RESTRICT"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False, index=True)
    grading_system_id = Column(Integer, ForeignKey("grading_systems.id", ondelete="SET NULL"), nullable=True)

    status = Column(String(30), nullable=False, default=ResultWorkflowStatus.COMPILED, index=True)
    is_published = Column(Boolean, default=False, nullable=False, index=True)
    is_locked = Column(Boolean, default=False, nullable=False, index=True)
    version_no = Column(Integer, nullable=False, default=1)

    compiled_by = Column(String(100), nullable=True)
    compiled_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_notes = Column(String(255), nullable=True)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(String(255), nullable=True)
    published_by = Column(String(100), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    exam_term = relationship("ExamTerm", back_populates="result_batches")
    school_class = relationship("SchoolClass")
    grading_system = relationship("GradingSystem")

    __table_args__ = (
        UniqueConstraint("exam_term_id", "class_id", name="uq_exam_result_batch_term_class"),
    )

    def __repr__(self):
        return f"<ExamResultBatch(term={self.exam_term_id}, class={self.class_id}, status='{self.status}', published={self.is_published})>"


class ExamResultHistory(Base, PublicIdMixin):
    """
    Immutable result audit history & snapshots capturing every compilation, mark edit,
    verification, approval, publication, and authorized post-publish reopen.
    """

    __tablename__ = "exam_result_history"

    exam_term_id = Column(Integer, ForeignKey("exam_terms.id", ondelete="RESTRICT"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=True, index=True)

    version_no = Column(Integer, nullable=False, default=1)
    action = Column(String(40), nullable=False, index=True)  # COMPILED | VERIFIED | APPROVED | PUBLISHED | REOPENED | MARK_UPDATED
    previous_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=True)
    snapshot_json = Column(Text, nullable=True)
    reason = Column(String(255), nullable=True)
    performed_by = Column(String(100), nullable=False, default="system")
    performed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    exam_term = relationship("ExamTerm")
    school_class = relationship("SchoolClass")
    student = relationship("Student")

    def __repr__(self):
        return f"<ExamResultHistory(term={self.exam_term_id}, class={self.class_id}, action='{self.action}', v={self.version_no})>"


class QuestionBankItem(Base, PublicIdMixin, TimestampMixin, SoftDeleteMixin):
    """
    Structured Question Bank supporting MCQ, Written, Short Answer, Practical & Viva questions.
    """

    __tablename__ = "exam_question_bank"

    question_code = Column(String(40), unique=True, nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="SET NULL"), nullable=True, index=True)
    topic = Column(String(120), nullable=True, index=True)
    question_type = Column(String(25), nullable=False, default="MCQ", index=True)  # MCQ | Written | ShortAnswer | Practical | Viva
    difficulty = Column(String(20), nullable=False, default="Medium", index=True)  # Easy | Medium | Hard
    bloom_level = Column(String(30), nullable=True, default="Understand")
    question_text = Column(Text, nullable=False)
    options_json = Column(Text, nullable=True)  # JSON object/list for MCQ options
    correct_option = Column(String(20), nullable=True)  # e.g., "A", "B", "C", "D"
    model_answer = Column(Text, nullable=True)
    marks = Column(Float, nullable=False, default=1.0)
    negative_marks = Column(Float, nullable=False, default=0.0)
    created_by = Column(String(100), nullable=False, default="teacher")
    is_active = Column(Boolean, default=True, nullable=False)

    subject = relationship("Subject")
    school_class = relationship("SchoolClass")

    __table_args__ = (
        CheckConstraint("marks > 0 AND negative_marks >= 0", name="ck_qb_marks_valid"),
    )

    def __repr__(self):
        return f"<QuestionBankItem(code='{self.question_code}', type='{self.question_type}', marks={self.marks})>"


class ExamPaper(Base, PublicIdMixin, TimestampMixin, SoftDeleteMixin):
    """
    Generated or curated Examination Question Paper supporting MCQ, Written, or Combined assessments.
    """

    __tablename__ = "exam_papers"

    paper_code = Column(String(40), unique=True, nullable=False, index=True)
    title = Column(String(180), nullable=False)
    exam_term_id = Column(Integer, ForeignKey("exam_terms.id", ondelete="SET NULL"), nullable=True, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    paper_type = Column(String(25), nullable=False, default="Written", index=True)  # MCQ | Written | Combined
    duration_minutes = Column(Integer, nullable=False, default=60)
    total_marks = Column(Float, nullable=False, default=100.0)
    pass_marks = Column(Float, nullable=False, default=33.0)
    negative_marking = Column(Boolean, default=False, nullable=False)
    instructions = Column(Text, nullable=True)
    status = Column(String(25), nullable=False, default="Draft", index=True)  # Draft | Approved | Conducted
    created_by = Column(String(100), nullable=False, default="teacher")

    exam_term = relationship("ExamTerm")
    school_class = relationship("SchoolClass")
    subject = relationship("Subject")
    questions = relationship(
        "ExamPaperQuestion",
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="ExamPaperQuestion.order_no.asc()",
    )
    attempts = relationship("MCQAttempt", back_populates="paper")

    __table_args__ = (
        CheckConstraint("duration_minutes > 0 AND total_marks > 0", name="ck_exam_paper_valid"),
    )

    def __repr__(self):
        return f"<ExamPaper(code='{self.paper_code}', type='{self.paper_type}', total={self.total_marks})>"


class ExamPaperQuestion(Base, TimestampMixin):
    """Ordered link attaching QuestionBankItem entries into an ExamPaper."""

    __tablename__ = "exam_paper_questions"

    exam_paper_id = Column(Integer, ForeignKey("exam_papers.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("exam_question_bank.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_no = Column(Integer, nullable=False, default=1)
    section_label = Column(String(80), nullable=True, default="Section A")
    marks = Column(Float, nullable=False, default=1.0)

    paper = relationship("ExamPaper", back_populates="questions")
    question = relationship("QuestionBankItem")

    __table_args__ = (
        UniqueConstraint("exam_paper_id", "question_id", name="uq_paper_question"),
        CheckConstraint("marks > 0 AND order_no >= 1", name="ck_paper_question_valid"),
    )


class MCQAttempt(Base, PublicIdMixin, TimestampMixin):
    """Records & auto-grades a student's MCQ ExamPaper submission and syncs marks."""

    __tablename__ = "exam_mcq_attempts"

    attempt_code = Column(String(40), unique=True, nullable=False, index=True)
    exam_paper_id = Column(Integer, ForeignKey("exam_papers.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    submitted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    total_questions = Column(Integer, nullable=False, default=0)
    correct_count = Column(Integer, nullable=False, default=0)
    wrong_count = Column(Integer, nullable=False, default=0)
    unanswered_count = Column(Integer, nullable=False, default=0)
    raw_score = Column(Float, nullable=False, default=0.0)
    negative_deducted = Column(Float, nullable=False, default=0.0)
    net_score = Column(Float, nullable=False, default=0.0)
    percentage = Column(Float, nullable=False, default=0.0)
    is_passed = Column(Boolean, default=False, nullable=False)
    synced_to_marks = Column(Boolean, default=False, nullable=False)

    paper = relationship("ExamPaper", back_populates="attempts")
    student = relationship("Student")
    answers = relationship("MCQAttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("exam_paper_id", "student_id", name="uq_mcq_attempt_paper_student"),
    )


class MCQAttemptAnswer(Base):
    """Per-question response within an MCQAttempt."""

    __tablename__ = "exam_mcq_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    attempt_id = Column(Integer, ForeignKey("exam_mcq_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("exam_question_bank.id", ondelete="RESTRICT"), nullable=False)
    selected_option = Column(String(20), nullable=True)
    is_correct = Column(Boolean, default=False, nullable=False)
    marks_awarded = Column(Float, nullable=False, default=0.0)

    attempt = relationship("MCQAttempt", back_populates="answers")
    question = relationship("QuestionBankItem")


def _prevent_exam_history_delete(mapper, connection, target):
    raise ValueError(
        f"Permanent deletion of {type(target).__name__} is prohibited by academic audit policy."
    )


event.listen(ExamResultHistory, "before_delete", _prevent_exam_history_delete)
