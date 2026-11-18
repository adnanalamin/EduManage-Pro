"""
EduManage Pro - Enterprise Hostel & Dormitory Management Page
7-Tab PySide6 GUI for Buildings, Floors, Rooms, Beds, Double-Bed Prevention,
Check-In/Check-Out, Hostel Fees, Mess Management, Visitor Records,
Complaints, Maintenance, Gate Passes, CR80 Resident Cards & Reports.
"""

from datetime import date, datetime
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.database.connection import SessionLocal
from app.models.hostel import (
    HostelAllocation,
    HostelBed,
    HostelComplaint,
    HostelFeeCharge,
    HostelGatePass,
    HostelMaintenanceRequest,
    HostelRoom,
)
from app.models.school import SchoolSetting
from app.reports.hostel_id_card_pdf import HostelCardGenerator
from app.reports.hostel_reports_pdf import HostelReportsPDFGenerator
from app.reports.hostel_roll_call_pdf import HostelRollCallPDFGenerator
from app.repositories.hostel_repository import HostelRepository
from app.services.hostel_service import HostelService
from app.ui.dialogs.hostel_allocation_dialog import HostelAllocationDialog
from app.ui.dialogs.hostel_block_dialog import HostelBlockDialog
from app.ui.dialogs.hostel_dialogs import (
    HostelBedDialog,
    HostelCheckOutDialog,
    HostelComplaintDialog,
    HostelFeePaymentDialog,
    HostelFloorDialog,
    HostelMaintenanceDialog,
    HostelMessLogDialog,
    HostelMessMenuDialog,
    HostelMessPlanDialog,
    HostelVisitorDialog,
)
from app.ui.dialogs.hostel_gate_pass_dialog import HostelGatePassDialog
from app.ui.dialogs.hostel_room_dialog import HostelRoomDialog


