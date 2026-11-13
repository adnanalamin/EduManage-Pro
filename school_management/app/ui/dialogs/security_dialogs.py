"""
EduManage Pro - Enterprise Security Dialogs (PySide6)
Includes:
- FirstAdminDialog (first-run Super Admin creation)
- ChangePasswordDialog
- ForgotPasswordDialog (offline token redemption workflow)
- CreateUserDialog
- CreateRoleDialog / CloneRoleDialog
- AdminResetResultDialog (displays one-time generated credential once without storing plaintext)
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt

from app.database.connection import SessionLocal
from app.security.hasher import PasswordHasher
from app.services.auth_service import AuthService


class FirstAdminDialog(QDialog):
    """Creates the initial Super Administrator when no active Super Admin exists."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Initial Super Administrator")
        self.setFixedSize(460, 460)
        self.created_username = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("First-Run Super Administrator Setup")
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #3b82f6;")
        subtitle = QLabel(
            "No administrator account exists yet. Create your permanent Super Admin credentials."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)
        self.full_name_input = QLineEdit()
        self.full_name_input.setPlaceholderText("e.g. Principal / System Admin")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("e.g. superadmin")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("admin@yourschool.edu")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Optional phone number")

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Min 8 chars: upper, lower, number, symbol")

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText("Confirm administrator password")

        form.addRow("Full Name*:", self.full_name_input)
        form.addRow("Username*:", self.username_input)
        form.addRow("Email*:", self.email_input)
        form.addRow("Phone:", self.phone_input)
        form.addRow("Password*:", self.password_input)
        form.addRow("Confirm Password*:", self.confirm_input)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_create = QPushButton("Create Super Admin")
        btn_create.setStyleSheet("background-color: #2563eb; color: white; padding: 8px 16px; font-weight: bold;")
        btn_create.clicked.connect(self._on_submit)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_create)
        layout.addLayout(btn_row)

    def _on_submit(self):
        pw = self.password_input.text()
        cpw = self.confirm_input.text()
        if pw != cpw:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match.")
            return

        db = SessionLocal()
        try:
            ok, user, msg = AuthService.create_first_admin(
                db,
                username=self.username_input.text(),
                email=self.email_input.text(),
                full_name=self.full_name_input.text(),
                password=pw,
                phone=self.phone_input.text(),
            )
            if ok and user:
                self.created_username = user.username
                QMessageBox.information(self, "Success", msg)
                self.accept()
            else:
                QMessageBox.warning(self, "Creation Failed", msg)
        finally:
            db.close()


