"""
EduManage Pro - Academic Configuration Wizard Dialog (PySide6)
Multi-step guided wizard for setting up Academic Years, Groups, Shifts, Departments,
Custom Class Structures (Presets, Custom Hierarchy, or Non-Destructive Clone), Rooms, and Subjects.
"""

from datetime import date
from typing import Any, Dict, List

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.repositories.academic_repository import AcademicRepository
from app.services.academic_service import AcademicService, STRUCTURE_PRESETS


class AcademicWizardDialog(QDialog):
    """5-Step Academic Configuration Wizard supporting presets, cloning, and custom structures."""

    def __init__(self, parent=None, actor: str = "admin"):
        super().__init__(parent)
        self.actor = actor
        self.setWindowTitle("EduManage Pro — Academic Configuration Wizard")
        self.resize(860, 640)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._step_titles = [
            "1. Academic Session & Setup Mode",
            "2. Groups, Shifts & Departments",
            "3. Custom Class & Section Structure",
            "4. Rooms & Curriculum Defaults",
            "5. Review & Apply Configuration",
        ]
        self._init_ui()
        self._load_initial_data()
        self._go_to_step(0)

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        # Header banner
        banner = QFrame()
        banner.setStyleSheet("background-color: #1E3A8A; border-radius: 8px;")
        b_lay = QVBoxLayout(banner)
        b_lay.setContentsMargins(16, 12, 16, 12)
        self.lbl_step_title = QLabel("1. Academic Session & Setup Mode")
        self.lbl_step_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        self.lbl_step_sub = QLabel(
            "Guided institutional setup — previous academic year records are never overwritten."
        )
        self.lbl_step_sub.setStyleSheet("color: #BFDBFE; font-size: 12px;")
        b_lay.addWidget(self.lbl_step_title)
        b_lay.addWidget(self.lbl_step_sub)
        root.addWidget(banner)

        # Main stacked pages
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_step1_session())
        self.stack.addWidget(self._build_step2_groups_shifts())
        self.stack.addWidget(self._build_step3_class_builder())
        self.stack.addWidget(self._build_step4_rooms_subjects())
        self.stack.addWidget(self._build_step5_review())
        root.addWidget(self.stack, stretch=1)

        # Wizard Navigation Footer
        nav = QHBoxLayout()
        self.lbl_progress = QLabel("Step 1 of 5")
        self.lbl_progress.setStyleSheet("font-weight: bold; color: #475569;")
        nav.addWidget(self.lbl_progress)
        nav.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        nav.addWidget(self.btn_cancel)

        self.btn_back = QPushButton("← Previous")
        self.btn_back.clicked.connect(self._on_back)
        nav.addWidget(self.btn_back)

        self.btn_next = QPushButton("Next →")
        self.btn_next.setStyleSheet(
            "background-color: #2563EB; color: white; font-weight: bold; padding: 8px 18px; border-radius: 5px;"
        )
        self.btn_next.clicked.connect(self._on_next)
        nav.addWidget(self.btn_next)

        self.btn_finish = QPushButton("Apply Academic Configuration")
        self.btn_finish.setStyleSheet(
            "background-color: #059669; color: white; font-weight: bold; padding: 8px 18px; border-radius: 5px;"
        )
        self.btn_finish.clicked.connect(self._on_apply)
        nav.addWidget(self.btn_finish)

        root.addLayout(nav)

    # ------------------------------------------------------------------
    # Step 1: Academic Year & Mode
    # ------------------------------------------------------------------
    def _build_step1_session(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        grp_yr = QGroupBox("Target Academic Year")
        yr_form = QFormLayout(grp_yr)

        self.rb_new_year = QRadioButton("Create New Academic Year")
        self.rb_existing_year = QRadioButton("Configure Existing Academic Year")
        self.rb_new_year.setChecked(True)
        self.rb_new_year.toggled.connect(self._toggle_year_mode)

        mode_row = QHBoxLayout()
        mode_row.addWidget(self.rb_new_year)
        mode_row.addWidget(self.rb_existing_year)
        mode_row.addStretch()
        yr_form.addRow("Target:", mode_row)

        self.existing_year_combo = QComboBox()
        self.existing_year_combo.setEnabled(False)
        yr_form.addRow("Existing Session:", self.existing_year_combo)

        curr_yr = date.today().year
        self.new_year_name = QLineEdit(f"{curr_yr}-{curr_yr + 1}")
        self.new_year_start = QDateEdit(QDate(curr_yr, 1, 1))
        self.new_year_start.setCalendarPopup(True)
        self.new_year_end = QDateEdit(QDate(curr_yr, 12, 31))
        self.new_year_end.setCalendarPopup(True)
        self.chk_activate_year = QCheckBox("Set as Active Current Academic Session")
        self.chk_activate_year.setChecked(True)

        yr_form.addRow("New Year Name:*", self.new_year_name)
        yr_form.addRow("Start Date:*", self.new_year_start)
        yr_form.addRow("End Date:*", self.new_year_end)
        yr_form.addRow("", self.chk_activate_year)
        lay.addWidget(grp_yr)

        grp_mode = QGroupBox("Structure Initialization Strategy")
        m_lay = QVBoxLayout(grp_mode)

        self.rb_preset = QRadioButton("Start from Institutional Class Preset Template (or Custom Builder)")
        self.rb_preset.setChecked(True)
        self.rb_clone = QRadioButton("Non-Destructively Clone Classes, Sections & Subjects from Previous Year")
        self.rb_preset.toggled.connect(self._toggle_strategy_mode)

        m_lay.addWidget(self.rb_preset)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(STRUCTURE_PRESETS.keys()))
        self.preset_combo.currentTextChanged.connect(self._load_preset_into_builder)
        m_lay.addWidget(self.preset_combo)

        m_lay.addSpacing(8)
        m_lay.addWidget(self.rb_clone)
        clone_opts = QHBoxLayout()
        clone_opts.addWidget(QLabel("Source Year:"))
        self.clone_source_combo = QComboBox()
        self.clone_source_combo.setEnabled(False)
        clone_opts.addWidget(self.clone_source_combo, stretch=1)
        self.chk_clone_sections = QCheckBox("Sections")
        self.chk_clone_sections.setChecked(True)
        self.chk_clone_subjects = QCheckBox("Subjects")
        self.chk_clone_subjects.setChecked(True)
        self.chk_clone_teachers = QCheckBox("Teacher Assignments")
        self.chk_clone_teachers.setChecked(True)
        clone_opts.addWidget(self.chk_clone_sections)
        clone_opts.addWidget(self.chk_clone_subjects)
        clone_opts.addWidget(self.chk_clone_teachers)
        m_lay.addLayout(clone_opts)

        lay.addWidget(grp_mode)
        lay.addStretch()
        return w

    def _toggle_year_mode(self):
        new_mode = self.rb_new_year.isChecked()
        self.existing_year_combo.setEnabled(not new_mode)
        self.new_year_name.setEnabled(new_mode)
        self.new_year_start.setEnabled(new_mode)
        self.new_year_end.setEnabled(new_mode)

    def _toggle_strategy_mode(self):
        clone_mode = self.rb_clone.isChecked()
        self.preset_combo.setEnabled(not clone_mode)
        self.clone_source_combo.setEnabled(clone_mode)
        self.chk_clone_sections.setEnabled(clone_mode)
        self.chk_clone_subjects.setEnabled(clone_mode)
        self.chk_clone_teachers.setEnabled(clone_mode)

    # ------------------------------------------------------------------
    # Step 2: Groups, Shifts & Departments
    # ------------------------------------------------------------------
    def _build_step2_groups_shifts(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        info = QLabel(
            "Standard Groups (General, Science, Humanities, Business Studies), Shifts (Morning, Day, Evening), "
            "and Academic Departments are pre-seeded automatically. Add any extra institutional streams or shifts below."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #334155; background: #F8FAFC; padding: 8px; border-radius: 6px;")
        lay.addWidget(info)

        # Extra Group add row
        grp_box = QGroupBox("Custom Academic Groups / Streams (Queued for Wizard)")
        g_lay = QVBoxLayout(grp_box)
        g_row = QHBoxLayout()
        self.wiz_grp_name = QLineEdit()
        self.wiz_grp_name.setPlaceholderText("Group Name (e.g. Vocational, Cambridge A-Level)")
        self.wiz_grp_code = QLineEdit()
        self.wiz_grp_code.setPlaceholderText("Code (e.g. VOC)")
        self.wiz_grp_code.setFixedWidth(100)
        btn_add_g = QPushButton("+ Queue Group")
        btn_add_g.clicked.connect(self._queue_group)
        g_row.addWidget(self.wiz_grp_name)
        g_row.addWidget(self.wiz_grp_code)
        g_row.addWidget(btn_add_g)
        g_lay.addLayout(g_row)

        self.groups_table = QTableWidget(0, 3)
        self.groups_table.setHorizontalHeaderLabels(["Group Name", "Code", "Origin"])
        self.groups_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        g_lay.addWidget(self.groups_table)
        lay.addWidget(grp_box)

        # Extra Shift add row
        sh_box = QGroupBox("Campus Shifts & Timings")
        s_lay = QVBoxLayout(sh_box)
        s_row = QHBoxLayout()
        self.wiz_sh_name = QLineEdit()
        self.wiz_sh_name.setPlaceholderText("Shift Name (e.g. Weekend)")
        self.wiz_sh_code = QLineEdit()
        self.wiz_sh_code.setPlaceholderText("Code (WKD)")
        self.wiz_sh_code.setFixedWidth(90)
        self.wiz_sh_start = QLineEdit()
        self.wiz_sh_start.setPlaceholderText("Start (08:00 AM)")
        self.wiz_sh_end = QLineEdit()
        self.wiz_sh_end.setPlaceholderText("End (01:00 PM)")
        btn_add_s = QPushButton("+ Queue Shift")
        btn_add_s.clicked.connect(self._queue_shift)
        s_row.addWidget(self.wiz_sh_name)
        s_row.addWidget(self.wiz_sh_code)
        s_row.addWidget(self.wiz_sh_start)
        s_row.addWidget(self.wiz_sh_end)
        s_row.addWidget(btn_add_s)
        s_lay.addLayout(s_row)

        self.shifts_table = QTableWidget(0, 4)
        self.shifts_table.setHorizontalHeaderLabels(["Shift Name", "Code", "Start Time", "End Time"])
        self.shifts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        s_lay.addWidget(self.shifts_table)
        lay.addWidget(sh_box)

        return w

    def _queue_group(self):
        name = self.wiz_grp_name.text().strip()
        code = (self.wiz_grp_code.text().strip() or name[:4]).upper()
        if not name:
            return
        r = self.groups_table.rowCount()
        self.groups_table.insertRow(r)
        self.groups_table.setItem(r, 0, QTableWidgetItem(name))
        self.groups_table.setItem(r, 1, QTableWidgetItem(code))
        self.groups_table.setItem(r, 2, QTableWidgetItem("New (Wizard)"))
        self.wiz_grp_name.clear()
        self.wiz_grp_code.clear()

    def _queue_shift(self):
        name = self.wiz_sh_name.text().strip()
        code = (self.wiz_sh_code.text().strip() or name[:3]).upper()
        if not name:
            return
        r = self.shifts_table.rowCount()
        self.shifts_table.insertRow(r)
        self.shifts_table.setItem(r, 0, QTableWidgetItem(name))
        self.shifts_table.setItem(r, 1, QTableWidgetItem(code))
        self.shifts_table.setItem(r, 2, QTableWidgetItem(self.wiz_sh_start.text().strip() or "-"))
        self.shifts_table.setItem(r, 3, QTableWidgetItem(self.wiz_sh_end.text().strip() or "-"))
        self.wiz_sh_name.clear()
        self.wiz_sh_code.clear()
        self.wiz_sh_start.clear()
        self.wiz_sh_end.clear()

    # ------------------------------------------------------------------
    # Step 3: Custom Class & Section Structure Builder
    # ------------------------------------------------------------------
    def _build_step3_class_builder(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)

        self.lbl_builder_note = QLabel(
            "Customize class levels, numeric order, streams, shifts, and comma-separated sections below. "
            "Cells are directly editable."
        )
        self.lbl_builder_note.setWordWrap(True)
        lay.addWidget(self.lbl_builder_note)

        ctrl = QHBoxLayout()
        btn_add_row = QPushButton("+ Add Custom Class Level")
        btn_add_row.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 5px 12px; border-radius: 4px;")
        btn_add_row.clicked.connect(self._add_custom_class_row)
        btn_del_row = QPushButton("Remove Selected Row")
        btn_del_row.clicked.connect(self._remove_selected_class_row)
        ctrl.addWidget(btn_add_row)
        ctrl.addWidget(btn_del_row)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self.builder_table = QTableWidget(0, 7)
        self.builder_table.setHorizontalHeaderLabels([
            "Class Name*", "Code", "Order", "Group / Stream", "Shift", "Sections (comma-sep)", "Capacity"
        ])
        self.builder_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.builder_table)
        return w

    def _load_preset_into_builder(self, preset_name: str):
        preset = AcademicService.get_preset_structure(preset_name)
        classes = preset.get("classes", [])
        self.builder_table.setRowCount(0)
        for cls in classes:
            r = self.builder_table.rowCount()
            self.builder_table.insertRow(r)
            self.builder_table.setItem(r, 0, QTableWidgetItem(cls["name"]))
            self.builder_table.setItem(r, 1, QTableWidgetItem(cls.get("code", "")))
            self.builder_table.setItem(r, 2, QTableWidgetItem(str(cls.get("numeric_order", r + 1))))
            self.builder_table.setItem(r, 3, QTableWidgetItem(cls.get("group", "General")))
            self.builder_table.setItem(r, 4, QTableWidgetItem(cls.get("shift", "Morning")))
            self.builder_table.setItem(r, 5, QTableWidgetItem(", ".join(cls.get("sections", ["Section A"]))))
            self.builder_table.setItem(r, 6, QTableWidgetItem("50"))

    def _add_custom_class_row(self):
        r = self.builder_table.rowCount()
        self.builder_table.insertRow(r)
        self.builder_table.setItem(r, 0, QTableWidgetItem(f"Grade {r + 1}"))
        self.builder_table.setItem(r, 1, QTableWidgetItem(f"G{r + 1:02d}"))
        self.builder_table.setItem(r, 2, QTableWidgetItem(str(r + 1)))
        self.builder_table.setItem(r, 3, QTableWidgetItem("General"))
        self.builder_table.setItem(r, 4, QTableWidgetItem("Morning"))
        self.builder_table.setItem(r, 5, QTableWidgetItem("Section A, Section B"))
        self.builder_table.setItem(r, 6, QTableWidgetItem("45"))

    def _remove_selected_class_row(self):
        row = self.builder_table.currentRow()
        if row >= 0:
            self.builder_table.removeRow(row)

    # ------------------------------------------------------------------
    # Step 4: Rooms & Default Starter Subjects
    # ------------------------------------------------------------------
    def _build_step4_rooms_subjects(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        rm_box = QGroupBox("Campus Rooms / Labs (Optional Batch Creation)")
        rm_lay = QVBoxLayout(rm_box)
        rm_row = QHBoxLayout()
        self.wiz_rm_no = QLineEdit()
        self.wiz_rm_no.setPlaceholderText("Room No (e.g. R-101)")
        self.wiz_rm_name = QLineEdit()
        self.wiz_rm_name.setPlaceholderText("Room Name / Lab")
        self.wiz_rm_type = QComboBox()
        self.wiz_rm_type.addItems(["Classroom", "Science Lab", "Computer Lab", "Auditorium", "Library"])
        self.wiz_rm_cap = QSpinBox()
        self.wiz_rm_cap.setRange(10, 500)
        self.wiz_rm_cap.setValue(50)
        btn_rm = QPushButton("+ Queue Room")
        btn_rm.clicked.connect(self._queue_room)
        rm_row.addWidget(self.wiz_rm_no)
        rm_row.addWidget(self.wiz_rm_name)
        rm_row.addWidget(self.wiz_rm_type)
        rm_row.addWidget(self.wiz_rm_cap)
        rm_row.addWidget(btn_rm)
        rm_lay.addLayout(rm_row)

        self.rooms_table = QTableWidget(0, 4)
        self.rooms_table.setHorizontalHeaderLabels(["Room No", "Name", "Type", "Capacity"])
        self.rooms_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rm_lay.addWidget(self.rooms_table)
        lay.addWidget(rm_box)

        sub_box = QGroupBox("Core Subjects Applied to Each New Class (Optional)")
        sub_lay = QVBoxLayout(sub_box)
        sub_row = QHBoxLayout()
        self.wiz_sub_name = QLineEdit()
        self.wiz_sub_name.setPlaceholderText("Subject Name (e.g. English, Higher Math)")
        self.wiz_sub_code = QLineEdit()
        self.wiz_sub_code.setPlaceholderText("Code (e.g. 101)")
        self.wiz_sub_code.setFixedWidth(90)
        self.wiz_sub_type = QComboBox()
        self.wiz_sub_type.addItems(["Mandatory", "Optional", "Elective"])
        btn_sub = QPushButton("+ Add Subject")
        btn_sub.clicked.connect(self._queue_subject)
        sub_row.addWidget(self.wiz_sub_name)
        sub_row.addWidget(self.wiz_sub_code)
        sub_row.addWidget(self.wiz_sub_type)
        sub_row.addWidget(btn_sub)
        sub_lay.addLayout(sub_row)

        self.subjects_table = QTableWidget(0, 4)
        self.subjects_table.setHorizontalHeaderLabels(["Subject Name", "Code", "Type", "Full / Pass"])
        self.subjects_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        sub_lay.addWidget(self.subjects_table)
        lay.addWidget(sub_box)

        return w

    def _queue_room(self):
        no = self.wiz_rm_no.text().strip()
        if not no:
            return
        r = self.rooms_table.rowCount()
        self.rooms_table.insertRow(r)
        self.rooms_table.setItem(r, 0, QTableWidgetItem(no))
        self.rooms_table.setItem(r, 1, QTableWidgetItem(self.wiz_rm_name.text().strip() or no))
        self.rooms_table.setItem(r, 2, QTableWidgetItem(self.wiz_rm_type.currentText()))
        self.rooms_table.setItem(r, 3, QTableWidgetItem(str(self.wiz_rm_cap.value())))
        self.wiz_rm_no.clear()
        self.wiz_rm_name.clear()

    def _queue_subject(self):
        name = self.wiz_sub_name.text().strip()
        code = self.wiz_sub_code.text().strip()
        if not name or not code:
            return
        r = self.subjects_table.rowCount()
        self.subjects_table.insertRow(r)
        self.subjects_table.setItem(r, 0, QTableWidgetItem(name))
        self.subjects_table.setItem(r, 1, QTableWidgetItem(code))
        self.subjects_table.setItem(r, 2, QTableWidgetItem(self.wiz_sub_type.currentText()))
        self.subjects_table.setItem(r, 3, QTableWidgetItem("100 / 33"))
        self.wiz_sub_name.clear()
        self.wiz_sub_code.clear()

    # ------------------------------------------------------------------
    # Step 5: Review & Apply
    # ------------------------------------------------------------------
    def _build_step5_review(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Configuration Preview & Integrity Check:"))
        self.review_text = QTextEdit()
        self.review_text.setReadOnly(True)
        lay.addWidget(self.review_text)
        return w

    def _load_initial_data(self):
        db: Session = SessionLocal()
        try:
            AcademicService.ensure_academic_defaults(db)
            years = AcademicRepository.get_all_academic_years(db)
            self.existing_year_combo.clear()
            self.clone_source_combo.clear()
            for y in years:
                lbl = f"{y.name} ({y.status})"
                self.existing_year_combo.addItem(lbl, y.id)
                self.clone_source_combo.addItem(lbl, y.id)

            for g in AcademicRepository.get_groups(db):
                r = self.groups_table.rowCount()
                self.groups_table.insertRow(r)
                self.groups_table.setItem(r, 0, QTableWidgetItem(g.name))
                self.groups_table.setItem(r, 1, QTableWidgetItem(g.code))
                self.groups_table.setItem(r, 2, QTableWidgetItem("Existing"))

            for sh in AcademicRepository.get_shifts(db):
                r = self.shifts_table.rowCount()
                self.shifts_table.insertRow(r)
                self.shifts_table.setItem(r, 0, QTableWidgetItem(sh.name))
                self.shifts_table.setItem(r, 1, QTableWidgetItem(sh.code))
                self.shifts_table.setItem(r, 2, QTableWidgetItem(sh.start_time or "-"))
                self.shifts_table.setItem(r, 3, QTableWidgetItem(sh.end_time or "-"))
        finally:
            db.close()

        self._load_preset_into_builder(self.preset_combo.currentText())

    def _go_to_step(self, idx: int):
        self.stack.setCurrentIndex(idx)
        self.lbl_step_title.setText(self._step_titles[idx])
        self.lbl_progress.setText(f"Step {idx + 1} of {len(self._step_titles)}")
        self.btn_back.setVisible(idx > 0)
        self.btn_next.setVisible(idx < len(self._step_titles) - 1)
        self.btn_finish.setVisible(idx == len(self._step_titles) - 1)

        if idx == 2:
            if self.rb_clone.isChecked():
                self.lbl_builder_note.setText(
                    "Clone Mode Selected: Structure will be copied non-destructively from "
                    f"'{self.clone_source_combo.currentText()}'. Optionally add extra custom classes below."
                )
            else:
                self.lbl_builder_note.setText(
                    "Customize class levels, numeric order, streams, shifts, and comma-separated sections below."
                )
        elif idx == 4:
            self._populate_review()

    def _on_back(self):
        curr = self.stack.currentIndex()
        if curr > 0:
            self._go_to_step(curr - 1)

    def _on_next(self):
        curr = self.stack.currentIndex()
        if curr == 0:
            if self.rb_new_year.isChecked() and not self.new_year_name.text().strip():
                QMessageBox.warning(self, "Validation Error", "Please enter an Academic Year name.")
                return
            if self.rb_clone.isChecked() and not self.clone_source_combo.currentData():
                QMessageBox.warning(self, "Validation Error", "Please select a source year to clone from.")
                return
        if curr < len(self._step_titles) - 1:
            self._go_to_step(curr + 1)

    def _collect_config(self) -> Dict[str, Any]:
        cfg: Dict[str, Any] = {}
        if self.rb_existing_year.isChecked() and self.existing_year_combo.currentData():
            cfg["academic_year_id"] = self.existing_year_combo.currentData()
            cfg["activate_year"] = self.chk_activate_year.isChecked()
        else:
            qs = self.new_year_start.date()
            qe = self.new_year_end.date()
            cfg["academic_year"] = {
                "name": self.new_year_name.text().strip(),
                "start_date": date(qs.year(), qs.month(), qs.day()),
                "end_date": date(qe.year(), qe.month(), qe.day()),
                "is_current": self.chk_activate_year.isChecked(),
                "status": "Active" if self.chk_activate_year.isChecked() else "Upcoming",
            }

        # Queued new groups/shifts
        new_groups = []
        for r in range(self.groups_table.rowCount()):
            if self.groups_table.item(r, 2) and "Wizard" in self.groups_table.item(r, 2).text():
                new_groups.append({
                    "name": self.groups_table.item(r, 0).text(),
                    "code": self.groups_table.item(r, 1).text(),
                })
        cfg["groups"] = new_groups

        new_shifts = []
        for r in range(self.shifts_table.rowCount()):
            new_shifts.append({
                "name": self.shifts_table.item(r, 0).text(),
                "code": self.shifts_table.item(r, 1).text(),
                "start_time": self.shifts_table.item(r, 2).text(),
                "end_time": self.shifts_table.item(r, 3).text(),
            })
        cfg["shifts"] = new_shifts

        rooms = []
        for r in range(self.rooms_table.rowCount()):
            rooms.append({
                "room_number": self.rooms_table.item(r, 0).text(),
                "room_name": self.rooms_table.item(r, 1).text(),
                "room_type": self.rooms_table.item(r, 2).text(),
                "capacity": int(self.rooms_table.item(r, 3).text() or 50),
            })
        cfg["rooms"] = rooms

        if self.rb_clone.isChecked():
            cfg["clone_from_year_id"] = self.clone_source_combo.currentData()
            cfg["clone_sections"] = self.chk_clone_sections.isChecked()
            cfg["clone_subjects"] = self.chk_clone_subjects.isChecked()
            cfg["clone_teachers"] = self.chk_clone_teachers.isChecked()
            cfg["structure_profile"] = "Cloned"
        else:
            preset_info = AcademicService.get_preset_structure(self.preset_combo.currentText())
            cfg["structure_profile"] = preset_info.get("profile", "Custom")

        starter_subjects: List[Dict[str, Any]] = []
        for r in range(self.subjects_table.rowCount()):
            starter_subjects.append({
                "name": self.subjects_table.item(r, 0).text(),
                "code": self.subjects_table.item(r, 1).text(),
                "subject_type": self.subjects_table.item(r, 2).text(),
                "full_marks": 100,
                "pass_marks": 33,
            })

        classes = []
        if not self.rb_clone.isChecked():
            for r in range(self.builder_table.rowCount()):
                c_name = self.builder_table.item(r, 0).text().strip()
                if not c_name:
                    continue
                sec_raw = self.builder_table.item(r, 5).text()
                cap_val = int(self.builder_table.item(r, 6).text() or 50)
                secs = [
                    {"name": s.strip(), "capacity": cap_val}
                    for s in sec_raw.split(",")
                    if s.strip()
                ]
                classes.append({
                    "name": c_name,
                    "code": self.builder_table.item(r, 1).text().strip() or None,
                    "numeric_order": int(self.builder_table.item(r, 2).text() or (r + 1)),
                    "group": self.builder_table.item(r, 3).text().strip() or "General",
                    "shift": self.builder_table.item(r, 4).text().strip() or "Morning",
                    "sections": secs,
                    "subjects": list(starter_subjects),
                })
        cfg["classes"] = classes
        return cfg

    def _populate_review(self):
        cfg = self._collect_config()
        yr_label = (
            self.existing_year_combo.currentText()
            if cfg.get("academic_year_id")
            else f"{cfg['academic_year']['name']} ({cfg['academic_year']['start_date']} to {cfg['academic_year']['end_date']})"
        )
        lines = [
            f"Target Academic Session: {yr_label}",
            f"Structure Profile: {cfg.get('structure_profile')}",
            f"Queued New Groups: {len(cfg.get('groups', []))}",
            f"Queued Rooms: {len(cfg.get('rooms', []))}",
        ]
        if cfg.get("clone_from_year_id"):
            lines.append(
                f"Clone Source Session: {self.clone_source_combo.currentText()} "
                f"(Sections={cfg['clone_sections']}, Subjects={cfg['clone_subjects']}, Teachers={cfg['clone_teachers']})"
            )
        else:
            lines.append(f"Classes to Provision: {len(cfg.get('classes', []))}")
            for c in cfg.get("classes", []):
                sec_names = ", ".join(s["name"] for s in c["sections"])
                lines.append(
                    f"  - {c['name']} [{c['group']} / {c['shift']}] -> Sections: {sec_names or 'None'} | Subjects: {len(c['subjects'])}"
                )
        lines.append("")
        lines.append("Historical Guarantee: Previous academic year classes, sections, subjects, and student records will NOT be overwritten.")
        self.review_text.setPlainText("\n".join(lines))

    def _on_apply(self):
        cfg = self._collect_config()
        db: Session = SessionLocal()
        try:
            ok, summary, msg = AcademicService.apply_academic_configuration_wizard(
                db, cfg, current_user=self.actor
            )
            if ok:
                QMessageBox.information(self, "Configuration Applied", msg)
                self.accept()
            else:
                QMessageBox.warning(self, "Configuration Error", msg)
        finally:
            db.close()
