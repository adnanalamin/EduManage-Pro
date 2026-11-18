"""
EduManage Pro - Advanced Timetable & Routine Management Page (PySide6)
Supports:
- Academic Year History Context & Multi-Shift Selection (Morning, Day, Evening)
- Class Timetable Matrix (manual edit, move/swap, Auto-Suggestion wizard, PDF & Excel)
- Teacher Timetable & Weekly Workload + Printable PDF
- Room Timetable & Weekly Utilization + Printable PDF & Excel
- Real-Time Teacher, Room & Class Conflict Scanner + Multi-Shift Bell Periods
- Immutable Academic Year Timetable History, Snapshots & Cross-Year Cloning
"""

from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.academic import AcademicRoom, AcademicShift, AcademicYear, SchoolClass, Section, Subject
from app.models.school import SchoolSetting
from app.models.staff import Teacher
from app.models.timetable import PeriodSlot, TimetableEntry
from app.reports.class_timetable_pdf import ClassTimetablePDFGenerator
from app.reports.room_timetable_pdf import RoomTimetablePDFGenerator
from app.reports.teacher_routine_pdf import TeacherRoutinePDFGenerator
from app.repositories.timetable_repository import TimetableRepository
from app.security.session import session as app_session
from app.services.timetable_service import STANDARD_DAYS, TimetableService
from app.ui.dialogs.period_config_dialog import PeriodConfigDialog
from app.ui.dialogs.timetable_slot_dialog import TimetableSlotDialog


