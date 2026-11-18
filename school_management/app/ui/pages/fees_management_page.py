"""
EduManage Pro - Enterprise Fees & Billing Management View (PySide6)
Full commercial ERP console for Fee Structures (Monthly, Admission, Exam, Library,
Transport, Hostel, Other), Batch Monthly Invoicing, Individual Invoices,
Concessions (Discount / Scholarship / Waiver), Partial & Full Payments, Advance Credit Wallet,
Refunds, Non-Destructive Invoice Cancellation, and Due / Collection PDF & Excel Reports.
"""

from datetime import date
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.fee import PAYMENT_CHANNELS
from app.models.school import SchoolSetting
from app.models.student import Student
from app.reports.fee_receipt_pdf import FeeReceiptPDFGenerator
from app.reports.finance_pdf import FinancePDFGenerator
from app.repositories.academic_repository import AcademicRepository
from app.repositories.fee_repository import FeeRepository
from app.security.session import session
from app.services.fee_service import FeeService, MONTH_NAMES
from app.ui.dialogs.fee_payment_dialog import FeePaymentDialog
from app.ui.dialogs.fee_structure_dialog import FeeStructureDialog


class FeesManagementPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.invoice_data_list = []
        self.payment_data_list = []
        self._init_ui()
        self.refresh_all()

    def _actor(self) -> str:
        return session.current_user.username if session.current_user else "admin"

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # 1. Header Banner
        header_h = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("Enterprise Fees & Billing Management")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A;")
        sub_lbl = QLabel(
            "Monthly tuition, admission, exam, library, transport, hostel & other fees • "
            "Discounts, scholarships, waivers, advance credits, refunds & audited invoices"
        )
        sub_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header_h.addLayout(title_box)
        header_h.addStretch()

        btn_monthly = QPushButton("+ Monthly Fee Batch")
        btn_monthly.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;")
        btn_monthly.clicked.connect(self._on_monthly_batch_dialog)
        header_h.addWidget(btn_monthly)

        btn_ind_inv = QPushButton("+ Individual Invoice")
        btn_ind_inv.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;")
        btn_ind_inv.clicked.connect(self._on_individual_invoice_dialog)
        header_h.addWidget(btn_ind_inv)

        btn_new_struct = QPushButton("+ New Fee Structure")
        btn_new_struct.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;")
        btn_new_struct.clicked.connect(self._on_add_fee_structure)
        header_h.addWidget(btn_new_struct)

        main_layout.addLayout(header_h)

        # 2. Financial KPI Cards
        kpi_frame = QFrame()
        kpi_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        kpi_layout = QHBoxLayout(kpi_frame)
        kpi_layout.setContentsMargins(16, 12, 16, 12)

        self.kpi_invoiced = QLabel("Total Billed: ৳0.00")
        self.kpi_invoiced.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        kpi_layout.addWidget(self.kpi_invoiced)
        kpi_layout.addSpacing(18)

        self.kpi_collected = QLabel("Net Collected: ৳0.00")
        self.kpi_collected.setStyleSheet("font-size: 13px; color: #059669; font-weight: bold;")
        kpi_layout.addWidget(self.kpi_collected)
        kpi_layout.addSpacing(18)

        self.kpi_due = QLabel("Outstanding Due: ৳0.00")
        self.kpi_due.setStyleSheet("font-size: 13px; color: #DC2626; font-weight: bold;")
        kpi_layout.addWidget(self.kpi_due)
        kpi_layout.addSpacing(18)

        self.kpi_discount = QLabel("Concessions: ৳0.00")
        self.kpi_discount.setStyleSheet("font-size: 13px; color: #7C3AED; font-weight: bold;")
        kpi_layout.addWidget(self.kpi_discount)
        kpi_layout.addSpacing(18)

        self.kpi_advance = QLabel("Advance Pool: ৳0.00")
        self.kpi_advance.setStyleSheet("font-size: 13px; color: #0284C7; font-weight: bold;")
        kpi_layout.addWidget(self.kpi_advance)
        kpi_layout.addSpacing(18)

        self.kpi_refunded = QLabel("Refunded: ৳0.00")
        self.kpi_refunded.setStyleSheet("font-size: 13px; color: #D97706; font-weight: bold;")
        kpi_layout.addWidget(self.kpi_refunded)
        kpi_layout.addStretch()

        main_layout.addWidget(kpi_frame)

        # 3. Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { font-weight: 600; padding: 8px 14px; margin-right: 4px; }
            QTabBar::tab:selected { background: #2563EB; color: white; border-radius: 4px; }
        """)

        self.tabs.addTab(self._build_invoices_tab(), "Student Invoices & Dues")
        self.tabs.addTab(self._build_structures_tab(), "Fee Structures & Categories")
        self.tabs.addTab(self._build_history_tab(), "Payment History & Refunds")
        self.tabs.addTab(self._build_advance_tab(), "Advance Credit Wallet")
        self.tabs.addTab(self._build_reports_tab(), "Due & Collection Reports")

        main_layout.addWidget(self.tabs)

    # ==================== TAB 1: INVOICES ====================
    def _build_invoices_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        filter_h = QHBoxLayout()
        filter_h.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Invoice #, Student Name, Student ID...")
        self.search_edit.textChanged.connect(self._load_invoices)
        filter_h.addWidget(self.search_edit)

        filter_h.addSpacing(12)
        filter_h.addWidget(QLabel("Class:"))
        self.class_combo = QComboBox()
        self.class_combo.addItem("All Classes", None)
        self.class_combo.currentIndexChanged.connect(self._load_invoices)
        filter_h.addWidget(self.class_combo)

        filter_h.addSpacing(12)
        filter_h.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["all", "Unpaid", "Partial", "Paid", "Overdue", "Partially Refunded", "Refunded", "Cancelled"])
        self.status_combo.currentIndexChanged.connect(self._load_invoices)
        filter_h.addWidget(self.status_combo)

        filter_h.addStretch()
        layout.addLayout(filter_h)

        self.invoice_table = QTableWidget()
        self.invoice_table.setColumnCount(10)
        self.invoice_table.setHorizontalHeaderLabels([
            "Invoice No", "Student ID", "Student Name", "Fee Head / Description",
            "Total (৳)", "Concession", "Paid (৳)", "Due (৳)", "Status", "Actions"
        ])
        self.invoice_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.invoice_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.invoice_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.invoice_table)
        return tab

    # ==================== TAB 2: STRUCTURES ====================
    def _build_structures_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        self.struct_table = QTableWidget()
        self.struct_table.setColumnCount(6)
        self.struct_table.setHorizontalHeaderLabels([
            "Title", "Category", "Class", "Amount (৳)", "Billing Frequency", "Due Date"
        ])
        self.struct_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.struct_table)
        return tab

    # ==================== TAB 3: PAYMENTS & REFUNDS ====================
    def _build_history_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        h_bar = QHBoxLayout()
        h_bar.addWidget(QLabel("Filter Receipts:"))
        self.history_search_edit = QLineEdit()
        self.history_search_edit.setPlaceholderText("Search receipt #, trx ID, provider, student...")
        self.history_search_edit.textChanged.connect(self._load_history)
        h_bar.addWidget(self.history_search_edit)

        h_bar.addSpacing(12)
        h_bar.addWidget(QLabel("Channel:"))
        self.history_channel_combo = QComboBox()
        self.history_channel_combo.addItems(["All Channels"] + list(PAYMENT_CHANNELS))
        self.history_channel_combo.currentIndexChanged.connect(self._load_history)
        h_bar.addWidget(self.history_channel_combo)

        h_bar.addStretch()
        layout.addLayout(h_bar)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels([
            "Receipt No", "Date", "Student", "Paid (৳)", "Refunded (৳)",
            "Channel", "Status", "Cashier", "Actions"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        layout.addWidget(self.history_table)
        return tab

    # ==================== TAB 4: ADVANCE WALLET ====================
    def _build_advance_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        top_bar = QHBoxLayout()
        btn_adv = QPushButton("+ Record Advance Deposit")
        btn_adv.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 14px; border-radius: 6px;")
        btn_adv.clicked.connect(self._on_record_advance_dialog)
        top_bar.addWidget(btn_adv)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.advance_table = QTableWidget()
        self.advance_table.setColumnCount(8)
        self.advance_table.setHorizontalHeaderLabels([
            "Voucher No", "Date", "Student", "Type", "Amount (৳)", "Balance After (৳)", "Channel", "Remarks"
        ])
        self.advance_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.advance_table)
        return tab

    # ==================== TAB 5: DUE & COLLECTION REPORTS ====================
    def _build_reports_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(12)

        ctrl_bar = QHBoxLayout()
        ctrl_bar.addWidget(QLabel("From:"))
        self.rep_start = QDateEdit(QDate.currentDate().addMonths(-1))
        self.rep_start.setCalendarPopup(True)
        ctrl_bar.addWidget(self.rep_start)

        ctrl_bar.addWidget(QLabel("To:"))
        self.rep_end = QDateEdit(QDate.currentDate())
        self.rep_end.setCalendarPopup(True)
        ctrl_bar.addWidget(self.rep_end)

        btn_refresh_rep = QPushButton("Run Reports")
        btn_refresh_rep.clicked.connect(self._load_reports_summary)
        ctrl_bar.addWidget(btn_refresh_rep)

        btn_due_xls = QPushButton("Due Report (Excel)")
        btn_due_xls.clicked.connect(self._export_due_excel)
        ctrl_bar.addWidget(btn_due_xls)

        btn_due_pdf = QPushButton("Due Report (PDF)")
        btn_due_pdf.clicked.connect(self._export_due_pdf)
        ctrl_bar.addWidget(btn_due_pdf)

        btn_col_xls = QPushButton("Collection (Excel)")
        btn_col_xls.clicked.connect(self._export_collection_excel)
        ctrl_bar.addWidget(btn_col_xls)

        btn_col_pdf = QPushButton("Collection (PDF)")
        btn_col_pdf.clicked.connect(self._export_collection_pdf)
        ctrl_bar.addWidget(btn_col_pdf)

        ctrl_bar.addStretch()
        layout.addLayout(ctrl_bar)

        self.rep_summary_lbl = QLabel("Loading aging and channel collection metrics...")
        self.rep_summary_lbl.setStyleSheet("background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; font-weight: bold;")
        layout.addWidget(self.rep_summary_lbl)

        self.due_report_table = QTableWidget()
        self.due_report_table.setColumnCount(7)
        self.due_report_table.setHorizontalHeaderLabels([
            "Invoice No", "Student", "Class", "Fee Category", "Due Date", "Aging Bucket", "Due (৳)"
        ])
        self.due_report_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.due_report_table)
        return tab

    # ==================== REFRESH & LOADERS ====================
    def refresh_all(self):
        db: Session = SessionLocal()
        try:
            FeeService.seed_default_fee_categories(db)
            kpi = FeeRepository.get_financial_kpi(db)
            self.kpi_invoiced.setText(f"Total Billed: ৳{kpi['total_invoiced']:,.2f}")
            self.kpi_collected.setText(f"Net Collected: ৳{kpi['total_collected']:,.2f}")
            self.kpi_due.setText(f"Outstanding Due: ৳{kpi['total_due']:,.2f}")
            self.kpi_discount.setText(f"Concessions: ৳{kpi['total_discount']:,.2f}")
            self.kpi_advance.setText(f"Advance Pool: ৳{kpi['total_advance_balance']:,.2f}")
            self.kpi_refunded.setText(f"Refunded: ৳{kpi['total_refunded']:,.2f}")

            classes = AcademicRepository.get_classes(db)
            curr_idx = self.class_combo.currentIndex()
            self.class_combo.blockSignals(True)
            self.class_combo.clear()
            self.class_combo.addItem("All Classes", None)
            for c in classes:
                self.class_combo.addItem(f"{c.name} ({c.group})", c.id)
            if 0 <= curr_idx < self.class_combo.count():
                self.class_combo.setCurrentIndex(curr_idx)
            self.class_combo.blockSignals(False)

            self._load_invoices()
            self._load_structures()
            self._load_history()
            self._load_advance_ledger()
            self._load_reports_summary()
        finally:
            db.close()

    def _load_invoices(self):
        search_text = self.search_edit.text().strip()
        class_id = self.class_combo.currentData()
        status = self.status_combo.currentText()

        db: Session = SessionLocal()
        try:
            invoices, _ = FeeRepository.get_student_fees(
                db, class_id=class_id, status=status, search=search_text or None, per_page=150
            )
            self.invoice_data_list = invoices
            self.invoice_table.setRowCount(len(invoices))

            for row, inv in enumerate(invoices):
                stu = inv.student
                self.invoice_table.setItem(row, 0, QTableWidgetItem(inv.invoice_number))
                self.invoice_table.setItem(row, 1, QTableWidgetItem(stu.student_id if stu else "-"))
                self.invoice_table.setItem(row, 2, QTableWidgetItem(stu.full_name if stu else "-"))
                self.invoice_table.setItem(row, 3, QTableWidgetItem(inv.display_title))
                self.invoice_table.setItem(row, 4, QTableWidgetItem(f"৳{float(inv.total_amount):,.2f}"))
                self.invoice_table.setItem(row, 5, QTableWidgetItem(f"৳{float(inv.discount_amount or 0.0):,.2f}"))
                self.invoice_table.setItem(row, 6, QTableWidgetItem(f"৳{float(inv.paid_amount or 0.0):,.2f}"))
                self.invoice_table.setItem(row, 7, QTableWidgetItem(f"৳{float(inv.due_amount):,.2f}"))
                self.invoice_table.setItem(row, 8, QTableWidgetItem(inv.status))

                btn_widget = QWidget()
                btn_h = QHBoxLayout(btn_widget)
                btn_h.setContentsMargins(2, 2, 2, 2)
                btn_h.setSpacing(4)

                if inv.due_amount > 0.01 and inv.status != "Cancelled":
                    pay_btn = QPushButton("Collect")
                    pay_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold; border-radius: 4px; padding: 3px 7px;")
                    pay_btn.clicked.connect(lambda _, fee_id=inv.id: self._on_collect_payment(fee_id))
                    btn_h.addWidget(pay_btn)

                    adj_btn = QPushButton("Adjust")
                    adj_btn.setStyleSheet("background-color: #7C3AED; color: white; border-radius: 4px; padding: 3px 7px;")
                    adj_btn.clicked.connect(lambda _, fee_id=inv.id: self._on_adjust_invoice(fee_id))
                    btn_h.addWidget(adj_btn)

                inv_pdf_btn = QPushButton("Invoice")
                inv_pdf_btn.setStyleSheet("background-color: #2563EB; color: white; border-radius: 4px; padding: 3px 7px;")
                inv_pdf_btn.clicked.connect(lambda _, fee_id=inv.id: self._on_download_invoice_pdf(fee_id))
                btn_h.addWidget(inv_pdf_btn)

                if inv.status != "Cancelled" and max(0.0, float(inv.paid_amount or 0.0) - float(inv.refunded_amount or 0.0)) <= 0.01:
                    cancel_btn = QPushButton("Cancel")
                    cancel_btn.setStyleSheet("background-color: #DC2626; color: white; border-radius: 4px; padding: 3px 7px;")
                    cancel_btn.clicked.connect(lambda _, fee_id=inv.id: self._on_cancel_invoice(fee_id))
                    btn_h.addWidget(cancel_btn)

                self.invoice_table.setCellWidget(row, 9, btn_widget)
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
                self.struct_table.setItem(row, 3, QTableWidgetItem(f"৳{float(s.amount):,.2f}"))
                self.struct_table.setItem(row, 4, QTableWidgetItem(s.frequency))
                due_d = s.due_date.strftime("%d-%b-%Y") if hasattr(s.due_date, "strftime") else str(s.due_date)
                self.struct_table.setItem(row, 5, QTableWidgetItem(due_d))
        finally:
            db.close()

    def _load_history(self):
        search_text = self.history_search_edit.text().strip()
        channel = self.history_channel_combo.currentText()
        db: Session = SessionLocal()
        try:
            payments, _ = FeeRepository.get_payments(
                db, search=search_text or None, payment_method=channel, per_page=150
            )
            self.payment_data_list = payments
            self.history_table.setRowCount(len(payments))

            for row, p in enumerate(payments):
                self.history_table.setItem(row, 0, QTableWidgetItem(p.receipt_no))
                p_date = p.payment_date.strftime("%d-%b-%Y") if hasattr(p.payment_date, "strftime") else str(p.payment_date)
                self.history_table.setItem(row, 1, QTableWidgetItem(p_date))
                self.history_table.setItem(row, 2, QTableWidgetItem(p.student.full_name if p.student else "-"))
                self.history_table.setItem(row, 3, QTableWidgetItem(f"৳{float(p.amount_paid):,.2f}"))
                self.history_table.setItem(row, 4, QTableWidgetItem(f"৳{float(p.refunded_amount or 0.0):,.2f}"))
                ch_str = p.payment_method + (f" ({p.channel_detail})" if p.channel_detail else "")
                self.history_table.setItem(row, 5, QTableWidgetItem(ch_str))
                self.history_table.setItem(row, 6, QTableWidgetItem(p.status))
                self.history_table.setItem(row, 7, QTableWidgetItem(p.collected_by))

                act_w = QWidget()
                act_h = QHBoxLayout(act_w)
                act_h.setContentsMargins(2, 2, 2, 2)
                act_h.setSpacing(4)

                pdf_btn = QPushButton("Receipt PDF")
                pdf_btn.setStyleSheet("background-color: #2563EB; color: white; border-radius: 4px; padding: 3px 7px;")
                pdf_btn.clicked.connect(lambda _, pid=p.id: self._on_download_receipt_by_id(pid))
                act_h.addWidget(pdf_btn)

                if p.refundable_balance > 0.01:
                    ref_btn = QPushButton("Refund")
                    ref_btn.setStyleSheet("background-color: #DC2626; color: white; border-radius: 4px; padding: 3px 7px;")
                    ref_btn.clicked.connect(lambda _, pid=p.id: self._on_refund_payment(pid))
                    act_h.addWidget(ref_btn)

                self.history_table.setCellWidget(row, 8, act_w)
        finally:
            db.close()

    def _load_advance_ledger(self):
        db: Session = SessionLocal()
        try:
            credits = FeeRepository.get_advance_credits(db, limit=150)
            self.advance_table.setRowCount(len(credits))
            for r_idx, cr in enumerate(credits):
                self.advance_table.setItem(r_idx, 0, QTableWidgetItem(cr.receipt_no))
                self.advance_table.setItem(r_idx, 1, QTableWidgetItem(str(cr.transaction_date)))
                self.advance_table.setItem(r_idx, 2, QTableWidgetItem(cr.student.full_name if cr.student else "-"))
                self.advance_table.setItem(r_idx, 3, QTableWidgetItem(cr.transaction_type))
                self.advance_table.setItem(r_idx, 4, QTableWidgetItem(f"৳{float(cr.amount):,.2f}"))
                self.advance_table.setItem(r_idx, 5, QTableWidgetItem(f"৳{float(cr.balance_after):,.2f}"))
                self.advance_table.setItem(r_idx, 6, QTableWidgetItem(cr.payment_method))
                self.advance_table.setItem(r_idx, 7, QTableWidgetItem(cr.remarks or "-"))
        finally:
            db.close()

    def _load_reports_summary(self):
        db: Session = SessionLocal()
        try:
            qd1, qd2 = self.rep_start.date(), self.rep_end.date()
            d1 = date(qd1.year(), qd1.month(), qd1.day())
            d2 = date(qd2.year(), qd2.month(), qd2.day())
            due_rep = FeeRepository.get_due_report(db)
            col_rep = FeeRepository.get_collection_report(db, start_date=d1, end_date=d2)
            aging = due_rep["aging_summary"]
            ch_txt = " | ".join(f"{k}: ৳{v:,.0f}" for k, v in col_rep["by_channel"].items()) or "No collections"
            self.rep_summary_lbl.setText(
                f"Collection ({d1} to {d2}): Net ৳{col_rep['net_collected']:,.2f} ({ch_txt})   ||   "
                f"Due Aging: Current ৳{aging['Current']:,.0f} | 1-30d ৳{aging['1-30 Days']:,.0f} | "
                f"31-60d ৳{aging['31-60 Days']:,.0f} | 61-90d ৳{aging['61-90 Days']:,.0f} | 90+d ৳{aging['90+ Days']:,.0f}"
            )
            rows = due_rep["rows"]
            self.due_report_table.setRowCount(len(rows))
            for idx, r in enumerate(rows):
                self.due_report_table.setItem(idx, 0, QTableWidgetItem(r["invoice_no"]))
                self.due_report_table.setItem(idx, 1, QTableWidgetItem(f"{r['student_name']} ({r['student_id']})"))
                self.due_report_table.setItem(idx, 2, QTableWidgetItem(r["class_name"]))
                self.due_report_table.setItem(idx, 3, QTableWidgetItem(r["category"]))
                self.due_report_table.setItem(idx, 4, QTableWidgetItem(str(r["due_date"])))
                self.due_report_table.setItem(idx, 5, QTableWidgetItem(r["aging_bucket"]))
                self.due_report_table.setItem(idx, 6, QTableWidgetItem(f"৳{r['due_amount']:,.2f}"))
        finally:
            db.close()

    # ==================== ACTIONS & DIALOGS ====================
    def _on_collect_payment(self, fee_id: int):
        dlg = FeePaymentDialog(self, student_fee_id=fee_id, current_user=self._actor())
        if dlg.exec() == FeePaymentDialog.Accepted:
            self.refresh_all()

    def _on_add_fee_structure(self):
        dlg = FeeStructureDialog(self)
        if dlg.exec() == FeeStructureDialog.Accepted:
            self.refresh_all()

    def _on_monthly_batch_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Generate Monthly Fee Invoices")
        dlg.setMinimumWidth(420)
        form = QFormLayout(dlg)

        db = SessionLocal()
        try:
            FeeService.seed_default_fee_categories(db)
            cats = FeeRepository.get_categories(db)
            classes = AcademicRepository.get_classes(db)
            curr_ay = AcademicRepository.get_current_academic_year(db)
        finally:
            db.close()

        cat_cb = QComboBox()
        for c in cats:
            cat_cb.addItem(f"{c.name} ({c.code})", c.id)
        cls_cb = QComboBox()
        for cl in classes:
            cls_cb.addItem(f"{cl.name} ({cl.group})", cl.id)
        month_cb = QComboBox()
        for idx, m_name in enumerate(MONTH_NAMES, 1):
            month_cb.addItem(m_name, idx)
        month_cb.setCurrentIndex(date.today().month - 1)
        year_sp = QSpinBox()
        year_sp.setRange(2020, 2050)
        year_sp.setValue(date.today().year)
        amt_sp = QDoubleSpinBox()
        amt_sp.setRange(10.0, 500000.0)
        amt_sp.setValue(2500.0)
        due_ed = QDateEdit(QDate.currentDate().addDays(10))
        due_ed.setCalendarPopup(True)

        form.addRow("Fee Category:", cat_cb)
        form.addRow("Class:", cls_cb)
        form.addRow("Billing Month:", month_cb)
        form.addRow("Year:", year_sp)
        form.addRow("Amount (৳):", amt_sp)
        form.addRow("Due Date:", due_ed)

        btn_ok = QPushButton("Generate Monthly Batch")
        btn_ok.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 14px;")
        btn_ok.clicked.connect(dlg.accept)
        form.addRow(btn_ok)

        if dlg.exec() == QDialog.Accepted:
            qd = due_ed.date()
            db2 = SessionLocal()
            try:
                ay_id = curr_ay.id if curr_ay else 1
                _, cnt, msg = FeeService.generate_monthly_fees(
                    db2,
                    category_id=cat_cb.currentData(),
                    class_id=cls_cb.currentData(),
                    academic_year_id=ay_id,
                    month=month_cb.currentData(),
                    year=year_sp.value(),
                    amount=amt_sp.value(),
                    due_date=date(qd.year(), qd.month(), qd.day()),
                    current_user=self._actor(),
                )
                QMessageBox.information(self, "Monthly Billing", msg)
                self.refresh_all()
            finally:
                db2.close()

    def _on_individual_invoice_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Create Individual Student Invoice")
        dlg.setMinimumWidth(420)
        form = QFormLayout(dlg)

        db = SessionLocal()
        try:
            FeeService.seed_default_fee_categories(db)
            cats = FeeRepository.get_categories(db)
            students = db.query(Student).filter(Student.is_deleted == False).order_by(Student.full_name.asc()).limit(500).all()
        finally:
            db.close()

        stu_cb = QComboBox()
        for s in students:
            stu_cb.addItem(f"{s.full_name} ({s.student_id})", s.id)
        cat_cb = QComboBox()
        for c in cats:
            cat_cb.addItem(f"{c.name} ({c.code})", c.id)
        title_ed = QLineEdit()
        title_ed.setPlaceholderText("Optional custom title (e.g. Lab Caution Fee)")
        amt_sp = QDoubleSpinBox()
        amt_sp.setRange(1.0, 500000.0)
        amt_sp.setValue(1000.0)
        due_ed = QDateEdit(QDate.currentDate().addDays(15))
        due_ed.setCalendarPopup(True)

        form.addRow("Student:", stu_cb)
        form.addRow("Fee Category:", cat_cb)
        form.addRow("Title:", title_ed)
        form.addRow("Amount (৳):", amt_sp)
        form.addRow("Due Date:", due_ed)

        btn_ok = QPushButton("Create Invoice")
        btn_ok.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 14px;")
        btn_ok.clicked.connect(dlg.accept)
        form.addRow(btn_ok)

        if dlg.exec() == QDialog.Accepted and stu_cb.currentData():
            qd = due_ed.date()
            db2 = SessionLocal()
            try:
                inv, msg = FeeService.create_student_invoice(
                    db2,
                    student_id=stu_cb.currentData(),
                    category_id=cat_cb.currentData(),
                    amount=amt_sp.value(),
                    due_date=date(qd.year(), qd.month(), qd.day()),
                    title=title_ed.text().strip() or None,
                    current_user=self._actor(),
                )
                QMessageBox.information(self, "Invoice Created", msg)
                if inv:
                    self.refresh_all()
            finally:
                db2.close()

    def _on_adjust_invoice(self, fee_id: int):
        adj_type, ok1 = QInputDialog.getItem(
            self, "Fee Concession", "Adjustment Type:", ["Discount", "Scholarship", "Waiver"], 0, False
        )
        if not ok1:
            return
        amt, ok2 = QInputDialog.getDouble(self, f"Apply {adj_type}", f"{adj_type} Amount (৳):", 500.0, 1.0, 500000.0, 2)
        if not ok2:
            return
        reason, ok3 = QInputDialog.getText(self, f"Apply {adj_type}", "Approval Reason:")
        if not ok3 or not reason.strip():
            return
        db = SessionLocal()
        try:
            fee, msg = FeeService.apply_adjustment(
                db, fee_id, adj_type, amt, reason.strip(), current_user=self._actor()
            )
            QMessageBox.information(self, "Adjustment", msg)
            if fee:
                self.refresh_all()
        finally:
            db.close()

    def _on_cancel_invoice(self, fee_id: int):
        reason, ok = QInputDialog.getText(self, "Cancel Invoice", "Mandatory cancellation reason:")
        if not ok or not reason.strip():
            return
        db = SessionLocal()
        try:
            fee, msg = FeeService.cancel_invoice(db, fee_id, reason.strip(), current_user=self._actor())
            QMessageBox.information(self, "Invoice Cancellation", msg)
            if fee:
                self.refresh_all()
        finally:
            db.close()

    def _on_refund_payment(self, payment_id: int):
        db = SessionLocal()
        try:
            pay = FeeRepository.get_payment_by_id(db, payment_id)
            if not pay:
                return
            max_ref = pay.refundable_balance
        finally:
            db.close()

        amt, ok1 = QInputDialog.getDouble(
            self, "Refund Payment", f"Refund Amount (Max ৳{max_ref:,.2f}):", max_ref, 1.0, max_ref, 2
        )
        if not ok1:
            return
        method, ok2 = QInputDialog.getItem(
            self, "Refund Channel", "Select Refund Method:", list(PAYMENT_CHANNELS), 0, False
        )
        if not ok2:
            return
        reason, ok3 = QInputDialog.getText(self, "Refund Reason", "Mandatory audit reason for refund:")
        if not ok3 or not reason.strip():
            return

        db2 = SessionLocal()
        try:
            refund, msg = FeeService.process_refund(
                db2, payment_id, amt, refund_method=method, reason=reason.strip(), current_user=self._actor()
            )
            QMessageBox.information(self, "Fee Refund", msg)
            if refund:
                self.refresh_all()
        finally:
            db2.close()

    def _on_record_advance_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Record Student Advance Deposit")
        dlg.setMinimumWidth(400)
        form = QFormLayout(dlg)

        db = SessionLocal()
        try:
            students = db.query(Student).filter(Student.is_deleted == False).order_by(Student.full_name.asc()).limit(500).all()
        finally:
            db.close()

        stu_cb = QComboBox()
        for s in students:
            stu_cb.addItem(f"{s.full_name} ({s.student_id})", s.id)
        amt_sp = QDoubleSpinBox()
        amt_sp.setRange(1.0, 500000.0)
        amt_sp.setValue(2000.0)
        ch_cb = QComboBox()
        ch_cb.addItems(list(PAYMENT_CHANNELS))
        rem_ed = QLineEdit()
        rem_ed.setPlaceholderText("Optional remarks / reference")

        form.addRow("Student:", stu_cb)
        form.addRow("Advance Amount (৳):", amt_sp)
        form.addRow("Channel:", ch_cb)
        form.addRow("Remarks:", rem_ed)

        btn_ok = QPushButton("Record Deposit")
        btn_ok.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 14px;")
        btn_ok.clicked.connect(dlg.accept)
        form.addRow(btn_ok)

        if dlg.exec() == QDialog.Accepted and stu_cb.currentData():
            db2 = SessionLocal()
            try:
                entry, msg = FeeService.record_advance_payment(
                    db2,
                    student_id=stu_cb.currentData(),
                    amount=amt_sp.value(),
                    payment_method=ch_cb.currentText(),
                    remarks=rem_ed.text().strip() or None,
                    current_user=self._actor(),
                )
                QMessageBox.information(self, "Advance Wallet", msg)
                if entry:
                    self.refresh_all()
            finally:
                db2.close()

    def _on_download_receipt_by_id(self, payment_id: int):
        db = SessionLocal()
        try:
            payment = FeeRepository.get_payment_by_id(db, payment_id)
            school = db.query(SchoolSetting).first()
            if not payment:
                return
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Fee Receipt", f"Receipt_{payment.receipt_no}.pdf", "PDF Documents (*.pdf)"
            )
            if file_path:
                FeeReceiptPDFGenerator.generate_receipt(payment, school, file_path)
                QMessageBox.information(self, "Saved", f"Receipt voucher saved to:\n{file_path}")
        finally:
            db.close()

    def _on_download_invoice_pdf(self, fee_id: int):
        db = SessionLocal()
        try:
            inv = FeeRepository.get_student_fee_by_id(db, fee_id)
            school = db.query(SchoolSetting).first()
            if not inv:
                return
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Fee Invoice", f"Invoice_{inv.invoice_number}.pdf", "PDF Documents (*.pdf)"
            )
            if file_path and FinancePDFGenerator.generate_invoice_pdf(inv, school, file_path):
                QMessageBox.information(self, "Saved", f"Invoice saved to:\n{file_path}")
        finally:
            db.close()

    def _export_due_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Due Report", f"DueReport_{date.today()}.xlsx", "Excel Files (*.xlsx)")
        if not path:
            return
        db = SessionLocal()
        try:
            if FeeService.export_due_report_excel(db, path):
                QMessageBox.information(self, "Exported", f"Due Report saved:\n{path}")
        finally:
            db.close()

    def _export_due_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Due Report PDF", f"DueReport_{date.today()}.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        db = SessionLocal()
        try:
            rep = FeeRepository.get_due_report(db)
            school = db.query(SchoolSetting).first()
            if FinancePDFGenerator.generate_due_report_pdf(rep, school, path):
                QMessageBox.information(self, "Exported", f"Due Report PDF saved:\n{path}")
        finally:
            db.close()

    def _export_collection_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Collection Report", f"CollectionReport_{date.today()}.xlsx", "Excel Files (*.xlsx)")
        if not path:
            return
        db = SessionLocal()
        try:
            qd1, qd2 = self.rep_start.date(), self.rep_end.date()
            if FeeService.export_collection_report_excel(db, path, start_date=date(qd1.year(), qd1.month(), qd1.day()), end_date=date(qd2.year(), qd2.month(), qd2.day())):
                QMessageBox.information(self, "Exported", f"Collection Report saved:\n{path}")
        finally:
            db.close()

    def _export_collection_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Collection Report PDF", f"CollectionReport_{date.today()}.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        db = SessionLocal()
        try:
            qd1, qd2 = self.rep_start.date(), self.rep_end.date()
            rep = FeeRepository.get_collection_report(db, start_date=date(qd1.year(), qd1.month(), qd1.day()), end_date=date(qd2.year(), qd2.month(), qd2.day()))
            school = db.query(SchoolSetting).first()
            if FinancePDFGenerator.generate_collection_report_pdf(rep, school, path):
                QMessageBox.information(self, "Exported", f"Collection Report PDF saved:\n{path}")
        finally:
            db.close()
