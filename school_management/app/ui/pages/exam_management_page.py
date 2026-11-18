"""
EduManage Pro - Advanced Examination Management, Question Bank & Result Governance Page (PySide6)
Full enterprise examination engine workspace:
- Tab 1: Tabulation Sheet, Merit List, CGPA, Verification/Approval/Publishing Lock & Report Exports
- Tab 2: Exam Types, Terms & Schedules (with component marks & Admit Cards)
- Tab 3: Question Bank, Written Papers, MCQ Assessment & Auto-Grading
- Tab 4: Customizable Grading Systems & Configurable Grading Rules
- Tab 5: Immutable Result History & Governance Audit Trail
"""

from datetime import date
import json
from typing import Dict, List, Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database.connection import SessionLocal
from app.models.academic import AcademicYear, SchoolClass, Subject
from app.models.exam import (
    ExamPaper,
    ExamResultBatch,
    ExamResultHistory,
    ExamResultSummary,
    ExamSchedule,
    ExamTerm,
    ExamType,
    GradingSystem,
    QuestionBankItem,
    ResultWorkflowStatus,
)
from app.models.school import SchoolSetting
from app.models.student import Student
from app.reports.admit_card_pdf import AdmitCardPDFGenerator
from app.reports.exam_reports_pdf import ExamReportsPDFGenerator
from app.reports.report_card_pdf import ReportCardPDFGenerator
from app.repositories.exam_repository import ExamRepository
from app.security.session import session as app_session
from app.services.exam_service import ExamService
from app.ui.dialogs.exam_schedule_dialog import ExamScheduleDialog
from app.ui.dialogs.marks_entry_dialog import MarksEntryDialog


def _get_school_info(db) -> Dict[str, str]:
    s = db.query(SchoolSetting).first()
    return {
        "name": getattr(s, "school_name", None) or "EduManage Pro Model High School",
        "eiin": getattr(s, "eiin_number", None) or "134211",
        "phone": getattr(s, "phone", None) or "+880 1712-345678",
        "address": getattr(s, "address", None) or "Uttara, Dhaka, Bangladesh",
    }


def _actor():
    return app_session.current_user if app_session.is_authenticated else None


class ExamManagementPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh_all()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header with Title & Top Actions
        header_layout = QHBoxLayout()
        header_text = QVBoxLayout()
        h1 = QLabel("Advanced Examination Engine, Question Bank & Result Governance")
        h1.setStyleSheet("font-size: 20px; font-weight: bold; color: #3b82f6;")
        sub = QLabel(
            "Customizable grading rules, Theory/MCQ/Practical/Viva/Attendance marks, "
            "CGPA, Question Bank, verification/approval lock & audit history."
        )
        sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        header_text.addWidget(h1)
        header_text.addWidget(sub)
        header_layout.addLayout(header_text)
        header_layout.addStretch()

        self.btn_marks = QPushButton("+ Enter Marks")
        self.btn_marks.setStyleSheet(
            "background-color: #059669; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;"
        )
        self.btn_marks.clicked.connect(self._open_marks_dialog)
        header_layout.addWidget(self.btn_marks)

        self.btn_routine = QPushButton("+ Add Routine Slot")
        self.btn_routine.setStyleSheet(
            "background-color: #2563eb; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;"
        )
        self.btn_routine.clicked.connect(self._open_schedule_dialog)
        header_layout.addWidget(self.btn_routine)

        self.btn_excel = QPushButton("Tabulation Excel")
        self.btn_excel.setStyleSheet(
            "background-color: #0284c7; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;"
        )
        self.btn_excel.clicked.connect(self._export_tabulation_excel)
        header_layout.addWidget(self.btn_excel)

        self.btn_tab_pdf = QPushButton("Tabulation PDF")
        self.btn_tab_pdf.setStyleSheet(
            "background-color: #4f46e5; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;"
        )
        self.btn_tab_pdf.clicked.connect(self._export_tabulation_pdf)
        header_layout.addWidget(self.btn_tab_pdf)

        self.btn_merit_pdf = QPushButton("Merit List PDF")
        self.btn_merit_pdf.setStyleSheet(
            "background-color: #7c3aed; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;"
        )
        self.btn_merit_pdf.clicked.connect(self._export_merit_list_pdf)
        header_layout.addWidget(self.btn_merit_pdf)

        main_layout.addLayout(header_layout)

        # 2. Executive KPI Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_exams = self._create_kpi_card("Exam Terms / Types", "0", "#3b82f6")
        self.card_evaluated = self._create_kpi_card("Students Evaluated", "0", "#10b981")
        self.card_avg_gpa = self._create_kpi_card("Class Average GPA / CGPA", "0.00", "#f59e0b")
        self.card_pass_rate = self._create_kpi_card("Pass Rate / Batch Status", "0.0%", "#06b6d4")

        cards_layout.addWidget(self.card_exams)
        cards_layout.addWidget(self.card_evaluated)
        cards_layout.addWidget(self.card_avg_gpa)
        cards_layout.addWidget(self.card_pass_rate)
        main_layout.addLayout(cards_layout)

        # 3. Tabbed Views
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { font-size: 13px; font-weight: bold; padding: 8px 16px; }
            QTabBar::tab:selected { color: #3b82f6; border-bottom: 2px solid #3b82f6; }
        """)

        self.tab_tabulation = QWidget()
        self._build_tabulation_tab()
        self.tabs.addTab(self.tab_tabulation, "Tabulation, Merit & Result Governance")

        self.tab_routines = QWidget()
        self._build_routines_tab()
        self.tabs.addTab(self.tab_routines, "Exam Types, Terms & Schedules")

        self.tab_qb = QWidget()
        self._build_question_bank_tab()
        self.tabs.addTab(self.tab_qb, "Question Bank, Written & MCQ")

        self.tab_grading = QWidget()
        self._build_grading_tab()
        self.tabs.addTab(self.tab_grading, "Grading Systems & Rules")

        self.tab_history = QWidget()
        self._build_history_tab()
        self.tabs.addTab(self.tab_history, "Result History & Audit Log")

        main_layout.addWidget(self.tabs)

    def _create_kpi_card(self, title: str, val: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px 12px;
            }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: bold;")
        lbl_v = QLabel(val)
        lbl_v.setStyleSheet(f"font-size: 17px; font-weight: bold; color: {color_hex};")
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        return card

    # -------------------------------------------------------------
    # Tab 1: Tabulation Sheet, Merit List & Result Governance
    # -------------------------------------------------------------
    def _build_tabulation_tab(self):
        lay = QVBoxLayout(self.tab_tabulation)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Exam Term:"))
        self.combo_filter_term = QComboBox()
        self.combo_filter_term.currentIndexChanged.connect(self._on_term_or_class_changed)
        filter_bar.addWidget(self.combo_filter_term)

        filter_bar.addWidget(QLabel("Class:"))
        self.combo_filter_class = QComboBox()
        self.combo_filter_class.currentIndexChanged.connect(self._on_term_or_class_changed)
        filter_bar.addWidget(self.combo_filter_class)

        self.lbl_batch_status = QLabel("Workflow: Draft")
        self.lbl_batch_status.setStyleSheet(
            "background-color: #334155; color: #e2e8f0; font-weight: bold; padding: 4px 10px; border-radius: 4px;"
        )
        filter_bar.addWidget(self.lbl_batch_status)
        filter_bar.addStretch()

        self.btn_sync_att = QPushButton("Sync Attendance Marks")
        self.btn_sync_att.clicked.connect(self._sync_attendance_marks)
        filter_bar.addWidget(self.btn_sync_att)

        self.btn_compile = QPushButton("Compile GPA/CGPA")
        self.btn_compile.clicked.connect(self._recompile_results)
        filter_bar.addWidget(self.btn_compile)

        self.btn_verify = QPushButton("Verify")
        self.btn_verify.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 5px 10px;")
        self.btn_verify.clicked.connect(self._verify_results)
        filter_bar.addWidget(self.btn_verify)

        self.btn_approve = QPushButton("Approve")
        self.btn_approve.setStyleSheet("background-color: #d97706; color: white; font-weight: bold; padding: 5px 10px;")
        self.btn_approve.clicked.connect(self._approve_results)
        filter_bar.addWidget(self.btn_approve)

        self.btn_publish = QPushButton("Publish & Lock")
        self.btn_publish.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 5px 10px;")
        self.btn_publish.clicked.connect(self._publish_results)
        filter_bar.addWidget(self.btn_publish)

        self.btn_reopen = QPushButton("Reopen (Audit)")
        self.btn_reopen.setStyleSheet("background-color: #dc2626; color: white; font-weight: bold; padding: 5px 10px;")
        self.btn_reopen.clicked.connect(self._reopen_results)
        filter_bar.addWidget(self.btn_reopen)

        lay.addLayout(filter_bar)

        self.table_tabulation = QTableWidget()
        self.table_tabulation.setColumnCount(12)
        self.table_tabulation.setHorizontalHeaderLabels([
            "Class Pos", "Sec Pos", "Roll", "Student ID", "Candidate Name",
            "Obtained / Full", "Percent", "GPA", "CGPA", "Grade", "Workflow", "Actions"
        ])
        self.table_tabulation.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for c in (0, 1, 2, 3, 10, 11):
            self.table_tabulation.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.table_tabulation.setAlternatingRowColors(True)
        self.table_tabulation.setSelectionBehavior(QTableWidget.SelectRows)
        lay.addWidget(self.table_tabulation)

    # -------------------------------------------------------------
    # Tab 2: Exam Types, Terms & Schedules
    # -------------------------------------------------------------
    def _build_routines_tab(self):
        lay = QVBoxLayout(self.tab_routines)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        top_tools = QHBoxLayout()
        self.lbl_exam_types_summary = QLabel("Exam Types: Loading...")
        self.lbl_exam_types_summary.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        top_tools.addWidget(self.lbl_exam_types_summary)
        top_tools.addStretch()

        btn_new_type = QPushButton("+ Add Exam Type")
        btn_new_type.setStyleSheet("background-color: #334155; color: white; font-weight: bold; padding: 5px 10px;")
        btn_new_type.clicked.connect(self._open_new_exam_type_dialog)
        top_tools.addWidget(btn_new_type)

        btn_new_term = QPushButton("+ New Exam Term")
        btn_new_term.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 5px 10px;")
        btn_new_term.clicked.connect(self._open_new_exam_term_dialog)
        top_tools.addWidget(btn_new_term)

        lay.addLayout(top_tools)

        self.table_routines = QTableWidget()
        self.table_routines.setColumnCount(8)
        self.table_routines.setHorizontalHeaderLabels([
            "Date", "Time Slot", "Class", "Subject", "Hall / Room",
            "Component Marks (Th/MCQ/Prac/Viva/Att)", "Pass / Opt", "Actions"
        ])
        self.table_routines.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for c in (0, 1, 7):
            self.table_routines.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.table_routines.setAlternatingRowColors(True)
        lay.addWidget(self.table_routines)

    # -------------------------------------------------------------
    # Tab 3: Question Bank, Written Papers & MCQ Engine
    # -------------------------------------------------------------
    def _build_question_bank_tab(self):
        lay = QVBoxLayout(self.tab_qb)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Type Filter:"))
        self.combo_qb_type = QComboBox()
        self.combo_qb_type.addItems(["All", "MCQ", "Written", "ShortAnswer", "Practical", "Viva"])
        self.combo_qb_type.currentIndexChanged.connect(self._reload_qb_and_papers)
        bar.addWidget(self.combo_qb_type)
        bar.addStretch()

        btn_add_q = QPushButton("+ Add Question Bank Item")
        btn_add_q.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 5px 12px;")
        btn_add_q.clicked.connect(self._open_add_question_dialog)
        bar.addWidget(btn_add_q)

        btn_build_paper = QPushButton("+ Create Exam Paper (Written/MCQ)")
        btn_build_paper.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 5px 12px;")
        btn_build_paper.clicked.connect(self._open_create_paper_dialog)
        bar.addWidget(btn_build_paper)

        lay.addLayout(bar)

        lbl_q = QLabel("Question Bank Repository")
        lbl_q.setStyleSheet("font-weight: bold; color: #93c5fd;")
        lay.addWidget(lbl_q)

        self.table_qb = QTableWidget()
        self.table_qb.setColumnCount(7)
        self.table_qb.setHorizontalHeaderLabels([
            "Code", "Type", "Subject", "Topic", "Difficulty", "Marks", "Question Preview"
        ])
        self.table_qb.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for c in (0, 1, 4, 5):
            self.table_qb.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.table_qb.setAlternatingRowColors(True)
        lay.addWidget(self.table_qb)

        lbl_p = QLabel("Exam Papers (Printable Written Papers & Auto-Graded MCQ Assessments)")
        lbl_p.setStyleSheet("font-weight: bold; color: #93c5fd;")
        lay.addWidget(lbl_p)

        self.table_papers = QTableWidget()
        self.table_papers.setColumnCount(7)
        self.table_papers.setHorizontalHeaderLabels([
            "Paper Code", "Title", "Type", "Class / Subject", "Total / Pass", "Questions", "Actions"
        ])
        self.table_papers.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for c in (0, 2, 4, 5, 6):
            self.table_papers.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.table_papers.setAlternatingRowColors(True)
        lay.addWidget(self.table_papers)

    # -------------------------------------------------------------
    # Tab 4: Customizable Grading Systems & Configurable Rules
    # -------------------------------------------------------------
    def _build_grading_tab(self):
        lay = QVBoxLayout(self.tab_grading)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Grading System:"))
        self.combo_grading_system = QComboBox()
        self.combo_grading_system.currentIndexChanged.connect(self._on_grading_system_selected)
        top_bar.addWidget(self.combo_grading_system)

        self.lbl_grading_rules = QLabel("Rules: Loading...")
        self.lbl_grading_rules.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        top_bar.addWidget(self.lbl_grading_rules)
        top_bar.addStretch()

        btn_apply_to_term = QPushButton("Assign to Selected Term")
        btn_apply_to_term.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 5px 10px;")
        btn_apply_to_term.clicked.connect(self._assign_grading_to_term)
        top_bar.addWidget(btn_apply_to_term)

        btn_create_gs = QPushButton("+ Create Custom Grading System")
        btn_create_gs.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 5px 12px;")
        btn_create_gs.clicked.connect(self._open_create_grading_system_dialog)
        top_bar.addWidget(btn_create_gs)

        lay.addLayout(top_bar)

        self.table_grading = QTableWidget()
        self.table_grading.setColumnCount(6)
        self.table_grading.setHorizontalHeaderLabels([
            "Letter Grade", "Grade Point", "Mark From (%)", "Mark To (%)", "Passing Band", "Evaluative Remarks"
        ])
        self.table_grading.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_grading.setAlternatingRowColors(True)
        lay.addWidget(self.table_grading)

    # -------------------------------------------------------------
    # Tab 5: Result History & Governance Audit Trail
    # -------------------------------------------------------------
    def _build_history_tab(self):
        lay = QVBoxLayout(self.tab_history)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        top = QHBoxLayout()
        top.addWidget(QLabel("Immutable Result Governance & Audit History Log (Snapshots & Reopen Reasons)"))
        top.addStretch()
        btn_ref = QPushButton("Refresh History")
        btn_ref.clicked.connect(self._reload_history_tab)
        top.addWidget(btn_ref)
        lay.addLayout(top)

        self.table_history = QTableWidget()
        self.table_history.setColumnCount(7)
        self.table_history.setHorizontalHeaderLabels([
            "Timestamp", "Version", "Action", "Transition", "Reason / Notes", "Performed By", "Snapshot Summary"
        ])
        self.table_history.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for c in (0, 1, 2, 5):
            self.table_history.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.table_history.setAlternatingRowColors(True)
        lay.addWidget(self.table_history)

    # -------------------------------------------------------------
    # Data Loading & Refresh
    # -------------------------------------------------------------
    def refresh_all(self):
        db = SessionLocal()
        try:
            ExamService.seed_default_grading_scale(db)
            ExamService.seed_default_exam_types(db)
            ExamService.seed_default_grading_system(db)
            self._ensure_default_exam(db)

            total_terms = db.query(ExamTerm).filter(ExamTerm.is_deleted == False).count()
            total_types = db.query(ExamType).filter(ExamType.is_deleted == False).count()
            self.card_exams.findChildren(QLabel)[1].setText(f"{total_terms} Terms / {total_types} Types")

            # Populate Terms
            curr_term = self.combo_filter_term.currentData()
            self.combo_filter_term.blockSignals(True)
            self.combo_filter_term.clear()
            for t in ExamRepository.get_all_exam_terms(db):
                et_tag = f" [{t.exam_type.code}]" if t.exam_type else ""
                self.combo_filter_term.addItem(f"{t.name}{et_tag}", t.id)
            if curr_term:
                idx = self.combo_filter_term.findData(curr_term)
                if idx >= 0:
                    self.combo_filter_term.setCurrentIndex(idx)
            self.combo_filter_term.blockSignals(False)

            # Populate Classes
            curr_cls = self.combo_filter_class.currentData()
            self.combo_filter_class.blockSignals(True)
            self.combo_filter_class.clear()
            for c in db.query(SchoolClass).order_by(SchoolClass.numeric_order.asc()).all():
                self.combo_filter_class.addItem(c.name, c.id)
            if curr_cls:
                idx = self.combo_filter_class.findData(curr_cls)
                if idx >= 0:
                    self.combo_filter_class.setCurrentIndex(idx)
            self.combo_filter_class.blockSignals(False)

            # Populate ExamTypes label
            etypes = ExamRepository.get_all_exam_types(db)
            self.lbl_exam_types_summary.setText(
                "Exam Types: " + " | ".join(f"{e.code} ({e.default_weight_pct:.0f}%)" for e in etypes)
            )

            # Populate Grading Systems Combo
            curr_gs = self.combo_grading_system.currentData()
            self.combo_grading_system.blockSignals(True)
            self.combo_grading_system.clear()
            for gs in ExamRepository.get_all_grading_systems(db):
                tag = " [Default]" if gs.is_default else ""
                self.combo_grading_system.addItem(f"{gs.name} ({gs.code}){tag}", gs.id)
            if curr_gs:
                idx = self.combo_grading_system.findData(curr_gs)
                if idx >= 0:
                    self.combo_grading_system.setCurrentIndex(idx)
            self.combo_grading_system.blockSignals(False)

            self._load_tabulation_data()
            self._load_routines(db)
            self._load_grading_scale_rows(db)
            self._load_qb_and_papers(db)
            self._load_history_rows(db)
        finally:
            db.close()

    def _ensure_default_exam(self, db):
        if db.query(ExamTerm).count() == 0:
            ay = db.query(AcademicYear).filter(AcademicYear.is_current == True).first() or db.query(AcademicYear).first()
            if not ay:
                return
            ann_type = db.query(ExamType).filter(ExamType.code == "ANN").first()
            def_gs = ExamRepository.get_default_grading_system(db)
            ExamRepository.create_exam_term(
                db,
                {
                    "name": "Annual Examination 2026",
                    "exam_code": "EXM-2026-ANN",
                    "academic_year_id": ay.id,
                    "exam_type_id": ann_type.id if ann_type else None,
                    "grading_system_id": def_gs.id if def_gs else None,
                    "start_date": date(2026, 11, 15),
                    "end_date": date(2026, 11, 30),
                    "status": "Scheduled",
                    "description": "Final comprehensive academic term examination",
                },
            )

    def _on_term_or_class_changed(self):
        self._load_tabulation_data()
        db = SessionLocal()
        try:
            self._load_routines(db)
            self._load_history_rows(db)
        finally:
            db.close()

    def _load_tabulation_data(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        if not term_id or not class_id:
            return

        db = SessionLocal()
        try:
            batch = ExamRepository.get_result_batch(db, term_id, class_id)
            summaries = ExamRepository.get_class_result_summaries(db, term_id, class_id)
            if not summaries and not (batch and batch.is_published):
                try:
                    ExamService.compile_class_results(db, term_id, class_id, actor_user=_actor())
                    summaries = ExamRepository.get_class_result_summaries(db, term_id, class_id)
                    batch = ExamRepository.get_result_batch(db, term_id, class_id)
                except PermissionError:
                    pass

            batch_status = batch.status if batch else ResultWorkflowStatus.DRAFT
            version_no = batch.version_no if batch else 1
            is_pub = bool(batch and batch.is_published)
            lock_suffix = " [LOCKED]" if is_pub else ""
            self.lbl_batch_status.setText(f"Status: {batch_status} (v{version_no}){lock_suffix}")
            if is_pub:
                self.lbl_batch_status.setStyleSheet(
                    "background-color: #065f46; color: #ecfdf5; font-weight: bold; padding: 4px 10px; border-radius: 4px;"
                )
            elif batch_status == ResultWorkflowStatus.APPROVED:
                self.lbl_batch_status.setStyleSheet(
                    "background-color: #92400e; color: #fef3c7; font-weight: bold; padding: 4px 10px; border-radius: 4px;"
                )
            elif batch_status == ResultWorkflowStatus.VERIFIED:
                self.lbl_batch_status.setStyleSheet(
                    "background-color: #1e40af; color: #dbeafe; font-weight: bold; padding: 4px 10px; border-radius: 4px;"
                )
            else:
                self.lbl_batch_status.setStyleSheet(
                    "background-color: #334155; color: #e2e8f0; font-weight: bold; padding: 4px 10px; border-radius: 4px;"
                )

            self.table_tabulation.setRowCount(len(summaries))
            total_gpa = 0.0
            total_cgpa = 0.0
            passed_count = 0

            for row, res in enumerate(summaries):
                stu = res.student
                rank_item = QTableWidgetItem(f"#{res.class_rank}" if res.class_rank else "—")
                rank_item.setFont(QFont("Helvetica", 9, QFont.Bold))
                if res.class_rank == 1:
                    rank_item.setForeground(QColor("#f59e0b"))
                self.table_tabulation.setItem(row, 0, rank_item)
                self.table_tabulation.setItem(
                    row, 1, QTableWidgetItem(f"#{res.section_rank}" if res.section_rank else "—")
                )
                self.table_tabulation.setItem(row, 2, QTableWidgetItem(str(stu.roll_number if stu else "-")))
                self.table_tabulation.setItem(row, 3, QTableWidgetItem(stu.student_id if stu else "-"))
                self.table_tabulation.setItem(row, 4, QTableWidgetItem(stu.full_name if stu else "Unknown"))
                self.table_tabulation.setItem(
                    row, 5, QTableWidgetItem(f"{res.total_obtained:.1f} / {res.total_full_marks:.0f}")
                )
                self.table_tabulation.setItem(row, 6, QTableWidgetItem(f"{res.percentage:.1f}%"))

                gpa_item = QTableWidgetItem(f"{res.gpa:.2f}")
                gpa_item.setFont(QFont("Helvetica", 9, QFont.Bold))
                gpa_item.setForeground(QColor("#10b981") if res.passed_all else QColor("#ef4444"))
                self.table_tabulation.setItem(row, 7, gpa_item)

                cgpa_val = float(res.cgpa if res.cgpa is not None else res.gpa)
                self.table_tabulation.setItem(row, 8, QTableWidgetItem(f"{cgpa_val:.2f}"))

                grd_item = QTableWidgetItem(res.overall_grade)
                grd_item.setFont(QFont("Helvetica", 9, QFont.Bold))
                self.table_tabulation.setItem(row, 9, grd_item)
                self.table_tabulation.setItem(row, 10, QTableWidgetItem(res.result_status))

                act_widget = QWidget()
                act_lay = QHBoxLayout(act_widget)
                act_lay.setContentsMargins(2, 2, 2, 2)
                act_lay.setSpacing(4)

                btn_ms = QPushButton("Mark Sheet")
                btn_ms.setStyleSheet("background-color: #1e3a8a; color: white; padding: 3px 6px; font-size: 11px;")
                btn_ms.clicked.connect(lambda _, s_id=res.student_id: self._print_student_mark_sheet(s_id))
                act_lay.addWidget(btn_ms)

                btn_rc = QPushButton("Report Card")
                btn_rc.setStyleSheet("background-color: #334155; color: white; padding: 3px 6px; font-size: 11px;")
                btn_rc.clicked.connect(lambda _, s_id=res.student_id: self._print_student_report_card(s_id))
                act_lay.addWidget(btn_rc)

                self.table_tabulation.setCellWidget(row, 11, act_widget)

                total_gpa += res.gpa
                total_cgpa += cgpa_val
                if res.passed_all:
                    passed_count += 1

            evaluated = len(summaries)
            self.card_evaluated.findChildren(QLabel)[1].setText(str(evaluated))
            avg_gpa = (total_gpa / evaluated) if evaluated > 0 else 0.0
            avg_cgpa = (total_cgpa / evaluated) if evaluated > 0 else 0.0
            self.card_avg_gpa.findChildren(QLabel)[1].setText(f"{avg_gpa:.2f} / {avg_cgpa:.2f}")
            pass_rate = (passed_count / evaluated * 100.0) if evaluated > 0 else 0.0
            self.card_pass_rate.findChildren(QLabel)[1].setText(f"{pass_rate:.1f}% ({batch_status})")
        finally:
            db.close()

    def _load_routines(self, db):
        term_id = self.combo_filter_term.currentData()
        if not term_id:
            return
        schedules = ExamRepository.get_schedules_by_term(db, term_id)
        self.table_routines.setRowCount(len(schedules))
        for row, sc in enumerate(schedules):
            self.table_routines.setItem(row, 0, QTableWidgetItem(str(sc.exam_date)))
            self.table_routines.setItem(row, 1, QTableWidgetItem(f"{sc.start_time} - {sc.end_time}"))
            self.table_routines.setItem(row, 2, QTableWidgetItem(sc.school_class.name if sc.school_class else "-"))
            self.table_routines.setItem(row, 3, QTableWidgetItem(sc.subject.name if sc.subject else "-"))
            self.table_routines.setItem(row, 4, QTableWidgetItem(sc.room_number or "-"))
            comp = (
                f"{sc.full_marks:g} (Th:{sc.theory_full:g}, MCQ:{sc.mcq_full:g}, "
                f"Pr:{sc.practical_full:g}, V:{sc.viva_full:g}, Att:{sc.attendance_full:g})"
            )
            self.table_routines.setItem(row, 5, QTableWidgetItem(comp))
            flags = f"Pass {sc.pass_marks:g}"
            if sc.require_component_pass:
                flags += " | Comp"
            if sc.is_optional_eligible:
                flags += " | Opt"
            self.table_routines.setItem(row, 6, QTableWidgetItem(flags))

            btn_admit = QPushButton("Print Admit Card")
            btn_admit.setStyleSheet("background-color: #334155; color: white; padding: 4px 8px; font-size: 11px;")
            btn_admit.clicked.connect(lambda _, c_id=sc.class_id: self._print_class_admit_card(c_id))
            self.table_routines.setCellWidget(row, 7, btn_admit)

    def _on_grading_system_selected(self):
        db = SessionLocal()
        try:
            self._load_grading_scale_rows(db)
        finally:
            db.close()

    def _load_grading_scale_rows(self, db):
        gs_id = self.combo_grading_system.currentData()
        gs = ExamRepository.get_grading_system_by_id(db, gs_id) if gs_id else ExamRepository.get_default_grading_system(db)
        if gs and gs.rules:
            self.lbl_grading_rules.setText(
                f"Max GPA: {gs.max_gpa:g} | Pass: {gs.pass_percentage:g}% | "
                f"ComponentPass: {'Yes' if gs.require_component_pass else 'No'} | "
                f"Grace Limit: {gs.grace_marks_limit:g} | Optional Bonus: {'Yes' if gs.optional_subject_enabled else 'No'} | "
                f"CGPA: {gs.cgpa_mode}"
            )
            self.table_grading.setRowCount(len(gs.rules))
            for row, r in enumerate(gs.rules):
                g_item = QTableWidgetItem(r.grade_name)
                g_item.setFont(QFont("Helvetica", 10, QFont.Bold))
                g_item.setForeground(QColor("#10b981") if r.is_passing else QColor("#ef4444"))
                self.table_grading.setItem(row, 0, g_item)
                self.table_grading.setItem(row, 1, QTableWidgetItem(f"{r.grade_point:.2f}"))
                self.table_grading.setItem(row, 2, QTableWidgetItem(f"{r.mark_from:g}%"))
                self.table_grading.setItem(row, 3, QTableWidgetItem(f"{r.mark_to:g}%"))
                self.table_grading.setItem(row, 4, QTableWidgetItem("Pass" if r.is_passing else "Fail"))
                self.table_grading.setItem(row, 5, QTableWidgetItem(r.remarks))
            return

        scales = ExamRepository.get_grading_scales(db)
        self.table_grading.setRowCount(len(scales))
        for row, sc in enumerate(scales):
            self.table_grading.setItem(row, 0, QTableWidgetItem(sc.grade_name))
            self.table_grading.setItem(row, 1, QTableWidgetItem(f"{sc.grade_point:.2f}"))
            self.table_grading.setItem(row, 2, QTableWidgetItem(f"{sc.mark_from:.0f}%"))
            self.table_grading.setItem(row, 3, QTableWidgetItem(f"{sc.mark_to:.0f}%"))
            self.table_grading.setItem(row, 4, QTableWidgetItem("Fail" if sc.grade_name == "F" else "Pass"))
            self.table_grading.setItem(row, 5, QTableWidgetItem(sc.remarks))

    def _reload_qb_and_papers(self):
        db = SessionLocal()
        try:
            self._load_qb_and_papers(db)
        finally:
            db.close()

    def _load_qb_and_papers(self, db):
        q_type = self.combo_qb_type.currentText()
        questions = ExamRepository.list_questions(db, question_type=q_type)
        self.table_qb.setRowCount(len(questions))
        for row, q in enumerate(questions):
            self.table_qb.setItem(row, 0, QTableWidgetItem(q.question_code))
            self.table_qb.setItem(row, 1, QTableWidgetItem(q.question_type))
            self.table_qb.setItem(row, 2, QTableWidgetItem(q.subject.name if q.subject else "-"))
            self.table_qb.setItem(row, 3, QTableWidgetItem(q.topic or "-"))
            self.table_qb.setItem(row, 4, QTableWidgetItem(q.difficulty))
            self.table_qb.setItem(row, 5, QTableWidgetItem(f"{q.marks:g}"))
            self.table_qb.setItem(row, 6, QTableWidgetItem(q.question_text[:95]))

        papers = ExamRepository.list_exam_papers(db)
        self.table_papers.setRowCount(len(papers))
        for row, p in enumerate(papers):
            self.table_papers.setItem(row, 0, QTableWidgetItem(p.paper_code))
            self.table_papers.setItem(row, 1, QTableWidgetItem(p.title))
            self.table_papers.setItem(row, 2, QTableWidgetItem(p.paper_type))
            cs_label = f"{p.school_class.name if p.school_class else '-'} / {p.subject.name if p.subject else '-'}"
            self.table_papers.setItem(row, 3, QTableWidgetItem(cs_label))
            self.table_papers.setItem(row, 4, QTableWidgetItem(f"{p.total_marks:g} / {p.pass_marks:g}"))
            self.table_papers.setItem(row, 5, QTableWidgetItem(str(len(p.questions))))

            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(2, 2, 2, 2)
            hl.setSpacing(4)

            b_pdf = QPushButton("Paper PDF")
            b_pdf.setStyleSheet("background-color: #334155; color: white; padding: 3px 6px; font-size: 11px;")
            b_pdf.clicked.connect(lambda _, pid=p.id: self._export_question_paper_pdf(pid, False))
            hl.addWidget(b_pdf)

            b_key = QPushButton("Key PDF")
            b_key.setStyleSheet("background-color: #1e3a8a; color: white; padding: 3px 6px; font-size: 11px;")
            b_key.clicked.connect(lambda _, pid=p.id: self._export_question_paper_pdf(pid, True))
            hl.addWidget(b_key)

            if p.paper_type in ("MCQ", "Combined"):
                b_mcq = QPushButton("Grade MCQ")
                b_mcq.setStyleSheet("background-color: #059669; color: white; padding: 3px 6px; font-size: 11px;")
                b_mcq.clicked.connect(lambda _, pid=p.id: self._open_mcq_attempt_dialog(pid))
                hl.addWidget(b_mcq)

            self.table_papers.setCellWidget(row, 6, w)

    def _reload_history_tab(self):
        db = SessionLocal()
        try:
            self._load_history_rows(db)
        finally:
            db.close()

    def _load_history_rows(self, db):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        history = ExamRepository.list_result_history(db, exam_term_id=term_id, class_id=class_id)
        self.table_history.setRowCount(len(history))
        for row, h in enumerate(history):
            ts_str = h.performed_at.strftime("%Y-%m-%d %H:%M") if h.performed_at else "-"
            self.table_history.setItem(row, 0, QTableWidgetItem(ts_str))
            self.table_history.setItem(row, 1, QTableWidgetItem(f"v{h.version_no}"))
            self.table_history.setItem(row, 2, QTableWidgetItem(h.action))
            trans = f"{h.previous_status or '-'} -> {h.new_status or '-'}"
            self.table_history.setItem(row, 3, QTableWidgetItem(trans))
            self.table_history.setItem(row, 4, QTableWidgetItem(h.reason or "-"))
            self.table_history.setItem(row, 5, QTableWidgetItem(h.performed_by))
            self.table_history.setItem(row, 6, QTableWidgetItem((h.snapshot_json or "-")[:100]))

    # -------------------------------------------------------------
    # Workflow Governance Actions (Compile / Verify / Approve / Publish / Reopen)
    # -------------------------------------------------------------
    def _sync_attendance_marks(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        if not term_id or not class_id:
            return
        db = SessionLocal()
        try:
            cnt = ExamService.sync_attendance_marks_for_term(db, term_id, class_id, actor_user=_actor())
            QMessageBox.information(self, "Attendance Sync", f"Updated attendance marks for {cnt} student entries.")
            self._load_tabulation_data()
        except PermissionError as exc:
            QMessageBox.warning(self, "Access Denied / Published Lock", str(exc))
        finally:
            db.close()

    def _recompile_results(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        if not term_id or not class_id:
            return
        db = SessionLocal()
        try:
            ExamService.compile_class_results(db, term_id, class_id, actor_user=_actor())
            QMessageBox.information(self, "Compilation Finished", "GPAs, CGPA, and Class/Section rankings updated.")
            self._load_tabulation_data()
            self._load_history_rows(db)
        except PermissionError as exc:
            QMessageBox.warning(self, "Published Lock / Access Denied", str(exc))
        finally:
            db.close()

    def _verify_results(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        if not term_id or not class_id:
            return
        db = SessionLocal()
        try:
            ok, _, msg = ExamService.verify_class_results(db, term_id, class_id, actor_user=_actor())
            if ok:
                QMessageBox.information(self, "Verified", msg)
            else:
                QMessageBox.warning(self, "Verification", msg)
            self._load_tabulation_data()
            self._load_history_rows(db)
        except PermissionError as exc:
            QMessageBox.warning(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _approve_results(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        if not term_id or not class_id:
            return
        db = SessionLocal()
        try:
            ok, _, msg = ExamService.approve_class_results(db, term_id, class_id, actor_user=_actor())
            if ok:
                QMessageBox.information(self, "Approved", msg)
            else:
                QMessageBox.warning(self, "Approval", msg)
            self._load_tabulation_data()
            self._load_history_rows(db)
        except PermissionError as exc:
            QMessageBox.warning(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _publish_results(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        if not term_id or not class_id:
            return
        db = SessionLocal()
        try:
            ok, _, msg = ExamService.publish_class_results(db, term_id, class_id, actor_user=_actor())
            if ok:
                QMessageBox.information(self, "Published & Locked", msg)
            else:
                QMessageBox.warning(self, "Publish Blocked", msg)
            self._load_tabulation_data()
            self._load_history_rows(db)
        except PermissionError as exc:
            QMessageBox.warning(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _reopen_results(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        if not term_id or not class_id:
            return
        reason, accepted = QInputDialog.getText(
            self,
            "Audit Reason Required — Reopen Published Result",
            "Enter mandatory audit reason to unlock published results for correction:",
        )
        if not accepted or not reason.strip():
            return
        db = SessionLocal()
        try:
            ok, _, msg = ExamService.reopen_published_results(
                db, term_id, class_id, reason=reason.strip(), actor_user=_actor()
            )
            if ok:
                QMessageBox.information(self, "Results Reopened", msg)
            else:
                QMessageBox.warning(self, "Reopen", msg)
            self._load_tabulation_data()
            self._load_history_rows(db)
        except PermissionError as exc:
            QMessageBox.warning(self, "Access Denied", str(exc))
        finally:
            db.close()

    # -------------------------------------------------------------
    # Dialogs & Creation Helpers
    # -------------------------------------------------------------
    def _open_marks_dialog(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        dialog = MarksEntryDialog(self, default_term_id=term_id, default_class_id=class_id)
        if dialog.exec():
            self._load_tabulation_data()
            db = SessionLocal()
            try:
                self._load_history_rows(db)
            finally:
                db.close()

    def _open_schedule_dialog(self):
        term_id = self.combo_filter_term.currentData()
        dialog = ExamScheduleDialog(self, default_term_id=term_id)
        if dialog.exec():
            db = SessionLocal()
            try:
                self._load_routines(db)
            finally:
                db.close()

    def _open_new_exam_type_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Create Configurable Exam Type")
        form = QFormLayout(dlg)
        ed_name = QLineEdit()
        ed_code = QLineEdit()
        cb_cat = QComboBox()
        cb_cat.addItems(["Summative", "Formative", "Practical", "MCQ"])
        sp_wt = QDoubleSpinBox()
        sp_wt.setRange(0, 100)
        sp_wt.setValue(25)
        chk_cgpa = QCheckBox("Counts Toward CGPA")
        chk_cgpa.setChecked(True)

        form.addRow("Name *:", ed_name)
        form.addRow("Code *:", ed_code)
        form.addRow("Category:", cb_cat)
        form.addRow("CGPA Weight %:", sp_wt)
        form.addRow("", chk_cgpa)

        btns = QHBoxLayout()
        b_save = QPushButton("Save Exam Type")
        btns.addWidget(b_save)
        form.addRow(btns)

        def _save():
            if not ed_name.text().strip() or not ed_code.text().strip():
                QMessageBox.warning(dlg, "Validation", "Name and Code are required.")
                return
            db = SessionLocal()
            try:
                ExamRepository.create_exam_type(
                    db,
                    {
                        "name": ed_name.text().strip(),
                        "code": ed_code.text().strip().upper(),
                        "category": cb_cat.currentText(),
                        "default_weight_pct": sp_wt.value(),
                        "counts_for_cgpa": chk_cgpa.isChecked(),
                    },
                )
                dlg.accept()
            except Exception as exc:
                QMessageBox.warning(dlg, "Error", str(exc))
            finally:
                db.close()

        b_save.clicked.connect(_save)
        if dlg.exec():
            self.refresh_all()

    def _open_new_exam_term_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Create Exam Term")
        form = QFormLayout(dlg)
        ed_name = QLineEdit()
        ed_code = QLineEdit()
        cb_type = QComboBox()
        cb_gs = QComboBox()
        dt_start = QDateEdit(QDate.currentDate())
        dt_start.setCalendarPopup(True)
        dt_end = QDateEdit(QDate.currentDate().addDays(10))
        dt_end.setCalendarPopup(True)

        db = SessionLocal()
        try:
            for et in ExamRepository.get_all_exam_types(db):
                cb_type.addItem(f"{et.name} ({et.code})", et.id)
            for gs in ExamRepository.get_all_grading_systems(db):
                cb_gs.addItem(f"{gs.name} ({gs.code})", gs.id)
        finally:
            db.close()

        form.addRow("Term Name *:", ed_name)
        form.addRow("Exam Code *:", ed_code)
        form.addRow("Exam Type:", cb_type)
        form.addRow("Grading System:", cb_gs)
        form.addRow("Start Date:", dt_start)
        form.addRow("End Date:", dt_end)

        b_save = QPushButton("Create Term")
        form.addRow(b_save)

        def _save():
            if not ed_name.text().strip() or not ed_code.text().strip():
                QMessageBox.warning(dlg, "Validation", "Name and Code are required.")
                return
            db_s = SessionLocal()
            try:
                ay = db_s.query(AcademicYear).filter(AcademicYear.is_current == True).first() or db_s.query(AcademicYear).first()
                s_q, e_q = dt_start.date(), dt_end.date()
                ExamRepository.create_exam_term(
                    db_s,
                    {
                        "name": ed_name.text().strip(),
                        "exam_code": ed_code.text().strip().upper(),
                        "academic_year_id": ay.id,
                        "exam_type_id": cb_type.currentData(),
                        "grading_system_id": cb_gs.currentData(),
                        "start_date": date(s_q.year(), s_q.month(), s_q.day()),
                        "end_date": date(e_q.year(), e_q.month(), e_q.day()),
                    },
                )
                dlg.accept()
            except Exception as exc:
                QMessageBox.warning(dlg, "Error", str(exc))
            finally:
                db_s.close()

        b_save.clicked.connect(_save)
        if dlg.exec():
            self.refresh_all()

    def _open_add_question_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Question Bank Item")
        dlg.setMinimumWidth(500)
        form = QFormLayout(dlg)

        cb_sub = QComboBox()
        cb_cls = QComboBox()
        db = SessionLocal()
        try:
            for c in db.query(SchoolClass).order_by(SchoolClass.numeric_order.asc()).all():
                cb_cls.addItem(c.name, c.id)
            for s in db.query(Subject).all():
                cb_sub.addItem(f"{s.name} ({s.code})", s.id)
        finally:
            db.close()

        cb_type = QComboBox()
        cb_type.addItems(["MCQ", "Written", "ShortAnswer", "Practical", "Viva"])
        cb_diff = QComboBox()
        cb_diff.addItems(["Easy", "Medium", "Hard"])
        ed_topic = QLineEdit()
        ed_text = QTextEdit()
        ed_text.setMaximumHeight(70)
        ed_opts = QLineEdit('{"A": "", "B": "", "C": "", "D": ""}')
        ed_ans = QLineEdit("A")
        sp_marks = QDoubleSpinBox()
        sp_marks.setRange(0.5, 100.0)
        sp_marks.setValue(1.0)
        sp_neg = QDoubleSpinBox()
        sp_neg.setRange(0.0, 10.0)
        sp_neg.setValue(0.25)

        form.addRow("Class:", cb_cls)
        form.addRow("Subject *:", cb_sub)
        form.addRow("Question Type:", cb_type)
        form.addRow("Difficulty:", cb_diff)
        form.addRow("Topic:", ed_topic)
        form.addRow("Question Text *:", ed_text)
        form.addRow("Options JSON (MCQ):", ed_opts)
        form.addRow("Correct Opt / Model Ans:", ed_ans)
        form.addRow("Marks:", sp_marks)
        form.addRow("Negative Marks:", sp_neg)

        b_save = QPushButton("Add Question")
        form.addRow(b_save)

        def _save():
            if not cb_sub.currentData() or not ed_text.toPlainText().strip():
                QMessageBox.warning(dlg, "Validation", "Subject and Question Text are required.")
                return
            db_s = SessionLocal()
            try:
                is_mcq = cb_type.currentText() == "MCQ"
                ok, _, msg = ExamService.add_question(
                    db_s,
                    {
                        "class_id": cb_cls.currentData(),
                        "subject_id": cb_sub.currentData(),
                        "question_type": cb_type.currentText(),
                        "difficulty": cb_diff.currentText(),
                        "topic": ed_topic.text().strip() or None,
                        "question_text": ed_text.toPlainText().strip(),
                        "options_json": ed_opts.text().strip() if is_mcq else None,
                        "correct_option": ed_ans.text().strip() if is_mcq else None,
                        "model_answer": None if is_mcq else ed_ans.text().strip(),
                        "marks": sp_marks.value(),
                        "negative_marks": sp_neg.value() if is_mcq else 0.0,
                    },
                    actor_user=_actor(),
                )
                if not ok:
                    QMessageBox.warning(dlg, "Error", msg)
                    return
                dlg.accept()
            except PermissionError as exc:
                QMessageBox.warning(dlg, "Access Denied", str(exc))
            finally:
                db_s.close()

        b_save.clicked.connect(_save)
        if dlg.exec():
            self._reload_qb_and_papers()

    def _open_create_paper_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Build Written / MCQ Exam Paper from Question Bank")
        dlg.setMinimumWidth(560)
        lay = QVBoxLayout(dlg)
        form = QFormLayout()

        ed_title = QLineEdit()
        cb_type = QComboBox()
        cb_type.addItems(["Written", "MCQ", "Combined"])
        cb_cls = QComboBox()
        cb_sub = QComboBox()
        sp_dur = QSpinBox()
        sp_dur.setRange(5, 300)
        sp_dur.setValue(60)
        chk_neg = QCheckBox("Enable Negative Marking for MCQ")
        ed_inst = QLineEdit("Answer all questions neatly.")

        lst_q = QListWidget()

        db = SessionLocal()
        try:
            for c in db.query(SchoolClass).order_by(SchoolClass.numeric_order.asc()).all():
                cb_cls.addItem(c.name, c.id)
            for s in db.query(Subject).all():
                cb_sub.addItem(f"{s.name} ({s.code})", s.id)
            for q in ExamRepository.list_questions(db):
                it = QListWidgetItem(f"[{q.question_type} | {q.marks:g}m] {q.question_code}: {q.question_text[:65]}")
                it.setData(Qt.UserRole, (q.id, q.marks))
                it.setCheckState(Qt.Unchecked)
                lst_q.addItem(it)
        finally:
            db.close()

        form.addRow("Paper Title *:", ed_title)
        form.addRow("Paper Type:", cb_type)
        form.addRow("Class *:", cb_cls)
        form.addRow("Subject *:", cb_sub)
        form.addRow("Duration (mins):", sp_dur)
        form.addRow("Instructions:", ed_inst)
        form.addRow("", chk_neg)
        lay.addLayout(form)
        lay.addWidget(QLabel("Select Questions from Bank:"))
        lay.addWidget(lst_q)

        b_save = QPushButton("Create Exam Paper")
        lay.addWidget(b_save)

        def _save():
            if not ed_title.text().strip() or not cb_cls.currentData() or not cb_sub.currentData():
                QMessageBox.warning(dlg, "Validation", "Title, Class, and Subject are required.")
                return
            entries = []
            for i in range(lst_q.count()):
                it = lst_q.item(i)
                if it.checkState() == Qt.Checked:
                    qid, qm = it.data(Qt.UserRole)
                    entries.append({"question_id": qid, "marks": qm, "order_no": len(entries) + 1})

            db_s = SessionLocal()
            try:
                ok, _, msg = ExamService.create_exam_paper(
                    db_s,
                    {
                        "title": ed_title.text().strip(),
                        "paper_type": cb_type.currentText(),
                        "exam_term_id": self.combo_filter_term.currentData(),
                        "class_id": cb_cls.currentData(),
                        "subject_id": cb_sub.currentData(),
                        "duration_minutes": sp_dur.value(),
                        "negative_marking": chk_neg.isChecked(),
                        "instructions": ed_inst.text().strip(),
                    },
                    question_entries=entries,
                    actor_user=_actor(),
                )
                if not ok:
                    QMessageBox.warning(dlg, "Error", msg)
                    return
                dlg.accept()
            except PermissionError as exc:
                QMessageBox.warning(dlg, "Access Denied", str(exc))
            finally:
                db_s.close()

        b_save.clicked.connect(_save)
        if dlg.exec():
            self._reload_qb_and_papers()

    def _open_mcq_attempt_dialog(self, paper_id: int):
        db = SessionLocal()
        try:
            paper = ExamRepository.get_exam_paper_by_id(db, paper_id)
            if not paper:
                return
            mcq_qs = [pq for pq in paper.questions if pq.question.question_type == "MCQ"]
            if not mcq_qs:
                QMessageBox.information(self, "MCQ Paper", "This paper contains no MCQ questions.")
                return
            students = (
                db.query(Student)
                .filter(Student.class_id == paper.class_id, Student.status == "Active")
                .order_by(Student.roll_number.asc())
                .all()
            )
            if not students:
                QMessageBox.warning(self, "No Students", "No active students in this class.")
                return
        finally:
            db.close()

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Auto-Grade MCQ Submission — {paper.title}")
        dlg.setMinimumWidth(520)
        lay = QVBoxLayout(dlg)
        cb_stu = QComboBox()
        for s in students:
            cb_stu.addItem(f"Roll {s.roll_number}: {s.full_name} ({s.student_id})", s.id)
        lay.addWidget(QLabel("Candidate:"))
        lay.addWidget(cb_stu)

        ans_widgets: Dict[int, QLineEdit] = {}
        form = QFormLayout()
        for idx, pq in enumerate(mcq_qs, 1):
            ed = QLineEdit()
            ed.setPlaceholderText("A / B / C / D (leave blank if unanswered)")
            ans_widgets[pq.question_id] = ed
            form.addRow(f"Q{idx} ({pq.marks:g}m):", ed)
        lay.addLayout(form)

        b_sub = QPushButton("Submit & Auto-Grade (Syncs to Marks Register)")
        b_sub.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px;")
        lay.addWidget(b_sub)

        def _submit():
            ans_map = {qid: w.text().strip().upper() or None for qid, w in ans_widgets.items()}
            db_s = SessionLocal()
            try:
                ok, _, msg = ExamService.submit_mcq_attempt(
                    db_s, paper_id, cb_stu.currentData(), ans_map, auto_sync_to_marks=True, actor_user=_actor()
                )
                if ok:
                    QMessageBox.information(dlg, "MCQ Graded", msg)
                    dlg.accept()
                else:
                    QMessageBox.warning(dlg, "Submission Info", msg)
            except PermissionError as exc:
                QMessageBox.warning(dlg, "Published Lock / Access Denied", str(exc))
            finally:
                db_s.close()

        b_sub.clicked.connect(_submit)
        if dlg.exec():
            self._load_tabulation_data()

    def _open_create_grading_system_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Create Customizable Grading System & Rules")
        dlg.setMinimumWidth(520)
        form = QFormLayout(dlg)

        ed_name = QLineEdit("Custom Mastery Scale")
        ed_code = QLineEdit()
        sp_max_gpa = QDoubleSpinBox()
        sp_max_gpa.setRange(1.0, 10.0)
        sp_max_gpa.setValue(4.0)
        sp_pass = QDoubleSpinBox()
        sp_pass.setRange(0.0, 90.0)
        sp_pass.setValue(40.0)
        sp_grace = QDoubleSpinBox()
        sp_grace.setRange(0.0, 15.0)
        sp_grace.setValue(3.0)
        chk_comp = QCheckBox("Require Component-wise Pass")
        chk_opt = QCheckBox("Enable Optional Subject Bonus")
        chk_opt.setChecked(True)
        cb_cgpa = QComboBox()
        cb_cgpa.addItems(["WeightedTerms", "EqualAverage"])

        form.addRow("System Name *:", ed_name)
        form.addRow("Unique Code *:", ed_code)
        form.addRow("Max GPA:", sp_max_gpa)
        form.addRow("Pass % Threshold:", sp_pass)
        form.addRow("Auto Grace Marks Limit:", sp_grace)
        form.addRow("CGPA Aggregation Mode:", cb_cgpa)
        form.addRow("", chk_comp)
        form.addRow("", chk_opt)

        b_save = QPushButton("Create Grading System")
        form.addRow(b_save)

        def _save():
            code = ed_code.text().strip().upper()
            if not ed_name.text().strip() or not code:
                QMessageBox.warning(dlg, "Validation", "Name and Code are required.")
                return
            mg = sp_max_gpa.value()
            p_pct = sp_pass.value()
            bands = [
                {"grade_name": "A+", "grade_point": round(mg, 2), "mark_from": 85.0, "mark_to": 100.0, "is_passing": True, "remarks": "Distinction"},
                {"grade_name": "A", "grade_point": round(mg * 0.85, 2), "mark_from": 70.0, "mark_to": 84.99, "is_passing": True, "remarks": "Very Good"},
                {"grade_name": "B", "grade_point": round(mg * 0.70, 2), "mark_from": 55.0, "mark_to": 69.99, "is_passing": True, "remarks": "Good"},
                {"grade_name": "C", "grade_point": round(mg * 0.50, 2), "mark_from": p_pct, "mark_to": 54.99, "is_passing": True, "remarks": "Pass"},
                {"grade_name": "F", "grade_point": 0.0, "mark_from": 0.0, "mark_to": max(0.0, p_pct - 0.01), "is_passing": False, "remarks": "Fail"},
            ]
            db_s = SessionLocal()
            try:
                ok, _, msg = ExamService.create_grading_system(
                    db_s,
                    {
                        "name": ed_name.text().strip(),
                        "code": code,
                        "max_gpa": mg,
                        "pass_percentage": p_pct,
                        "grace_marks_limit": sp_grace.value(),
                        "require_component_pass": chk_comp.isChecked(),
                        "optional_subject_enabled": chk_opt.isChecked(),
                        "cgpa_mode": cb_cgpa.currentText(),
                    },
                    bands,
                    actor_user=_actor(),
                )
                if not ok:
                    QMessageBox.warning(dlg, "Error", msg)
                    return
                dlg.accept()
            except PermissionError as exc:
                QMessageBox.warning(dlg, "Access Denied", str(exc))
            finally:
                db_s.close()

        b_save.clicked.connect(_save)
        if dlg.exec():
            self.refresh_all()

    def _assign_grading_to_term(self):
        term_id = self.combo_filter_term.currentData()
        gs_id = self.combo_grading_system.currentData()
        if not term_id or not gs_id:
            return
        db = SessionLocal()
        try:
            ExamRepository.update_exam_term(db, term_id, {"grading_system_id": gs_id})
            QMessageBox.information(self, "Grading Assigned", "Selected Grading System assigned to active Exam Term.")
        finally:
            db.close()

    # -------------------------------------------------------------
    # Exporters & PDF Generators
    # -------------------------------------------------------------
    def _export_tabulation_excel(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        if not term_id or not class_id:
            QMessageBox.warning(self, "Selection Error", "Please select term and class.")
            return
        default_name = f"Tabulation_Sheet_Term{term_id}_Class{class_id}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Export Tabulation Sheet (Excel)", default_name, "Excel Files (*.xlsx)")
        if not path:
            return
        db = SessionLocal()
        try:
            ok = ExamService.export_tabulation_excel(db, term_id, class_id, path, school_info=_get_school_info(db))
            if ok:
                QMessageBox.information(self, "Export Successful", f"Tabulation Sheet exported to:\n{path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Could not export Tabulation Sheet.")
        finally:
            db.close()

    def _export_tabulation_pdf(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        if not term_id or not class_id:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Tabulation Sheet (PDF)", f"Tabulation_T{term_id}_C{class_id}.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        db = SessionLocal()
        try:
            ExamReportsPDFGenerator.generate_tabulation_pdf(db, term_id, class_id, path)
            QMessageBox.information(self, "PDF Generated", f"Tabulation Sheet PDF saved to:\n{path}")
        finally:
            db.close()

    def _export_merit_list_pdf(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        if not term_id or not class_id:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Official Merit List (PDF)", f"MeritList_T{term_id}_C{class_id}.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        db = SessionLocal()
        try:
            ExamReportsPDFGenerator.generate_merit_list_pdf(db, term_id, class_id, path)
            QMessageBox.information(self, "Merit List Saved", f"Official Merit List PDF saved to:\n{path}")
        finally:
            db.close()

    def _print_student_mark_sheet(self, student_id: int):
        term_id = self.combo_filter_term.currentData()
        if not term_id:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Official Mark Sheet (PDF)", f"MarkSheet_S{student_id}_T{term_id}.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        db = SessionLocal()
        try:
            ExamReportsPDFGenerator.generate_mark_sheet_pdf(db, term_id, student_id, path)
            QMessageBox.information(self, "Mark Sheet Generated", f"Official Mark Sheet PDF created:\n{path}")
        finally:
            db.close()

    def _print_student_report_card(self, student_id: int):
        term_id = self.combo_filter_term.currentData()
        if not term_id:
            return
        db = SessionLocal()
        try:
            student = db.query(Student).filter(Student.id == student_id).first()
            term = ExamRepository.get_exam_term_by_id(db, term_id)
            summary = ExamRepository.get_student_result_summary(db, term_id, student_id)
            marks = ExamRepository.get_marks_for_student(db, term_id, student_id)
            if not marks:
                QMessageBox.warning(self, "No Marks", f"No evaluation marks recorded for {student.full_name}.")
                return
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Report Card (PDF)", f"ReportCard_{student.student_id}_{term.exam_code}.pdf", "PDF Files (*.pdf)"
            )
            if not path:
                return
            ok = ReportCardPDFGenerator.generate_report_card(
                student=student,
                exam_term=term,
                summary=summary,
                subject_marks=marks,
                school_info=_get_school_info(db),
                output_path=path,
            )
            if ok:
                QMessageBox.information(self, "Report Card Created", f"Academic Report Card created:\n{path}")
        finally:
            db.close()

    def _print_class_admit_card(self, class_id: int):
        term_id = self.combo_filter_term.currentData()
        if not term_id:
            return
        db = SessionLocal()
        try:
            student = db.query(Student).filter(Student.class_id == class_id, Student.status == "Active").first()
            if not student:
                QMessageBox.warning(self, "No Candidate", "No active students found in this class.")
                return
            term = ExamRepository.get_exam_term_by_id(db, term_id)
            schedules = ExamRepository.get_schedules_by_term(db, term_id, class_id=class_id)
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Admit Card (PDF)", f"AdmitCard_{student.student_id}_{term.exam_code}.pdf", "PDF Files (*.pdf)"
            )
            if not path:
                return
            ok = AdmitCardPDFGenerator.generate_admit_card(
                student=student,
                exam_term=term,
                schedules=schedules,
                school_info=_get_school_info(db),
                output_path=path,
            )
            if ok:
                QMessageBox.information(self, "Admit Card Generated", f"Admit Card created:\n{path}")
        finally:
            db.close()

    def _export_question_paper_pdf(self, paper_id: int, include_key: bool):
        suffix = "AnswerKey" if include_key else "QuestionPaper"
        path, _ = QFileDialog.getSaveFileName(
            self, f"Export {suffix} (PDF)", f"Exam_{suffix}_{paper_id}.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        db = SessionLocal()
        try:
            ExamReportsPDFGenerator.generate_question_paper_pdf(
                db, paper_id, path, include_answer_key=include_key
            )
            QMessageBox.information(self, "PDF Exported", f"{suffix} PDF created:\n{path}")
        finally:
            db.close()
