"""
EduManage Pro - Period Slot Configuration Dialog
Phase 9: PySide6 Modal for Managing Period Timings & Break Slots
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QSpinBox, QCheckBox, QPushButton, QLabel, QMessageBox
)
from sqlalchemy.orm import Session
from app.models.timetable import PeriodSlot
from app.repositories.timetable_repository import TimetableRepository


class PeriodConfigDialog(QDialog):
    """Dialog to create or edit a school period time slot."""

    def __init__(self, db_session: Session, slot: Optional[PeriodSlot] = None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.slot = slot

        self.setWindowTitle("Edit Period Slot" if slot else "Add New Period Slot")
        self.setMinimumWidth(380)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("School Bell Timing Configuration")
        header.setStyleSheet("font-weight: bold; font-size: 13px; color: #1E3A8A;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(8)

        self.num_spin = QSpinBox()
        self.num_spin.setRange(0, 50)
        self.num_spin.setValue(self.slot.period_number if self.slot else 1)
        form.addRow("Period Number (0 for Break):", self.num_spin)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. 1st Period, Assembly, Tiffin")
        self.name_edit.setText(self.slot.name if self.slot else "")
        form.addRow("Period Name:*", self.name_edit)

        self.start_edit = QLineEdit()
        self.start_edit.setPlaceholderText("e.g. 08:45 AM")
        self.start_edit.setText(self.slot.start_time if self.slot else "08:45 AM")
        form.addRow("Start Time:*", self.start_edit)

        self.end_edit = QLineEdit()
        self.end_edit.setPlaceholderText("e.g. 09:30 AM")
        self.end_edit.setText(self.slot.end_time if self.slot else "09:30 AM")
        form.addRow("End Time:*", self.end_edit)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 180)
        self.duration_spin.setValue(self.slot.duration_minutes if self.slot else 45)
        form.addRow("Duration (Minutes):", self.duration_spin)

        self.break_chk = QCheckBox("This is a Break / Non-Teaching Interval (Assembly, Tiffin, Recess)")
        self.break_chk.setChecked(self.slot.is_break if self.slot else False)
        form.addRow("", self.break_chk)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save Period")
        btn_save.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 16px;")
        btn_save.clicked.connect(self._save)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    def _save(self):
        name = self.name_edit.text().strip()
        start = self.start_edit.text().strip()
        end = self.end_edit.text().strip()

        if not name or not start or not end:
            QMessageBox.warning(self, "Validation Error", "Name, Start Time, and End Time are required.")
            return

        if self.slot:
            TimetableRepository.update_period_slot(
                self.db_session,
                slot_id=self.slot.id,
                period_number=self.num_spin.value(),
                name=name,
                start_time=start,
                end_time=end,
                duration_minutes=self.duration_spin.value(),
                is_break=self.break_chk.isChecked()
            )
        else:
            TimetableRepository.create_period_slot(
                self.db_session,
                period_number=self.num_spin.value(),
                name=name,
                start_time=start,
                end_time=end,
                duration_minutes=self.duration_spin.value(),
                is_break=self.break_chk.isChecked(),
                shift="Morning",
                academic_year_id=1
            )

        self.accept()
