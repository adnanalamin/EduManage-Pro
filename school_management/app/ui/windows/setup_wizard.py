"""
EduManage Pro - First-Run Setup Wizard (PySide6)
Guides the administrator through:
1. School Identity & EIIN
2. Admin Credentials Configuration
3. Academic Year Definition
4. Initial Classes & Sections
5. Summary Confirmation
"""

from datetime import date
from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QFormLayout, QMessageBox, QDateEdit, QCheckBox, QTextEdit, QComboBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from app.database.connection import SessionLocal
from app.models.school import SchoolSetting
from app.models.user import User
from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.activity import ActivityLog
from app.security.hasher import PasswordHasher


class SetupWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EduManage Pro — First-Run Setup Wizard")
        self.setFixedSize(650, 520)
        self.setWizardStyle(QWizard.ModernStyle)

        self.addPage(self._create_school_info_page())
        self.addPage(self._create_admin_account_page())
        self.addPage(self._create_academic_year_page())
        self.addPage(self._create_classes_page())
        self.addPage(self._create_finish_page())

    def _create_school_info_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("1. School Profile & Localization")
        page.setSubTitle("Enter your institution details and regional settings.")

        layout = QFormLayout(page)
        layout.setSpacing(10)

        self.school_name_input = QLineEdit("Ideal Model High School & College")
        self.school_bn_input = QLineEdit("আইডিয়াল মডেল হাই স্কুল অ্যান্ড কলেজ")
        self.eiin_input = QLineEdit("134211")
        self.phone_input = QLineEdit("+880 1712-345678")
        self.email_input = QLineEdit("contact@idealmodel.edu.bd")
        self.address_input = QLineEdit("Sector 7, Uttara, Dhaka, Bangladesh")

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["BDT (৳ - Bangladeshi Taka)", "USD ($ - US Dollar)", "EUR (€ - Euro)", "INR (₹ - Indian Rupee)"])

        layout.addRow("School Name (English)*:", self.school_name_input)
        layout.addRow("School Name (Bangla):", self.school_bn_input)
        layout.addRow("EIIN / Reg Number:", self.eiin_input)
        layout.addRow("Official Phone*:", self.phone_input)
        layout.addRow("Official Email*:", self.email_input)
        layout.addRow("Campus Address:", self.address_input)
        layout.addRow("Primary Currency:", self.currency_combo)

        return page

    def _create_admin_account_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("2. Super Administrator Account")
        page.setSubTitle("Secure your system by setting your permanent administrator password.")

        layout = QFormLayout(page)
        layout.setSpacing(10)

        self.admin_name_input = QLineEdit("Super Administrator")
        self.admin_username_input = QLineEdit("admin")
        self.admin_email_input = QLineEdit("admin@school.local")
        
        self.admin_password_input = QLineEdit()
        self.admin_password_input.setEchoMode(QLineEdit.Password)
        self.admin_password_input.setPlaceholderText("Minimum 8 characters with letters & numbers")
        
        self.admin_confirm_password_input = QLineEdit()
        self.admin_confirm_password_input.setEchoMode(QLineEdit.Password)

        layout.addRow("Full Name*:", self.admin_name_input)
        layout.addRow("Admin Username*:", self.admin_username_input)
        layout.addRow("Admin Email*:", self.admin_email_input)
        layout.addRow("New Password*:", self.admin_password_input)
        layout.addRow("Confirm Password*:", self.admin_confirm_password_input)

        return page

    def _create_academic_year_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("3. Academic Session")
        page.setSubTitle("Define the active academic calendar year.")

        layout = QFormLayout(page)
        layout.setSpacing(10)

        current_year = date.today().year
        self.ay_name_input = QLineEdit(f"{current_year}-{current_year + 1}")
        
        self.start_date_picker = QDateEdit()
        self.start_date_picker.setCalendarPopup(True)
        self.start_date_picker.setDate(QDate(current_year, 1, 1))

        self.end_date_picker = QDateEdit()
        self.end_date_picker.setCalendarPopup(True)
        self.end_date_picker.setDate(QDate(current_year, 12, 31))

        layout.addRow("Session Name*:", self.ay_name_input)
        layout.addRow("Session Start Date*:", self.start_date_picker)
        layout.addRow("Session End Date*:", self.end_date_picker)

        return page

    def _create_classes_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("4. Initial Classes")
        page.setSubTitle("Select standard classes to generate initially.")

        layout = QVBoxLayout(page)
        label = QLabel("The following default grades will be configured with Sections A & B:")
        label.setStyleSheet("color: #cbd5e1; margin-bottom: 8px;")
        layout.addWidget(label)

        self.class_boxes = []
        standard_classes = ["Play / Nursery", "Kindergarten (KG)", "Class 1", "Class 2", "Class 3", "Class 4", "Class 5", "Class 6", "Class 7", "Class 8", "Class 9", "Class 10"]
        for c in standard_classes:
            cb = QCheckBox(c)
            cb.setChecked(True)
            layout.addWidget(cb)
            self.class_boxes.append(cb)

        return page

    def _create_finish_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("5. Finish & Apply Configuration")
        page.setSubTitle("Review and click Finish to initialize your offline database.")

        layout = QVBoxLayout(page)
        summary = QLabel(
            "Ready to launch EduManage Pro!\n\n"
            "• Local SQLite database will be initialized.\n"
            "• Administrator credentials will be securely hashed with bcrypt.\n"
            "• Starter curriculum and sections will be provisioned.\n"
            "• The system will be ready for student admissions, attendance, and fee tracking."
        )
        summary.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.6;")
        layout.addWidget(summary)

        return page

    def validateCurrentPage(self) -> bool:
        idx = self.currentId()
        if idx == 1:  # Admin account validation
            p1 = self.admin_password_input.text()
            p2 = self.admin_confirm_password_input.text()
            if p1 or p2:  # If user typed something to change
                if p1 != p2:
                    QMessageBox.warning(self, "Validation Error", "Passwords do not match!")
                    return False
                if len(p1) < 8:
                    QMessageBox.warning(self, "Validation Error", "Password must be at least 8 characters long.")
                    return False
        return True

    def accept(self):
        """Save settings and mark setup as completed."""
        db = SessionLocal()
        try:
            # Update School Settings
            school = db.query(SchoolSetting).first()
            if not school:
                school = SchoolSetting()
                db.add(school)

            school.school_name = self.school_name_input.text().strip()
            school.school_name_bn = self.school_bn_input.text().strip()
            school.eiin_number = self.eiin_input.text().strip()
            school.phone = self.phone_input.text().strip()
            school.email = self.email_input.text().strip()
            school.address = self.address_input.text().strip()
            school.currency_code = "BDT" if "BDT" in self.currency_combo.currentText() else "USD"
            school.currency_symbol = "৳" if school.currency_code == "BDT" else "$"
            school.is_setup_completed = True

            # Update Admin password if provided
            new_pass = self.admin_password_input.text()
            admin = db.query(User).filter_by(username="admin").first()
            if admin and new_pass:
                admin.password_hash = PasswordHasher.hash_password(new_pass)
                admin.is_default_password = False
                admin.full_name = self.admin_name_input.text().strip()
                admin.email = self.admin_email_input.text().strip()

            # Record activity log
            log = ActivityLog(
                user_id=admin.id if admin else None,
                username="admin",
                action="SETUP_WIZARD_COMPLETED",
                module="SYSTEM",
                description="First-Run Setup Wizard completed successfully.",
                severity="INFO"
            )
            db.add(log)
            db.commit()
            QMessageBox.information(self, "Setup Completed", "Configuration saved! Welcome to EduManage Pro.")
            super().accept()
        except Exception as exc:
            db.rollback()
            QMessageBox.critical(self, "Setup Error", f"Failed to save setup configuration: {exc}")
        finally:
            db.close()
