"""
EduManage Pro - Transport & Fleet Management Page
Phase 11: PySide6 4-Tab Interface (Fleet Vehicles, Routes & Stops, Commuter Allocations & Transit Passes)
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
from app.models.transport import Vehicle, TransportRoute, TransportStop, TransportPassenger
from app.models.school import SchoolSetting
from app.repositories.transport_repository import TransportRepository
from app.services.transport_service import TransportService
from app.reports.bus_pass_pdf import BusPassGenerator
from app.reports.route_manifest_pdf import RouteManifestPDFGenerator
from app.ui.dialogs.vehicle_form_dialog import VehicleFormDialog
from app.ui.dialogs.route_form_dialog import RouteFormDialog
from app.ui.dialogs.assign_transport_dialog import AssignTransportDialog
from app.database.connection import SessionLocal


class TransportPage(QWidget):
    """Main Transport & Fleet Management page for vehicles, routes, passenger allocations & passes."""

    def __init__(self, parent=None, db_session: Optional[Session] = None, session_manager=None):
        super().__init__(parent)
        self.session_manager = session_manager
        self.db_session = db_session if db_session is not None else SessionLocal()

        # Seed defaults if first run
        TransportService.seed_default_transport_data(self.db_session)

        self._setup_ui()
        self.refresh_data()

    def refresh_all(self):
        """Standard lifecycle hook called on navigation."""
        self.refresh_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header Title & Actions
        title_box = QHBoxLayout()
        title_label = QLabel("Transport & Fleet Management")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        title_box.addWidget(title_label)
        title_box.addStretch()

        export_excel_btn = QPushButton("📊 Export Manifest (Excel)")
        export_excel_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        export_excel_btn.clicked.connect(self._export_manifest_excel)
        title_box.addWidget(export_excel_btn)

        manifest_pdf_btn = QPushButton("📑 Route Roll Sheet (PDF)")
        manifest_pdf_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        manifest_pdf_btn.clicked.connect(self._generate_route_manifest_pdf)
        title_box.addWidget(manifest_pdf_btn)

        main_layout.addLayout(title_box)

        # 2. KPI Metrics Bar
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(10)
        self.lbl_vehicles = self._create_kpi_card("Fleet Vehicles", "0", "#0284C7")
        self.lbl_routes = self._create_kpi_card("Active Routes", "0", "#B45309")
        self.lbl_capacity = self._create_kpi_card("Total Capacity", "0", "#475569")
        self.lbl_passengers = self._create_kpi_card("Allocated Commuters", "0", "#059669")
        self.lbl_available = self._create_kpi_card("Available Seats", "0", "#6366F1")
        self.lbl_revenue = self._create_kpi_card("Monthly Revenue", "$ 0.00", "#10B981")
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
                color: #B45309;
                border-bottom: 2px solid #B45309;
            }
        """)

        # Tab 1: Fleet Vehicles
        self.tab_vehicles = QWidget()
        self._setup_vehicles_tab()
        self.tabs.addTab(self.tab_vehicles, "🚌 Fleet Vehicles")

        # Tab 2: Routes & Stops
        self.tab_routes = QWidget()
        self._setup_routes_tab()
        self.tabs.addTab(self.tab_routes, "🗺️ Transit Routes & Stops")

        # Tab 3: Commuter Allocations
        self.tab_passengers = QWidget()
        self._setup_passengers_tab()
        self.tabs.addTab(self.tab_passengers, "👥 Passenger Seat Allocations")

        # Tab 4: Bus Transit Passes
        self.tab_passes = QWidget()
        self._setup_passes_tab()
        self.tabs.addTab(self.tab_passes, "🪪 School Bus Transit Passes")

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

    # ---------------- TAB 1: FLEET VEHICLES ----------------
    def _setup_vehicles_tab(self):
        layout = QVBoxLayout(self.tab_vehicles)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        ctrl_box = QHBoxLayout()
        ctrl_box.addWidget(QLabel("Registered School Buses & Fleet"))
        ctrl_box.addStretch()

        add_v_btn = QPushButton("+ Register New Vehicle")
        add_v_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        add_v_btn.clicked.connect(self._add_vehicle)
        ctrl_box.addWidget(add_v_btn)

        layout.addLayout(ctrl_box)

        self.vehicles_table = QTableWidget()
        headers = [
            "Plate Number", "Vehicle Model", "Type", "Capacity",
            "Driver Name", "Driver Phone", "Helper / Conductor", "Status", "Actions"
        ]
        self.vehicles_table.setColumnCount(len(headers))
        self.vehicles_table.setHorizontalHeaderLabels(headers)
        self.vehicles_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.vehicles_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.vehicles_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.vehicles_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.vehicles_table.verticalHeader().setVisible(False)
        self.vehicles_table.setAlternatingRowColors(True)

        layout.addWidget(self.vehicles_table)

    def load_vehicles_table(self):
        vehicles = TransportRepository.get_vehicles(self.db_session)
        self.vehicles_table.setRowCount(len(vehicles))

        for row, v in enumerate(vehicles):
            it_num = QTableWidgetItem(v.vehicle_number)
            it_num.setTextAlignment(Qt.AlignCenter)
            self.vehicles_table.setItem(row, 0, it_num)

            self.vehicles_table.setItem(row, 1, QTableWidgetItem(v.vehicle_model))

            it_t = QTableWidgetItem(v.vehicle_type)
            it_t.setTextAlignment(Qt.AlignCenter)
            self.vehicles_table.setItem(row, 2, it_t)

            booked = len([p for p in v.passengers if p.status == "Active"]) if v.passengers else 0
            it_cap = QTableWidgetItem(f"{booked} / {v.seating_capacity} seats")
            it_cap.setTextAlignment(Qt.AlignCenter)
            self.vehicles_table.setItem(row, 3, it_cap)

            self.vehicles_table.setItem(row, 4, QTableWidgetItem(v.driver_name))

            it_dp = QTableWidgetItem(v.driver_phone)
            it_dp.setTextAlignment(Qt.AlignCenter)
            self.vehicles_table.setItem(row, 5, it_dp)

            h_text = f"{v.helper_name or '-'} ({v.helper_phone or '-'})" if v.helper_name else "-"
            self.vehicles_table.setItem(row, 6, QTableWidgetItem(h_text))

            it_st = QTableWidgetItem(v.status)
            it_st.setTextAlignment(Qt.AlignCenter)
            if v.status == "Active":
                it_st.setForeground(Qt.darkGreen)
            else:
                it_st.setForeground(Qt.red)
            self.vehicles_table.setItem(row, 7, it_st)

            # Actions
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)
            act_layout.setSpacing(4)

            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet("background-color: #F1F5F9; color: #1E293B; font-size: 11px; padding: 2px 8px; border-radius: 3px;")
            edit_btn.clicked.connect(lambda _, veh=v: self._edit_vehicle(veh))
            act_layout.addWidget(edit_btn)

            self.vehicles_table.setCellWidget(row, 8, act_widget)

    def _add_vehicle(self):
        dlg = VehicleFormDialog(self.db_session, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _edit_vehicle(self, v: Vehicle):
        dlg = VehicleFormDialog(self.db_session, vehicle=v, parent=self)
        if dlg.exec():
            self.refresh_data()

    # ---------------- TAB 2: ROUTES & STOPS ----------------
    def _setup_routes_tab(self):
        layout = QVBoxLayout(self.tab_routes)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        ctrl_box = QHBoxLayout()
        ctrl_box.addWidget(QLabel("School Bus Transit Routes"))
        ctrl_box.addStretch()

        add_r_btn = QPushButton("+ Create New Route")
        add_r_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        add_r_btn.clicked.connect(self._add_route)
        ctrl_box.addWidget(add_r_btn)

        layout.addLayout(ctrl_box)

        self.routes_table = QTableWidget()
        headers = [
            "Route Code", "Route Name", "Origin Point", "Destination Point",
            "Distance", "Monthly Fare ($)", "Assigned Vehicle", "Pickup / Drop", "Stops", "Actions"
        ]
        self.routes_table.setColumnCount(len(headers))
        self.routes_table.setHorizontalHeaderLabels(headers)
        self.routes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.routes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.routes_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.routes_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.routes_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.routes_table.verticalHeader().setVisible(False)
        self.routes_table.setAlternatingRowColors(True)

        layout.addWidget(self.routes_table)

    def load_routes_table(self):
        routes = TransportRepository.get_routes(self.db_session)
        self.routes_table.setRowCount(len(routes))

        for row, r in enumerate(routes):
            it_code = QTableWidgetItem(r.route_code)
            it_code.setTextAlignment(Qt.AlignCenter)
            self.routes_table.setItem(row, 0, it_code)

            self.routes_table.setItem(row, 1, QTableWidgetItem(r.route_name))
            self.routes_table.setItem(row, 2, QTableWidgetItem(r.start_point))
            self.routes_table.setItem(row, 3, QTableWidgetItem(r.end_point))

            it_dist = QTableWidgetItem(f"{r.distance_km:.1f} km")
            it_dist.setTextAlignment(Qt.AlignCenter)
            self.routes_table.setItem(row, 4, it_dist)

            it_fare = QTableWidgetItem(f"${r.monthly_fee:.2f}")
            it_fare.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.routes_table.setItem(row, 5, it_fare)

            v_info = r.vehicle.vehicle_number if r.vehicle else "Unassigned"
            self.routes_table.setItem(row, 6, QTableWidgetItem(v_info))

            time_info = f"{r.pickup_time or '-'} / {r.drop_time or '-'}"
            it_tm = QTableWidgetItem(time_info)
            it_tm.setTextAlignment(Qt.AlignCenter)
            self.routes_table.setItem(row, 7, it_tm)

            stop_count = len(r.stops) if r.stops else 0
            it_sc = QTableWidgetItem(f"{stop_count} stops")
            it_sc.setTextAlignment(Qt.AlignCenter)
            self.routes_table.setItem(row, 8, it_sc)

            # Actions
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)

            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet("background-color: #F1F5F9; color: #1E293B; font-size: 11px; padding: 2px 8px; border-radius: 3px;")
            edit_btn.clicked.connect(lambda _, rt=r: self._edit_route(rt))
            act_layout.addWidget(edit_btn)

            self.routes_table.setCellWidget(row, 9, act_widget)

    def _add_route(self):
        dlg = RouteFormDialog(self.db_session, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _edit_route(self, r: TransportRoute):
        dlg = RouteFormDialog(self.db_session, route=r, parent=self)
        if dlg.exec():
            self.refresh_data()

    # ---------------- TAB 3: COMMUTER ALLOCATIONS ----------------
    def _setup_passengers_tab(self):
        layout = QVBoxLayout(self.tab_passengers)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        ctrl_box = QHBoxLayout()
        ctrl_box.addWidget(QLabel("Route Filter:"))
        self.route_filter_combo = QComboBox()
        self.route_filter_combo.addItem("All Transit Routes", None)
        self.route_filter_combo.currentIndexChanged.connect(self.load_passengers_table)
        ctrl_box.addWidget(self.route_filter_combo)
        ctrl_box.addStretch()

        assign_btn = QPushButton("➕ Allocate Commuter (Student / Staff)")
        assign_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        assign_btn.clicked.connect(self._allocate_commuter)
        ctrl_box.addWidget(assign_btn)

        layout.addLayout(ctrl_box)

        self.passengers_table = QTableWidget()
        headers = [
            "Pass ID", "Commuter Name", "Type", "Class / Designation",
            "Route Code & Name", "Boarding Stop", "Bus Plate", "Seat No", "Monthly Fee", "Status", "Actions"
        ]
        self.passengers_table.setColumnCount(len(headers))
        self.passengers_table.setHorizontalHeaderLabels(headers)
        self.passengers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.passengers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.passengers_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.passengers_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.passengers_table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeToContents)
        self.passengers_table.verticalHeader().setVisible(False)
        self.passengers_table.setAlternatingRowColors(True)

        layout.addWidget(self.passengers_table)

    def load_passengers_table(self):
        r_id = self.route_filter_combo.currentData()
        passengers = TransportRepository.get_passengers(self.db_session, route_id=r_id)
        self.passengers_table.setRowCount(len(passengers))

        for row, p in enumerate(passengers):
            it_id = QTableWidgetItem(f"#{p.id:04d}")
            it_id.setTextAlignment(Qt.AlignCenter)
            self.passengers_table.setItem(row, 0, it_id)

            name = "Unknown"
            affil = "-"
            if p.student:
                name = p.student.full_name
                affil = f"Class {p.student.school_class.name if p.student.school_class else '-'} (Roll {p.student.roll_number})"
            elif p.teacher:
                name = p.teacher.full_name
                affil = p.teacher.designation or "Faculty"

            self.passengers_table.setItem(row, 1, QTableWidgetItem(name))

            it_type = QTableWidgetItem(p.passenger_type)
            it_type.setTextAlignment(Qt.AlignCenter)
            self.passengers_table.setItem(row, 2, it_type)

            self.passengers_table.setItem(row, 3, QTableWidgetItem(affil))

            r_text = f"{p.route.route_code}: {p.route.route_name}" if p.route else "-"
            self.passengers_table.setItem(row, 4, QTableWidgetItem(r_text))

            stop_text = p.stop.stop_name if p.stop else "Campus Gate"
            self.passengers_table.setItem(row, 5, QTableWidgetItem(stop_text))

            v_text = p.vehicle.vehicle_number if p.vehicle else "-"
            it_v = QTableWidgetItem(v_text)
            it_v.setTextAlignment(Qt.AlignCenter)
            self.passengers_table.setItem(row, 6, it_v)

            it_seat = QTableWidgetItem(p.seat_number or "Assigned")
            it_seat.setTextAlignment(Qt.AlignCenter)
            self.passengers_table.setItem(row, 7, it_seat)

            it_fare = QTableWidgetItem(f"${p.monthly_fare:.2f}")
            it_fare.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.passengers_table.setItem(row, 8, it_fare)

            it_st = QTableWidgetItem(p.status)
            it_st.setTextAlignment(Qt.AlignCenter)
            if p.status == "Active":
                it_st.setForeground(Qt.darkGreen)
            else:
                it_st.setForeground(Qt.red)
            self.passengers_table.setItem(row, 9, it_st)

            # Actions
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)

            if p.status == "Active":
                cancel_btn = QPushButton("Cancel")
                cancel_btn.setStyleSheet("background-color: #FEE2E2; color: #DC2626; font-size: 11px; padding: 2px 6px; border-radius: 3px;")
                cancel_btn.clicked.connect(lambda _, pid=p.id: self._cancel_allocation(pid))
                act_layout.addWidget(cancel_btn)

            self.passengers_table.setCellWidget(row, 10, act_widget)

    def _allocate_commuter(self):
        dlg = AssignTransportDialog(self.db_session, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _cancel_allocation(self, passenger_id: int):
        if QMessageBox.question(self, "Confirm Cancellation", "Are you sure you want to cancel this transport seat allocation?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            TransportRepository.cancel_allocation(self.db_session, passenger_id, reason="User cancellation")
            self.refresh_data()

    # ---------------- TAB 4: BUS TRANSIT PASSES ----------------
    def _setup_passes_tab(self):
        layout = QVBoxLayout(self.tab_passes)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        ctrl_box = QHBoxLayout()
        ctrl_box.addWidget(QLabel("School Bus Transit Pass Directory"))
        ctrl_box.addStretch()
        layout.addLayout(ctrl_box)

        self.passes_table = QTableWidget()
        headers = ["Pass No", "Commuter Name", "Type", "Route Code", "Bus Plate", "Boarding Stop", "Seat No", "Actions"]
        self.passes_table.setColumnCount(len(headers))
        self.passes_table.setHorizontalHeaderLabels(headers)
        self.passes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.passes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.passes_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.passes_table.verticalHeader().setVisible(False)
        self.passes_table.setAlternatingRowColors(True)

        layout.addWidget(self.passes_table)

    def load_passes_table(self):
        passengers = TransportRepository.get_passengers(self.db_session, status="Active")
        self.passes_table.setRowCount(len(passengers))

        for row, p in enumerate(passengers):
            it_id = QTableWidgetItem(f"PASS-{p.id:04d}")
            it_id.setTextAlignment(Qt.AlignCenter)
            self.passes_table.setItem(row, 0, it_id)

            name = p.student.full_name if p.student else (p.teacher.full_name if p.teacher else "Commuter")
            self.passes_table.setItem(row, 1, QTableWidgetItem(name))

            it_type = QTableWidgetItem(p.passenger_type)
            it_type.setTextAlignment(Qt.AlignCenter)
            self.passes_table.setItem(row, 2, it_type)

            r_code = p.route.route_code if p.route else "-"
            it_rc = QTableWidgetItem(r_code)
            it_rc.setTextAlignment(Qt.AlignCenter)
            self.passes_table.setItem(row, 3, it_rc)

            v_no = p.vehicle.vehicle_number if p.vehicle else "-"
            it_vn = QTableWidgetItem(v_no)
            it_vn.setTextAlignment(Qt.AlignCenter)
            self.passes_table.setItem(row, 4, it_vn)

            stop_name = p.stop.stop_name if p.stop else "Campus Gate"
            self.passes_table.setItem(row, 5, QTableWidgetItem(stop_name))

            seat_no = p.seat_number or "Assigned"
            it_st = QTableWidgetItem(seat_no)
            it_st.setTextAlignment(Qt.AlignCenter)
            self.passes_table.setItem(row, 6, it_st)

            # Actions
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)

            card_btn = QPushButton("Print CR80 Bus Pass (PDF)")
            card_btn.setStyleSheet("background-color: #B45309; color: white; font-size: 11px; padding: 2px 8px; border-radius: 3px;")
            card_btn.clicked.connect(lambda _, pass_obj=p: self._print_bus_pass(pass_obj))
            act_layout.addWidget(card_btn)

            self.passes_table.setCellWidget(row, 7, act_widget)

    def _print_bus_pass(self, passenger: TransportPassenger):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save School Bus Pass PDF",
            f"Bus_Pass_{passenger.id}.pdf",
            "PDF Files (*.pdf)"
        )
        if file_path:
            try:
                school = self.db_session.query(SchoolSetting).first()
                BusPassGenerator.generate_single_pass(passenger, school, file_path)
                QMessageBox.information(self, "Bus Pass Generated", f"Printable CR80 Bus Pass saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "PDF Error", f"Failed to generate pass:\n{str(e)}")

    # ---------------- REFRESH & EXPORTS ----------------
    def refresh_data(self):
        stats = TransportRepository.get_transport_stats(self.db_session)
        self.lbl_vehicles.setText(str(stats["total_vehicles"]))
        self.lbl_routes.setText(str(stats["total_routes"]))
        self.lbl_capacity.setText(str(stats["total_capacity"]))
        self.lbl_passengers.setText(str(stats["allocated_passengers"]))
        self.lbl_available.setText(str(stats["available_seats"]))
        self.lbl_revenue.setText(f"${stats['monthly_revenue']:.2f}")

        # Update Route filter combo
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
        self.load_passes_table()

    def _export_manifest_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Route Manifest Excel",
            "Transport_Passenger_Manifest.xlsx",
            "Excel Files (*.xlsx)"
        )
        if file_path:
            try:
                route_id = self.route_filter_combo.currentData()
                TransportService.export_passengers_excel(self.db_session, route_id, file_path)
                QMessageBox.information(self, "Export Complete", f"Passenger manifest successfully exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export manifest:\n{str(e)}")

    def _generate_route_manifest_pdf(self):
        route_id = self.route_filter_combo.currentData()
        if not route_id:
            route = self.db_session.query(TransportRoute).first()
        else:
            route = TransportRepository.get_route_by_id(self.db_session, route_id)

        if not route:
            QMessageBox.warning(self, "No Route", "Please select an active route to generate a roll sheet.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Route Conductor Roll Sheet",
            f"Route_{route.route_code}_Manifest.pdf",
            "PDF Files (*.pdf)"
        )
        if file_path:
            try:
                passengers = TransportRepository.get_passengers(self.db_session, route_id=route.id, status="Active")
                school = self.db_session.query(SchoolSetting).first()
                RouteManifestPDFGenerator.generate_manifest(route, passengers, school, file_path)
                QMessageBox.information(self, "Report Generated", f"Route Roll Sheet PDF saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Report Error", f"Failed to generate roll sheet:\n{str(e)}")
