"""
EduManage Pro - Enterprise Payroll Processing & Compensation Console (PySide6)
Covers:
1. Monthly Payroll Batch Processing, Draft OT/Bonus Adjustments, Period Finalization/Locking & Accounting Disbursement
2. Salary Structure Configuration (Basic, Allowances, PF/Insurance, Overtime Rate, Tax/TIN, Attendance & Leave Rules)
3. Employee Loans & Salary Advances Ledger (Auto-deduction & Accounting Integration)
4. Employee Payment History & Tax Ledger
5. Audit-Safe Payroll Reversals, Salary Slip PDF & Monthly Payroll Reports (PDF/Excel)
"""

from datetime import date
from typing import List, Optional, Tuple

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
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
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.database.connection import SessionLocal
from app.models.fee import PAYMENT_CHANNELS
from app.models.payroll import PayrollPeriodStatus
from app.models.staff import EmployeeStatus
from app.reports.payroll_pdf import PayrollPDFGenerator
from app.repositories.payroll_repository import PayrollRepository
from app.repositories.staff_repository import StaffRepository
from app.services.payroll_service import PayrollSecurityGuard, PayrollService


class SalaryStructureDialog(QDialog):
    def __init__(self, employees: List[Tuple[str, int, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Employee Salary Structure")
        self.resize(520, 620)
        self._employees = employees
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.cmb_emp = QComboBox()
        for etype, eid, label in self._employees:
            self.cmb_emp.addItem(label, (etype, eid))
        form.addRow("Employee *:", self.cmb_emp)

        self.dt_eff = QDateEdit(QDate.currentDate())
        self.dt_eff.setCalendarPopup(True)
        form.addRow("Effective From *:", self.dt_eff)

        self.sp_basic = QDoubleSpinBox()
        self.sp_basic.setRange(0, 10000000)
        self.sp_basic.setDecimals(2)
        self.sp_basic.setValue(35000)
        form.addRow("Basic Salary *:", self.sp_basic)

        self.sp_hra = QDoubleSpinBox()
        self.sp_hra.setRange(0, 5000000)
        self.sp_hra.setDecimals(2)
        form.addRow("House Rent Allowance:", self.sp_hra)

        self.sp_med = QDoubleSpinBox()
        self.sp_med.setRange(0, 1000000)
        self.sp_med.setDecimals(2)
        form.addRow("Medical Allowance:", self.sp_med)

        self.sp_trn = QDoubleSpinBox()
        self.sp_trn.setRange(0, 1000000)
        self.sp_trn.setDecimals(2)
        form.addRow("Transport Allowance:", self.sp_trn)

        self.sp_oth_allow = QDoubleSpinBox()
        self.sp_oth_allow.setRange(0, 1000000)
        self.sp_oth_allow.setDecimals(2)
        form.addRow("Special / Other Allowance:", self.sp_oth_allow)

        self.sp_ot_rate = QDoubleSpinBox()
        self.sp_ot_rate.setRange(0, 100000)
        self.sp_ot_rate.setDecimals(2)
        form.addRow("Overtime Rate (per hr):", self.sp_ot_rate)

        self.sp_pf_pct = QDoubleSpinBox()
        self.sp_pf_pct.setRange(0, 50)
        self.sp_pf_pct.setDecimals(2)
        form.addRow("Provident Fund (%):", self.sp_pf_pct)

        self.sp_ins = QDoubleSpinBox()
        self.sp_ins.setRange(0, 500000)
        self.sp_ins.setDecimals(2)
        form.addRow("Insurance Deduction:", self.sp_ins)

        self.txt_tin = QLineEdit()
        self.txt_tin.setPlaceholderText("e.g., TIN-884210045")
        form.addRow("Tax Identification (TIN):", self.txt_tin)

        self.sp_tax = QDoubleSpinBox()
        self.sp_tax.setRange(0, 2000000)
        self.sp_tax.setDecimals(2)
        form.addRow("Monthly Income Tax (TDS):", self.sp_tax)

        self.sp_wdays = QSpinBox()
        self.sp_wdays.setRange(0, 31)
        self.sp_wdays.setValue(26)
        form.addRow("Working Days / Month (0=cal):", self.sp_wdays)

        self.sp_late_ratio = QSpinBox()
        self.sp_late_ratio.setRange(0, 15)
        self.sp_late_ratio.setValue(3)
        form.addRow("Late Days = 1 Absent (0=off):", self.sp_late_ratio)

        self.sp_leave_quota = QSpinBox()
        self.sp_leave_quota.setRange(0, 30)
        self.sp_leave_quota.setValue(2)
        form.addRow("Paid Leave Quota / Mo:", self.sp_leave_quota)

        self.chk_deduct_att = QCheckBox("Enable Attendance & Unpaid Leave Auto-Deduction")
        self.chk_deduct_att.setChecked(True)
        form.addRow("", self.chk_deduct_att)

        self.cmb_method = QComboBox()
        self.cmb_method.addItems(list(PAYMENT_CHANNELS))
        self.cmb_method.setCurrentText("Bank")
        form.addRow("Payment Method:", self.cmb_method)

        self.txt_bank_name = QLineEdit()
        form.addRow("Bank / Provider:", self.txt_bank_name)

        self.txt_bank_acc = QLineEdit()
        form.addRow("Account / Wallet No:", self.txt_bank_acc)

        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_payload(self) -> Tuple[str, int, dict]:
        etype, eid = self.cmb_emp.currentData()
        qd = self.dt_eff.date()
        return (
            etype,
            eid,
            {
                "effective_from": date(qd.year(), qd.month(), qd.day()),
                "basic_salary": self.sp_basic.value(),
                "house_rent_allowance": self.sp_hra.value(),
                "medical_allowance": self.sp_med.value(),
                "transport_allowance": self.sp_trn.value(),
                "special_allowance": self.sp_oth_allow.value(),
                "overtime_hourly_rate": self.sp_ot_rate.value(),
                "provident_fund_pct": self.sp_pf_pct.value(),
                "insurance_deduction": self.sp_ins.value(),
                "tax_tin": self.txt_tin.text().strip() or None,
                "monthly_tax_deduction": self.sp_tax.value(),
                "working_days_per_month": self.sp_wdays.value(),
                "late_days_per_absent": self.sp_late_ratio.value(),
                "monthly_paid_leave_quota": self.sp_leave_quota.value(),
                "deduct_for_absent": self.chk_deduct_att.isChecked(),
                "deduct_unpaid_leave": self.chk_deduct_att.isChecked(),
                "payment_method": self.cmb_method.currentText(),
                "bank_name": self.txt_bank_name.text().strip() or None,
                "bank_account_no": self.txt_bank_acc.text().strip() or None,
            },
        )


class LoanAdvanceDialog(QDialog):
    def __init__(self, employees: List[Tuple[str, int, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Issue Employee Loan or Salary Advance")
        self.resize(440, 360)
        self._employees = employees
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.cmb_emp = QComboBox()
        for etype, eid, label in self._employees:
            self.cmb_emp.addItem(label, (etype, eid))
        form.addRow("Employee *:", self.cmb_emp)

        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Loan", "Advance"])
        form.addRow("Facility Type *:", self.cmb_type)

        self.sp_principal = QDoubleSpinBox()
        self.sp_principal.setRange(100, 10000000)
        self.sp_principal.setDecimals(2)
        self.sp_principal.setValue(10000)
        form.addRow("Principal Amount *:", self.sp_principal)

        self.sp_inst = QDoubleSpinBox()
        self.sp_inst.setRange(50, 10000000)
        self.sp_inst.setDecimals(2)
        self.sp_inst.setValue(2500)
        form.addRow("Monthly Installment *:", self.sp_inst)

        self.sp_start_year = QSpinBox()
        self.sp_start_year.setRange(2020, 2050)
        self.sp_start_year.setValue(date.today().year)
        form.addRow("Recovery Start Year:", self.sp_start_year)

        self.sp_start_month = QSpinBox()
        self.sp_start_month.setRange(1, 12)
        self.sp_start_month.setValue(date.today().month)
        form.addRow("Recovery Start Month:", self.sp_start_month)

        self.cmb_method = QComboBox()
        self.cmb_method.addItems(list(PAYMENT_CHANNELS))
        self.cmb_method.setCurrentText("Bank")
        form.addRow("Disbursement Channel:", self.cmb_method)

        self.txt_reason = QLineEdit()
        self.txt_reason.setPlaceholderText("e.g., Medical / Family Emergency Loan")
        form.addRow("Reason *:", self.txt_reason)

        self.chk_acc = QCheckBox("Post Disbursement Voucher to School Accounting")
        self.chk_acc.setChecked(True)
        form.addRow("", self.chk_acc)

        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_payload(self) -> Tuple[str, int, dict, bool]:
        etype, eid = self.cmb_emp.currentData()
        return (
            etype,
            eid,
            {
                "loan_type": self.cmb_type.currentText(),
                "principal_amount": self.sp_principal.value(),
                "monthly_installment": self.sp_inst.value(),
                "repayment_start_year": self.sp_start_year.value(),
                "repayment_start_month": self.sp_start_month.value(),
                "disbursement_method": self.cmb_method.currentText(),
                "reason": self.txt_reason.text().strip() or "Employee Facility",
            },
            self.chk_acc.isChecked(),
        )


class PayrollPage(QWidget):
    """Enterprise Payroll & Compensation Management Workspace."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_run_id: Optional[int] = None
        self._build_ui()
        self.refresh_all()

    def _make_kpi(self, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"background-color: #1e293b; border: 1px solid #334155; border-left: 4px solid {color}; border-radius: 8px; padding: 10px;"
        )
        col = QVBoxLayout(card)
        col.setSpacing(4)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        lbl_v = QLabel(value)
        lbl_v.setObjectName("kpiValue")
        lbl_v.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_v.setStyleSheet("color: #f8fafc;")
        col.addWidget(lbl_t)
        col.addWidget(lbl_v)
        return card

    def _set_kpi_value(self, card: QFrame, val: str):
        lbl = card.findChild(QLabel, "kpiValue")
        if lbl:
            lbl.setText(val)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        tcol = QVBoxLayout()
        title = QLabel("Enterprise Payroll & Compensation")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #f8fafc;")
        sub = QLabel(
            "Salary Structures • Attendance & Leave Deductions • Loans & Advances • Period Locking • Accounting Vouchers • Audit-Safe Reversals"
        )
        sub.setStyleSheet("color: #94a3b8; font-size: 12px;")
        tcol.addWidget(title)
        tcol.addWidget(sub)
        hdr.addLayout(tcol)
        hdr.addStretch()

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self.refresh_all)
        hdr.addWidget(btn_refresh)
        root.addLayout(hdr)

        # KPI Strip
        kpi_row = QHBoxLayout()
        self.kpi_runs = self._make_kpi("Payroll Runs", "0", "#3b82f6")
        self.kpi_net = self._make_kpi("Latest Net Payroll", "৳ 0", "#10b981")
        self.kpi_loans = self._make_kpi("Active Loan Balance", "৳ 0", "#f59e0b")
        self.kpi_structures = self._make_kpi("Configured Structures", "0", "#8b5cf6")
        for c in (self.kpi_runs, self.kpi_net, self.kpi_loans, self.kpi_structures):
            kpi_row.addWidget(c)
        root.addLayout(kpi_row)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, stretch=1)

        self.tab_runs = QWidget()
        self._build_runs_tab()
        self.tabs.addTab(self.tab_runs, "📅 Monthly Payroll & Runs")

        self.tab_structures = QWidget()
        self._build_structures_tab()
        self.tabs.addTab(self.tab_structures, "🏗 Salary Structures")

        self.tab_loans = QWidget()
        self._build_loans_tab()
        self.tabs.addTab(self.tab_loans, "💳 Loans & Advances")

        self.tab_history = QWidget()
        self._build_history_tab()
        self.tabs.addTab(self.tab_history, "📜 Employee Payment History")

        self.tab_reversals = QWidget()
        self._build_reversals_tab()
        self.tabs.addTab(self.tab_reversals, "🛡 Reversals & Audit Log")

    def _build_runs_tab(self):
        lay = QVBoxLayout(self.tab_runs)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Year:"))
        self.sp_year = QSpinBox()
        self.sp_year.setRange(2020, 2050)
        self.sp_year.setValue(date.today().year)
        ctrl.addWidget(self.sp_year)

        ctrl.addWidget(QLabel("Month:"))
        self.sp_month = QSpinBox()
        self.sp_month.setRange(1, 12)
        self.sp_month.setValue(date.today().month)
        ctrl.addWidget(self.sp_month)

        btn_gen = QPushButton("⚙️ Generate / Refresh Draft")
        btn_gen.setStyleSheet("background-color: #2563eb; color: white; padding: 6px 12px; font-weight: bold;")
        btn_gen.clicked.connect(self._generate_draft_run)
        ctrl.addWidget(btn_gen)

        btn_lock = QPushButton("🔒 Finalize & Lock Period")
        btn_lock.setStyleSheet("background-color: #d97706; color: white; padding: 6px 12px; font-weight: bold;")
        btn_lock.clicked.connect(self._finalize_selected_run)
        ctrl.addWidget(btn_lock)

        btn_pay = QPushButton("💸 Disburse Batch (Post Accounting)")
        btn_pay.setStyleSheet("background-color: #059669; color: white; padding: 6px 12px; font-weight: bold;")
        btn_pay.clicked.connect(self._disburse_selected_run)
        ctrl.addWidget(btn_pay)

        btn_rev_run = QPushButton("↩️ Reverse Run")
        btn_rev_run.setStyleSheet("background-color: #dc2626; color: white; padding: 6px 12px;")
        btn_rev_run.clicked.connect(self._reverse_selected_run)
        ctrl.addWidget(btn_rev_run)

        ctrl.addStretch()
        btn_pdf = QPushButton("📄 Register PDF")
        btn_pdf.clicked.connect(self._export_run_pdf)
        ctrl.addWidget(btn_pdf)
        btn_xls = QPushButton("📊 Excel Export")
        btn_xls.clicked.connect(self._export_run_excel)
        ctrl.addWidget(btn_xls)
        lay.addLayout(ctrl)

        self.tbl_runs = QTableWidget(0, 9)
        self.tbl_runs.setHorizontalHeaderLabels(
            ["ID", "Run Code", "Period", "Emp.", "Gross", "Deductions", "Tax", "Net Payable", "Status"]
        )
        self.tbl_runs.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_runs.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_runs.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_runs.itemSelectionChanged.connect(self._on_run_selected)
        self.tbl_runs.setMaximumHeight(180)
        lay.addWidget(self.tbl_runs)

        # Payslip row actions
        slip_bar = QHBoxLayout()
        slip_bar.addWidget(QLabel("Payslips in Selected Run:"))
        slip_bar.addStretch()
        btn_ot = QPushButton("⏱ Edit OT / Bonus (Draft Only)")
        btn_ot.clicked.connect(self._edit_draft_payslip)
        slip_bar.addWidget(btn_ot)

        btn_slip_pay = QPushButton("✅ Pay Selected Slip")
        btn_slip_pay.clicked.connect(self._disburse_single_slip)
        slip_bar.addWidget(btn_slip_pay)

        btn_slip_pdf = QPushButton("🖨 Salary Slip PDF")
        btn_slip_pdf.clicked.connect(self._export_selected_slip_pdf)
        slip_bar.addWidget(btn_slip_pdf)

        btn_slip_rev = QPushButton("↩️ Reverse Selected Slip")
        btn_slip_rev.clicked.connect(self._reverse_selected_slip)
        slip_bar.addWidget(btn_slip_rev)
        lay.addLayout(slip_bar)

        self.tbl_slips = QTableWidget(0, 12)
        self.tbl_slips.setHorizontalHeaderLabels(
            [
                "ID",
                "Slip No",
                "Employee",
                "Basic",
                "Allowances",
                "OT + Bonus",
                "Gross",
                "Att/Leave Ded",
                "Tax/PF/Loan",
                "Net Payable",
                "Status",
                "Voucher",
            ]
        )
        self.tbl_slips.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_slips.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_slips.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.tbl_slips, stretch=1)

    def _build_structures_tab(self):
        lay = QVBoxLayout(self.tab_structures)
        top = QHBoxLayout()
        btn_new = QPushButton("➕ Configure / Update Salary Structure")
        btn_new.setStyleSheet("background-color: #4f46e5; color: white; padding: 7px 14px; font-weight: bold;")
        btn_new.clicked.connect(self._open_structure_dialog)
        top.addWidget(btn_new)
        top.addStretch()
        lay.addLayout(top)

        self.tbl_structures = QTableWidget(0, 10)
        self.tbl_structures.setHorizontalHeaderLabels(
            ["Code", "Employee", "Type", "Basic", "Allowances", "Base Gross", "PF %", "Tax (TDS)", "TIN", "Method"]
        )
        self.tbl_structures.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_structures.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.tbl_structures)

    def _build_loans_tab(self):
        lay = QVBoxLayout(self.tab_loans)
        top = QHBoxLayout()
        btn_new = QPushButton("➕ Issue Loan / Salary Advance")
        btn_new.setStyleSheet("background-color: #059669; color: white; padding: 7px 14px; font-weight: bold;")
        btn_new.clicked.connect(self._open_loan_dialog)
        top.addWidget(btn_new)
        top.addStretch()
        lay.addLayout(top)

        self.tbl_loans = QTableWidget(0, 9)
        self.tbl_loans.setHorizontalHeaderLabels(
            ["Loan Code", "Type", "Employee", "Principal", "Installment/Mo", "Repaid", "Remaining", "Status", "Issue Date"]
        )
        self.tbl_loans.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_loans.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.tbl_loans)

    def _build_history_tab(self):
        lay = QVBoxLayout(self.tab_history)
        top = QHBoxLayout()
        top.addWidget(QLabel("Select Employee:"))
        self.cmb_hist_emp = QComboBox()
        self.cmb_hist_emp.currentIndexChanged.connect(self._load_employee_history)
        top.addWidget(self.cmb_hist_emp, stretch=1)

        btn_hist_pdf = QPushButton("📄 Export History PDF")
        btn_hist_pdf.clicked.connect(self._export_employee_history_pdf)
        top.addWidget(btn_hist_pdf)
        lay.addLayout(top)

        self.lbl_hist_summary = QLabel("Cumulative Net Paid: ৳ 0.00 | Tax Paid: ৳ 0.00 | Active Loan Balance: ৳ 0.00")
        self.lbl_hist_summary.setStyleSheet("color: #38bdf8; font-weight: bold; padding: 4px;")
        lay.addWidget(self.lbl_hist_summary)

        self.tbl_hist = QTableWidget(0, 8)
        self.tbl_hist.setHorizontalHeaderLabels(
            ["Period", "Slip No", "Gross", "Deductions", "Tax", "Net Payable", "Method", "Status"]
        )
        self.tbl_hist.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_hist.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.tbl_hist)

    def _build_reversals_tab(self):
        lay = QVBoxLayout(self.tab_reversals)
        self.tbl_reversals = QTableWidget(0, 7)
        self.tbl_reversals.setHorizontalHeaderLabels(
            ["Reversal No", "Run ID", "Slip ID", "Scope", "Reversed Amount", "Reason", "Authorized By"]
        )
        self.tbl_reversals.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_reversals.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.tbl_reversals)

    # ------------------------------------------------------------------
    # Data Loading & Actions
    # ------------------------------------------------------------------
    def _employee_choices(self, db) -> List[Tuple[str, int, str]]:
        choices: List[Tuple[str, int, str]] = []
        for t in StaffRepository.get_all_teachers(db, active_only=False):
            if t.status in (EmployeeStatus.ACTIVE, EmployeeStatus.PROBATION, EmployeeStatus.ON_LEAVE):
                choices.append(("teacher", t.id, f"[Teacher] {t.full_name} ({t.teacher_id})"))
        for s in StaffRepository.get_all_staff(db, active_only=False):
            if s.status in (EmployeeStatus.ACTIVE, EmployeeStatus.PROBATION, EmployeeStatus.ON_LEAVE):
                choices.append(("staff", s.id, f"[Staff - {s.position}] {s.full_name} ({s.staff_id})"))
        return choices

    def refresh_all(self):
        if not PayrollSecurityGuard.can_access_payroll():
            return
        db = SessionLocal()
        try:
            runs = PayrollRepository.list_period_runs(db)
            structs = PayrollRepository.list_structures(db, active_only=True)
            loans = PayrollRepository.list_loans(db)
            revs = PayrollRepository.list_reversals(db)

            self._set_kpi_value(self.kpi_runs, str(len(runs)))
            latest_net = float(runs[0].total_net_payable or 0.0) if runs else 0.0
            self._set_kpi_value(self.kpi_net, f"৳ {latest_net:,.0f}")
            active_loan_bal = sum(float(l.remaining_balance or 0.0) for l in loans if l.status == "Active")
            self._set_kpi_value(self.kpi_loans, f"৳ {active_loan_bal:,.0f}")
            self._set_kpi_value(self.kpi_structures, str(len(structs)))

            # Runs Table
            self.tbl_runs.setRowCount(0)
            for r in runs:
                row = self.tbl_runs.rowCount()
                self.tbl_runs.insertRow(row)
                vals = [
                    str(r.id),
                    r.run_code,
                    r.period_label,
                    str(r.total_employees),
                    f"{float(r.total_gross or 0):,.2f}",
                    f"{float(r.total_deductions or 0):,.2f}",
                    f"{float(r.total_tax or 0):,.2f}",
                    f"{float(r.total_net_payable or 0):,.2f}",
                    f"{r.status}{' 🔒' if r.is_locked else ''}",
                ]
                for c_idx, val in enumerate(vals):
                    self.tbl_runs.setItem(row, c_idx, QTableWidgetItem(val))

            if runs and (self._selected_run_id is None or not any(r.id == self._selected_run_id for r in runs)):
                self._selected_run_id = runs[0].id
                self.tbl_runs.selectRow(0)
            self._load_slips_for_selected_run(db)

            # Structures Table
            self.tbl_structures.setRowCount(0)
            for st in structs:
                row = self.tbl_structures.rowCount()
                self.tbl_structures.insertRow(row)
                emp = st.teacher if st.employee_type == "teacher" else st.staff
                emp_name = emp.full_name if emp else "-"
                vals = [
                    st.structure_code,
                    emp_name,
                    st.employee_type.title(),
                    f"{float(st.basic_salary or 0):,.2f}",
                    f"{st.total_allowances:,.2f}",
                    f"{st.base_gross_salary:,.2f}",
                    f"{float(st.provident_fund_pct or 0):g}%",
                    f"{float(st.monthly_tax_deduction or 0):,.2f}",
                    st.tax_tin or "-",
                    st.payment_method,
                ]
                for c_idx, val in enumerate(vals):
                    self.tbl_structures.setItem(row, c_idx, QTableWidgetItem(val))

            # Loans Table
            self.tbl_loans.setRowCount(0)
            for ln in loans:
                row = self.tbl_loans.rowCount()
                self.tbl_loans.insertRow(row)
                emp = ln.teacher if ln.employee_type == "teacher" else ln.staff
                vals = [
                    ln.loan_code,
                    ln.loan_type,
                    emp.full_name if emp else "-",
                    f"{float(ln.principal_amount):,.2f}",
                    f"{float(ln.monthly_installment):,.2f}",
                    f"{float(ln.total_repaid):,.2f}",
                    f"{float(ln.remaining_balance):,.2f}",
                    ln.status,
                    str(ln.issue_date),
                ]
                for c_idx, val in enumerate(vals):
                    self.tbl_loans.setItem(row, c_idx, QTableWidgetItem(val))

            # History Employee Dropdown
            cur_data = self.cmb_hist_emp.currentData()
            self.cmb_hist_emp.blockSignals(True)
            self.cmb_hist_emp.clear()
            for etype, eid, label in self._employee_choices(db):
                self.cmb_hist_emp.addItem(label, (etype, eid))
            if cur_data:
                idx = self.cmb_hist_emp.findData(cur_data)
                if idx >= 0:
                    self.cmb_hist_emp.setCurrentIndex(idx)
            self.cmb_hist_emp.blockSignals(False)
            self._load_employee_history()

            # Reversals Table
            self.tbl_reversals.setRowCount(0)
            for rv in revs:
                row = self.tbl_reversals.rowCount()
                self.tbl_reversals.insertRow(row)
                vals = [
                    rv.reversal_no,
                    str(rv.payroll_run_id),
                    str(rv.payslip_id or "-"),
                    rv.reversal_scope,
                    f"{float(rv.reversed_amount):,.2f}",
                    rv.reason,
                    rv.authorized_by,
                ]
                for c_idx, val in enumerate(vals):
                    self.tbl_reversals.setItem(row, c_idx, QTableWidgetItem(val))
        finally:
            db.close()

    def _on_run_selected(self):
        row = self.tbl_runs.currentRow()
        if row >= 0:
            self._selected_run_id = int(self.tbl_runs.item(row, 0).text())
            db = SessionLocal()
            try:
                self._load_slips_for_selected_run(db)
            finally:
                db.close()

    def _load_slips_for_selected_run(self, db):
        self.tbl_slips.setRowCount(0)
        if not self._selected_run_id:
            return
        slips = PayrollRepository.list_payslips(db, run_id=self._selected_run_id)
        for s in slips:
            row = self.tbl_slips.rowCount()
            self.tbl_slips.insertRow(row)
            ot_bon = float(s.overtime_amount or 0) + float(s.bonus_amount or 0)
            att_lv = float(s.attendance_deduction or 0) + float(s.leave_deduction or 0)
            tpl = float(s.tax_deduction or 0) + float(s.provident_fund_deduction or 0) + float(s.loan_deduction or 0) + float(s.advance_deduction or 0)
            vch = s.accounting_tx.voucher_no if s.accounting_tx else "-"
            vals = [
                str(s.id),
                s.slip_no,
                f"{s.employee_name} ({s.employee_code})",
                f"{float(s.basic_salary):,.2f}",
                f"{s.total_allowances:,.2f}",
                f"{ot_bon:,.2f}",
                f"{float(s.gross_earnings):,.2f}",
                f"{att_lv:,.2f}",
                f"{tpl:,.2f}",
                f"{float(s.net_payable):,.2f}",
                s.payment_status,
                vch,
            ]
            for c_idx, val in enumerate(vals):
                self.tbl_slips.setItem(row, c_idx, QTableWidgetItem(val))

    def _selected_slip_id(self) -> Optional[int]:
        row = self.tbl_slips.currentRow()
        if row < 0:
            return None
        return int(self.tbl_slips.item(row, 0).text())

    def _generate_draft_run(self):
        db = SessionLocal()
        try:
            ok, _, msg = PayrollService.generate_monthly_payroll(db, self.sp_year.value(), self.sp_month.value())
            if ok:
                QMessageBox.information(self, "Payroll Generated", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Payroll Blocked", msg)
        except PermissionError as exc:
            QMessageBox.critical(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _finalize_selected_run(self):
        if not self._selected_run_id:
            return
        db = SessionLocal()
        try:
            ok, _, msg = PayrollService.finalize_and_lock_period(db, self._selected_run_id)
            if ok:
                QMessageBox.information(self, "Period Locked", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Lock Failed", msg)
        except PermissionError as exc:
            QMessageBox.critical(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _disburse_selected_run(self):
        if not self._selected_run_id:
            return
        db = SessionLocal()
        try:
            ok, _, msg = PayrollService.disburse_payroll_run(db, self._selected_run_id)
            if ok:
                QMessageBox.information(self, "Disbursed", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Disbursement Notice", msg)
        except PermissionError as exc:
            QMessageBox.critical(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _reverse_selected_run(self):
        if not self._selected_run_id:
            return
        reason, ok_inp = QInputDialog.getText(
            self, "Audit-Safe Period Reversal", "Mandatory Audit Reason for Reversing Payroll Period:"
        )
        if not ok_inp or not reason.strip():
            return
        db = SessionLocal()
        try:
            ok, _, msg = PayrollService.reverse_payroll_run(db, self._selected_run_id, reason=reason.strip())
            if ok:
                QMessageBox.information(self, "Audit Reversal Completed", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Reversal Failed", msg)
        except PermissionError as exc:
            QMessageBox.critical(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _edit_draft_payslip(self):
        sid = self._selected_slip_id()
        if not sid:
            QMessageBox.information(self, "Select Payslip", "Select a payslip row first.")
            return
        ot_amt, ok1 = QInputDialog.getDouble(self, "Draft Overtime Amount", "Overtime Amount:", 0.0, 0.0, 500000.0, 2)
        if not ok1:
            return
        bon_amt, ok2 = QInputDialog.getDouble(self, "Draft Bonus Amount", "Bonus Amount:", 0.0, 0.0, 1000000.0, 2)
        if not ok2:
            return
        db = SessionLocal()
        try:
            ok, _, msg = PayrollService.update_draft_payslip(
                db, sid, {"overtime_amount": ot_amt, "bonus_amount": bon_amt, "bonus_reason": "Manual Draft Bonus"}
            )
            if ok:
                QMessageBox.information(self, "Updated", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Edit Blocked", msg)
        except PermissionError as exc:
            QMessageBox.critical(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _disburse_single_slip(self):
        sid = self._selected_slip_id()
        if not sid:
            return
        db = SessionLocal()
        try:
            ok, _, msg = PayrollService.disburse_payslip(db, sid)
            if ok:
                QMessageBox.information(self, "Payslip Disbursed", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Disbursement Failed", msg)
        except PermissionError as exc:
            QMessageBox.critical(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _reverse_selected_slip(self):
        sid = self._selected_slip_id()
        if not sid:
            return
        reason, ok_inp = QInputDialog.getText(
            self, "Audit-Safe Payslip Reversal", "Mandatory Audit Reason for Reversal:"
        )
        if not ok_inp or not reason.strip():
            return
        db = SessionLocal()
        try:
            ok, _, msg = PayrollService.reverse_payslip(db, sid, reason=reason.strip())
            if ok:
                QMessageBox.information(self, "Payslip Reversed", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Reversal Failed", msg)
        except PermissionError as exc:
            QMessageBox.critical(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _export_selected_slip_pdf(self):
        sid = self._selected_slip_id()
        if not sid:
            QMessageBox.information(self, "Select Payslip", "Select a payslip row first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Salary Slip PDF", f"salary_slip_{sid}.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        db = SessionLocal()
        try:
            PayrollPDFGenerator.generate_salary_slip_pdf(db, sid, path)
            QMessageBox.information(self, "Exported", f"Salary slip saved to:\n{path}")
        finally:
            db.close()

    def _export_run_pdf(self):
        if not self._selected_run_id:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Payroll Register PDF", f"payroll_report_{self._selected_run_id}.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        db = SessionLocal()
        try:
            PayrollPDFGenerator.generate_payroll_report_pdf(db, self._selected_run_id, path)
            QMessageBox.information(self, "Exported", f"Payroll report saved to:\n{path}")
        finally:
            db.close()

    def _export_run_excel(self):
        if not self._selected_run_id:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Payroll Register Excel", f"payroll_report_{self._selected_run_id}.xlsx", "Excel Files (*.xlsx)"
        )
        if not path:
            return
        db = SessionLocal()
        try:
            PayrollService.export_payroll_report_excel(db, self._selected_run_id, path)
            QMessageBox.information(self, "Exported", f"Payroll Excel report saved to:\n{path}")
        finally:
            db.close()

    def _open_structure_dialog(self):
        db = SessionLocal()
        try:
            choices = self._employee_choices(db)
            if not choices:
                QMessageBox.information(self, "No Employees", "Add a Teacher or Staff member first.")
                return
            dlg = SalaryStructureDialog(choices, self)
            if dlg.exec() == QDialog.Accepted:
                etype, eid, payload = dlg.get_payload()
                ok, _, msg = PayrollService.upsert_salary_structure(db, etype, eid, payload)
                if ok:
                    QMessageBox.information(self, "Saved", msg)
                    self.refresh_all()
                else:
                    QMessageBox.warning(self, "Failed", msg)
        except PermissionError as exc:
            QMessageBox.critical(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _open_loan_dialog(self):
        db = SessionLocal()
        try:
            choices = self._employee_choices(db)
            if not choices:
                QMessageBox.information(self, "No Employees", "Add a Teacher or Staff member first.")
                return
            dlg = LoanAdvanceDialog(choices, self)
            if dlg.exec() == QDialog.Accepted:
                etype, eid, payload, post_acc = dlg.get_payload()
                ok, _, msg = PayrollService.issue_loan_or_advance(db, etype, eid, payload, post_to_accounting=post_acc)
                if ok:
                    QMessageBox.information(self, "Issued", msg)
                    self.refresh_all()
                else:
                    QMessageBox.warning(self, "Failed", msg)
        except PermissionError as exc:
            QMessageBox.critical(self, "Access Denied", str(exc))
        finally:
            db.close()

    def _load_employee_history(self):
        data = self.cmb_hist_emp.currentData()
        self.tbl_hist.setRowCount(0)
        if not data:
            return
        etype, eid = data
        db = SessionLocal()
        try:
            hist = PayrollService.get_employee_payment_history(db, etype, eid)
            self.lbl_hist_summary.setText(
                f"Cumulative Gross Paid: ৳ {hist['total_gross_paid']:,.2f} | "
                f"Tax Deducted: ৳ {hist['total_tax_paid']:,.2f} | "
                f"Net Paid: ৳ {hist['total_net_paid']:,.2f} | "
                f"Active Loan Balance: ৳ {hist['active_loan_balance']:,.2f}"
            )
            for s in hist["payslips"]:
                row = self.tbl_hist.rowCount()
                self.tbl_hist.insertRow(row)
                vals = [
                    f"{s.payroll_year}-{s.payroll_month:02d}",
                    s.slip_no,
                    f"{float(s.gross_earnings):,.2f}",
                    f"{float(s.total_deductions):,.2f}",
                    f"{float(s.tax_deduction):,.2f}",
                    f"{float(s.net_payable):,.2f}",
                    s.payment_method,
                    s.payment_status,
                ]
                for c_idx, val in enumerate(vals):
                    self.tbl_hist.setItem(row, c_idx, QTableWidgetItem(val))
        except PermissionError:
            self.lbl_hist_summary.setText("Access restricted.")
        finally:
            db.close()

    def _export_employee_history_pdf(self):
        data = self.cmb_hist_emp.currentData()
        if not data:
            return
        etype, eid = data
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Employee Payment History PDF", f"payment_history_{etype}_{eid}.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        db = SessionLocal()
        try:
            PayrollPDFGenerator.generate_employee_payment_history_pdf(db, etype, eid, path)
            QMessageBox.information(self, "Exported", f"Payment history PDF saved to:\n{path}")
        finally:
            db.close()
