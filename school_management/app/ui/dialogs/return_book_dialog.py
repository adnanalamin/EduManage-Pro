"""
EduManage Pro - Return Book Dialog
PySide6 Modal for Book Check-In, Good/Damaged/Lost Condition Handling,
Overdue Fines & Payment Recording.
"""

from datetime import date, datetime
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from sqlalchemy.orm import Session

from app.models.library import BookCirculation
from app.repositories.library_repository import LibraryRepository
from app.security.session import session as app_session


class ReturnBookDialog(QDialog):
    """Dialog for processing book check-in with condition inspection, overdue & damage/lost fee settlement."""

    def __init__(self, db_session: Session, circulation: BookCirculation, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.circulation = circulation

        self.setWindowTitle(f"Check In Book — Loan #{circulation.id}")
        self.setMinimumWidth(480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title_lbl = QLabel("Book Check-In & Settlement")
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #065F46;")
        layout.addWidget(title_lbl)

        form = QFormLayout()
        form.setSpacing(9)

        book_title = self.circulation.book.title if self.circulation.book else "Unknown Book"
        acc_no = self.circulation.book.accession_no if self.circulation.book else "-"
        copy_info = f" | Copy: {self.circulation.copy.copy_code}" if self.circulation.copy else ""
        form.addRow("Book & Copy:", QLabel(f"<b>{book_title}</b> ({acc_no}{copy_info})"))

        borrower_name = self.circulation.member.display_name if self.circulation.member else "Borrower"
        borrower_id = self.circulation.member.member_id if self.circulation.member else "-"
        form.addRow("Borrower:", QLabel(f"{borrower_name} ({borrower_id})"))
        form.addRow("Issue / Due Date:", QLabel(f"{self.circulation.issue_date}  →  <b>{self.circulation.due_date}</b>"))

        today = date.today()
        self.return_date_edit = QDateEdit()
        self.return_date_edit.setCalendarPopup(True)
        self.return_date_edit.setDate(QDate(today.year, today.month, today.day))
        self.return_date_edit.dateChanged.connect(self._recalculate_fine)
        form.addRow("Return Date *:", self.return_date_edit)

        self.condition_combo = QComboBox()
        self.condition_combo.addItems(["Good", "Fair", "Damaged", "Lost"])
        self.condition_combo.currentTextChanged.connect(self._on_condition_changed)
        form.addRow("Return Condition *:", self.condition_combo)

        self.overdue_lbl = QLabel("0 Days Overdue")
        form.addRow("Overdue Status:", self.overdue_lbl)

        self.fine_rate_spin = QDoubleSpinBox()
        self.fine_rate_spin.setRange(0.0, 500.0)
        self.fine_rate_spin.setValue(5.0)
        self.fine_rate_spin.setPrefix("$ ")
        self.fine_rate_spin.valueChanged.connect(self._recalculate_fine)
        form.addRow("Overdue Rate / Day:", self.fine_rate_spin)

        self.damage_fee_spin = QDoubleSpinBox()
        self.damage_fee_spin.setRange(0.0, 10000.0)
        self.damage_fee_spin.setValue(0.0)
        self.damage_fee_spin.setPrefix("$ ")
        self.damage_fee_spin.valueChanged.connect(self._recalculate_fine)
        form.addRow("Damage / Lost Fee:", self.damage_fee_spin)

        self.total_fine_lbl = QLabel("$ 0.00")
        self.total_fine_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #0F172A;")
        form.addRow("Total Fine / Fee:", self.total_fine_lbl)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["Cash", "Bank", "Card", "Mobile Banking"])
        form.addRow("Payment Method:", self.method_combo)

        self.paid_checkbox = QCheckBox("Collect Full Amount Now (Uncheck to record as Unpaid Fine)")
        self.paid_checkbox.setChecked(True)
        form.addRow("", self.paid_checkbox)

        self.remarks_input = QLineEdit()
        self.remarks_input.setPlaceholderText("Book condition or settlement notes...")
        form.addRow("Remarks:", self.remarks_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("Complete Check-In")
        confirm_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 18px;")
        confirm_btn.clicked.connect(self._confirm_return)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)
        self._recalculate_fine()

    def _on_condition_changed(self, cond: str):
        if cond == "Lost" and self.circulation.book:
            self.damage_fee_spin.setValue(float(self.circulation.book.price or 0.0))
        elif cond == "Damaged" and self.damage_fee_spin.value() == 0.0 and self.circulation.book:
            self.damage_fee_spin.setValue(round(float(self.circulation.book.price or 0.0) * 0.5, 2))
        elif cond in ("Good", "Fair"):
            self.damage_fee_spin.setValue(0.0)
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
        total = round(overdue_days * rate + self.damage_fee_spin.value(), 2)

        if overdue_days > 0:
            self.overdue_lbl.setText(f"{overdue_days} Days OVERDUE")
            self.overdue_lbl.setStyleSheet("font-weight: bold; color: #DC2626;")
        else:
            self.overdue_lbl.setText("On Time (No Overdue)")
            self.overdue_lbl.setStyleSheet("font-weight: bold; color: #10B981;")

        self.total_fine_lbl.setText(f"$ {total:.2f}")
        self.total_fine_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {'#DC2626' if total > 0 else '#0F172A'};"
        )

    def _confirm_return(self):
        q_ret = self.return_date_edit.date()
        return_date_str = f"{q_ret.year():04d}-{q_ret.month():02d}-{q_ret.day():02d}"
        actor = None
        if app_session.is_authenticated and app_session.current_user:
            actor = app_session.current_user.full_name or app_session.current_user.username

        circ, err = LibraryRepository.return_book(
            session=self.db_session,
            circulation_id=self.circulation.id,
            return_date=return_date_str,
            fine_rate_per_day=self.fine_rate_spin.value(),
            fine_paid=self.paid_checkbox.isChecked(),
            remarks=self.remarks_input.text().strip() or None,
            return_condition=self.condition_combo.currentText(),
            damage_fee=self.damage_fee_spin.value(),
            returned_to=actor,
            payment_method=self.method_combo.currentText(),
        )
        if err:
            QMessageBox.warning(self, "Return Failed", err)
            return

        QMessageBox.information(
            self,
            "Check-In Completed",
            f"Loan #{circ.id} updated ({circ.status}).",
        )
        self.accept()
