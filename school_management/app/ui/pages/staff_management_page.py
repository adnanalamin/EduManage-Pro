"""
EduManage Pro - Staff Management Page (PySide6)
Non-teaching employee directory with position filters, payroll overview, and badge printing.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from app.database.connection import SessionLocal
from app.models.staff import Staff, Department, STAFF_ROLE_CATALOG
from app.repositories.staff_repository import StaffRepository
from app.services.staff_service import StaffService
from app.ui.dialogs.hr_profile_dialog import HRProfileDialog
from app.ui.dialogs.staff_form_dialog import StaffFormDialog
from app.ui.dialogs.teacher_id_card_dialog import TeacherIDCardDialog


class StaffManagementPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 1
        self.per_page = 20
        self.total_records = 0

        self._build_ui()
        self._load_departments()
        self.refresh_roster()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Header & Actions
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Non-Teaching Staff & Employee Directory")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #f8fafc;")
        subtitle = QLabel("Support personnel: Accountants, Librarians, Receptionists, Security, and IT Staff")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box)
        header_row.addStretch()

        btn_add = QPushButton("➕ Register Staff Member")
        btn_add.setStyleSheet("background-color: #6366f1; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        btn_add.clicked.connect(self._open_add_dialog)
        btn_export = QPushButton("📤 Export Excel (.xlsx)")
        btn_export.setStyleSheet("background-color: #0891b2; color: white; padding: 8px 14px; font-weight: bold; border-radius: 6px;")
        btn_export.clicked.connect(self._export_excel)
        header_row.addWidget(btn_add)
        header_row.addWidget(btn_export)
        main_layout.addLayout(header_row)

        # KPI Summary Cards
        kpi_bar = QHBoxLayout()
        self.kpi_total = self._create_mini_kpi("Total Staff", "0", "#6366f1")
        self.kpi_active = self._create_mini_kpi("Active Personnel", "0", "#10b981")
        self.kpi_accounts = self._create_mini_kpi("Finance & Office", "8", "#3b82f6")
        self.kpi_security = self._create_mini_kpi("Security & Campus", "12", "#f59e0b")
        kpi_bar.addWidget(self.kpi_total)
        kpi_bar.addWidget(self.kpi_active)
        kpi_bar.addWidget(self.kpi_accounts)
        kpi_bar.addWidget(self.kpi_security)
        main_layout.addLayout(kpi_bar)

        # Filter Bar
        filter_frame = QFrame()
        filter_frame.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px;")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(8, 4, 8, 4)
        filter_layout.setSpacing(10)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search staff by name, employee ID, phone, or position...")
        self.search_box.textChanged.connect(self.refresh_roster)

        self.filter_position = QComboBox()
        self.filter_position.addItem("All Positions", None)
        self.filter_position.addItems(STAFF_ROLE_CATALOG)
        self.filter_position.currentIndexChanged.connect(self.refresh_roster)

        self.filter_dept = QComboBox()
        self.filter_dept.addItem("All Departments", None)
        self.filter_dept.currentIndexChanged.connect(self.refresh_roster)

        filter_layout.addWidget(self.search_box, stretch=2)
        filter_layout.addWidget(self.filter_position, stretch=1)
        filter_layout.addWidget(self.filter_dept, stretch=1)
        main_layout.addWidget(filter_frame)

        # Staff Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Staff ID", "Employee Name", "Position", "Department",
            "Shift", "Phone Number", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        main_layout.addWidget(self.table)

        # Pagination
        page_box = QHBoxLayout()
        self.lbl_page_info = QLabel("Showing 0 to 0 of 0 staff members")
        self.lbl_page_info.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.btn_prev = QPushButton("◀ Previous")
        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_next = QPushButton("Next ▶")
        self.btn_next.clicked.connect(self._next_page)
        page_box.addWidget(self.lbl_page_info)
        page_box.addStretch()
        page_box.addWidget(self.btn_prev)
        page_box.addWidget(self.btn_next)
        main_layout.addLayout(page_box)

    def _create_mini_kpi(self, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"background-color: #1e293b; border: 1px solid #334155; border-left: 4px solid {color}; border-radius: 6px; padding: 8px;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(6, 4, 6, 4)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600; text-transform: uppercase;")
        v_lbl = QLabel(value)
        v_lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        v_lbl.setStyleSheet(f"color: {color};")
        layout.addWidget(t_lbl)
        layout.addWidget(v_lbl)
        card.value_lbl = v_lbl
        return card

    def _load_departments(self):
        db = SessionLocal()
        try:
            depts = StaffRepository.get_or_create_departments(db)
            for d in depts:
                self.filter_dept.addItem(d.name, d.id)
        finally:
            db.close()

    def refresh_roster(self):
        db = SessionLocal()
        try:
            stats = StaffRepository.get_overview_statistics(db)
            self.kpi_total.value_lbl.setText(str(stats["total_staff"]))
            self.kpi_active.value_lbl.setText(str(stats["active_staff"]))

            search = self.search_box.text()
            dept_id = self.filter_dept.currentData()
            pos = self.filter_position.currentText()
            pos_filter = pos if pos != "All Positions" else None

            staff_list, total = StaffRepository.search_and_filter_staff(
                db, search_query=search, department_id=dept_id,
                position=pos_filter, page=self.current_page, per_page=self.per_page
            )
            self.total_records = total

            self.table.setRowCount(len(staff_list))
            for i, s in enumerate(staff_list):
                self.table.setItem(i, 0, QTableWidgetItem(s.staff_id))
                self.table.setItem(i, 1, QTableWidgetItem(s.full_name))
                self.table.setItem(i, 2, QTableWidgetItem(s.position))
                dept_name = s.department.name if s.department else "-"
                self.table.setItem(i, 3, QTableWidgetItem(dept_name))
                self.table.setItem(i, 4, QTableWidgetItem(f"{s.shift} Shift"))
                self.table.setItem(i, 5, QTableWidgetItem(s.phone))

                # Actions
                act_widget = QWidget()
                act_layout = QHBoxLayout(act_widget)
                act_layout.setContentsMargins(4, 2, 4, 2)
                act_layout.setSpacing(4)

                btn_hr = QPushButton("📋")
                btn_hr.setToolTip("Open 360° HR Profile & Timeline")
                btn_hr.clicked.connect(lambda checked, s_id=s.id: self._open_hr_profile(s_id))

                btn_badge = QPushButton("🪪")
                btn_badge.setToolTip("Print Staff Badge")
                btn_badge.clicked.connect(lambda checked, s_id=s.id: self._open_badge(s_id))

                btn_edit = QPushButton("✏️")
                btn_edit.setToolTip("Edit Profile")
                btn_edit.clicked.connect(lambda checked, s_id=s.id: self._open_edit_dialog(s_id))

                act_layout.addWidget(btn_hr)
                act_layout.addWidget(btn_badge)
                act_layout.addWidget(btn_edit)
                self.table.setCellWidget(i, 6, act_widget)

            start_num = (self.current_page - 1) * self.per_page + 1 if total > 0 else 0
            end_num = min(self.current_page * self.per_page, total)
            self.lbl_page_info.setText(f"Showing {start_num} to {end_num} of {total} staff members")
            self.btn_prev.setEnabled(self.current_page > 1)
            self.btn_next.setEnabled(end_num < total)
        finally:
            db.close()

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_roster()

    def _next_page(self):
        if self.current_page * self.per_page < self.total_records:
            self.current_page += 1
            self.refresh_roster()

    def _open_add_dialog(self):
        diag = StaffFormDialog(self)
        if diag.exec() == StaffFormDialog.Accepted:
            self.refresh_roster()

    def _open_edit_dialog(self, staff_pk: int):
        diag = StaffFormDialog(self, staff_id=staff_pk)
        if diag.exec() == StaffFormDialog.Accepted:
            self.refresh_roster()

    def _open_badge(self, staff_pk: int):
        diag = TeacherIDCardDialog(self, entity_id=staff_pk, is_teacher=False)
        diag.exec()

    def _open_hr_profile(self, staff_pk: int):
        diag = HRProfileDialog(self, employee_type="staff", employee_pk=staff_pk)
        diag.exec()
        self.refresh_roster()

    def _export_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Staff Directory", "Staff_Directory.xlsx", "Excel Files (*.xlsx)"
        )
        if file_path:
            db = SessionLocal()
            try:
                StaffService.export_staff_to_excel(db, file_path)
                QMessageBox.information(self, "Export Success", f"Staff roster exported to:\n{file_path}")
            finally:
                db.close()
