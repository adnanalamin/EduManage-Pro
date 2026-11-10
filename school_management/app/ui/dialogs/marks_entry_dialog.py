"""
EduManage Pro - Marks Entry Dialog (PySide6)
Bulk grading modal for teachers to input Theory, MCQ, Practical marks with live GPA and grade updates.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QMessageBox, QDoubleSpinBox, QCheckBox, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from app.database.connection import SessionLocal
from app.models.exam import ExamTerm, StudentMark
from app.models.academic import SchoolClass, Subject
from app.models.student import Student
from app.repositories.exam_repository import ExamRepository
from app.services.exam_service import ExamService


class MarksEntryDialog(QDialog):
    def __init__(self, parent=None, default_term_id=None, default_class_id=None):
        super().__init__(parent)
        self.setWindowTitle("Student Marks Entry & Evaluation — EduManage Pro")
        self.resize(920, 600)
        self.setModal(True)

        self.default_term_id = default_term_id
        self.default_class_id = default_class_id
        self.students = []

        self._build_ui()
        self._load_selectors()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header Title
        title = QLabel("Subject-wise Marks Entry Register")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6;")
        layout.addWidget(title)

        # Selector Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        top_bar.addWidget(QLabel("Exam Term:"))
        self.combo_term = QComboBox()
        self.combo_term.currentIndexChanged.connect(self._on_selector_changed)
        top_bar.addWidget(self.combo_term)

        top_bar.addWidget(QLabel("Class:"))
        self.combo_class = QComboBox()
        self.combo_class.currentIndexChanged.connect(self._on_class_changed)
        top_bar.addWidget(self.combo_class)

        top_bar.addWidget(QLabel("Subject:"))
        self.combo_subject = QComboBox()
        self.combo_subject.currentIndexChanged.connect(self._load_marks_table)
        top_bar.addWidget(self.combo_subject)

        top_bar.addStretch()

        self.btn_load = QPushButton("Load Roster")
        self.btn_load.clicked.connect(self._load_marks_table)
        top_bar.addWidget(self.btn_load)

        layout.addLayout(top_bar)

        # Marks Grid
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Roll", "Student ID", "Candidate Name", "Theory (70)",
            "MCQ (30)", "Practical", "Total (100)", "GP (5.0)", "Grade", "Absent"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save All Marks & Update GPA")
        self.btn_save.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px 18px;")
        self.btn_save.clicked.connect(self._handle_save)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _load_selectors(self):
        db = SessionLocal()
        try:
            ExamService.seed_default_grading_scale(db)
            terms = ExamRepository.get_all_exam_terms(db)
            self.combo_term.clear()
            for t in terms:
                self.combo_term.addItem(f"{t.name} ({t.exam_code})", t.id)

            classes = db.query(SchoolClass).order_by(SchoolClass.numeric_order.asc()).all()
            self.combo_class.clear()
            for c in classes:
                self.combo_class.addItem(c.name, c.id)

            self._on_class_changed()
        finally:
            db.close()

    def _on_class_changed(self):
        cls_id = self.combo_class.currentData()
        if not cls_id:
            return
        db = SessionLocal()
        try:
            subjects = db.query(Subject).filter(Subject.class_id == cls_id).all()
            self.combo_subject.clear()
            for s in subjects:
                self.combo_subject.addItem(f"{s.name} ({s.code})", s.id)
            self._load_marks_table()
        finally:
            db.close()

    def _on_selector_changed(self):
        self._load_marks_table()

    def _load_marks_table(self):
        term_id = self.combo_term.currentData()
        class_id = self.combo_class.currentData()
        subject_id = self.combo_subject.currentData()

        if not term_id or not class_id or not subject_id:
            return

        db = SessionLocal()
        try:
            self.students = db.query(Student).filter(
                Student.class_id == class_id,
                Student.status == "Active"
            ).order_by(Student.roll_number.asc()).all()

            existing_marks = ExamRepository.get_marks_for_subject(db, term_id, class_id, subject_id)
            marks_map = {m.student_id: m for m in existing_marks}

            self.table.setRowCount(len(self.students))

            for row, stu in enumerate(self.students):
                # Roll, ID, Name
                self.table.setItem(row, 0, QTableWidgetItem(str(stu.roll_number)))
                self.table.setItem(row, 1, QTableWidgetItem(stu.student_id))
                self.table.setItem(row, 2, QTableWidgetItem(stu.full_name))

                mark = marks_map.get(stu.id)

                # Theory SpinBox
                th_spin = QDoubleSpinBox()
                th_spin.setRange(0.0, 100.0)
                th_spin.setValue(mark.theory_marks if mark else 50.0)
                th_spin.valueChanged.connect(lambda _, r=row: self._recalc_row(r))
                self.table.setCellWidget(row, 3, th_spin)

                # MCQ SpinBox
                mcq_spin = QDoubleSpinBox()
                mcq_spin.setRange(0.0, 50.0)
                mcq_spin.setValue(mark.mcq_marks if mark else 25.0)
                mcq_spin.valueChanged.connect(lambda _, r=row: self._recalc_row(r))
                self.table.setCellWidget(row, 4, mcq_spin)

                # Practical SpinBox
                pr_spin = QDoubleSpinBox()
                pr_spin.setRange(0.0, 50.0)
                pr_spin.setValue(mark.practical_marks if mark else 0.0)
                pr_spin.valueChanged.connect(lambda _, r=row: self._recalc_row(r))
                self.table.setCellWidget(row, 5, pr_spin)

                # Total Item
                total_item = QTableWidgetItem("0.0")
                total_item.setFont(QFont("Helvetica", 9, QFont.Bold))
                self.table.setItem(row, 6, total_item)

                # GP Item
                gp_item = QTableWidgetItem("0.0")
                self.table.setItem(row, 7, gp_item)

                # Grade Item
                grd_item = QTableWidgetItem("F")
                grd_item.setFont(QFont("Helvetica", 9, QFont.Bold))
                self.table.setItem(row, 8, grd_item)

                # Absent Checkbox
                abs_cb = QCheckBox()
                abs_cb.setChecked(mark.is_absent if mark else False)
                abs_cb.toggled.connect(lambda _, r=row: self._recalc_row(r))
                self.table.setCellWidget(row, 9, abs_cb)

                self._recalc_row(row)
        finally:
            db.close()

    def _recalc_row(self, row: int):
        th_spin = self.table.cellWidget(row, 3)
        mcq_spin = self.table.cellWidget(row, 4)
        pr_spin = self.table.cellWidget(row, 5)
        abs_cb = self.table.cellWidget(row, 9)

        if not th_spin or not mcq_spin:
            return

        is_abs = abs_cb.isChecked() if abs_cb else False
        if is_abs:
            total = 0.0
            grade = "F"
            gp = 0.0
        else:
            total = th_spin.value() + mcq_spin.value() + (pr_spin.value() if pr_spin else 0.0)
            if total >= 80:
                grade, gp = "A+", 5.0
            elif total >= 70:
                grade, gp = "A", 4.0
            elif total >= 60:
                grade, gp = "A-", 3.5
            elif total >= 50:
                grade, gp = "B", 3.0
            elif total >= 40:
                grade, gp = "C", 2.0
            elif total >= 33:
                grade, gp = "D", 1.0
            else:
                grade, gp = "F", 0.0

        tot_item = self.table.item(row, 6)
        if tot_item:
            tot_item.setText(f"{total:.1f}")

        gp_item = self.table.item(row, 7)
        if gp_item:
            gp_item.setText(f"{gp:.2f}")

        grd_item = self.table.item(row, 8)
        if grd_item:
            grd_item.setText(grade)
            grd_item.setForeground(QColor("#047857") if grade != "F" else QColor("#b91c1c"))

    def _handle_save(self):
        term_id = self.combo_term.currentData()
        class_id = self.combo_class.currentData()
        subject_id = self.combo_subject.currentData()

        if not term_id or not class_id or not subject_id:
            QMessageBox.warning(self, "Validation Error", "Please select term, class, and subject.")
            return

        db = SessionLocal()
        try:
            saved_count = 0
            for row, stu in enumerate(self.students):
                th_spin = self.table.cellWidget(row, 3)
                mcq_spin = self.table.cellWidget(row, 4)
                pr_spin = self.table.cellWidget(row, 5)
                abs_cb = self.table.cellWidget(row, 9)

                data = {
                    "exam_term_id": term_id,
                    "class_id": class_id,
                    "subject_id": subject_id,
                    "student_id": stu.id,
                    "theory_marks": th_spin.value(),
                    "mcq_marks": mcq_spin.value(),
                    "practical_marks": pr_spin.value() if pr_spin else 0.0,
                    "is_absent": abs_cb.isChecked() if abs_cb else False
                }
                ExamRepository.upsert_student_mark(db, data)
                saved_count += 1

            # Compile overall class results & rankings
            ExamService.compile_class_results(db, term_id, class_id)

            QMessageBox.information(
                self,
                "Marks Saved",
                f"Successfully saved evaluation marks for {saved_count} candidates.\n\n"
                f"Class result summary, GPAs, and merit rankings have been compiled."
            )
            self.accept()
        finally:
            db.close()
