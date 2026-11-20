"""
EduManage Pro - Main Dashboard Page (PySide6)
Presents live real-database operational KPI metric cards, database-driven
analytics charts (no fake charts), academic-year filter, quick shortcuts,
and live system audit activity log.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.connection import SessionLocal
from app.models.academic import AcademicYear
from app.models.activity import ActivityLog
from app.models.school import SchoolSetting
from app.services.analytics_service import AnalyticsService
from app.ui.widgets.analytics_charts import (
    RealBarChartWidget,
    RealGroupedBarChartWidget,
    RealHorizontalBreakdownWidget,
)


class DashboardPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)

        # Header Title + Academic Year Filter + Refresh
        title_row = QHBoxLayout()
        header_vbox = QVBoxLayout()
        self.welcome_label = QLabel("EduManage Pro Executive Dashboard")
        self.welcome_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.welcome_label.setStyleSheet("color: #f8fafc;")

        self.school_label = QLabel("Loading school profile from database...")
        self.school_label.setStyleSheet("color: #94a3b8; font-size: 13px;")

        header_vbox.addWidget(self.welcome_label)
        header_vbox.addWidget(self.school_label)
        title_row.addLayout(header_vbox)
        title_row.addStretch()

        yr_lbl = QLabel("Academic Year:")
        yr_lbl.setStyleSheet("color: #cbd5e1; font-weight: 600;")
        title_row.addWidget(yr_lbl)

        self.cmb_year_filter = QComboBox()
        self.cmb_year_filter.setMinimumWidth(160)
        self.cmb_year_filter.addItem("All Academic Years", None)
        self.cmb_year_filter.setStyleSheet(
            "padding: 6px 10px; background: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 6px;"
        )
        self.cmb_year_filter.currentIndexChanged.connect(self._on_year_changed)
        title_row.addWidget(self.cmb_year_filter)

        btn_refresh = QPushButton("Refresh Analytics")
        btn_refresh.setStyleSheet(
            "padding: 8px 16px; background: #2563eb; color: #ffffff; border-radius: 6px; font-weight: 600;"
        )
        btn_refresh.clicked.connect(self.refresh_data)
        title_row.addWidget(btn_refresh)

        main_layout.addLayout(title_row)

        # Scrollable container for KPI cards, live DB charts, and activity trail
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(18)

        # KPI Metrics Grid (6 Primary Cards initialized cleanly to zero)
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(14)

        self.card_students, self.val_students, self.sub_students = self._create_kpi_card(
            "Total Students", "0", "Active: 0  |  Other: 0", "🎓", "#3b82f6"
        )
        self.card_teachers, self.val_teachers, self.sub_teachers = self._create_kpi_card(
            "Teachers & Faculty", "0", "Active: 0  |  Present Today: 0", "👨‍🏫", "#10b981"
        )
        self.card_staff, self.val_staff, self.sub_staff = self._create_kpi_card(
            "Staff & Employees", "0", "Active Non-Teaching: 0", "💼", "#6366f1"
        )
        self.card_attendance, self.val_attendance, self.sub_attendance = self._create_kpi_card(
            "Overall Attendance", "0.0%", "Today Present: 0  |  Absent: 0", "📅", "#f59e0b"
        )
        self.card_fees, self.val_fees, self.sub_fees = self._create_kpi_card(
            "Today's Collections", "৳ 0.00", "Month: ৳ 0.00  |  Total: ৳ 0.00", "💰", "#06b6d4"
        )
        self.card_dues, self.val_dues, self.sub_dues = self._create_kpi_card(
            "Outstanding Dues", "৳ 0.00", "Overdue Invoices: 0", "⚠️", "#ef4444"
        )

        kpi_grid.addWidget(self.card_students, 0, 0)
        kpi_grid.addWidget(self.card_teachers, 0, 1)
        kpi_grid.addWidget(self.card_staff, 0, 2)
        kpi_grid.addWidget(self.card_attendance, 1, 0)
        kpi_grid.addWidget(self.card_fees, 1, 1)
        kpi_grid.addWidget(self.card_dues, 1, 2)

        content_layout.addLayout(kpi_grid)

        # Real-Database Analytics Charts Grid (2 x 2)
        charts_grid = QGridLayout()
        charts_grid.setSpacing(14)

        self.chart_enrollment = RealBarChartWidget(
            title="Student Enrollment by Class (Live DB)",
            accent_color="#3b82f6",
            empty_message="No student records enrolled yet for selected academic year.",
        )
        self.chart_cashflow = RealGroupedBarChartWidget(
            title="Monthly Accounting Cashflow: Income vs Expense",
            primary_label="Income",
            secondary_label="Expense",
            primary_color="#10b981",
            secondary_color="#ef4444",
            empty_message="No accounting vouchers recorded yet.",
        )
        self.chart_attendance = RealHorizontalBreakdownWidget(
            title="Attendance Status Breakdown (Live Records)",
            empty_message="No attendance sessions recorded yet.",
        )
        self.chart_fees_by_cat = RealGroupedBarChartWidget(
            title="Fee Realization by Category: Billed vs Collected",
            primary_label="Billed",
            secondary_label="Collected",
            primary_color="#3b82f6",
            secondary_color="#06b6d4",
            empty_message="No fee invoices generated yet.",
        )

        charts_grid.addWidget(self.chart_enrollment, 0, 0)
        charts_grid.addWidget(self.chart_cashflow, 0, 1)
        charts_grid.addWidget(self.chart_attendance, 1, 0)
        charts_grid.addWidget(self.chart_fees_by_cat, 1, 1)

        content_layout.addLayout(charts_grid)

        # Secondary section: Recent Activities & Quick Management Shortcuts
        sec_layout = QHBoxLayout()
        sec_layout.setSpacing(16)

        act_box = QFrame()
        act_box.setStyleSheet(
            "background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px;"
        )
        act_layout = QVBoxLayout(act_box)

        act_title = QLabel("System Activity & Audit Trail")
        act_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        act_title.setStyleSheet("color: #f8fafc; margin-bottom: 6px;")
        act_layout.addWidget(act_title)

        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(4)
        self.activity_table.setHorizontalHeaderLabels(["Timestamp", "User", "Action", "Module"])
        self.activity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.activity_table.setMinimumHeight(210)
        act_layout.addWidget(self.activity_table)

        qa_box = QFrame()
        qa_box.setFixedWidth(280)
        qa_box.setStyleSheet(
            "background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px;"
        )
        qa_layout = QVBoxLayout(qa_box)
        qa_title = QLabel("Quick Management")
        qa_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        qa_title.setStyleSheet("color: #f8fafc; margin-bottom: 6px;")
        qa_layout.addWidget(qa_title)

        quick_buttons = [
            ("➕ Admit / View Students", "#2563eb", "students"),
            ("📝 Mark Attendance", "#059669", "attendance"),
            ("💵 Collect Student Fee", "#0891b2", "fees"),
            ("📢 Communication Center", "#7c3aed", "communications"),
            ("📊 Open Report Builder", "#475569", "reports"),
        ]
        for label, color, target_mod in quick_buttons:
            b = QPushButton(label)
            b.setStyleSheet(
                f"background-color: {color}; color: white; padding: 10px; border-radius: 6px; font-weight: 600; text-align: left;"
            )
            b.clicked.connect(lambda _checked=False, m=target_mod: self.navigate_requested.emit(m))
            qa_layout.addWidget(b)

        qa_layout.addStretch()

        sec_layout.addWidget(act_box, stretch=2)
        sec_layout.addWidget(qa_box, stretch=1)
        content_layout.addLayout(sec_layout)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        self._loading_years = False

    def _create_kpi_card(
        self, title: str, value: str, subtext: str, emoji: str, accent_color: str
    ):
        card = QFrame()
        card.setProperty("class", "kpiCard")
        card.setStyleSheet(
            f"background-color: #1e293b; border: 1px solid #334155; border-left: 5px solid {accent_color}; border-radius: 8px; padding: 12px;"
        )

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
        v_label.setFont(QFont("Segoe UI", 19, QFont.Bold))
        v_label.setStyleSheet(f"color: {accent_color};")
        layout.addWidget(v_label)

        s_label = QLabel(subtext)
        s_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(s_label)

        return card, v_label, s_label

    def _on_year_changed(self):
        if not self._loading_years:
            self.refresh_data()

    def refresh_data(self):
        db = SessionLocal()
        try:
            school = db.query(SchoolSetting).first()
            currency = school.currency_symbol if school and school.currency_symbol else "৳"
            if school:
                self.school_label.setText(
                    f"{school.school_name} — EIIN: {school.eiin_number or 'N/A'} ({school.city or ''}, {school.country or ''})"
                )

            # Refresh academic year selector safely without recursion
            selected_year_id = self.cmb_year_filter.currentData()
            self._loading_years = True
            self.cmb_year_filter.clear()
            self.cmb_year_filter.addItem("All Academic Years", None)
            years = db.query(AcademicYear).filter(AcademicYear.is_deleted == False).order_by(AcademicYear.start_date.desc()).all()  # noqa: E712
            for yr in years:
                lbl = f"{yr.name} (Current)" if yr.is_current else yr.name
                self.cmb_year_filter.addItem(lbl, yr.id)
            if selected_year_id is not None:
                idx = self.cmb_year_filter.findData(selected_year_id)
                if idx >= 0:
                    self.cmb_year_filter.setCurrentIndex(idx)
            self._loading_years = False

            year_id = self.cmb_year_filter.currentData()
            analytics = AnalyticsService.get_dashboard_analytics(db, academic_year_id=year_id)
            kpis = analytics["kpis"]

            # Populate 6 Real KPI Cards
            self.val_students.setText(f"{kpis['total_students']:,}")
            self.sub_students.setText(
                f"Active: {kpis['active_students']:,}  |  Other: {kpis['inactive_or_other_students']:,}"
            )

            self.val_teachers.setText(f"{kpis['total_teachers']:,}")
            self.sub_teachers.setText(
                f"Active: {kpis['active_teachers']:,}  |  Present Today: {kpis['teachers_present_today']:,}"
            )

            self.val_staff.setText(f"{kpis['total_non_teaching_staff']:,}")
            self.sub_staff.setText(
                f"Active Non-Teaching: {kpis['active_non_teaching_staff']:,}  |  Total HR: {kpis['total_staff']:,}"
            )

            self.val_attendance.setText(f"{kpis['attendance_rate']:.1f}%")
            self.sub_attendance.setText(
                f"Today Present: {kpis['today_att_present']:,}  |  Absent: {kpis['today_att_absent']:,}"
            )

            self.val_fees.setText(f"{currency} {kpis['today_collections']:,.2f}")
            self.sub_fees.setText(
                f"Month: {currency} {kpis['month_collections']:,.0f}  |  Total: {currency} {kpis['total_collected']:,.0f}"
            )

            self.val_dues.setText(f"{currency} {kpis['total_dues']:,.2f}")
            self.sub_dues.setText(
                f"Overdue Accounts: {kpis['defaulters_count']:,}  |  Efficiency: {kpis['collection_efficiency']:.1f}%"
            )

            # Populate Real DB Charts
            self.chart_enrollment.set_data(analytics["enrollment_by_class"])
            self.chart_cashflow.set_data(analytics["finance_monthly_series"])
            self.chart_attendance.set_data(analytics["attendance_distribution"])
            self.chart_fees_by_cat.set_data(analytics["fee_collection_by_category"])

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
