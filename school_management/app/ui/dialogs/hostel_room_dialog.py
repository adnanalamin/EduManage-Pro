"""
EduManage Pro - Hostel Room Dialog
PySide6 Modal for Adding & Editing Hostel Rooms with Floor Link & Bed Generation
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QPushButton, QMessageBox, QCheckBox
)
from app.models.hostel import HOSTEL_ROOM_TYPES
from app.repositories.hostel_repository import HostelRepository


class HostelRoomDialog(QDialog):
    """Dialog to create or edit a hostel room within a designated block and floor."""

    def __init__(self, parent=None, db_session=None, room=None, default_block_id=None):
        super().__init__(parent)
        self.db = db_session
        self.room = room
        self.default_block_id = default_block_id
        self.setWindowTitle("Edit Hostel Room" if room else "Add Hostel Room")
        self.resize(470, 440)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Block Selector
        self.block_combo = QComboBox()
        blocks = HostelRepository.get_all_blocks(self.db)
        for b in blocks:
            self.block_combo.addItem(f"{b.block_name} ({b.gender_type})", b.id)

        if self.room:
            idx = self.block_combo.findData(self.room.block_id)
            if idx >= 0:
                self.block_combo.setCurrentIndex(idx)
        elif self.default_block_id:
            idx = self.block_combo.findData(self.default_block_id)
            if idx >= 0:
                self.block_combo.setCurrentIndex(idx)

        self.block_combo.currentIndexChanged.connect(self._reload_floors)
        form.addRow("Hostel Building:*", self.block_combo)

        self.floor_combo = QComboBox()
        self.floor_combo.currentIndexChanged.connect(self._sync_floor_spin)
        form.addRow("Building Floor:", self.floor_combo)

        self.floor_spin = QSpinBox()
        self.floor_spin.setRange(0, 25)
        self.floor_spin.setValue(self.room.floor_number if self.room else 1)
        form.addRow("Floor Number:", self.floor_spin)

        self.room_no_edit = QLineEdit()
        self.room_no_edit.setPlaceholderText("e.g. A-101, B-204")
        if self.room:
            self.room_no_edit.setText(self.room.room_number)
        form.addRow("Room Number:*", self.room_no_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(HOSTEL_ROOM_TYPES)
        if self.room:
            self.type_combo.setCurrentText(self.room.room_type)
        else:
            self.type_combo.setCurrentText("Double")
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Room Type:", self.type_combo)

        self.capacity_spin = QSpinBox()
        self.capacity_spin.setRange(1, 20)
        self.capacity_spin.setValue(self.room.capacity if self.room else 2)
        form.addRow("Bed Capacity:*", self.capacity_spin)

        self.fee_spin = QDoubleSpinBox()
        self.fee_spin.setRange(0, 100000)
        self.fee_spin.setValue(self.room.monthly_fee if self.room else 3000.0)
        self.fee_spin.setPrefix("৳ ")
        form.addRow("Monthly Rent:", self.fee_spin)

        self.amenities_edit = QLineEdit()
        self.amenities_edit.setPlaceholderText("Attached Bath, Study Table, Wi-Fi")
        self.amenities_edit.setText(self.room.amenities if self.room else "Attached Bath, Study Table, Wi-Fi")
        form.addRow("Amenities:", self.amenities_edit)

        flags_row = QHBoxLayout()
        self.bath_check = QCheckBox("Attached Bath")
        self.bath_check.setChecked(self.room.has_attached_bath if self.room else True)
        self.ac_check = QCheckBox("Air Conditioned")
        self.ac_check.setChecked(self.room.has_ac if self.room else False)
        flags_row.addWidget(self.bath_check)
        flags_row.addWidget(self.ac_check)
        flags_row.addStretch()
        form.addRow("Facilities:", flags_row)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Available", "Full", "Maintenance"])
        if self.room:
            self.status_combo.setCurrentText(self.room.status)
        form.addRow("Status:", self.status_combo)

        layout.addLayout(form)
        self._reload_floors()

        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Room")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _reload_floors(self):
        self.floor_combo.blockSignals(True)
        self.floor_combo.clear()
        self.floor_combo.addItem("Auto-resolve from Floor Number", None)
        block_id = self.block_combo.currentData()
        if block_id:
            floors = HostelRepository.get_floors(self.db, block_id=block_id)
            for fl in floors:
                self.floor_combo.addItem(f"{fl.floor_name} (Level {fl.floor_number})", (fl.id, fl.floor_number))
            if self.room and getattr(self.room, "floor_id", None):
                for idx in range(self.floor_combo.count()):
                    data = self.floor_combo.itemData(idx)
                    if isinstance(data, tuple) and data[0] == self.room.floor_id:
                        self.floor_combo.setCurrentIndex(idx)
                        break
        self.floor_combo.blockSignals(False)

    def _sync_floor_spin(self):
        data = self.floor_combo.currentData()
        if isinstance(data, tuple):
            self.floor_spin.setValue(data[1])

    def _on_type_changed(self, text):
        if not self.room:
            if text in ("Single", "Suite"):
                self.capacity_spin.setValue(1)
            elif text == "Double":
                self.capacity_spin.setValue(2)
            elif text == "Triple":
                self.capacity_spin.setValue(3)
            elif text == "4-Bed Dorm":
                self.capacity_spin.setValue(4)
            elif text == "6-Bed Dorm":
                self.capacity_spin.setValue(6)

    def _save(self):
        room_no = self.room_no_edit.text().strip()
        if not room_no:
            QMessageBox.warning(self, "Validation Error", "Room Number cannot be empty.")
            return

        block_id = self.block_combo.currentData()
        if not block_id:
            QMessageBox.warning(self, "Validation Error", "Please select a Hostel Building.")
            return

        floor_data = self.floor_combo.currentData()
        floor_id = floor_data[0] if isinstance(floor_data, tuple) else None

        try:
            if self.room:
                HostelRepository.update_room(
                    self.db,
                    self.room.id,
                    block_id=block_id,
                    floor_id=floor_id,
                    room_number=room_no,
                    floor_number=self.floor_spin.value(),
                    room_type=self.type_combo.currentText(),
                    capacity=self.capacity_spin.value(),
                    monthly_fee=self.fee_spin.value(),
                    amenities=self.amenities_edit.text().strip() or "Standard",
                    has_attached_bath=self.bath_check.isChecked(),
                    has_ac=self.ac_check.isChecked(),
                    status=self.status_combo.currentText(),
                )
            else:
                HostelRepository.create_room(
                    self.db,
                    block_id=block_id,
                    floor_id=floor_id,
                    room_number=room_no,
                    floor_number=self.floor_spin.value(),
                    room_type=self.type_combo.currentText(),
                    capacity=self.capacity_spin.value(),
                    monthly_fee=self.fee_spin.value(),
                    amenities=self.amenities_edit.text().strip() or "Standard",
                    has_attached_bath=self.bath_check.isChecked(),
                    has_ac=self.ac_check.isChecked(),
                    status=self.status_combo.currentText(),
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))

