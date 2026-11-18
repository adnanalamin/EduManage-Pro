"""
EduManage Pro - Complete Transport & Fleet Management Page
PySide6 7-Tab Operations Center using Real Database Records (No Demo Auto-Seeding):
1. Fleet Vehicles (Bus, Van, Microbus, Other, Registration, Driver, Helper, Odometer)
2. Routes & Pickup Points (Routes + Ordered Boarding Stops & Fares)
3. Commuters & Bus Passes (Students, Teachers, Staff + CR80 Transit Passes)
4. Transport Fees (Monthly Billing, Partial/Full Collection, Waivers, Receipts & Reports)
5. Fuel, Maintenance & Reminders (Mileage Tracking, Service History & Automated Alerts)
6. Insurance & Compliance Documents (Policies, Fitness, Permits, Tax Tokens Vault)
7. GPS Integration Hub (Hardware-Optional Telematics Adapters & Manual Check-Ins)
"""

from datetime import date
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QComboBox, QLineEdit, QPushButton, QLabel, QHeaderView,
    QMessageBox, QFileDialog, QFrame, QSplitter
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session

from app.models.transport import (
    Vehicle,
    TransportRoute,
    TransportPassenger,
    TransportFeeCharge,
    VEHICLE_TYPES,
)
from app.models.school import SchoolSetting
from app.repositories.transport_repository import TransportRepository
from app.services.transport_service import TransportService, GPSIntegrationManager
from app.reports.bus_pass_pdf import BusPassGenerator
from app.reports.route_manifest_pdf import RouteManifestPDFGenerator
from app.reports.transport_reports_pdf import TransportReportsPDFGenerator
from app.ui.dialogs.vehicle_form_dialog import VehicleFormDialog
from app.ui.dialogs.route_form_dialog import RouteFormDialog
from app.ui.dialogs.assign_transport_dialog import AssignTransportDialog
from app.ui.dialogs.transport_dialogs import (
    FuelLogDialog,
    MaintenanceLogDialog,
    InsuranceDialog,
    VehicleDocumentDialog,
    TransportFeePaymentDialog,
    GPSDeviceConfigDialog,
    ManualGPSCheckinDialog,
)
from app.database.connection import SessionLocal


