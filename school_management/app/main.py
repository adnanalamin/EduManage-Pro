"""
EduManage Pro - Main Desktop Application Launcher
Initializes PySide6 application, database schema, first-run Super Admin setup,
and enterprise login/logout/timeout authentication loop.
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from app.config.logging_config import app_logger, error_logger
from app.config.settings import settings
from app.database.init_db import init_database
from app.ui.windows.login_window import LoginWindow
from app.ui.windows.main_window import MainWindow
from app.ui.windows.setup_wizard import SetupWizard


def global_exception_handler(exctype, value, tb):
    """Global unhandled exception hook to prevent silent crashes and log to error.log."""
    error_logger.critical("Uncaught desktop exception:", exc_info=(exctype, value, tb))
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("EduManage Pro — Unexpected System Error")
    msg.setText("An unexpected technical error occurred in EduManage Pro.")
    msg.setInformativeText(f"Details: {value}\n\nPlease check logs/error.log or contact system support.")
    msg.exec()


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(settings.APP_NAME)
    app.setOrganizationName(settings.ORGANIZATION)
    sys.excepthook = global_exception_handler

    app_logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # 1. Initialize Database & Seed Baseline Roles/Permissions (zero hardcoded passwords)
    try:
        needs_wizard = init_database()
    except Exception as exc:
        QMessageBox.critical(
            None,
            "Database Initialization Error",
            f"Failed to connect to or initialize database:\n{exc}\n\nCheck logs/error.log",
        )
        sys.exit(1)

    # 2. First-Run Setup Wizard (enforces initial Super Administrator creation)
    if needs_wizard:
        app_logger.info("First run or missing Super Admin detected. Launching Setup Wizard...")
        wizard = SetupWizard()
        if wizard.exec() != SetupWizard.Accepted:
            app_logger.warning("Setup wizard cancelled by user. Terminating startup.")
            sys.exit(0)

    # 3. Enterprise Login -> MainWindow -> Logout / Timeout Re-Login Loop
    notice_msg = ""
    while True:
        login_dialog = LoginWindow(notice_message=notice_msg)
        authenticated_user = None

        def on_login_success(user):
            nonlocal authenticated_user
            authenticated_user = user

        login_dialog.login_successful.connect(on_login_success)

        if login_dialog.exec() != LoginWindow.Accepted or not authenticated_user:
            app_logger.info("Login cancelled or closed by user.")
            sys.exit(0)

        app_logger.info(f"Launching main window for user: {authenticated_user.username}")
        session_reason = None
        main_win = MainWindow()

        def on_session_ended(reason: str):
            nonlocal session_reason
            session_reason = reason

        main_win.session_ended.connect(on_session_ended)
        main_win.show()
        exit_code = app.exec()

        if session_reason == "SESSION_TIMEOUT":
            notice_msg = "Your previous session timed out due to inactivity. Please sign in again."
            continue
        if session_reason == "LOGOUT":
            notice_msg = ""
            continue

        sys.exit(exit_code)


if __name__ == "__main__":
    main()
