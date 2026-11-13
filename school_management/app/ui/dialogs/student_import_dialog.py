"""
EduManage Pro - Excel & CSV Student Import Wizard (PySide6)
Multi-step import wizard supporting .xlsx and .csv files with:
- Target class / section / academic year selection
- Live row preview
- Interactive column-to-CRM-field mapping (with smart auto-detection)
- Duplicate detection policy (Skip duplicates vs Report duplicate error)
- Validation summary and audit logging
"""

from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from app.database.connection import SessionLocal
from app.models.academic import AcademicYear, SchoolClass, Section
from app.services.student_service import IMPORT_TARGET_FIELDS, StudentService


class StudentImportDialog(QDialog):
    def __init__(self, parent=None, actor: str = "admin"):
        super().__init__(parent)
        self.actor = actor
        self.selected_file_path = ""
        self.headers = []
        self.preview_rows = []
        self.mapping_combos: Dict[int, QComboBox] = {}

        self.setWindowTitle("EduManage Pro — Student Import Wizard (Excel & CSV)")
        self.resize(840, 620)
        self._build_ui()
        self._load_reference_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        desc = QLabel(
            "Import student rosters from Excel (.xlsx) or CSV (.csv). Map source columns to EduManage "
            "fields below; duplicate Student IDs, Admission Numbers, or Student Profiles are automatically blocked."
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # File Picker Row
        file_box = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setReadOnly(True)
        self.file_input.setPlaceholderText("Select .xlsx or .csv file...")

        btn_browse = QPushButton("Browse Excel / CSV...")
        btn_browse.clicked.connect(self._browse_file)
        file_box.addWidget(self.file_input, stretch=1)
        file_box.addWidget(btn_browse)
        layout.addLayout(file_box)

        # Target Class, Section, Session, Duplicate Policy
        c_layout = QHBoxLayout()
        self.class_combo = QComboBox()
        self.section_combo = QComboBox()
        self.ay_combo = QComboBox()
        self.dup_policy_combo = QComboBox()
        self.dup_policy_combo.addItem("Skip Duplicate Students (Safe)", "skip")
        self.dup_policy_combo.addItem("Fail Row on Duplicate", "error")

        c_layout.addWidget(QLabel("Target Class*:"))
        c_layout.addWidget(self.class_combo)
        c_layout.addWidget(QLabel("Section:"))
        c_layout.addWidget(self.section_combo)
        c_layout.addWidget(QLabel("Session*:"))
        c_layout.addWidget(self.ay_combo)
        c_layout.addWidget(QLabel("Duplicates:"))
        c_layout.addWidget(self.dup_policy_combo)
        layout.addLayout(c_layout)

        # Column Mapping Table
        layout.addWidget(QLabel("Step 2: Map Spreadsheet Columns to Student CRM Fields"))
        self.mapping_table = QTableWidget(0, 3)
        self.mapping_table.setHorizontalHeaderLabels(["File Column Header", "Sample Value", "Target CRM Field"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mapping_table.setMaximumHeight(200)
        layout.addWidget(self.mapping_table)

        # Preview Table
        layout.addWidget(QLabel("Step 3: Data Preview (First 10 Rows)"))
        self.preview_table = QTableWidget(0, 0)
        self.preview_table.setMaximumHeight(140)
        layout.addWidget(self.preview_table)

        # Progress & Validation Log
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(110)
        self.log_text.setPlaceholderText("Import summary and validation diagnostics will appear here...")
        self.log_text.setStyleSheet("background-color: #0f172a; font-family: monospace; font-size: 11px;")
        layout.addWidget(self.log_text)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Close")
        btn_cancel.clicked.connect(self.reject)

        self.btn_import = QPushButton("Run Import Wizard")
        self.btn_import.setEnabled(False)
        self.btn_import.setStyleSheet(
            "background-color: #059669; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;"
        )
        self.btn_import.clicked.connect(self._run_import)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_import)
        layout.addLayout(btn_box)

    def _load_reference_data(self):
        db = SessionLocal()
        try:
            for c in db.query(SchoolClass).all():
                self.class_combo.addItem(c.name, c.id)
            self.section_combo.addItem("None", None)
            for s in db.query(Section).all():
                self.section_combo.addItem(s.name, s.id)
            for y in db.query(AcademicYear).all():
                self.ay_combo.addItem(y.name, y.id)
        finally:
            db.close()

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Student Import File",
            "",
            "Spreadsheets (*.xlsx *.xlsm *.csv);;Excel Files (*.xlsx *.xlsm);;CSV Files (*.csv)",
        )
        if not path:
            return

        try:
            inspection = StudentService.inspect_import_file(path, preview_rows=10)
        except Exception as exc:
            QMessageBox.critical(self, "Read Error", f"Could not inspect file:\n{exc}")
            return

        self.selected_file_path = path
        self.file_input.setText(path)
        self.headers = inspection["headers"]
        self.preview_rows = inspection["preview_rows"]
        suggested = inspection["suggested_mapping"]

        self.mapping_combos.clear()
        self.mapping_table.setRowCount(len(self.headers))
        first_row = self.preview_rows[0] if self.preview_rows else []

        for col_idx, header in enumerate(self.headers):
            self.mapping_table.setItem(col_idx, 0, QTableWidgetItem(header))
            sample = str(first_row[col_idx]) if col_idx < len(first_row) and first_row[col_idx] is not None else ""
            self.mapping_table.setItem(col_idx, 1, QTableWidgetItem(sample))

            combo = QComboBox()
            for field_key, label in IMPORT_TARGET_FIELDS:
                combo.addItem(label, field_key)
            default_field = suggested.get(col_idx, "ignore")
            f_idx = combo.findData(default_field)
            if f_idx >= 0:
                combo.setCurrentIndex(f_idx)
            self.mapping_combos[col_idx] = combo
            self.mapping_table.setCellWidget(col_idx, 2, combo)

        self.preview_table.setColumnCount(len(self.headers))
        self.preview_table.setHorizontalHeaderLabels(self.headers)
        self.preview_table.setRowCount(len(self.preview_rows))
        for r_idx, row in enumerate(self.preview_rows):
            for c_idx in range(len(self.headers)):
                val = str(row[c_idx]) if c_idx < len(row) and row[c_idx] is not None else ""
                self.preview_table.setItem(r_idx, c_idx, QTableWidgetItem(val))

        self.btn_import.setEnabled(bool(self.headers))
        self.progress.setValue(0)
        self.log_text.clear()
        self.log_text.append(
            f"Loaded '{path}' ({inspection['total_rows']} data row(s), {len(self.headers)} columns)."
        )

    def _run_import(self):
        class_id = self.class_combo.currentData()
        section_id = self.section_combo.currentData()
        ay_id = self.ay_combo.currentData()
        if not class_id or not ay_id:
            QMessageBox.warning(self, "Missing Selection", "Please select a target class and academic session.")
            return

        column_mapping: Dict[int, str] = {
            col_idx: combo.currentData()
            for col_idx, combo in self.mapping_combos.items()
        }
        dup_policy = self.dup_policy_combo.currentData() or "skip"

        self.progress.setValue(25)
        self.log_text.append("Running validation & duplicate checks...")
        db = SessionLocal()
        try:
            result = StudentService.import_students_with_mapping(
                db,
                file_path=self.selected_file_path,
                column_mapping=column_mapping,
                default_class_id=class_id,
                default_ay_id=ay_id,
                default_section_id=section_id,
                duplicate_policy=dup_policy,
                current_username=self.actor,
            )
            self.progress.setValue(100)
            self.log_text.append(
                f"Import Finished — Processed: {result['total_rows']} | "
                f"Imported: {result['imported']} | Skipped Duplicates: {result['skipped']} | "
                f"Errors/Warnings: {len(result['errors'])}"
            )
            if result["errors"]:
                self.log_text.append("\nDetails:\n" + "\n".join(result["errors"]))

            QMessageBox.information(
                self,
                "Import Wizard Complete",
                f"Imported: {result['imported']}\nSkipped duplicates: {result['skipped']}\nErrors/Warnings: {len(result['errors'])}",
            )
            if result["imported"] > 0:
                self.accept()
        except Exception as exc:
            self.progress.setValue(0)
            QMessageBox.critical(self, "Import Failed", f"Import failed: {exc}")
            self.log_text.append(f"Fatal Error: {exc}")
        finally:
            db.close()
