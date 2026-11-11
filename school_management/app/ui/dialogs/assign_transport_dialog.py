"""
EduManage Pro - Assign Transport Dialog
Phase 11: PySide6 Modal for Passenger Seat & Route Allocation
"""

from datetime import date
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QDoubleSpinBox, QPushButton, QLabel, QMessageBox, QDateEdit
)
from PySide6.QtCore import QDate
from sqlalchemy.orm import Session
from app.models.transport import TransportRoute, TransportStop, TransportPassenger, Vehicle
from app.models.student import Student
from app.models.staff import Teacher
from app.repositories.transport_repository import TransportRepository


class AssignTransportDialog(QDialog):
    """Dialog for assigning students or teachers to transport routes and seats."""

    def __init__(self, db_session: Session, parent=None):
        super().__init__(parent)
        self.db_session = db_session

        self.setWindowTitle("Assign Passenger to Route & Bus Seat")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title_lbl = QLabel("Transport Commuter Allocation")
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #B45309;")
        layout.addWidget(title_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        # Passenger Type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Student", "Teacher"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Passenger Type *:", self.type_combo)

        # Person Selector
        self.person_combo = QComboBox()
        form.addRow("Select Commuter *:", self.person_combo)

        # Route Selector
        self.route_combo = QComboBox()
        routes = TransportRepository.get_routes(self.db_session, status="Active")
        for r in routes:
            v_info = f"[{r.vehicle.vehicle_number}]" if r.vehicle else "[No Bus]"
            self.route_combo.addItem(f"{r.route_code}: {r.route_name} {v_info}", r.id)
        self.route_combo.currentIndexChanged.connect(self._on_route_changed)
        form.addRow("Select Route *:", self.route_combo)

        # Boarding Stop Selector
        self.stop_combo = QComboBox()
        form.addRow("Boarding Stop:", self.stop_combo)

        # Seat Number & Monthly Fare
        seat_fare_box = QHBoxLayout()
        self.seat_input = QLineEdit()
        self.seat_input.setPlaceholderText("e.g. Seat 05A")
        seat_fare_box.addWidget(self.seat_input)

        self.fare_spin = QDoubleSpinBox()
        self.fare_spin.setRange(0.0, 50000.0)
        self.fare_spin.setPrefix("$ ")
        self.fare_spin.setValue(2500.0)
        seat_fare_box.addWidget(QLabel("Monthly Fee:"))
        seat_fare_box.addWidget(self.fare_spin)
        form.addRow("Seat & Fare:", seat_fare_box)

        # Allocation Date
        today = date.today()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate(today.year, today.month, today.day))
        form.addRow("Effective Date *:", self.date_edit)

        # Remarks
        self.remarks_input = QLineEdit()
        self.remarks_input.setPlaceholderText("Special commute or medical notes...")
        form.addRow("Remarks:", self.remarks_input)

        layout.addLayout(form)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        assign_btn = QPushButton("Confirm Allocation")
        assign_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 6px 16px;")
        assign_btn.clicked.connect(self._confirm_allocation)
        btn_layout.addWidget(assign_btn)

        layout.addLayout(btn_layout)

        # Initialize dropdowns
        self._on_type_changed()
        self._on_route_changed()

    def _on_type_changed(self):
        p_type = self.type_combo.currentText()
        self.person_combo.clear()
        if p_type == "Student":
            students = self.db_session.query(Student).filter(Student.status == "Active").order_by(Student.id.asc()).all()
            for s in students:
                cls_name = s.school_class.name if s.school_class else "-"
                self.person_combo.addItem(f"{s.student_id} - {s.full_name} (Class {cls_name})", s.id)
            self.fare_spin.setValue(2500.0)
        else:
            teachers = self.db_session.query(Teacher).filter(Teacher.status == "Active").order_by(Teacher.id.asc()).all()
            for t in teachers:
                self.person_combo.addItem(f"{t.employee_id} - {t.full_name} ({t.designation or 'Faculty'})", t.id)
            self.fare_spin.setValue(0.0)  # Free faculty transport

    def _on_route_changed(self):
        route_id = self.route_combo.currentData()
        self.stop_combo.clear()
        self.stop_combo.addItem("Default Origin Stop", None)
        if route_id:
            route = TransportRepository.get_route_by_id(self.db_session, route_id)
            if route:
                self.fare_spin.setValue(route.monthly_fee if self.type_combo.currentText() == "Student" else 0.0)
                for s in route.stops:
                    self.stop_combo.addItem(f"{s.stop_order}. {s.stop_name} (Pickup: {s.pickup_time or '-'})", s.id)

    def _confirm_allocation(self):
        person_id = self.person_combo.currentData()
        route_id = self.route_combo.currentData()

        if not person_id or not route_id:
            QMessageBox.warning(self, "Selection Required", "Please select a commuter and an active transit route.")
            return

        p_type = self.type_combo.currentText()
        student_id = person_id if p_type == "Student" else None
        teacher_id = person_id if p_type == "Teacher" else None

        q_date = self.date_edit.date()
        date_str = f"{q_date.year():04d}-{q_date.month():02d}-{q_date.day():02d}"

        passenger, err = TransportRepository.allocate_passenger(
            session=self.db_session,
            passenger_type=p_type,
            student_id=student_id,
            teacher_id=teacher_id,
            route_id=route_id,
            stop_id=self.stop_combo.currentData(),
            seat_number=self.seat_input.text().strip() or None,
            allocation_date=date_str,
            monthly_fare=self.fare_spin.value(),
            remarks=self.remarks_input.text().strip() or None
        )

        if err:
            QMessageBox.warning(self, "Allocation Error", err)
            return

        QMessageBox.information(
            self,
            "Allocation Confirmed",
            f"Passenger #{passenger.id} allocated successfully.\nMonthly transport fee: ${passenger.monthly_fare:.2f}"
        )
        self.accept()
