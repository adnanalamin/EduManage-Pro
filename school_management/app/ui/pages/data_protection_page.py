"""
EduManage Pro - Professional Data Protection, Encrypted Backup & Migration Wizard UI
Features:
1. Backup & Recovery: Manual/Automatic/Daily/Weekly/Monthly, Encrypted Fernet containers,
   Verification in isolated staging, Backup History, and Safe Restore w/ Mandatory Pre-Restore Backup.
2. Automated Backup Scheduler Policy & Live Timer.
3. 6-Step Data Migration Wizard: Upload -> Detect -> Map -> Validate -> Preview -> Import
   (Excel, CSV, Previous SQLite Database) with zero-corruption & non-overwrite safety.
4. Migration Audit Ledger & Atomic Rollback Console.
"""

import json
from typing import Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import BACKUPS_DIR
from app.database.connection import SessionLocal
from app.models.data_protection import (
    BACKUP_SCHEDULE_MODES,
    MIGRATION_CONFLICT_POLICIES,
    MIGRATION_TARGET_ENTITIES,
)
from app.services.backup_service import DataProtectionBackupService
from app.services.data_migration_service import DataMigrationService, TARGET_FIELD_SPECS


class DataProtectionPage(QWidget):
    """Unified Backup/Restore & 6-Step Data Migration Wizard Studio."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session or SessionLocal()
        self._active_batch_id: Optional[int] = None
        self._mapping_combos: Dict[str, QComboBox] = {}
        self._init_ui()

        # Background non-blocking scheduler check (every 5 minutes)
        self._sched_timer = QTimer(self)
        self._sched_timer.timeout.connect(self._check_due_schedule)
        self._sched_timer.start(300_000)

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        tcol = QVBoxLayout()
        title = QLabel("Data Protection, Encrypted Backup & Migration Center")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        sub = QLabel(
            "Encrypted Manual & Scheduled Backups • Pre-Restore Safety Snapshots • Reversible 6-Step Excel/CSV/DB Migration Wizard"
        )
        sub.setStyleSheet("color: #64748B; font-size: 12px;")
        tcol.addWidget(title)
        tcol.addWidget(sub)
        hdr.addLayout(tcol)
        hdr.addStretch()

        btn_ref = QPushButton("🔄 Refresh Status")
        btn_ref.setStyleSheet("background: #2563EB; color: white; padding: 7px 14px; font-weight: bold; border-radius: 6px;")
        btn_ref.clicked.connect(self.refresh_all)
        hdr.addWidget(btn_ref)
        root.addLayout(hdr)

        # KPI Cards
        self.kpi_layout = QHBoxLayout()
        self._build_kpi_cards()
        root.addLayout(self.kpi_layout)

        # Main Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 8px; }
            QTabBar::tab { padding: 8px 16px; font-weight: 600; font-size: 12px; }
            QTabBar::tab:selected { background: #1E3A8A; color: white; border-top-left-radius: 6px; border-top-right-radius: 6px; }
        """)

        self.tab_backups = QWidget()
        self._init_backups_tab()
        self.tabs.addTab(self.tab_backups, "🛡️ Backup, Verify & Restore")

        self.tab_schedule = QWidget()
        self._init_schedule_tab()
        self.tabs.addTab(self.tab_schedule, "⏰ Automated Backup Schedule")

        self.tab_wizard = QWidget()
        self._init_wizard_tab()
        self.tabs.addTab(self.tab_wizard, "🪄 6-Step Data Migration Wizard")

        self.tab_mig_history = QWidget()
        self._init_migration_history_tab()
        self.tabs.addTab(self.tab_mig_history, "⏪ Migration History & Rollback")

        root.addWidget(self.tabs)
        self.refresh_all()

    def _build_kpi_cards(self):
        cards = [
            ("Total Backups", "0", "#1E3A8A", "💾"),
            ("Verified Safe", "0", "#059669", "✅"),
            ("Encrypted Vaults", "0", "#7C3AED", "🔐"),
            ("Pre-Restore Guards", "0", "#D97706", "🛡️"),
            ("Active Schedule", "Daily", "#0284C7", "⏰"),
        ]
        self.kpi_labels = {}
        for title, val, col, icon in cards:
            frame = QFrame()
            frame.setStyleSheet(
                f"QFrame {{ background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid {col}; border-radius: 8px; padding: 6px; }}"
            )
            fl = QVBoxLayout(frame)
            top = QHBoxLayout()
            tl = QLabel(title)
            tl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
            top.addWidget(tl)
            top.addStretch()
            top.addWidget(QLabel(icon))
            fl.addLayout(top)
            vl = QLabel(val)
            vl.setFont(QFont("Segoe UI", 14, QFont.Bold))
            vl.setStyleSheet("color: #0F172A;")
            fl.addWidget(vl)
            self.kpi_labels[title] = vl
            self.kpi_layout.addWidget(frame)

    # ------------------------------------------------------------------ #
    # TAB 1: Backup, Verification & Restore
    # ------------------------------------------------------------------ #
    def _init_backups_tab(self):
        lay = QVBoxLayout(self.tab_backups)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(12)

        # Quick Create Bar
        create_box = QFrame()
        create_box.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px;")
        c_lay = QHBoxLayout(create_box)

        self.cmb_bkp_mode = QComboBox()
        self.cmb_bkp_mode.addItems(BACKUP_SCHEDULE_MODES)
        c_lay.addWidget(QLabel("<b>Mode:</b>"))
        c_lay.addWidget(self.cmb_bkp_mode)

        self.txt_bkp_passphrase = QLineEdit()
        self.txt_bkp_passphrase.setEchoMode(QLineEdit.Password)
        self.txt_bkp_passphrase.setPlaceholderText("Optional custom passphrase (blank = institutional vault key)")
        c_lay.addWidget(self.txt_bkp_passphrase, 2)

        self.chk_bkp_encrypt = QCheckBox("Encrypt (AES+HMAC)")
        self.chk_bkp_encrypt.setChecked(True)
        c_lay.addWidget(self.chk_bkp_encrypt)

        self.txt_bkp_notes = QLineEdit()
        self.txt_bkp_notes.setPlaceholderText("Backup label / notes...")
        c_lay.addWidget(self.txt_bkp_notes, 2)

        btn_create = QPushButton("🔐 Create Verified Backup Now")
        btn_create.setStyleSheet("background: #059669; color: white; padding: 7px 14px; font-weight: bold; border-radius: 6px;")
        btn_create.clicked.connect(self._create_manual_backup)
        c_lay.addWidget(btn_create)
        lay.addWidget(create_box)

        # Action Bar
        act = QHBoxLayout()
        btn_verify = QPushButton("🔍 Verify Selected Backup")
        btn_verify.setStyleSheet("background: #0284C7; color: white; padding: 6px 12px; font-weight: bold; border-radius: 5px;")
        btn_verify.clicked.connect(self._verify_selected_backup)
        act.addWidget(btn_verify)

        btn_restore = QPushButton("♻️ Restore Selected (Auto Pre-Restore Backup)")
        btn_restore.setStyleSheet("background: #D97706; color: white; padding: 6px 12px; font-weight: bold; border-radius: 5px;")
        btn_restore.clicked.connect(self._restore_selected_backup)
        act.addWidget(btn_restore)

        btn_ext = QPushButton("📂 Restore External Backup File...")
        btn_ext.clicked.connect(self._restore_external_file)
        act.addWidget(btn_ext)
        act.addStretch()
        lay.addLayout(act)

        self.tbl_backups = QTableWidget(0, 10)
        self.tbl_backups.setHorizontalHeaderLabels([
            "ID", "Backup Code", "Mode", "Trigger", "Pre-Restore",
            "Encrypted", "Size (KB)", "SHA-256", "Verification", "Status"
        ])
        self.tbl_backups.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_backups.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_backups.setAlternatingRowColors(True)
        self.tbl_backups.verticalHeader().setVisible(False)
        lay.addWidget(self.tbl_backups)

    # ------------------------------------------------------------------ #
    # TAB 2: Automated Backup Scheduler
    # ------------------------------------------------------------------ #
    def _init_schedule_tab(self):
        lay = QVBoxLayout(self.tab_schedule)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.chk_sched_enabled = QCheckBox("Enable Automated Data Protection Backups")
        form.addRow("Automation Status:", self.chk_sched_enabled)

        self.cmb_sched_freq = QComboBox()
        self.cmb_sched_freq.addItems(["Automatic", "Daily", "Weekly", "Monthly"])
        form.addRow("Backup Frequency:", self.cmb_sched_freq)

        self.spn_sched_interval = QSpinBox()
        self.spn_sched_interval.setRange(1, 168)
        self.spn_sched_interval.setSuffix(" hours")
        form.addRow("Interval (Automatic Mode):", self.spn_sched_interval)

        self.txt_sched_time = QLineEdit("23:00")
        form.addRow("Preferred Time (HH:MM):", self.txt_sched_time)

        self.cmb_sched_dow = QComboBox()
        self.cmb_sched_dow.addItems(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        form.addRow("Day of Week (Weekly):", self.cmb_sched_dow)

        self.spn_sched_dom = QSpinBox()
        self.spn_sched_dom.setRange(1, 28)
        form.addRow("Day of Month (Monthly):", self.spn_sched_dom)

        self.spn_sched_retention = QSpinBox()
        self.spn_sched_retention.setRange(3, 365)
        self.spn_sched_retention.setSuffix(" backups")
        form.addRow("Retention Policy:", self.spn_sched_retention)

        self.chk_sched_encrypt = QCheckBox("Always Encrypt Scheduled Backups")
        self.chk_sched_verify = QCheckBox("Auto-Verify Integrity After Creation")
        form.addRow("Encryption:", self.chk_sched_encrypt)
        form.addRow("Integrity Check:", self.chk_sched_verify)

        dir_row = QHBoxLayout()
        self.txt_sched_dir = QLineEdit(str(BACKUPS_DIR))
        btn_dir = QPushButton("Browse...")
        btn_dir.clicked.connect(self._browse_backup_dir)
        dir_row.addWidget(self.txt_sched_dir)
        dir_row.addWidget(btn_dir)
        form.addRow("Vault Directory:", dir_row)

        self.lbl_sched_next = QLabel("-")
        self.lbl_sched_last = QLabel("-")
        form.addRow("Last Run:", self.lbl_sched_last)
        form.addRow("Next Scheduled Run:", self.lbl_sched_next)
        lay.addLayout(form)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("💾 Save Schedule Policy")
        btn_save.setStyleSheet("background: #1E3A8A; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        btn_save.clicked.connect(self._save_schedule)
        btn_row.addWidget(btn_save)

        btn_run_now = QPushButton("▶️ Execute Scheduled Backup Now")
        btn_run_now.setStyleSheet("background: #059669; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        btn_run_now.clicked.connect(self._run_scheduled_now)
        btn_row.addWidget(btn_run_now)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        lay.addStretch()

    # ------------------------------------------------------------------ #
    # TAB 3: 6-Step Data Migration Wizard
    # ------------------------------------------------------------------ #
    def _init_wizard_tab(self):
        lay = QVBoxLayout(self.tab_wizard)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        # Visual Step Bar
        self.step_labels = []
        step_bar = QHBoxLayout()
        for idx, sname in enumerate([
            "1. Upload", "2. Detect", "3. Map", "4. Validate", "5. Preview", "6. Import"
        ]):
            lbl = QLabel(sname)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("padding: 6px 10px; border-radius: 5px; background: #E2E8F0; color: #334155; font-weight: bold;")
            self.step_labels.append(lbl)
            step_bar.addWidget(lbl)
        lay.addLayout(step_bar)

        self.wiz_stack = QStackedWidget()

        # Step 1: Upload
        s1 = QWidget()
        s1_lay = QFormLayout(s1)
        s1_lay.setSpacing(10)
        file_row = QHBoxLayout()
        self.txt_mig_file = QLineEdit()
        self.txt_mig_file.setPlaceholderText("Select Excel (.xlsx), CSV (.csv), or Previous SQLite Database (.db)...")
        btn_browse_mig = QPushButton("📂 Choose File...")
        btn_browse_mig.clicked.connect(self._browse_migration_file)
        file_row.addWidget(self.txt_mig_file)
        file_row.addWidget(btn_browse_mig)
        s1_lay.addRow("Source Data File:", file_row)

        self.cmb_mig_entity = QComboBox()
        self.cmb_mig_entity.addItems(MIGRATION_TARGET_ENTITIES)
        s1_lay.addRow("Target Module:", self.cmb_mig_entity)

        btn_step1 = QPushButton("Step 1 → Upload & Stage File")
        btn_step1.setStyleSheet("background: #1E3A8A; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        btn_step1.clicked.connect(self._wiz_do_upload)
        s1_lay.addRow("", btn_step1)
        self.wiz_stack.addWidget(s1)

        # Step 2: Detect
        s2 = QWidget()
        s2_lay = QVBoxLayout(s2)
        d_bar = QHBoxLayout()
        d_bar.addWidget(QLabel("<b>Detected Worksheet / DB Table:</b>"))
        self.cmb_mig_sheet = QComboBox()
        d_bar.addWidget(self.cmb_mig_sheet, 1)
        btn_redetect = QPushButton("🔍 Inspect Selected Sheet/Table")
        btn_redetect.clicked.connect(self._wiz_do_detect)
        d_bar.addWidget(btn_redetect)
        s2_lay.addLayout(d_bar)
        self.lbl_detect_info = QLabel("Upload a file to detect schema.")
        self.lbl_detect_info.setStyleSheet("background: #F8FAFC; border: 1px solid #CBD5E1; padding: 10px; border-radius: 6px;")
        s2_lay.addWidget(self.lbl_detect_info)
        btn_to_map = QPushButton("Step 2 → Proceed to Column Mapping")
        btn_to_map.setStyleSheet("background: #1E3A8A; color: white; padding: 8px; font-weight: bold; border-radius: 6px;")
        btn_to_map.clicked.connect(lambda: self._set_wizard_step(2))
        s2_lay.addWidget(btn_to_map)
        self.wiz_stack.addWidget(s2)

        # Step 3: Map
        s3 = QWidget()
        s3_lay = QVBoxLayout(s3)
        pol_row = QHBoxLayout()
        pol_row.addWidget(QLabel("<b>Conflict Safety Policy (Never Silently Overwrites):</b>"))
        self.cmb_mig_policy = QComboBox()
        self.cmb_mig_policy.addItems(MIGRATION_CONFLICT_POLICIES)
        pol_row.addWidget(self.cmb_mig_policy)
        s3_lay.addLayout(pol_row)

        self.tbl_mapping = QTableWidget(0, 3)
        self.tbl_mapping.setHorizontalHeaderLabels(["Target System Field", "Required?", "Mapped Source Column"])
        self.tbl_mapping.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        s3_lay.addWidget(self.tbl_mapping)

        btn_to_val = QPushButton("Step 3 → Save Mapping & Run Validation")
        btn_to_val.setStyleSheet("background: #1E3A8A; color: white; padding: 8px; font-weight: bold; border-radius: 6px;")
        btn_to_val.clicked.connect(self._wiz_save_map_and_validate)
        s3_lay.addWidget(btn_to_val)
        self.wiz_stack.addWidget(s3)

        # Step 4: Validate
        s4 = QWidget()
        s4_lay = QVBoxLayout(s4)
        self.lbl_val_summary = QLabel("Validation summary...")
        self.lbl_val_summary.setWordWrap(True)
        self.lbl_val_summary.setStyleSheet("background: #F8FAFC; border: 1px solid #CBD5E1; padding: 14px; border-radius: 6px; font-size: 13px;")
        s4_lay.addWidget(self.lbl_val_summary)
        btn_to_prev = QPushButton("Step 4 → Generate Dry-Run Preview")
        btn_to_prev.setStyleSheet("background: #0284C7; color: white; padding: 8px; font-weight: bold; border-radius: 6px;")
        btn_to_prev.clicked.connect(self._wiz_do_preview)
        s4_lay.addWidget(btn_to_prev)
        self.wiz_stack.addWidget(s4)

        # Step 5: Preview
        s5 = QWidget()
        s5_lay = QVBoxLayout(s5)
        self.tbl_mig_preview = QTableWidget(0, 4)
        self.tbl_mig_preview.setHorizontalHeaderLabels(["Row #", "Planned Action", "Safety Decision / Reason", "Mapped Data Snapshot"])
        self.tbl_mig_preview.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        s5_lay.addWidget(self.tbl_mig_preview)
        btn_to_imp = QPushButton("Step 5 → Review & Proceed to Import")
        btn_to_imp.setStyleSheet("background: #059669; color: white; padding: 8px; font-weight: bold; border-radius: 6px;")
        btn_to_imp.clicked.connect(lambda: self._set_wizard_step(5))
        s5_lay.addWidget(btn_to_imp)
        self.wiz_stack.addWidget(s5)

        # Step 6: Import
        s6 = QWidget()
        s6_lay = QVBoxLayout(s6)
        self.chk_mig_pre_backup = QCheckBox("Create Automatic Pre-Migration Encrypted Safety Backup Before Importing (Recommended)")
        self.chk_mig_pre_backup.setChecked(True)
        s6_lay.addWidget(self.chk_mig_pre_backup)
        self.lbl_import_ready = QLabel("Ready to execute atomic import. Existing records will never be corrupted or silently overwritten.")
        self.lbl_import_ready.setWordWrap(True)
        self.lbl_import_ready.setStyleSheet("background: #ECFDF5; border: 1px solid #10B981; color: #065F46; padding: 14px; border-radius: 6px;")
        s6_lay.addWidget(self.lbl_import_ready)

        btn_exec = QPushButton("🚀 Step 6 → Execute Atomic Import Now")
        btn_exec.setStyleSheet("background: #059669; color: white; padding: 10px; font-weight: bold; border-radius: 6px;")
        btn_exec.clicked.connect(self._wiz_execute_import)
        s6_lay.addWidget(btn_exec)
        s6_lay.addStretch()
        self.wiz_stack.addWidget(s6)

        lay.addWidget(self.wiz_stack)
        self._set_wizard_step(0)

    # ------------------------------------------------------------------ #
    # TAB 4: Migration History & Rollback Console
    # ------------------------------------------------------------------ #
    def _init_migration_history_tab(self):
        lay = QVBoxLayout(self.tab_mig_history)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        bar = QHBoxLayout()
        btn_logs = QPushButton("🔎 View Row Audit Ledger")
        btn_logs.setStyleSheet("background: #0284C7; color: white; padding: 6px 12px; font-weight: bold; border-radius: 5px;")
        btn_logs.clicked.connect(self._load_selected_batch_logs)
        bar.addWidget(btn_logs)

        btn_rb = QPushButton("⏪ Rollback Selected Migration Batch")
        btn_rb.setStyleSheet("background: #DC2626; color: white; padding: 6px 12px; font-weight: bold; border-radius: 5px;")
        btn_rb.clicked.connect(self._rollback_selected_batch)
        bar.addWidget(btn_rb)
        bar.addStretch()
        lay.addLayout(bar)

        splitter = QSplitter(Qt.Vertical)
        self.tbl_mig_batches = QTableWidget(0, 9)
        self.tbl_mig_batches.setHorizontalHeaderLabels([
            "ID", "Batch Code", "Source", "Filename", "Target", "Policy", "Inserted / Skipped", "Pre-Backup", "Status"
        ])
        self.tbl_mig_batches.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_mig_batches.setSelectionBehavior(QAbstractItemView.SelectRows)
        splitter.addWidget(self.tbl_mig_batches)

        self.tbl_mig_logs = QTableWidget(0, 6)
        self.tbl_mig_logs.setHorizontalHeaderLabels([
            "Row #", "Action", "Target Table", "Record ID", "Rolled Back?", "Audit Message"
        ])
        self.tbl_mig_logs.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        splitter.addWidget(self.tbl_mig_logs)
        lay.addWidget(splitter)

    # ------------------------------------------------------------------ #
    # Handlers & State Synchronization
    # ------------------------------------------------------------------ #
    def _set_wizard_step(self, step_idx: int):
        self.wiz_stack.setCurrentIndex(step_idx)
        for i, lbl in enumerate(self.step_labels):
            if i == step_idx:
                lbl.setStyleSheet("padding: 6px 10px; border-radius: 5px; background: #1E3A8A; color: white; font-weight: bold;")
            elif i < step_idx:
                lbl.setStyleSheet("padding: 6px 10px; border-radius: 5px; background: #059669; color: white; font-weight: bold;")
            else:
                lbl.setStyleSheet("padding: 6px 10px; border-radius: 5px; background: #E2E8F0; color: #334155; font-weight: bold;")

    def refresh_all(self):
        stats = DataProtectionBackupService.get_stats(self.db)
        self.kpi_labels["Total Backups"].setText(str(stats["total_backups"]))
        self.kpi_labels["Verified Safe"].setText(str(stats["verified_backups"]))
        self.kpi_labels["Encrypted Vaults"].setText(str(stats["encrypted_backups"]))
        self.kpi_labels["Pre-Restore Guards"].setText(str(stats["pre_restore_backups"]))
        self.kpi_labels["Active Schedule"].setText(f"{stats['schedule_frequency']} ({'ON' if stats['schedule_enabled'] else 'OFF'})")
        self._load_backups_table()
        self._load_schedule_form()
        self._load_migration_batches()

    def _check_due_schedule(self):
        try:
            DataProtectionBackupService.run_due_scheduled_backup(self.db)
            self.refresh_all()
        except Exception:
            pass

    def _load_backups_table(self):
        rows = DataProtectionBackupService.list_backup_history(self.db)
        self.tbl_backups.setRowCount(len(rows))
        for r, b in enumerate(rows):
            self.tbl_backups.setItem(r, 0, QTableWidgetItem(str(b.id)))
            self.tbl_backups.setItem(r, 1, QTableWidgetItem(b.backup_code))
            self.tbl_backups.setItem(r, 2, QTableWidgetItem(b.schedule_mode))
            self.tbl_backups.setItem(r, 3, QTableWidgetItem(b.trigger_source))
            self.tbl_backups.setItem(r, 4, QTableWidgetItem("Yes" if b.is_pre_restore else "No"))
            self.tbl_backups.setItem(r, 5, QTableWidgetItem("🔐 Yes" if b.is_encrypted else "No"))
            self.tbl_backups.setItem(r, 6, QTableWidgetItem(f"{b.file_size_bytes / 1024.0:.1f}"))
            self.tbl_backups.setItem(r, 7, QTableWidgetItem(b.checksum_sha256[:14] + "..."))
            v_item = QTableWidgetItem(b.verification_status)
            v_item.setForeground(QColor("#059669" if b.verification_status == "Verified" else "#DC2626"))
            self.tbl_backups.setItem(r, 8, v_item)
            self.tbl_backups.setItem(r, 9, QTableWidgetItem(b.status))

    def _create_manual_backup(self):
        try:
            bkp = DataProtectionBackupService.create_backup(
                self.db,
                schedule_mode=self.cmb_bkp_mode.currentText(),
                encrypt=self.chk_bkp_encrypt.isChecked(),
                passphrase=self.txt_bkp_passphrase.text() or None,
                verify=True,
                notes=self.txt_bkp_notes.text().strip() or None,
            )
            self.refresh_all()
            QMessageBox.information(
                self,
                "Backup Created & Verified",
                f"Backup {bkp.backup_code} created ({bkp.verification_status}).\nFile: {bkp.file_path}",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Backup Error", str(exc))

    def _verify_selected_backup(self):
        row = self.tbl_backups.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Select Backup", "Select a backup row first.")
            return
        bid = int(self.tbl_backups.item(row, 0).text())
        rows = {b.id: b for b in DataProtectionBackupService.list_backup_history(self.db)}
        b = rows.get(bid)
        if not b:
            return
        pw = self.txt_bkp_passphrase.text() or None
        res = DataProtectionBackupService.verify_backup(self.db, b.file_path, passphrase=pw, backup_id=b.id)
        self.refresh_all()
        if res["ok"]:
            QMessageBox.information(self, "Verification Passed", f"Backup {b.backup_code} verified!\n{res['notes']}")
        else:
            QMessageBox.critical(self, "Verification Failed", str(res.get("error") or res.get("notes")))

    def _restore_selected_backup(self):
        row = self.tbl_backups.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Select Backup", "Select a backup row first.")
            return
        bid = int(self.tbl_backups.item(row, 0).text())
        confirm = QMessageBox.question(
            self,
            "Confirm Safe Restore",
            "Restore database from selected backup?\nA mandatory Pre-Restore Safety Backup of your live database will be taken automatically BEFORE restoring.",
        )
        if confirm != QMessageBox.Yes:
            return
        pw = self.txt_bkp_passphrase.text() or None
        try:
            res = DataProtectionBackupService.restore_backup(self.db, bid, passphrase=pw, target_engine=self.db.get_bind())
            self.db = SessionLocal()
            self.refresh_all()
            QMessageBox.information(
                self,
                "Restore Completed Safely",
                f"Restored cleanly!\nPre-Restore Safety Backup created: {res['pre_restore_backup_code']}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Restore Aborted", str(exc))

    def _restore_external_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select Backup Archive", str(BACKUPS_DIR), "Backup Files (*.ebk *.zbk)")
        if not p:
            return
        pw, _ = QInputDialog.getText(self, "Backup Passphrase", "Enter passphrase (leave blank if institutional default):", QLineEdit.Password)
        try:
            res = DataProtectionBackupService.restore_backup(self.db, p, passphrase=pw or None, target_engine=self.db.get_bind())
            self.db = SessionLocal()
            self.refresh_all()
            QMessageBox.information(self, "External Restore Complete", f"Restored from external file.\nPre-Restore Safety Backup: {res['pre_restore_backup_code']}")
        except Exception as exc:
            QMessageBox.critical(self, "Restore Aborted", str(exc))

    def _load_schedule_form(self):
        cfg = DataProtectionBackupService.get_or_create_schedule(self.db)
        self.chk_sched_enabled.setChecked(bool(cfg.is_enabled))
        self.cmb_sched_freq.setCurrentText(cfg.frequency)
        self.spn_sched_interval.setValue(int(cfg.interval_hours or 24))
        self.txt_sched_time.setText(cfg.preferred_time or "23:00")
        self.cmb_sched_dow.setCurrentIndex(int(cfg.day_of_week or 0))
        self.spn_sched_dom.setValue(int(cfg.day_of_month or 1))
        self.spn_sched_retention.setValue(int(cfg.retention_count or 30))
        self.chk_sched_encrypt.setChecked(bool(cfg.encrypt_backups))
        self.chk_sched_verify.setChecked(bool(cfg.verify_after_backup))
        self.txt_sched_dir.setText(cfg.backup_directory or str(BACKUPS_DIR))
        self.lbl_sched_last.setText(f"{cfg.last_run_at or 'Never'} ({cfg.last_status})")
        self.lbl_sched_next.setText(str(cfg.next_run_at or "-"))

    def _browse_backup_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Backup Directory", self.txt_sched_dir.text())
        if d:
            self.txt_sched_dir.setText(d)

    def _save_schedule(self):
        DataProtectionBackupService.update_schedule(
            self.db,
            is_enabled=self.chk_sched_enabled.isChecked(),
            frequency=self.cmb_sched_freq.currentText(),
            interval_hours=self.spn_sched_interval.value(),
            preferred_time=self.txt_sched_time.text().strip() or "23:00",
            day_of_week=self.cmb_sched_dow.currentIndex(),
            day_of_month=self.spn_sched_dom.value(),
            retention_count=self.spn_sched_retention.value(),
            encrypt_backups=self.chk_sched_encrypt.isChecked(),
            verify_after_backup=self.chk_sched_verify.isChecked(),
            backup_directory=self.txt_sched_dir.text().strip() or str(BACKUPS_DIR),
        )
        self.refresh_all()
        QMessageBox.information(self, "Schedule Saved", "Automated backup policy updated.")

    def _run_scheduled_now(self):
        bkp = DataProtectionBackupService.run_due_scheduled_backup(self.db, force=True)
        self.refresh_all()
        if bkp:
            QMessageBox.information(self, "Scheduled Backup Complete", f"Created scheduled {bkp.schedule_mode} backup: {bkp.backup_code}")

    # ------------------------------------------------------------------ #
    # 6-Step Migration Wizard Handlers
    # ------------------------------------------------------------------ #
    def _browse_migration_file(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Select Migration Source", "", "Supported Sources (*.csv *.xlsx *.xlsm *.db *.sqlite *.sqlite3)"
        )
        if p:
            self.txt_mig_file.setText(p)

    def _wiz_do_upload(self):
        fpath = self.txt_mig_file.text().strip()
        if not fpath:
            QMessageBox.warning(self, "File Required", "Choose a CSV, Excel, or SQLite DB file first.")
            return
        try:
            batch = DataMigrationService.upload_source(
                self.db, fpath, target_entity=self.cmb_mig_entity.currentText()
            )
            self._active_batch_id = batch.id
            det = DataMigrationService.detect_schema(self.db, batch.id)
            self.cmb_mig_sheet.clear()
            self.cmb_mig_sheet.addItems(det["sheets_or_tables"])
            self.cmb_mig_sheet.setCurrentText(det["selected_sheet_or_table"])
            self._populate_detect_and_mapping(det)
            self._set_wizard_step(1)
        except Exception as exc:
            QMessageBox.warning(self, "Upload Error", str(exc))

    def _wiz_do_detect(self):
        if not self._active_batch_id:
            return
        det = DataMigrationService.detect_schema(self.db, self._active_batch_id, sheet_or_table=self.cmb_mig_sheet.currentText())
        self._populate_detect_and_mapping(det)

    def _populate_detect_and_mapping(self, det: dict):
        self.lbl_detect_info.setText(
            f"<b>Batch:</b> {det['batch_code']} | <b>Type:</b> {det['source_type']} | "
            f"<b>Sheet/Table:</b> {det['selected_sheet_or_table']} | <b>Rows Found:</b> {det['total_rows']}<br/>"
            f"<b>Detected Columns:</b> {', '.join(det['headers'])}"
        )
        headers = ["(Unmapped)"] + det["headers"]
        target_fields = det["target_fields"]
        req_set = set(det["required_fields"])
        suggested = det["suggested_mapping"]

        self.tbl_mapping.setRowCount(len(target_fields))
        self._mapping_combos.clear()
        for r, tf in enumerate(target_fields):
            self.tbl_mapping.setItem(r, 0, QTableWidgetItem(tf))
            self.tbl_mapping.setItem(r, 1, QTableWidgetItem("Required" if tf in req_set else "Optional"))
            cmb = QComboBox()
            cmb.addItems(headers)
            if tf in suggested and suggested[tf] in headers:
                cmb.setCurrentText(suggested[tf])
            self._mapping_combos[tf] = cmb
            self.tbl_mapping.setCellWidget(r, 2, cmb)

    def _wiz_save_map_and_validate(self):
        if not self._active_batch_id:
            return
        mapping = {tf: cmb.currentText() for tf, cmb in self._mapping_combos.items() if cmb.currentText() != "(Unmapped)"}
        DataMigrationService.save_mapping(
            self.db,
            self._active_batch_id,
            mapping=mapping,
            conflict_policy=self.cmb_mig_policy.currentText(),
            sheet_or_table=self.cmb_mig_sheet.currentText() or None,
        )
        summary = DataMigrationService.validate_batch(self.db, self._active_batch_id)
        self.lbl_val_summary.setText(
            f"<b>Total Source Rows:</b> {summary['total_rows']}<br/>"
            f"<b>Ready to Insert (New):</b> {summary['will_insert']}<br/>"
            f"<b>Safe Skip (Existing Preserved):</b> {summary['will_skip']}<br/>"
            f"<b>Safe Merge (Empty Fields Only):</b> {summary['will_merge_empty']}<br/>"
            f"<b>Validation Errors / Rejections:</b> {summary['error_rows']}<br/>"
            f"<b>Conflict Policy:</b> {summary['conflict_policy']}"
        )
        self._set_wizard_step(3)

    def _wiz_do_preview(self):
        if not self._active_batch_id:
            return
        prev = DataMigrationService.preview_batch(self.db, self._active_batch_id)
        rows = prev.get("preview_rows", [])
        self.tbl_mig_preview.setRowCount(len(rows))
        for r, item in enumerate(rows):
            self.tbl_mig_preview.setItem(r, 0, QTableWidgetItem(str(item["row_number"])))
            act_item = QTableWidgetItem(item["planned_action"])
            col_hex = "#059669" if item["planned_action"] == "INSERT" else ("#D97706" if item["planned_action"] in ("SKIP", "MERGE_EMPTY") else "#DC2626")
            act_item.setForeground(QColor(col_hex))
            self.tbl_mig_preview.setItem(r, 1, act_item)
            self.tbl_mig_preview.setItem(r, 2, QTableWidgetItem(item.get("reason", "")))
            self.tbl_mig_preview.setItem(r, 3, QTableWidgetItem(json.dumps(item.get("mapped", {}), default=str)[:120]))
        self._set_wizard_step(4)

    def _wiz_execute_import(self):
        if not self._active_batch_id:
            return
        try:
            batch = DataMigrationService.execute_import(
                self.db,
                self._active_batch_id,
                create_pre_backup=self.chk_mig_pre_backup.isChecked(),
            )
            self.refresh_all()
            QMessageBox.information(
                self,
                "Import Completed Safely",
                f"Batch {batch.batch_code} complete!\n"
                f"Inserted: {batch.inserted_rows} | Skipped: {batch.skipped_rows} | "
                f"Merged: {batch.merged_rows} | Errors: {batch.error_rows}\n"
                f"Pre-Migration Safety Backup: {batch.pre_migration_backup_code or 'None'}",
            )
            self._set_wizard_step(0)
            self.tabs.setCurrentIndex(3)
        except Exception as exc:
            QMessageBox.critical(self, "Import Aborted Safely", str(exc))

    def _load_migration_batches(self):
        batches = DataMigrationService.list_batches(self.db)
        self.tbl_mig_batches.setRowCount(len(batches))
        for r, b in enumerate(batches):
            self.tbl_mig_batches.setItem(r, 0, QTableWidgetItem(str(b.id)))
            self.tbl_mig_batches.setItem(r, 1, QTableWidgetItem(b.batch_code))
            self.tbl_mig_batches.setItem(r, 2, QTableWidgetItem(b.source_type))
            self.tbl_mig_batches.setItem(r, 3, QTableWidgetItem(b.source_filename))
            self.tbl_mig_batches.setItem(r, 4, QTableWidgetItem(b.target_entity))
            self.tbl_mig_batches.setItem(r, 5, QTableWidgetItem(b.conflict_policy))
            self.tbl_mig_batches.setItem(r, 6, QTableWidgetItem(f"{b.inserted_rows} ins / {b.skipped_rows} skip"))
            self.tbl_mig_batches.setItem(r, 7, QTableWidgetItem(b.pre_migration_backup_code or "-"))
            self.tbl_mig_batches.setItem(r, 8, QTableWidgetItem(b.status))

    def _load_selected_batch_logs(self):
        row = self.tbl_mig_batches.currentRow()
        if row < 0:
            return
        bid = int(self.tbl_mig_batches.item(row, 0).text())
        logs = DataMigrationService.list_batch_logs(self.db, bid)
        self.tbl_mig_logs.setRowCount(len(logs))
        for r, lg in enumerate(logs):
            self.tbl_mig_logs.setItem(r, 0, QTableWidgetItem(str(lg.row_number)))
            self.tbl_mig_logs.setItem(r, 1, QTableWidgetItem(lg.action))
            self.tbl_mig_logs.setItem(r, 2, QTableWidgetItem(lg.target_table or "-"))
            self.tbl_mig_logs.setItem(r, 3, QTableWidgetItem(str(lg.target_record_id or "-")))
            self.tbl_mig_logs.setItem(r, 4, QTableWidgetItem("Yes" if lg.is_rolled_back else "No"))
            self.tbl_mig_logs.setItem(r, 5, QTableWidgetItem(lg.message or ""))

    def _rollback_selected_batch(self):
        row = self.tbl_mig_batches.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Select Batch", "Select a migration batch first.")
            return
        bid = int(self.tbl_mig_batches.item(row, 0).text())
        reason, ok = QInputDialog.getText(self, "Rollback Migration", "Reason for rolling back this import:", text="Administrative Rollback")
        if not ok:
            return
        try:
            res = DataMigrationService.rollback_batch(self.db, bid, reason=reason)
            self.refresh_all()
            self._load_selected_batch_logs()
            QMessageBox.information(
                self,
                "Rollback Complete",
                f"Batch {res['batch_code']} rolled back cleanly!\n"
                f"Removed inserted rows: {res['deleted_inserted_records']}\n"
                f"Restored merged rows: {res['restored_merged_records']}",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Rollback Error", str(exc))
