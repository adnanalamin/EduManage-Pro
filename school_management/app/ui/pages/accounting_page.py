"""
EduManage Pro - School Accounting & Expense Management Page (PySide6)
Tabbed interface for Daily Cash Book, Financial Statements, Profit/Loss, and Chart of Accounts.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QLineEdit, QDateEdit, QTabWidget, QMessageBox, QFileDialog,
    QFrame
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont
from datetime import date, datetime
import os
from app.database.connection import SessionLocal
from app.repositories.accounting_repository import AccountingRepository
from app.services.accounting_service import AccountingService
from app.reports.financial_statement_pdf import FinancialStatementPDFGenerator
from app.ui.dialogs.transaction_form_dialog import TransactionFormDialog
from app.ui.dialogs.account_category_dialog import AccountCategoryDialog


class AccountingPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh_all()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 1. Header with Title & Action Buttons
        header_layout = QHBoxLayout()
        header_text = QVBoxLayout()
        h1 = QLabel("School Accounting & Expense Management")
        h1.setStyleSheet("font-size: 20px; font-weight: bold; color: #3b82f6;")
        sub = QLabel("Daily cash book, operational expenses, income vouchers, and audited financial statements.")
        sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        header_text.addWidget(h1)
        header_text.addWidget(sub)
        header_layout.addLayout(header_text)
        header_layout.addStretch()

        self.btn_income = QPushButton("+ Add Income Voucher")
        self.btn_income.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")
        self.btn_income.clicked.connect(self._open_income_dialog)
        header_layout.addWidget(self.btn_income)

        self.btn_expense = QPushButton("+ Record Expense")
        self.btn_expense.setStyleSheet("background-color: #dc2626; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")
        self.btn_expense.clicked.connect(self._open_expense_dialog)
        header_layout.addWidget(self.btn_expense)

        self.btn_excel = QPushButton("Export Cash Book (Excel)")
        self.btn_excel.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")
        self.btn_excel.clicked.connect(self._export_cash_book_excel)
        header_layout.addWidget(self.btn_excel)

        self.btn_pdf = QPushButton("Financial Statement (PDF)")
        self.btn_pdf.setStyleSheet("background-color: #475569; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")
        self.btn_pdf.clicked.connect(self._export_financial_statement_pdf)
        header_layout.addWidget(self.btn_pdf)

        main_layout.addLayout(header_layout)

        # 2. Executive KPI Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_income = self._create_kpi_card("Total Revenue / Inflows", "৳ 0.00", "#10b981")
        self.card_expense = self._create_kpi_card("Total Expenditure / Outflows", "৳ 0.00", "#ef4444")
        self.card_net = self._create_kpi_card("Net Operating Surplus / Deficit", "৳ 0.00", "#3b82f6")
        self.card_cash = self._create_kpi_card("Current Cash-in-Hand", "৳ 0.00", "#f59e0b")

        cards_layout.addWidget(self.card_income)
        cards_layout.addWidget(self.card_expense)
        cards_layout.addWidget(self.card_net)
        cards_layout.addWidget(self.card_cash)
        main_layout.addLayout(cards_layout)

        # 3. Tabbed Views
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { font-size: 13px; font-weight: bold; padding: 8px 18px; }
            QTabBar::tab:selected { color: #3b82f6; border-bottom: 2px solid #3b82f6; }
        """)

        # Tab 1: Cash Book & Daily Transactions
        self.tab_cashbook = QWidget()
        self._build_cashbook_tab()
        self.tabs.addTab(self.tab_cashbook, "Cash Book & Vouchers")

        # Tab 2: Profit & Loss Statement
        self.tab_pnl = QWidget()
        self._build_pnl_tab()
        self.tabs.addTab(self.tab_pnl, "Income & Expenditure Breakdown")

        # Tab 3: Chart of Accounts
        self.tab_categories = QWidget()
        self._build_categories_tab()
        self.tabs.addTab(self.tab_categories, "Chart of Accounts Heads")

        main_layout.addWidget(self.tabs)

    def _create_kpi_card(self, title: str, val: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: bold;")
        lbl_v = QLabel(val)
        lbl_v.setStyleSheet(f"font-size: 19px; font-weight: bold; color: {color_hex};")
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        return card

    # -------------------------------------------------------------
    # Tab 1: Cash Book
    # -------------------------------------------------------------
    def _build_cashbook_tab(self):
        lay = QVBoxLayout(self.tab_cashbook)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        filter_bar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by voucher #, payee, memo, reference...")
        self.search_edit.textChanged.connect(self._filter_transactions)
        filter_bar.addWidget(self.search_edit)

        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "Income", "Expense"])
        self.type_filter.currentIndexChanged.connect(self._filter_transactions)
        filter_bar.addWidget(self.type_filter)

        self.cat_filter = QComboBox()
        self.cat_filter.addItem("All Categories", None)
        self.cat_filter.currentIndexChanged.connect(self._filter_transactions)
        filter_bar.addWidget(self.cat_filter)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh_all)
        filter_bar.addWidget(self.btn_refresh)

        lay.addLayout(filter_bar)

        self.table_transactions = QTableWidget()
        self.table_transactions.setColumnCount(10)
        self.table_transactions.setHorizontalHeaderLabels([
            "Voucher No", "Date", "Type", "Category Head",
            "Particulars / Payee", "Method", "Ref No", "Amount (৳)", "Recorded By", "Status"
        ])
        self.table_transactions.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_transactions.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_transactions.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_transactions.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_transactions.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_transactions.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table_transactions.setAlternatingRowColors(True)
        self.table_transactions.setSelectionBehavior(QTableWidget.SelectRows)
        lay.addWidget(self.table_transactions)

    # -------------------------------------------------------------
    # Tab 2: Profit & Loss Breakdown
    # -------------------------------------------------------------
    def _build_pnl_tab(self):
        lay = QVBoxLayout(self.tab_pnl)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(12)

        split_layout = QHBoxLayout()

        # Left: Income Breakdown
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

        # Right: Expense Breakdown
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

    # -------------------------------------------------------------
    # Tab 3: Chart of Accounts
    # -------------------------------------------------------------
    def _build_categories_tab(self):
        lay = QVBoxLayout(self.tab_categories)
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
        self.table_categories.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_categories.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_categories.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_categories.setAlternatingRowColors(True)
        lay.addWidget(self.table_categories)

    # -------------------------------------------------------------
    # Refresh Logic
    # -------------------------------------------------------------
    def refresh_all(self):
        db = SessionLocal()
        try:
            AccountingService.seed_default_categories(db)
            summary = AccountingRepository.get_financial_summary(db)

            # Update KPI labels
            self.card_income.findChildren(QLabel)[1].setText(f"৳ {summary['total_income']:,.2f}")
            self.card_expense.findChildren(QLabel)[1].setText(f"৳ {summary['total_expense']:,.2f}")
            net_lbl = self.card_net.findChildren(QLabel)[1]
            net_lbl.setText(f"৳ {summary['net_surplus']:,.2f}")
            net_lbl.setStyleSheet(f"font-size: 19px; font-weight: bold; color: {'#10b981' if summary['is_profit'] else '#ef4444'};")
            self.card_cash.findChildren(QLabel)[1].setText(f"৳ {summary['cash_in_hand']:,.2f}")

            # Refresh Category Dropdown
            curr_cat_id = self.cat_filter.currentData()
            self.cat_filter.blockSignals(True)
            self.cat_filter.clear()
            self.cat_filter.addItem("All Categories", None)
            cats = AccountingRepository.get_all_categories(db)
            for c in cats:
                self.cat_filter.addItem(f"{c.name} ({c.type})", c.id)
            if curr_cat_id:
                idx = self.cat_filter.findData(curr_cat_id)
                if idx >= 0:
                    self.cat_filter.setCurrentIndex(idx)
            self.cat_filter.blockSignals(False)

            self._filter_transactions()
            self._load_pnl_tables(db)
            self._load_categories_table(db)
        finally:
            db.close()

    def _filter_transactions(self):
        db = SessionLocal()
        try:
            t_text = self.type_filter.currentText()
            trans_type = None if t_text == "All Types" else t_text
            category_id = self.cat_filter.currentData()
            search = self.search_edit.text().strip() or None

            transactions, _ = AccountingRepository.get_transactions(
                db, trans_type=trans_type, category_id=category_id, search=search, limit=200
            )

            self.table_transactions.setRowCount(len(transactions))
            for row_idx, tx in enumerate(transactions):
                vch_item = QTableWidgetItem(tx.voucher_no)
                vch_item.setFont(QFont("Monospace", 9, QFont.Bold))
                self.table_transactions.setItem(row_idx, 0, vch_item)

                self.table_transactions.setItem(row_idx, 1, QTableWidgetItem(str(tx.transaction_date)))

                type_item = QTableWidgetItem(tx.type)
                type_item.setForeground(QColor("#10b981") if tx.type == "Income" else QColor("#ef4444"))
                type_item.setFont(QFont("Helvetica", 9, QFont.Bold))
                self.table_transactions.setItem(row_idx, 2, type_item)

                cat_name = tx.category.name if tx.category else "General"
                self.table_transactions.setItem(row_idx, 3, QTableWidgetItem(cat_name))

                self.table_transactions.setItem(row_idx, 4, QTableWidgetItem(tx.paid_to_received_from))
                self.table_transactions.setItem(row_idx, 5, QTableWidgetItem(tx.payment_method))
                self.table_transactions.setItem(row_idx, 6, QTableWidgetItem(tx.reference_no or "-"))

                amt_item = QTableWidgetItem(f"৳ {tx.amount:,.2f}")
                amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                amt_item.setFont(QFont("Helvetica", 9, QFont.Bold))
                amt_item.setForeground(QColor("#10b981") if tx.type == "Income" else QColor("#ef4444"))
                self.table_transactions.setItem(row_idx, 7, amt_item)

                self.table_transactions.setItem(row_idx, 8, QTableWidgetItem(tx.recorded_by))
                self.table_transactions.setItem(row_idx, 9, QTableWidgetItem(tx.status))
        finally:
            db.close()

    def _load_pnl_tables(self, db):
        # Incomes
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

        # Expenses
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

    # -------------------------------------------------------------
    # Dialog Openers & Exporters
    # -------------------------------------------------------------
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

    def _export_cash_book_excel(self):
        default_name = f"EduManagePro_CashBook_{date.today().strftime('%Y%m%d')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Export Cash Book (Excel)", default_name, "Excel Files (*.xlsx)")
        if not path:
            return

        db = SessionLocal()
        try:
            ok = AccountingService.export_cash_book_excel(db, path)
            if ok:
                QMessageBox.information(self, "Export Successful", f"Cash book ledger successfully exported to:\n{path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Could not write Cash Book Excel workbook.")
        finally:
            db.close()

    def _export_financial_statement_pdf(self):
        default_name = f"EduManagePro_FinancialStatement_{date.today().strftime('%Y%m%d')}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Export Statement of Accounts (PDF)", default_name, "PDF Files (*.pdf)")
        if not path:
            return

        db = SessionLocal()
        try:
            summary = AccountingRepository.get_financial_summary(db)
            inc_rows = AccountingRepository.get_category_breakdown(db, trans_type="Income")
            exp_rows = AccountingRepository.get_category_breakdown(db, trans_type="Expense")

            school_info = {
                "name": "Ideal Model High School & College",
                "eiin": "134211",
                "phone": "+880 1712-345678",
                "address": "Plot 12, Road 4, Sector 7, Uttara, Dhaka"
            }

            ok = FinancialStatementPDFGenerator.generate_statement(
                summary=summary,
                income_breakdown=inc_rows,
                expense_breakdown=exp_rows,
                school_info=school_info,
                period_str=f"Fiscal Year {date.today().year}",
                output_path=path
            )
            if ok:
                QMessageBox.information(self, "Export Successful", f"Official Financial Statement PDF generated:\n{path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Failed to compile Financial Statement PDF.")
        finally:
            db.close()
