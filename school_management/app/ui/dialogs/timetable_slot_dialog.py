"""
EduManage Pro - Timetable Slot Assignment Dialog
Phase 9: PySide6 Modal for Assigning Teaching Periods with Conflict Detection
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QPushButton, QLabel, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from app.models.timetable import PeriodSlot, TimetableEntry
from app.models.academic import SchoolClass, Section, Subject
from app.models.staff import Teacher
from app.repositories.timetable_repository import TimetableRepository
from app.services.timetable_service import TimetableService, STANDARD_DAYS


class TimetableSlotDialog(QDialog):
    """Dialog for creating or editing a class teaching slot with real-time clash checking."""

    def __init__(
        self,
        db_session: Session,
        class_id: int,
        section_id: Optional[int] = None,
        default_day: str = "Sunday",
        default_period_id: Optional[int] = None,
        entry: Optional[TimetableEntry] = None,
        parent=None
    ):
        super().__init__(parent)
        self.db_session = db_session
        self.class_id = class_id
        self.section_id = section_id
        self.entry = entry

        self.setWindowTitle("Edit Timetable Slot" if entry else "Assign Timetable Teaching Slot")
        self.setMinimumWidth(450)
        self._setup_ui(default_day, default_period_id)

    def _setup_ui(self, default_day: str, default_period_id: Optional[int]):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header Info Banner
        header = QLabel("Teaching Period Assignment & Conflict Detection")
        header.setStyleSheet("font-weight: bold; font-size: 14px; color: #1E3A8A;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(10)

        # Day Selector
        self.day_combo = QComboBox()
        self.day_combo.addItems(STANDARD_DAYS)
        if self.entry:
            idx = self.day_combo.findText(self.entry.day_of_week)
            if idx >= 0:
                self.day_combo.setCurrentIndex(idx)
        else:
            idx = self.day_combo.findText(default_day)
            if idx >= 0:
                self.day_combo.setCurrentIndex(idx)
        form.addRow("Day of Week:*", self.day_combo)

        # Period Slot Selector
        self.period_combo = QComboBox()
        periods = TimetableRepository.get_period_slots(self.db_session)
        self.teaching_periods = [p for p in periods if not p.is_break]
        for p in self.teaching_periods:
            self.period_combo.addItem(f"{p.name} ({p.start_time} - {p.end_time})", p.id)

        if self.entry:
            for i in range(self.period_combo.count()):
                if self.period_combo.itemData(i) == self.entry.period_slot_id:
                    self.period_combo.setCurrentIndex(i)
                    break
        elif default_period_id:
            for i in range(self.period_combo.count()):
                if self.period_combo.itemData(i) == default_period_id:
                    self.period_combo.setCurrentIndex(i)
                    break
        form.addRow("Period Slot:*", self.period_combo)

        # Subject Selector
        self.subject_combo = QComboBox()
        subjects = self.db_session.query(Subject).filter(Subject.class_id == self.class_id).all()
        for s in subjects:
            self.subject_combo.addItem(f"{s.name} ({s.code})", s.id)
        if self.entry:
            for i in range(self.subject_combo.count()):
                if self.subject_combo.itemData(i) == self.entry.subject_id:
                    self.subject_combo.setCurrentIndex(i)
                    break
        form.addRow("Subject:*", self.subject_combo)

        # Teacher Selector
        self.teacher_combo = QComboBox()
        teachers = self.db_session.query(Teacher).filter(Teacher.status == "Active").all()
        for t in teachers:
            self.teacher_combo.addItem(f"{t.name} ({t.employee_id})", t.id)
        if self.entry:
            for i in range(self.teacher_combo.count()):
                if self.teacher_combo.itemData(i) == self.entry.teacher_id:
                    self.teacher_combo.setCurrentIndex(i)
                    break
        form.addRow("Teacher:*", self.teacher_combo)

        # Room Number
        self.room_edit = QLineEdit()
        self.room_edit.setPlaceholderText("e.g. Room 301, Science Lab 1, ICT Lab")
        self.room_edit.setText(self.entry.room_number if self.entry else "Room 301")
        form.addRow("Room / Hall:*", self.room_edit)

        # Notes
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Optional remarks...")
        if self.entry and self.entry.notes:
            self.notes_edit.setText(self.entry.notes)
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)

        # Clash Warning Label
        self.warning_label = QLabel()
        self.warning_label.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: bold;")
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()
        layout.addWidget(self.warning_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Assignment")
        self.btn_save.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 16px;")
        self.btn_save.clicked.connect(self._save_slot)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _save_slot(self):
        day = self.day_combo.currentText()
        period_slot_id = self.period_combo.currentData()
        subject_id = self.subject_combo.currentData()
        teacher_id = self.teacher_combo.currentData()
        room = self.room_edit.text().strip()

        if not period_slot_id or not subject_id or not teacher_id or not room:
            QMessageBox.warning(self, "Validation Error", "All fields marked with an asterisk are required.")
            return

        entry_id = self.entry.id if self.entry else None

        entry, conflicts = TimetableService.assign_timetable_slot(
            session=self.db_session,
            academic_year_id=1,
            class_id=self.class_id,
            section_id=self.section_id,
            day_of_week=day,
            period_slot_id=period_slot_id,
            subject_id=subject_id,
            teacher_id=teacher_id,
            room_number=room,
            notes=self.notes_edit.text().strip(),
            entry_id=entry_id
        )

        if conflicts:
            msg = "\n".join(conflicts)
            self.warning_label.setText(f"Conflict Detected:\n{msg}")
            self.warning_label.show()
            QMessageBox.critical(self, "Schedule Collision Warning", f"Cannot assign slot due to conflicts:\n\n{msg}")
            return

        self.accept()
