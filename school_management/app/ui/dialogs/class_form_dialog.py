"""
EduManage Pro - Class Creation and Edit Dialog (PySide6)
Allows configuring class name, numeric order, academic year, group, and shift.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QSpinBox, QPushButton, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.repositories.academic_repository import AcademicRepository
from app.services.academic_service import AcademicService


class ClassFormDialog(QDialog):
    def __init__(self, parent=None, class_id: int = None):
        super().__init__(parent)
        self.class_id = class_id
        self.setWindowTitle("Edit Class" if class_id else "Add New Class")
        self.setFixedSize(450, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Class Configuration" if not self.class_id else "Edit Class Details")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E3A8A;")
        layout.addWidget(header)

        # Form fields
        # Academic Year
        layout.addWidget(QLabel("Academic Year *"))
        self.year_combo = QComboBox()
        layout.addWidget(self.year_combo)

        # Class Name
        layout.addWidget(QLabel("Class Name * (e.g. Class 9, Nursery, Grade 12)"))
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
        v_order.addWidget(QLabel("Numeric Order"))
        self.order_spin = QSpinBox()
        self.order_spin.setRange(1, 20)
        self.order_spin.setValue(9)
        v_order.addWidget(self.order_spin)
        h_row1.addLayout(v_order)
        layout.addLayout(h_row1)

        # Group & Shift
        h_row2 = QHBoxLayout()
        v_grp = QVBoxLayout()
        v_grp.addWidget(QLabel("Academic Group"))
        self.group_combo = QComboBox()
        self.group_combo.addItems(["General", "Science", "Humanities", "Business Studies"])
        v_grp.addWidget(self.group_combo)
        h_row2.addLayout(v_grp)

        v_shift = QVBoxLayout()
        v_shift.addWidget(QLabel("Default Shift"))
        self.shift_combo = QComboBox()
        self.shift_combo.addItems(["Morning", "Day", "Evening"])
        v_shift.addWidget(self.shift_combo)
        h_row2.addLayout(v_shift)
        layout.addLayout(h_row2)

        layout.addStretch()

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Save Class")
        save_btn.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
        save_btn.clicked.connect(self._on_save)
        btn_box.addWidget(save_btn)

        layout.addLayout(btn_box)

    def _load_data(self):
        db: Session = SessionLocal()
        try:
            years = AcademicRepository.get_all_academic_years(db)
            self.year_combo.clear()
            for y in years:
                title = f"{y.name} {'(Current)' if y.is_current else ''}"
                self.year_combo.addItem(title, y.id)

            if self.class_id:
                cls_obj = AcademicRepository.get_class_by_id(db, self.class_id)
                if cls_obj:
                    self.name_edit.setText(cls_obj.name)
                    self.code_edit.setText(cls_obj.code or "")
                    self.order_spin.setValue(cls_obj.numeric_order)
                    idx = self.group_combo.findText(cls_obj.group)
                    if idx >= 0:
                        self.group_combo.setCurrentIndex(idx)
                    idx_s = self.shift_combo.findText(cls_obj.shift)
                    if idx_s >= 0:
                        self.shift_combo.setCurrentIndex(idx_s)
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
            "shift": self.shift_combo.currentText(),
            "academic_year_id": year_id
        }

        db: Session = SessionLocal()
        try:
            if self.class_id:
                cls_obj, msg = AcademicService.update_class(db, self.class_id, data)
            else:
                cls_obj, msg = AcademicService.create_class(db, data)

            if not cls_obj:
                QMessageBox.critical(self, "Error", msg)
                return

            self.accept()
        finally:
            db.close()
