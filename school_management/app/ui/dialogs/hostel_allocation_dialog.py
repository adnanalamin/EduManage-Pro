"""
EduManage Pro - Hostel Bed Allocation Dialog
Phase 12: Commuter/Resident Bed Allocation with Strict Capacity & Duplicate Rules
"""

from typing import Optional
from datetime import date
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QDateEdit, QPushButton, QMessageBox, QLabel
)
from PySide6.QtCore import QDate
from app.repositories.hostel_repository import HostelRepository
from app.models.student import Student


class HostelAllocationDialog(QDialog):
    """Dialog to admit a student into a hostel room bed."""

    def __init__(self, parent=None, db_session=None, default_room_id=None):
        super().__init__(parent)
        self.db = db_session
        self.default_room_id = default_room_id
        self.setWindowTitle("Allocate Student to Hostel Bed")
        self.resize(460, 380)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Room Selector
        self.room_combo = QComboBox()
        rooms = HostelRepository.get_all_rooms(self.db)
        for r in rooms:
            block_name = r.block.block_name if r.block else "N/A"
            gender = r.block.gender_type if r.block else ""
            occupied = len([a for a in r.allocations if a.status == "Active"])
            label = f"{r.room_number} [{block_name} ({gender})] - {occupied}/{r.capacity} Beds"
            self.room_combo.addItem(label, r.id)

        if self.default_room_id:
            idx = self.room_combo.findData(self.default_room_id)
            if idx >= 0:
                self.room_combo.setCurrentIndex(idx)

        form.addRow("Target Room:*", self.room_combo)

        # Student Selector
        self.student_combo = QComboBox()
        students = self.db.query(Student).order_by(Student.first_name.asc()).all()
        for s in students:
            gender_label = f", {s.gender}" if s.gender else ""
            self.student_combo.addItem(f"{s.student_id} - {s.first_name} {s.last_name} ({gender_label})", s.id)
        form.addRow("Student:*", self.student_combo)

        self.bed_edit = QLineEdit()
        self.bed_edit.setPlaceholderText("e.g., Bed-1, Bed-A, Lower Bunk")
        self.bed_edit.setText("Bed-1")
        form.addRow("Bed Identifier:*", self.bed_edit)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Admission Date:", self.date_edit)

        self.contact_edit = QLineEdit()
        self.contact_edit.setPlaceholderText("Guardian Mobile Number")
        form.addRow("Guardian Contact:", self.contact_edit)

        self.emergency_edit = QLineEdit()
        self.emergency_edit.setPlaceholderText("Hostel Emergency Contact")
        form.addRow("Emergency Phone:", self.emergency_edit)

        self.remarks_edit = QLineEdit()
        self.remarks_edit.setPlaceholderText("Optional notes or medical dietary considerations")
        form.addRow("Remarks:", self.remarks_edit)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Confirm Bed Allocation")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _save(self):
        room_id = self.room_combo.currentData()
        student_id = self.student_combo.currentData()
        bed_number = self.bed_edit.text().strip()

        if not room_id:
            QMessageBox.warning(self, "Validation Error", "Please select a hostel room.")
            return

        if not student_id:
            QMessageBox.warning(self, "Validation Error", "Please select a student.")
            return

        if not bed_number:
            QMessageBox.warning(self, "Validation Error", "Bed Identifier cannot be empty.")
            return

        qdate = self.date_edit.date()
        adm_date = date(qdate.year(), qdate.month(), qdate.day())

        try:
            HostelRepository.allocate_student_to_room(
                session=self.db,
                room_id=room_id,
                student_id=student_id,
                bed_number=bed_number,
                admission_date=adm_date,
                guardian_contact=self.contact_edit.text().strip() or None,
                emergency_phone=self.emergency_edit.text().strip() or None,
                remarks=self.remarks_edit.text().strip() or None
            )
            QMessageBox.information(self, "Success", "Student successfully admitted to hostel bed!")
            self.accept()
        except ValueError as ve:
            QMessageBox.warning(self, "Allocation Denied", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to allocate bed: {str(e)}")
