"""
EduManage Pro - Fee Structure Dialog (PySide6)
Create fee rates and batch-assign to entire classes.
"""

from datetime import date
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDoubleSpinBox, QDateEdit, QCheckBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QDate
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.repositories.academic_repository import AcademicRepository
from app.repositories.fee_repository import FeeRepository
from app.services.fee_service import FeeService


class FeeStructureDialog(QDialog):
    def __init__(self, parent=None, default_class_id: int = None):
        super().__init__(parent)
        self.default_class_id = default_class_id
        self.setWindowTitle("Create Fee Rate Structure")
        self.setFixedSize(460, 480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Fee Structure Configuration")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E3A8A;")
        layout.addWidget(header)

        # Category
        layout.addWidget(QLabel("Fee Category *"))
        self.cat_combo = QComboBox()
        layout.addWidget(self.cat_combo)

        # Class
        layout.addWidget(QLabel("Target School Class *"))
        self.class_combo = QComboBox()
        layout.addWidget(self.class_combo)

        # Title
        layout.addWidget(QLabel("Title / Description *"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. Monthly Tuition Fee - Class 10")
        layout.addWidget(self.title_edit)

        # Amount & Frequency
        h_row = QHBoxLayout()
        v_amt = QVBoxLayout()
        v_amt.addWidget(QLabel("Amount (BDT ৳) *"))
        self.amt_spin = QDoubleSpinBox()
        self.amt_spin.setRange(10.0, 500000.0)
        self.amt_spin.setValue(2500.0)
        v_amt.addWidget(self.amt_spin)
        h_row.addLayout(v_amt)

        v_freq = QVBoxLayout()
        v_freq.addWidget(QLabel("Billing Frequency"))
        self.freq_combo = QComboBox()
        self.freq_combo.addItems(["Monthly", "Quarterly", "Annual", "One-Time"])
        v_freq.addWidget(self.freq_combo)
        h_row.addLayout(v_freq)
        layout.addLayout(h_row)

        # Due Date
        layout.addWidget(QLabel("Due Date *"))
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDate(QDate.currentDate().addDays(15))
        layout.addWidget(self.due_date_edit)

        # Batch Assignment Checkbox
        self.batch_check = QCheckBox("Batch assign invoice to all active students in this class now")
        self.batch_check.setChecked(True)
        self.batch_check.setStyleSheet("font-weight: bold; color: #2563EB; margin-top: 6px;")
        layout.addWidget(self.batch_check)

        layout.addStretch()

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Create Fee Structure")
        save_btn.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 7px 16px; border-radius: 6px;")
        save_btn.clicked.connect(self._on_save)
        btn_box.addWidget(save_btn)

        layout.addLayout(btn_box)

    def _load_data(self):
        db: Session = SessionLocal()
        try:
            FeeService.seed_default_fee_categories(db)
            cats = FeeRepository.get_categories(db)
            self.cat_combo.clear()
            for c in cats:
                self.cat_combo.addItem(f"{c.name} ({c.code})", c.id)

            classes = AcademicRepository.get_classes(db)
            self.class_combo.clear()
            for cls_obj in classes:
                self.class_combo.addItem(f"{cls_obj.name} ({cls_obj.group})", cls_obj.id)

            if self.default_class_id:
                idx = self.class_combo.findData(self.default_class_id)
                if idx >= 0:
                    self.class_combo.setCurrentIndex(idx)
        finally:
            db.close()

    def _on_save(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation Error", "Fee Title is required.")
            return

        cat_id = self.cat_combo.currentData()
        class_id = self.class_combo.currentData()
        qdate = self.due_date_edit.date()
        due_d = date(qdate.year(), qdate.month(), qdate.day())

        db: Session = SessionLocal()
        try:
            curr_year = AcademicRepository.get_current_academic_year(db)
            ay_id = curr_year.id if curr_year else 1

            struct_data = {
                "title": title,
                "category_id": cat_id,
                "class_id": class_id,
                "academic_year_id": ay_id,
                "amount": self.amt_spin.value(),
                "due_date": due_d,
                "frequency": self.freq_combo.currentText()
            }

            struct = FeeRepository.create_fee_structure(db, struct_data)
            assigned_count = 0
            if self.batch_check.isChecked():
                assigned_count = FeeRepository.batch_assign_fee_structure(db, struct.id, class_id, ay_id)

            msg = f"Fee structure '{struct.title}' created successfully!"
            if assigned_count > 0:
                msg += f"\nAssigned to {assigned_count} students in this class."

            QMessageBox.information(self, "Success", msg)
            self.accept()
        finally:
            db.close()
