"""
EduManage Pro - Enterprise Security, RBAC Permission Matrix & Settings Page (PySide6)
Replaces the Settings placeholder with full Super Admin controls:
1. User Account Management (create, activate/deactivate, unlock, admin password reset, reset token)
2. Roles & Hierarchical Permission Matrix UI (Module -> Feature -> Action: VIEW..MANAGE, role cloning, global permission disable)
3. Login History & User Activity Audit Viewer
4. Session Timeout & Security Policy Controls
"""

from typing import Dict, List, Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QComboBox,
    QListWidget, QListWidgetItem, QCheckBox, QMessageBox, QFrame, QSpinBox,
    QFormLayout, QSplitter
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import joinedload

from app.config.settings import settings
from app.database.connection import SessionLocal
from app.models.user import User, Role, Permission
from app.security.permissions import ALL_ACTIONS
from app.security.session import session as app_session
from app.services.auth_service import AuthService
from app.ui.dialogs.security_dialogs import (
    AdminResetResultDialog,
    ChangePasswordDialog,
    CreateRoleDialog,
    CreateUserDialog,
)


class SecuritySettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.matrix_checkboxes: Dict[int, QCheckBox] = {}
        self.selected_role_id: Optional[int] = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("Security, Users & Access Control")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f8fafc;")
        sub = QLabel(
            "Enterprise RBAC, Module → Feature → Action Permission Matrix, Account Lifecycle & Login Audit"
        )
        sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        title_col.addWidget(title)
        title_col.addWidget(sub)
        header.addLayout(title_col)
        header.addStretch()

        btn_refresh = QPushButton("↻ Refresh")
        btn_refresh.clicked.connect(self.refresh_all)
        header.addWidget(btn_refresh)
        root.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_users_tab(), "Users & Accounts")
        self.tabs.addTab(self._build_matrix_tab(), "Roles & Permission Matrix")
        self.tabs.addTab(self._build_audit_tab(), "Login History & Activity Audit")
        self.tabs.addTab(self._build_policies_tab(), "My Account & Session Policies")
        root.addWidget(self.tabs)

    # ------------------------------------------------------------------
    # Tab 1: Users & Account Lifecycle
    # ------------------------------------------------------------------
    def _build_users_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        bar = QHBoxLayout()
        self.user_search = QLineEdit()
        self.user_search.setPlaceholderText("Filter by username, name, or email...")
        self.user_search.textChanged.connect(self._load_users)
        bar.addWidget(self.user_search)

        self.btn_add_user = QPushButton("+ Create User")
        self.btn_add_user.setStyleSheet("background-color: #2563eb; color: white; padding: 6px 12px; font-weight: 600;")
        self.btn_add_user.clicked.connect(self._handle_create_user)

        self.btn_toggle_active = QPushButton("Activate / Deactivate")
        self.btn_toggle_active.clicked.connect(self._handle_toggle_user_active)

        self.btn_unlock_user = QPushButton("Unlock")
        self.btn_unlock_user.clicked.connect(self._handle_unlock_user)

        self.btn_reset_pw = QPushButton("Reset Password")
        self.btn_reset_pw.clicked.connect(self._handle_admin_reset_password)

        self.btn_issue_token = QPushButton("Issue Reset Token")
        self.btn_issue_token.clicked.connect(self._handle_issue_reset_token)

        for b in [
            self.btn_add_user,
            self.btn_toggle_active,
            self.btn_unlock_user,
            self.btn_reset_pw,
            self.btn_issue_token,
        ]:
            bar.addWidget(b)
        layout.addLayout(bar)

        self.users_table = QTableWidget(0, 8)
        self.users_table.setHorizontalHeaderLabels(
            ["ID", "Username", "Full Name", "Email", "Role", "Status", "Failed Attempts", "Last Login"]
        )
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setSelectionMode(QTableWidget.SingleSelection)
        self.users_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.users_table)
        return tab

    # ------------------------------------------------------------------
    # Tab 2: Roles & Permission Matrix UI (Module -> Feature -> Action)
    # ------------------------------------------------------------------
    def _build_matrix_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setSpacing(12)

        # Left column: Role selector + create/clone controls
        left = QFrame()
        left.setFixedWidth(250)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(8)

        lbl_roles = QLabel("Roles")
        lbl_roles.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_lay.addWidget(lbl_roles)

        self.roles_list = QListWidget()
        self.roles_list.currentItemChanged.connect(self._on_role_selected)
        left_lay.addWidget(self.roles_list)

        role_btns = QHBoxLayout()
        self.btn_create_role = QPushButton("+ New Role")
        self.btn_create_role.clicked.connect(self._handle_create_role)
        self.btn_clone_role = QPushButton("Clone Role")
        self.btn_clone_role.clicked.connect(self._handle_clone_role)
        role_btns.addWidget(self.btn_create_role)
        role_btns.addWidget(self.btn_clone_role)
        left_lay.addLayout(role_btns)
        layout.addWidget(left)

        # Right column: Hierarchical Permission Matrix
        right = QVBoxLayout()
        right.setSpacing(8)

        filter_bar = QHBoxLayout()
        self.module_filter = QComboBox()
        self.module_filter.addItem("All Modules")
        self.module_filter.currentTextChanged.connect(self._load_permission_matrix)
        filter_bar.addWidget(QLabel("Module:"))
        filter_bar.addWidget(self.module_filter)

        self.btn_select_all_matrix = QPushButton("Check Visible")
        self.btn_select_all_matrix.clicked.connect(lambda: self._bulk_toggle_matrix(True))
        self.btn_clear_matrix = QPushButton("Uncheck Visible")
        self.btn_clear_matrix.clicked.connect(lambda: self._bulk_toggle_matrix(False))
        self.btn_save_matrix = QPushButton("Save Role Permissions")
        self.btn_save_matrix.setStyleSheet("background-color: #16a34a; color: white; padding: 6px 14px; font-weight: bold;")
        self.btn_save_matrix.clicked.connect(self._save_role_permissions)

        filter_bar.addStretch()
        filter_bar.addWidget(self.btn_select_all_matrix)
        filter_bar.addWidget(self.btn_clear_matrix)
        filter_bar.addWidget(self.btn_save_matrix)
        right.addLayout(filter_bar)

        # Global Permission Disable/Enable strip (Super Admin)
        global_bar = QHBoxLayout()
        global_bar.addWidget(QLabel("Global Permission Switch:"))
        self.perm_toggle_combo = QComboBox()
        self.perm_toggle_combo.setMinimumWidth(300)
        global_bar.addWidget(self.perm_toggle_combo)
        self.btn_disable_perm = QPushButton("Disable Permission")
        self.btn_disable_perm.clicked.connect(lambda: self._toggle_global_permission(False))
        self.btn_enable_perm = QPushButton("Enable Permission")
        self.btn_enable_perm.clicked.connect(lambda: self._toggle_global_permission(True))
        global_bar.addWidget(self.btn_disable_perm)
        global_bar.addWidget(self.btn_enable_perm)
        global_bar.addStretch()
        right.addLayout(global_bar)

        # Matrix Columns: Module, Feature, + 10 Actions
        headers = ["Module", "Feature"] + ALL_ACTIONS
        self.matrix_table = QTableWidget(0, len(headers))
        self.matrix_table.setHorizontalHeaderLabels(headers)
        self.matrix_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.matrix_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for col_idx in range(2, len(headers)):
            self.matrix_table.horizontalHeader().setSectionResizeMode(col_idx, QHeaderView.ResizeToContents)
        self.matrix_table.setEditTriggers(QTableWidget.NoEditTriggers)
        right.addWidget(self.matrix_table)

        layout.addLayout(right, 1)
        return tab

    # ------------------------------------------------------------------
    # Tab 3: Login History & Activity Audit
    # ------------------------------------------------------------------
    def _build_audit_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        bar = QHBoxLayout()
        self.audit_user_filter = QLineEdit()
        self.audit_user_filter.setPlaceholderText("Filter by username...")
        self.audit_user_filter.textChanged.connect(self._load_audit_tables)

        self.login_status_filter = QComboBox()
        self.login_status_filter.addItems(
            ["ALL", "SUCCESS", "FAILED_PASSWORD", "FAILED_LOCKED", "FAILED_INACTIVE", "FAILED_UNKNOWN"]
        )
        self.login_status_filter.currentTextChanged.connect(self._load_audit_tables)

        bar.addWidget(QLabel("Username:"))
        bar.addWidget(self.audit_user_filter)
        bar.addWidget(QLabel("Login Status:"))
        bar.addWidget(self.login_status_filter)
        bar.addStretch()
        layout.addLayout(bar)

        splitter = QSplitter(Qt.Vertical)

        self.login_hist_table = QTableWidget(0, 7)
        self.login_hist_table.setHorizontalHeaderLabels(
            ["Login Time (UTC)", "Username", "Status", "Reason", "IP Address", "Workstation", "Logout / Timeout"]
        )
        self.login_hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.login_hist_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.activity_table = QTableWidget(0, 6)
        self.activity_table.setHorizontalHeaderLabels(
            ["Timestamp (UTC)", "Username", "Module", "Action", "Severity", "Description"]
        )
        self.activity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.activity_table.setEditTriggers(QTableWidget.NoEditTriggers)

        splitter.addWidget(self.login_hist_table)
        splitter.addWidget(self.activity_table)
        layout.addWidget(splitter)
        return tab

    # ------------------------------------------------------------------
    # Tab 4: My Account & Session Policies
    # ------------------------------------------------------------------
    def _build_policies_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)

        self.lbl_current_user = QLabel("-")
        self.lbl_current_role = QLabel("-")
        self.lbl_session_status = QLabel("-")

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 480)
        self.timeout_spin.setSuffix(" minutes")
        self.timeout_spin.setValue(app_session.timeout_minutes or settings.SESSION_TIMEOUT_MINUTES)

        btn_apply_timeout = QPushButton("Apply Idle Timeout")
        btn_apply_timeout.clicked.connect(self._apply_session_timeout)

        btn_change_my_pw = QPushButton("Change My Password")
        btn_change_my_pw.setStyleSheet("background-color: #2563eb; color: white; padding: 8px 14px; font-weight: bold;")
        btn_change_my_pw.clicked.connect(self._handle_change_my_password)

        form.addRow("Signed-In User:", self.lbl_current_user)
        form.addRow("Assigned Role:", self.lbl_current_role)
        form.addRow("Max Failed Login Attempts:", QLabel(str(settings.MAX_LOGIN_ATTEMPTS)))
        form.addRow("Account Lockout Duration:", QLabel(f"{settings.LOCKOUT_DURATION_SECONDS} seconds"))
        form.addRow("Idle Session Timeout:", self.timeout_spin)
        form.addRow("", btn_apply_timeout)
        form.addRow("Password Security:", btn_change_my_pw)
        form.addRow("Session Health:", self.lbl_session_status)

        layout.addLayout(form)
        layout.addStretch()
        return tab

    # ------------------------------------------------------------------
    # Data Loading & Actions
    # ------------------------------------------------------------------
    def refresh_all(self):
        self._apply_admin_controls()
        self._load_users()
        self._load_roles_and_modules()
        self._load_audit_tables()
        self._refresh_policy_summary()

    def _apply_admin_controls(self):
        is_super = app_session.is_super_admin()
        can_users = is_super or app_session.has_permission("security.users.MANAGE")
        can_roles = is_super or app_session.has_permission("security.roles.MANAGE")

        for b in [
            self.btn_add_user,
            self.btn_toggle_active,
            self.btn_unlock_user,
            self.btn_reset_pw,
            self.btn_issue_token,
        ]:
            b.setEnabled(can_users)

        for b in [
            self.btn_create_role,
            self.btn_clone_role,
            self.btn_select_all_matrix,
            self.btn_clear_matrix,
            self.btn_save_matrix,
        ]:
            b.setEnabled(can_roles)

        self.btn_disable_perm.setEnabled(is_super)
        self.btn_enable_perm.setEnabled(is_super)

    def _load_users(self):
        search = self.user_search.text().strip().lower()
        db = SessionLocal()
        try:
            users = (
                db.query(User)
                .options(joinedload(User.role))
                .filter(User.is_deleted == False)
                .order_by(User.id.asc())
                .all()
            )
            filtered = [
                u
                for u in users
                if not search
                or search in u.username.lower()
                or search in u.full_name.lower()
                or search in u.email.lower()
            ]
            self.users_table.setRowCount(len(filtered))
            for r_idx, u in enumerate(filtered):
                status_text = "Active" if u.is_active else "Deactivated"
                if u.locked_until:
                    status_text += " (Locked)"
                vals = [
                    str(u.id),
                    u.username,
                    u.full_name,
                    u.email,
                    u.role.display_name if u.role else "-",
                    status_text,
                    str(u.failed_login_attempts),
                    u.last_login_at.strftime("%Y-%m-%d %H:%M") if u.last_login_at else "Never",
                ]
                for c_idx, val in enumerate(vals):
                    item = QTableWidgetItem(val)
                    item.setData(Qt.UserRole, u.id)
                    self.users_table.setItem(r_idx, c_idx, item)
        finally:
            db.close()

    def _selected_user_id(self) -> Optional[int]:
        row = self.users_table.currentRow()
        if row < 0:
            return None
        item = self.users_table.item(row, 0)
        return int(item.text()) if item else None

    def _load_roles_and_modules(self):
        db = SessionLocal()
        try:
            roles = (
                db.query(Role)
                .options(joinedload(Role.permissions))
                .order_by(Role.id.asc())
                .all()
            )
            self.roles_list.blockSignals(True)
            self.roles_list.clear()
            selected_row = 0
            for idx, r in enumerate(roles):
                tag = "System" if r.is_system_role else "Custom"
                item = QListWidgetItem(f"{r.display_name} [{tag}] ({len(r.permissions)})")
                item.setData(Qt.UserRole, r.id)
                self.roles_list.addItem(item)
                if self.selected_role_id == r.id:
                    selected_row = idx
            self.roles_list.blockSignals(False)
            if roles:
                self.roles_list.setCurrentRow(selected_row)
                self.selected_role_id = self.roles_list.currentItem().data(Qt.UserRole)

            perms = db.query(Permission).order_by(Permission.module.asc(), Permission.feature.asc()).all()
            modules = sorted({p.module for p in perms})
            current_mod = self.module_filter.currentText()
            self.module_filter.blockSignals(True)
            self.module_filter.clear()
            self.module_filter.addItem("All Modules")
            for m in modules:
                self.module_filter.addItem(m)
            idx_mod = self.module_filter.findText(current_mod)
            if idx_mod >= 0:
                self.module_filter.setCurrentIndex(idx_mod)
            self.module_filter.blockSignals(False)

            self.perm_toggle_combo.clear()
            for p in perms:
                state_lbl = "Enabled" if p.is_active else "DISABLED"
                self.perm_toggle_combo.addItem(f"[{state_lbl}] {p.code} ({p.feature})", p.id)
        finally:
            db.close()
        self._load_permission_matrix()

    def _on_role_selected(self, current: Optional[QListWidgetItem], _prev):
        if current:
            self.selected_role_id = current.data(Qt.UserRole)
            self._load_permission_matrix()

    def _load_permission_matrix(self):
        self.matrix_checkboxes.clear()
        self.matrix_table.setRowCount(0)
        if not self.selected_role_id:
            return

        mod_filter = self.module_filter.currentText()
        db = SessionLocal()
        try:
            role = (
                db.query(Role)
                .options(joinedload(Role.permissions))
                .filter(Role.id == self.selected_role_id)
                .first()
            )
            if not role:
                return
            assigned_ids = {p.id for p in role.permissions}
            is_super_role = role.name == "super_admin"

            q = db.query(Permission).order_by(Permission.module.asc(), Permission.feature.asc())
            if mod_filter and mod_filter != "All Modules":
                q = q.filter(Permission.module == mod_filter)
            perms = q.all()

            grouped: Dict[Tuple[str, str], Dict[str, Permission]] = {}
            for p in perms:
                key = (p.module, p.feature)
                grouped.setdefault(key, {})[p.action.upper()] = p

            rows = sorted(grouped.items(), key=lambda kv: (kv[0][0], kv[0][1]))
            self.matrix_table.setRowCount(len(rows))
            for r_idx, ((mod, feat), action_map) in enumerate(rows):
                self.matrix_table.setItem(r_idx, 0, QTableWidgetItem(mod))
                self.matrix_table.setItem(r_idx, 1, QTableWidgetItem(feat))
                for a_idx, action_name in enumerate(ALL_ACTIONS):
                    col_idx = 2 + a_idx
                    perm = action_map.get(action_name)
                    if not perm:
                        na_item = QTableWidgetItem("—")
                        na_item.setTextAlignment(Qt.AlignCenter)
                        na_item.setForeground(Qt.gray)
                        self.matrix_table.setItem(r_idx, col_idx, na_item)
                        continue

                    cb = QCheckBox()
                    cb.setChecked(is_super_role or (perm.id in assigned_ids))
                    cb.setEnabled((not is_super_role) and perm.is_active)
                    cb.setToolTip(
                        f"{perm.code} ({'ACTIVE' if perm.is_active else 'GLOBALLY DISABLED'})"
                    )
                    cell_w = QWidget()
                    cell_lay = QHBoxLayout(cell_w)
                    cell_lay.setContentsMargins(0, 0, 0, 0)
                    cell_lay.setAlignment(Qt.AlignCenter)
                    cell_lay.addWidget(cb)
                    self.matrix_table.setCellWidget(r_idx, col_idx, cell_w)
                    self.matrix_checkboxes[perm.id] = cb
        finally:
            db.close()

    def _bulk_toggle_matrix(self, checked: bool):
        for cb in self.matrix_checkboxes.values():
            if cb.isEnabled():
                cb.setChecked(checked)

    def _save_role_permissions(self):
        if not self.selected_role_id or not app_session.current_user:
            return
        db = SessionLocal()
        try:
            actor = db.query(User).options(joinedload(User.role)).filter(
                User.id == app_session.current_user.id
            ).first()
            role = db.query(Role).options(joinedload(Role.permissions)).filter(
                Role.id == self.selected_role_id
            ).first()
            if not role:
                return
            if role.name == "super_admin":
                QMessageBox.information(self, "Super Admin", "Super Admin inherently holds all system permissions.")
                return

            # Preserve permissions outside current filtered view while updating visible ones
            current_ids = {p.id for p in role.permissions}
            for perm_id, cb in self.matrix_checkboxes.items():
                if cb.isChecked():
                    current_ids.add(perm_id)
                else:
                    current_ids.discard(perm_id)

            ok, msg = AuthService.assign_role_permissions(
                db, actor, self.selected_role_id, sorted(current_ids)
            )
            if ok:
                QMessageBox.information(self, "Saved", msg)
                self._load_roles_and_modules()
            else:
                QMessageBox.warning(self, "Permission Denied", msg)
        finally:
            db.close()

    def _toggle_global_permission(self, enabled: bool):
        perm_id = self.perm_toggle_combo.currentData()
        if not perm_id or not app_session.current_user:
            return
        db = SessionLocal()
        try:
            actor = db.query(User).options(joinedload(User.role)).filter(
                User.id == app_session.current_user.id
            ).first()
            ok, msg = AuthService.set_permission_enabled(db, actor, perm_id, enabled)
            if ok:
                QMessageBox.information(self, "Updated", msg)
                self._load_roles_and_modules()
            else:
                QMessageBox.warning(self, "Denied", msg)
        finally:
            db.close()

    def _handle_create_role(self):
        if not app_session.current_user:
            return
        dlg = CreateRoleDialog(parent=self)
        if dlg.exec() == CreateRoleDialog.Accepted:
            db = SessionLocal()
            try:
                actor = db.query(User).options(joinedload(User.role)).filter(
                    User.id == app_session.current_user.id
                ).first()
                ok, role, msg = AuthService.create_role(
                    db, actor, dlg.role_code, dlg.role_display, dlg.role_desc
                )
                if ok and role:
                    self.selected_role_id = role.id
                    QMessageBox.information(self, "Role Created", msg)
                    self._load_roles_and_modules()
                else:
                    QMessageBox.warning(self, "Error", msg)
            finally:
                db.close()

    def _handle_clone_role(self):
        if not self.selected_role_id or not app_session.current_user:
            return
        db = SessionLocal()
        try:
            src = db.query(Role).filter(Role.id == self.selected_role_id).first()
            if not src:
                return
            dlg = CreateRoleDialog(source_role=src, parent=self)
            if dlg.exec() == CreateRoleDialog.Accepted:
                actor = db.query(User).options(joinedload(User.role)).filter(
                    User.id == app_session.current_user.id
                ).first()
                ok, cloned, msg = AuthService.clone_role(
                    db, actor, src.id, dlg.role_code, dlg.role_display, dlg.role_desc
                )
                if ok and cloned:
                    self.selected_role_id = cloned.id
                    QMessageBox.information(self, "Role Cloned", msg)
                    self._load_roles_and_modules()
                else:
                    QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()

    def _handle_create_user(self):
        if not app_session.current_user:
            return
        db = SessionLocal()
        try:
            roles = db.query(Role).filter(Role.is_active == True).order_by(Role.id.asc()).all()
        finally:
            db.close()
        dlg = CreateUserDialog(roles, app_session.current_user.id, parent=self)
        if dlg.exec() == CreateUserDialog.Accepted:
            self._load_users()

    def _handle_toggle_user_active(self):
        uid = self._selected_user_id()
        if not uid or not app_session.current_user:
            QMessageBox.information(self, "Select User", "Please select a user row first.")
            return
        db = SessionLocal()
        try:
            target = db.query(User).filter(User.id == uid).first()
            actor = db.query(User).options(joinedload(User.role)).filter(
                User.id == app_session.current_user.id
            ).first()
            if not target:
                return
            ok, msg = AuthService.set_user_active(db, actor, target.id, not target.is_active)
            if ok:
                QMessageBox.information(self, "Account Updated", msg)
                self._load_users()
            else:
                QMessageBox.warning(self, "Action Blocked", msg)
        finally:
            db.close()

    def _handle_unlock_user(self):
        uid = self._selected_user_id()
        if not uid or not app_session.current_user:
            return
        db = SessionLocal()
        try:
            actor = db.query(User).options(joinedload(User.role)).filter(
                User.id == app_session.current_user.id
            ).first()
            ok, msg = AuthService.unlock_user(db, actor, uid)
            if ok:
                QMessageBox.information(self, "Unlocked", msg)
                self._load_users()
            else:
                QMessageBox.warning(self, "Denied", msg)
        finally:
            db.close()

    def _handle_admin_reset_password(self):
        uid = self._selected_user_id()
        if not uid or not app_session.current_user:
            QMessageBox.information(self, "Select User", "Please select a user row first.")
            return
        db = SessionLocal()
        try:
            target = db.query(User).filter(User.id == uid).first()
            actor = db.query(User).options(joinedload(User.role)).filter(
                User.id == app_session.current_user.id
            ).first()
            if not target:
                return
            ok, temp_pw, msg = AuthService.admin_reset_password(db, actor, uid)
            if ok and temp_pw:
                AdminResetResultDialog(target.username, temp_pw, "Temporary Password", self).exec()
                self._load_users()
            else:
                QMessageBox.warning(self, "Reset Failed", msg)
        finally:
            db.close()

    def _handle_issue_reset_token(self):
        uid = self._selected_user_id()
        if not uid or not app_session.current_user:
            QMessageBox.information(self, "Select User", "Please select a user row first.")
            return
        db = SessionLocal()
        try:
            target = db.query(User).filter(User.id == uid).first()
            if not target:
                return
            ok, raw_token, msg = AuthService.request_password_reset(
                db, target.username, actor_username=app_session.current_user.username
            )
            if ok and raw_token:
                AdminResetResultDialog(target.username, raw_token, "Single-Use Reset Token", self).exec()
            else:
                QMessageBox.warning(self, "Token Failed", msg)
        finally:
            db.close()

    def _load_audit_tables(self):
        uname = self.audit_user_filter.text().strip()
        status = self.login_status_filter.currentText()
        db = SessionLocal()
        try:
            hist_rows = AuthService.get_login_history(db, username=uname, status=status, limit=150)
            self.login_hist_table.setRowCount(len(hist_rows))
            for idx, h in enumerate(hist_rows):
                vals = [
                    h.login_at.strftime("%Y-%m-%d %H:%M:%S") if h.login_at else "-",
                    h.username_attempted,
                    h.status,
                    h.failure_reason or "—",
                    h.ip_address or "-",
                    h.workstation or "-",
                    h.logout_at.strftime("%Y-%m-%d %H:%M:%S") if h.logout_at else "Active / N/A",
                ]
                for c, v in enumerate(vals):
                    self.login_hist_table.setItem(idx, c, QTableWidgetItem(v))

            logs = AuthService.get_activity_logs(db, username=uname, limit=150)
            self.activity_table.setRowCount(len(logs))
            for idx, a in enumerate(logs):
                vals = [
                    a.created_at.strftime("%Y-%m-%d %H:%M:%S") if a.created_at else "-",
                    a.username,
                    a.module,
                    a.action,
                    a.severity,
                    a.description,
                ]
                for c, v in enumerate(vals):
                    self.activity_table.setItem(idx, c, QTableWidgetItem(v))
        finally:
            db.close()

    def _refresh_policy_summary(self):
        user = app_session.current_user
        if user:
            self.lbl_current_user.setText(f"{user.full_name} ({user.username})")
            self.lbl_current_role.setText(user.role.display_name if user.role else "-")
            rem = app_session.remaining_seconds()
            rem_text = f"Active ({rem // 60}m {rem % 60}s idle limit left)" if rem is not None else "Active (No timeout)"
            self.lbl_session_status.setText(rem_text)

    def _apply_session_timeout(self):
        minutes = self.timeout_spin.value()
        app_session.timeout_minutes = minutes
        settings.SESSION_TIMEOUT_MINUTES = minutes
        self._refresh_policy_summary()
        QMessageBox.information(self, "Policy Updated", f"Idle session timeout set to {minutes} minutes.")

    def _handle_change_my_password(self):
        user = app_session.current_user
        if not user:
            return
        ChangePasswordDialog(user.id, user.username, parent=self).exec()
