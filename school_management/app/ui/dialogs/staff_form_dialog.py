"""
EduManage Pro - Staff Form Dialog (PySide6)
Registration and edit dialog for non-teaching administrative and support personnel.
"""

from datetime import date
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDateEdit, QSpinBox, QPushButton, QFormLayout, QMessageBox, QTextEdit
)
from PySide6.QtCore import Qt, QDate
from app.database.connection import SessionLocal
from app.models.staff import Staff, Department
from app.repositories.staff_repository import StaffRepository
from app.services.staff_service import StaffService


class StaffFormDialog(QDialog):
    def __init__(self, parent=None, staff_id: Optional[int] = None):
        super().__init__(parent)
        self.staff_pk = staff_id
        self.is_edit_mode = bool(staff_id)
        self.setWindowTitle("EduManage Pro — " + ("Edit Staff Member" if self.is_edit_mode else "Register Staff Member"))
        self.setFixedSize(560, 480)

        self._build_ui()
        self._load_departments()
        if self.is_edit_mode:
            self._load_staff_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_bn_input = QLineEdit()
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Male", "Female", "Other"])

        self.dob_picker = QDateEdit()
        self.dob_picker.setCalendarPopup(True)
        self.dob_picker.setDate(QDate(1992, 1, 1))

        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()

        self.position_combo = QComboBox()
        self.position_combo.addItems([
            "Accountant",
            "Receptionist",
            "Librarian",
            "Office Assistant",
            "IT / Lab Technician",
            "Security Supervisor",
            "Security Guard",
            "Transport Supervisor",
            "Hostel Warden",
            "Support Staff"
        ])

        self.dept_combo = QComboBox()

        self.shift_combo = QComboBox()
        self.shift_combo.addItems(["Day", "Morning", "Night"])

        self.salary_spin = QSpinBox()
        self.salary_spin.setRange(8000, 150000)
        self.salary_spin.setValue(22000)
        self.salary_spin.setSuffix(" ৳")

        self.status_combo = QComboBox()
        self.status_combo.addItems(["active", "on_leave", "resigned"])

        form.addRow("Staff Full Name*:", self.name_input)
        form.addRow("Name in Bangla:", self.name_bn_input)
        form.addRow("Gender*:", self.gender_combo)
        form.addRow("Date of Birth*:", self.dob_picker)
        form.addRow("Phone Number*:", self.phone_input)
        form.addRow("Email Address:", self.email_input)
        form.addRow("Position / Role*:", self.position_combo)
        form.addRow("Department*:", self.dept_combo)
        form.addRow("Duty Shift:", self.shift_combo)
        form.addRow("Monthly Salary*:", self.salary_spin)
        form.addRow("Status:", self.status_combo)

        layout.addLayout(form)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Save Staff Member")
        self.btn_save.setStyleSheet("background-color: #2563eb; color: white; padding: 8px 18px; font-weight: bold; border-radius: 6px;")
        self.btn_save.clicked.connect(self._save)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_save)
        layout.addLayout(btn_box)

    def _load_departments(self):
        db = SessionLocal()
        try:
            depts = StaffRepository.get_or_create_departments(db)
            for d in depts:
                self.dept_combo.addItem(d.name, d.id)
        finally:
            db.close()

    def _load_staff_data(self):
        db = SessionLocal()
        try:
            s = StaffRepository.get_staff_by_id(db, self.staff_pk)
            if s:
                self.name_input.setText(s.full_name)
                self.name_bn_input.setText(s.full_name_bn or "")
                self.gender_combo.setCurrentText(s.gender)
                if s.date_of_birth:
                    self.dob_picker.setDate(QDate(s.date_of_birth.year, s.date_of_birth.month, s.date_of_birth.day))
                self.phone_input.setText(s.phone)
                self.email_input.setText(s.email or "")
                self.position_combo.setCurrentText(s.position)
                idx = self.dept_combo.findData(s.department_id)
                if idx >= 0: self.dept_combo.setCurrentIndex(idx)
                self.shift_combo.setCurrentText(s.shift)
                self.salary_spin.setValue(s.salary)
                self.status_combo.setCurrentText(s.status)
        finally:
            db.close()

    def _save(self):
        name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()

        if not name or not phone:
            QMessageBox.warning(self, "Validation Error", "Full Name and Phone Number are required.")
            return

        qdate = self.dob_picker.date()
        dob = date(qdate.year(), qdate.month(), qdate.day())

        payload = {
            "full_name": name,
            "full_name_bn": self.name_bn_input.text().strip() or None,
            "gender": self.gender_combo.currentText(),
            "date_of_birth": dob,
            "phone": phone,
            "email": self.email_input.text().strip() or None,
            "position": self.position_combo.currentText(),
            "department_id": self.dept_combo.currentData(),
            "shift": self.shift_combo.currentText(),
            "salary": self.salary_spin.value(),
            "status": self.status_combo.currentText(),
        }

        db = SessionLocal()
        try:
            if self.is_edit_mode:
                staff_obj = StaffRepository.get_staff_by_id(db, self.staff_pk)
                if staff_obj:
                    StaffRepository.update_staff(db, staff_obj, payload)
                    QMessageBox.information(self, "Success", "Staff profile updated.")
                    self.accept()
            else:
                success, _, msg = StaffService.add_staff(db, payload)
                if success:
                    QMessageBox.information(self, "Success", msg)
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", msg)
        finally:
            db.close()
