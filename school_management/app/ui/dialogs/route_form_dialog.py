"""
EduManage Pro - Route Form Dialog
PySide6 Modal for Route Configuration, Vehicle Assignment & Pickup Points Editor
"""

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QDoubleSpinBox, QPushButton, QLabel, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox
)
from sqlalchemy.orm import Session

from app.models.transport import TransportRoute, Vehicle
from app.repositories.transport_repository import TransportRepository


class RouteFormDialog(QDialog):
    """Dialog for creating or updating school transit routes and pickup points."""

    def __init__(self, db_session: Session, route: Optional[TransportRoute] = None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.route = route

        self.setWindowTitle("Edit Transport Route & Pickup Points" if route else "Create New Transport Route")
        self.setMinimumSize(720, 620)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title_lbl = QLabel("Route Configuration & Pickup Points")
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #B45309;")
        layout.addWidget(title_lbl)

        form = QFormLayout()
        form.setSpacing(8)

        code_box = QHBoxLayout()
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g. RT-04")
        code_box.addWidget(self.code_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Route Name (Origin - Destination)")
        code_box.addWidget(self.name_input)
        form.addRow("Route Code & Title *:", code_box)

        points_box = QHBoxLayout()
        self.start_input = QLineEdit()
        self.start_input.setPlaceholderText("Start Point")
        points_box.addWidget(self.start_input)

        self.end_input = QLineEdit("School Main Campus")
        points_box.addWidget(self.end_input)
        form.addRow("Origin & Destination *:", points_box)

        num_box = QHBoxLayout()
        self.distance_spin = QDoubleSpinBox()
        self.distance_spin.setRange(0.5, 250.0)
        self.distance_spin.setValue(12.0)
        self.distance_spin.setSuffix(" km")
        num_box.addWidget(self.distance_spin)

        self.fee_spin = QDoubleSpinBox()
        self.fee_spin.setRange(0.0, 50000.0)
        self.fee_spin.setValue(2500.0)
        num_box.addWidget(QLabel("Default Monthly Fee:"))
        num_box.addWidget(self.fee_spin)
        form.addRow("Distance & Fee:", num_box)

        self.vehicle_combo = QComboBox()
        self.vehicle_combo.addItem("None (Unassigned)", None)
        vehicles = TransportRepository.get_vehicles(self.db_session)
        for v in vehicles:
            self.vehicle_combo.addItem(f"{v.vehicle_number} [{v.vehicle_type}] ({v.seating_capacity} seats - {v.status})", v.id)
        form.addRow("Assigned Vehicle:", self.vehicle_combo)

        time_box = QHBoxLayout()
        self.pickup_time_input = QLineEdit("06:45 AM")
        time_box.addWidget(self.pickup_time_input)
        self.drop_time_input = QLineEdit("02:30 PM")
        time_box.addWidget(QLabel("Drop:"))
        time_box.addWidget(self.drop_time_input)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Inactive"])
        time_box.addWidget(QLabel("Status:"))
        time_box.addWidget(self.status_combo)
        form.addRow("Timing & Status:", time_box)

        layout.addLayout(form)

        # Pickup Points / Stops Table Editor
        stops_group = QGroupBox("Pickup & Drop-Off Points (Stops along Route)")
        stops_vbox = QVBoxLayout(stops_group)

        stop_ctrl = QHBoxLayout()
        add_stop_btn = QPushButton("+ Add Pickup Point")
        add_stop_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 4px 10px;")
        add_stop_btn.clicked.connect(lambda: self._append_stop_row())
        stop_ctrl.addWidget(add_stop_btn)

        rem_stop_btn = QPushButton("Remove Selected Stop")
        rem_stop_btn.clicked.connect(self._remove_selected_stop)
        stop_ctrl.addWidget(rem_stop_btn)
        stop_ctrl.addStretch()
        stops_vbox.addLayout(stop_ctrl)

        self.stops_table = QTableWidget(0, 6)
        self.stops_table.setHorizontalHeaderLabels([
            "Order", "Pickup Point Name *", "Pickup Time", "Drop Time", "Stop Fee", "Landmark / GPS Note"
        ])
        self.stops_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stops_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.stops_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.stops_table.verticalHeader().setVisible(False)
        stops_vbox.addWidget(self.stops_table)

        layout.addWidget(stops_group)

        if self.route:
            self.code_input.setText(self.route.route_code)
            self.code_input.setEnabled(False)
            self.name_input.setText(self.route.route_name)
            self.start_input.setText(self.route.start_point)
            self.end_input.setText(self.route.end_point)
            self.distance_spin.setValue(float(self.route.distance_km or 0.0))
            self.fee_spin.setValue(float(self.route.monthly_fee or 0.0))
            if self.route.vehicle_id:
                idx_v = self.vehicle_combo.findData(self.route.vehicle_id)
                if idx_v >= 0:
                    self.vehicle_combo.setCurrentIndex(idx_v)
            if self.route.pickup_time:
                self.pickup_time_input.setText(self.route.pickup_time)
            if self.route.drop_time:
                self.drop_time_input.setText(self.route.drop_time)
            idx_s = self.status_combo.findText(self.route.status)
            if idx_s >= 0:
                self.status_combo.setCurrentIndex(idx_s)
            for s in sorted(self.route.stops, key=lambda x: x.stop_order):
                self._append_stop_row(
                    stop_order=str(s.stop_order),
                    stop_name=s.stop_name,
                    pickup_time=s.pickup_time or "",
                    drop_time=s.drop_time or "",
                    fare=f"{float(s.fare or 0.0):.2f}",
                    landmark=s.landmark or "",
                )

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Route & Pickup Points")
        save_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 16px;")
        save_btn.clicked.connect(self._save_route)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _append_stop_row(
        self,
        stop_order: Optional[str] = None,
        stop_name: str = "",
        pickup_time: str = "07:00 AM",
        drop_time: str = "02:45 PM",
        fare: Optional[str] = None,
        landmark: str = "",
    ):
        r = self.stops_table.rowCount()
        self.stops_table.insertRow(r)
        order_val = stop_order or str(r + 1)
        fare_val = fare if fare is not None else f"{self.fee_spin.value():.2f}"
        self.stops_table.setItem(r, 0, QTableWidgetItem(order_val))
        self.stops_table.setItem(r, 1, QTableWidgetItem(stop_name))
        self.stops_table.setItem(r, 2, QTableWidgetItem(pickup_time))
        self.stops_table.setItem(r, 3, QTableWidgetItem(drop_time))
        self.stops_table.setItem(r, 4, QTableWidgetItem(fare_val))
        self.stops_table.setItem(r, 5, QTableWidgetItem(landmark))

    def _remove_selected_stop(self):
        row = self.stops_table.currentRow()
        if row >= 0:
            self.stops_table.removeRow(row)

    def _collect_stops_data(self) -> List[Dict[str, Any]]:
        stops: List[Dict[str, Any]] = []
        for r in range(self.stops_table.rowCount()):
            name_it = self.stops_table.item(r, 1)
            stop_name = name_it.text().strip() if name_it else ""
            if not stop_name:
                continue
            ord_it = self.stops_table.item(r, 0)
            p_it = self.stops_table.item(r, 2)
            d_it = self.stops_table.item(r, 3)
            f_it = self.stops_table.item(r, 4)
            l_it = self.stops_table.item(r, 5)
            try:
                order_num = int((ord_it.text() if ord_it else "").strip() or (r + 1))
            except ValueError:
                order_num = r + 1
            try:
                fare_num = max(0.0, float((f_it.text() if f_it else "").strip() or 0.0))
            except ValueError:
                fare_num = 0.0
            stops.append({
                "stop_order": order_num,
                "stop_name": stop_name,
                "pickup_time": (p_it.text() if p_it else "").strip() or None,
                "drop_time": (d_it.text() if d_it else "").strip() or None,
                "fare": fare_num,
                "landmark": (l_it.text() if l_it else "").strip() or None,
            })
        return stops

    def _save_route(self):
        code = self.code_input.text().strip()
        name = self.name_input.text().strip()
        start = self.start_input.text().strip()
        end = self.end_input.text().strip()

        if not code or not name or not start or not end:
            QMessageBox.warning(self, "Validation Error", "Route Code, Name, Origin, and Destination are required.")
            return

        stops_data = self._collect_stops_data()

        try:
            v_id = self.vehicle_combo.currentData()
            if self.route:
                TransportRepository.update_route(
                    self.db_session,
                    self.route.id,
                    route_name=name,
                    start_point=start,
                    end_point=end,
                    distance_km=self.distance_spin.value(),
                    monthly_fee=self.fee_spin.value(),
                    vehicle_id=v_id,
                    pickup_time=self.pickup_time_input.text().strip() or None,
                    drop_time=self.drop_time_input.text().strip() or None,
                    status=self.status_combo.currentText(),
                )
                TransportRepository.replace_route_stops(self.db_session, self.route.id, stops_data)
            else:
                existing = self.db_session.query(TransportRoute).filter(TransportRoute.route_code == code).first()
                if existing:
                    QMessageBox.warning(self, "Duplicate Route", f"Route code '{code}' already exists.")
                    return

                TransportRepository.create_route(
                    self.db_session,
                    route_code=code,
                    route_name=name,
                    start_point=start,
                    end_point=end,
                    distance_km=self.distance_spin.value(),
                    monthly_fee=self.fee_spin.value(),
                    vehicle_id=v_id,
                    pickup_time=self.pickup_time_input.text().strip() or None,
                    drop_time=self.drop_time_input.text().strip() or None,
                    status=self.status_combo.currentText(),
                    stops=stops_data,
                )

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save route:\n{str(e)}")
