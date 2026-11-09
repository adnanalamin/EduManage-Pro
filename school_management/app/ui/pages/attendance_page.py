"""
EduManage Pro - Attendance Management View (PySide6)
Full GUI interface for Student Daily Marking, Quick Bulk Actions (All Present/Absent),
Teacher Attendance Register, and Excel Export.
"""

from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDateEdit, QTabWidget, QMessageBox, QFrame,
    QButtonGroup, QRadioButton, QFileDialog
)
from PySide6.QtCore import Qt, QDate
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.repositories.academic_repository import AcademicRepository
from app.repositories.attendance_repository import AttendanceRepository
from app.services.attendance_service import AttendanceService


class AttendancePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.student_rows_data = []
        self.teacher_rows_data = []
        self._init_ui()
        self._load_classes_and_initial_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # 1. Header Banner
        header_h = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("Attendance & Register Management")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A;")
        sub_lbl = QLabel("Record and monitor daily student attendance, teacher punctuality, and monthly registers")
        sub_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header_h.addLayout(title_box)
        header_h.addStretch()

        main_layout.addLayout(header_h)

        # 2. Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { font-weight: 600; padding: 8px 16px; margin-right: 4px; }
            QTabBar::tab:selected { background: #2563EB; color: white; border-radius: 4px; }
        """)

        # Tab 1: Student Attendance
        tab_student = self._build_student_tab()
        self.tabs.addTab(tab_student, "Student Daily Attendance")

        # Tab 2: Teacher Attendance
        tab_teacher = self._build_teacher_tab()
        self.tabs.addTab(tab_teacher, "Faculty / Teacher Attendance")

        main_layout.addWidget(self.tabs)

    def _build_student_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(12)

        # Controls & Filter Bar
        bar = QFrame()
        bar.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(12, 10, 12, 10)
        bar_layout.setSpacing(12)

        # Date Picker
        bar_layout.addWidget(QLabel("Date:"))
        self.stu_date_edit = QDateEdit()
        self.stu_date_edit.setCalendarPopup(True)
        self.stu_date_edit.setDate(QDate.currentDate())
        self.stu_date_edit.dateChanged.connect(self._load_student_roster)
        bar_layout.addWidget(self.stu_date_edit)

        # Class Picker
        bar_layout.addWidget(QLabel("Class:"))
        self.stu_class_combo = QComboBox()
        self.stu_class_combo.currentIndexChanged.connect(self._on_class_changed)
        bar_layout.addWidget(self.stu_class_combo)

        # Section Picker
        bar_layout.addWidget(QLabel("Section:"))
        self.stu_sec_combo = QComboBox()
        self.stu_sec_combo.currentIndexChanged.connect(self._load_student_roster)
        bar_layout.addWidget(self.stu_sec_combo)

        bar_layout.addStretch()

        # Quick Actions
        btn_all_p = QPushButton("Mark All Present")
        btn_all_p.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_all_p.clicked.connect(self._on_mark_all_students_present)
        bar_layout.addWidget(btn_all_p)

        btn_all_a = QPushButton("Mark All Absent")
        btn_all_a.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_all_a.clicked.connect(self._on_mark_all_students_absent)
        bar_layout.addWidget(btn_all_a)

        btn_export = QPushButton("Export Register (.xlsx)")
        btn_export.setStyleSheet("background-color: #4B5563; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_export.clicked.connect(self._on_export_student_excel)
        bar_layout.addWidget(btn_export)

        btn_save = QPushButton("Save Attendance")
        btn_save.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 16px; border-radius: 6px;")
        btn_save.clicked.connect(self._on_save_student_attendance)
        bar_layout.addWidget(btn_save)

        layout.addWidget(bar)

        # Live Metrics Strip
        self.stu_kpi_frame = QFrame()
        self.stu_kpi_frame.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;")
        kpi_h = QHBoxLayout(self.stu_kpi_frame)
        kpi_h.setContentsMargins(16, 8, 16, 8)

        self.stu_kpi_total = QLabel("Total: 0")
        self.stu_kpi_total.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        kpi_h.addWidget(self.stu_kpi_total)
        kpi_h.addSpacing(20)

        self.stu_kpi_p = QLabel("Present: 0")
        self.stu_kpi_p.setStyleSheet("font-size: 13px; font-weight: bold; color: #059669;")
        kpi_h.addWidget(self.stu_kpi_p)
        kpi_h.addSpacing(20)

        self.stu_kpi_a = QLabel("Absent: 0")
        self.stu_kpi_a.setStyleSheet("font-size: 13px; font-weight: bold; color: #DC2626;")
        kpi_h.addWidget(self.stu_kpi_a)
        kpi_h.addSpacing(20)

        self.stu_kpi_l = QLabel("Late: 0")
        self.stu_kpi_l.setStyleSheet("font-size: 13px; font-weight: bold; color: #D97706;")
        kpi_h.addWidget(self.stu_kpi_l)
        kpi_h.addSpacing(20)

        self.stu_kpi_rate = QLabel("Rate: 0.0%")
        self.stu_kpi_rate.setStyleSheet("font-size: 13px; font-weight: bold; color: #2563EB;")
        kpi_h.addWidget(self.stu_kpi_rate)
        kpi_h.addStretch()

        layout.addWidget(self.stu_kpi_frame)

        # Students Attendance Table
        self.stu_table = QTableWidget()
        self.stu_table.setColumnCount(7)
        self.stu_table.setHorizontalHeaderLabels([
            "Roll", "Student ID", "Full Name", "Status", "Quick Selection", "Check-in Time", "Remarks / Reason"
        ])
        self.stu_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stu_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.stu_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.stu_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.stu_table)

        return tab

    def _build_teacher_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(12)

        # Control Bar
        bar = QFrame()
        bar.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(12, 10, 12, 10)
        bar_layout.setSpacing(12)

        bar_layout.addWidget(QLabel("Date:"))
        self.tch_date_edit = QDateEdit()
        self.tch_date_edit.setCalendarPopup(True)
        self.tch_date_edit.setDate(QDate.currentDate())
        self.tch_date_edit.dateChanged.connect(self._load_teacher_roster)
        bar_layout.addWidget(self.tch_date_edit)

        bar_layout.addStretch()

        btn_tch_p = QPushButton("Mark All Present")
        btn_tch_p.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_tch_p.clicked.connect(self._on_mark_all_teachers_present)
        bar_layout.addWidget(btn_tch_p)

        btn_tch_save = QPushButton("Save Faculty Attendance")
        btn_tch_save.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 16px; border-radius: 6px;")
        btn_tch_save.clicked.connect(self._on_save_teacher_attendance)
        bar_layout.addWidget(btn_tch_save)

        layout.addWidget(bar)

        # Table
        self.tch_table = QTableWidget()
        self.tch_table.setColumnCount(7)
        self.tch_table.setHorizontalHeaderLabels([
            "Employee ID", "Teacher Name", "Department", "Subject", "Status", "Check-in / Out", "Remarks"
        ])
        self.tch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.tch_table)

        return tab

    def _load_classes_and_initial_data(self):
        db: Session = SessionLocal()
        try:
            classes = AcademicRepository.get_classes(db)
            self.stu_class_combo.clear()
            for c in classes:
                self.stu_class_combo.addItem(f"{c.name} ({c.group})", c.id)

            self._on_class_changed()
            self._load_teacher_roster()
        finally:
            db.close()

    def _on_class_changed(self):
        class_id = self.stu_class_combo.currentData()
        if not class_id:
            return

        db: Session = SessionLocal()
        try:
            sections = AcademicRepository.get_sections(db, class_id=class_id)
            self.stu_sec_combo.clear()
            self.stu_sec_combo.addItem("All Sections", None)
            for s in sections:
                self.stu_sec_combo.addItem(s.name, s.id)

            self._load_student_roster()
        finally:
            db.close()

    def _load_student_roster(self):
        class_id = self.stu_class_combo.currentData()
        if not class_id:
            return
        section_id = self.stu_sec_combo.currentData()
        qdate = self.stu_date_edit.date()
        att_date = date(qdate.year(), qdate.month(), qdate.day())

        db: Session = SessionLocal()
        try:
            records = AttendanceRepository.get_class_students_with_attendance(
                db, class_id, section_id=section_id, att_date=att_date
            )
            self.student_rows_data = records
            self.stu_table.setRowCount(len(records))

            for row, item in enumerate(records):
                stu = item["student"]
                self.stu_table.setItem(row, 0, QTableWidgetItem(str(stu.roll_number)))
                self.stu_table.setItem(row, 1, QTableWidgetItem(stu.student_id))
                self.stu_table.setItem(row, 2, QTableWidgetItem(stu.full_name))

                # Status combo
                combo = QComboBox()
                combo.addItems(["Present", "Absent", "Late", "Leave"])
                idx = combo.findText(item["status"])
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                combo.currentIndexChanged.connect(lambda idx, r=row: self._on_student_status_changed(r))
                self.stu_table.setCellWidget(row, 3, combo)

                # Quick action buttons in row
                btn_widget = QWidget()
                btn_h = QHBoxLayout(btn_widget)
                btn_h.setContentsMargins(2, 2, 2, 2)
                btn_p = QPushButton("P")
                btn_p.setStyleSheet("background-color: #059669; color: white; font-weight: bold; width: 22px;")
                btn_p.clicked.connect(lambda _, r=row: self._set_single_student_status(r, "Present"))
                btn_a = QPushButton("A")
                btn_a.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; width: 22px;")
                btn_a.clicked.connect(lambda _, r=row: self._set_single_student_status(r, "Absent"))
                btn_l = QPushButton("L")
                btn_l.setStyleSheet("background-color: #D97706; color: white; font-weight: bold; width: 22px;")
                btn_l.clicked.connect(lambda _, r=row: self._set_single_student_status(r, "Late"))
                btn_h.addWidget(btn_p)
                btn_h.addWidget(btn_a)
                btn_h.addWidget(btn_l)
                self.stu_table.setCellWidget(row, 4, btn_widget)

                # Check-in edit
                checkin_edit = QLineEdit(item["check_in_time"] or "08:15 AM")
                self.stu_table.setCellWidget(row, 5, checkin_edit)

                # Remarks
                rem_edit = QLineEdit(item["remarks"] or "")
                self.stu_table.setCellWidget(row, 6, rem_edit)

            self._update_student_kpi()
        finally:
            db.close()

    def _set_single_student_status(self, row: int, status: str):
        combo = self.stu_table.cellWidget(row, 3)
        if isinstance(combo, QComboBox):
            idx = combo.findText(status)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        self._update_student_kpi()

    def _on_student_status_changed(self, row: int):
        self._update_student_kpi()

    def _update_student_kpi(self):
        total = self.stu_table.rowCount()
        p_count = 0
        a_count = 0
        l_count = 0

        for r in range(total):
            combo = self.stu_table.cellWidget(r, 3)
            if isinstance(combo, QComboBox):
                st = combo.currentText()
                if st == "Present":
                    p_count += 1
                elif st == "Absent":
                    a_count += 1
                elif st == "Late":
                    l_count += 1

        rate = round((p_count / total * 100), 1) if total > 0 else 0.0
        self.stu_kpi_total.setText(f"Total: {total}")
        self.stu_kpi_p.setText(f"Present: {p_count}")
        self.stu_kpi_a.setText(f"Absent: {a_count}")
        self.stu_kpi_l.setText(f"Late: {l_count}")
        self.stu_kpi_rate.setText(f"Rate: {rate}%")

    def _on_mark_all_students_present(self):
        for r in range(self.stu_table.rowCount()):
            self._set_single_student_status(r, "Present")

    def _on_mark_all_students_absent(self):
        for r in range(self.stu_table.rowCount()):
            self._set_single_student_status(r, "Absent")

    def _on_save_student_attendance(self):
        class_id = self.stu_class_combo.currentData()
        section_id = self.stu_sec_combo.currentData()
        qdate = self.stu_date_edit.date()
        att_date = date(qdate.year(), qdate.month(), qdate.day())

        records = []
        for r in range(self.stu_table.rowCount()):
            stu = self.student_rows_data[r]["student"]
            combo = self.stu_table.cellWidget(r, 3)
            cin = self.stu_table.cellWidget(r, 5)
            rem = self.stu_table.cellWidget(r, 6)

            records.append({
                "student_id": stu.id,
                "class_id": class_id,
                "section_id": stu.section_id or section_id,
                "date": att_date,
                "status": combo.currentText() if isinstance(combo, QComboBox) else "Present",
                "check_in_time": cin.text() if isinstance(cin, QLineEdit) else None,
                "remarks": rem.text() if isinstance(rem, QLineEdit) else None,
            })

        db: Session = SessionLocal()
        try:
            ok, msg = AttendanceService.mark_student_attendance(db, class_id, section_id, att_date, records)
            if ok:
                QMessageBox.information(self, "Attendance Saved", msg)
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()

    def _on_export_student_excel(self):
        class_id = self.stu_class_combo.currentData()
        section_id = self.stu_sec_combo.currentData()
        qdate = self.stu_date_edit.date()

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Attendance Register",
            f"Attendance_Register_Class{class_id}_{qdate.year()}_{qdate.month():02d}.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not path:
            return

        db: Session = SessionLocal()
        try:
            AttendanceService.export_monthly_register_excel(
                db, class_id, qdate.year(), qdate.month(), path, section_id=section_id
            )
            QMessageBox.information(self, "Export Successful", f"Monthly attendance register exported to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))
        finally:
            db.close()

    # ==================== TEACHER ATTENDANCE ====================
    def _load_teacher_roster(self):
        qdate = self.tch_date_edit.date()
        att_date = date(qdate.year(), qdate.month(), qdate.day())

        db: Session = SessionLocal()
        try:
            records = AttendanceRepository.get_teachers_with_attendance(db, att_date=att_date)
            self.teacher_rows_data = records
            self.tch_table.setRowCount(len(records))

            for row, item in enumerate(records):
                t = item["teacher"]
                self.tch_table.setItem(row, 0, QTableWidgetItem(t.employee_id))
                self.tch_table.setItem(row, 1, QTableWidgetItem(t.full_name))
                self.tch_table.setItem(row, 2, QTableWidgetItem(t.department.name if t.department else "-"))
                self.tch_table.setItem(row, 3, QTableWidgetItem(t.primary_subject))

                combo = QComboBox()
                combo.addItems(["Present", "Absent", "Late", "Leave"])
                idx = combo.findText(item["status"])
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                self.tch_table.setCellWidget(row, 4, combo)

                cin = QLineEdit(item["check_in_time"] or "07:50 AM")
                self.tch_table.setCellWidget(row, 5, cin)

                rem = QLineEdit(item["remarks"] or "")
                self.tch_table.setCellWidget(row, 6, rem)
        finally:
            db.close()

    def _on_mark_all_teachers_present(self):
        for r in range(self.tch_table.rowCount()):
            combo = self.tch_table.cellWidget(r, 4)
            if isinstance(combo, QComboBox):
                combo.setCurrentIndex(combo.findText("Present"))

    def _on_save_teacher_attendance(self):
        qdate = self.tch_date_edit.date()
        att_date = date(qdate.year(), qdate.month(), qdate.day())

        records = []
        for r in range(self.tch_table.rowCount()):
            t = self.teacher_rows_data[r]["teacher"]
            combo = self.tch_table.cellWidget(r, 4)
            cin = self.tch_table.cellWidget(r, 5)
            rem = self.tch_table.cellWidget(r, 6)

            records.append({
                "teacher_id": t.id,
                "date": att_date,
                "status": combo.currentText() if isinstance(combo, QComboBox) else "Present",
                "check_in_time": cin.text() if isinstance(cin, QLineEdit) else "07:50 AM",
                "remarks": rem.text() if isinstance(rem, QLineEdit) else "",
            })

        db: Session = SessionLocal()
        try:
            ok, msg = AttendanceService.mark_teacher_attendance(db, att_date, records)
            if ok:
                QMessageBox.information(self, "Faculty Attendance Saved", msg)
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()
