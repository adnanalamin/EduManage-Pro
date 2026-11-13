"""
EduManage Pro - Main Desktop Window (PySide6)
Combines Sidebar, Topbar, Stacked Page Router, RBAC Module Guarding,
Idle Session Timeout Enforcement, and Enterprise Security Console.
"""

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QMessageBox
)
from PySide6.QtCore import Qt, QEvent, QTimer, Signal

from app.database.connection import SessionLocal
from app.security.session import session
from app.services.auth_service import AuthService
from app.ui.dialogs.security_dialogs import ChangePasswordDialog
from app.ui.pages.academic_management_page import AcademicManagementPage
from app.ui.pages.accounting_page import AccountingPage
from app.ui.pages.attendance_page import AttendancePage
from app.ui.pages.certificate_page import CertificatePage
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.exam_management_page import ExamManagementPage
from app.ui.pages.fees_management_page import FeesManagementPage
from app.ui.pages.hostel_page import HostelPage
from app.ui.pages.library_page import LibraryPage
from app.ui.pages.notice_page import NoticePage
from app.ui.pages.reports_page import ReportsPage
from app.ui.pages.security_settings_page import SecuritySettingsPage
from app.ui.pages.staff_management_page import StaffManagementPage
from app.ui.pages.student_management_page import StudentManagementPage
from app.ui.pages.teacher_management_page import TeacherManagementPage
from app.ui.pages.timetable_page import TimetablePage
from app.ui.pages.transport_page import TransportPage
from app.ui.themes.styles import DARK_THEME_QSS, LIGHT_THEME_QSS
from app.ui.widgets.sidebar import SidebarWidget
from app.ui.widgets.topbar import TopbarWidget


class MainWindow(QMainWindow):
    session_ended = Signal(str)  # Emits "LOGOUT" or "SESSION_TIMEOUT"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("EduManage Pro — School Management System (Desktop)")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)
        self.is_dark_theme = True
        self._closing_for_session_end = False

        self._build_ui()
        self.apply_theme()
        self.sidebar.apply_permissions()
        self.topbar.refresh_user_display()

        # Monitor user activity & enforce idle session timeout
        app_inst = QApplication.instance()
        if app_inst:
            app_inst.installEventFilter(self)

        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._check_session_timeout)
        self._idle_timer.start(15000)

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
        self.topbar.password_change_requested.connect(self._handle_change_password)
        self.topbar.search_triggered.connect(self._handle_search)
        self.topbar.notifications_requested.connect(self._show_notifications)
        right_layout.addWidget(self.topbar)

        # Stacked Pages
        self.stack = QStackedWidget()

        self.dashboard_page = DashboardPage(self)
        self.stack.addWidget(self.dashboard_page)

        self.student_page = StudentManagementPage(self)
        self.stack.addWidget(self.student_page)

        self.teacher_page = TeacherManagementPage(self)
        self.stack.addWidget(self.teacher_page)

        self.staff_page = StaffManagementPage(self)
        self.stack.addWidget(self.staff_page)

        self.academic_page = AcademicManagementPage(self)
        self.stack.addWidget(self.academic_page)

        self.attendance_page = AttendancePage(self)
        self.stack.addWidget(self.attendance_page)

        self.fees_page = FeesManagementPage(self)
        self.stack.addWidget(self.fees_page)

        self.accounting_page = AccountingPage(self)
        self.stack.addWidget(self.accounting_page)

        self.exam_page = ExamManagementPage(self)
        self.stack.addWidget(self.exam_page)

        self.timetable_page = TimetablePage(self)
        self.stack.addWidget(self.timetable_page)

        self.library_page = LibraryPage(self)
        self.stack.addWidget(self.library_page)

        self.transport_page = TransportPage(self)
        self.stack.addWidget(self.transport_page)

        self.hostel_page = HostelPage(self)
        self.stack.addWidget(self.hostel_page)

        self.notice_page = NoticePage(self)
        self.stack.addWidget(self.notice_page)

        self.reports_page = ReportsPage(self, db_session=SessionLocal())
        self.stack.addWidget(self.reports_page)

        self.certificate_page = CertificatePage(self, db_session=SessionLocal())
        self.stack.addWidget(self.certificate_page)

        self.settings_page = SecuritySettingsPage(self)
        self.stack.addWidget(self.settings_page)

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
            "settings": 16,
        }

        right_layout.addWidget(self.stack)
        root_layout.addWidget(right_column)

    def eventFilter(self, watched, event):
        if event.type() in (
            QEvent.MouseButtonPress,
            QEvent.KeyPress,
            QEvent.MouseMove,
            QEvent.Wheel,
        ):
            session.touch()
        return super().eventFilter(watched, event)

    def _check_session_timeout(self):
        if session.current_user and session.is_expired():
            self._idle_timer.stop()
            db = SessionLocal()
            try:
                AuthService.logout(db, reason="SESSION_TIMEOUT")
            finally:
                db.close()
            self._closing_for_session_end = True
            QMessageBox.warning(
                self,
                "Session Timed Out",
                "Your session expired due to inactivity. Please sign in again.",
            )
            self.session_ended.emit("SESSION_TIMEOUT")
            self.close()
        else:
            self.topbar.refresh_user_display()

    def _on_navigation(self, module_key: str):
        if not session.can_access_sidebar_module(module_key):
            QMessageBox.warning(
                self,
                "Access Denied",
                f"You do not have permission to access the '{module_key}' module.",
            )
            return

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
            elif module_key == "settings":
                self.settings_page.refresh_all()

    def _toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        self.apply_theme()

    def apply_theme(self):
        qss = DARK_THEME_QSS if self.is_dark_theme else LIGHT_THEME_QSS
        self.setStyleSheet(qss)

    def _handle_change_password(self):
        user = session.current_user
        if not user:
            return
        ChangePasswordDialog(user.id, user.username, parent=self).exec()

    def _handle_search(self, query: str):
        QMessageBox.information(
            self,
            "Global Search",
            f"Searching database for '{query}' across authorized modules...",
        )

    def _show_notifications(self):
        QMessageBox.information(
            self,
            "System Notifications",
            "• Security: RBAC permission matrix & login audit active\n"
            "• Fee Collection: Check Fees & Billing for pending dues\n"
            "• Backup: Verify latest database snapshot in Settings",
        )

    def _handle_logout(self):
        confirm = QMessageBox.question(
            self,
            "Sign Out Confirmation",
            "Are you sure you want to sign out of EduManage Pro?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self._idle_timer.stop()
            db = SessionLocal()
            try:
                AuthService.logout(db, reason="LOGOUT")
            finally:
                db.close()
            self._closing_for_session_end = True
            self.session_ended.emit("LOGOUT")
            self.close()

    def closeEvent(self, event):
        if self._closing_for_session_end:
            event.accept()
            return
        reply = QMessageBox.question(
            self,
            "Exit Application",
            "Are you sure you want to close EduManage Pro?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._idle_timer.stop()
            if session.current_user:
                db = SessionLocal()
                try:
                    AuthService.logout(db, reason="LOGOUT")
                finally:
                    db.close()
            event.accept()
        else:
            event.ignore()
