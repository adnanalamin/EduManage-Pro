"""
EduManage Pro - Topbar Widget (PySide6)
Contains Global Search, Active Session indicator, Theme Toggle, Notification trigger, and User Profile.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel, QFrame, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QFont
from app.security.session import session


class TopbarWidget(QWidget):
    search_triggered = Signal(str)
    theme_toggled = Signal()
    logout_requested = Signal()
    notifications_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topbarContainer")
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(16)

        # Global Search input
        self.search_input = QLineEdit()
        self.search_input.setProperty("class", "searchBox")
        self.search_input.setPlaceholderText("🔍 Quick search students, teachers, receipts... (Ctrl+K)")
        self.search_input.setFixedWidth(360)
        self.search_input.returnPressed.connect(self._on_search)
        layout.addWidget(self.search_input)

        layout.addStretch()

        # Session badge
        self.session_badge = QLabel("Academic Year: 2024–2025")
        self.session_badge.setStyleSheet(
            "background-color: #0f172a; color: #38bdf8; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600;"
        )
        layout.addWidget(self.session_badge)

        # Theme toggle button
        self.btn_theme = QPushButton("🌓 Theme")
        self.btn_theme.setCursor(Qt.PointingHandCursor)
        self.btn_theme.setStyleSheet("padding: 6px 12px; background: #334155; border-radius: 6px; font-size: 12px;")
        self.btn_theme.clicked.connect(self.theme_toggled.emit)
        layout.addWidget(self.btn_theme)

        # Notification button
        self.btn_notif = QPushButton("🔔")
        self.btn_notif.setToolTip("Notifications (3 Unread)")
        self.btn_notif.setStyleSheet("padding: 6px 10px; background: #334155; border-radius: 6px; font-size: 14px;")
        self.btn_notif.clicked.connect(self.notifications_requested.emit)
        layout.addWidget(self.btn_notif)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setStyleSheet("color: #475569;")
        layout.addWidget(divider)

        # User profile chip
        user = session.current_user
        display_name = user.full_name if user else "Super Administrator"
        role_name = user.role.display_name if user and user.role else "Super Admin"

        user_col = QHBoxLayout()
        user_col.setSpacing(8)

        avatar_lbl = QLabel("👤")
        avatar_lbl.setStyleSheet("font-size: 16px; background: #2563eb; padding: 4px; border-radius: 12px;")

        info_lbl = QLabel(f"<b>{display_name}</b> <span style='color: #94a3b8;'>({role_name})</span>")
        info_lbl.setStyleSheet("font-size: 12px;")

        user_col.addWidget(avatar_lbl)
        user_col.addWidget(info_lbl)
        layout.addLayout(user_col)

        # Sign out button
        self.btn_logout = QPushButton("Sign Out")
        self.btn_logout.setStyleSheet("padding: 6px 12px; background: #dc2626; color: white; border-radius: 6px; font-size: 12px; font-weight: 600;")
        self.btn_logout.clicked.connect(self.logout_requested.emit)
        layout.addWidget(self.btn_logout)

    def _on_search(self):
        query = self.search_input.text().strip()
        if query:
            self.search_triggered.emit(query)

    def refresh_user_display(self):
        user = session.current_user
        if user:
            role_name = user.role.display_name if user.role else "Super Admin"
            self.session_badge.setText(f"Session: 2024–2025")
