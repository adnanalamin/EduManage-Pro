"""
EduManage Pro - Teacher Management Page (PySide6)
Faculty roster with department filtering, search, ID badge generator, and salary details.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from app.database.connection import SessionLocal
from app.models.staff import Teacher, Department
from app.repositories.staff_repository import StaffRepository
from app.services.staff_service import StaffService
from app.ui.dialogs.teacher_form_dialog import TeacherFormDialog
from app.ui.dialogs.teacher_id_card_dialog import TeacherIDCardDialog


class TeacherManagementPage(QWidget):
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
        title = QLabel("Faculty & Teacher Directory")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #f8fafc;")
        subtitle = QLabel("Manage teaching staff, subjects, qualifications, ID cards, and salary scales")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box)
        header_row.addStretch()

        btn_add = QPushButton("➕ Register New Teacher")
        btn_add.setStyleSheet("background-color: #059669; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        btn_add.clicked.connect(self._open_add_dialog)

        btn_export = QPushButton("📤 Export Excel (.xlsx)")
        btn_export.setStyleSheet("background-color: #0891b2; color: white; padding: 8px 14px; font-weight: bold; border-radius: 6px;")
        btn_export.clicked.connect(self._export_excel)

        header_row.addWidget(btn_add)
        header_row.addWidget(btn_export)
        main_layout.addLayout(header_row)

        # KPI Metrics Cards
        kpi_bar = QHBoxLayout()
        self.kpi_total = self._create_mini_kpi("Total Faculty", "0", "#10b981")
        self.kpi_active = self._create_mini_kpi("Active Teachers", "0", "#3b82f6")
        self.kpi_departments = self._create_mini_kpi("Departments", "9", "#8b5cf6")
        self.kpi_payroll = self._create_mini_kpi("Monthly Payroll", "৳ 0", "#06b6d4")
        kpi_bar.addWidget(self.kpi_total)
        kpi_bar.addWidget(self.kpi_active)
        kpi_bar.addWidget(self.kpi_departments)
        kpi_bar.addWidget(self.kpi_payroll)
        main_layout.addLayout(kpi_bar)

        # Search & Filter Bar
        filter_frame = QFrame()
        filter_frame.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px;")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(8, 4, 8, 4)
        filter_layout.setSpacing(10)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search teacher by name, ID, phone, or subject...")
        self.search_box.textChanged.connect(self.refresh_roster)

        self.filter_dept = QComboBox()
        self.filter_dept.addItem("All Departments", None)
        self.filter_dept.currentIndexChanged.connect(self.refresh_roster)

        self.filter_gender = QComboBox()
        self.filter_gender.addItems(["All Genders", "Male", "Female"])
        self.filter_gender.currentIndexChanged.connect(self.refresh_roster)

        self.filter_status = QComboBox()
        self.filter_status.addItem("All Statuses", None)
        self.filter_status.addItems(["active", "on_leave", "resigned", "retired"])
        self.filter_status.currentIndexChanged.connect(self.refresh_roster)

        filter_layout.addWidget(self.search_box, stretch=2)
        filter_layout.addWidget(self.filter_dept, stretch=1)
        filter_layout.addWidget(self.filter_gender, stretch=1)
        filter_layout.addWidget(self.filter_status, stretch=1)
        main_layout.addWidget(filter_frame)

        # Faculty Roster Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Teacher ID", "Full Name", "Department", "Primary Subject",
            "Designation", "Phone & Email", "Monthly Salary", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        main_layout.addWidget(self.table)

        # Pagination Bar
        page_box = QHBoxLayout()
        self.lbl_page_info = QLabel("Showing 0 to 0 of 0 faculty members")
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
        layout.setSpacing(2)

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
            self.kpi_total.value_lbl.setText(str(stats["total_teachers"]))
            self.kpi_active.value_lbl.setText(str(stats["active_teachers"]))
            self.kpi_payroll.value_lbl.setText(f"৳ {stats['monthly_payroll']:,}")

            search = self.search_box.text()
            dept_id = self.filter_dept.currentData()
            gender_txt = self.filter_gender.currentText()
            gender = gender_txt if gender_txt != "All Genders" else None
            status = self.filter_status.currentData()

            teachers, total = StaffRepository.search_and_filter_teachers(
                db, search_query=search, department_id=dept_id, gender=gender,
                status=status, page=self.current_page, per_page=self.per_page
            )
            self.total_records = total

            self.table.setRowCount(len(teachers))
            for i, t in enumerate(teachers):
                self.table.setItem(i, 0, QTableWidgetItem(t.teacher_id))
                self.table.setItem(i, 1, QTableWidgetItem(t.full_name))
                dept_name = t.department.name if t.department else "-"
                self.table.setItem(i, 2, QTableWidgetItem(dept_name))
                self.table.setItem(i, 3, QTableWidgetItem(t.primary_subject))
                self.table.setItem(i, 4, QTableWidgetItem(t.designation))
                self.table.setItem(i, 5, QTableWidgetItem(f"{t.phone}\n{t.email}"))
                self.table.setItem(i, 6, QTableWidgetItem(f"৳ {t.salary:,}"))

                # Actions
                act_widget = QWidget()
                act_layout = QHBoxLayout(act_widget)
                act_layout.setContentsMargins(4, 2, 4, 2)
                act_layout.setSpacing(4)

                btn_badge = QPushButton("🪪")
                btn_badge.setToolTip("View & Print Faculty Badge")
                btn_badge.clicked.connect(lambda checked, t_id=t.id: self._open_badge(t_id))

                btn_edit = QPushButton("✏️")
                btn_edit.setToolTip("Edit Teacher Profile")
                btn_edit.clicked.connect(lambda checked, t_id=t.id: self._open_edit_dialog(t_id))

                act_layout.addWidget(btn_badge)
                act_layout.addWidget(btn_edit)
                self.table.setCellWidget(i, 7, act_widget)

            start_num = (self.current_page - 1) * self.per_page + 1 if total > 0 else 0
            end_num = min(self.current_page * self.per_page, total)
            self.lbl_page_info.setText(f"Showing {start_num} to {end_num} of {total} teachers")
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
        diag = TeacherFormDialog(self)
        if diag.exec() == TeacherFormDialog.Accepted:
            self.refresh_roster()

    def _open_edit_dialog(self, teacher_pk: int):
        diag = TeacherFormDialog(self, teacher_id=teacher_pk)
        if diag.exec() == TeacherFormDialog.Accepted:
            self.refresh_roster()

    def _open_badge(self, teacher_pk: int):
        diag = TeacherIDCardDialog(self, entity_id=teacher_pk, is_teacher=True)
        diag.exec()

    def _export_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Faculty Directory", "Faculty_Directory.xlsx", "Excel Files (*.xlsx)"
        )
        if file_path:
            db = SessionLocal()
            try:
                StaffService.export_teachers_to_excel(db, file_path)
                QMessageBox.information(self, "Export Success", f"Faculty roster exported to:\n{file_path}")
            finally:
                db.close()
