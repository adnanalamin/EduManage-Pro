"""
EduManage Pro - Student Lifecycle Action Dialogs (PySide6)
Handles Transfer Out, Withdrawal, Archive, and Restore transitions with reason,
effective date, TC reference, and destination school validation.
"""

from datetime import date
from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.database.connection import SessionLocal
from app.services.student_service import StudentService


class StudentLifecycleDialog(QDialog):
    """Unified dialog for Student Transfer, Withdrawal, Archive, and Restore workflows."""

    def __init__(
        self,
        parent=None,
        student_pk: int = 0,
        student_name: str = "",
        action: str = "transfer",  # transfer | withdraw | archive | restore
        actor: str = "admin",
    ):
        super().__init__(parent)
        self.student_pk = student_pk
        self.student_name = student_name
        self.action = action.lower()
        self.actor = actor

        titles = {
            "transfer": "Transfer Student Out",
            "withdraw": "Withdraw Student Enrollment",
            "archive": "Archive Student Record",
            "restore": "Restore Student to Active Enrollment",
        }
        self.setWindowTitle(f"EduManage Pro — {titles.get(self.action, 'Update Status')}")
        self.setFixedSize(460, 320)
        self._build_ui(titles.get(self.action, "Update Status"))

    def _build_ui(self, heading: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title_lbl = QLabel(f"{heading}: {self.student_name}")
        title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #f8fafc;")
        layout.addWidget(title_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Effective Date:", self.date_edit)

        self.dest_school_input: Optional[QLineEdit] = None
        self.tc_number_input: Optional[QLineEdit] = None
        if self.action == "transfer":
            self.dest_school_input = QLineEdit()
            self.dest_school_input.setPlaceholderText("Destination school name*")
            self.tc_number_input = QLineEdit()
            self.tc_number_input.setPlaceholderText("Optional Transfer Certificate (TC) #")
            form.addRow("Destination School*:", self.dest_school_input)
            form.addRow("TC Reference No:", self.tc_number_input)

        self.reason_input = QTextEdit()
        self.reason_input.setMaximumHeight(80)
        default_reasons = {
            "transfer": "Family relocation / academic transfer",
            "withdraw": "",
            "archive": "Archived after completion / inactivity",
            "restore": "Restored to active student roster",
        }
        self.reason_input.setPlainText(default_reasons.get(self.action, ""))
        self.reason_input.setPlaceholderText("Enter reason / remarks...")
        form.addRow("Reason / Remarks*:" if self.action == "withdraw" else "Reason / Remarks:", self.reason_input)

        layout.addLayout(form)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_confirm = QPushButton("Confirm Transition")
        color_map = {
            "transfer": "#0284c7",
            "withdraw": "#d97706",
            "archive": "#64748b",
            "restore": "#059669",
        }
        btn_color = color_map.get(self.action, "#2563eb")
        btn_confirm.setStyleSheet(
            f"background-color: {btn_color}; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;"
        )
        btn_confirm.clicked.connect(self._submit)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_confirm)
        layout.addLayout(btn_row)

    def _submit(self):
        qd = self.date_edit.date()
        eff_date = date(qd.year(), qd.month(), qd.day())
        reason = self.reason_input.toPlainText().strip()

        db = SessionLocal()
        try:
            if self.action == "transfer":
                dest = self.dest_school_input.text().strip() if self.dest_school_input else ""
                tc = self.tc_number_input.text().strip() if self.tc_number_input else None
                ok, _s, msg = StudentService.transfer_student(
                    db,
                    self.student_pk,
                    destination_school=dest,
                    tc_number=tc or None,
                    reason=reason or "Transferred out",
                    effective_date=eff_date,
                    actor=self.actor,
                )
            elif self.action == "withdraw":
                ok, _s, msg = StudentService.withdraw_student(
                    db,
                    self.student_pk,
                    reason=reason,
                    effective_date=eff_date,
                    actor=self.actor,
                )
            elif self.action == "archive":
                ok, _s, msg = StudentService.archive_student(
                    db,
                    self.student_pk,
                    reason=reason or "Archived record",
                    actor=self.actor,
                )
            elif self.action == "restore":
                ok, _s, msg = StudentService.restore_student(
                    db,
                    self.student_pk,
                    reason=reason or "Restored to active status",
                    actor=self.actor,
                )
            else:
                ok, msg = False, f"Unknown lifecycle action '{self.action}'."

            if ok:
                QMessageBox.information(self, "Status Updated", msg)
                self.accept()
            else:
                QMessageBox.warning(self, "Validation Error", msg)
        finally:
            db.close()
