"""
EduManage Pro - Comprehensive Academic Management Page (PySide6)
Covers Academic Years, Custom Class Structures, Academic Configuration Wizard,
Sections & Class Teachers, Groups, Shifts, Departments, Rooms, Subjects,
Optional Subject Enrollments, Promotions, Class/Section Transfers,
Chronological Student Academic History, and Academic Calendar.
"""

from datetime import date
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.academic import SchoolClass, Section, Subject
from app.models.staff import Teacher
from app.models.student import Student, StudentStatus
from app.repositories.academic_repository import AcademicRepository
from app.security.session import session as app_session
from app.services.academic_service import AcademicService
from app.ui.dialogs.academic_wizard_dialog import AcademicWizardDialog
from app.ui.dialogs.class_form_dialog import ClassFormDialog
from app.ui.dialogs.section_form_dialog import SectionFormDialog
from app.ui.dialogs.student_promote_dialog import StudentPromoteDialog
from app.ui.dialogs.subject_form_dialog import SubjectFormDialog


class AcademicManagementPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._actor = (
            app_session.current_user.username
            if app_session.is_authenticated and app_session.current_user
            else "admin"
        )
        self._init_ui()
        self.refresh_all()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # 1. Header Banner & Action Toolbar
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("Academic & Curriculum Management")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A;")
        sub_lbl = QLabel(
            "Sessions, Custom Class Structures, Groups, Shifts, Departments, Rooms, Subjects, Movements & Calendar"
        )
        sub_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        header_layout.addWidget(QLabel("Session Scope:"))
        self.global_year_combo = QComboBox()
        self.global_year_combo.setMinimumWidth(160)
        self.global_year_combo.currentIndexChanged.connect(self._on_year_scope_changed)
        header_layout.addWidget(self.global_year_combo)

        btn_wizard = QPushButton("Configuration Wizard")
        btn_wizard.setStyleSheet(
            "background-color: #0F172A; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;"
        )
        btn_wizard.clicked.connect(self._on_open_wizard)
        header_layout.addWidget(btn_wizard)

        btn_class = QPushButton("+ Add Class")
        btn_class.setStyleSheet(
            "background-color: #2563EB; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;"
        )
        btn_class.clicked.connect(self._on_add_class)
        header_layout.addWidget(btn_class)

        btn_section = QPushButton("+ Add Section")
        btn_section.setStyleSheet(
            "background-color: #059669; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;"
        )
        btn_section.clicked.connect(self._on_add_section)
        header_layout.addWidget(btn_section)

        btn_sub = QPushButton("+ Add Subject")
        btn_sub.setStyleSheet(
            "background-color: #7C3AED; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;"
        )
        btn_sub.clicked.connect(self._on_add_subject)
        header_layout.addWidget(btn_sub)

        btn_promote = QPushButton("Batch Promote")
        btn_promote.setStyleSheet(
            "background-color: #D97706; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;"
        )
        btn_promote.clicked.connect(self._on_open_promote_dialog)
        header_layout.addWidget(btn_promote)

        main_layout.addLayout(header_layout)

        # 2. KPI Summary Bar
        kpi_frame = QFrame()
        kpi_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        kpi_layout = QHBoxLayout(kpi_frame)
        kpi_layout.setContentsMargins(16, 10, 16, 10)

        self.kpi_year = QLabel("Active Session: -")
        self.kpi_year.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        self.kpi_classes = QLabel("Classes: 0")
        self.kpi_classes.setStyleSheet("font-size: 13px; color: #2563EB; font-weight: 600;")
        self.kpi_sections = QLabel("Sections: 0")
        self.kpi_sections.setStyleSheet("font-size: 13px; color: #059669; font-weight: 600;")
        self.kpi_subjects = QLabel("Subjects: 0")
        self.kpi_subjects.setStyleSheet("font-size: 13px; color: #7C3AED; font-weight: 600;")
        self.kpi_infra = QLabel("Groups: 0 | Shifts: 0 | Rooms: 0 | Depts: 0")
        self.kpi_infra.setStyleSheet("font-size: 12px; color: #475569; font-weight: 600;")

        for lbl in (self.kpi_year, self.kpi_classes, self.kpi_sections, self.kpi_subjects, self.kpi_infra):
            kpi_layout.addWidget(lbl)
            kpi_layout.addSpacing(18)
        kpi_layout.addStretch()
        main_layout.addWidget(kpi_frame)

        # 3. 6 Feature Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { font-weight: 600; padding: 8px 14px; margin-right: 3px; }
            QTabBar::tab:selected { background: #2563EB; color: white; border-radius: 4px; }
        """)

        self.tabs.addTab(self._build_classes_sections_tab(), "Classes, Sections & Teachers")
        self.tabs.addTab(self._build_academic_years_tab(), "Academic Years & Cloning")
        self.tabs.addTab(self._build_groups_shifts_rooms_tab(), "Groups, Shifts, Depts & Rooms")
        self.tabs.addTab(self._build_subjects_tab(), "Subjects & Optional Enrollment")
        self.tabs.addTab(self._build_movements_history_tab(), "Promotions, Transfers & History")
        self.tabs.addTab(self._build_calendar_tab(), "Academic Calendar")

        main_layout.addWidget(self.tabs, stretch=1)

    # ------------------------------------------------------------------
    # Tab 1: Classes, Sections & Class Teachers
    # ------------------------------------------------------------------
    def _build_classes_sections_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        filter_h = QHBoxLayout()
        filter_h.addWidget(QLabel("Search Classes:"))
        self.class_search_edit = QLineEdit()
        self.class_search_edit.setPlaceholderText("Search by name, code, group, or structure profile...")
        self.class_search_edit.textChanged.connect(self._load_classes_table)
        filter_h.addWidget(self.class_search_edit, stretch=1)

        btn_edit_cls = QPushButton("Edit Selected Class")
        btn_edit_cls.clicked.connect(self._on_edit_selected_class)
        btn_del_cls = QPushButton("Delete Selected Class")
        btn_del_cls.clicked.connect(self._on_delete_selected_class)
        filter_h.addWidget(btn_edit_cls)
        filter_h.addWidget(btn_del_cls)
        lay.addLayout(filter_h)

        splitter = QSplitter(Qt.Vertical)

        self.classes_table = QTableWidget(0, 8)
        self.classes_table.setHorizontalHeaderLabels([
            "Order", "Class Name", "Code", "Session", "Group / Stream", "Shift", "Profile", "Sections / Subjects"
        ])
        self.classes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.classes_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.classes_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.classes_table.itemSelectionChanged.connect(self._load_sections_table)
        splitter.addWidget(self.classes_table)

        sec_box = QGroupBox("Sections, Rooms & Class Teacher Assignments (Filtered by selected class when clicked)")
        sec_lay = QVBoxLayout(sec_box)
        sec_btns = QHBoxLayout()
        btn_edit_sec = QPushButton("Edit Selected Section")
        btn_edit_sec.clicked.connect(self._on_edit_selected_section)
        btn_del_sec = QPushButton("Delete Selected Section")
        btn_del_sec.clicked.connect(self._on_delete_selected_section)
        btn_all_sec = QPushButton("Show All Sections")
        btn_all_sec.clicked.connect(self._clear_class_selection)
        sec_btns.addWidget(btn_edit_sec)
        sec_btns.addWidget(btn_del_sec)
        sec_btns.addWidget(btn_all_sec)
        sec_btns.addStretch()
        sec_lay.addLayout(sec_btns)

        self.sections_table = QTableWidget(0, 7)
        self.sections_table.setHorizontalHeaderLabels([
            "Class", "Section Name", "Room", "Capacity", "Shift", "Group", "Class Teacher"
        ])
        self.sections_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sections_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sections_table.setEditTriggers(QTableWidget.NoEditTriggers)
        sec_lay.addWidget(self.sections_table)
        splitter.addWidget(sec_box)

        lay.addWidget(splitter, stretch=1)
        return w

    # ------------------------------------------------------------------
    # Tab 2: Academic Years & Non-Destructive Structure Cloning
    # ------------------------------------------------------------------
    def _build_academic_years_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        create_box = QGroupBox("Create New Academic Session")
        c_row = QHBoxLayout(create_box)
        self.ay_name_edit = QLineEdit()
        self.ay_name_edit.setPlaceholderText("e.g. 2026-2027")
        self.ay_start_edit = QDateEdit(QDate(date.today().year, 1, 1))
        self.ay_start_edit.setCalendarPopup(True)
        self.ay_end_edit = QDateEdit(QDate(date.today().year, 12, 31))
        self.ay_end_edit.setCalendarPopup(True)
        self.ay_curr_chk = QCheckBox("Set Active Immediately")
        btn_add_ay = QPushButton("+ Create Academic Year")
        btn_add_ay.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        btn_add_ay.clicked.connect(self._on_create_academic_year)

        c_row.addWidget(QLabel("Name:"))
        c_row.addWidget(self.ay_name_edit)
        c_row.addWidget(QLabel("Start:"))
        c_row.addWidget(self.ay_start_edit)
        c_row.addWidget(QLabel("End:"))
        c_row.addWidget(self.ay_end_edit)
        c_row.addWidget(self.ay_curr_chk)
        c_row.addWidget(btn_add_ay)
        lay.addWidget(create_box)

        self.years_table = QTableWidget(0, 6)
        self.years_table.setHorizontalHeaderLabels([
            "Session Name", "Start Date", "End Date", "Status", "Current Active", "Classes Defined"
        ])
        self.years_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.years_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.years_table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.years_table, stretch=1)

        act_row = QHBoxLayout()
        btn_activate = QPushButton("Activate Selected Year")
        btn_activate.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        btn_activate.clicked.connect(self._on_activate_selected_year)
        btn_close_yr = QPushButton("Mark Selected Completed")
        btn_close_yr.clicked.connect(self._on_close_selected_year)
        act_row.addWidget(btn_activate)
        act_row.addWidget(btn_close_yr)
        act_row.addStretch()
        lay.addLayout(act_row)

        clone_box = QGroupBox("Non-Destructive Structure Rollover (Clone Classes, Sections & Subjects to New Year)")
        cl_row = QHBoxLayout(clone_box)
        self.clone_src_combo = QComboBox()
        self.clone_tgt_combo = QComboBox()
        self.clone_teachers_chk = QCheckBox("Copy Teachers")
        self.clone_teachers_chk.setChecked(True)
        btn_clone = QPushButton("Clone Academic Structure")
        btn_clone.setStyleSheet("background-color: #7C3AED; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        btn_clone.clicked.connect(self._on_clone_year_structure)
        cl_row.addWidget(QLabel("From Source Year:"))
        cl_row.addWidget(self.clone_src_combo, stretch=1)
        cl_row.addWidget(QLabel("Into Target Year:"))
        cl_row.addWidget(self.clone_tgt_combo, stretch=1)
        cl_row.addWidget(self.clone_teachers_chk)
        cl_row.addWidget(btn_clone)
        lay.addWidget(clone_box)

        return w

    # ------------------------------------------------------------------
    # Tab 3: Groups, Shifts, Departments & Rooms
    # ------------------------------------------------------------------
    def _build_groups_shifts_rooms_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        top_split = QSplitter(Qt.Horizontal)

        # Groups panel
        g_box = QGroupBox("Academic Groups / Streams")
        g_lay = QVBoxLayout(g_box)
        g_form = QHBoxLayout()
        self.grp_name_in = QLineEdit()
        self.grp_name_in.setPlaceholderText("Group Name (e.g. Science)")
        self.grp_code_in = QLineEdit()
        self.grp_code_in.setPlaceholderText("Code")
        self.grp_code_in.setFixedWidth(75)
        btn_g = QPushButton("+ Add")
        btn_g.clicked.connect(self._on_add_group)
        g_form.addWidget(self.grp_name_in)
        g_form.addWidget(self.grp_code_in)
        g_form.addWidget(btn_g)
        g_lay.addLayout(g_form)
        self.grp_table = QTableWidget(0, 3)
        self.grp_table.setHorizontalHeaderLabels(["Name", "Code", "Description"])
        self.grp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        g_lay.addWidget(self.grp_table)
        top_split.addWidget(g_box)

        # Shifts panel
        s_box = QGroupBox("Campus Shifts")
        s_lay = QVBoxLayout(s_box)
        s_form = QHBoxLayout()
        self.sh_name_in = QLineEdit()
        self.sh_name_in.setPlaceholderText("Shift Name")
        self.sh_code_in = QLineEdit()
        self.sh_code_in.setPlaceholderText("Code")
        self.sh_code_in.setFixedWidth(65)
        self.sh_start_in = QLineEdit()
        self.sh_start_in.setPlaceholderText("07:30 AM")
        self.sh_end_in = QLineEdit()
        self.sh_end_in.setPlaceholderText("12:30 PM")
        btn_s = QPushButton("+ Add")
        btn_s.clicked.connect(self._on_add_shift)
        s_form.addWidget(self.sh_name_in)
        s_form.addWidget(self.sh_code_in)
        s_form.addWidget(self.sh_start_in)
        s_form.addWidget(self.sh_end_in)
        s_form.addWidget(btn_s)
        s_lay.addLayout(s_form)
        self.sh_table = QTableWidget(0, 4)
        self.sh_table.setHorizontalHeaderLabels(["Name", "Code", "Start", "End"])
        self.sh_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        s_lay.addWidget(self.sh_table)
        top_split.addWidget(s_box)

        lay.addWidget(top_split, stretch=1)

        bot_split = QSplitter(Qt.Horizontal)

        # Departments panel
        d_box = QGroupBox("Academic Departments")
        d_lay = QVBoxLayout(d_box)
        d_form = QHBoxLayout()
        self.dept_name_in = QLineEdit()
        self.dept_name_in.setPlaceholderText("Department Name")
        self.dept_code_in = QLineEdit()
        self.dept_code_in.setPlaceholderText("Code")
        self.dept_code_in.setFixedWidth(75)
        btn_d = QPushButton("+ Add")
        btn_d.clicked.connect(self._on_add_department)
        d_form.addWidget(self.dept_name_in)
        d_form.addWidget(self.dept_code_in)
        d_form.addWidget(btn_d)
        d_lay.addLayout(d_form)
        self.dept_table = QTableWidget(0, 3)
        self.dept_table.setHorizontalHeaderLabels(["Name", "Code", "Description"])
        self.dept_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        d_lay.addWidget(self.dept_table)
        bot_split.addWidget(d_box)

        # Rooms panel
        r_box = QGroupBox("Rooms & Laboratories")
        r_lay = QVBoxLayout(r_box)
        r_form = QHBoxLayout()
        self.rm_no_in = QLineEdit()
        self.rm_no_in.setPlaceholderText("Room No (e.g. R-204)")
        self.rm_bldg_in = QLineEdit("Main Building")
        self.rm_type_in = QComboBox()
        self.rm_type_in.addItems(["Classroom", "Science Lab", "Computer Lab", "Auditorium", "Library"])
        self.rm_cap_in = QSpinBox()
        self.rm_cap_in.setRange(5, 500)
        self.rm_cap_in.setValue(50)
        btn_r = QPushButton("+ Add")
        btn_r.clicked.connect(self._on_add_room)
        r_form.addWidget(self.rm_no_in)
        r_form.addWidget(self.rm_bldg_in)
        r_form.addWidget(self.rm_type_in)
        r_form.addWidget(self.rm_cap_in)
        r_form.addWidget(btn_r)
        r_lay.addLayout(r_form)
        self.rm_table = QTableWidget(0, 5)
        self.rm_table.setHorizontalHeaderLabels(["Room No", "Building", "Floor", "Type", "Capacity"])
        self.rm_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        r_lay.addWidget(self.rm_table)
        bot_split.addWidget(r_box)

        lay.addWidget(bot_split, stretch=1)
        return w

    # ------------------------------------------------------------------
    # Tab 4: Subjects, Optional Subjects & Subject Teachers
    # ------------------------------------------------------------------
    def _build_subjects_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        s_filter_h = QHBoxLayout()
        s_filter_h.addWidget(QLabel("Class:"))
        self.sub_class_combo = QComboBox()
        self.sub_class_combo.addItem("All Classes", None)
        self.sub_class_combo.currentIndexChanged.connect(self._load_subjects_table)
        s_filter_h.addWidget(self.sub_class_combo)

        s_filter_h.addWidget(QLabel("Type:"))
        self.sub_type_filter = QComboBox()
        self.sub_type_filter.addItems(["All", "Mandatory", "Optional", "Elective"])
        self.sub_type_filter.currentIndexChanged.connect(self._load_subjects_table)
        s_filter_h.addWidget(self.sub_type_filter)

        s_filter_h.addWidget(QLabel("Search:"))
        self.sub_search_edit = QLineEdit()
        self.sub_search_edit.setPlaceholderText("Subject name or code...")
        self.sub_search_edit.textChanged.connect(self._load_subjects_table)
        s_filter_h.addWidget(self.sub_search_edit, stretch=1)

        btn_edit_sub = QPushButton("Edit Selected")
        btn_edit_sub.clicked.connect(self._on_edit_selected_subject)
        btn_del_sub = QPushButton("Delete Selected")
        btn_del_sub.clicked.connect(self._on_delete_selected_subject)
        s_filter_h.addWidget(btn_edit_sub)
        s_filter_h.addWidget(btn_del_sub)
        lay.addLayout(s_filter_h)

        self.subjects_table = QTableWidget(0, 9)
        self.subjects_table.setHorizontalHeaderLabels([
            "Subject ID", "Name", "Code", "Class", "Dept", "Type", "Credits", "Full / Pass", "Subject Teacher"
        ])
        self.subjects_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.subjects_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.subjects_table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.subjects_table, stretch=2)

        # Optional Subject Enrollment Widget
        opt_box = QGroupBox("Student Optional / Elective Subject Enrollment")
        opt_lay = QVBoxLayout(opt_box)
        opt_ctrl = QHBoxLayout()
        self.opt_stu_combo = QComboBox()
        self.opt_stu_combo.currentIndexChanged.connect(self._load_student_subject_enrollments)
        self.opt_sub_combo = QComboBox()
        btn_enroll_opt = QPushButton("Enroll Subject")
        btn_enroll_opt.setStyleSheet("background-color: #7C3AED; color: white; font-weight: bold; padding: 5px 12px; border-radius: 4px;")
        btn_enroll_opt.clicked.connect(self._on_enroll_optional_subject)
        btn_drop_opt = QPushButton("Drop Selected")
        btn_drop_opt.clicked.connect(self._on_drop_optional_subject)

        opt_ctrl.addWidget(QLabel("Student:"))
        opt_ctrl.addWidget(self.opt_stu_combo, stretch=1)
        opt_ctrl.addWidget(QLabel("Subject:"))
        opt_ctrl.addWidget(self.opt_sub_combo, stretch=1)
        opt_ctrl.addWidget(btn_enroll_opt)
        opt_ctrl.addWidget(btn_drop_opt)
        opt_lay.addLayout(opt_ctrl)

        self.opt_table = QTableWidget(0, 5)
        self.opt_table.setHorizontalHeaderLabels(["Academic Year", "Class", "Subject", "Optional?", "Status"])
        self.opt_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.opt_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.opt_table.setEditTriggers(QTableWidget.NoEditTriggers)
        opt_lay.addWidget(self.opt_table)
        lay.addWidget(opt_box, stretch=1)

        return w

    # ------------------------------------------------------------------
    # Tab 5: Promotions, Class/Section Transfers & Academic History
    # ------------------------------------------------------------------
    def _build_movements_history_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        # Movement controls
        mv_box = QGroupBox("Student Class Transfer, Section Transfer & Single Promotion (Preserves History)")
        mv_lay = QVBoxLayout(mv_box)

        r1 = QHBoxLayout()
        self.mv_student_combo = QComboBox()
        self.mv_student_combo.currentIndexChanged.connect(self._on_movement_student_changed)
        self.mv_op_combo = QComboBox()
        self.mv_op_combo.addItems(["Section Transfer", "Class Transfer", "Single Promotion"])
        self.mv_op_combo.currentTextChanged.connect(self._on_movement_op_changed)
        r1.addWidget(QLabel("Student:"))
        r1.addWidget(self.mv_student_combo, stretch=2)
        r1.addWidget(QLabel("Operation:"))
        r1.addWidget(self.mv_op_combo, stretch=1)
        mv_lay.addLayout(r1)

        r2 = QHBoxLayout()
        self.mv_ay_combo = QComboBox()
        self.mv_ay_combo.currentIndexChanged.connect(self._reload_mv_classes)
        self.mv_class_combo = QComboBox()
        self.mv_class_combo.currentIndexChanged.connect(self._reload_mv_sections)
        self.mv_section_combo = QComboBox()
        self.mv_roll_spin = QSpinBox()
        self.mv_roll_spin.setRange(0, 9999)
        self.mv_roll_spin.setSpecialValueText("Auto")
        self.mv_reason_edit = QLineEdit("Academic reallocation")
        btn_exec_mv = QPushButton("Execute Movement")
        btn_exec_mv.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        btn_exec_mv.clicked.connect(self._on_execute_movement)

        r2.addWidget(QLabel("Session:"))
        r2.addWidget(self.mv_ay_combo)
        r2.addWidget(QLabel("Target Class:"))
        r2.addWidget(self.mv_class_combo)
        r2.addWidget(QLabel("Target Section:"))
        r2.addWidget(self.mv_section_combo)
        r2.addWidget(QLabel("Roll:"))
        r2.addWidget(self.mv_roll_spin)
        r2.addWidget(QLabel("Reason:"))
        r2.addWidget(self.mv_reason_edit, stretch=1)
        r2.addWidget(btn_exec_mv)
        mv_lay.addLayout(r2)
        lay.addWidget(mv_box)

        # Student Academic History Viewer
        hist_box = QGroupBox("Student Chronological Academic History, Promotions & Transfers")
        h_lay = QVBoxLayout(hist_box)
        self.hist_acad_table = QTableWidget(0, 7)
        self.hist_acad_table.setHorizontalHeaderLabels([
            "Session", "Class", "Section", "Roll", "Status", "GPA / Grade", "Period / Remarks"
        ])
        self.hist_acad_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.hist_acad_table.setEditTriggers(QTableWidget.NoEditTriggers)
        h_lay.addWidget(self.hist_acad_table, stretch=2)

        self.hist_moves_table = QTableWidget(0, 5)
        self.hist_moves_table.setHorizontalHeaderLabels([
            "Date", "Movement Type", "From", "To", "Reason / By"
        ])
        self.hist_moves_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.hist_moves_table.setEditTriggers(QTableWidget.NoEditTriggers)
        h_lay.addWidget(self.hist_moves_table, stretch=1)

        lay.addWidget(hist_box, stretch=1)
        return w

    # ------------------------------------------------------------------
    # Tab 6: Academic Calendar
    # ------------------------------------------------------------------
    def _build_calendar_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        ev_box = QGroupBox("Add Event / Exam Period / Official Holiday to Academic Calendar")
        ev_row = QHBoxLayout(ev_box)
        self.cal_title_in = QLineEdit()
        self.cal_title_in.setPlaceholderText("Event Title (e.g. First Term Final Exam, Winter Break)")
        self.cal_cat_in = QComboBox()
        self.cal_cat_in.addItems(["Academic", "Exam", "Holiday", "Sports", "Cultural", "PTM"])
        self.cal_start_in = QDateEdit(QDate.currentDate())
        self.cal_start_in.setCalendarPopup(True)
        self.cal_end_in = QDateEdit(QDate.currentDate())
        self.cal_end_in.setCalendarPopup(True)
        self.cal_term_in = QLineEdit()
        self.cal_term_in.setPlaceholderText("Term (e.g. Term 1)")
        self.cal_hol_chk = QCheckBox("Holiday")
        btn_add_ev = QPushButton("+ Add Calendar Event")
        btn_add_ev.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        btn_add_ev.clicked.connect(self._on_add_calendar_event)
        btn_pdf = QPushButton("Export Calendar PDF")
        btn_pdf.clicked.connect(self._on_export_calendar_pdf)

        ev_row.addWidget(self.cal_title_in, stretch=2)
        ev_row.addWidget(self.cal_cat_in)
        ev_row.addWidget(self.cal_start_in)
        ev_row.addWidget(self.cal_end_in)
        ev_row.addWidget(self.cal_term_in)
        ev_row.addWidget(self.cal_hol_chk)
        ev_row.addWidget(btn_add_ev)
        ev_row.addWidget(btn_pdf)
        lay.addWidget(ev_box)

        self.cal_table = QTableWidget(0, 7)
        self.cal_table.setHorizontalHeaderLabels([
            "Title", "Category", "Start Date", "End Date", "Term", "Venue", "Holiday?"
        ])
        self.cal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cal_table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.cal_table, stretch=1)
        return w

    # ------------------------------------------------------------------
    # Refresh & Loaders
    # ------------------------------------------------------------------
    def _selected_year_id(self):
        return self.global_year_combo.currentData()

    def _on_year_scope_changed(self):
        self._load_kpi_and_combos()
        self._load_classes_table()
        self._load_sections_table()
        self._load_subjects_table()
        self._load_calendar_table()

    def refresh_all(self):
        db: Session = SessionLocal()
        try:
            AcademicService.ensure_academic_defaults(db)
            years = AcademicRepository.get_all_academic_years(db)
            prev_year_id = self.global_year_combo.currentData()
            self.global_year_combo.blockSignals(True)
            self.global_year_combo.clear()
            self.global_year_combo.addItem("All Academic Years", None)
            default_idx = 0
            for idx, y in enumerate(years, start=1):
                lbl = f"{y.name} ({'Current' if y.is_current else y.status})"
                self.global_year_combo.addItem(lbl, y.id)
                if prev_year_id == y.id:
                    default_idx = idx
                elif prev_year_id is None and y.is_current:
                    default_idx = idx
            self.global_year_combo.setCurrentIndex(default_idx)
            self.global_year_combo.blockSignals(False)
        finally:
            db.close()

        self._load_kpi_and_combos()
        self._load_classes_table()
        self._load_sections_table()
        self._load_years_tab()
        self._load_infra_tables()
        self._load_subjects_table()
        self._load_students_combos()
        self._load_calendar_table()

    def _load_kpi_and_combos(self):
        ay_id = self._selected_year_id()
        db: Session = SessionLocal()
        try:
            summary = AcademicService.get_academic_summary(db, academic_year_id=ay_id)
            self.kpi_year.setText(f"Active Session: {summary['current_year']}")
            self.kpi_classes.setText(f"Classes: {summary['total_classes']}")
            self.kpi_sections.setText(f"Sections: {summary['total_sections']}")
            self.kpi_subjects.setText(f"Subjects: {summary['total_subjects']}")
            self.kpi_infra.setText(
                f"Groups: {summary['total_groups']} | Shifts: {summary['total_shifts']} | "
                f"Rooms: {summary['total_rooms']} | Depts: {summary['total_departments']} | Events: {summary['total_events']}"
            )

            classes = AcademicRepository.get_classes(db, academic_year_id=ay_id)
            cur_sub_cls = self.sub_class_combo.currentData()
            self.sub_class_combo.blockSignals(True)
            self.sub_class_combo.clear()
            self.sub_class_combo.addItem("All Classes", None)
            for c in classes:
                self.sub_class_combo.addItem(f"{c.name} ({c.group})", c.id)
            idx_c = self.sub_class_combo.findData(cur_sub_cls)
            if idx_c >= 0:
                self.sub_class_combo.setCurrentIndex(idx_c)
            self.sub_class_combo.blockSignals(False)
        finally:
            db.close()

    def _clear_class_selection(self):
        self.classes_table.clearSelection()
        self._load_sections_table()

    def _load_classes_table(self):
        ay_id = self._selected_year_id()
        q = self.class_search_edit.text().strip()
        db: Session = SessionLocal()
        try:
            classes = AcademicRepository.get_classes(db, academic_year_id=ay_id, search=q or None)
            self.classes_table.setRowCount(len(classes))
            for r, c in enumerate(classes):
                ord_item = QTableWidgetItem(str(c.numeric_order))
                ord_item.setData(Qt.UserRole, c.id)
                self.classes_table.setItem(r, 0, ord_item)
                self.classes_table.setItem(r, 1, QTableWidgetItem(c.name))
                self.classes_table.setItem(r, 2, QTableWidgetItem(c.code or "-"))
                self.classes_table.setItem(r, 3, QTableWidgetItem(c.academic_year.name if c.academic_year else "-"))
                self.classes_table.setItem(r, 4, QTableWidgetItem(c.group))
                self.classes_table.setItem(r, 5, QTableWidgetItem(c.shift))
                self.classes_table.setItem(r, 6, QTableWidgetItem(c.structure_profile or "Standard"))
                sec_names = ", ".join(s.name for s in c.sections) if c.sections else "None"
                self.classes_table.setItem(r, 7, QTableWidgetItem(f"{len(c.sections)} ({sec_names}) | {len(c.subjects)} subj"))
        finally:
            db.close()

    def _selected_class_id(self):
        row = self.classes_table.currentRow()
        if row < 0:
            return None
        item = self.classes_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _load_sections_table(self):
        cls_id = self._selected_class_id()
        ay_id = self._selected_year_id()
        db: Session = SessionLocal()
        try:
            secs = AcademicRepository.get_sections(
                db,
                class_id=cls_id,
                academic_year_id=None if cls_id else ay_id,
            )
            self.sections_table.setRowCount(len(secs))
            for r, s in enumerate(secs):
                cls_lbl = s.school_class.name if s.school_class else "-"
                it = QTableWidgetItem(cls_lbl)
                it.setData(Qt.UserRole, s.id)
                self.sections_table.setItem(r, 0, it)
                self.sections_table.setItem(r, 1, QTableWidgetItem(s.name))
                room_lbl = s.room.room_number if s.room else (s.room_number or "-")
                self.sections_table.setItem(r, 2, QTableWidgetItem(room_lbl))
                self.sections_table.setItem(r, 3, QTableWidgetItem(str(s.capacity)))
                self.sections_table.setItem(r, 4, QTableWidgetItem(s.shift))
                self.sections_table.setItem(r, 5, QTableWidgetItem(s.group))
                t_lbl = s.class_teacher.full_name if s.class_teacher else "Unassigned"
                self.sections_table.setItem(r, 6, QTableWidgetItem(t_lbl))
        finally:
            db.close()

    def _load_years_tab(self):
        db: Session = SessionLocal()
        try:
            years = AcademicRepository.get_all_academic_years(db)
            self.years_table.setRowCount(len(years))
            self.clone_src_combo.clear()
            self.clone_tgt_combo.clear()
            self.mv_ay_combo.blockSignals(True)
            self.mv_ay_combo.clear()

            for r, y in enumerate(years):
                it = QTableWidgetItem(y.name)
                it.setData(Qt.UserRole, y.id)
                self.years_table.setItem(r, 0, it)
                self.years_table.setItem(r, 1, QTableWidgetItem(str(y.start_date)))
                self.years_table.setItem(r, 2, QTableWidgetItem(str(y.end_date)))
                self.years_table.setItem(r, 3, QTableWidgetItem(y.status))
                self.years_table.setItem(r, 4, QTableWidgetItem("YES" if y.is_current else "No"))
                cls_cnt = db.query(SchoolClass).filter(
                    SchoolClass.academic_year_id == y.id, SchoolClass.is_deleted == False
                ).count()
                self.years_table.setItem(r, 5, QTableWidgetItem(str(cls_cnt)))

                self.clone_src_combo.addItem(f"{y.name} ({cls_cnt} classes)", y.id)
                self.clone_tgt_combo.addItem(f"{y.name} ({y.status})", y.id)
                self.mv_ay_combo.addItem(f"{y.name} ({y.status})", y.id)
            self.mv_ay_combo.blockSignals(False)
        finally:
            db.close()
        self._reload_mv_classes()

    def _load_infra_tables(self):
        db: Session = SessionLocal()
        try:
            groups = AcademicRepository.get_groups(db)
            self.grp_table.setRowCount(len(groups))
            for r, g in enumerate(groups):
                self.grp_table.setItem(r, 0, QTableWidgetItem(g.name))
                self.grp_table.setItem(r, 1, QTableWidgetItem(g.code))
                self.grp_table.setItem(r, 2, QTableWidgetItem(g.description or "-"))

            shifts = AcademicRepository.get_shifts(db)
            self.sh_table.setRowCount(len(shifts))
            for r, sh in enumerate(shifts):
                self.sh_table.setItem(r, 0, QTableWidgetItem(sh.name))
                self.sh_table.setItem(r, 1, QTableWidgetItem(sh.code))
                self.sh_table.setItem(r, 2, QTableWidgetItem(sh.start_time or "-"))
                self.sh_table.setItem(r, 3, QTableWidgetItem(sh.end_time or "-"))

            depts = AcademicRepository.get_departments(db)
            self.dept_table.setRowCount(len(depts))
            for r, d in enumerate(depts):
                self.dept_table.setItem(r, 0, QTableWidgetItem(d.name))
                self.dept_table.setItem(r, 1, QTableWidgetItem(d.code))
                self.dept_table.setItem(r, 2, QTableWidgetItem(d.description or "-"))

            rooms = AcademicRepository.get_rooms(db)
            self.rm_table.setRowCount(len(rooms))
            for r, rm in enumerate(rooms):
                self.rm_table.setItem(r, 0, QTableWidgetItem(rm.room_number))
                self.rm_table.setItem(r, 1, QTableWidgetItem(rm.building))
                self.rm_table.setItem(r, 2, QTableWidgetItem(rm.floor))
                self.rm_table.setItem(r, 3, QTableWidgetItem(rm.room_type))
                self.rm_table.setItem(r, 4, QTableWidgetItem(str(rm.capacity)))
        finally:
            db.close()

    def _load_subjects_table(self):
        class_id = self.sub_class_combo.currentData()
        sub_type = self.sub_type_filter.currentText()
        search_text = self.sub_search_edit.text().strip()
        ay_id = self._selected_year_id()
        db: Session = SessionLocal()
        try:
            subjects = AcademicRepository.get_subjects(
                db,
                class_id=class_id,
                search=search_text or None,
                academic_year_id=None if class_id else ay_id,
                subject_type=sub_type,
            )
            self.subjects_table.setRowCount(len(subjects))
            self.opt_sub_combo.clear()
            for r, s in enumerate(subjects):
                it = QTableWidgetItem(s.subject_id)
                it.setData(Qt.UserRole, s.id)
                self.subjects_table.setItem(r, 0, it)
                self.subjects_table.setItem(r, 1, QTableWidgetItem(s.name))
                self.subjects_table.setItem(r, 2, QTableWidgetItem(s.code))
                self.subjects_table.setItem(r, 3, QTableWidgetItem(s.school_class.name if s.school_class else "-"))
                self.subjects_table.setItem(r, 4, QTableWidgetItem(s.department.name if s.department else "-"))
                self.subjects_table.setItem(r, 5, QTableWidgetItem(s.subject_type))
                self.subjects_table.setItem(r, 6, QTableWidgetItem(f"{float(s.credit_hours or 1.0):.1f}"))
                self.subjects_table.setItem(r, 7, QTableWidgetItem(f"{s.full_marks} / {s.pass_marks}"))
                t_lbl = s.assigned_teacher.full_name if s.assigned_teacher else "Unassigned"
                self.subjects_table.setItem(r, 8, QTableWidgetItem(t_lbl))

                cls_name = s.school_class.name if s.school_class else ""
                self.opt_sub_combo.addItem(f"{s.name} ({s.subject_type} — {cls_name})", s.id)
        finally:
            db.close()

    def _load_students_combos(self):
        db: Session = SessionLocal()
        try:
            students = (
                db.query(Student)
                .filter(Student.is_deleted == False)
                .order_by(Student.full_name.asc())
                .all()
            )
            self.opt_stu_combo.blockSignals(True)
            self.mv_student_combo.blockSignals(True)
            self.opt_stu_combo.clear()
            self.mv_student_combo.clear()
            for stu in students:
                lbl = f"{stu.full_name} ({stu.student_id}) — {stu.status}"
                self.opt_stu_combo.addItem(lbl, stu.id)
                self.mv_student_combo.addItem(lbl, stu.id)
            self.opt_stu_combo.blockSignals(False)
            self.mv_student_combo.blockSignals(False)
        finally:
            db.close()
        self._load_student_subject_enrollments()
        self._on_movement_student_changed()

    def _load_student_subject_enrollments(self):
        stu_id = self.opt_stu_combo.currentData()
        if not stu_id:
            self.opt_table.setRowCount(0)
            return
        db: Session = SessionLocal()
        try:
            rows = AcademicRepository.list_student_subject_enrollments(db, student_id=stu_id)
            self.opt_table.setRowCount(len(rows))
            for r, enr in enumerate(rows):
                it = QTableWidgetItem(enr.academic_year.name if enr.academic_year else "-")
                it.setData(Qt.UserRole, enr.id)
                self.opt_table.setItem(r, 0, it)
                self.opt_table.setItem(r, 1, QTableWidgetItem(enr.school_class.name if enr.school_class else "-"))
                self.opt_table.setItem(r, 2, QTableWidgetItem(enr.subject.name if enr.subject else "-"))
                self.opt_table.setItem(r, 3, QTableWidgetItem("Optional" if enr.is_optional else "Mandatory"))
                self.opt_table.setItem(r, 4, QTableWidgetItem(enr.enrollment_status))
        finally:
            db.close()

    def _on_movement_op_changed(self, op_text: str):
        is_promo = op_text == "Single Promotion"
        is_sec_only = op_text == "Section Transfer"
        self.mv_ay_combo.setEnabled(is_promo)
        self.mv_class_combo.setEnabled(not is_sec_only)
        self._reload_mv_classes()

    def _on_movement_student_changed(self):
        stu_id = self.mv_student_combo.currentData()
        if not stu_id:
            self.hist_acad_table.setRowCount(0)
            self.hist_moves_table.setRowCount(0)
            return
        db: Session = SessionLocal()
        try:
            data = AcademicService.get_student_academic_history(db, stu_id)
            stu = data["student"]
            if stu:
                idx_ay = self.mv_ay_combo.findData(stu.academic_year_id)
                if idx_ay >= 0 and self.mv_op_combo.currentText() != "Single Promotion":
                    self.mv_ay_combo.setCurrentIndex(idx_ay)
                    self._reload_mv_classes()
                    idx_cls = self.mv_class_combo.findData(stu.class_id)
                    if idx_cls >= 0:
                        self.mv_class_combo.setCurrentIndex(idx_cls)

            acad = data["academic_history"]
            self.hist_acad_table.setRowCount(len(acad))
            for r, h in enumerate(acad):
                self.hist_acad_table.setItem(r, 0, QTableWidgetItem(h.academic_year.name if h.academic_year else "-"))
                self.hist_acad_table.setItem(r, 1, QTableWidgetItem(h.school_class.name if h.school_class else "-"))
                self.hist_acad_table.setItem(r, 2, QTableWidgetItem(h.section.name if h.section else "-"))
                self.hist_acad_table.setItem(r, 3, QTableWidgetItem(str(h.roll_number or "-")))
                self.hist_acad_table.setItem(r, 4, QTableWidgetItem(h.result_status))
                gpa_lbl = f"{h.gpa:.2f}" if h.gpa is not None else "-"
                if h.final_grade:
                    gpa_lbl = f"{gpa_lbl} ({h.final_grade})"
                self.hist_acad_table.setItem(r, 5, QTableWidgetItem(gpa_lbl))
                period = f"{h.start_date or '-'} -> {h.end_date or 'Present'} | {h.remarks or ''}"
                self.hist_acad_table.setItem(r, 6, QTableWidgetItem(period))

            moves = []
            for p in data["promotions"]:
                moves.append((
                    str(p.promoted_date),
                    p.promotion_type or "Promoted",
                    f"{p.from_class.name if p.from_class else '-'} ({p.from_academic_year.name if p.from_academic_year else '-'})",
                    f"{p.to_class.name if p.to_class else '-'} ({p.to_academic_year.name if p.to_academic_year else '-'})",
                    f"{p.remarks or ''} [{p.promoted_by}]",
                ))
            for x in data["transfers"]:
                moves.append((
                    str(x.effective_date),
                    x.transfer_type.replace("_", " ").title(),
                    f"{x.from_class.name if x.from_class else '-'} / {x.from_section.name if x.from_section else '-'} (Roll {x.from_roll_number})",
                    f"{x.to_class.name if x.to_class else '-'} / {x.to_section.name if x.to_section else '-'} (Roll {x.to_roll_number})",
                    f"{x.reason or ''} [{x.transferred_by}]",
                ))
            self.hist_moves_table.setRowCount(len(moves))
            for r, m in enumerate(moves):
                for col, val in enumerate(m):
                    self.hist_moves_table.setItem(r, col, QTableWidgetItem(val))
        finally:
            db.close()

    def _reload_mv_classes(self):
        ay_id = self.mv_ay_combo.currentData()
        db: Session = SessionLocal()
        try:
            self.mv_class_combo.blockSignals(True)
            self.mv_class_combo.clear()
            for c in AcademicRepository.get_classes(db, academic_year_id=ay_id):
                self.mv_class_combo.addItem(f"{c.name} ({c.group})", c.id)
            self.mv_class_combo.blockSignals(False)
        finally:
            db.close()
        self._reload_mv_sections()

    def _reload_mv_sections(self):
        cls_id = self.mv_class_combo.currentData()
        db: Session = SessionLocal()
        try:
            self.mv_section_combo.clear()
            if cls_id:
                for s in AcademicRepository.get_sections(db, class_id=cls_id):
                    self.mv_section_combo.addItem(f"{s.name} ({s.shift})", s.id)
        finally:
            db.close()

    def _load_calendar_table(self):
        ay_id = self._selected_year_id()
        db: Session = SessionLocal()
        try:
            events = AcademicRepository.list_calendar_events(db, academic_year_id=ay_id)
            self.cal_table.setRowCount(len(events))
            for r, ev in enumerate(events):
                self.cal_table.setItem(r, 0, QTableWidgetItem(ev.event_title))
                self.cal_table.setItem(r, 1, QTableWidgetItem(ev.event_category))
                self.cal_table.setItem(r, 2, QTableWidgetItem(str(ev.start_date)))
                self.cal_table.setItem(r, 3, QTableWidgetItem(str(ev.end_date)))
                self.cal_table.setItem(r, 4, QTableWidgetItem(ev.term_name or "-"))
                self.cal_table.setItem(r, 5, QTableWidgetItem(ev.venue or "-"))
                self.cal_table.setItem(r, 6, QTableWidgetItem("Holiday" if ev.is_holiday else "Regular"))
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Action Handlers
    # ------------------------------------------------------------------
    def _on_open_wizard(self):
        dlg = AcademicWizardDialog(self, actor=self._actor)
        if dlg.exec() == AcademicWizardDialog.Accepted:
            self.refresh_all()

    def _on_add_class(self):
        dlg = ClassFormDialog(self, default_year_id=self._selected_year_id())
        if dlg.exec() == ClassFormDialog.Accepted:
            self.refresh_all()

    def _on_edit_selected_class(self):
        cls_id = self._selected_class_id()
        if not cls_id:
            QMessageBox.information(self, "Select Class", "Please select a class row to edit.")
            return
        dlg = ClassFormDialog(self, class_id=cls_id)
        if dlg.exec() == ClassFormDialog.Accepted:
            self.refresh_all()

    def _on_delete_selected_class(self):
        cls_id = self._selected_class_id()
        if not cls_id:
            return
        db = SessionLocal()
        try:
            ok, msg = AcademicService.safe_delete_class(db, cls_id, current_user=self._actor)
            if ok:
                QMessageBox.information(self, "Deleted", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Protected Historical Record", msg)
        finally:
            db.close()

    def _on_add_section(self):
        dlg = SectionFormDialog(
            self,
            default_class_id=self._selected_class_id(),
            default_year_id=self._selected_year_id(),
        )
        if dlg.exec() == SectionFormDialog.Accepted:
            self.refresh_all()

    def _on_edit_selected_section(self):
        row = self.sections_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Section", "Please select a section row to edit.")
            return
        sec_id = self.sections_table.item(row, 0).data(Qt.UserRole)
        dlg = SectionFormDialog(self, section_id=sec_id)
        if dlg.exec() == SectionFormDialog.Accepted:
            self.refresh_all()

    def _on_delete_selected_section(self):
        row = self.sections_table.currentRow()
        if row < 0:
            return
        sec_id = self.sections_table.item(row, 0).data(Qt.UserRole)
        db = SessionLocal()
        try:
            ok, msg = AcademicService.safe_delete_section(db, sec_id, current_user=self._actor)
            if ok:
                QMessageBox.information(self, "Deleted", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Protected Record", msg)
        finally:
            db.close()

    def _on_add_subject(self):
        dlg = SubjectFormDialog(
            self,
            default_class_id=self._selected_class_id(),
            default_year_id=self._selected_year_id(),
        )
        if dlg.exec() == SubjectFormDialog.Accepted:
            self.refresh_all()

    def _on_edit_selected_subject(self):
        row = self.subjects_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Subject", "Please select a subject row to edit.")
            return
        sub_id = self.subjects_table.item(row, 0).data(Qt.UserRole)
        dlg = SubjectFormDialog(self, subject_pk=sub_id)
        if dlg.exec() == SubjectFormDialog.Accepted:
            self.refresh_all()

    def _on_delete_selected_subject(self):
        row = self.subjects_table.currentRow()
        if row < 0:
            return
        sub_id = self.subjects_table.item(row, 0).data(Qt.UserRole)
        db = SessionLocal()
        try:
            ok, msg = AcademicService.safe_delete_subject(db, sub_id, current_user=self._actor)
            if ok:
                QMessageBox.information(self, "Deleted", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Protected Record", msg)
        finally:
            db.close()

    def _on_open_promote_dialog(self):
        dlg = StudentPromoteDialog(self, actor=self._actor)
        if dlg.exec() == StudentPromoteDialog.Accepted:
            self.refresh_all()

    def _on_create_academic_year(self):
        qs = self.ay_start_edit.date()
        qe = self.ay_end_edit.date()
        db = SessionLocal()
        try:
            ay, msg = AcademicService.create_academic_year(
                db,
                {
                    "name": self.ay_name_edit.text().strip(),
                    "start_date": date(qs.year(), qs.month(), qs.day()),
                    "end_date": date(qe.year(), qe.month(), qe.day()),
                    "is_current": self.ay_curr_chk.isChecked(),
                    "status": "Active" if self.ay_curr_chk.isChecked() else "Upcoming",
                },
                current_user=self._actor,
            )
            if ay:
                self.ay_name_edit.clear()
                QMessageBox.information(self, "Success", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Validation Error", msg)
        finally:
            db.close()

    def _on_activate_selected_year(self):
        row = self.years_table.currentRow()
        if row < 0:
            return
        y_id = self.years_table.item(row, 0).data(Qt.UserRole)
        db = SessionLocal()
        try:
            ay, msg = AcademicService.activate_academic_year(db, y_id, current_user=self._actor)
            if ay:
                QMessageBox.information(self, "Activated", msg)
                self.refresh_all()
        finally:
            db.close()

    def _on_close_selected_year(self):
        row = self.years_table.currentRow()
        if row < 0:
            return
        y_id = self.years_table.item(row, 0).data(Qt.UserRole)
        db = SessionLocal()
        try:
            ay, msg = AcademicService.close_academic_year(db, y_id, current_user=self._actor)
            if ay:
                QMessageBox.information(self, "Completed", msg)
                self.refresh_all()
        finally:
            db.close()

    def _on_clone_year_structure(self):
        src_id = self.clone_src_combo.currentData()
        tgt_id = self.clone_tgt_combo.currentData()
        db = SessionLocal()
        try:
            ok, _cnts, msg = AcademicService.clone_academic_structure(
                db,
                source_year_id=src_id,
                target_year_id=tgt_id,
                include_sections=True,
                include_subjects=True,
                copy_teachers=self.clone_teachers_chk.isChecked(),
                current_user=self._actor,
            )
            if ok:
                QMessageBox.information(self, "Structure Cloned", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Clone Notice", msg)
        finally:
            db.close()

    def _on_add_group(self):
        db = SessionLocal()
        try:
            grp, msg = AcademicService.create_group(
                db,
                {"name": self.grp_name_in.text(), "code": self.grp_code_in.text()},
                current_user=self._actor,
            )
            if grp:
                self.grp_name_in.clear()
                self.grp_code_in.clear()
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Group Error", msg)
        finally:
            db.close()

    def _on_add_shift(self):
        db = SessionLocal()
        try:
            sh, msg = AcademicService.create_shift(
                db,
                {
                    "name": self.sh_name_in.text(),
                    "code": self.sh_code_in.text(),
                    "start_time": self.sh_start_in.text(),
                    "end_time": self.sh_end_in.text(),
                },
                current_user=self._actor,
            )
            if sh:
                self.sh_name_in.clear()
                self.sh_code_in.clear()
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Shift Error", msg)
        finally:
            db.close()

    def _on_add_department(self):
        db = SessionLocal()
        try:
            d, msg = AcademicService.create_department(
                db,
                {"name": self.dept_name_in.text(), "code": self.dept_code_in.text()},
                current_user=self._actor,
            )
            if d:
                self.dept_name_in.clear()
                self.dept_code_in.clear()
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Department Error", msg)
        finally:
            db.close()

    def _on_add_room(self):
        db = SessionLocal()
        try:
            rm, msg = AcademicService.create_room(
                db,
                {
                    "room_number": self.rm_no_in.text(),
                    "building": self.rm_bldg_in.text(),
                    "room_type": self.rm_type_in.currentText(),
                    "capacity": self.rm_cap_in.value(),
                },
                current_user=self._actor,
            )
            if rm:
                self.rm_no_in.clear()
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Room Error", msg)
        finally:
            db.close()

    def _on_enroll_optional_subject(self):
        stu_id = self.opt_stu_combo.currentData()
        sub_id = self.opt_sub_combo.currentData()
        if not stu_id or not sub_id:
            return
        db = SessionLocal()
        try:
            enr, msg = AcademicService.enroll_student_subject(
                db, student_id=stu_id, subject_id=sub_id, current_user=self._actor
            )
            if enr:
                QMessageBox.information(self, "Enrolled", msg)
                self._load_student_subject_enrollments()
            else:
                QMessageBox.warning(self, "Enrollment Notice", msg)
        finally:
            db.close()

    def _on_drop_optional_subject(self):
        row = self.opt_table.currentRow()
        if row < 0:
            return
        enr_id = self.opt_table.item(row, 0).data(Qt.UserRole)
        db = SessionLocal()
        try:
            ok, msg = AcademicService.drop_student_subject(db, enr_id, current_user=self._actor)
            if ok:
                self._load_student_subject_enrollments()
            else:
                QMessageBox.warning(self, "Notice", msg)
        finally:
            db.close()

    def _on_execute_movement(self):
        stu_id = self.mv_student_combo.currentData()
        if not stu_id:
            return
        op = self.mv_op_combo.currentText()
        cls_id = self.mv_class_combo.currentData()
        sec_id = self.mv_section_combo.currentData()
        ay_id = self.mv_ay_combo.currentData()
        roll_val = self.mv_roll_spin.value()
        new_roll = roll_val if roll_val > 0 else None
        reason = self.mv_reason_edit.text().strip() or op

        db = SessionLocal()
        try:
            if op == "Section Transfer":
                if not sec_id:
                    QMessageBox.warning(self, "Validation Error", "Please choose a target section.")
                    return
                ok, _stu, msg = AcademicService.transfer_student_section(
                    db, stu_id, to_section_id=sec_id, new_roll_number=new_roll, reason=reason, current_user=self._actor
                )
            elif op == "Class Transfer":
                if not cls_id:
                    QMessageBox.warning(self, "Validation Error", "Please choose a target class.")
                    return
                ok, _stu, msg = AcademicService.transfer_student_class(
                    db, stu_id, to_class_id=cls_id, to_section_id=sec_id, new_roll_number=new_roll, reason=reason, current_user=self._actor
                )
            else:
                ok, _stu, msg = AcademicService.promote_single_student(
                    db,
                    stu_id,
                    to_class_id=cls_id,
                    to_academic_year_id=ay_id,
                    to_section_id=sec_id,
                    new_roll_number=new_roll,
                    remarks=reason,
                    current_user=self._actor,
                )

            if ok:
                QMessageBox.information(self, "Movement Recorded", msg)
                self._on_movement_student_changed()
                self._load_kpi_and_combos()
            else:
                QMessageBox.warning(self, "Movement Failed", msg)
        finally:
            db.close()

    def _on_add_calendar_event(self):
        qs = self.cal_start_in.date()
        qe = self.cal_end_in.date()
        db = SessionLocal()
        try:
            ev, msg = AcademicService.create_calendar_event(
                db,
                event_title=self.cal_title_in.text(),
                start_date=date(qs.year(), qs.month(), qs.day()),
                end_date=date(qe.year(), qe.month(), qe.day()),
                event_category=self.cal_cat_in.currentText(),
                academic_year_id=self._selected_year_id(),
                term_name=self.cal_term_in.text().strip() or None,
                is_holiday=self.cal_hol_chk.isChecked(),
                current_user=self._actor,
            )
            if ev:
                self.cal_title_in.clear()
                self._load_calendar_table()
                self._load_kpi_and_combos()
            else:
                QMessageBox.warning(self, "Calendar Error", msg)
        finally:
            db.close()

    def _on_export_calendar_pdf(self):
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Academic Calendar PDF", "academic_calendar.pdf", "PDF Files (*.pdf)"
        )
        if not out_path:
            return
        db = SessionLocal()
        try:
            saved = AcademicService.export_calendar_pdf(
                db, out_path, academic_year_id=self._selected_year_id()
            )
            QMessageBox.information(self, "PDF Exported", f"Academic calendar exported to:\n{saved}")
        finally:
            db.close()
