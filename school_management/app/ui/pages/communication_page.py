"""
EduManage Pro - Enterprise Communication Center Page (PySide6)
5-Tab GUI backed by real database records covering:
1. In-App Feed (Notifications, Announcements, Notices, Alerts)
2. Event Triggers & Emergency Broadcasts (Attendance, Fee Due, Result, Admission, Emergency)
3. Configurable Provider Adapters (SMS, Email, WhatsApp Business, In-App — never hard-coded)
4. Scenario Templates
5. Complete Communication Audit Logs (Search, Retry, PDF & Multi-Sheet Excel Export)
"""

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database.connection import SessionLocal
from app.models.academic import SchoolClass
from app.models.admission import AdmissionStatus
from app.models.communication import (
    COMM_CHANNELS,
    COMM_SCENARIO_TYPES,
    DELIVERY_STATUSES,
    INAPP_ITEM_TYPES,
    CommunicationProviderConfig,
)
from app.models.exam import ExamTerm
from app.models.school import SchoolSetting
from app.reports.communication_reports_pdf import CommunicationReportsPDFGenerator
from app.repositories.communication_repository import CommunicationRepository
from app.security.session import session as app_session
from app.services.communication_service import CommunicationService
from app.ui.dialogs.communication_dialogs import (
    CommunicationTemplateDialog,
    ComposeInAppDialog,
    DirectMessageDialog,
    ProviderConfigDialog,
)


