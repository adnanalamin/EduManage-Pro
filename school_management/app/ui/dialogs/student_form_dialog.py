"""
EduManage Pro - Student Admission & Edit Form Dialog (PySide6)
Tabbed interface covering:
1. Personal Information (Name, Gender, DOB, Blood Group, Phone, Religion)
2. Academic Details (Class, Section, Roll, Shift, Group)
3. Guardian Details (Father, Mother, Guardian Name, Phone, Occupation)
4. Address & Emergency Contacts
"""

from datetime import date
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDateEdit, QTextEdit, QSpinBox, QPushButton, QTabWidget, QWidget,
    QFormLayout, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, QDate
from app.database.connection import SessionLocal
from app.models.student import Student, StudentStatus
from app.models.academic import SchoolClass, Section, AcademicYear
from app.services.student_service import StudentService


class StudentFormDialog(QDialog):
    def __init__(self, parent=None, student_id: Optional[int] = None):
        super().__init__(parent)
        self.student_pk = student_id
        self.is_edit_mode = bool(student_id)
        self.setWindowTitle("EduManage Pro — " + ("Edit Student Profile" if self.is_edit_mode else "Student Admission Form"))
        self.setFixedSize(680, 560)

        self._build_ui()
        self._load_reference_data()

        if self.is_edit_mode:
            self._load_student_data()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Tabs Container
        self.tabs = QTabWidget()

        # Tab 1: Personal Details
        self.tab_personal = QWidget()
        personal_form = QFormLayout(self.tab_personal)
        personal_form.setSpacing(10)

        self.first_name_input = QLineEdit()
        self.last_name_input = QLineEdit()
        self.name_bn_input = QLineEdit()
        
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Male", "Female", "Other"])

        self.dob_picker = QDateEdit()
        self.dob_picker.setCalendarPopup(True)
        self.dob_picker.setDate(QDate(2010, 1, 1))

        self.blood_combo = QComboBox()
        self.blood_combo.addItems(["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-", "Unknown"])

        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()
        self.birth_cert_input = QLineEdit()

        personal_form.addRow("First Name*:", self.first_name_input)
        personal_form.addRow("Last Name*:", self.last_name_input)
        personal_form.addRow("Name in Bangla:", self.name_bn_input)
        personal_form.addRow("Gender*:", self.gender_combo)
        personal_form.addRow("Date of Birth*:", self.dob_picker)
        personal_form.addRow("Blood Group:", self.blood_combo)
        personal_form.addRow("Student Phone:", self.phone_input)
        personal_form.addRow("Student Email:", self.email_input)
        personal_form.addRow("Birth Certificate No:", self.birth_cert_input)

        self.tabs.addTab(self.tab_personal, "1. Personal Details")

        # Tab 2: Academic Enrollment
        self.tab_academic = QWidget()
        acad_form = QFormLayout(self.tab_academic)
        acad_form.setSpacing(10)

        self.roll_spin = QSpinBox()
        self.roll_spin.setRange(1, 9999)
        self.roll_spin.setValue(1)

        self.class_combo = QComboBox()
        self.section_combo = QComboBox()
        self.ay_combo = QComboBox()

        self.group_combo = QComboBox()
        self.group_combo.addItems(["General", "Science", "Humanities", "Business Studies"])

        self.shift_combo = QComboBox()
        self.shift_combo.addItems(["Day", "Morning"])

        self.status_combo = QComboBox()
        self.status_combo.addItems([StudentStatus.ACTIVE, StudentStatus.INACTIVE, StudentStatus.TRANSFERRED, StudentStatus.GRADUATED])

        acad_form.addRow("Roll Number*:", self.roll_spin)
        acad_form.addRow("Enrolled Class*:", self.class_combo)
        acad_form.addRow("Section:", self.section_combo)
        acad_form.addRow("Academic Session*:", self.ay_combo)
        acad_form.addRow("Study Group:", self.group_combo)
        acad_form.addRow("Shift:", self.shift_combo)
        acad_form.addRow("Enrollment Status:", self.status_combo)

        self.tabs.addTab(self.tab_academic, "2. Academic Enrollment")

        # Tab 3: Guardian Details
        self.tab_guardian = QWidget()
        guard_form = QFormLayout(self.tab_guardian)
        guard_form.setSpacing(10)

        self.guardian_name_input = QLineEdit()
        self.relation_combo = QComboBox()
        self.relation_combo.addItems(["Father", "Mother", "Uncle", "Legal Guardian"])
        self.father_name_input = QLineEdit()
        self.mother_name_input = QLineEdit()
        self.guardian_phone_input = QLineEdit()
        self.guardian_email_input = QLineEdit()
        self.guardian_occ_input = QLineEdit()
        self.emergency_phone_input = QLineEdit()

        guard_form.addRow("Primary Guardian Name*:", self.guardian_name_input)
        guard_form.addRow("Relationship*:", self.relation_combo)
        guard_form.addRow("Father's Name:", self.father_name_input)
        guard_form.addRow("Mother's Name:", self.mother_name_input)
        guard_form.addRow("Guardian Phone*:", self.guardian_phone_input)
        guard_form.addRow("Guardian Email:", self.guardian_email_input)
        guard_form.addRow("Guardian Occupation:", self.guardian_occ_input)
        guard_form.addRow("Emergency Contact:", self.emergency_phone_input)

        self.tabs.addTab(self.tab_guardian, "3. Guardian & Emergency")

        # Tab 4: Address & Health
        self.tab_address = QWidget()
        addr_form = QFormLayout(self.tab_address)
        addr_form.setSpacing(10)

        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(70)
        self.city_input = QLineEdit("Dhaka")
        self.district_input = QLineEdit("Dhaka")
        self.previous_school_input = QLineEdit()
        self.medical_notes_input = QTextEdit()
        self.medical_notes_input.setMaximumHeight(70)

        addr_form.addRow("Residential Address:", self.address_input)
        addr_form.addRow("City / Area:", self.city_input)
        addr_form.addRow("District:", self.district_input)
        addr_form.addRow("Previous School:", self.previous_school_input)
        addr_form.addRow("Medical / Allergy Notes:", self.medical_notes_input)

        self.tabs.addTab(self.tab_address, "4. Address & Medical")

        main_layout.addWidget(self.tabs)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Save Student Record" if self.is_edit_mode else "Complete Admission")
        self.btn_save.setStyleSheet("background-color: #2563eb; color: white; padding: 8px 18px; font-weight: bold; border-radius: 6px;")
        self.btn_save.clicked.connect(self._save_student)

        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_save)
        main_layout.addLayout(btn_box)

    def _load_reference_data(self):
        db = SessionLocal()
        try:
            classes = db.query(SchoolClass).all()
            for c in classes:
                self.class_combo.addItem(c.name, c.id)

            sections = db.query(Section).all()
            for s in sections:
                self.section_combo.addItem(s.name, s.id)

            years = db.query(AcademicYear).all()
            for y in years:
                self.ay_combo.addItem(y.name, y.id)
        finally:
            db.close()

    def _load_student_data(self):
        db = SessionLocal()
        try:
            stu = db.query(Student).filter_by(id=self.student_pk).first()
            if stu:
                self.first_name_input.setText(stu.first_name)
                self.last_name_input.setText(stu.last_name)
                self.name_bn_input.setText(stu.full_name_bn or "")
                self.gender_combo.setCurrentText(stu.gender)
                if stu.date_of_birth:
                    self.dob_picker.setDate(QDate(stu.date_of_birth.year, stu.date_of_birth.month, stu.date_of_birth.day))
                self.blood_combo.setCurrentText(stu.blood_group or "Unknown")
                self.phone_input.setText(stu.phone or "")
                self.email_input.setText(stu.email or "")
                self.birth_cert_input.setText(stu.birth_certificate_no or "")

                self.roll_spin.setValue(stu.roll_number)
                idx = self.class_combo.findData(stu.class_id)
                if idx >= 0: self.class_combo.setCurrentIndex(idx)
                if stu.section_id:
                    s_idx = self.section_combo.findData(stu.section_id)
                    if s_idx >= 0: self.section_combo.setCurrentIndex(s_idx)

                self.group_combo.setCurrentText(stu.group or "General")
                self.shift_combo.setCurrentText(stu.shift or "Day")
                self.status_combo.setCurrentText(stu.status)

                if stu.guardian:
                    self.guardian_name_input.setText(stu.guardian.guardian_name)
                    self.relation_combo.setCurrentText(stu.guardian.relation or "Father")
                    self.father_name_input.setText(stu.guardian.father_name or "")
                    self.mother_name_input.setText(stu.guardian.mother_name or "")
                    self.guardian_phone_input.setText(stu.guardian.guardian_phone or "")
                    self.guardian_email_input.setText(stu.guardian.guardian_email or "")
                    self.guardian_occ_input.setText(stu.guardian.guardian_occupation or "")

                self.address_input.setText(stu.address or "")
                self.city_input.setText(stu.city or "Dhaka")
                self.district_input.setText(stu.district or "Dhaka")
                self.previous_school_input.setText(stu.previous_school or "")
                self.medical_notes_input.setText(stu.medical_notes or "")
                self.emergency_phone_input.setText(stu.emergency_contact or "")
        finally:
            db.close()

    def _save_student(self):
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        guardian_name = self.guardian_name_input.text().strip()
        guardian_phone = self.guardian_phone_input.text().strip()

        if not first_name or not last_name:
            QMessageBox.warning(self, "Validation Error", "First Name and Last Name are required.")
            self.tabs.setCurrentIndex(0)
            return

        if not guardian_name or not guardian_phone:
            QMessageBox.warning(self, "Validation Error", "Guardian Name and Phone are required.")
            self.tabs.setCurrentIndex(2)
            return

        qdate = self.dob_picker.date()
        dob = date(qdate.year(), qdate.month(), qdate.day())

        class_id = self.class_combo.currentData()
        section_id = self.section_combo.currentData()
        ay_id = self.ay_combo.currentData()

        stu_payload = {
            "first_name": first_name,
            "last_name": last_name,
            "full_name_bn": self.name_bn_input.text().strip() or None,
            "gender": self.gender_combo.currentText(),
            "date_of_birth": dob,
            "blood_group": self.blood_combo.currentText(),
            "phone": self.phone_input.text().strip() or None,
            "email": self.email_input.text().strip() or None,
            "birth_certificate_no": self.birth_cert_input.text().strip() or None,
            "roll_number": self.roll_spin.value(),
            "class_id": class_id,
            "section_id": section_id,
            "academic_year_id": ay_id,
            "group": self.group_combo.currentText(),
            "shift": self.shift_combo.currentText(),
            "status": self.status_combo.currentText(),
            "address": self.address_input.toPlainText().strip() or None,
            "city": self.city_input.text().strip() or "Dhaka",
            "district": self.district_input.text().strip() or "Dhaka",
            "previous_school": self.previous_school_input.text().strip() or None,
            "medical_notes": self.medical_notes_input.toPlainText().strip() or None,
            "emergency_contact": self.emergency_phone_input.text().strip() or None,
        }

        guardian_payload = {
            "guardian_name": guardian_name,
            "relation": self.relation_combo.currentText(),
            "father_name": self.father_name_input.text().strip() or None,
            "mother_name": self.mother_name_input.text().strip() or None,
            "guardian_phone": guardian_phone,
            "guardian_email": self.guardian_email_input.text().strip() or None,
            "guardian_occupation": self.guardian_occ_input.text().strip() or None,
        }

        db = SessionLocal()
        try:
            if self.is_edit_mode:
                success, stu, msg = StudentService.update_student(db, self.student_pk, stu_payload, guardian_payload)
            else:
                success, stu, msg = StudentService.admit_student(db, stu_payload, guardian_payload)

            if success:
                QMessageBox.information(self, "Success", msg)
                self.accept()
            else:
                QMessageBox.critical(self, "Error", msg)
        finally:
            db.close()
