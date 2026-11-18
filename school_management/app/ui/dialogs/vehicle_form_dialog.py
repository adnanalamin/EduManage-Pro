"""
EduManage Pro - Vehicle Form Dialog
PySide6 Modal for Registering & Updating Fleet Vehicles (Bus, Van, Microbus, Other),
Registrations, Mechanical Details, Driver/Helper Crew, and Compliance Dates.
"""

from datetime import date
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QSpinBox, QDoubleSpinBox, QPushButton, QLabel, QMessageBox,
    QGroupBox, QScrollArea, QWidget, QTextEdit
)
from sqlalchemy.orm import Session

from app.models.transport import Vehicle, VEHICLE_TYPES
from app.models.staff import Staff
from app.repositories.transport_repository import TransportRepository


class VehicleFormDialog(QDialog):
    """Dialog for registering or updating transport fleet vehicles."""

    def __init__(self, db_session: Session, vehicle: Optional[Vehicle] = None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.vehicle = vehicle

        self.setWindowTitle("Edit Fleet Vehicle" if vehicle else "Register New Fleet Vehicle")
        self.setMinimumSize(620, 620)
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setSpacing(10)

        title_lbl = QLabel("Vehicle Registration, Mechanical Specs & Crew Assignment")
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #B45309;")
        outer.addWidget(title_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(10)

        # Group 1: Core Identification & Registration
        g_reg = QGroupBox("1. Vehicle Identity & Registration")
        f_reg = QFormLayout(g_reg)
        f_reg.setSpacing(8)

        self.number_input = QLineEdit()
        self.number_input.setPlaceholderText("e.g. DHK-METRO-CHA-11-2041")
        f_reg.addRow("Vehicle Plate No *:", self.number_input)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("e.g. Tata Marcopolo 42-Seater")
        f_reg.addRow("Vehicle Model *:", self.model_input)

        type_cap_box = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(VEHICLE_TYPES)
        type_cap_box.addWidget(self.type_combo)

        self.capacity_spin = QSpinBox()
        self.capacity_spin.setRange(2, 120)
        self.capacity_spin.setValue(40)
        type_cap_box.addWidget(QLabel("Seats:"))
        type_cap_box.addWidget(self.capacity_spin)

        self.fuel_combo = QComboBox()
        self.fuel_combo.addItems(["Diesel", "Petrol", "CNG", "Octane", "Electric", "Hybrid"])
        type_cap_box.addWidget(QLabel("Fuel:"))
        type_cap_box.addWidget(self.fuel_combo)
        f_reg.addRow("Type / Capacity / Fuel *:", type_cap_box)

        reg_box = QHBoxLayout()
        self.reg_no_input = QLineEdit()
        self.reg_no_input.setPlaceholderText("Official Registration No")
        reg_box.addWidget(self.reg_no_input)

        self.reg_expiry_input = QLineEdit()
        self.reg_expiry_input.setPlaceholderText("Reg Expiry YYYY-MM-DD")
        reg_box.addWidget(self.reg_expiry_input)
        f_reg.addRow("Registration & Expiry:", reg_box)

        mech_box = QHBoxLayout()
        self.chassis_input = QLineEdit()
        self.chassis_input.setPlaceholderText("Chassis No")
        mech_box.addWidget(self.chassis_input)
        self.engine_input = QLineEdit()
        self.engine_input.setPlaceholderText("Engine No")
        mech_box.addWidget(self.engine_input)
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1990, date.today().year + 1)
        self.year_spin.setValue(date.today().year - 2)
        mech_box.addWidget(QLabel("Year:"))
        mech_box.addWidget(self.year_spin)
        f_reg.addRow("Chassis / Engine / Year:", mech_box)

        odo_box = QHBoxLayout()
        self.odo_spin = QDoubleSpinBox()
        self.odo_spin.setRange(0.0, 2000000.0)
        self.odo_spin.setDecimals(1)
        self.odo_spin.setSuffix(" km")
        odo_box.addWidget(self.odo_spin)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Maintenance", "Out of Service"])
        odo_box.addWidget(QLabel("Status:"))
        odo_box.addWidget(self.status_combo)
        f_reg.addRow("Odometer & Status:", odo_box)

        container_layout.addWidget(g_reg)

        # Group 2: Driver & Helper Crew
        g_crew = QGroupBox("2. Driver & Helper Assignment")
        f_crew = QFormLayout(g_crew)
        f_crew.setSpacing(8)

        staff_list = self.db_session.query(Staff).order_by(Staff.full_name.asc()).all()

        self.driver_staff_combo = QComboBox()
        self.driver_staff_combo.addItem("-- External / Manual Driver Entry --", None)
        for st in staff_list:
            self.driver_staff_combo.addItem(f"{st.full_name} ({st.position})", st.id)
        self.driver_staff_combo.currentIndexChanged.connect(self._on_driver_staff_selected)
        f_crew.addRow("Link Driver Staff (Opt):", self.driver_staff_combo)

        driver_box = QHBoxLayout()
        self.driver_name_input = QLineEdit()
        self.driver_name_input.setPlaceholderText("Driver Full Name *")
        driver_box.addWidget(self.driver_name_input)
        self.driver_phone_input = QLineEdit()
        self.driver_phone_input.setPlaceholderText("Driver Phone *")
        driver_box.addWidget(self.driver_phone_input)
        f_crew.addRow("Driver Name & Phone *:", driver_box)

        lic_box = QHBoxLayout()
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("e.g. DL-DHK-88412")
        lic_box.addWidget(self.license_input)
        self.license_expiry_input = QLineEdit()
        self.license_expiry_input.setPlaceholderText("License Expiry YYYY-MM-DD")
        lic_box.addWidget(self.license_expiry_input)
        f_crew.addRow("License & Expiry:", lic_box)

        self.helper_staff_combo = QComboBox()
        self.helper_staff_combo.addItem("-- External / Manual Helper Entry --", None)
        for st in staff_list:
            self.helper_staff_combo.addItem(f"{st.full_name} ({st.position})", st.id)
        self.helper_staff_combo.currentIndexChanged.connect(self._on_helper_staff_selected)
        f_crew.addRow("Link Helper Staff (Opt):", self.helper_staff_combo)

        helper_box = QHBoxLayout()
        self.helper_name_input = QLineEdit()
        self.helper_name_input.setPlaceholderText("Conductor / Helper Name")
        helper_box.addWidget(self.helper_name_input)
        self.helper_phone_input = QLineEdit()
        self.helper_phone_input.setPlaceholderText("Helper Phone")
        helper_box.addWidget(self.helper_phone_input)
        f_crew.addRow("Helper / Conductor:", helper_box)

        container_layout.addWidget(g_crew)

        # Group 3: Compliance & Service Reminders
        g_comp = QGroupBox("3. Insurance, Fitness & Service Schedule")
        f_comp = QFormLayout(g_comp)
        f_comp.setSpacing(8)

        exp_box = QHBoxLayout()
        self.ins_expiry_input = QLineEdit()
        self.ins_expiry_input.setPlaceholderText("Insurance YYYY-MM-DD")
        exp_box.addWidget(self.ins_expiry_input)
        self.fit_expiry_input = QLineEdit()
        self.fit_expiry_input.setPlaceholderText("Fitness YYYY-MM-DD")
        exp_box.addWidget(self.fit_expiry_input)
        f_comp.addRow("Insurance & Fitness Exp:", exp_box)

        svc_box = QHBoxLayout()
        self.next_svc_date_input = QLineEdit()
        self.next_svc_date_input.setPlaceholderText("Next Service YYYY-MM-DD")
        svc_box.addWidget(self.next_svc_date_input)
        self.next_svc_odo_spin = QDoubleSpinBox()
        self.next_svc_odo_spin.setRange(0.0, 2000000.0)
        self.next_svc_odo_spin.setDecimals(0)
        self.next_svc_odo_spin.setSuffix(" km")
        svc_box.addWidget(QLabel("Next Svc Odo:"))
        svc_box.addWidget(self.next_svc_odo_spin)
        f_comp.addRow("Next Service Reminder:", svc_box)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(55)
        self.notes_input.setPlaceholderText("Additional vehicle notes or permit remarks...")
        f_comp.addRow("Notes:", self.notes_input)

        container_layout.addWidget(g_comp)
        scroll.setWidget(container)
        outer.addWidget(scroll)

        # Populate when editing
        if self.vehicle:
            self.number_input.setText(self.vehicle.vehicle_number)
            self.number_input.setEnabled(False)
            self.model_input.setText(self.vehicle.vehicle_model)
            v_type = "Microbus" if self.vehicle.vehicle_type == "Minibus" else self.vehicle.vehicle_type
            idx_t = self.type_combo.findText(v_type)
            if idx_t >= 0:
                self.type_combo.setCurrentIndex(idx_t)
            self.capacity_spin.setValue(int(self.vehicle.seating_capacity or 40))
            idx_f = self.fuel_combo.findText(self.vehicle.fuel_type or "Diesel")
            if idx_f >= 0:
                self.fuel_combo.setCurrentIndex(idx_f)
            self.reg_no_input.setText(self.vehicle.registration_no or "")
            self.reg_expiry_input.setText(self.vehicle.registration_expiry or "")
            self.chassis_input.setText(self.vehicle.chassis_no or "")
            self.engine_input.setText(self.vehicle.engine_no or "")
            if self.vehicle.manufacture_year:
                self.year_spin.setValue(int(self.vehicle.manufacture_year))
            self.odo_spin.setValue(float(self.vehicle.current_odometer_km or 0.0))
            idx_s = self.status_combo.findText(self.vehicle.status)
            if idx_s >= 0:
                self.status_combo.setCurrentIndex(idx_s)

            if self.vehicle.driver_staff_id:
                idx_ds = self.driver_staff_combo.findData(self.vehicle.driver_staff_id)
                if idx_ds >= 0:
                    self.driver_staff_combo.setCurrentIndex(idx_ds)
            self.driver_name_input.setText(self.vehicle.driver_name)
            self.driver_phone_input.setText(self.vehicle.driver_phone)
            self.license_input.setText(self.vehicle.driver_license or "")
            self.license_expiry_input.setText(self.vehicle.driver_license_expiry or "")

            if self.vehicle.helper_staff_id:
                idx_hs = self.helper_staff_combo.findData(self.vehicle.helper_staff_id)
                if idx_hs >= 0:
                    self.helper_staff_combo.setCurrentIndex(idx_hs)
            self.helper_name_input.setText(self.vehicle.helper_name or "")
            self.helper_phone_input.setText(self.vehicle.helper_phone or "")
            self.ins_expiry_input.setText(self.vehicle.insurance_expiry or "")
            self.fit_expiry_input.setText(self.vehicle.fitness_expiry or "")
            self.next_svc_date_input.setText(self.vehicle.next_service_date or "")
            if self.vehicle.next_service_odometer_km:
                self.next_svc_odo_spin.setValue(float(self.vehicle.next_service_odometer_km))
            self.notes_input.setPlainText(self.vehicle.notes or "")

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Vehicle")
        save_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 16px;")
        save_btn.clicked.connect(self._save_vehicle)
        btn_layout.addWidget(save_btn)
        outer.addLayout(btn_layout)

    def _on_driver_staff_selected(self):
        st_id = self.driver_staff_combo.currentData()
        if st_id:
            st = self.db_session.query(Staff).filter(Staff.id == st_id).first()
            if st:
                self.driver_name_input.setText(st.full_name)
                self.driver_phone_input.setText(st.phone or "")

    def _on_helper_staff_selected(self):
        st_id = self.helper_staff_combo.currentData()
        if st_id:
            st = self.db_session.query(Staff).filter(Staff.id == st_id).first()
            if st:
                self.helper_name_input.setText(st.full_name)
                self.helper_phone_input.setText(st.phone or "")

    def _save_vehicle(self):
        number = self.number_input.text().strip()
        model = self.model_input.text().strip()
        d_name = self.driver_name_input.text().strip()
        d_phone = self.driver_phone_input.text().strip()

        if not number or not model or not d_name or not d_phone:
            QMessageBox.warning(self, "Validation Error", "Plate No, Model, Driver Name, and Driver Phone are required.")
            return

        payload = dict(
            vehicle_model=model,
            vehicle_type=self.type_combo.currentText(),
            seating_capacity=self.capacity_spin.value(),
            fuel_type=self.fuel_combo.currentText(),
            registration_no=self.reg_no_input.text().strip() or number,
            registration_expiry=self.reg_expiry_input.text().strip() or None,
            chassis_no=self.chassis_input.text().strip() or None,
            engine_no=self.engine_input.text().strip() or None,
            manufacture_year=self.year_spin.value(),
            current_odometer_km=float(self.odo_spin.value()),
            driver_staff_id=self.driver_staff_combo.currentData(),
            driver_name=d_name,
            driver_phone=d_phone,
            driver_license=self.license_input.text().strip() or None,
            driver_license_expiry=self.license_expiry_input.text().strip() or None,
            helper_staff_id=self.helper_staff_combo.currentData(),
            helper_name=self.helper_name_input.text().strip() or None,
            helper_phone=self.helper_phone_input.text().strip() or None,
            insurance_expiry=self.ins_expiry_input.text().strip() or None,
            fitness_expiry=self.fit_expiry_input.text().strip() or None,
            next_service_date=self.next_svc_date_input.text().strip() or None,
            next_service_odometer_km=float(self.next_svc_odo_spin.value()) if self.next_svc_odo_spin.value() > 0 else None,
            status=self.status_combo.currentText(),
            notes=self.notes_input.toPlainText().strip() or None,
        )

        try:
            if self.vehicle:
                TransportRepository.update_vehicle(self.db_session, self.vehicle.id, **payload)
            else:
                existing = self.db_session.query(Vehicle).filter(Vehicle.vehicle_number == number).first()
                if existing:
                    QMessageBox.warning(self, "Duplicate Plate", f"Vehicle with plate '{number}' already exists.")
                    return
                TransportRepository.create_vehicle(self.db_session, vehicle_number=number, **payload)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save vehicle:\n{str(e)}")