class TransportPage(QWidget):
    """Main Transport & Fleet Management page backed strictly by live database records."""

    def __init__(self, parent=None, db_session: Optional[Session] = None, session_manager=None):
        super().__init__(parent)
        self.session_manager = session_manager
        self.db_session = db_session if db_session is not None else SessionLocal()

        self._setup_ui()
        self.refresh_data()

    def refresh_all(self):
        """Standard lifecycle hook called on navigation."""
        self.refresh_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # 1. Header & Global Export/Report Actions
        title_box = QHBoxLayout()
        title_label = QLabel("Transport & Fleet Management")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        title_box.addWidget(title_label)
        title_box.addStretch()

        export_fleet_btn = QPushButton("Export Fleet Workbook (Excel)")
        export_fleet_btn.setStyleSheet("background-color: #0369A1; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        export_fleet_btn.clicked.connect(self._export_fleet_excel)
        title_box.addWidget(export_fleet_btn)

        fleet_pdf_btn = QPushButton("Fleet & Maintenance Report (PDF)")
        fleet_pdf_btn.setStyleSheet("background-color: #047857; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        fleet_pdf_btn.clicked.connect(self._generate_fleet_pdf)
        title_box.addWidget(fleet_pdf_btn)

        export_excel_btn = QPushButton("Export Manifest (Excel)")
        export_excel_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        export_excel_btn.clicked.connect(self._export_manifest_excel)
        title_box.addWidget(export_excel_btn)

        manifest_pdf_btn = QPushButton("Route Roll Sheet (PDF)")
        manifest_pdf_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        manifest_pdf_btn.clicked.connect(self._generate_route_manifest_pdf)
        title_box.addWidget(manifest_pdf_btn)

        main_layout.addLayout(title_box)

        # 2. Reminder Alert Banner
        self.reminder_banner = QLabel("Checking fleet maintenance & compliance reminders...")
        self.reminder_banner.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 5px; "
            "padding: 6px 12px; color: #334155; font-weight: 600;"
        )
        main_layout.addWidget(self.reminder_banner)

        # 3. KPI Metrics Bar
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(10)
        self.lbl_vehicles = self._create_kpi_card("Fleet Vehicles", "0", "#0284C7")
        self.lbl_routes = self._create_kpi_card("Active Routes", "0", "#B45309")
        self.lbl_capacity = self._create_kpi_card("Seat Capacity", "0", "#475569")
        self.lbl_passengers = self._create_kpi_card("Active Commuters", "0", "#059669")
        self.lbl_revenue = self._create_kpi_card("Monthly Fare Pool", "$0.00", "#10B981")
        self.lbl_fuel_maint = self._create_kpi_card("Fuel + Maint Spend", "$0.00", "#7C3AED")
        self.lbl_alerts = self._create_kpi_card("Active Alerts", "0", "#DC2626")
        main_layout.addLayout(self.kpi_layout)

        # 4. 7-Tab Operations Center
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                font-weight: 600;
                padding: 8px 14px;
                color: #475569;
            }
            QTabBar::tab:selected {
                color: #B45309;
                border-bottom: 2px solid #B45309;
            }
        """)

        self.tab_vehicles = QWidget()
        self._setup_vehicles_tab()
        self.tabs.addTab(self.tab_vehicles, "Fleet Vehicles")

        self.tab_routes = QWidget()
        self._setup_routes_tab()
        self.tabs.addTab(self.tab_routes, "Routes & Pickup Points")

        self.tab_passengers = QWidget()
        self._setup_passengers_tab()
        self.tabs.addTab(self.tab_passengers, "Commuters & Bus Passes")

        self.tab_fees = QWidget()
        self._setup_fees_tab()
        self.tabs.addTab(self.tab_fees, "Transport Fees")

        self.tab_fuel_maint = QWidget()
        self._setup_fuel_maint_tab()
        self.tabs.addTab(self.tab_fuel_maint, "Fuel, Maintenance & Reminders")

        self.tab_compliance = QWidget()
        self._setup_compliance_tab()
        self.tabs.addTab(self.tab_compliance, "Insurance & Documents")

        self.tab_gps = QWidget()
        self._setup_gps_tab()
        self.tabs.addTab(self.tab_gps, "GPS Hub (Optional)")

        main_layout.addWidget(self.tabs)

    def _create_kpi_card(self, title: str, default_val: str, color_hex: str) -> QLabel:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid #E2E8F0;
                border-top: 3px solid {color_hex};
                border-radius: 6px;
                padding: 4px 8px;
            }}
        """)
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(6, 4, 6, 4)
        vbox.setSpacing(2)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 500;")
        v_lbl = QLabel(default_val)
        v_lbl.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {color_hex};")

        vbox.addWidget(t_lbl)
        vbox.addWidget(v_lbl)
        self.kpi_layout.addWidget(frame)
        return v_lbl

    # ---------------- TAB 1: FLEET VEHICLES ----------------
    def _setup_vehicles_tab(self):
        layout = QVBoxLayout(self.tab_vehicles)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        ctrl_box = QHBoxLayout()
        ctrl_box.addWidget(QLabel("Type Filter:"))
        self.v_type_filter = QComboBox()
        self.v_type_filter.addItem("All Types", None)
        for vt in VEHICLE_TYPES:
            self.v_type_filter.addItem(vt, vt)
        self.v_type_filter.currentIndexChanged.connect(self.load_vehicles_table)
        ctrl_box.addWidget(self.v_type_filter)
        ctrl_box.addStretch()

        add_v_btn = QPushButton("+ Register New Vehicle")
        add_v_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        add_v_btn.clicked.connect(self._add_vehicle)
        ctrl_box.addWidget(add_v_btn)
        layout.addLayout(ctrl_box)

        self.vehicles_table = QTableWidget()
        headers = [
            "Plate / Reg No", "Model", "Type", "Capacity", "Odometer",
            "Driver & License", "Helper / Conductor", "Insurance / Fitness", "Status", "Actions"
        ]
        self.vehicles_table.setColumnCount(len(headers))
        self.vehicles_table.setHorizontalHeaderLabels(headers)
        self.vehicles_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.vehicles_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.vehicles_table.verticalHeader().setVisible(False)
        self.vehicles_table.setAlternatingRowColors(True)
        layout.addWidget(self.vehicles_table)

    def load_vehicles_table(self):
        v_type = self.v_type_filter.currentData()
        vehicles = TransportRepository.get_vehicles(self.db_session, vehicle_type=v_type)
        self.vehicles_table.setRowCount(len(vehicles))

        for row, v in enumerate(vehicles):
            plate_txt = f"{v.vehicle_number}"
            if v.registration_no and v.registration_no != v.vehicle_number:
                plate_txt += f"\n({v.registration_no})"
            self.vehicles_table.setItem(row, 0, QTableWidgetItem(plate_txt))
            self.vehicles_table.setItem(row, 1, QTableWidgetItem(v.vehicle_model))

            disp_type = "Microbus (Minibus)" if v.vehicle_type == "Minibus" else v.vehicle_type
            it_t = QTableWidgetItem(disp_type)
            it_t.setTextAlignment(Qt.AlignCenter)
            self.vehicles_table.setItem(row, 2, it_t)

            booked = len([p for p in v.passengers if p.status == "Active"]) if v.passengers else 0
            it_cap = QTableWidgetItem(f"{booked} / {v.seating_capacity}")
            it_cap.setTextAlignment(Qt.AlignCenter)
            self.vehicles_table.setItem(row, 3, it_cap)

            it_odo = QTableWidgetItem(f"{float(v.current_odometer_km or 0.0):,.0f} km")
            it_odo.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.vehicles_table.setItem(row, 4, it_odo)

            drv_txt = f"{v.driver_name} ({v.driver_phone})"
            if v.driver_license:
                drv_txt += f" [{v.driver_license}]"
            self.vehicles_table.setItem(row, 5, QTableWidgetItem(drv_txt))

            h_text = f"{v.helper_name} ({v.helper_phone or '-'})" if v.helper_name else "-"
            self.vehicles_table.setItem(row, 6, QTableWidgetItem(h_text))

            comp_txt = f"Ins: {v.insurance_expiry or '-'}\nFit: {v.fitness_expiry or '-'}"
            self.vehicles_table.setItem(row, 7, QTableWidgetItem(comp_txt))

            it_st = QTableWidgetItem(v.status)
            it_st.setTextAlignment(Qt.AlignCenter)
            it_st.setForeground(Qt.darkGreen if v.status == "Active" else Qt.red)
            self.vehicles_table.setItem(row, 8, it_st)

            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)
            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet("background-color: #F1F5F9; color: #1E293B; font-size: 11px; padding: 2px 8px;")
            edit_btn.clicked.connect(lambda _, veh=v: self._edit_vehicle(veh))
            act_layout.addWidget(edit_btn)
            self.vehicles_table.setCellWidget(row, 9, act_widget)

    def _add_vehicle(self):
        dlg = VehicleFormDialog(self.db_session, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _edit_vehicle(self, v: Vehicle):
        dlg = VehicleFormDialog(self.db_session, vehicle=v, parent=self)
        if dlg.exec():
            self.refresh_data()

    # ---------------- TAB 2: ROUTES & PICKUP POINTS ----------------
    def _setup_routes_tab(self):
        layout = QVBoxLayout(self.tab_routes)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        ctrl_box = QHBoxLayout()
        ctrl_box.addWidget(QLabel("Transit Routes (click any route to inspect its Pickup Points below)"))
        ctrl_box.addStretch()

        add_r_btn = QPushButton("+ Create Route & Pickup Points")
        add_r_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        add_r_btn.clicked.connect(self._add_route)
        ctrl_box.addWidget(add_r_btn)
        layout.addLayout(ctrl_box)

        splitter = QSplitter(Qt.Vertical)

        self.routes_table = QTableWidget()
        headers = [
            "Route Code", "Route Name", "Origin", "Destination",
            "Distance", "Monthly Fee", "Vehicle", "Pickup / Drop", "Stops", "Actions"
        ]
        self.routes_table.setColumnCount(len(headers))
        self.routes_table.setHorizontalHeaderLabels(headers)
        self.routes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.routes_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.routes_table.verticalHeader().setVisible(False)
        self.routes_table.setAlternatingRowColors(True)
        self.routes_table.itemSelectionChanged.connect(self._on_route_selected_for_stops)
        splitter.addWidget(self.routes_table)

        stops_wrap = QWidget()
        sw_layout = QVBoxLayout(stops_wrap)
        sw_layout.setContentsMargins(0, 6, 0, 0)
        self.stops_header_lbl = QLabel("Pickup Points for Selected Route:")
        self.stops_header_lbl.setStyleSheet("font-weight: bold; color: #334155;")
        sw_layout.addWidget(self.stops_header_lbl)

        self.route_stops_table = QTableWidget(0, 6)
        self.route_stops_table.setHorizontalHeaderLabels([
            "Order", "Pickup Point", "Morning Pickup", "Afternoon Drop", "Stop Fee", "Landmark / Note"
        ])
        self.route_stops_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.route_stops_table.verticalHeader().setVisible(False)
        self.route_stops_table.setAlternatingRowColors(True)
        sw_layout.addWidget(self.route_stops_table)
        splitter.addWidget(stops_wrap)

        layout.addWidget(splitter)

    def load_routes_table(self):
        routes = TransportRepository.get_routes(self.db_session)
        self._loaded_routes = routes
        self.routes_table.setRowCount(len(routes))

        for row, r in enumerate(routes):
            it_code = QTableWidgetItem(r.route_code)
            it_code.setTextAlignment(Qt.AlignCenter)
            it_code.setData(Qt.UserRole, r.id)
            self.routes_table.setItem(row, 0, it_code)

            self.routes_table.setItem(row, 1, QTableWidgetItem(r.route_name))
            self.routes_table.setItem(row, 2, QTableWidgetItem(r.start_point))
            self.routes_table.setItem(row, 3, QTableWidgetItem(r.end_point))

            it_dist = QTableWidgetItem(f"{r.distance_km:.1f} km")
            it_dist.setTextAlignment(Qt.AlignCenter)
            self.routes_table.setItem(row, 4, it_dist)

            it_fare = QTableWidgetItem(f"{float(r.monthly_fee or 0.0):.2f}")
            it_fare.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.routes_table.setItem(row, 5, it_fare)

            v_info = r.vehicle.vehicle_number if r.vehicle else "Unassigned"
            self.routes_table.setItem(row, 6, QTableWidgetItem(v_info))

            it_tm = QTableWidgetItem(f"{r.pickup_time or '-'} / {r.drop_time or '-'}")
            it_tm.setTextAlignment(Qt.AlignCenter)
            self.routes_table.setItem(row, 7, it_tm)

            it_sc = QTableWidgetItem(f"{len(r.stops) if r.stops else 0} stops")
            it_sc.setTextAlignment(Qt.AlignCenter)
            self.routes_table.setItem(row, 8, it_sc)

            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)
            edit_btn = QPushButton("Edit / Stops")
            edit_btn.setStyleSheet("background-color: #F1F5F9; color: #1E293B; font-size: 11px; padding: 2px 8px;")
            edit_btn.clicked.connect(lambda _, rt=r: self._edit_route(rt))
            act_layout.addWidget(edit_btn)
            self.routes_table.setCellWidget(row, 9, act_widget)

        if routes:
            self.routes_table.selectRow(0)
            self._populate_route_stops_table(routes[0])
        else:
            self.route_stops_table.setRowCount(0)

    def _on_route_selected_for_stops(self):
        row = self.routes_table.currentRow()
        if row < 0:
            return
        it = self.routes_table.item(row, 0)
        if not it:
            return
        r_id = it.data(Qt.UserRole)
        route = TransportRepository.get_route_by_id(self.db_session, r_id)
        if route:
            self._populate_route_stops_table(route)

    def _populate_route_stops_table(self, route: TransportRoute):
        self.stops_header_lbl.setText(f"Pickup Points for {route.route_code}: {route.route_name}")
        stops = sorted(route.stops or [], key=lambda s: s.stop_order)
        self.route_stops_table.setRowCount(len(stops))
        for idx, s in enumerate(stops):
            self.route_stops_table.setItem(idx, 0, QTableWidgetItem(str(s.stop_order)))
            self.route_stops_table.setItem(idx, 1, QTableWidgetItem(s.stop_name))
            self.route_stops_table.setItem(idx, 2, QTableWidgetItem(s.pickup_time or "-"))
            self.route_stops_table.setItem(idx, 3, QTableWidgetItem(s.drop_time or "-"))
            self.route_stops_table.setItem(idx, 4, QTableWidgetItem(f"{float(s.fare or 0.0):.2f}"))
            self.route_stops_table.setItem(idx, 5, QTableWidgetItem(s.landmark or "-"))

    def _add_route(self):
        dlg = RouteFormDialog(self.db_session, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _edit_route(self, r: TransportRoute):
        dlg = RouteFormDialog(self.db_session, route=r, parent=self)
        if dlg.exec():
            self.refresh_data()

    # ---------------- TAB 3: COMMUTERS & BUS PASSES ----------------
    def _setup_passengers_tab(self):
        layout = QVBoxLayout(self.tab_passengers)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        ctrl_box = QHBoxLayout()
        ctrl_box.addWidget(QLabel("Route Filter:"))
        self.route_filter_combo = QComboBox()
        self.route_filter_combo.addItem("All Transit Routes", None)
        self.route_filter_combo.currentIndexChanged.connect(self.load_passengers_table)
        ctrl_box.addWidget(self.route_filter_combo)
        ctrl_box.addStretch()

        assign_btn = QPushButton("+ Allocate Commuter (Student / Teacher / Staff)")
        assign_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        assign_btn.clicked.connect(self._allocate_commuter)
        ctrl_box.addWidget(assign_btn)
        layout.addLayout(ctrl_box)

        self.passengers_table = QTableWidget()
        headers = [
            "Pass Code", "Commuter Name", "Type", "Class / Designation",
            "Route", "Pickup Point", "Vehicle Plate", "Seat", "Monthly Fee", "Status", "Actions"
        ]
        self.passengers_table.setColumnCount(len(headers))
        self.passengers_table.setHorizontalHeaderLabels(headers)
        self.passengers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.passengers_table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeToContents)
        self.passengers_table.verticalHeader().setVisible(False)
        self.passengers_table.setAlternatingRowColors(True)
        layout.addWidget(self.passengers_table)

    def load_passengers_table(self):
        r_id = self.route_filter_combo.currentData()
        passengers = TransportRepository.get_passengers(self.db_session, route_id=r_id)
        self.passengers_table.setRowCount(len(passengers))

        for row, p in enumerate(passengers):
            it_id = QTableWidgetItem(p.pass_code or f"#{p.id:04d}")
            it_id.setTextAlignment(Qt.AlignCenter)
            self.passengers_table.setItem(row, 0, it_id)

            name, affil, _, _ = TransportService._passenger_display_info(p)
            self.passengers_table.setItem(row, 1, QTableWidgetItem(name))

            it_type = QTableWidgetItem(p.passenger_type)
            it_type.setTextAlignment(Qt.AlignCenter)
            self.passengers_table.setItem(row, 2, it_type)

            self.passengers_table.setItem(row, 3, QTableWidgetItem(affil))
            self.passengers_table.setItem(row, 4, QTableWidgetItem(f"{p.route.route_code}: {p.route.route_name}" if p.route else "-"))
            self.passengers_table.setItem(row, 5, QTableWidgetItem(p.stop.stop_name if p.stop else "Campus Gate"))

            it_v = QTableWidgetItem(p.vehicle.vehicle_number if p.vehicle else "-")
            it_v.setTextAlignment(Qt.AlignCenter)
            self.passengers_table.setItem(row, 6, it_v)

            it_seat = QTableWidgetItem(p.seat_number or "Assigned")
            it_seat.setTextAlignment(Qt.AlignCenter)
            self.passengers_table.setItem(row, 7, it_seat)

            it_fare = QTableWidgetItem(f"{float(p.monthly_fare or 0.0):.2f}")
            it_fare.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.passengers_table.setItem(row, 8, it_fare)

            it_st = QTableWidgetItem(p.status)
            it_st.setTextAlignment(Qt.AlignCenter)
            it_st.setForeground(Qt.darkGreen if p.status == "Active" else Qt.red)
            self.passengers_table.setItem(row, 9, it_st)

            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)
            act_layout.setSpacing(4)

            if p.status == "Active":
                pass_btn = QPushButton("Pass PDF")
                pass_btn.setStyleSheet("background-color: #B45309; color: white; font-size: 11px; padding: 2px 6px;")
                pass_btn.clicked.connect(lambda _, pax=p: self._print_bus_pass(pax))
                act_layout.addWidget(pass_btn)

                cancel_btn = QPushButton("Cancel")
                cancel_btn.setStyleSheet("background-color: #FEE2E2; color: #DC2626; font-size: 11px; padding: 2px 6px;")
                cancel_btn.clicked.connect(lambda _, pid=p.id: self._cancel_allocation(pid))
                act_layout.addWidget(cancel_btn)

            self.passengers_table.setCellWidget(row, 10, act_widget)

    def _allocate_commuter(self):
        dlg = AssignTransportDialog(self.db_session, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _cancel_allocation(self, passenger_id: int):
        if QMessageBox.question(self, "Confirm Cancellation", "Cancel this commuter's transport seat allocation?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            TransportRepository.cancel_allocation(self.db_session, passenger_id, reason="User cancellation")
            self.refresh_data()

    def _print_bus_pass(self, passenger: TransportPassenger):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save School Bus Pass PDF", f"Bus_Pass_{passenger.id}.pdf", "PDF Files (*.pdf)")
        if file_path:
            try:
                school = self.db_session.query(SchoolSetting).first()
                BusPassGenerator.generate_single_pass(passenger, school, file_path)
                QMessageBox.information(self, "Bus Pass Generated", f"Printable CR80 Bus Pass saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "PDF Error", f"Failed to generate pass:\n{str(e)}")

    # ---------------- TAB 4: TRANSPORT FEES ----------------
    def _setup_fees_tab(self):
        layout = QVBoxLayout(self.tab_fees)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        ctrl_box = QHBoxLayout()
        ctrl_box.addWidget(QLabel("Billing Month (YYYY-MM):"))
        self.fee_month_input = QLineEdit(date.today().strftime("%Y-%m"))
        self.fee_month_input.setMaximumWidth(100)
        ctrl_box.addWidget(self.fee_month_input)

        filter_btn = QPushButton("Filter")
        filter_btn.clicked.connect(self.load_fees_table)
        ctrl_box.addWidget(filter_btn)

        gen_btn = QPushButton("Generate Monthly Transport Bills")
        gen_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 12px;")
        gen_btn.clicked.connect(self._generate_monthly_bills)
        ctrl_box.addWidget(gen_btn)

        ctrl_box.addStretch()

        fee_xls_btn = QPushButton("Export Fees (Excel)")
        fee_xls_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 10px;")
        fee_xls_btn.clicked.connect(self._export_fees_excel)
        ctrl_box.addWidget(fee_xls_btn)

        fee_pdf_btn = QPushButton("Fee Report (PDF)")
        fee_pdf_btn.setStyleSheet("background-color: #047857; color: white; font-weight: bold; padding: 6px 10px;")
        fee_pdf_btn.clicked.connect(self._export_fees_pdf)
        ctrl_box.addWidget(fee_pdf_btn)

        layout.addLayout(ctrl_box)

        self.fees_table = QTableWidget(0, 11)
        self.fees_table.setHorizontalHeaderLabels([
            "Month", "Commuter", "Route", "Amount", "Discount", "Paid", "Due", "Method", "Receipt No", "Status", "Actions"
        ])
        self.fees_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.fees_table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeToContents)
        self.fees_table.verticalHeader().setVisible(False)
        self.fees_table.setAlternatingRowColors(True)
        layout.addWidget(self.fees_table)

    def load_fees_table(self):
        month_filter = self.fee_month_input.text().strip() or None
        charges = TransportRepository.get_fee_charges(self.db_session, billing_month=month_filter)
        self.fees_table.setRowCount(len(charges))
        for row, ch in enumerate(charges):
            pax = ch.passenger
            name = TransportService._passenger_display_info(pax)[0] if pax else f"Passenger #{ch.passenger_id}"
            self.fees_table.setItem(row, 0, QTableWidgetItem(ch.billing_month))
            self.fees_table.setItem(row, 1, QTableWidgetItem(name))
            self.fees_table.setItem(row, 2, QTableWidgetItem(ch.route.route_code if ch.route else "-"))
            self.fees_table.setItem(row, 3, QTableWidgetItem(f"{float(ch.amount or 0.0):.2f}"))
            self.fees_table.setItem(row, 4, QTableWidgetItem(f"{float(ch.discount or 0.0):.2f}"))
            self.fees_table.setItem(row, 5, QTableWidgetItem(f"{float(ch.paid_amount or 0.0):.2f}"))
            self.fees_table.setItem(row, 6, QTableWidgetItem(f"{ch.balance_due:.2f}"))
            self.fees_table.setItem(row, 7, QTableWidgetItem(ch.payment_method or "-"))
            self.fees_table.setItem(row, 8, QTableWidgetItem(ch.receipt_no or "-"))

            it_st = QTableWidgetItem(ch.status)
            it_st.setTextAlignment(Qt.AlignCenter)
            it_st.setForeground(Qt.darkGreen if ch.status in ("Paid", "Waived") else Qt.red)
            self.fees_table.setItem(row, 9, it_st)

            act_w = QWidget()
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(4, 2, 4, 2)
            act_l.setSpacing(4)
            if ch.status in ("Pending", "Partial"):
                pay_btn = QPushButton("Collect")
                pay_btn.setStyleSheet("background-color: #059669; color: white; font-size: 11px; padding: 2px 8px;")
                pay_btn.clicked.connect(lambda _, charge=ch: self._collect_fee(charge))
                act_l.addWidget(pay_btn)

                waive_btn = QPushButton("Waive")
                waive_btn.setStyleSheet("background-color: #F1F5F9; color: #334155; font-size: 11px; padding: 2px 6px;")
                waive_btn.clicked.connect(lambda _, cid=ch.id: self._waive_fee(cid))
                act_l.addWidget(waive_btn)
            self.fees_table.setCellWidget(row, 10, act_w)

    def _generate_monthly_bills(self):
        month_str = self.fee_month_input.text().strip()
        if len(month_str) != 7 or "-" not in month_str:
            QMessageBox.warning(self, "Invalid Month", "Please enter billing month in YYYY-MM format.")
            return
        res = TransportRepository.generate_monthly_fees(self.db_session, billing_month=month_str)
        QMessageBox.information(
            self,
            "Billing Complete",
            f"Generated {res['created']} transport fee bill(s) for {month_str} ({res['skipped']} skipped).",
        )
        self.refresh_data()

    def _collect_fee(self, charge: TransportFeeCharge):
        dlg = TransportFeePaymentDialog(self.db_session, charge, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _waive_fee(self, charge_id: int):
        if QMessageBox.question(self, "Confirm Waiver", "Waive remaining transport fee balance?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            TransportRepository.waive_fee_charge(self.db_session, charge_id, remarks="Admin waiver")
            self.refresh_data()

    # ---------------- TAB 5: FUEL, MAINTENANCE & REMINDERS ----------------
    def _setup_fuel_maint_tab(self):
        layout = QVBoxLayout(self.tab_fuel_maint)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        ctrl = QHBoxLayout()
        add_fuel_btn = QPushButton("+ Record Fuel Refill")
        add_fuel_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 14px;")
        add_fuel_btn.clicked.connect(self._add_fuel_log)
        ctrl.addWidget(add_fuel_btn)

        add_maint_btn = QPushButton("+ Log Maintenance / Service")
        add_maint_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 14px;")
        add_maint_btn.clicked.connect(self._add_maintenance_log)
        ctrl.addWidget(add_maint_btn)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        splitter = QSplitter(Qt.Vertical)

        # Reminders table
        rem_box = QWidget()
        rem_l = QVBoxLayout(rem_box)
        rem_l.setContentsMargins(0, 0, 0, 0)
        rem_lbl = QLabel("Automated Vehicle Maintenance, Service & Expiry Reminders")
        rem_lbl.setStyleSheet("font-weight: bold; color: #991B1B;")
        rem_l.addWidget(rem_lbl)
        self.reminders_table = QTableWidget(0, 6)
        self.reminders_table.setHorizontalHeaderLabels(["Severity", "Vehicle", "Category", "Reminder", "Due Date / Odo", "Details"])
        self.reminders_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.reminders_table.verticalHeader().setVisible(False)
        rem_l.addWidget(self.reminders_table)
        splitter.addWidget(rem_box)

        # Fuel logs table
        fuel_box = QWidget()
        fuel_l = QVBoxLayout(fuel_box)
        fuel_l.setContentsMargins(0, 4, 0, 0)
        fuel_lbl = QLabel("Fuel Refills & Mileage Efficiency Logs")
        fuel_lbl.setStyleSheet("font-weight: bold; color: #0369A1;")
        fuel_l.addWidget(fuel_lbl)
        self.fuel_table = QTableWidget(0, 8)
        self.fuel_table.setHorizontalHeaderLabels(["Date", "Vehicle", "Fuel", "Liters", "Total Cost", "Odometer", "km/L", "Station"])
        self.fuel_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.fuel_table.verticalHeader().setVisible(False)
        fuel_l.addWidget(self.fuel_table)
        splitter.addWidget(fuel_box)

        # Maintenance logs table
        maint_box = QWidget()
        maint_l = QVBoxLayout(maint_box)
        maint_l.setContentsMargins(0, 4, 0, 0)
        maint_lbl = QLabel("Vehicle Maintenance & Repair History")
        maint_lbl.setStyleSheet("font-weight: bold; color: #047857;")
        maint_l.addWidget(maint_lbl)
        self.maint_table = QTableWidget(0, 8)
        self.maint_table.setHorizontalHeaderLabels(["Date", "Vehicle", "Service Type", "Workshop", "Cost", "Odometer", "Next Due Date", "Status"])
        self.maint_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.maint_table.verticalHeader().setVisible(False)
        maint_l.addWidget(self.maint_table)
        splitter.addWidget(maint_box)

        layout.addWidget(splitter)

    def load_fuel_maint_tables(self):
        reminders = TransportRepository.get_maintenance_reminders(self.db_session)
        self.reminders_table.setRowCount(len(reminders))
        for r_idx, rem in enumerate(reminders):
            it_sev = QTableWidgetItem(rem["severity"])
            it_sev.setForeground(Qt.red if rem["severity"] == "Overdue" else Qt.darkYellow)
            self.reminders_table.setItem(r_idx, 0, it_sev)
            self.reminders_table.setItem(r_idx, 1, QTableWidgetItem(rem["vehicle_number"]))
            self.reminders_table.setItem(r_idx, 2, QTableWidgetItem(rem["category"]))
            self.reminders_table.setItem(r_idx, 3, QTableWidgetItem(rem["title"]))
            due_str = rem["due_date"]
            if rem.get("due_odometer_km"):
                due_str += f" / {rem['due_odometer_km']:.0f} km"
            self.reminders_table.setItem(r_idx, 4, QTableWidgetItem(due_str))
            self.reminders_table.setItem(r_idx, 5, QTableWidgetItem(rem["details"]))

        fuel_logs = TransportRepository.get_fuel_logs(self.db_session)
        self.fuel_table.setRowCount(len(fuel_logs))
        for r_idx, fl in enumerate(fuel_logs):
            self.fuel_table.setItem(r_idx, 0, QTableWidgetItem(fl.fill_date))
            self.fuel_table.setItem(r_idx, 1, QTableWidgetItem(fl.vehicle.vehicle_number if fl.vehicle else "-"))
            self.fuel_table.setItem(r_idx, 2, QTableWidgetItem(fl.fuel_type))
            self.fuel_table.setItem(r_idx, 3, QTableWidgetItem(f"{fl.liters:.1f} L"))
            self.fuel_table.setItem(r_idx, 4, QTableWidgetItem(f"{float(fl.total_cost or 0.0):.2f}"))
            self.fuel_table.setItem(r_idx, 5, QTableWidgetItem(f"{fl.odometer_km:,.0f} km"))
            self.fuel_table.setItem(r_idx, 6, QTableWidgetItem(f"{fl.km_per_liter:.2f}" if fl.km_per_liter > 0 else "-"))
            self.fuel_table.setItem(r_idx, 7, QTableWidgetItem(fl.station_name or "-"))

        maint_logs = TransportRepository.get_maintenance_logs(self.db_session)
        self.maint_table.setRowCount(len(maint_logs))
        for r_idx, ml in enumerate(maint_logs):
            self.maint_table.setItem(r_idx, 0, QTableWidgetItem(ml.service_date))
            self.maint_table.setItem(r_idx, 1, QTableWidgetItem(ml.vehicle.vehicle_number if ml.vehicle else "-"))
            self.maint_table.setItem(r_idx, 2, QTableWidgetItem(ml.service_type))
            self.maint_table.setItem(r_idx, 3, QTableWidgetItem(ml.workshop_name or "-"))
            self.maint_table.setItem(r_idx, 4, QTableWidgetItem(f"{float(ml.cost or 0.0):.2f}"))
            self.maint_table.setItem(r_idx, 5, QTableWidgetItem(f"{ml.odometer_km:,.0f} km"))
            self.maint_table.setItem(r_idx, 6, QTableWidgetItem(ml.next_service_date or "-"))
            self.maint_table.setItem(r_idx, 7, QTableWidgetItem(ml.status))

    def _add_fuel_log(self):
        dlg = FuelLogDialog(self.db_session, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _add_maintenance_log(self):
        dlg = MaintenanceLogDialog(self.db_session, parent=self)
        if dlg.exec():
            self.refresh_data()

    # ---------------- TAB 6: INSURANCE & COMPLIANCE DOCUMENTS ----------------
    def _setup_compliance_tab(self):
        layout = QVBoxLayout(self.tab_compliance)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        ctrl = QHBoxLayout()
        add_ins_btn = QPushButton("+ Add Insurance Policy")
        add_ins_btn.setStyleSheet("background-color: #7C3AED; color: white; font-weight: bold; padding: 6px 14px;")
        add_ins_btn.clicked.connect(self._add_insurance)
        ctrl.addWidget(add_ins_btn)

        add_doc_btn = QPushButton("+ Upload / Register Vehicle Document")
        add_doc_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 14px;")
        add_doc_btn.clicked.connect(self._add_document)
        ctrl.addWidget(add_doc_btn)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        splitter = QSplitter(Qt.Vertical)

        ins_wrap = QWidget()
        ins_l = QVBoxLayout(ins_wrap)
        ins_l.setContentsMargins(0, 0, 0, 0)
        ins_lbl = QLabel("Vehicle Insurance Policies")
        ins_lbl.setStyleSheet("font-weight: bold; color: #5B21B6;")
        ins_l.addWidget(ins_lbl)
        self.insurance_table = QTableWidget(0, 8)
        self.insurance_table.setHorizontalHeaderLabels([
            "Vehicle", "Policy No", "Provider", "Coverage", "Start Date", "Expiry Date", "Premium", "Status"
        ])
        self.insurance_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.insurance_table.verticalHeader().setVisible(False)
        ins_l.addWidget(self.insurance_table)
        splitter.addWidget(ins_wrap)

        doc_wrap = QWidget()
        doc_l = QVBoxLayout(doc_wrap)
        doc_l.setContentsMargins(0, 4, 0, 0)
        doc_lbl = QLabel("Vehicle Compliance Document Vault (Registration, Fitness, Route Permit, Tax Token, License)")
        doc_lbl.setStyleSheet("font-weight: bold; color: #92400E;")
        doc_l.addWidget(doc_lbl)
        self.documents_table = QTableWidget(0, 7)
        self.documents_table.setHorizontalHeaderLabels([
            "Vehicle", "Document Type", "Document No", "Issuer", "Issue Date", "Expiry Date", "Status"
        ])
        self.documents_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.documents_table.verticalHeader().setVisible(False)
        doc_l.addWidget(self.documents_table)
        splitter.addWidget(doc_wrap)

        layout.addWidget(splitter)

    def load_compliance_tables(self):
        ins_list = TransportRepository.get_insurances(self.db_session)
        self.insurance_table.setRowCount(len(ins_list))
        for r_idx, ins in enumerate(ins_list):
            self.insurance_table.setItem(r_idx, 0, QTableWidgetItem(ins.vehicle.vehicle_number if ins.vehicle else "-"))
            self.insurance_table.setItem(r_idx, 1, QTableWidgetItem(ins.policy_number))
            self.insurance_table.setItem(r_idx, 2, QTableWidgetItem(ins.provider))
            self.insurance_table.setItem(r_idx, 3, QTableWidgetItem(ins.coverage_type))
            self.insurance_table.setItem(r_idx, 4, QTableWidgetItem(ins.start_date))
            self.insurance_table.setItem(r_idx, 5, QTableWidgetItem(ins.expiry_date))
            self.insurance_table.setItem(r_idx, 6, QTableWidgetItem(f"{float(ins.premium_amount or 0.0):.2f}"))
            self.insurance_table.setItem(r_idx, 7, QTableWidgetItem(ins.status))

        docs = TransportRepository.get_documents(self.db_session)
        self.documents_table.setRowCount(len(docs))
        for r_idx, doc in enumerate(docs):
            self.documents_table.setItem(r_idx, 0, QTableWidgetItem(doc.vehicle.vehicle_number if doc.vehicle else "-"))
            self.documents_table.setItem(r_idx, 1, QTableWidgetItem(doc.document_type))
            self.documents_table.setItem(r_idx, 2, QTableWidgetItem(doc.document_number or "-"))
            self.documents_table.setItem(r_idx, 3, QTableWidgetItem(doc.issuing_authority or "-"))
            self.documents_table.setItem(r_idx, 4, QTableWidgetItem(doc.issue_date or "-"))
            self.documents_table.setItem(r_idx, 5, QTableWidgetItem(doc.expiry_date or "-"))
            self.documents_table.setItem(r_idx, 6, QTableWidgetItem(doc.status))

    def _add_insurance(self):
        dlg = InsuranceDialog(self.db_session, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _add_document(self):
        dlg = VehicleDocumentDialog(self.db_session, parent=self)
        if dlg.exec():
            self.refresh_data()

    # ---------------- TAB 7: GPS INTEGRATION HUB (OPTIONAL) ----------------
    def _setup_gps_tab(self):
        layout = QVBoxLayout(self.tab_gps)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        info_lbl = QLabel(
            "Hardware-Optional GPS Architecture: Fleet operations work 100% without GPS hardware. "
            "Use manual check-ins below or connect SIM_GPS / OBD-II / Webhook / MQTT adapters anytime."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("background-color: #EFF6FF; border: 1px solid #BFDBFE; padding: 8px; border-radius: 4px; color: #1E3A8A;")
        layout.addWidget(info_lbl)

        ctrl = QHBoxLayout()
        checkin_btn = QPushButton("+ Manual Location Check-In (No Hardware)")
        checkin_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 14px;")
        checkin_btn.clicked.connect(self._manual_gps_checkin)
        ctrl.addWidget(checkin_btn)

        reg_dev_btn = QPushButton("+ Register Optional GPS Device Adapter")
        reg_dev_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 14px;")
        reg_dev_btn.clicked.connect(self._register_gps_device)
        ctrl.addWidget(reg_dev_btn)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        splitter = QSplitter(Qt.Vertical)

        pos_wrap = QWidget()
        pos_l = QVBoxLayout(pos_wrap)
        pos_l.setContentsMargins(0, 0, 0, 0)
        pos_l.addWidget(QLabel("Live / Manual Vehicle Telemetry Snapshot"))
        self.gps_positions_table = QTableWidget(0, 7)
        self.gps_positions_table.setHorizontalHeaderLabels([
            "Vehicle No", "Type", "GPS Mode", "Last Known Location", "Coordinates", "Speed", "Last Updated"
        ])
        self.gps_positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.gps_positions_table.verticalHeader().setVisible(False)
        pos_l.addWidget(self.gps_positions_table)
        splitter.addWidget(pos_wrap)

        dev_wrap = QWidget()
        dev_l = QVBoxLayout(dev_wrap)
        dev_l.setContentsMargins(0, 4, 0, 0)
        dev_l.addWidget(QLabel("Registered Optional GPS Adapters"))
        self.gps_devices_table = QTableWidget(0, 6)
        self.gps_devices_table.setHorizontalHeaderLabels([
            "Device Code", "Bound Vehicle", "Provider Adapter", "IMEI / Serial", "Enabled (Mandatory=No)", "Status"
        ])
        self.gps_devices_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.gps_devices_table.verticalHeader().setVisible(False)
        dev_l.addWidget(self.gps_devices_table)
        splitter.addWidget(dev_wrap)

        layout.addWidget(splitter)

    def load_gps_tables(self):
        snapshots = TransportRepository.get_latest_vehicle_positions(self.db_session)
        self.gps_positions_table.setRowCount(len(snapshots))
        for r_idx, s in enumerate(snapshots):
            self.gps_positions_table.setItem(r_idx, 0, QTableWidgetItem(s["vehicle_number"]))
            self.gps_positions_table.setItem(r_idx, 1, QTableWidgetItem(s["vehicle_type"]))
            self.gps_positions_table.setItem(r_idx, 2, QTableWidgetItem(s["gps_mode"]))
            self.gps_positions_table.setItem(r_idx, 3, QTableWidgetItem(s["location_label"] or "No check-in yet"))
            coords = f"{s['latitude']:.5f}, {s['longitude']:.5f}" if s["latitude"] is not None else "-"
            self.gps_positions_table.setItem(r_idx, 4, QTableWidgetItem(coords))
            spd = f"{s['speed_kmh']:.1f} km/h" if s["speed_kmh"] is not None else "-"
            self.gps_positions_table.setItem(r_idx, 5, QTableWidgetItem(spd))
            self.gps_positions_table.setItem(r_idx, 6, QTableWidgetItem(s["last_ping_at"] or "-"))

        devices = TransportRepository.get_gps_devices(self.db_session)
        self.gps_devices_table.setRowCount(len(devices))
        for r_idx, d in enumerate(devices):
            self.gps_devices_table.setItem(r_idx, 0, QTableWidgetItem(d.device_code))
            self.gps_devices_table.setItem(r_idx, 1, QTableWidgetItem(d.vehicle.vehicle_number if d.vehicle else "Unassigned"))
            self.gps_devices_table.setItem(r_idx, 2, QTableWidgetItem(d.provider_type))
            self.gps_devices_table.setItem(r_idx, 3, QTableWidgetItem(d.imei_or_serial or "-"))
            self.gps_devices_table.setItem(r_idx, 4, QTableWidgetItem("Yes" if d.is_enabled else "No (Optional)"))
            self.gps_devices_table.setItem(r_idx, 5, QTableWidgetItem(d.status))

    def _manual_gps_checkin(self):
        dlg = ManualGPSCheckinDialog(self.db_session, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _register_gps_device(self):
        dlg = GPSDeviceConfigDialog(self.db_session, parent=self)
        if dlg.exec():
            self.refresh_data()

    # ---------------- REFRESH & EXPORTS ----------------
    def refresh_data(self):
        stats = TransportRepository.get_transport_stats(self.db_session)
        self.lbl_vehicles.setText(str(stats["total_vehicles"]))
        self.lbl_routes.setText(str(stats["total_routes"]))
        self.lbl_capacity.setText(str(stats["total_capacity"]))
        self.lbl_passengers.setText(str(stats["allocated_passengers"]))
        self.lbl_revenue.setText(f"${stats['monthly_revenue']:.2f}")
        spend = stats["total_fuel_cost"] + stats["total_maintenance_cost"]
        self.lbl_fuel_maint.setText(f"${spend:.2f}")
        self.lbl_alerts.setText(f"{stats['overdue_reminders']} / {stats['active_reminders']}")

        if stats["overdue_reminders"] > 0:
            self.reminder_banner.setText(
                f"ATTENTION: {stats['overdue_reminders']} Overdue and {stats['active_reminders']} Total Maintenance/Insurance/Document Reminders require action."
            )
            self.reminder_banner.setStyleSheet(
                "background-color: #FEF2F2; border: 1px solid #FCA5A5; border-radius: 5px; "
                "padding: 6px 12px; color: #991B1B; font-weight: bold;"
            )
        elif stats["active_reminders"] > 0:
            self.reminder_banner.setText(
                f"Upcoming Fleet Notices: {stats['active_reminders']} service or expiry item(s) due soon."
            )
            self.reminder_banner.setStyleSheet(
                "background-color: #FFFBEB; border: 1px solid #FCD34D; border-radius: 5px; "
                "padding: 6px 12px; color: #92400E; font-weight: 600;"
            )
        else:
            self.reminder_banner.setText("Fleet Compliance Status: No overdue or upcoming maintenance/document reminders.")
            self.reminder_banner.setStyleSheet(
                "background-color: #ECFDF5; border: 1px solid #6EE7B7; border-radius: 5px; "
                "padding: 6px 12px; color: #065F46; font-weight: 600;"
            )

        routes = TransportRepository.get_routes(self.db_session)
        curr_r_id = self.route_filter_combo.currentData()
        self.route_filter_combo.blockSignals(True)
        self.route_filter_combo.clear()
        self.route_filter_combo.addItem("All Transit Routes", None)
        for r in routes:
            self.route_filter_combo.addItem(f"{r.route_code}: {r.route_name}", r.id)
        if curr_r_id:
            idx = self.route_filter_combo.findData(curr_r_id)
            if idx >= 0:
                self.route_filter_combo.setCurrentIndex(idx)
        self.route_filter_combo.blockSignals(False)

        self.load_vehicles_table()
        self.load_routes_table()
        self.load_passengers_table()
        self.load_fees_table()
        self.load_fuel_maint_tables()
        self.load_compliance_tables()
        self.load_gps_tables()

    def _export_manifest_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Route Manifest Excel", "Transport_Passenger_Manifest.xlsx", "Excel Files (*.xlsx)")
        if file_path:
            try:
                TransportService.export_passengers_excel(self.db_session, self.route_filter_combo.currentData(), file_path)
                QMessageBox.information(self, "Export Complete", f"Passenger manifest exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export manifest:\n{str(e)}")

    def _export_fleet_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Fleet Operations Workbook", "Transport_Fleet_Operations.xlsx", "Excel Files (*.xlsx)")
        if file_path:
            try:
                TransportService.export_fleet_operations_excel(self.db_session, file_path)
                QMessageBox.information(self, "Export Complete", f"Fleet workbook exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export fleet workbook:\n{str(e)}")

    def _generate_fleet_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Fleet & Maintenance Report PDF", "Fleet_Maintenance_Fuel_Report.pdf", "PDF Files (*.pdf)")
        if file_path:
            try:
                vehicles = TransportRepository.get_vehicles(self.db_session)
                fuel_logs = TransportRepository.get_fuel_logs(self.db_session)
                maint_logs = TransportRepository.get_maintenance_logs(self.db_session)
                reminders = TransportRepository.get_maintenance_reminders(self.db_session)
                school = self.db_session.query(SchoolSetting).first()
                TransportReportsPDFGenerator.generate_maintenance_fuel_report(
                    vehicles, fuel_logs, maint_logs, reminders, school, file_path
                )
                QMessageBox.information(self, "Report Generated", f"Fleet & Maintenance PDF saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Report Error", f"Failed to generate fleet PDF:\n{str(e)}")

    def _export_fees_excel(self):
        month_filter = self.fee_month_input.text().strip() or None
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Transport Fees Excel", "Transport_Fees_Ledger.xlsx", "Excel Files (*.xlsx)")
        if file_path:
            try:
                TransportService.export_transport_fees_excel(self.db_session, month_filter, file_path)
                QMessageBox.information(self, "Export Complete", f"Transport fees exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export fees:\n{str(e)}")

    def _export_fees_pdf(self):
        month_filter = self.fee_month_input.text().strip() or None
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Transport Fee Report PDF", "Transport_Fee_Report.pdf", "PDF Files (*.pdf)")
        if file_path:
            try:
                charges = TransportRepository.get_fee_charges(self.db_session, billing_month=month_filter)
                school = self.db_session.query(SchoolSetting).first()
                TransportReportsPDFGenerator.generate_fee_collection_report(charges, month_filter, school, file_path)
                QMessageBox.information(self, "Report Generated", f"Transport fee report PDF saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Report Error", f"Failed to generate fee report:\n{str(e)}")

    def _generate_route_manifest_pdf(self):
        route_id = self.route_filter_combo.currentData()
        route = (
            TransportRepository.get_route_by_id(self.db_session, route_id)
            if route_id
            else self.db_session.query(TransportRoute).first()
        )
        if not route:
            QMessageBox.warning(self, "No Route", "Please create or select an active route first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Route Roll Sheet", f"Route_{route.route_code}_Manifest.pdf", "PDF Files (*.pdf)")
        if file_path:
            try:
                passengers = TransportRepository.get_passengers(self.db_session, route_id=route.id, status="Active")
                school = self.db_session.query(SchoolSetting).first()
                RouteManifestPDFGenerator.generate_manifest(route, passengers, school, file_path)
                QMessageBox.information(self, "Report Generated", f"Route Roll Sheet PDF saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Report Error", f"Failed to generate roll sheet:\n{str(e)}")
