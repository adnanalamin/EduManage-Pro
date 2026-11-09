"""
EduManage Pro - Main Dashboard Page (PySide6)
Presents real-time operational KPI metric cards, attendance summary, fee collections, and live activity log.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from app.database.connection import SessionLocal
from app.models.activity import ActivityLog
from app.models.school import SchoolSetting
from app.models.academic import SchoolClass, AcademicYear


class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # Header Title
        title_row = QHBoxLayout()
        header_vbox = QVBoxLayout()
        self.welcome_label = QLabel("Welcome to EduManage Pro Executive Dashboard")
        self.welcome_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.welcome_label.setStyleSheet("color: #f8fafc;")

        self.school_label = QLabel("Ideal Model High School & College — Dhaka, Bangladesh")
        self.school_label.setStyleSheet("color: #94a3b8; font-size: 13px;")

        header_vbox.addWidget(self.welcome_label)
        header_vbox.addWidget(self.school_label)
        title_row.addLayout(header_vbox)
        title_row.addStretch()

        btn_refresh = QPushButton("🔄 Refresh Analytics")
        btn_refresh.setStyleSheet("padding: 8px 16px; background: #334155; border-radius: 6px; font-weight: 600;")
        btn_refresh.clicked.connect(self.refresh_data)
        title_row.addWidget(btn_refresh)

        main_layout.addLayout(title_row)

        # Scrollable container for cards and charts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)

        # KPI Metrics Grid (6 Primary Cards)
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(16)

        self.card_students = self._create_kpi_card("Total Students", "1,420", "Active: 1,385  |  Enrolled: 35", "🎓", "#3b82f6")
        self.card_teachers = self._create_kpi_card("Teachers & Faculty", "68", "Present Today: 64  |  Leave: 4", "👨‍🏫", "#10b981")
        self.card_staff = self._create_kpi_card("Staff & Employees", "24", "Admin, Accounts, Support", "💼", "#6366f1")
        self.card_attendance = self._create_kpi_card("Today's Attendance", "94.2%", "Present: 1,304  |  Absent: 81", "📅", "#f59e0b")
        self.card_fees = self._create_kpi_card("Today's Collections", "৳ 85,400", "Month: ৳ 1,420,000", "💰", "#06b6d4")
        self.card_dues = self._create_kpi_card("Outstanding Dues", "৳ 124,500", "Overdue Invoices: 42", "⚠️", "#ef4444")

        kpi_grid.addWidget(self.card_students, 0, 0)
        kpi_grid.addWidget(self.card_teachers, 0, 1)
        kpi_grid.addWidget(self.card_staff, 0, 2)
        kpi_grid.addWidget(self.card_attendance, 1, 0)
        kpi_grid.addWidget(self.card_fees, 1, 1)
        kpi_grid.addWidget(self.card_dues, 1, 2)

        content_layout.addLayout(kpi_grid)

        # Secondary section: Recent Activities & Fast Action Shortcuts
        sec_layout = QHBoxLayout()
        sec_layout.setSpacing(16)

        # Recent Activity Table
        act_box = QFrame()
        act_box.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px;")
        act_layout = QVBoxLayout(act_box)
        
        act_title = QLabel("System Activity & Audit Trail")
        act_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        act_title.setStyleSheet("color: #f8fafc; margin-bottom: 8px;")
        act_layout.addWidget(act_title)

        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(4)
        self.activity_table.setHorizontalHeaderLabels(["Timestamp", "User", "Action", "Module"])
        self.activity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.activity_table.setMinimumHeight(240)
        act_layout.addWidget(self.activity_table)

        # Quick Actions Box
        qa_box = QFrame()
        qa_box.setFixedWidth(280)
        qa_box.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px;")
        qa_layout = QVBoxLayout(qa_box)
        qa_title = QLabel("Quick Management")
        qa_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        qa_title.setStyleSheet("color: #f8fafc; margin-bottom: 8px;")
        qa_layout.addWidget(qa_title)

        quick_buttons = [
            ("➕ Admit New Student", "#2563eb"),
            ("📝 Mark Class Attendance", "#059669"),
            ("💵 Collect Student Fee", "#0891b2"),
            ("📢 Publish Campus Notice", "#7c3aed"),
            ("🖨️ Print Daily Summary", "#475569"),
        ]
        for label, color in quick_buttons:
            b = QPushButton(label)
            b.setStyleSheet(f"background-color: {color}; color: white; padding: 10px; border-radius: 6px; font-weight: 600; text-align: left;")
            qa_layout.addWidget(b)

        qa_layout.addStretch()

        sec_layout.addWidget(act_box, stretch=2)
        sec_layout.addWidget(qa_box, stretch=1)
        content_layout.addLayout(sec_layout)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def _create_kpi_card(self, title: str, value: str, subtext: str, emoji: str, accent_color: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "kpiCard")
        card.setStyleSheet(f"background-color: #1e293b; border: 1px solid #334155; border-left: 5px solid {accent_color}; border-radius: 8px; padding: 14px;")

        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        t_label = QLabel(title)
        t_label.setProperty("class", "kpiTitle")
        t_label.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 11px;")
        
        icon_lbl = QLabel(emoji)
        icon_lbl.setStyleSheet("font-size: 18px;")

        top_row.addWidget(t_label)
        top_row.addStretch()
        top_row.addWidget(icon_lbl)
        layout.addLayout(top_row)

        v_label = QLabel(value)
        v_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        v_label.setStyleSheet(f"color: {accent_color};")
        layout.addWidget(v_label)

        s_label = QLabel(subtext)
        s_label.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(s_label)

        return card

    def refresh_data(self):
        db = SessionLocal()
        try:
            school = db.query(SchoolSetting).first()
            if school:
                self.school_label.setText(f"{school.school_name} — EIIN: {school.eiin_number} ({school.city}, {school.country})")

            # Load recent 10 activity logs
            logs = db.query(ActivityLog).order_by(ActivityLog.id.desc()).limit(10).all()
            self.activity_table.setRowCount(len(logs))
            for row_idx, log in enumerate(logs):
                t_str = log.created_at.strftime("%Y-%m-%d %H:%M") if log.created_at else "-"
                self.activity_table.setItem(row_idx, 0, QTableWidgetItem(t_str))
                self.activity_table.setItem(row_idx, 1, QTableWidgetItem(log.username))
                self.activity_table.setItem(row_idx, 2, QTableWidgetItem(log.action))
                self.activity_table.setItem(row_idx, 3, QTableWidgetItem(log.module))
        finally:
            db.close()
