"""
EduManage Pro - Student CRM Management Page (PySide6)
Full Student CRM directory with 10-field advanced search, 7 lifecycle statuses,
360° CRM Profile view, Digital ID cards with QR code, Excel/CSV Import Wizard,
Promotion, Transfer, Withdrawal, Archive, and Restore workflows.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.connection import SessionLocal
from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.school import SchoolSetting
from app.models.student import StudentStatus
from app.reports.student_profile_pdf import StudentProfilePDFGenerator
from app.repositories.student_repository import StudentRepository
from app.services.student_service import StudentService
from app.ui.dialogs.student_form_dialog import StudentFormDialog
from app.ui.dialogs.student_id_card_dialog import StudentIDCardDialog
from app.ui.dialogs.student_import_dialog import StudentImportDialog
from app.ui.dialogs.student_lifecycle_dialog import StudentLifecycleDialog
from app.ui.dialogs.student_profile_dialog import StudentProfileDialog
from app.ui.dialogs.student_promote_dialog import StudentPromoteDialog


class StudentManagementPage(QWidget):
    def __init__(self, parent=None, current_username: str = "admin"):
        super().__init__(parent)
        self.current_username = current_username
        self.current_page = 1
        self.per_page = 20
        self.total_records = 0

        self._build_ui()
        self._load_filter_options()
        self.refresh_roster()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header & Action Toolbar
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Student CRM & Admissions")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #f8fafc;")
        subtitle = QLabel(
            "360° student profiles, guardians & siblings, Digital QR IDs, timelines, and lifecycle management"
        )
        subtitle.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box)
        header_row.addStretch()

        btn_admit = QPushButton("➕ Admit Student")
        btn_admit.setStyleSheet(
            "background-color: #2563eb; color: white; padding: 8px 14px; font-weight: bold; border-radius: 6px;"
        )
        btn_admit.clicked.connect(self._open_admit_dialog)

        btn_import = QPushButton("📥 Import Excel/CSV")
        btn_import.setStyleSheet(
            "background-color: #059669; color: white; padding: 8px 14px; font-weight: bold; border-radius: 6px;"
        )
        btn_import.clicked.connect(self._open_import_dialog)

        btn_export = QPushButton("📤 Export Excel")
        btn_export.setStyleSheet(
            "background-color: #0891b2; color: white; padding: 8px 14px; font-weight: bold; border-radius: 6px;"
        )
        btn_export.clicked.connect(self._export_excel)

        btn_promote = QPushButton("🎓 Batch Promote")
        btn_promote.setStyleSheet(
            "background-color: #7c3aed; color: white; padding: 8px 14px; font-weight: bold; border-radius: 6px;"
        )
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
        self.kpi_archived = self._create_mini_kpi("Archived / Out", "0", "#f59e0b")
        self.kpi_male = self._create_mini_kpi("Male Students", "0", "#6366f1")
        self.kpi_female = self._create_mini_kpi("Female Students", "0", "#ec4899")
        kpi_bar.addWidget(self.kpi_total)
        kpi_bar.addWidget(self.kpi_active)
        kpi_bar.addWidget(self.kpi_archived)
        kpi_bar.addWidget(self.kpi_male)
        kpi_bar.addWidget(self.kpi_female)
        main_layout.addLayout(kpi_bar)

        # 3. Advanced Multi-Criteria Search Panel (Name, ID, Adm #, Roll, Class, Section, Guardian, Phone, Status, Academic Year, Tags)
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px;"
        )
        f_grid = QGridLayout(filter_frame)
        f_grid.setContentsMargins(8, 6, 8, 6)
        f_grid.setSpacing(8)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Quick Search (Name, ID, Guardian, Phone, Tag)...")
        self.search_box.textChanged.connect(self._on_filter_changed)

        self.filter_name = QLineEdit()
        self.filter_name.setPlaceholderText("Student Name...")
        self.filter_name.textChanged.connect(self._on_filter_changed)

        self.filter_student_id = QLineEdit()
        self.filter_student_id.setPlaceholderText("Student ID / Digital ID...")
        self.filter_student_id.textChanged.connect(self._on_filter_changed)

        self.filter_adm_no = QLineEdit()
        self.filter_adm_no.setPlaceholderText("Admission No...")
        self.filter_adm_no.textChanged.connect(self._on_filter_changed)

        self.filter_roll = QLineEdit()
        self.filter_roll.setPlaceholderText("Roll #...")
        self.filter_roll.textChanged.connect(self._on_filter_changed)

        self.filter_guardian = QLineEdit()
        self.filter_guardian.setPlaceholderText("Guardian Name...")
        self.filter_guardian.textChanged.connect(self._on_filter_changed)

        self.filter_phone = QLineEdit()
        self.filter_phone.setPlaceholderText("Phone (Student/Guardian)...")
        self.filter_phone.textChanged.connect(self._on_filter_changed)

        self.filter_tag = QLineEdit()
        self.filter_tag.setPlaceholderText("CRM Tag...")
        self.filter_tag.textChanged.connect(self._on_filter_changed)

        self.filter_class = QComboBox()
        self.filter_class.addItem("All Classes", None)
        self.filter_class.currentIndexChanged.connect(self._on_filter_changed)

        self.filter_section = QComboBox()
        self.filter_section.addItem("All Sections", None)
        self.filter_section.currentIndexChanged.connect(self._on_filter_changed)

        self.filter_ay = QComboBox()
        self.filter_ay.addItem("All Academic Years", None)
        self.filter_ay.currentIndexChanged.connect(self._on_filter_changed)

        self.filter_status = QComboBox()
        self.filter_status.addItem("All Statuses", None)
        for st in StudentStatus.ALL:
            self.filter_status.addItem(StudentStatus.LABELS.get(st, st.title()), st)
        self.filter_status.currentIndexChanged.connect(self._on_filter_changed)

        self.filter_gender = QComboBox()
        self.filter_gender.addItems(["All Genders", "Male", "Female", "Other"])
        self.filter_gender.currentIndexChanged.connect(self._on_filter_changed)

        self.chk_show_deleted = QCheckBox("Show Soft-Deleted")
        self.chk_show_deleted.stateChanged.connect(self._on_filter_changed)

        btn_reset = QPushButton("Reset Filters")
        btn_reset.clicked.connect(self._reset_filters)

        # Row 0: Quick search + Academic filters
        f_grid.addWidget(self.search_box, 0, 0, 1, 2)
        f_grid.addWidget(self.filter_class, 0, 2)
        f_grid.addWidget(self.filter_section, 0, 3)
        f_grid.addWidget(self.filter_ay, 0, 4)
        f_grid.addWidget(self.filter_status, 0, 5)

        # Row 1: Dedicated field search
        f_grid.addWidget(self.filter_name, 1, 0)
        f_grid.addWidget(self.filter_student_id, 1, 1)
        f_grid.addWidget(self.filter_adm_no, 1, 2)
        f_grid.addWidget(self.filter_roll, 1, 3)
        f_grid.addWidget(self.filter_guardian, 1, 4)
        f_grid.addWidget(self.filter_phone, 1, 5)

        # Row 2: Tag, Gender, Soft-deleted toggle, Reset
        f_grid.addWidget(self.filter_tag, 2, 0)
        f_grid.addWidget(self.filter_gender, 2, 1)
        f_grid.addWidget(self.chk_show_deleted, 2, 2)
        f_grid.addWidget(btn_reset, 2, 5)

        main_layout.addWidget(filter_frame)

        # 4. Student Roster Table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Student ID",
            "Digital ID",
            "Roll",
            "Full Name",
            "Class & Section",
            "Gender",
            "Guardian & Phone",
            "Tags",
            "Status",
            "Actions",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
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
        card.setStyleSheet(
            f"background-color: #1e293b; border: 1px solid #334155; border-left: 4px solid {color}; border-radius: 6px; padding: 8px;"
        )
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
            for c in db.query(SchoolClass).order_by(SchoolClass.numeric_order).all():
                self.filter_class.addItem(c.name, c.id)
            for s in db.query(Section).all():
                self.filter_section.addItem(s.name, s.id)
            for y in db.query(AcademicYear).all():
                self.filter_ay.addItem(y.name, y.id)
        finally:
            db.close()

    def _on_filter_changed(self):
        self.current_page = 1
        self.refresh_roster()

    def refresh_roster(self):
        db = SessionLocal()
        try:
            stats = StudentRepository.get_summary_statistics(db)
            self.kpi_total.value_lbl.setText(f"{stats['total']:,}")
            self.kpi_active.value_lbl.setText(f"{stats['active']:,}")
            out_cnt = stats["archived"] + stats["transferred"] + stats["withdrawn"]
            self.kpi_archived.value_lbl.setText(f"{out_cnt:,}")
            self.kpi_male.value_lbl.setText(f"{stats['male']:,}")
            self.kpi_female.value_lbl.setText(f"{stats['female']:,}")

            gender_txt = self.filter_gender.currentText()
            gender = gender_txt if gender_txt != "All Genders" else None

            students, total = StudentRepository.search_and_filter(
                db,
                search_query=self.search_box.text(),
                name=self.filter_name.text(),
                student_id_code=self.filter_student_id.text(),
                admission_number=self.filter_adm_no.text(),
                roll_number=self.filter_roll.text(),
                class_id=self.filter_class.currentData(),
                section_id=self.filter_section.currentData(),
                academic_year_id=self.filter_ay.currentData(),
                guardian=self.filter_guardian.text(),
                phone=self.filter_phone.text(),
                status=self.filter_status.currentData(),
                tag=self.filter_tag.text(),
                gender=gender,
                include_deleted=self.chk_show_deleted.isChecked(),
                page=self.current_page,
                per_page=self.per_page,
            )
            self.total_records = total

            self.table.setRowCount(len(students))
            for i, stu in enumerate(students):
                sid_item = QTableWidgetItem(stu.student_id)
                sid_item.setData(Qt.UserRole, stu.id)
                self.table.setItem(i, 0, sid_item)
                self.table.setItem(i, 1, QTableWidgetItem(stu.digital_id_code or "-"))
                self.table.setItem(i, 2, QTableWidgetItem(str(stu.roll_number)))
                self.table.setItem(i, 3, QTableWidgetItem(stu.full_name))

                c_str = f"{stu.school_class.name if stu.school_class else '-'} ({stu.section.name if stu.section else '-'})"
                self.table.setItem(i, 4, QTableWidgetItem(c_str))
                self.table.setItem(i, 5, QTableWidgetItem(stu.gender))

                g_str = (
                    f"{stu.guardian.guardian_name if stu.guardian else '-'} "
                    f"({stu.guardian.guardian_phone if stu.guardian else '-'})"
                )
                self.table.setItem(i, 6, QTableWidgetItem(g_str))
                self.table.setItem(i, 7, QTableWidgetItem(", ".join(stu.get_tag_names()) or "-"))

                status_label = StudentStatus.LABELS.get(stu.status, stu.status.capitalize())
                if stu.is_deleted:
                    status_label += " (Deleted)"
                status_item = QTableWidgetItem(status_label)
                if stu.status == StudentStatus.ACTIVE and not stu.is_deleted:
                    status_item.setForeground(Qt.green)
                elif stu.status in (StudentStatus.SUSPENDED, StudentStatus.WITHDRAWN):
                    status_item.setForeground(Qt.yellow)
                else:
                    status_item.setForeground(Qt.gray)
                self.table.setItem(i, 8, status_item)

                # Actions row widget
                act_widget = QWidget()
                act_layout = QHBoxLayout(act_widget)
                act_layout.setContentsMargins(4, 2, 4, 2)
                act_layout.setSpacing(4)

                btn_crm = QPushButton("360°")
                btn_crm.setToolTip("Open Student 360° CRM Profile & Timeline")
                btn_crm.clicked.connect(lambda _chk=False, s_id=stu.id: self._open_crm_profile(s_id))

                btn_id = QPushButton("ID")
                btn_id.setToolTip("View & Print Digital QR ID Card")
                btn_id.clicked.connect(lambda _chk=False, s_id=stu.id: self._open_id_card(s_id))

                btn_edit = QPushButton("✏️")
                btn_edit.setToolTip("Edit Profile")
                btn_edit.clicked.connect(lambda _chk=False, s_id=stu.id: self._open_edit_dialog(s_id))

                btn_more = QPushButton("▾")
                btn_more.setToolTip("Lifecycle Actions (Transfer, Withdraw, Archive, Restore)")
                btn_more.clicked.connect(
                    lambda _chk=False, s_id=stu.id, s_name=stu.full_name, b=btn_more: self._show_lifecycle_menu(s_id, s_name, b)
                )

                act_layout.addWidget(btn_crm)
                act_layout.addWidget(btn_id)
                act_layout.addWidget(btn_edit)
                act_layout.addWidget(btn_more)
                self.table.setCellWidget(i, 9, act_widget)

            start_num = (self.current_page - 1) * self.per_page + 1 if total > 0 else 0
            end_num = min(self.current_page * self.per_page, total)
            self.lbl_page_info.setText(f"Showing {start_num} to {end_num} of {total} students")
            self.btn_prev.setEnabled(self.current_page > 1)
            self.btn_next.setEnabled(end_num < total)
        finally:
            db.close()

    def _on_row_double_clicked(self, row: int, _col: int):
        item = self.table.item(row, 0)
        if item:
            student_pk = item.data(Qt.UserRole)
            if student_pk:
                self._open_crm_profile(student_pk)

    def _show_lifecycle_menu(self, student_pk: int, student_name: str, anchor_btn: QPushButton):
        menu = QMenu(self)
        act_pdf = menu.addAction("Export Dossier PDF")
        menu.addSeparator()
        act_transfer = menu.addAction("Transfer Out...")
        act_withdraw = menu.addAction("Withdraw Enrollment...")
        act_archive = menu.addAction("Archive Student...")
        act_restore = menu.addAction("Restore to Active...")
        menu.addSeparator()
        act_soft_del = menu.addAction("Soft Delete Record")

        chosen = menu.exec(anchor_btn.mapToGlobal(anchor_btn.rect().bottomLeft()))
        if not chosen:
            return
        if chosen == act_pdf:
            self._export_profile_pdf(student_pk)
        elif chosen == act_transfer:
            self._run_lifecycle_dialog(student_pk, student_name, "transfer")
        elif chosen == act_withdraw:
            self._run_lifecycle_dialog(student_pk, student_name, "withdraw")
        elif chosen == act_archive:
            self._run_lifecycle_dialog(student_pk, student_name, "archive")
        elif chosen == act_restore:
            self._run_lifecycle_dialog(student_pk, student_name, "restore")
        elif chosen == act_soft_del:
            self._archive_student(student_pk)

    def _run_lifecycle_dialog(self, student_pk: int, student_name: str, action: str):
        diag = StudentLifecycleDialog(
            self,
            student_pk=student_pk,
            student_name=student_name,
            action=action,
            actor=self.current_username,
        )
        if diag.exec() == StudentLifecycleDialog.Accepted:
            self.refresh_roster()

    def _reset_filters(self):
        for w in (
            self.search_box,
            self.filter_name,
            self.filter_student_id,
            self.filter_adm_no,
            self.filter_roll,
            self.filter_guardian,
            self.filter_phone,
            self.filter_tag,
        ):
            w.blockSignals(True)
            w.clear()
            w.blockSignals(False)

        for cb in (
            self.filter_class,
            self.filter_section,
            self.filter_ay,
            self.filter_status,
            self.filter_gender,
        ):
            cb.blockSignals(True)
            cb.setCurrentIndex(0)
            cb.blockSignals(False)

        self.chk_show_deleted.blockSignals(True)
        self.chk_show_deleted.setChecked(False)
        self.chk_show_deleted.blockSignals(False)

        self.current_page = 1
        self.refresh_roster()

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_roster()

    def _next_page(self):
        if self.current_page * self.per_page < self.total_records:
            self.current_page += 1
            self.refresh_roster()

    def _open_crm_profile(self, student_pk: int):
        diag = StudentProfileDialog(self, student_pk=student_pk, actor=self.current_username)
        diag.exec()
        if diag.modified:
            self.refresh_roster()

    def _open_admit_dialog(self):
        diag = StudentFormDialog(self, actor=self.current_username)
        if diag.exec() == StudentFormDialog.Accepted:
            self.refresh_roster()

    def _open_edit_dialog(self, student_pk: int):
        diag = StudentFormDialog(self, student_id=student_pk, actor=self.current_username)
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
        diag = StudentImportDialog(self, actor=self.current_username)
        if diag.exec() == StudentImportDialog.Accepted:
            self.refresh_roster()

    def _open_promote_dialog(self):
        diag = StudentPromoteDialog(self, actor=self.current_username)
        if diag.exec() == StudentPromoteDialog.Accepted:
            self.refresh_roster()

    def _export_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Student Directory", "Students_Roster.xlsx", "Excel Files (*.xlsx)"
        )
        if file_path:
            db = SessionLocal()
            try:
                StudentService.export_students_to_excel(
                    db,
                    file_path,
                    class_id=self.filter_class.currentData(),
                    status=self.filter_status.currentData(),
                )
                QMessageBox.information(self, "Export Success", f"Exported student roster to:\n{file_path}")
            finally:
                db.close()

    def _archive_student(self, student_pk: int):
        confirm = QMessageBox.question(
            self,
            "Soft-Delete Student Record",
            "Are you sure you want to soft-delete this student record? Status will be set to inactive.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            db = SessionLocal()
            try:
                stu = StudentRepository.get_by_id(db, student_pk)
                if stu:
                    StudentRepository.archive_or_delete(
                        db, stu, soft_delete=True, deleted_by=self.current_username
                    )
                    self.refresh_roster()
            finally:
                db.close()
