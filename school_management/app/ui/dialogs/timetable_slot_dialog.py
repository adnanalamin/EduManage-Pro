"""
EduManage Pro - Timetable Slot Assignment & Manual Editing Dialog
Supports Multi-Shift, Academic Year, AcademicRoom catalog selection, Live Conflict Checker
(Teacher, Room, Class & Cross-Shift Overlap), and manual Delete Slot.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QPushButton, QLabel, QMessageBox
)
from sqlalchemy.orm import Session
from app.models.academic import AcademicRoom, Subject
from app.models.staff import Teacher
from app.models.timetable import PeriodSlot, TimetableEntry
from app.repositories.timetable_repository import TimetableRepository
from app.services.timetable_service import TimetableService, STANDARD_DAYS


class TimetableSlotDialog(QDialog):
    """Dialog for assigning, editing, or deleting a class teaching slot with real-time clash checking."""

    def __init__(
        self,
        db_session: Session,
        class_id: int,
        section_id: Optional[int] = None,
        default_day: str = "Sunday",
        default_period_id: Optional[int] = None,
        entry: Optional[TimetableEntry] = None,
        academic_year_id: int = 1,
        shift: str = "Morning",
        parent=None,
    ):
        super().__init__(parent)
        self.db_session = db_session
        self.class_id = class_id
        self.section_id = section_id
        self.entry = entry
        self.academic_year_id = (entry.academic_year_id if entry else academic_year_id) or 1
        self.shift = (entry.shift if entry else shift) or "Morning"

        self.setWindowTitle("Edit Timetable Slot" if entry else "Assign Timetable Teaching Slot")
        self.setMinimumWidth(480)
        self._setup_ui(default_day, default_period_id)

    def _setup_ui(self, default_day: str, default_period_id: Optional[int]):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel(f"Teaching Period Assignment ({self.shift} Shift) — Conflict Guard Active")
        header.setStyleSheet("font-weight: bold; font-size: 14px; color: #1E3A8A;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(10)

        # Day Selector
        self.day_combo = QComboBox()
        self.day_combo.addItems(STANDARD_DAYS)
        target_day = self.entry.day_of_week if self.entry else default_day
        idx = self.day_combo.findText(target_day)
        if idx >= 0:
            self.day_combo.setCurrentIndex(idx)
        form.addRow("Day of Week *:", self.day_combo)

        # Period Slot Selector (scoped by shift)
        self.period_combo = QComboBox()
        periods = TimetableRepository.get_period_slots(
            self.db_session, shift=self.shift, academic_year_id=self.academic_year_id
        )
        if not periods:
            periods = TimetableRepository.get_period_slots(self.db_session)
        self.teaching_periods = [p for p in periods if not p.is_break]
        for p in self.teaching_periods:
            self.period_combo.addItem(f"{p.name} ({p.start_time} - {p.end_time})", p.id)

        target_pid = self.entry.period_slot_id if self.entry else default_period_id
        if target_pid:
            idx = self.period_combo.findData(target_pid)
            if idx >= 0:
                self.period_combo.setCurrentIndex(idx)
        form.addRow("Period Slot *:", self.period_combo)

        # Subject Selector
        self.subject_combo = QComboBox()
        subjects = self.db_session.query(Subject).filter(Subject.class_id == self.class_id, Subject.is_deleted == False).all()
        for s in subjects:
            self.subject_combo.addItem(f"{s.name} ({s.code})", s.id)
        if self.entry:
            idx = self.subject_combo.findData(self.entry.subject_id)
            if idx >= 0:
                self.subject_combo.setCurrentIndex(idx)
        form.addRow("Subject *:", self.subject_combo)

        # Teacher Selector
        self.teacher_combo = QComboBox()
        teachers = self.db_session.query(Teacher).filter(Teacher.status == "Active", Teacher.is_deleted == False).all()
        for t in teachers:
            self.teacher_combo.addItem(f"{t.name} ({t.employee_id})", t.id)
        if self.entry:
            idx = self.teacher_combo.findData(self.entry.teacher_id)
            if idx >= 0:
                self.teacher_combo.setCurrentIndex(idx)
        form.addRow("Teacher *:", self.teacher_combo)

        # Room Selector + Custom Override
        self.room_combo = QComboBox()
        self.room_combo.addItem("-- Custom / Manual Room --", None)
        for rm in self.db_session.query(AcademicRoom).filter(AcademicRoom.is_deleted == False, AcademicRoom.is_active == True).order_by(AcademicRoom.room_number.asc()).all():
            self.room_combo.addItem(f"{rm.room_number} ({rm.room_type}, Cap {rm.capacity})", rm.id)
        if self.entry and self.entry.room_id:
            idx = self.room_combo.findData(self.entry.room_id)
            if idx >= 0:
                self.room_combo.setCurrentIndex(idx)
        self.room_combo.currentIndexChanged.connect(self._on_room_combo_changed)
        form.addRow("Academic Room:", self.room_combo)

        self.room_edit = QLineEdit()
        self.room_edit.setPlaceholderText("e.g. Room 301, Science Lab 1, ICT Lab")
        self.room_edit.setText(self.entry.room_number if self.entry else "Room 301")
        form.addRow("Room Number *:", self.room_edit)

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Optional remarks...")
        if self.entry and self.entry.notes:
            self.notes_edit.setText(self.entry.notes)
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)

        # Live Clash Warning Banner
        self.warning_label = QLabel()
        self.warning_label.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: bold;")
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()
        layout.addWidget(self.warning_label)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_check = QPushButton("Check Conflicts")
        self.btn_check.clicked.connect(self._check_conflicts_preview)
        btn_layout.addWidget(self.btn_check)

        if self.entry:
            self.btn_delete = QPushButton("Remove Slot")
            self.btn_delete.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; padding: 6px 12px;")
            self.btn_delete.clicked.connect(self._delete_slot)
            btn_layout.addWidget(self.btn_delete)

        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Assignment")
        self.btn_save.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 16px;")
        self.btn_save.clicked.connect(self._save_slot)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _on_room_combo_changed(self):
        rid = self.room_combo.currentData()
        if rid:
            rm = self.db_session.query(AcademicRoom).filter(AcademicRoom.id == rid).first()
            if rm:
                self.room_edit.setText(rm.room_number)

    def _check_conflicts_preview(self):
        day = self.day_combo.currentText()
        period_slot_id = self.period_combo.currentData()
        teacher_id = self.teacher_combo.currentData()
        room = self.room_edit.text().strip()
        room_id = self.room_combo.currentData()
        if not period_slot_id or not teacher_id or not room:
            return
        entry_id = self.entry.id if self.entry else None
        conflicts = TimetableRepository.check_conflicts(
            self.db_session,
            day_of_week=day,
            period_slot_id=period_slot_id,
            teacher_id=teacher_id,
            room_number=room,
            exclude_entry_id=entry_id,
            academic_year_id=self.academic_year_id,
            class_id=self.class_id,
            section_id=self.section_id,
            room_id=room_id,
            check_class_conflict=(entry_id is None),
        )
        if conflicts:
            self.warning_label.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: bold;")
            self.warning_label.setText("Conflicts Detected:\n" + "\n".join(conflicts))
            self.warning_label.show()
        else:
            self.warning_label.setStyleSheet("color: #059669; font-size: 11px; font-weight: bold;")
            self.warning_label.setText("No Teacher, Room, or Class conflicts detected for this slot.")
            self.warning_label.show()

    def _delete_slot(self):
        if not self.entry:
            return
        TimetableService.delete_slot_with_history(self.db_session, self.entry.id, reason="Removed via edit dialog")
        self.accept()

    def _save_slot(self):
        day = self.day_combo.currentText()
        period_slot_id = self.period_combo.currentData()
        subject_id = self.subject_combo.currentData()
        teacher_id = self.teacher_combo.currentData()
        room = self.room_edit.text().strip()
        room_id = self.room_combo.currentData()

        if not period_slot_id or not subject_id or not teacher_id or not room:
            QMessageBox.warning(self, "Validation Error", "All required fields must be selected.")
            return

        entry_id = self.entry.id if self.entry else None
        entry, conflicts = TimetableService.assign_timetable_slot(
            session=self.db_session,
            academic_year_id=self.academic_year_id,
            class_id=self.class_id,
            section_id=self.section_id,
            day_of_week=day,
            period_slot_id=period_slot_id,
            subject_id=subject_id,
            teacher_id=teacher_id,
            room_number=room,
            room_id=room_id,
            shift=self.shift,
            notes=self.notes_edit.text().strip(),
            entry_id=entry_id,
        )

        if conflicts:
            msg = "\n".join(conflicts)
            self.warning_label.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: bold;")
            self.warning_label.setText(f"Conflict Detected:\n{msg}")
            self.warning_label.show()
            QMessageBox.critical(self, "Schedule Collision Warning", f"Cannot assign slot due to conflicts:\n\n{msg}")
            return

        self.accept()
