"""
EduManage Pro - Supporting Hostel Management Dialogs
PySide6 dialogs for Floors, Beds, Boarder Check-Out, Fee Payments,
Mess Plans/Menus/Logs, Visitor Check-In, Complaints, and Maintenance Work Orders.
"""

from datetime import date, datetime
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from app.models.hostel import (
    COMPLAINT_CATEGORIES,
    DAYS_OF_WEEK,
    MAINTENANCE_TYPES,
)
from app.repositories.hostel_repository import HostelRepository
from app.security.session import session as app_session


class HostelFloorDialog(QDialog):
    """Add a floor level inside a hostel building."""

    def __init__(self, parent=None, db_session=None, default_block_id=None):
        super().__init__(parent)
        self.db = db_session
        self.default_block_id = default_block_id
        self.setWindowTitle("Add Hostel Building Floor")
        self.resize(420, 290)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.block_combo = QComboBox()
        for b in HostelRepository.get_all_blocks(self.db):
            self.block_combo.addItem(f"{b.block_name} ({b.gender_type})", b.id)
        if self.default_block_id:
            idx = self.block_combo.findData(self.default_block_id)
            if idx >= 0:
                self.block_combo.setCurrentIndex(idx)
        form.addRow("Building:*", self.block_combo)

        self.floor_spin = QSpinBox()
        self.floor_spin.setRange(0, 25)
        self.floor_spin.setValue(1)
        form.addRow("Floor Number:*", self.floor_spin)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Floor 1 or Senior Wing")
        form.addRow("Floor Name:", self.name_edit)

        self.supervisor_edit = QLineEdit()
        self.supervisor_edit.setPlaceholderText("Floor In-charge / Prefect")
        form.addRow("Floor Supervisor:", self.supervisor_edit)

        self.phone_edit = QLineEdit()
        form.addRow("Supervisor Phone:", self.phone_edit)

        self.cap_spin = QSpinBox()
        self.cap_spin.setRange(0, 500)
        form.addRow("Target Capacity:", self.cap_spin)

        layout.addLayout(form)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Floor")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _save(self):
        block_id = self.block_combo.currentData()
        if not block_id:
            QMessageBox.warning(self, "Validation Error", "Please select a building.")
            return
        try:
            HostelRepository.create_floor(
                self.db,
                block_id=block_id,
                floor_number=self.floor_spin.value(),
                floor_name=self.name_edit.text().strip() or None,
                supervisor_name=self.supervisor_edit.text().strip() or None,
                supervisor_phone=self.phone_edit.text().strip() or None,
                target_capacity=self.cap_spin.value(),
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class HostelBedDialog(QDialog):
    """Add or update an individual bed unit inside a room."""

    def __init__(self, parent=None, db_session=None, bed=None, default_room_id=None):
        super().__init__(parent)
        self.db = db_session
        self.bed = bed
        self.default_room_id = default_room_id
        self.setWindowTitle("Edit Bed" if bed else "Add Room Bed")
        self.resize(410, 260)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.room_combo = QComboBox()
        for r in HostelRepository.get_all_rooms(self.db):
            b_name = r.block.block_name if r.block else "N/A"
            self.room_combo.addItem(f"{b_name} - {r.room_number}", r.id)
        if self.bed:
            idx = self.room_combo.findData(self.bed.room_id)
            if idx >= 0:
                self.room_combo.setCurrentIndex(idx)
            self.room_combo.setEnabled(False)
        elif self.default_room_id:
            idx = self.room_combo.findData(self.default_room_id)
            if idx >= 0:
                self.room_combo.setCurrentIndex(idx)
        form.addRow("Hostel Room:*", self.room_combo)

        self.bed_no_edit = QLineEdit()
        self.bed_no_edit.setPlaceholderText("e.g. Bed-1, A, Upper-1")
        if self.bed:
            self.bed_no_edit.setText(self.bed.bed_number)
        form.addRow("Bed Identifier:*", self.bed_no_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Single", "Bunk-Lower", "Bunk-Upper", "Executive"])
        if self.bed:
            self.type_combo.setCurrentText(self.bed.bed_type)
        form.addRow("Bed Type:", self.type_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Available", "Occupied", "Reserved", "Maintenance"])
        if self.bed:
            self.status_combo.setCurrentText(self.bed.status)
        form.addRow("Status:", self.status_combo)

        self.notes_edit = QLineEdit()
        if self.bed and self.bed.notes:
            self.notes_edit.setText(self.bed.notes)
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Bed")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _save(self):
        bed_no = self.bed_no_edit.text().strip()
        room_id = self.room_combo.currentData()
        if not bed_no or not room_id:
            QMessageBox.warning(self, "Validation Error", "Room and Bed Identifier are required.")
            return
        try:
            if self.bed:
                HostelRepository.update_bed(
                    self.db,
                    self.bed.id,
                    bed_number=bed_no,
                    bed_type=self.type_combo.currentText(),
                    status=self.status_combo.currentText(),
                    notes=self.notes_edit.text().strip() or None,
                )
            else:
                HostelRepository.create_bed(
                    self.db,
                    room_id=room_id,
                    bed_number=bed_no,
                    bed_type=self.type_combo.currentText(),
                    status=self.status_combo.currentText(),
                    notes=self.notes_edit.text().strip() or None,
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))


class HostelCheckOutDialog(QDialog):
    """Boarder check-out and room clearance dialog."""

    def __init__(self, parent=None, db_session=None, allocation=None):
        super().__init__(parent)
        self.db = db_session
        self.allocation = allocation
        self.setWindowTitle("Boarder Check-Out & Room Clearance")
        self.resize(430, 320)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        s_name = (
            f"{self.allocation.student.first_name} {self.allocation.student.last_name}"
            if self.allocation and self.allocation.student else "Resident"
        )
        r_no = self.allocation.room.room_number if self.allocation and self.allocation.room else "-"
        hdr = QLabel(f"Boarder: <b>{s_name}</b> | Room {r_no} ({self.allocation.bed_number if self.allocation else ''})")
        layout.addWidget(hdr)

        form = QFormLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Check-Out Date:", self.date_edit)

        self.time_edit = QLineEdit()
        self.time_edit.setText(datetime.now().strftime("%I:%M %p"))
        form.addRow("Check-Out Time:", self.time_edit)

        self.clearance_combo = QComboBox()
        self.clearance_combo.addItems(["Cleared", "Damage Charge", "Pending"])
        form.addRow("Clearance Status:", self.clearance_combo)

        self.damage_spin = QDoubleSpinBox()
        self.damage_spin.setRange(0, 100000)
        self.damage_spin.setPrefix("৳ ")
        form.addRow("Damage / Key Fee:", self.damage_spin)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(70)
        self.notes_edit.setPlaceholderText("Key handover, mattress/desk condition, final remarks...")
        form.addRow("Clearance Notes:", self.notes_edit)

        layout.addLayout(form)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Complete Check-Out")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

    def _save(self):
        if not self.allocation:
            return
        qd = self.date_edit.date()
        out_dt = date(qd.year(), qd.month(), qd.day())
        try:
            HostelRepository.check_out_boarder(
                self.db,
                allocation_id=self.allocation.id,
                check_out_date=out_dt,
                check_out_time=self.time_edit.text().strip() or None,
                clearance_status=self.clearance_combo.currentText(),
                damage_charges=self.damage_spin.value(),
                notes=self.notes_edit.toPlainText().strip() or None,
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class HostelFeePaymentDialog(QDialog):
    """Collect full or partial hostel + mess fee payment with optional discount."""

    def __init__(self, parent=None, db_session=None, charge=None):
        super().__init__(parent)
        self.db = db_session
        self.charge = charge
        self.setWindowTitle("Collect Hostel Fee Payment")
        self.resize(430, 320)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        s_name = (
            f"{self.charge.student.first_name} {self.charge.student.last_name}"
            if self.charge and self.charge.student else "Boarder"
        )
        info = QLabel(
            f"<b>{s_name}</b> | Month: {self.charge.billing_month if self.charge else ''} | "
            f"Billed: ৳ {self.charge.total_billed:,.2f} | Balance Due: ৳ {self.charge.balance_due:,.2f}"
            if self.charge else ""
        )
        layout.addWidget(info)

        form = QFormLayout()
        self.discount_spin = QDoubleSpinBox()
        self.discount_spin.setRange(0, float(self.charge.total_billed) if self.charge else 100000)
        self.discount_spin.setPrefix("৳ ")
        self.discount_spin.setValue(float(self.charge.discount or 0.0) if self.charge else 0.0)
        form.addRow("Discount:", self.discount_spin)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 200000)
        self.amount_spin.setPrefix("৳ ")
        self.amount_spin.setValue(float(self.charge.balance_due) if self.charge else 0.0)
        form.addRow("Pay Amount:*", self.amount_spin)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["Cash", "Bank Transfer", "Card", "Mobile Banking", "Cheque"])
        form.addRow("Payment Method:", self.method_combo)

        self.remarks_edit = QLineEdit()
        self.remarks_edit.setPlaceholderText("Transaction ref / warden note")
        form.addRow("Remarks:", self.remarks_edit)

        layout.addLayout(form)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        pay_btn = QPushButton("Record Payment")
        pay_btn.setDefault(True)
        pay_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(pay_btn)
        layout.addLayout(btns)

    def _save(self):
        if not self.charge:
            return
        collector = app_session.current_user.username if getattr(app_session, "current_user", None) else "admin"
        updated, err = HostelRepository.record_fee_payment(
            self.db,
            charge_id=self.charge.id,
            amount=self.amount_spin.value(),
            payment_method=self.method_combo.currentText(),
            discount=self.discount_spin.value(),
            collected_by=collector,
            remarks=self.remarks_edit.text().strip() or None,
        )
        if err:
            QMessageBox.warning(self, "Payment Error", err)
            return
        QMessageBox.information(self, "Receipt Issued", f"Payment recorded.\nReceipt: {updated.receipt_no or 'N/A'}")
        self.accept()


class HostelMessPlanDialog(QDialog):
    """Create a hostel mess / dining subscription plan."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Create Hostel Mess Plan")
        self.resize(410, 290)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Full Board Dining, Two-Meal Plan")
        form.addRow("Plan Name:*", self.name_edit)

        self.fee_spin = QDoubleSpinBox()
        self.fee_spin.setRange(0, 50000)
        self.fee_spin.setPrefix("৳ ")
        self.fee_spin.setValue(2500.0)
        form.addRow("Monthly Mess Fee:", self.fee_spin)

        self.chk_bf = QCheckBox("Breakfast")
        self.chk_bf.setChecked(True)
        self.chk_ln = QCheckBox("Lunch")
        self.chk_ln.setChecked(True)
        self.chk_sn = QCheckBox("Evening Snacks")
        self.chk_sn.setChecked(True)
        self.chk_dn = QCheckBox("Dinner")
        self.chk_dn.setChecked(True)

        meals_row = QHBoxLayout()
        meals_row.addWidget(self.chk_bf)
        meals_row.addWidget(self.chk_ln)
        meals_row.addWidget(self.chk_sn)
        meals_row.addWidget(self.chk_dn)
        form.addRow("Included Meals:", meals_row)

        self.desc_edit = QLineEdit()
        form.addRow("Description:", self.desc_edit)
        layout.addLayout(form)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Mess Plan")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Plan Name cannot be empty.")
            return
        try:
            HostelRepository.create_mess_plan(
                self.db,
                plan_name=name,
                monthly_fee=self.fee_spin.value(),
                includes_breakfast=self.chk_bf.isChecked(),
                includes_lunch=self.chk_ln.isChecked(),
                includes_snacks=self.chk_sn.isChecked(),
                includes_dinner=self.chk_dn.isChecked(),
                description=self.desc_edit.text().strip() or None,
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class HostelMessMenuDialog(QDialog):
    """Add an entry to the weekly hostel mess dining menu."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Add Mess Weekly Menu Item")
        self.resize(430, 300)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.block_combo = QComboBox()
        self.block_combo.addItem("All Hostel Buildings", None)
        for b in HostelRepository.get_all_blocks(self.db):
            self.block_combo.addItem(b.block_name, b.id)
        form.addRow("Hostel Building:", self.block_combo)

        self.day_combo = QComboBox()
        self.day_combo.addItems(DAYS_OF_WEEK)
        form.addRow("Day of Week:*", self.day_combo)

        self.meal_combo = QComboBox()
        self.meal_combo.addItems(["Breakfast", "Lunch", "Snacks", "Dinner"])
        form.addRow("Meal Slot:*", self.meal_combo)

        self.time_edit = QLineEdit()
        self.time_edit.setPlaceholderText("e.g., 07:30 AM - 08:45 AM")
        form.addRow("Serving Time:", self.time_edit)

        self.items_edit = QTextEdit()
        self.items_edit.setMaximumHeight(80)
        self.items_edit.setPlaceholderText("Paratha, Egg Omelette, Milk / Tea...")
        form.addRow("Menu Items:*", self.items_edit)

        layout.addLayout(form)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Menu Entry")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _save(self):
        items = self.items_edit.toPlainText().strip()
        if not items:
            QMessageBox.warning(self, "Validation Error", "Menu items cannot be empty.")
            return
        try:
            HostelRepository.add_mess_menu_item(
                self.db,
                day_of_week=self.day_combo.currentText(),
                meal_type=self.meal_combo.currentText(),
                menu_items=items,
                serving_time=self.time_edit.text().strip() or None,
                block_id=self.block_combo.currentData(),
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class HostelMessLogDialog(QDialog):
    """Record daily mess meal service count and kitchen cost."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Log Daily Mess Service")
        self.resize(410, 290)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Service Date:", self.date_edit)

        self.block_combo = QComboBox()
        self.block_combo.addItem("Central Dining Hall", None)
        for b in HostelRepository.get_all_blocks(self.db):
            self.block_combo.addItem(b.block_name, b.id)
        form.addRow("Building / Mess:", self.block_combo)

        self.meal_combo = QComboBox()
        self.meal_combo.addItems(["Breakfast", "Lunch", "Snacks", "Dinner"])
        form.addRow("Meal Type:*", self.meal_combo)

        self.plates_spin = QSpinBox()
        self.plates_spin.setRange(1, 5000)
        self.plates_spin.setValue(60)
        form.addRow("Plates Served:*", self.plates_spin)

        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 500000)
        self.cost_spin.setPrefix("৳ ")
        form.addRow("Meal Cost:", self.cost_spin)

        self.remarks_edit = QLineEdit()
        form.addRow("Remarks:", self.remarks_edit)

        layout.addLayout(form)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Mess Log")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _save(self):
        qd = self.date_edit.date()
        log_dt = date(qd.year(), qd.month(), qd.day())
        try:
            HostelRepository.add_mess_log(
                self.db,
                meal_type=self.meal_combo.currentText(),
                plates_served=self.plates_spin.value(),
                meal_cost=self.cost_spin.value(),
                block_id=self.block_combo.currentData(),
                log_date=log_dt,
                remarks=self.remarks_edit.text().strip() or None,
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class HostelVisitorDialog(QDialog):
    """Visitor check-in modal linked to a resident boarder."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Check In Hostel Visitor")
        self.resize(450, 380)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.alloc_combo = QComboBox()
        self.alloc_combo.addItem("— General Hostel Visit —", None)
        for a in HostelRepository.get_active_allocations(self.db):
            s_name = f"{a.student.first_name} {a.student.last_name}" if a.student else f"Student #{a.student_id}"
            r_no = a.room.room_number if a.room else "-"
            self.alloc_combo.addItem(f"{s_name} (Room {r_no}, {a.bed_number})", a.id)
        form.addRow("Visiting Boarder:", self.alloc_combo)

        self.visitor_edit = QLineEdit()
        self.visitor_edit.setPlaceholderText("Full Name of Visitor")
        form.addRow("Visitor Name:*", self.visitor_edit)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+880 17...")
        form.addRow("Phone:*", self.phone_edit)

        self.rel_combo = QComboBox()
        self.rel_combo.setEditable(True)
        self.rel_combo.addItems(["Parent", "Guardian", "Sibling", "Relative", "Official"])
        form.addRow("Relationship:", self.rel_combo)

        self.id_type_combo = QComboBox()
        self.id_type_combo.addItems(["NID", "Passport", "Driving License", "Other"])
        form.addRow("ID Proof Type:", self.id_type_combo)

        self.id_no_edit = QLineEdit()
        form.addRow("ID Number:", self.id_no_edit)

        self.purpose_edit = QLineEdit()
        self.purpose_edit.setPlaceholderText("e.g., Monthly allowance & family visit")
        form.addRow("Visit Purpose:*", self.purpose_edit)

        self.approved_edit = QLineEdit()
        self.approved_edit.setText("Warden On Duty")
        form.addRow("Approved By:", self.approved_edit)

        layout.addLayout(form)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Check In Visitor")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _save(self):
        v_name = self.visitor_edit.text().strip()
        v_phone = self.phone_edit.text().strip()
        purpose = self.purpose_edit.text().strip()
        if not v_name or not v_phone or not purpose:
            QMessageBox.warning(self, "Validation Error", "Visitor Name, Phone, and Purpose are required.")
            return
        try:
            HostelRepository.check_in_visitor(
                self.db,
                visitor_name=v_name,
                visitor_phone=v_phone,
                purpose=purpose,
                allocation_id=self.alloc_combo.currentData(),
                relationship_to_student=self.rel_combo.currentText().strip() or "Parent",
                id_proof_type=self.id_type_combo.currentText(),
                id_proof_no=self.id_no_edit.text().strip() or None,
                approved_by=self.approved_edit.text().strip() or None,
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class HostelComplaintDialog(QDialog):
    """Log a new hostel boarder complaint."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Log Hostel Complaint")
        self.resize(460, 380)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.alloc_combo = QComboBox()
        self.alloc_combo.addItem("— General Building Issue —", None)
        for a in HostelRepository.get_active_allocations(self.db):
            s_name = f"{a.student.first_name} {a.student.last_name}" if a.student else f"Student #{a.student_id}"
            r_no = a.room.room_number if a.room else "-"
            self.alloc_combo.addItem(f"{s_name} (Room {r_no})", a.id)
        form.addRow("Resident / Room:", self.alloc_combo)

        self.block_combo = QComboBox()
        self.block_combo.addItem("Auto from Resident / None", None)
        for b in HostelRepository.get_all_blocks(self.db):
            self.block_combo.addItem(b.block_name, b.id)
        form.addRow("Building:", self.block_combo)

        self.cat_combo = QComboBox()
        self.cat_combo.addItems(COMPLAINT_CATEGORIES)
        form.addRow("Category:", self.cat_combo)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Urgent"])
        self.priority_combo.setCurrentText("Medium")
        form.addRow("Priority:", self.priority_combo)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g., Ceiling fan noise / Water tap leaking")
        form.addRow("Complaint Title:*", self.title_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(90)
        self.desc_edit.setPlaceholderText("Detailed description of issue...")
        form.addRow("Description:*", self.desc_edit)

        self.assigned_edit = QLineEdit()
        self.assigned_edit.setPlaceholderText("Warden / Floor Prefect / Technician")
        form.addRow("Assign To:", self.assigned_edit)

        layout.addLayout(form)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Submit Complaint")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _save(self):
        title = self.title_edit.text().strip()
        desc = self.desc_edit.toPlainText().strip()
        if not title or not desc:
            QMessageBox.warning(self, "Validation Error", "Title and Description are required.")
            return
        try:
            HostelRepository.create_complaint(
                self.db,
                title=title,
                description=desc,
                category=self.cat_combo.currentText(),
                priority=self.priority_combo.currentText(),
                block_id=self.block_combo.currentData(),
                allocation_id=self.alloc_combo.currentData(),
                assigned_to=self.assigned_edit.text().strip() or None,
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class HostelMaintenanceDialog(QDialog):
    """Create a hostel maintenance work order (optionally linked to a complaint)."""

    def __init__(self, parent=None, db_session=None, complaint=None):
        super().__init__(parent)
        self.db = db_session
        self.complaint = complaint
        self.setWindowTitle("Escalate Complaint to Maintenance" if complaint else "Create Hostel Maintenance Work Order")
        self.resize(470, 440)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.block_combo = QComboBox()
        for b in HostelRepository.get_all_blocks(self.db):
            self.block_combo.addItem(b.block_name, b.id)
        if self.complaint and self.complaint.block_id:
            idx = self.block_combo.findData(self.complaint.block_id)
            if idx >= 0:
                self.block_combo.setCurrentIndex(idx)
        self.block_combo.currentIndexChanged.connect(self._reload_rooms)
        form.addRow("Hostel Building:*", self.block_combo)

        self.room_combo = QComboBox()
        self.room_combo.currentIndexChanged.connect(self._reload_beds)
        form.addRow("Room (Optional):", self.room_combo)

        self.bed_combo = QComboBox()
        form.addRow("Bed (Optional):", self.bed_combo)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g., Replace MCB breaker & wiring")
        if self.complaint:
            self.title_edit.setText(self.complaint.title)
        form.addRow("Work Order Title:*", self.title_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(MAINTENANCE_TYPES)
        form.addRow("Maintenance Type:", self.type_combo)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Urgent"])
        if self.complaint:
            self.priority_combo.setCurrentText(self.complaint.priority)
        form.addRow("Priority:", self.priority_combo)

        self.tech_edit = QLineEdit()
        self.tech_edit.setPlaceholderText("Technician / Contractor Name")
        form.addRow("Technician / Vendor:", self.tech_edit)

        self.est_spin = QDoubleSpinBox()
        self.est_spin.setRange(0, 500000)
        self.est_spin.setPrefix("৳ ")
        form.addRow("Estimated Cost:", self.est_spin)

        self.sched_edit = QDateEdit()
        self.sched_edit.setCalendarPopup(True)
        self.sched_edit.setDate(QDate.currentDate())
        form.addRow("Scheduled Date:", self.sched_edit)

        self.block_occ_check = QCheckBox("Mark Room / Bed as 'Maintenance' (blocks new bed allocations)")
        form.addRow("Occupancy Block:", self.block_occ_check)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(65)
        if self.complaint:
            self.notes_edit.setPlainText(f"From {self.complaint.complaint_no}: {self.complaint.description}")
        form.addRow("Work Notes:", self.notes_edit)

        layout.addLayout(form)
        self._reload_rooms()
        if self.complaint and self.complaint.room_id:
            idx = self.room_combo.findData(self.complaint.room_id)
            if idx >= 0:
                self.room_combo.setCurrentIndex(idx)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Create Work Order")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _reload_rooms(self):
        self.room_combo.clear()
        self.room_combo.addItem("— Whole Building / Common Area —", None)
        block_id = self.block_combo.currentData()
        if block_id:
            for r in HostelRepository.get_all_rooms(self.db, block_id=block_id):
                self.room_combo.addItem(f"{r.room_number} ({r.status})", r.id)
        self._reload_beds()

    def _reload_beds(self):
        self.bed_combo.clear()
        self.bed_combo.addItem("— Entire Room / Not Bed-Specific —", None)
        room_id = self.room_combo.currentData()
        if room_id:
            for b in HostelRepository.get_beds(self.db, room_id=room_id):
                self.bed_combo.addItem(f"{b.bed_number} ({b.status})", b.id)

    def _save(self):
        block_id = self.block_combo.currentData()
        title = self.title_edit.text().strip()
        if not block_id or not title:
            QMessageBox.warning(self, "Validation Error", "Building and Work Order Title are required.")
            return
        qd = self.sched_edit.date()
        sched_dt = date(qd.year(), qd.month(), qd.day())
        try:
            HostelRepository.create_maintenance_request(
                self.db,
                block_id=block_id,
                issue_title=title,
                maintenance_type=self.type_combo.currentText(),
                priority=self.priority_combo.currentText(),
                room_id=self.room_combo.currentData(),
                bed_id=self.bed_combo.currentData(),
                complaint_id=self.complaint.id if self.complaint else None,
                vendor_or_technician=self.tech_edit.text().strip() or None,
                estimated_cost=self.est_spin.value(),
                scheduled_date=sched_dt,
                blocks_occupancy=self.block_occ_check.isChecked(),
                notes=self.notes_edit.toPlainText().strip() or None,
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
