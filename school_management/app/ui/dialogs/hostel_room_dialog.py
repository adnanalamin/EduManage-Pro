"""
EduManage Pro - Hostel Room Dialog
Phase 12: PySide6 Modal for Adding & Editing Hostel Rooms
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QPushButton, QMessageBox
)
from app.repositories.hostel_repository import HostelRepository


class HostelRoomDialog(QDialog):
    """Dialog to create or edit a hostel room within a designated block."""

    def __init__(self, parent=None, db_session=None, room=None, default_block_id=None):
        super().__init__(parent)
        self.db = db_session
        self.room = room
        self.default_block_id = default_block_id
        self.setWindowTitle("Edit Hostel Room" if room else "Add Hostel Room")
        self.resize(440, 360)
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

        form.addRow("Hostel Block:*", self.block_combo)

        self.room_no_edit = QLineEdit()
        self.room_no_edit.setPlaceholderText("e.g. A-101, B-204")
        if self.room:
            self.room_no_edit.setText(self.room.room_number)
        form.addRow("Room Number:*", self.room_no_edit)

        self.floor_spin = QSpinBox()
        self.floor_spin.setRange(0, 20)
        self.floor_spin.setValue(self.room.floor_number if self.room else 1)
        form.addRow("Floor Number:", self.floor_spin)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Single", "Double", "Triple", "4-Bed Dorm", "6-Bed Dorm"])
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
        form.addRow("Monthly Fee:", self.fee_spin)

        self.amenities_edit = QLineEdit()
        self.amenities_edit.setPlaceholderText("Attached Bath, Study Table, Wi-Fi")
        self.amenities_edit.setText(self.room.amenities if self.room else "Attached Bath, Study Table, Wi-Fi")
        form.addRow("Amenities:", self.amenities_edit)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Available", "Full", "Maintenance"])
        if self.room:
            self.status_combo.setCurrentText(self.room.status)
        form.addRow("Status:", self.status_combo)

        layout.addLayout(form)

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

    def _on_type_changed(self, text):
        if not self.room:
            if text == "Single":
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
            QMessageBox.warning(self, "Validation Error", "Please select a Hostel Block.")
            return

        try:
            if self.room:
                HostelRepository.update_room(
                    self.db,
                    self.room.id,
                    block_id=block_id,
                    room_number=room_no,
                    floor_number=self.floor_spin.value(),
                    room_type=self.type_combo.currentText(),
                    capacity=self.capacity_spin.value(),
                    monthly_fee=self.fee_spin.value(),
                    amenities=self.amenities_edit.text().strip() or "Standard",
                    status=self.status_combo.currentText()
                )
            else:
                HostelRepository.create_room(
                    self.db,
                    block_id=block_id,
                    room_number=room_no,
                    floor_number=self.floor_spin.value(),
                    room_type=self.type_combo.currentText(),
                    capacity=self.capacity_spin.value(),
                    monthly_fee=self.fee_spin.value(),
                    amenities=self.amenities_edit.text().strip() or "Standard",
                    status=self.status_combo.currentText()
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))
