"""
EduManage Pro - Event Form Dialog
Phase 13: PySide6 Modal for Scheduling Academic Events & Holidays
"""

from typing import Optional
from datetime import date
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QTextEdit, QDateEdit, QCheckBox, QPushButton, QMessageBox
)
from PySide6.QtCore import QDate
from app.repositories.notice_repository import NoticeRepository


class EventFormDialog(QDialog):
    """Dialog to schedule an academic calendar event, ceremony, or official holiday."""

    def __init__(self, parent=None, db_session=None, event=None):
        super().__init__(parent)
        self.db = db_session
        self.event = event
        self.setWindowTitle("Edit Academic Event" if event else "Schedule Academic Event / Holiday")
        self.resize(480, 440)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Event Name / Holiday Title")
        if self.event:
            self.title_edit.setText(self.event.event_title)
        form.addRow("Event Title:*", self.title_edit)

        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["Academic", "Holiday", "Exam", "Sports", "Cultural", "PTM", "Meeting", "Tour"])
        if self.event:
            self.cat_combo.setCurrentText(self.event.event_category)
        self.cat_combo.currentTextChanged.connect(self._on_cat_changed)
        form.addRow("Category:*", self.cat_combo)

        self.holiday_check = QCheckBox("Mark as Official School Holiday (Closed for Attendance)")
        if self.event:
            self.holiday_check.setChecked(self.event.is_holiday)
        form.addRow("", self.holiday_check)

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        if self.event and self.event.start_date:
            d = self.event.start_date
            self.start_date.setDate(QDate(d.year, d.month, d.day))
        else:
            self.start_date.setDate(QDate.currentDate())
        form.addRow("Start Date:*", self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        if self.event and self.event.end_date:
            d = self.event.end_date
            self.end_date.setDate(QDate(d.year, d.month, d.day))
        else:
            self.end_date.setDate(QDate.currentDate())
        form.addRow("End Date:*", self.end_date)

        time_box = QHBoxLayout()
        self.start_time = QLineEdit()
        self.start_time.setPlaceholderText("09:00 AM")
        if self.event and self.event.start_time:
            self.start_time.setText(self.event.start_time)
        self.end_time = QLineEdit()
        self.end_time.setPlaceholderText("01:00 PM")
        if self.event and self.event.end_time:
            self.end_time.setText(self.event.end_time)
        time_box.addWidget(self.start_time)
        time_box.addWidget(self.end_time)
        form.addRow("Timing (From - To):", time_box)

        self.venue_edit = QLineEdit()
        self.venue_edit.setPlaceholderText("Campus Main Auditorium, Playground, etc.")
        self.venue_edit.setText(self.event.venue if self.event else "Campus Main Auditorium")
        form.addRow("Venue / Location:", self.venue_edit)

        self.aud_combo = QComboBox()
        self.aud_combo.addItems(["All", "Students", "Teachers", "Parents", "Staff"])
        if self.event:
            self.aud_combo.setCurrentText(self.event.target_audience)
        form.addRow("Target Audience:", self.aud_combo)

        self.org_edit = QLineEdit()
        self.org_edit.setPlaceholderText("e.g. Cultural Affairs, Exam Board")
        self.org_edit.setText(self.event.organizer if self.event else "School Administration")
        form.addRow("Organizer:", self.org_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Event description, student attire, rules...")
        if self.event and self.event.description:
            self.desc_edit.setPlainText(self.event.description)
        form.addRow("Description:", self.desc_edit)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Event")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _on_cat_changed(self, text):
        if text == "Holiday":
            self.holiday_check.setChecked(True)

    def _save(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation Error", "Event Title cannot be empty.")
            return

        s_qdate = self.start_date.date()
        s_dt = date(s_qdate.year(), s_qdate.month(), s_qdate.day())

        e_qdate = self.end_date.date()
        e_dt = date(e_qdate.year(), e_qdate.month(), e_qdate.day())

        if e_dt < s_dt:
            QMessageBox.warning(self, "Validation Error", "End Date cannot be earlier than Start Date.")
            return

        try:
            if self.event:
                NoticeRepository.update_event(
                    self.db,
                    self.event.id,
                    event_title=title,
                    start_date=s_dt,
                    end_date=e_dt,
                    event_category=self.cat_combo.currentText(),
                    start_time=self.start_time.text().strip() or None,
                    end_time=self.end_time.text().strip() or None,
                    venue=self.venue_edit.text().strip() or "Campus Grounds",
                    target_audience=self.aud_combo.currentText(),
                    is_holiday=self.holiday_check.isChecked(),
                    description=self.desc_edit.toPlainText().strip() or None,
                    organizer=self.org_edit.text().strip() or "School Administration"
                )
            else:
                NoticeRepository.create_event(
                    self.db,
                    event_title=title,
                    start_date=s_dt,
                    end_date=e_dt,
                    event_category=self.cat_combo.currentText(),
                    start_time=self.start_time.text().strip() or None,
                    end_time=self.end_time.text().strip() or None,
                    venue=self.venue_edit.text().strip() or "Campus Grounds",
                    target_audience=self.aud_combo.currentText(),
                    is_holiday=self.holiday_check.isChecked(),
                    description=self.desc_edit.toPlainText().strip() or None,
                    organizer=self.org_edit.text().strip() or "School Administration"
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))
