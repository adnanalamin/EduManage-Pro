"""
EduManage Pro - Teacher Form Dialog (PySide6)
Registration and profile modification dialog for faculty members.
"""

from datetime import date
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDateEdit, QSpinBox, QDoubleSpinBox, QPushButton, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, QDate
from app.database.connection import SessionLocal
from app.models.staff import Teacher, Department, EmployeeStatus
from app.repositories.staff_repository import StaffRepository
from app.services.hr_service import HRSecurityGuard
from app.services.staff_service import StaffService


class TeacherFormDialog(QDialog):
    def __init__(self, parent=None, teacher_id: Optional[int] = None):
        super().__init__(parent)
        self.teacher_pk = teacher_id
        self.is_edit_mode = bool(teacher_id)
        self.can_view_salary = HRSecurityGuard.can_view_salary(allow_when_no_session=True)
        self.can_manage_salary = HRSecurityGuard.can_manage_salary(allow_when_no_session=True)
        self.setWindowTitle("EduManage Pro — " + ("Edit Faculty Member" if self.is_edit_mode else "Register New Teacher"))
        self.setFixedSize(620, 620)

        self._build_ui()
        self._load_departments()
        if self.is_edit_mode:
            self._load_teacher_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_bn_input = QLineEdit()
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Male", "Female", "Other"])

        self.dob_picker = QDateEdit()
        self.dob_picker.setCalendarPopup(True)
        self.dob_picker.setDate(QDate(1988, 1, 1))

        self.blood_combo = QComboBox()
        self.blood_combo.addItems(["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-", "Unknown"])

        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()

        self.qual_input = QLineEdit()
        self.qual_input.setPlaceholderText("e.g. M.Sc. in Physics, B.Ed")

        self.exp_spin = QDoubleSpinBox()
        self.exp_spin.setRange(0.0, 60.0)
        self.exp_spin.setSingleStep(0.5)
        self.exp_spin.setSuffix(" yrs")

        self.designation_input = QLineEdit("Assistant Teacher")
        self.dept_combo = QComboBox()

        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("e.g. Physics, Mathematics, English")

        self.emergency_name_input = QLineEdit()
        self.emergency_phone_input = QLineEdit()

        self.salary_spin = QSpinBox()
        self.salary_spin.setRange(10000, 300000)
        self.salary_spin.setValue(35000)
        self.salary_spin.setSuffix(" ৳")

        self.status_combo = QComboBox()
        self.status_combo.addItems(EmployeeStatus.ALL)

        form.addRow("Teacher Full Name*:", self.name_input)
        form.addRow("Name in Bangla:", self.name_bn_input)
        form.addRow("Gender*:", self.gender_combo)
        form.addRow("Date of Birth*:", self.dob_picker)
        form.addRow("Blood Group:", self.blood_combo)
        form.addRow("Phone Number*:", self.phone_input)
        form.addRow("Email Address*:", self.email_input)
        form.addRow("Highest Qualification*:", self.qual_input)
        form.addRow("Experience (Years):", self.exp_spin)
        form.addRow("Designation*:", self.designation_input)
        form.addRow("Department*:", self.dept_combo)
        form.addRow("Primary Subject*:", self.subject_input)
        form.addRow("Emergency Contact Name:", self.emergency_name_input)
        form.addRow("Emergency Contact Phone:", self.emergency_phone_input)
        form.addRow("Monthly Basic Salary*:", self.salary_spin)
        form.addRow("Employment Status:", self.status_combo)

        # Hide salary row completely when user lacks salary permission
        show_sal = self.can_view_salary and self.can_manage_salary
        sal_lbl = form.labelForField(self.salary_spin)
        if sal_lbl:
            sal_lbl.setVisible(show_sal)
        self.salary_spin.setVisible(show_sal)

        layout.addLayout(form)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Save Faculty Profile")
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

    def _load_teacher_data(self):
        db = SessionLocal()
        try:
            t = StaffRepository.get_teacher_by_id(db, self.teacher_pk)
            if t:
                self.name_input.setText(t.full_name)
                self.name_bn_input.setText(t.full_name_bn or "")
                self.gender_combo.setCurrentText(t.gender)
                if t.date_of_birth:
                    self.dob_picker.setDate(QDate(t.date_of_birth.year, t.date_of_birth.month, t.date_of_birth.day))
                self.blood_combo.setCurrentText(t.blood_group or "Unknown")
                self.phone_input.setText(t.phone)
                self.email_input.setText(t.email)
                self.qual_input.setText(t.qualification)
                self.exp_spin.setValue(float(t.experience_years or 0.0))
                self.designation_input.setText(t.designation)
                idx = self.dept_combo.findData(t.department_id)
                if idx >= 0:
                    self.dept_combo.setCurrentIndex(idx)
                self.subject_input.setText(t.primary_subject)
                self.emergency_name_input.setText(t.emergency_contact_name or "")
                self.emergency_phone_input.setText(t.emergency_contact_phone or "")
                if self.can_view_salary:
                    self.salary_spin.setValue(t.salary)
                self.status_combo.setCurrentText(t.status)
        finally:
            db.close()

    def _save(self):
        name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        email = self.email_input.text().strip()
        subject = self.subject_input.text().strip()
        qual = self.qual_input.text().strip()

        if not name or not phone or not email or not subject or not qual:
            QMessageBox.warning(self, "Validation Error", "Please fill in all mandatory fields (*).")
            return

        qdate = self.dob_picker.date()
        dob = date(qdate.year(), qdate.month(), qdate.day())

        payload = {
            "full_name": name,
            "full_name_bn": self.name_bn_input.text().strip() or None,
            "gender": self.gender_combo.currentText(),
            "date_of_birth": dob,
            "blood_group": self.blood_combo.currentText(),
            "phone": phone,
            "email": email,
            "qualification": qual,
            "experience_years": self.exp_spin.value(),
            "designation": self.designation_input.text().strip(),
            "department_id": self.dept_combo.currentData(),
            "primary_subject": subject,
            "emergency_contact_name": self.emergency_name_input.text().strip() or None,
            "emergency_contact_phone": self.emergency_phone_input.text().strip() or None,
            "status": self.status_combo.currentText(),
        }
        if self.can_view_salary and self.can_manage_salary:
            payload["salary"] = self.salary_spin.value()

        db = SessionLocal()
        try:
            if self.is_edit_mode:
                success, _, msg = StaffService.update_teacher(db, self.teacher_pk, payload)
            else:
                success, _, msg = StaffService.add_teacher(db, payload)

            if success:
                QMessageBox.information(self, "Success", msg)
                self.accept()
            else:
                QMessageBox.critical(self, "Error", msg)
        finally:
            db.close()

