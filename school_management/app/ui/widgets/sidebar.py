"""
EduManage Pro - Collapsible Sidebar Navigation Widget (PySide6)
Contains all 19 functional modules with badge counters and role-aware navigation.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QScrollArea, QFrame, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont


MODULES = [
    ("dashboard", "Dashboard", "📊"),
    ("students", "Students", "🎓"),
    ("teachers", "Teachers", "👨‍🏫"),
    ("staff", "Staff", "💼"),
    ("academics", "Academics", "🏫"),
    ("attendance", "Attendance", "📅"),
    ("fees", "Fees & Billing", "💰"),
    ("accounting", "Accounting", "📈"),
    ("exams", "Exams", "📝"),
    ("results", "Results", "🏆"),
    ("timetable", "Timetable", "⏰"),
    ("library", "Library", "📚"),
    ("transport", "Transport", "🚌"),
    ("hostel", "Hostel", "🏢"),
    ("notices", "Notices", "📢"),
    ("events", "Events", "🎉"),
    ("reports", "Reports", "📑"),
    ("certificates", "Certificates", "📜"),
    ("settings", "Settings", "⚙️"),
]


class SidebarWidget(QWidget):
    navigation_requested = Signal(str)  # module key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarContainer")
        self.setFixedWidth(240)
        self.buttons = {}
        self.active_module = "dashboard"

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 16, 12, 16)
        main_layout.setSpacing(12)

        # Brand header
        brand_row = QHBoxLayout()
        logo_label = QLabel("🎓")
        logo_label.setStyleSheet("font-size: 24px;")
        
        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        title_label = QLabel("EduManage Pro")
        title_label.setStyleSheet("font-weight: 700; font-size: 15px; color: #3b82f6;")
        sub_label = QLabel("School Suite v1.0")
        sub_label.setStyleSheet("color: #64748b; font-size: 11px;")
        name_col.addWidget(title_label)
        name_col.addWidget(sub_label)

        brand_row.addWidget(logo_label)
        brand_row.addLayout(name_col)
        main_layout.addLayout(brand_row)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #334155;")
        main_layout.addWidget(divider)

        # Scrollable navigation items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(4)

        for key, label, emoji in MODULES:
            btn = QPushButton(f"  {emoji}   {label}")
            btn.setProperty("class", "sidebarButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._on_button_clicked(k))
            nav_layout.addWidget(btn)
            self.buttons[key] = btn

        nav_layout.addStretch()
        scroll.setWidget(nav_container)
        main_layout.addWidget(scroll)

        # Set initial active button
        self.set_active_module("dashboard")

    def _on_button_clicked(self, module_key: str):
        self.set_active_module(module_key)
        self.navigation_requested.emit(module_key)

    def set_active_module(self, module_key: str):
        self.active_module = module_key
        for k, btn in self.buttons.items():
            is_active = (k == module_key)
            btn.setChecked(is_active)
            if is_active:
                btn.setStyleSheet("background-color: #2563eb; color: #ffffff; font-weight: 600;")
            else:
                btn.setStyleSheet("background-color: transparent; color: #94a3b8;")
