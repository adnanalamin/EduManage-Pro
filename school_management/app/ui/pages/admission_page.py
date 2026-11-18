"""
EduManage Pro - Admission CRM Console (PySide6)
Complete 6-Tab Admissions Management Workbench:
1. Applications & Intake (Applicant IDs, 8 Statuses, Search, Form PDF, Excel Import/Export)
2. Document Checklist & Verification
3. Admission Test & Interview Evaluation (+ Admit Card PDF)
4. Merit List, Waiting List, Admission Approval & Student Conversion (+ Merit List PDF)
5. Configurable Admission Fees & Applicant Payment Receipts (+ Receipt PDF)
6. Admission Funnel Statistics & Financials
"""

from datetime import date
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.admission import AdmissionApplication, AdmissionFeePayment, AdmissionStatus
from app.repositories.academic_repository import AcademicRepository
from app.repositories.admission_repository import AdmissionRepository
from app.services.admission_service import AdmissionService


class AdmissionPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.applications_cache: List[AdmissionApplication] = []
        self._init_ui()
        self.refresh_all()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        hdr = QHBoxLayout()
        tbox = QVBoxLayout()
        title = QLabel("Admission CRM & Enrollment Pipeline")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A;")
        sub = QLabel(
            "Applicant IDs · 8-Stage Funnel · Checklists · Entrance Tests & Interviews · "
            "Merit & Waitlist · Configurable Fees · Student Conversion"
        )
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        tbox.addWidget(title)
        tbox.addWidget(sub)
        hdr.addLayout(tbox)
        hdr.addStretch()

        btn_ref = QPushButton("Refresh All")
        btn_ref.setStyleSheet(
            "background-color: #0F172A; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;"
        )
        btn_ref.clicked.connect(self.refresh_all)
        hdr.addWidget(btn_ref)
        root.addLayout(hdr)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { font-weight: 600; padding: 8px 13px; margin-right: 3px; }
            QTabBar::tab:selected { background: #2563EB; color: white; border-radius: 4px; }
        """)
        self.tabs.addTab(self._build_applications_tab(), "1. Applications & Intake")
        self.tabs.addTab(self._build_checklist_tab(), "2. Document Checklist")
        self.tabs.addTab(self._build_evaluation_tab(), "3. Test & Interview")
        self.tabs.addTab(self._build_merit_conversion_tab(), "4. Merit List & Conversion")
        self.tabs.addTab(self._build_fees_tab(), "5. Admission Fees & Receipts")
        self.tabs.addTab(self._build_stats_tab(), "6. Admission Statistics")
        root.addWidget(self.tabs)

    def refresh_all(self):
        self._load_reference_combos()
        self._load_applications_table()
        self._load_fee_configs()
        self._load_statistics()

    # ------------------------------------------------------------------
    # TAB 1: APPLICATIONS & INTAKE
    # ------------------------------------------------------------------
    def _build_applications_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)

        # Left Form: New Application
        form_box = QFrame()
        form_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        flay = QFormLayout(form_box)
        flay.setContentsMargins(12, 12, 12, 12)
        flay.addRow(QLabel("<b>New Admission Application</b>"))

        self.app_ay_combo = QComboBox()
        flay.addRow("Academic Year:", self.app_ay_combo)

        self.app_class_combo = QComboBox()
        flay.addRow("Applying Class:", self.app_class_combo)

        self.app_fname_edit = QLineEdit()
        flay.addRow("First Name*:", self.app_fname_edit)

        self.app_lname_edit = QLineEdit()
        flay.addRow("Last Name*:", self.app_lname_edit)

        self.app_gender_combo = QComboBox()
        self.app_gender_combo.addItems(["Male", "Female", "Other"])
        flay.addRow("Gender:", self.app_gender_combo)

        self.app_dob_edit = QDateEdit()
        self.app_dob_edit.setCalendarPopup(True)
        self.app_dob_edit.setDate(QDate(2012, 1, 1))
        flay.addRow("Date of Birth:", self.app_dob_edit)

        self.app_gname_edit = QLineEdit()
        flay.addRow("Guardian Name*:", self.app_gname_edit)

        self.app_gphone_edit = QLineEdit()
        flay.addRow("Guardian Phone*:", self.app_gphone_edit)

        self.app_prev_school = QLineEdit()
        flay.addRow("Previous School:", self.app_prev_school)

        self.app_prev_gpa = QDoubleSpinBox()
        self.app_prev_gpa.setRange(0.0, 100.0)
        self.app_prev_gpa.setValue(4.5)
        flay.addRow("Previous GPA:", self.app_prev_gpa)

        self.app_source_combo = QComboBox()
        self.app_source_combo.addItems(["Walk-in", "Website", "Referral", "Campaign"])
        flay.addRow("Source:", self.app_source_combo)

        btn_submit = QPushButton("Submit Application")
        btn_submit.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 8px 12px; border-radius: 6px;")
        btn_submit.clicked.connect(self._on_submit_application)
        flay.addRow(btn_submit)

        # Right: Filter Bar + Applications Table + Actions
        right = QWidget()
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(6, 0, 0, 0)

        fbar = QHBoxLayout()
        self.app_search_edit = QLineEdit()
        self.app_search_edit.setPlaceholderText("Search Applicant ID, Name, Guardian, Phone...")
        self.app_search_edit.returnPressed.connect(self._load_applications_table)
        fbar.addWidget(self.app_search_edit)

        self.app_status_filter = QComboBox()
        self.app_status_filter.addItems(["All"] + AdmissionStatus.ALL)
        self.app_status_filter.currentIndexChanged.connect(self._load_applications_table)
        fbar.addWidget(self.app_status_filter)

        btn_find = QPushButton("Search")
        btn_find.clicked.connect(self._load_applications_table)
        fbar.addWidget(btn_find)

        btn_imp = QPushButton("Import Excel/CSV")
        btn_imp.setStyleSheet("background-color: #0D9488; color: white; font-weight: bold; padding: 5px 10px; border-radius: 5px;")
        btn_imp.clicked.connect(self._on_import_excel)
        fbar.addWidget(btn_imp)

        btn_exp = QPushButton("Export Excel")
        btn_exp.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 5px 10px; border-radius: 5px;")
        btn_exp.clicked.connect(self._on_export_excel)
        fbar.addWidget(btn_exp)
        rlay.addLayout(fbar)

        self.app_table = QTableWidget()
        self.app_table.setColumnCount(8)
        self.app_table.setHorizontalHeaderLabels([
            "ID", "Applicant ID", "Full Name", "Target Class", "Guardian", "Phone", "Status", "Merit Rank"
        ])
        self.app_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.app_table.setSelectionBehavior(QTableWidget.SelectRows)
        rlay.addWidget(self.app_table)

        act_bar = QHBoxLayout()
        act_bar.addWidget(QLabel("Set Selected Status:"))
        self.app_next_status_combo = QComboBox()
        self.app_next_status_combo.addItems(AdmissionStatus.ALL)
        act_bar.addWidget(self.app_next_status_combo)

        btn_chg_st = QPushButton("Update Status")
        btn_chg_st.setStyleSheet("background-color: #4F46E5; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_chg_st.clicked.connect(self._on_change_status)
        act_bar.addWidget(btn_chg_st)

        btn_pdf_form = QPushButton("Admission Form (PDF)")
        btn_pdf_form.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_pdf_form.clicked.connect(self._on_export_form_pdf)
        act_bar.addWidget(btn_pdf_form)
        act_bar.addStretch()
        rlay.addLayout(act_bar)

        splitter.addWidget(form_box)
        splitter.addWidget(right)
        splitter.setSizes([330, 770])
        lay.addWidget(splitter)
        return tab

    # ------------------------------------------------------------------
    # TAB 2: DOCUMENT CHECKLIST
    # ------------------------------------------------------------------
    def _build_checklist_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(0, 10, 0, 0)

        top = QHBoxLayout()
        top.addWidget(QLabel("Select Applicant:"))
        self.chk_app_combo = QComboBox()
        self.chk_app_combo.currentIndexChanged.connect(self._load_checklist_for_selected)
        top.addWidget(self.chk_app_combo)

        self.chk_summary_lbl = QLabel("Checklist status: -")
        self.chk_summary_lbl.setStyleSheet("font-weight: bold; color: #1E3A8A;")
        top.addWidget(self.chk_summary_lbl)
        top.addStretch()

        btn_sub = QPushButton("Mark Submitted")
        btn_sub.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_sub.clicked.connect(lambda: self._update_selected_checklist(is_submitted=True))
        top.addWidget(btn_sub)

        btn_ver = QPushButton("Verify Document")
        btn_ver.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_ver.clicked.connect(lambda: self._update_selected_checklist(is_verified=True))
        top.addWidget(btn_ver)
        lay.addLayout(top)

        self.chk_table = QTableWidget()
        self.chk_table.setColumnCount(6)
        self.chk_table.setHorizontalHeaderLabels(["Code", "Document Name", "Required", "Submitted", "Verified", "Verified By"])
        self.chk_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.chk_table.setSelectionBehavior(QTableWidget.SelectRows)
        lay.addWidget(self.chk_table)
        return tab

    # ------------------------------------------------------------------
    # TAB 3: TEST & INTERVIEW EVALUATION
    # ------------------------------------------------------------------
    def _build_evaluation_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(0, 10, 0, 0)

        top = QHBoxLayout()
        top.addWidget(QLabel("Select Applicant:"))
        self.eval_app_combo = QComboBox()
        top.addWidget(self.eval_app_combo)
        btn_admit = QPushButton("Generate Admit Card (PDF)")
        btn_admit.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_admit.clicked.connect(self._on_export_admit_card_pdf)
        top.addWidget(btn_admit)
        top.addStretch()
        lay.addLayout(top)

        split = QSplitter(Qt.Horizontal)

        # Admission Test Panel
        test_box = QFrame()
        test_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        tf = QFormLayout(test_box)
        tf.setContentsMargins(12, 12, 12, 12)
        tf.addRow(QLabel("<b>Admission Entrance Test</b>"))
        self.test_date_edit = QDateEdit()
        self.test_date_edit.setCalendarPopup(True)
        self.test_date_edit.setDate(QDate.currentDate())
        tf.addRow("Exam Date:", self.test_date_edit)
        self.test_venue_edit = QLineEdit("Main Examination Hall")
        tf.addRow("Venue / Room:", self.test_venue_edit)
        self.test_seat_edit = QLineEdit()
        self.test_seat_edit.setPlaceholderText("Auto if blank")
        tf.addRow("Seat Number:", self.test_seat_edit)
        self.test_max_spin = QDoubleSpinBox()
        self.test_max_spin.setRange(10, 500)
        self.test_max_spin.setValue(100)
        tf.addRow("Max Marks:", self.test_max_spin)
        self.test_obt_spin = QDoubleSpinBox()
        self.test_obt_spin.setRange(0, 500)
        self.test_obt_spin.setValue(78)
        tf.addRow("Obtained Marks:", self.test_obt_spin)

        btn_save_test = QPushButton("Save Test Score")
        btn_save_test.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 8px 12px; border-radius: 6px;")
        btn_save_test.clicked.connect(self._on_save_test_score)
        tf.addRow(btn_save_test)

        # Interview Panel
        iv_box = QFrame()
        iv_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        ivf = QFormLayout(iv_box)
        ivf.setContentsMargins(12, 12, 12, 12)
        ivf.addRow(QLabel("<b>Applicant Interview Evaluation</b>"))
        self.iv_date_edit = QDateEdit()
        self.iv_date_edit.setCalendarPopup(True)
        self.iv_date_edit.setDate(QDate.currentDate())
        ivf.addRow("Interview Date:", self.iv_date_edit)
        self.iv_panel_edit = QLineEdit("Principal Admission Panel")
        ivf.addRow("Interviewer:", self.iv_panel_edit)
        self.iv_comm_spin = QDoubleSpinBox()
        self.iv_comm_spin.setRange(0, 10)
        self.iv_comm_spin.setValue(8.0)
        ivf.addRow("Communication (0-10):", self.iv_comm_spin)
        self.iv_apt_spin = QDoubleSpinBox()
        self.iv_apt_spin.setRange(0, 10)
        self.iv_apt_spin.setValue(8.5)
        ivf.addRow("Aptitude (0-10):", self.iv_apt_spin)
        self.iv_rec_combo = QComboBox()
        self.iv_rec_combo.addItems(["Recommended", "Waitlist", "Not Recommended", "Pending"])
        ivf.addRow("Recommendation:", self.iv_rec_combo)
        self.iv_feedback_edit = QTextEdit()
        self.iv_feedback_edit.setMaximumHeight(70)
        ivf.addRow("Feedback:", self.iv_feedback_edit)

        btn_save_iv = QPushButton("Save Interview Evaluation")
        btn_save_iv.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 8px 12px; border-radius: 6px;")
        btn_save_iv.clicked.connect(self._on_save_interview)
        ivf.addRow(btn_save_iv)

        split.addWidget(test_box)
        split.addWidget(iv_box)
        lay.addWidget(split)
        return tab

    # ------------------------------------------------------------------
    # TAB 4: MERIT LIST, WAITING LIST, APPROVAL & STUDENT CONVERSION
    # ------------------------------------------------------------------
    def _build_merit_conversion_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(0, 10, 0, 0)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Year:"))
        self.merit_ay_combo = QComboBox()
        bar.addWidget(self.merit_ay_combo)

        bar.addWidget(QLabel("Class:"))
        self.merit_class_combo = QComboBox()
        bar.addWidget(self.merit_class_combo)

        bar.addWidget(QLabel("Seat Quota:"))
        self.merit_quota_spin = QSpinBox()
        self.merit_quota_spin.setRange(1, 500)
        self.merit_quota_spin.setValue(40)
        bar.addWidget(self.merit_quota_spin)

        btn_gen = QPushButton("Generate Merit List")
        btn_gen.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_gen.clicked.connect(self._on_generate_merit_list)
        bar.addWidget(btn_gen)

        btn_promote = QPushButton("Promote Waitlist (+1)")
        btn_promote.setStyleSheet("background-color: #D97706; color: white; font-weight: bold; padding: 6px 10px; border-radius: 6px;")
        btn_promote.clicked.connect(self._on_promote_waitlist)
        bar.addWidget(btn_promote)

        btn_pdf = QPushButton("Merit List (PDF)")
        btn_pdf.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold; padding: 6px 10px; border-radius: 6px;")
        btn_pdf.clicked.connect(self._on_export_merit_pdf)
        bar.addWidget(btn_pdf)
        bar.addStretch()
        lay.addLayout(bar)

        self.merit_table = QTableWidget()
        self.merit_table.setColumnCount(8)
        self.merit_table.setHorizontalHeaderLabels([
            "ID", "Rank", "Applicant ID", "Candidate Name", "Test %", "Interview", "Merit Score", "Status / Waitlist"
        ])
        self.merit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.merit_table.setSelectionBehavior(QTableWidget.SelectRows)
        lay.addWidget(self.merit_table)

        bottom = QHBoxLayout()
        btn_approve = QPushButton("Approve Admission (Selected Row)")
        btn_approve.setStyleSheet("background-color: #0D9488; color: white; font-weight: bold; padding: 8px 14px; border-radius: 6px;")
        btn_approve.clicked.connect(self._on_approve_selected)
        bottom.addWidget(btn_approve)

        btn_convert = QPushButton("Convert to Student CRM")
        btn_convert.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        btn_convert.clicked.connect(self._on_convert_selected_to_student)
        bottom.addWidget(btn_convert)
        bottom.addStretch()
        lay.addLayout(bottom)
        return tab

    # ------------------------------------------------------------------
    # TAB 5: CONFIGURABLE FEES & RECEIPTS
    # ------------------------------------------------------------------
    def _build_fees_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(0, 10, 0, 0)

        split = QSplitter(Qt.Horizontal)

        cfg_box = QFrame()
        cfg_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        cf = QFormLayout(cfg_box)
        cf.setContentsMargins(12, 12, 12, 12)
        cf.addRow(QLabel("<b>Configure Class / Year Admission Fees</b>"))

        self.cfg_ay_combo = QComboBox()
        cf.addRow("Academic Year:", self.cfg_ay_combo)
        self.cfg_class_combo = QComboBox()
        cf.addRow("Class (or Default):", self.cfg_class_combo)
        self.cfg_app_fee = QDoubleSpinBox()
        self.cfg_app_fee.setRange(0, 100000)
        self.cfg_app_fee.setValue(500)
        cf.addRow("Application Fee:", self.cfg_app_fee)
        self.cfg_test_fee = QDoubleSpinBox()
        self.cfg_test_fee.setRange(0, 100000)
        self.cfg_test_fee.setValue(300)
        cf.addRow("Admission Test Fee:", self.cfg_test_fee)
        self.cfg_enroll_fee = QDoubleSpinBox()
        self.cfg_enroll_fee.setRange(0, 500000)
        self.cfg_enroll_fee.setValue(5000)
        cf.addRow("Enrollment Fee:", self.cfg_enroll_fee)
        self.cfg_quota_spin = QSpinBox()
        self.cfg_quota_spin.setRange(1, 500)
        self.cfg_quota_spin.setValue(40)
        cf.addRow("Default Seat Quota:", self.cfg_quota_spin)

        btn_cfg = QPushButton("Save Fee Configuration")
        btn_cfg.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 7px 12px; border-radius: 6px;")
        btn_cfg.clicked.connect(self._on_save_fee_config)
        cf.addRow(btn_cfg)

        right = QWidget()
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(6, 0, 0, 0)

        pbox = QFrame()
        pbox.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;")
        pf = QHBoxLayout(pbox)
        self.pay_app_combo = QComboBox()
        pf.addWidget(self.pay_app_combo)
        self.pay_type_combo = QComboBox()
        self.pay_type_combo.addItems(["Application Fee", "Admission Test Fee", "Enrollment Fee", "Combined Admission Fee"])
        pf.addWidget(self.pay_type_combo)
        self.pay_method_combo = QComboBox()
        self.pay_method_combo.addItems(["Cash", "Card", "Bank Transfer", "Mobile Banking"])
        pf.addWidget(self.pay_method_combo)
        btn_pay = QPushButton("Collect Fee & Receipt PDF")
        btn_pay.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_pay.clicked.connect(self._on_collect_fee_and_receipt)
        pf.addWidget(btn_pay)
        rlay.addWidget(pbox)

        self.cfg_table = QTableWidget()
        self.cfg_table.setColumnCount(7)
        self.cfg_table.setHorizontalHeaderLabels([
            "Schedule", "Year", "Class", "App Fee", "Test Fee", "Enroll Fee", "Seat Quota"
        ])
        self.cfg_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rlay.addWidget(self.cfg_table)

        split.addWidget(cfg_box)
        split.addWidget(right)
        split.setSizes([340, 760])
        lay.addWidget(split)
        return tab

    # ------------------------------------------------------------------
    # TAB 6: ADMISSION STATISTICS
    # ------------------------------------------------------------------
    def _build_stats_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(0, 10, 0, 0)

        self.stats_banner_lbl = QLabel("Loading admission statistics...")
        self.stats_banner_lbl.setWordWrap(True)
        self.stats_banner_lbl.setStyleSheet(
            "background-color: #EFF6FF; border: 1px solid #BFDBFE; color: #1E3A8A; "
            "padding: 12px 16px; border-radius: 8px; font-size: 13px; font-weight: bold;"
        )
        lay.addWidget(self.stats_banner_lbl)

        self.stats_class_table = QTableWidget()
        self.stats_class_table.setColumnCount(7)
        self.stats_class_table.setHorizontalHeaderLabels([
            "Target Class", "Seat Quota", "Applications", "Selected", "Waitlisted", "Admitted", "Rejected"
        ])
        self.stats_class_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.stats_class_table)
        return tab

    # ------------------------------------------------------------------
    # DATA LOADERS & ACTION HANDLERS
    # ------------------------------------------------------------------
    def _load_reference_combos(self):
        db: Session = SessionLocal()
        try:
            years = AcademicRepository.get_all_academic_years(db)
            classes = AcademicRepository.get_classes(db)
            for combo in (self.app_ay_combo, self.merit_ay_combo, self.cfg_ay_combo):
                combo.clear()
                for y in years:
                    combo.addItem(y.name, y.id)

            for combo in (self.app_class_combo, self.merit_class_combo):
                combo.clear()
                for c in classes:
                    combo.addItem(f"{c.name} ({c.group})", c.id)

            self.cfg_class_combo.clear()
            self.cfg_class_combo.addItem("All Classes (Default)", None)
            for c in classes:
                self.cfg_class_combo.addItem(f"{c.name} ({c.group})", c.id)
        finally:
            db.close()

    def _load_applications_table(self):
        db: Session = SessionLocal()
        try:
            items, _ = AdmissionRepository.search_applications(
                db,
                search_query=self.app_search_edit.text().strip() or None,
                status=self.app_status_filter.currentText(),
                page=1,
                per_page=250,
            )
            self.applications_cache = items
            self.app_table.setRowCount(len(items))
            for combo in (self.chk_app_combo, self.eval_app_combo, self.pay_app_combo):
                combo.blockSignals(True)
                combo.clear()

            for r, a in enumerate(items):
                self.app_table.setItem(r, 0, QTableWidgetItem(str(a.id)))
                self.app_table.setItem(r, 1, QTableWidgetItem(a.applicant_id))
                self.app_table.setItem(r, 2, QTableWidgetItem(a.full_name))
                self.app_table.setItem(r, 3, QTableWidgetItem(a.applying_class.name if a.applying_class else "-"))
                self.app_table.setItem(r, 4, QTableWidgetItem(a.guardian_name))
                self.app_table.setItem(r, 5, QTableWidgetItem(a.guardian_phone))
                self.app_table.setItem(r, 6, QTableWidgetItem(a.status))
                self.app_table.setItem(r, 7, QTableWidgetItem(str(a.merit_rank or "-")))

                label = f"{a.applicant_id} - {a.full_name} ({a.status})"
                for combo in (self.chk_app_combo, self.eval_app_combo, self.pay_app_combo):
                    combo.addItem(label, a.id)

            for combo in (self.chk_app_combo, self.eval_app_combo, self.pay_app_combo):
                combo.blockSignals(False)
            self._load_checklist_for_selected()
        finally:
            db.close()

    def _on_submit_application(self):
        ay_id = self.app_ay_combo.currentData()
        cls_id = self.app_class_combo.currentData()
        if not ay_id or not cls_id:
            QMessageBox.warning(self, "Missing Setup", "Please configure an Academic Year and Class first.")
            return
        qd = self.app_dob_edit.date()
        payload = {
            "academic_year_id": ay_id,
            "applying_class_id": cls_id,
            "first_name": self.app_fname_edit.text().strip(),
            "last_name": self.app_lname_edit.text().strip(),
            "gender": self.app_gender_combo.currentText(),
            "date_of_birth": date(qd.year(), qd.month(), qd.day()),
            "guardian_name": self.app_gname_edit.text().strip(),
            "guardian_phone": self.app_gphone_edit.text().strip(),
            "previous_school": self.app_prev_school.text().strip() or None,
            "previous_gpa": float(self.app_prev_gpa.value()),
            "source_channel": self.app_source_combo.currentText(),
        }
        db: Session = SessionLocal()
        try:
            ok, app_obj, msg = AdmissionService.submit_application(db, payload)
            if ok:
                QMessageBox.information(self, "Application Saved", msg)
                self.app_fname_edit.clear()
                self.app_lname_edit.clear()
                self.app_gname_edit.clear()
                self.app_gphone_edit.clear()
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Validation", msg)
        finally:
            db.close()

    def _selected_app_id(self) -> Optional[int]:
        row = self.app_table.currentRow()
        if row < 0:
            return None
        return int(self.app_table.item(row, 0).text())

    def _on_change_status(self):
        pk = self._selected_app_id()
        if not pk:
            QMessageBox.warning(self, "Select Application", "Please select an application row.")
            return
        st = self.app_next_status_combo.currentText()
        db: Session = SessionLocal()
        try:
            ok, _, msg = AdmissionService.transition_status(db, pk, st)
            if ok:
                QMessageBox.information(self, "Status Updated", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()

    def _on_export_form_pdf(self):
        pk = self._selected_app_id()
        if not pk:
            QMessageBox.warning(self, "Select Application", "Please select an application row.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Admission Form PDF", f"Admission_Form_{pk}.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        db: Session = SessionLocal()
        try:
            AdmissionService.export_admission_form_pdf(db, pk, path)
            QMessageBox.information(self, "PDF Generated", f"Saved Admission Form to:\n{path}")
        finally:
            db.close()

    def _on_import_excel(self):
        ay_id = self.app_ay_combo.currentData()
        cls_id = self.app_class_combo.currentData()
        if not ay_id:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Import Admission Applications", "", "Spreadsheets (*.xlsx *.csv)")
        if not path:
            return
        db: Session = SessionLocal()
        try:
            res = AdmissionService.import_applications_excel(db, path, default_academic_year_id=ay_id, default_class_id=cls_id)
            QMessageBox.information(self, "Import Complete", f"Imported: {res['imported']} | Skipped: {res['skipped']}")
            self.refresh_all()
        finally:
            db.close()

    def _on_export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Admission Applications", "Admission_Applications.xlsx", "Excel Files (*.xlsx)")
        if not path:
            return
        db: Session = SessionLocal()
        try:
            AdmissionService.export_applications_excel(db, path, status=self.app_status_filter.currentText())
            QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")
        finally:
            db.close()

    def _load_checklist_for_selected(self):
        pk = self.chk_app_combo.currentData()
        if not pk:
            self.chk_table.setRowCount(0)
            return
        db: Session = SessionLocal()
        try:
            app_obj = AdmissionRepository.get_by_id(db, pk)
            if not app_obj:
                return
            items = app_obj.checklist_items or []
            self.chk_table.setRowCount(len(items))
            for r, it in enumerate(items):
                self.chk_table.setItem(r, 0, QTableWidgetItem(it.document_code))
                self.chk_table.setItem(r, 1, QTableWidgetItem(it.document_name))
                self.chk_table.setItem(r, 2, QTableWidgetItem("Required" if it.is_required else "Optional"))
                self.chk_table.setItem(r, 3, QTableWidgetItem("Yes" if it.is_submitted else "No"))
                self.chk_table.setItem(r, 4, QTableWidgetItem("Verified" if it.is_verified else "Pending"))
                self.chk_table.setItem(r, 5, QTableWidgetItem(it.verified_by or "-"))
            sm = AdmissionService.get_checklist_summary(app_obj)
            self.chk_summary_lbl.setText(
                f"Required Submitted: {sm['required_submitted']}/{sm['required_items']} | "
                f"Verified: {sm['required_verified']}/{sm['required_items']}"
            )
        finally:
            db.close()

    def _update_selected_checklist(self, is_submitted: Optional[bool] = None, is_verified: Optional[bool] = None):
        pk = self.chk_app_combo.currentData()
        row = self.chk_table.currentRow()
        if not pk or row < 0:
            QMessageBox.warning(self, "Select Row", "Select a checklist document row first.")
            return
        code = self.chk_table.item(row, 0).text()
        db: Session = SessionLocal()
        try:
            ok, _, msg = AdmissionService.update_checklist_item(db, pk, code, is_submitted=is_submitted, is_verified=is_verified)
            if ok:
                self._load_checklist_for_selected()
                self._load_applications_table()
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()

    def _on_save_test_score(self):
        pk = self.eval_app_combo.currentData()
        if not pk:
            return
        qd = self.test_date_edit.date()
        db: Session = SessionLocal()
        try:
            ok, _, msg = AdmissionService.schedule_or_score_test(
                db,
                pk,
                exam_date=date(qd.year(), qd.month(), qd.day()),
                venue_room=self.test_venue_edit.text().strip(),
                seat_number=self.test_seat_edit.text().strip() or None,
                max_marks=float(self.test_max_spin.value()),
                obtained_marks=float(self.test_obt_spin.value()),
            )
            QMessageBox.information(self, "Test Score", msg)
            self.refresh_all()
        finally:
            db.close()

    def _on_export_admit_card_pdf(self):
        pk = self.eval_app_combo.currentData()
        if not pk:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Admit Card PDF", f"Admission_Admit_Card_{pk}.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        db: Session = SessionLocal()
        try:
            AdmissionService.export_admit_card_pdf(db, pk, path)
            QMessageBox.information(self, "Admit Card Generated", f"Saved to:\n{path}")
        finally:
            db.close()

    def _on_save_interview(self):
        pk = self.eval_app_combo.currentData()
        if not pk:
            return
        qd = self.iv_date_edit.date()
        db: Session = SessionLocal()
        try:
            ok, _, msg = AdmissionService.schedule_or_record_interview(
                db,
                pk,
                interview_date=date(qd.year(), qd.month(), qd.day()),
                interviewer_name=self.iv_panel_edit.text().strip(),
                communication_score=float(self.iv_comm_spin.value()),
                aptitude_score=float(self.iv_apt_spin.value()),
                recommendation=self.iv_rec_combo.currentText(),
                feedback=self.iv_feedback_edit.toPlainText().strip() or None,
            )
            QMessageBox.information(self, "Interview Evaluation", msg)
            self.refresh_all()
        finally:
            db.close()

    def _on_generate_merit_list(self):
        ay_id = self.merit_ay_combo.currentData()
        cls_id = self.merit_class_combo.currentData()
        if not ay_id or not cls_id:
            return
        quota = int(self.merit_quota_spin.value())
        db: Session = SessionLocal()
        try:
            ok, rows, msg = AdmissionService.generate_merit_list(db, ay_id, cls_id, seat_quota=quota)
            self.merit_table.setRowCount(len(rows))
            for r, it in enumerate(rows):
                self.merit_table.setItem(r, 0, QTableWidgetItem(str(it["id"])))
                self.merit_table.setItem(r, 1, QTableWidgetItem(str(it["merit_rank"])))
                self.merit_table.setItem(r, 2, QTableWidgetItem(it["applicant_id"]))
                self.merit_table.setItem(r, 3, QTableWidgetItem(it["full_name"]))
                self.merit_table.setItem(r, 4, QTableWidgetItem(f"{it['test_pct']:.1f}%"))
                self.merit_table.setItem(r, 5, QTableWidgetItem(f"{it['interview_score']:.1f}"))
                self.merit_table.setItem(r, 6, QTableWidgetItem(f"{it['combined_score']:.2f}"))
                st_txt = f"Waitlisted (#{it['waitlist_position']})" if it.get("waitlist_position") else it["status"]
                self.merit_table.setItem(r, 7, QTableWidgetItem(st_txt))
            QMessageBox.information(self, "Merit List", msg)
            self._load_applications_table()
            self._load_statistics()
        finally:
            db.close()

    def _on_promote_waitlist(self):
        ay_id = self.merit_ay_combo.currentData()
        cls_id = self.merit_class_combo.currentData()
        if not ay_id or not cls_id:
            return
        db: Session = SessionLocal()
        try:
            ok, _, msg = AdmissionService.promote_from_waitlist(db, ay_id, cls_id, count=1)
            QMessageBox.information(self, "Waitlist Promotion", msg)
            self._on_generate_merit_list()
        finally:
            db.close()

    def _on_export_merit_pdf(self):
        ay_id = self.merit_ay_combo.currentData()
        cls_id = self.merit_class_combo.currentData()
        if not ay_id or not cls_id:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Merit List PDF", f"Merit_List_Class_{cls_id}.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        db: Session = SessionLocal()
        try:
            AdmissionService.export_merit_list_pdf(db, ay_id, cls_id, path)
            QMessageBox.information(self, "Merit List Exported", f"Saved to:\n{path}")
        finally:
            db.close()

    def _on_approve_selected(self):
        row = self.merit_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Select Candidate", "Select a candidate row in the Merit List table.")
            return
        pk = int(self.merit_table.item(row, 0).text())
        db: Session = SessionLocal()
        try:
            ok, _, msg = AdmissionService.approve_admission(db, pk)
            QMessageBox.information(self, "Admission Approval", msg)
            self.refresh_all()
        finally:
            db.close()

    def _on_convert_selected_to_student(self):
        row = self.merit_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Select Candidate", "Select a candidate row in the Merit List table.")
            return
        pk = int(self.merit_table.item(row, 0).text())
        db: Session = SessionLocal()
        try:
            ok, student, msg = AdmissionService.convert_to_student(db, pk, auto_approve_if_needed=True)
            if ok:
                QMessageBox.information(self, "Converted to Student", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Conversion Failed", msg)
        finally:
            db.close()

    def _on_save_fee_config(self):
        ay_id = self.cfg_ay_combo.currentData()
        cls_id = self.cfg_class_combo.currentData()
        if not ay_id:
            return
        db: Session = SessionLocal()
        try:
            ok, _, msg = AdmissionService.configure_fee_schedule(
                db,
                academic_year_id=ay_id,
                class_id=cls_id,
                application_fee=float(self.cfg_app_fee.value()),
                admission_test_fee=float(self.cfg_test_fee.value()),
                enrollment_fee=float(self.cfg_enroll_fee.value()),
                seat_quota=int(self.cfg_quota_spin.value()),
            )
            QMessageBox.information(self, "Fee Schedule", msg)
            self._load_fee_configs()
        finally:
            db.close()

    def _load_fee_configs(self):
        db: Session = SessionLocal()
        try:
            cfgs = AdmissionRepository.list_fee_configs(db)
            self.cfg_table.setRowCount(len(cfgs))
            for r, c in enumerate(cfgs):
                self.cfg_table.setItem(r, 0, QTableWidgetItem(c.fee_name))
                self.cfg_table.setItem(r, 1, QTableWidgetItem(c.academic_year.name if c.academic_year else str(c.academic_year_id)))
                self.cfg_table.setItem(r, 2, QTableWidgetItem(c.target_class.name if c.target_class else "All Classes"))
                self.cfg_table.setItem(r, 3, QTableWidgetItem(f"{c.application_fee:,.2f}"))
                self.cfg_table.setItem(r, 4, QTableWidgetItem(f"{c.admission_test_fee:,.2f}"))
                self.cfg_table.setItem(r, 5, QTableWidgetItem(f"{c.enrollment_fee:,.2f}"))
                self.cfg_table.setItem(r, 6, QTableWidgetItem(str(c.seat_quota)))
        finally:
            db.close()

    def _on_collect_fee_and_receipt(self):
        pk = self.pay_app_combo.currentData()
        if not pk:
            return
        db: Session = SessionLocal()
        try:
            ok, payment, msg = AdmissionService.record_fee_payment(
                db,
                pk,
                fee_type=self.pay_type_combo.currentText(),
                payment_method=self.pay_method_combo.currentText(),
            )
            if not ok or not payment:
                QMessageBox.warning(self, "Payment Error", msg)
                return
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Applicant Fee Receipt", f"{payment.receipt_no}.pdf", "PDF Files (*.pdf)"
            )
            if path:
                AdmissionService.export_applicant_receipt_pdf(db, payment.id, path)
                QMessageBox.information(self, "Receipt Saved", f"{msg}\nPDF saved to:\n{path}")
            else:
                QMessageBox.information(self, "Fee Collected", msg)
            self._load_statistics()
        finally:
            db.close()

    def _load_statistics(self):
        db: Session = SessionLocal()
        try:
            st = AdmissionService.get_admission_statistics(db)
            sc = st["status_counts"]
            fin = st["financials"]
            self.stats_banner_lbl.setText(
                f"Total Applications: {st['total_applications']}  |  "
                f"Applied: {sc['Applied']} · Under Review: {sc['Under Review']} · "
                f"Shortlisted: {sc['Shortlisted']} · Interview: {sc['Interview']} · "
                f"Selected: {sc['Selected']} · Waitlisted: {sc['Waitlisted']} · "
                f"Rejected: {sc['Rejected']} · Admitted: {sc['Admitted']}\n"
                f"Conversion Rate: {st['conversion_rate_pct']}%  |  "
                f"Avg Test: {st['avg_test_percentage']}%  |  "
                f"Avg Interview: {st['avg_interview_score']}  |  "
                f"Fees Collected: {fin['total_collected']:,.2f} (Due: {fin['total_due']:,.2f})"
            )
            cls_rows = st["class_breakdown"]
            self.stats_class_table.setRowCount(len(cls_rows))
            for r, c in enumerate(cls_rows):
                self.stats_class_table.setItem(r, 0, QTableWidgetItem(c["class_name"]))
                self.stats_class_table.setItem(r, 1, QTableWidgetItem(str(c["seat_quota"])))
                self.stats_class_table.setItem(r, 2, QTableWidgetItem(str(c["applications"])))
                self.stats_class_table.setItem(r, 3, QTableWidgetItem(str(c["selected"])))
                self.stats_class_table.setItem(r, 4, QTableWidgetItem(str(c["waitlisted"])))
                self.stats_class_table.setItem(r, 5, QTableWidgetItem(str(c["admitted"])))
                self.stats_class_table.setItem(r, 6, QTableWidgetItem(str(c["rejected"])))
        except PermissionError:
            self.stats_banner_lbl.setText("Admission statistics view is restricted for current user permissions.")
        finally:
            db.close()
