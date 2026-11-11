"""
EduManage Pro - Hostel Block Dialog
Phase 12: PySide6 Modal for Adding & Editing Hostel Blocks
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QSpinBox, QPushButton, QMessageBox, QLabel
)
from app.repositories.hostel_repository import HostelRepository


class HostelBlockDialog(QDialog):
    """Dialog to register or edit a residential hostel block."""

    def __init__(self, parent=None, db_session=None, block=None):
        super().__init__(parent)
        self.db = db_session
        self.block = block
        self.setWindowTitle("Edit Hostel Block" if block else "Add New Hostel Block")
        self.resize(420, 320)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Iqbal Hall (Boys Block A)")
        if self.block:
            self.name_edit.setText(self.block.block_name)
        form.addRow("Block / Hall Name:*", self.name_edit)

        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Boys", "Girls", "Co-ed"])
        if self.block:
            self.gender_combo.setCurrentText(self.block.gender_type)
        form.addRow("Gender Type:*", self.gender_combo)

        self.warden_edit = QLineEdit()
        self.warden_edit.setPlaceholderText("Warden In-charge Name")
        if self.block and self.block.warden_name:
            self.warden_edit.setText(self.block.warden_name)
        form.addRow("Warden Name:", self.warden_edit)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+880 1700-000000")
        if self.block and self.block.warden_phone:
            self.phone_edit.setText(self.block.warden_phone)
        form.addRow("Warden Phone:", self.phone_edit)

        self.floors_spin = QSpinBox()
        self.floors_spin.setRange(1, 20)
        self.floors_spin.setValue(self.block.total_floors if self.block else 3)
        form.addRow("Total Floors:", self.floors_spin)

        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("Campus Location / Address")
        if self.block and self.block.address:
            self.address_edit.setText(self.block.address)
        form.addRow("Location / Address:", self.address_edit)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Maintenance"])
        if self.block:
            self.status_combo.setCurrentText(self.block.status)
        form.addRow("Status:", self.status_combo)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Block")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Block Name cannot be empty.")
            return

        try:
            if self.block:
                HostelRepository.update_block(
                    self.db,
                    self.block.id,
                    block_name=name,
                    gender_type=self.gender_combo.currentText(),
                    warden_name=self.warden_edit.text().strip() or None,
                    warden_phone=self.phone_edit.text().strip() or None,
                    total_floors=self.floors_spin.value(),
                    address=self.address_edit.text().strip() or None,
                    status=self.status_combo.currentText()
                )
            else:
                HostelRepository.create_block(
                    self.db,
                    block_name=name,
                    gender_type=self.gender_combo.currentText(),
                    warden_name=self.warden_edit.text().strip() or None,
                    warden_phone=self.phone_edit.text().strip() or None,
                    total_floors=self.floors_spin.value(),
                    address=self.address_edit.text().strip() or None,
                    status=self.status_combo.currentText()
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))
