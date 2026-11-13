"""
EduManage Pro - Class Creation and Edit Dialog (PySide6)
Supports custom class structures, academic year, department, group/stream, shift,
max sections, and multi-stream mode.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
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
from app.repositories.academic_repository import AcademicRepository
from app.services.academic_service import AcademicService


class ClassFormDialog(QDialog):
    def __init__(self, parent=None, class_id: int = None, default_year_id: int = None):
        super().__init__(parent)
        self.class_id = class_id
        self.default_year_id = default_year_id
        self.setWindowTitle("Edit Class" if class_id else "Add New Class")
        self.setFixedSize(500, 560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Class & Structure Configuration" if not self.class_id else "Edit Class Details")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E3A8A;")
        layout.addWidget(header)

        # Academic Year
        layout.addWidget(QLabel("Academic Year *"))
        self.year_combo = QComboBox()
        layout.addWidget(self.year_combo)

        # Class Name
        layout.addWidget(QLabel("Class Name * (e.g. Class 9, Playgroup, Grade 12, Honors Year 1)"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Class 9")
        layout.addWidget(self.name_edit)

        # Class Code & Numeric Order
        h_row1 = QHBoxLayout()
        v_code = QVBoxLayout()
        v_code.addWidget(QLabel("Class Code"))
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g. C09")
        v_code.addWidget(self.code_edit)
        h_row1.addLayout(v_code)

        v_order = QVBoxLayout()
        v_order.addWidget(QLabel("Display / Numeric Order"))
        self.order_spin = QSpinBox()
        self.order_spin.setRange(1, 50)
        self.order_spin.setValue(9)
        v_order.addWidget(self.order_spin)
        h_row1.addLayout(v_order)
        layout.addLayout(h_row1)

        # Group & Shift
        h_row2 = QHBoxLayout()
        v_grp = QVBoxLayout()
        v_grp.addWidget(QLabel("Academic Group / Stream"))
        self.group_combo = QComboBox()
        v_grp.addWidget(self.group_combo)
        h_row2.addLayout(v_grp)

        v_shift = QVBoxLayout()
        v_shift.addWidget(QLabel("Default Shift"))
        self.shift_combo = QComboBox()
        v_shift.addWidget(self.shift_combo)
        h_row2.addLayout(v_shift)
        layout.addLayout(h_row2)

        # Department & Structure Profile
        h_row3 = QHBoxLayout()
        v_dept = QVBoxLayout()
        v_dept.addWidget(QLabel("Academic Department"))
        self.dept_combo = QComboBox()
        v_dept.addWidget(self.dept_combo)
        h_row3.addLayout(v_dept)

        v_prof = QVBoxLayout()
        v_prof.addWidget(QLabel("Class Structure Profile"))
        self.profile_combo = QComboBox()
        self.profile_combo.setEditable(True)
        self.profile_combo.addItems([
            "Standard",
            "Pre-Primary",
            "Primary",
            "Secondary Streams",
            "Higher Secondary",
            "Vocational",
            "Custom",
        ])
        v_prof.addWidget(self.profile_combo)
        h_row3.addLayout(v_prof)
        layout.addLayout(h_row3)

        # Max sections & Multi-stream option
        h_row4 = QHBoxLayout()
        v_max = QVBoxLayout()
        v_max.addWidget(QLabel("Max Sections"))
        self.max_sec_spin = QSpinBox()
        self.max_sec_spin.setRange(1, 30)
        self.max_sec_spin.setValue(10)
        v_max.addWidget(self.max_sec_spin)
        h_row4.addLayout(v_max)

        self.multi_stream_chk = QCheckBox("Allow same class name in separate Group / Shift")
        self.multi_stream_chk.setToolTip(
            "Enable this to create separate streamed classes such as 'Class 9 (Science)' and 'Class 9 (Humanities)'."
        )
        h_row4.addWidget(self.multi_stream_chk)
        layout.addLayout(h_row4)

        layout.addStretch()

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Save Class")
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

            years = AcademicRepository.get_all_academic_years(db)
            self.year_combo.clear()
            for y in years:
                title = f"{y.name} {'(Current)' if y.is_current else f'({y.status})'}"
                self.year_combo.addItem(title, y.id)

            if self.default_year_id:
                idx_def = self.year_combo.findData(self.default_year_id)
                if idx_def >= 0:
                    self.year_combo.setCurrentIndex(idx_def)

            groups = AcademicRepository.get_groups(db)
            self.group_combo.clear()
            for g in groups:
                self.group_combo.addItem(g.name, g.id)

            shifts = AcademicRepository.get_shifts(db)
            self.shift_combo.clear()
            for sh in shifts:
                self.shift_combo.addItem(sh.name, sh.id)

            depts = AcademicRepository.get_departments(db)
            self.dept_combo.clear()
            self.dept_combo.addItem("-- Unassigned --", None)
            for d in depts:
                self.dept_combo.addItem(f"{d.name} ({d.code})", d.id)

            if self.class_id:
                cls_obj = AcademicRepository.get_class_by_id(db, self.class_id)
                if cls_obj:
                    self.name_edit.setText(cls_obj.name)
                    self.code_edit.setText(cls_obj.code or "")
                    self.order_spin.setValue(cls_obj.numeric_order)
                    self.max_sec_spin.setValue(cls_obj.max_sections or 10)
                    self.profile_combo.setCurrentText(cls_obj.structure_profile or "Standard")
                    idx = self.group_combo.findText(cls_obj.group)
                    if idx >= 0:
                        self.group_combo.setCurrentIndex(idx)
                    idx_s = self.shift_combo.findText(cls_obj.shift)
                    if idx_s >= 0:
                        self.shift_combo.setCurrentIndex(idx_s)
                    idx_d = self.dept_combo.findData(cls_obj.department_id)
                    if idx_d >= 0:
                        self.dept_combo.setCurrentIndex(idx_d)
                    idx_y = self.year_combo.findData(cls_obj.academic_year_id)
                    if idx_y >= 0:
                        self.year_combo.setCurrentIndex(idx_y)
        finally:
            db.close()

    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Class name is required.")
            return

        year_id = self.year_combo.currentData()
        if not year_id:
            QMessageBox.warning(self, "Validation Error", "Please select an Academic Year.")
            return

        data = {
            "name": name,
            "code": self.code_edit.text().strip() or None,
            "numeric_order": self.order_spin.value(),
            "group": self.group_combo.currentText(),
            "group_id": self.group_combo.currentData(),
            "shift": self.shift_combo.currentText(),
            "shift_id": self.shift_combo.currentData(),
            "department_id": self.dept_combo.currentData(),
            "structure_profile": self.profile_combo.currentText().strip() or "Standard",
            "max_sections": self.max_sec_spin.value(),
            "academic_year_id": year_id,
        }

        db: Session = SessionLocal()
        try:
            if self.class_id:
                cls_obj, msg = AcademicService.update_class(db, self.class_id, data)
            else:
                cls_obj, msg = AcademicService.create_class(
                    db,
                    data,
                    allow_multi_stream=self.multi_stream_chk.isChecked(),
                )

            if not cls_obj:
                QMessageBox.critical(self, "Error", msg)
                return

            self.accept()
        finally:
            db.close()
