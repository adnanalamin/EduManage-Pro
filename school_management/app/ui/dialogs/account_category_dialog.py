"""
EduManage Pro - Account Category Dialog (PySide6)
Modal dialog to manage Chart of Accounts categories and expenditure heads.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QComboBox, QTextEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
from app.database.connection import SessionLocal
from app.repositories.accounting_repository import AccountingRepository


class AccountCategoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Account Head / Category — EduManage Pro")
        self.setMinimumWidth(440)
        self.setModal(True)
        self.created_category = None

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Create Chart of Accounts Head")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #3b82f6;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Expense", "Income"])
        form.addRow("Category Type *:", self.type_combo)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Science Laboratory Reagents")
        form.addRow("Category Name *:", self.name_edit)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g. EXP-SCI-01")
        form.addRow("Account Code *:", self.code_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(65)
        self.desc_edit.setPlaceholderText("Optional description of the purpose of this accounting head")
        form.addRow("Description:", self.desc_edit)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Create Category")
        self.save_btn.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 6px 16px;")
        self.save_btn.clicked.connect(self._handle_save)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    def _handle_save(self):
        name = self.name_edit.text().strip()
        code = self.code_edit.text().strip().upper()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Category name is required.")
            return
        if not code:
            QMessageBox.warning(self, "Validation Error", "Category code is required.")
            return

        db = SessionLocal()
        try:
            if AccountingRepository.get_category_by_name(db, name):
                QMessageBox.warning(self, "Duplicate Error", f"A category with name '{name}' already exists.")
                return
            if AccountingRepository.get_category_by_code(db, code):
                QMessageBox.warning(self, "Duplicate Error", f"A category with code '{code}' already exists.")
                return

            cat = AccountingRepository.create_category(db, {
                "name": name,
                "code": code,
                "type": self.type_combo.currentText(),
                "description": self.desc_edit.toPlainText().strip() or None,
                "is_system": False,
                "is_active": True
            })
            self.created_category = cat
            QMessageBox.information(self, "Success", f"Account Category '{name}' created successfully.")
            self.accept()
        finally:
            db.close()
