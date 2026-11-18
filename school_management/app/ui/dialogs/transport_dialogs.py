"""
EduManage Pro - Transport Module Supporting Dialogs
Fuel Refill Dialog, Maintenance Service Dialog, Insurance Policy Dialog,
Vehicle Document Vault Dialog, Transport Fee Payment Dialog, GPS Device Config
& Hardware-Free Manual Location Check-In Dialog.
"""

from datetime import date
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QDoubleSpinBox, QPushButton, QLabel, QMessageBox,
    QCheckBox, QTextEdit, QFileDialog
)
from sqlalchemy.orm import Session

from app.models.transport import (
    Vehicle,
    TransportFeeCharge,
    DOCUMENT_TYPES,
    MAINTENANCE_SERVICE_TYPES,
    GPS_PROVIDER_TYPES,
)
from app.repositories.transport_repository import TransportRepository
from app.services.transport_service import GPSIntegrationManager
from app.security.session import session as app_session


def _current_username() -> str:
    try:
        user = app_session.current_user
        return user.username if user else "admin"
    except Exception:
        return "admin"


class FuelLogDialog(QDialog):
    """Modal for recording a fleet vehicle fuel refill & odometer reading."""

    def __init__(self, db_session: Session, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.setWindowTitle("Record Vehicle Fuel Refill")
        self.setMinimumWidth(460)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.vehicle_combo = QComboBox()
        vehicles = TransportRepository.get_vehicles(self.db_session)
        for v in vehicles:
            self.vehicle_combo.addItem(f"{v.vehicle_number} ({v.vehicle_type} - {v.fuel_type})", v.id)
        self.vehicle_combo.currentIndexChanged.connect(self._sync_vehicle_defaults)
        form.addRow("Vehicle *:", self.vehicle_combo)

        self.date_input = QLineEdit(date.today().isoformat())
        form.addRow("Fill Date (YYYY-MM-DD) *:", self.date_input)

        self.fuel_type_combo = QComboBox()
        self.fuel_type_combo.addItems(["Diesel", "Petrol", "CNG", "Octane", "Electric"])
        form.addRow("Fuel Type:", self.fuel_type_combo)

        self.liters_spin = QDoubleSpinBox()
        self.liters_spin.setRange(0.5, 1000.0)
        self.liters_spin.setValue(40.0)
        self.liters_spin.valueChanged.connect(self._recalc_total)
        form.addRow("Quantity (Liters / Units) *:", self.liters_spin)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.0, 5000.0)
        self.price_spin.setValue(109.0)
        self.price_spin.valueChanged.connect(self._recalc_total)
        form.addRow("Price per Unit *:", self.price_spin)

        self.total_spin = QDoubleSpinBox()
        self.total_spin.setRange(0.0, 1000000.0)
        self.total_spin.setValue(4360.0)
        form.addRow("Total Cost:", self.total_spin)

        self.odo_spin = QDoubleSpinBox()
        self.odo_spin.setRange(0.0, 3000000.0)
        self.odo_spin.setSuffix(" km")
        form.addRow("Odometer Reading *:", self.odo_spin)

        self.station_input = QLineEdit()
        self.station_input.setPlaceholderText("Filling station / vendor name")
        form.addRow("Fuel Station:", self.station_input)

        self.receipt_input = QLineEdit()
        self.receipt_input.setPlaceholderText("Slip / Receipt No")
        form.addRow("Receipt No:", self.receipt_input)

        self.filled_by_input = QLineEdit(_current_username())
        form.addRow("Filled By:", self.filled_by_input)

        layout.addLayout(form)
        self._sync_vehicle_defaults()

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        save_btn = QPushButton("Save Fuel Log")
        save_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 14px;")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _sync_vehicle_defaults(self):
        v_id = self.vehicle_combo.currentData()
        if not v_id:
            return
        v = self.db_session.query(Vehicle).filter(Vehicle.id == v_id).first()
        if v:
            self.odo_spin.setValue(float(v.current_odometer_km or 0.0))
            idx = self.fuel_type_combo.findText(v.fuel_type or "Diesel")
            if idx >= 0:
                self.fuel_type_combo.setCurrentIndex(idx)

    def _recalc_total(self):
        self.total_spin.setValue(round(self.liters_spin.value() * self.price_spin.value(), 2))

    def _save(self):
        v_id = self.vehicle_combo.currentData()
        if not v_id:
            QMessageBox.warning(self, "Required", "Please select a vehicle.")
            return
        log, err = TransportRepository.add_fuel_log(
            session=self.db_session,
            vehicle_id=v_id,
            fill_date=self.date_input.text().strip() or date.today().isoformat(),
            liters=self.liters_spin.value(),
            price_per_liter=self.price_spin.value(),
            odometer_km=self.odo_spin.value(),
            fuel_type=self.fuel_type_combo.currentText(),
            total_cost=self.total_spin.value(),
            station_name=self.station_input.text().strip() or None,
            receipt_no=self.receipt_input.text().strip() or None,
            filled_by=self.filled_by_input.text().strip() or None,
        )
        if err:
            QMessageBox.warning(self, "Error", err)
            return
        self.accept()


