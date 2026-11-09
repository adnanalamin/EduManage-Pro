"""
EduManage Pro - Student Management Page (PySide6)
Full student roster with multi-column filtering, search, pagination, ID card printing, and Excel sync.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from app.database.connection import SessionLocal
from app.models.student import Student, StudentStatus
from app.models.academic import SchoolClass, Section
from app.models.school import SchoolSetting
from app.repositories.student_repository import StudentRepository
from app.services.student_service import StudentService
from app.reports.student_profile_pdf import StudentProfilePDFGenerator
from app.ui.dialogs.student_form_dialog import StudentFormDialog
from app.ui.dialogs.student_id_card_dialog import StudentIDCardDialog
from app.ui.dialogs.student_import_dialog import StudentImportDialog
from app.ui.dialogs.student_promote_dialog import StudentPromoteDialog


class StudentManagementPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 1
        self.per_page = 20
        self.total_records = 0

        self._build_ui()
        self._load_filter_options()
        self.refresh_roster()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 1. Header & Actions Bar
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Student Management & Admissions")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #f8fafc;")
        subtitle = QLabel("Manage student enrollment, identity cards, guardians, promotions and records")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box)
        header_row.addStretch()

        btn_admit = QPushButton("➕ Admit New Student")
        btn_admit.setStyleSheet("background-color: #2563eb; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        btn_admit.clicked.connect(self._open_admit_dialog)

        btn_import = QPushButton("📥 Import Excel")
        btn_import.setStyleSheet("background-color: #059669; color: white; padding: 8px 14px; font-weight: bold; border-radius: 6px;")
        btn_import.clicked.connect(self._open_import_dialog)

        btn_export = QPushButton("📤 Export Excel")
        btn_export.setStyleSheet("background-color: #0891b2; color: white; padding: 8px 14px; font-weight: bold; border-radius: 6px;")
        btn_export.clicked.connect(self._export_excel)

        btn_promote = QPushButton("🎓 Batch Promote")
        btn_promote.setStyleSheet("background-color: #7c3aed; color: white; padding: 8px 14px; font-weight: bold; border-radius: 6px;")
        btn_promote.clicked.connect(self._open_promote_dialog)

        header_row.addWidget(btn_admit)
        header_row.addWidget(btn_import)
        header_row.addWidget(btn_export)
        header_row.addWidget(btn_promote)
        main_layout.addLayout(header_row)

        # 2. KPI Summary Bar
        kpi_bar = QHBoxLayout()
        self.kpi_total = self._create_mini_kpi("Total Enrolled", "0", "#3b82f6")
        self.kpi_active = self._create_mini_kpi("Active Students", "0", "#10b981")
        self.kpi_male = self._create_mini_kpi("Male Students", "0", "#6366f1")
        self.kpi_female = self._create_mini_kpi("Female Students", "0", "#ec4899")
        kpi_bar.addWidget(self.kpi_total)
        kpi_bar.addWidget(self.kpi_active)
        kpi_bar.addWidget(self.kpi_male)
        kpi_bar.addWidget(self.kpi_female)
        main_layout.addLayout(kpi_bar)

        # 3. Search & Filter Bar
        filter_frame = QFrame()
        filter_frame.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px;")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(8, 4, 8, 4)
        filter_layout.setSpacing(10)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search student by name, roll, ID, or phone...")
        self.search_box.textChanged.connect(self.refresh_roster)

        self.filter_class = QComboBox()
        self.filter_class.addItem("All Classes", None)
        self.filter_class.currentIndexChanged.connect(self.refresh_roster)

        self.filter_gender = QComboBox()
        self.filter_gender.addItems(["All Genders", "Male", "Female"])
        self.filter_gender.currentIndexChanged.connect(self.refresh_roster)

        self.filter_status = QComboBox()
        self.filter_status.addItem("All Statuses", None)
        self.filter_status.addItems([StudentStatus.ACTIVE, StudentStatus.INACTIVE, StudentStatus.TRANSFERRED])
        self.filter_status.currentIndexChanged.connect(self.refresh_roster)

        btn_reset = QPushButton("Reset Filters")
        btn_reset.clicked.connect(self._reset_filters)

        filter_layout.addWidget(self.search_box, stretch=2)
        filter_layout.addWidget(self.filter_class, stretch=1)
        filter_layout.addWidget(self.filter_gender, stretch=1)
        filter_layout.addWidget(self.filter_status, stretch=1)
        filter_layout.addWidget(btn_reset)
        main_layout.addWidget(filter_frame)

        # 4. Student Roster Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Roll", "Full Name", "Class & Section", "Gender",
            "Blood", "Guardian & Phone", "Status", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        main_layout.addWidget(self.table)

        # 5. Pagination Bar
        page_box = QHBoxLayout()
        self.lbl_page_info = QLabel("Showing 0 to 0 of 0 students")
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

    def _load_filter_options(self):
        db = SessionLocal()
        try:
            for c in db.query(SchoolClass).all():
                self.filter_class.addItem(c.name, c.id)
        finally:
            db.close()

    def refresh_roster(self):
        db = SessionLocal()
        try:
            # Update KPI summary
            stats = StudentRepository.get_summary_statistics(db)
            self.kpi_total.value_lbl.setText(f"{stats['total']:,}")
            self.kpi_active.value_lbl.setText(f"{stats['active']:,}")
            self.kpi_male.value_lbl.setText(f"{stats['male']:,}")
            self.kpi_female.value_lbl.setText(f"{stats['female']:,}")

            search = self.search_box.text()
            c_id = self.filter_class.currentData()
            gender_txt = self.filter_gender.currentText()
            gender = gender_txt if gender_txt != "All Genders" else None
            status = self.filter_status.currentData()

            students, total = StudentRepository.search_and_filter(
                db, search_query=search, class_id=c_id, gender=gender,
                status=status, page=self.current_page, per_page=self.per_page
            )
            self.total_records = total

            self.table.setRowCount(len(students))
            for i, stu in enumerate(students):
                self.table.setItem(i, 0, QTableWidgetItem(stu.student_id))
                self.table.setItem(i, 1, QTableWidgetItem(str(stu.roll_number)))
                self.table.setItem(i, 2, QTableWidgetItem(stu.full_name))

                c_str = f"{stu.school_class.name if stu.school_class else '-'} ({stu.section.name if stu.section else '-'})"
                self.table.setItem(i, 3, QTableWidgetItem(c_str))
                self.table.setItem(i, 4, QTableWidgetItem(stu.gender))
                self.table.setItem(i, 5, QTableWidgetItem(stu.blood_group or "-"))

                g_str = f"{stu.guardian.guardian_name if stu.guardian else '-'} ({stu.guardian.guardian_phone if stu.guardian else '-'})"
                self.table.setItem(i, 6, QTableWidgetItem(g_str))

                status_item = QTableWidgetItem(stu.status.capitalize())
                if stu.status == StudentStatus.ACTIVE:
                    status_item.setForeground(Qt.green)
                else:
                    status_item.setForeground(Qt.gray)
                self.table.setItem(i, 7, status_item)

                # Actions row widget
                act_widget = QWidget()
                act_layout = QHBoxLayout(act_widget)
                act_layout.setContentsMargins(4, 2, 4, 2)
                act_layout.setSpacing(4)

                btn_id = QPushButton("ID")
                btn_id.setToolTip("View & Print ID Card")
                btn_id.clicked.connect(lambda checked, s_id=stu.id: self._open_id_card(s_id))

                btn_dossier = QPushButton("📄")
                btn_dossier.setToolTip("Export Printable Dossier PDF")
                btn_dossier.clicked.connect(lambda checked, s_id=stu.id: self._export_profile_pdf(s_id))

                btn_edit = QPushButton("✏️")
                btn_edit.setToolTip("Edit Profile")
                btn_edit.clicked.connect(lambda checked, s_id=stu.id: self._open_edit_dialog(s_id))

                btn_del = QPushButton("❌")
                btn_del.setToolTip("Archive Student")
                btn_del.clicked.connect(lambda checked, s_id=stu.id: self._archive_student(s_id))

                act_layout.addWidget(btn_id)
                act_layout.addWidget(btn_dossier)
                act_layout.addWidget(btn_edit)
                act_layout.addWidget(btn_del)

                self.table.setCellWidget(i, 8, act_widget)

            # Update pagination label
            start_num = (self.current_page - 1) * self.per_page + 1 if total > 0 else 0
            end_num = min(self.current_page * self.per_page, total)
            self.lbl_page_info.setText(f"Showing {start_num} to {end_num} of {total} students")
            self.btn_prev.setEnabled(self.current_page > 1)
            self.btn_next.setEnabled(end_num < total)
        finally:
            db.close()

    def _reset_filters(self):
        self.search_box.clear()
        self.filter_class.setCurrentIndex(0)
        self.filter_gender.setCurrentIndex(0)
        self.filter_status.setCurrentIndex(0)

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_roster()

    def _next_page(self):
        if self.current_page * self.per_page < self.total_records:
            self.current_page += 1
            self.refresh_roster()

    def _open_admit_dialog(self):
        diag = StudentFormDialog(self)
        if diag.exec() == StudentFormDialog.Accepted:
            self.refresh_roster()

    def _open_edit_dialog(self, student_pk: int):
        diag = StudentFormDialog(self, student_id=student_pk)
        if diag.exec() == StudentFormDialog.Accepted:
            self.refresh_roster()

    def _open_id_card(self, student_pk: int):
        diag = StudentIDCardDialog(self, student_pk=student_pk)
        diag.exec()

    def _export_profile_pdf(self, student_pk: int):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Student Dossier PDF", f"Student_Dossier_{student_pk}.pdf", "PDF Files (*.pdf)"
        )
        if file_path:
            db = SessionLocal()
            try:
                stu = StudentRepository.get_by_id(db, student_pk)
                school = db.query(SchoolSetting).first()
                if stu and school:
                    StudentProfilePDFGenerator.generate(stu, school, file_path)
                    QMessageBox.information(self, "Export Completed", f"Official dossier exported to:\n{file_path}")
            finally:
                db.close()

    def _open_import_dialog(self):
        diag = StudentImportDialog(self)
        if diag.exec() == StudentImportDialog.Accepted:
            self.refresh_roster()

    def _open_promote_dialog(self):
        diag = StudentPromoteDialog(self)
        if diag.exec() == StudentPromoteDialog.Accepted:
            self.refresh_roster()

    def _export_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Student Directory", "Students_Roster.xlsx", "Excel Files (*.xlsx)"
        )
        if file_path:
            db = SessionLocal()
            try:
                StudentService.export_students_to_excel(db, file_path)
                QMessageBox.information(self, "Export Success", f"Exported student roster to:\n{file_path}")
            finally:
                db.close()

    def _archive_student(self, student_pk: int):
        confirm = QMessageBox.question(
            self,
            "Archive Student Record",
            "Are you sure you want to archive this student? Their status will be set to inactive.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            db = SessionLocal()
            try:
                stu = StudentRepository.get_by_id(db, student_pk)
                if stu:
                    StudentRepository.archive_or_delete(db, stu, soft_delete=True)
                    self.refresh_roster()
            finally:
                db.close()
