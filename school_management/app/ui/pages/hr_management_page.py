"""
EduManage Pro - Enterprise HR Management Workspace (PySide6)
Unified workspace covering:
1. Employee Directory (Teachers + Office Staff, Accountant, Receptionist, Librarian, Security, Support)
2. Leave Management & Approval Workflow
3. Employee Attendance (Teachers & Non-Teaching Staff)
4. Contracts & Lifecycle Actions (Promote, Transfer, Status Change)
5. Performance Evaluations
6. Confidential Payroll & Salary Control (hidden for unauthorized roles)
7. HR Reports Center (PDF / Excel)
"""

from datetime import date
from typing import List, Tuple

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.database.connection import SessionLocal
from app.models.staff import EmployeeStatus, STAFF_ROLE_CATALOG
from app.reports.hr_reports import HRReportsGenerator
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.staff_repository import StaffRepository
from app.services.hr_service import HRSecurityGuard, HRService
from app.ui.dialogs.hr_profile_dialog import HRProfileDialog
from app.ui.dialogs.staff_form_dialog import StaffFormDialog
from app.ui.dialogs.teacher_form_dialog import TeacherFormDialog


class HRManagementPage(QWidget):
    """Comprehensive, permission-aware HR & Payroll Management console."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._att_row_refs: List[Tuple[str, int]] = []
        self._build_ui()
        self.refresh_all()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # Header
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Human Resources & Employee Lifecycle Management")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #f8fafc;")
        subtitle = QLabel(
            "Teachers & Staff Directory • Contracts • Leave Approvals • Attendance • Evaluations • Confidential Payroll"
        )
        subtitle.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box)
        header_row.addStretch()

        btn_add_teacher = QPushButton("➕ Onboard Teacher")
        btn_add_teacher.setStyleSheet(
            "background-color: #059669; color: white; padding: 8px 14px; font-weight: bold; border-radius: 6px;"
        )
        btn_add_teacher.clicked.connect(self._onboard_teacher)

        btn_add_staff = QPushButton("➕ Onboard Staff")
        btn_add_staff.setStyleSheet(
            "background-color: #4f46e5; color: white; padding: 8px 14px; font-weight: bold; border-radius: 6px;"
        )
        btn_add_staff.clicked.connect(self._onboard_staff)

        header_row.addWidget(btn_add_teacher)
        header_row.addWidget(btn_add_staff)
        root.addLayout(header_row)

        # KPI Strip
        kpi_row = QHBoxLayout()
        self.kpi_teachers = self._make_kpi("Total Faculty", "0", "#10b981")
        self.kpi_staff = self._make_kpi("Total Staff", "0", "#6366f1")
        self.kpi_leaves = self._make_kpi("Pending Leaves", "0", "#f59e0b")
        self.kpi_contracts = self._make_kpi("Active Contracts", "0", "#3b82f6")
        self.kpi_payroll = self._make_kpi("Monthly Payroll", "Confidential", "#06b6d4")
        for card in (self.kpi_teachers, self.kpi_staff, self.kpi_leaves, self.kpi_contracts, self.kpi_payroll):
            kpi_row.addWidget(card)
        root.addLayout(kpi_row)

        # Tabs
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, stretch=1)

        self.tab_directory = QWidget()
        self._build_directory_tab()
        self.tabs.addTab(self.tab_directory, "👥 Employee Directory")

        self.tab_leave = QWidget()
        self._build_leave_tab()
        self.tabs.addTab(self.tab_leave, "🏖 Leave Requests & Approvals")

        self.tab_attendance = QWidget()
        self._build_attendance_tab()
        self.tabs.addTab(self.tab_attendance, "📅 Employee Attendance")

        self.tab_contracts = QWidget()
        self._build_contracts_tab()
        self.tabs.addTab(self.tab_contracts, "📄 Contracts & Lifecycle")

        self.tab_evals = QWidget()
        self._build_evaluations_tab()
        self.tabs.addTab(self.tab_evals, "⭐ Performance Evaluations")

        self.tab_payroll = QWidget()
        self._build_payroll_tab()
        self._payroll_tab_index = self.tabs.addTab(self.tab_payroll, "💰 Payroll & Salary Control")

        self.tab_reports = QWidget()
        self._build_reports_tab()
        self.tabs.addTab(self.tab_reports, "📑 HR Reports")

    def _make_kpi(self, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"background-color: #1e293b; border: 1px solid #334155; border-left: 4px solid {color}; border-radius: 6px; padding: 8px;"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(6, 4, 6, 4)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600; text-transform: uppercase;")
        v_lbl = QLabel(value)
        v_lbl.setFont(QFont("Segoe UI", 15, QFont.Bold))
        v_lbl.setStyleSheet(f"color: {color};")
        lay.addWidget(t_lbl)
        lay.addWidget(v_lbl)
        card.value_lbl = v_lbl
        return card

    # ------------------------------------------------------------------
    # Tab Builders
    # ------------------------------------------------------------------
    def _build_directory_tab(self):
        lay = QVBoxLayout(self.tab_directory)
        flt = QHBoxLayout()
        self.dir_search = QLineEdit()
        self.dir_search.setPlaceholderText("🔍 Search name, employee ID, phone, role or subject...")
        self.dir_search.textChanged.connect(self._load_directory)

        self.dir_category = QComboBox()
        self.dir_category.addItems(["All Employees", "Teachers Only", "Staff Only"])
        self.dir_category.currentIndexChanged.connect(self._load_directory)

        self.dir_role = QComboBox()
        self.dir_role.addItem("All Staff Roles", None)
        for role_name in STAFF_ROLE_CATALOG:
            self.dir_role.addItem(role_name, role_name)
        self.dir_role.currentIndexChanged.connect(self._load_directory)

        self.dir_status = QComboBox()
        self.dir_status.addItem("All Statuses", None)
        for st in EmployeeStatus.ALL:
            self.dir_status.addItem(EmployeeStatus.LABELS.get(st, st), st)
        self.dir_status.currentIndexChanged.connect(self._load_directory)

        flt.addWidget(self.dir_search, stretch=2)
        flt.addWidget(self.dir_category)
        flt.addWidget(self.dir_role)
        flt.addWidget(self.dir_status)
        lay.addLayout(flt)

        self.tbl_dir = QTableWidget(0, 8)
        self.tbl_dir.setHorizontalHeaderLabels([
            "Category", "Emp ID", "Full Name", "Role / Designation",
            "Department", "Phone", "Status", "360° Profile"
        ])
        self.tbl_dir.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_dir.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        lay.addWidget(self.tbl_dir)

    def _build_leave_tab(self):
        lay = QVBoxLayout(self.tab_leave)
        top = QHBoxLayout()
        self.leave_status_filter = QComboBox()
        self.leave_status_filter.addItems(["All", "Pending", "Approved", "Rejected"])
        self.leave_status_filter.currentIndexChanged.connect(self._load_leaves)
        btn_refresh = QPushButton("🔄 Refresh Queue")
        btn_refresh.clicked.connect(self._load_leaves)
        top.addWidget(QLabel("Status Filter:"))
        top.addWidget(self.leave_status_filter)
        top.addWidget(btn_refresh)
        top.addStretch()
        lay.addLayout(top)

        self.tbl_leave_queue = QTableWidget(0, 8)
        self.tbl_leave_queue.setHorizontalHeaderLabels([
            "Req #", "Category", "Employee", "Type", "Dates", "Days", "Status", "Approval Actions"
        ])
        self.tbl_leave_queue.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_leave_queue.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        lay.addWidget(self.tbl_leave_queue)

    def _build_attendance_tab(self):
        lay = QVBoxLayout(self.tab_attendance)
        top = QHBoxLayout()
        self.att_emp_type = QComboBox()
        self.att_emp_type.addItem("Teachers", "teacher")
        self.att_emp_type.addItem("Non-Teaching Staff", "staff")
        self.att_date = QDateEdit(QDate.currentDate())
        self.att_date.setCalendarPopup(True)

        btn_load = QPushButton("Load Roster")
        btn_load.clicked.connect(self._load_attendance_roster)
        btn_save = QPushButton("💾 Save Attendance")
        btn_save.setStyleSheet(
            "background-color: #2563eb; color: white; padding: 6px 14px; font-weight: bold; border-radius: 6px;"
        )
        btn_save.clicked.connect(self._save_attendance)

        top.addWidget(QLabel("Category:"))
        top.addWidget(self.att_emp_type)
        top.addWidget(QLabel("Date:"))
        top.addWidget(self.att_date)
        top.addWidget(btn_load)
        top.addStretch()
        top.addWidget(btn_save)
        lay.addLayout(top)

        self.tbl_att = QTableWidget(0, 5)
        self.tbl_att.setHorizontalHeaderLabels(["Emp ID", "Full Name", "Role / Department", "Status", "Remarks"])
        self.tbl_att.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_att)

    def _build_contracts_tab(self):
        lay = QVBoxLayout(self.tab_contracts)
        self.tbl_contracts = QTableWidget(0, 7)
        self.tbl_contracts.setHorizontalHeaderLabels([
            "Contract #", "Category", "Employee", "Contract Type", "Start Date", "End Date", "Status"
        ])
        self.tbl_contracts.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_contracts)

    def _build_evaluations_tab(self):
        lay = QVBoxLayout(self.tab_evals)
        self.tbl_evals = QTableWidget(0, 7)
        self.tbl_evals.setHorizontalHeaderLabels([
            "Category", "Employee", "Period", "Review Date", "Reviewer", "Overall Score", "Rating Band"
        ])
        self.tbl_evals.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_evals)

    def _build_payroll_tab(self):
        lay = QVBoxLayout(self.tab_payroll)
        info = QLabel("CONFIDENTIAL PAYROLL REGISTER — Restricted to Super Admin, Administrator & Accountant")
        info.setStyleSheet("color: #fbbf24; font-weight: bold; font-size: 12px;")
        lay.addWidget(info)

        self.tbl_payroll = QTableWidget(0, 7)
        self.tbl_payroll.setHorizontalHeaderLabels([
            "Category", "Emp ID", "Full Name", "Role", "Monthly Salary (BDT)", "Bank Details", "Action"
        ])
        self.tbl_payroll.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_payroll)

    def _build_reports_tab(self):
        lay = QVBoxLayout(self.tab_reports)
        card = QFrame()
        card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px;")
        c_lay = QVBoxLayout(card)
        c_lay.addWidget(QLabel("Select HR Report to Export (PDF / Excel):"))

        self.report_selector = QComboBox()
        self._populate_report_selector()
        c_lay.addWidget(self.report_selector)

        btn_row = QHBoxLayout()
        btn_pdf = QPushButton("📄 Export PDF Report")
        btn_pdf.setStyleSheet("background-color: #dc2626; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        btn_pdf.clicked.connect(lambda: self._export_report("pdf"))

        btn_xlsx = QPushButton("📊 Export Excel (.xlsx)")
        btn_xlsx.setStyleSheet("background-color: #059669; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        btn_xlsx.clicked.connect(lambda: self._export_report("xlsx"))

        btn_row.addWidget(btn_pdf)
        btn_row.addWidget(btn_xlsx)
        btn_row.addStretch()
        c_lay.addLayout(btn_row)
        lay.addWidget(card)
        lay.addStretch()

    def _populate_report_selector(self):
        self.report_selector.clear()
        self.report_selector.addItem("Employee Directory Report", "directory")
        self.report_selector.addItem("Leave Requests & Approval Audit", "leave")
        self.report_selector.addItem("Teacher & Staff Attendance Register", "attendance")
        self.report_selector.addItem("Employment Contracts Register", "contracts")
        self.report_selector.addItem("Performance Evaluations Summary", "performance")
        if HRSecurityGuard.can_view_salary(allow_when_no_session=True) and HRSecurityGuard.has_permission(
            "hr.salary.EXPORT", allow_when_no_session=True
        ):
            self.report_selector.addItem("Confidential Monthly Payroll Register", "payroll")

    # ------------------------------------------------------------------
    # Refresh & Loaders
    # ------------------------------------------------------------------
    def refresh_all(self):
        can_salary = HRSecurityGuard.can_view_salary(allow_when_no_session=True)
        self.kpi_payroll.setVisible(can_salary)
        self.tabs.setTabVisible(self._payroll_tab_index, can_salary)
        self._populate_report_selector()

        db = SessionLocal()
        try:
            kpis = HRService.get_hr_kpis(db)
            self.kpi_teachers.value_lbl.setText(str(kpis["total_teachers"]))
            self.kpi_staff.value_lbl.setText(str(kpis["total_staff"]))
            self.kpi_leaves.value_lbl.setText(str(kpis["pending_leaves"]))
            self.kpi_contracts.value_lbl.setText(str(kpis["active_contracts"]))
            if kpis["salary_visible"] and kpis["monthly_payroll"] is not None:
                self.kpi_payroll.value_lbl.setText(f"৳ {kpis['monthly_payroll']:,}")
            else:
                self.kpi_payroll.value_lbl.setText("Restricted")
        finally:
            db.close()

        self._load_directory()
        self._load_leaves()
        self._load_attendance_roster()
        self._load_contracts()
        self._load_evaluations()
        if can_salary:
            self._load_payroll_register()

    def _load_directory(self):
        db = SessionLocal()
        try:
            q = self.dir_search.text().strip()
            cat = self.dir_category.currentText()
            role_filter = self.dir_role.currentData()
            status = self.dir_status.currentData()

            rows = []
            if cat in ("All Employees", "Teachers Only") and not role_filter:
                teachers, _ = StaffRepository.search_and_filter_teachers(
                    db, search_query=q, status=status, per_page=500
                )
                for t in teachers:
                    rows.append((
                        "Teacher",
                        t.id,
                        t.employee_id,
                        t.full_name,
                        f"{t.designation} ({t.primary_subject})",
                        t.department.name if t.department else "-",
                        t.phone,
                        EmployeeStatus.LABELS.get(t.status, t.status),
                    ))
            if cat in ("All Employees", "Staff Only"):
                staff_list, _ = StaffRepository.search_and_filter_staff(
                    db, search_query=q, position=role_filter, status=status, per_page=500
                )
                for s in staff_list:
                    rows.append((
                        "Staff",
                        s.id,
                        s.employee_id,
                        s.full_name,
                        f"{s.position} ({s.shift})",
                        s.department.name if s.department else "-",
                        s.phone,
                        EmployeeStatus.LABELS.get(s.status, s.status),
                    ))

            self.tbl_dir.setRowCount(len(rows))
            for i, (etype, pk, eid, name, role_txt, dept, phone, st_txt) in enumerate(rows):
                self.tbl_dir.setItem(i, 0, QTableWidgetItem(etype))
                self.tbl_dir.setItem(i, 1, QTableWidgetItem(eid))
                self.tbl_dir.setItem(i, 2, QTableWidgetItem(name))
                self.tbl_dir.setItem(i, 3, QTableWidgetItem(role_txt))
                self.tbl_dir.setItem(i, 4, QTableWidgetItem(dept))
                self.tbl_dir.setItem(i, 5, QTableWidgetItem(phone))
                self.tbl_dir.setItem(i, 6, QTableWidgetItem(st_txt))

                btn_profile = QPushButton("📋 HR Profile")
                btn_profile.clicked.connect(
                    lambda checked, et=etype.lower(), p=pk: self._open_hr_profile(et, p)
                )
                self.tbl_dir.setCellWidget(i, 7, btn_profile)
        finally:
            db.close()

    def _load_leaves(self):
        db = SessionLocal()
        try:
            st = self.leave_status_filter.currentText()
            reqs = StaffRepository.list_leave_requests(db, status=None if st == "All" else st)
            can_approve = HRSecurityGuard.has_permission("hr.leave.APPROVE", allow_when_no_session=True)

            self.tbl_leave_queue.setRowCount(len(reqs))
            for i, lv in enumerate(reqs):
                emp = lv.teacher if lv.employee_type == "teacher" else lv.staff
                self.tbl_leave_queue.setItem(i, 0, QTableWidgetItem(str(lv.id)))
                self.tbl_leave_queue.setItem(i, 1, QTableWidgetItem(lv.employee_type.capitalize()))
                self.tbl_leave_queue.setItem(i, 2, QTableWidgetItem(emp.full_name if emp else "-"))
                self.tbl_leave_queue.setItem(i, 3, QTableWidgetItem(lv.leave_type))
                self.tbl_leave_queue.setItem(i, 4, QTableWidgetItem(f"{lv.start_date} -> {lv.end_date}"))
                self.tbl_leave_queue.setItem(i, 5, QTableWidgetItem(str(lv.total_days)))
                self.tbl_leave_queue.setItem(i, 6, QTableWidgetItem(lv.status))

                act_w = QWidget()
                act_l = QHBoxLayout(act_w)
                act_l.setContentsMargins(2, 2, 2, 2)
                if lv.status == "Pending" and can_approve:
                    b_app = QPushButton("✓ Approve")
                    b_app.setStyleSheet("background-color: #059669; color: white; padding: 3px 8px;")
                    b_app.clicked.connect(lambda checked, rid=lv.id: self._approve_leave(rid))
                    b_rej = QPushButton("✕ Reject")
                    b_rej.setStyleSheet("background-color: #dc2626; color: white; padding: 3px 8px;")
                    b_rej.clicked.connect(lambda checked, rid=lv.id: self._reject_leave(rid))
                    act_l.addWidget(b_app)
                    act_l.addWidget(b_rej)
                else:
                    act_l.addWidget(QLabel(lv.reviewed_by or lv.status))
                self.tbl_leave_queue.setCellWidget(i, 7, act_w)
        finally:
            db.close()

    def _load_attendance_roster(self):
        db = SessionLocal()
        try:
            etype = self.att_emp_type.currentData()
            att_date = self.att_date.date().toPython()
            self._att_row_refs = []

            if etype == "teacher":
                employees, _ = StaffRepository.search_and_filter_teachers(db, status="active", per_page=500)
                existing = AttendanceRepository.get_teacher_attendance_by_date(db, att_date)
            else:
                employees, _ = StaffRepository.search_and_filter_staff(db, status="active", per_page=500)
                existing = StaffRepository.get_staff_attendance_by_date(db, att_date)

            self.tbl_att.setRowCount(len(employees))
            for i, emp in enumerate(employees):
                self._att_row_refs.append((etype, emp.id))
                role_txt = emp.designation if etype == "teacher" else emp.position
                dept_txt = emp.department.name if emp.department else "-"
                rec = existing.get(emp.id)

                self.tbl_att.setItem(i, 0, QTableWidgetItem(emp.employee_id))
                self.tbl_att.setItem(i, 1, QTableWidgetItem(emp.full_name))
                self.tbl_att.setItem(i, 2, QTableWidgetItem(f"{role_txt} ({dept_txt})"))

                cb = QComboBox()
                cb.addItems(["Present", "Absent", "Late", "Leave"])
                if rec:
                    cb.setCurrentText(rec.status)
                self.tbl_att.setCellWidget(i, 3, cb)
                self.tbl_att.setItem(i, 4, QTableWidgetItem(rec.remarks if rec and rec.remarks else ""))
        finally:
            db.close()

    def _save_attendance(self):
        etype = self.att_emp_type.currentData()
        att_date = self.att_date.date().toPython()
        records = []
        id_key = "teacher_id" if etype == "teacher" else "staff_id"

        for i, (_, emp_pk) in enumerate(self._att_row_refs):
            cb = self.tbl_att.cellWidget(i, 3)
            rem_item = self.tbl_att.item(i, 4)
            records.append({
                id_key: emp_pk,
                "date": att_date,
                "status": cb.currentText() if cb else "Present",
                "remarks": rem_item.text().strip() if rem_item else None,
            })

        db = SessionLocal()
        try:
            ok, msg = HRService.mark_employee_attendance(db, etype, att_date, records)
            if ok:
                QMessageBox.information(self, "Attendance Saved", msg)
            else:
                QMessageBox.warning(self, "Validation Error", msg)
        except PermissionError as exc:
            QMessageBox.warning(self, "Permission Denied", str(exc))
        finally:
            db.close()

    def _load_contracts(self):
        db = SessionLocal()
        try:
            contracts = StaffRepository.list_contracts(db)
            self.tbl_contracts.setRowCount(len(contracts))
            for i, c in enumerate(contracts):
                emp = c.teacher if c.employee_type == "teacher" else c.staff
                self.tbl_contracts.setItem(i, 0, QTableWidgetItem(c.contract_number))
                self.tbl_contracts.setItem(i, 1, QTableWidgetItem(c.employee_type.capitalize()))
                self.tbl_contracts.setItem(i, 2, QTableWidgetItem(emp.full_name if emp else "-"))
                self.tbl_contracts.setItem(i, 3, QTableWidgetItem(c.contract_type))
                self.tbl_contracts.setItem(i, 4, QTableWidgetItem(c.start_date.isoformat()))
                self.tbl_contracts.setItem(i, 5, QTableWidgetItem(c.end_date.isoformat() if c.end_date else "Open-Ended"))
                self.tbl_contracts.setItem(i, 6, QTableWidgetItem(c.status))
        finally:
            db.close()

    def _load_evaluations(self):
        db = SessionLocal()
        try:
            evals = StaffRepository.list_evaluations(db)
            self.tbl_evals.setRowCount(len(evals))
            for i, ev in enumerate(evals):
                emp = ev.teacher if ev.employee_type == "teacher" else ev.staff
                self.tbl_evals.setItem(i, 0, QTableWidgetItem(ev.employee_type.capitalize()))
                self.tbl_evals.setItem(i, 1, QTableWidgetItem(emp.full_name if emp else "-"))
                self.tbl_evals.setItem(i, 2, QTableWidgetItem(ev.review_period))
                self.tbl_evals.setItem(i, 3, QTableWidgetItem(ev.review_date.isoformat()))
                self.tbl_evals.setItem(i, 4, QTableWidgetItem(ev.reviewer_name))
                self.tbl_evals.setItem(i, 5, QTableWidgetItem(f"{ev.overall_rating:.2f} / 5.0"))
                self.tbl_evals.setItem(i, 6, QTableWidgetItem(ev.rating_band))
        finally:
            db.close()

    def _load_payroll_register(self):
        if not HRSecurityGuard.can_view_salary(allow_when_no_session=True):
            self.tbl_payroll.setRowCount(0)
            return
        db = SessionLocal()
        try:
            teachers, _ = StaffRepository.search_and_filter_teachers(db, per_page=500)
            staff_list, _ = StaffRepository.search_and_filter_staff(db, per_page=500)
            entries = []
            for t in teachers:
                entries.append(("teacher", t.id, t.employee_id, t.full_name, t.designation, t.salary, f"{t.bank_name or '-'} / {t.bank_account_no or '-'}"))
            for s in staff_list:
                entries.append(("staff", s.id, s.employee_id, s.full_name, s.position, s.salary, f"{s.bank_name or '-'} / {s.bank_account_no or '-'}"))

            self.tbl_payroll.setRowCount(len(entries))
            for i, (et, pk, eid, name, role, sal, bank) in enumerate(entries):
                self.tbl_payroll.setItem(i, 0, QTableWidgetItem(et.capitalize()))
                self.tbl_payroll.setItem(i, 1, QTableWidgetItem(eid))
                self.tbl_payroll.setItem(i, 2, QTableWidgetItem(name))
                self.tbl_payroll.setItem(i, 3, QTableWidgetItem(role))
                self.tbl_payroll.setItem(i, 4, QTableWidgetItem(f"৳ {sal:,}"))
                self.tbl_payroll.setItem(i, 5, QTableWidgetItem(bank))

                btn = QPushButton("Manage Salary")
                btn.clicked.connect(lambda checked, e_t=et, p=pk: self._open_hr_profile(e_t, p))
                self.tbl_payroll.setCellWidget(i, 6, btn)
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _open_hr_profile(self, employee_type: str, employee_pk: int):
        dlg = HRProfileDialog(self, employee_type=employee_type, employee_pk=employee_pk)
        dlg.exec()
        self.refresh_all()

    def _onboard_teacher(self):
        if TeacherFormDialog(self).exec() == TeacherFormDialog.Accepted:
            self.refresh_all()

    def _onboard_staff(self):
        if StaffFormDialog(self).exec() == StaffFormDialog.Accepted:
            self.refresh_all()

    def _approve_leave(self, req_id: int):
        db = SessionLocal()
        try:
            ok, _, msg = HRService.approve_leave_request(db, req_id)
            if ok:
                QMessageBox.information(self, "Approved", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Notice", msg)
        except PermissionError as exc:
            QMessageBox.warning(self, "Permission Denied", str(exc))
        finally:
            db.close()

    def _reject_leave(self, req_id: int):
        db = SessionLocal()
        try:
            ok, _, msg = HRService.reject_leave_request(db, req_id, remarks="Rejected by HR Admin")
            if ok:
                QMessageBox.information(self, "Rejected", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Notice", msg)
        except PermissionError as exc:
            QMessageBox.warning(self, "Permission Denied", str(exc))
        finally:
            db.close()

    def _export_report(self, fmt: str):
        report_key = self.report_selector.currentData()
        ext = "pdf" if fmt == "pdf" else "xlsx"
        file_filter = "PDF Files (*.pdf)" if fmt == "pdf" else "Excel Files (*.xlsx)"
        default_name = f"HR_{report_key}_{date.today().isoformat()}.{ext}"
        path, _ = QFileDialog.getSaveFileName(self, "Save HR Report", default_name, file_filter)
        if not path:
            return

        db = SessionLocal()
        try:
            if report_key == "directory":
                HRReportsGenerator.generate_employee_directory_report(db, path, fmt=fmt)
            elif report_key == "leave":
                HRReportsGenerator.generate_leave_report(db, path, fmt=fmt)
            elif report_key == "attendance":
                HRReportsGenerator.generate_attendance_report(db, path, fmt=fmt)
            elif report_key == "contracts":
                HRReportsGenerator.generate_contracts_report(db, path, fmt=fmt)
            elif report_key == "performance":
                HRReportsGenerator.generate_performance_report(db, path, fmt=fmt)
            elif report_key == "payroll":
                HRReportsGenerator.generate_payroll_salary_report(db, path, fmt=fmt)
            QMessageBox.information(self, "Report Generated", f"Saved report to:\n{path}")
        except PermissionError as exc:
            QMessageBox.warning(self, "Access Denied", str(exc))
        finally:
            db.close()
