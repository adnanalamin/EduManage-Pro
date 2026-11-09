"""
EduManage Pro - Excel Student Import Dialog (PySide6)
Validates and batch-imports student rosters from .xlsx spreadsheets.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QFileDialog, QMessageBox, QTextEdit, QProgressBar
)
from PySide6.QtCore import Qt
from app.database.connection import SessionLocal
from app.models.academic import SchoolClass, AcademicYear
from app.services.student_service import StudentService


class StudentImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EduManage Pro — Batch Import Students from Excel (.xlsx)")
        self.setFixedSize(540, 420)
        self.selected_file_path = ""
        self._build_ui()
        self._load_classes()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        desc = QLabel(
            "Upload an Excel (.xlsx) file containing student columns:\n"
            "Columns: [Roll, First Name, Last Name, Gender, DOB (YYYY-MM-DD), Phone, Guardian Name, Guardian Phone]"
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # File Picker Row
        file_box = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setReadOnly(True)
        self.file_input.setPlaceholderText("Select .xlsx spreadsheet...")

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_file)
        file_box.addWidget(self.file_input)
        file_box.addWidget(btn_browse)
        layout.addLayout(file_box)

        # Target Class & Session
        c_layout = QHBoxLayout()
        self.class_combo = QComboBox()
        self.ay_combo = QComboBox()
        c_layout.addWidget(QLabel("Target Class:"))
        c_layout.addWidget(self.class_combo)
        c_layout.addWidget(QLabel("Session:"))
        c_layout.addWidget(self.ay_combo)
        layout.addLayout(c_layout)

        # Log Output
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Import status and validation log will appear here...")
        self.log_text.setStyleSheet("background-color: #0f172a; font-family: monospace; font-size: 11px;")
        layout.addWidget(self.log_text)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        self.btn_import = QPushButton("Start Import")
        self.btn_import.setEnabled(False)
        self.btn_import.setStyleSheet("background-color: #059669; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        self.btn_import.clicked.connect(self._run_import)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_import)
        layout.addLayout(btn_box)

    def _load_classes(self):
        db = SessionLocal()
        try:
            for c in db.query(SchoolClass).all():
                self.class_combo.addItem(c.name, c.id)
            for y in db.query(AcademicYear).all():
                self.ay_combo.addItem(y.name, y.id)
        finally:
            db.close()

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Excel Student File", "", "Excel Files (*.xlsx)")
        if path:
            self.selected_file_path = path
            self.file_input.setText(path)
            self.btn_import.setEnabled(True)
            self.log_text.append(f"Selected file: {path}")

    def _run_import(self):
        class_id = self.class_combo.currentData()
        ay_id = self.ay_combo.currentData()
        if not class_id or not ay_id:
            QMessageBox.warning(self, "Missing Selection", "Please select a target class and session.")
            return

        self.log_text.append("Parsing workbook and validating records...")
        db = SessionLocal()
        try:
            count, errors = StudentService.import_students_from_excel(db, self.selected_file_path, class_id, ay_id)
            self.log_text.append(f"Successfully imported {count} student records into database.")
            if errors:
                self.log_text.append(f"Encountered {len(errors)} validation warnings:\n" + "\n".join(errors))
            QMessageBox.information(self, "Import Completed", f"Successfully imported {count} students.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Excel import failed: {e}")
            self.log_text.append(f"Fatal Error: {e}")
        finally:
            db.close()