class MaintenanceLogDialog(QDialog):
    """Modal for logging vehicle servicing, repairs & scheduling next reminder."""

    def __init__(self, db_session: Session, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.setWindowTitle("Log Vehicle Maintenance / Service")
        self.setMinimumWidth(480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.vehicle_combo = QComboBox()
        for v in TransportRepository.get_vehicles(self.db_session):
            self.vehicle_combo.addItem(f"{v.vehicle_number} ({v.vehicle_model})", v.id)
        self.vehicle_combo.currentIndexChanged.connect(self._sync_odo)
        form.addRow("Vehicle *:", self.vehicle_combo)

        self.service_type_combo = QComboBox()
        self.service_type_combo.setEditable(True)
        self.service_type_combo.addItems(MAINTENANCE_SERVICE_TYPES)
        form.addRow("Service Type *:", self.service_type_combo)

        self.date_input = QLineEdit(date.today().isoformat())
        form.addRow("Service Date (YYYY-MM-DD) *:", self.date_input)

        self.workshop_input = QLineEdit()
        self.workshop_input.setPlaceholderText("Garage / Authorized Service Center")
        form.addRow("Workshop / Vendor:", self.workshop_input)

        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0.0, 2000000.0)
        form.addRow("Service Cost:", self.cost_spin)

        self.odo_spin = QDoubleSpinBox()
        self.odo_spin.setRange(0.0, 3000000.0)
        self.odo_spin.setSuffix(" km")
        form.addRow("Odometer at Service:", self.odo_spin)

        self.next_date_input = QLineEdit()
        self.next_date_input.setPlaceholderText("Next Due YYYY-MM-DD (for auto reminder)")
        form.addRow("Next Service Due Date:", self.next_date_input)

        self.next_odo_spin = QDoubleSpinBox()
        self.next_odo_spin.setRange(0.0, 3000000.0)
        self.next_odo_spin.setSuffix(" km")
        form.addRow("Next Service Odometer:", self.next_odo_spin)

        self.invoice_input = QLineEdit()
        form.addRow("Invoice / Bill No:", self.invoice_input)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Completed", "Scheduled", "In Progress"])
        form.addRow("Status:", self.status_combo)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(55)
        form.addRow("Notes / Parts Replaced:", self.notes_input)

        layout.addLayout(form)
        self._sync_odo()

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        save_btn = QPushButton("Save Maintenance Log")
        save_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 14px;")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _sync_odo(self):
        v_id = self.vehicle_combo.currentData()
        if v_id:
            v = self.db_session.query(Vehicle).filter(Vehicle.id == v_id).first()
            if v:
                self.odo_spin.setValue(float(v.current_odometer_km or 0.0))

    def _save(self):
        v_id = self.vehicle_combo.currentData()
        if not v_id:
            QMessageBox.warning(self, "Required", "Please select a vehicle.")
            return
        log, err = TransportRepository.add_maintenance_log(
            session=self.db_session,
            vehicle_id=v_id,
            service_type=self.service_type_combo.currentText().strip() or "General Inspection",
            service_date=self.date_input.text().strip() or date.today().isoformat(),
            workshop_name=self.workshop_input.text().strip() or None,
            cost=self.cost_spin.value(),
            odometer_km=self.odo_spin.value(),
            next_service_date=self.next_date_input.text().strip() or None,
            next_service_odometer_km=self.next_odo_spin.value() if self.next_odo_spin.value() > 0 else None,
            invoice_no=self.invoice_input.text().strip() or None,
            status=self.status_combo.currentText(),
            notes=self.notes_input.toPlainText().strip() or None,
        )
        if err:
            QMessageBox.warning(self, "Error", err)
            return
        self.accept()


class InsuranceDialog(QDialog):
    """Modal for adding a vehicle insurance policy."""

    def __init__(self, db_session: Session, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.setWindowTitle("Add Vehicle Insurance Policy")
        self.setMinimumWidth(460)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.vehicle_combo = QComboBox()
        for v in TransportRepository.get_vehicles(self.db_session):
            self.vehicle_combo.addItem(f"{v.vehicle_number} ({v.vehicle_model})", v.id)
        form.addRow("Vehicle *:", self.vehicle_combo)

        self.policy_input = QLineEdit()
        self.policy_input.setPlaceholderText("e.g. POL-2026-88412")
        form.addRow("Policy Number *:", self.policy_input)

        self.provider_input = QLineEdit()
        self.provider_input.setPlaceholderText("Insurance Company Name *")
        form.addRow("Insurance Provider *:", self.provider_input)

        self.coverage_combo = QComboBox()
        self.coverage_combo.addItems(["Comprehensive", "Third-Party", "Passenger Liability"])
        form.addRow("Coverage Type:", self.coverage_combo)

        self.start_input = QLineEdit(date.today().isoformat())
        form.addRow("Start Date (YYYY-MM-DD) *:", self.start_input)

        self.expiry_input = QLineEdit()
        self.expiry_input.setPlaceholderText("YYYY-MM-DD")
        form.addRow("Expiry Date (YYYY-MM-DD) *:", self.expiry_input)

        self.premium_spin = QDoubleSpinBox()
        self.premium_spin.setRange(0.0, 2000000.0)
        form.addRow("Premium Amount:", self.premium_spin)

        self.insured_val_spin = QDoubleSpinBox()
        self.insured_val_spin.setRange(0.0, 50000000.0)
        form.addRow("Insured Value:", self.insured_val_spin)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        save_btn = QPushButton("Save Insurance Policy")
        save_btn.setStyleSheet("background-color: #7C3AED; color: white; font-weight: bold; padding: 6px 14px;")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _save(self):
        v_id = self.vehicle_combo.currentData()
        policy = self.policy_input.text().strip()
        provider = self.provider_input.text().strip()
        expiry = self.expiry_input.text().strip()
        if not v_id or not policy or not provider or not expiry:
            QMessageBox.warning(self, "Validation", "Vehicle, Policy Number, Provider, and Expiry Date are required.")
            return
        _, err = TransportRepository.add_insurance(
            session=self.db_session,
            vehicle_id=v_id,
            policy_number=policy,
            provider=provider,
            start_date=self.start_input.text().strip() or date.today().isoformat(),
            expiry_date=expiry,
            coverage_type=self.coverage_combo.currentText(),
            premium_amount=self.premium_spin.value(),
            insured_value=self.insured_val_spin.value(),
            status="Active",
        )
        if err:
            QMessageBox.warning(self, "Error", err)
            return
        self.accept()


class VehicleDocumentDialog(QDialog):
    """Modal for registering a vehicle compliance document in the vault."""

    def __init__(self, db_session: Session, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.setWindowTitle("Upload / Register Vehicle Compliance Document")
        self.setMinimumWidth(480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.vehicle_combo = QComboBox()
        for v in TransportRepository.get_vehicles(self.db_session):
            self.vehicle_combo.addItem(f"{v.vehicle_number} ({v.vehicle_model})", v.id)
        form.addRow("Vehicle *:", self.vehicle_combo)

        self.doc_type_combo = QComboBox()
        self.doc_type_combo.addItems(DOCUMENT_TYPES)
        form.addRow("Document Type *:", self.doc_type_combo)

        self.doc_no_input = QLineEdit()
        self.doc_no_input.setPlaceholderText("Permit / Fitness / Tax Token Number")
        form.addRow("Document Number:", self.doc_no_input)

        self.issuer_input = QLineEdit()
        self.issuer_input.setPlaceholderText("e.g. BRTA / Transport Authority")
        form.addRow("Issuing Authority:", self.issuer_input)

        self.issue_input = QLineEdit(date.today().isoformat())
        form.addRow("Issue Date (YYYY-MM-DD):", self.issue_input)

        self.expiry_input = QLineEdit()
        self.expiry_input.setPlaceholderText("Expiry Date YYYY-MM-DD")
        form.addRow("Expiry Date:", self.expiry_input)

        file_box = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("Optional local scan/PDF path")
        file_box.addWidget(self.file_path_input)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_file)
        file_box.addWidget(browse_btn)
        form.addRow("Document File:", file_box)

        self.notes_input = QLineEdit()
        form.addRow("Notes:", self.notes_input)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        save_btn = QPushButton("Save Document")
        save_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 14px;")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Document File", "", "Documents (*.pdf *.png *.jpg *.jpeg);;All Files (*)")
        if path:
            self.file_path_input.setText(path)

    def _save(self):
        v_id = self.vehicle_combo.currentData()
        if not v_id:
            QMessageBox.warning(self, "Required", "Please select a vehicle.")
            return
        _, err = TransportRepository.add_document(
            session=self.db_session,
            vehicle_id=v_id,
            document_type=self.doc_type_combo.currentText(),
            document_number=self.doc_no_input.text().strip() or None,
            issuing_authority=self.issuer_input.text().strip() or None,
            issue_date=self.issue_input.text().strip() or None,
            expiry_date=self.expiry_input.text().strip() or None,
            file_path=self.file_path_input.text().strip() or None,
            notes=self.notes_input.text().strip() or None,
        )
        if err:
            QMessageBox.warning(self, "Error", err)
            return
        self.accept()


class TransportFeePaymentDialog(QDialog):
    """Modal for collecting transport fee payment against a monthly charge."""

    def __init__(self, db_session: Session, charge: TransportFeeCharge, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.charge = charge
        self.setWindowTitle(f"Collect Transport Fee ({charge.billing_month})")
        self.setMinimumWidth(420)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        form.addRow("Billing Month:", QLabel(self.charge.billing_month))
        form.addRow("Fee Amount:", QLabel(f"{float(self.charge.amount or 0.0):.2f}"))
        form.addRow("Already Paid:", QLabel(f"{float(self.charge.paid_amount or 0.0):.2f}"))

        self.discount_spin = QDoubleSpinBox()
        self.discount_spin.setRange(0.0, float(self.charge.amount or 0.0))
        self.discount_spin.setValue(float(self.charge.discount or 0.0))
        form.addRow("Discount:", self.discount_spin)

        self.pay_spin = QDoubleSpinBox()
        self.pay_spin.setRange(0.0, 100000.0)
        self.pay_spin.setValue(self.charge.balance_due)
        form.addRow("Amount Paying Now *:", self.pay_spin)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["Cash", "Bank", "Card", "Mobile Banking", "Other"])
        form.addRow("Payment Method:", self.method_combo)

        self.remarks_input = QLineEdit()
        form.addRow("Remarks:", self.remarks_input)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        pay_btn = QPushButton("Confirm Payment")
        pay_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 14px;")
        pay_btn.clicked.connect(self._collect)
        btns.addWidget(pay_btn)
        layout.addLayout(btns)

    def _collect(self):
        updated, err = TransportRepository.record_fee_payment(
            session=self.db_session,
            charge_id=self.charge.id,
            amount=self.pay_spin.value(),
            payment_method=self.method_combo.currentText(),
            discount=self.discount_spin.value(),
            collected_by=_current_username(),
            remarks=self.remarks_input.text().strip() or None,
        )
        if err:
            QMessageBox.warning(self, "Payment Error", err)
            return
        QMessageBox.information(self, "Payment Recorded", f"Receipt: {updated.receipt_no or '-'}\nStatus: {updated.status}")
        self.accept()


class GPSDeviceConfigDialog(QDialog):
    """Optional GPS tracker device registration (hardware is never mandatory)."""

    def __init__(self, db_session: Session, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.setWindowTitle("Register Optional GPS / Telematics Adapter")
        self.setMinimumWidth(460)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        note = QLabel("GPS hardware is strictly optional. Manual fleet management works without any GPS tracker.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #475569; font-style: italic;")
        layout.addWidget(note)

        form = QFormLayout()
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g. GPS-BUS-01")
        form.addRow("Device Code *:", self.code_input)

        self.vehicle_combo = QComboBox()
        self.vehicle_combo.addItem("Unassigned", None)
        for v in TransportRepository.get_vehicles(self.db_session):
            self.vehicle_combo.addItem(f"{v.vehicle_number} ({v.vehicle_type})", v.id)
        form.addRow("Bind to Vehicle:", self.vehicle_combo)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(GPS_PROVIDER_TYPES)
        form.addRow("Provider Adapter:", self.provider_combo)

        self.imei_input = QLineEdit()
        self.imei_input.setPlaceholderText("Optional IMEI / Hardware Serial")
        form.addRow("IMEI / Serial:", self.imei_input)

        self.endpoint_input = QLineEdit()
        self.endpoint_input.setPlaceholderText("Optional Webhook URL or MQTT Topic")
        form.addRow("Endpoint / Topic:", self.endpoint_input)

        self.enabled_chk = QCheckBox("Enable Adapter Immediately")
        self.enabled_chk.setChecked(True)
        form.addRow("", self.enabled_chk)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        save_btn = QPushButton("Register GPS Adapter")
        save_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 14px;")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _save(self):
        code = self.code_input.text().strip()
        if not code:
            QMessageBox.warning(self, "Required", "Device Code is required.")
            return
        try:
            TransportRepository.register_gps_device(
                session=self.db_session,
                device_code=code,
                vehicle_id=self.vehicle_combo.currentData(),
                provider_type=self.provider_combo.currentText(),
                imei_or_serial=self.imei_input.text().strip() or None,
                endpoint_url=self.endpoint_input.text().strip() or None,
                is_enabled=self.enabled_chk.isChecked(),
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not register GPS device:\n{str(e)}")


class ManualGPSCheckinDialog(QDialog):
    """Hardware-free checkpoint check-in dialog to record vehicle coordinates manually."""

    def __init__(self, db_session: Session, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.setWindowTitle("Manual Vehicle Location Check-In (No GPS Hardware Required)")
        self.setMinimumWidth(440)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.vehicle_combo = QComboBox()
        for v in TransportRepository.get_vehicles(self.db_session):
            self.vehicle_combo.addItem(f"{v.vehicle_number} ({v.vehicle_type})", v.id)
        form.addRow("Vehicle *:", self.vehicle_combo)

        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("e.g. Departed Uttara Sector 14 Stop")
        form.addRow("Location / Checkpoint *:", self.label_input)

        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90.0, 90.0)
        self.lat_spin.setDecimals(6)
        self.lat_spin.setValue(23.810300)
        form.addRow("Latitude:", self.lat_spin)

        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(-180.0, 180.0)
        self.lon_spin.setDecimals(6)
        self.lon_spin.setValue(90.412500)
        form.addRow("Longitude:", self.lon_spin)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.0, 180.0)
        self.speed_spin.setSuffix(" km/h")
        form.addRow("Estimated Speed:", self.speed_spin)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        save_btn = QPushButton("Record Check-In")
        save_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 14px;")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _save(self):
        v_id = self.vehicle_combo.currentData()
        lbl = self.label_input.text().strip()
        if not v_id or not lbl:
            QMessageBox.warning(self, "Required", "Vehicle and Location label are required.")
            return
        ping, err = GPSIntegrationManager.record_manual_checkin(
            session=self.db_session,
            vehicle_id=v_id,
            latitude=self.lat_spin.value(),
            longitude=self.lon_spin.value(),
            location_label=lbl,
            speed_kmh=self.speed_spin.value(),
        )
        if err:
            QMessageBox.warning(self, "Error", err)
            return
        self.accept()
