"""
EduManage Pro - Hostel & Dormitory Management Page
Phase 12: 4-Tab PySide6 GUI for Blocks, Rooms, Boarders, Gate Passes & CR80 Passes
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QHeaderView, QMessageBox,
    QFileDialog, QFrame, QGridLayout, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from app.repositories.hostel_repository import HostelRepository
from app.services.hostel_service import HostelService
from app.reports.hostel_id_card_pdf import HostelCardGenerator
from app.reports.hostel_roll_call_pdf import HostelRollCallPDFGenerator
from app.ui.dialogs.hostel_block_dialog import HostelBlockDialog
from app.ui.dialogs.hostel_room_dialog import HostelRoomDialog
from app.ui.dialogs.hostel_allocation_dialog import HostelAllocationDialog
from app.ui.dialogs.hostel_gate_pass_dialog import HostelGatePassDialog


class HostelPage(QWidget):
    """Main PySide6 page for Hostel, Dormitory & Residential Facility Management."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header & Quick KPI Stats
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Hostel & Dormitory Management")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        subtitle = QLabel("Residential halls, room capacity, bed allocations, gate passes & PVC boarder cards")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        seed_btn = QPushButton("🌱 Seed Demo Hostel")
        seed_btn.setStyleSheet("background-color: #059669; color: white; padding: 6px 12px; font-weight: bold; border-radius: 6px;")
        seed_btn.clicked.connect(self._seed_data)
        header_layout.addWidget(seed_btn)

        main_layout.addLayout(header_layout)

        # KPI Summary Cards
        self.kpi_layout = QHBoxLayout()
        self._build_kpi_cards()
        main_layout.addLayout(self.kpi_layout)

        # 2. Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 8px; }
            QTabBar::tab { padding: 8px 16px; font-weight: 600; font-size: 12px; }
            QTabBar::tab:selected { background: #059669; color: white; border-top-left-radius: 6px; border-top-right-radius: 6px; }
        """)

        # Tab 1: Blocks & Rooms
        self.tab_rooms = QWidget()
        self._init_rooms_tab()
        self.tabs.addTab(self.tab_rooms, "🏢 Hostel Blocks & Rooms")

        # Tab 2: Boarder Allocations
        self.tab_allocations = QWidget()
        self._init_allocations_tab()
        self.tabs.addTab(self.tab_allocations, "🛏️ Boarder Bed Allocations")

        # Tab 3: Gate Passes & Curfew
        self.tab_gate_passes = QWidget()
        self._init_gate_passes_tab()
        self.tabs.addTab(self.tab_gate_passes, "🎫 Gate Passes & Curfew")

        # Tab 4: Resident PVC Passes
        self.tab_passes = QWidget()
        self._init_passes_tab()
        self.tabs.addTab(self.tab_passes, "🪪 Resident Passes (CR80 PVC)")

        main_layout.addWidget(self.tabs)
        self.refresh_all()

    def _build_kpi_cards(self):
        # Clear existing
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        stats = HostelRepository.get_hostel_stats(self.db) if self.db else {}

        cards_data = [
            ("Hostel Blocks", str(stats.get("total_blocks", 0)), "#1E3A8A"),
            ("Total Rooms", str(stats.get("total_rooms", 0)), "#0D9488"),
            ("Bed Capacity", f"{stats.get('occupied_beds', 0)} / {stats.get('total_capacity', 0)}", "#059669"),
            ("Occupancy Rate", f"{stats.get('occupancy_rate', 0)}%", "#D97706"),
            ("Boarders On Leave", str(stats.get("boarders_out", 0)), "#DC2626")
        ]

        for label, val, color in cards_data:
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-left: 4px solid {color};
                    border-radius: 8px;
                    padding: 8px 12px;
                }}
            """)
            flayout = QVBoxLayout(frame)
            flayout.setContentsMargins(4, 4, 4, 4)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
            val_lbl = QLabel(val)
            val_lbl.setStyleSheet(f"color: {color}; font-size: 17px; font-weight: bold;")
            flayout.addWidget(lbl)
            flayout.addWidget(val_lbl)
            self.kpi_layout.addWidget(frame)

    # -------------------------------------------------------------
    # TAB 1: Blocks & Rooms
    # -------------------------------------------------------------
    def _init_rooms_tab(self):
        layout = QVBoxLayout(self.tab_rooms)
        layout.setContentsMargins(12, 12, 12, 12)

        btn_bar = QHBoxLayout()
        add_block_btn = QPushButton("➕ Add Block")
        add_block_btn.clicked.connect(self._add_block)
        add_room_btn = QPushButton("➕ Add Room")
        add_room_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        add_room_btn.clicked.connect(self._add_room)

        self.block_filter = QComboBox()
        self.block_filter.addItem("All Hostel Blocks", None)
        self.block_filter.currentIndexChanged.connect(self._filter_rooms)

        btn_bar.addWidget(add_block_btn)
        btn_bar.addWidget(add_room_btn)
        btn_bar.addSpacing(16)
        btn_bar.addWidget(QLabel("Filter by Block:"))
        btn_bar.addWidget(self.block_filter)
        btn_bar.addStretch()

        layout.addLayout(btn_bar)

        self.rooms_table = QTableWidget()
        self.rooms_table.setColumnCount(8)
        self.rooms_table.setHorizontalHeaderLabels([
            "ID", "Block Name", "Room No", "Floor", "Type", "Capacity / Occupied", "Monthly Fee", "Status"
        ])
        self.rooms_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rooms_table.setAlternatingRowColors(True)
        layout.addWidget(self.rooms_table)

    def _add_block(self):
        dlg = HostelBlockDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _add_room(self):
        dlg = HostelRoomDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _filter_rooms(self):
        block_id = self.block_filter.currentData()
        rooms = HostelRepository.get_all_rooms(self.db, block_id=block_id)
        self.rooms_table.setRowCount(len(rooms))
        for r_idx, r in enumerate(rooms):
            block_name = r.block.block_name if r.block else "N/A"
            occupied = len([a for a in r.allocations if a.status == "Active"])
            cap_str = f"{occupied} / {r.capacity} Beds"

            self.rooms_table.setItem(r_idx, 0, QTableWidgetItem(str(r.id)))
            self.rooms_table.setItem(r_idx, 1, QTableWidgetItem(block_name))
            self.rooms_table.setItem(r_idx, 2, QTableWidgetItem(r.room_number))
            self.rooms_table.setItem(r_idx, 3, QTableWidgetItem(f"Floor {r.floor_number}"))
            self.rooms_table.setItem(r_idx, 4, QTableWidgetItem(r.room_type))
            self.rooms_table.setItem(r_idx, 5, QTableWidgetItem(cap_str))
            self.rooms_table.setItem(r_idx, 6, QTableWidgetItem(f"৳ {r.monthly_fee:,.0f}"))

            status_item = QTableWidgetItem(r.status)
            if r.status == "Available":
                status_item.setForeground(QColor("#059669"))
            elif r.status == "Full":
                status_item.setForeground(QColor("#DC2626"))
            self.rooms_table.setItem(r_idx, 7, status_item)

    # -------------------------------------------------------------
    # TAB 2: Boarder Bed Allocations
    # -------------------------------------------------------------
    def _init_allocations_tab(self):
        layout = QVBoxLayout(self.tab_allocations)
        layout.setContentsMargins(12, 12, 12, 12)

        btn_bar = QHBoxLayout()
        alloc_btn = QPushButton("🛏️ Allocate Student to Bed")
        alloc_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        alloc_btn.clicked.connect(self._allocate_bed)

        vacate_btn = QPushButton("🚪 Vacate Selected Bed")
        vacate_btn.clicked.connect(self._vacate_bed)

        excel_btn = QPushButton("📊 Export Manifest (.xlsx)")
        excel_btn.clicked.connect(self._export_excel)

        btn_bar.addWidget(alloc_btn)
        btn_bar.addWidget(vacate_btn)
        btn_bar.addWidget(excel_btn)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self.alloc_table = QTableWidget()
        self.alloc_table.setColumnCount(8)
        self.alloc_table.setHorizontalHeaderLabels([
            "ID", "Student Name", "Student ID", "Hostel Block", "Room No", "Bed", "Admission Date", "Status"
        ])
        self.alloc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.alloc_table.setAlternatingRowColors(True)
        layout.addWidget(self.alloc_table)

    def _allocate_bed(self):
        dlg = HostelAllocationDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _vacate_bed(self):
        row = self.alloc_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Row", "Please select an allocation row to vacate.")
            return

        alloc_id = int(self.alloc_table.item(row, 0).text())
        confirm = QMessageBox.question(
            self, "Confirm Vacate", "Are you sure you want to mark this resident as vacated?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            HostelRepository.vacate_student(self.db, alloc_id)
            self.refresh_all()

    def _export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Hostel Manifest", "Hostel_Boarders_Manifest.xlsx", "Excel Files (*.xlsx)")
        if path:
            try:
                HostelService.export_hostel_allocations_excel(self.db, path)
                QMessageBox.information(self, "Export Complete", f"Successfully exported hostel manifest to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    # -------------------------------------------------------------
    # TAB 3: Gate Passes & Curfew
    # -------------------------------------------------------------
    def _init_gate_passes_tab(self):
        layout = QVBoxLayout(self.tab_gate_passes)
        layout.setContentsMargins(12, 12, 12, 12)

        btn_bar = QHBoxLayout()
        issue_pass_btn = QPushButton("🎫 Issue Gate Pass")
        issue_pass_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        issue_pass_btn.clicked.connect(self._issue_gate_pass)

        return_btn = QPushButton("✅ Mark Returned")
        return_btn.clicked.connect(self._mark_returned)

        roll_call_btn = QPushButton("📑 Print Night Roll Call PDF")
        roll_call_btn.clicked.connect(self._print_roll_call)

        btn_bar.addWidget(issue_pass_btn)
        btn_bar.addWidget(return_btn)
        btn_bar.addWidget(roll_call_btn)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self.pass_table = QTableWidget()
        self.pass_table.setColumnCount(8)
        self.pass_table.setHorizontalHeaderLabels([
            "Pass No", "Resident Name", "Room / Bed", "Purpose", "Departure Date", "Expected Return", "Actual Return", "Status"
        ])
        self.pass_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pass_table.setAlternatingRowColors(True)
        layout.addWidget(self.pass_table)

    def _issue_gate_pass(self):
        dlg = HostelGatePassDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _mark_returned(self):
        row = self.pass_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Row", "Please select a gate pass to mark returned.")
            return

        pass_no = self.pass_table.item(row, 0).text()
        from app.models.hostel import HostelGatePass
        gp = self.db.query(HostelGatePass).filter(HostelGatePass.pass_number == pass_no).first()
        if gp:
            HostelRepository.return_gate_pass(self.db, gp.id)
            self.refresh_all()

    def _print_roll_call(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Night Roll Call PDF", "Hostel_Night_Roll_Call.pdf", "PDF Files (*.pdf)")
        if path:
            try:
                from app.models.school import SchoolSetting
                school = self.db.query(SchoolSetting).first()
                allocs = HostelRepository.get_active_allocations(self.db)
                first_block = allocs[0].room.block if allocs and allocs[0].room else None
                HostelRollCallPDFGenerator.generate_manifest(first_block, allocs, school, path)
                QMessageBox.information(self, "Print Complete", f"Night Roll Call PDF generated at:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "PDF Error", str(e))

    # -------------------------------------------------------------
    # TAB 4: Resident PVC Passes (CR80)
    # -------------------------------------------------------------
    def _init_passes_tab(self):
        layout = QVBoxLayout(self.tab_passes)
        layout.setContentsMargins(12, 12, 12, 12)

        top_bar = QHBoxLayout()
        print_card_btn = QPushButton("🪪 Print Selected Resident Card PDF")
        print_card_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        print_card_btn.clicked.connect(self._print_resident_card)
        top_bar.addWidget(print_card_btn)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.cards_table = QTableWidget()
        self.cards_table.setColumnCount(7)
        self.cards_table.setHorizontalHeaderLabels([
            "Allocation ID", "Student Name", "Student ID", "Hostel Block", "Room No", "Bed No", "Emergency Phone"
        ])
        self.cards_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cards_table.setAlternatingRowColors(True)
        layout.addWidget(self.cards_table)

    def _print_resident_card(self):
        row = self.cards_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Resident", "Please select a resident to generate their CR80 card.")
            return

        alloc_id = int(self.cards_table.item(row, 0).text())
        from app.models.hostel import HostelAllocation
        from app.models.school import SchoolSetting
        alloc = self.db.query(HostelAllocation).filter(HostelAllocation.id == alloc_id).first()
        school = self.db.query(SchoolSetting).first()

        path, _ = QFileDialog.getSaveFileName(self, "Save Resident Card", f"Hostel_Card_{alloc_id}.pdf", "PDF Files (*.pdf)")
        if path:
            try:
                HostelCardGenerator.generate_single_card(alloc, school, path)
                QMessageBox.information(self, "Card Generated", f"CR80 Resident Card PDF generated at:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    # -------------------------------------------------------------
    # Refresh & Seeder
    # -------------------------------------------------------------
    def _seed_data(self):
        try:
            res = HostelService.seed_default_hostel_data(self.db)
            QMessageBox.information(self, "Seed Successful", res.get("message", "Hostel seeded."))
            self.refresh_all()
        except Exception as e:
            QMessageBox.critical(self, "Seed Error", str(e))

    def refresh_all(self):
        self._build_kpi_cards()

        # Update block filter
        self.block_filter.blockSignals(True)
        self.block_filter.clear()
        self.block_filter.addItem("All Hostel Blocks", None)
        blocks = HostelRepository.get_all_blocks(self.db)
        for b in blocks:
            self.block_filter.addItem(f"{b.block_name} ({b.gender_type})", b.id)
        self.block_filter.blockSignals(False)

        # 1. Rooms
        self._filter_rooms()

        # 2. Allocations
        allocs = HostelRepository.get_all_allocations(self.db)
        self.alloc_table.setRowCount(len(allocs))
        for r_idx, a in enumerate(allocs):
            s_name = f"{a.student.first_name} {a.student.last_name}" if a.student else "N/A"
            s_id = a.student.student_id if a.student else f"ID-{a.student_id}"
            b_name = a.room.block.block_name if a.room and a.room.block else "N/A"
            r_no = a.room.room_number if a.room else "N/A"
            adm = a.admission_date.strftime("%Y-%m-%d") if a.admission_date else ""

            self.alloc_table.setItem(r_idx, 0, QTableWidgetItem(str(a.id)))
            self.alloc_table.setItem(r_idx, 1, QTableWidgetItem(s_name))
            self.alloc_table.setItem(r_idx, 2, QTableWidgetItem(s_id))
            self.alloc_table.setItem(r_idx, 3, QTableWidgetItem(b_name))
            self.alloc_table.setItem(r_idx, 4, QTableWidgetItem(r_no))
            self.alloc_table.setItem(r_idx, 5, QTableWidgetItem(a.bed_number))
            self.alloc_table.setItem(r_idx, 6, QTableWidgetItem(adm))

            st = QTableWidgetItem(a.status)
            if a.status == "Active":
                st.setForeground(QColor("#059669"))
            elif a.status == "Vacated":
                st.setForeground(QColor("#64748B"))
            self.alloc_table.setItem(r_idx, 7, st)

        # 3. Gate Passes
        passes = HostelRepository.get_all_gate_passes(self.db)
        self.pass_table.setRowCount(len(passes))
        for r_idx, p in enumerate(passes):
            alloc = p.allocation
            s_name = f"{alloc.student.first_name} {alloc.student.last_name}" if alloc and alloc.student else "N/A"
            room_info = f"{alloc.room.room_number if alloc and alloc.room else 'N/A'} ({alloc.bed_number if alloc else ''})"
            dep_date = p.leave_date.strftime("%Y-%m-%d") if p.leave_date else ""
            ret_date = p.expected_return_date.strftime("%Y-%m-%d") if p.expected_return_date else ""
            act_date = p.actual_return_date.strftime("%Y-%m-%d") if p.actual_return_date else "—"

            self.pass_table.setItem(r_idx, 0, QTableWidgetItem(p.pass_number))
            self.pass_table.setItem(r_idx, 1, QTableWidgetItem(s_name))
            self.pass_table.setItem(r_idx, 2, QTableWidgetItem(room_info))
            self.pass_table.setItem(r_idx, 3, QTableWidgetItem(p.purpose))
            self.pass_table.setItem(r_idx, 4, QTableWidgetItem(dep_date))
            self.pass_table.setItem(r_idx, 5, QTableWidgetItem(ret_date))
            self.pass_table.setItem(r_idx, 6, QTableWidgetItem(act_date))

            st = QTableWidgetItem(p.status)
            if p.status == "Out":
                st.setForeground(QColor("#D97706"))
            elif p.status == "Returned":
                st.setForeground(QColor("#059669"))
            elif p.status == "Overstayed":
                st.setForeground(QColor("#DC2626"))
            self.pass_table.setItem(r_idx, 7, st)

        # 4. Resident Passes (Active Allocations)
        active_allocs = [a for a in allocs if a.status == "Active"]
        self.cards_table.setRowCount(len(active_allocs))
        for r_idx, a in enumerate(active_allocs):
            s_name = f"{a.student.first_name} {a.student.last_name}" if a.student else "N/A"
            s_id = a.student.student_id if a.student else f"ID-{a.student_id}"
            b_name = a.room.block.block_name if a.room and a.room.block else "N/A"
            r_no = a.room.room_number if a.room else "N/A"
            phone = a.emergency_phone or (a.student.emergency_contact if a.student else "") or "N/A"

            self.cards_table.setItem(r_idx, 0, QTableWidgetItem(str(a.id)))
            self.cards_table.setItem(r_idx, 1, QTableWidgetItem(s_name))
            self.cards_table.setItem(r_idx, 2, QTableWidgetItem(s_id))
            self.cards_table.setItem(r_idx, 3, QTableWidgetItem(b_name))
            self.cards_table.setItem(r_idx, 4, QTableWidgetItem(r_no))
            self.cards_table.setItem(r_idx, 5, QTableWidgetItem(a.bed_number))
            self.cards_table.setItem(r_idx, 6, QTableWidgetItem(phone))
