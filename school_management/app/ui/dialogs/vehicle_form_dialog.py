"""
EduManage Pro - Vehicle Form Dialog
Phase 11: PySide6 Modal for Adding & Editing Fleet Vehicles
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QSpinBox, QPushButton, QLabel, QMessageBox, QDateEdit
)
from PySide6.QtCore import QDate
from sqlalchemy.orm import Session
from app.models.transport import Vehicle
from app.repositories.transport_repository import TransportRepository


class VehicleFormDialog(QDialog):
    """Dialog for registering or updating transport fleet vehicles."""

    def __init__(self, db_session: Session, vehicle: Optional[Vehicle] = None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.vehicle = vehicle

        self.setWindowTitle("Edit Vehicle" if vehicle else "Add New Fleet Vehicle")
        self.setMinimumWidth(480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title_lbl = QLabel("Vehicle & Driver Profile")
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #B45309;")
        layout.addWidget(title_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        # Vehicle Plate Number
        self.number_input = QLineEdit()
        self.number_input.setPlaceholderText("e.g. DHK-METRO-CHA-11-2041")
        form.addRow("Vehicle Plate No *:", self.number_input)

        # Vehicle Model
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("e.g. Tata Marcopolo 42-Seater")
        form.addRow("Vehicle Model *:", self.model_input)

        # Vehicle Type & Seating Capacity
        type_cap_box = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Bus", "Minibus", "Van", "Coaster"])
        type_cap_box.addWidget(self.type_combo)

        self.capacity_spin = QSpinBox()
        self.capacity_spin.setRange(5, 120)
        self.capacity_spin.setValue(40)
        type_cap_box.addWidget(QLabel("Seats:"))
        type_cap_box.addWidget(self.capacity_spin)
        form.addRow("Type & Capacity *:", type_cap_box)

        # Driver Name & Phone
        driver_box = QHBoxLayout()
        self.driver_name_input = QLineEdit()
        self.driver_name_input.setPlaceholderText("Driver Full Name")
        driver_box.addWidget(self.driver_name_input)

        self.driver_phone_input = QLineEdit()
        self.driver_phone_input.setPlaceholderText("+880 1711-XXXXXX")
        driver_box.addWidget(self.driver_phone_input)
        form.addRow("Driver & Contact *:", driver_box)

        # Driver License
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("e.g. DL-DHK-88412")
        form.addRow("Driver License No:", self.license_input)

        # Helper / Conductor
        helper_box = QHBoxLayout()
        self.helper_name_input = QLineEdit()
        self.helper_name_input.setPlaceholderText("Conductor Name")
        helper_box.addWidget(self.helper_name_input)

        self.helper_phone_input = QLineEdit()
        self.helper_phone_input.setPlaceholderText("Phone Number")
        helper_box.addWidget(self.helper_phone_input)
        form.addRow("Helper / Conductor:", helper_box)

        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Maintenance", "Out of Service"])
        form.addRow("Operational Status:", self.status_combo)

        layout.addLayout(form)

        # Populate if editing
        if self.vehicle:
            self.number_input.setText(self.vehicle.vehicle_number)
            self.number_input.setEnabled(False)
            self.model_input.setText(self.vehicle.vehicle_model)
            idx_t = self.type_combo.findText(self.vehicle.vehicle_type)
            if idx_t >= 0:
                self.type_combo.setCurrentIndex(idx_t)
            self.capacity_spin.setValue(self.vehicle.seating_capacity)
            self.driver_name_input.setText(self.vehicle.driver_name)
            self.driver_phone_input.setText(self.vehicle.driver_phone)
            self.license_input.setText(self.vehicle.driver_license or "")
            self.helper_name_input.setText(self.vehicle.helper_name or "")
            self.helper_phone_input.setText(self.vehicle.helper_phone or "")
            idx_s = self.status_combo.findText(self.vehicle.status)
            if idx_s >= 0:
                self.status_combo.setCurrentIndex(idx_s)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Vehicle")
        save_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 16px;")
        save_btn.clicked.connect(self._save_vehicle)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _save_vehicle(self):
        number = self.number_input.text().strip()
        model = self.model_input.text().strip()
        d_name = self.driver_name_input.text().strip()
        d_phone = self.driver_phone_input.text().strip()

        if not number or not model or not d_name or not d_phone:
            QMessageBox.warning(self, "Validation Error", "Plate No, Model, Driver Name, and Driver Phone are required.")
            return

        try:
            if self.vehicle:
                TransportRepository.update_vehicle(
                    self.db_session,
                    self.vehicle.id,
                    vehicle_model=model,
                    vehicle_type=self.type_combo.currentText(),
                    seating_capacity=self.capacity_spin.value(),
                    driver_name=d_name,
                    driver_phone=d_phone,
                    driver_license=self.license_input.text().strip() or None,
                    helper_name=self.helper_name_input.text().strip() or None,
                    helper_phone=self.helper_phone_input.text().strip() or None,
                    status=self.status_combo.currentText()
                )
            else:
                existing = self.db_session.query(Vehicle).filter(Vehicle.vehicle_number == number).first()
                if existing:
                    QMessageBox.warning(self, "Duplicate Plate", f"Vehicle with plate '{number}' already exists.")
                    return

                TransportRepository.create_vehicle(
                    self.db_session,
                    vehicle_number=number,
                    vehicle_model=model,
                    vehicle_type=self.type_combo.currentText(),
                    seating_capacity=self.capacity_spin.value(),
                    driver_name=d_name,
                    driver_phone=d_phone,
                    driver_license=self.license_input.text().strip() or None,
                    helper_name=self.helper_name_input.text().strip() or None,
                    helper_phone=self.helper_phone_input.text().strip() or None,
                    status=self.status_combo.currentText()
                )

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save vehicle:\n{str(e)}")
