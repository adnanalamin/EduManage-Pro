"""
EduManage Pro - Hostel Block / Building Dialog
PySide6 Modal for Adding & Editing Hostel Buildings
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QSpinBox, QPushButton, QMessageBox, QTextEdit
)
from app.repositories.hostel_repository import HostelRepository
from app.models.staff import Staff


class HostelBlockDialog(QDialog):
    """Dialog to register or edit a residential hostel building / block."""

    def __init__(self, parent=None, db_session=None, block=None):
        super().__init__(parent)
        self.db = db_session
        self.block = block
        self.setWindowTitle("Edit Hostel Building" if block else "Add New Hostel Building")
        self.resize(470, 440)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g., HST-B1")
        if self.block and getattr(self.block, "block_code", None):
            self.code_edit.setText(self.block.block_code)
        form.addRow("Building Code:", self.code_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Iqbal Hall (Boys Block A)")
        if self.block:
            self.name_edit.setText(self.block.block_name)
        form.addRow("Building / Hall Name:*", self.name_edit)

        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Boys", "Girls", "Co-ed"])
        if self.block:
            self.gender_combo.setCurrentText(self.block.gender_type)
        form.addRow("Gender Type:*", self.gender_combo)

        self.warden_staff_combo = QComboBox()
        self.warden_staff_combo.addItem("— Manual / External Warden —", None)
        if self.db is not None:
            staff_list = self.db.query(Staff).filter(Staff.is_deleted == False).order_by(Staff.full_name.asc()).all()
            for st in staff_list:
                self.warden_staff_combo.addItem(f"{st.full_name} ({st.position})", (st.id, st.full_name, st.phone))
        if self.block and getattr(self.block, "warden_staff_id", None):
            for idx in range(self.warden_staff_combo.count()):
                data = self.warden_staff_combo.itemData(idx)
                if isinstance(data, tuple) and data[0] == self.block.warden_staff_id:
                    self.warden_staff_combo.setCurrentIndex(idx)
                    break
        self.warden_staff_combo.currentIndexChanged.connect(self._on_staff_selected)
        form.addRow("Staff Warden (Optional):", self.warden_staff_combo)

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
        self.floors_spin.setRange(1, 25)
        self.floors_spin.setValue(self.block.total_floors if self.block else 3)
        form.addRow("Total Floors:", self.floors_spin)

        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("Campus Location / Address")
        if self.block and self.block.address:
            self.address_edit.setText(self.block.address)
        form.addRow("Location / Address:", self.address_edit)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Maintenance", "Closed"])
        if self.block:
            self.status_combo.setCurrentText(self.block.status)
        form.addRow("Status:", self.status_combo)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(65)
        self.notes_edit.setPlaceholderText("Curfew rules, building amenities, emergency remarks...")
        if self.block and getattr(self.block, "notes", None):
            self.notes_edit.setPlainText(self.block.notes)
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Building")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _on_staff_selected(self):
        data = self.warden_staff_combo.currentData()
        if isinstance(data, tuple):
            _, name, phone = data
            if name:
                self.warden_edit.setText(name)
            if phone:
                self.phone_edit.setText(phone)

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Building Name cannot be empty.")
            return

        staff_data = self.warden_staff_combo.currentData()
        staff_id = staff_data[0] if isinstance(staff_data, tuple) else None

        try:
            if self.block:
                HostelRepository.update_block(
                    self.db,
                    self.block.id,
                    block_code=self.code_edit.text().strip() or None,
                    block_name=name,
                    gender_type=self.gender_combo.currentText(),
                    warden_staff_id=staff_id,
                    warden_name=self.warden_edit.text().strip() or None,
                    warden_phone=self.phone_edit.text().strip() or None,
                    total_floors=self.floors_spin.value(),
                    address=self.address_edit.text().strip() or None,
                    status=self.status_combo.currentText(),
                    notes=self.notes_edit.toPlainText().strip() or None,
                )
            else:
                HostelRepository.create_block(
                    self.db,
                    block_code=self.code_edit.text().strip() or None,
                    block_name=name,
                    gender_type=self.gender_combo.currentText(),
                    warden_staff_id=staff_id,
                    warden_name=self.warden_edit.text().strip() or None,
                    warden_phone=self.phone_edit.text().strip() or None,
                    total_floors=self.floors_spin.value(),
                    address=self.address_edit.text().strip() or None,
                    status=self.status_combo.currentText(),
                    notes=self.notes_edit.toPlainText().strip() or None,
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))

