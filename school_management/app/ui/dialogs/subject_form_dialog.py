"""
EduManage Pro - Subject Creation and Edit Dialog (PySide6)
Configure Subject Name, Code, Department, Group, Type (Mandatory/Optional/Elective),
Credit Hours, Marks Distribution, and Subject Teacher.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.staff import Teacher
from app.repositories.academic_repository import AcademicRepository
from app.services.academic_service import AcademicService


class SubjectFormDialog(QDialog):
    def __init__(
        self,
        parent=None,
        subject_pk: int = None,
        default_class_id: int = None,
        default_year_id: int = None,
    ):
        super().__init__(parent)
        self.subject_pk = subject_pk
        self.default_class_id = default_class_id
        self.default_year_id = default_year_id
        self.setWindowTitle("Edit Subject" if subject_pk else "Add New Subject")
        self.setFixedSize(510, 560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Subject & Curriculum Configuration" if not self.subject_pk else "Edit Subject Details")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E3A8A;")
        layout.addWidget(header)

        # Class
        layout.addWidget(QLabel("Assigned School Class *"))
        self.class_combo = QComboBox()
        layout.addWidget(self.class_combo)

        # Subject Name
        layout.addWidget(QLabel("Subject Name * (e.g. Physics, Higher Mathematics, Agriculture)"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Physics")
        layout.addWidget(self.name_edit)

        # Subject Code, Type & Credit Hours
        h_row1 = QHBoxLayout()
        v_code = QVBoxLayout()
        v_code.addWidget(QLabel("Subject Code *"))
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g. 174")
        v_code.addWidget(self.code_edit)
        h_row1.addLayout(v_code)

        v_type = QVBoxLayout()
        v_type.addWidget(QLabel("Subject Type"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Mandatory", "Optional", "Elective"])
        v_type.addWidget(self.type_combo)
        h_row1.addLayout(v_type)

        v_cred = QVBoxLayout()
        v_cred.addWidget(QLabel("Credit Hours"))
        self.credit_spin = QDoubleSpinBox()
        self.credit_spin.setRange(0.5, 10.0)
        self.credit_spin.setSingleStep(0.5)
        self.credit_spin.setValue(1.0)
        v_cred.addWidget(self.credit_spin)
        h_row1.addLayout(v_cred)
        layout.addLayout(h_row1)

        # Department & Group
        h_dept = QHBoxLayout()
        v_d = QVBoxLayout()
        v_d.addWidget(QLabel("Academic Department"))
        self.dept_combo = QComboBox()
        v_d.addWidget(self.dept_combo)
        h_dept.addLayout(v_d)

        v_g = QVBoxLayout()
        v_g.addWidget(QLabel("Academic Group"))
        self.group_combo = QComboBox()
        v_g.addWidget(self.group_combo)
        h_dept.addLayout(v_g)
        layout.addLayout(h_dept)

        # Marks Grid (Full, Pass, Theory, Practical)
        h_row2 = QHBoxLayout()
        v_full = QVBoxLayout()
        v_full.addWidget(QLabel("Full Marks"))
        self.full_spin = QSpinBox()
        self.full_spin.setRange(25, 200)
        self.full_spin.setValue(100)
        v_full.addWidget(self.full_spin)
        h_row2.addLayout(v_full)

        v_pass = QVBoxLayout()
        v_pass.addWidget(QLabel("Pass Marks"))
        self.pass_spin = QSpinBox()
        self.pass_spin.setRange(10, 100)
        self.pass_spin.setValue(33)
        v_pass.addWidget(self.pass_spin)
        h_row2.addLayout(v_pass)

        v_theory = QVBoxLayout()
        v_theory.addWidget(QLabel("Theory Marks"))
        self.theory_spin = QSpinBox()
        self.theory_spin.setRange(0, 200)
        self.theory_spin.setValue(75)
        v_theory.addWidget(self.theory_spin)
        h_row2.addLayout(v_theory)

        v_prac = QVBoxLayout()
        v_prac.addWidget(QLabel("Practical"))
        self.prac_spin = QSpinBox()
        self.prac_spin.setRange(0, 100)
        self.prac_spin.setValue(25)
        v_prac.addWidget(self.prac_spin)
        h_row2.addLayout(v_prac)
        layout.addLayout(h_row2)

        # Assigned Teacher
        layout.addWidget(QLabel("Assigned Faculty / Subject Teacher"))
        self.teacher_combo = QComboBox()
        layout.addWidget(self.teacher_combo)

        layout.addWidget(QLabel("Syllabus Summary / Description"))
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Optional syllabus notes...")
        layout.addWidget(self.desc_edit)

        layout.addStretch()

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Save Subject")
        save_btn.setStyleSheet(
            "background-color: #2563EB; color: white; font-weight: bold; padding: 7px 16px; border-radius: 4px;"
        )
        save_btn.clicked.connect(self._on_save)
        btn_box.addWidget(save_btn)

        layout.addLayout(btn_box)

    def _load_data(self):
        db: Session = SessionLocal()
        try:
            AcademicService.ensure_academic_defaults(db)

            classes = AcademicRepository.get_classes(db, academic_year_id=self.default_year_id)
            if not classes and self.default_year_id is not None:
                classes = AcademicRepository.get_classes(db)
            self.class_combo.clear()
            for c in classes:
                yr_name = c.academic_year.name if c.academic_year else ""
                self.class_combo.addItem(f"{c.name} ({c.group} | {yr_name})", c.id)

            depts = AcademicRepository.get_departments(db)
            self.dept_combo.clear()
            self.dept_combo.addItem("-- Unassigned --", None)
            for d in depts:
                self.dept_combo.addItem(f"{d.name} ({d.code})", d.id)

            groups = AcademicRepository.get_groups(db)
            self.group_combo.clear()
            self.group_combo.addItem("-- Any / General --", None)
            for g in groups:
                self.group_combo.addItem(g.name, g.id)

            teachers = (
                db.query(Teacher)
                .filter(Teacher.status == "active", Teacher.is_deleted == False)
                .order_by(Teacher.full_name)
                .all()
            )
            self.teacher_combo.clear()
            self.teacher_combo.addItem("-- None (Unassigned) --", None)
            for t in teachers:
                self.teacher_combo.addItem(f"{t.full_name} ({t.primary_subject})", t.id)

            if self.default_class_id:
                idx = self.class_combo.findData(self.default_class_id)
                if idx >= 0:
                    self.class_combo.setCurrentIndex(idx)

            if self.subject_pk:
                sub = AcademicRepository.get_subject_by_id(db, self.subject_pk)
                if sub:
                    self.name_edit.setText(sub.name)
                    self.code_edit.setText(sub.code)
                    self.credit_spin.setValue(float(sub.credit_hours or 1.0))
                    self.full_spin.setValue(sub.full_marks)
                    self.pass_spin.setValue(sub.pass_marks)
                    self.theory_spin.setValue(sub.theory_marks)
                    self.prac_spin.setValue(sub.practical_marks)
                    self.desc_edit.setText(sub.description or "")
                    idx_type = self.type_combo.findText(sub.subject_type)
                    if idx_type >= 0:
                        self.type_combo.setCurrentIndex(idx_type)
                    idx_c = self.class_combo.findData(sub.class_id)
                    if idx_c >= 0:
                        self.class_combo.setCurrentIndex(idx_c)
                    idx_d = self.dept_combo.findData(sub.department_id)
                    if idx_d >= 0:
                        self.dept_combo.setCurrentIndex(idx_d)
                    idx_g = self.group_combo.findData(sub.group_id)
                    if idx_g >= 0:
                        self.group_combo.setCurrentIndex(idx_g)
                    idx_t = self.teacher_combo.findData(sub.teacher_id)
                    if idx_t >= 0:
                        self.teacher_combo.setCurrentIndex(idx_t)
        finally:
            db.close()

    def _on_save(self):
        name = self.name_edit.text().strip()
        code = self.code_edit.text().strip()
        if not name or not code:
            QMessageBox.warning(self, "Validation Error", "Subject Name and Code are required.")
            return

        class_id = self.class_combo.currentData()
        if not class_id:
            QMessageBox.warning(self, "Validation Error", "Please select a School Class.")
            return

        full = self.full_spin.value()
        pass_m = self.pass_spin.value()
        theory = self.theory_spin.value()
        prac = self.prac_spin.value()

        if pass_m > full:
            QMessageBox.warning(self, "Validation Error", "Pass marks cannot exceed Full marks.")
            return

        if theory + prac != full:
            reply = QMessageBox.question(
                self,
                "Mark Distribution Notice",
                f"Theory ({theory}) + Practical ({prac}) = {theory + prac}, which does not match Full Marks ({full}).\nAuto-adjust theory marks to {full - prac}?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                theory = full - prac
                self.theory_spin.setValue(theory)
            else:
                return

        sub_type = self.type_combo.currentText()
        data = {
            "name": name,
            "code": code,
            "subject_type": sub_type,
            "is_optional": sub_type in ("Optional", "Elective"),
            "full_marks": full,
            "pass_marks": pass_m,
            "theory_marks": theory,
            "practical_marks": prac,
            "class_id": class_id,
            "teacher_id": self.teacher_combo.currentData(),
            "department_id": self.dept_combo.currentData(),
            "group_id": self.group_combo.currentData(),
            "credit_hours": self.credit_spin.value(),
            "description": self.desc_edit.text().strip() or None,
        }

        db: Session = SessionLocal()
        try:
            if self.subject_pk:
                sub, msg = AcademicService.update_subject(db, self.subject_pk, data)
            else:
                sub, msg = AcademicService.create_subject(db, data)

            if not sub:
                QMessageBox.critical(self, "Error", msg)
                return

            self.accept()
        finally:
            db.close()
