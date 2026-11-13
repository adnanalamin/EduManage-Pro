"""
EduManage Pro - Student Batch Promotion & Graduation Dialog (PySide6)
Supports annual batch promotion, optional graduation, sequential roll re-assignment,
and strict historical record preservation across academic years.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.database.connection import SessionLocal
from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.student import Student, StudentStatus
from app.services.academic_service import AcademicService


class StudentPromoteDialog(QDialog):
    def __init__(self, parent=None, actor: str = "admin"):
        super().__init__(parent)
        self.actor = actor
        self.setWindowTitle("EduManage Pro — Student Academic Promotion & Graduation")
        self.setFixedSize(760, 580)
        self._build_ui()
        self._load_reference_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        banner = QLabel(
            "Promote selected students to a target Academic Session & Class, or mark graduating seniors as Graduated. "
            "All previous academic year history & marks remain strictly preserved."
        )
        banner.setWordWrap(True)
        banner.setStyleSheet(
            "background-color: #EFF6FF; color: #1E3A8A; padding: 10px; border-radius: 6px; border: 1px solid #BFDBFE;"
        )
        layout.addWidget(banner)

        row_src = QHBoxLayout()
        self.from_class_combo = QComboBox()
        self.from_class_combo.currentIndexChanged.connect(self._load_students)
        row_src.addWidget(QLabel("Source Class:"))
        row_src.addWidget(self.from_class_combo, stretch=1)

        self.graduated_chk = QCheckBox("Mark Selected Students as Graduated")
        self.graduated_chk.toggled.connect(self._on_grad_toggled)
        row_src.addWidget(self.graduated_chk)
        layout.addLayout(row_src)

        top_grid = QHBoxLayout()
        self.to_ay_combo = QComboBox()
        self.to_ay_combo.currentIndexChanged.connect(self._on_target_year_changed)
        self.to_class_combo = QComboBox()
        self.to_class_combo.currentIndexChanged.connect(self._on_target_class_changed)
        self.to_section_combo = QComboBox()

        top_grid.addWidget(QLabel("Target Session:"))
        top_grid.addWidget(self.to_ay_combo)
        top_grid.addWidget(QLabel("Promote To Class:"))
        top_grid.addWidget(self.to_class_combo)
        top_grid.addWidget(QLabel("Target Section:"))
        top_grid.addWidget(self.to_section_combo)
        layout.addLayout(top_grid)

        roll_row = QHBoxLayout()
        self.auto_roll_chk = QCheckBox("Re-assign Sequential Rolls Starting From:")
        self.start_roll_spin = QSpinBox()
        self.start_roll_spin.setRange(1, 9999)
        self.start_roll_spin.setValue(1)
        self.start_roll_spin.setEnabled(False)
        self.auto_roll_chk.toggled.connect(self.start_roll_spin.setEnabled)

        self.remarks_input = QLineEdit("Year-end batch promotion")
        roll_row.addWidget(self.auto_roll_chk)
        roll_row.addWidget(self.start_roll_spin)
        roll_row.addSpacing(12)
        roll_row.addWidget(QLabel("Remarks:"))
        roll_row.addWidget(self.remarks_input, stretch=1)
        layout.addLayout(roll_row)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Select", "Roll", "Student ID", "Full Name", "Current Session"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        sel_row = QHBoxLayout()
        btn_sel_all = QPushButton("Select All")
        btn_sel_all.clicked.connect(self._select_all)
        btn_desel_all = QPushButton("Deselect All")
        btn_desel_all.clicked.connect(self._deselect_all)
        sel_row.addWidget(btn_sel_all)
        sel_row.addWidget(btn_desel_all)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        self.btn_promote = QPushButton("Execute Batch Promotion")
        self.btn_promote.setStyleSheet(
            "background-color: #7c3aed; color: white; padding: 8px 18px; font-weight: bold; border-radius: 6px;"
        )
        self.btn_promote.clicked.connect(self._run_promotion)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_promote)
        layout.addLayout(btn_box)

    def _on_grad_toggled(self, checked: bool):
        self.to_ay_combo.setEnabled(not checked)
        self.to_class_combo.setEnabled(not checked)
        self.to_section_combo.setEnabled(not checked)
        self.auto_roll_chk.setEnabled(not checked)
        self.start_roll_spin.setEnabled((not checked) and self.auto_roll_chk.isChecked())
        self.btn_promote.setText("Graduate Selected Students" if checked else "Execute Batch Promotion")
        if checked:
            self.remarks_input.setText("Graduated upon completing academic level")
        else:
            self.remarks_input.setText("Year-end batch promotion")

    def _load_reference_data(self):
        db = SessionLocal()
        try:
            self.from_class_combo.blockSignals(True)
            self.from_class_combo.clear()
            classes = (
                db.query(SchoolClass)
                .filter(SchoolClass.is_deleted == False)
                .order_by(SchoolClass.academic_year_id.desc(), SchoolClass.numeric_order.asc())
                .all()
            )
            for c in classes:
                yr_name = c.academic_year.name if c.academic_year else "-"
                self.from_class_combo.addItem(f"{c.name} ({c.group}) — {yr_name}", c.id)
            self.from_class_combo.blockSignals(False)

            self.to_ay_combo.blockSignals(True)
            self.to_ay_combo.clear()
            years = db.query(AcademicYear).filter(AcademicYear.is_deleted == False).order_by(AcademicYear.start_date.desc()).all()
            for y in years:
                self.to_ay_combo.addItem(f"{y.name} ({y.status})", y.id)
            self.to_ay_combo.blockSignals(False)
        finally:
            db.close()

        self._on_target_year_changed()
        self._load_students()

    def _on_target_year_changed(self):
        ay_id = self.to_ay_combo.currentData()
        db = SessionLocal()
        try:
            self.to_class_combo.blockSignals(True)
            self.to_class_combo.clear()
            q = db.query(SchoolClass).filter(SchoolClass.is_deleted == False)
            if ay_id:
                q = q.filter(SchoolClass.academic_year_id == ay_id)
            for c in q.order_by(SchoolClass.numeric_order.asc()).all():
                self.to_class_combo.addItem(f"{c.name} ({c.group} / {c.shift})", c.id)
            self.to_class_combo.blockSignals(False)
        finally:
            db.close()
        self._on_target_class_changed()

    def _on_target_class_changed(self):
        cls_id = self.to_class_combo.currentData()
        db = SessionLocal()
        try:
            self.to_section_combo.clear()
            self.to_section_combo.addItem("Keep Existing / Unassigned", None)
            if cls_id:
                for s in db.query(Section).filter(Section.class_id == cls_id, Section.is_deleted == False).all():
                    self.to_section_combo.addItem(f"{s.name} ({s.shift})", s.id)
        finally:
            db.close()

    def _load_students(self):
        from_id = self.from_class_combo.currentData()
        if not from_id:
            self.table.setRowCount(0)
            return
        db = SessionLocal()
        try:
            students = (
                db.query(Student)
                .filter(
                    Student.class_id == from_id,
                    Student.status == StudentStatus.ACTIVE,
                    Student.is_deleted == False,
                )
                .order_by(Student.roll_number)
                .all()
            )

            self.table.setRowCount(len(students))
            for i, s in enumerate(students):
                cb_item = QTableWidgetItem()
                cb_item.setCheckState(Qt.Checked)
                cb_item.setData(Qt.UserRole, s.id)
                self.table.setItem(i, 0, cb_item)
                self.table.setItem(i, 1, QTableWidgetItem(str(s.roll_number)))
                self.table.setItem(i, 2, QTableWidgetItem(s.student_id))
                self.table.setItem(i, 3, QTableWidgetItem(s.full_name))
                yr_name = s.academic_year.name if s.academic_year else "-"
                self.table.setItem(i, 4, QTableWidgetItem(yr_name))
        finally:
            db.close()

    def _select_all(self):
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item:
                item.setCheckState(Qt.Checked)

    def _deselect_all(self):
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item:
                item.setCheckState(Qt.Unchecked)

    def _run_promotion(self):
        selected_ids = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item and item.checkState() == Qt.Checked:
                selected_ids.append(item.data(Qt.UserRole))

        if not selected_ids:
            QMessageBox.warning(self, "No Selection", "Please select at least one student.")
            return

        mark_grad = self.graduated_chk.isChecked()
        to_class = self.to_class_combo.currentData()
        to_section = self.to_section_combo.currentData()
        to_ay = self.to_ay_combo.currentData()
        remarks = self.remarks_input.text().strip() or (
            "Graduated" if mark_grad else "Year-end batch promotion"
        )

        if not mark_grad and (not to_class or not to_ay):
            QMessageBox.warning(self, "Validation Error", "Target Academic Session and Class are required.")
            return

        action_label = "graduate" if mark_grad else f"promote to {self.to_class_combo.currentText()} ({self.to_ay_combo.currentText()})"
        confirm = QMessageBox.question(
            self,
            "Confirm Academic Promotion",
            f"Proceed to {action_label} for {len(selected_ids)} student(s)?\n"
            "Previous academic year records will remain intact.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            db = SessionLocal()
            try:
                ok, count, msg = AcademicService.bulk_promote_students(
                    db,
                    student_ids=selected_ids,
                    to_class_id=to_class,
                    to_academic_year_id=to_ay,
                    to_section_id=to_section,
                    auto_assign_rolls=self.auto_roll_chk.isChecked(),
                    starting_roll=self.start_roll_spin.value(),
                    mark_graduated=mark_grad,
                    remarks=remarks,
                    current_user=self.actor,
                )
                if ok:
                    QMessageBox.information(self, "Success", msg)
                    self.accept()
                else:
                    QMessageBox.warning(self, "Promotion Failed", msg)
            finally:
                db.close()
