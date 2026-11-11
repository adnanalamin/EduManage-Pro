"""
EduManage Pro - Route Form Dialog
Phase 11: PySide6 Modal for Route Configuration & Vehicle Assignment
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QDoubleSpinBox, QPushButton, QLabel, QMessageBox
)
from sqlalchemy.orm import Session
from app.models.transport import TransportRoute, Vehicle
from app.repositories.transport_repository import TransportRepository


class RouteFormDialog(QDialog):
    """Dialog for creating or updating school transit routes."""

    def __init__(self, db_session: Session, route: Optional[TransportRoute] = None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.route = route

        self.setWindowTitle("Edit Transport Route" if route else "Add New Transport Route")
        self.setMinimumWidth(480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title_lbl = QLabel("Route Configuration & Timing")
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #B45309;")
        layout.addWidget(title_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        # Route Code & Name
        code_box = QHBoxLayout()
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g. RT-04")
        code_box.addWidget(self.code_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Route Name (Origin - Destination)")
        code_box.addWidget(self.name_input)
        form.addRow("Route Code & Title *:", code_box)

        # Origin & Destination
        points_box = QHBoxLayout()
        self.start_input = QLineEdit()
        self.start_input.setPlaceholderText("Start Point (e.g. Badda Link Rd)")
        points_box.addWidget(self.start_input)

        self.end_input = QLineEdit("School Main Campus")
        points_box.addWidget(self.end_input)
        form.addRow("Origin & Destination *:", points_box)

        # Distance & Monthly Fee
        num_box = QHBoxLayout()
        self.distance_spin = QDoubleSpinBox()
        self.distance_spin.setRange(0.5, 200.0)
        self.distance_spin.setValue(12.0)
        self.distance_spin.setSuffix(" km")
        num_box.addWidget(self.distance_spin)

        self.fee_spin = QDoubleSpinBox()
        self.fee_spin.setRange(0.0, 50000.0)
        self.fee_spin.setValue(2500.0)
        self.fee_spin.setPrefix("$ ")
        num_box.addWidget(QLabel("Monthly Fee:"))
        num_box.addWidget(self.fee_spin)
        form.addRow("Distance & Fee:", num_box)

        # Vehicle Selector
        self.vehicle_combo = QComboBox()
        self.vehicle_combo.addItem("None (Unassigned)", None)
        vehicles = TransportRepository.get_vehicles(self.db_session, status="Active")
        for v in vehicles:
            self.vehicle_combo.addItem(f"{v.vehicle_number} ({v.vehicle_model} - {v.seating_capacity} seats)", v.id)
        form.addRow("Assigned Bus *:", self.vehicle_combo)

        # Pickup & Drop Timing
        time_box = QHBoxLayout()
        self.pickup_time_input = QLineEdit("06:45 AM")
        time_box.addWidget(self.pickup_time_input)

        self.drop_time_input = QLineEdit("02:30 PM")
        time_box.addWidget(QLabel("Drop:"))
        time_box.addWidget(self.drop_time_input)
        form.addRow("Pickup & Drop Time:", time_box)

        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Inactive"])
        form.addRow("Status:", self.status_combo)

        layout.addLayout(form)

        # Populate if editing
        if self.route:
            self.code_input.setText(self.route.route_code)
            self.code_input.setEnabled(False)
            self.name_input.setText(self.route.route_name)
            self.start_input.setText(self.route.start_point)
            self.end_input.setText(self.route.end_point)
            self.distance_spin.setValue(self.route.distance_km)
            self.fee_spin.setValue(self.route.monthly_fee)
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

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Route")
        save_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 16px;")
        save_btn.clicked.connect(self._save_route)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _save_route(self):
        code = self.code_input.text().strip()
        name = self.name_input.text().strip()
        start = self.start_input.text().strip()
        end = self.end_input.text().strip()

        if not code or not name or not start or not end:
            QMessageBox.warning(self, "Validation Error", "Route Code, Name, Origin, and Destination are required.")
            return

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
                    status=self.status_combo.currentText()
                )
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
                    status=self.status_combo.currentText()
                )

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save route:\n{str(e)}")
