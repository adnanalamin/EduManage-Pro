"""
EduManage Pro - Desktop Login Window (PySide6)
Enterprise Authentication UI:
- Clean username/email & masked password entry (zero hardcoded credentials)
- Show/Hide toggle
- First-run admin creation trigger if no active Super Admin exists
- Real-time lockout countdown
- Token-verified password reset dialog
- Mandatory password change prompt when must_change_password is flagged
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from app.config.settings import settings
from app.database.connection import SessionLocal
from app.services.auth_service import AuthService
from app.ui.dialogs.security_dialogs import (
    ChangePasswordDialog,
    FirstAdminDialog,
    ForgotPasswordDialog,
)


class LoginWindow(QDialog):
    login_successful = Signal(object)  # Emits User object

    def __init__(self, parent=None, notice_message: str = ""):
        super().__init__(parent)
        self.setWindowTitle("EduManage Pro — Enterprise Sign In")
        self.setFixedSize(440, 560)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.remaining_lockout = 0
        self.lockout_timer = QTimer(self)
        self.lockout_timer.timeout.connect(self._update_lockout)

        self._build_ui()
        if notice_message:
            self.error_label.setText(notice_message)
            self.error_label.show()
        self._check_admin_presence()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 40, 36, 40)
        layout.setSpacing(14)

        # Header Branding
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        brand_label = QLabel("EduManage Pro")
        brand_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        brand_label.setAlignment(Qt.AlignCenter)
        brand_label.setStyleSheet("color: #3b82f6;")

        sub_label = QLabel("Enterprise School Management System")
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setStyleSheet("color: #94a3b8; font-size: 12px; margin-bottom: 10px;")

        header_layout.addWidget(brand_label)
        header_layout.addWidget(sub_label)
        layout.addLayout(header_layout)

        # First-run notice banner (shown only if 0 active super admins exist)
        self.setup_banner = QFrame()
        self.setup_banner.setStyleSheet(
            "background-color: #1e293b; border: 1px solid #f59e0b; border-radius: 6px; padding: 8px;"
        )
        sb_layout = QVBoxLayout(self.setup_banner)
        sb_layout.setSpacing(6)
        sb_lbl = QLabel("No active Super Administrator configured. Create your initial admin account:")
        sb_lbl.setWordWrap(True)
        sb_lbl.setStyleSheet("color: #fbbf24; font-size: 12px;")
        self.btn_create_first_admin = QPushButton("Create Super Administrator")
        self.btn_create_first_admin.setStyleSheet(
            "background-color: #f59e0b; color: #0f172a; font-weight: bold; padding: 6px; border-radius: 4px;"
        )
        self.btn_create_first_admin.clicked.connect(self._open_first_admin_dialog)
        sb_layout.addWidget(sb_lbl)
        sb_layout.addWidget(self.btn_create_first_admin)
        self.setup_banner.hide()
        layout.addWidget(self.setup_banner)

        # Error notification container
        self.error_label = QLabel("")
        self.error_label.setStyleSheet(
            "color: #ef4444; background: #450a0a; border: 1px solid #7f1d1d; "
            "border-radius: 6px; padding: 8px; font-size: 12px;"
        )
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Username / Email input (never pre-filled with credentials)
        u_label = QLabel("Username or Email")
        u_label.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username or registered email")
        layout.addWidget(u_label)
        layout.addWidget(self.username_input)

        # Password input (never pre-filled)
        p_label = QLabel("Password")
        p_label.setStyleSheet("font-weight: 600; color: #cbd5e1;")

        pass_row = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.returnPressed.connect(self._attempt_login)

        self.btn_toggle_pass = QPushButton("Show")
        self.btn_toggle_pass.setFixedWidth(60)
        self.btn_toggle_pass.setStyleSheet(
            "padding: 8px; background: #334155; border-radius: 6px; font-size: 11px;"
        )
        self.btn_toggle_pass.clicked.connect(self._toggle_password_visibility)

        pass_row.addWidget(self.password_input)
        pass_row.addWidget(self.btn_toggle_pass)

        layout.addWidget(p_label)
        layout.addLayout(pass_row)

        # Remember username & Reset Password workflow
        extra_row = QHBoxLayout()
        self.remember_checkbox = QCheckBox("Remember username")
        self.remember_checkbox.setChecked(False)
        self.remember_checkbox.setStyleSheet("color: #94a3b8; font-size: 12px;")

        btn_forgot = QPushButton("Reset with token")
        btn_forgot.setStyleSheet(
            "background: transparent; color: #60a5fa; border: none; font-size: 12px; text-decoration: underline;"
        )
        btn_forgot.clicked.connect(self._handle_forgot_password)

        extra_row.addWidget(self.remember_checkbox)
        extra_row.addStretch()
        extra_row.addWidget(btn_forgot)
        layout.addLayout(extra_row)

        layout.addSpacing(8)

        # Sign In Button
        self.btn_signin = QPushButton("Sign In")
        self.btn_signin.setStyleSheet(
            "background-color: #2563eb; color: #ffffff; padding: 12px; "
            "border-radius: 8px; font-weight: bold; font-size: 14px;"
        )
        self.btn_signin.clicked.connect(self._attempt_login)
        layout.addWidget(self.btn_signin)

        sec_note = QLabel(
            f"Protected by bcrypt hashing, {settings.MAX_LOGIN_ATTEMPTS}-attempt lockout, and activity auditing."
        )
        sec_note.setAlignment(Qt.AlignCenter)
        sec_note.setWordWrap(True)
        sec_note.setStyleSheet("color: #64748b; font-size: 11px; margin-top: 6px;")
        layout.addWidget(sec_note)
        layout.addStretch()

    def _check_admin_presence(self):
        db = SessionLocal()
        try:
            has_admin = AuthService.has_super_admin(db)
            if not has_admin:
                self.setup_banner.show()
            else:
                self.setup_banner.hide()
        finally:
            db.close()

    def _open_first_admin_dialog(self):
        dlg = FirstAdminDialog(self)
        if dlg.exec() == FirstAdminDialog.Accepted:
            self._check_admin_presence()
            if dlg.created_username:
                self.username_input.setText(dlg.created_username)
                self.password_input.setFocus()

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
                self.password_input.clear()

                # Force immediate password change if flagged by admin reset or legacy migration
                if getattr(user, "must_change_password", False) or getattr(user, "is_default_password", False):
                    cp_dlg = ChangePasswordDialog(
                        user.id, user.username, force_mode=True, parent=self
                    )
                    if cp_dlg.exec() != ChangePasswordDialog.Accepted:
                        AuthService.logout(db, reason="LOGOUT")
                        self.error_label.setText("Password update is required before entering the system.")
                        self.error_label.show()
                        return

                self.login_successful.emit(user)
                self.accept()
            else:
                self.error_label.setText(message)
                self.error_label.show()
                if "locked" in message.lower():
                    self.remaining_lockout = settings.LOCKOUT_DURATION_SECONDS
                    self.btn_signin.setEnabled(False)
                    self.lockout_timer.start(1000)
        finally:
            db.close()

    def _update_lockout(self):
        self.remaining_lockout -= 1
        if self.remaining_lockout <= 0:
            self.lockout_timer.stop()
            self.btn_signin.setEnabled(True)
            self.btn_signin.setText("Sign In")
            self.error_label.hide()
        else:
            self.btn_signin.setText(f"Locked ({self.remaining_lockout}s)")

    def _handle_forgot_password(self):
        dlg = ForgotPasswordDialog(self)
        dlg.exec()