class HostelPage(QWidget):
    """Main PySide6 workspace for complete Hostel & Boarding Operations."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session if db_session is not None else SessionLocal()
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Hostel & Dormitory Management")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        subtitle = QLabel(
            "Buildings, floors, rooms, bed inventory (zero double allocation), "
            "check-in/out clearance, fees, mess, visitors, maintenance & reports"
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        refresh_btn = QPushButton("🔄 Refresh Data")
        refresh_btn.setStyleSheet("background-color: #0F172A; color: white; padding: 6px 14px; font-weight: 600; border-radius: 6px;")
        refresh_btn.clicked.connect(self.refresh_all)
        header_layout.addWidget(refresh_btn)

        main_layout.addLayout(header_layout)

        # KPI Cards
        self.kpi_layout = QHBoxLayout()
        self._build_kpi_cards()
        main_layout.addLayout(self.kpi_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 8px; }
            QTabBar::tab { padding: 8px 13px; font-weight: 600; font-size: 12px; }
            QTabBar::tab:selected { background: #059669; color: white; border-top-left-radius: 6px; border-top-right-radius: 6px; }
        """)

        self.tab_infra = QWidget()
        self._init_infra_tab()
        self.tabs.addTab(self.tab_infra, "🏢 Buildings, Floors & Rooms")

        self.tab_allocs = QWidget()
        self._init_allocations_tab()
        self.tabs.addTab(self.tab_allocs, "🛏️ Allocations & Check-In/Out")

        self.tab_fees = QWidget()
        self._init_fees_tab()
        self.tabs.addTab(self.tab_fees, "💳 Hostel Fees")

        self.tab_mess = QWidget()
        self._init_mess_tab()
        self.tabs.addTab(self.tab_mess, "🍽️ Mess & Dining")

        self.tab_visitors = QWidget()
        self._init_visitors_tab()
        self.tabs.addTab(self.tab_visitors, "🛂 Visitors & Gate Passes")

        self.tab_maintenance = QWidget()
        self._init_maintenance_tab()
        self.tabs.addTab(self.tab_maintenance, "🛠️ Complaints & Maintenance")

        self.tab_reports = QWidget()
        self._init_reports_tab()
        self.tabs.addTab(self.tab_reports, "🪪 Resident Cards & Reports")

        main_layout.addWidget(self.tabs)
        self.refresh_all()

    def _build_kpi_cards(self):
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        stats = HostelRepository.get_hostel_stats(self.db)
        cards = [
            ("Buildings / Floors", f"{stats.get('total_blocks', 0)} / {stats.get('total_floors', 0)}", "#1E3A8A"),
            ("Rooms / Beds", f"{stats.get('total_rooms', 0)} / {stats.get('total_capacity', 0)}", "#0D9488"),
            ("Occupied / Vacant", f"{stats.get('occupied_beds', 0)} / {stats.get('available_beds', 0)} ({stats.get('occupancy_rate', 0)}%)", "#059669"),
            ("Hostel Fee Due", f"৳ {stats.get('fee_due', 0):,.0f}", "#B45309"),
            ("Open Issues / Maint", f"{stats.get('open_complaints', 0)} / {stats.get('pending_maintenance', 0)}", "#DC2626"),
            ("Visitors / Outpass", f"{stats.get('visitors_inside', 0)} / {stats.get('boarders_out', 0)}", "#4338CA"),
        ]
        for label, val, color in cards:
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-left: 4px solid {color};
                    border-radius: 8px;
                    padding: 6px 10px;
                }}
            """)
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(4, 2, 4, 2)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
            val_lbl = QLabel(val)
            val_lbl.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold;")
            fl.addWidget(lbl)
            fl.addWidget(val_lbl)
            self.kpi_layout.addWidget(frame)

    # -------------------------------------------------------------
    # TAB 1: Buildings, Floors & Rooms
    # -------------------------------------------------------------
    def _init_infra_tab(self):
        layout = QVBoxLayout(self.tab_infra)
        layout.setContentsMargins(12, 12, 12, 12)

        btn_bar = QHBoxLayout()
        add_blk = QPushButton("➕ Add Building")
        add_blk.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold;")
        add_blk.clicked.connect(self._add_block)

        edit_blk = QPushButton("✏️ Edit Selected Building")
        edit_blk.clicked.connect(self._edit_block)

        add_flr = QPushButton("➕ Add Floor")
        add_flr.clicked.connect(self._add_floor)

        add_rm = QPushButton("➕ Add Room")
        add_rm.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        add_rm.clicked.connect(self._add_room)

        edit_rm = QPushButton("✏️ Edit Selected Room")
        edit_rm.clicked.connect(self._edit_room)

        self.block_filter = QComboBox()
        self.block_filter.addItem("All Hostel Buildings", None)
        self.block_filter.currentIndexChanged.connect(self._filter_rooms)

        btn_bar.addWidget(add_blk)
        btn_bar.addWidget(edit_blk)
        btn_bar.addWidget(add_flr)
        btn_bar.addWidget(add_rm)
        btn_bar.addWidget(edit_rm)
        btn_bar.addSpacing(12)
        btn_bar.addWidget(QLabel("Building Filter:"))
        btn_bar.addWidget(self.block_filter)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        splitter = QSplitter(Qt.Vertical)

        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self.blocks_table = QTableWidget()
        self.blocks_table.setColumnCount(7)
        self.blocks_table.setHorizontalHeaderLabels([
            "ID", "Code", "Building Name", "Gender", "Warden", "Floors / Rooms", "Status"
        ])
        self.blocks_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.blocks_table.setAlternatingRowColors(True)

        self.floors_table = QTableWidget()
        self.floors_table.setColumnCount(6)
        self.floors_table.setHorizontalHeaderLabels([
            "Building", "Floor #", "Floor Name", "Supervisor", "Rooms", "Status"
        ])
        self.floors_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.floors_table.setAlternatingRowColors(True)

        top_layout.addWidget(self.blocks_table, 3)
        top_layout.addWidget(self.floors_table, 2)
        splitter.addWidget(top_widget)

        self.rooms_table = QTableWidget()
        self.rooms_table.setColumnCount(10)
        self.rooms_table.setHorizontalHeaderLabels([
            "ID", "Building", "Floor", "Room No", "Type", "Occupied / Capacity", "Vacant", "Monthly Fee", "Facilities", "Status"
        ])
        self.rooms_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rooms_table.setAlternatingRowColors(True)
        splitter.addWidget(self.rooms_table)

        layout.addWidget(splitter)

    def _add_block(self):
        dlg = HostelBlockDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _edit_block(self):
        row = self.blocks_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Building", "Please select a building row to edit.")
            return
        block_id = int(self.blocks_table.item(row, 0).text())
        blk = HostelRepository.get_block_by_id(self.db, block_id)
        if blk:
            dlg = HostelBlockDialog(self, self.db, block=blk)
            if dlg.exec():
                self.refresh_all()

    def _add_floor(self):
        dlg = HostelFloorDialog(self, self.db, default_block_id=self.block_filter.currentData())
        if dlg.exec():
            self.refresh_all()

    def _add_room(self):
        dlg = HostelRoomDialog(self, self.db, default_block_id=self.block_filter.currentData())
        if dlg.exec():
            self.refresh_all()

    def _edit_room(self):
        row = self.rooms_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Room", "Please select a room row to edit.")
            return
        room_id = int(self.rooms_table.item(row, 0).text())
        room = HostelRepository.get_room_by_id(self.db, room_id)
        if room:
            dlg = HostelRoomDialog(self, self.db, room=room)
            if dlg.exec():
                self.refresh_all()

    def _filter_rooms(self):
        block_id = self.block_filter.currentData()
        rooms = HostelRepository.get_all_rooms(self.db, block_id=block_id)
        self.rooms_table.setRowCount(len(rooms))
        for r_idx, r in enumerate(rooms):
            block_name = r.block.block_name if r.block else "N/A"
            floor_lbl = r.floor.floor_name if r.floor else f"Floor {r.floor_number}"
            occ = len([a for a in r.allocations if a.status == "Active"])
            vac = max(0, int(r.capacity or 0) - occ)
            fac = ", ".join([x for x in ["Attached Bath" if r.has_attached_bath else None, "AC" if r.has_ac else None] if x]) or r.amenities

            self.rooms_table.setItem(r_idx, 0, QTableWidgetItem(str(r.id)))
            self.rooms_table.setItem(r_idx, 1, QTableWidgetItem(block_name))
            self.rooms_table.setItem(r_idx, 2, QTableWidgetItem(floor_lbl))
            self.rooms_table.setItem(r_idx, 3, QTableWidgetItem(r.room_number))
            self.rooms_table.setItem(r_idx, 4, QTableWidgetItem(r.room_type))
            self.rooms_table.setItem(r_idx, 5, QTableWidgetItem(f"{occ} / {r.capacity}"))
            self.rooms_table.setItem(r_idx, 6, QTableWidgetItem(str(vac)))
            self.rooms_table.setItem(r_idx, 7, QTableWidgetItem(f"৳ {r.monthly_fee:,.0f}"))
            self.rooms_table.setItem(r_idx, 8, QTableWidgetItem(fac or "Standard"))

            st = QTableWidgetItem(r.status)
            if r.status == "Available":
                st.setForeground(QColor("#059669"))
            elif r.status == "Full":
                st.setForeground(QColor("#DC2626"))
            else:
                st.setForeground(QColor("#D97706"))
            self.rooms_table.setItem(r_idx, 9, st)

    # -------------------------------------------------------------
    # TAB 2: Allocations, Bed Inventory & Check-In/Out
    # -------------------------------------------------------------
    def _init_allocations_tab(self):
        layout = QVBoxLayout(self.tab_allocs)
        layout.setContentsMargins(12, 12, 12, 12)

        btn_bar = QHBoxLayout()
        alloc_btn = QPushButton("🛏️ Allocate Bed & Check-In")
        alloc_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        alloc_btn.clicked.connect(self._allocate_bed)

        cin_btn = QPushButton("✅ Log Check-In Time")
        cin_btn.clicked.connect(self._check_in_boarder)

        cout_btn = QPushButton("🚪 Check-Out & Clearance")
        cout_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold;")
        cout_btn.clicked.connect(self._check_out_boarder)

        add_bed_btn = QPushButton("➕ Add Bed Unit")
        add_bed_btn.clicked.connect(self._add_bed)

        maint_bed_btn = QPushButton("🔧 Toggle Selected Bed Maintenance")
        maint_bed_btn.clicked.connect(self._toggle_bed_maintenance)

        btn_bar.addWidget(alloc_btn)
        btn_bar.addWidget(cin_btn)
        btn_bar.addWidget(cout_btn)
        btn_bar.addSpacing(12)
        btn_bar.addWidget(add_bed_btn)
        btn_bar.addWidget(maint_bed_btn)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        splitter = QSplitter(Qt.Vertical)

        self.alloc_table = QTableWidget()
        self.alloc_table.setColumnCount(10)
        self.alloc_table.setHorizontalHeaderLabels([
            "ID", "Student", "Student ID", "Building", "Room / Bed", "Check-In", "Check-Out", "Clearance", "Damage", "Status"
        ])
        self.alloc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.alloc_table.setAlternatingRowColors(True)
        splitter.addWidget(self.alloc_table)

        self.beds_table = QTableWidget()
        self.beds_table.setColumnCount(6)
        self.beds_table.setHorizontalHeaderLabels([
            "Bed ID", "Building", "Room No", "Bed Identifier", "Bed Type", "Status"
        ])
        self.beds_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.beds_table.setAlternatingRowColors(True)
        splitter.addWidget(self.beds_table)

        layout.addWidget(splitter)

    def _allocate_bed(self):
        dlg = HostelAllocationDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _check_in_boarder(self):
        row = self.alloc_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Allocation", "Select an active allocation row to update check-in.")
            return
        alloc_id = int(self.alloc_table.item(row, 0).text())
        note, ok = QInputDialog.getText(self, "Check-In Note", "Enter room key / check-in note (optional):")
        if ok:
            HostelRepository.check_in_boarder(
                self.db,
                allocation_id=alloc_id,
                check_in_date=date.today(),
                check_in_time=datetime.now().strftime("%I:%M %p"),
                notes=note.strip() or None,
            )
            self.refresh_all()

    def _check_out_boarder(self):
        row = self.alloc_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Allocation", "Select an active allocation row to check out.")
            return
        alloc_id = int(self.alloc_table.item(row, 0).text())
        alloc = self.db.query(HostelAllocation).filter(HostelAllocation.id == alloc_id).first()
        if not alloc or alloc.status != "Active":
            QMessageBox.warning(self, "Already Checked Out", "Only active allocations can be checked out.")
            return
        dlg = HostelCheckOutDialog(self, self.db, allocation=alloc)
        if dlg.exec():
            self.refresh_all()

    def _add_bed(self):
        dlg = HostelBedDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _toggle_bed_maintenance(self):
        row = self.beds_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Bed", "Select a bed unit below to toggle maintenance status.")
            return
        bed_id = int(self.beds_table.item(row, 0).text())
        bed = self.db.query(HostelBed).filter(HostelBed.id == bed_id).first()
        if not bed:
            return
        if bed.status == "Occupied":
            QMessageBox.warning(self, "Bed Occupied", "Check out the resident first before putting this bed under maintenance.")
            return
        new_status = "Available" if bed.status == "Maintenance" else "Maintenance"
        HostelRepository.update_bed(self.db, bed.id, status=new_status)
        self.refresh_all()

    # -------------------------------------------------------------
    # TAB 3: Hostel Fees
    # -------------------------------------------------------------
    def _init_fees_tab(self):
        layout = QVBoxLayout(self.tab_fees)
        layout.setContentsMargins(12, 12, 12, 12)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Billing Month (YYYY-MM):"))
        self.fee_month_edit = QLineEdit(date.today().strftime("%Y-%m"))
        self.fee_month_edit.setFixedWidth(95)
        bar.addWidget(self.fee_month_edit)

        bar.addWidget(QLabel("Default Mess Fee:"))
        self.default_mess_spin = QDoubleSpinBox()
        self.default_mess_spin.setRange(0, 50000)
        self.default_mess_spin.setPrefix("৳ ")
        self.default_mess_spin.setValue(2500.0)
        bar.addWidget(self.default_mess_spin)

        gen_btn = QPushButton("🧾 Generate Monthly Bills")
        gen_btn.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold;")
        gen_btn.clicked.connect(self._generate_fees)
        bar.addWidget(gen_btn)

        pay_btn = QPushButton("💵 Collect Fee")
        pay_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        pay_btn.clicked.connect(self._collect_fee)
        bar.addWidget(pay_btn)

        waive_btn = QPushButton("🏷️ Waive Charge")
        waive_btn.clicked.connect(self._waive_fee)
        bar.addWidget(waive_btn)

        pdf_btn = QPushButton("📄 Fee Statement PDF")
        pdf_btn.clicked.connect(self._export_fee_pdf)
        bar.addWidget(pdf_btn)
        bar.addStretch()
        layout.addLayout(bar)

        self.fees_table = QTableWidget()
        self.fees_table.setColumnCount(11)
        self.fees_table.setHorizontalHeaderLabels([
            "ID", "Month", "Student", "Room / Bed", "Rent", "Mess", "Other", "Discount", "Paid", "Due", "Status"
        ])
        self.fees_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.fees_table.setAlternatingRowColors(True)
        layout.addWidget(self.fees_table)

    def _generate_fees(self):
        month_str = self.fee_month_edit.text().strip()
        if len(month_str) != 7 or month_str[4] != "-":
            QMessageBox.warning(self, "Invalid Month", "Please use YYYY-MM format (e.g., 2026-05).")
            return
        res = HostelRepository.generate_monthly_fees(
            self.db,
            billing_month=month_str,
            default_mess_fee=self.default_mess_spin.value(),
        )
        QMessageBox.information(
            self,
            "Hostel Billing Complete",
            f"Generated: {res['created']} new bills | Skipped existing: {res['skipped']}",
        )
        self.refresh_all()

    def _collect_fee(self):
        row = self.fees_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Bill", "Select a hostel fee bill to collect payment.")
            return
        charge_id = int(self.fees_table.item(row, 0).text())
        charge = self.db.query(HostelFeeCharge).filter(HostelFeeCharge.id == charge_id).first()
        if charge:
            dlg = HostelFeePaymentDialog(self, self.db, charge=charge)
            if dlg.exec():
                self.refresh_all()

    def _waive_fee(self):
        row = self.fees_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Bill", "Select a hostel fee bill to waive.")
            return
        charge_id = int(self.fees_table.item(row, 0).text())
        reason, ok = QInputDialog.getText(self, "Waive Fee Charge", "Waiver Reason:")
        if ok:
            HostelRepository.waive_fee_charge(self.db, charge_id, remarks=reason.strip() or None)
            self.refresh_all()

    def _export_fee_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Hostel Fee Report", "Hostel_Fee_Statement.pdf", "PDF Files (*.pdf)")
        if path:
            charges = HostelRepository.get_fee_charges(self.db)
            school = self.db.query(SchoolSetting).first()
            HostelReportsPDFGenerator.generate_fee_report(charges, billing_month=self.fee_month_edit.text().strip(), school=school, output_path=path)
            QMessageBox.information(self, "PDF Saved", f"Hostel Fee Report saved to:\n{path}")

    # -------------------------------------------------------------
    # TAB 4: Mess & Dining Management
    # -------------------------------------------------------------
    def _init_mess_tab(self):
        layout = QVBoxLayout(self.tab_mess)
        layout.setContentsMargins(12, 12, 12, 12)

        bar = QHBoxLayout()
        plan_btn = QPushButton("➕ Create Mess Plan")
        plan_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        plan_btn.clicked.connect(self._add_mess_plan)

        menu_btn = QPushButton("📅 Add Weekly Menu Slot")
        menu_btn.clicked.connect(self._add_mess_menu)

        log_btn = QPushButton("🍲 Log Daily Service Count")
        log_btn.clicked.connect(self._add_mess_log)

        bar.addWidget(plan_btn)
        bar.addWidget(menu_btn)
        bar.addWidget(log_btn)
        bar.addStretch()
        layout.addLayout(bar)

        splitter = QSplitter(Qt.Vertical)

        self.mess_plans_table = QTableWidget()
        self.mess_plans_table.setColumnCount(5)
        self.mess_plans_table.setHorizontalHeaderLabels([
            "Plan Name", "Monthly Fee", "Meals Included", "Description", "Status"
        ])
        self.mess_plans_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mess_plans_table.setAlternatingRowColors(True)
        splitter.addWidget(self.mess_plans_table)

        bottom_split = QSplitter(Qt.Horizontal)
        self.mess_menu_table = QTableWidget()
        self.mess_menu_table.setColumnCount(5)
        self.mess_menu_table.setHorizontalHeaderLabels(["Day", "Meal", "Menu Items", "Serving Time", "Building"])
        self.mess_menu_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mess_menu_table.setAlternatingRowColors(True)

        self.mess_logs_table = QTableWidget()
        self.mess_logs_table.setColumnCount(5)
        self.mess_logs_table.setHorizontalHeaderLabels(["Date", "Meal", "Plates Served", "Meal Cost", "Building"])
        self.mess_logs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mess_logs_table.setAlternatingRowColors(True)

        bottom_split.addWidget(self.mess_menu_table)
        bottom_split.addWidget(self.mess_logs_table)
        splitter.addWidget(bottom_split)
        layout.addWidget(splitter)

    def _add_mess_plan(self):
        dlg = HostelMessPlanDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _add_mess_menu(self):
        dlg = HostelMessMenuDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _add_mess_log(self):
        dlg = HostelMessLogDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    # -------------------------------------------------------------
    # TAB 5: Visitors & Gate Passes
    # -------------------------------------------------------------
    def _init_visitors_tab(self):
        layout = QVBoxLayout(self.tab_visitors)
        layout.setContentsMargins(12, 12, 12, 12)

        splitter = QSplitter(Qt.Vertical)

        # Visitors pane
        v_widget = QWidget()
        v_lay = QVBoxLayout(v_widget)
        v_lay.setContentsMargins(0, 0, 0, 0)
        v_bar = QHBoxLayout()
        v_in_btn = QPushButton("🛂 Check In Visitor")
        v_in_btn.setStyleSheet("background-color: #0369A1; color: white; font-weight: bold;")
        v_in_btn.clicked.connect(self._check_in_visitor)
        v_out_btn = QPushButton("👋 Check Out Visitor")
        v_out_btn.clicked.connect(self._check_out_visitor)
        v_bar.addWidget(QLabel("<b>Visitor Register</b>"))
        v_bar.addStretch()
        v_bar.addWidget(v_in_btn)
        v_bar.addWidget(v_out_btn)
        v_lay.addLayout(v_bar)

        self.visitors_table = QTableWidget()
        self.visitors_table.setColumnCount(9)
        self.visitors_table.setHorizontalHeaderLabels([
            "ID", "Date", "Visitor", "Phone", "Relation", "Visiting Boarder", "Check-In", "Check-Out", "Status"
        ])
        self.visitors_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.visitors_table.setAlternatingRowColors(True)
        v_lay.addWidget(self.visitors_table)
        splitter.addWidget(v_widget)

        # Gate passes pane
        gp_widget = QWidget()
        gp_lay = QVBoxLayout(gp_widget)
        gp_lay.setContentsMargins(0, 0, 0, 0)
        gp_bar = QHBoxLayout()
        issue_gp = QPushButton("🎫 Issue Gate Pass")
        issue_gp.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        issue_gp.clicked.connect(self._issue_gate_pass)
        ret_gp = QPushButton("✅ Mark Returned")
        ret_gp.clicked.connect(self._mark_returned)
        roll_gp = QPushButton("📑 Night Roll Call PDF")
        roll_gp.clicked.connect(self._print_roll_call)
        gp_bar.addWidget(QLabel("<b>Boarder Gate Passes / Curfew Outpasses</b>"))
        gp_bar.addStretch()
        gp_bar.addWidget(issue_gp)
        gp_bar.addWidget(ret_gp)
        gp_bar.addWidget(roll_gp)
        gp_lay.addLayout(gp_bar)

        self.pass_table = QTableWidget()
        self.pass_table.setColumnCount(8)
        self.pass_table.setHorizontalHeaderLabels([
            "Pass No", "Resident", "Room / Bed", "Purpose", "Departure", "Expected Return", "Actual Return", "Status"
        ])
        self.pass_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pass_table.setAlternatingRowColors(True)
        gp_lay.addWidget(self.pass_table)
        splitter.addWidget(gp_widget)

        layout.addWidget(splitter)

    def _check_in_visitor(self):
        dlg = HostelVisitorDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _check_out_visitor(self):
        row = self.visitors_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Visitor", "Please select a visitor row to check out.")
            return
        vis_id = int(self.visitors_table.item(row, 0).text())
        HostelRepository.check_out_visitor(self.db, vis_id)
        self.refresh_all()

    def _issue_gate_pass(self):
        dlg = HostelGatePassDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _mark_returned(self):
        row = self.pass_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Gate Pass", "Select a gate pass row to mark returned.")
            return
        pass_no = self.pass_table.item(row, 0).text()
        gp = self.db.query(HostelGatePass).filter(HostelGatePass.pass_number == pass_no).first()
        if gp:
            HostelRepository.return_gate_pass(self.db, gp.id)
            self.refresh_all()

    def _print_roll_call(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Night Roll Call PDF", "Hostel_Night_Roll_Call.pdf", "PDF Files (*.pdf)")
        if path:
            school = self.db.query(SchoolSetting).first()
            allocs = HostelRepository.get_active_allocations(self.db)
            first_block = allocs[0].room.block if allocs and allocs[0].room else None
            HostelRollCallPDFGenerator.generate_manifest(first_block, allocs, school, path)
            QMessageBox.information(self, "Print Complete", f"Night Roll Call PDF generated at:\n{path}")

    # -------------------------------------------------------------
    # TAB 6: Complaints & Maintenance
    # -------------------------------------------------------------
    def _init_maintenance_tab(self):
        layout = QVBoxLayout(self.tab_maintenance)
        layout.setContentsMargins(12, 12, 12, 12)

        splitter = QSplitter(Qt.Vertical)

        # Complaints section
        c_widget = QWidget()
        c_lay = QVBoxLayout(c_widget)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_bar = QHBoxLayout()
        add_cmp = QPushButton("📢 Log Complaint")
        add_cmp.setStyleSheet("background-color: #B45309; color: white; font-weight: bold;")
        add_cmp.clicked.connect(self._log_complaint)
        esc_cmp = QPushButton("🔧 Escalate to Maintenance")
        esc_cmp.clicked.connect(self._escalate_complaint)
        res_cmp = QPushButton("✅ Resolve Complaint")
        res_cmp.clicked.connect(self._resolve_complaint)
        c_bar.addWidget(QLabel("<b>Boarder Complaints</b>"))
        c_bar.addStretch()
        c_bar.addWidget(add_cmp)
        c_bar.addWidget(esc_cmp)
        c_bar.addWidget(res_cmp)
        c_lay.addLayout(c_bar)

        self.complaints_table = QTableWidget()
        self.complaints_table.setColumnCount(8)
        self.complaints_table.setHorizontalHeaderLabels([
            "ID", "Ref No", "Date", "Student / Room", "Title", "Category", "Priority", "Status"
        ])
        self.complaints_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.complaints_table.setAlternatingRowColors(True)
        c_lay.addWidget(self.complaints_table)
        splitter.addWidget(c_widget)

        # Maintenance work orders
        m_widget = QWidget()
        m_lay = QVBoxLayout(m_widget)
        m_lay.setContentsMargins(0, 0, 0, 0)
        m_bar = QHBoxLayout()
        add_m = QPushButton("🛠️ New Maintenance Work Order")
        add_m.setStyleSheet("background-color: #991B1B; color: white; font-weight: bold;")
        add_m.clicked.connect(self._create_maintenance)
        done_m = QPushButton("✅ Complete Maintenance")
        done_m.clicked.connect(self._complete_maintenance)
        m_bar.addWidget(QLabel("<b>Facility & Room Maintenance Tickets</b>"))
        m_bar.addStretch()
        m_bar.addWidget(add_m)
        m_bar.addWidget(done_m)
        m_lay.addLayout(m_bar)

        self.maint_table = QTableWidget()
        self.maint_table.setColumnCount(8)
        self.maint_table.setHorizontalHeaderLabels([
            "ID", "Ticket No", "Building / Room", "Issue", "Type", "Technician", "Cost", "Status"
        ])
        self.maint_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.maint_table.setAlternatingRowColors(True)
        m_lay.addWidget(self.maint_table)
        splitter.addWidget(m_widget)

        layout.addWidget(splitter)

    def _log_complaint(self):
        dlg = HostelComplaintDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _escalate_complaint(self):
        row = self.complaints_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Complaint", "Select a complaint to escalate to maintenance.")
            return
        comp_id = int(self.complaints_table.item(row, 0).text())
        comp = self.db.query(HostelComplaint).filter(HostelComplaint.id == comp_id).first()
        if comp:
            dlg = HostelMaintenanceDialog(self, self.db, complaint=comp)
            if dlg.exec():
                self.refresh_all()

    def _resolve_complaint(self):
        row = self.complaints_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Complaint", "Select a complaint to resolve.")
            return
        comp_id = int(self.complaints_table.item(row, 0).text())
        note, ok = QInputDialog.getText(self, "Resolve Complaint", "Resolution Notes:")
        if ok:
            HostelRepository.update_complaint(self.db, comp_id, status="Resolved", resolution_notes=note.strip() or None)
            self.refresh_all()

    def _create_maintenance(self):
        dlg = HostelMaintenanceDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _complete_maintenance(self):
        row = self.maint_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Ticket", "Select a maintenance ticket to mark completed.")
            return
        req_id = int(self.maint_table.item(row, 0).text())
        req = self.db.query(HostelMaintenanceRequest).filter(HostelMaintenanceRequest.id == req_id).first()
        if req:
            cost, ok = QInputDialog.getDouble(
                self, "Complete Work Order", "Final Actual Cost (৳):", float(req.estimated_cost or 0.0), 0, 1000000, 2
            )
            if ok:
                HostelRepository.update_maintenance_request(self.db, req_id, status="Completed", actual_cost=cost)
                self.refresh_all()

    # -------------------------------------------------------------
    # TAB 7: Resident Cards & Hostel Reports
    # -------------------------------------------------------------
    def _init_reports_tab(self):
        layout = QVBoxLayout(self.tab_reports)
        layout.setContentsMargins(12, 12, 12, 12)

        top_bar = QHBoxLayout()
        print_card = QPushButton("🪪 Resident CR80 Card PDF")
        print_card.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        print_card.clicked.connect(self._print_resident_card)

        occ_pdf = QPushButton("🏢 Occupancy Inventory PDF")
        occ_pdf.clicked.connect(self._export_occupancy_pdf)

        fee_pdf = QPushButton("💳 Fee Statement PDF")
        fee_pdf.clicked.connect(self._export_fee_pdf)

        ops_pdf = QPushButton("🛠️ Operations Audit PDF")
        ops_pdf.clicked.connect(self._export_operations_pdf)

        xlsx_full = QPushButton("📊 Full Hostel Workbook (.xlsx)")
        xlsx_full.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold;")
        xlsx_full.clicked.connect(self._export_full_excel)

        top_bar.addWidget(print_card)
        top_bar.addWidget(occ_pdf)
        top_bar.addWidget(fee_pdf)
        top_bar.addWidget(ops_pdf)
        top_bar.addWidget(xlsx_full)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.cards_table = QTableWidget()
        self.cards_table.setColumnCount(7)
        self.cards_table.setHorizontalHeaderLabels([
            "Allocation ID", "Student Name", "Student ID", "Building", "Room No", "Bed No", "Emergency Phone"
        ])
        self.cards_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cards_table.setAlternatingRowColors(True)
        layout.addWidget(self.cards_table)

    def _print_resident_card(self):
        row = self.cards_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Resident", "Please select a resident row.")
            return
        alloc_id = int(self.cards_table.item(row, 0).text())
        alloc = self.db.query(HostelAllocation).filter(HostelAllocation.id == alloc_id).first()
        school = self.db.query(SchoolSetting).first()
        path, _ = QFileDialog.getSaveFileName(self, "Save Resident Card", f"Hostel_Card_{alloc_id}.pdf", "PDF Files (*.pdf)")
        if path and alloc:
            HostelCardGenerator.generate_single_card(alloc, school, path)
            QMessageBox.information(self, "Card Generated", f"CR80 Resident Card generated at:\n{path}")

    def _export_occupancy_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Occupancy Report", "Hostel_Occupancy_Report.pdf", "PDF Files (*.pdf)")
        if path:
            school = self.db.query(SchoolSetting).first()
            HostelReportsPDFGenerator.generate_occupancy_report(
                HostelRepository.get_all_blocks(self.db),
                HostelRepository.get_all_rooms(self.db),
                HostelRepository.get_all_allocations(self.db),
                school=school,
                output_path=path,
            )
            QMessageBox.information(self, "PDF Saved", f"Occupancy report generated at:\n{path}")

    def _export_operations_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Operations Audit Report", "Hostel_Operations_Audit.pdf", "PDF Files (*.pdf)")
        if path:
            school = self.db.query(SchoolSetting).first()
            HostelReportsPDFGenerator.generate_operations_report(
                HostelRepository.get_visitors(self.db),
                HostelRepository.get_complaints(self.db),
                HostelRepository.get_maintenance_requests(self.db),
                school=school,
                output_path=path,
            )
            QMessageBox.information(self, "PDF Saved", f"Operations audit PDF generated at:\n{path}")

    def _export_full_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Hostel Workbook", "Hostel_Complete_Report.xlsx", "Excel Files (*.xlsx)")
        if path:
            HostelService.export_hostel_comprehensive_excel(self.db, path)
            QMessageBox.information(self, "Export Complete", f"Multi-sheet hostel workbook saved to:\n{path}")

    # -------------------------------------------------------------
    # Global Refresh
    # -------------------------------------------------------------
    def refresh_all(self):
        self._build_kpi_cards()

        # Buildings & filter
        blocks = HostelRepository.get_all_blocks(self.db)
        cur_blk = self.block_filter.currentData()
        self.block_filter.blockSignals(True)
        self.block_filter.clear()
        self.block_filter.addItem("All Hostel Buildings", None)
        for b in blocks:
            self.block_filter.addItem(f"{b.block_name} ({b.gender_type})", b.id)
        if cur_blk is not None:
            idx = self.block_filter.findData(cur_blk)
            if idx >= 0:
                self.block_filter.setCurrentIndex(idx)
        self.block_filter.blockSignals(False)

        self.blocks_table.setRowCount(len(blocks))
        for r_idx, b in enumerate(blocks):
            self.blocks_table.setItem(r_idx, 0, QTableWidgetItem(str(b.id)))
            self.blocks_table.setItem(r_idx, 1, QTableWidgetItem(b.block_code or "-"))
            self.blocks_table.setItem(r_idx, 2, QTableWidgetItem(b.block_name))
            self.blocks_table.setItem(r_idx, 3, QTableWidgetItem(b.gender_type))
            self.blocks_table.setItem(r_idx, 4, QTableWidgetItem(b.warden_name or "-"))
            self.blocks_table.setItem(r_idx, 5, QTableWidgetItem(f"{len(b.floors)} / {len(b.rooms)}"))
            self.blocks_table.setItem(r_idx, 6, QTableWidgetItem(b.status))

        # Floors
        floors = HostelRepository.get_floors(self.db)
        self.floors_table.setRowCount(len(floors))
        for r_idx, fl in enumerate(floors):
            self.floors_table.setItem(r_idx, 0, QTableWidgetItem(fl.block.block_name if fl.block else "-"))
            self.floors_table.setItem(r_idx, 1, QTableWidgetItem(str(fl.floor_number)))
            self.floors_table.setItem(r_idx, 2, QTableWidgetItem(fl.floor_name))
            self.floors_table.setItem(r_idx, 3, QTableWidgetItem(fl.supervisor_name or "-"))
            self.floors_table.setItem(r_idx, 4, QTableWidgetItem(str(len(fl.rooms))))
            self.floors_table.setItem(r_idx, 5, QTableWidgetItem(fl.status))

        # Rooms
        self._filter_rooms()

        # Allocations
        allocs = HostelRepository.get_all_allocations(self.db)
        self.alloc_table.setRowCount(len(allocs))
        for r_idx, a in enumerate(allocs):
            s_name = f"{a.student.first_name} {a.student.last_name}" if a.student else f"Student #{a.student_id}"
            s_id = a.student.student_id if a.student else str(a.student_id)
            b_name = a.room.block.block_name if a.room and a.room.block else "-"
            r_no = f"{a.room.room_number if a.room else '-'} / {a.bed_number}"
            cin = str(a.check_in_date or a.admission_date or "-")
            cout = str(a.check_out_date or a.vacate_date or "-")
            self.alloc_table.setItem(r_idx, 0, QTableWidgetItem(str(a.id)))
            self.alloc_table.setItem(r_idx, 1, QTableWidgetItem(s_name))
            self.alloc_table.setItem(r_idx, 2, QTableWidgetItem(s_id))
            self.alloc_table.setItem(r_idx, 3, QTableWidgetItem(b_name))
            self.alloc_table.setItem(r_idx, 4, QTableWidgetItem(r_no))
            self.alloc_table.setItem(r_idx, 5, QTableWidgetItem(cin))
            self.alloc_table.setItem(r_idx, 6, QTableWidgetItem(cout))
            self.alloc_table.setItem(r_idx, 7, QTableWidgetItem(a.clearance_status))
            self.alloc_table.setItem(r_idx, 8, QTableWidgetItem(f"৳ {float(a.damage_charges or 0.0):,.0f}"))
            st = QTableWidgetItem(a.status)
            st.setForeground(QColor("#059669" if a.status == "Active" else "#64748B"))
            self.alloc_table.setItem(r_idx, 9, st)

        # Beds inventory
        beds = HostelRepository.get_beds(self.db)
        self.beds_table.setRowCount(len(beds))
        for r_idx, bd in enumerate(beds):
            b_name = bd.room.block.block_name if bd.room and bd.room.block else "-"
            r_no = bd.room.room_number if bd.room else "-"
            self.beds_table.setItem(r_idx, 0, QTableWidgetItem(str(bd.id)))
            self.beds_table.setItem(r_idx, 1, QTableWidgetItem(b_name))
            self.beds_table.setItem(r_idx, 2, QTableWidgetItem(r_no))
            self.beds_table.setItem(r_idx, 3, QTableWidgetItem(bd.bed_number))
            self.beds_table.setItem(r_idx, 4, QTableWidgetItem(bd.bed_type))
            st = QTableWidgetItem(bd.status)
            st.setForeground(QColor("#059669" if bd.status == "Available" else ("#DC2626" if bd.status == "Occupied" else "#D97706")))
            self.beds_table.setItem(r_idx, 5, st)

        # Fees
        charges = HostelRepository.get_fee_charges(self.db)
        self.fees_table.setRowCount(len(charges))
        for r_idx, ch in enumerate(charges):
            s_name = f"{ch.student.first_name} {ch.student.last_name}" if ch.student else f"Student #{ch.student_id}"
            rb = f"{ch.allocation.room.room_number if ch.allocation and ch.allocation.room else '-'} / {ch.allocation.bed_number if ch.allocation else '-'}"
            self.fees_table.setItem(r_idx, 0, QTableWidgetItem(str(ch.id)))
            self.fees_table.setItem(r_idx, 1, QTableWidgetItem(ch.billing_month))
            self.fees_table.setItem(r_idx, 2, QTableWidgetItem(s_name))
            self.fees_table.setItem(r_idx, 3, QTableWidgetItem(rb))
            self.fees_table.setItem(r_idx, 4, QTableWidgetItem(f"৳ {float(ch.room_rent or 0):,.0f}"))
            self.fees_table.setItem(r_idx, 5, QTableWidgetItem(f"৳ {float(ch.mess_fee or 0):,.0f}"))
            self.fees_table.setItem(r_idx, 6, QTableWidgetItem(f"৳ {float(ch.other_charges or 0):,.0f}"))
            self.fees_table.setItem(r_idx, 7, QTableWidgetItem(f"৳ {float(ch.discount or 0):,.0f}"))
            self.fees_table.setItem(r_idx, 8, QTableWidgetItem(f"৳ {float(ch.paid_amount or 0):,.0f}"))
            self.fees_table.setItem(r_idx, 9, QTableWidgetItem(f"৳ {ch.balance_due:,.0f}"))
            self.fees_table.setItem(r_idx, 10, QTableWidgetItem(ch.status))

        # Mess
        plans = HostelRepository.get_mess_plans(self.db)
        self.mess_plans_table.setRowCount(len(plans))
        for r_idx, p in enumerate(plans):
            meals = ", ".join([m for flag, m in [(p.includes_breakfast, "Breakfast"), (p.includes_lunch, "Lunch"), (p.includes_snacks, "Snacks"), (p.includes_dinner, "Dinner")] if flag])
            self.mess_plans_table.setItem(r_idx, 0, QTableWidgetItem(p.plan_name))
            self.mess_plans_table.setItem(r_idx, 1, QTableWidgetItem(f"৳ {float(p.monthly_fee or 0):,.0f}"))
            self.mess_plans_table.setItem(r_idx, 2, QTableWidgetItem(meals))
            self.mess_plans_table.setItem(r_idx, 3, QTableWidgetItem(p.description or "-"))
            self.mess_plans_table.setItem(r_idx, 4, QTableWidgetItem(p.status))

        menus = HostelRepository.get_mess_menus(self.db)
        self.mess_menu_table.setRowCount(len(menus))
        for r_idx, m in enumerate(menus):
            self.mess_menu_table.setItem(r_idx, 0, QTableWidgetItem(m.day_of_week))
            self.mess_menu_table.setItem(r_idx, 1, QTableWidgetItem(m.meal_type))
            self.mess_menu_table.setItem(r_idx, 2, QTableWidgetItem(m.menu_items))
            self.mess_menu_table.setItem(r_idx, 3, QTableWidgetItem(m.serving_time or "-"))
            self.mess_menu_table.setItem(r_idx, 4, QTableWidgetItem(m.block.block_name if m.block else "All Buildings"))

        logs = HostelRepository.get_mess_logs(self.db)
        self.mess_logs_table.setRowCount(len(logs))
        for r_idx, lg in enumerate(logs):
            self.mess_logs_table.setItem(r_idx, 0, QTableWidgetItem(str(lg.log_date)))
            self.mess_logs_table.setItem(r_idx, 1, QTableWidgetItem(lg.meal_type))
            self.mess_logs_table.setItem(r_idx, 2, QTableWidgetItem(str(lg.plates_served)))
            self.mess_logs_table.setItem(r_idx, 3, QTableWidgetItem(f"৳ {float(lg.meal_cost or 0):,.2f}"))
            self.mess_logs_table.setItem(r_idx, 4, QTableWidgetItem(lg.block.block_name if lg.block else "Central Mess"))

        # Visitors
        visitors = HostelRepository.get_visitors(self.db)
        self.visitors_table.setRowCount(len(visitors))
        for r_idx, v in enumerate(visitors):
            s_name = f"{v.student.first_name} {v.student.last_name}" if v.student else "-"
            self.visitors_table.setItem(r_idx, 0, QTableWidgetItem(str(v.id)))
            self.visitors_table.setItem(r_idx, 1, QTableWidgetItem(str(v.visit_date)))
            self.visitors_table.setItem(r_idx, 2, QTableWidgetItem(v.visitor_name))
            self.visitors_table.setItem(r_idx, 3, QTableWidgetItem(v.visitor_phone))
            self.visitors_table.setItem(r_idx, 4, QTableWidgetItem(v.relationship_to_student))
            self.visitors_table.setItem(r_idx, 5, QTableWidgetItem(s_name))
            self.visitors_table.setItem(r_idx, 6, QTableWidgetItem(v.check_in_time))
            self.visitors_table.setItem(r_idx, 7, QTableWidgetItem(v.check_out_time or "—"))
            self.visitors_table.setItem(r_idx, 8, QTableWidgetItem(v.status))

        # Gate Passes
        passes = HostelRepository.get_all_gate_passes(self.db)
        self.pass_table.setRowCount(len(passes))
        for r_idx, p in enumerate(passes):
            alloc = p.allocation
            s_name = f"{alloc.student.first_name} {alloc.student.last_name}" if alloc and alloc.student else "N/A"
            rb = f"{alloc.room.room_number if alloc and alloc.room else 'N/A'} ({alloc.bed_number if alloc else ''})"
            self.pass_table.setItem(r_idx, 0, QTableWidgetItem(p.pass_number))
            self.pass_table.setItem(r_idx, 1, QTableWidgetItem(s_name))
            self.pass_table.setItem(r_idx, 2, QTableWidgetItem(rb))
            self.pass_table.setItem(r_idx, 3, QTableWidgetItem(p.purpose))
            self.pass_table.setItem(r_idx, 4, QTableWidgetItem(p.leave_date.strftime("%Y-%m-%d") if p.leave_date else ""))
            self.pass_table.setItem(r_idx, 5, QTableWidgetItem(p.expected_return_date.strftime("%Y-%m-%d") if p.expected_return_date else ""))
            self.pass_table.setItem(r_idx, 6, QTableWidgetItem(p.actual_return_date.strftime("%Y-%m-%d") if p.actual_return_date else "—"))
            self.pass_table.setItem(r_idx, 7, QTableWidgetItem(p.status))

        # Complaints & Maintenance
        complaints = HostelRepository.get_complaints(self.db)
        self.complaints_table.setRowCount(len(complaints))
        for r_idx, cmp_row in enumerate(complaints):
            s_name = f"{cmp_row.student.first_name} {cmp_row.student.last_name}" if cmp_row.student else "-"
            r_no = cmp_row.room.room_number if cmp_row.room else "-"
            self.complaints_table.setItem(r_idx, 0, QTableWidgetItem(str(cmp_row.id)))
            self.complaints_table.setItem(r_idx, 1, QTableWidgetItem(cmp_row.complaint_no))
            self.complaints_table.setItem(r_idx, 2, QTableWidgetItem(str(cmp_row.reported_date)))
            self.complaints_table.setItem(r_idx, 3, QTableWidgetItem(f"{s_name} ({r_no})"))
            self.complaints_table.setItem(r_idx, 4, QTableWidgetItem(cmp_row.title))
            self.complaints_table.setItem(r_idx, 5, QTableWidgetItem(cmp_row.category))
            self.complaints_table.setItem(r_idx, 6, QTableWidgetItem(cmp_row.priority))
            self.complaints_table.setItem(r_idx, 7, QTableWidgetItem(cmp_row.status))

        maint = HostelRepository.get_maintenance_requests(self.db)
        self.maint_table.setRowCount(len(maint))
        for r_idx, m in enumerate(maint):
            loc = f"{m.block.block_name if m.block else '-'} / {m.room.room_number if m.room else '-'}"
            cost_val = float(m.actual_cost or m.estimated_cost or 0.0)
            self.maint_table.setItem(r_idx, 0, QTableWidgetItem(str(m.id)))
            self.maint_table.setItem(r_idx, 1, QTableWidgetItem(m.ticket_no))
            self.maint_table.setItem(r_idx, 2, QTableWidgetItem(loc))
            self.maint_table.setItem(r_idx, 3, QTableWidgetItem(m.issue_title))
            self.maint_table.setItem(r_idx, 4, QTableWidgetItem(m.maintenance_type))
            self.maint_table.setItem(r_idx, 5, QTableWidgetItem(m.vendor_or_technician or "-"))
            self.maint_table.setItem(r_idx, 6, QTableWidgetItem(f"৳ {cost_val:,.2f}"))
            self.maint_table.setItem(r_idx, 7, QTableWidgetItem(m.status))

        # Active Resident Cards Table
        active_allocs = [a for a in allocs if a.status == "Active"]
        self.cards_table.setRowCount(len(active_allocs))
        for r_idx, a in enumerate(active_allocs):
            s_name = f"{a.student.first_name} {a.student.last_name}" if a.student else f"Student #{a.student_id}"
            s_id = a.student.student_id if a.student else str(a.student_id)
            b_name = a.room.block.block_name if a.room and a.room.block else "-"
            r_no = a.room.room_number if a.room else "-"
            phone = a.emergency_phone or (a.student.emergency_contact if a.student else "") or "N/A"
            self.cards_table.setItem(r_idx, 0, QTableWidgetItem(str(a.id)))
            self.cards_table.setItem(r_idx, 1, QTableWidgetItem(s_name))
            self.cards_table.setItem(r_idx, 2, QTableWidgetItem(s_id))
            self.cards_table.setItem(r_idx, 3, QTableWidgetItem(b_name))
            self.cards_table.setItem(r_idx, 4, QTableWidgetItem(r_no))
            self.cards_table.setItem(r_idx, 5, QTableWidgetItem(a.bed_number))
            self.cards_table.setItem(r_idx, 6, QTableWidgetItem(phone))
