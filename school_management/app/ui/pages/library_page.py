"""
EduManage Pro - Enterprise Library Management Workspace
7-Tab Real-Database Interface:
1. Book Catalog & Physical Copies
2. Circulation Desk (Issue, Return & Renewal)
3. Reservations Queue
4. Fines, Lost & Damaged Books
5. Members & Barcode/QR Library Cards
6. Authors, Publishers, Categories & Shelves
7. Borrowing History, Fine & Inventory Reports
"""

from datetime import date
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.library import Book, BookCirculation, BookIncident, LibraryFine, LibraryMember
from app.models.school import SchoolSetting
from app.reports.circulation_report_pdf import CirculationReportPDFGenerator
from app.reports.library_card_pdf import LibraryCardGenerator
from app.reports.library_reports_pdf import LibraryReportsPDFGenerator
from app.repositories.library_repository import LibraryRepository
from app.security.session import session as app_session
from app.services.library_service import LibraryService
from app.ui.dialogs.book_form_dialog import BookFormDialog
from app.ui.dialogs.issue_book_dialog import IssueBookDialog
from app.ui.dialogs.library_dialogs import (
    BookCopiesDialog,
    BookImportDialog,
    BookIncidentDialog,
    FineCollectionDialog,
    LibraryMemberDialog,
    RenewLoanDialog,
    ReservationDialog,
)
from app.ui.dialogs.return_book_dialog import ReturnBookDialog


