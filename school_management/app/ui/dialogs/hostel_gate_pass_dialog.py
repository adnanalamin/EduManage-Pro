"""
EduManage Pro - Hostel Gate Pass Dialog
Phase 12: PySide6 Modal for Issuing Boarder Gate Passes / Outpasses
"""

from typing import Optional
from datetime import date
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QDateEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import QDate
from app.repositories.hostel_repository import HostelRepository


class HostelGatePassDialog(QDialog):
    """Dialog to issue warden-approved gate pass for a resident boarder."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Issue Hostel Gate Pass / Outpass")
        self.resize(440, 320)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Resident Boarder Selector
        self.alloc_combo = QComboBox()
        allocations = HostelRepository.get_active_allocations(self.db)
        for a in allocations:
            student_name = f"{a.student.first_name} {a.student.last_name}" if a.student else f"Student #{a.student_id}"
            room_no = a.room.room_number if a.room else "N/A"
            self.alloc_combo.addItem(f"{student_name} (Room {room_no}, {a.bed_number})", a.id)
        form.addRow("Resident Boarder:*", self.alloc_combo)

        self.purpose_combo = QComboBox()
        self.purpose_combo.setEditable(True)
        self.purpose_combo.addItems([
            "Home Visit (Weekend Leave)",
            "Medical Emergency / Doctor Appointment",
            "Local Market / Personal Errands",
            "School Sports / Competition",
            "Academic Seminar / Excursion"
        ])
        form.addRow("Reason / Purpose:*", self.purpose_combo)

        self.leave_date = QDateEdit()
        self.leave_date.setCalendarPopup(True)
        self.leave_date.setDate(QDate.currentDate())
        form.addRow("Departure Date:", self.leave_date)

        self.return_date = QDateEdit()
        self.return_date.setCalendarPopup(True)
        self.return_date.setDate(QDate.currentDate().addDays(2))
        form.addRow("Expected Return:*", self.return_date)

        self.remarks_edit = QLineEdit()
        self.remarks_edit.setPlaceholderText("Parent / Guardian approval notes")
        form.addRow("Warden Remarks:", self.remarks_edit)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        issue_btn = QPushButton("Approve & Issue Gate Pass")
        issue_btn.setDefault(True)
        issue_btn.clicked.connect(self._save)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(issue_btn)
        layout.addLayout(btn_layout)

    def _save(self):
        alloc_id = self.alloc_combo.currentData()
        if not alloc_id:
            QMessageBox.warning(self, "Validation Error", "Please select a resident boarder.")
            return

        purpose = self.purpose_combo.currentText().strip()
        if not purpose:
            QMessageBox.warning(self, "Validation Error", "Purpose cannot be empty.")
            return

        l_qdate = self.leave_date.date()
        leave_dt = date(l_qdate.year(), l_qdate.month(), l_qdate.day())

        r_qdate = self.return_date.date()
        return_dt = date(r_qdate.year(), r_qdate.month(), r_qdate.day())

        if return_dt < leave_dt:
            QMessageBox.warning(self, "Validation Error", "Expected Return Date cannot be earlier than Departure Date.")
            return

        try:
            gp = HostelRepository.create_gate_pass(
                session=self.db,
                allocation_id=alloc_id,
                purpose=purpose,
                leave_date=leave_dt,
                expected_return_date=return_dt,
                remarks=self.remarks_edit.text().strip() or None
            )
            QMessageBox.information(self, "Gate Pass Issued", f"Gate Pass #{gp.pass_number} successfully authorized.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to issue gate pass: {str(e)}")
