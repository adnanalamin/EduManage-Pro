"""
EduManage Pro - Main Desktop Application Launcher
Initializes PySide6 application, database schema, logging, and initiates the login lifecycle.
"""

import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from app.config.settings import settings
from app.config.logging_config import app_logger, error_logger
from app.database.init_db import init_database
from app.ui.windows.login_window import LoginWindow
from app.ui.windows.setup_wizard import SetupWizard
from app.ui.windows.main_window import MainWindow


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
    # Configure high-DPI attributes for Windows 10/11
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(settings.APP_NAME)
    app.setOrganizationName(settings.ORGANIZATION)

    # Attach global exception catcher
    sys.excepthook = global_exception_handler

    app_logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # 1. Initialize Database & Seed Baseline Tables
    try:
        needs_wizard = init_database()
    except Exception as exc:
        QMessageBox.critical(
            None,
            "Database Initialization Error",
            f"Failed to connect to or initialize local SQLite database:\n{exc}\n\nCheck logs/error.log"
        )
        sys.exit(1)

    # 2. First-Run Setup Wizard if not completed
    if needs_wizard:
        app_logger.info("First run detected. Displaying First-Run Setup Wizard...")
        wizard = SetupWizard()
        if wizard.exec() != SetupWizard.Accepted:
            app_logger.warning("Setup wizard was cancelled by user. Terminating startup.")
            sys.exit(0)

    # 3. Present Secure Login Window
    login_dialog = LoginWindow()
    authenticated_user = None

    def on_login_success(user):
        nonlocal authenticated_user
        authenticated_user = user

    login_dialog.login_successful.connect(on_login_success)

    if login_dialog.exec() == LoginWindow.Accepted and authenticated_user:
        app_logger.info(f"Launching main window for user: {authenticated_user.username}")
        main_win = MainWindow()
        main_win.show()
        sys.exit(app.exec())
    else:
        app_logger.info("Login cancelled or closed by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