class LibraryPage(QWidget):
    """Main Library Management page powered 100% by real database records."""

    def __init__(self, parent=None, db_session: Optional[Session] = None, session_manager=None):
        super().__init__(parent)
        self.session_manager = session_manager
        self.db_session = db_session if db_session is not None else SessionLocal()

        # Ensure baseline classification categories only (never seeds demo books or fake loans)
        LibraryService.ensure_default_categories(self.db_session)
        LibraryRepository.refresh_overdue_statuses(self.db_session)

        self._setup_ui()
        self.refresh_data()

    def refresh_all(self):
        """Standard lifecycle hook called on navigation."""
        LibraryRepository.refresh_overdue_statuses(self.db_session)
        self.refresh_data()

    def _actor(self) -> Optional[str]:
        if app_session.is_authenticated and app_session.current_user:
            return app_session.current_user.full_name or app_session.current_user.username
        return None

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # 1. Header & Barcode/QR Quick Scanner
        header_row = QHBoxLayout()
        title_label = QLabel("Library Management & Circulation Desk")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        header_row.addWidget(title_label)
        header_row.addStretch()

        self.quick_scan_input = QLineEdit()
        self.quick_scan_input.setFixedWidth(290)
        self.quick_scan_input.setPlaceholderText("Scan Book/Copy/Member Barcode or QR...")
        self.quick_scan_input.returnPressed.connect(self._handle_quick_scan)
        header_row.addWidget(self.quick_scan_input)

        scan_go_btn = QPushButton("Scan Lookup")
        scan_go_btn.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        scan_go_btn.clicked.connect(self._handle_quick_scan)
        header_row.addWidget(scan_go_btn)

        import_btn = QPushButton("Import Books")
        import_btn.setStyleSheet("background-color: #0F766E; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        import_btn.clicked.connect(self._open_import_wizard)
        header_row.addWidget(import_btn)

        export_excel_btn = QPushButton("Export Catalog (Excel)")
        export_excel_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        export_excel_btn.clicked.connect(self._export_catalog_excel)
        header_row.addWidget(export_excel_btn)

        main_layout.addLayout(header_row)

        # 2. KPI Metrics Bar
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(8)
        self.lbl_titles = self._create_kpi_card("Titles", "0", "#0284C7")
        self.lbl_copies = self._create_kpi_card("Total Copies", "0", "#475569")
        self.lbl_available = self._create_kpi_card("Available", "0", "#059669")
        self.lbl_issued = self._create_kpi_card("Active Loans", "0", "#D97706")
        self.lbl_overdue = self._create_kpi_card("Overdue", "0", "#DC2626")
        self.lbl_damaged_lost = self._create_kpi_card("Damaged / Lost", "0 / 0", "#B91C1C")
        self.lbl_reservations = self._create_kpi_card("Reservations", "0", "#0891B2")
        self.lbl_fines = self._create_kpi_card("Fines Paid / Due", "$0 / $0", "#7C3AED")
        main_layout.addLayout(self.kpi_layout)

        # 3. Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                font-weight: 600;
                padding: 8px 14px;
                color: #475569;
            }
            QTabBar::tab:selected {
                color: #065F46;
                border-bottom: 2px solid #065F46;
            }
        """)

        self.tab_catalog = QWidget()
        self._setup_catalog_tab()
        self.tabs.addTab(self.tab_catalog, "Book Catalog & Copies")

        self.tab_circulation = QWidget()
        self._setup_circulation_tab()
        self.tabs.addTab(self.tab_circulation, "Circulation Desk")

        self.tab_reservations = QWidget()
        self._setup_reservations_tab()
        self.tabs.addTab(self.tab_reservations, "Reservations")

        self.tab_fines_incidents = QWidget()
        self._setup_fines_incidents_tab()
        self.tabs.addTab(self.tab_fines_incidents, "Fines, Lost & Damaged")

        self.tab_members = QWidget()
        self._setup_members_tab()
        self.tabs.addTab(self.tab_members, "Members & Cards")

        self.tab_directory = QWidget()
        self._setup_directory_tab()
        self.tabs.addTab(self.tab_directory, "Authors, Publishers, Categories & Shelves")

        self.tab_reports = QWidget()
        self._setup_reports_tab()
        self.tabs.addTab(self.tab_reports, "History & Reports")

        main_layout.addWidget(self.tabs)

    def _create_kpi_card(self, title: str, default_val: str, color_hex: str) -> QLabel:
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background-color: white; border: 1px solid #E2E8F0; "
            f"border-top: 3px solid {color_hex}; border-radius: 6px; padding: 4px 8px; }}"
        )
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(6, 4, 6, 4)
        vbox.setSpacing(2)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 500;")
        v_lbl = QLabel(default_val)
        v_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color_hex};")
        vbox.addWidget(t_lbl)
        vbox.addWidget(v_lbl)
        self.kpi_layout.addWidget(frame)
        return v_lbl

    # ---------------- TAB 1: BOOK CATALOG ----------------
    def _setup_catalog_tab(self):
        layout = QVBoxLayout(self.tab_catalog)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Category:"))
        self.cat_filter_combo = QComboBox()
        self.cat_filter_combo.addItem("All Categories", None)
        self.cat_filter_combo.currentIndexChanged.connect(self.load_catalog_table)
        ctrl.addWidget(self.cat_filter_combo)

        ctrl.addWidget(QLabel("Shelf:"))
        self.shelf_filter_combo = QComboBox()
        self.shelf_filter_combo.addItem("All Shelves", None)
        self.shelf_filter_combo.currentIndexChanged.connect(self.load_catalog_table)
        ctrl.addWidget(self.shelf_filter_combo)

        self.catalog_search_input = QLineEdit()
        self.catalog_search_input.setPlaceholderText("Search Title, Author, Publisher, ISBN, Accession, Barcode...")
        self.catalog_search_input.textChanged.connect(self.load_catalog_table)
        ctrl.addWidget(self.catalog_search_input, 2)

        labels_btn = QPushButton("Print All Barcodes (PDF)")
        labels_btn.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold; padding: 6px 10px; border-radius: 4px;")
        labels_btn.clicked.connect(self._print_catalog_barcodes_pdf)
        ctrl.addWidget(labels_btn)

        export_csv_btn = QPushButton("Export CSV")
        export_csv_btn.clicked.connect(self._export_catalog_csv)
        ctrl.addWidget(export_csv_btn)

        add_book_btn = QPushButton("+ Add Book")
        add_book_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        add_book_btn.clicked.connect(self._add_book)
        ctrl.addWidget(add_book_btn)
        layout.addLayout(ctrl)

        self.catalog_table = QTableWidget()
        headers = [
            "Accession No", "Title", "Author", "Publisher", "ISBN",
            "Category", "Shelf Loc", "Total", "Avail", "Issued", "Dam/Lost", "Price", "Status", "Actions",
        ]
        self.catalog_table.setColumnCount(len(headers))
        self.catalog_table.setHorizontalHeaderLabels(headers)
        self.catalog_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for col in (0, 7, 8, 9, 10, 11, 13):
            self.catalog_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.catalog_table.verticalHeader().setVisible(False)
        self.catalog_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.catalog_table.setAlternatingRowColors(True)
        layout.addWidget(self.catalog_table)

    def load_catalog_table(self):
        cat_id = self.cat_filter_combo.currentData()
        shelf_id = self.shelf_filter_combo.currentData()
        search = self.catalog_search_input.text().strip() or None
        books = LibraryRepository.get_books(
            self.db_session, category_id=cat_id, shelf_id=shelf_id, search_query=search
        )
        self.catalog_table.setRowCount(len(books))

        for row, b in enumerate(books):
            it_acc = QTableWidgetItem(b.accession_no)
            it_acc.setTextAlignment(Qt.AlignCenter)
            self.catalog_table.setItem(row, 0, it_acc)
            self.catalog_table.setItem(row, 1, QTableWidgetItem(b.title))
            self.catalog_table.setItem(row, 2, QTableWidgetItem(b.author))
            self.catalog_table.setItem(row, 3, QTableWidgetItem(b.publisher or "-"))
            self.catalog_table.setItem(row, 4, QTableWidgetItem(b.isbn or "-"))
            self.catalog_table.setItem(row, 5, QTableWidgetItem(b.category.name if b.category else "Uncategorized"))
            loc = f"{b.rack_number or '-'} / {b.shelf_number or '-'}"
            self.catalog_table.setItem(row, 6, QTableWidgetItem(loc))

            for c_idx, val in ((7, b.total_copies), (8, b.available_copies), (9, b.issued_copies)):
                it = QTableWidgetItem(str(val or 0))
                it.setTextAlignment(Qt.AlignCenter)
                if c_idx == 8:
                    it.setForeground(Qt.darkGreen if (val or 0) > 0 else Qt.red)
                self.catalog_table.setItem(row, c_idx, it)

            dl_item = QTableWidgetItem(f"{b.damaged_copies or 0}/{b.lost_copies or 0}")
            dl_item.setTextAlignment(Qt.AlignCenter)
            self.catalog_table.setItem(row, 10, dl_item)

            pr_item = QTableWidgetItem(f"${float(b.price or 0.0):.2f}")
            pr_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.catalog_table.setItem(row, 11, pr_item)

            st_item = QTableWidgetItem(b.status)
            st_item.setTextAlignment(Qt.AlignCenter)
            self.catalog_table.setItem(row, 12, st_item)

            act_w = QWidget()
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(2, 2, 2, 2)
            act_l.setSpacing(3)

            issue_btn = QPushButton("Issue")
            issue_btn.setEnabled((b.available_copies or 0) > 0)
            issue_btn.setStyleSheet("background-color: #059669; color: white; font-size: 11px; padding: 2px 6px;")
            issue_btn.clicked.connect(lambda _, bk_id=b.id: self._quick_issue(bk_id))
            act_l.addWidget(issue_btn)

            copies_btn = QPushButton("Copies")
            copies_btn.setStyleSheet("background-color: #1E3A8A; color: white; font-size: 11px; padding: 2px 6px;")
            copies_btn.clicked.connect(lambda _, bk=b: self._manage_copies(bk))
            act_l.addWidget(copies_btn)

            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet("background-color: #F1F5F9; color: #1E293B; font-size: 11px; padding: 2px 6px;")
            edit_btn.clicked.connect(lambda _, bk=b: self._edit_book(bk))
            act_l.addWidget(edit_btn)
            self.catalog_table.setCellWidget(row, 13, act_w)

    # ---------------- TAB 2: CIRCULATION DESK ----------------
    def _setup_circulation_tab(self):
        layout = QVBoxLayout(self.tab_circulation)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Loan Filter:"))
        self.loan_status_combo = QComboBox()
        self.loan_status_combo.addItems(["Active (Issued + Renewed + Overdue)", "All Loans", "Issued", "Renewed", "Overdue", "Returned", "Lost", "Damaged"])
        self.loan_status_combo.currentIndexChanged.connect(self.load_circulation_table)
        ctrl.addWidget(self.loan_status_combo)
        ctrl.addStretch()

        issue_btn = QPushButton("+ Issue Book (Check Out)")
        issue_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        issue_btn.clicked.connect(lambda: self._quick_issue(None))
        ctrl.addWidget(issue_btn)
        layout.addLayout(ctrl)

        self.circ_table = QTableWidget()
        headers = [
            "Loan #", "Book & Copy", "Borrower Patron", "Type",
            "Issue Date", "Due Date", "Return Date", "Renewals", "Fine ($)", "Status", "Actions",
        ]
        self.circ_table.setColumnCount(len(headers))
        self.circ_table.setHorizontalHeaderLabels(headers)
        self.circ_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for col in (0, 7, 8, 10):
            self.circ_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.circ_table.verticalHeader().setVisible(False)
        self.circ_table.setAlternatingRowColors(True)
        layout.addWidget(self.circ_table)

    def load_circulation_table(self):
        sel = self.loan_status_combo.currentText()
        status_param = None
        if sel.startswith("Active"):
            status_param = "Active"
        elif sel != "All Loans":
            status_param = sel

        circs = LibraryRepository.get_circulations(self.db_session, status=status_param)
        self.circ_table.setRowCount(len(circs))
        for row, c in enumerate(circs):
            it_id = QTableWidgetItem(f"#{c.id:04d}")
            it_id.setTextAlignment(Qt.AlignCenter)
            self.circ_table.setItem(row, 0, it_id)

            cp_lbl = f" [{c.copy.copy_code}]" if c.copy else ""
            title_txt = f"{c.book.title} ({c.book.accession_no}){cp_lbl}" if c.book else "Unknown"
            self.circ_table.setItem(row, 1, QTableWidgetItem(title_txt))

            b_name = f"{c.member.display_name} ({c.member.member_id})" if c.member else "Patron"
            self.circ_table.setItem(row, 2, QTableWidgetItem(b_name))
            self.circ_table.setItem(row, 3, QTableWidgetItem(c.member.member_type if c.member else "-"))
            self.circ_table.setItem(row, 4, QTableWidgetItem(c.issue_date))
            self.circ_table.setItem(row, 5, QTableWidgetItem(c.due_date))
            self.circ_table.setItem(row, 6, QTableWidgetItem(c.return_date or "—"))

            ren_it = QTableWidgetItem(f"{c.renewal_count or 0}/{c.max_renewals or 2}")
            ren_it.setTextAlignment(Qt.AlignCenter)
            self.circ_table.setItem(row, 7, ren_it)

            tot_f = float((c.fine_amount or 0.0) + (c.damage_or_lost_fee or 0.0))
            f_it = QTableWidgetItem(f"${tot_f:.2f}")
            f_it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if tot_f > 0:
                f_it.setForeground(Qt.red)
            self.circ_table.setItem(row, 8, f_it)

            st_it = QTableWidgetItem(c.status)
            st_it.setTextAlignment(Qt.AlignCenter)
            if c.status in ("Overdue", "Lost", "Damaged"):
                st_it.setForeground(Qt.red)
            elif c.status == "Returned":
                st_it.setForeground(Qt.darkGreen)
            self.circ_table.setItem(row, 9, st_it)

            act_w = QWidget()
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(2, 2, 2, 2)
            act_l.setSpacing(3)
            if c.status in ("Issued", "Overdue", "Renewed"):
                ret_btn = QPushButton("Return")
                ret_btn.setStyleSheet("background-color: #2563EB; color: white; font-size: 11px; padding: 2px 6px;")
                ret_btn.clicked.connect(lambda _, co=c: self._return_book(co))
                act_l.addWidget(ret_btn)

                ren_btn = QPushButton("Renew")
                ren_btn.setStyleSheet("background-color: #0284C7; color: white; font-size: 11px; padding: 2px 6px;")
                ren_btn.clicked.connect(lambda _, co=c: self._renew_loan(co))
                act_l.addWidget(ren_btn)
            else:
                lbl = QLabel("Closed")
                lbl.setStyleSheet("color: #64748B; font-size: 11px;")
                act_l.addWidget(lbl)
            self.circ_table.setCellWidget(row, 10, act_w)

    # ---------------- TAB 3: RESERVATIONS ----------------
    def _setup_reservations_tab(self):
        layout = QVBoxLayout(self.tab_reservations)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Status:"))
        self.res_filter_combo = QComboBox()
        self.res_filter_combo.addItems(["Active", "All", "Pending", "Ready", "Fulfilled", "Cancelled"])
        self.res_filter_combo.currentIndexChanged.connect(self.load_reservations_table)
        ctrl.addWidget(self.res_filter_combo)
        ctrl.addStretch()

        new_res_btn = QPushButton("+ New Reservation")
        new_res_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        new_res_btn.clicked.connect(self._create_reservation)
        ctrl.addWidget(new_res_btn)
        layout.addLayout(ctrl)

        self.res_table = QTableWidget()
        headers = ["Code", "Book Title", "Copy", "Member", "Reserved Date", "Hold Expiry", "Priority", "Status", "Actions"]
        self.res_table.setColumnCount(len(headers))
        self.res_table.setHorizontalHeaderLabels(headers)
        self.res_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.res_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.res_table.verticalHeader().setVisible(False)
        self.res_table.setAlternatingRowColors(True)
        layout.addWidget(self.res_table)

    def load_reservations_table(self):
        st = self.res_filter_combo.currentText()
        rows = LibraryRepository.get_reservations(self.db_session, status=None if st == "All" else st)
        self.res_table.setRowCount(len(rows))
        for r, res in enumerate(rows):
            self.res_table.setItem(r, 0, QTableWidgetItem(res.reservation_code))
            self.res_table.setItem(r, 1, QTableWidgetItem(res.book.title if res.book else "-"))
            self.res_table.setItem(r, 2, QTableWidgetItem(res.copy.copy_code if res.copy else "Queue"))
            self.res_table.setItem(r, 3, QTableWidgetItem(f"{res.member.display_name} ({res.member.member_id})" if res.member else "-"))
            self.res_table.setItem(r, 4, QTableWidgetItem(res.reserved_date))
            self.res_table.setItem(r, 5, QTableWidgetItem(res.expiry_date or "-"))
            self.res_table.setItem(r, 6, QTableWidgetItem(str(res.priority_order)))
            self.res_table.setItem(r, 7, QTableWidgetItem(res.status))

            act_w = QWidget()
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(2, 2, 2, 2)
            if res.status in ("Pending", "Ready"):
                iss_btn = QPushButton("Issue")
                iss_btn.setStyleSheet("background-color: #059669; color: white; font-size: 11px; padding: 2px 6px;")
                iss_btn.clicked.connect(
                    lambda _, b_id=res.book_id, m_id=res.member_id, c_id=res.copy_id: self._issue_from_reservation(b_id, m_id, c_id)
                )
                act_l.addWidget(iss_btn)

                can_btn = QPushButton("Cancel")
                can_btn.setStyleSheet("background-color: #DC2626; color: white; font-size: 11px; padding: 2px 6px;")
                can_btn.clicked.connect(lambda _, rid=res.id: self._cancel_reservation(rid))
                act_l.addWidget(can_btn)
            self.res_table.setCellWidget(r, 8, act_w)

    # ---------------- TAB 4: FINES, LOST & DAMAGED BOOKS ----------------
    def _setup_fines_incidents_tab(self):
        layout = QVBoxLayout(self.tab_fines_incidents)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        sub_tabs = QTabWidget()

        # Sub-tab A: Fines Ledger
        f_w = QWidget()
        f_l = QVBoxLayout(f_w)
        f_ctrl = QHBoxLayout()
        f_ctrl.addWidget(QLabel("Fine Status:"))
        self.fine_filter_combo = QComboBox()
        self.fine_filter_combo.addItems(["All", "Outstanding", "Unpaid", "Partial", "Paid", "Waived"])
        self.fine_filter_combo.currentIndexChanged.connect(self.load_fines_table)
        f_ctrl.addWidget(self.fine_filter_combo)
        f_ctrl.addStretch()
        f_l.addLayout(f_ctrl)

        self.fines_table = QTableWidget()
        f_headers = ["Fine Code", "Date", "Member", "Book", "Type", "Assessed", "Paid", "Waived", "Balance", "Receipt #", "Status", "Actions"]
        self.fines_table.setColumnCount(len(f_headers))
        self.fines_table.setHorizontalHeaderLabels(f_headers)
        self.fines_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.fines_table.horizontalHeader().setSectionResizeMode(11, QHeaderView.ResizeToContents)
        self.fines_table.verticalHeader().setVisible(False)
        f_l.addWidget(self.fines_table)
        sub_tabs.addTab(f_w, "Fines Ledger")

        # Sub-tab B: Lost & Damaged Incidents
        i_w = QWidget()
        i_l = QVBoxLayout(i_w)
        i_ctrl = QHBoxLayout()
        i_ctrl.addWidget(QLabel("Incident Type:"))
        self.inc_filter_combo = QComboBox()
        self.inc_filter_combo.addItems(["All", "Lost", "Damaged"])
        self.inc_filter_combo.currentIndexChanged.connect(self.load_incidents_table)
        i_ctrl.addWidget(self.inc_filter_combo)
        i_ctrl.addStretch()
        rep_inc_btn = QPushButton("+ Report Lost / Damaged Book")
        rep_inc_btn.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        rep_inc_btn.clicked.connect(self._report_incident)
        i_ctrl.addWidget(rep_inc_btn)
        i_l.addLayout(i_ctrl)

        self.incidents_table = QTableWidget()
        i_headers = ["Incident #", "Type", "Severity", "Book", "Copy", "Member", "Date", "Rep. Cost", "Fine", "Resolution", "Actions"]
        self.incidents_table.setColumnCount(len(i_headers))
        self.incidents_table.setHorizontalHeaderLabels(i_headers)
        self.incidents_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.incidents_table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeToContents)
        self.incidents_table.verticalHeader().setVisible(False)
        i_l.addWidget(self.incidents_table)
        sub_tabs.addTab(i_w, "Lost & Damaged Books")

        layout.addWidget(sub_tabs)

    def load_fines_table(self):
        st = self.fine_filter_combo.currentText()
        fines = LibraryRepository.get_fines(self.db_session, status=None if st == "All" else st)
        self.fines_table.setRowCount(len(fines))
        for r, f in enumerate(fines):
            self.fines_table.setItem(r, 0, QTableWidgetItem(f.fine_code))
            self.fines_table.setItem(r, 1, QTableWidgetItem(f.assessed_date))
            self.fines_table.setItem(r, 2, QTableWidgetItem(f"{f.member.display_name} ({f.member.member_id})" if f.member else "-"))
            self.fines_table.setItem(r, 3, QTableWidgetItem(f.book.title if f.book else "-"))
            self.fines_table.setItem(r, 4, QTableWidgetItem(f.fine_type))
            self.fines_table.setItem(r, 5, QTableWidgetItem(f"${float(f.amount or 0.0):.2f}"))
            self.fines_table.setItem(r, 6, QTableWidgetItem(f"${float(f.paid_amount or 0.0):.2f}"))
            self.fines_table.setItem(r, 7, QTableWidgetItem(f"${float(f.waived_amount or 0.0):.2f}"))
            self.fines_table.setItem(r, 8, QTableWidgetItem(f"${f.balance_due:.2f}"))
            self.fines_table.setItem(r, 9, QTableWidgetItem(f.receipt_no or "-"))
            self.fines_table.setItem(r, 10, QTableWidgetItem(f.status))

            act_w = QWidget()
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(2, 2, 2, 2)
            if f.status in ("Unpaid", "Partial"):
                pay_btn = QPushButton("Collect")
                pay_btn.setStyleSheet("background-color: #059669; color: white; font-size: 11px; padding: 2px 6px;")
                pay_btn.clicked.connect(lambda _, fn=f: self._collect_fine(fn, False))
                act_l.addWidget(pay_btn)

                waive_btn = QPushButton("Waive")
                waive_btn.setStyleSheet("background-color: #D97706; color: white; font-size: 11px; padding: 2px 6px;")
                waive_btn.clicked.connect(lambda _, fn=f: self._collect_fine(fn, True))
                act_l.addWidget(waive_btn)
            self.fines_table.setCellWidget(r, 11, act_w)

    def load_incidents_table(self):
        t_filter = self.inc_filter_combo.currentText()
        rows = LibraryRepository.get_incidents(self.db_session, incident_type=None if t_filter == "All" else t_filter)
        self.incidents_table.setRowCount(len(rows))
        for r, inc in enumerate(rows):
            self.incidents_table.setItem(r, 0, QTableWidgetItem(inc.incident_code))
            self.incidents_table.setItem(r, 1, QTableWidgetItem(inc.incident_type))
            self.incidents_table.setItem(r, 2, QTableWidgetItem(inc.severity))
            self.incidents_table.setItem(r, 3, QTableWidgetItem(inc.book.title if inc.book else "-"))
            self.incidents_table.setItem(r, 4, QTableWidgetItem(inc.copy.copy_code if inc.copy else "-"))
            self.incidents_table.setItem(r, 5, QTableWidgetItem(inc.member.display_name if inc.member else "Internal Audit"))
            self.incidents_table.setItem(r, 6, QTableWidgetItem(inc.incident_date))
            self.incidents_table.setItem(r, 7, QTableWidgetItem(f"${float(inc.replacement_cost or 0.0):.2f}"))
            self.incidents_table.setItem(r, 8, QTableWidgetItem(f"${float(inc.fine_assessed or 0.0):.2f}"))
            self.incidents_table.setItem(r, 9, QTableWidgetItem(inc.resolution_status))

            act_w = QWidget()
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(2, 2, 2, 2)
            if inc.resolution_status in ("Reported", "Billed"):
                rep_btn = QPushButton("Replace/Repair")
                rep_btn.setStyleSheet("background-color: #059669; color: white; font-size: 11px; padding: 2px 6px;")
                rep_btn.clicked.connect(lambda _, iid=inc.id, itype=inc.incident_type: self._resolve_incident(iid, "Repaired" if itype == "Damaged" else "Replaced"))
                act_l.addWidget(rep_btn)

                wo_btn = QPushButton("Write Off")
                wo_btn.setStyleSheet("background-color: #64748B; color: white; font-size: 11px; padding: 2px 6px;")
                wo_btn.clicked.connect(lambda _, iid=inc.id: self._resolve_incident(iid, "Written Off"))
                act_l.addWidget(wo_btn)
            self.incidents_table.setCellWidget(r, 10, act_w)

    # ---------------- TAB 5: MEMBERS & LIBRARY CARDS ----------------
    def _setup_members_tab(self):
        layout = QVBoxLayout(self.tab_members)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        ctrl = QHBoxLayout()
        self.member_search_input = QLineEdit()
        self.member_search_input.setPlaceholderText("Search Member ID, Name, Barcode...")
        self.member_search_input.textChanged.connect(self.load_members_table)
        ctrl.addWidget(self.member_search_input)

        sync_btn = QPushButton("Sync Real Students / Teachers / Staff")
        sync_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        sync_btn.clicked.connect(self._sync_members)
        ctrl.addWidget(sync_btn)

        batch_card_btn = QPushButton("Batch Print Cards (PDF)")
        batch_card_btn.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        batch_card_btn.clicked.connect(self._batch_print_cards)
        ctrl.addWidget(batch_card_btn)

        add_m_btn = QPushButton("+ Enroll Member")
        add_m_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        add_m_btn.clicked.connect(self._add_member)
        ctrl.addWidget(add_m_btn)
        layout.addLayout(ctrl)

        self.members_table = QTableWidget()
        headers = ["Member ID", "Barcode", "Patron Name", "Type", "Affiliation / Class", "Quota / Days", "Expiry", "Status", "Actions"]
        self.members_table.setColumnCount(len(headers))
        self.members_table.setHorizontalHeaderLabels(headers)
        self.members_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.members_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.members_table.verticalHeader().setVisible(False)
        self.members_table.setAlternatingRowColors(True)
        layout.addWidget(self.members_table)

    def load_members_table(self):
        q = self.member_search_input.text().strip() or None
        members = LibraryRepository.get_members(self.db_session, search_query=q)
        self.members_table.setRowCount(len(members))
        for row, m in enumerate(members):
            self.members_table.setItem(row, 0, QTableWidgetItem(m.member_id))
            self.members_table.setItem(row, 1, QTableWidgetItem(m.barcode or "-"))
            self.members_table.setItem(row, 2, QTableWidgetItem(m.display_name))
            self.members_table.setItem(row, 3, QTableWidgetItem(m.member_type))
            self.members_table.setItem(row, 4, QTableWidgetItem(m.affiliation_label))
            self.members_table.setItem(row, 5, QTableWidgetItem(f"{m.max_allowed_books} books / {getattr(m, 'max_loan_days', 14)}d"))
            self.members_table.setItem(row, 6, QTableWidgetItem(getattr(m, "card_expiry_date", None) or "-"))
            self.members_table.setItem(row, 7, QTableWidgetItem(m.status))

            act_w = QWidget()
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(2, 2, 2, 2)
            act_l.setSpacing(3)

            card_btn = QPushButton("CR80 Card")
            card_btn.setStyleSheet("background-color: #065F46; color: white; font-size: 11px; padding: 2px 6px;")
            card_btn.clicked.connect(lambda _, mem=m: self._print_library_card(mem))
            act_l.addWidget(card_btn)

            edit_btn = QPushButton("Edit / QR")
            edit_btn.setStyleSheet("background-color: #F1F5F9; color: #1E293B; font-size: 11px; padding: 2px 6px;")
            edit_btn.clicked.connect(lambda _, mem=m: self._edit_member(mem))
            act_l.addWidget(edit_btn)
            self.members_table.setCellWidget(row, 8, act_w)

    # ---------------- TAB 6: AUTHORS, PUBLISHERS, CATEGORIES & SHELVES ----------------
    def _setup_directory_tab(self):
        layout = QVBoxLayout(self.tab_directory)
        layout.setContentsMargins(10, 10, 10, 10)
        sub = QTabWidget()

        # Authors
        a_w = QWidget()
        a_l = QVBoxLayout(a_w)
        a_ctrl = QHBoxLayout()
        a_ctrl.addStretch()
        a_add = QPushButton("+ Add Author")
        a_add.clicked.connect(self._add_author)
        a_ctrl.addWidget(a_add)
        a_l.addLayout(a_ctrl)
        self.authors_table = QTableWidget(0, 4)
        self.authors_table.setHorizontalHeaderLabels(["Code", "Author Name", "Country", "Books Count"])
        self.authors_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.authors_table.verticalHeader().setVisible(False)
        a_l.addWidget(self.authors_table)
        sub.addTab(a_w, "Authors")

        # Publishers
        p_w = QWidget()
        p_l = QVBoxLayout(p_w)
        p_ctrl = QHBoxLayout()
        p_ctrl.addStretch()
        p_add = QPushButton("+ Add Publisher")
        p_add.clicked.connect(self._add_publisher)
        p_ctrl.addWidget(p_add)
        p_l.addLayout(p_ctrl)
        self.publishers_table = QTableWidget(0, 5)
        self.publishers_table.setHorizontalHeaderLabels(["Code", "Publisher Name", "Country", "Phone", "Books Count"])
        self.publishers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.publishers_table.verticalHeader().setVisible(False)
        p_l.addWidget(self.publishers_table)
        sub.addTab(p_w, "Publishers")

        # Categories
        c_w = QWidget()
        c_l = QVBoxLayout(c_w)
        c_ctrl = QHBoxLayout()
        c_ctrl.addStretch()
        c_add = QPushButton("+ Add Category")
        c_add.clicked.connect(self._add_category)
        c_ctrl.addWidget(c_add)
        c_l.addLayout(c_ctrl)
        self.categories_table = QTableWidget(0, 5)
        self.categories_table.setHorizontalHeaderLabels(["Code", "Category Name", "DDC", "Default Days", "Titles Count"])
        self.categories_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.categories_table.verticalHeader().setVisible(False)
        c_l.addWidget(self.categories_table)
        sub.addTab(c_w, "Categories")

        # Shelves
        s_w = QWidget()
        s_l = QVBoxLayout(s_w)
        s_ctrl = QHBoxLayout()
        s_ctrl.addStretch()
        s_add = QPushButton("+ Add Shelf")
        s_add.clicked.connect(self._add_shelf)
        s_ctrl.addWidget(s_add)
        s_l.addLayout(s_ctrl)
        self.shelves_table = QTableWidget(0, 6)
        self.shelves_table.setHorizontalHeaderLabels(["Shelf Code", "Rack", "Shelf", "Floor / Zone", "Capacity", "Titles Stored"])
        self.shelves_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.shelves_table.verticalHeader().setVisible(False)
        s_l.addWidget(self.shelves_table)
        sub.addTab(s_w, "Shelves & Racks")

        layout.addWidget(sub)

    def load_directory_tables(self):
        authors = LibraryRepository.get_authors(self.db_session)
        self.authors_table.setRowCount(len(authors))
        for r, a in enumerate(authors):
            self.authors_table.setItem(r, 0, QTableWidgetItem(a.code))
            self.authors_table.setItem(r, 1, QTableWidgetItem(a.name))
            self.authors_table.setItem(r, 2, QTableWidgetItem(a.country or "-"))
            self.authors_table.setItem(r, 3, QTableWidgetItem(str(len(a.books or []))))

        pubs = LibraryRepository.get_publishers(self.db_session)
        self.publishers_table.setRowCount(len(pubs))
        for r, p in enumerate(pubs):
            self.publishers_table.setItem(r, 0, QTableWidgetItem(p.code))
            self.publishers_table.setItem(r, 1, QTableWidgetItem(p.name))
            self.publishers_table.setItem(r, 2, QTableWidgetItem(p.country or "-"))
            self.publishers_table.setItem(r, 3, QTableWidgetItem(p.phone or "-"))
            self.publishers_table.setItem(r, 4, QTableWidgetItem(str(len(p.books or []))))

        categories = LibraryRepository.get_categories(self.db_session)
        self.categories_table.setRowCount(len(categories))
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

        for r, cat in enumerate(categories):
            self.categories_table.setItem(r, 0, QTableWidgetItem(cat.code))
            self.categories_table.setItem(r, 1, QTableWidgetItem(cat.name))
            self.categories_table.setItem(r, 2, QTableWidgetItem(getattr(cat, "ddc_code", None) or "-"))
            self.categories_table.setItem(r, 3, QTableWidgetItem(str(getattr(cat, "default_loan_days", 14) or 14)))
            self.categories_table.setItem(r, 4, QTableWidgetItem(str(len(cat.books or []))))

        shelves = LibraryRepository.get_shelves(self.db_session)
        self.shelves_table.setRowCount(len(shelves))
        curr_sh_id = self.shelf_filter_combo.currentData()
        self.shelf_filter_combo.blockSignals(True)
        self.shelf_filter_combo.clear()
        self.shelf_filter_combo.addItem("All Shelves", None)
        for sh in shelves:
            self.shelf_filter_combo.addItem(f"{sh.shelf_code} ({sh.rack_number}/{sh.shelf_number})", sh.id)
        if curr_sh_id:
            s_idx = self.shelf_filter_combo.findData(curr_sh_id)
            if s_idx >= 0:
                self.shelf_filter_combo.setCurrentIndex(s_idx)
        self.shelf_filter_combo.blockSignals(False)

        for r, sh in enumerate(shelves):
            self.shelves_table.setItem(r, 0, QTableWidgetItem(sh.shelf_code))
            self.shelves_table.setItem(r, 1, QTableWidgetItem(sh.rack_number))
            self.shelves_table.setItem(r, 2, QTableWidgetItem(sh.shelf_number))
            fz = f"{sh.floor or '-'} / {sh.section_zone or '-'}"
            self.shelves_table.setItem(r, 3, QTableWidgetItem(fz))
            self.shelves_table.setItem(r, 4, QTableWidgetItem(str(sh.capacity)))
            self.shelves_table.setItem(r, 5, QTableWidgetItem(str(len(sh.books or []))))

    # ---------------- TAB 7: BORROWING HISTORY & ANALYTICAL REPORTS ----------------
    def _setup_reports_tab(self):
        layout = QVBoxLayout(self.tab_reports)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Member History:"))
        self.hist_member_combo = QComboBox()
        self.hist_member_combo.addItem("All Members", None)
        self.hist_member_combo.currentIndexChanged.connect(self.load_history_table)
        ctrl.addWidget(self.hist_member_combo)

        bh_pdf = QPushButton("Borrowing History (PDF)")
        bh_pdf.clicked.connect(self._export_borrowing_history_pdf)
        ctrl.addWidget(bh_pdf)

        bh_xl = QPushButton("Borrowing History (Excel)")
        bh_xl.clicked.connect(self._export_borrowing_history_excel)
        ctrl.addWidget(bh_xl)

        fine_pdf = QPushButton("Fine Report (PDF)")
        fine_pdf.clicked.connect(self._export_fine_report_pdf)
        ctrl.addWidget(fine_pdf)

        fine_xl = QPushButton("Fine Report (Excel)")
        fine_xl.clicked.connect(self._export_fine_report_excel)
        ctrl.addWidget(fine_xl)

        inv_pdf = QPushButton("Inventory Report (PDF)")
        inv_pdf.clicked.connect(self._export_inventory_report_pdf)
        ctrl.addWidget(inv_pdf)

        circ_pdf = QPushButton("Circulation Audit (PDF)")
        circ_pdf.clicked.connect(self._generate_circulation_pdf)
        ctrl.addWidget(circ_pdf)
        layout.addLayout(ctrl)

        self.history_table = QTableWidget(0, 9)
        self.history_table.setHorizontalHeaderLabels([
            "Loan #", "Accession / Copy", "Book Title", "Member", "Issue Date", "Due Date", "Return Date", "Total Fine", "Status",
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)

    def load_history_table(self):
        m_id = self.hist_member_combo.currentData()
        circs = LibraryRepository.get_circulations(self.db_session, member_id=m_id)
        self.history_table.setRowCount(len(circs))
        for r, c in enumerate(circs):
            self.history_table.setItem(r, 0, QTableWidgetItem(f"#{c.id:04d}"))
            cp = c.copy.copy_code if c.copy else (c.book.accession_no if c.book else "-")
            self.history_table.setItem(r, 1, QTableWidgetItem(cp))
            self.history_table.setItem(r, 2, QTableWidgetItem(c.book.title if c.book else "-"))
            self.history_table.setItem(r, 3, QTableWidgetItem(f"{c.member.display_name} ({c.member.member_id})" if c.member else "-"))
            self.history_table.setItem(r, 4, QTableWidgetItem(c.issue_date))
            self.history_table.setItem(r, 5, QTableWidgetItem(c.due_date))
            self.history_table.setItem(r, 6, QTableWidgetItem(c.return_date or "—"))
            tot_f = float((c.fine_amount or 0.0) + (c.damage_or_lost_fee or 0.0))
            self.history_table.setItem(r, 7, QTableWidgetItem(f"${tot_f:.2f}"))
            self.history_table.setItem(r, 8, QTableWidgetItem(c.status))

    def _reload_history_member_combo(self):
        cur = self.hist_member_combo.currentData()
        self.hist_member_combo.blockSignals(True)
        self.hist_member_combo.clear()
        self.hist_member_combo.addItem("All Members", None)
        for m in LibraryRepository.get_members(self.db_session):
            self.hist_member_combo.addItem(f"{m.member_id} — {m.display_name}", m.id)
        if cur:
            idx = self.hist_member_combo.findData(cur)
            if idx >= 0:
                self.hist_member_combo.setCurrentIndex(idx)
        self.hist_member_combo.blockSignals(False)

    # ---------------- REFRESH & ACTION HANDLERS ----------------
    def refresh_data(self):
        stats = LibraryRepository.get_library_stats(self.db_session)
        self.lbl_titles.setText(str(stats["total_titles"]))
        self.lbl_copies.setText(str(stats["total_inventory_copies"]))
        self.lbl_available.setText(str(stats["available_copies"]))
        self.lbl_issued.setText(str(stats["currently_issued"]))
        self.lbl_overdue.setText(str(stats["overdue_count"]))
        self.lbl_damaged_lost.setText(f"{stats['damaged_copies']} / {stats['lost_copies']}")
        self.lbl_reservations.setText(str(stats["active_reservations"]))
        self.lbl_fines.setText(f"${stats['total_fine_collected']:.0f} / ${stats['unpaid_fines_total']:.0f}")

        self.load_directory_tables()
        self.load_catalog_table()
        self.load_circulation_table()
        self.load_reservations_table()
        self.load_fines_table()
        self.load_incidents_table()
        self.load_members_table()
        self._reload_history_member_combo()
        self.load_history_table()

    def _handle_quick_scan(self):
        raw = self.quick_scan_input.text().strip()
        if not raw:
            return
        hit = LibraryRepository.lookup_by_barcode_or_qr(self.db_session, raw)
        if not hit:
            QMessageBox.information(self, "Scan Not Found", f"No catalog book, physical copy, or library member matched:\n{raw}")
            return

        if hit["type"] == "copy":
            cp = hit["copy"]
            bk = hit["book"]
            if cp.status in ("Available", "Reserved"):
                dlg = IssueBookDialog(self.db_session, preselected_book_id=bk.id, preselected_copy_id=cp.id, parent=self)
                if dlg.exec():
                    self.refresh_data()
            elif cp.status == "Issued":
                circ = (
                    self.db_session.query(BookCirculation)
                    .filter(BookCirculation.copy_id == cp.id, BookCirculation.status.in_(["Issued", "Overdue", "Renewed"]))
                    .first()
                )
                if circ:
                    self._return_book(circ)
            else:
                self._manage_copies(bk)
        elif hit["type"] == "book":
            bk = hit["book"]
            self.catalog_search_input.setText(bk.accession_no)
            self.tabs.setCurrentIndex(0)
        elif hit["type"] == "member":
            self._edit_member(hit["member"])
        self.quick_scan_input.clear()

    def _add_book(self):
        if BookFormDialog(self.db_session, parent=self).exec():
            self.refresh_data()

    def _edit_book(self, book: Book):
        if BookFormDialog(self.db_session, book=book, parent=self).exec():
            self.refresh_data()

    def _manage_copies(self, book: Book):
        BookCopiesDialog(self.db_session, book=book, parent=self).exec()
        self.refresh_data()

    def _quick_issue(self, book_id: Optional[int]):
        if IssueBookDialog(self.db_session, preselected_book_id=book_id, parent=self).exec():
            self.refresh_data()

    def _return_book(self, circ: BookCirculation):
        if ReturnBookDialog(self.db_session, circulation=circ, parent=self).exec():
            self.refresh_data()

    def _renew_loan(self, circ: BookCirculation):
        if RenewLoanDialog(self.db_session, circ=circ, parent=self).exec():
            self.refresh_data()

    def _create_reservation(self):
        if ReservationDialog(self.db_session, parent=self).exec():
            self.refresh_data()

    def _issue_from_reservation(self, book_id: int, member_id: int, copy_id: Optional[int]):
        dlg = IssueBookDialog(
            self.db_session,
            preselected_book_id=book_id,
            preselected_member_id=member_id,
            preselected_copy_id=copy_id,
            parent=self,
        )
        if dlg.exec():
            self.refresh_data()

    def _cancel_reservation(self, res_id: int):
        ok, err = LibraryRepository.cancel_reservation(self.db_session, res_id)
        if err:
            QMessageBox.warning(self, "Error", err)
        self.refresh_data()

    def _collect_fine(self, fine: LibraryFine, waive_mode: bool):
        if FineCollectionDialog(self.db_session, fine=fine, waive_mode=waive_mode, parent=self).exec():
            self.refresh_data()

    def _report_incident(self):
        if BookIncidentDialog(self.db_session, parent=self).exec():
            self.refresh_data()

    def _resolve_incident(self, inc_id: int, new_status: str):
        _, err = LibraryRepository.resolve_book_incident(self.db_session, inc_id, new_status, resolved_by=self._actor())
        if err:
            QMessageBox.warning(self, "Error", err)
        self.refresh_data()

    def _add_member(self):
        if LibraryMemberDialog(self.db_session, parent=self).exec():
            self.refresh_data()

    def _edit_member(self, member: LibraryMember):
        if LibraryMemberDialog(self.db_session, member=member, parent=self).exec():
            self.refresh_data()

    def _sync_members(self):
        res = LibraryRepository.sync_members_from_school(self.db_session)
        QMessageBox.information(
            self,
            "Members Synced",
            f"Enrolled from real school records:\n• Students: {res['students']}\n• Teachers: {res['teachers']}\n• Staff: {res['staff']}",
        )
        self.refresh_data()

    def _batch_print_cards(self):
        members = LibraryRepository.get_members(self.db_session, status="Active")
        if not members:
            QMessageBox.information(self, "No Active Members", "No active library members found to print.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Batch Library Cards", "Library_Cards_Batch.pdf", "PDF Files (*.pdf)")
        if path:
            school = self.db_session.query(SchoolSetting).first()
            LibraryCardGenerator.generate_bulk_cards_pdf(members, school, path)
            QMessageBox.information(self, "Batch Cards Generated", f"CR80 Card Sheet saved to:\n{path}")

    def _print_library_card(self, member: LibraryMember):
        path, _ = QFileDialog.getSaveFileName(self, "Save Library Card PDF", f"Library_Card_{member.member_id}.pdf", "PDF Files (*.pdf)")
        if path:
            school = self.db_session.query(SchoolSetting).first()
            LibraryCardGenerator.generate_single_card(member, school, path)
            QMessageBox.information(self, "Card Generated", f"Printable CR80 Library Card saved to:\n{path}")

    def _print_catalog_barcodes_pdf(self):
        books = LibraryRepository.get_books(self.db_session)
        if not books:
            QMessageBox.information(self, "Empty Catalog", "No books found to generate barcode labels.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Book Barcode/QR Labels", "Library_Book_Barcodes.pdf", "PDF Files (*.pdf)")
        if path:
            school = self.db_session.query(SchoolSetting).first()
            LibraryCardGenerator.generate_book_barcodes_pdf(books, school, path)
            QMessageBox.information(self, "Labels Generated", f"Barcode & QR Label sheet saved to:\n{path}")

    def _add_author(self):
        name, ok = QInputDialog.getText(self, "New Author", "Author Full Name:")
        if ok and name.strip():
            country, _ = QInputDialog.getText(self, "Author Country", "Country (optional):")
            LibraryRepository.create_author(self.db_session, name=name.strip(), country=country.strip() or None)
            self.refresh_data()

    def _add_publisher(self):
        name, ok = QInputDialog.getText(self, "New Publisher", "Publisher Name:")
        if ok and name.strip():
            country, _ = QInputDialog.getText(self, "Publisher Country", "Country (optional):")
            LibraryRepository.create_publisher(self.db_session, name=name.strip(), country=country.strip() or None)
            self.refresh_data()

    def _add_category(self):
        name, ok = QInputDialog.getText(self, "New Category", "Category Name:")
        if not ok or not name.strip():
            return
        code, ok2 = QInputDialog.getText(self, "Category Code", "Short Code (e.g. LIT-01):")
        if ok2 and code.strip():
            LibraryRepository.create_category(self.db_session, name=name.strip(), code=code.strip())
            self.refresh_data()

    def _add_shelf(self):
        code, ok = QInputDialog.getText(self, "New Shelf", "Shelf Code (e.g. SH-R1-A):")
        if not ok or not code.strip():
            return
        rack, ok2 = QInputDialog.getText(self, "Rack Number", "Rack Number (e.g. Rack 01):")
        if not ok2 or not rack.strip():
            return
        shelf, ok3 = QInputDialog.getText(self, "Shelf Number", "Shelf Level (e.g. Shelf A):")
        if ok3 and shelf.strip():
            LibraryRepository.create_shelf(self.db_session, shelf_code=code.strip(), rack_number=rack.strip(), shelf_number=shelf.strip())
            self.refresh_data()

    def _open_import_wizard(self):
        if BookImportDialog(self.db_session, parent=self).exec():
            self.refresh_data()

    # ---------------- REPORT EXPORTS ----------------
    def _export_catalog_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Book Catalog Excel", "Library_Catalog_Audit.xlsx", "Excel Files (*.xlsx)")
        if path:
            LibraryService.export_catalog_excel(self.db_session, path)
            QMessageBox.information(self, "Export Complete", f"Book catalog exported to:\n{path}")

    def _export_catalog_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Book Catalog CSV", "Library_Catalog.csv", "CSV Files (*.csv)")
        if path:
            LibraryService.export_catalog_csv(self.db_session, path)
            QMessageBox.information(self, "Export Complete", f"Book catalog CSV exported to:\n{path}")

    def _export_borrowing_history_pdf(self):
        m_id = self.hist_member_combo.currentData()
        scope = self.hist_member_combo.currentText()
        path, _ = QFileDialog.getSaveFileName(self, "Save Borrowing History PDF", "Borrowing_History_Report.pdf", "PDF Files (*.pdf)")
        if path:
            circs = LibraryRepository.get_circulations(self.db_session, member_id=m_id)
            school = self.db_session.query(SchoolSetting).first()
            LibraryReportsPDFGenerator.generate_borrowing_history_pdf(circs, scope, school, path)
            QMessageBox.information(self, "Report Saved", f"Borrowing History PDF saved to:\n{path}")

    def _export_borrowing_history_excel(self):
        m_id = self.hist_member_combo.currentData()
        path, _ = QFileDialog.getSaveFileName(self, "Export Borrowing History Excel", "Borrowing_History.xlsx", "Excel Files (*.xlsx)")
        if path:
            LibraryService.export_borrowing_history_excel(self.db_session, path, member_id=m_id)
            QMessageBox.information(self, "Export Saved", f"Borrowing History Excel saved to:\n{path}")

    def _export_fine_report_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Fine Report PDF", "Library_Fine_Report.pdf", "PDF Files (*.pdf)")
        if path:
            fines = LibraryRepository.get_fines(self.db_session)
            school = self.db_session.query(SchoolSetting).first()
            LibraryReportsPDFGenerator.generate_fine_report_pdf(fines, school, path)
            QMessageBox.information(self, "Report Saved", f"Fine Report PDF saved to:\n{path}")

    def _export_fine_report_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Fine Report Excel", "Library_Fine_Report.xlsx", "Excel Files (*.xlsx)")
        if path:
            LibraryService.export_fine_report_excel(self.db_session, path)
            QMessageBox.information(self, "Export Saved", f"Fine Report Excel saved to:\n{path}")

    def _export_inventory_report_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Inventory Report PDF", "Library_Inventory_Report.pdf", "PDF Files (*.pdf)")
        if path:
            books = LibraryRepository.get_books(self.db_session)
            stats = LibraryRepository.get_library_stats(self.db_session)
            school = self.db_session.query(SchoolSetting).first()
            LibraryReportsPDFGenerator.generate_inventory_report_pdf(books, stats, school, path)
            QMessageBox.information(self, "Report Saved", f"Inventory Report PDF saved to:\n{path}")

    def _generate_circulation_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Circulation Audit Report", "Circulation_Audit_Statement.pdf", "PDF Files (*.pdf)")
        if path:
            circs = LibraryRepository.get_circulations(self.db_session)
            stats = LibraryRepository.get_library_stats(self.db_session)
            school = self.db_session.query(SchoolSetting).first()
            CirculationReportPDFGenerator.generate_report(circs, stats, school, path)
            QMessageBox.information(self, "Report Generated", f"Circulation Audit PDF generated at:\n{path}")