class ChangePasswordDialog(QDialog):
    """Allows an authenticated user to securely update their password."""

    def __init__(self, user_id: int, username: str, force_mode: bool = False, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.username = username
        self.force_mode = force_mode
        self.setWindowTitle("Change Password" if not force_mode else "Password Update Required")
        self.setFixedSize(430, 340)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel(
            f"Update password for '{self.username}'"
            + (" (Required before continuing)" if self.force_mode else "")
        )
        header.setWordWrap(True)
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #3b82f6;")
        layout.addWidget(header)

        policy_lbl = QLabel(
            "Policy: Minimum 8 characters, including uppercase, lowercase, digit, and symbol (!@#$%)."
        )
        policy_lbl.setWordWrap(True)
        policy_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(policy_lbl)

        form = QFormLayout()
        form.setSpacing(10)
        self.old_pw_input = QLineEdit()
        self.old_pw_input.setEchoMode(QLineEdit.Password)
        self.new_pw_input = QLineEdit()
        self.new_pw_input.setEchoMode(QLineEdit.Password)
        self.confirm_pw_input = QLineEdit()
        self.confirm_pw_input.setEchoMode(QLineEdit.Password)

        form.addRow("Current Password*:", self.old_pw_input)
        form.addRow("New Password*:", self.new_pw_input)
        form.addRow("Confirm New*:", self.confirm_pw_input)
        layout.addLayout(form)

        self.show_cb = QCheckBox("Show passwords")
        self.show_cb.toggled.connect(self._toggle_echo)
        layout.addWidget(self.show_cb)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Update Password")
        btn_save.setStyleSheet("background-color: #2563eb; color: white; padding: 8px 14px; font-weight: bold;")
        btn_save.clicked.connect(self._submit)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _toggle_echo(self, checked: bool):
        mode = QLineEdit.Normal if checked else QLineEdit.Password
        self.old_pw_input.setEchoMode(mode)
        self.new_pw_input.setEchoMode(mode)
        self.confirm_pw_input.setEchoMode(mode)

    def _submit(self):
        new_pw = self.new_pw_input.text()
        if new_pw != self.confirm_pw_input.text():
            QMessageBox.warning(self, "Validation Error", "New passwords do not match.")
            return

        db = SessionLocal()
        try:
            ok, msg = AuthService.change_password(
                db, self.user_id, self.old_pw_input.text(), new_pw
            )
            if ok:
                QMessageBox.information(self, "Password Updated", msg)
                self.accept()
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()


class ForgotPasswordDialog(QDialog):
    """
    Token-verified Password Reset dialog on the Login screen.
    Users obtain a single-use expiring token from their Super Administrator (never self-disclosed).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reset Account Password")
        self.setFixedSize(440, 340)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        info = QLabel(
            "Enter the single-use reset token issued by your Super Administrator along with a new strong password."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste single-use reset token")
        self.new_pw_input = QLineEdit()
        self.new_pw_input.setEchoMode(QLineEdit.Password)
        self.confirm_pw_input = QLineEdit()
        self.confirm_pw_input.setEchoMode(QLineEdit.Password)

        form.addRow("Reset Token*:", self.token_input)
        form.addRow("New Password*:", self.new_pw_input)
        form.addRow("Confirm Password*:", self.confirm_pw_input)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_close = QPushButton("Cancel")
        btn_close.clicked.connect(self.reject)
        btn_reset = QPushButton("Reset Password")
        btn_reset.setStyleSheet("background-color: #2563eb; color: white; padding: 8px 14px; font-weight: bold;")
        btn_reset.clicked.connect(self._on_reset)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        btn_row.addWidget(btn_reset)
        layout.addLayout(btn_row)

    def _on_reset(self):
        pw = self.new_pw_input.text()
        if pw != self.confirm_pw_input.text():
            QMessageBox.warning(self, "Mismatch", "New passwords do not match.")
            return

        db = SessionLocal()
        try:
            ok, msg = AuthService.complete_password_reset(
                db, self.token_input.text(), pw
            )
            if ok:
                QMessageBox.information(self, "Reset Complete", msg)
                self.accept()
            else:
                QMessageBox.warning(self, "Reset Failed", msg)
        finally:
            db.close()


class CreateUserDialog(QDialog):
    """Super Admin dialog to provision a new staff/teacher/accountant user."""

    def __init__(self, roles, actor_user_id: int, parent=None):
        super().__init__(parent)
        self.roles = roles
        self.actor_user_id = actor_user_id
        self.setWindowTitle("Create User Account")
        self.setFixedSize(460, 420)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(10)
        self.full_name_input = QLineEdit()
        self.username_input = QLineEdit()
        self.email_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.role_combo = QComboBox()
        for r in self.roles:
            self.role_combo.addItem(f"{r.display_name} ({r.name})", r.id)

        pw_row = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        btn_gen = QPushButton("Generate")
        btn_gen.clicked.connect(self._generate_pw)
        pw_row.addWidget(self.password_input)
        pw_row.addWidget(btn_gen)

        self.show_cb = QCheckBox("Show password")
        self.show_cb.toggled.connect(
            lambda c: self.password_input.setEchoMode(QLineEdit.Normal if c else QLineEdit.Password)
        )
        self.force_change_cb = QCheckBox("Require password change on first login")
        self.force_change_cb.setChecked(True)

        form.addRow("Full Name*:", self.full_name_input)
        form.addRow("Username*:", self.username_input)
        form.addRow("Email*:", self.email_input)
        form.addRow("Phone:", self.phone_input)
        form.addRow("Role*:", self.role_combo)
        form.addRow("Initial Password*:", pw_row)

        layout.addLayout(form)
        layout.addWidget(self.show_cb)
        layout.addWidget(self.force_change_cb)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Create User")
        btn_save.setStyleSheet("background-color: #2563eb; color: white; padding: 8px 14px; font-weight: bold;")
        btn_save.clicked.connect(self._submit)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _generate_pw(self):
        self.password_input.setText(PasswordHasher.generate_temporary_password(14))
        self.show_cb.setChecked(True)

    def _submit(self):
        from app.models.user import User

        db = SessionLocal()
        try:
            actor = db.query(User).filter(User.id == self.actor_user_id).first()
            ok, user, msg = AuthService.create_user(
                db,
                actor_user=actor,
                username=self.username_input.text(),
                email=self.email_input.text(),
                full_name=self.full_name_input.text(),
                password=self.password_input.text(),
                role_id=self.role_combo.currentData(),
                phone=self.phone_input.text(),
                must_change_password=self.force_change_cb.isChecked(),
            )
            if ok:
                QMessageBox.information(self, "User Created", msg)
                self.accept()
            else:
                QMessageBox.warning(self, "Validation Error", msg)
        finally:
            db.close()


class CreateRoleDialog(QDialog):
    """Dialog to create a new custom role or clone an existing role."""

    def __init__(self, source_role=None, parent=None):
        super().__init__(parent)
        self.source_role = source_role
        self.setWindowTitle(
            f"Clone Role: {source_role.display_name}" if source_role else "Create Custom Role"
        )
        self.setFixedSize(420, 260)
        self.role_code = ""
        self.role_display = ""
        self.role_desc = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. senior_accountant")
        self.display_input = QLineEdit()
        self.display_input.setPlaceholderText("e.g. Senior Accountant")
        self.desc_input = QLineEdit()
        if self.source_role:
            self.name_input.setText(f"{self.source_role.name}_copy")
            self.display_input.setText(f"{self.source_role.display_name} Copy")
            self.desc_input.setText(f"Cloned from {self.source_role.display_name}")

        form.addRow("Role Code*:", self.name_input)
        form.addRow("Display Name*:", self.display_input)
        form.addRow("Description:", self.desc_input)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Clone Role" if self.source_role else "Create Role")
        btn_save.setStyleSheet("background-color: #2563eb; color: white; padding: 8px 14px; font-weight: bold;")
        btn_save.clicked.connect(self._on_ok)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _on_ok(self):
        self.role_code = self.name_input.text().strip()
        self.role_display = self.display_input.text().strip()
        self.role_desc = self.desc_input.text().strip()
        if not self.role_code or not self.role_display:
            QMessageBox.warning(self, "Validation Error", "Role code and display name are required.")
            return
        self.accept()


class AdminResetResultDialog(QDialog):
    """Displays a one-time generated temporary password or reset token securely once."""

    def __init__(self, username: str, secret_value: str, label: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{label} Issued")
        self.setFixedSize(460, 220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        lbl = QLabel(
            f"One-time {label} generated for '{username}'.\n"
            "Share this securely with the user. It is NOT saved in plaintext and will not be shown again."
        )
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #f59e0b; font-size: 12px;")
        layout.addWidget(lbl)

        self.val_box = QLineEdit(secret_value)
        self.val_box.setReadOnly(True)
        self.val_box.setStyleSheet("font-family: Consolas, monospace; font-size: 14px; padding: 8px;")
        layout.addWidget(self.val_box)

        btn_row = QHBoxLayout()
        btn_copy = QPushButton("Copy to Clipboard")
        btn_copy.clicked.connect(self._copy)
        btn_ok = QPushButton("Close")
        btn_ok.clicked.connect(self.accept)
        btn_row.addStretch()
        btn_row.addWidget(btn_copy)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _copy(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.val_box.text())
        QMessageBox.information(self, "Copied", "Copied to clipboard.")
