"""
EduManage Pro - Transaction Form Dialog (PySide6)
Modal dialog to record financial income and expenditure vouchers with instant validation.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit, QTextEdit,
    QPushButton, QMessageBox, QRadioButton, QButtonGroup, QWidget
)
from PySide6.QtCore import Qt, QDate
from datetime import date
from app.database.connection import SessionLocal
from app.repositories.accounting_repository import AccountingRepository
from app.services.accounting_service import AccountingService


class TransactionFormDialog(QDialog):
    def __init__(self, parent=None, default_type="Expense"):
        super().__init__(parent)
        self.default_type = default_type
        self.setWindowTitle(f"Record New {default_type} Voucher — EduManage Pro")
        self.setMinimumWidth(500)
        self.setModal(True)
        self.saved_transaction = None

        self._build_ui()
        self._load_categories()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header Title
        title = QLabel(f"Financial Transaction Voucher")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        # Type Toggle (Income / Expense)
        type_widget = QWidget()
        type_layout = QHBoxLayout(type_widget)
        type_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_income = QRadioButton("Income / Credit Inflow")
        self.btn_expense = QRadioButton("Expense / Debit Outflow")
        self.type_group = QButtonGroup(self)
        self.type_group.addButton(self.btn_income)
        self.type_group.addButton(self.btn_expense)

        if self.default_type == "Income":
            self.btn_income.setChecked(True)
        else:
            self.btn_expense.setChecked(True)

        self.btn_income.toggled.connect(self._on_type_changed)
        self.btn_expense.toggled.connect(self._on_type_changed)

        type_layout.addWidget(self.btn_income)
        type_layout.addWidget(self.btn_expense)
        type_layout.addStretch()
        form.addRow("Voucher Type *:", type_widget)

        # Account Category
        self.category_combo = QComboBox()
        form.addRow("Account Category *:", self.category_combo)

        # Amount
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(1.0, 10000000.0)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setValue(1000.0)
        self.amount_spin.setPrefix("৳ ")
        form.addRow("Voucher Amount *:", self.amount_spin)

        # Date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Transaction Date *:", self.date_edit)

        # Payment Method
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Cash", "Bank Transfer", "bKash", "Nagad", "Cheque", "Card"])
        form.addRow("Payment Channel *:", self.method_combo)

        # Reference No.
        self.ref_edit = QLineEdit()
        self.ref_edit.setPlaceholderText("e.g. Cheque #45012, TrxID BK99281, Slip #88")
        form.addRow("Ref / Instrument #:", self.ref_edit)

        # Payee / Payer
        self.party_edit = QLineEdit()
        self.party_edit.setPlaceholderText("Name of vendor, teacher, donor, or guardian")
        form.addRow("Party / Beneficiary *:", self.party_edit)

        # Particulars / Memo
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(70)
        self.desc_edit.setPlaceholderText("Detailed description of expenditure or receipt purpose")
        form.addRow("Particulars / Memo:", self.desc_edit)

        layout.addLayout(form)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Confirm & Post Voucher")
        self.save_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 16px;")
        self.save_btn.clicked.connect(self._handle_save)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    def _get_current_type(self) -> str:
        return "Income" if self.btn_income.isChecked() else "Expense"

    def _on_type_changed(self):
        t = self._get_current_type()
        self.setWindowTitle(f"Record New {t} Voucher — EduManage Pro")
        self._load_categories()

    def _load_categories(self):
        self.category_combo.clear()
        t = self._get_current_type()
        db = SessionLocal()
        try:
            AccountingService.seed_default_categories(db)
            cats = AccountingRepository.get_all_categories(db, trans_type=t)
            for c in cats:
                self.category_combo.addItem(f"{c.name} ({c.code})", c.id)
        finally:
            db.close()

    def _handle_save(self):
        cat_id = self.category_combo.currentData()
        if not cat_id:
            QMessageBox.warning(self, "Validation Error", "Please select an account category head.")
            return

        party = self.party_edit.text().strip()
        if not party:
            QMessageBox.warning(self, "Validation Error", "Please specify the party / payee / received from.")
            return

        qdate = self.date_edit.date()
        tx_date = date(qdate.year(), qdate.month(), qdate.day())
        trans_type = self._get_current_type()
        amount = self.amount_spin.value()

        payload = {
            "type": trans_type,
            "category_id": cat_id,
            "amount": amount,
            "transaction_date": tx_date,
            "payment_method": self.method_combo.currentText(),
            "reference_no": self.ref_edit.text().strip() or None,
            "paid_to_received_from": party,
            "description": self.desc_edit.toPlainText().strip() or None,
            "recorded_by": "Accounts Officer"
        }

        db = SessionLocal()
        try:
            tx, err = AccountingService.record_transaction(db, payload)
            if err:
                QMessageBox.critical(self, "Transaction Failed", err)
                return
            self.saved_transaction = tx
            QMessageBox.information(
                self,
                "Voucher Recorded",
                f"Successfully recorded {trans_type} voucher:\n\n"
                f"Voucher No: {tx.voucher_no}\n"
                f"Amount: ৳ {tx.amount:,.2f}\n"
                f"Party: {tx.paid_to_received_from}"
            )
            self.accept()
        finally:
            db.close()
