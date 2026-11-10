"""
EduManage Pro - Examination & Grading Models
Defines ExamTerm, ExamSchedule, GradingScale, StudentMark, and ExamResultSummary for GPA 5.0 grading.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Date, Time, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin


class ExamTerm(Base, TimestampMixin):
    """
    Examination session or term (e.g. First Term, Half-Yearly, Final Term, SSC Model Test).
    """
    __tablename__ = "exam_terms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    exam_code = Column(String(30), unique=True, nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(30), default="Scheduled")  # 'Scheduled' | 'In Progress' | 'Completed' | 'Published'
    description = Column(String(255), nullable=True)

    academic_year = relationship("AcademicYear")
    schedules = relationship("ExamSchedule", back_populates="exam_term", cascade="all, delete-orphan")
    marks = relationship("StudentMark", back_populates="exam_term", cascade="all, delete-orphan")
    summaries = relationship("ExamResultSummary", back_populates="exam_term", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ExamTerm(name='{self.name}', code='{self.exam_code}', status='{self.status}')>"


class GradingScale(Base, TimestampMixin):
    """
    Official GPA grading scale (Standard 5.0 scale: A+, A, A-, B, C, D, F).
    """
    __tablename__ = "grading_scales"

    id = Column(Integer, primary_key=True, index=True)
    grade_name = Column(String(10), unique=True, nullable=False)  # 'A+', 'A', etc.
    grade_point = Column(Float, nullable=False)                   # 5.0, 4.0, 3.5, etc.
    mark_from = Column(Float, nullable=False)                     # 80.0
    mark_to = Column(Float, nullable=False)                       # 100.0
    remarks = Column(String(50), nullable=False)                  # 'Outstanding', 'Fail', etc.

    def __repr__(self):
        return f"<GradingScale(grade='{self.grade_name}', point={self.grade_point}, range={self.mark_from}-{self.mark_to})>"


class ExamSchedule(Base, TimestampMixin):
    """
    Subject-wise exam timetable routine, room allocation, and full marks breakdown.
    """
    __tablename__ = "exam_schedules"

    id = Column(Integer, primary_key=True, index=True)
    exam_term_id = Column(Integer, ForeignKey("exam_terms.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    exam_date = Column(Date, nullable=False)
    start_time = Column(String(20), nullable=False, default="10:00 AM")
    end_time = Column(String(20), nullable=False, default="01:00 PM")
    room_number = Column(String(50), nullable=True, default="Room 101")
    full_marks = Column(Float, nullable=False, default=100.0)
    pass_marks = Column(Float, nullable=False, default=33.0)
    theory_full = Column(Float, nullable=False, default=70.0)
    mcq_full = Column(Float, nullable=False, default=30.0)
    practical_full = Column(Float, nullable=False, default=0.0)

    exam_term = relationship("ExamTerm", back_populates="schedules")
    school_class = relationship("SchoolClass")
    subject = relationship("Subject")

    __table_args__ = (
        UniqueConstraint("exam_term_id", "class_id", "subject_id", name="uq_exam_schedule_term_class_sub"),
    )

    def __repr__(self):
        return f"<ExamSchedule(term_id={self.exam_term_id}, class_id={self.class_id}, subject_id={self.subject_id})>"


class StudentMark(Base, TimestampMixin):
    """
    Component-wise exam marks obtained by an individual student in a specific subject.
    """
    __tablename__ = "student_marks"

    id = Column(Integer, primary_key=True, index=True)
    exam_term_id = Column(Integer, ForeignKey("exam_terms.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)

    theory_marks = Column(Float, default=0.0)
    mcq_marks = Column(Float, default=0.0)
    practical_marks = Column(Float, default=0.0)
    ca_marks = Column(Float, default=0.0)  # Continuous Assessment / Assignment
    total_marks = Column(Float, nullable=False, default=0.0)
    is_absent = Column(Boolean, default=False)

    grade_name = Column(String(10), nullable=False, default="F")
    grade_point = Column(Float, nullable=False, default=0.0)
    is_passed = Column(Boolean, default=False)
    remarks = Column(String(100), nullable=True)

    exam_term = relationship("ExamTerm", back_populates="marks")
    school_class = relationship("SchoolClass")
    subject = relationship("Subject")
    student = relationship("Student")

    __table_args__ = (
        UniqueConstraint("exam_term_id", "student_id", "subject_id", name="uq_student_exam_subject_mark"),
    )

    def __repr__(self):
        return f"<StudentMark(student_id={self.student_id}, subject_id={self.subject_id}, total={self.total_marks}, grade='{self.grade_name}')>"


class ExamResultSummary(Base, TimestampMixin):
    """
    Compiled term result summary, final GPA, overall grade, and merit rank for a student.
    """
    __tablename__ = "exam_result_summaries"

    id = Column(Integer, primary_key=True, index=True)
    exam_term_id = Column(Integer, ForeignKey("exam_terms.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)

    total_obtained = Column(Float, nullable=False, default=0.0)
    total_full_marks = Column(Float, nullable=False, default=0.0)
    percentage = Column(Float, nullable=False, default=0.0)
    gpa = Column(Float, nullable=False, default=0.0)
    overall_grade = Column(String(10), nullable=False, default="F")
    class_rank = Column(Integer, nullable=True)
    passed_all = Column(Boolean, default=False)
    failed_subject_count = Column(Integer, default=0)
    remarks = Column(String(150), nullable=True)

    exam_term = relationship("ExamTerm", back_populates="summaries")
    student = relationship("Student")
    school_class = relationship("SchoolClass")

    __table_args__ = (
        UniqueConstraint("exam_term_id", "student_id", name="uq_exam_result_summary_term_student"),
    )

    def __repr__(self):
        return f"<ExamResultSummary(student_id={self.student_id}, gpa={self.gpa}, grade='{self.overall_grade}', rank={self.class_rank})>"
