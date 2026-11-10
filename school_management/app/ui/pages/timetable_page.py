"""
EduManage Pro - Timetable & Routine Management Page
Phase 9: PySide6 3-Tab Interface (Class Timetable Grid, Teacher Routine & Bell Periods)
"""

import os
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QComboBox, QPushButton, QLabel, QHeaderView,
    QMessageBox, QFileDialog, QFrame
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from app.models.academic import SchoolClass, Section, Subject
from app.models.staff import Teacher
from app.models.school import SchoolSetting
from app.models.timetable import PeriodSlot, TimetableEntry
from app.repositories.timetable_repository import TimetableRepository
from app.database.connection import SessionLocal
from app.services.timetable_service import TimetableService, STANDARD_DAYS
from app.reports.class_timetable_pdf import ClassTimetablePDFGenerator
from app.reports.teacher_routine_pdf import TeacherRoutinePDFGenerator
from app.ui.dialogs.timetable_slot_dialog import TimetableSlotDialog
from app.ui.dialogs.period_config_dialog import PeriodConfigDialog


class TimetablePage(QWidget):
    """Main Timetable & Routine Page with Class Matrix, Faculty Schedule & Period Configuration."""

    def __init__(self, parent=None, db_session: Optional[Session] = None, session_manager=None):
        super().__init__(parent)
        self.session_manager = session_manager
        self.db_session = db_session if db_session is not None else SessionLocal()

        # Ensure default periods exist
        TimetableService.seed_default_periods(self.db_session)

        self._setup_ui()
        self.refresh_data()

    def refresh_all(self):
        """Standard lifecycle hook called on navigation."""
        self.refresh_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # Header Title
        title_box = QHBoxLayout()
        title_label = QLabel("Class Timetable & Teacher Routine Management")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1E293B;")
        title_box.addWidget(title_label)
        title_box.addStretch()
        main_layout.addLayout(title_box)

        # Tab Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # TAB 1: Class Timetable
        self.class_tab = QWidget()
        self._setup_class_tab()
        self.tabs.addTab(self.class_tab, "Class Timetable Matrix")

        # TAB 2: Teacher Routine
        self.teacher_tab = QWidget()
        self._setup_teacher_tab()
        self.tabs.addTab(self.teacher_tab, "Teacher Workload & Routine")

        # TAB 3: Period Slots
        self.period_tab = QWidget()
        self._setup_period_tab()
        self.tabs.addTab(self.period_tab, "Bell Periods & Intervals")

    # ==================== TAB 1: CLASS TIMETABLE ====================
    def _setup_class_tab(self):
        layout = QVBoxLayout(self.class_tab)
        layout.setSpacing(10)

        # Control Bar
        ctrl_bar = QHBoxLayout()
        ctrl_bar.addWidget(QLabel("Class:"))
        self.class_combo = QComboBox()
        self.class_combo.currentIndexChanged.connect(self._on_class_changed)
        ctrl_bar.addWidget(self.class_combo)

        ctrl_bar.addWidget(QLabel("Section:"))
        self.section_combo = QComboBox()
        self.section_combo.currentIndexChanged.connect(self.load_class_timetable)
        ctrl_bar.addWidget(self.section_combo)

        ctrl_bar.addStretch()

        self.btn_add_slot = QPushButton("+ Assign Slot")
        self.btn_add_slot.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_add_slot.clicked.connect(self._open_add_slot_dialog)
        ctrl_bar.addWidget(self.btn_add_slot)

        self.btn_export_excel = QPushButton("Export Excel")
        self.btn_export_excel.setStyleSheet("background-color: #10B981; color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_export_excel.clicked.connect(self._export_excel)
        ctrl_bar.addWidget(self.btn_export_excel)

        self.btn_export_pdf = QPushButton("Print Routine PDF")
        self.btn_export_pdf.setStyleSheet("background-color: #4F46E5; color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        ctrl_bar.addWidget(self.btn_export_pdf)

        layout.addLayout(ctrl_bar)

        # Class Grid Table
        self.class_table = QTableWidget()
        self.class_table.setAlternatingRowColors(True)
        self.class_table.cellDoubleClicked.connect(self._on_class_cell_double_clicked)
        layout.addWidget(self.class_table)

    def _setup_teacher_tab(self):
        layout = QVBoxLayout(self.teacher_tab)
        layout.setSpacing(10)

        # Control Bar
        ctrl_bar = QHBoxLayout()
        ctrl_bar.addWidget(QLabel("Faculty Member:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.currentIndexChanged.connect(self.load_teacher_routine)
        ctrl_bar.addWidget(self.teacher_combo)

        self.lbl_teacher_workload = QLabel("Workload: 0 Periods/Week")
        self.lbl_teacher_workload.setStyleSheet("font-weight: bold; color: #059669; padding-left: 12px;")
        ctrl_bar.addWidget(self.lbl_teacher_workload)

        ctrl_bar.addStretch()

        self.btn_teacher_pdf = QPushButton("Print Teacher Routine PDF")
        self.btn_teacher_pdf.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_teacher_pdf.clicked.connect(self._export_teacher_pdf)
        ctrl_bar.addWidget(self.btn_teacher_pdf)

        layout.addLayout(ctrl_bar)

        self.teacher_table = QTableWidget()
        self.teacher_table.setAlternatingRowColors(True)
        layout.addWidget(self.teacher_table)

    def _setup_period_tab(self):
        layout = QVBoxLayout(self.period_tab)
        layout.setSpacing(10)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("School Bell Schedule & Period Durations"))
        top_bar.addStretch()

        btn_add_p = QPushButton("+ Add Period Slot")
        btn_add_p.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 14px;")
        btn_add_p.clicked.connect(self._open_add_period_dialog)
        top_bar.addWidget(btn_add_p)

        layout.addLayout(top_bar)

        self.period_table = QTableWidget()
        self.period_table.setColumnCount(6)
        self.period_table.setHorizontalHeaderLabels([
            "Period #", "Slot Name", "Start Time", "End Time", "Duration (Min)", "Type"
        ])
        self.period_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.period_table)

    # ==================== DATA LOADING ====================
    def refresh_data(self):
        """Reload classes, teachers and period definitions."""
        # Load Classes
        self.class_combo.blockSignals(True)
        self.class_combo.clear()
        classes = self.db_session.query(SchoolClass).order_by(SchoolClass.numeric_order.asc()).all()
        for c in classes:
            self.class_combo.addItem(f"{c.name} ({c.group})", c.id)
        self.class_combo.blockSignals(False)

        # Load Teachers
        self.teacher_combo.blockSignals(True)
        self.teacher_combo.clear()
        teachers = self.db_session.query(Teacher).filter(Teacher.status == "Active").order_by(Teacher.name.asc()).all()
        for t in teachers:
            self.teacher_combo.addItem(f"{t.name} ({t.employee_id})", t.id)
        self.teacher_combo.blockSignals(False)

        self._on_class_changed()
        self.load_teacher_routine()
        self.load_periods()

    def _on_class_changed(self):
        class_id = self.class_combo.currentData()
        self.section_combo.blockSignals(True)
        self.section_combo.clear()
        self.section_combo.addItem("All Sections", None)
        if class_id:
            sections = self.db_session.query(Section).filter(Section.class_id == class_id).all()
            for s in sections:
                self.section_combo.addItem(f"Section {s.name}", s.id)
        self.section_combo.blockSignals(False)
        self.load_class_timetable()

    def load_class_timetable(self):
        class_id = self.class_combo.currentData()
        if not class_id:
            return

        section_id = self.section_combo.currentData()
        periods = TimetableRepository.get_period_slots(self.db_session)
        self.teaching_periods = [p for p in periods if not p.is_break or "Tiffin" in p.name]

        # Setup Table Columns
        self.class_table.setColumnCount(len(self.teaching_periods) + 1)
        headers = ["Day \\ Period"] + [f"{p.name}\n({p.start_time} - {p.end_time})" for p in self.teaching_periods]
        self.class_table.setHorizontalHeaderLabels(headers)
        self.class_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.class_table.setRowCount(len(STANDARD_DAYS))

        matrix = TimetableRepository.get_class_timetable_matrix(self.db_session, class_id, section_id)

        for row_idx, day in enumerate(STANDARD_DAYS):
            day_item = QTableWidgetItem(day)
            day_item.setTextAlignment(Qt.AlignCenter)
            day_item.setFlags(Qt.ItemIsEnabled)
            self.class_table.setItem(row_idx, 0, day_item)

            for col_idx, p in enumerate(self.teaching_periods, start=1):
                if p.is_break:
                    item = QTableWidgetItem("TIFFIN BREAK")
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFlags(Qt.ItemIsEnabled)
                    item.setBackground(Qt.lightGray)
                    self.class_table.setItem(row_idx, col_idx, item)
                else:
                    entry = matrix.get(day, {}).get(p.id)
                    if entry:
                        sub_text = entry.subject.name if entry.subject else "Subject"
                        t_text = entry.teacher.name if entry.teacher else ""
                        r_text = entry.room_number or ""
                        item = QTableWidgetItem(f"{sub_text}\n{t_text} | {r_text}")
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setData(Qt.UserRole, entry.id)
                        self.class_table.setItem(row_idx, col_idx, item)
                    else:
                        item = QTableWidgetItem("—")
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setData(Qt.UserRole, None)
                        self.class_table.setItem(row_idx, col_idx, item)

            self.class_table.setRowHeight(row_idx, 55)

    def load_teacher_routine(self):
        teacher_id = self.teacher_combo.currentData()
        if not teacher_id:
            return

        periods = TimetableRepository.get_period_slots(self.db_session)
        teaching_periods = [p for p in periods if not p.is_break or "Tiffin" in p.name]

        self.teacher_table.setColumnCount(len(teaching_periods) + 1)
        headers = ["Day \\ Period"] + [f"{p.name}\n({p.start_time} - {p.end_time})" for p in teaching_periods]
        self.teacher_table.setHorizontalHeaderLabels(headers)
        self.teacher_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.teacher_table.setRowCount(len(STANDARD_DAYS))

        matrix = TimetableRepository.get_teacher_routine_matrix(self.db_session, teacher_id)
        total_slots = 0

        for row_idx, day in enumerate(STANDARD_DAYS):
            day_item = QTableWidgetItem(day)
            day_item.setTextAlignment(Qt.AlignCenter)
            day_item.setFlags(Qt.ItemIsEnabled)
            self.teacher_table.setItem(row_idx, 0, day_item)

            for col_idx, p in enumerate(teaching_periods, start=1):
                if p.is_break:
                    item = QTableWidgetItem("TIFFIN BREAK")
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFlags(Qt.ItemIsEnabled)
                    item.setBackground(Qt.lightGray)
                    self.teacher_table.setItem(row_idx, col_idx, item)
                else:
                    entry = matrix.get(day, {}).get(p.id)
                    if entry:
                        total_slots += 1
                        cls_text = entry.school_class.name if entry.school_class else "Class"
                        sub_text = entry.subject.name if entry.subject else "Subject"
                        r_text = entry.room_number or ""
                        item = QTableWidgetItem(f"{cls_text}\n{sub_text} ({r_text})")
                        item.setTextAlignment(Qt.AlignCenter)
                        self.teacher_table.setItem(row_idx, col_idx, item)
                    else:
                        item = QTableWidgetItem("Off")
                        item.setTextAlignment(Qt.AlignCenter)
                        self.teacher_table.setItem(row_idx, col_idx, item)

            self.teacher_table.setRowHeight(row_idx, 55)

        self.lbl_teacher_workload.setText(f"Workload: {total_slots} Assigned Teaching Periods / Week")

    def load_periods(self):
        periods = TimetableRepository.get_period_slots(self.db_session)
        self.period_table.setRowCount(len(periods))

        for row, p in enumerate(periods):
            self.period_table.setItem(row, 0, QTableWidgetItem(str(p.period_number)))
            self.period_table.setItem(row, 1, QTableWidgetItem(p.name))
            self.period_table.setItem(row, 2, QTableWidgetItem(p.start_time))
            self.period_table.setItem(row, 3, QTableWidgetItem(p.end_time))
            self.period_table.setItem(row, 4, QTableWidgetItem(str(p.duration_minutes)))
            self.period_table.setItem(row, 5, QTableWidgetItem("Break / Interval" if p.is_break else "Teaching Period"))
            self.period_table.item(row, 0).setTextAlignment(Qt.AlignCenter)

    # ==================== ACTIONS ====================
    def _open_add_slot_dialog(self):
        class_id = self.class_combo.currentData()
        section_id = self.section_combo.currentData()
        if not class_id:
            return

        dialog = TimetableSlotDialog(self.db_session, class_id=class_id, section_id=section_id, parent=self)
        if dialog.exec_():
            self.load_class_timetable()
            self.load_teacher_routine()

    def _on_class_cell_double_clicked(self, row: int, col: int):
        if col == 0:
            return
        day = STANDARD_DAYS[row]
        period = self.teaching_periods[col - 1]
        if period.is_break:
            return

        class_id = self.class_combo.currentData()
        section_id = self.section_combo.currentData()
        item = self.class_table.item(row, col)
        entry_id = item.data(Qt.UserRole) if item else None

        entry = TimetableRepository.get_timetable_entry_by_id(self.db_session, entry_id) if entry_id else None

        dialog = TimetableSlotDialog(
            self.db_session,
            class_id=class_id,
            section_id=section_id,
            default_day=day,
            default_period_id=period.id,
            entry=entry,
            parent=self
        )
        if dialog.exec_():
            self.load_class_timetable()
            self.load_teacher_routine()

    def _open_add_period_dialog(self):
        dialog = PeriodConfigDialog(self.db_session, parent=self)
        if dialog.exec_():
            self.load_periods()
            self.load_class_timetable()

    def _export_excel(self):
        class_id = self.class_combo.currentData()
        class_name = self.class_combo.currentText()
        section_name = self.section_combo.currentText()
        if not class_id:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Timetable Excel", f"Class_Timetable_{class_name.split()[0]}.xlsx", "Excel Files (*.xlsx)"
        )
        if file_path:
            school = self.db_session.query(SchoolSetting).first()
            school_name = school.school_name if school else "Ideal Model High School & College"
            success = TimetableService.export_class_timetable_excel(
                session=self.db_session,
                class_id=class_id,
                class_name=class_name,
                section_name=section_name,
                school_name=school_name,
                output_path=file_path
            )
            if success:
                QMessageBox.information(self, "Export Success", f"Timetable spreadsheet exported to:\n{file_path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Could not generate Excel spreadsheet.")

    def _export_pdf(self):
        class_id = self.class_combo.currentData()
        class_name = self.class_combo.currentText()
        section_name = self.section_combo.currentText()
        if not class_id:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Timetable PDF", f"Class_Routine_{class_name.split()[0]}.pdf", "PDF Files (*.pdf)"
        )
        if file_path:
            school = self.db_session.query(SchoolSetting).first()
            school_info = {
                "school_name": school.school_name if school else "Ideal Model High School & College",
                "eiin_number": school.eiin_number if school else "134211",
                "address": school.address if school else "Uttara, Dhaka"
            }
            periods = TimetableRepository.get_period_slots(self.db_session)
            period_dicts = [
                {"id": p.id, "name": p.name, "start_time": p.start_time, "end_time": p.end_time, "is_break": p.is_break}
                for p in periods
            ]
            matrix_raw = TimetableRepository.get_class_timetable_matrix(self.db_session, class_id)
            matrix = {}
            for d, p_dict in matrix_raw.items():
                matrix[d] = {}
                for pid, entry in p_dict.items():
                    matrix[d][pid] = {
                        "subject_name": entry.subject.name if entry.subject else "",
                        "teacher_name": entry.teacher.name if entry.teacher else "",
                        "room_number": entry.room_number or ""
                    }

            success = ClassTimetablePDFGenerator.generate_timetable(
                class_name=class_name,
                section_name=section_name,
                shift_name="Morning",
                school_info=school_info,
                periods=period_dicts,
                matrix=matrix,
                output_path=file_path
            )
            if success:
                QMessageBox.information(self, "Export Success", f"Class routine PDF generated:\n{file_path}")

    def _export_teacher_pdf(self):
        teacher_id = self.teacher_combo.currentData()
        teacher = self.db_session.query(Teacher).filter(Teacher.id == teacher_id).first()
        if not teacher:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Teacher Routine PDF", f"Routine_{teacher.name.replace(' ', '_')}.pdf", "PDF Files (*.pdf)"
        )
        if file_path:
            school = self.db_session.query(SchoolSetting).first()
            school_info = {
                "school_name": school.school_name if school else "Ideal Model High School & College",
            }
            periods = TimetableRepository.get_period_slots(self.db_session)
            period_dicts = [
                {"id": p.id, "name": p.name, "start_time": p.start_time, "end_time": p.end_time, "is_break": p.is_break}
                for p in periods
            ]
            matrix_raw = TimetableRepository.get_teacher_routine_matrix(self.db_session, teacher.id)
            matrix = {}
            total_slots = 0
            for d, p_dict in matrix_raw.items():
                matrix[d] = {}
                for pid, entry in p_dict.items():
                    total_slots += 1
                    matrix[d][pid] = {
                        "class_name": entry.school_class.name if entry.school_class else "",
                        "section_name": entry.section.name if entry.section else "",
                        "subject_name": entry.subject.name if entry.subject else "",
                        "room_number": entry.room_number or ""
                    }

            teacher_info = {
                "name": teacher.name,
                "employee_id": teacher.employee_id,
                "department": teacher.department.name if teacher.department else "General",
                "designation": teacher.designation or "Lecturer",
                "total_weekly_periods": total_slots
            }

            success = TeacherRoutinePDFGenerator.generate_routine(
                teacher_info=teacher_info,
                school_info=school_info,
                periods=period_dicts,
                matrix=matrix,
                output_path=file_path
            )
            if success:
                QMessageBox.information(self, "Export Success", f"Faculty Routine PDF generated:\n{file_path}")
