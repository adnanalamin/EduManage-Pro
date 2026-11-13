"""
EduManage Pro - Issue Certificate Modal Dialog (PySide6)
Phase 15: Allows issuing Transfer, Character, Testimonial, Bonafide, Merit & Staff Experience Certificates.
"""

from datetime import date
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QComboBox,
    QLineEdit, QTextEdit, QPushButton, QDateEdit, QCheckBox, QLabel, QMessageBox
)
from PySide6.QtCore import QDate
from app.models.student import Student
from app.models.staff import Teacher, Staff
from app.services.certificate_service import CertificateService


class CertificateIssueDialog(QDialog):
    def __init__(self, db_session, parent=None):
        super().__init__(parent)
        self.db = db_session
        self.issued_certificate = None
        self.setWindowTitle("Issue Official Certificate / Credential")
        self.setMinimumWidth(520)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("📜 Generate & Register Official Credential")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #1E3A8A;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(10)

        self.cmb_type = QComboBox()
        self.cmb_type.addItems(CertificateService.CERTIFICATE_TYPES)
        self.cmb_type.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Certificate Type:", self.cmb_type)

        self.cmb_recipient_kind = QComboBox()
        self.cmb_recipient_kind.addItems(["Student", "Teacher", "Staff"])
        self.cmb_recipient_kind.currentTextChanged.connect(self._populate_recipients)
        form.addRow("Recipient Category:", self.cmb_recipient_kind)

        self.cmb_recipient = QComboBox()
        form.addRow("Select Recipient:", self.cmb_recipient)

        self.cmb_conduct = QComboBox()
        self.cmb_conduct.addItems(["Exemplary", "Very Good", "Good", "Satisfactory"])
        form.addRow("Conduct / Character:", self.cmb_conduct)

        self.txt_purpose = QLineEdit()
        self.txt_purpose.setPlaceholderText("e.g., Higher Studies, Passport Application, Science Fair Distinction")
        form.addRow("Purpose / Achievement:", self.txt_purpose)

        self.date_leaving = QDateEdit()
        self.date_leaving.setCalendarPopup(True)
        self.date_leaving.setDate(QDate.currentDate())
        form.addRow("Effective / Leaving Date:", self.date_leaving)

        self.chk_mark_transferred = QCheckBox("Mark student enrollment status as 'Transferred' (for Transfer Certificate)")
        form.addRow("", self.chk_mark_transferred)

        self.txt_remarks = QTextEdit()
        self.txt_remarks.setMaximumHeight(70)
        self.txt_remarks.setPlaceholderText("Optional official citation or registrar remarks...")
        form.addRow("Official Remarks:", self.txt_remarks)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_issue = QPushButton("✅ Issue & Sign Certificate")
        btn_issue.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        btn_issue.clicked.connect(self._handle_issue)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_issue)
        layout.addLayout(btn_row)

        self._populate_recipients()
        self._on_type_changed(self.cmb_type.currentText())

    def _on_type_changed(self, ctype: str):
        is_tc = ctype == "Transfer Certificate"
        is_staff_letter = ctype == "Staff Experience Letter"
        self.chk_mark_transferred.setVisible(is_tc)
        self.date_leaving.setEnabled(is_tc or is_staff_letter)
        if is_staff_letter and self.cmb_recipient_kind.currentText() == "Student":
            self.cmb_recipient_kind.setCurrentText("Teacher")

    def _populate_recipients(self):
        self.cmb_recipient.clear()
        if not self.db:
            return
        kind = self.cmb_recipient_kind.currentText()
        if kind == "Student":
            for s in self.db.query(Student).order_by(Student.full_name).all():
                cls_name = s.school_class.name if s.school_class else "Class"
                self.cmb_recipient.addItem(f"{s.full_name} ({s.student_id} - {cls_name})", s.id)
        elif kind == "Teacher":
            for t in self.db.query(Teacher).order_by(Teacher.full_name).all():
                self.cmb_recipient.addItem(f"{t.full_name} ({t.teacher_id} - {t.designation})", t.id)
        else:
            for st in self.db.query(Staff).order_by(Staff.full_name).all():
                self.cmb_recipient.addItem(f"{st.full_name} ({st.staff_id} - {st.position})", st.id)

    def _handle_issue(self):
        recipient_id = self.cmb_recipient.currentData()
        if not recipient_id:
            QMessageBox.warning(self, "Validation", "Please select a valid recipient.")
            return

        ctype = self.cmb_type.currentText()
        kind = self.cmb_recipient_kind.currentText()
        purpose = self.txt_purpose.text().strip() or "Official Institutional Verification"
        conduct = self.cmb_conduct.currentText()
        remarks = self.txt_remarks.toPlainText().strip()
        qdt = self.date_leaving.date()
        leaving_dt = date(qdt.year(), qdt.month(), qdt.day()) if self.date_leaving.isEnabled() else None

        try:
            if kind == "Student":
                self.issued_certificate = CertificateService.issue_student_certificate(
                    self.db,
                    student_id=recipient_id,
                    certificate_type=ctype,
                    conduct_grade=conduct,
                    reason_or_purpose=purpose,
                    leaving_date=leaving_dt,
                    remarks=remarks,
                    mark_student_transferred=self.chk_mark_transferred.isChecked(),
                )
            else:
                self.issued_certificate = CertificateService.issue_staff_certificate(
                    self.db,
                    staff_id=recipient_id,
                    certificate_type=ctype,
                    conduct_grade=conduct,
                    reason_or_purpose=purpose,
                    leaving_date=leaving_dt,
                    remarks=remarks,
                    is_teacher=(kind == "Teacher"),
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Issuance Failed", str(e))
