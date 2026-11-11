"""
EduManage Pro - Comprehensive Reports, Analytics & Data Export Page
Phase 14: Centralized Institutional Reporting Hub, Multi-sheet Excel & Executive PDF Exports
"""

import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QHeaderView, QMessageBox,
    QFileDialog, QFrame, QComboBox, QLineEdit, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from app.services.analytics_service import AnalyticsService
from app.reports.executive_summary_pdf import ExecutiveSummaryPdf
from app.models.school import SchoolSetting
from app.models.academic import SchoolClass


class ReportsPage(QWidget):
    """Main PySide6 page for Institutional Analytics, Audit Reporting, and Data Export."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header & Actions
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Reports, Analytics & Data Export Center")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        subtitle = QLabel("Executive audits, fee collection efficiency, attendance compliance, and multi-format data exports")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        btn_pdf = QPushButton("📑 Export Executive PDF")
        btn_pdf.setStyleSheet("background-color: #1E3A8A; color: white; padding: 7px 14px; font-weight: bold; border-radius: 6px;")
        btn_pdf.clicked.connect(self._export_executive_pdf)
        header_layout.addWidget(btn_pdf)

        btn_excel = QPushButton("📊 Export Master Excel (.xlsx)")
        btn_excel.setStyleSheet("background-color: #059669; color: white; padding: 7px 14px; font-weight: bold; border-radius: 6px;")
        btn_excel.clicked.connect(self._export_master_excel)
        header_layout.addWidget(btn_excel)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setStyleSheet("background-color: #F1F5F9; color: #334155; padding: 7px 12px; font-weight: bold; border: 1px solid #CBD5E1; border-radius: 6px;")
        btn_refresh.clicked.connect(self.refresh_all)
        header_layout.addWidget(btn_refresh)

        main_layout.addLayout(header_layout)

        # 2. KPI Cards
        self.kpi_layout = QHBoxLayout()
        self._build_kpi_cards()
        main_layout.addLayout(self.kpi_layout)

        # 3. Main Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 8px; }
            QTabBar::tab { padding: 8px 16px; font-weight: 600; font-size: 12px; }
            QTabBar::tab:selected { background: #1E3A8A; color: white; border-top-left-radius: 6px; border-top-right-radius: 6px; }
        """)

        # Tab 1: Analytics & Institutional Health
        self.tab_analytics = QWidget()
        self._init_analytics_tab()
        self.tabs.addTab(self.tab_analytics, "📈 Institutional Health & Analytics")

        # Tab 2: Report Generator
        self.tab_generator = QWidget()
        self._init_generator_tab()
        self.tabs.addTab(self.tab_generator, "📋 Report Generator & Table Preview")

        # Tab 3: Data Export Center
        self.tab_export = QWidget()
        self._init_export_tab()
        self.tabs.addTab(self.tab_export, "💾 Data Export Center")

        main_layout.addWidget(self.tabs)
        self.refresh_all()

    def _build_kpi_cards(self):
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cards_data = [
            ("Enrolled Students", "0 Active", "#3B82F6", "👥"),
            ("Attendance Rate", "0.0%", "#10B981", "📅"),
            ("Fee Realization", "0.0%", "#F59E0B", "💳"),
            ("Average GPA", "0.00 / 5.0", "#8B5CF6", "🎓"),
            ("Net Operating Margin", "৳ 0.00", "#06B6D4", "💰"),
        ]

        self.kpi_labels = {}
        for title, default_val, color, icon in cards_data:
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-left: 4px solid {color};
                    border-radius: 8px;
                    padding: 8px;
                }}
            """)
            flayout = QVBoxLayout(frame)
            flayout.setContentsMargins(10, 8, 10, 8)
            flayout.setSpacing(2)

            top_row = QHBoxLayout()
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
            i_lbl = QLabel(icon)
            i_lbl.setStyleSheet("font-size: 14px;")
            top_row.addWidget(t_lbl)
            top_row.addStretch()
            top_row.addWidget(i_lbl)
            flayout.addLayout(top_row)

            v_lbl = QLabel(default_val)
            v_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
            v_lbl.setStyleSheet("color: #0F172A;")
            flayout.addWidget(v_lbl)

            self.kpi_labels[title] = v_lbl
            self.kpi_layout.addWidget(frame)

    # -------------------------------------------------------------
    # TAB 1: Analytics & Institutional Health
    # -------------------------------------------------------------
    def _init_analytics_tab(self):
        layout = QVBoxLayout(self.tab_analytics)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Overview Grid
        grid_layout = QHBoxLayout()

        # Box 1: Financial & Fee Breakdown
        box1 = QGroupBox("Financial & Fee Realization Summary")
        box1.setStyleSheet("QGroupBox { font-weight: bold; color: #1E3A8A; font-size: 13px; }")
        b1_layout = QVBoxLayout(box1)
        self.lbl_finance_stats = QLabel("Loading financial statistics...")
        self.lbl_finance_stats.setStyleSheet("font-size: 12px; color: #334155; line-height: 140%;")
        b1_layout.addWidget(self.lbl_finance_stats)
        grid_layout.addWidget(box1)

        # Box 2: Academics & Operations
        box2 = QGroupBox("Academic Performance & Logistics Utilization")
        box2.setStyleSheet("QGroupBox { font-weight: bold; color: #1E3A8A; font-size: 13px; }")
        b2_layout = QVBoxLayout(box2)
        self.lbl_academic_stats = QLabel("Loading academic statistics...")
        self.lbl_academic_stats.setStyleSheet("font-size: 12px; color: #334155; line-height: 140%;")
        b2_layout.addWidget(self.lbl_academic_stats)
        grid_layout.addWidget(box2)

        layout.addLayout(grid_layout)

        # Class Attendance Compliance Table
        att_label = QLabel("Class-by-Class Attendance Compliance Breakdown")
        att_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        att_label.setStyleSheet("color: #1E293B; margin-top: 6px;")
        layout.addWidget(att_label)

        self.tbl_attendance_health = QTableWidget()
        self.tbl_attendance_health.setColumnCount(6)
        self.tbl_attendance_health.setHorizontalHeaderLabels([
            "Class / Grade", "Total Sessions", "Present", "Absent", "Late", "Attendance Rate (%)"
        ])
        self.tbl_attendance_health.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_attendance_health.setAlternatingRowColors(True)
        self.tbl_attendance_health.verticalHeader().setVisible(False)
        layout.addWidget(self.tbl_attendance_health)

    # -------------------------------------------------------------
    # TAB 2: Report Generator
    # -------------------------------------------------------------
    def _init_generator_tab(self):
        layout = QVBoxLayout(self.tab_generator)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        controls_frame = QFrame()
        controls_frame.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px;")
        ctrl_layout = QHBoxLayout(controls_frame)
        ctrl_layout.setSpacing(12)

        ctrl_layout.addWidget(QLabel("<b>Report Type:</b>"))
        self.cmb_report_type = QComboBox()
        self.cmb_report_type.addItems([
            "Fee Defaulters & Arrears Audit",
            "Student Demographic Roster",
            "Attendance Compliance Summary",
        ])
        self.cmb_report_type.setStyleSheet("padding: 5px; border-radius: 4px; border: 1px solid #CBD5E1;")
        self.cmb_report_type.currentIndexChanged.connect(self._load_selected_report_data)
        ctrl_layout.addWidget(self.cmb_report_type)

        ctrl_layout.addWidget(QLabel("<b>Class Filter:</b>"))
        self.cmb_class_filter = QComboBox()
        self.cmb_class_filter.addItem("All Classes", None)
        self.cmb_class_filter.setStyleSheet("padding: 5px; border-radius: 4px; border: 1px solid #CBD5E1;")
        self.cmb_class_filter.currentIndexChanged.connect(self._load_selected_report_data)
        ctrl_layout.addWidget(self.cmb_class_filter)

        ctrl_layout.addStretch()

        btn_run = QPushButton("⚡ Load Report")
        btn_run.setStyleSheet("background-color: #2563EB; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px;")
        btn_run.clicked.connect(self._load_selected_report_data)
        ctrl_layout.addWidget(btn_run)

        btn_csv = QPushButton("📥 Export Current Table CSV")
        btn_csv.setStyleSheet("background-color: #059669; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px;")
        btn_csv.clicked.connect(self._export_current_table_csv)
        ctrl_layout.addWidget(btn_csv)

        layout.addWidget(controls_frame)

        # Report Preview Table
        self.tbl_report_preview = QTableWidget()
        self.tbl_report_preview.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_report_preview.setAlternatingRowColors(True)
        self.tbl_report_preview.verticalHeader().setVisible(False)
        layout.addWidget(self.tbl_report_preview)

        self.lbl_report_summary = QLabel("Showing 0 records")
        self.lbl_report_summary.setStyleSheet("color: #64748B; font-size: 11px; font-style: italic;")
        layout.addWidget(self.lbl_report_summary)

    # -------------------------------------------------------------
    # TAB 3: Data Export Center
    # -------------------------------------------------------------
    def _init_export_tab(self):
        layout = QVBoxLayout(self.tab_export)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        desc = QLabel("Centralized Data Export Facility: Export complete school records, audited datasets, and ledger tables in Excel (.xlsx) and CSV formats.")
        desc.setStyleSheet("color: #475569; font-size: 13px;")
        layout.addWidget(desc)

        grid = QHBoxLayout()

        # Card 1: Master Excel
        c1 = QFrame()
        c1.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 4px solid #059669; border-radius: 8px; padding: 14px;")
        l1 = QVBoxLayout(c1)
        t1 = QLabel("📊 Master Institutional Workbook (.xlsx)")
        t1.setFont(QFont("Segoe UI", 12, QFont.Bold))
        d1 = QLabel("Comprehensive multi-sheet Excel file containing Executive Summary, Student Demographics, Fee Defaulters, Attendance Analysis, and Results.")
        d1.setWordWrap(True)
        d1.setStyleSheet("color: #64748B; font-size: 11px;")
        b1 = QPushButton("Generate & Download Master Excel")
        b1.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 8px; border-radius: 6px;")
        b1.clicked.connect(self._export_master_excel)
        l1.addWidget(t1)
        l1.addWidget(d1)
        l1.addStretch()
        l1.addWidget(b1)
        grid.addWidget(c1)

        # Card 2: Fee Defaulters CSV
        c2 = QFrame()
        c2.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 4px solid #F59E0B; border-radius: 8px; padding: 14px;")
        l2 = QVBoxLayout(c2)
        t2 = QLabel("💳 Fee Defaulters Dataset (.csv)")
        t2.setFont(QFont("Segoe UI", 12, QFont.Bold))
        d2 = QLabel("Complete roster of overdue fee invoices, outstanding balances, days overdue, and guardian contact numbers for phone recovery campaigns.")
        d2.setWordWrap(True)
        d2.setStyleSheet("color: #64748B; font-size: 11px;")
        b2 = QPushButton("Export Defaulters CSV")
        b2.setStyleSheet("background-color: #F59E0B; color: white; font-weight: bold; padding: 8px; border-radius: 6px;")
        b2.clicked.connect(self._export_defaulters_csv)
        l2.addWidget(t2)
        l2.addWidget(d2)
        l2.addStretch()
        l2.addWidget(b2)
        grid.addWidget(c2)

        # Card 3: Student Roster CSV
        c3 = QFrame()
        c3.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 4px solid #3B82F6; border-radius: 8px; padding: 14px;")
        l3 = QVBoxLayout(c3)
        t3 = QLabel("👥 Master Student Roster (.csv)")
        t3.setFont(QFont("Segoe UI", 12, QFont.Bold))
        d3 = QLabel("Export full active and inactive student registry with admission numbers, roll, gender, date of birth, and guardian phones.")
        d3.setWordWrap(True)
        d3.setStyleSheet("color: #64748B; font-size: 11px;")
        b3 = QPushButton("Export Student Roster CSV")
        b3.setStyleSheet("background-color: #3B82F6; color: white; font-weight: bold; padding: 8px; border-radius: 6px;")
        b3.clicked.connect(self._export_students_csv)
        l3.addWidget(t3)
        l3.addWidget(d3)
        l3.addStretch()
        l3.addWidget(b3)
        grid.addWidget(c3)

        layout.addLayout(grid)

        # Status & Log Display
        self.lbl_export_status = QLabel("Ready for export.")
        self.lbl_export_status.setStyleSheet("background: #F1F5F9; border: 1px dashed #CBD5E1; padding: 10px; border-radius: 6px; color: #334155; font-weight: 500;")
        layout.addWidget(self.lbl_export_status)
        layout.addStretch()

    # -------------------------------------------------------------
    # Data Refresh & Handlers
    # -------------------------------------------------------------
    def refresh_all(self):
        if not self.db:
            return

        # 1. KPIs
        kpis = AnalyticsService.get_executive_kpis(self.db)
        if "Enrolled Students" in self.kpi_labels:
            self.kpi_labels["Enrolled Students"].setText(f"{kpis['active_students']} Active ({kpis['total_students']} Tot)")
        if "Attendance Rate" in self.kpi_labels:
            self.kpi_labels["Attendance Rate"].setText(f"{kpis['attendance_rate']}%")
        if "Fee Realization" in self.kpi_labels:
            self.kpi_labels["Fee Realization"].setText(f"{kpis['collection_efficiency']}%")
        if "Average GPA" in self.kpi_labels:
            self.kpi_labels["Average GPA"].setText(f"{kpis['avg_gpa']} / 5.0")
        if "Net Operating Margin" in self.kpi_labels:
            self.kpi_labels["Net Operating Margin"].setText(f"৳ {kpis['net_surplus']:,.2f}")

        # 2. Detailed text summaries
        self.lbl_finance_stats.setText(
            f"<b>Total Invoiced Billed:</b> ৳ {kpis['total_invoiced']:,.2f}<br/>"
            f"<b>Total Realized Collections:</b> ৳ {kpis['total_collected']:,.2f}<br/>"
            f"<b>Outstanding Arrears:</b> ৳ {kpis['total_dues']:,.2f} ({kpis['defaulters_count']} Overdue Accounts)<br/>"
            f"<b>Operating Revenue (Income):</b> ৳ {kpis['total_income']:,.2f}<br/>"
            f"<b>Operating Expenditures:</b> ৳ {kpis['total_expenses']:,.2f}<br/>"
            f"<b>Net Cash Surplus / (Deficit):</b> ৳ {kpis['net_surplus']:,.2f}"
        )

        self.lbl_academic_stats.setText(
            f"<b>Faculty Strength:</b> {kpis['total_staff']} Total ({kpis['teaching_staff']} Teaching)<br/>"
            f"<b>Exam Term Assessments:</b> {kpis['total_assessed']} Student Evaluations<br/>"
            f"<b>Pass Rate:</b> {kpis['pass_rate']}% | <b>Average GPA:</b> {kpis['avg_gpa']} / 5.00<br/>"
            f"<b>Library Circulation:</b> {kpis['active_loans']} Active Loans / {kpis['total_books']} Cataloged Books<br/>"
            f"<b>Transport Fleet:</b> {kpis['transport_passengers']} Students across {kpis['total_routes']} Daily Routes<br/>"
            f"<b>Hostel Bed Occupancy:</b> {kpis['hostel_occupancy_rate']}% ({kpis['hostel_occupancy']}/{kpis['hostel_capacity']} Beds)"
        )

        # 3. Class attendance compliance table
        att_data = AnalyticsService.get_attendance_analytics(self.db)
        summary = att_data["class_summary"]
        self.tbl_attendance_health.setRowCount(len(summary))
        for r_idx, row in enumerate(summary):
            self.tbl_attendance_health.setItem(r_idx, 0, QTableWidgetItem(row["class_name"]))
            self.tbl_attendance_health.setItem(r_idx, 1, QTableWidgetItem(str(row["total_records"])))
            self.tbl_attendance_health.setItem(r_idx, 2, QTableWidgetItem(str(row["present_count"])))
            self.tbl_attendance_health.setItem(r_idx, 3, QTableWidgetItem(str(row["absent_count"])))
            self.tbl_attendance_health.setItem(r_idx, 4, QTableWidgetItem(str(row["late_count"])))
            rate_item = QTableWidgetItem(f"{row['attendance_percentage']}%")
            if row['attendance_percentage'] >= 90:
                rate_item.setForeground(QColor("#059669"))
            elif row['attendance_percentage'] >= 75:
                rate_item.setForeground(QColor("#D97706"))
            else:
                rate_item.setForeground(QColor("#DC2626"))
            self.tbl_attendance_health.setItem(r_idx, 5, rate_item)

        # 4. Classes in filter dropdown
        current_cls = self.cmb_class_filter.currentData()
        self.cmb_class_filter.clear()
        self.cmb_class_filter.addItem("All Classes", None)
        classes = self.db.query(SchoolClass).order_by(SchoolClass.name).all()
        for c in classes:
            self.cmb_class_filter.addItem(c.name, c.id)
        if current_cls:
            idx = self.cmb_class_filter.findData(current_cls)
            if idx >= 0:
                self.cmb_class_filter.setCurrentIndex(idx)

        # 5. Populate preview table
        self._load_selected_report_data()

    def _load_selected_report_data(self):
        if not self.db:
            return

        report_type = self.cmb_report_type.currentText()
        class_id = self.cmb_class_filter.currentData()

        if "Fee Defaulters" in report_type:
            headers = ["Invoice No", "Admission No", "Student Name", "Class & Section", "Billed (৳)", "Paid (৳)", "Due (৳)", "Due Date", "Overdue Days", "Status", "Guardian Phone"]
            self.tbl_report_preview.setColumnCount(len(headers))
            self.tbl_report_preview.setHorizontalHeaderLabels(headers)

            data = AnalyticsService.get_fee_defaulters(self.db, class_id=class_id)
            self.tbl_report_preview.setRowCount(len(data))
            for r_idx, d in enumerate(data):
                self.tbl_report_preview.setItem(r_idx, 0, QTableWidgetItem(d["invoice_number"]))
                self.tbl_report_preview.setItem(r_idx, 1, QTableWidgetItem(d["admission_number"]))
                self.tbl_report_preview.setItem(r_idx, 2, QTableWidgetItem(d["student_name"]))
                self.tbl_report_preview.setItem(r_idx, 3, QTableWidgetItem(d["class_section"]))
                self.tbl_report_preview.setItem(r_idx, 4, QTableWidgetItem(f"৳ {d['total_amount']:,.2f}"))
                self.tbl_report_preview.setItem(r_idx, 5, QTableWidgetItem(f"৳ {d['paid_amount']:,.2f}"))
                due_item = QTableWidgetItem(f"৳ {d['due_amount']:,.2f}")
                due_item.setForeground(QColor("#DC2626"))
                self.tbl_report_preview.setItem(r_idx, 6, due_item)
                self.tbl_report_preview.setItem(r_idx, 7, QTableWidgetItem(d["due_date"]))
                self.tbl_report_preview.setItem(r_idx, 8, QTableWidgetItem(str(d["days_overdue"])))
                self.tbl_report_preview.setItem(r_idx, 9, QTableWidgetItem(d["status"]))
                self.tbl_report_preview.setItem(r_idx, 10, QTableWidgetItem(d["guardian_phone"]))

            self.lbl_report_summary.setText(f"Showing {len(data)} fee defaulter records.")

        elif "Student Demographic" in report_type:
            headers = ["Adm No", "Full Name", "Class", "Section", "Roll", "Gender", "Birth Date", "Status", "Guardian Phone"]
            self.tbl_report_preview.setColumnCount(len(headers))
            self.tbl_report_preview.setHorizontalHeaderLabels(headers)

            from app.models.student import Student
            q = self.db.query(Student)
            if class_id:
                q = q.filter(Student.current_class_id == class_id)
            students = q.order_by(Student.admission_number).all()

            self.tbl_report_preview.setRowCount(len(students))
            for r_idx, s in enumerate(students):
                cls_name = s.current_class.name if s.current_class else "N/A"
                sec_name = s.current_section.name if s.current_section else "N/A"
                self.tbl_report_preview.setItem(r_idx, 0, QTableWidgetItem(s.admission_number))
                self.tbl_report_preview.setItem(r_idx, 1, QTableWidgetItem(f"{s.first_name} {s.last_name}"))
                self.tbl_report_preview.setItem(r_idx, 2, QTableWidgetItem(cls_name))
                self.tbl_report_preview.setItem(r_idx, 3, QTableWidgetItem(sec_name))
                self.tbl_report_preview.setItem(r_idx, 4, QTableWidgetItem(str(s.roll_number or "")))
                self.tbl_report_preview.setItem(r_idx, 5, QTableWidgetItem(s.gender or ""))
                self.tbl_report_preview.setItem(r_idx, 6, QTableWidgetItem(s.date_of_birth.strftime("%Y-%m-%d") if s.date_of_birth else ""))
                self.tbl_report_preview.setItem(r_idx, 7, QTableWidgetItem(s.status))
                self.tbl_report_preview.setItem(r_idx, 8, QTableWidgetItem(s.guardian_phone or ""))

            self.lbl_report_summary.setText(f"Showing {len(students)} student demographic records.")

        elif "Attendance Compliance" in report_type:
            headers = ["Class / Grade", "Total Sessions", "Present", "Absent", "Late", "Attendance Rate (%)"]
            self.tbl_report_preview.setColumnCount(len(headers))
            self.tbl_report_preview.setHorizontalHeaderLabels(headers)

            att_data = AnalyticsService.get_attendance_analytics(self.db)
            summary = att_data["class_summary"]
            self.tbl_report_preview.setRowCount(len(summary))
            for r_idx, row in enumerate(summary):
                self.tbl_report_preview.setItem(r_idx, 0, QTableWidgetItem(row["class_name"]))
                self.tbl_report_preview.setItem(r_idx, 1, QTableWidgetItem(str(row["total_records"])))
                self.tbl_report_preview.setItem(r_idx, 2, QTableWidgetItem(str(row["present_count"])))
                self.tbl_report_preview.setItem(r_idx, 3, QTableWidgetItem(str(row["absent_count"])))
                self.tbl_report_preview.setItem(r_idx, 4, QTableWidgetItem(str(row["late_count"])))
                self.tbl_report_preview.setItem(r_idx, 5, QTableWidgetItem(f"{row['attendance_percentage']}%"))

            self.lbl_report_summary.setText(f"Showing {len(summary)} class attendance compliance summaries.")

    # -------------------------------------------------------------
    # Export Actions
    # -------------------------------------------------------------
    def _export_executive_pdf(self):
        if not self.db:
            return
        default_name = f"Executive_Summary_Audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Executive Summary PDF", default_name, "PDF Files (*.pdf)")
        if not file_path:
            return

        try:
            kpis = AnalyticsService.get_executive_kpis(self.db)
            school = self.db.query(SchoolSetting).first()
            ExecutiveSummaryPdf.generate(kpis, school, file_path)
            self.lbl_export_status.setText(f"✅ Executive PDF successfully exported to:\n{file_path}")
            QMessageBox.information(self, "Export Successful", f"Executive Summary PDF generated successfully!\n\nSaved to: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to generate Executive PDF:\n{str(e)}")

    def _export_master_excel(self):
        if not self.db:
            return
        default_name = f"Master_School_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Master Excel Workbook", default_name, "Excel Files (*.xlsx)")
        if not file_path:
            return

        try:
            AnalyticsService.export_master_school_report_excel(self.db, file_path)
            self.lbl_export_status.setText(f"✅ Master Excel Workbook exported to:\n{file_path}")
            QMessageBox.information(self, "Export Successful", f"Master Institutional Workbook exported with all sheets!\n\nSaved to: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export Excel workbook:\n{str(e)}")

    def _export_defaulters_csv(self):
        if not self.db:
            return
        default_name = f"Fee_Defaulters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Fee Defaulters CSV", default_name, "CSV Files (*.csv)")
        if not file_path:
            return

        try:
            AnalyticsService.export_defaulters_csv(self.db, file_path)
            self.lbl_export_status.setText(f"✅ Fee Defaulters CSV exported to:\n{file_path}")
            QMessageBox.information(self, "Export Successful", f"Fee Defaulters CSV generated successfully!\n\nSaved to: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export Defaulters CSV:\n{str(e)}")

    def _export_students_csv(self):
        if not self.db:
            return
        default_name = f"Student_Roster_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Student Roster CSV", default_name, "CSV Files (*.csv)")
        if not file_path:
            return

        try:
            AnalyticsService.export_students_csv(self.db, file_path)
            self.lbl_export_status.setText(f"✅ Student Roster CSV exported to:\n{file_path}")
            QMessageBox.information(self, "Export Successful", f"Student Roster CSV generated successfully!\n\nSaved to: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export Student Roster CSV:\n{str(e)}")

    def _export_current_table_csv(self):
        default_name = f"Report_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Table as CSV", default_name, "CSV Files (*.csv)")
        if not file_path:
            return

        try:
            import csv
            with open(file_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = []
                for c in range(self.tbl_report_preview.columnCount()):
                    headers.append(self.tbl_report_preview.horizontalHeaderItem(c).text())
                writer.writerow(headers)

                for r in range(self.tbl_report_preview.rowCount()):
                    row_vals = []
                    for c in range(self.tbl_report_preview.columnCount()):
                        item = self.tbl_report_preview.item(r, c)
                        row_vals.append(item.text() if item else "")
                    writer.writerow(row_vals)

            self.lbl_export_status.setText(f"✅ Table data exported to:\n{file_path}")
            QMessageBox.information(self, "Export Successful", f"Report table exported to CSV successfully!\n\nSaved to: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV:\n{str(e)}")
