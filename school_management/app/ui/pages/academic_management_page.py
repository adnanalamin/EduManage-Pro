"""
EduManage Pro - Academic Management View (PySide6)
Full GUI interface for Class, Section, Group, Shift, and Subject administration.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QTabWidget, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.repositories.academic_repository import AcademicRepository
from app.services.academic_service import AcademicService
from app.ui.dialogs.class_form_dialog import ClassFormDialog
from app.ui.dialogs.section_form_dialog import SectionFormDialog
from app.ui.dialogs.subject_form_dialog import SubjectFormDialog


class AcademicManagementPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh_all()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # 1. Header Banner & Metrics
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("Academic & Curriculum Management")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A;")
        sub_lbl = QLabel("Manage School Classes, Sections, Shifts, Streams, and Subject Syllabi")
        sub_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Action Buttons
        btn_class = QPushButton("+ Add Class")
        btn_class.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")
        btn_class.clicked.connect(self._on_add_class)
        header_layout.addWidget(btn_class)

        btn_section = QPushButton("+ Add Section")
        btn_section.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")
        btn_section.clicked.connect(self._on_add_section)
        header_layout.addWidget(btn_section)

        btn_sub = QPushButton("+ Add Subject")
        btn_sub.setStyleSheet("background-color: #7C3AED; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")
        btn_sub.clicked.connect(self._on_add_subject)
        header_layout.addWidget(btn_sub)

        main_layout.addLayout(header_layout)

        # 2. KPI Summary Bar
        kpi_frame = QFrame()
        kpi_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        kpi_layout = QHBoxLayout(kpi_frame)
        kpi_layout.setContentsMargins(16, 12, 16, 12)

        self.kpi_year = QLabel("Session: 2025-2026")
        self.kpi_year.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        kpi_layout.addWidget(self.kpi_year)
        kpi_layout.addSpacing(20)

        self.kpi_classes = QLabel("Classes: 0")
        self.kpi_classes.setStyleSheet("font-size: 13px; color: #2563EB; font-weight: 600;")
        kpi_layout.addWidget(self.kpi_classes)
        kpi_layout.addSpacing(20)

        self.kpi_sections = QLabel("Sections: 0")
        self.kpi_sections.setStyleSheet("font-size: 13px; color: #059669; font-weight: 600;")
        kpi_layout.addWidget(self.kpi_sections)
        kpi_layout.addSpacing(20)

        self.kpi_subjects = QLabel("Subjects: 0")
        self.kpi_subjects.setStyleSheet("font-size: 13px; color: #7C3AED; font-weight: 600;")
        kpi_layout.addWidget(self.kpi_subjects)
        kpi_layout.addStretch()

        main_layout.addWidget(kpi_frame)

        # 3. Tabs: Classes & Sections vs. Subjects
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { font-weight: 600; padding: 8px 16px; margin-right: 4px; }
            QTabBar::tab:selected { background: #2563EB; color: white; border-radius: 4px; }
        """)

        # Tab 1: Classes & Sections
        tab_classes = QWidget()
        classes_vbox = QVBoxLayout(tab_classes)
        classes_vbox.setContentsMargins(0, 12, 0, 0)
        classes_vbox.setSpacing(10)

        # Filter bar
        c_filter_h = QHBoxLayout()
        c_filter_h.addWidget(QLabel("Filter:"))
        self.class_search_edit = QLineEdit()
        self.class_search_edit.setPlaceholderText("Search by class name, code, or group...")
        self.class_search_edit.textChanged.connect(self._load_classes_table)
        c_filter_h.addWidget(self.class_search_edit)

        c_filter_h.addStretch()
        classes_vbox.addLayout(c_filter_h)

        # Classes Table
        self.classes_table = QTableWidget()
        self.classes_table.setColumnCount(8)
        self.classes_table.setHorizontalHeaderLabels([
            "Order", "Class Name", "Code", "Group / Stream", "Shift", "Active Sections", "Subjects", "Actions"
        ])
        self.classes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.classes_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.classes_table.setEditTriggers(QTableWidget.NoEditTriggers)
        classes_vbox.addWidget(self.classes_table)

        self.tabs.addTab(tab_classes, "Classes & Sections Roster")

        # Tab 2: Subject Management
        tab_subjects = QWidget()
        subjects_vbox = QVBoxLayout(tab_subjects)
        subjects_vbox.setContentsMargins(0, 12, 0, 0)
        subjects_vbox.setSpacing(10)

        # Subject Filter Bar
        s_filter_h = QHBoxLayout()
        s_filter_h.addWidget(QLabel("Select Class:"))
        self.sub_class_combo = QComboBox()
        self.sub_class_combo.addItem("All Classes", None)
        self.sub_class_combo.currentIndexChanged.connect(self._load_subjects_table)
        s_filter_h.addWidget(self.sub_class_combo)

        s_filter_h.addSpacing(16)
        s_filter_h.addWidget(QLabel("Search:"))
        self.sub_search_edit = QLineEdit()
        self.sub_search_edit.setPlaceholderText("Search by subject name or code...")
        self.sub_search_edit.textChanged.connect(self._load_subjects_table)
        s_filter_h.addWidget(self.sub_search_edit)

        s_filter_h.addStretch()
        subjects_vbox.addLayout(s_filter_h)

        # Subjects Table
        self.subjects_table = QTableWidget()
        self.subjects_table.setColumnCount(8)
        self.subjects_table.setHorizontalHeaderLabels([
            "Subject ID", "Name", "Code", "Class", "Type", "Full / Pass", "Theory / Practical", "Assigned Faculty"
        ])
        self.subjects_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.subjects_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.subjects_table.setEditTriggers(QTableWidget.NoEditTriggers)
        subjects_vbox.addWidget(self.subjects_table)

        self.tabs.addTab(tab_subjects, "Subject Curriculum & Marks")

        main_layout.addWidget(self.tabs)

    def refresh_all(self):
        db: Session = SessionLocal()
        try:
            summary = AcademicService.get_academic_summary(db)
            self.kpi_year.setText(f"Session: {summary['current_year']}")
            self.kpi_classes.setText(f"Classes: {summary['total_classes']}")
            self.kpi_sections.setText(f"Sections: {summary['total_sections']}")
            self.kpi_subjects.setText(f"Subjects: {summary['total_subjects']}")

            # Populate class dropdown
            classes = AcademicRepository.get_classes(db)
            current_idx = self.sub_class_combo.currentIndex()
            self.sub_class_combo.blockSignals(True)
            self.sub_class_combo.clear()
            self.sub_class_combo.addItem("All Classes", None)
            for c in classes:
                self.sub_class_combo.addItem(f"{c.name} ({c.group})", c.id)
            if current_idx >= 0 and current_idx < self.sub_class_combo.count():
                self.sub_class_combo.setCurrentIndex(current_idx)
            self.sub_class_combo.blockSignals(False)

            self._load_classes_table()
            self._load_subjects_table()
        finally:
            db.close()

    def _load_classes_table(self):
        query_text = self.class_search_edit.text().strip()
        db: Session = SessionLocal()
        try:
            classes = AcademicRepository.get_classes(db, search=query_text if query_text else None)
            self.classes_table.setRowCount(len(classes))
            for row, cls_obj in enumerate(classes):
                self.classes_table.setItem(row, 0, QTableWidgetItem(str(cls_obj.numeric_order)))
                self.classes_table.setItem(row, 1, QTableWidgetItem(cls_obj.name))
                self.classes_table.setItem(row, 2, QTableWidgetItem(cls_obj.code or "-"))
                self.classes_table.setItem(row, 3, QTableWidgetItem(cls_obj.group))
                self.classes_table.setItem(row, 4, QTableWidgetItem(cls_obj.shift))
                
                # Active sections formatted
                sec_names = ", ".join([s.name for s in cls_obj.sections]) if cls_obj.sections else "None"
                self.classes_table.setItem(row, 5, QTableWidgetItem(f"{len(cls_obj.sections)} ({sec_names})"))
                self.classes_table.setItem(row, 6, QTableWidgetItem(str(len(cls_obj.subjects))))
                self.classes_table.setItem(row, 7, QTableWidgetItem("Edit | Sections"))
        finally:
            db.close()

    def _load_subjects_table(self):
        class_id = self.sub_class_combo.currentData()
        search_text = self.sub_search_edit.text().strip()
        db: Session = SessionLocal()
        try:
            subjects = AcademicRepository.get_subjects(db, class_id=class_id, search=search_text if search_text else None)
            self.subjects_table.setRowCount(len(subjects))
            for row, s in enumerate(subjects):
                self.subjects_table.setItem(row, 0, QTableWidgetItem(s.subject_id))
                self.subjects_table.setItem(row, 1, QTableWidgetItem(s.name))
                self.subjects_table.setItem(row, 2, QTableWidgetItem(s.code))
                cls_title = s.school_class.name if s.school_class else "-"
                self.subjects_table.setItem(row, 3, QTableWidgetItem(cls_title))
                self.subjects_table.setItem(row, 4, QTableWidgetItem(s.subject_type))
                self.subjects_table.setItem(row, 5, QTableWidgetItem(f"{s.full_marks} / {s.pass_marks}"))
                self.subjects_table.setItem(row, 6, QTableWidgetItem(f"Th: {s.theory_marks} | Pr: {s.practical_marks}"))
                teacher_title = s.assigned_teacher.full_name if s.assigned_teacher else "Unassigned"
                self.subjects_table.setItem(row, 7, QTableWidgetItem(teacher_title))
        finally:
            db.close()

    def _on_add_class(self):
        dlg = ClassFormDialog(self)
        if dlg.exec() == ClassFormDialog.Accepted:
            self.refresh_all()

    def _on_add_section(self):
        dlg = SectionFormDialog(self)
        if dlg.exec() == SectionFormDialog.Accepted:
            self.refresh_all()

    def _on_add_subject(self):
        dlg = SubjectFormDialog(self)
        if dlg.exec() == SubjectFormDialog.Accepted:
            self.refresh_all()