class CommunicationPage(QWidget):
    """Main Communication Center console for In-App feeds, multi-channel triggers, provider adapters, and logs."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session if db_session is not None else SessionLocal()
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Communication Center")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        subtitle = QLabel(
            "In-app notifications, announcements, notices & alerts • Configurable SMS, Email & WhatsApp Business adapters • Audit logs"
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        compose_btn = QPushButton("📣 Compose In-App")
        compose_btn.setStyleSheet("background-color: #1E3A8A; color: white; padding: 6px 12px; font-weight: 600; border-radius: 6px;")
        compose_btn.clicked.connect(self._compose_in_app)
        header_layout.addWidget(compose_btn)

        direct_btn = QPushButton("✉️ Direct Send")
        direct_btn.setStyleSheet("background-color: #0F766E; color: white; padding: 6px 12px; font-weight: 600; border-radius: 6px;")
        direct_btn.clicked.connect(self._send_direct)
        header_layout.addWidget(direct_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("background-color: #0F172A; color: white; padding: 6px 12px; font-weight: 600; border-radius: 6px;")
        refresh_btn.clicked.connect(self.refresh_all)
        header_layout.addWidget(refresh_btn)

        main_layout.addLayout(header_layout)

        # KPI Cards
        self.kpi_layout = QHBoxLayout()
        self._build_kpi_cards()
        main_layout.addLayout(self.kpi_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 8px; }
            QTabBar::tab { padding: 8px 14px; font-weight: 600; font-size: 12px; }
            QTabBar::tab:selected { background: #1E3A8A; color: white; border-top-left-radius: 6px; border-top-right-radius: 6px; }
        """)

        self.tab_feed = QWidget()
        self._init_feed_tab()
        self.tabs.addTab(self.tab_feed, "🔔 In-App Feed (Notices & Alerts)")

        self.tab_triggers = QWidget()
        self._init_triggers_tab()
        self.tabs.addTab(self.tab_triggers, "⚡ Alerts & Emergency Triggers")

        self.tab_providers = QWidget()
        self._init_providers_tab()
        self.tabs.addTab(self.tab_providers, "🔌 Provider Adapters (SMS/Email/WhatsApp)")

        self.tab_templates = QWidget()
        self._init_templates_tab()
        self.tabs.addTab(self.tab_templates, "📝 Templates")

        self.tab_logs = QWidget()
        self._init_logs_tab()
        self.tabs.addTab(self.tab_logs, "📜 Communication Audit Logs")

        main_layout.addWidget(self.tabs)
        self.refresh_all()

    def _build_kpi_cards(self):
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        stats = CommunicationRepository.get_communication_stats(self.db)
        cards = [
            ("Unread In-App Items", f"{stats.get('unread_inapp', 0)} / {stats.get('total_inapp', 0)}", "#1E3A8A"),
            ("Active Provider Adapters", str(stats.get("active_providers", 0)), "#059669"),
            ("Total Messages Logged", str(stats.get("total_logs", 0)), "#0369A1"),
            ("Delivery Rate", f"{stats.get('success_rate', 100.0):.1f}% ({stats.get('failed_logs', 0)} Failed)", "#7C3AED"),
            ("Emergency Dispatches", str(stats.get("emergency_count", 0)), "#DC2626"),
        ]
        for label, val, color in cards:
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-left: 4px solid {color};
                    border-radius: 8px;
                    padding: 6px 10px;
                }}
            """)
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(4, 2, 4, 2)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
            val_lbl = QLabel(val)
            val_lbl.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold;")
            fl.addWidget(lbl)
            fl.addWidget(val_lbl)
            self.kpi_layout.addWidget(frame)

    # -------------------------------------------------------------
    # TAB 1: In-App Notifications, Announcements, Notices & Alerts
    # -------------------------------------------------------------
    def _init_feed_tab(self):
        layout = QVBoxLayout(self.tab_feed)
        layout.setContentsMargins(12, 12, 12, 12)

        bar = QHBoxLayout()
        add_btn = QPushButton("➕ New Notification / Announcement / Notice / Alert")
        add_btn.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold;")
        add_btn.clicked.connect(self._compose_in_app)

        mark_sel = QPushButton("✓ Mark Selected Read")
        mark_sel.clicked.connect(self._mark_selected_read)

        mark_all = QPushButton("✓✓ Mark All Read")
        mark_all.clicked.connect(self._mark_all_read)

        self.feed_type_filter = QComboBox()
        self.feed_type_filter.addItems(["All"] + list(INAPP_ITEM_TYPES))
        self.feed_type_filter.currentTextChanged.connect(self._filter_feed)

        self.feed_unread_only = QCheckBox("Unread Only")
        self.feed_unread_only.stateChanged.connect(self._filter_feed)

        bar.addWidget(add_btn)
        bar.addWidget(mark_sel)
        bar.addWidget(mark_all)
        bar.addSpacing(10)
        bar.addWidget(QLabel("Type:"))
        bar.addWidget(self.feed_type_filter)
        bar.addWidget(self.feed_unread_only)
        bar.addStretch()
        layout.addLayout(bar)

        self.feed_table = QTableWidget(0, 8)
        self.feed_table.setHorizontalHeaderLabels([
            "ID", "Ref No", "Type", "Scenario", "Severity", "Audience", "Title & Message", "Status"
        ])
        self.feed_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.feed_table.setAlternatingRowColors(True)
        layout.addWidget(self.feed_table)

    def _compose_in_app(self):
        if ComposeInAppDialog(self, self.db).exec():
            self.refresh_all()

    def _send_direct(self):
        if DirectMessageDialog(self, self.db).exec():
            self.refresh_all()

    def _mark_selected_read(self):
        row = self.feed_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Item", "Select an in-app item first.")
            return
        nid = int(self.feed_table.item(row, 0).text())
        CommunicationRepository.mark_in_app_read(self.db, nid)
        self.refresh_all()

    def _mark_all_read(self):
        cnt = CommunicationRepository.mark_all_in_app_read(self.db, item_type=self.feed_type_filter.currentText())
        QMessageBox.information(self, "Updated", f"Marked {cnt} item(s) as read.")
        self.refresh_all()

    def _filter_feed(self):
        items = CommunicationRepository.get_in_app_feed(
            self.db,
            item_type=self.feed_type_filter.currentText(),
            unread_only=self.feed_unread_only.isChecked(),
        )
        self.feed_table.setRowCount(len(items))
        for r_idx, it in enumerate(items):
            self.feed_table.setItem(r_idx, 0, QTableWidgetItem(str(it.id)))
            self.feed_table.setItem(r_idx, 1, QTableWidgetItem(it.reference_no))
            self.feed_table.setItem(r_idx, 2, QTableWidgetItem(it.item_type))
            self.feed_table.setItem(r_idx, 3, QTableWidgetItem(it.scenario_type))
            sev_item = QTableWidgetItem(it.severity)
            if it.severity == "Critical":
                sev_item.setForeground(QColor("#DC2626"))
            elif it.severity == "Warning":
                sev_item.setForeground(QColor("#D97706"))
            self.feed_table.setItem(r_idx, 4, sev_item)
            self.feed_table.setItem(r_idx, 5, QTableWidgetItem(it.target_audience))
            self.feed_table.setItem(r_idx, 6, QTableWidgetItem(f"{it.title} — {it.message[:90]}"))
            self.feed_table.setItem(r_idx, 7, QTableWidgetItem("Read" if it.is_read else "Unread"))

    # -------------------------------------------------------------
    # TAB 2: Scenario Triggers & Emergency Notification
    # -------------------------------------------------------------
    def _init_triggers_tab(self):
        layout = QVBoxLayout(self.tab_triggers)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Channel selection bar
        ch_group = QGroupBox("Delivery Channels for Triggered Alerts")
        ch_layout = QHBoxLayout(ch_group)
        self.ch_checks = {}
        for ch in COMM_CHANNELS:
            cb = QCheckBox(ch)
            cb.setChecked(ch in ("InApp", "SMS"))
            self.ch_checks[ch] = cb
            ch_layout.addWidget(cb)
        ch_layout.addStretch()
        layout.addWidget(ch_group)

        # Top row: Attendance + Fee Due + Result + Admission
        top_row = QHBoxLayout()

        # 1. Attendance Alert Box
        att_box = QGroupBox("1. Attendance Alert")
        att_form = QFormLayout(att_box)
        self.att_date = QDateEdit(QDate.currentDate())
        self.att_date.setCalendarPopup(True)
        att_form.addRow("Date:", self.att_date)
        self.att_class_combo = QComboBox()
        att_form.addRow("Class:", self.att_class_combo)
        att_btn = QPushButton("🚨 Send Attendance Alerts")
        att_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold;")
        att_btn.clicked.connect(self._trigger_attendance)
        att_form.addRow(att_btn)
        top_row.addWidget(att_box)

        # 2. Fee Due Alert Box
        fee_box = QGroupBox("2. Fee Due Alert")
        fee_form = QFormLayout(fee_box)
        self.fee_overdue_check = QCheckBox("Overdue Only")
        fee_form.addRow("Filter:", self.fee_overdue_check)
        self.fee_min_due = QDoubleSpinBox()
        self.fee_min_due.setRange(1.0, 1000000.0)
        self.fee_min_due.setValue(100.0)
        fee_form.addRow("Min Due:", self.fee_min_due)
        fee_btn = QPushButton("💰 Send Fee Due Alerts")
        fee_btn.setStyleSheet("background-color: #0369A1; color: white; font-weight: bold;")
        fee_btn.clicked.connect(self._trigger_fee_due)
        fee_form.addRow(fee_btn)
        top_row.addWidget(fee_box)

        # 3. Result Notification Box
        res_box = QGroupBox("3. Result Notification")
        res_form = QFormLayout(res_box)
        self.exam_term_combo = QComboBox()
        res_form.addRow("Exam Term:", self.exam_term_combo)
        self.res_pub_only = QCheckBox("Published Only")
        self.res_pub_only.setChecked(True)
        res_form.addRow("Scope:", self.res_pub_only)
        res_btn = QPushButton("🏆 Send Result Notifications")
        res_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        res_btn.clicked.connect(self._trigger_results)
        res_form.addRow(res_btn)
        top_row.addWidget(res_box)

        # 4. Admission Notification Box
        adm_box = QGroupBox("4. Admission Notification")
        adm_form = QFormLayout(adm_box)
        self.adm_status_combo = QComboBox()
        self.adm_status_combo.addItems(["All"] + AdmissionStatus.ALL)
        adm_form.addRow("Status:", self.adm_status_combo)
        adm_btn = QPushButton("🪪 Send Admission Notices")
        adm_btn.setStyleSheet("background-color: #4338CA; color: white; font-weight: bold;")
        adm_btn.clicked.connect(self._trigger_admissions)
        adm_form.addRow(adm_btn)
        top_row.addWidget(adm_box)

        layout.addLayout(top_row)

        # 5. Emergency Notification Broadcast Box
        emg_box = QGroupBox("5. Emergency Campus Notification Broadcast (High-Priority)")
        emg_box.setStyleSheet("QGroupBox { font-weight: bold; color: #991B1B; }")
        emg_form = QFormLayout(emg_box)
        self.emg_audience = QComboBox()
        self.emg_audience.addItems(["All", "Parents", "Teachers", "Staff"])
        emg_form.addRow("Target Audience:", self.emg_audience)
        self.emg_title = QLineEdit()
        self.emg_title.setPlaceholderText("e.g., Severe Weather Campus Closure / Urgent Safety Advisory")
        emg_form.addRow("Emergency Title *:", self.emg_title)
        self.emg_msg = QTextEdit()
        self.emg_msg.setMaximumHeight(85)
        self.emg_msg.setPlaceholderText("Enter urgent emergency instructions for parents, faculty, and staff...")
        emg_form.addRow("Broadcast Message *:", self.emg_msg)
        emg_btn = QPushButton("🚨 BROADCAST EMERGENCY NOTIFICATION")
        emg_btn.setStyleSheet("background-color: #DC2626; color: white; padding: 8px 16px; font-weight: bold;")
        emg_btn.clicked.connect(self._trigger_emergency)
        emg_form.addRow(emg_btn)
        layout.addWidget(emg_box)
        layout.addStretch()

    def _selected_channels(self):
        chs = [ch for ch, cb in self.ch_checks.items() if cb.isChecked()]
        return chs or ["InApp"]

    def _actor(self) -> str:
        return app_session.current_user.username if app_session.current_user else "admin"

    def _trigger_attendance(self):
        dt = self.att_date.date().toPython()
        cid = self.att_class_combo.currentData()
        res = CommunicationService.dispatch_attendance_alerts(
            self.db,
            target_date=dt,
            class_id=cid,
            channels=self._selected_channels(),
            triggered_by=self._actor(),
        )
        QMessageBox.information(
            self,
            "Attendance Alerts Dispatched",
            f"Matched Attendance Records: {res['matched_records']}\nDispatched: {res['dispatched']} (Sent: {res['sent']}, Failed: {res['failed']})",
        )
        self.refresh_all()

    def _trigger_fee_due(self):
        res = CommunicationService.dispatch_fee_due_alerts(
            self.db,
            overdue_only=self.fee_overdue_check.isChecked(),
            min_due=float(self.fee_min_due.value()),
            channels=self._selected_channels(),
            triggered_by=self._actor(),
        )
        QMessageBox.information(
            self,
            "Fee Due Alerts Dispatched",
            f"Matched Invoices: {res['matched_invoices']}\nDispatched: {res['dispatched']} (Sent: {res['sent']}, Failed: {res['failed']})",
        )
        self.refresh_all()

    def _trigger_results(self):
        term_id = self.exam_term_combo.currentData()
        if not term_id:
            QMessageBox.warning(self, "No Exam Term", "Please select an Exam Term first.")
            return
        res = CommunicationService.dispatch_result_notifications(
            self.db,
            exam_term_id=term_id,
            published_only=self.res_pub_only.isChecked(),
            channels=self._selected_channels(),
            triggered_by=self._actor(),
        )
        QMessageBox.information(
            self,
            "Result Notifications Dispatched",
            f"Matched Results: {res['matched_results']}\nDispatched: {res['dispatched']} (Sent: {res['sent']}, Failed: {res['failed']})",
        )
        self.refresh_all()

    def _trigger_admissions(self):
        res = CommunicationService.dispatch_admission_notifications(
            self.db,
            status_filter=self.adm_status_combo.currentText(),
            channels=self._selected_channels(),
            triggered_by=self._actor(),
        )
        QMessageBox.information(
            self,
            "Admission Notifications Dispatched",
            f"Matched Applications: {res['matched_applications']}\nDispatched: {res['dispatched']} (Sent: {res['sent']}, Failed: {res['failed']})",
        )
        self.refresh_all()

    def _trigger_emergency(self):
        title = self.emg_title.text().strip()
        msg = self.emg_msg.toPlainText().strip()
        if not title or not msg:
            QMessageBox.warning(self, "Validation", "Emergency Title and Broadcast Message are required.")
            return
        res = CommunicationService.dispatch_emergency_notification(
            self.db,
            title=title,
            message=msg,
            target_audience=self.emg_audience.currentText(),
            channels=self._selected_channels(),
            triggered_by=self._actor(),
        )
        QMessageBox.information(
            self,
            "Emergency Notification Sent",
            f"Contacts Targeted: {res['recipients_targeted']}\nTotal Dispatches Logged: {res['dispatched']} (Sent: {res['sent']}, Failed: {res['failed']})",
        )
        self.emg_title.clear()
        self.emg_msg.clear()
        self.refresh_all()

    # -------------------------------------------------------------
    # TAB 3: Configurable Provider Adapters
    # -------------------------------------------------------------
    def _init_providers_tab(self):
        layout = QVBoxLayout(self.tab_providers)
        layout.setContentsMargins(12, 12, 12, 12)

        bar = QHBoxLayout()
        add_btn = QPushButton("➕ Add Provider Adapter")
        add_btn.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold;")
        add_btn.clicked.connect(self._add_provider)

        edit_btn = QPushButton("✏️ Edit Selected")
        edit_btn.clicked.connect(self._edit_provider)

        def_btn = QPushButton("⭐ Set as Default")
        def_btn.clicked.connect(self._set_default_provider)

        test_btn = QPushButton("🩺 Test Connection")
        test_btn.clicked.connect(self._test_provider)

        init_btn = QPushButton("⚙️ Initialize Starter Adapter Profiles")
        init_btn.clicked.connect(self._init_starter_configs)

        bar.addWidget(add_btn)
        bar.addWidget(edit_btn)
        bar.addWidget(def_btn)
        bar.addWidget(test_btn)
        bar.addWidget(init_btn)
        bar.addStretch()
        layout.addLayout(bar)

        self.prov_table = QTableWidget(0, 9)
        self.prov_table.setHorizontalHeaderLabels([
            "ID", "Code", "Channel", "Provider Name", "Driver Interface", "Sender / From", "Mode", "Default", "Last Test"
        ])
        self.prov_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.prov_table.setAlternatingRowColors(True)
        layout.addWidget(self.prov_table)

    def _add_provider(self):
        if ProviderConfigDialog(self, self.db).exec():
            self.refresh_all()

    def _edit_provider(self):
        row = self.prov_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Provider", "Select a provider adapter row to edit.")
            return
        pid = int(self.prov_table.item(row, 0).text())
        prov = self.db.query(CommunicationProviderConfig).filter(CommunicationProviderConfig.id == pid).first()
        if prov and ProviderConfigDialog(self, self.db, provider=prov).exec():
            self.refresh_all()

    def _set_default_provider(self):
        row = self.prov_table.currentRow()
        if row < 0:
            return
        pid = int(self.prov_table.item(row, 0).text())
        CommunicationRepository.set_default_provider(self.db, pid)
        self.refresh_all()

    def _test_provider(self):
        row = self.prov_table.currentRow()
        if row < 0:
            return
        pid = int(self.prov_table.item(row, 0).text())
        ok, msg = CommunicationRepository.test_provider_connection(self.db, pid)
        if ok:
            QMessageBox.information(self, "Adapter Health Check", f"PASS: {msg}")
        else:
            QMessageBox.warning(self, "Adapter Health Check", f"FAIL: {msg}")
        self.refresh_all()

    def _init_starter_configs(self):
        res = CommunicationService.seed_defaults_if_empty(self.db)
        QMessageBox.information(
            self,
            "Starter Adapters Initialized",
            f"Added {res['providers_added']} adapter profiles and {res['templates_added']} message templates.",
        )
        self.refresh_all()

    # -------------------------------------------------------------
    # TAB 4: Message Templates
    # -------------------------------------------------------------
    def _init_templates_tab(self):
        layout = QVBoxLayout(self.tab_templates)
        layout.setContentsMargins(12, 12, 12, 12)

        bar = QHBoxLayout()
        add_btn = QPushButton("➕ Create Template")
        add_btn.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold;")
        add_btn.clicked.connect(self._add_template)
        bar.addWidget(add_btn)
        bar.addStretch()
        layout.addLayout(bar)

        self.tpl_table = QTableWidget(0, 6)
        self.tpl_table.setHorizontalHeaderLabels(["Code", "Name", "Scenario", "Channel", "Subject", "Body Preview"])
        self.tpl_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tpl_table.setAlternatingRowColors(True)
        layout.addWidget(self.tpl_table)

    def _add_template(self):
        if CommunicationTemplateDialog(self, self.db).exec():
            self.refresh_all()

    # -------------------------------------------------------------
    # TAB 5: Communication Audit Logs
    # -------------------------------------------------------------
    def _init_logs_tab(self):
        layout = QVBoxLayout(self.tab_logs)
        layout.setContentsMargins(12, 12, 12, 12)

        bar = QHBoxLayout()
        self.log_search = QLineEdit()
        self.log_search.setPlaceholderText("Search log code, recipient, contact, provider...")
        self.log_search.textChanged.connect(self._filter_logs)

        self.log_channel_filter = QComboBox()
        self.log_channel_filter.addItems(["All"] + list(COMM_CHANNELS))
        self.log_channel_filter.currentTextChanged.connect(self._filter_logs)

        self.log_scenario_filter = QComboBox()
        self.log_scenario_filter.addItems(["All"] + list(COMM_SCENARIO_TYPES))
        self.log_scenario_filter.currentTextChanged.connect(self._filter_logs)

        self.log_status_filter = QComboBox()
        self.log_status_filter.addItems(["All"] + list(DELIVERY_STATUSES))
        self.log_status_filter.currentTextChanged.connect(self._filter_logs)

        retry_btn = QPushButton("🔁 Retry Selected")
        retry_btn.clicked.connect(self._retry_log)

        pdf_btn = QPushButton("📄 Audit PDF")
        pdf_btn.clicked.connect(self._export_pdf)

        xlsx_btn = QPushButton("📊 Export Excel (.xlsx)")
        xlsx_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        xlsx_btn.clicked.connect(self._export_excel)

        bar.addWidget(self.log_search)
        bar.addWidget(self.log_channel_filter)
        bar.addWidget(self.log_scenario_filter)
        bar.addWidget(self.log_status_filter)
        bar.addWidget(retry_btn)
        bar.addWidget(pdf_btn)
        bar.addWidget(xlsx_btn)
        layout.addLayout(bar)

        self.log_table = QTableWidget(0, 10)
        self.log_table.setHorizontalHeaderLabels([
            "ID", "Log Code", "Timestamp", "Channel", "Provider", "Scenario", "Recipient", "Contact", "Status", "Ext Ref / Error"
        ])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.log_table.setAlternatingRowColors(True)
        layout.addWidget(self.log_table)

    def _filter_logs(self):
        logs = CommunicationRepository.get_communication_logs(
            self.db,
            channel=self.log_channel_filter.currentText(),
            scenario_type=self.log_scenario_filter.currentText(),
            status=self.log_status_filter.currentText(),
            search=self.log_search.text().strip() or None,
        )
        self.log_table.setRowCount(len(logs))
        for r_idx, l in enumerate(logs):
            self.log_table.setItem(r_idx, 0, QTableWidgetItem(str(l.id)))
            self.log_table.setItem(r_idx, 1, QTableWidgetItem(l.log_code))
            self.log_table.setItem(r_idx, 2, QTableWidgetItem(str(l.sent_at)[:19] if l.sent_at else "-"))
            self.log_table.setItem(r_idx, 3, QTableWidgetItem(l.channel))
            self.log_table.setItem(r_idx, 4, QTableWidgetItem(l.provider_name))
            self.log_table.setItem(r_idx, 5, QTableWidgetItem(l.scenario_type))
            self.log_table.setItem(r_idx, 6, QTableWidgetItem(l.recipient_name))
            self.log_table.setItem(r_idx, 7, QTableWidgetItem(l.recipient_contact))
            st_item = QTableWidgetItem(l.status)
            if l.status == "Failed":
                st_item.setForeground(QColor("#DC2626"))
            elif l.status in ("Sent", "Delivered", "Read"):
                st_item.setForeground(QColor("#059669"))
            self.log_table.setItem(r_idx, 8, st_item)
            self.log_table.setItem(r_idx, 9, QTableWidgetItem(l.error_message or l.external_message_id or "-"))

    def _retry_log(self):
        row = self.log_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Log", "Select a failed communication log row to retry.")
            return
        lid = int(self.log_table.item(row, 0).text())
        try:
            updated = CommunicationRepository.retry_failed_log(self.db, lid, actor_username=self._actor())
            if updated:
                QMessageBox.information(self, "Retry Result", f"Retry status: {updated.status}")
            self.refresh_all()
        except Exception as exc:
            QMessageBox.warning(self, "Retry Error", str(exc))

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Communication Audit PDF", "Communication_Audit_Report.pdf", "PDF Files (*.pdf)")
        if path:
            school = self.db.query(SchoolSetting).first()
            logs = CommunicationRepository.get_communication_logs(self.db, limit=500)
            CommunicationReportsPDFGenerator.generate_communication_audit_pdf(logs, school=school, output_path=path)
            QMessageBox.information(self, "PDF Generated", f"Communication Audit PDF saved to:\n{path}")

    def _export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Communication Logs Workbook", "Communication_Center_Logs.xlsx", "Excel Files (*.xlsx)")
        if path:
            CommunicationService.export_communication_logs_excel(self.db, path)
            QMessageBox.information(self, "Export Complete", f"Communication workbook saved to:\n{path}")

    # -------------------------------------------------------------
    # Global Refresh
    # -------------------------------------------------------------
    def refresh_all(self):
        self._build_kpi_cards()
        self._filter_feed()
        self._filter_logs()

        # Trigger reference dropdowns from live DB
        cur_cls = self.att_class_combo.currentData()
        self.att_class_combo.clear()
        self.att_class_combo.addItem("All Classes", None)
        for cls in self.db.query(SchoolClass).order_by(SchoolClass.numeric_order.asc()).all():
            self.att_class_combo.addItem(cls.name, cls.id)
        if cur_cls is not None:
            idx = self.att_class_combo.findData(cur_cls)
            if idx >= 0:
                self.att_class_combo.setCurrentIndex(idx)

        cur_term = self.exam_term_combo.currentData()
        self.exam_term_combo.clear()
        for t in self.db.query(ExamTerm).order_by(ExamTerm.id.desc()).all():
            self.exam_term_combo.addItem(t.name, t.id)
        if cur_term is not None:
            idx = self.exam_term_combo.findData(cur_term)
            if idx >= 0:
                self.exam_term_combo.setCurrentIndex(idx)

        # Providers table
        provs = CommunicationRepository.get_providers(self.db)
        self.prov_table.setRowCount(len(provs))
        for r_idx, p in enumerate(provs):
            self.prov_table.setItem(r_idx, 0, QTableWidgetItem(str(p.id)))
            self.prov_table.setItem(r_idx, 1, QTableWidgetItem(p.provider_code))
            self.prov_table.setItem(r_idx, 2, QTableWidgetItem(p.channel))
            self.prov_table.setItem(r_idx, 3, QTableWidgetItem(p.provider_name))
            self.prov_table.setItem(r_idx, 4, QTableWidgetItem(p.driver_key))
            self.prov_table.setItem(r_idx, 5, QTableWidgetItem(p.sender_id or "-"))
            self.prov_table.setItem(r_idx, 6, QTableWidgetItem("Sandbox" if p.sandbox_mode else "Live"))
            self.prov_table.setItem(r_idx, 7, QTableWidgetItem("Default" if p.is_default else f"P{p.priority_order}"))
            self.prov_table.setItem(r_idx, 8, QTableWidgetItem(p.last_test_status or "Untested"))

        # Templates table
        tpls = CommunicationRepository.get_templates(self.db)
        self.tpl_table.setRowCount(len(tpls))
        for r_idx, t in enumerate(tpls):
            self.tpl_table.setItem(r_idx, 0, QTableWidgetItem(t.template_code))
            self.tpl_table.setItem(r_idx, 1, QTableWidgetItem(t.name))
            self.tpl_table.setItem(r_idx, 2, QTableWidgetItem(t.scenario_type))
            self.tpl_table.setItem(r_idx, 3, QTableWidgetItem(t.channel))
            self.tpl_table.setItem(r_idx, 4, QTableWidgetItem(t.subject_template or "-"))
            self.tpl_table.setItem(r_idx, 5, QTableWidgetItem(t.body_template[:90]))
