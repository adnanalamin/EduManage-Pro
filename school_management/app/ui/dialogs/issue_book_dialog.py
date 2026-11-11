"""
EduManage Pro - Issue Book Dialog
Phase 10: PySide6 Modal for Issuing Books to Members
"""

from datetime import date, timedelta
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QDateEdit, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import QDate
from sqlalchemy.orm import Session
from app.models.library import Book, LibraryMember
from app.repositories.library_repository import LibraryRepository


class IssueBookDialog(QDialog):
    """Dialog for checking out a book to a registered student or staff library member."""

    def __init__(self, db_session: Session, preselected_book_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.preselected_book_id = preselected_book_id

        self.setWindowTitle("Issue Book (Circulation Checkout)")
        self.setMinimumWidth(480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title_lbl = QLabel("Book Circulation - Issue Book")
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #065F46;")
        layout.addWidget(title_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        # Book Selector
        self.book_combo = QComboBox()
        available_books = LibraryRepository.get_books(self.db_session, only_available=True)
        for b in available_books:
            self.book_combo.addItem(f"{b.accession_no} - {b.title} ({b.available_copies} avail)", b.id)
        if self.preselected_book_id:
            idx = self.book_combo.findData(self.preselected_book_id)
            if idx >= 0:
                self.book_combo.setCurrentIndex(idx)
        form.addRow("Select Book *:", self.book_combo)

        # Borrower Member Selector
        self.member_combo = QComboBox()
        members = LibraryRepository.get_members(self.db_session)
        for m in members:
            name = "Unknown"
            if m.student:
                name = f"{m.student.full_name} [Student]"
            elif m.teacher:
                name = f"{m.teacher.full_name} [Teacher]"
            elif m.staff:
                name = f"{m.staff.full_name} [Staff]"
            self.member_combo.addItem(f"{m.member_id} - {name} (Limit: {m.max_allowed_books})", m.id)
        form.addRow("Borrower Member *:", self.member_combo)

        # Issue Date
        today = date.today()
        self.issue_date_edit = QDateEdit()
        self.issue_date_edit.setCalendarPopup(True)
        self.issue_date_edit.setDate(QDate(today.year, today.month, today.day))
        form.addRow("Issue Date *:", self.issue_date_edit)

        # Due Date (+7 days default)
        due_d = today + timedelta(days=7)
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDate(QDate(due_d.year, due_d.month, due_d.day))
        form.addRow("Due Date *:", self.due_date_edit)

        # Issued By Officer
        self.officer_input = QLineEdit("Chief Librarian")
        form.addRow("Issued By:", self.officer_input)

        # Remarks
        self.remarks_input = QLineEdit()
        self.remarks_input.setPlaceholderText("Optional notes or condition...")
        form.addRow("Remarks:", self.remarks_input)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        issue_btn = QPushButton("Confirm Issue")
        issue_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 16px;")
        issue_btn.clicked.connect(self._confirm_issue)
        btn_layout.addWidget(issue_btn)

        layout.addLayout(btn_layout)

    def _confirm_issue(self):
        book_id = self.book_combo.currentData()
        member_id = self.member_combo.currentData()

        if not book_id:
            QMessageBox.warning(self, "Selection Required", "Please select an available book title.")
            return

        if not member_id:
            QMessageBox.warning(self, "Selection Required", "Please select a library borrower member.")
            return

        q_issue = self.issue_date_edit.date()
        q_due = self.due_date_edit.date()

        if q_due < q_issue:
            QMessageBox.warning(self, "Invalid Dates", "Due date cannot be earlier than issue date.")
            return

        issue_date_str = f"{q_issue.year():04d}-{q_issue.month():02d}-{q_issue.day():02d}"
        due_date_str = f"{q_due.year():04d}-{q_due.month():02d}-{q_due.day():02d}"

        circulation, err = LibraryRepository.issue_book(
            session=self.db_session,
            book_id=book_id,
            member_id=member_id,
            issue_date=issue_date_str,
            due_date=due_date_str,
            issued_by=self.officer_input.text().strip() or "Library Staff",
            remarks=self.remarks_input.text().strip() or None
        )

        if err:
            QMessageBox.warning(self, "Issue Denied", err)
            return

        QMessageBox.information(
            self,
            "Book Issued Successfully",
            f"Book loan #{circulation.id} created.\nDue date: {due_date_str}"
        )
        self.accept()
