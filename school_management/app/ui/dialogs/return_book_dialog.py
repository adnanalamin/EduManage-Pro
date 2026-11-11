"""
EduManage Pro - Return Book Dialog
Phase 10: PySide6 Modal for Book Return & Overdue Fine Calculation
"""

from datetime import date, datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QDateEdit, QDoubleSpinBox, QCheckBox, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import QDate
from sqlalchemy.orm import Session
from app.models.library import BookCirculation
from app.repositories.library_repository import LibraryRepository


class ReturnBookDialog(QDialog):
    """Dialog for processing book check-in with dynamic overdue days and fine calculation."""

    def __init__(self, db_session: Session, circulation: BookCirculation, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.circulation = circulation

        self.setWindowTitle(f"Check In Book - Loan #{circulation.id}")
        self.setMinimumWidth(460)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title_lbl = QLabel("Book Check-In & Overdue Settlement")
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #065F46;")
        layout.addWidget(title_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        # Book & Borrower Details
        book_title = self.circulation.book.title if self.circulation.book else "Unknown Book"
        acc_no = self.circulation.book.accession_no if self.circulation.book else "-"
        form.addRow("Book Title:", QLabel(f"<b>{book_title}</b> ({acc_no})"))

        borrower_name = "Borrower"
        if self.circulation.member:
            if self.circulation.member.student:
                borrower_name = f"{self.circulation.member.student.full_name} ({self.circulation.member.member_id})"
            elif self.circulation.member.teacher:
                borrower_name = f"{self.circulation.member.teacher.full_name} ({self.circulation.member.member_id})"
            else:
                borrower_name = self.circulation.member.member_id
        form.addRow("Borrower:", QLabel(borrower_name))

        form.addRow("Issue Date:", QLabel(self.circulation.issue_date))
        form.addRow("Due Date:", QLabel(f"<b>{self.circulation.due_date}</b>"))

        # Return Date
        today = date.today()
        self.return_date_edit = QDateEdit()
        self.return_date_edit.setCalendarPopup(True)
        self.return_date_edit.setDate(QDate(today.year, today.month, today.day))
        self.return_date_edit.dateChanged.connect(self._recalculate_fine)
        form.addRow("Return Date *:", self.return_date_edit)

        # Overdue Days Label
        self.overdue_lbl = QLabel("0 Days Overdue")
        self.overdue_lbl.setStyleSheet("font-weight: bold; color: #10B981;")
        form.addRow("Overdue Status:", self.overdue_lbl)

        # Fine Rate
        self.fine_rate_spin = QDoubleSpinBox()
        self.fine_rate_spin.setRange(0.0, 100.0)
        self.fine_rate_spin.setValue(5.0)  # $5.00 per day
        self.fine_rate_spin.setPrefix("$ ")
        self.fine_rate_spin.valueChanged.connect(self._recalculate_fine)
        form.addRow("Fine Rate / Day:", self.fine_rate_spin)

        # Computed Total Fine
        self.total_fine_lbl = QLabel("$ 0.00")
        self.total_fine_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #0F172A;")
        form.addRow("Total Overdue Fine:", self.total_fine_lbl)

        # Fine Paid Checkbox
        self.paid_checkbox = QCheckBox("Fine Collected / Waived (Mark as Paid)")
        self.paid_checkbox.setChecked(True)
        form.addRow("", self.paid_checkbox)

        # Remarks
        self.remarks_input = QLineEdit()
        self.remarks_input.setPlaceholderText("Book condition upon return...")
        form.addRow("Remarks:", self.remarks_input)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("Complete Check-In")
        confirm_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 16px;")
        confirm_btn.clicked.connect(self._confirm_return)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

        # Initial calculation
        self._recalculate_fine()

    def _recalculate_fine(self):
        q_ret = self.return_date_edit.date()
        ret_date = date(q_ret.year(), q_ret.month(), q_ret.day())

        try:
            due_d = datetime.strptime(self.circulation.due_date, "%Y-%m-%d").date()
            overdue_days = max(0, (ret_date - due_d).days)
        except Exception:
            overdue_days = 0

        rate = self.fine_rate_spin.value()
        fine_amount = overdue_days * rate

        if overdue_days > 0:
            self.overdue_lbl.setText(f"{overdue_days} Days OVERDUE")
            self.overdue_lbl.setStyleSheet("font-weight: bold; color: #DC2626;")
            self.total_fine_lbl.setText(f"$ {fine_amount:.2f}")
            self.total_fine_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #DC2626;")
        else:
            self.overdue_lbl.setText("On Time (No Overdue)")
            self.overdue_lbl.setStyleSheet("font-weight: bold; color: #10B981;")
            self.total_fine_lbl.setText("$ 0.00")
            self.total_fine_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #0F172A;")

    def _confirm_return(self):
        q_ret = self.return_date_edit.date()
        return_date_str = f"{q_ret.year():04d}-{q_ret.month():02d}-{q_ret.day():02d}"

        circ, err = LibraryRepository.return_book(
            session=self.db_session,
            circulation_id=self.circulation.id,
            return_date=return_date_str,
            fine_rate_per_day=self.fine_rate_spin.value(),
            fine_paid=self.paid_checkbox.isChecked(),
            remarks=self.remarks_input.text().strip() or None
        )

        if err:
            QMessageBox.warning(self, "Return Failed", err)
            return

        QMessageBox.information(
            self,
            "Book Returned Successfully",
            f"Book '{self.circulation.book.title}' has been returned.\nInventory copy replenished."
        )
        self.accept()