class TimetablePage(QWidget):
    """Enterprise Timetable & Routine Workspace."""

    def __init__(self, parent=None, db_session: Optional[Session] = None, session_manager=None):
        super().__init__(parent)
        self.session_manager = session_manager
        self.db_session = db_session if db_session is not None else SessionLocal()
        self.teaching_periods = []

        TimetableService.seed_all_shift_periods(self.db_session, academic_year_id=1)

        self._setup_ui()
        self.refresh_data()

    def refresh_all(self):
        self.refresh_data()

    def _actor(self):
        return app_session.current_user if app_session.is_authenticated else None

    def _current_year_id(self) -> int:
        val = self.year_combo.currentData()
        return int(val) if val else 1

    def _current_shift(self) -> str:
        return self.shift_combo.currentText() or "Morning"

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        # 1. Global Header + Academic Year & Multi-Shift Context Bar
        title_box = QHBoxLayout()
        header_v = QVBoxLayout()
        title_label = QLabel("Advanced Timetable, Multi-Shift & Conflict Management")
        title_label.setStyleSheet("font-size: 19px; font-weight: bold; color: #3b82f6;")
        sub_label = QLabel(
            "Class, Teacher & Room timetables with conflict detection, automatic scheduling, "
            "multi-shift bells, printable PDFs & academic-year history."
        )
        sub_label.setStyleSheet("font-size: 12px; color: #94a3b8;")
        header_v.addWidget(title_label)
        header_v.addWidget(sub_label)
        title_box.addLayout(header_v)
        title_box.addStretch()

        title_box.addWidget(QLabel("Academic Year:"))
        self.year_combo = QComboBox()
        self.year_combo.currentIndexChanged.connect(self._on_context_changed)
        title_box.addWidget(self.year_combo)

        title_box.addWidget(QLabel("Shift:"))
        self.shift_combo = QComboBox()
        self.shift_combo.currentIndexChanged.connect(self._on_context_changed)
        title_box.addWidget(self.shift_combo)

        main_layout.addLayout(title_box)

        # 2. Tab Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.class_tab = QWidget()
        self._setup_class_tab()
        self.tabs.addTab(self.class_tab, "Class Timetable")

        self.teacher_tab = QWidget()
        self._setup_teacher_tab()
        self.tabs.addTab(self.teacher_tab, "Teacher Timetable")

        self.room_tab = QWidget()
        self._setup_room_tab()
        self.tabs.addTab(self.room_tab, "Room Timetable")

        self.period_tab = QWidget()
        self._setup_period_and_conflict_tab()
        self.tabs.addTab(self.period_tab, "Conflicts & Bell Periods")

        self.history_tab = QWidget()
        self._setup_history_tab()
        self.tabs.addTab(self.history_tab, "Academic Year History")

    # ==================== TAB 1: CLASS TIMETABLE ====================
    def _setup_class_tab(self):
        layout = QVBoxLayout(self.class_tab)
        layout.setSpacing(10)

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

        self.btn_auto_suggest = QPushButton("Auto-Suggest Timetable")
        self.btn_auto_suggest.setStyleSheet("background-color: #7c3aed; color: white; font-weight: bold; padding: 6px 12px;")
        self.btn_auto_suggest.clicked.connect(self._open_auto_suggest_dialog)
        ctrl_bar.addWidget(self.btn_auto_suggest)

        self.btn_swap_slot = QPushButton("Move / Swap Slot")
        self.btn_swap_slot.setStyleSheet("background-color: #d97706; color: white; font-weight: bold; padding: 6px 12px;")
        self.btn_swap_slot.clicked.connect(self._open_move_swap_dialog)
        ctrl_bar.addWidget(self.btn_swap_slot)

        self.btn_add_slot = QPushButton("+ Assign Slot")
        self.btn_add_slot.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 12px;")
        self.btn_add_slot.clicked.connect(self._open_add_slot_dialog)
        ctrl_bar.addWidget(self.btn_add_slot)

        self.btn_export_excel = QPushButton("Export Excel")
        self.btn_export_excel.setStyleSheet("background-color: #10B981; color: white; font-weight: bold; padding: 6px 12px;")
        self.btn_export_excel.clicked.connect(self._export_excel)
        ctrl_bar.addWidget(self.btn_export_excel)

        self.btn_export_pdf = QPushButton("Print Class PDF")
        self.btn_export_pdf.setStyleSheet("background-color: #4F46E5; color: white; font-weight: bold; padding: 6px 12px;")
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        ctrl_bar.addWidget(self.btn_export_pdf)

        layout.addLayout(ctrl_bar)

        self.class_table = QTableWidget()
        self.class_table.setAlternatingRowColors(True)
        self.class_table.cellDoubleClicked.connect(self._on_class_cell_double_clicked)
        layout.addWidget(self.class_table)

        hint = QLabel("Tip: Double-click any cell in the timetable grid to manually assign, edit, or delete that teaching slot.")
        hint.setStyleSheet("font-size: 11px; color: #94a3b8;")
        layout.addWidget(hint)

    # ==================== TAB 2: TEACHER TIMETABLE ====================
    def _setup_teacher_tab(self):
        layout = QVBoxLayout(self.teacher_tab)
        layout.setSpacing(10)

        ctrl_bar = QHBoxLayout()
        ctrl_bar.addWidget(QLabel("Faculty Member:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.currentIndexChanged.connect(self.load_teacher_routine)
        ctrl_bar.addWidget(self.teacher_combo)

        self.lbl_teacher_workload = QLabel("Workload: 0 Periods/Week")
        self.lbl_teacher_workload.setStyleSheet("font-weight: bold; color: #10b981; padding-left: 12px;")
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

    # ==================== TAB 3: ROOM TIMETABLE ====================
    def _setup_room_tab(self):
        layout = QVBoxLayout(self.room_tab)
        layout.setSpacing(10)

        ctrl_bar = QHBoxLayout()
        ctrl_bar.addWidget(QLabel("Classroom / Laboratory:"))
        self.room_filter_combo = QComboBox()
        self.room_filter_combo.currentIndexChanged.connect(self.load_room_timetable)
        ctrl_bar.addWidget(self.room_filter_combo)

        self.lbl_room_util = QLabel("Utilization: 0%")
        self.lbl_room_util.setStyleSheet("font-weight: bold; color: #0284c7; padding-left: 12px;")
        ctrl_bar.addWidget(self.lbl_room_util)

        ctrl_bar.addStretch()

        btn_room_xlsx = QPushButton("Export Room Excel")
        btn_room_xlsx.setStyleSheet("background-color: #10b981; color: white; font-weight: bold; padding: 6px 12px;")
        btn_room_xlsx.clicked.connect(self._export_room_excel)
        ctrl_bar.addWidget(btn_room_xlsx)

        btn_room_pdf = QPushButton("Print Room PDF")
        btn_room_pdf.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 6px 12px;")
        btn_room_pdf.clicked.connect(self._export_room_pdf)
        ctrl_bar.addWidget(btn_room_pdf)

        layout.addLayout(ctrl_bar)

        self.room_table = QTableWidget()
        self.room_table.setAlternatingRowColors(True)
        layout.addWidget(self.room_table)

    # ==================== TAB 4: CONFLICTS & MULTI-SHIFT PERIODS ====================
    def _setup_period_and_conflict_tab(self):
        layout = QVBoxLayout(self.period_tab)
        layout.setSpacing(10)

        # Conflict Scanner Section
        conf_bar = QHBoxLayout()
        self.lbl_conflict_status = QLabel("Conflict Audit: Scanning...")
        self.lbl_conflict_status.setStyleSheet("font-weight: bold; font-size: 13px;")
        conf_bar.addWidget(self.lbl_conflict_status)
        conf_bar.addStretch()
        btn_scan = QPushButton("Re-Scan Teacher / Room / Class Conflicts")
        btn_scan.clicked.connect(self.load_conflicts_audit)
        conf_bar.addWidget(btn_scan)
        layout.addLayout(conf_bar)

        self.conflict_table = QTableWidget()
        self.conflict_table.setColumnCount(4)
        self.conflict_table.setHorizontalHeaderLabels(["Conflict Type", "Day", "Period", "Conflict Details"])
        self.conflict_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.conflict_table.setMaximumHeight(160)
        layout.addWidget(self.conflict_table)

        # Period Slots Section
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Multi-Shift Bell Schedule & Period Durations"))
        top_bar.addStretch()

        btn_seed_shifts = QPushButton("Seed Default Multi-Shift Bells (Morning/Day/Evening)")
        btn_seed_shifts.clicked.connect(self._seed_all_shifts)
        top_bar.addWidget(btn_seed_shifts)

        btn_add_p = QPushButton("+ Add Period Slot")
        btn_add_p.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 14px;")
        btn_add_p.clicked.connect(self._open_add_period_dialog)
        top_bar.addWidget(btn_add_p)

        layout.addLayout(top_bar)

        self.period_table = QTableWidget()
        self.period_table.setColumnCount(7)
        self.period_table.setHorizontalHeaderLabels([
            "Shift", "Period #", "Slot Name", "Start Time", "End Time", "Duration (Min)", "Type"
        ])
        self.period_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.period_table)

    # ==================== TAB 5: ACADEMIC YEAR HISTORY ====================
    def _setup_history_tab(self):
        layout = QVBoxLayout(self.history_tab)
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.addWidget(QLabel("Immutable Academic Year Timetable History, Snapshots & Cross-Year Carry-Forward"))
        top.addStretch()

        btn_snap = QPushButton("+ Archive Current Year Snapshot")
        btn_snap.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 6px 12px;")
        btn_snap.clicked.connect(self._archive_year_snapshot)
        top.addWidget(btn_snap)

        btn_clone = QPushButton("Clone From Previous Academic Year")
        btn_clone.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 12px;")
        btn_clone.clicked.connect(self._open_clone_year_dialog)
        top.addWidget(btn_clone)

        layout.addLayout(top)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "Timestamp", "Academic Year", "Shift", "Action", "Summary", "Reason", "Performed By"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for c in (0, 2, 3, 6):
            self.history_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)

    # ==================== DATA LOADING ====================
    def refresh_data(self):
        # Populate Academic Years
        curr_yr = self.year_combo.currentData()
        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        years = (
            self.db_session.query(AcademicYear)
            .filter(AcademicYear.is_deleted == False)
            .order_by(AcademicYear.is_current.desc(), AcademicYear.start_date.desc())
            .all()
        )
        for ay in years:
            lbl = f"{ay.name} [Current]" if ay.is_current else ay.name
            self.year_combo.addItem(lbl, ay.id)
        if curr_yr:
            idx = self.year_combo.findData(curr_yr)
            if idx >= 0:
                self.year_combo.setCurrentIndex(idx)
        self.year_combo.blockSignals(False)

        # Populate Multi-Shift Selector
        curr_sh = self.shift_combo.currentText()
        self.shift_combo.blockSignals(True)
        self.shift_combo.clear()
        shifts = ["Morning", "Day", "Evening"]
        for sh in self.db_session.query(AcademicShift).filter(AcademicShift.is_deleted == False, AcademicShift.is_active == True).all():
            if sh.name not in shifts:
                shifts.append(sh.name)
        self.shift_combo.addItems(shifts)
        if curr_sh:
            idx = self.shift_combo.findText(curr_sh)
            if idx >= 0:
                self.shift_combo.setCurrentIndex(idx)
        self.shift_combo.blockSignals(False)

        self._on_context_changed()

    def _on_context_changed(self):
        year_id = self._current_year_id()

        # Load Classes scoped to academic year (or all if legacy year has none)
        curr_cls = self.class_combo.currentData()
        self.class_combo.blockSignals(True)
        self.class_combo.clear()
        classes = (
            self.db_session.query(SchoolClass)
            .filter(SchoolClass.academic_year_id == year_id, SchoolClass.is_deleted == False)
            .order_by(SchoolClass.numeric_order.asc())
            .all()
        )
        if not classes:
            classes = (
                self.db_session.query(SchoolClass)
                .filter(SchoolClass.is_deleted == False)
                .order_by(SchoolClass.numeric_order.asc())
                .all()
            )
        for c in classes:
            self.class_combo.addItem(f"{c.name} ({c.group} | {c.shift})", c.id)
        if curr_cls:
            idx = self.class_combo.findData(curr_cls)
            if idx >= 0:
                self.class_combo.setCurrentIndex(idx)
        self.class_combo.blockSignals(False)

        # Load Teachers
        curr_t = self.teacher_combo.currentData()
        self.teacher_combo.blockSignals(True)
        self.teacher_combo.clear()
        for t in self.db_session.query(Teacher).filter(Teacher.status == "Active", Teacher.is_deleted == False).order_by(Teacher.name.asc()).all():
            self.teacher_combo.addItem(f"{t.name} ({t.employee_id})", t.id)
        if curr_t:
            idx = self.teacher_combo.findData(curr_t)
            if idx >= 0:
                self.teacher_combo.setCurrentIndex(idx)
        self.teacher_combo.blockSignals(False)

        # Load Rooms
        curr_rm = self.room_filter_combo.currentData()
        self.room_filter_combo.blockSignals(True)
        self.room_filter_combo.clear()
        for rm in TimetableRepository.get_distinct_rooms_and_catalog(self.db_session, academic_year_id=year_id):
            self.room_filter_combo.addItem(rm["label"], rm["room_number"])
        if curr_rm:
            idx = self.room_filter_combo.findData(curr_rm)
            if idx >= 0:
                self.room_filter_combo.setCurrentIndex(idx)
        self.room_filter_combo.blockSignals(False)

        self._on_class_changed()
        self.load_teacher_routine()
        self.load_room_timetable()
        self.load_periods()
        self.load_conflicts_audit()
        self.load_history()

    def _on_class_changed(self):
        class_id = self.class_combo.currentData()
        self.section_combo.blockSignals(True)
        self.section_combo.clear()
        self.section_combo.addItem("All Sections", None)
        if class_id:
            for s in self.db_session.query(Section).filter(Section.class_id == class_id).all():
                self.section_combo.addItem(f"Section {s.name}", s.id)
        self.section_combo.blockSignals(False)
        self.load_class_timetable()

    def _active_shift_periods(self):
        year_id = self._current_year_id()
        shift = self._current_shift()
        periods = TimetableRepository.get_period_slots(self.db_session, shift=shift, academic_year_id=year_id)
        if not periods:
            periods = TimetableService.seed_default_periods(self.db_session, academic_year_id=year_id, shift=shift)
        return periods

    def load_class_timetable(self):
        class_id = self.class_combo.currentData()
        if not class_id:
            self.class_table.setRowCount(0)
            return

        year_id = self._current_year_id()
        shift = self._current_shift()
        section_id = self.section_combo.currentData()
        periods = self._active_shift_periods()
        self.teaching_periods = [p for p in periods if not p.is_break or "Tiffin" in p.name or "Break" in p.name]

        self.class_table.setColumnCount(len(self.teaching_periods) + 1)
        headers = ["Day \\ Period"] + [f"{p.name}\n({p.start_time} - {p.end_time})" for p in self.teaching_periods]
        self.class_table.setHorizontalHeaderLabels(headers)
        self.class_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.class_table.setRowCount(len(STANDARD_DAYS))

        matrix = TimetableRepository.get_class_timetable_matrix(
            self.db_session, class_id, section_id=section_id, academic_year_id=year_id, shift=shift
        )

        for row_idx, day in enumerate(STANDARD_DAYS):
            day_item = QTableWidgetItem(day)
            day_item.setTextAlignment(Qt.AlignCenter)
            day_item.setFlags(Qt.ItemIsEnabled)
            self.class_table.setItem(row_idx, 0, day_item)

            for col_idx, p in enumerate(self.teaching_periods, start=1):
                if p.is_break:
                    item = QTableWidgetItem(p.name.upper())
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFlags(Qt.ItemIsEnabled)
                    item.setBackground(QColor("#334155"))
                    self.class_table.setItem(row_idx, col_idx, item)
                else:
                    entry = matrix.get(day, {}).get(p.id)
                    if entry:
                        sub_text = entry.subject.name if entry.subject else "Subject"
                        t_text = entry.teacher.name if entry.teacher else ""
                        r_text = entry.room_number or ""
                        auto_tag = " [Auto]" if entry.is_auto_generated else ""
                        item = QTableWidgetItem(f"{sub_text}{auto_tag}\n{t_text} | {r_text}")
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setData(Qt.UserRole, entry.id)
                        self.class_table.setItem(row_idx, col_idx, item)
                    else:
                        item = QTableWidgetItem("—")
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setData(Qt.UserRole, None)
                        self.class_table.setItem(row_idx, col_idx, item)
            self.class_table.setRowHeight(row_idx, 54)

    def load_teacher_routine(self):
        teacher_id = self.teacher_combo.currentData()
        if not teacher_id:
            self.teacher_table.setRowCount(0)
            return

        year_id = self._current_year_id()
        shift = self._current_shift()
        periods = self._active_shift_periods()
        teaching_periods = [p for p in periods if not p.is_break or "Tiffin" in p.name or "Break" in p.name]

        self.teacher_table.setColumnCount(len(teaching_periods) + 1)
        headers = ["Day \\ Period"] + [f"{p.name}\n({p.start_time} - {p.end_time})" for p in teaching_periods]
        self.teacher_table.setHorizontalHeaderLabels(headers)
        self.teacher_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.teacher_table.setRowCount(len(STANDARD_DAYS))

        matrix = TimetableRepository.get_teacher_routine_matrix(
            self.db_session, teacher_id, academic_year_id=year_id, shift=shift
        )
        total_slots = 0

        for row_idx, day in enumerate(STANDARD_DAYS):
            day_item = QTableWidgetItem(day)
            day_item.setTextAlignment(Qt.AlignCenter)
            day_item.setFlags(Qt.ItemIsEnabled)
            self.teacher_table.setItem(row_idx, 0, day_item)

            for col_idx, p in enumerate(teaching_periods, start=1):
                if p.is_break:
                    item = QTableWidgetItem(p.name.upper())
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFlags(Qt.ItemIsEnabled)
                    item.setBackground(QColor("#334155"))
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
            self.teacher_table.setRowHeight(row_idx, 54)

        self.lbl_teacher_workload.setText(f"Workload ({shift}): {total_slots} Teaching Periods / Week")

    def load_room_timetable(self):
        room_num = self.room_filter_combo.currentData()
        if not room_num:
            self.room_table.setRowCount(0)
            return

        year_id = self._current_year_id()
        shift = self._current_shift()
        periods = self._active_shift_periods()
        teaching_periods = [p for p in periods if not p.is_break]

        self.room_table.setColumnCount(len(teaching_periods) + 1)
        headers = ["Day \\ Period"] + [f"{p.name}\n({p.start_time} - {p.end_time})" for p in teaching_periods]
        self.room_table.setHorizontalHeaderLabels(headers)
        self.room_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.room_table.setRowCount(len(STANDARD_DAYS))

        matrix = TimetableRepository.get_room_timetable_matrix(
            self.db_session, room_number=room_num, academic_year_id=year_id, shift=shift
        )
        occupied = 0
        total = len(STANDARD_DAYS) * len(teaching_periods)

        for row_idx, day in enumerate(STANDARD_DAYS):
            day_item = QTableWidgetItem(day)
            day_item.setTextAlignment(Qt.AlignCenter)
            self.room_table.setItem(row_idx, 0, day_item)
            for col_idx, p in enumerate(teaching_periods, start=1):
                entry = matrix.get(day, {}).get(p.id)
                if entry:
                    occupied += 1
                    cls_n = entry.school_class.name if entry.school_class else "Class"
                    sub_n = entry.subject.name if entry.subject else ""
                    t_n = entry.teacher.name if entry.teacher else ""
                    item = QTableWidgetItem(f"{cls_n}\n{sub_n} ({t_n})")
                else:
                    item = QTableWidgetItem("Available")
                item.setTextAlignment(Qt.AlignCenter)
                self.room_table.setItem(row_idx, col_idx, item)
            self.room_table.setRowHeight(row_idx, 52)

        util = round((occupied / total) * 100.0, 1) if total > 0 else 0.0
        self.lbl_room_util.setText(f"Utilization ({shift}): {occupied}/{total} slots ({util}%)")

    def load_periods(self):
        year_id = self._current_year_id()
        shift = self._current_shift()
        periods = TimetableRepository.get_period_slots(self.db_session, shift=shift, academic_year_id=year_id)
        self.period_table.setRowCount(len(periods))
        for row, p in enumerate(periods):
            self.period_table.setItem(row, 0, QTableWidgetItem(p.shift))
            self.period_table.setItem(row, 1, QTableWidgetItem(str(p.period_number)))
            self.period_table.setItem(row, 2, QTableWidgetItem(p.name))
            self.period_table.setItem(row, 3, QTableWidgetItem(p.start_time))
            self.period_table.setItem(row, 4, QTableWidgetItem(p.end_time))
            self.period_table.setItem(row, 5, QTableWidgetItem(str(p.duration_minutes)))
            self.period_table.setItem(row, 6, QTableWidgetItem("Break / Interval" if p.is_break else "Teaching Period"))

    def load_conflicts_audit(self):
        year_id = self._current_year_id()
        issues = TimetableRepository.scan_all_conflicts(self.db_session, academic_year_id=year_id)
        self.conflict_table.setRowCount(len(issues))
        if not issues:
            self.lbl_conflict_status.setText("Conflict Audit: 0 Conflicts Detected (Clean Schedule)")
            self.lbl_conflict_status.setStyleSheet("font-weight: bold; color: #10b981; font-size: 13px;")
        else:
            self.lbl_conflict_status.setText(f"Conflict Audit: {len(issues)} Scheduling Conflict(s) Found!")
            self.lbl_conflict_status.setStyleSheet("font-weight: bold; color: #ef4444; font-size: 13px;")

        for row, c in enumerate(issues):
            t_it = QTableWidgetItem(c["type"])
            t_it.setForeground(QColor("#ef4444"))
            t_it.setFont(QFont("Helvetica", 9, QFont.Bold))
            self.conflict_table.setItem(row, 0, t_it)
            self.conflict_table.setItem(row, 1, QTableWidgetItem(c["day"]))
            self.conflict_table.setItem(row, 2, QTableWidgetItem(c["period"]))
            self.conflict_table.setItem(row, 3, QTableWidgetItem(c["detail"]))

    def load_history(self):
        year_id = self._current_year_id()
        rows = TimetableRepository.list_history(self.db_session, academic_year_id=year_id)
        self.history_table.setRowCount(len(rows))
        for r_idx, h in enumerate(rows):
            ts = h.performed_at.strftime("%Y-%m-%d %H:%M") if h.performed_at else "-"
            self.history_table.setItem(r_idx, 0, QTableWidgetItem(ts))
            self.history_table.setItem(r_idx, 1, QTableWidgetItem(h.academic_year.name if h.academic_year else str(h.academic_year_id)))
            self.history_table.setItem(r_idx, 2, QTableWidgetItem(h.shift_name or "-"))
            self.history_table.setItem(r_idx, 3, QTableWidgetItem(h.action))
            self.history_table.setItem(r_idx, 4, QTableWidgetItem(h.entry_summary or "-"))
            self.history_table.setItem(r_idx, 5, QTableWidgetItem(h.reason or "-"))
            self.history_table.setItem(r_idx, 6, QTableWidgetItem(h.performed_by))

    # ==================== DIALOGS & INTERACTIONS ====================
    def _open_add_slot_dialog(self):
        class_id = self.class_combo.currentData()
        section_id = self.section_combo.currentData()
        if not class_id:
            return
        dialog = TimetableSlotDialog(
            self.db_session,
            class_id=class_id,
            section_id=section_id,
            academic_year_id=self._current_year_id(),
            shift=self._current_shift(),
            parent=self,
        )
        if dialog.exec():
            self._refresh_views_after_edit()

    def _on_class_cell_double_clicked(self, row: int, col: int):
        if col == 0 or row >= len(STANDARD_DAYS) or (col - 1) >= len(self.teaching_periods):
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
            academic_year_id=self._current_year_id(),
            shift=self._current_shift(),
            parent=self,
        )
        if dialog.exec():
            self._refresh_views_after_edit()

    def _open_auto_suggest_dialog(self):
        class_id = self.class_combo.currentData()
        if not class_id:
            return
        section_id = self.section_combo.currentData()
        year_id = self._current_year_id()
        shift = self._current_shift()

        dlg = QDialog(self)
        dlg.setWindowTitle("Automatic Timetable Suggestion Wizard")
        dlg.setMinimumWidth(640)
        lay = QVBoxLayout(dlg)

        lay.addWidget(QLabel(f"Configure weekly periods per subject for {self.class_combo.currentText()} ({shift} Shift):"))
        subjects = self.db_session.query(Subject).filter(Subject.class_id == class_id, Subject.is_deleted == False).all()
        quota_spins: Dict[int, QSpinBox] = {}
        form = QFormLayout()
        for sub in subjects:
            sp = QSpinBox()
            sp.setRange(0, 12)
            sp.setValue(4)
            quota_spins[sub.id] = sp
            form.addRow(f"{sub.name} ({sub.code}):", sp)
        lay.addLayout(form)

        chk_clear = QCheckBox("Clear existing routine for this class/section before applying suggestions")
        lay.addWidget(chk_clear)

        preview_table = QTableWidget()
        preview_table.setColumnCount(5)
        preview_table.setHorizontalHeaderLabels(["Day", "Period", "Subject", "Teacher", "Room"])
        preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(preview_table)

        lbl_stats = QLabel("Click 'Preview Suggestions' to generate conflict-free slots.")
        lay.addWidget(lbl_stats)

        btns = QHBoxLayout()
        btn_prev = QPushButton("Preview Suggestions")
        btn_apply = QPushButton("Apply Suggested Timetable")
        btn_apply.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 14px;")
        btns.addWidget(btn_prev)
        btns.addStretch()
        btns.addWidget(btn_apply)
        lay.addLayout(btns)

        def _preview():
            quotas = {sid: sp.value() for sid, sp in quota_spins.items()}
            res = TimetableService.suggest_timetable(
                self.db_session,
                academic_year_id=year_id,
                class_id=class_id,
                section_id=section_id,
                shift=shift,
                subject_weekly_quotas=quotas,
                apply_immediately=False,
            )
            suggs = res["suggestions"]
            preview_table.setRowCount(len(suggs))
            for i, s in enumerate(suggs):
                preview_table.setItem(i, 0, QTableWidgetItem(s["day_of_week"]))
                preview_table.setItem(i, 1, QTableWidgetItem(s["period_name"]))
                preview_table.setItem(i, 2, QTableWidgetItem(s["subject_name"]))
                preview_table.setItem(i, 3, QTableWidgetItem(s["teacher_name"]))
                preview_table.setItem(i, 4, QTableWidgetItem(s["room_number"]))
            lbl_stats.setText(
                f"Suggested {len(suggs)}/{res['total_requested']} slots | "
                f"Unplaced: {len(res['unplaced'])} | Utilization: {res['utilization_pct']}% | "
                f"Conflicts Avoided: {res['conflicts_avoided']}"
            )

        def _apply():
            quotas = {sid: sp.value() for sid, sp in quota_spins.items()}
            res = TimetableService.suggest_timetable(
                self.db_session,
                academic_year_id=year_id,
                class_id=class_id,
                section_id=section_id,
                shift=shift,
                subject_weekly_quotas=quotas,
                apply_immediately=True,
                clear_existing_class_slots=chk_clear.isChecked(),
                actor_user=self._actor(),
            )
            QMessageBox.information(
                dlg,
                "Auto-Timetable Applied",
                f"Applied {res['applied_count']} conflict-free slots (Unplaced: {len(res['unplaced'])}).",
            )
            dlg.accept()

        btn_prev.clicked.connect(_preview)
        btn_apply.clicked.connect(_apply)
        if dlg.exec():
            self._refresh_views_after_edit()

    def _open_move_swap_dialog(self):
        class_id = self.class_combo.currentData()
        section_id = self.section_combo.currentData()
        if not class_id:
            return
        entries = TimetableRepository.get_all_entries(
            self.db_session,
            class_id=class_id,
            section_id=section_id,
            academic_year_id=self._current_year_id(),
            shift=self._current_shift(),
        )
        if not entries:
            QMessageBox.information(self, "Move / Swap", "No assigned slots exist for this class yet.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Move or Swap Timetable Slot")
        form = QFormLayout(dlg)

        cb_src = QComboBox()
        for e in entries:
            p_lbl = e.period_slot.name if e.period_slot else str(e.period_slot_id)
            s_lbl = e.subject.name if e.subject else str(e.subject_id)
            cb_src.addItem(f"{e.day_of_week} | {p_lbl} — {s_lbl} ({e.room_number})", e.id)

        cb_day = QComboBox()
        cb_day.addItems(STANDARD_DAYS)
        cb_period = QComboBox()
        for p in [x for x in self._active_shift_periods() if not x.is_break]:
            cb_period.addItem(f"{p.name} ({p.start_time}-{p.end_time})", p.id)

        chk_swap = QCheckBox("Swap atomically if target period is already occupied")
        chk_swap.setChecked(True)

        form.addRow("Source Slot:", cb_src)
        form.addRow("Target Day:", cb_day)
        form.addRow("Target Period:", cb_period)
        form.addRow("", chk_swap)

        btn_go = QPushButton("Move / Swap Now")
        form.addRow(btn_go)

        def _exec_move():
            ok, conflicts, msg = TimetableService.move_or_swap_slot(
                self.db_session,
                entry_id=cb_src.currentData(),
                target_day=cb_day.currentText(),
                target_period_slot_id=cb_period.currentData(),
                swap_if_occupied=chk_swap.isChecked(),
                actor_user=self._actor(),
            )
            if ok:
                QMessageBox.information(dlg, "Updated", msg)
                dlg.accept()
            else:
                QMessageBox.warning(dlg, "Conflict Detected", msg)

        btn_go.clicked.connect(_exec_move)
        if dlg.exec():
            self._refresh_views_after_edit()

    def _open_add_period_dialog(self):
        dialog = PeriodConfigDialog(
            self.db_session,
            default_shift=self._current_shift(),
            academic_year_id=self._current_year_id(),
            parent=self,
        )
        if dialog.exec():
            self.load_periods()
            self.load_class_timetable()

    def _seed_all_shifts(self):
        TimetableService.seed_all_shift_periods(self.db_session, academic_year_id=self._current_year_id())
        QMessageBox.information(self, "Shifts Seeded", "Default bell schedules ensured for Morning, Day, and Evening shifts.")
        self.load_periods()

    def _archive_year_snapshot(self):
        year_id = self._current_year_id()
        reason, accepted = QInputDialog.getText(
            self, "Archive Timetable Snapshot", "Enter snapshot label/reason for this academic year:"
        )
        if not accepted:
            return
        TimetableService.save_year_snapshot(
            self.db_session,
            academic_year_id=year_id,
            reason=reason.strip() or "Manual Academic Year Snapshot",
            actor_user=self._actor(),
        )
        QMessageBox.information(self, "Archived", "Academic year timetable snapshot saved to immutable history.")
        self.load_history()

    def _open_clone_year_dialog(self):
        years = self.db_session.query(AcademicYear).filter(AcademicYear.is_deleted == False).all()
        if len(years) < 2:
            QMessageBox.information(self, "Clone Year", "At least two Academic Years are required to clone historical routines.")
            return
        target_id = self._current_year_id()
        src_choices = [f"{y.id}: {y.name}" for y in years if y.id != target_id]
        choice, accepted = QInputDialog.getItem(
            self, "Clone Timetable From Year", "Select source Academic Year to clone into current year:", src_choices, 0, False
        )
        if not accepted or not choice:
            return
        src_id = int(choice.split(":", 1)[0])
        cloned, skipped = TimetableService.clone_timetable_from_year(
            self.db_session, src_id, target_id, shift=self._current_shift(), actor_user=self._actor()
        )
        QMessageBox.information(self, "Clone Finished", f"Cloned {cloned} slots into active year ({skipped} skipped due to conflicts/mismatch).")
        self._refresh_views_after_edit()

    def _refresh_views_after_edit(self):
        self.load_class_timetable()
        self.load_teacher_routine()
        self.load_room_timetable()
        self.load_conflicts_audit()
        self.load_history()

    # ==================== EXPORTS & PRINTABLE PDFs ====================
    def _school_dict(self):
        school = self.db_session.query(SchoolSetting).first()
        return {
            "school_name": school.school_name if school else "EduManage Pro Model High School",
            "eiin_number": school.eiin_number if school else "134211",
            "address": school.address if school else "Uttara, Dhaka",
        }

    def _export_excel(self):
        class_id = self.class_combo.currentData()
        if not class_id:
            return
        class_name = self.class_combo.currentText()
        section_name = self.section_combo.currentText()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Timetable Excel", f"Class_Timetable_{class_name.split()[0]}.xlsx", "Excel Files (*.xlsx)"
        )
        if file_path:
            ok = TimetableService.export_class_timetable_excel(
                session=self.db_session,
                class_id=class_id,
                class_name=class_name,
                section_name=section_name,
                school_name=self._school_dict()["school_name"],
                output_path=file_path,
                academic_year_id=self._current_year_id(),
                shift=self._current_shift(),
            )
            if ok:
                QMessageBox.information(self, "Export Success", f"Timetable exported to:\n{file_path}")

    def _export_pdf(self):
        class_id = self.class_combo.currentData()
        if not class_id:
            return
        class_name = self.class_combo.currentText()
        section_name = self.section_combo.currentText()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Class Timetable PDF", f"Class_Routine_{class_name.split()[0]}.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        periods = self._active_shift_periods()
        period_dicts = [
            {"id": p.id, "name": p.name, "start_time": p.start_time, "end_time": p.end_time, "is_break": p.is_break}
            for p in periods
        ]
        matrix_raw = TimetableRepository.get_class_timetable_matrix(
            self.db_session,
            class_id,
            section_id=self.section_combo.currentData(),
            academic_year_id=self._current_year_id(),
            shift=self._current_shift(),
        )
        matrix = {
            d: {
                pid: {
                    "subject_name": e.subject.name if e.subject else "",
                    "teacher_name": e.teacher.name if e.teacher else "",
                    "room_number": e.room_number or "",
                }
                for pid, e in p_dict.items()
            }
            for d, p_dict in matrix_raw.items()
        }
        if ClassTimetablePDFGenerator.generate_timetable(
            class_name=class_name,
            section_name=section_name,
            shift_name=self._current_shift(),
            school_info=self._school_dict(),
            periods=period_dicts,
            matrix=matrix,
            output_path=file_path,
            academic_year_label=self.year_combo.currentText(),
        ):
            QMessageBox.information(self, "Export Success", f"Class routine PDF generated:\n{file_path}")

    def _export_teacher_pdf(self):
        teacher_id = self.teacher_combo.currentData()
        teacher = self.db_session.query(Teacher).filter(Teacher.id == teacher_id).first()
        if not teacher:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Teacher Routine PDF", f"Routine_{teacher.name.replace(' ', '_')}.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        periods = self._active_shift_periods()
        period_dicts = [
            {"id": p.id, "name": p.name, "start_time": p.start_time, "end_time": p.end_time, "is_break": p.is_break}
            for p in periods
        ]
        matrix_raw = TimetableRepository.get_teacher_routine_matrix(
            self.db_session, teacher.id, academic_year_id=self._current_year_id(), shift=self._current_shift()
        )
        total_slots = sum(len(p_dict) for p_dict in matrix_raw.values())
        matrix = {
            d: {
                pid: {
                    "class_name": e.school_class.name if e.school_class else "",
                    "section_name": e.section.name if e.section else "",
                    "subject_name": e.subject.name if e.subject else "",
                    "room_number": e.room_number or "",
                }
                for pid, e in p_dict.items()
            }
            for d, p_dict in matrix_raw.items()
        }
        teacher_info = {
            "name": teacher.name,
            "employee_id": teacher.employee_id,
            "department": teacher.department.name if teacher.department else "General",
            "designation": teacher.designation or "Lecturer",
            "total_weekly_periods": total_slots,
        }
        if TeacherRoutinePDFGenerator.generate_routine(
            teacher_info=teacher_info,
            school_info=self._school_dict(),
            periods=period_dicts,
            matrix=matrix,
            output_path=file_path,
        ):
            QMessageBox.information(self, "Export Success", f"Faculty Routine PDF generated:\n{file_path}")

    def _export_room_excel(self):
        room_num = self.room_filter_combo.currentData()
        if not room_num:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Room Timetable Excel", f"Room_Schedule_{room_num.replace(' ', '_')}.xlsx", "Excel Files (*.xlsx)"
        )
        if path:
            if TimetableService.export_room_timetable_excel(
                self.db_session,
                room_number=room_num,
                school_name=self._school_dict()["school_name"],
                output_path=path,
                academic_year_id=self._current_year_id(),
                shift=self._current_shift(),
            ):
                QMessageBox.information(self, "Export Success", f"Room schedule exported to:\n{path}")

    def _export_room_pdf(self):
        room_num = self.room_filter_combo.currentData()
        if not room_num:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Room Timetable PDF", f"Room_Timetable_{room_num.replace(' ', '_')}.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        rm_obj = self.db_session.query(AcademicRoom).filter(AcademicRoom.room_number == room_num).first()
        room_info = {
            "room_number": room_num,
            "room_type": rm_obj.room_type if rm_obj else "Classroom",
            "capacity": rm_obj.capacity if rm_obj else 40,
        }
        periods = self._active_shift_periods()
        period_dicts = [
            {"id": p.id, "name": p.name, "start_time": p.start_time, "end_time": p.end_time, "is_break": p.is_break}
            for p in periods
        ]
        matrix_raw = TimetableRepository.get_room_timetable_matrix(
            self.db_session, room_number=room_num, academic_year_id=self._current_year_id(), shift=self._current_shift()
        )
        matrix = {
            d: {
                pid: {
                    "class_name": e.school_class.name if e.school_class else "",
                    "section_name": e.section.name if e.section else "",
                    "subject_name": e.subject.name if e.subject else "",
                    "teacher_name": e.teacher.name if e.teacher else "",
                }
                for pid, e in p_dict.items()
            }
            for d, p_dict in matrix_raw.items()
        }
        if RoomTimetablePDFGenerator.generate_room_timetable(
            room_info=room_info,
            school_info=self._school_dict(),
            periods=period_dicts,
            matrix=matrix,
            output_path=path,
            shift_name=self._current_shift(),
            academic_year_label=self.year_combo.currentText(),
        ):
            QMessageBox.information(self, "Export Success", f"Room timetable PDF generated:\n{path}")
