"""
EduManage Pro - Issue Book Dialog
PySide6 Modal for Issuing Specific Barcoded Physical Book Copies to Members
with Barcode / QR Scanner Lookup.
"""

from datetime import date, timedelta
from typing import Optional
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from sqlalchemy.orm import Session

from app.repositories.library_repository import LibraryRepository
from app.security.session import session as app_session


class IssueBookDialog(QDialog):
    """Dialog for checking out a book copy to a registered student, teacher, or staff library member."""

    def __init__(
        self,
        db_session: Session,
        preselected_book_id: Optional[int] = None,
        preselected_member_id: Optional[int] = None,
        preselected_copy_id: Optional[int] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.db_session = db_session
        self.preselected_book_id = preselected_book_id
        self.preselected_member_id = preselected_member_id
        self.preselected_copy_id = preselected_copy_id

        self.setWindowTitle("Issue Book (Circulation Checkout)")
        self.setMinimumWidth(520)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title_lbl = QLabel("Book Circulation — Check Out")
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #065F46;")
        layout.addWidget(title_lbl)

        # Barcode / QR Quick-Scan Box
        scan_row = QHBoxLayout()
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("Scan Book/Copy Barcode, QR, ISBN, or Member Card ID...")
        self.scan_input.returnPressed.connect(self._apply_scan)
        scan_row.addWidget(self.scan_input)
        scan_btn = QPushButton("Lookup Scan")
        scan_btn.clicked.connect(self._apply_scan)
        scan_row.addWidget(scan_btn)
        layout.addLayout(scan_row)

        form = QFormLayout()
        form.setSpacing(10)

        # Book Selector
        self.book_combo = QComboBox()
        books = LibraryRepository.get_books(self.db_session)
        for b in books:
            self.book_combo.addItem(
                f"{b.accession_no} — {b.title} ({b.available_copies}/{b.total_copies} avail)",
                b.id,
            )
        self.book_combo.currentIndexChanged.connect(self._refresh_copies_combo)
        form.addRow("Select Book *:", self.book_combo)

        # Physical Copy Selector
        self.copy_combo = QComboBox()
        form.addRow("Physical Copy:", self.copy_combo)

        # Borrower Member Selector
        self.member_combo = QComboBox()
        members = LibraryRepository.get_members(self.db_session, status="Active")
        for m in members:
            self.member_combo.addItem(
                f"{m.member_id} — {m.display_name} [{m.member_type}] (Max {m.max_allowed_books})",
                m.id,
            )
        self.member_combo.currentIndexChanged.connect(self._adjust_due_date_for_member)
        form.addRow("Borrower Member *:", self.member_combo)

        if self.preselected_book_id:
            idx = self.book_combo.findData(self.preselected_book_id)
            if idx >= 0:
                self.book_combo.setCurrentIndex(idx)
        self._refresh_copies_combo()

        if self.preselected_copy_id:
            cidx = self.copy_combo.findData(self.preselected_copy_id)
            if cidx >= 0:
                self.copy_combo.setCurrentIndex(cidx)

        if self.preselected_member_id:
            midx = self.member_combo.findData(self.preselected_member_id)
            if midx >= 0:
                self.member_combo.setCurrentIndex(midx)

        # Issue Date & Due Date
        today = date.today()
        self.issue_date_edit = QDateEdit()
        self.issue_date_edit.setCalendarPopup(True)
        self.issue_date_edit.setDate(QDate(today.year, today.month, today.day))
        form.addRow("Issue Date *:", self.issue_date_edit)

        due_d = today + timedelta(days=14)
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDate(QDate(due_d.year, due_d.month, due_d.day))
        form.addRow("Due Date *:", self.due_date_edit)

        default_actor = ""
        if app_session.is_authenticated and app_session.current_user:
            default_actor = app_session.current_user.full_name or app_session.current_user.username
        self.officer_input = QLineEdit(default_actor)
        self.officer_input.setPlaceholderText("Issuing Librarian / Officer")
        form.addRow("Issued By:", self.officer_input)

        self.remarks_input = QLineEdit()
        self.remarks_input.setPlaceholderText("Optional checkout notes...")
        form.addRow("Remarks:", self.remarks_input)

        layout.addLayout(form)
        self._adjust_due_date_for_member()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        issue_btn = QPushButton("Confirm Issue")
        issue_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 18px;")
        issue_btn.clicked.connect(self._confirm_issue)
        btn_layout.addWidget(issue_btn)
        layout.addLayout(btn_layout)

    def _refresh_copies_combo(self):
        self.copy_combo.clear()
        book_id = self.book_combo.currentData()
        if not book_id:
            return
        copies = LibraryRepository.get_book_copies(self.db_session, book_id)
        selectable = [c for c in copies if c.status in ("Available", "Reserved")]
        if not selectable:
            self.copy_combo.addItem("Auto-assign / No specific copy available", None)
            return
        for c in selectable:
            self.copy_combo.addItem(f"{c.copy_code} | BC:{c.barcode} [{c.status}]", c.id)

    def _adjust_due_date_for_member(self):
        m_id = self.member_combo.currentData()
        if not m_id:
            return
        member = LibraryRepository.get_member_by_id(self.db_session, m_id)
        if member and getattr(member, "max_loan_days", None):
            q_iss = self.issue_date_edit.date()
            iss_d = date(q_iss.year(), q_iss.month(), q_iss.day())
            due_d = iss_d + timedelta(days=int(member.max_loan_days))
            self.due_date_edit.setDate(QDate(due_d.year, due_d.month, due_d.day))

    def _apply_scan(self):
        code = self.scan_input.text().strip()
        if not code:
            return
        hit = LibraryRepository.lookup_by_barcode_or_qr(self.db_session, code)
        if not hit:
            QMessageBox.information(self, "Scan Not Found", f"No book, physical copy, or member matched '{code}'.")
            return
        if hit["type"] == "copy":
            b_idx = self.book_combo.findData(hit["book"].id)
            if b_idx >= 0:
                self.book_combo.setCurrentIndex(b_idx)
            c_idx = self.copy_combo.findData(hit["copy"].id)
            if c_idx >= 0:
                self.copy_combo.setCurrentIndex(c_idx)
        elif hit["type"] == "book":
            b_idx = self.book_combo.findData(hit["book"].id)
            if b_idx >= 0:
                self.book_combo.setCurrentIndex(b_idx)
        elif hit["type"] == "member":
            m_idx = self.member_combo.findData(hit["member"].id)
            if m_idx >= 0:
                self.member_combo.setCurrentIndex(m_idx)
        self.scan_input.clear()

    def _confirm_issue(self):
        book_id = self.book_combo.currentData()
        copy_id = self.copy_combo.currentData()
        member_id = self.member_combo.currentData()

        if not book_id:
            QMessageBox.warning(self, "Selection Required", "Please select a book.")
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
            issued_by=self.officer_input.text().strip() or None,
            remarks=self.remarks_input.text().strip() or None,
            copy_id=copy_id,
        )
        if err:
            QMessageBox.warning(self, "Issue Denied", err)
            return

        QMessageBox.information(
            self,
            "Book Issued Successfully",
            f"Loan #{circulation.id} recorded.\nDue date: {due_date_str}",
        )
        self.accept()
