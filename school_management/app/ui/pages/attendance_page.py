"""
EduManage Pro - Professional Attendance Management Console (PySide6)
6-Tab Enterprise Console:
1. Student Daily & Bulk Attendance (5 Statuses: Present, Absent, Late, Leave, Excused)
2. Teacher & Non-Teaching Staff Attendance (with Approved HR Leave Sync)
3. Monthly Register, Date Range & Individual Attendance History (+ Excel Export)
4. Attendance Correction Requests & Supervisor Approval Queue
5. Attendance Analytics & Chronic Absenteeism Risk Alerts
6. Optional Capture Integration (QR, RFID, Biometric, Face Recognition — Hardware Not Required)
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.attendance import AttendanceStatus
from app.models.staff import Department, Staff, Teacher
from app.models.student import Student
from app.repositories.academic_repository import AcademicRepository
from app.repositories.attendance_repository import AttendanceRepository
from app.services.attendance_integration import AdapterType, AttendanceIntegrationManager
from app.services.attendance_service import AttendanceService


class AttendancePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.student_rows_data: List[Dict[str, Any]] = []
        self.employee_rows_data: List[Dict[str, Any]] = []
        self._init_ui()
        self.refresh_all()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # Header
        header_h = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("Attendance Management & Analytics")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A;")
        sub_lbl = QLabel(
            "Student, Teacher & Staff Registers (Present, Absent, Late, Leave, Excused) · "
            "Correction Approvals · HR Leave Sync · Analytics · Optional QR/RFID/Biometric Integration"
        )
        sub_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header_h.addLayout(title_box)
        header_h.addStretch()

        btn_refresh = QPushButton("Refresh All")
        btn_refresh.setStyleSheet(
            "background-color: #0F172A; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;"
        )
        btn_refresh.clicked.connect(self.refresh_all)
        header_h.addWidget(btn_refresh)
        main_layout.addLayout(header_h)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { font-weight: 600; padding: 8px 14px; margin-right: 3px; }
            QTabBar::tab:selected { background: #2563EB; color: white; border-radius: 4px; }
        """)

        self.tabs.addTab(self._build_student_tab(), "1. Student Daily & Bulk")
        self.tabs.addTab(self._build_employee_tab(), "2. Teacher & Staff Attendance")
        self.tabs.addTab(self._build_reports_history_tab(), "3. Monthly / Range / History")
        self.tabs.addTab(self._build_corrections_tab(), "4. Correction Approvals")
        self.tabs.addTab(self._build_analytics_tab(), "5. Analytics & Alerts")
        self.tabs.addTab(self._build_integration_tab(), "6. QR / RFID / Biometric (Optional)")

        main_layout.addWidget(self.tabs)

    def refresh_all(self):
        self._load_reference_filters()
        self._load_student_roster()
        self._load_employee_roster()
        self._load_correction_requests()
        self._load_analytics()
        self._load_integration_state()

    # ==================================================================
    # TAB 1: STUDENT DAILY & BULK ATTENDANCE
    # ==================================================================
    def _build_student_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        bar = QFrame()
        bar.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        bar_h = QHBoxLayout(bar)
        bar_h.setContentsMargins(12, 8, 12, 8)
        bar_h.setSpacing(10)

        bar_h.addWidget(QLabel("Date:"))
        self.stu_date_edit = QDateEdit()
        self.stu_date_edit.setCalendarPopup(True)
        self.stu_date_edit.setDate(QDate.currentDate())
        self.stu_date_edit.dateChanged.connect(self._load_student_roster)
        bar_h.addWidget(self.stu_date_edit)

        bar_h.addWidget(QLabel("Class:"))
        self.stu_class_combo = QComboBox()
        self.stu_class_combo.currentIndexChanged.connect(self._on_class_changed)
        bar_h.addWidget(self.stu_class_combo)

        bar_h.addWidget(QLabel("Section:"))
        self.stu_sec_combo = QComboBox()
        self.stu_sec_combo.currentIndexChanged.connect(self._load_student_roster)
        bar_h.addWidget(self.stu_sec_combo)

        bar_h.addStretch()

        btn_all_p = QPushButton("Mark All Present")
        btn_all_p.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 10px; border-radius: 6px;")
        btn_all_p.clicked.connect(lambda: self._bulk_set_student_table_status(AttendanceStatus.PRESENT))
        bar_h.addWidget(btn_all_p)

        btn_all_a = QPushButton("Mark All Absent")
        btn_all_a.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; padding: 6px 10px; border-radius: 6px;")
        btn_all_a.clicked.connect(lambda: self._bulk_set_student_table_status(AttendanceStatus.ABSENT))
        bar_h.addWidget(btn_all_a)

        btn_export = QPushButton("Export Monthly (.xlsx)")
        btn_export.setStyleSheet("background-color: #4B5563; color: white; font-weight: bold; padding: 6px 10px; border-radius: 6px;")
        btn_export.clicked.connect(self._on_export_student_excel)
        bar_h.addWidget(btn_export)

        btn_save = QPushButton("Save Attendance")
        btn_save.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 14px; border-radius: 6px;")
        btn_save.clicked.connect(self._on_save_student_attendance)
        bar_h.addWidget(btn_save)
        layout.addWidget(bar)

        # KPI Strip (All 5 statuses)
        kpi_frame = QFrame()
        kpi_frame.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;")
        kpi_h = QHBoxLayout(kpi_frame)
        kpi_h.setContentsMargins(14, 8, 14, 8)
        self.stu_kpi_total = QLabel("Total: 0")
        self.stu_kpi_p = QLabel("Present: 0")
        self.stu_kpi_a = QLabel("Absent: 0")
        self.stu_kpi_l = QLabel("Late: 0")
        self.stu_kpi_lv = QLabel("Leave: 0")
        self.stu_kpi_ex = QLabel("Excused: 0")
        self.stu_kpi_rate = QLabel("Rate: 0.0%")
        for lbl, col in [
            (self.stu_kpi_total, "#1E293B"),
            (self.stu_kpi_p, "#059669"),
            (self.stu_kpi_a, "#DC2626"),
            (self.stu_kpi_l, "#D97706"),
            (self.stu_kpi_lv, "#4F46E5"),
            (self.stu_kpi_ex, "#0D9488"),
            (self.stu_kpi_rate, "#2563EB"),
        ]:
            lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {col};")
            kpi_h.addWidget(lbl)
            kpi_h.addSpacing(14)
        kpi_h.addStretch()
        layout.addWidget(kpi_frame)

        self.stu_table = QTableWidget()
        self.stu_table.setColumnCount(8)
        self.stu_table.setHorizontalHeaderLabels([
            "Roll", "Student ID", "Full Name", "Status", "Quick Actions", "Check-in Time", "Remarks / Excuse", "Source"
        ])
        self.stu_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stu_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.stu_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.stu_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.stu_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.stu_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.stu_table)
        return tab

    # ==================================================================
    # TAB 2: TEACHER & NON-TEACHING STAFF ATTENDANCE + LEAVE SYNC
    # ==================================================================
    def _build_employee_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        bar = QFrame()
        bar.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        bar_h = QHBoxLayout(bar)
        bar_h.setContentsMargins(12, 8, 12, 8)
        bar_h.setSpacing(10)

        bar_h.addWidget(QLabel("Group:"))
        self.emp_type_combo = QComboBox()
        self.emp_type_combo.addItem("Teachers / Faculty", "teacher")
        self.emp_type_combo.addItem("Non-Teaching Staff", "staff")
        self.emp_type_combo.currentIndexChanged.connect(self._load_employee_roster)
        bar_h.addWidget(self.emp_type_combo)

        bar_h.addWidget(QLabel("Date:"))
        self.emp_date_edit = QDateEdit()
        self.emp_date_edit.setCalendarPopup(True)
        self.emp_date_edit.setDate(QDate.currentDate())
        self.emp_date_edit.dateChanged.connect(self._load_employee_roster)
        bar_h.addWidget(self.emp_date_edit)

        bar_h.addWidget(QLabel("Department:"))
        self.emp_dept_combo = QComboBox()
        self.emp_dept_combo.currentIndexChanged.connect(self._load_employee_roster)
        bar_h.addWidget(self.emp_dept_combo)

        bar_h.addStretch()

        btn_sync_lv = QPushButton("Sync HR Approved Leaves")
        btn_sync_lv.setStyleSheet("background-color: #4F46E5; color: white; font-weight: bold; padding: 6px 10px; border-radius: 6px;")
        btn_sync_lv.clicked.connect(self._on_sync_hr_leaves)
        bar_h.addWidget(btn_sync_lv)

        btn_emp_p = QPushButton("Mark All Present")
        btn_emp_p.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 10px; border-radius: 6px;")
        btn_emp_p.clicked.connect(lambda: self._bulk_set_employee_table_status(AttendanceStatus.PRESENT))
        bar_h.addWidget(btn_emp_p)

        btn_emp_save = QPushButton("Save Attendance")
        btn_emp_save.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 14px; border-radius: 6px;")
        btn_emp_save.clicked.connect(self._on_save_employee_attendance)
        bar_h.addWidget(btn_emp_save)
        layout.addWidget(bar)

        # KPI Strip
        kpi_frame = QFrame()
        kpi_frame.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;")
        kpi_h = QHBoxLayout(kpi_frame)
        kpi_h.setContentsMargins(14, 8, 14, 8)
        self.emp_kpi_summary = QLabel("Total: 0 | Present: 0 | Absent: 0 | Late: 0 | Leave: 0 | Excused: 0 | Rate: 0.0%")
        self.emp_kpi_summary.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        kpi_h.addWidget(self.emp_kpi_summary)
        kpi_h.addStretch()
        layout.addWidget(kpi_frame)

        self.emp_table = QTableWidget()
        self.emp_table.setColumnCount(8)
        self.emp_table.setHorizontalHeaderLabels([
            "Employee ID", "Full Name", "Department", "Role / Subject", "Status", "Check-In", "Check-Out", "Remarks / Source"
        ])
        self.emp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.emp_table)
        return tab

    # ==================================================================
    # TAB 3: MONTHLY REGISTER, DATE RANGE & INDIVIDUAL HISTORY
    # ==================================================================
    def _build_reports_history_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        bar = QFrame()
        bar.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        bar_h = QHBoxLayout(bar)
        bar_h.setContentsMargins(12, 8, 12, 8)
        bar_h.setSpacing(8)

        bar_h.addWidget(QLabel("Target:"))
        self.rep_target_combo = QComboBox()
        self.rep_target_combo.addItem("Student", "student")
        self.rep_target_combo.addItem("Teacher", "teacher")
        self.rep_target_combo.addItem("Staff", "staff")
        self.rep_target_combo.currentIndexChanged.connect(self._on_report_target_changed)
        bar_h.addWidget(self.rep_target_combo)

        bar_h.addWidget(QLabel("Mode:"))
        self.rep_mode_combo = QComboBox()
        self.rep_mode_combo.addItems(["Monthly Summary", "Date Range Log", "Individual History"])
        bar_h.addWidget(self.rep_mode_combo)

        bar_h.addWidget(QLabel("Class/Dept:"))
        self.rep_scope_combo = QComboBox()
        bar_h.addWidget(self.rep_scope_combo)

        bar_h.addWidget(QLabel("Individual:"))
        self.rep_person_combo = QComboBox()
        bar_h.addWidget(self.rep_person_combo)

        bar_h.addWidget(QLabel("From:"))
        self.rep_start_date = QDateEdit()
        self.rep_start_date.setCalendarPopup(True)
        today_q = QDate.currentDate()
        self.rep_start_date.setDate(QDate(today_q.year(), today_q.month(), 1))
        bar_h.addWidget(self.rep_start_date)

        bar_h.addWidget(QLabel("To:"))
        self.rep_end_date = QDateEdit()
        self.rep_end_date.setCalendarPopup(True)
        self.rep_end_date.setDate(today_q)
        bar_h.addWidget(self.rep_end_date)

        btn_run = QPushButton("Load Report")
        btn_run.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_run.clicked.connect(self._on_run_history_report)
        bar_h.addWidget(btn_run)

        btn_exp = QPushButton("Export Monthly (.xlsx)")
        btn_exp.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 10px; border-radius: 6px;")
        btn_exp.clicked.connect(self._on_export_report_excel)
        bar_h.addWidget(btn_exp)
        layout.addWidget(bar)

        self.rep_summary_lbl = QLabel("Select parameters and click 'Load Report' to inspect Monthly, Date Range, or Individual History.")
        self.rep_summary_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #0F172A; padding: 6px;")
        layout.addWidget(self.rep_summary_lbl)

        self.rep_table = QTableWidget()
        self.rep_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.rep_table)
        return tab

    # ==================================================================
    # TAB 4: ATTENDANCE CORRECTION REQUESTS & APPROVAL QUEUE
    # ==================================================================
    def _build_corrections_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)

        # Left Form: Submit Request
        form_box = QFrame()
        form_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        flay = QFormLayout(form_box)
        flay.setContentsMargins(14, 14, 14, 14)

        hdr = QLabel("Submit Attendance Correction")
        hdr.setStyleSheet("font-size: 14px; font-weight: bold; color: #0F172A;")
        flay.addRow(hdr)

        self.corr_target_combo = QComboBox()
        self.corr_target_combo.addItem("Student", "student")
        self.corr_target_combo.addItem("Teacher", "teacher")
        self.corr_target_combo.addItem("Staff", "staff")
        self.corr_target_combo.currentIndexChanged.connect(self._populate_correction_persons)
        flay.addRow("Target Type:", self.corr_target_combo)

        self.corr_person_combo = QComboBox()
        flay.addRow("Person:", self.corr_person_combo)

        self.corr_date_edit = QDateEdit()
        self.corr_date_edit.setCalendarPopup(True)
        self.corr_date_edit.setDate(QDate.currentDate())
        flay.addRow("Attendance Date:", self.corr_date_edit)

        self.corr_status_combo = QComboBox()
        self.corr_status_combo.addItems(AttendanceStatus.ALL)
        flay.addRow("Requested Status:", self.corr_status_combo)

        self.corr_cin_edit = QLineEdit()
        self.corr_cin_edit.setPlaceholderText("e.g. 08:15 AM (optional)")
        flay.addRow("Check-in Time:", self.corr_cin_edit)

        self.corr_reason_edit = QTextEdit()
        self.corr_reason_edit.setPlaceholderText("Provide justification / medical or duty note...")
        self.corr_reason_edit.setMaximumHeight(90)
        flay.addRow("Reason:", self.corr_reason_edit)

        btn_sub = QPushButton("Submit Correction Request")
        btn_sub.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 8px 12px; border-radius: 6px;")
        btn_sub.clicked.connect(self._on_submit_correction)
        flay.addRow(btn_sub)

        # Right Table: Approval Queue
        right_box = QWidget()
        rlay = QVBoxLayout(right_box)
        rlay.setContentsMargins(6, 0, 0, 0)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Filter Status:"))
        self.corr_filter_combo = QComboBox()
        self.corr_filter_combo.addItems(["All", "Pending", "Approved", "Rejected"])
        self.corr_filter_combo.currentIndexChanged.connect(self._load_correction_requests)
        top_bar.addWidget(self.corr_filter_combo)
        top_bar.addStretch()

        btn_app = QPushButton("Approve Selected")
        btn_app.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_app.clicked.connect(lambda: self._on_review_correction(True))
        top_bar.addWidget(btn_app)

        btn_rej = QPushButton("Reject Selected")
        btn_rej.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_rej.clicked.connect(lambda: self._on_review_correction(False))
        top_bar.addWidget(btn_rej)
        rlay.addLayout(top_bar)

        self.corr_table = QTableWidget()
        self.corr_table.setColumnCount(8)
        self.corr_table.setHorizontalHeaderLabels([
            "ID", "Type", "Person", "Date", "Original -> Requested", "Reason", "Status", "Reviewed By"
        ])
        self.corr_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.corr_table.setSelectionBehavior(QTableWidget.SelectRows)
        rlay.addWidget(self.corr_table)

        splitter.addWidget(form_box)
        splitter.addWidget(right_box)
        splitter.setSizes([340, 760])
        layout.addWidget(splitter)
        return tab

    # ==================================================================
    # TAB 5: ATTENDANCE ANALYTICS & RISK ALERTS
    # ==================================================================
    def _build_analytics_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        bar = QFrame()
        bar.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        bar_h = QHBoxLayout(bar)
        bar_h.setContentsMargins(12, 8, 12, 8)
        bar_h.addWidget(QLabel("From:"))
        self.ana_start = QDateEdit()
        self.ana_start.setCalendarPopup(True)
        self.ana_start.setDate(QDate.currentDate().addDays(-29))
        bar_h.addWidget(self.ana_start)

        bar_h.addWidget(QLabel("To:"))
        self.ana_end = QDateEdit()
        self.ana_end.setCalendarPopup(True)
        self.ana_end.setDate(QDate.currentDate())
        bar_h.addWidget(self.ana_end)

        bar_h.addWidget(QLabel("At-Risk Threshold (%):"))
        self.ana_threshold = QSpinBox()
        self.ana_threshold.setRange(10, 95)
        self.ana_threshold.setValue(75)
        bar_h.addWidget(self.ana_threshold)

        btn_calc = QPushButton("Run Analytics")
        btn_calc.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 14px; border-radius: 6px;")
        btn_calc.clicked.connect(self._load_analytics)
        bar_h.addWidget(btn_calc)
        bar_h.addStretch()
        layout.addWidget(bar)

        self.ana_kpi_lbl = QLabel("Analytics KPI summary will appear here.")
        self.ana_kpi_lbl.setStyleSheet(
            "background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; "
            "padding: 10px 14px; font-size: 13px; font-weight: bold; color: #0F172A;"
        )
        layout.addWidget(self.ana_kpi_lbl)

        tables_split = QSplitter(Qt.Horizontal)
        self.ana_breakdown_table = QTableWidget()
        self.ana_breakdown_table.setColumnCount(7)
        self.ana_breakdown_table.setHorizontalHeaderLabels([
            "Scope / Class / Dept", "Total", "Present", "Absent", "Late", "Leave/Ex", "Rate %"
        ])
        self.ana_breakdown_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.ana_risk_table = QTableWidget()
        self.ana_risk_table.setColumnCount(6)
        self.ana_risk_table.setHorizontalHeaderLabels([
            "Category", "ID", "Name", "Class / Dept", "Days", "Attendance %"
        ])
        self.ana_risk_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        tables_split.addWidget(self.ana_breakdown_table)
        tables_split.addWidget(self.ana_risk_table)
        layout.addWidget(tables_split)
        return tab

    # ==================================================================
    # TAB 6: OPTIONAL CAPTURE INTEGRATION (QR / RFID / BIOMETRIC / FACE)
    # ==================================================================
    def _build_integration_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        banner = QLabel(
            "Hardware-Optional Architecture: Manual marking in Tabs 1–4 works 100% standalone without any device. "
            "Configure QR, RFID, Biometric, or future Face Recognition gateways below if your campus uses automated scanning."
        )
        banner.setWordWrap(True)
        banner.setStyleSheet(
            "background-color: #EFF6FF; border: 1px solid #BFDBFE; color: #1E3A8A; "
            "padding: 10px 14px; border-radius: 8px; font-weight: 600;"
        )
        layout.addWidget(banner)

        splitter = QSplitter(Qt.Horizontal)

        # Left: Device Registry + Credential Binding + Scan Test
        left_box = QFrame()
        left_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        lform = QFormLayout(left_box)
        lform.setContentsMargins(12, 12, 12, 12)

        lform.addRow(QLabel("<b>1. Process Scan Event (QR / RFID / Biometric / Face)</b>"))
        self.scan_adapter_combo = QComboBox()
        self.scan_adapter_combo.addItems(AdapterType.ALL)
        lform.addRow("Adapter Type:", self.scan_adapter_combo)

        self.scan_identifier_edit = QLineEdit()
        self.scan_identifier_edit.setPlaceholderText("e.g. STU-2026-0001, Digital ID, RFID Hex UID, Biometric ID")
        lform.addRow("Credential Token:", self.scan_identifier_edit)

        self.scan_direction_combo = QComboBox()
        self.scan_direction_combo.addItems(["CHECK_IN", "CHECK_OUT"])
        lform.addRow("Direction:", self.scan_direction_combo)

        self.scan_conf_spin = QDoubleSpinBox()
        self.scan_conf_spin.setRange(0.0, 1.0)
        self.scan_conf_spin.setSingleStep(0.05)
        self.scan_conf_spin.setValue(0.95)
        lform.addRow("Match Confidence:", self.scan_conf_spin)

        btn_scan = QPushButton("Process Scan & Mark Attendance")
        btn_scan.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;")
        btn_scan.clicked.connect(self._on_process_scan)
        lform.addRow(btn_scan)

        lform.addRow(QLabel("<b>2. Register Optional Capture Device</b>"))
        self.dev_code_edit = QLineEdit()
        self.dev_code_edit.setPlaceholderText("e.g. GATE-QR-01")
        lform.addRow("Device Code:", self.dev_code_edit)

        self.dev_name_edit = QLineEdit()
        self.dev_name_edit.setPlaceholderText("e.g. Main Gate USB Scanner")
        lform.addRow("Device Name:", self.dev_name_edit)

        self.dev_adapter_combo = QComboBox()
        self.dev_adapter_combo.addItems(AdapterType.ALL)
        lform.addRow("Channel:", self.dev_adapter_combo)

        self.dev_mode_combo = QComboBox()
        self.dev_mode_combo.addItems(["Simulated", "USB_HID", "Serial", "TCP_IP", "REST_Webhook", "Camera"])
        lform.addRow("Connection Mode:", self.dev_mode_combo)

        btn_reg_dev = QPushButton("Register Optional Device")
        btn_reg_dev.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;")
        btn_reg_dev.clicked.connect(self._on_register_device)
        lform.addRow(btn_reg_dev)

        # Right: Registered Devices + Recent Scan Audit Log
        right_box = QWidget()
        rlay = QVBoxLayout(right_box)
        rlay.setContentsMargins(6, 0, 0, 0)
        rlay.addWidget(QLabel("<b>Configured Optional Devices</b>"))
        self.dev_table = QTableWidget()
        self.dev_table.setColumnCount(5)
        self.dev_table.setHorizontalHeaderLabels(["Code", "Name", "Adapter", "Mode", "Enabled"])
        self.dev_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rlay.addWidget(self.dev_table)

        rlay.addWidget(QLabel("<b>Recent Automated Scan Audit Log</b>"))
        self.scan_log_table = QTableWidget()
        self.scan_log_table.setColumnCount(6)
        self.scan_log_table.setHorizontalHeaderLabels(["Timestamp", "Adapter", "Token", "Direction", "Status", "Notes"])
        self.scan_log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rlay.addWidget(self.scan_log_table)

        splitter.addWidget(left_box)
        splitter.addWidget(right_box)
        splitter.setSizes([380, 720])
        layout.addWidget(splitter)
        return tab

    # ==================================================================
    # DATA LOADING & INTERACTION HANDLERS
    # ==================================================================
    def _load_reference_filters(self):
        db: Session = SessionLocal()
        try:
            classes = AcademicRepository.get_classes(db)
            self.stu_class_combo.blockSignals(True)
            self.stu_class_combo.clear()
            for c in classes:
                self.stu_class_combo.addItem(f"{c.name} ({c.group})", c.id)
            self.stu_class_combo.blockSignals(False)

            depts = db.query(Department).filter(Department.is_deleted == False).order_by(Department.name.asc()).all()
            self.emp_dept_combo.blockSignals(True)
            self.emp_dept_combo.clear()
            self.emp_dept_combo.addItem("All Departments", None)
            for d in depts:
                self.emp_dept_combo.addItem(d.name, d.id)
            self.emp_dept_combo.blockSignals(False)

            self._sync_sections_combo()
            self._on_report_target_changed()
            self._populate_correction_persons()
        finally:
            db.close()

    def _sync_sections_combo(self):
        class_id = self.stu_class_combo.currentData()
        self.stu_sec_combo.blockSignals(True)
        self.stu_sec_combo.clear()
        self.stu_sec_combo.addItem("All Sections", None)
        if class_id:
            db: Session = SessionLocal()
            try:
                for s in AcademicRepository.get_sections(db, class_id=class_id):
                    self.stu_sec_combo.addItem(s.name, s.id)
            finally:
                db.close()
        self.stu_sec_combo.blockSignals(False)

    def _on_class_changed(self):
        self._sync_sections_combo()
        self._load_student_roster()

    def _load_student_roster(self):
        class_id = self.stu_class_combo.currentData()
        if not class_id:
            self.stu_table.setRowCount(0)
            self.student_rows_data = []
            return
        section_id = self.stu_sec_combo.currentData()
        qd = self.stu_date_edit.date()
        att_date = date(qd.year(), qd.month(), qd.day())

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

                combo = QComboBox()
                combo.addItems(AttendanceStatus.ALL)
                idx = combo.findText(item["status"])
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                combo.currentIndexChanged.connect(lambda _, r=row: self._update_student_kpi())
                self.stu_table.setCellWidget(row, 3, combo)

                btn_widget = QWidget()
                btn_h = QHBoxLayout(btn_widget)
                btn_h.setContentsMargins(2, 2, 2, 2)
                btn_h.setSpacing(2)
                for code, st_name, color in [
                    ("P", AttendanceStatus.PRESENT, "#059669"),
                    ("A", AttendanceStatus.ABSENT, "#DC2626"),
                    ("L", AttendanceStatus.LATE, "#D97706"),
                    ("Lv", AttendanceStatus.LEAVE, "#4F46E5"),
                    ("Ex", AttendanceStatus.EXCUSED, "#0D9488"),
                ]:
                    b = QPushButton(code)
                    b.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold; padding: 2px 5px;")
                    b.clicked.connect(lambda _, r=row, s=st_name: self._set_single_student_status(r, s))
                    btn_h.addWidget(b)
                self.stu_table.setCellWidget(row, 4, btn_widget)

                cin_edit = QLineEdit(item["check_in_time"] or "08:15 AM")
                self.stu_table.setCellWidget(row, 5, cin_edit)

                rem_edit = QLineEdit(item["remarks"] or item["excuse_reason"] or "")
                self.stu_table.setCellWidget(row, 6, rem_edit)

                src_txt = item.get("capture_source", "Manual")
                if item.get("is_edited"):
                    src_txt += " (Edited)"
                self.stu_table.setItem(row, 7, QTableWidgetItem(src_txt))

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

    def _bulk_set_student_table_status(self, status: str):
        for r in range(self.stu_table.rowCount()):
            self._set_single_student_status(r, status)

    def _update_student_kpi(self):
        total = self.stu_table.rowCount()
        counts = {s: 0 for s in AttendanceStatus.ALL}
        for r in range(total):
            combo = self.stu_table.cellWidget(r, 3)
            if isinstance(combo, QComboBox):
                st = combo.currentText()
                if st in counts:
                    counts[st] += 1
        rate = round((counts[AttendanceStatus.PRESENT] / total * 100), 1) if total > 0 else 0.0
        self.stu_kpi_total.setText(f"Total: {total}")
        self.stu_kpi_p.setText(f"Present: {counts[AttendanceStatus.PRESENT]}")
        self.stu_kpi_a.setText(f"Absent: {counts[AttendanceStatus.ABSENT]}")
        self.stu_kpi_l.setText(f"Late: {counts[AttendanceStatus.LATE]}")
        self.stu_kpi_lv.setText(f"Leave: {counts[AttendanceStatus.LEAVE]}")
        self.stu_kpi_ex.setText(f"Excused: {counts[AttendanceStatus.EXCUSED]}")
        self.stu_kpi_rate.setText(f"Rate: {rate}%")

    def _on_save_student_attendance(self):
        class_id = self.stu_class_combo.currentData()
        if not class_id:
            return
        section_id = self.stu_sec_combo.currentData()
        qd = self.stu_date_edit.date()
        att_date = date(qd.year(), qd.month(), qd.day())

        records = []
        for r in range(self.stu_table.rowCount()):
            stu = self.student_rows_data[r]["student"]
            combo = self.stu_table.cellWidget(r, 3)
            cin = self.stu_table.cellWidget(r, 5)
            rem = self.stu_table.cellWidget(r, 6)
            st = combo.currentText() if isinstance(combo, QComboBox) else AttendanceStatus.PRESENT
            rem_txt = rem.text() if isinstance(rem, QLineEdit) else ""
            records.append({
                "student_id": stu.id,
                "class_id": class_id,
                "section_id": stu.section_id or section_id,
                "academic_year_id": stu.academic_year_id,
                "date": att_date,
                "status": st,
                "check_in_time": cin.text() if isinstance(cin, QLineEdit) else None,
                "remarks": rem_txt,
                "excuse_reason": rem_txt if st == AttendanceStatus.EXCUSED else None,
            })

        db: Session = SessionLocal()
        try:
            ok, msg = AttendanceService.mark_student_attendance(db, class_id, section_id, att_date, records)
            if ok:
                QMessageBox.information(self, "Attendance Saved", msg)
                self._load_student_roster()
            else:
                QMessageBox.warning(self, "Validation", msg)
        except PermissionError as exc:
            QMessageBox.warning(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _on_export_student_excel(self):
        class_id = self.stu_class_combo.currentData()
        if not class_id:
            return
        section_id = self.stu_sec_combo.currentData()
        qd = self.stu_date_edit.date()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Student Attendance Register",
            f"Attendance_Student_Class{class_id}_{qd.year()}_{qd.month():02d}.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        db: Session = SessionLocal()
        try:
            AttendanceService.export_monthly_register_excel(db, class_id, qd.year(), qd.month(), path, section_id=section_id)
            QMessageBox.information(self, "Export Successful", f"Exported to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))
        finally:
            db.close()

    # -------------------- TAB 2: EMPLOYEE (TEACHER + STAFF) --------------------
    def _load_employee_roster(self):
        etype = self.emp_type_combo.currentData() or "teacher"
        dept_id = self.emp_dept_combo.currentData()
        qd = self.emp_date_edit.date()
        att_date = date(qd.year(), qd.month(), qd.day())

        db: Session = SessionLocal()
        try:
            if etype == "teacher":
                records = AttendanceRepository.get_teachers_with_attendance(db, att_date=att_date, department_id=dept_id)
            else:
                records = AttendanceRepository.get_staff_with_attendance(db, att_date=att_date, department_id=dept_id)

            self.employee_rows_data = records
            self.emp_table.setRowCount(len(records))
            counts = {s: 0 for s in AttendanceStatus.ALL}

            for row, item in enumerate(records):
                emp = item["teacher"] if etype == "teacher" else item["staff"]
                role_txt = emp.primary_subject if etype == "teacher" else emp.position
                self.emp_table.setItem(row, 0, QTableWidgetItem(emp.employee_id))
                self.emp_table.setItem(row, 1, QTableWidgetItem(emp.full_name))
                self.emp_table.setItem(row, 2, QTableWidgetItem(emp.department.name if emp.department else "-"))
                self.emp_table.setItem(row, 3, QTableWidgetItem(role_txt or "-"))

                combo = QComboBox()
                combo.addItems(AttendanceStatus.ALL)
                idx = combo.findText(item["status"])
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                self.emp_table.setCellWidget(row, 4, combo)
                if item["status"] in counts:
                    counts[item["status"]] += 1

                self.emp_table.setCellWidget(row, 5, QLineEdit(item.get("check_in_time") or ""))
                self.emp_table.setCellWidget(row, 6, QLineEdit(item.get("check_out_time") or ""))
                rem_txt = item.get("remarks") or ""
                if item.get("capture_source") == "LeaveSync" and "HR" not in rem_txt:
                    rem_txt = f"[HR Leave] {rem_txt}".strip()
                self.emp_table.setCellWidget(row, 7, QLineEdit(rem_txt))

            tot = len(records)
            rate = round((counts[AttendanceStatus.PRESENT] / tot * 100), 1) if tot > 0 else 0.0
            self.emp_kpi_summary.setText(
                f"Total: {tot} | Present: {counts[AttendanceStatus.PRESENT]} | "
                f"Absent: {counts[AttendanceStatus.ABSENT]} | Late: {counts[AttendanceStatus.LATE]} | "
                f"Leave: {counts[AttendanceStatus.LEAVE]} | Excused: {counts[AttendanceStatus.EXCUSED]} | Rate: {rate}%"
            )
        finally:
            db.close()

    def _bulk_set_employee_table_status(self, status: str):
        for r in range(self.emp_table.rowCount()):
            combo = self.emp_table.cellWidget(r, 4)
            if isinstance(combo, QComboBox):
                idx = combo.findText(status)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

    def _on_save_employee_attendance(self):
        etype = self.emp_type_combo.currentData() or "teacher"
        qd = self.emp_date_edit.date()
        att_date = date(qd.year(), qd.month(), qd.day())

        records = []
        id_key = "teacher_id" if etype == "teacher" else "staff_id"
        for r in range(self.emp_table.rowCount()):
            emp = self.employee_rows_data[r]["teacher" if etype == "teacher" else "staff"]
            combo = self.emp_table.cellWidget(r, 4)
            cin = self.emp_table.cellWidget(r, 5)
            cout = self.emp_table.cellWidget(r, 6)
            rem = self.emp_table.cellWidget(r, 7)
            records.append({
                id_key: emp.id,
                "date": att_date,
                "status": combo.currentText() if isinstance(combo, QComboBox) else AttendanceStatus.PRESENT,
                "check_in_time": cin.text() if isinstance(cin, QLineEdit) else "",
                "check_out_time": cout.text() if isinstance(cout, QLineEdit) else "",
                "remarks": rem.text() if isinstance(rem, QLineEdit) else "",
            })

        db: Session = SessionLocal()
        try:
            if etype == "teacher":
                ok, msg = AttendanceService.mark_teacher_attendance(db, att_date, records)
            else:
                ok, msg = AttendanceService.mark_staff_attendance(db, att_date, records)
            if ok:
                QMessageBox.information(self, "Employee Attendance Saved", msg)
                self._load_employee_roster()
            else:
                QMessageBox.warning(self, "Validation", msg)
        except PermissionError as exc:
            QMessageBox.warning(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _on_sync_hr_leaves(self):
        qd = self.emp_date_edit.date()
        att_date = date(qd.year(), qd.month(), qd.day())
        start_d = date(att_date.year, att_date.month, 1)
        db: Session = SessionLocal()
        try:
            ok, synced, msg = AttendanceService.sync_approved_hr_leaves_to_attendance(
                db, start_date=start_d, end_date=att_date
            )
            QMessageBox.information(self, "HR Leave Sync", msg)
            self._load_employee_roster()
        except PermissionError as exc:
            QMessageBox.warning(self, "Access Denied", str(exc))
        finally:
            db.close()

    # -------------------- TAB 3: MONTHLY / RANGE / HISTORY --------------------
    def _on_report_target_changed(self):
        ttype = self.rep_target_combo.currentData() or "student"
        db: Session = SessionLocal()
        try:
            self.rep_scope_combo.clear()
            self.rep_person_combo.clear()
            self.rep_person_combo.addItem("All / Summary", None)
            if ttype == "student":
                for c in AcademicRepository.get_classes(db):
                    self.rep_scope_combo.addItem(c.name, c.id)
                for s in db.query(Student).filter(Student.is_deleted == False).order_by(Student.full_name.asc()).limit(250).all():
                    self.rep_person_combo.addItem(f"{s.full_name} ({s.student_id})", s.id)
            elif ttype == "teacher":
                self.rep_scope_combo.addItem("All Departments", None)
                for d in db.query(Department).filter(Department.is_deleted == False).order_by(Department.name.asc()).all():
                    self.rep_scope_combo.addItem(d.name, d.id)
                for t in db.query(Teacher).filter(Teacher.is_deleted == False).order_by(Teacher.full_name.asc()).all():
                    self.rep_person_combo.addItem(f"{t.full_name} ({t.employee_id})", t.id)
            else:
                self.rep_scope_combo.addItem("All Departments", None)
                for d in db.query(Department).filter(Department.is_deleted == False).order_by(Department.name.asc()).all():
                    self.rep_scope_combo.addItem(d.name, d.id)
                for s in db.query(Staff).filter(Staff.is_deleted == False).order_by(Staff.full_name.asc()).all():
                    self.rep_person_combo.addItem(f"{s.full_name} ({s.employee_id})", s.id)
        finally:
            db.close()

    def _on_run_history_report(self):
        ttype = self.rep_target_combo.currentData() or "student"
        mode = self.rep_mode_combo.currentText()
        scope_id = self.rep_scope_combo.currentData()
        person_id = self.rep_person_combo.currentData()
        s_q = self.rep_start_date.date()
        e_q = self.rep_end_date.date()
        s_date = date(s_q.year(), s_q.month(), s_q.day())
        e_date = date(e_q.year(), e_q.month(), e_q.day())

        db: Session = SessionLocal()
        try:
            if mode == "Monthly Summary":
                if ttype == "student":
                    if not scope_id:
                        self.rep_summary_lbl.setText("Please select a Class for Monthly Student Register.")
                        return
                    data = AttendanceRepository.get_monthly_student_register(db, scope_id, s_date.year, s_date.month)
                    reg = data["register"]
                    self.rep_table.setColumnCount(8)
                    self.rep_table.setHorizontalHeaderLabels(["Roll", "Student ID", "Name", "Present", "Absent", "Late", "Leave/Ex", "Attendance %"])
                    self.rep_table.setRowCount(len(reg))
                    for r_idx, row in enumerate(reg):
                        stu = row["student"]
                        self.rep_table.setItem(r_idx, 0, QTableWidgetItem(str(stu.roll_number)))
                        self.rep_table.setItem(r_idx, 1, QTableWidgetItem(stu.student_id))
                        self.rep_table.setItem(r_idx, 2, QTableWidgetItem(stu.full_name))
                        self.rep_table.setItem(r_idx, 3, QTableWidgetItem(str(row["present_count"])))
                        self.rep_table.setItem(r_idx, 4, QTableWidgetItem(str(row["absent_count"])))
                        self.rep_table.setItem(r_idx, 5, QTableWidgetItem(str(row["late_count"])))
                        self.rep_table.setItem(r_idx, 6, QTableWidgetItem(f"{row['leave_count']} / {row['excused_count']}"))
                        self.rep_table.setItem(r_idx, 7, QTableWidgetItem(f"{row['percentage']}%"))
                    self.rep_summary_lbl.setText(f"Monthly Student Summary ({s_date.year}-{s_date.month:02d}): {len(reg)} student(s)")
                else:
                    data = AttendanceRepository.get_monthly_employee_register(db, ttype, s_date.year, s_date.month, department_id=scope_id)
                    reg = data["register"]
                    self.rep_table.setColumnCount(8)
                    self.rep_table.setHorizontalHeaderLabels(["Employee ID", "Name", "Department", "Present", "Absent", "Late", "Leave/Ex", "Attendance %"])
                    self.rep_table.setRowCount(len(reg))
                    for r_idx, row in enumerate(reg):
                        emp = row["employee"]
                        self.rep_table.setItem(r_idx, 0, QTableWidgetItem(emp.employee_id))
                        self.rep_table.setItem(r_idx, 1, QTableWidgetItem(emp.full_name))
                        self.rep_table.setItem(r_idx, 2, QTableWidgetItem(emp.department.name if emp.department else "-"))
                        self.rep_table.setItem(r_idx, 3, QTableWidgetItem(str(row["present_count"])))
                        self.rep_table.setItem(r_idx, 4, QTableWidgetItem(str(row["absent_count"])))
                        self.rep_table.setItem(r_idx, 5, QTableWidgetItem(str(row["late_count"])))
                        self.rep_table.setItem(r_idx, 6, QTableWidgetItem(f"{row['leave_count']} / {row['excused_count']}"))
                        self.rep_table.setItem(r_idx, 7, QTableWidgetItem(f"{row['percentage']}%"))
                    self.rep_summary_lbl.setText(f"Monthly {ttype.capitalize()} Summary ({s_date.year}-{s_date.month:02d}): {len(reg)} record(s)")

            elif mode == "Date Range Log":
                rep = AttendanceService.get_date_range_report(
                    db,
                    target_type=ttype,
                    start_date=s_date,
                    end_date=e_date,
                    class_id=scope_id if ttype == "student" else None,
                    department_id=scope_id if ttype != "student" else None,
                    entity_pk=person_id,
                )
                rows = rep["records"]
                self.rep_table.setColumnCount(7)
                self.rep_table.setHorizontalHeaderLabels(["Date", "ID", "Name", "Status", "Check-In", "Source", "Remarks"])
                self.rep_table.setRowCount(len(rows))
                for idx, rec in enumerate(rows):
                    subj = rec.student if ttype == "student" else (rec.teacher if ttype == "teacher" else rec.staff)
                    code = subj.student_id if ttype == "student" else (subj.employee_id if subj else "-")
                    self.rep_table.setItem(idx, 0, QTableWidgetItem(rec.date.isoformat()))
                    self.rep_table.setItem(idx, 1, QTableWidgetItem(code))
                    self.rep_table.setItem(idx, 2, QTableWidgetItem(subj.full_name if subj else "-"))
                    self.rep_table.setItem(idx, 3, QTableWidgetItem(rec.status))
                    self.rep_table.setItem(idx, 4, QTableWidgetItem(rec.check_in_time or "-"))
                    self.rep_table.setItem(idx, 5, QTableWidgetItem(rec.capture_source or "Manual"))
                    self.rep_table.setItem(idx, 6, QTableWidgetItem(rec.remarks or ""))
                self.rep_summary_lbl.setText(
                    f"Date Range ({s_date} -> {e_date}) | Records: {rep['total']} | "
                    f"P:{rep['present']} A:{rep['absent']} L:{rep['late']} Lv:{rep['leave']} Ex:{rep['excused']} | "
                    f"Strict Rate: {rep['percentage']}% (Effective: {rep['effective_percentage']}%)"
                )

            else:  # Individual History
                if not person_id:
                    self.rep_summary_lbl.setText("Please select a specific Individual for Individual History.")
                    return
                if ttype == "student":
                    hist = AttendanceRepository.get_student_individual_history(db, person_id, start_date=s_date, end_date=e_date)
                    person_name = hist["student"].full_name if hist["student"] else str(person_id)
                else:
                    hist = AttendanceRepository.get_employee_individual_history(db, ttype, person_id, start_date=s_date, end_date=e_date)
                    person_name = hist["employee"].full_name if hist["employee"] else str(person_id)

                rows = hist["records"]
                self.rep_table.setColumnCount(7)
                self.rep_table.setHorizontalHeaderLabels(["Date", "Status", "Check-In", "Check-Out", "Source", "Edited", "Remarks"])
                self.rep_table.setRowCount(len(rows))
                for idx, rec in enumerate(rows):
                    self.rep_table.setItem(idx, 0, QTableWidgetItem(rec.date.isoformat()))
                    self.rep_table.setItem(idx, 1, QTableWidgetItem(rec.status))
                    self.rep_table.setItem(idx, 2, QTableWidgetItem(rec.check_in_time or "-"))
                    self.rep_table.setItem(idx, 3, QTableWidgetItem(getattr(rec, "check_out_time", None) or "-"))
                    self.rep_table.setItem(idx, 4, QTableWidgetItem(rec.capture_source or "Manual"))
                    self.rep_table.setItem(idx, 5, QTableWidgetItem("Yes" if rec.is_edited else "No"))
                    self.rep_table.setItem(idx, 6, QTableWidgetItem(rec.remarks or rec.excuse_reason or ""))
                self.rep_summary_lbl.setText(
                    f"Individual History: {person_name} | Total Days: {hist['total_days']} | "
                    f"P:{hist['present']} A:{hist['absent']} L:{hist['late']} Lv:{hist['leave']} Ex:{hist['excused']} | "
                    f"Attendance %: {hist['percentage']}% (Effective: {hist['effective_percentage']}%)"
                )
        finally:
            db.close()

    def _on_export_report_excel(self):
        ttype = self.rep_target_combo.currentData() or "student"
        scope_id = self.rep_scope_combo.currentData()
        s_q = self.rep_start_date.date()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Monthly Register (.xlsx)",
            f"Attendance_{ttype}_{s_q.year()}_{s_q.month():02d}.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        db: Session = SessionLocal()
        try:
            if ttype == "student":
                if not scope_id:
                    QMessageBox.warning(self, "Select Class", "Please select a Class first.")
                    return
                AttendanceService.export_monthly_register_excel(db, scope_id, s_q.year(), s_q.month(), path)
            else:
                AttendanceService.export_employee_monthly_register_excel(
                    db, ttype, s_q.year(), s_q.month(), path, department_id=scope_id
                )
            QMessageBox.information(self, "Export Complete", f"Saved register to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))
        finally:
            db.close()

    # -------------------- TAB 4: CORRECTION REQUESTS --------------------
    def _populate_correction_persons(self):
        ttype = self.corr_target_combo.currentData() or "student"
        db: Session = SessionLocal()
        try:
            self.corr_person_combo.clear()
            if ttype == "student":
                for s in db.query(Student).filter(Student.is_deleted == False).order_by(Student.full_name.asc()).limit(250).all():
                    self.corr_person_combo.addItem(f"{s.full_name} ({s.student_id})", s.id)
            elif ttype == "teacher":
                for t in db.query(Teacher).filter(Teacher.is_deleted == False).order_by(Teacher.full_name.asc()).all():
                    self.corr_person_combo.addItem(f"{t.full_name} ({t.employee_id})", t.id)
            else:
                for st in db.query(Staff).filter(Staff.is_deleted == False).order_by(Staff.full_name.asc()).all():
                    self.corr_person_combo.addItem(f"{st.full_name} ({st.employee_id})", st.id)
        finally:
            db.close()

    def _load_correction_requests(self):
        filt = self.corr_filter_combo.currentText()
        status_arg = None if filt == "All" else filt
        db: Session = SessionLocal()
        try:
            rows = AttendanceRepository.list_correction_requests(db, approval_status=status_arg)
            self.corr_table.setRowCount(len(rows))
            for idx, req in enumerate(rows):
                person = (
                    req.student.full_name if req.student else
                    req.teacher.full_name if req.teacher else
                    req.staff.full_name if req.staff else "-"
                )
                self.corr_table.setItem(idx, 0, QTableWidgetItem(str(req.id)))
                self.corr_table.setItem(idx, 1, QTableWidgetItem(req.target_type.capitalize()))
                self.corr_table.setItem(idx, 2, QTableWidgetItem(person))
                self.corr_table.setItem(idx, 3, QTableWidgetItem(req.attendance_date.isoformat()))
                self.corr_table.setItem(idx, 4, QTableWidgetItem(f"{req.original_status} -> {req.requested_status}"))
                self.corr_table.setItem(idx, 5, QTableWidgetItem(req.reason))
                self.corr_table.setItem(idx, 6, QTableWidgetItem(req.approval_status))
                self.corr_table.setItem(idx, 7, QTableWidgetItem(req.reviewed_by or "-"))
        finally:
            db.close()

    def _on_submit_correction(self):
        ttype = self.corr_target_combo.currentData()
        person_pk = self.corr_person_combo.currentData()
        if not person_pk:
            QMessageBox.warning(self, "Select Person", "Please select a Student, Teacher, or Staff member.")
            return
        qd = self.corr_date_edit.date()
        att_date = date(qd.year(), qd.month(), qd.day())
        req_status = self.corr_status_combo.currentText()
        cin = self.corr_cin_edit.text().strip() or None
        reason = self.corr_reason_edit.toPlainText().strip()

        db: Session = SessionLocal()
        try:
            ok, _, msg = AttendanceService.submit_correction_request(
                db, ttype, person_pk, att_date, req_status, reason, requested_check_in=cin
            )
            if ok:
                QMessageBox.information(self, "Correction Submitted", msg)
                self.corr_reason_edit.clear()
                self._load_correction_requests()
            else:
                QMessageBox.warning(self, "Submission Error", msg)
        except PermissionError as exc:
            QMessageBox.warning(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _on_review_correction(self, approve: bool):
        row = self.corr_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Select Request", "Please select a correction request row to review.")
            return
        req_id = int(self.corr_table.item(row, 0).text())
        db: Session = SessionLocal()
        try:
            ok, _, msg = AttendanceService.review_correction_request(db, req_id, approve=approve)
            if ok:
                QMessageBox.information(self, "Correction Reviewed", msg)
                self._load_correction_requests()
                self._load_student_roster()
                self._load_employee_roster()
            else:
                QMessageBox.warning(self, "Review Failed", msg)
        except PermissionError as exc:
            QMessageBox.warning(self, "Access Denied", str(exc))
        finally:
            db.close()

    # -------------------- TAB 5: ANALYTICS --------------------
    def _load_analytics(self):
        sq = self.ana_start.date()
        eq = self.ana_end.date()
        s_date = date(sq.year(), sq.month(), sq.day())
        e_date = date(eq.year(), eq.month(), eq.day())
        thresh = float(self.ana_threshold.value())

        db: Session = SessionLocal()
        try:
            data = AttendanceService.get_attendance_analytics(
                db, start_date=s_date, end_date=e_date, chronic_threshold_pct=thresh
            )
            ov = data["overall"]
            st = data["students"]
            tc = data["teachers"]
            sf = data["staff"]
            self.ana_kpi_lbl.setText(
                f"Period: {data['period']['start_date']} to {data['period']['end_date']}   |   "
                f"Overall: {ov['attendance_rate']}% ({ov['total']} records)   |   "
                f"Students: {st['attendance_rate']}%   |   Teachers: {tc['attendance_rate']}%   |   "
                f"Staff: {sf['attendance_rate']}%   |   Pending Corrections: {data['pending_corrections']}"
            )

            breakdown_rows = []
            for cb in data["class_breakdown"]:
                breakdown_rows.append((f"[Class] {cb['class_name']}", cb))
            for db_item in data["department_breakdown"]:
                breakdown_rows.append((f"[Dept] {db_item['department_name']}", db_item))

            self.ana_breakdown_table.setRowCount(len(breakdown_rows))
            for r_idx, (label, item) in enumerate(breakdown_rows):
                self.ana_breakdown_table.setItem(r_idx, 0, QTableWidgetItem(label))
                self.ana_breakdown_table.setItem(r_idx, 1, QTableWidgetItem(str(item["total"])))
                self.ana_breakdown_table.setItem(r_idx, 2, QTableWidgetItem(str(item["present"])))
                self.ana_breakdown_table.setItem(r_idx, 3, QTableWidgetItem(str(item["absent"])))
                self.ana_breakdown_table.setItem(r_idx, 4, QTableWidgetItem(str(item["late"])))
                self.ana_breakdown_table.setItem(r_idx, 5, QTableWidgetItem(f"{item['leave']} / {item['excused']}"))
                self.ana_breakdown_table.setItem(r_idx, 6, QTableWidgetItem(f"{item['attendance_rate']}%"))

            risk_rows = []
            for c_stu in data["chronic_absentee_students"]:
                risk_rows.append((
                    "Student", c_stu["student_code"], c_stu["full_name"],
                    c_stu["class_name"], str(c_stu["total"]), f"{c_stu['attendance_rate']}%"
                ))
            for c_emp in data["at_risk_employees"]:
                risk_rows.append((
                    c_emp["employee_type"].capitalize(), c_emp["employee_id"], c_emp["full_name"],
                    c_emp["department"], str(c_emp["total"]), f"{c_emp['attendance_rate']}%"
                ))

            self.ana_risk_table.setRowCount(len(risk_rows))
            for r_idx, tup in enumerate(risk_rows):
                for c_idx, val in enumerate(tup):
                    self.ana_risk_table.setItem(r_idx, c_idx, QTableWidgetItem(val))
        except PermissionError:
            self.ana_kpi_lbl.setText("Analytics view restricted by current user permissions.")
        finally:
            db.close()

    # -------------------- TAB 6: OPTIONAL CAPTURE INTEGRATION --------------------
    def _load_integration_state(self):
        db: Session = SessionLocal()
        try:
            devices = AttendanceIntegrationManager.list_devices(db)
            self.dev_table.setRowCount(len(devices))
            for idx, d in enumerate(devices):
                self.dev_table.setItem(idx, 0, QTableWidgetItem(d.device_code))
                self.dev_table.setItem(idx, 1, QTableWidgetItem(d.name))
                self.dev_table.setItem(idx, 2, QTableWidgetItem(d.adapter_type))
                self.dev_table.setItem(idx, 3, QTableWidgetItem(d.connection_mode))
                self.dev_table.setItem(idx, 4, QTableWidgetItem("Yes" if d.is_enabled else "No"))

            logs = AttendanceIntegrationManager.get_recent_scan_logs(db, limit=40)
            self.scan_log_table.setRowCount(len(logs))
            for idx, lg in enumerate(logs):
                self.scan_log_table.setItem(idx, 0, QTableWidgetItem(lg.scan_timestamp.strftime("%Y-%m-%d %H:%M:%S") if lg.scan_timestamp else "-"))
                self.scan_log_table.setItem(idx, 1, QTableWidgetItem(lg.adapter_type))
                self.scan_log_table.setItem(idx, 2, QTableWidgetItem(lg.raw_identifier))
                self.scan_log_table.setItem(idx, 3, QTableWidgetItem(lg.direction))
                self.scan_log_table.setItem(idx, 4, QTableWidgetItem(lg.processing_status))
                self.scan_log_table.setItem(idx, 5, QTableWidgetItem(lg.notes or ""))
        finally:
            db.close()

    def _on_process_scan(self):
        adapter = self.scan_adapter_combo.currentText()
        token = self.scan_identifier_edit.text().strip()
        direction = self.scan_direction_combo.currentText()
        conf = float(self.scan_conf_spin.value())

        db: Session = SessionLocal()
        try:
            ok, _, msg = AttendanceService.process_scan_event(
                db, adapter_type=adapter, raw_identifier=token, direction=direction, confidence_score=conf
            )
            if ok:
                QMessageBox.information(self, "Scan Applied", msg)
                self.scan_identifier_edit.clear()
                self._load_student_roster()
                self._load_employee_roster()
            else:
                QMessageBox.warning(self, "Scan Result", msg)
            self._load_integration_state()
        except PermissionError as exc:
            QMessageBox.warning(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _on_register_device(self):
        code = self.dev_code_edit.text().strip()
        name = self.dev_name_edit.text().strip()
        adapter = self.dev_adapter_combo.currentText()
        mode = self.dev_mode_combo.currentText()
        if not code or not name:
            QMessageBox.warning(self, "Missing Input", "Device code and name are required.")
            return
        db: Session = SessionLocal()
        try:
            ok, _, msg = AttendanceService.register_capture_device(
                db, device_code=code, name=name, adapter_type=adapter, connection_mode=mode
            )
            if ok:
                QMessageBox.information(self, "Device Registered", msg)
                self.dev_code_edit.clear()
                self.dev_name_edit.clear()
                self._load_integration_state()
            else:
                QMessageBox.warning(self, "Registration Error", msg)
        except PermissionError as exc:
            QMessageBox.warning(self, "Access Denied", str(exc))
        finally:
            db.close()
