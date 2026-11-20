"""
EduManage Pro - Professional Reporting Engine, Report Builder & Analytics Center
Features:
  - All 11 Domain Reports (Student, Attendance, Finance, Payroll, Academic, Exam,
    Library, Transport, Hostel, Inventory & Assets, HR)
  - Dynamic Report Builder (Columns, Filters, Grouping, Sorting, Date Range, Academic Year)
  - Saved Report Templates persisted in Database
  - Universal Export to PDF (ReportLab), Excel (.xlsx), and CSV (.csv)
  - Real-DB Dashboard & Executive Analytics Charts (Zero fake charts)
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.academic import AcademicYear
from app.models.school import SchoolSetting
from app.reports.dynamic_report_pdf import DynamicReportPDFGenerator
from app.reports.executive_summary_pdf import ExecutiveSummaryPdf
from app.services.analytics_service import AnalyticsService
from app.services.reporting_engine import REPORT_DOMAIN_CATALOG, ReportingEngine
from app.ui.widgets.analytics_charts import (
    RealBarChartWidget,
    RealGroupedBarChartWidget,
    RealHorizontalBreakdownWidget,
)


class ReportsPage(QWidget):
    """Main PySide6 page for the 11-Domain Professional Reporting Engine & Report Builder."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self._current_preset_result: Optional[Dict[str, Any]] = None
        self._current_builder_result: Optional[Dict[str, Any]] = None
        self._filter_rows: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        # 1. Header & Global Controls
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Professional Reporting Engine & Analytics Center")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        subtitle = QLabel(
            "11 institutional reporting domains, custom Report Builder, real-DB analytics & PDF/Excel/CSV exports"
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        btn_pdf = QPushButton("📑 Executive Summary PDF")
        btn_pdf.setStyleSheet(
            "background-color: #1E3A8A; color: white; padding: 7px 14px; font-weight: bold; border-radius: 6px;"
        )
        btn_pdf.clicked.connect(self._export_executive_pdf)
        header_layout.addWidget(btn_pdf)

        btn_excel = QPushButton("📊 Master Excel (.xlsx)")
        btn_excel.setStyleSheet(
            "background-color: #059669; color: white; padding: 7px 14px; font-weight: bold; border-radius: 6px;"
        )
        btn_excel.clicked.connect(self._export_master_excel)
        header_layout.addWidget(btn_excel)

        btn_refresh = QPushButton("🔄 Refresh Data")
        btn_refresh.setStyleSheet(
            "background-color: #F1F5F9; color: #334155; padding: 7px 12px; font-weight: bold; border: 1px solid #CBD5E1; border-radius: 6px;"
        )
        btn_refresh.clicked.connect(self.refresh_all)
        header_layout.addWidget(btn_refresh)

        main_layout.addLayout(header_layout)

        # 2. Live KPI Cards
        self.kpi_layout = QHBoxLayout()
        self._build_kpi_cards()
        main_layout.addLayout(self.kpi_layout)

        # 3. Main Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            """
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 8px; }
            QTabBar::tab { padding: 8px 16px; font-weight: 600; font-size: 12px; }
            QTabBar::tab:selected { background: #1E3A8A; color: white; border-top-left-radius: 6px; border-top-right-radius: 6px; }
            """
        )

        # Tab 1: 11-Domain Report Catalog
        self.tab_catalog = QWidget()
        self._init_catalog_tab()
        self.tabs.addTab(self.tab_catalog, "📚 11-Domain Standard Reports")

        # Tab 2: Interactive Report Builder
        self.tab_builder = QWidget()
        self._init_builder_tab()
        self.tabs.addTab(self.tab_builder, "🛠️ Custom Report Builder")

        # Tab 3: Real-DB Analytics & Charts
        self.tab_analytics = QWidget()
        self._init_analytics_tab()
        self.tabs.addTab(self.tab_analytics, "📈 Live Database Analytics & Charts")

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
            ("Net Cashflow", "৳ 0.00", "#06B6D4", "💰"),
        ]

        self.kpi_labels: Dict[str, QLabel] = {}
        for title, default_val, color, icon in cards_data:
            frame = QFrame()
            frame.setStyleSheet(
                f"QFrame {{ background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid {color}; border-radius: 8px; padding: 8px; }}"
            )
            flayout = QVBoxLayout(frame)
            flayout.setContentsMargins(10, 6, 10, 6)
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

    # ------------------------------------------------------------------
    # TAB 1: 11-Domain Standard Reports Launcher & Viewer
    # ------------------------------------------------------------------
    def _init_catalog_tab(self):
        layout = QVBoxLayout(self.tab_catalog)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Quick domain selector pills (11 domains in clean 2-row grid)
        domain_grid = QGridLayout()
        domain_grid.setSpacing(6)
        self._domain_buttons: Dict[str, QPushButton] = {}
        domain_keys = list(REPORT_DOMAIN_CATALOG.keys())
        for idx, dkey in enumerate(domain_keys):
            meta = REPORT_DOMAIN_CATALOG[dkey]
            btn = QPushButton(meta["label"])
            btn.setCheckable(True)
            btn.setStyleSheet(
                """
                QPushButton { background: #F8FAFC; color: #1E293B; border: 1px solid #CBD5E1; padding: 6px 10px; border-radius: 6px; font-weight: 600; font-size: 11px; }
                QPushButton:checked { background: #1E3A8A; color: #FFFFFF; border-color: #1E3A8A; }
                """
            )
            btn.clicked.connect(lambda _c=False, k=dkey: self._select_preset_domain(k))
            self._domain_buttons[dkey] = btn
            domain_grid.addWidget(btn, idx // 6, idx % 6)
        layout.addLayout(domain_grid)

        # Filter bar
        ctrl = QFrame()
        ctrl.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 6px;")
        cl = QHBoxLayout(ctrl)
        cl.setSpacing(10)

        cl.addWidget(QLabel("<b>Academic Year:</b>"))
        self.cmb_preset_year = QComboBox()
        self.cmb_preset_year.addItem("All Academic Years", None)
        cl.addWidget(self.cmb_preset_year)

        self.chk_preset_dates = QCheckBox("Filter Date Range:")
        cl.addWidget(self.chk_preset_dates)

        self.dt_preset_from = QDateEdit(QDate.currentDate().addMonths(-6))
        self.dt_preset_from.setCalendarPopup(True)
        self.dt_preset_from.setDisplayFormat("yyyy-MM-dd")
        cl.addWidget(self.dt_preset_from)

        cl.addWidget(QLabel("to"))
        self.dt_preset_to = QDateEdit(QDate.currentDate())
        self.dt_preset_to.setCalendarPopup(True)
        self.dt_preset_to.setDisplayFormat("yyyy-MM-dd")
        cl.addWidget(self.dt_preset_to)

        cl.addStretch()

        btn_run = QPushButton("⚡ Run Report")
        btn_run.setStyleSheet("background: #2563EB; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px;")
        btn_run.clicked.connect(self._run_preset_report)
        cl.addWidget(btn_run)

        btn_customize = QPushButton("🛠️ Customize in Builder")
        btn_customize.setStyleSheet("background: #475569; color: white; padding: 6px 10px; font-weight: bold; border-radius: 4px;")
        btn_customize.clicked.connect(self._send_preset_to_builder)
        cl.addWidget(btn_customize)

        btn_pdf = QPushButton("📄 PDF")
        btn_pdf.setStyleSheet("background: #DC2626; color: white; padding: 6px 10px; font-weight: bold; border-radius: 4px;")
        btn_pdf.clicked.connect(lambda: self._export_report_result(self._current_preset_result, "pdf"))
        cl.addWidget(btn_pdf)

        btn_xlsx = QPushButton("📊 Excel")
        btn_xlsx.setStyleSheet("background: #059669; color: white; padding: 6px 10px; font-weight: bold; border-radius: 4px;")
        btn_xlsx.clicked.connect(lambda: self._export_report_result(self._current_preset_result, "excel"))
        cl.addWidget(btn_xlsx)

        btn_csv = QPushButton("📥 CSV")
        btn_csv.setStyleSheet("background: #0891B2; color: white; padding: 6px 10px; font-weight: bold; border-radius: 4px;")
        btn_csv.clicked.connect(lambda: self._export_report_result(self._current_preset_result, "csv"))
        cl.addWidget(btn_csv)

        layout.addWidget(ctrl)

        self.lbl_preset_desc = QLabel("")
        self.lbl_preset_desc.setStyleSheet("color: #475569; font-size: 12px;")
        layout.addWidget(self.lbl_preset_desc)

        self.tbl_preset = QTableWidget()
        self.tbl_preset.setAlternatingRowColors(True)
        self.tbl_preset.verticalHeader().setVisible(False)
        layout.addWidget(self.tbl_preset)

        self.lbl_preset_footer = QLabel("Showing 0 records.")
        self.lbl_preset_footer.setStyleSheet("color: #334155; font-size: 11px; font-weight: 600;")
        layout.addWidget(self.lbl_preset_footer)

        self._active_preset_domain = "students"
        self._domain_buttons["students"].setChecked(True)

    def _select_preset_domain(self, domain_key: str):
        self._active_preset_domain = domain_key
        for k, b in self._domain_buttons.items():
            b.setChecked(k == domain_key)
        self._run_preset_report()

    def _run_preset_report(self):
        if not self.db:
            return
        self.db.expire_all()
        dkey = self._active_preset_domain
        meta = REPORT_DOMAIN_CATALOG[dkey]
        self.lbl_preset_desc.setText(f"<b>{meta['label']}:</b> {meta['description']}")

        ay_id = self.cmb_preset_year.currentData()
        d_from = self.dt_preset_from.date().toPython() if self.chk_preset_dates.isChecked() else None
        d_to = self.dt_preset_to.date().toPython() if self.chk_preset_dates.isChecked() else None

        res = ReportingEngine.build_report(
            self.db,
            domain_key=dkey,
            academic_year_id=ay_id,
            date_from=d_from,
            date_to=d_to,
        )
        self._current_preset_result = res
        self._populate_table_from_result(self.tbl_preset, res, grouped=False)

        tot_bits = [f"{k}: {v:,.2f}" for k, v in (res.get("totals") or {}).items()]
        tot_str = f" | Totals: {', '.join(tot_bits[:5])}" if tot_bits else ""
        self.lbl_preset_footer.setText(f"Records: {res['row_count']}{tot_str}")

    def _send_preset_to_builder(self):
        idx = self.cmb_builder_domain.findData(self._active_preset_domain)
        if idx >= 0:
            self.cmb_builder_domain.setCurrentIndex(idx)
        self.tabs.setCurrentIndex(1)

    # ------------------------------------------------------------------
    # TAB 2: Interactive Report Builder
    # ------------------------------------------------------------------
    def _init_builder_tab(self):
        outer = QVBoxLayout(self.tab_builder)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        # Saved Templates Top Bar
        tpl_bar = QHBoxLayout()
        tpl_bar.addWidget(QLabel("<b>Saved Templates:</b>"))
        self.cmb_saved_templates = QComboBox()
        self.cmb_saved_templates.setMinimumWidth(220)
        tpl_bar.addWidget(self.cmb_saved_templates)

        btn_load_tpl = QPushButton("Load & Run")
        btn_load_tpl.setStyleSheet("background: #334155; color: white; padding: 5px 10px; border-radius: 4px; font-weight: 600;")
        btn_load_tpl.clicked.connect(self._load_saved_template)
        tpl_bar.addWidget(btn_load_tpl)

        btn_save_tpl = QPushButton("💾 Save Current Template")
        btn_save_tpl.setStyleSheet("background: #0F766E; color: white; padding: 5px 10px; border-radius: 4px; font-weight: 600;")
        btn_save_tpl.clicked.connect(self._save_current_template)
        tpl_bar.addWidget(btn_save_tpl)

        btn_del_tpl = QPushButton("Delete")
        btn_del_tpl.setStyleSheet("background: #DC2626; color: white; padding: 5px 10px; border-radius: 4px; font-weight: 600;")
        btn_del_tpl.clicked.connect(self._delete_saved_template)
        tpl_bar.addWidget(btn_del_tpl)
        tpl_bar.addStretch()

        btn_b_pdf = QPushButton("📄 Export PDF")
        btn_b_pdf.setStyleSheet("background: #DC2626; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px;")
        btn_b_pdf.clicked.connect(lambda: self._export_report_result(self._current_builder_result, "pdf"))
        tpl_bar.addWidget(btn_b_pdf)

        btn_b_xlsx = QPushButton("📊 Export Excel")
        btn_b_xlsx.setStyleSheet("background: #059669; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px;")
        btn_b_xlsx.clicked.connect(lambda: self._export_report_result(self._current_builder_result, "excel"))
        tpl_bar.addWidget(btn_b_xlsx)

        btn_b_csv = QPushButton("📥 Export CSV")
        btn_b_csv.setStyleSheet("background: #0891B2; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px;")
        btn_b_csv.clicked.connect(lambda: self._export_report_result(self._current_builder_result, "csv"))
        tpl_bar.addWidget(btn_b_csv)

        outer.addLayout(tpl_bar)

        splitter = QSplitter(Qt.Horizontal)

        # Left Panel: Builder Configuration Controls
        cfg_panel = QFrame()
        cfg_panel.setMinimumWidth(330)
        cfg_panel.setMaximumWidth(420)
        cfg_panel.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        cfg_layout = QVBoxLayout(cfg_panel)
        cfg_layout.setContentsMargins(10, 10, 10, 10)
        cfg_layout.setSpacing(8)

        cfg_layout.addWidget(QLabel("<b>1. Dataset / Module Domain</b>"))
        self.cmb_builder_domain = QComboBox()
        for k, meta in REPORT_DOMAIN_CATALOG.items():
            self.cmb_builder_domain.addItem(meta["label"], k)
        self.cmb_builder_domain.currentIndexChanged.connect(self._on_builder_domain_changed)
        cfg_layout.addWidget(self.cmb_builder_domain)

        # Academic Year & Date Range
        cfg_layout.addWidget(QLabel("<b>2. Academic Year & Date Range</b>"))
        self.cmb_builder_year = QComboBox()
        self.cmb_builder_year.addItem("All Academic Years", None)
        cfg_layout.addWidget(self.cmb_builder_year)

        self.chk_builder_dates = QCheckBox("Apply Date Range Filter")
        cfg_layout.addWidget(self.chk_builder_dates)
        dr_row = QHBoxLayout()
        self.dt_builder_from = QDateEdit(QDate.currentDate().addMonths(-12))
        self.dt_builder_from.setCalendarPopup(True)
        self.dt_builder_from.setDisplayFormat("yyyy-MM-dd")
        self.dt_builder_to = QDateEdit(QDate.currentDate())
        self.dt_builder_to.setCalendarPopup(True)
        self.dt_builder_to.setDisplayFormat("yyyy-MM-dd")
        dr_row.addWidget(self.dt_builder_from)
        dr_row.addWidget(QLabel("to"))
        dr_row.addWidget(self.dt_builder_to)
        cfg_layout.addLayout(dr_row)

        # Columns CheckList
        col_hdr = QHBoxLayout()
        col_hdr.addWidget(QLabel("<b>3. Columns to Include</b>"))
        btn_all_cols = QPushButton("All")
        btn_all_cols.setFixedWidth(44)
        btn_all_cols.clicked.connect(lambda: self._set_all_columns(True))
        btn_none_cols = QPushButton("None")
        btn_none_cols.setFixedWidth(48)
        btn_none_cols.clicked.connect(lambda: self._set_all_columns(False))
        col_hdr.addStretch()
        col_hdr.addWidget(btn_all_cols)
        col_hdr.addWidget(btn_none_cols)
        cfg_layout.addLayout(col_hdr)

        self.lst_columns = QListWidget()
        self.lst_columns.setMaximumHeight(160)
        cfg_layout.addWidget(self.lst_columns)

        # Grouping & Sorting
        cfg_layout.addWidget(QLabel("<b>4. Grouping & Sorting</b>"))
        grp_row = QHBoxLayout()
        grp_row.addWidget(QLabel("Group By:"))
        self.cmb_group_by = QComboBox()
        grp_row.addWidget(self.cmb_group_by)
        cfg_layout.addLayout(grp_row)

        sort_row = QHBoxLayout()
        sort_row.addWidget(QLabel("Sort By:"))
        self.cmb_sort_by = QComboBox()
        self.cmb_sort_dir = QComboBox()
        self.cmb_sort_dir.addItem("Asc", False)
        self.cmb_sort_dir.addItem("Desc", True)
        sort_row.addWidget(self.cmb_sort_by)
        sort_row.addWidget(self.cmb_sort_dir)
        cfg_layout.addLayout(sort_row)

        # Filters Section
        flt_hdr = QHBoxLayout()
        flt_hdr.addWidget(QLabel("<b>5. Custom Filters</b>"))
        btn_add_flt = QPushButton("+ Add Filter")
        btn_add_flt.clicked.connect(lambda: self._add_filter_row())
        btn_clr_flt = QPushButton("Clear")
        btn_clr_flt.clicked.connect(self._clear_filter_rows)
        flt_hdr.addStretch()
        flt_hdr.addWidget(btn_add_flt)
        flt_hdr.addWidget(btn_clr_flt)
        cfg_layout.addLayout(flt_hdr)

        self.filters_container = QVBoxLayout()
        self.filters_container.setSpacing(4)
        flt_scroll = QScrollArea()
        flt_scroll.setWidgetResizable(True)
        flt_scroll.setMinimumHeight(85)
        flt_host = QWidget()
        flt_host.setLayout(self.filters_container)
        flt_scroll.setWidget(flt_host)
        cfg_layout.addWidget(flt_scroll)

        btn_build = QPushButton("🚀 Build & Preview Report")
        btn_build.setStyleSheet(
            "background: #1E3A8A; color: white; padding: 9px; font-weight: bold; border-radius: 6px; font-size: 13px;"
        )
        btn_build.clicked.connect(self._run_builder_report)
        cfg_layout.addWidget(btn_build)

        splitter.addWidget(cfg_panel)

        # Right Panel: Built Report Results (Detailed + Grouped Rollups)
        res_panel = QWidget()
        res_layout = QVBoxLayout(res_panel)
        res_layout.setContentsMargins(6, 0, 0, 0)
        res_layout.setSpacing(8)

        view_toggle = QHBoxLayout()
        self.lbl_builder_title = QLabel("<b>Built Report Preview</b>")
        view_toggle.addWidget(self.lbl_builder_title)
        view_toggle.addStretch()
        self.chk_show_grouped = QCheckBox("Show Grouped Summary View")
        self.chk_show_grouped.toggled.connect(self._refresh_builder_table_view)
        view_toggle.addWidget(self.chk_show_grouped)
        res_layout.addLayout(view_toggle)

        self.tbl_builder = QTableWidget()
        self.tbl_builder.setAlternatingRowColors(True)
        self.tbl_builder.verticalHeader().setVisible(False)
        res_layout.addWidget(self.tbl_builder)

        self.lbl_builder_footer = QLabel("Configure options and click 'Build & Preview Report'.")
        self.lbl_builder_footer.setStyleSheet("color: #334155; font-size: 11px; font-weight: 600;")
        res_layout.addWidget(self.lbl_builder_footer)

        splitter.addWidget(res_panel)
        splitter.setSizes([360, 760])
        outer.addWidget(splitter)

        self._on_builder_domain_changed()

    def _on_builder_domain_changed(self):
        dkey = self.cmb_builder_domain.currentData() or "students"
        cols = ReportingEngine.get_domain_columns(dkey)

        self.lst_columns.clear()
        self.cmb_group_by.clear()
        self.cmb_group_by.addItem("(No Grouping)", None)
        self.cmb_sort_by.clear()
        self.cmb_sort_by.addItem("(Default Order)", None)

        for c in cols:
            item = QListWidgetItem(c["label"])
            item.setData(Qt.UserRole, c["key"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.lst_columns.addItem(item)

            self.cmb_group_by.addItem(c["label"], c["key"])
            self.cmb_sort_by.addItem(c["label"], c["key"])

        self._clear_filter_rows()

    def _set_all_columns(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.lst_columns.count()):
            self.lst_columns.item(i).setCheckState(state)

    def _clear_filter_rows(self):
        for fr in self._filter_rows:
            fr["widget"].setParent(None)
            fr["widget"].deleteLater()
        self._filter_rows.clear()

    def _add_filter_row(self, field: Optional[str] = None, op: str = "contains", value: str = ""):
        dkey = self.cmb_builder_domain.currentData() or "students"
        cols = ReportingEngine.get_domain_columns(dkey)

        row_w = QWidget()
        hl = QHBoxLayout(row_w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)

        cmb_f = QComboBox()
        for c in cols:
            cmb_f.addItem(c["label"], c["key"])
        if field:
            idx = cmb_f.findData(field)
            if idx >= 0:
                cmb_f.setCurrentIndex(idx)

        cmb_op = QComboBox()
        for op_lbl, op_val in [
            ("contains", "contains"),
            ("equals", "eq"),
            ("not eq", "neq"),
            ("starts", "starts_with"),
            (">", "gt"),
            (">=", "gte"),
            ("<", "lt"),
            ("<=", "lte"),
            ("in (comma)", "in"),
        ]:
            cmb_op.addItem(op_lbl, op_val)
        op_idx = cmb_op.findData(op)
        if op_idx >= 0:
            cmb_op.setCurrentIndex(op_idx)

        txt_v = QLineEdit(str(value or ""))
        txt_v.setPlaceholderText("Value...")

        btn_rm = QPushButton("✕")
        btn_rm.setFixedWidth(26)

        hl.addWidget(cmb_f, 3)
        hl.addWidget(cmb_op, 2)
        hl.addWidget(txt_v, 3)
        hl.addWidget(btn_rm)

        entry = {"widget": row_w, "field": cmb_f, "op": cmb_op, "value": txt_v}
        btn_rm.clicked.connect(lambda: self._remove_filter_row(entry))
        self._filter_rows.append(entry)
        self.filters_container.addWidget(row_w)

    def _remove_filter_row(self, entry: Dict[str, Any]):
        if entry in self._filter_rows:
            self._filter_rows.remove(entry)
            entry["widget"].setParent(None)
            entry["widget"].deleteLater()

    def _collect_builder_config(self) -> Dict[str, Any]:
        selected_cols = []
        for i in range(self.lst_columns.count()):
            it = self.lst_columns.item(i)
            if it.checkState() == Qt.Checked:
                selected_cols.append(it.data(Qt.UserRole))

        filters = []
        for fr in self._filter_rows:
            val = fr["value"].text().strip()
            if val:
                filters.append({
                    "field": fr["field"].currentData(),
                    "op": fr["op"].currentData(),
                    "value": val,
                })

        use_dates = self.chk_builder_dates.isChecked()
        return {
            "domain_key": self.cmb_builder_domain.currentData() or "students",
            "selected_columns": selected_cols,
            "filters": filters,
            "group_by": self.cmb_group_by.currentData(),
            "sort_by": self.cmb_sort_by.currentData(),
            "sort_desc": bool(self.cmb_sort_dir.currentData()),
            "date_from": self.dt_builder_from.date().toPython() if use_dates else None,
            "date_to": self.dt_builder_to.date().toPython() if use_dates else None,
            "academic_year_id": self.cmb_builder_year.currentData(),
        }

    def _run_builder_report(self):
        if not self.db:
            return
        self.db.expire_all()
        cfg = self._collect_builder_config()
        res = ReportingEngine.build_report(self.db, **cfg)
        self._current_builder_result = res

        if res.get("grouped_rows"):
            self.chk_show_grouped.setEnabled(True)
        else:
            self.chk_show_grouped.setChecked(False)
            self.chk_show_grouped.setEnabled(False)

        self._refresh_builder_table_view()

    def _refresh_builder_table_view(self):
        if not self._current_builder_result:
            return
        res = self._current_builder_result
        show_grp = self.chk_show_grouped.isChecked() and bool(res.get("grouped_rows"))
        self._populate_table_from_result(self.tbl_builder, res, grouped=show_grp)

        if show_grp:
            self.lbl_builder_title.setText(f"<b>Grouped Rollup Summary (By {res.get('group_by_label')})</b>")
            self.lbl_builder_footer.setText(
                f"Groups: {len(res['grouped_rows'])} | Underlying Records: {res['row_count']}"
            )
        else:
            self.lbl_builder_title.setText(f"<b>Built Report Preview — {res['domain_label']}</b>")
            tot_bits = [f"{k}: {v:,.2f}" for k, v in (res.get("totals") or {}).items()]
            tot_str = f" | Totals: {', '.join(tot_bits[:5])}" if tot_bits else ""
            self.lbl_builder_footer.setText(f"Showing {res['row_count']} records.{tot_str}")

    def _save_current_template(self):
        if not self.db:
            return
        name, ok = QInputDialog.getText(self, "Save Report Template", "Enter template name:")
        if not ok or not name.strip():
            return
        cfg = self._collect_builder_config()
        try:
            tpl = ReportingEngine.save_report_definition(self.db, name=name.strip(), **cfg)
            self._reload_saved_templates_combo(select_id=tpl.id)
            QMessageBox.information(self, "Template Saved", f"Saved report template '{tpl.name}'.")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    def _load_saved_template(self):
        if not self.db:
            return
        tpl_id = self.cmb_saved_templates.currentData()
        if not tpl_id:
            return
        from app.models.report import SavedReportDefinition
        tpl = self.db.query(SavedReportDefinition).filter(SavedReportDefinition.id == tpl_id).first()
        if not tpl:
            return

        # Apply template into builder controls
        d_idx = self.cmb_builder_domain.findData(tpl.domain_key)
        if d_idx >= 0:
            self.cmb_builder_domain.setCurrentIndex(d_idx)

        cols_set = set(tpl.get_columns())
        if cols_set:
            for i in range(self.lst_columns.count()):
                it = self.lst_columns.item(i)
                it.setCheckState(Qt.Checked if it.data(Qt.UserRole) in cols_set else Qt.Unchecked)

        if tpl.academic_year_id:
            y_idx = self.cmb_builder_year.findData(tpl.academic_year_id)
            if y_idx >= 0:
                self.cmb_builder_year.setCurrentIndex(y_idx)
        else:
            self.cmb_builder_year.setCurrentIndex(0)

        if tpl.date_from or tpl.date_to:
            self.chk_builder_dates.setChecked(True)
            if tpl.date_from:
                self.dt_builder_from.setDate(QDate.fromString(tpl.date_from, "yyyy-MM-dd"))
            if tpl.date_to:
                self.dt_builder_to.setDate(QDate.fromString(tpl.date_to, "yyyy-MM-dd"))
        else:
            self.chk_builder_dates.setChecked(False)

        g_idx = self.cmb_group_by.findData(tpl.group_by)
        self.cmb_group_by.setCurrentIndex(g_idx if g_idx >= 0 else 0)

        s_idx = self.cmb_sort_by.findData(tpl.sort_by)
        self.cmb_sort_by.setCurrentIndex(s_idx if s_idx >= 0 else 0)
        sd_idx = self.cmb_sort_dir.findData(bool(tpl.sort_desc))
        if sd_idx >= 0:
            self.cmb_sort_dir.setCurrentIndex(sd_idx)

        self._clear_filter_rows()
        for flt in tpl.get_filters():
            self._add_filter_row(field=flt.get("field"), op=flt.get("op", "contains"), value=str(flt.get("value", "")))

        self._run_builder_report()

    def _delete_saved_template(self):
        if not self.db:
            return
        tpl_id = self.cmb_saved_templates.currentData()
        if not tpl_id:
            return
        ReportingEngine.delete_saved_definition(self.db, tpl_id)
        self._reload_saved_templates_combo()

    def _reload_saved_templates_combo(self, select_id: Optional[int] = None):
        if not self.db:
            return
        self.cmb_saved_templates.clear()
        self.cmb_saved_templates.addItem("-- Select Saved Template --", None)
        for tpl in ReportingEngine.list_saved_definitions(self.db):
            self.cmb_saved_templates.addItem(f"{tpl.name} ({tpl.domain_key})", tpl.id)
        if select_id:
            idx = self.cmb_saved_templates.findData(select_id)
            if idx >= 0:
                self.cmb_saved_templates.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    # TAB 3: Live Database Analytics & Charts
    # ------------------------------------------------------------------
    def _init_analytics_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Charts Row (2 x 2 real database charts)
        chart_grid = QGridLayout()
        chart_grid.setSpacing(12)

        self.rep_chart_enrollment = RealBarChartWidget(
            title="Enrollment by Class (Real DB)",
            accent_color="#3b82f6",
            empty_message="No students recorded in database.",
        )
        self.rep_chart_finance = RealGroupedBarChartWidget(
            title="Monthly Income vs Expense (Real Ledger)",
            primary_label="Income",
            secondary_label="Expense",
            primary_color="#10b981",
            secondary_color="#ef4444",
            empty_message="No accounting transactions recorded yet.",
        )
        self.rep_chart_grades = RealHorizontalBreakdownWidget(
            title="Exam Result Grade Distribution (Real DB)",
            empty_message="No compiled exam result summaries yet.",
        )
        self.rep_chart_payroll = RealBarChartWidget(
            title="Monthly Payroll Net Disbursement (Real DB)",
            accent_color="#8b5cf6",
            empty_message="No monthly payroll slips generated yet.",
        )

        chart_grid.addWidget(self.rep_chart_enrollment, 0, 0)
        chart_grid.addWidget(self.rep_chart_finance, 0, 1)
        chart_grid.addWidget(self.rep_chart_grades, 1, 0)
        chart_grid.addWidget(self.rep_chart_payroll, 1, 1)
        layout.addLayout(chart_grid)

        # Detailed Financial & Facility Audit Text Cards
        grid_layout = QHBoxLayout()
        box1 = QGroupBox("Financial & Fee Realization Summary")
        box1.setStyleSheet("QGroupBox { font-weight: bold; color: #1E3A8A; font-size: 13px; }")
        b1_layout = QVBoxLayout(box1)
        self.lbl_finance_stats = QLabel("Loading...")
        self.lbl_finance_stats.setStyleSheet("font-size: 12px; color: #334155;")
        b1_layout.addWidget(self.lbl_finance_stats)
        grid_layout.addWidget(box1)

        box2 = QGroupBox("Academic Performance, Facilities & Inventory Audit")
        box2.setStyleSheet("QGroupBox { font-weight: bold; color: #1E3A8A; font-size: 13px; }")
        b2_layout = QVBoxLayout(box2)
        self.lbl_academic_stats = QLabel("Loading...")
        self.lbl_academic_stats.setStyleSheet("font-size: 12px; color: #334155;")
        b2_layout.addWidget(self.lbl_academic_stats)
        grid_layout.addWidget(box2)
        layout.addLayout(grid_layout)

        # Attendance Table
        att_label = QLabel("Class-by-Class Attendance Compliance Breakdown")
        att_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        att_label.setStyleSheet("color: #1E293B;")
        layout.addWidget(att_label)

        self.tbl_attendance_health = QTableWidget()
        self.tbl_attendance_health.setColumnCount(6)
        self.tbl_attendance_health.setHorizontalHeaderLabels([
            "Class / Grade", "Total Sessions", "Present", "Absent", "Late", "Attendance Rate (%)"
        ])
        self.tbl_attendance_health.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_attendance_health.setAlternatingRowColors(True)
        self.tbl_attendance_health.verticalHeader().setVisible(False)
        self.tbl_attendance_health.setMinimumHeight(200)
        layout.addWidget(self.tbl_attendance_health)

        scroll.setWidget(host)
        tab_outer = QVBoxLayout(self.tab_analytics)
        tab_outer.setContentsMargins(0, 0, 0, 0)
        tab_outer.addWidget(scroll)

    # ------------------------------------------------------------------
    # Helpers: Table Rendering, Refresh & Universal Exports
    # ------------------------------------------------------------------
    def _populate_table_from_result(
        self,
        table: QTableWidget,
        report_result: Dict[str, Any],
        grouped: bool = False,
    ):
        cols = report_result["group_columns"] if grouped else report_result["columns"]
        rows = report_result["grouped_rows"] if grouped else report_result["rows"]

        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels([c["label"] for c in cols])
        table.setRowCount(len(rows))

        for r_idx, row in enumerate(rows):
            for c_idx, cdef in enumerate(cols):
                val = row.get(cdef["key"])
                if cdef["type"] == "num" and isinstance(val, float):
                    txt = f"{val:,.2f}"
                elif val is None:
                    txt = ""
                else:
                    txt = str(val)
                item = QTableWidgetItem(txt)
                if cdef["type"] == "num":
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(r_idx, c_idx, item)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.resizeColumnsToContents()

    def refresh_all(self):
        if not self.db:
            return
        self.db.expire_all()

        # Populate academic year combos
        years = (
            self.db.query(AcademicYear)
            .filter(AcademicYear.is_deleted == False)  # noqa: E712
            .order_by(AcademicYear.start_date.desc())
            .all()
        )
        for cmb in (self.cmb_preset_year, self.cmb_builder_year):
            cur = cmb.currentData()
            cmb.blockSignals(True)
            cmb.clear()
            cmb.addItem("All Academic Years", None)
            for y in years:
                lbl = f"{y.name} (Current)" if y.is_current else y.name
                cmb.addItem(lbl, y.id)
            if cur is not None:
                idx = cmb.findData(cur)
                if idx >= 0:
                    cmb.setCurrentIndex(idx)
            cmb.blockSignals(False)

        self._reload_saved_templates_combo()

        # Refresh Live DB Analytics & KPIs
        analytics = AnalyticsService.get_dashboard_analytics(self.db)
        kpis = analytics["kpis"]

        if "Enrolled Students" in self.kpi_labels:
            self.kpi_labels["Enrolled Students"].setText(f"{kpis['active_students']} Active ({kpis['total_students']} Tot)")
        if "Attendance Rate" in self.kpi_labels:
            self.kpi_labels["Attendance Rate"].setText(f"{kpis['attendance_rate']:.1f}%")
        if "Fee Realization" in self.kpi_labels:
            self.kpi_labels["Fee Realization"].setText(f"{kpis['collection_efficiency']:.1f}%")
        if "Average GPA" in self.kpi_labels:
            self.kpi_labels["Average GPA"].setText(f"{kpis['avg_gpa']:.2f} / 5.0")
        if "Net Cashflow" in self.kpi_labels:
            self.kpi_labels["Net Cashflow"].setText(f"৳ {kpis['net_surplus']:,.2f}")

        self.rep_chart_enrollment.set_data(analytics["enrollment_by_class"])
        self.rep_chart_finance.set_data(analytics["finance_monthly_series"])
        self.rep_chart_grades.set_data(analytics["exam_grade_distribution"])
        self.rep_chart_payroll.set_data(analytics["payroll_monthly_series"])

        self.lbl_finance_stats.setText(
            f"<b>Total Fee Billing:</b> ৳ {kpis['total_invoiced']:,.2f}<br/>"
            f"<b>Total Fee Collected:</b> ৳ {kpis['total_collected']:,.2f}<br/>"
            f"<b>Outstanding Arrears:</b> ৳ {kpis['total_dues']:,.2f} ({kpis['defaulters_count']} Overdue)<br/>"
            f"<b>Accounting Income:</b> ৳ {kpis['total_income']:,.2f}<br/>"
            f"<b>Accounting Expenses:</b> ৳ {kpis['total_expenses']:,.2f}<br/>"
            f"<b>Net Payroll Processed:</b> ৳ {kpis['total_payroll_net']:,.2f}"
        )
        self.lbl_academic_stats.setText(
            f"<b>HR Strength:</b> {kpis['total_staff']} ({kpis['total_teachers']} Teachers, {kpis['total_non_teaching_staff']} Staff)<br/>"
            f"<b>Exam Assessments:</b> {kpis['total_assessed']} | Pass Rate: {kpis['pass_rate']:.1f}%<br/>"
            f"<b>Library:</b> {kpis['active_loans']} Active Loans / {kpis['total_books']} Books<br/>"
            f"<b>Transport:</b> {kpis['transport_passengers']} Commuters / {kpis['total_vehicles']} Vehicles<br/>"
            f"<b>Hostel Occupancy:</b> {kpis['hostel_occupancy_rate']:.1f}% ({kpis['hostel_occupancy']}/{kpis['hostel_capacity']} Beds)<br/>"
            f"<b>Inventory & Assets:</b> {kpis['inventory_items_count']} Items ({kpis['low_stock_count']} Low Stock) | {kpis['fixed_assets_count']} Fixed Assets"
        )

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
            if row["attendance_percentage"] >= 90:
                rate_item.setForeground(QColor("#059669"))
            elif row["attendance_percentage"] >= 75:
                rate_item.setForeground(QColor("#D97706"))
            else:
                rate_item.setForeground(QColor("#DC2626"))
            self.tbl_attendance_health.setItem(r_idx, 5, rate_item)

        self._run_preset_report()
        self._run_builder_report()

    def _export_report_result(self, report_result: Optional[Dict[str, Any]], fmt: str):
        if not report_result or not self.db:
            QMessageBox.warning(self, "No Report Data", "Please run a report first before exporting.")
            return

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        domain = report_result.get("domain_key", "report")

        if fmt == "pdf":
            path, _ = QFileDialog.getSaveFileName(self, "Export Report PDF", f"{domain}_report_{stamp}.pdf", "PDF Files (*.pdf)")
            if not path:
                return
            school = self.db.query(SchoolSetting).first()
            DynamicReportPDFGenerator.generate_pdf(report_result, school, path)
            QMessageBox.information(self, "PDF Exported", f"Report PDF saved to:\n{path}")
        elif fmt == "excel":
            path, _ = QFileDialog.getSaveFileName(self, "Export Report Excel", f"{domain}_report_{stamp}.xlsx", "Excel Files (*.xlsx)")
            if not path:
                return
            ReportingEngine.export_to_excel(report_result, path)
            QMessageBox.information(self, "Excel Exported", f"Report Excel workbook saved to:\n{path}")
        elif fmt == "csv":
            path, _ = QFileDialog.getSaveFileName(self, "Export Report CSV", f"{domain}_report_{stamp}.csv", "CSV Files (*.csv)")
            if not path:
                return
            use_grp = self.chk_show_grouped.isChecked() and report_result is self._current_builder_result
            ReportingEngine.export_to_csv(report_result, path, use_grouped_if_present=use_grp)
            QMessageBox.information(self, "CSV Exported", f"Report CSV saved to:\n{path}")

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
            QMessageBox.information(self, "Export Successful", f"Master Institutional Workbook exported!\n\nSaved to: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export Excel workbook:\n{str(e)}")
