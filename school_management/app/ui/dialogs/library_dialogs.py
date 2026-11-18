"""
EduManage Pro - Library Operations Dialogs
Includes Member Enrollment & Digital QR Card Preview, Physical Book Copies Manager,
Loan Renewal, Book Reservation, Fine Collection/Waiver, Lost/Damaged Incident Modal,
and Excel/CSV Book Import Wizard.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)
from sqlalchemy.orm import Session

from app.models.library import (
    Book,
    BookCirculation,
    BookIncident,
    LibraryFine,
    LibraryMember,
)
from app.models.school import SchoolSetting
from app.models.staff import Staff, Teacher
from app.models.student import Student
from app.reports.library_card_pdf import LibraryCardGenerator
from app.repositories.library_repository import LibraryRepository
from app.security.session import session as app_session
from app.services.library_service import LibraryService
from app.ui.widgets.qr_code_widget import QRCodeWidget


def _current_actor() -> Optional[str]:
    if app_session.is_authenticated and app_session.current_user:
        return app_session.current_user.full_name or app_session.current_user.username
    return None


class LibraryMemberDialog(QDialog):
    """Enroll a real Student/Teacher/Staff patron or edit a library member card with live QR preview."""

    def __init__(self, db_session: Session, member: Optional[LibraryMember] = None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.member = member
        self.setWindowTitle("Library Member Card" if member else "Enroll Library Member")
        self.setMinimumWidth(540)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("Library Membership & Digital Card")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #065F46;")
        top.addWidget(title)
        top.addStretch()
        self.qr_widget = QRCodeWidget(size=72)
        top.addWidget(self.qr_widget)
        layout.addLayout(top)

        form = QFormLayout()
        form.setSpacing(8)

        self.member_code_input = QLineEdit()
        self.member_code_input.setPlaceholderText("e.g. LIB-STD-1001")
        self.member_code_input.textChanged.connect(self._update_qr)
        form.addRow("Card / Member ID *:", self.member_code_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Student", "Teacher", "Staff"])
        self.type_combo.currentTextChanged.connect(self._load_patron_list)
        form.addRow("Member Type *:", self.type_combo)

        self.patron_combo = QComboBox()
        form.addRow("Link School Record:", self.patron_combo)

        self.name_override_input = QLineEdit()
        self.name_override_input.setPlaceholderText("Auto from Student/Teacher/Staff or override")
        form.addRow("Name Override:", self.name_override_input)

        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()
        contact_row = QHBoxLayout()
        self.phone_input.setPlaceholderText("Phone")
        self.email_input.setPlaceholderText("Email")
        contact_row.addWidget(self.phone_input)
        contact_row.addWidget(self.email_input)
        form.addRow("Phone & Email:", contact_row)

        quota_row = QHBoxLayout()
        self.max_books_spin = QSpinBox()
        self.max_books_spin.setRange(1, 30)
        self.max_books_spin.setValue(3)
        quota_row.addWidget(self.max_books_spin)
        quota_row.addWidget(QLabel("Loan Days:"))
        self.max_days_spin = QSpinBox()
        self.max_days_spin.setRange(1, 180)
        self.max_days_spin.setValue(14)
        quota_row.addWidget(self.max_days_spin)
        form.addRow("Max Books & Days:", quota_row)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Suspended", "Expired"])
        form.addRow("Card Status:", self.status_combo)

        self.expiry_edit = QDateEdit()
        self.expiry_edit.setCalendarPopup(True)
        exp_d = date.today() + timedelta(days=365)
        self.expiry_edit.setDate(QDate(exp_d.year, exp_d.month, exp_d.day))
        form.addRow("Card Expiry Date:", self.expiry_edit)

        layout.addLayout(form)
        self._load_patron_list(self.type_combo.currentText())

        if self.member:
            self.member_code_input.setText(self.member.member_id)
            self.member_code_input.setEnabled(False)
            self.type_combo.setCurrentText(self.member.member_type)
            self.type_combo.setEnabled(False)
            pid = self.member.student_id or self.member.teacher_id or self.member.staff_id
            if pid:
                idx = self.patron_combo.findData(pid)
                if idx >= 0:
                    self.patron_combo.setCurrentIndex(idx)
            self.name_override_input.setText(self.member.full_name_override or "")
            self.phone_input.setText(self.member.phone or "")
            self.email_input.setText(self.member.email or "")
            self.max_books_spin.setValue(self.member.max_allowed_books)
            self.max_days_spin.setValue(getattr(self.member, "max_loan_days", 14) or 14)
            self.status_combo.setCurrentText(self.member.status)
            if getattr(self.member, "card_expiry_date", None):
                try:
                    d = datetime.strptime(self.member.card_expiry_date, "%Y-%m-%d").date()
                    self.expiry_edit.setDate(QDate(d.year, d.month, d.day))
                except Exception:
                    pass
            self._update_qr()

        btns = QHBoxLayout()
        if self.member:
            pdf_btn = QPushButton("Print CR80 Card (PDF)")
            pdf_btn.clicked.connect(self._print_card)
            btns.addWidget(pdf_btn)
        btns.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        save_btn = QPushButton("Save Member")
        save_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 16px;")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _load_patron_list(self, m_type: str):
        self.patron_combo.clear()
        self.patron_combo.addItem("-- Unlinked / External --", None)
        if m_type == "Student":
            for s in self.db_session.query(Student).filter(Student.is_deleted == False).order_by(Student.full_name.asc()).all():
                self.patron_combo.addItem(f"{s.student_id} — {s.full_name}", s.id)
        elif m_type == "Teacher":
            self.max_books_spin.setValue(5)
            self.max_days_spin.setValue(30)
            for t in self.db_session.query(Teacher).filter(Teacher.is_deleted == False).order_by(Teacher.full_name.asc()).all():
                self.patron_combo.addItem(f"{t.teacher_id} — {t.full_name}", t.id)
        elif m_type == "Staff":
            for st in self.db_session.query(Staff).filter(Staff.is_deleted == False).order_by(Staff.full_name.asc()).all():
                self.patron_combo.addItem(f"{st.staff_id} — {st.full_name}", st.id)

    def _update_qr(self):
        code = self.member_code_input.text().strip() or "LIB-NEW"
        bc = LibraryRepository.generate_member_barcode(code)
        self.qr_widget.set_payload(f"EDUMANAGE|LIB_MEM|ID:{code}|TYPE:{self.type_combo.currentText()}|BC:{bc}")

    def _print_card(self):
        if not self.member:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save CR80 Card PDF", f"Library_Card_{self.member.member_id}.pdf", "PDF Files (*.pdf)")
        if path:
            school = self.db_session.query(SchoolSetting).first()
            LibraryCardGenerator.generate_single_card(self.member, school, path)
            QMessageBox.information(self, "Card Saved", f"CR80 Library Card saved to:\n{path}")

    def _save(self):
        code = self.member_code_input.text().strip()
        if not code:
            QMessageBox.warning(self, "Validation", "Card / Member ID is required.")
            return
        q_exp = self.expiry_edit.date()
        exp_str = f"{q_exp.year():04d}-{q_exp.month():02d}-{q_exp.day():02d}"
        m_type = self.type_combo.currentText()
        pid = self.patron_combo.currentData()

        kwargs = {
            "full_name_override": self.name_override_input.text().strip() or None,
            "phone": self.phone_input.text().strip() or None,
            "email": self.email_input.text().strip() or None,
            "max_allowed_books": self.max_books_spin.value(),
            "max_loan_days": self.max_days_spin.value(),
            "status": self.status_combo.currentText(),
            "card_expiry_date": exp_str,
            "student_id": pid if m_type == "Student" else None,
            "teacher_id": pid if m_type == "Teacher" else None,
            "staff_id": pid if m_type == "Staff" else None,
        }
        try:
            if self.member:
                LibraryRepository.update_member(self.db_session, self.member.id, **kwargs)
            else:
                if LibraryRepository.get_member_by_code(self.db_session, code):
                    QMessageBox.warning(self, "Duplicate ID", f"Member '{code}' already exists.")
                    return
                LibraryRepository.create_member(
                    self.db_session,
                    member_id=code,
                    member_type=m_type,
                    card_issue_date=date.today().isoformat(),
                    **kwargs,
                )
            self.accept()
        except Exception as exc:
            self.db_session.rollback()
            QMessageBox.critical(self, "Error", str(exc))


class BookCopiesDialog(QDialog):
    """Manage physical barcoded copies of a catalog book, print labels, or report lost/damaged copies."""

    def __init__(self, db_session: Session, book: Book, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.book = book
        self.setWindowTitle(f"Physical Copies — {book.title} ({book.accession_no})")
        self.setMinimumSize(780, 460)
        self._setup_ui()
        self.load_copies()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel(f"<b>{self.book.title}</b> • Accession: {self.book.accession_no} • ISBN: {self.book.isbn or '-'}"))
        top.addStretch()

        add_copy_btn = QPushButton("+ Add Copy")
        add_copy_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 5px 12px;")
        add_copy_btn.clicked.connect(self._add_copy)
        top.addWidget(add_copy_btn)

        lbl_btn = QPushButton("Print Barcode/QR Labels (PDF)")
        lbl_btn.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold; padding: 5px 12px;")
        lbl_btn.clicked.connect(self._print_labels)
        top.addWidget(lbl_btn)
        layout.addLayout(top)

        self.table = QTableWidget()
        headers = ["Copy Code", "Barcode", "Condition", "Status", "Shelf", "Notes", "Actions"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    def load_copies(self):
        copies = LibraryRepository.get_book_copies(self.db_session, self.book.id)
        self.table.setRowCount(len(copies))
        for r, cp in enumerate(copies):
            self.table.setItem(r, 0, QTableWidgetItem(cp.copy_code))
            self.table.setItem(r, 1, QTableWidgetItem(cp.barcode))
            self.table.setItem(r, 2, QTableWidgetItem(cp.condition))
            self.table.setItem(r, 3, QTableWidgetItem(cp.status))
            sh_lbl = cp.shelf.shelf_code if cp.shelf else (self.book.shelf_number or "-")
            self.table.setItem(r, 4, QTableWidgetItem(sh_lbl))
            self.table.setItem(r, 5, QTableWidgetItem(cp.notes or ""))

            act_w = QPushButton("Report Lost/Damaged")
            act_w.setEnabled(cp.status in ("Available", "Issued"))
            act_w.clicked.connect(lambda _, c_id=cp.id: self._report_incident(c_id))
            self.table.setCellWidget(r, 6, act_w)

    def _add_copy(self):
        LibraryRepository.add_book_copy(self.db_session, self.book.id, shelf_id=self.book.shelf_id)
        self.load_copies()

    def _report_incident(self, copy_id: int):
        dlg = BookIncidentDialog(self.db_session, preselected_book_id=self.book.id, preselected_copy_id=copy_id, parent=self)
        if dlg.exec():
            self.load_copies()

    def _print_labels(self):
        copies = LibraryRepository.get_book_copies(self.db_session, self.book.id)
        items = copies if copies else [self.book]
        path, _ = QFileDialog.getSaveFileName(self, "Save Barcode/QR Labels PDF", f"Labels_{self.book.accession_no}.pdf", "PDF Files (*.pdf)")
        if path:
            school = self.db_session.query(SchoolSetting).first()
            LibraryCardGenerator.generate_book_barcodes_pdf(items, school, path)
            QMessageBox.information(self, "Labels Saved", f"Barcode & QR Label sheet saved to:\n{path}")


class RenewLoanDialog(QDialog):
    """Modal for renewing an active book loan."""

    def __init__(self, db_session: Session, circ: BookCirculation, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.circ = circ
        self.setWindowTitle(f"Renew Loan #{circ.id}")
        self.setMinimumWidth(420)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("Book:", QLabel(self.circ.book.title if self.circ.book else "-"))
        form.addRow("Borrower:", QLabel(self.circ.member.display_name if self.circ.member else "-"))
        form.addRow("Current Due Date:", QLabel(f"<b>{self.circ.due_date}</b>"))
        form.addRow("Renewals Used:", QLabel(f"{self.circ.renewal_count or 0} / {self.circ.max_renewals or 2}"))

        try:
            cur_d = datetime.strptime(self.circ.due_date, "%Y-%m-%d").date()
        except Exception:
            cur_d = date.today()
        new_d = max(date.today(), cur_d) + timedelta(days=7)

        self.new_due_edit = QDateEdit()
        self.new_due_edit.setCalendarPopup(True)
        self.new_due_edit.setDate(QDate(new_d.year, new_d.month, new_d.day))
        form.addRow("New Due Date *:", self.new_due_edit)

        self.remarks_input = QLineEdit()
        self.remarks_input.setPlaceholderText("Optional renewal notes...")
        form.addRow("Remarks:", self.remarks_input)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(self.reject)
        btns.addWidget(c_btn)
        ok_btn = QPushButton("Confirm Renewal")
        ok_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 14px;")
        ok_btn.clicked.connect(self._renew)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

    def _renew(self):
        q_d = self.new_due_edit.date()
        due_str = f"{q_d.year():04d}-{q_d.month():02d}-{q_d.day():02d}"
        _, err = LibraryRepository.renew_loan(
            self.db_session,
            self.circ.id,
            new_due_date=due_str,
            renewed_by=_current_actor(),
            remarks=self.remarks_input.text().strip() or None,
        )
        if err:
            QMessageBox.warning(self, "Renewal Blocked", err)
            return
        self.accept()


class ReservationDialog(QDialog):
    """Modal for reserving a book title for a member."""

    def __init__(self, db_session: Session, preselected_book_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.setWindowTitle("New Book Reservation")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.book_combo = QComboBox()
        for b in LibraryRepository.get_books(self.db_session):
            self.book_combo.addItem(f"{b.accession_no} — {b.title} ({b.available_copies} avail)", b.id)
        if preselected_book_id:
            idx = self.book_combo.findData(preselected_book_id)
            if idx >= 0:
                self.book_combo.setCurrentIndex(idx)
        form.addRow("Book Title *:", self.book_combo)

        self.member_combo = QComboBox()
        for m in LibraryRepository.get_members(self.db_session, status="Active"):
            self.member_combo.addItem(f"{m.member_id} — {m.display_name}", m.id)
        form.addRow("Library Member *:", self.member_combo)

        self.hold_days_spin = QSpinBox()
        self.hold_days_spin.setRange(1, 14)
        self.hold_days_spin.setValue(3)
        form.addRow("Hold Expiry (Days):", self.hold_days_spin)

        self.hold_avail_chk = QCheckBox("Lock an available copy immediately if in stock")
        self.hold_avail_chk.setChecked(True)
        form.addRow("", self.hold_avail_chk)

        self.notes_input = QLineEdit()
        form.addRow("Notes:", self.notes_input)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        save_btn = QPushButton("Place Reservation")
        save_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 14px;")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _save(self):
        b_id = self.book_combo.currentData()
        m_id = self.member_combo.currentData()
        if not b_id or not m_id:
            QMessageBox.warning(self, "Required", "Please select both a Book and a Member.")
            return
        res, err = LibraryRepository.create_reservation(
            self.db_session,
            book_id=b_id,
            member_id=m_id,
            expiry_days=self.hold_days_spin.value(),
            notes=self.notes_input.text().strip() or None,
            created_by=_current_actor(),
            hold_available_copy=self.hold_avail_chk.isChecked(),
        )
        if err:
            QMessageBox.warning(self, "Reservation Failed", err)
            return
        QMessageBox.information(self, "Reserved", f"Reservation {res.reservation_code} created ({res.status}).")
        self.accept()


class FineCollectionDialog(QDialog):
    """Collect payment or waive an unpaid/partial LibraryFine."""

    def __init__(self, db_session: Session, fine: LibraryFine, waive_mode: bool = False, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.fine = fine
        self.waive_mode = waive_mode
        self.setWindowTitle("Waive Fine" if waive_mode else "Collect Fine Payment")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.addRow("Fine Code:", QLabel(f"<b>{fine.fine_code}</b> ({fine.fine_type})"))
        form.addRow("Borrower:", QLabel(fine.member.display_name if fine.member else "-"))
        form.addRow("Balance Due:", QLabel(f"<b>$ {fine.balance_due:.2f}</b>"))

        if waive_mode:
            self.reason_input = QLineEdit()
            self.reason_input.setPlaceholderText("Reason for waiver (approved by Principal/Librarian)...")
            form.addRow("Waiver Reason *:", self.reason_input)
        else:
            self.amount_spin = QDoubleSpinBox()
            self.amount_spin.setRange(0.01, max(0.01, fine.balance_due))
            self.amount_spin.setValue(fine.balance_due)
            self.amount_spin.setPrefix("$ ")
            form.addRow("Payment Amount *:", self.amount_spin)

            self.method_combo = QComboBox()
            self.method_combo.addItems(["Cash", "Bank", "Card", "Mobile Banking"])
            form.addRow("Payment Method:", self.method_combo)

            self.notes_input = QLineEdit()
            form.addRow("Notes:", self.notes_input)

        layout.addLayout(form)
        btns = QHBoxLayout()
        btns.addStretch()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(self.reject)
        btns.addWidget(c_btn)
        ok_btn = QPushButton("Waive Fine" if waive_mode else "Record Payment")
        ok_btn.setStyleSheet("background-color: #7C3AED; color: white; font-weight: bold; padding: 6px 14px;")
        ok_btn.clicked.connect(self._submit)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

    def _submit(self):
        if self.waive_mode:
            reason = self.reason_input.text().strip()
            if not reason:
                QMessageBox.warning(self, "Required", "Please enter a reason for waiving this fine.")
                return
            _, err = LibraryRepository.waive_fine(self.db_session, self.fine.id, reason, waived_by=_current_actor())
        else:
            _, err = LibraryRepository.collect_fine_payment(
                self.db_session,
                self.fine.id,
                amount=self.amount_spin.value(),
                payment_method=self.method_combo.currentText(),
                collected_by=_current_actor(),
                notes=self.notes_input.text().strip() or None,
            )
        if err:
            QMessageBox.warning(self, "Error", err)
            return
        self.accept()


class BookIncidentDialog(QDialog):
    """Report a Lost or Damaged book copy with optional borrower billing."""

    def __init__(
        self,
        db_session: Session,
        preselected_book_id: Optional[int] = None,
        preselected_copy_id: Optional[int] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.db_session = db_session
        self.setWindowTitle("Report Lost or Damaged Book")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Lost", "Damaged"])
        form.addRow("Incident Type *:", self.type_combo)

        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["Total Loss", "Unusable", "Major", "Minor"])
        form.addRow("Severity:", self.severity_combo)

        self.book_combo = QComboBox()
        for b in LibraryRepository.get_books(self.db_session):
            self.book_combo.addItem(f"{b.accession_no} — {b.title}", b.id)
        if preselected_book_id:
            idx = self.book_combo.findData(preselected_book_id)
            if idx >= 0:
                self.book_combo.setCurrentIndex(idx)
        self.book_combo.currentIndexChanged.connect(self._reload_copies)
        form.addRow("Book *:", self.book_combo)

        self.copy_combo = QComboBox()
        form.addRow("Physical Copy:", self.copy_combo)
        self._reload_copies()
        if preselected_copy_id:
            c_idx = self.copy_combo.findData(preselected_copy_id)
            if c_idx >= 0:
                self.copy_combo.setCurrentIndex(c_idx)

        self.member_combo = QComboBox()
        self.member_combo.addItem("-- Internal Shelf Audit / No Borrower --", None)
        for m in LibraryRepository.get_members(self.db_session):
            self.member_combo.addItem(f"{m.member_id} — {m.display_name}", m.id)
        form.addRow("Responsible Member:", self.member_combo)

        self.fine_spin = QDoubleSpinBox()
        self.fine_spin.setRange(0.0, 50000.0)
        self.fine_spin.setPrefix("$ ")
        form.addRow("Fine Assessed:", self.fine_spin)

        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(65)
        self.desc_input.setPlaceholderText("Describe damage or circumstances of loss...")
        form.addRow("Description:", self.desc_input)

        layout.addLayout(form)
        btns = QHBoxLayout()
        btns.addStretch()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(self.reject)
        btns.addWidget(c_btn)
        s_btn = QPushButton("Record Incident")
        s_btn.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; padding: 6px 14px;")
        s_btn.clicked.connect(self._submit)
        btns.addWidget(s_btn)
        layout.addLayout(btns)

    def _reload_copies(self):
        self.copy_combo.clear()
        self.copy_combo.addItem("-- Auto-select --", None)
        b_id = self.book_combo.currentData()
        if not b_id:
            return
        for c in LibraryRepository.get_book_copies(self.db_session, b_id):
            if c.status in ("Available", "Issued", "Reserved"):
                self.copy_combo.addItem(f"{c.copy_code} [{c.status}]", c.id)

    def _submit(self):
        b_id = self.book_combo.currentData()
        if not b_id:
            return
        inc, err = LibraryRepository.report_book_incident(
            self.db_session,
            book_id=b_id,
            incident_type=self.type_combo.currentText(),
            copy_id=self.copy_combo.currentData(),
            member_id=self.member_combo.currentData(),
            severity=self.severity_combo.currentText(),
            description=self.desc_input.toPlainText().strip() or None,
            fine_assessed=self.fine_spin.value(),
            reported_by=_current_actor(),
        )
        if err:
            QMessageBox.warning(self, "Error", err)
            return
        QMessageBox.information(self, "Recorded", f"Incident {inc.incident_code} recorded.")
        self.accept()


class BookImportDialog(QDialog):
    """Excel / CSV Bulk Book Catalog Import Wizard."""

    def __init__(self, db_session: Session, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.setWindowTitle("Import Books from Excel / CSV")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        info = QLabel(
            "Select an Excel (.xlsx) or CSV (.csv) catalog file. Missing categories, authors, "
            "publishers, shelves, and barcoded physical copies will be created automatically."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        file_row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Choose .xlsx or .csv file...")
        file_row.addWidget(self.path_input)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        self.update_chk = QCheckBox("Update existing books if Accession No matches")
        layout.addWidget(self.update_chk)

        btns = QHBoxLayout()
        tpl_btn = QPushButton("Download Excel Template")
        tpl_btn.clicked.connect(self._download_template)
        btns.addWidget(tpl_btn)
        btns.addStretch()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(self.reject)
        btns.addWidget(c_btn)
        run_btn = QPushButton("Run Import")
        run_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 16px;")
        run_btn.clicked.connect(self._run_import)
        btns.addWidget(run_btn)
        layout.addLayout(btns)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Book Catalog File", "", "Spreadsheets (*.xlsx *.xlsm *.csv)"
        )
        if path:
            self.path_input.setText(path)

    def _download_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Book Import Template", "Library_Book_Import_Template.xlsx", "Excel Files (*.xlsx)"
        )
        if path:
            LibraryService.export_import_template_excel(path)
            QMessageBox.information(self, "Template Saved", f"Import template saved to:\n{path}")

    def _run_import(self):
        path = self.path_input.text().strip()
        if not path:
            QMessageBox.warning(self, "No File", "Please choose an .xlsx or .csv file.")
            return
        try:
            res = LibraryService.import_books_from_file(
                self.db_session, path, update_existing=self.update_chk.isChecked()
            )
            msg = (
                f"Import Complete:\n"
                f"• Imported: {res['imported']}\n"
                f"• Updated: {res['updated']}\n"
                f"• Skipped: {res['skipped']}"
            )
            if res["errors"]:
                msg += "\n\nNotes:\n" + "\n".join(res["errors"][:5])
            QMessageBox.information(self, "Import Summary", msg)
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", str(exc))
