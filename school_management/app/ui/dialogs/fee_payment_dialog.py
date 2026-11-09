"""
EduManage Pro - Fee Payment Collection Dialog (PySide6)
Collects full or partial fee payments, records payment method and transaction ID,
and triggers official PDF receipt voucher generation.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDoubleSpinBox, QPushButton, QMessageBox, QFrame, QFileDialog
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.models.fee import StudentFee
from app.models.school import SchoolSetting
from app.services.fee_service import FeeService
from app.reports.fee_receipt_pdf import FeeReceiptPDFGenerator


class FeePaymentDialog(QDialog):
    def __init__(self, parent=None, student_fee_id: int = None, current_user: str = "admin"):
        super().__init__(parent)
        self.student_fee_id = student_fee_id
        self.current_user = current_user
        self.latest_payment = None

        self.setWindowTitle("Collect Student Fee Payment")
        self.setFixedSize(480, 480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._init_ui()
        self._load_fee_details()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Fee Payment Collection")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E3A8A;")
        layout.addWidget(header)

        # Student & Fee Info Banner
        self.info_frame = QFrame()
        self.info_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        info_layout = QVBoxLayout(self.info_frame)
        info_layout.setContentsMargins(12, 10, 12, 10)
        info_layout.setSpacing(4)

        self.lbl_student = QLabel("Student: Loading...")
        self.lbl_student.setStyleSheet("font-size: 13px; font-weight: bold; color: #0F172A;")
        info_layout.addWidget(self.lbl_student)

        self.lbl_fee_title = QLabel("Fee Item: Loading...")
        self.lbl_fee_title.setStyleSheet("font-size: 12px; color: #475569;")
        info_layout.addWidget(self.lbl_fee_title)

        self.lbl_due = QLabel("Outstanding Due: ৳0.00")
        self.lbl_due.setStyleSheet("font-size: 13px; font-weight: bold; color: #DC2626;")
        info_layout.addWidget(self.lbl_due)

        layout.addWidget(self.info_frame)

        # Payment Amount Input
        layout.addWidget(QLabel("Payment Amount (BDT ৳) *"))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(1.0, 1000000.0)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSingleStep(100.0)
        layout.addWidget(self.amount_spin)

        # Payment Channel & Method
        h_row = QHBoxLayout()
        v_method = QVBoxLayout()
        v_method.addWidget(QLabel("Payment Method *"))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Cash", "bKash", "Nagad", "Rocket", "Bank Transfer", "Debit/Credit Card"])
        v_method.addWidget(self.method_combo)
        h_row.addLayout(v_method)

        v_trx = QVBoxLayout()
        v_trx.addWidget(QLabel("Transaction ID / Slip No"))
        self.trx_edit = QLineEdit()
        self.trx_edit.setPlaceholderText("e.g. BKASH-89210 or Slip #401")
        v_trx.addWidget(self.trx_edit)
        h_row.addLayout(v_trx)
        layout.addLayout(h_row)

        # Remarks
        layout.addWidget(QLabel("Notes / Remarks"))
        self.remarks_edit = QLineEdit()
        self.remarks_edit.setPlaceholderText("Optional cashier notes...")
        layout.addWidget(self.remarks_edit)

        layout.addStretch()

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        self.save_btn = QPushButton("Confirm Payment & Print Receipt")
        self.save_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px 16px; border-radius: 6px;")
        self.save_btn.clicked.connect(self._on_confirm_payment)
        btn_box.addWidget(self.save_btn)

        layout.addLayout(btn_box)

    def _load_fee_details(self):
        db: Session = SessionLocal()
        try:
            fee = db.query(StudentFee).filter(StudentFee.id == self.student_fee_id).first()
            if not fee:
                QMessageBox.critical(self, "Error", "Fee record not found.")
                self.reject()
                return

            self.lbl_student.setText(f"Student: {fee.student.full_name} ({fee.student.student_id}) — Roll #{fee.student.roll_number}")
            self.lbl_fee_title.setText(f"Fee: {fee.fee_structure.title} | Net: ৳{fee.net_amount:,.2f} | Paid: ৳{fee.paid_amount:,.2f}")
            self.lbl_due.setText(f"Outstanding Due Balance: ৳{fee.due_amount:,.2f}")

            self.amount_spin.setValue(fee.due_amount)
            self.amount_spin.setMaximum(fee.due_amount)
        finally:
            db.close()

    def _on_confirm_payment(self):
        amount = self.amount_spin.value()
        if amount <= 0:
            QMessageBox.warning(self, "Validation Error", "Payment amount must be greater than zero.")
            return

        method = self.method_combo.currentText()
        trx = self.trx_edit.text().strip() or None
        rem = self.remarks_edit.text().strip() or None

        db: Session = SessionLocal()
        try:
            payment, msg = FeeService.collect_fee_payment(
                db, self.student_fee_id, amount,
                payment_method=method,
                transaction_id=trx,
                remarks=rem,
                current_user=self.current_user
            )

            if not payment:
                QMessageBox.critical(self, "Payment Failed", msg)
                return

            self.latest_payment = payment
            school = db.query(SchoolSetting).first()

            # Ask user if they wish to export / print the PDF receipt
            reply = QMessageBox.question(
                self, "Payment Recorded",
                f"Payment of ৳{amount:,.2f} recorded successfully!\nReceipt No: {payment.receipt_no}\n\nWould you like to export/save the official PDF receipt now?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes and school:
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Save Fee Receipt",
                    f"Receipt_{payment.receipt_no}.pdf",
                    "PDF Documents (*.pdf)"
                )
                if file_path:
                    FeeReceiptPDFGenerator.generate_receipt(payment, school, file_path)
                    QMessageBox.information(self, "Receipt Saved", f"Receipt voucher saved to:\n{file_path}")

            self.accept()
        finally:
            db.close()
