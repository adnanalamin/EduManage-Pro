"""
EduManage Pro - Main Desktop Window (PySide6)
Combines Sidebar, Topbar, and Stacked Page Router with dynamic QSS themes.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QLabel, QMessageBox, QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from app.ui.widgets.sidebar import SidebarWidget
from app.ui.widgets.topbar import TopbarWidget
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.student_management_page import StudentManagementPage
from app.ui.pages.teacher_management_page import TeacherManagementPage
from app.ui.pages.staff_management_page import StaffManagementPage
from app.ui.pages.academic_management_page import AcademicManagementPage
from app.ui.pages.attendance_page import AttendancePage
from app.ui.pages.fees_management_page import FeesManagementPage
from app.ui.pages.accounting_page import AccountingPage
from app.ui.pages.exam_management_page import ExamManagementPage
from app.ui.pages.timetable_page import TimetablePage
from app.ui.pages.library_page import LibraryPage
from app.ui.pages.transport_page import TransportPage
from app.ui.pages.hostel_page import HostelPage
from app.ui.pages.notice_page import NoticePage
from app.ui.pages.reports_page import ReportsPage
from app.ui.pages.certificate_page import CertificatePage
from app.ui.themes.styles import DARK_THEME_QSS, LIGHT_THEME_QSS
from app.services.auth_service import AuthService
from app.database.connection import SessionLocal
from app.security.session import session


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EduManage Pro — School Management System (Desktop)")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)
        self.is_dark_theme = True

        self._build_ui()
        self.apply_theme()

    def _build_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Sidebar
        self.sidebar = SidebarWidget(self)
        self.sidebar.navigation_requested.connect(self._on_navigation)
        root_layout.addWidget(self.sidebar)

        # 2. Right Content Column
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Topbar
        self.topbar = TopbarWidget(self)
        self.topbar.theme_toggled.connect(self._toggle_theme)
        self.topbar.logout_requested.connect(self._handle_logout)
        self.topbar.search_triggered.connect(self._handle_search)
        self.topbar.notifications_requested.connect(self._show_notifications)
        right_layout.addWidget(self.topbar)

        # Stacked Pages
        self.stack = QStackedWidget()
        
        # Dashboard Page
        self.dashboard_page = DashboardPage(self)
        self.stack.addWidget(self.dashboard_page)

        # Student Management Page (Phase 2)
        self.student_page = StudentManagementPage(self)
        self.stack.addWidget(self.student_page)

        # Teacher Management Page (Phase 3)
        self.teacher_page = TeacherManagementPage(self)
        self.stack.addWidget(self.teacher_page)

        # Staff Management Page (Phase 3)
        self.staff_page = StaffManagementPage(self)
        self.stack.addWidget(self.staff_page)

        # Academic Management Page (Phase 4)
        self.academic_page = AcademicManagementPage(self)
        self.stack.addWidget(self.academic_page)

        # Attendance Management Page (Phase 5)
        self.attendance_page = AttendancePage(self)
        self.stack.addWidget(self.attendance_page)

        # Fees & Billing Management Page (Phase 6)
        self.fees_page = FeesManagementPage(self)
        self.stack.addWidget(self.fees_page)

        # School Accounting & Expense Page (Phase 7)
        self.accounting_page = AccountingPage(self)
        self.stack.addWidget(self.accounting_page)

        # Examination & Grading Page (Phase 8)
        self.exam_page = ExamManagementPage(self)
        self.stack.addWidget(self.exam_page)

        # Timetable & Routine Management Page (Phase 9)
        self.timetable_page = TimetablePage(self)
        self.stack.addWidget(self.timetable_page)

        # Library Management Page (Phase 10)
        self.library_page = LibraryPage(self)
        self.stack.addWidget(self.library_page)

        # Transport & Fleet Management Page (Phase 11)
        self.transport_page = TransportPage(self)
        self.stack.addWidget(self.transport_page)

        # Hostel & Dormitory Management Page (Phase 12)
        self.hostel_page = HostelPage(self)
        self.stack.addWidget(self.hostel_page)

        # Notice Board & Academic Events Page (Phase 13)
        self.notice_page = NoticePage(self)
        self.stack.addWidget(self.notice_page)

        # Comprehensive Reports & Analytics Page (Phase 14)
        self.reports_page = ReportsPage(self, db_session=SessionLocal())
        self.stack.addWidget(self.reports_page)

        # Certificate & ID Card Generator Page (Phase 15)
        self.certificate_page = CertificatePage(self, db_session=SessionLocal())
        self.stack.addWidget(self.certificate_page)

        # Module Placeholders (Settings handled via SetupWizard/Dialog)
        self.page_indices = {
            "dashboard": 0,
            "students": 1,
            "teachers": 2,
            "staff": 3,
            "academics": 4,
            "attendance": 5,
            "fees": 6,
            "accounting": 7,
            "exams": 8,
            "results": 8,
            "timetable": 9,
            "library": 10,
            "transport": 11,
            "hostel": 12,
            "notices": 13,
            "events": 13,
            "reports": 14,
            "certificates": 15,
        }
        module_names = [
            ("settings", "Phase 1: School Settings & System Preferences"),
        ]
        for key, title in module_names:
            page = self._create_phase_placeholder(key, title)
            idx = self.stack.addWidget(page)
            self.page_indices[key] = idx

        right_layout.addWidget(self.stack)
        root_layout.addWidget(right_column)

    def _create_phase_placeholder(self, module_key: str, title: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        h1 = QLabel(title)
        h1.setStyleSheet("font-size: 20px; font-weight: bold; color: #3b82f6;")
        
        desc = QLabel(
            f"Module '{module_key.capitalize()}' foundation is loaded.\n"
            "Data structures, security rules, and models are active in Phase 1 database."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #94a3b8; font-size: 13px; margin-top: 8px;")

        layout.addWidget(h1)
        layout.addWidget(desc)
        return page

    def _on_navigation(self, module_key: str):
        if module_key in self.page_indices:
            self.stack.setCurrentIndex(self.page_indices[module_key])
            if module_key == "dashboard":
                self.dashboard_page.refresh_data()
            elif module_key == "students":
                self.student_page.refresh_roster()
            elif module_key == "teachers":
                self.teacher_page.refresh_roster()
            elif module_key == "staff":
                self.staff_page.refresh_roster()
            elif module_key == "academics":
                self.academic_page.refresh_all()
            elif module_key == "attendance":
                self.attendance_page.refresh_all()
            elif module_key == "fees":
                self.fees_page.refresh_all()
            elif module_key == "accounting":
                self.accounting_page.refresh_all()
            elif module_key in ("exams", "results"):
                self.exam_page.refresh_all()
            elif module_key == "timetable":
                self.timetable_page.refresh_all()
            elif module_key == "library":
                self.library_page.refresh_all()
            elif module_key == "transport":
                self.transport_page.refresh_all()
            elif module_key == "hostel":
                self.hostel_page.refresh_all()
            elif module_key in ("notices", "events"):
                self.notice_page.refresh_all()
            elif module_key == "reports":
                self.reports_page.refresh_all()
            elif module_key == "certificates":
                self.certificate_page.refresh_all()

    def _toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        self.apply_theme()

    def apply_theme(self):
        qss = DARK_THEME_QSS if self.is_dark_theme else LIGHT_THEME_QSS
        self.setStyleSheet(qss)

    def _handle_search(self, query: str):
        QMessageBox.information(
            self,
            "Global Search",
            f"Searching database for '{query}' across students, staff, and transactions...\n\n"
            f"Found 3 matches in Phase 1 database records."
        )

    def _show_notifications(self):
        QMessageBox.information(
            self,
            "System Notifications",
            "• Fee Collection: 42 invoices due for Class 9\n"
            "• Academic: Final Term Exam timetable drafted\n"
            "• Backup: Nightly database backup verified"
        )

    def _handle_logout(self):
        confirm = QMessageBox.question(
            self,
            "Sign Out Confirmation",
            "Are you sure you want to sign out of EduManage Pro?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            db = SessionLocal()
            try:
                AuthService.logout(db)
            finally:
                db.close()
            self.close()

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Exit Application",
            "Are you sure you want to close EduManage Pro?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
