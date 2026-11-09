"""
EduManage Pro - Student Batch Promotion Dialog (PySide6)
Enables annual promotion of students from current class to next academic level.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt
from app.database.connection import SessionLocal
from app.models.student import Student, StudentStatus
from app.models.academic import SchoolClass, AcademicYear
from app.repositories.student_repository import StudentRepository


class StudentPromoteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EduManage Pro — Student Academic Promotion")
        self.setFixedSize(620, 480)
        self._build_ui()
        self._load_classes()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Selection Bar
        top_grid = QHBoxLayout()
        self.from_class_combo = QComboBox()
        self.from_class_combo.currentIndexChanged.connect(self._load_students)

        self.to_class_combo = QComboBox()
        self.to_ay_combo = QComboBox()

        top_grid.addWidget(QLabel("From Class:"))
        top_grid.addWidget(self.from_class_combo)
        top_grid.addWidget(QLabel("Promote To:"))
        top_grid.addWidget(self.to_class_combo)
        top_grid.addWidget(QLabel("Session:"))
        top_grid.addWidget(self.to_ay_combo)
        layout.addLayout(top_grid)

        # Student Selection Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Select", "Roll", "Student ID", "Full Name"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # Select All / Deselect All
        sel_row = QHBoxLayout()
        btn_sel_all = QPushButton("Select All")
        btn_sel_all.clicked.connect(self._select_all)
        btn_desel_all = QPushButton("Deselect All")
        btn_desel_all.clicked.connect(self._deselect_all)
        sel_row.addWidget(btn_sel_all)
        sel_row.addWidget(btn_desel_all)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        self.btn_promote = QPushButton("Execute Batch Promotion")
        self.btn_promote.setStyleSheet("background-color: #7c3aed; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        self.btn_promote.clicked.connect(self._run_promotion)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_promote)
        layout.addLayout(btn_box)

    def _load_classes(self):
        db = SessionLocal()
        try:
            classes = db.query(SchoolClass).order_by(SchoolClass.numeric_order).all()
            for c in classes:
                self.from_class_combo.addItem(c.name, c.id)
                self.to_class_combo.addItem(c.name, c.id)

            for y in db.query(AcademicYear).all():
                self.to_ay_combo.addItem(y.name, y.id)
        finally:
            db.close()
        self._load_students()

    def _load_students(self):
        from_id = self.from_class_combo.currentData()
        if not from_id:
            return
        db = SessionLocal()
        try:
            students = db.query(Student).filter(
                Student.class_id == from_id,
                Student.status == StudentStatus.ACTIVE
            ).order_by(Student.roll_number).all()

            self.table.setRowCount(len(students))
            for i, s in enumerate(students):
                cb_item = QTableWidgetItem()
                cb_item.setCheckState(Qt.Checked)
                cb_item.setData(Qt.UserRole, s.id)
                self.table.setItem(i, 0, cb_item)
                self.table.setItem(i, 1, QTableWidgetItem(str(s.roll_number)))
                self.table.setItem(i, 2, QTableWidgetItem(s.student_id))
                self.table.setItem(i, 3, QTableWidgetItem(s.full_name))
        finally:
            db.close()

    def _select_all(self):
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item: item.setCheckState(Qt.Checked)

    def _deselect_all(self):
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item: item.setCheckState(Qt.Unchecked)

    def _run_promotion(self):
        selected_ids = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item and item.checkState() == Qt.Checked:
                selected_ids.append(item.data(Qt.UserRole))

        if not selected_ids:
            QMessageBox.warning(self, "No Selection", "Please select at least one student to promote.")
            return

        to_class = self.to_class_combo.currentData()
        to_ay = self.to_ay_combo.currentData()

        confirm = QMessageBox.question(
            self,
            "Confirm Batch Promotion",
            f"Are you sure you want to promote {len(selected_ids)} students to {self.to_class_combo.currentText()}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            db = SessionLocal()
            try:
                count = StudentRepository.bulk_promote(db, selected_ids, to_class, to_ay)
                QMessageBox.information(self, "Success", f"Successfully promoted {count} students!")
                self.accept()
            finally:
                db.close()
