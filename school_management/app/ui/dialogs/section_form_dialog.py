"""
EduManage Pro - Section Creation and Edit Dialog (PySide6)
Configure Section Name, Room, Capacity, Shift, and Assign Class Teacher.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QSpinBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.repositories.academic_repository import AcademicRepository
from app.models.staff import Teacher
from app.services.academic_service import AcademicService


class SectionFormDialog(QDialog):
    def __init__(self, parent=None, section_id: int = None, default_class_id: int = None):
        super().__init__(parent)
        self.section_id = section_id
        self.default_class_id = default_class_id
        self.setWindowTitle("Edit Section" if section_id else "Add New Section")
        self.setFixedSize(460, 460)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Section Configuration" if not self.section_id else "Edit Section Details")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E3A8A;")
        layout.addWidget(header)

        # Class Selector
        layout.addWidget(QLabel("Assigned School Class *"))
        self.class_combo = QComboBox()
        layout.addWidget(self.class_combo)

        # Section Name
        layout.addWidget(QLabel("Section Name * (e.g. Section A, Padma, Meghna)"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Section A")
        layout.addWidget(self.name_edit)

        # Room & Capacity
        h_row1 = QHBoxLayout()
        v_room = QVBoxLayout()
        v_room.addWidget(QLabel("Assigned Room / Hall"))
        self.room_edit = QLineEdit()
        self.room_edit.setPlaceholderText("e.g. Room 204")
        v_room.addWidget(self.room_edit)
        h_row1.addLayout(v_room)

        v_cap = QVBoxLayout()
        v_cap.addWidget(QLabel("Student Capacity"))
        self.cap_spin = QSpinBox()
        self.cap_spin.setRange(10, 150)
        self.cap_spin.setValue(50)
        v_cap.addWidget(self.cap_spin)
        h_row1.addLayout(v_cap)
        layout.addLayout(h_row1)

        # Shift & Group
        h_row2 = QHBoxLayout()
        v_shift = QVBoxLayout()
        v_shift.addWidget(QLabel("Shift"))
        self.shift_combo = QComboBox()
        self.shift_combo.addItems(["Morning", "Day", "Evening"])
        v_shift.addWidget(self.shift_combo)
        h_row2.addLayout(v_shift)

        v_grp = QVBoxLayout()
        v_grp.addWidget(QLabel("Stream / Group"))
        self.group_combo = QComboBox()
        self.group_combo.addItems(["General", "Science", "Humanities", "Business Studies"])
        v_grp.addWidget(self.group_combo)
        h_row2.addLayout(v_grp)
        layout.addLayout(h_row2)

        # Assigned Class Teacher
        layout.addWidget(QLabel("Designated Class Teacher"))
        self.teacher_combo = QComboBox()
        layout.addWidget(self.teacher_combo)

        layout.addStretch()

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Save Section")
        save_btn.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
        save_btn.clicked.connect(self._on_save)
        btn_box.addWidget(save_btn)

        layout.addLayout(btn_box)

    def _load_data(self):
        db: Session = SessionLocal()
        try:
            classes = AcademicRepository.get_classes(db)
            self.class_combo.clear()
            for c in classes:
                self.class_combo.addItem(f"{c.name} ({c.group})", c.id)

            teachers = db.query(Teacher).filter(Teacher.status == "active").order_by(Teacher.full_name).all()
            self.teacher_combo.clear()
            self.teacher_combo.addItem("-- None (Unassigned) --", None)
            for t in teachers:
                self.teacher_combo.addItem(f"{t.full_name} ({t.primary_subject})", t.id)

            if self.default_class_id:
                idx = self.class_combo.findData(self.default_class_id)
                if idx >= 0:
                    self.class_combo.setCurrentIndex(idx)

            if self.section_id:
                sec = AcademicRepository.get_section_by_id(db, self.section_id)
                if sec:
                    self.name_edit.setText(sec.name)
                    self.room_edit.setText(sec.room_number or "")
                    self.cap_spin.setValue(sec.capacity)
                    idx_c = self.class_combo.findData(sec.class_id)
                    if idx_c >= 0:
                        self.class_combo.setCurrentIndex(idx_c)
                    idx_t = self.teacher_combo.findData(sec.class_teacher_id)
                    if idx_t >= 0:
                        self.teacher_combo.setCurrentIndex(idx_t)
                    idx_s = self.shift_combo.findText(sec.shift)
                    if idx_s >= 0:
                        self.shift_combo.setCurrentIndex(idx_s)
                    idx_g = self.group_combo.findText(sec.group)
                    if idx_g >= 0:
                        self.group_combo.setCurrentIndex(idx_g)
        finally:
            db.close()

    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Section name is required.")
            return

        class_id = self.class_combo.currentData()
        if not class_id:
            QMessageBox.warning(self, "Validation Error", "Please select a School Class.")
            return

        data = {
            "name": name,
            "room_number": self.room_edit.text().strip() or None,
            "capacity": self.cap_spin.value(),
            "shift": self.shift_combo.currentText(),
            "group": self.group_combo.currentText(),
            "class_id": class_id,
            "class_teacher_id": self.teacher_combo.currentData()
        }

        db: Session = SessionLocal()
        try:
            if self.section_id:
                sec, msg = AcademicService.update_section(db, self.section_id, data)
            else:
                sec, msg = AcademicService.create_section(db, data)

            if not sec:
                QMessageBox.critical(self, "Error", msg)
                return

            self.accept()
        finally:
            db.close()
