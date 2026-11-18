"""
EduManage Pro - Hostel Bed Allocation & Check-In Dialog
Strict Double-Bed Allocation Prevention, Capacity & Gender Rules
"""

from datetime import date, datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QDateEdit, QPushButton, QMessageBox, QCheckBox, QLabel
)
from PySide6.QtCore import QDate
from app.repositories.hostel_repository import HostelRepository
from app.models.student import Student


class HostelAllocationDialog(QDialog):
    """Dialog to admit & check in a student into a vacant hostel room bed."""

    def __init__(self, parent=None, db_session=None, default_room_id=None):
        super().__init__(parent)
        self.db = db_session
        self.default_room_id = default_room_id
        self.setWindowTitle("Allocate & Check-In Student to Hostel Bed")
        self.resize(490, 460)
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
            label = f"{r.room_number} [{block_name} ({gender})] - {occupied}/{r.capacity} Beds ({r.status})"
            self.room_combo.addItem(label, r.id)

        if self.default_room_id:
            idx = self.room_combo.findData(self.default_room_id)
            if idx >= 0:
                self.room_combo.setCurrentIndex(idx)

        self.room_combo.currentIndexChanged.connect(self._reload_beds)
        form.addRow("Target Room:*", self.room_combo)

        # Dynamic Vacant Bed Selector (editable in case custom bed ID is desired)
        self.bed_combo = QComboBox()
        self.bed_combo.setEditable(True)
        form.addRow("Bed Identifier:*", self.bed_combo)

        self.bed_hint = QLabel("")
        self.bed_hint.setStyleSheet("color: #64748B; font-size: 11px;")
        form.addRow("", self.bed_hint)

        # Student Selector
        self.student_combo = QComboBox()
        students = self.db.query(Student).order_by(Student.first_name.asc()).all()
        for s in students:
            gender_label = f"{s.gender}" if s.gender else "N/A"
            self.student_combo.addItem(f"{s.student_id} - {s.first_name} {s.last_name} ({gender_label})", s.id)
        form.addRow("Student:*", self.student_combo)

        # Mess Plan
        self.mess_plan_combo = QComboBox()
        self.mess_plan_combo.addItem("Default Hostel Mess Rate", None)
        for mp in HostelRepository.get_mess_plans(self.db):
            self.mess_plan_combo.addItem(f"{mp.plan_name} (৳ {mp.monthly_fee:,.0f}/mo)", mp.id)
        form.addRow("Mess Plan:", self.mess_plan_combo)

        self.mess_opted_check = QCheckBox("Boarder subscribed to Hostel Dining / Mess")
        self.mess_opted_check.setChecked(True)
        form.addRow("Dining Opted:", self.mess_opted_check)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Check-In Date:", self.date_edit)

        self.time_edit = QLineEdit()
        self.time_edit.setText(datetime.now().strftime("%I:%M %p"))
        form.addRow("Check-In Time:", self.time_edit)

        self.contact_edit = QLineEdit()
        self.contact_edit.setPlaceholderText("Guardian Mobile Number")
        form.addRow("Guardian Contact:", self.contact_edit)

        self.emergency_edit = QLineEdit()
        self.emergency_edit.setPlaceholderText("Hostel Emergency Contact")
        form.addRow("Emergency Phone:", self.emergency_edit)

        self.remarks_edit = QLineEdit()
        self.remarks_edit.setPlaceholderText("Check-in remarks, medical notes, key issued...")
        form.addRow("Check-In Notes:", self.remarks_edit)

        layout.addLayout(form)
        self._reload_beds()

        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Confirm Bed Allocation & Check-In")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _reload_beds(self):
        self.bed_combo.clear()
        room_id = self.room_combo.currentData()
        if not room_id:
            return
        beds = HostelRepository.get_beds(self.db, room_id=room_id)
        vacant = [b for b in beds if b.status == "Available"]
        occupied = [b for b in beds if b.status != "Available"]
        for b in vacant:
            self.bed_combo.addItem(b.bed_number, b.bed_number)
        if not vacant and not beds:
            self.bed_combo.addItem("Bed-1", "Bed-1")
        occ_names = ", ".join(f"{b.bed_number} ({b.status})" for b in occupied)
        self.bed_hint.setText(
            f"Vacant: {len(vacant)} | Unavailable: {occ_names or 'None'}"
        )

    def _save(self):
        room_id = self.room_combo.currentData()
        student_id = self.student_combo.currentData()
        bed_number = (self.bed_combo.currentData() or self.bed_combo.currentText() or "").strip()

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
                check_in_date=adm_date,
                check_in_time=self.time_edit.text().strip() or None,
                check_in_notes=self.remarks_edit.text().strip() or None,
                mess_plan_id=self.mess_plan_combo.currentData(),
                mess_opted=self.mess_opted_check.isChecked(),
                guardian_contact=self.contact_edit.text().strip() or None,
                emergency_phone=self.emergency_edit.text().strip() or None,
                remarks=self.remarks_edit.text().strip() or None,
            )
            QMessageBox.information(self, "Success", "Student allocated and checked in successfully!")
            self.accept()
        except ValueError as ve:
            QMessageBox.warning(self, "Allocation Denied", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to allocate bed: {str(e)}")

