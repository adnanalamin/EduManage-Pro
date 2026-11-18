"""
EduManage Pro - Enterprise School Accounting, Ledger, Cashbook, Budget & Audit Page (PySide6)
Tabbed interface for Cash Book, General Ledger with Running Balance, Voucher Reversals
(no permanent deletions), Institutional Budgets & Variance Tracking, P&L Financial Summary,
Chart of Accounts, and Financial Audit Trail.
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

from app.database.connection import SessionLocal
from app.models.fee import PAYMENT_CHANNELS
from app.models.school import SchoolSetting
from app.reports.finance_pdf import FinancePDFGenerator
from app.reports.financial_statement_pdf import FinancialStatementPDFGenerator
from app.repositories.accounting_repository import AccountingRepository
from app.security.session import session
from app.services.accounting_service import AccountingService
from app.ui.dialogs.account_category_dialog import AccountCategoryDialog
from app.ui.dialogs.transaction_form_dialog import TransactionFormDialog


class AccountingPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh_all()

    def _actor(self) -> str:
        return session.current_user.username if session.current_user else "admin"

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header
        header_layout = QHBoxLayout()
        header_text = QVBoxLayout()
        h1 = QLabel("Enterprise School Accounting, Ledger & Budgets")
        h1.setStyleSheet("font-size: 20px; font-weight: bold; color: #3b82f6;")
        sub = QLabel("Immutable cashbook, running-balance general ledger, voucher reversals, budgets & audit trail.")
        sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        header_text.addWidget(h1)
        header_text.addWidget(sub)
        header_layout.addLayout(header_text)
        header_layout.addStretch()

        self.btn_income = QPushButton("+ Income Voucher")
        self.btn_income.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;")
        self.btn_income.clicked.connect(self._open_income_dialog)
        header_layout.addWidget(self.btn_income)

        self.btn_expense = QPushButton("+ Record Expense")
        self.btn_expense.setStyleSheet("background-color: #dc2626; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;")
        self.btn_expense.clicked.connect(self._open_expense_dialog)
        header_layout.addWidget(self.btn_expense)

        self.btn_excel = QPushButton("Cash Book (Excel)")
        self.btn_excel.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;")
        self.btn_excel.clicked.connect(self._export_cash_book_excel)
        header_layout.addWidget(self.btn_excel)

        self.btn_pdf = QPushButton("Financial Statement (PDF)")
        self.btn_pdf.setStyleSheet("background-color: #475569; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;")
        self.btn_pdf.clicked.connect(self._export_financial_statement_pdf)
        header_layout.addWidget(self.btn_pdf)

        main_layout.addLayout(header_layout)

        # 2. Executive KPI Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_income = self._create_kpi_card("Total Revenue / Inflows", "৳ 0.00", "#10b981")
        self.card_expense = self._create_kpi_card("Total Expenditure / Outflows", "৳ 0.00", "#ef4444")
        self.card_net = self._create_kpi_card("Net Operating Surplus / Deficit", "৳ 0.00", "#3b82f6")
        self.card_cash = self._create_kpi_card("Cash-in-Hand (Cash Channel)", "৳ 0.00", "#f59e0b")
        self.card_bank = self._create_kpi_card("Bank / Card / Mobile Balances", "৳ 0.00", "#38bdf8")

        cards_layout.addWidget(self.card_income)
        cards_layout.addWidget(self.card_expense)
        cards_layout.addWidget(self.card_net)
        cards_layout.addWidget(self.card_cash)
        cards_layout.addWidget(self.card_bank)
        main_layout.addLayout(cards_layout)

        # 3. Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { font-size: 13px; font-weight: bold; padding: 8px 14px; }
            QTabBar::tab:selected { color: #3b82f6; border-bottom: 2px solid #3b82f6; }
        """)

        self.tab_cashbook = QWidget()
        self._build_cashbook_tab()
        self.tabs.addTab(self.tab_cashbook, "Cash Book & Vouchers")

        self.tab_ledger = QWidget()
        self._build_ledger_tab()
        self.tabs.addTab(self.tab_ledger, "General Ledger")

        self.tab_budgets = QWidget()
        self._build_budgets_tab()
        self.tabs.addTab(self.tab_budgets, "Budgets & Variance")

        self.tab_pnl = QWidget()
        self._build_pnl_tab()
        self.tabs.addTab(self.tab_pnl, "Financial Summary & P&L")

        self.tab_audit = QWidget()
        self._build_audit_tab()
        self.tabs.addTab(self.tab_audit, "Chart of Accounts & Audit Trail")

        main_layout.addWidget(self.tabs)

    def _create_kpi_card(self, title: str, val: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: bold;")
        lbl_v = QLabel(val)
        lbl_v.setStyleSheet(f"font-size: 17px; font-weight: bold; color: {color_hex};")
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        return card

    # ==================== TAB 1: CASH BOOK ====================
    def _build_cashbook_tab(self):
        lay = QVBoxLayout(self.tab_cashbook)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        filter_bar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search voucher #, payee, memo, ref...")
        self.search_edit.textChanged.connect(self._filter_transactions)
        filter_bar.addWidget(self.search_edit)

        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "Income", "Expense"])
        self.type_filter.currentIndexChanged.connect(self._filter_transactions)
        filter_bar.addWidget(self.type_filter)

        self.channel_filter = QComboBox()
        self.channel_filter.addItems(["All Channels"] + list(PAYMENT_CHANNELS))
        self.channel_filter.currentIndexChanged.connect(self._filter_transactions)
        filter_bar.addWidget(self.channel_filter)

        self.cat_filter = QComboBox()
        self.cat_filter.addItem("All Categories", None)
        self.cat_filter.currentIndexChanged.connect(self._filter_transactions)
        filter_bar.addWidget(self.cat_filter)

        btn_cb_pdf = QPushButton("Cashbook PDF")
        btn_cb_pdf.clicked.connect(self._export_cashbook_pdf)
        filter_bar.addWidget(btn_cb_pdf)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh_all)
        filter_bar.addWidget(self.btn_refresh)

        lay.addLayout(filter_bar)

        self.table_transactions = QTableWidget()
        self.table_transactions.setColumnCount(11)
        self.table_transactions.setHorizontalHeaderLabels([
            "Voucher No", "Date", "Type", "Category Head",
            "Particulars / Payee", "Channel", "Ref No", "Amount (৳)", "Recorded By", "Status", "Action"
        ])
        self.table_transactions.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_transactions.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeToContents)
        self.table_transactions.setAlternatingRowColors(True)
        self.table_transactions.setSelectionBehavior(QTableWidget.SelectRows)
        lay.addWidget(self.table_transactions)

    # ==================== TAB 2: GENERAL LEDGER ====================
    def _build_ledger_tab(self):
        lay = QVBoxLayout(self.tab_ledger)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("From:"))
        self.ledger_start = QDateEdit(QDate.currentDate().addMonths(-3))
        self.ledger_start.setCalendarPopup(True)
        ctrl.addWidget(self.ledger_start)

        ctrl.addWidget(QLabel("To:"))
        self.ledger_end = QDateEdit(QDate.currentDate())
        self.ledger_end.setCalendarPopup(True)
        ctrl.addWidget(self.ledger_end)

        self.ledger_cat = QComboBox()
        self.ledger_cat.addItem("All Account Heads", None)
        ctrl.addWidget(self.ledger_cat)

        btn_run = QPushButton("Load Ledger")
        btn_run.clicked.connect(self._load_general_ledger)
        ctrl.addWidget(btn_run)

        self.ledger_totals_lbl = QLabel("Opening: ৳0.00 | Closing: ৳0.00")
        self.ledger_totals_lbl.setStyleSheet("font-weight: bold; color: #3b82f6;")
        ctrl.addWidget(self.ledger_totals_lbl)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self.table_ledger = QTableWidget()
        self.table_ledger.setColumnCount(8)
        self.table_ledger.setHorizontalHeaderLabels([
            "Date", "Voucher No", "Account Head", "Party", "Channel", "Credit (+)", "Debit (-)", "Running Balance"
        ])
        self.table_ledger.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.table_ledger)

    # ==================== TAB 3: BUDGETS ====================
    def _build_budgets_tab(self):
        lay = QVBoxLayout(self.tab_budgets)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        top = QHBoxLayout()
        top.addWidget(QLabel("Fiscal Year:"))
        self.budget_year_spin = QSpinBox()
        self.budget_year_spin.setRange(2020, 2050)
        self.budget_year_spin.setValue(date.today().year)
        self.budget_year_spin.valueChanged.connect(self._load_budgets_table)
        top.addWidget(self.budget_year_spin)

        btn_add_b = QPushButton("+ Set Category Budget")
        btn_add_b.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 6px 14px;")
        btn_add_b.clicked.connect(self._open_budget_dialog)
        top.addWidget(btn_add_b)

        btn_b_pdf = QPushButton("Budget Variance PDF")
        btn_b_pdf.clicked.connect(self._export_budget_pdf)
        top.addWidget(btn_b_pdf)
        top.addStretch()
        lay.addLayout(top)

        self.table_budgets = QTableWidget()
        self.table_budgets.setColumnCount(8)
        self.table_budgets.setHorizontalHeaderLabels([
            "Code", "Budget Title", "Category", "Period", "Allocated (৳)", "Actual (৳)", "Remaining (৳)", "Utilization & Alert"
        ])
        self.table_budgets.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.table_budgets)

    # ==================== TAB 4: P&L & SUMMARY ====================
    def _build_pnl_tab(self):
        lay = QVBoxLayout(self.tab_pnl)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(12)

        self.pnl_fee_banner = QLabel("Fee Receivables & Advance Liability Summary")
        self.pnl_fee_banner.setStyleSheet("background-color: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; padding: 10px; font-weight: bold;")
        lay.addWidget(self.pnl_fee_banner)

        split_layout = QHBoxLayout()

        income_box = QVBoxLayout()
        lbl_inc = QLabel("Revenue Inflow Breakdown by Head")
        lbl_inc.setStyleSheet("font-size: 14px; font-weight: bold; color: #10b981;")
        income_box.addWidget(lbl_inc)
        self.table_inc_breakdown = QTableWidget()
        self.table_inc_breakdown.setColumnCount(4)
        self.table_inc_breakdown.setHorizontalHeaderLabels(["Code", "Revenue Head", "Count", "Total (৳)"])
        self.table_inc_breakdown.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        income_box.addWidget(self.table_inc_breakdown)
        split_layout.addLayout(income_box)

        expense_box = QVBoxLayout()
        lbl_exp = QLabel("Operational Expenditure Breakdown by Head")
        lbl_exp.setStyleSheet("font-size: 14px; font-weight: bold; color: #ef4444;")
        expense_box.addWidget(lbl_exp)
        self.table_exp_breakdown = QTableWidget()
        self.table_exp_breakdown.setColumnCount(4)
        self.table_exp_breakdown.setHorizontalHeaderLabels(["Code", "Expense Head", "Count", "Total (৳)"])
        self.table_exp_breakdown.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        expense_box.addWidget(self.table_exp_breakdown)
        split_layout.addLayout(expense_box)

        lay.addLayout(split_layout)

    # ==================== TAB 5: COA & AUDIT TRAIL ====================
    def _build_audit_tab(self):
        lay = QVBoxLayout(self.tab_audit)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        top_bar = QHBoxLayout()
        btn_add_cat = QPushButton("+ Add Account Category Head")
        btn_add_cat.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 6px 14px;")
        btn_add_cat.clicked.connect(self._open_category_dialog)
        top_bar.addWidget(btn_add_cat)
        top_bar.addStretch()
        lay.addLayout(top_bar)

        self.table_categories = QTableWidget()
        self.table_categories.setColumnCount(6)
        self.table_categories.setHorizontalHeaderLabels(["Code", "Category Name", "Type", "Description", "System Head", "Status"])
        self.table_categories.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_categories.setMaximumHeight(200)
        lay.addWidget(self.table_categories)

        lbl_aud = QLabel("Immutable Financial Audit Trail (Fees, Payments, Refunds, Reversals & Vouchers)")
        lbl_aud.setStyleSheet("font-size: 13px; font-weight: bold; color: #3b82f6;")
        lay.addWidget(lbl_aud)

        self.table_audit = QTableWidget()
        self.table_audit.setColumnCount(7)
        self.table_audit.setHorizontalHeaderLabels([
            "Timestamp", "Module", "Action", "Reference No", "Amount (৳)", "Actor", "Reason"
        ])
        self.table_audit.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.table_audit)

    # ==================== REFRESH & DATA LOADING ====================
    def refresh_all(self):
        db = SessionLocal()
        try:
            AccountingService.seed_default_categories(db)
            summary = AccountingService.get_comprehensive_financial_summary(db)

            self.card_income.findChildren(QLabel)[1].setText(f"৳ {summary['total_income']:,.2f}")
            self.card_expense.findChildren(QLabel)[1].setText(f"৳ {summary['total_expense']:,.2f}")
            net_lbl = self.card_net.findChildren(QLabel)[1]
            net_lbl.setText(f"৳ {summary['net_surplus']:,.2f}")
            net_lbl.setStyleSheet(f"font-size: 17px; font-weight: bold; color: {'#10b981' if summary['is_profit'] else '#ef4444'};")
            self.card_cash.findChildren(QLabel)[1].setText(f"৳ {summary['cash_in_hand']:,.2f}")

            cb = summary.get("channel_balances", {})
            non_cash = cb.get("Bank", 0.0) + cb.get("Card", 0.0) + cb.get("Mobile Banking", 0.0) + cb.get("Other", 0.0)
            self.card_bank.findChildren(QLabel)[1].setText(f"৳ {non_cash:,.2f}")

            fr = summary.get("fee_receivables", {})
            self.pnl_fee_banner.setText(
                f"Fee Receivables: Net Billed ৳{fr.get('net_billed', 0):,.2f} | "
                f"Collected ৳{fr.get('net_collected', 0):,.2f} ({fr.get('collection_rate_pct', 0)}%) | "
                f"Outstanding Due ৳{fr.get('outstanding_due', 0):,.2f} | "
                f"Advance Wallet Pool ৳{fr.get('advance_wallet_liability', 0):,.2f}"
            )

            curr_cat_id = self.cat_filter.currentData()
            self.cat_filter.blockSignals(True)
            self.ledger_cat.blockSignals(True)
            self.cat_filter.clear()
            self.ledger_cat.clear()
            self.cat_filter.addItem("All Categories", None)
            self.ledger_cat.addItem("All Account Heads", None)
            cats = AccountingRepository.get_all_categories(db)
            for c in cats:
                self.cat_filter.addItem(f"{c.name} ({c.type})", c.id)
                self.ledger_cat.addItem(f"{c.name} ({c.type})", c.id)
            if curr_cat_id:
                idx = self.cat_filter.findData(curr_cat_id)
                if idx >= 0:
                    self.cat_filter.setCurrentIndex(idx)
            self.cat_filter.blockSignals(False)
            self.ledger_cat.blockSignals(False)

            self._filter_transactions()
            self._load_general_ledger()
            self._load_budgets_table()
            self._load_pnl_tables(db)
            self._load_categories_table(db)
            self._load_audit_table(db)
        finally:
            db.close()

    def _filter_transactions(self):
        db = SessionLocal()
        try:
            t_text = self.type_filter.currentText()
            trans_type = None if t_text == "All Types" else t_text
            channel = self.channel_filter.currentText()
            category_id = self.cat_filter.currentData()
            search = self.search_edit.text().strip() or None

            transactions, _ = AccountingRepository.get_transactions(
                db, trans_type=trans_type, category_id=category_id, payment_method=channel, search=search, limit=250
            )

            self.table_transactions.setRowCount(len(transactions))
            for row_idx, tx in enumerate(transactions):
                vch_item = QTableWidgetItem(tx.voucher_no)
                vch_item.setFont(QFont("Monospace", 9, QFont.Bold))
                self.table_transactions.setItem(row_idx, 0, vch_item)
                self.table_transactions.setItem(row_idx, 1, QTableWidgetItem(str(tx.transaction_date)))

                type_item = QTableWidgetItem(f"{tx.type}" + (" (REV)" if tx.entry_kind == "Reversal" else ""))
                type_item.setForeground(QColor("#10b981") if tx.type == "Income" else QColor("#ef4444"))
                self.table_transactions.setItem(row_idx, 2, type_item)

                cat_name = tx.category.name if tx.category else "General"
                self.table_transactions.setItem(row_idx, 3, QTableWidgetItem(cat_name))
                self.table_transactions.setItem(row_idx, 4, QTableWidgetItem(tx.paid_to_received_from))
                ch_txt = tx.payment_method + (f" ({tx.channel_detail})" if tx.channel_detail else "")
                self.table_transactions.setItem(row_idx, 5, QTableWidgetItem(ch_txt))
                self.table_transactions.setItem(row_idx, 6, QTableWidgetItem(tx.reference_no or "-"))

                amt_item = QTableWidgetItem(f"৳ {tx.amount:,.2f}")
                amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                amt_item.setForeground(QColor("#10b981") if tx.type == "Income" else QColor("#ef4444"))
                self.table_transactions.setItem(row_idx, 7, amt_item)

                self.table_transactions.setItem(row_idx, 8, QTableWidgetItem(tx.recorded_by))
                self.table_transactions.setItem(row_idx, 9, QTableWidgetItem(tx.status))

                if not tx.is_reversed and tx.entry_kind != "Reversal" and tx.status == "Approved":
                    rev_btn = QPushButton("Reverse")
                    rev_btn.setStyleSheet("background-color: #d97706; color: white; border-radius: 4px; padding: 3px 8px;")
                    rev_btn.clicked.connect(lambda _, tid=tx.id: self._on_reverse_voucher(tid))
                    self.table_transactions.setCellWidget(row_idx, 10, rev_btn)
                else:
                    lbl = QLabel(tx.status)
                    lbl.setAlignment(Qt.AlignCenter)
                    self.table_transactions.setCellWidget(row_idx, 10, lbl)
        finally:
            db.close()

    def _load_general_ledger(self):
        db = SessionLocal()
        try:
            qd1, qd2 = self.ledger_start.date(), self.ledger_end.date()
            d1 = date(qd1.year(), qd1.month(), qd1.day())
            d2 = date(qd2.year(), qd2.month(), qd2.day())
            cat_id = self.ledger_cat.currentData()
            ledger = AccountingService.get_general_ledger(db, start_date=d1, end_date=d2, category_id=cat_id)
            self.ledger_totals_lbl.setText(
                f"Opening: ৳{ledger['opening_balance']:,.2f} | Credits: ৳{ledger['total_credit']:,.2f} | "
                f"Debits: ৳{ledger['total_debit']:,.2f} | Closing: ৳{ledger['closing_balance']:,.2f}"
            )
            entries = ledger["entries"]
            self.table_ledger.setRowCount(len(entries))
            for r_idx, e in enumerate(entries):
                self.table_ledger.setItem(r_idx, 0, QTableWidgetItem(str(e["date"])))
                self.table_ledger.setItem(r_idx, 1, QTableWidgetItem(e["voucher_no"]))
                self.table_ledger.setItem(r_idx, 2, QTableWidgetItem(e["category_name"]))
                self.table_ledger.setItem(r_idx, 3, QTableWidgetItem(e["party"]))
                self.table_ledger.setItem(r_idx, 4, QTableWidgetItem(e["payment_method"]))
                self.table_ledger.setItem(r_idx, 5, QTableWidgetItem(f"৳ {e['credit']:,.2f}" if e["credit"] > 0 else "-"))
                self.table_ledger.setItem(r_idx, 6, QTableWidgetItem(f"৳ {e['debit']:,.2f}" if e["debit"] > 0 else "-"))
                self.table_ledger.setItem(r_idx, 7, QTableWidgetItem(f"৳ {e['running_balance']:,.2f}"))
        finally:
            db.close()

    def _load_budgets_table(self):
        db = SessionLocal()
        try:
            rep = AccountingService.get_budget_variance_report(db, fiscal_year=self.budget_year_spin.value())
            rows = rep["rows"]
            self.table_budgets.setRowCount(len(rows))
            for r_idx, r in enumerate(rows):
                self.table_budgets.setItem(r_idx, 0, QTableWidgetItem(r["budget_code"]))
                self.table_budgets.setItem(r_idx, 1, QTableWidgetItem(r["title"]))
                self.table_budgets.setItem(r_idx, 2, QTableWidgetItem(f"{r['category_name']} ({r['category_type']})"))
                self.table_budgets.setItem(r_idx, 3, QTableWidgetItem(r["period_type"]))
                self.table_budgets.setItem(r_idx, 4, QTableWidgetItem(f"৳ {r['allocated_amount']:,.2f}"))
                self.table_budgets.setItem(r_idx, 5, QTableWidgetItem(f"৳ {r['actual_amount']:,.2f}"))
                self.table_budgets.setItem(r_idx, 6, QTableWidgetItem(f"৳ {r['remaining_amount']:,.2f}"))
                st_item = QTableWidgetItem(f"{r['alert_status']} ({r['utilization_pct']}%)")
                if r["alert_status"] == "Over Budget":
                    st_item.setForeground(QColor("#ef4444"))
                elif r["alert_status"] == "Warning":
                    st_item.setForeground(QColor("#f59e0b"))
                else:
                    st_item.setForeground(QColor("#10b981"))
                self.table_budgets.setItem(r_idx, 7, st_item)
        finally:
            db.close()

    def _load_pnl_tables(self, db):
        inc_rows = AccountingRepository.get_category_breakdown(db, trans_type="Income")
        self.table_inc_breakdown.setRowCount(len(inc_rows))
        for r_idx, r in enumerate(inc_rows):
            self.table_inc_breakdown.setItem(r_idx, 0, QTableWidgetItem(r["code"]))
            self.table_inc_breakdown.setItem(r_idx, 1, QTableWidgetItem(r["category"]))
            self.table_inc_breakdown.setItem(r_idx, 2, QTableWidgetItem(str(r["count"])))
            amt_item = QTableWidgetItem(f"৳ {r['amount']:,.2f}")
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            amt_item.setForeground(QColor("#10b981"))
            self.table_inc_breakdown.setItem(r_idx, 3, amt_item)

        exp_rows = AccountingRepository.get_category_breakdown(db, trans_type="Expense")
        self.table_exp_breakdown.setRowCount(len(exp_rows))
        for r_idx, r in enumerate(exp_rows):
            self.table_exp_breakdown.setItem(r_idx, 0, QTableWidgetItem(r["code"]))
            self.table_exp_breakdown.setItem(r_idx, 1, QTableWidgetItem(r["category"]))
            self.table_exp_breakdown.setItem(r_idx, 2, QTableWidgetItem(str(r["count"])))
            amt_item = QTableWidgetItem(f"৳ {r['amount']:,.2f}")
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            amt_item.setForeground(QColor("#ef4444"))
            self.table_exp_breakdown.setItem(r_idx, 3, amt_item)

    def _load_categories_table(self, db):
        cats = AccountingRepository.get_all_categories(db, active_only=False)
        self.table_categories.setRowCount(len(cats))
        for r_idx, c in enumerate(cats):
            self.table_categories.setItem(r_idx, 0, QTableWidgetItem(c.code))
            self.table_categories.setItem(r_idx, 1, QTableWidgetItem(c.name))
            type_item = QTableWidgetItem(c.type)
            type_item.setForeground(QColor("#10b981") if c.type == "Income" else QColor("#ef4444"))
            self.table_categories.setItem(r_idx, 2, type_item)
            self.table_categories.setItem(r_idx, 3, QTableWidgetItem(c.description or "-"))
            self.table_categories.setItem(r_idx, 4, QTableWidgetItem("Yes (System)" if c.is_system else "No"))
            self.table_categories.setItem(r_idx, 5, QTableWidgetItem("Active" if c.is_active else "Inactive"))

    def _load_audit_table(self, db):
        logs = AccountingRepository.get_audit_logs(db, limit=150)
        self.table_audit.setRowCount(len(logs))
        for r_idx, lg in enumerate(logs):
            ts_str = lg.created_at.strftime("%Y-%m-%d %H:%M") if lg.created_at else "-"
            self.table_audit.setItem(r_idx, 0, QTableWidgetItem(ts_str))
            self.table_audit.setItem(r_idx, 1, QTableWidgetItem(lg.module))
            self.table_audit.setItem(r_idx, 2, QTableWidgetItem(lg.action))
            self.table_audit.setItem(r_idx, 3, QTableWidgetItem(lg.reference_no or "-"))
            self.table_audit.setItem(r_idx, 4, QTableWidgetItem(f"৳ {float(lg.amount):,.2f}" if lg.amount is not None else "-"))
            self.table_audit.setItem(r_idx, 5, QTableWidgetItem(lg.actor_username))
            self.table_audit.setItem(r_idx, 6, QTableWidgetItem(lg.reason or "-"))

    # ==================== DIALOGS & EXPORTS ====================
    def _open_income_dialog(self):
        dialog = TransactionFormDialog(self, default_type="Income")
        if dialog.exec():
            self.refresh_all()

    def _open_expense_dialog(self):
        dialog = TransactionFormDialog(self, default_type="Expense")
        if dialog.exec():
            self.refresh_all()

    def _open_category_dialog(self):
        dialog = AccountCategoryDialog(self)
        if dialog.exec():
            self.refresh_all()

    def _on_reverse_voucher(self, tx_id: int):
        reason, ok = QInputDialog.getText(
            self, "Reverse Financial Voucher",
            "Permanent deletion is disabled. Enter mandatory audit reason to post a compensating reversal:"
        )
        if not ok or not reason.strip():
            return
        db = SessionLocal()
        try:
            contra, msg = AccountingService.reverse_transaction(db, tx_id, reason.strip(), actor_username=self._actor())
            QMessageBox.information(self, "Voucher Reversal", msg)
            if contra:
                self.refresh_all()
        finally:
            db.close()

    def _open_budget_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Create Institutional Category Budget")
        dlg.setMinimumWidth(420)
        form = QFormLayout(dlg)

        db = SessionLocal()
        try:
            cats = AccountingRepository.get_all_categories(db)
        finally:
            db.close()

        cat_cb = QComboBox()
        for c in cats:
            cat_cb.addItem(f"{c.name} ({c.type})", c.id)
        title_ed = QLineEdit()
        title_ed.setPlaceholderText("e.g. FY 2026 Faculty Payroll Budget")
        yr_sp = QSpinBox()
        yr_sp.setRange(2020, 2050)
        yr_sp.setValue(self.budget_year_spin.value())
        per_cb = QComboBox()
        per_cb.addItems(["Annual", "Quarterly", "Monthly"])
        amt_sp = QDoubleSpinBox()
        amt_sp.setRange(0.0, 50000000.0)
        amt_sp.setValue(100000.0)
        thr_sp = QDoubleSpinBox()
        thr_sp.setRange(10.0, 100.0)
        thr_sp.setValue(80.0)

        form.addRow("Account Category:", cat_cb)
        form.addRow("Budget Title:", title_ed)
        form.addRow("Fiscal Year:", yr_sp)
        form.addRow("Period Type:", per_cb)
        form.addRow("Allocated Amount (৳):", amt_sp)
        form.addRow("Warning Threshold (%):", thr_sp)

        btn_save = QPushButton("Save Budget")
        btn_save.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 6px 14px;")
        btn_save.clicked.connect(dlg.accept)
        form.addRow(btn_save)

        if dlg.exec() == QDialog.Accepted and cat_cb.currentData():
            db2 = SessionLocal()
            try:
                b, msg = AccountingService.create_or_update_budget(
                    db2,
                    {
                        "category_id": cat_cb.currentData(),
                        "title": title_ed.text().strip() or None,
                        "fiscal_year": yr_sp.value(),
                        "period_type": per_cb.currentText(),
                        "allocated_amount": amt_sp.value(),
                        "alert_threshold_pct": thr_sp.value(),
                    },
                    actor_username=self._actor(),
                )
                QMessageBox.information(self, "Budget", msg)
                if b:
                    self.refresh_all()
            finally:
                db2.close()

    def _export_cash_book_excel(self):
        default_name = f"EduManagePro_CashBook_{date.today().strftime('%Y%m%d')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Export Cash Book (Excel)", default_name, "Excel Files (*.xlsx)")
        if not path:
            return
        db = SessionLocal()
        try:
            school = db.query(SchoolSetting).first()
            s_info = {"name": school.school_name, "eiin": school.eiin_number} if school else None
            if AccountingService.export_cash_book_excel(db, path, school_info=s_info):
                QMessageBox.information(self, "Export Successful", f"Cash book ledger exported to:\n{path}")
        finally:
            db.close()

    def _export_cashbook_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Cashbook PDF", f"Cashbook_{date.today()}.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        db = SessionLocal()
        try:
            ledger = AccountingService.get_general_ledger(db)
            school = db.query(SchoolSetting).first()
            if FinancePDFGenerator.generate_cashbook_pdf(ledger, school, path):
                QMessageBox.information(self, "Exported", f"Cashbook PDF saved to:\n{path}")
        finally:
            db.close()

    def _export_budget_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Budget Variance PDF", f"BudgetVariance_{self.budget_year_spin.value()}.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        db = SessionLocal()
        try:
            rep = AccountingService.get_budget_variance_report(db, fiscal_year=self.budget_year_spin.value())
            school = db.query(SchoolSetting).first()
            if FinancePDFGenerator.generate_budget_report_pdf(rep, school, path):
                QMessageBox.information(self, "Exported", f"Budget Variance PDF saved to:\n{path}")
        finally:
            db.close()

    def _export_financial_statement_pdf(self):
        default_name = f"EduManagePro_FinancialStatement_{date.today().strftime('%Y%m%d')}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Export Statement of Accounts (PDF)", default_name, "PDF Files (*.pdf)")
        if not path:
            return
        db = SessionLocal()
        try:
            summary = AccountingService.get_comprehensive_financial_summary(db)
            inc_rows = summary["income_breakdown"]
            exp_rows = summary["expense_breakdown"]
            school = db.query(SchoolSetting).first()
            school_info = {
                "name": school.school_name if school else "EduManage Pro Model High School",
                "eiin": school.eiin_number if school else "134211",
                "phone": school.phone if school else "+880 1712-345678",
                "address": school.address if school else "Uttara, Dhaka",
            }
            ok = FinancialStatementPDFGenerator.generate_statement(
                summary=summary,
                income_breakdown=inc_rows,
                expense_breakdown=exp_rows,
                school_info=school_info,
                period_str=f"Fiscal Year {date.today().year}",
                output_path=path,
            )
            if ok:
                QMessageBox.information(self, "Export Successful", f"Financial Statement PDF generated:\n{path}")
        finally:
            db.close()
