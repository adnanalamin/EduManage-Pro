"""
EduManage Pro - Examination Management & Results Page (PySide6)
Tabbed desktop view for Exam Routines, Marks Entry, Tabulation Sheets, Merit List, and PDF Transcripts.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QTabWidget, QMessageBox, QFileDialog, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from datetime import date
from app.database.connection import SessionLocal
from app.models.exam import ExamTerm, GradingScale, ExamSchedule, StudentMark, ExamResultSummary
from app.models.academic import SchoolClass, Subject
from app.models.student import Student
from app.repositories.exam_repository import ExamRepository
from app.services.exam_service import ExamService
from app.reports.report_card_pdf import ReportCardPDFGenerator
from app.reports.admit_card_pdf import AdmitCardPDFGenerator
from app.ui.dialogs.marks_entry_dialog import MarksEntryDialog
from app.ui.dialogs.exam_schedule_dialog import ExamScheduleDialog


class ExamManagementPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh_all()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 1. Header with Title & Action Buttons
        header_layout = QHBoxLayout()
        header_text = QVBoxLayout()
        h1 = QLabel("Examination Management, Grading & Results")
        h1.setStyleSheet("font-size: 20px; font-weight: bold; color: #3b82f6;")
        sub = QLabel("GPA 5.0 grading scale, marks distribution, class merit rankings, tabulation sheets & report cards.")
        sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        header_text.addWidget(h1)
        header_text.addWidget(sub)
        header_layout.addLayout(header_text)
        header_layout.addStretch()

        self.btn_marks = QPushButton("+ Enter Marks")
        self.btn_marks.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")
        self.btn_marks.clicked.connect(self._open_marks_dialog)
        header_layout.addWidget(self.btn_marks)

        self.btn_routine = QPushButton("+ Add Routine Slot")
        self.btn_routine.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")
        self.btn_routine.clicked.connect(self._open_schedule_dialog)
        header_layout.addWidget(self.btn_routine)

        self.btn_excel = QPushButton("Export Tabulation (Excel)")
        self.btn_excel.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")
        self.btn_excel.clicked.connect(self._export_tabulation_excel)
        header_layout.addWidget(self.btn_excel)

        main_layout.addLayout(header_layout)

        # 2. Executive KPI Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_exams = self._create_kpi_card("Scheduled Exam Terms", "0", "#3b82f6")
        self.card_evaluated = self._create_kpi_card("Students Evaluated", "0", "#10b981")
        self.card_avg_gpa = self._create_kpi_card("Class Average GPA", "0.00", "#f59e0b")
        self.card_pass_rate = self._create_kpi_card("Class Pass Rate", "0.0%", "#06b6d4")

        cards_layout.addWidget(self.card_exams)
        cards_layout.addWidget(self.card_evaluated)
        cards_layout.addWidget(self.card_avg_gpa)
        cards_layout.addWidget(self.card_pass_rate)
        main_layout.addLayout(cards_layout)

        # 3. Tabbed Views
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { font-size: 13px; font-weight: bold; padding: 8px 18px; }
            QTabBar::tab:selected { color: #3b82f6; border-bottom: 2px solid #3b82f6; }
        """)

        # Tab 1: Tabulation Sheet & Merit List
        self.tab_tabulation = QWidget()
        self._build_tabulation_tab()
        self.tabs.addTab(self.tab_tabulation, "Tabulation Sheet & Merit List")

        # Tab 2: Exam Routines & Timetable
        self.tab_routines = QWidget()
        self._build_routines_tab()
        self.tabs.addTab(self.tab_routines, "Exam Routines & Timetable")

        # Tab 3: Official Grading Scale (GPA 5.0)
        self.tab_grading = QWidget()
        self._build_grading_tab()
        self.tabs.addTab(self.tab_grading, "Grading Scale (GPA 5.0)")

        main_layout.addWidget(self.tabs)

    def _create_kpi_card(self, title: str, val: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: bold;")
        lbl_v = QLabel(val)
        lbl_v.setStyleSheet(f"font-size: 19px; font-weight: bold; color: {color_hex};")
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        return card

    # -------------------------------------------------------------
    # Tab 1: Tabulation Sheet & Merit List
    # -------------------------------------------------------------
    def _build_tabulation_tab(self):
        lay = QVBoxLayout(self.tab_tabulation)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Exam Term:"))
        self.combo_filter_term = QComboBox()
        self.combo_filter_term.currentIndexChanged.connect(self._load_tabulation_data)
        filter_bar.addWidget(self.combo_filter_term)

        filter_bar.addWidget(QLabel("Class:"))
        self.combo_filter_class = QComboBox()
        self.combo_filter_class.currentIndexChanged.connect(self._load_tabulation_data)
        filter_bar.addWidget(self.combo_filter_class)

        filter_bar.addStretch()

        self.btn_compile = QPushButton("Recompile Rankings & GPA")
        self.btn_compile.clicked.connect(self._recompile_results)
        filter_bar.addWidget(self.btn_compile)

        lay.addLayout(filter_bar)

        self.table_tabulation = QTableWidget()
        self.table_tabulation.setColumnCount(9)
        self.table_tabulation.setHorizontalHeaderLabels([
            "Merit Rank", "Roll", "Student ID", "Candidate Name",
            "Total Obtained", "Percent", "GPA (5.0)", "Grade", "Actions"
        ])
        self.table_tabulation.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_tabulation.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_tabulation.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_tabulation.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_tabulation.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.table_tabulation.setAlternatingRowColors(True)
        self.table_tabulation.setSelectionBehavior(QTableWidget.SelectRows)
        lay.addWidget(self.table_tabulation)

    # -------------------------------------------------------------
    # Tab 2: Exam Routines
    # -------------------------------------------------------------
    def _build_routines_tab(self):
        lay = QVBoxLayout(self.tab_routines)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        self.table_routines = QTableWidget()
        self.table_routines.setColumnCount(7)
        self.table_routines.setHorizontalHeaderLabels([
            "Date", "Time Slot", "Class", "Subject", "Hall / Room", "Full Marks", "Actions"
        ])
        self.table_routines.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_routines.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_routines.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_routines.setAlternatingRowColors(True)
        lay.addWidget(self.table_routines)

    # -------------------------------------------------------------
    # Tab 3: Grading Scale
    # -------------------------------------------------------------
    def _build_grading_tab(self):
        lay = QVBoxLayout(self.tab_grading)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        self.table_grading = QTableWidget()
        self.table_grading.setColumnCount(5)
        self.table_grading.setHorizontalHeaderLabels([
            "Letter Grade", "Grade Point (GPA)", "Mark From", "Mark To", "Evaluative Remarks"
        ])
        self.table_grading.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_grading.setAlternatingRowColors(True)
        lay.addWidget(self.table_grading)

    # -------------------------------------------------------------
    # Refresh & Loading Logic
    # -------------------------------------------------------------
    def refresh_all(self):
        db = SessionLocal()
        try:
            ExamService.seed_default_grading_scale(db)
            self._ensure_default_exam(db)

            # Update KPI card 1: total exams
            total_terms = db.query(ExamTerm).count()
            self.card_exams.findChildren(QLabel)[1].setText(str(total_terms))

            # Populate combo boxes
            curr_term = self.combo_filter_term.currentData()
            self.combo_filter_term.blockSignals(True)
            self.combo_filter_term.clear()
            terms = ExamRepository.get_all_exam_terms(db)
            for t in terms:
                self.combo_filter_term.addItem(t.name, t.id)
            if curr_term:
                idx = self.combo_filter_term.findData(curr_term)
                if idx >= 0:
                    self.combo_filter_term.setCurrentIndex(idx)
            self.combo_filter_term.blockSignals(False)

            curr_cls = self.combo_filter_class.currentData()
            self.combo_filter_class.blockSignals(True)
            self.combo_filter_class.clear()
            classes = db.query(SchoolClass).order_by(SchoolClass.numeric_order.asc()).all()
            for c in classes:
                self.combo_filter_class.addItem(c.name, c.id)
            if curr_cls:
                idx = self.combo_filter_class.findData(curr_cls)
                if idx >= 0:
                    self.combo_filter_class.setCurrentIndex(idx)
            self.combo_filter_class.blockSignals(False)

            self._load_tabulation_data()
            self._load_routines(db)
            self._load_grading_scale(db)
        finally:
            db.close()

    def _ensure_default_exam(self, db):
        count = db.query(ExamTerm).count()
        if count == 0:
            ExamRepository.create_exam_term(db, {
                "name": "Annual Examination 2026",
                "exam_code": "EXM-2026-ANN",
                "academic_year_id": 1,
                "start_date": date(2026, 11, 15),
                "end_date": date(2026, 11, 30),
                "status": "Scheduled",
                "description": "Final comprehensive academic term examination"
            })

    def _load_tabulation_data(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        if not term_id or not class_id:
            return

        db = SessionLocal()
        try:
            summaries = ExamRepository.get_class_result_summaries(db, term_id, class_id)
            if not summaries:
                # Auto-compile
                ExamService.compile_class_results(db, term_id, class_id)
                summaries = ExamRepository.get_class_result_summaries(db, term_id, class_id)

            self.table_tabulation.setRowCount(len(summaries))
            total_gpa = 0.0
            passed_count = 0

            for row, res in enumerate(summaries):
                stu = res.student
                rank_str = f"#{res.class_rank}" if res.class_rank else "—"
                rank_item = QTableWidgetItem(rank_str)
                rank_item.setFont(QFont("Helvetica", 9, QFont.Bold))
                if res.class_rank == 1:
                    rank_item.setForeground(QColor("#f59e0b"))  # Gold
                self.table_tabulation.setItem(row, 0, rank_item)

                self.table_tabulation.setItem(row, 1, QTableWidgetItem(str(stu.roll_number if stu else "-")))
                self.table_tabulation.setItem(row, 2, QTableWidgetItem(stu.student_id if stu else "-"))
                self.table_tabulation.setItem(row, 3, QTableWidgetItem(stu.full_name if stu else "Unknown"))

                self.table_tabulation.setItem(row, 4, QTableWidgetItem(f"{res.total_obtained:.1f} / {res.total_full_marks:.0f}"))
                self.table_tabulation.setItem(row, 5, QTableWidgetItem(f"{res.percentage:.1f}%"))

                gpa_item = QTableWidgetItem(f"{res.gpa:.2f}")
                gpa_item.setFont(QFont("Helvetica", 9, QFont.Bold))
                gpa_item.setForeground(QColor("#10b981") if res.passed_all else QColor("#ef4444"))
                self.table_tabulation.setItem(row, 6, gpa_item)

                grd_item = QTableWidgetItem(res.overall_grade)
                grd_item.setFont(QFont("Helvetica", 9, QFont.Bold))
                self.table_tabulation.setItem(row, 7, grd_item)

                btn_report = QPushButton("Print Transcript")
                btn_report.setStyleSheet("background-color: #334155; color: white; padding: 4px 8px; font-size: 11px;")
                btn_report.clicked.connect(lambda _, s_id=res.student_id: self._print_student_report_card(s_id))
                self.table_tabulation.setCellWidget(row, 8, btn_report)

                total_gpa += res.gpa
                if res.passed_all:
                    passed_count += 1

            # Update KPI Cards
            evaluated = len(summaries)
            self.card_evaluated.findChildren(QLabel)[1].setText(str(evaluated))
            avg_gpa = (total_gpa / evaluated) if evaluated > 0 else 0.0
            self.card_avg_gpa.findChildren(QLabel)[1].setText(f"{avg_gpa:.2f}")
            pass_rate = (passed_count / evaluated * 100.0) if evaluated > 0 else 0.0
            self.card_pass_rate.findChildren(QLabel)[1].setText(f"{pass_rate:.1f}%")
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
            self.table_routines.setItem(row, 5, QTableWidgetItem(f"{sc.full_marks:.0f} (Th:{sc.theory_full:.0f}, MCQ:{sc.mcq_full:.0f})"))

            btn_admit = QPushButton("Print Admit Card")
            btn_admit.setStyleSheet("background-color: #334155; color: white; padding: 4px 8px; font-size: 11px;")
            btn_admit.clicked.connect(lambda _, c_id=sc.class_id: self._print_class_admit_card(c_id))
            self.table_routines.setCellWidget(row, 6, btn_admit)

    def _load_grading_scale(self, db):
        scales = ExamRepository.get_grading_scales(db)
        self.table_grading.setRowCount(len(scales))
        for row, sc in enumerate(scales):
            g_item = QTableWidgetItem(sc.grade_name)
            g_item.setFont(QFont("Helvetica", 10, QFont.Bold))
            if sc.grade_name == "F":
                g_item.setForeground(QColor("#ef4444"))
            else:
                g_item.setForeground(QColor("#10b981"))
            self.table_grading.setItem(row, 0, g_item)

            self.table_grading.setItem(row, 1, QTableWidgetItem(f"{sc.grade_point:.2f}"))
            self.table_grading.setItem(row, 2, QTableWidgetItem(f"{sc.mark_from:.0f}%"))
            self.table_grading.setItem(row, 3, QTableWidgetItem(f"{sc.mark_to:.0f}%"))
            self.table_grading.setItem(row, 4, QTableWidgetItem(sc.remarks))

    def _recompile_results(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        if not term_id or not class_id:
            return
        db = SessionLocal()
        try:
            ExamService.compile_class_results(db, term_id, class_id)
            QMessageBox.information(self, "Compilation Finished", "GPAs and merit rankings updated successfully.")
            self._load_tabulation_data()
        finally:
            db.close()

    # -------------------------------------------------------------
    # Dialogs & PDF Exporters
    # -------------------------------------------------------------
    def _open_marks_dialog(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        dialog = MarksEntryDialog(self, default_term_id=term_id, default_class_id=class_id)
        if dialog.exec():
            self._load_tabulation_data()

    def _open_schedule_dialog(self):
        term_id = self.combo_filter_term.currentData()
        dialog = ExamScheduleDialog(self, default_term_id=term_id)
        if dialog.exec():
            db = SessionLocal()
            try:
                self._load_routines(db)
            finally:
                db.close()

    def _export_tabulation_excel(self):
        term_id = self.combo_filter_term.currentData()
        class_id = self.combo_filter_class.currentData()
        if not term_id or not class_id:
            QMessageBox.warning(self, "Selection Error", "Please select term and class to export tabulation.")
            return

        default_name = f"Tabulation_Sheet_Term{term_id}_Class{class_id}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Export Tabulation Sheet (Excel)", default_name, "Excel Files (*.xlsx)")
        if not path:
            return

        db = SessionLocal()
        try:
            ok = ExamService.export_tabulation_excel(db, term_id, class_id, path)
            if ok:
                QMessageBox.information(self, "Export Successful", f"Tabulation Sheet exported to:\n{path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Could not compile Tabulation Sheet workbook.")
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

            default_name = f"ReportCard_{student.student_id}_{term.exam_code}.pdf"
            path, _ = QFileDialog.getSaveFileName(self, "Save Academic Progress Report (PDF)", default_name, "PDF Files (*.pdf)")
            if not path:
                return

            school_info = {
                "name": "Ideal Model High School & College",
                "eiin": "134211",
                "phone": "+880 1712-345678",
                "address": "Plot 12, Road 4, Sector 7, Uttara, Dhaka"
            }

            ok = ReportCardPDFGenerator.generate_report_card(
                student=student,
                exam_term=term,
                summary=summary,
                subject_marks=marks,
                school_info=school_info,
                output_path=path
            )
            if ok:
                QMessageBox.information(self, "Report Card Created", f"Official Academic Transcript compiled:\n{path}")
            else:
                QMessageBox.critical(self, "PDF Failed", "Failed to compile Report Card PDF.")
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

            default_name = f"AdmitCard_{student.student_id}_{term.exam_code}.pdf"
            path, _ = QFileDialog.getSaveFileName(self, "Save Exam Admit Card (PDF)", default_name, "PDF Files (*.pdf)")
            if not path:
                return

            school_info = {
                "name": "Ideal Model High School & College",
                "eiin": "134211"
            }

            ok = AdmitCardPDFGenerator.generate_admit_card(
                student=student,
                exam_term=term,
                schedules=schedules,
                school_info=school_info,
                output_path=path
            )
            if ok:
                QMessageBox.information(self, "Admit Card Generated", f"Printable Candidate Admit Card created:\n{path}")
        finally:
            db.close()
