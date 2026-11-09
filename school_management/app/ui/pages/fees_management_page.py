"""
EduManage Pro - Fees Management View (PySide6)
Full GUI interface for Fee Billing, Payments Collection, Partial / Due tracking,
Fee Structures, and PDF Receipt Export.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QTabWidget, QMessageBox, QFrame, QFileDialog, QInputDialog
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.repositories.fee_repository import FeeRepository
from app.repositories.academic_repository import AcademicRepository
from app.services.fee_service import FeeService
from app.models.fee import StudentFee, FeePayment
from app.models.school import SchoolSetting
from app.reports.fee_receipt_pdf import FeeReceiptPDFGenerator
from app.ui.dialogs.fee_payment_dialog import FeePaymentDialog
from app.ui.dialogs.fee_structure_dialog import FeeStructureDialog


class FeesManagementPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.invoice_data_list = []
        self.payment_data_list = []
        self._init_ui()
        self.refresh_all()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # 1. Header Banner
        header_h = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("Fees & Billing Management")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A;")
        sub_lbl = QLabel("Manage Tuition fees, payment vouchers, partial dues, scholarships, and receipts")
        sub_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header_h.addLayout(title_box)
        header_h.addStretch()

        btn_new_struct = QPushButton("+ New Fee Structure")
        btn_new_struct.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")
        btn_new_struct.clicked.connect(self._on_add_fee_structure)
        header_h.addWidget(btn_new_struct)

        main_layout.addLayout(header_h)

        # 2. Financial KPI Cards
        kpi_frame = QFrame()
        kpi_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        kpi_layout = QHBoxLayout(kpi_frame)
        kpi_layout.setContentsMargins(16, 12, 16, 12)

        self.kpi_invoiced = QLabel("Total Invoiced: ৳0.00")
        self.kpi_invoiced.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        kpi_layout.addWidget(self.kpi_invoiced)
        kpi_layout.addSpacing(20)

        self.kpi_collected = QLabel("Collected: ৳0.00")
        self.kpi_collected.setStyleSheet("font-size: 13px; color: #059669; font-weight: bold;")
        kpi_layout.addWidget(self.kpi_collected)
        kpi_layout.addSpacing(20)

        self.kpi_due = QLabel("Outstanding Due: ৳0.00")
        self.kpi_due.setStyleSheet("font-size: 13px; color: #DC2626; font-weight: bold;")
        kpi_layout.addWidget(self.kpi_due)
        kpi_layout.addSpacing(20)

        self.kpi_discount = QLabel("Scholarships: ৳0.00")
        self.kpi_discount.setStyleSheet("font-size: 13px; color: #7C3AED; font-weight: bold;")
        kpi_layout.addWidget(self.kpi_discount)
        kpi_layout.addStretch()

        main_layout.addWidget(kpi_frame)

        # 3. Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { font-weight: 600; padding: 8px 16px; margin-right: 4px; }
            QTabBar::tab:selected { background: #2563EB; color: white; border-radius: 4px; }
        """)

        # Tab 1: Invoices & Collection
        tab_invoices = self._build_invoices_tab()
        self.tabs.addTab(tab_invoices, "Student Invoices & Dues")

        # Tab 2: Fee Structures & Rates
        tab_structures = self._build_structures_tab()
        self.tabs.addTab(tab_structures, "Fee Structures & Rates")

        # Tab 3: Payment History & Receipts
        tab_history = self._build_history_tab()
        self.tabs.addTab(tab_history, "Payment Ledger & Receipts")

        main_layout.addWidget(self.tabs)

    def _build_invoices_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(10)

        # Filter bar
        filter_h = QHBoxLayout()
        filter_h.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by student name or ID...")
        self.search_edit.textChanged.connect(self._load_invoices)
        filter_h.addWidget(self.search_edit)

        filter_h.addSpacing(16)
        filter_h.addWidget(QLabel("Class:"))
        self.class_combo = QComboBox()
        self.class_combo.addItem("All Classes", None)
        self.class_combo.currentIndexChanged.connect(self._load_invoices)
        filter_h.addWidget(self.class_combo)

        filter_h.addSpacing(16)
        filter_h.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["all", "Unpaid", "Partial", "Paid"])
        self.status_combo.currentIndexChanged.connect(self._load_invoices)
        filter_h.addWidget(self.status_combo)

        filter_h.addStretch()
        layout.addLayout(filter_h)

        # Invoices Table
        self.invoice_table = QTableWidget()
        self.invoice_table.setColumnCount(9)
        self.invoice_table.setHorizontalHeaderLabels([
            "Roll", "Student ID", "Student Name", "Fee Description", "Total (৳)", "Paid (৳)", "Due (৳)", "Status", "Actions"
        ])
        self.invoice_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.invoice_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.invoice_table)

        return tab

    def _build_structures_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(10)

        self.struct_table = QTableWidget()
        self.struct_table.setColumnCount(6)
        self.struct_table.setHorizontalHeaderLabels([
            "Title", "Category", "Class", "Amount (৳)", "Billing Frequency", "Due Date"
        ])
        self.struct_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.struct_table)
        return tab

    def _build_history_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(10)

        # Search bar
        h_bar = QHBoxLayout()
        h_bar.addWidget(QLabel("Filter Receipts:"))
        self.history_search_edit = QLineEdit()
        self.history_search_edit.setPlaceholderText("Search receipt number, transaction ID, student...")
        self.history_search_edit.textChanged.connect(self._load_history)
        h_bar.addWidget(self.history_search_edit)
        h_bar.addStretch()
        layout.addLayout(h_bar)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "Receipt No", "Date", "Student Name", "Amount Paid", "Channel", "Cashier", "Download PDF"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.history_table)
        return tab

    def refresh_all(self):
        db: Session = SessionLocal()
        try:
            FeeService.seed_default_fee_categories(db)
            kpi = FeeRepository.get_financial_kpi(db)
            self.kpi_invoiced.setText(f"Total Invoiced: ৳{kpi['total_invoiced']:,.2f}")
            self.kpi_collected.setText(f"Collected: ৳{kpi['total_collected']:,.2f}")
            self.kpi_due.setText(f"Outstanding Due: ৳{kpi['total_due']:,.2f}")
            self.kpi_discount.setText(f"Scholarships: ৳{kpi['total_discount']:,.2f}")

            # Populate class combo
            classes = AcademicRepository.get_classes(db)
            curr_idx = self.class_combo.currentIndex()
            self.class_combo.blockSignals(True)
            self.class_combo.clear()
            self.class_combo.addItem("All Classes", None)
            for c in classes:
                self.class_combo.addItem(f"{c.name} ({c.group})", c.id)
            if curr_idx >= 0 and curr_idx < self.class_combo.count():
                self.class_combo.setCurrentIndex(curr_idx)
            self.class_combo.blockSignals(False)

            self._load_invoices()
            self._load_structures()
            self._load_history()
        finally:
            db.close()

    def _load_invoices(self):
        search_text = self.search_edit.text().strip()
        class_id = self.class_combo.currentData()
        status = self.status_combo.currentText()

        db: Session = SessionLocal()
        try:
            invoices, total = FeeRepository.get_student_fees(
                db, class_id=class_id, status=status, search=search_text if search_text else None, per_page=100
            )
            self.invoice_data_list = invoices
            self.invoice_table.setRowCount(len(invoices))

            for row, inv in enumerate(invoices):
                stu = inv.student
                self.invoice_table.setItem(row, 0, QTableWidgetItem(f"#{stu.roll_number}"))
                self.invoice_table.setItem(row, 1, QTableWidgetItem(stu.student_id))
                self.invoice_table.setItem(row, 2, QTableWidgetItem(stu.full_name))
                self.invoice_table.setItem(row, 3, QTableWidgetItem(inv.fee_structure.title if inv.fee_structure else "Tuition"))
                self.invoice_table.setItem(row, 4, QTableWidgetItem(f"৳{inv.net_amount:,.2f}"))
                self.invoice_table.setItem(row, 5, QTableWidgetItem(f"৳{inv.paid_amount:,.2f}"))
                self.invoice_table.setItem(row, 6, QTableWidgetItem(f"৳{inv.due_amount:,.2f}"))

                # Status item
                st_item = QTableWidgetItem(inv.status)
                self.invoice_table.setItem(row, 7, st_item)

                # Actions button
                btn_widget = QWidget()
                btn_h = QHBoxLayout(btn_widget)
                btn_h.setContentsMargins(2, 2, 2, 2)
                if inv.due_amount > 0.01:
                    pay_btn = QPushButton("Collect Payment")
                    pay_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold; border-radius: 4px; padding: 4px 8px;")
                    pay_btn.clicked.connect(lambda _, fee_id=inv.id: self._on_collect_payment(fee_id))
                    btn_h.addWidget(pay_btn)
                else:
                    paid_lbl = QLabel("Paid in Full")
                    paid_lbl.setStyleSheet("color: #059669; font-weight: bold;")
                    btn_h.addWidget(paid_lbl)

                self.invoice_table.setCellWidget(row, 8, btn_widget)
        finally:
            db.close()

    def _load_structures(self):
        db: Session = SessionLocal()
        try:
            structures = FeeRepository.get_fee_structures(db)
            self.struct_table.setRowCount(len(structures))
            for row, s in enumerate(structures):
                self.struct_table.setItem(row, 0, QTableWidgetItem(s.title))
                self.struct_table.setItem(row, 1, QTableWidgetItem(s.category.name if s.category else "-"))
                self.struct_table.setItem(row, 2, QTableWidgetItem(s.school_class.name if s.school_class else "All Classes"))
                self.struct_table.setItem(row, 3, QTableWidgetItem(f"৳{s.amount:,.2f}"))
                self.struct_table.setItem(row, 4, QTableWidgetItem(s.frequency))
                due_d = s.due_date.strftime("%d-%b-%Y") if hasattr(s.due_date, "strftime") else str(s.due_date)
                self.struct_table.setItem(row, 5, QTableWidgetItem(due_d))
        finally:
            db.close()

    def _load_history(self):
        search_text = self.history_search_edit.text().strip()
        db: Session = SessionLocal()
        try:
            payments, total = FeeRepository.get_payments(db, search=search_text if search_text else None, per_page=100)
            self.payment_data_list = payments
            self.history_table.setRowCount(len(payments))

            for row, p in enumerate(payments):
                self.history_table.setItem(row, 0, QTableWidgetItem(p.receipt_no))
                p_date = p.payment_date.strftime("%d-%b-%Y") if hasattr(p.payment_date, "strftime") else str(p.payment_date)
                self.history_table.setItem(row, 1, QTableWidgetItem(p_date))
                self.history_table.setItem(row, 2, QTableWidgetItem(p.student.full_name if p.student else "-"))
                self.history_table.setItem(row, 3, QTableWidgetItem(f"৳{p.amount_paid:,.2f}"))
                self.history_table.setItem(row, 4, QTableWidgetItem(p.payment_method))
                self.history_table.setItem(row, 5, QTableWidgetItem(p.collected_by))

                # Download PDF receipt button
                pdf_btn = QPushButton("Print Receipt")
                pdf_btn.setStyleSheet("background-color: #2563EB; color: white; border-radius: 4px; padding: 4px 8px; font-weight: bold;")
                pdf_btn.clicked.connect(lambda _, pay_obj=p: self._on_download_receipt(pay_obj))
                self.history_table.setCellWidget(row, 6, pdf_btn)
        finally:
            db.close()

    def _on_collect_payment(self, fee_id: int):
        dlg = FeePaymentDialog(self, student_fee_id=fee_id)
        if dlg.exec() == FeePaymentDialog.Accepted:
            self.refresh_all()

    def _on_add_fee_structure(self):
        dlg = FeeStructureDialog(self)
        if dlg.exec() == FeeStructureDialog.Accepted:
            self.refresh_all()

    def _on_download_receipt(self, payment):
        db: Session = SessionLocal()
        try:
            school = db.query(SchoolSetting).first()
            if not school:
                QMessageBox.warning(self, "Notice", "School settings must be configured to generate receipt header.")
                return

            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Fee Receipt",
                f"Receipt_{payment.receipt_no}.pdf",
                "PDF Documents (*.pdf)"
            )
            if file_path:
                FeeReceiptPDFGenerator.generate_receipt(payment, school, file_path)
                QMessageBox.information(self, "Saved", f"Receipt voucher saved to:\n{file_path}")
        finally:
            db.close()
