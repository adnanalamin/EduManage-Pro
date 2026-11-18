"""
EduManage Pro - Marks Entry Dialog (PySide6)
Bulk grading modal supporting Theory, MCQ, Practical, Viva, and Attendance marks
with live GPA preview, schedule full-mark bounds, and Published-Result Lock enforcement.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QMessageBox, QDoubleSpinBox, QCheckBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from app.database.connection import SessionLocal
from app.models.academic import SchoolClass, Subject
from app.models.exam import ExamResultBatch, ResultWorkflowStatus
from app.models.student import Student
from app.repositories.exam_repository import ExamRepository
from app.security.session import session as app_session
from app.services.exam_service import ExamService


class MarksEntryDialog(QDialog):
    def __init__(self, parent=None, default_term_id=None, default_class_id=None):
        super().__init__(parent)
        self.setWindowTitle("Student Marks Entry & Evaluation — EduManage Pro")
        self.resize(1120, 640)
        self.setModal(True)

        self.default_term_id = default_term_id
        self.default_class_id = default_class_id
        self.students = []
        self._active_full_marks = 100.0
        self._active_grading_system_id = None
        self._is_locked = False

        self._build_ui()
        self._load_selectors()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Subject-wise Granular Marks Entry Register (Theory, MCQ, Practical, Viva & Attendance)")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6;")
        layout.addWidget(title)

        # Lock / Status Banner
        self.lock_banner = QFrame()
        self.lock_banner.setVisible(False)
        self.lock_banner.setStyleSheet(
            "QFrame { background-color: #7f1d1d; border: 1px solid #ef4444; border-radius: 6px; padding: 6px 10px; }"
        )
        lock_lay = QHBoxLayout(self.lock_banner)
        lock_lay.setContentsMargins(6, 4, 6, 4)
        self.lbl_lock_msg = QLabel("Results for this term & class are PUBLISHED and LOCKED. Mark modifications are blocked.")
        self.lbl_lock_msg.setStyleSheet("color: #fecaca; font-weight: bold; font-size: 12px;")
        lock_lay.addWidget(self.lbl_lock_msg)
        layout.addWidget(self.lock_banner)

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

        self.btn_sync_att = QPushButton("Auto-Fill Attendance Marks")
        self.btn_sync_att.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 5px 10px;")
        self.btn_sync_att.clicked.connect(self._handle_auto_attendance)
        top_bar.addWidget(self.btn_sync_att)

        self.btn_load = QPushButton("Reload Roster")
        self.btn_load.clicked.connect(self._load_marks_table)
        top_bar.addWidget(self.btn_load)

        layout.addLayout(top_bar)

        # Marks Grid
        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "Roll", "Student ID", "Candidate Name",
            "Theory", "MCQ", "Practical", "Viva", "Attendance",
            "Total", "GP", "Grade", "Absent"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for col in (0, 1, 2, 11):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.lbl_schedule_hint = QLabel("")
        self.lbl_schedule_hint.setStyleSheet("color: #94a3b8; font-size: 11px;")
        btn_layout.addWidget(self.lbl_schedule_hint)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save All Marks & Compile Results")
        self.btn_save.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px 18px;")
        self.btn_save.clicked.connect(self._handle_save)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _load_selectors(self):
        db = SessionLocal()
        try:
            ExamService.seed_default_grading_scale(db)
            terms = ExamRepository.get_all_exam_terms(db)
            self.combo_term.blockSignals(True)
            self.combo_term.clear()
            for t in terms:
                self.combo_term.addItem(f"{t.name} ({t.exam_code})", t.id)
            if self.default_term_id:
                idx = self.combo_term.findData(self.default_term_id)
                if idx >= 0:
                    self.combo_term.setCurrentIndex(idx)
            self.combo_term.blockSignals(False)

            classes = db.query(SchoolClass).order_by(SchoolClass.numeric_order.asc()).all()
            self.combo_class.blockSignals(True)
            self.combo_class.clear()
            for c in classes:
                self.combo_class.addItem(c.name, c.id)
            if self.default_class_id:
                idx = self.combo_class.findData(self.default_class_id)
                if idx >= 0:
                    self.combo_class.setCurrentIndex(idx)
            self.combo_class.blockSignals(False)

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
            self.combo_subject.blockSignals(True)
            self.combo_subject.clear()
            for s in subjects:
                self.combo_subject.addItem(f"{s.name} ({s.code})", s.id)
            self.combo_subject.blockSignals(False)
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
            term = ExamRepository.get_exam_term_by_id(db, term_id)
            schedule = ExamRepository.get_schedule_for_subject(db, term_id, class_id, subject_id)
            batch = ExamRepository.get_result_batch(db, term_id, class_id)

            self._is_locked = bool(
                batch and (batch.is_published or batch.is_locked or batch.status == ResultWorkflowStatus.PUBLISHED)
            )
            self.lock_banner.setVisible(self._is_locked)
            self.btn_save.setEnabled(not self._is_locked)
            self.btn_sync_att.setEnabled(not self._is_locked)

            self._active_full_marks = float(schedule.full_marks) if schedule else 100.0
            self._active_grading_system_id = term.grading_system_id if term else None

            if schedule:
                self.lbl_schedule_hint.setText(
                    f"Schedule Full: {schedule.full_marks:g} | Pass: {schedule.pass_marks:g} | "
                    f"Th:{schedule.theory_full:g} MCQ:{schedule.mcq_full:g} Prac:{schedule.practical_full:g} "
                    f"Viva:{schedule.viva_full:g} Att:{schedule.attendance_full:g}"
                )
            else:
                self.lbl_schedule_hint.setText("No schedule defined; defaulting to 100 Full Marks (33% Pass).")

            self.students = (
                db.query(Student)
                .filter(Student.class_id == class_id, Student.status == "Active")
                .order_by(Student.roll_number.asc())
                .all()
            )
            existing_marks = ExamRepository.get_marks_for_subject(db, term_id, class_id, subject_id)
            marks_map = {m.student_id: m for m in existing_marks}

            self.table.setRowCount(len(self.students))
            for row, stu in enumerate(self.students):
                self.table.setItem(row, 0, QTableWidgetItem(str(stu.roll_number)))
                self.table.setItem(row, 1, QTableWidgetItem(stu.student_id))
                self.table.setItem(row, 2, QTableWidgetItem(stu.full_name))

                mark = marks_map.get(stu.id)

                def _make_spin(val: float, max_val: float = 200.0):
                    sp = QDoubleSpinBox()
                    sp.setRange(0.0, max_val)
                    sp.setDecimals(1)
                    sp.setValue(float(val))
                    sp.setEnabled(not self._is_locked)
                    sp.valueChanged.connect(lambda _, r=row: self._recalc_row(r))
                    return sp

                self.table.setCellWidget(row, 3, _make_spin(mark.theory_marks if mark else 0.0, 200.0))
                self.table.setCellWidget(row, 4, _make_spin(mark.mcq_marks if mark else 0.0, 100.0))
                self.table.setCellWidget(row, 5, _make_spin(mark.practical_marks if mark else 0.0, 100.0))
                self.table.setCellWidget(row, 6, _make_spin(mark.viva_marks if mark else 0.0, 50.0))
                self.table.setCellWidget(row, 7, _make_spin(mark.attendance_marks if mark else 0.0, 50.0))

                total_item = QTableWidgetItem("0.0")
                total_item.setFont(QFont("Helvetica", 9, QFont.Bold))
                self.table.setItem(row, 8, total_item)

                self.table.setItem(row, 9, QTableWidgetItem("0.00"))

                grd_item = QTableWidgetItem("F")
                grd_item.setFont(QFont("Helvetica", 9, QFont.Bold))
                self.table.setItem(row, 10, grd_item)

                abs_cb = QCheckBox()
                abs_cb.setChecked(mark.is_absent if mark else False)
                abs_cb.setEnabled(not self._is_locked)
                abs_cb.toggled.connect(lambda _, r=row: self._recalc_row(r))
                self.table.setCellWidget(row, 11, abs_cb)

                self._recalc_row(row)
        finally:
            db.close()

    def _recalc_row(self, row: int):
        th_spin = self.table.cellWidget(row, 3)
        mcq_spin = self.table.cellWidget(row, 4)
        pr_spin = self.table.cellWidget(row, 5)
        viva_spin = self.table.cellWidget(row, 6)
        att_spin = self.table.cellWidget(row, 7)
        abs_cb = self.table.cellWidget(row, 11)

        if not th_spin:
            return

        is_abs = abs_cb.isChecked() if abs_cb else False
        if is_abs:
            total = 0.0
            grade, gp = "F", 0.0
        else:
            total = (
                th_spin.value()
                + (mcq_spin.value() if mcq_spin else 0.0)
                + (pr_spin.value() if pr_spin else 0.0)
                + (viva_spin.value() if viva_spin else 0.0)
                + (att_spin.value() if att_spin else 0.0)
            )
            pct = (total / self._active_full_marks * 100.0) if self._active_full_marks > 0 else 0.0
            if pct >= 80:
                grade, gp = "A+", 5.0
            elif pct >= 70:
                grade, gp = "A", 4.0
            elif pct >= 60:
                grade, gp = "A-", 3.5
            elif pct >= 50:
                grade, gp = "B", 3.0
            elif pct >= 40:
                grade, gp = "C", 2.0
            elif pct >= 33:
                grade, gp = "D", 1.0
            else:
                grade, gp = "F", 0.0

        if self.table.item(row, 8):
            self.table.item(row, 8).setText(f"{total:.1f}")
        if self.table.item(row, 9):
            self.table.item(row, 9).setText(f"{gp:.2f}")
        if self.table.item(row, 10):
            self.table.item(row, 10).setText(grade)
            self.table.item(row, 10).setForeground(QColor("#047857") if grade != "F" else QColor("#b91c1c"))

    def _handle_auto_attendance(self):
        term_id = self.combo_term.currentData()
        class_id = self.combo_class.currentData()
        if not term_id or not class_id:
            return
        db = SessionLocal()
        try:
            actor = app_session.current_user if app_session.is_authenticated else None
            count = ExamService.sync_attendance_marks_for_term(db, term_id, class_id, actor_user=actor)
            QMessageBox.information(
                self,
                "Attendance Marks Synced",
                f"Synced attendance marks for {count} scheduled subject entries from Student Attendance logs.",
            )
            self._load_marks_table()
        except PermissionError as exc:
            QMessageBox.warning(self, "Access Denied / Locked", str(exc))
        finally:
            db.close()

    def _handle_save(self):
        term_id = self.combo_term.currentData()
        class_id = self.combo_class.currentData()
        subject_id = self.combo_subject.currentData()

        if not term_id or not class_id or not subject_id:
            QMessageBox.warning(self, "Validation Error", "Please select term, class, and subject.")
            return

        db = SessionLocal()
        try:
            actor = app_session.current_user if app_session.is_authenticated else None
            saved_count = 0
            for row, stu in enumerate(self.students):
                th_spin = self.table.cellWidget(row, 3)
                mcq_spin = self.table.cellWidget(row, 4)
                pr_spin = self.table.cellWidget(row, 5)
                viva_spin = self.table.cellWidget(row, 6)
                att_spin = self.table.cellWidget(row, 7)
                abs_cb = self.table.cellWidget(row, 11)

                data = {
                    "exam_term_id": term_id,
                    "class_id": class_id,
                    "subject_id": subject_id,
                    "student_id": stu.id,
                    "theory_marks": th_spin.value() if th_spin else 0.0,
                    "mcq_marks": mcq_spin.value() if mcq_spin else 0.0,
                    "practical_marks": pr_spin.value() if pr_spin else 0.0,
                    "viva_marks": viva_spin.value() if viva_spin else 0.0,
                    "attendance_marks": att_spin.value() if att_spin else 0.0,
                    "is_absent": abs_cb.isChecked() if abs_cb else False,
                }
                ExamRepository.upsert_student_mark(db, data, actor_user=actor)
                saved_count += 1

            ExamService.compile_class_results(db, term_id, class_id, actor_user=actor)
            QMessageBox.information(
                self,
                "Marks Saved",
                f"Successfully saved evaluation marks for {saved_count} candidates.\n"
                f"GPA, CGPA, and Class/Section rankings have been compiled.",
            )
            self.accept()
        except PermissionError as exc:
            QMessageBox.warning(self, "Published Lock / Permission Error", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not save marks:\n{exc}")
        finally:
            db.close()
