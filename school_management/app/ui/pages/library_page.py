"""
EduManage Pro - Library Circulation & Book Management Page
Phase 10: PySide6 4-Tab Interface (Book Catalog, Circulation Desk, Member Passes & Categories)
"""

import os
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QComboBox, QLineEdit, QPushButton, QLabel, QHeaderView,
    QMessageBox, QFileDialog, QFrame
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from app.models.library import BookCategory, Book, LibraryMember, BookCirculation
from app.models.school import SchoolSetting
from app.repositories.library_repository import LibraryRepository
from app.services.library_service import LibraryService
from app.reports.library_card_pdf import LibraryCardGenerator
from app.reports.circulation_report_pdf import CirculationReportPDFGenerator
from app.ui.dialogs.book_form_dialog import BookFormDialog
from app.ui.dialogs.issue_book_dialog import IssueBookDialog
from app.ui.dialogs.return_book_dialog import ReturnBookDialog
from app.database.connection import SessionLocal


class LibraryPage(QWidget):
    """Main Library Management page for cataloging, loan circulations, fines, and ID passes."""

    def __init__(self, parent=None, db_session: Optional[Session] = None, session_manager=None):
        super().__init__(parent)
        self.session_manager = session_manager
        self.db_session = db_session if db_session is not None else SessionLocal()

        # Seed defaults if first run
        LibraryService.seed_default_library_data(self.db_session)

        self._setup_ui()
        self.refresh_data()

    def refresh_all(self):
        """Standard lifecycle hook called on navigation."""
        self.refresh_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header Title & Quick Actions
        title_box = QHBoxLayout()
        title_label = QLabel("Library Catalog & Circulation Desk")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        title_box.addWidget(title_label)
        title_box.addStretch()

        export_excel_btn = QPushButton("📊 Export Catalog (Excel)")
        export_excel_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        export_excel_btn.clicked.connect(self._export_catalog_excel)
        title_box.addWidget(export_excel_btn)

        audit_pdf_btn = QPushButton("📑 Circulation Audit Report (PDF)")
        audit_pdf_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        audit_pdf_btn.clicked.connect(self._generate_circulation_pdf)
        title_box.addWidget(audit_pdf_btn)

        main_layout.addLayout(title_box)

        # 2. KPI Metrics Bar
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(10)
        self.lbl_titles = self._create_kpi_card("Total Titles", "0", "#0284C7")
        self.lbl_copies = self._create_kpi_card("Total Copies", "0", "#475569")
        self.lbl_available = self._create_kpi_card("Available Copies", "0", "#059669")
        self.lbl_issued = self._create_kpi_card("Active Loans", "0", "#D97706")
        self.lbl_overdue = self._create_kpi_card("Overdue Loans", "0", "#DC2626")
        self.lbl_fines = self._create_kpi_card("Fines Collected", "$ 0.00", "#7C3AED")
        main_layout.addLayout(self.kpi_layout)

        # 3. Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                font-weight: 600;
                padding: 8px 18px;
                color: #475569;
            }
            QTabBar::tab:selected {
                color: #065F46;
                border-bottom: 2px solid #065F46;
            }
        """)

        # Tab 1: Book Catalog
        self.tab_catalog = QWidget()
        self._setup_catalog_tab()
        self.tabs.addTab(self.tab_catalog, "📚 Book Catalog & Inventory")

        # Tab 2: Circulation Desk
        self.tab_circulation = QWidget()
        self._setup_circulation_tab()
        self.tabs.addTab(self.tab_circulation, "🔄 Circulation Desk (Loans & Returns)")

        # Tab 3: Members Register
        self.tab_members = QWidget()
        self._setup_members_tab()
        self.tabs.addTab(self.tab_members, "🪪 Library Member Passes")

        # Tab 4: Categories & Shelves
        self.tab_categories = QWidget()
        self._setup_categories_tab()
        self.tabs.addTab(self.tab_categories, "🏷️ Categories & Rack Map")

        main_layout.addWidget(self.tabs)

    def _create_kpi_card(self, title: str, default_val: str, color_hex: str) -> QLabel:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid #E2E8F0;
                border-top: 3px solid {color_hex};
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """)
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(8, 4, 8, 4)
        vbox.setSpacing(2)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 500;")
        v_lbl = QLabel(default_val)
        v_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color_hex};")

        vbox.addWidget(t_lbl)
        vbox.addWidget(v_lbl)
        self.kpi_layout.addWidget(frame)
        return v_lbl

    # ---------------- TAB 1: BOOK CATALOG ----------------
    def _setup_catalog_tab(self):
        layout = QVBoxLayout(self.tab_catalog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Filters & Search
        ctrl_box = QHBoxLayout()
        ctrl_box.addWidget(QLabel("Category:"))
        self.cat_filter_combo = QComboBox()
        self.cat_filter_combo.addItem("All Categories", None)
        self.cat_filter_combo.currentIndexChanged.connect(self.load_catalog_table)
        ctrl_box.addWidget(self.cat_filter_combo)

        ctrl_box.addWidget(QLabel("Search:"))
        self.catalog_search_input = QLineEdit()
        self.catalog_search_input.setPlaceholderText("Search by Title, Author, ISBN, or Accession...")
        self.catalog_search_input.textChanged.connect(self.load_catalog_table)
        ctrl_box.addWidget(self.catalog_search_input)

        add_book_btn = QPushButton("+ Add New Book")
        add_book_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        add_book_btn.clicked.connect(self._add_book)
        ctrl_box.addWidget(add_book_btn)

        layout.addLayout(ctrl_box)

        # Catalog Table
        self.catalog_table = QTableWidget()
        headers = [
            "Accession No", "Title", "Author", "Category", "Rack / Shelf",
            "Total", "Avail", "Issued", "Price", "Status", "Actions"
        ]
        self.catalog_table.setColumnCount(len(headers))
        self.catalog_table.setHorizontalHeaderLabels(headers)
        self.catalog_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.catalog_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeToContents)
        self.catalog_table.verticalHeader().setVisible(False)
        self.catalog_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.catalog_table.setAlternatingRowColors(True)

        layout.addWidget(self.catalog_table)

    def load_catalog_table(self):
        cat_id = self.cat_filter_combo.currentData()
        search = self.catalog_search_input.text().strip() or None

        books = LibraryRepository.get_books(self.db_session, category_id=cat_id, search_query=search)
        self.catalog_table.setRowCount(len(books))

        for row, b in enumerate(books):
            # Accession
            it_acc = QTableWidgetItem(b.accession_no)
            it_acc.setTextAlignment(Qt.AlignCenter)
            self.catalog_table.setItem(row, 0, it_acc)

            # Title & Author
            self.catalog_table.setItem(row, 1, QTableWidgetItem(b.title))
            self.catalog_table.setItem(row, 2, QTableWidgetItem(b.author))

            # Category
            cat_name = b.category.name if b.category else "Uncategorized"
            self.catalog_table.setItem(row, 3, QTableWidgetItem(cat_name))

            # Rack / Shelf
            loc = f"{b.rack_number or '-'} / {b.shelf_number or '-'}"
            it_loc = QTableWidgetItem(loc)
            it_loc.setTextAlignment(Qt.AlignCenter)
            self.catalog_table.setItem(row, 4, it_loc)

            # Counts
            it_tot = QTableWidgetItem(str(b.total_copies))
            it_tot.setTextAlignment(Qt.AlignCenter)
            self.catalog_table.setItem(row, 5, it_tot)

            it_av = QTableWidgetItem(str(b.available_copies))
            it_av.setTextAlignment(Qt.AlignCenter)
            if b.available_copies > 0:
                it_av.setForeground(Qt.darkGreen)
            else:
                it_av.setForeground(Qt.red)
            self.catalog_table.setItem(row, 6, it_av)

            it_iss = QTableWidgetItem(str(b.issued_copies))
            it_iss.setTextAlignment(Qt.AlignCenter)
            self.catalog_table.setItem(row, 7, it_iss)

            # Price
            it_pr = QTableWidgetItem(f"${b.price:.2f}")
            it_pr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.catalog_table.setItem(row, 8, it_pr)

            # Status
            it_st = QTableWidgetItem(b.status)
            it_st.setTextAlignment(Qt.AlignCenter)
            self.catalog_table.setItem(row, 9, it_st)

            # Actions Cell
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)
            act_layout.setSpacing(4)

            # Quick Issue Button
            issue_btn = QPushButton("Issue")
            issue_btn.setEnabled(b.available_copies > 0)
            issue_btn.setStyleSheet("background-color: #059669; color: white; font-size: 11px; padding: 2px 8px; border-radius: 3px;")
            issue_btn.clicked.connect(lambda _, bk_id=b.id: self._quick_issue(bk_id))
            act_layout.addWidget(issue_btn)

            # Edit Button
            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet("background-color: #F1F5F9; color: #1E293B; font-size: 11px; padding: 2px 8px; border-radius: 3px;")
            edit_btn.clicked.connect(lambda _, bk=b: self._edit_book(bk))
            act_layout.addWidget(edit_btn)

            self.catalog_table.setCellWidget(row, 10, act_widget)

    def _add_book(self):
        dlg = BookFormDialog(self.db_session, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _edit_book(self, book: Book):
        dlg = BookFormDialog(self.db_session, book=book, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _quick_issue(self, book_id: int):
        dlg = IssueBookDialog(self.db_session, preselected_book_id=book_id, parent=self)
        if dlg.exec():
            self.refresh_data()

    # ---------------- TAB 2: CIRCULATION DESK ----------------
    def _setup_circulation_tab(self):
        layout = QVBoxLayout(self.tab_circulation)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        ctrl_box = QHBoxLayout()
        ctrl_box.addWidget(QLabel("Loan Status:"))
        self.loan_status_combo = QComboBox()
        self.loan_status_combo.addItems(["Active (Issued + Overdue)", "All Loans", "Issued", "Overdue", "Returned"])
        self.loan_status_combo.currentIndexChanged.connect(self.load_circulation_table)
        ctrl_box.addWidget(self.loan_status_combo)
        ctrl_box.addStretch()

        issue_loan_btn = QPushButton("➕ Issue Book (Check Out)")
        issue_loan_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        issue_loan_btn.clicked.connect(lambda: self._quick_issue(None))
        ctrl_box.addWidget(issue_loan_btn)

        layout.addLayout(ctrl_box)

        # Circulation Table
        self.circ_table = QTableWidget()
        headers = [
            "Loan ID", "Book Title", "Borrower Patron", "Member Type",
            "Issue Date", "Due Date", "Return Date", "Fine ($)", "Status", "Actions"
        ]
        self.circ_table.setColumnCount(len(headers))
        self.circ_table.setHorizontalHeaderLabels(headers)
        self.circ_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.circ_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.circ_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.circ_table.verticalHeader().setVisible(False)
        self.circ_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.circ_table.setAlternatingRowColors(True)

        layout.addWidget(self.circ_table)

    def load_circulation_table(self):
        sel_filter = self.loan_status_combo.currentText()
        status_param = None
        if sel_filter == "Active (Issued + Overdue)":
            status_param = "Active"
        elif sel_filter != "All Loans":
            status_param = sel_filter

        circs = LibraryRepository.get_circulations(self.db_session, status=status_param)
        self.circ_table.setRowCount(len(circs))

        for row, c in enumerate(circs):
            # Loan ID
            it_id = QTableWidgetItem(f"#{c.id:04d}")
            it_id.setTextAlignment(Qt.AlignCenter)
            self.circ_table.setItem(row, 0, it_id)

            # Book Title
            title_text = f"{c.book.title} ({c.book.accession_no})" if c.book else "Unknown Book"
            self.circ_table.setItem(row, 1, QTableWidgetItem(title_text))

            # Borrower
            borrower_name = "Patron"
            if c.member:
                if c.member.student:
                    borrower_name = f"{c.member.student.full_name} ({c.member.member_id})"
                elif c.member.teacher:
                    borrower_name = f"{c.member.teacher.full_name} ({c.member.member_id})"
                else:
                    borrower_name = c.member.member_id
            self.circ_table.setItem(row, 2, QTableWidgetItem(borrower_name))

            # Type
            m_type = c.member.member_type if c.member else "-"
            it_type = QTableWidgetItem(m_type)
            it_type.setTextAlignment(Qt.AlignCenter)
            self.circ_table.setItem(row, 3, it_type)

            # Dates
            it_iss = QTableWidgetItem(c.issue_date)
            it_iss.setTextAlignment(Qt.AlignCenter)
            self.circ_table.setItem(row, 4, it_iss)

            it_due = QTableWidgetItem(c.due_date)
            it_due.setTextAlignment(Qt.AlignCenter)
            self.circ_table.setItem(row, 5, it_due)

            it_ret = QTableWidgetItem(c.return_date or "—")
            it_ret.setTextAlignment(Qt.AlignCenter)
            self.circ_table.setItem(row, 6, it_ret)

            # Fine
            it_fine = QTableWidgetItem(f"${c.fine_amount:.2f}")
            it_fine.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if c.fine_amount > 0:
                it_fine.setForeground(Qt.red)
            self.circ_table.setItem(row, 7, it_fine)

            # Status
            it_st = QTableWidgetItem(c.status)
            it_st.setTextAlignment(Qt.AlignCenter)
            if c.status == "Overdue":
                it_st.setForeground(Qt.red)
            elif c.status == "Returned":
                it_st.setForeground(Qt.darkGreen)
            self.circ_table.setItem(row, 8, it_st)

            # Actions Cell
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)

            if c.status in ["Issued", "Overdue"]:
                ret_btn = QPushButton("Check In / Return")
                ret_btn.setStyleSheet("background-color: #2563EB; color: white; font-size: 11px; padding: 2px 8px; border-radius: 3px;")
                ret_btn.clicked.connect(lambda _, circ_obj=c: self._return_book(circ_obj))
                act_layout.addWidget(ret_btn)
            else:
                comp_lbl = QLabel("Completed")
                comp_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
                comp_lbl.setAlignment(Qt.AlignCenter)
                act_layout.addWidget(comp_lbl)

            self.circ_table.setCellWidget(row, 9, act_widget)

    def _return_book(self, circ: BookCirculation):
        dlg = ReturnBookDialog(self.db_session, circulation=circ, parent=self)
        if dlg.exec():
            self.refresh_data()

    # ---------------- TAB 3: MEMBERS REGISTER ----------------
    def _setup_members_tab(self):
        layout = QVBoxLayout(self.tab_members)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        ctrl_box = QHBoxLayout()
        ctrl_box.addWidget(QLabel("Registered Library Cardholders"))
        ctrl_box.addStretch()
        layout.addLayout(ctrl_box)

        self.members_table = QTableWidget()
        headers = ["Member ID", "Patron Name", "Member Type", "Affiliation / Class", "Max Quota", "Issued Date", "Status", "Actions"]
        self.members_table.setColumnCount(len(headers))
        self.members_table.setHorizontalHeaderLabels(headers)
        self.members_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.members_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.members_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.members_table.verticalHeader().setVisible(False)
        self.members_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.members_table.setAlternatingRowColors(True)

        layout.addWidget(self.members_table)

    def load_members_table(self):
        members = LibraryRepository.get_members(self.db_session)
        self.members_table.setRowCount(len(members))

        for row, m in enumerate(members):
            it_id = QTableWidgetItem(m.member_id)
            it_id.setTextAlignment(Qt.AlignCenter)
            self.members_table.setItem(row, 0, it_id)

            name = "Unknown"
            affil = "-"
            if m.student:
                name = m.student.full_name
                affil = f"Class {m.student.school_class.name if m.student.school_class else '-'} (Roll {m.student.roll_number})"
            elif m.teacher:
                name = m.teacher.full_name
                affil = f"{m.teacher.designation or 'Faculty'}"
            elif m.staff:
                name = m.staff.full_name
                affil = m.staff.role or "Staff"

            self.members_table.setItem(row, 1, QTableWidgetItem(name))

            it_type = QTableWidgetItem(m.member_type)
            it_type.setTextAlignment(Qt.AlignCenter)
            self.members_table.setItem(row, 2, it_type)

            self.members_table.setItem(row, 3, QTableWidgetItem(affil))

            it_q = QTableWidgetItem(f"{m.max_allowed_books} Books")
            it_q.setTextAlignment(Qt.AlignCenter)
            self.members_table.setItem(row, 4, it_q)

            it_date = QTableWidgetItem(m.card_issue_date)
            it_date.setTextAlignment(Qt.AlignCenter)
            self.members_table.setItem(row, 5, it_date)

            it_st = QTableWidgetItem(m.status)
            it_st.setTextAlignment(Qt.AlignCenter)
            self.members_table.setItem(row, 6, it_st)

            # Actions Cell
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)

            card_btn = QPushButton("Print CR80 Card (PDF)")
            card_btn.setStyleSheet("background-color: #065F46; color: white; font-size: 11px; padding: 2px 8px; border-radius: 3px;")
            card_btn.clicked.connect(lambda _, mem=m: self._print_library_card(mem))
            act_layout.addWidget(card_btn)

            self.members_table.setCellWidget(row, 7, act_widget)

    def _print_library_card(self, member: LibraryMember):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Library Card PDF",
            f"Library_Card_{member.member_id}.pdf",
            "PDF Files (*.pdf)"
        )
        if file_path:
            try:
                school = self.db_session.query(SchoolSetting).first()
                LibraryCardGenerator.generate_single_card(member, school, file_path)
                QMessageBox.information(self, "Card Generated", f"Printable CR80 Library Card saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "PDF Error", f"Failed to generate card:\n{str(e)}")

    # ---------------- TAB 4: CATEGORIES ----------------
    def _setup_categories_tab(self):
        layout = QVBoxLayout(self.tab_categories)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.categories_table = QTableWidget()
        headers = ["Code", "Category Name", "Description", "Book Titles Count"]
        self.categories_table.setColumnCount(len(headers))
        self.categories_table.setHorizontalHeaderLabels(headers)
        self.categories_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.categories_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.categories_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.categories_table.verticalHeader().setVisible(False)
        self.categories_table.setAlternatingRowColors(True)

        layout.addWidget(self.categories_table)

    def load_categories_table(self):
        categories = LibraryRepository.get_categories(self.db_session)
        self.categories_table.setRowCount(len(categories))

        # Update category filter combo in Tab 1 if needed
        curr_cat_id = self.cat_filter_combo.currentData()
        self.cat_filter_combo.blockSignals(True)
        self.cat_filter_combo.clear()
        self.cat_filter_combo.addItem("All Categories", None)
        for cat in categories:
            self.cat_filter_combo.addItem(cat.name, cat.id)
        if curr_cat_id:
            idx = self.cat_filter_combo.findData(curr_cat_id)
            if idx >= 0:
                self.cat_filter_combo.setCurrentIndex(idx)
        self.cat_filter_combo.blockSignals(False)

        for row, cat in enumerate(categories):
            it_code = QTableWidgetItem(cat.code)
            it_code.setTextAlignment(Qt.AlignCenter)
            self.categories_table.setItem(row, 0, it_code)

            self.categories_table.setItem(row, 1, QTableWidgetItem(cat.name))
            self.categories_table.setItem(row, 2, QTableWidgetItem(cat.description or "-"))

            b_count = len(cat.books) if cat.books else 0
            it_cnt = QTableWidgetItem(str(b_count))
            it_cnt.setTextAlignment(Qt.AlignCenter)
            self.categories_table.setItem(row, 3, it_cnt)

    # ---------------- REFRESH & EXPORTS ----------------
    def refresh_data(self):
        stats = LibraryRepository.get_library_stats(self.db_session)
        self.lbl_titles.setText(str(stats["total_titles"]))
        self.lbl_copies.setText(str(stats["total_inventory_copies"]))
        self.lbl_available.setText(str(stats["available_copies"]))
        self.lbl_issued.setText(str(stats["currently_issued"]))
        self.lbl_overdue.setText(str(stats["overdue_count"]))
        self.lbl_fines.setText(f"$ {stats['total_fine_collected']:.2f}")

        self.load_catalog_table()
        self.load_circulation_table()
        self.load_members_table()
        self.load_categories_table()

    def _export_catalog_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Library Catalog Excel",
            "Library_Catalog_Audit.xlsx",
            "Excel Files (*.xlsx)"
        )
        if file_path:
            try:
                LibraryService.export_catalog_excel(self.db_session, file_path)
                QMessageBox.information(self, "Export Complete", f"Book catalog successfully exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export catalog:\n{str(e)}")

    def _generate_circulation_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Circulation Audit Report",
            "Circulation_Audit_Statement.pdf",
            "PDF Files (*.pdf)"
        )
        if file_path:
            try:
                circs = LibraryRepository.get_circulations(self.db_session)
                stats = LibraryRepository.get_library_stats(self.db_session)
                school = self.db_session.query(SchoolSetting).first()
                CirculationReportPDFGenerator.generate_report(circs, stats, school, file_path)
                QMessageBox.information(self, "Report Generated", f"Circulation Audit PDF statement generated at:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Report Error", f"Failed to generate report:\n{str(e)}")
