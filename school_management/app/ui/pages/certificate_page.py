"""
EduManage Pro - Professional Document Generation & Template Management Center
Supports all 10 institutional document types with school-agnostic templates,
custom logos/signatures, dynamic custom fields, sequential serial numbers,
QR verification, ReportLab PDF export, and live interactive Qt Print Preview.
"""

from datetime import datetime
import json
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
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
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.admission import AdmissionFeePayment
from app.models.document import (
    BORDER_STYLES,
    FONT_FAMILIES,
    OFFICIAL_DOCUMENT_TYPES,
    ORIENTATIONS,
    PAGE_SIZES,
)
from app.models.exam import ExamTerm
from app.models.fee import FeePayment
from app.models.school import SchoolSetting
from app.models.staff import Staff, Teacher
from app.models.student import Student
from app.reports.universal_document_pdf import UniversalDocumentPDFGenerator
from app.services.document_service import DocumentService
from app.ui.widgets.document_preview_widget import DocumentPreviewWidget


class CertificatePage(QWidget):
    """
    Unified Document & Certificate Studio mounted at MainWindow index 15 (`certificates`).
    """

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self._custom_field_inputs: Dict[str, QLineEdit] = {}
        self._current_preview_payload: Optional[Dict[str, Any]] = None
        self._editing_template_id: Optional[int] = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Top Header
        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("Document Generation & Template Studio")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        subtitle = QLabel(
            "All 10 Official Document Types • Customizable Multi-School Templates • Logos & Signatures • Custom Fields • QR Verification & Print Preview"
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header_row.addLayout(title_col)
        header_row.addStretch()

        btn_assets = QPushButton("🏫 Configure School Logo & Signatures")
        btn_assets.setStyleSheet("background-color: #0F172A; color: white; padding: 7px 12px; font-weight: bold; border-radius: 6px;")
        btn_assets.clicked.connect(self._configure_school_assets)
        header_row.addWidget(btn_assets)

        btn_refresh = QPushButton("🔄 Refresh Data")
        btn_refresh.setStyleSheet("background-color: #2563EB; color: white; padding: 7px 12px; font-weight: bold; border-radius: 6px;")
        btn_refresh.clicked.connect(self.refresh_all)
        header_row.addWidget(btn_refresh)
        main_layout.addLayout(header_row)

        # KPI Strip
        self.kpi_layout = QHBoxLayout()
        self._build_kpi_cards()
        main_layout.addLayout(self.kpi_layout)

        # 4 Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 8px; }
            QTabBar::tab { padding: 8px 16px; font-weight: 600; font-size: 12px; }
            QTabBar::tab:selected { background: #1E3A8A; color: white; border-top-left-radius: 6px; border-top-right-radius: 6px; }
        """)

        self.tab_generate = QWidget()
        self._init_generate_tab()
        self.tabs.addTab(self.tab_generate, "🖨️ Generate & Print Preview")

        self.tab_templates = QWidget()
        self._init_templates_tab()
        self.tabs.addTab(self.tab_templates, "🎨 Template Management")

        self.tab_registry = QWidget()
        self._init_registry_tab()
        self.tabs.addTab(self.tab_registry, "📜 Issued Documents Registry")

        self.tab_verify = QWidget()
        self._init_verify_tab()
        self.tabs.addTab(self.tab_verify, "🔍 QR & Serial Verification")

        main_layout.addWidget(self.tabs)
        self.refresh_all()

    def _build_kpi_cards(self):
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cards = [
            ("Issued Documents", "0", "#1E3A8A", "📜"),
            ("Active Templates", "0", "#7C3AED", "🎨"),
            ("Receipts Issued", "0", "#059669", "🧾"),
            ("Transcripts & IDs", "0", "#0284C7", "🪪"),
            ("Revoked", "0", "#DC2626", "⛔"),
        ]
        self.kpi_labels = {}
        for title, val, color, icon in cards:
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-left: 4px solid {color};
                    border-radius: 8px;
                    padding: 6px;
                }}
            """)
            fl = QVBoxLayout(frame)
            top = QHBoxLayout()
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
            top.addWidget(t_lbl)
            top.addStretch()
            top.addWidget(QLabel(icon))
            fl.addLayout(top)
            v_lbl = QLabel(val)
            v_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
            v_lbl.setStyleSheet("color: #0F172A;")
            fl.addWidget(v_lbl)
            self.kpi_labels[title] = v_lbl
            self.kpi_layout.addWidget(frame)

    # ------------------------------------------------------------------ #
    # TAB 1: Generate Document & Live Print Preview
    # ------------------------------------------------------------------ #
    def _init_generate_tab(self):
        layout = QHBoxLayout(self.tab_generate)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Horizontal)

        # Left Form Panel
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(360)
        left_widget = QWidget()
        left_lay = QVBoxLayout(left_widget)
        left_lay.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        self.cmb_gen_doc_type = QComboBox()
        self.cmb_gen_doc_type.addItems(OFFICIAL_DOCUMENT_TYPES)
        self.cmb_gen_doc_type.currentTextChanged.connect(self._on_gen_doc_type_changed)
        form.addRow("<b>Document Type:</b>", self.cmb_gen_doc_type)

        self.cmb_gen_template = QComboBox()
        self.cmb_gen_template.currentIndexChanged.connect(self._rebuild_custom_fields_inputs)
        form.addRow("<b>Template:</b>", self.cmb_gen_template)

        self.cmb_gen_recipient_type = QComboBox()
        self.cmb_gen_recipient_type.addItems(["Student", "Teacher", "Staff"])
        self.cmb_gen_recipient_type.currentTextChanged.connect(self._load_gen_sources)
        self.lbl_gen_rec_type = QLabel("<b>Holder Type:</b>")
        form.addRow(self.lbl_gen_rec_type, self.cmb_gen_recipient_type)

        self.cmb_gen_source = QComboBox()
        self.cmb_gen_source.currentIndexChanged.connect(self._update_live_preview)
        self.lbl_gen_source = QLabel("<b>Record Source:</b>")
        form.addRow(self.lbl_gen_source, self.cmb_gen_source)

        self.cmb_gen_exam_term = QComboBox()
        self.cmb_gen_exam_term.currentIndexChanged.connect(self._update_live_preview)
        self.lbl_gen_exam_term = QLabel("<b>Exam Term:</b>")
        form.addRow(self.lbl_gen_exam_term, self.cmb_gen_exam_term)

        left_lay.addLayout(form)

        # Custom Fields Box
        self.custom_fields_group = QFrame()
        self.custom_fields_group.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px;")
        cf_outer = QVBoxLayout(self.custom_fields_group)
        cf_outer.addWidget(QLabel("<b>Dynamic Template Custom Fields</b>"))
        self.cf_form_layout = QFormLayout()
        cf_outer.addLayout(self.cf_form_layout)
        left_lay.addWidget(self.custom_fields_group)

        # Action Buttons
        btn_preview = QPushButton("👁️ Update Live Preview")
        btn_preview.setStyleSheet("background-color: #0284C7; color: white; padding: 8px; font-weight: bold; border-radius: 6px;")
        btn_preview.clicked.connect(self._update_live_preview)
        left_lay.addWidget(btn_preview)

        btn_issue = QPushButton("✅ Issue Document (Assign Serial + QR) & Export PDF")
        btn_issue.setStyleSheet("background-color: #059669; color: white; padding: 9px; font-weight: bold; border-radius: 6px;")
        btn_issue.clicked.connect(self._issue_and_export_current)
        left_lay.addWidget(btn_issue)

        self.btn_batch_id = QPushButton("🪪 Export Batch A4 ID Sheet (All Students)")
        self.btn_batch_id.setStyleSheet("background-color: #1E3A8A; color: white; padding: 8px; font-weight: bold; border-radius: 6px;")
        self.btn_batch_id.clicked.connect(self._export_batch_id_sheet)
        left_lay.addWidget(self.btn_batch_id)

        left_lay.addStretch()
        left_scroll.setWidget(left_widget)

        # Right Print Preview Panel
        self.preview_widget = DocumentPreviewWidget()

        splitter.addWidget(left_scroll)
        splitter.addWidget(self.preview_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

    # ------------------------------------------------------------------ #
    # TAB 2: Template Management
    # ------------------------------------------------------------------ #
    def _init_templates_tab(self):
        layout = QHBoxLayout(self.tab_templates)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Horizontal)

        # Left Templates List
        left_box = QWidget()
        llay = QVBoxLayout(left_box)
        bar = QHBoxLayout()
        self.cmb_tpl_filter = QComboBox()
        self.cmb_tpl_filter.addItems(["All"] + OFFICIAL_DOCUMENT_TYPES)
        self.cmb_tpl_filter.currentTextChanged.connect(self._load_templates_table)
        bar.addWidget(self.cmb_tpl_filter, 2)

        btn_new = QPushButton("➕ New")
        btn_new.setStyleSheet("background: #059669; color: white; padding: 5px 10px; font-weight: bold; border-radius: 4px;")
        btn_new.clicked.connect(self._create_new_template_dialog)
        bar.addWidget(btn_new)

        btn_clone = QPushButton("🧬 Clone")
        btn_clone.setStyleSheet("background: #2563EB; color: white; padding: 5px 10px; font-weight: bold; border-radius: 4px;")
        btn_clone.clicked.connect(self._clone_selected_template)
        bar.addWidget(btn_clone)

        btn_def = QPushButton("⭐ Default")
        btn_def.setStyleSheet("background: #D97706; color: white; padding: 5px 10px; font-weight: bold; border-radius: 4px;")
        btn_def.clicked.connect(self._set_selected_template_default)
        bar.addWidget(btn_def)

        btn_del = QPushButton("🗑️")
        btn_del.setStyleSheet("background: #DC2626; color: white; padding: 5px 8px; font-weight: bold; border-radius: 4px;")
        btn_del.clicked.connect(self._delete_selected_template)
        bar.addWidget(btn_del)
        llay.addLayout(bar)

        self.tbl_templates = QTableWidget()
        self.tbl_templates.setColumnCount(6)
        self.tbl_templates.setHorizontalHeaderLabels(["ID", "Code", "Template Name", "Document Type", "Layout", "Default"])
        self.tbl_templates.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_templates.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_templates.setAlternatingRowColors(True)
        self.tbl_templates.verticalHeader().setVisible(False)
        self.tbl_templates.itemSelectionChanged.connect(self._load_selected_template_into_editor)
        llay.addWidget(self.tbl_templates)

        # Right Visual Editor
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        editor_w = QWidget()
        elay = QVBoxLayout(editor_w)
        ef = QFormLayout()
        ef.setSpacing(7)

        self.ed_tpl_name = QLineEdit()
        self.ed_tpl_doc_type = QComboBox()
        self.ed_tpl_doc_type.addItems(OFFICIAL_DOCUMENT_TYPES)
        self.ed_tpl_page = QComboBox()
        self.ed_tpl_page.addItems(PAGE_SIZES)
        self.ed_tpl_orient = QComboBox()
        self.ed_tpl_orient.addItems(ORIENTATIONS)
        self.ed_tpl_border = QComboBox()
        self.ed_tpl_border.addItems(BORDER_STYLES)
        self.ed_tpl_font = QComboBox()
        self.ed_tpl_font.addItems(FONT_FAMILIES)

        ef.addRow("Template Name:", self.ed_tpl_name)
        ef.addRow("Document Type:", self.ed_tpl_doc_type)

        row_layout = QHBoxLayout()
        row_layout.addWidget(self.ed_tpl_page)
        row_layout.addWidget(self.ed_tpl_orient)
        row_layout.addWidget(self.ed_tpl_border)
        row_layout.addWidget(self.ed_tpl_font)
        ef.addRow("Page / Border / Font:", row_layout)

        # Colors Row
        col_row = QHBoxLayout()
        self.ed_col_primary = QLineEdit("#1E3A8A")
        self.ed_col_secondary = QLineEdit("#0F172A")
        self.ed_col_accent = QLineEdit("#D97706")
        self.ed_col_bg = QLineEdit("#FFFFFF")
        for lbl_txt, line_ed in [("Primary", self.ed_col_primary), ("Secondary", self.ed_col_secondary), ("Accent", self.ed_col_accent), ("Bg", self.ed_col_bg)]:
            b_pick = QPushButton(lbl_txt)
            b_pick.clicked.connect(lambda _c=False, target=line_ed: self._pick_color_for(target))
            col_row.addWidget(b_pick)
            col_row.addWidget(line_ed)
        ef.addRow("Color Theme:", col_row)

        # Branding Overrides & Assets
        self.chk_use_school = QCheckBox("Bind Live School Profile (Name/EIIN/Address/Phone)")
        self.chk_use_school.setChecked(True)
        ef.addRow("School Binding:", self.chk_use_school)

        self.ed_school_override = QLineEdit()
        self.ed_school_override.setPlaceholderText("Optional: Override School Name for this template...")
        ef.addRow("School Name Override:", self.ed_school_override)

        self.ed_tpl_logo = self._make_file_row("Logo PNG/JPG...", ef, "Template Logo:")
        self.ed_tpl_sig_left_lbl = QLineEdit("Academic Registrar")
        self.ed_tpl_sig_left_img = self._make_file_row("Left signature image...", ef, "Left Signature Asset:")
        ef.addRow("Left Signatory Title:", self.ed_tpl_sig_left_lbl)
        self.ed_tpl_sig_right_lbl = QLineEdit("Principal")
        self.ed_tpl_sig_right_img = self._make_file_row("Right signature image...", ef, "Right Signature Asset:")
        ef.addRow("Right Signatory Title:", self.ed_tpl_sig_right_lbl)
        self.ed_tpl_seal_img = self._make_file_row("Official seal/stamp image...", ef, "Official Seal Asset:")

        self.ed_tpl_watermark = QLineEdit()
        ef.addRow("Watermark Text:", self.ed_tpl_watermark)
        self.ed_tpl_header = QLineEdit()
        ef.addRow("Header Title:", self.ed_tpl_header)
        self.ed_tpl_subheader = QLineEdit()
        ef.addRow("Subheader:", self.ed_tpl_subheader)
        self.ed_tpl_body = QTextEdit()
        self.ed_tpl_body.setMaximumHeight(95)
        ef.addRow("Body ({{placeholders}}):", self.ed_tpl_body)
        self.ed_tpl_footer = QLineEdit()
        ef.addRow("Footer Text:", self.ed_tpl_footer)

        # Feature Toggles
        tog_row = QHBoxLayout()
        self.chk_show_logo = QCheckBox("Logo")
        self.chk_show_qr = QCheckBox("QR Code")
        self.chk_show_serial = QCheckBox("Serial No")
        self.chk_show_photo = QCheckBox("Photo")
        self.chk_show_border = QCheckBox("Border")
        self.chk_show_seal = QCheckBox("Seal")
        self.chk_show_sigs = QCheckBox("Signatures")
        self.chk_show_cf = QCheckBox("Custom Fields")
        for ck in [self.chk_show_logo, self.chk_show_qr, self.chk_show_serial, self.chk_show_photo,
                   self.chk_show_border, self.chk_show_seal, self.chk_show_sigs, self.chk_show_cf]:
            ck.setChecked(True)
            tog_row.addWidget(ck)
        ef.addRow("Visible Elements:", tog_row)

        # Custom Fields Schema JSON + Helper
        cf_hdr = QHBoxLayout()
        btn_add_cf = QPushButton("➕ Add Custom Field")
        btn_add_cf.clicked.connect(self._append_custom_field_to_schema)
        cf_hdr.addWidget(btn_add_cf)
        cf_hdr.addWidget(QLabel("<small>Placeholders: {{recipient_name}}, {{recipient_code}}, {{school_name}}, {{class_or_designation}}, {{serial_number}}, {{issue_date}}</small>"))
        elay.addLayout(ef)
        elay.addLayout(cf_hdr)

        self.ed_tpl_cf_schema = QTextEdit()
        self.ed_tpl_cf_schema.setMaximumHeight(85)
        elay.addWidget(self.ed_tpl_cf_schema)

        btn_save_tpl = QPushButton("💾 Save Template Configuration")
        btn_save_tpl.setStyleSheet("background: #1E3A8A; color: white; padding: 9px; font-weight: bold; border-radius: 6px;")
        btn_save_tpl.clicked.connect(self._save_edited_template)
        elay.addWidget(btn_save_tpl)

        right_scroll.setWidget(editor_w)
        splitter.addWidget(left_box)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

    def _make_file_row(self, placeholder: str, form_layout: QFormLayout, label: str) -> QLineEdit:
        row = QHBoxLayout()
        ed = QLineEdit()
        ed.setPlaceholderText(placeholder)
        btn = QPushButton("Browse...")
        btn.clicked.connect(lambda _c=False, target=ed: self._browse_image_into(target))
        row.addWidget(ed)
        row.addWidget(btn)
        form_layout.addRow(label, row)
        return ed

    # ------------------------------------------------------------------ #
    # TAB 3: Issued Documents Registry
    # ------------------------------------------------------------------ #
    def _init_registry_tab(self):
        layout = QVBoxLayout(self.tab_registry)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        bar = QHBoxLayout()
        self.txt_reg_search = QLineEdit()
        self.txt_reg_search.setPlaceholderText("Search by serial (DOC-...), verification token (VER-...), name or ID...")
        self.txt_reg_search.textChanged.connect(self._load_registry_table)
        bar.addWidget(self.txt_reg_search, 2)

        self.cmb_reg_type = QComboBox()
        self.cmb_reg_type.addItems(["All"] + OFFICIAL_DOCUMENT_TYPES)
        self.cmb_reg_type.currentTextChanged.connect(self._load_registry_table)
        bar.addWidget(self.cmb_reg_type, 1)

        btn_prev = QPushButton("👁️ Open Print Preview")
        btn_prev.setStyleSheet("background: #0284C7; color: white; padding: 6px 12px; font-weight: bold; border-radius: 5px;")
        btn_prev.clicked.connect(self._preview_selected_issued_doc)
        bar.addWidget(btn_prev)

        btn_pdf = QPushButton("📥 Export PDF")
        btn_pdf.setStyleSheet("background: #2563EB; color: white; padding: 6px 12px; font-weight: bold; border-radius: 5px;")
        btn_pdf.clicked.connect(self._export_selected_issued_pdf)
        bar.addWidget(btn_pdf)

        btn_rev = QPushButton("⛔ Revoke")
        btn_rev.setStyleSheet("background: #DC2626; color: white; padding: 6px 12px; font-weight: bold; border-radius: 5px;")
        btn_rev.clicked.connect(self._revoke_selected_issued_doc)
        bar.addWidget(btn_rev)
        layout.addLayout(bar)

        self.tbl_registry = QTableWidget()
        self.tbl_registry.setColumnCount(9)
        self.tbl_registry.setHorizontalHeaderLabels([
            "ID", "Serial Number", "Document Type", "Recipient", "Code", "Template", "Issue Date", "Verify Token", "Status"
        ])
        self.tbl_registry.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_registry.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_registry.setAlternatingRowColors(True)
        self.tbl_registry.verticalHeader().setVisible(False)
        layout.addWidget(self.tbl_registry)

    # ------------------------------------------------------------------ #
    # TAB 4: QR & Serial Verification
    # ------------------------------------------------------------------ #
    def _init_verify_tab(self):
        layout = QVBoxLayout(self.tab_verify)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        lbl = QLabel("Scan QR Payload, or enter Document Serial Number (e.g. DOC-TC-2026-00001) or Verification Code (VER-XXXX):")
        lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        layout.addWidget(lbl)

        row = QHBoxLayout()
        self.txt_verify_input = QLineEdit()
        self.txt_verify_input.setPlaceholderText("DOC-... or VER-... or EDUMANAGE-DOC|SER:...")
        self.txt_verify_input.setStyleSheet("padding: 8px; font-size: 13px;")
        row.addWidget(self.txt_verify_input)

        btn_check = QPushButton("🔍 Verify Document Authenticity")
        btn_check.setStyleSheet("background: #1E3A8A; color: white; padding: 8px 18px; font-weight: bold; border-radius: 6px;")
        btn_check.clicked.connect(self._run_verification)
        row.addWidget(btn_check)
        layout.addLayout(row)

        self.lbl_verify_result = QLabel("Awaiting serial or QR verification lookup...")
        self.lbl_verify_result.setWordWrap(True)
        self.lbl_verify_result.setStyleSheet("background: #F8FAFC; border: 1px solid #CBD5E1; padding: 18px; border-radius: 8px; font-size: 13px;")
        layout.addWidget(self.lbl_verify_result)
        layout.addStretch()

    # ------------------------------------------------------------------ #
    # Data Refresh & Event Handlers
    # ------------------------------------------------------------------ #
    def refresh_all(self):
        if not self.db:
            return
        DocumentService.seed_default_templates(self.db)
        stats = DocumentService.get_stats(self.db)
        self.kpi_labels["Issued Documents"].setText(str(stats["issued"]))
        self.kpi_labels["Active Templates"].setText(str(stats["templates"]))
        self.kpi_labels["Receipts Issued"].setText(str(stats["receipts"]))
        self.kpi_labels["Transcripts & IDs"].setText(str(stats["academic_records"] + stats["id_cards"]))
        self.kpi_labels["Revoked"].setText(str(stats["revoked"]))

        self._on_gen_doc_type_changed(self.cmb_gen_doc_type.currentText())
        self._load_templates_table()
        self._load_registry_table()

    def _on_gen_doc_type_changed(self, doc_type: str):
        if not self.db:
            return
        self.cmb_gen_template.blockSignals(True)
        self.cmb_gen_template.clear()
        for t in DocumentService.list_templates(self.db, document_type=doc_type):
            tag = " ★" if t.is_default else ""
            self.cmb_gen_template.addItem(f"{t.name}{tag}", t.id)
        self.cmb_gen_template.blockSignals(False)

        is_id = doc_type == "ID Card"
        is_exam = doc_type in ("Mark Sheet", "Report Card")
        self.lbl_gen_rec_type.setVisible(is_id)
        self.cmb_gen_recipient_type.setVisible(is_id)
        self.btn_batch_id.setVisible(is_id)
        self.lbl_gen_exam_term.setVisible(is_exam)
        self.cmb_gen_exam_term.setVisible(is_exam)

        self._load_gen_sources()
        self._rebuild_custom_fields_inputs()

    def _load_gen_sources(self):
        if not self.db:
            return
        doc_type = self.cmb_gen_doc_type.currentText()
        self.cmb_gen_source.blockSignals(True)
        self.cmb_gen_source.clear()

        if doc_type == "Fee Receipt":
            for fp in self.db.query(FeePayment).order_by(FeePayment.id.desc()).limit(100).all():
                stu = fp.student.full_name if fp.student else f"Student #{fp.student_id}"
                self.cmb_gen_source.addItem(f"{fp.receipt_no} — {stu} ({fp.amount_paid})", fp.id)
        elif doc_type == "Admission Receipt":
            for ap in self.db.query(AdmissionFeePayment).order_by(AdmissionFeePayment.id.desc()).limit(100).all():
                app_name = ap.application.full_name if ap.application else f"App #{ap.application_id}"
                self.cmb_gen_source.addItem(f"{ap.receipt_no} — {app_name} ({ap.amount_paid})", ap.id)
        elif doc_type == "ID Card" and self.cmb_gen_recipient_type.currentText() == "Teacher":
            for t in self.db.query(Teacher).order_by(Teacher.full_name).all():
                self.cmb_gen_source.addItem(f"{t.teacher_id} — {t.full_name} ({t.designation})", t.id)
        elif doc_type == "ID Card" and self.cmb_gen_recipient_type.currentText() == "Staff":
            for s in self.db.query(Staff).order_by(Staff.full_name).all():
                self.cmb_gen_source.addItem(f"{s.staff_id} — {s.full_name} ({s.position})", s.id)
        else:
            for st in self.db.query(Student).order_by(Student.full_name).all():
                cls_str = st.school_class.name if st.school_class else "-"
                self.cmb_gen_source.addItem(f"{st.student_id} — {st.full_name} ({cls_str})", st.id)
        self.cmb_gen_source.blockSignals(False)

        self.cmb_gen_exam_term.blockSignals(True)
        self.cmb_gen_exam_term.clear()
        for et in self.db.query(ExamTerm).order_by(ExamTerm.id.desc()).all():
            self.cmb_gen_exam_term.addItem(f"{et.name} ({et.exam_code})", et.id)
        self.cmb_gen_exam_term.blockSignals(False)

    def _rebuild_custom_fields_inputs(self):
        while self.cf_form_layout.rowCount():
            self.cf_form_layout.removeRow(0)
        self._custom_field_inputs.clear()
        if not self.db:
            return
        tpl_id = self.cmb_gen_template.currentData()
        tpl = DocumentService.get_template(self.db, template_id=tpl_id) if tpl_id else None
        schema = []
        if tpl:
            try:
                schema = json.loads(tpl.custom_fields_schema_json or "[]")
            except Exception:
                schema = []
        if not schema:
            self.cf_form_layout.addRow(QLabel("<i>No custom fields defined on this template.</i>"))
        else:
            for f in schema:
                k = str(f.get("key", ""))
                lbl = str(f.get("label") or k)
                ed = QLineEdit(str(f.get("default_value", "")))
                ed.editingFinished.connect(self._update_live_preview)
                self._custom_field_inputs[k] = ed
                self.cf_form_layout.addRow(f"{lbl}:", ed)
        self._update_live_preview()

    def _collect_gen_kwargs(self) -> Optional[Dict[str, Any]]:
        src_id = self.cmb_gen_source.currentData()
        if not src_id:
            return None
        doc_type = self.cmb_gen_doc_type.currentText()
        tpl_id = self.cmb_gen_template.currentData()
        cf_vals = {k: ed.text() for k, ed in self._custom_field_inputs.items()}
        kwargs: Dict[str, Any] = {
            "document_type": doc_type,
            "template_id": tpl_id,
            "custom_fields_values": cf_vals,
        }
        if doc_type == "Fee Receipt":
            kwargs["fee_payment_id"] = src_id
        elif doc_type == "Admission Receipt":
            kwargs["admission_payment_id"] = src_id
        elif doc_type == "ID Card" and self.cmb_gen_recipient_type.currentText() == "Teacher":
            kwargs["recipient_type"] = "Teacher"
            kwargs["teacher_id"] = src_id
        elif doc_type == "ID Card" and self.cmb_gen_recipient_type.currentText() == "Staff":
            kwargs["recipient_type"] = "Staff"
            kwargs["staff_id"] = src_id
        else:
            kwargs["student_id"] = src_id
            if doc_type in ("Mark Sheet", "Report Card"):
                kwargs["exam_term_id"] = self.cmb_gen_exam_term.currentData()
        return kwargs

    def _update_live_preview(self):
        if not self.db:
            return
        kw = self._collect_gen_kwargs()
        if not kw:
            self._current_preview_payload = None
            self.preview_widget.set_payload(None)
            return
        try:
            payload = DocumentService.preview_document_data(self.db, **kw)
            self._current_preview_payload = payload
            self.preview_widget.set_payload(payload)
        except Exception as exc:
            self._current_preview_payload = None
            self.preview_widget.set_payload(None)
            QMessageBox.warning(self, "Preview Error", str(exc))

    def _issue_and_export_current(self):
        if not self.db:
            return
        kw = self._collect_gen_kwargs()
        if not kw:
            QMessageBox.warning(self, "Selection Required", "Please select a record source first.")
            return
        default_name = f"{kw['document_type'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Official Document PDF", default_name, "PDF Files (*.pdf)")
        if not file_path:
            return
        doc = DocumentService.issue_document(self.db, output_pdf_path=file_path, **kw)
        self.refresh_all()
        payload = DocumentService.document_to_render_payload(self.db, doc)
        self.preview_widget.set_payload(payload)
        QMessageBox.information(
            self,
            "Document Issued & Saved",
            f"Serial: {doc.serial_number}\nVerification Code: {doc.verification_code}\nSaved to:\n{file_path}",
        )

    def _export_batch_id_sheet(self):
        if not self.db:
            return
        tpl_id = self.cmb_gen_template.currentData()
        students = self.db.query(Student).order_by(Student.roll_number).limit(24).all()
        if not students:
            QMessageBox.warning(self, "No Students", "No student records available for batch ID generation.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Batch A4 ID Sheet", f"Batch_IDs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        cf_vals = {k: ed.text() for k, ed in self._custom_field_inputs.items()}
        payloads = []
        for st in students:
            doc = DocumentService.issue_document(
                self.db,
                document_type="ID Card",
                template_id=tpl_id,
                student_id=st.id,
                custom_fields_values=cf_vals,
            )
            payloads.append(DocumentService.document_to_render_payload(self.db, doc))
        UniversalDocumentPDFGenerator.generate_batch_id_sheet(payloads, file_path)
        self.refresh_all()
        QMessageBox.information(self, "Batch Sheet Exported", f"Issued & exported {len(payloads)} CR80 ID cards to:\n{file_path}")

    # ------------------------------------------------------------------ #
    # Template Manager Handlers
    # ------------------------------------------------------------------ #
    def _load_templates_table(self):
        if not self.db:
            return
        ftype = self.cmb_tpl_filter.currentText()
        tpls = DocumentService.list_templates(self.db, document_type=ftype)
        self.tbl_templates.setRowCount(len(tpls))
        for r, t in enumerate(tpls):
            self.tbl_templates.setItem(r, 0, QTableWidgetItem(str(t.id)))
            self.tbl_templates.setItem(r, 1, QTableWidgetItem(t.template_code))
            self.tbl_templates.setItem(r, 2, QTableWidgetItem(t.name))
            self.tbl_templates.setItem(r, 3, QTableWidgetItem(t.document_type))
            self.tbl_templates.setItem(r, 4, QTableWidgetItem(f"{t.page_size} {t.orientation}"))
            self.tbl_templates.setItem(r, 5, QTableWidgetItem("★ Default" if t.is_default else ""))

    def _load_selected_template_into_editor(self):
        if not self.db:
            return
        row = self.tbl_templates.currentRow()
        if row < 0:
            return
        tpl_id = int(self.tbl_templates.item(row, 0).text())
        tpl = DocumentService.get_template(self.db, template_id=tpl_id)
        if not tpl:
            return
        self._editing_template_id = tpl.id
        self.ed_tpl_name.setText(tpl.name)
        self.ed_tpl_doc_type.setCurrentText(tpl.document_type)
        self.ed_tpl_page.setCurrentText(tpl.page_size)
        self.ed_tpl_orient.setCurrentText(tpl.orientation)
        self.ed_tpl_border.setCurrentText(tpl.border_style)
        self.ed_tpl_font.setCurrentText(tpl.font_family)
        self.ed_col_primary.setText(tpl.primary_color)
        self.ed_col_secondary.setText(tpl.secondary_color)
        self.ed_col_accent.setText(tpl.accent_color)
        self.ed_col_bg.setText(tpl.background_color)
        self.chk_use_school.setChecked(bool(tpl.use_school_profile))
        self.ed_school_override.setText(tpl.school_name_override or "")
        self.ed_tpl_logo.setText(tpl.logo_path or "")
        self.ed_tpl_sig_left_lbl.setText(tpl.signature_left_label or "")
        self.ed_tpl_sig_left_img.setText(tpl.signature_left_image_path or "")
        self.ed_tpl_sig_right_lbl.setText(tpl.signature_right_label or "")
        self.ed_tpl_sig_right_img.setText(tpl.signature_right_image_path or "")
        self.ed_tpl_seal_img.setText(tpl.seal_image_path or "")
        self.ed_tpl_watermark.setText(tpl.watermark_text or "")
        self.ed_tpl_header.setText(tpl.header_text or "")
        self.ed_tpl_subheader.setText(tpl.subheader_text or "")
        self.ed_tpl_body.setPlainText(tpl.body_template or "")
        self.ed_tpl_footer.setText(tpl.footer_text or "")
        self.chk_show_logo.setChecked(bool(tpl.show_logo))
        self.chk_show_qr.setChecked(bool(tpl.show_qr))
        self.chk_show_serial.setChecked(bool(tpl.show_serial))
        self.chk_show_photo.setChecked(bool(tpl.show_photo))
        self.chk_show_border.setChecked(bool(tpl.show_border))
        self.chk_show_seal.setChecked(bool(tpl.show_seal))
        self.chk_show_sigs.setChecked(bool(tpl.show_signatures))
        self.chk_show_cf.setChecked(bool(tpl.show_custom_fields))
        self.ed_tpl_cf_schema.setPlainText(tpl.custom_fields_schema_json or "[]")

    def _save_edited_template(self):
        if not self.db or not self._editing_template_id:
            QMessageBox.warning(self, "Select Template", "Select a template from the list to edit.")
            return
        try:
            schema_list = json.loads(self.ed_tpl_cf_schema.toPlainText() or "[]")
            if not isinstance(schema_list, list):
                raise ValueError("Custom fields schema must be a JSON array.")
        except Exception as exc:
            QMessageBox.warning(self, "Invalid Custom Fields JSON", str(exc))
            return

        DocumentService.update_template(
            self.db,
            self._editing_template_id,
            name=self.ed_tpl_name.text().strip() or "Custom Template",
            document_type=self.ed_tpl_doc_type.currentText(),
            page_size=self.ed_tpl_page.currentText(),
            orientation=self.ed_tpl_orient.currentText(),
            border_style=self.ed_tpl_border.currentText(),
            font_family=self.ed_tpl_font.currentText(),
            primary_color=self.ed_col_primary.text().strip(),
            secondary_color=self.ed_col_secondary.text().strip(),
            accent_color=self.ed_col_accent.text().strip(),
            background_color=self.ed_col_bg.text().strip(),
            use_school_profile=self.chk_use_school.isChecked(),
            school_name_override=self.ed_school_override.text().strip() or None,
            logo_path=self.ed_tpl_logo.text().strip() or None,
            signature_left_label=self.ed_tpl_sig_left_lbl.text().strip() or None,
            signature_left_image_path=self.ed_tpl_sig_left_img.text().strip() or None,
            signature_right_label=self.ed_tpl_sig_right_lbl.text().strip() or None,
            signature_right_image_path=self.ed_tpl_sig_right_img.text().strip() or None,
            seal_image_path=self.ed_tpl_seal_img.text().strip() or None,
            watermark_text=self.ed_tpl_watermark.text().strip() or None,
            header_text=self.ed_tpl_header.text().strip() or "OFFICIAL DOCUMENT",
            subheader_text=self.ed_tpl_subheader.text().strip() or None,
            body_template=self.ed_tpl_body.toPlainText(),
            footer_text=self.ed_tpl_footer.text().strip() or None,
            show_logo=self.chk_show_logo.isChecked(),
            show_qr=self.chk_show_qr.isChecked(),
            show_serial=self.chk_show_serial.isChecked(),
            show_photo=self.chk_show_photo.isChecked(),
            show_border=self.chk_show_border.isChecked(),
            show_seal=self.chk_show_seal.isChecked(),
            show_signatures=self.chk_show_sigs.isChecked(),
            show_custom_fields=self.chk_show_cf.isChecked(),
            custom_fields_schema=schema_list,
        )
        self.refresh_all()
        QMessageBox.information(self, "Template Saved", "Template design, branding, and custom fields saved.")

    def _create_new_template_dialog(self):
        if not self.db:
            return
        doc_type, ok = QInputDialog.getItem(self, "New Template", "Select Document Type:", OFFICIAL_DOCUMENT_TYPES, 0, False)
        if not ok or not doc_type:
            return
        name, ok2 = QInputDialog.getText(self, "Template Name", "Enter new template name:", text=f"Custom {doc_type} Design")
        if not ok2 or not name.strip():
            return
        tpl = DocumentService.create_template(
            self.db,
            name=name.strip(),
            document_type=doc_type,
            header_text=doc_type.upper(),
            body_template="This certifies {{recipient_name}} ({{recipient_code}}) at {{school_name}}.",
        )
        self.refresh_all()
        QMessageBox.information(self, "Template Created", f"Created template '{tpl.name}' ({tpl.template_code}).")

    def _clone_selected_template(self):
        row = self.tbl_templates.currentRow()
        if row < 0 or not self.db:
            return
        tpl_id = int(self.tbl_templates.item(row, 0).text())
        cloned = DocumentService.clone_template(self.db, tpl_id)
        self.refresh_all()
        QMessageBox.information(self, "Template Cloned", f"Cloned as '{cloned.name}'. Customize it on the right panel.")

    def _set_selected_template_default(self):
        row = self.tbl_templates.currentRow()
        if row < 0 or not self.db:
            return
        tpl_id = int(self.tbl_templates.item(row, 0).text())
        tpl = DocumentService.set_default_template(self.db, tpl_id)
        self.refresh_all()
        QMessageBox.information(self, "Default Updated", f"'{tpl.name}' is now default for {tpl.document_type}.")

    def _delete_selected_template(self):
        row = self.tbl_templates.currentRow()
        if row < 0 or not self.db:
            return
        tpl_id = int(self.tbl_templates.item(row, 0).text())
        if QMessageBox.question(self, "Delete Template", "Soft-delete selected template?") == QMessageBox.Yes:
            DocumentService.delete_template(self.db, tpl_id)
            self.refresh_all()

    def _append_custom_field_to_schema(self):
        key, ok = QInputDialog.getText(self, "Add Custom Field", "Field key (e.g. scholarship_tier):")
        if not ok or not key.strip():
            return
        label, ok2 = QInputDialog.getText(self, "Custom Field Label", "Display Label:", text=key.strip().replace("_", " ").title())
        if not ok2:
            return
        default_val, _ = QInputDialog.getText(self, "Default Value", "Default Value:")
        try:
            cur = json.loads(self.ed_tpl_cf_schema.toPlainText() or "[]")
        except Exception:
            cur = []
        cur.append({"key": key.strip().replace(" ", "_").lower(), "label": label.strip(), "type": "text", "default_value": default_val})
        self.ed_tpl_cf_schema.setPlainText(json.dumps(cur, indent=2))

    def _pick_color_for(self, target: QLineEdit):
        c = QColorDialog.getColor(QColor(target.text() or "#1E3A8A"), self)
        if c.isValid():
            target.setText(c.name().upper())

    def _browse_image_into(self, target: QLineEdit):
        p, _ = QFileDialog.getOpenFileName(self, "Select Image Asset", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if p:
            target.setText(p)

    def _configure_school_assets(self):
        if not self.db:
            return
        school = self.db.query(SchoolSetting).first()
        if not school:
            school = SchoolSetting()
            self.db.add(school)
            self.db.commit()
        choice, ok = QInputDialog.getItem(
            self,
            "School Asset Setup",
            "Choose institutional image asset to update:",
            ["School Logo", "Principal Signature Image", "Registrar Signature Image", "Official Seal Image"],
            0,
            False,
        )
        if not ok or not choice:
            return
        path, _ = QFileDialog.getOpenFileName(self, f"Select {choice}", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        if choice == "School Logo":
            school.logo_path = path
        elif choice == "Principal Signature Image":
            school.principal_signature_path = path
        elif choice == "Registrar Signature Image":
            school.registrar_signature_path = path
        else:
            school.official_seal_path = path
        self.db.commit()
        self._update_live_preview()
        QMessageBox.information(self, "Asset Updated", f"Updated {choice} in School Settings.")

    # ------------------------------------------------------------------ #
    # Registry & Verification Handlers
    # ------------------------------------------------------------------ #
    def _load_registry_table(self):
        if not self.db:
            return
        docs = DocumentService.list_issued_documents(
            self.db,
            document_type=self.cmb_reg_type.currentText(),
            search=self.txt_reg_search.text(),
        )
        self.tbl_registry.setRowCount(len(docs))
        for r, d in enumerate(docs):
            tpl_name = d.template.name if d.template else "-"
            self.tbl_registry.setItem(r, 0, QTableWidgetItem(str(d.id)))
            self.tbl_registry.setItem(r, 1, QTableWidgetItem(d.serial_number))
            self.tbl_registry.setItem(r, 2, QTableWidgetItem(d.document_type))
            self.tbl_registry.setItem(r, 3, QTableWidgetItem(d.recipient_name))
            self.tbl_registry.setItem(r, 4, QTableWidgetItem(d.recipient_code))
            self.tbl_registry.setItem(r, 5, QTableWidgetItem(tpl_name))
            self.tbl_registry.setItem(r, 6, QTableWidgetItem(str(d.issue_date)))
            self.tbl_registry.setItem(r, 7, QTableWidgetItem(d.verification_code))
            st_item = QTableWidgetItem(d.status)
            st_item.setForeground(QColor("#059669" if d.status == "Issued" else "#DC2626"))
            self.tbl_registry.setItem(r, 8, st_item)

    def _get_selected_issued_id(self) -> Optional[int]:
        row = self.tbl_registry.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select an issued document row first.")
            return None
        return int(self.tbl_registry.item(row, 0).text())

    def _preview_selected_issued_doc(self):
        doc_id = self._get_selected_issued_id()
        if not doc_id or not self.db:
            return
        doc = DocumentService.verify_document(self.db, self.tbl_registry.item(self.tbl_registry.currentRow(), 1).text())
        if not doc:
            return
        payload = DocumentService.document_to_render_payload(self.db, doc)
        self.preview_widget.set_payload(payload)
        self.tabs.setCurrentIndex(0)

    def _export_selected_issued_pdf(self):
        doc_id = self._get_selected_issued_id()
        if not doc_id or not self.db:
            return
        serial = self.tbl_registry.item(self.tbl_registry.currentRow(), 1).text()
        doc = DocumentService.verify_document(self.db, serial)
        if not doc:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Document PDF", f"{doc.serial_number}.pdf", "PDF Files (*.pdf)")
        if not file_path:
            return
        payload = DocumentService.document_to_render_payload(self.db, doc)
        UniversalDocumentPDFGenerator.generate_pdf(payload, file_path)
        DocumentService.increment_print_count(self.db, doc.id)
        QMessageBox.information(self, "PDF Saved", f"Document {doc.serial_number} exported to:\n{file_path}")

    def _revoke_selected_issued_doc(self):
        doc_id = self._get_selected_issued_id()
        if not doc_id or not self.db:
            return
        reason, ok = QInputDialog.getText(self, "Revoke Document", "Reason for revocation:", text="Revoked by Administration")
        if ok:
            DocumentService.revoke_document(self.db, doc_id, reason=reason.strip() or "Revoked")
            self.refresh_all()

    def _run_verification(self):
        if not self.db:
            return
        q = self.txt_verify_input.text().strip()
        doc = DocumentService.verify_document(self.db, q)
        if not doc:
            self.lbl_verify_result.setText("❌ <b>NOT FOUND:</b> No issued document matches that Serial Number, Token, or QR Payload.")
            self.lbl_verify_result.setStyleSheet("background: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; padding: 18px; border-radius: 8px;")
            return
        valid = doc.status == "Issued"
        fg = "#065F46" if valid else "#991B1B"
        bg = "#ECFDF5" if valid else "#FEF2F2"
        school_snap = json.loads(doc.school_snapshot_json or "{}")
        cf_snap = json.loads(doc.custom_fields_values_json or "{}")
        self.lbl_verify_result.setText(
            f"<b>AUTHENTICATION RESULT: {doc.status.upper()}</b><br/>"
            f"<b>Serial Number:</b> {doc.serial_number} &nbsp;|&nbsp; <b>Token:</b> {doc.verification_code}<br/>"
            f"<b>Document Type:</b> {doc.document_type}<br/>"
            f"<b>Issuing Institution:</b> {school_snap.get('school_name', '-')}<br/>"
            f"<b>Recipient:</b> {doc.recipient_name} ({doc.recipient_code})<br/>"
            f"<b>Issue Date:</b> {doc.issue_date} &nbsp;|&nbsp; <b>Issued By:</b> {doc.issued_by}<br/>"
            f"<b>Custom Fields:</b> {cf_snap}<br/>"
            f"<b>QR Payload:</b> <code>{doc.qr_payload}</code>"
        )
        self.lbl_verify_result.setStyleSheet(f"background: {bg}; border: 1px solid {fg}; color: {fg}; padding: 18px; border-radius: 8px;")
