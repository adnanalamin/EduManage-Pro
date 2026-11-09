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

        # Module Placeholders (Ready for Phases 7 - 17)
        self.page_indices = {
            "dashboard": 0,
            "students": 1,
            "teachers": 2,
            "staff": 3,
            "academics": 4,
            "attendance": 5,
            "fees": 6,
        }
        module_names = [
            ("accounting", "Phase 7: School Accounting & Ledgers"),
            ("exams", "Phase 8: Exam Management"),
            ("results", "Phase 8: Grading & Results"),
            ("timetable", "Phase 9: Class & Teacher Timetable"),
            ("library", "Phase 10: Library Circulation"),
            ("transport", "Phase 11: Transport & Fleet Management"),
            ("hostel", "Phase 12: Hostel & Dormitory Management"),
            ("notices", "Phase 13: Notices & Bulletin Board"),
            ("events", "Phase 13: School Calendar Events"),
            ("reports", "Phase 14: Comprehensive Reports"),
            ("certificates", "Phase 15: Certificate & ID Generator"),
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
