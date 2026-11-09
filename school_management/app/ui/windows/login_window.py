"""
EduManage Pro - Desktop Login Window (PySide6)
Features:
- Username/Email field
- Password with Show/Hide toggle
- Remember Me option
- Real-time lock-out countdown handling
- Forgot password dialog
- Direct database verification with bcrypt
"""

import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QMessageBox, QFrame, QWidget
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QFont
from app.database.connection import SessionLocal
from app.services.auth_service import AuthService
from app.models.user import User


class LoginWindow(QDialog):
    login_successful = Signal(object)  # Emits User object

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EduManage Pro — Sign In")
        self.setFixedSize(440, 560)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.remaining_lockout = 0
        self.lockout_timer = QTimer(self)
        self.lockout_timer.timeout.connect(self._update_lockout)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 40, 36, 40)
        layout.setSpacing(16)

        # Header Branding
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        brand_label = QLabel("EduManage Pro")
        brand_font = QFont("Segoe UI", 20, QFont.Bold)
        brand_label.setFont(brand_font)
        brand_label.setAlignment(Qt.AlignCenter)
        brand_label.setStyleSheet("color: #3b82f6;")

        sub_label = QLabel("Complete School Management System")
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setStyleSheet("color: #94a3b8; font-size: 12px; margin-bottom: 12px;")

        header_layout.addWidget(brand_label)
        header_layout.addWidget(sub_label)
        layout.addLayout(header_layout)

        # Error notification container
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ef4444; background: #450a0a; border: 1px solid #7f1d1d; border-radius: 6px; padding: 8px; font-size: 12px;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Username / Email input
        u_label = QLabel("Username or Email")
        u_label.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("e.g. admin or admin@school.local")
        self.username_input.setText("admin")  # Default seed
        layout.addWidget(u_label)
        layout.addWidget(self.username_input)

        # Password input
        p_label = QLabel("Password")
        p_label.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        
        pass_row = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your secure password")
        self.password_input.setText("Admin@123")  # Default seed

        self.btn_toggle_pass = QPushButton("Show")
        self.btn_toggle_pass.setFixedWidth(60)
        self.btn_toggle_pass.setStyleSheet("padding: 8px; background: #334155; border-radius: 6px; font-size: 11px;")
        self.btn_toggle_pass.clicked.connect(self._toggle_password_visibility)

        pass_row.addWidget(self.password_input)
        pass_row.addWidget(self.btn_toggle_pass)

        layout.addWidget(p_label)
        layout.addLayout(pass_row)

        # Remember me & Forgot Password
        extra_row = QHBoxLayout()
        self.remember_checkbox = QCheckBox("Remember username")
        self.remember_checkbox.setChecked(True)
        self.remember_checkbox.setStyleSheet("color: #94a3b8; font-size: 12px;")

        btn_forgot = QPushButton("Forgot password?")
        btn_forgot.setStyleSheet("background: transparent; color: #60a5fa; border: none; font-size: 12px; text-decoration: underline;")
        btn_forgot.clicked.connect(self._handle_forgot_password)

        extra_row.addWidget(self.remember_checkbox)
        extra_row.addStretch()
        extra_row.addWidget(btn_forgot)
        layout.addLayout(extra_row)

        layout.addSpacing(10)

        # Sign In Button
        self.btn_signin = QPushButton("Sign In to Dashboard")
        self.btn_signin.setStyleSheet(
            "background-color: #2563eb; color: #ffffff; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 14px;"
        )
        self.btn_signin.clicked.connect(self._attempt_login)
        layout.addWidget(self.btn_signin)

        # Demo Credentials hint
        hint_frame = QFrame()
        hint_frame.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 8px;")
        hint_layout = QVBoxLayout(hint_frame)
        hint_layout.setContentsMargins(6, 6, 6, 6)
        hint_text = QLabel("Default Super Admin Credentials:\nUsername: admin  |  Password: Admin@123")
        hint_text.setStyleSheet("color: #94a3b8; font-size: 11px;")
        hint_layout.addWidget(hint_text)
        layout.addWidget(hint_frame)

        layout.addStretch()

    def _toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.Password:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_pass.setText("Hide")
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.btn_toggle_pass.setText("Show")

    def _attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.error_label.setText("Please enter both username/email and password.")
            self.error_label.show()
            return

        db = SessionLocal()
        try:
            success, user, message = AuthService.authenticate(db, username, password)
            if success and user:
                self.error_label.hide()
                self.login_successful.emit(user)
                self.accept()
            else:
                self.error_label.setText(message)
                self.error_label.show()
                if "locked for" in message.lower():
                    self.remaining_lockout = 60
                    self.btn_signin.setEnabled(False)
                    self.lockout_timer.start(1000)
        finally:
            db.close()

    def _update_lockout(self):
        self.remaining_lockout -= 1
        if self.remaining_lockout <= 0:
            self.lockout_timer.stop()
            self.btn_signin.setEnabled(True)
            self.btn_signin.setText("Sign In to Dashboard")
            self.error_label.hide()
        else:
            self.btn_signin.setText(f"Locked ({self.remaining_lockout}s)")

    def _handle_forgot_password(self):
        QMessageBox.information(
            self,
            "Reset Password Assistance",
            "To reset your administrator or staff account password offline:\n\n"
            "1. Please contact your Super Administrator directly.\n"
            "2. Or launch EduManage Pro with '--reset-admin' flag to restore emergency access.\n\n"
            "For assistance: contact@edumanage.local"
        )
