"""
EduManage Pro - 360° Employee HR Profile & Timeline Dialog (PySide6)
Covers Qualifications, Experience, Subject Assignments (Teachers), Contracts,
Promotion/Transfer/Status History, Leave Requests, Documents, Emergency Contacts,
Performance Evaluations, Chronological Timeline, and Strictly Protected Salary Tab.
"""

from datetime import date
from typing import Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database.connection import SessionLocal
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.models.staff import Department, EmployeeStatus
from app.repositories.staff_repository import StaffRepository
from app.services.hr_service import HRSecurityGuard, HRService


class HRProfileDialog(QDialog):
    """Unified 360° HR Dossier Dialog for Teachers and Non-Teaching Staff."""

    def __init__(self, parent=None, employee_type: str = "teacher", employee_pk: int = 0):
        super().__init__(parent)
        self.employee_type = employee_type.strip().lower()
        self.employee_pk = employee_pk
        self.can_view_salary = HRSecurityGuard.can_view_salary(allow_when_no_session=True)
        self.can_manage_salary = HRSecurityGuard.can_manage_salary(allow_when_no_session=True)

        self.setWindowTitle("EduManage Pro — 360° Employee HR Dossier & Timeline")
        self.resize(1040, 720)
        self.setMinimumSize(900, 620)

        self._build_ui()
        self.reload_all()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header Summary Card
        header_card = QFrame()
        header_card.setStyleSheet(
            "background-color: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 12px;"
        )
        h_layout = QHBoxLayout(header_card)
        h_layout.setSpacing(14)

        self.lbl_avatar = QLabel("👤")
        self.lbl_avatar.setFixedSize(64, 64)
        self.lbl_avatar.setAlignment(Qt.AlignCenter)
        self.lbl_avatar.setStyleSheet(
            "background-color: #0f172a; border: 2px solid #3b82f6; border-radius: 32px; font-size: 28px;"
        )
        h_layout.addWidget(self.lbl_avatar)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        self.lbl_name = QLabel("Loading Employee...")
        self.lbl_name.setFont(QFont("Segoe UI", 15, QFont.Bold))
        self.lbl_name.setStyleSheet("color: #f8fafc;")
        self.lbl_meta = QLabel("-")
        self.lbl_meta.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.lbl_extra = QLabel("-")
        self.lbl_extra.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        info_col.addWidget(self.lbl_name)
        info_col.addWidget(self.lbl_meta)
        info_col.addWidget(self.lbl_extra)
        h_layout.addLayout(info_col, stretch=1)

        right_col = QVBoxLayout()
        right_col.setAlignment(Qt.AlignRight)
        self.lbl_status_badge = QLabel("ACTIVE")
        self.lbl_status_badge.setAlignment(Qt.AlignCenter)
        self.lbl_status_badge.setStyleSheet(
            "background-color: #065f46; color: #d1fae5; padding: 4px 12px; border-radius: 12px; font-weight: bold;"
        )
        self.lbl_salary_badge = QLabel("Salary: Confidential")
        self.lbl_salary_badge.setAlignment(Qt.AlignCenter)
        self.lbl_salary_badge.setStyleSheet(
            "background-color: #0f172a; color: #94a3b8; padding: 4px 12px; border-radius: 8px; font-size: 11px;"
        )
        right_col.addWidget(self.lbl_status_badge)
        right_col.addWidget(self.lbl_salary_badge)
        h_layout.addLayout(right_col)

        root.addWidget(header_card)

        # Tabs
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, stretch=1)

        # 1. Timeline Tab
        self.tab_timeline = QWidget()
        self._build_timeline_tab()
        self.tabs.addTab(self.tab_timeline, "📜 360° Timeline")

        # 2. Qualifications, Experience & Subjects Tab
        self.tab_qual = QWidget()
        self._build_qual_exp_tab()
        self.tabs.addTab(self.tab_qual, "🎓 Qualifications & Experience")

        # 3. Contracts & Lifecycle Tab
        self.tab_contracts = QWidget()
        self._build_contracts_tab()
        self.tabs.addTab(self.tab_contracts, "📄 Contracts & Lifecycle")

        # 4. Leave History Tab
        self.tab_leave = QWidget()
        self._build_leave_tab()
        self.tabs.addTab(self.tab_leave, "🏖 Leave History")

        # 5. Documents & Emergency Contacts Tab
        self.tab_docs = QWidget()
        self._build_docs_contacts_tab()
        self.tabs.addTab(self.tab_docs, "🗂 Documents & Emergency")

        # 6. Performance Evaluations Tab
        self.tab_evals = QWidget()
        self._build_evals_tab()
        self.tabs.addTab(self.tab_evals, "⭐ Evaluations")

        # 7. Confidential Salary Tab — ONLY rendered when authorized
        if self.can_view_salary:
            self.tab_salary = QWidget()
            self._build_salary_tab()
            self.tabs.addTab(self.tab_salary, "💰 Salary & History")

        # Footer Close
        footer = QHBoxLayout()
        footer.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        root.addLayout(footer)

    # ------------------------------------------------------------------
    # Tab Builders
    # ------------------------------------------------------------------
    def _build_timeline_tab(self):
        lay = QVBoxLayout(self.tab_timeline)
        self.tbl_timeline = QTableWidget(0, 4)
        self.tbl_timeline.setHorizontalHeaderLabels(["Date", "Category", "Event", "Details & Actor"])
        self.tbl_timeline.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_timeline.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_timeline.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        lay.addWidget(self.tbl_timeline)

    def _build_qual_exp_tab(self):
        lay = QVBoxLayout(self.tab_qual)
        top_btns = QHBoxLayout()
        btn_q = QPushButton("➕ Add Qualification")
        btn_q.clicked.connect(self._add_qualification_dialog)
        btn_e = QPushButton("➕ Add Work Experience")
        btn_e.clicked.connect(self._add_experience_dialog)
        top_btns.addWidget(btn_q)
        top_btns.addWidget(btn_e)
        if self.employee_type == "teacher":
            btn_subj = QPushButton("📘 Assign Subject")
            btn_subj.clicked.connect(self._assign_subject_dialog)
            top_btns.addWidget(btn_subj)
        top_btns.addStretch()
        lay.addLayout(top_btns)

        lay.addWidget(QLabel("Academic & Professional Qualifications"))
        self.tbl_quals = QTableWidget(0, 5)
        self.tbl_quals.setHorizontalHeaderLabels(["Degree / Cert", "Institution", "Specialization", "Year", "Grade"])
        self.tbl_quals.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_quals)

        lay.addWidget(QLabel("Prior Work Experience"))
        self.tbl_exps = QTableWidget(0, 5)
        self.tbl_exps.setHorizontalHeaderLabels(["Organization", "Designation", "Start Date", "End Date", "Responsibilities"])
        self.tbl_exps.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_exps)

        if self.employee_type == "teacher":
            lay.addWidget(QLabel("Assigned Classes & Subjects"))
            self.tbl_subjects = QTableWidget(0, 5)
            self.tbl_subjects.setHorizontalHeaderLabels(["Academic Year", "Class", "Section", "Subject", "Weekly Periods"])
            self.tbl_subjects.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            lay.addWidget(self.tbl_subjects)

    def _build_contracts_tab(self):
        lay = QVBoxLayout(self.tab_contracts)
        btn_row = QHBoxLayout()
        btn_ctr = QPushButton("📄 Issue / Renew Contract")
        btn_ctr.clicked.connect(self._issue_contract_dialog)
        btn_promote = QPushButton("🚀 Promote Employee")
        btn_promote.clicked.connect(self._promote_dialog)
        btn_transfer = QPushButton("🏢 Department Transfer")
        btn_transfer.clicked.connect(self._transfer_dialog)
        btn_status = QPushButton("🔄 Change Employment Status")
        btn_status.clicked.connect(self._status_dialog)

        btn_row.addWidget(btn_ctr)
        btn_row.addWidget(btn_promote)
        btn_row.addWidget(btn_transfer)
        btn_row.addWidget(btn_status)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        lay.addWidget(QLabel("Employment Contracts"))
        cols = ["Contract #", "Type", "Start Date", "End Date", "Hrs/Wk", "Status"]
        if self.can_view_salary:
            cols.insert(5, "Basic + Allowance")
        self.tbl_contracts = QTableWidget(0, len(cols))
        self.tbl_contracts.setHorizontalHeaderLabels(cols)
        self.tbl_contracts.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_contracts)

        lay.addWidget(QLabel("Career Lifecycle Audit (Joining, Promotions, Transfers, Status Changes)"))
        self.tbl_lifecycle = QTableWidget(0, 5)
        self.tbl_lifecycle.setHorizontalHeaderLabels(["Date", "Event Type", "Transition Details", "Reason", "Recorded By"])
        self.tbl_lifecycle.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_lifecycle)

    def _build_leave_tab(self):
        lay = QVBoxLayout(self.tab_leave)
        btn_row = QHBoxLayout()
        btn_req = QPushButton("📝 Submit Leave Request")
        btn_req.clicked.connect(self._submit_leave_dialog)
        btn_row.addWidget(btn_req)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        self.tbl_leaves = QTableWidget(0, 7)
        self.tbl_leaves.setHorizontalHeaderLabels(["ID", "Leave Type", "From", "To", "Days", "Status", "Reason / Remarks"])
        self.tbl_leaves.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_leaves)

    def _build_docs_contacts_tab(self):
        lay = QVBoxLayout(self.tab_docs)
        btn_row = QHBoxLayout()
        btn_doc = QPushButton("📎 Upload / Register Document")
        btn_doc.clicked.connect(self._add_document_dialog)
        btn_ec = QPushButton("☎ Add Emergency Contact")
        btn_ec.clicked.connect(self._add_emergency_contact_dialog)
        btn_row.addWidget(btn_doc)
        btn_row.addWidget(btn_ec)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        lay.addWidget(QLabel("Employee Document Vault"))
        self.tbl_docs = QTableWidget(0, 5)
        self.tbl_docs.setHorizontalHeaderLabels(["Doc Type", "Title", "File Name", "Verified", "Notes"])
        self.tbl_docs.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_docs)

        lay.addWidget(QLabel("Emergency Contacts"))
        self.tbl_ec = QTableWidget(0, 5)
        self.tbl_ec.setHorizontalHeaderLabels(["Contact Name", "Relationship", "Primary Phone", "Secondary Phone", "Address"])
        self.tbl_ec.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_ec)

    def _build_evals_tab(self):
        lay = QVBoxLayout(self.tab_evals)
        btn_row = QHBoxLayout()
        btn_ev = QPushButton("⭐ Record Performance Evaluation")
        btn_ev.clicked.connect(self._add_evaluation_dialog)
        btn_row.addWidget(btn_ev)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        self.tbl_evals = QTableWidget(0, 7)
        self.tbl_evals.setHorizontalHeaderLabels(["Period", "Date", "Reviewer", "Overall Score", "Rating Band", "Strengths", "Goals"])
        self.tbl_evals.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_evals)

    def _build_salary_tab(self):
        lay = QVBoxLayout(self.tab_salary)
        top_row = QHBoxLayout()
        self.lbl_sal_summary = QLabel("Current Salary: -")
        self.lbl_sal_summary.setStyleSheet("font-size: 13px; font-weight: bold; color: #38bdf8;")
        top_row.addWidget(self.lbl_sal_summary)
        top_row.addStretch()

        if self.can_manage_salary:
            btn_rev = QPushButton("💵 Process Salary Revision / Increment")
            btn_rev.setStyleSheet("background-color: #059669; color: white; padding: 6px 14px; font-weight: bold; border-radius: 6px;")
            btn_rev.clicked.connect(self._revise_salary_dialog)
            top_row.addWidget(btn_rev)
        lay.addLayout(top_row)

        self.tbl_salary = QTableWidget(0, 6)
        self.tbl_salary.setHorizontalHeaderLabels([
            "Effective Date", "Previous Salary", "New Salary", "Allowances", "Reason", "Approved By"
        ])
        self.tbl_salary.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_salary)

    # ------------------------------------------------------------------
    # Data Loader
    # ------------------------------------------------------------------
    def reload_all(self):
        db = SessionLocal()
        try:
            emp = StaffRepository.get_employee(db, self.employee_type, self.employee_pk)
            if not emp:
                QMessageBox.warning(self, "Not Found", "Employee record could not be loaded.")
                return

            dossier = HRService.get_employee_dossier(db, self.employee_type, self.employee_pk)
            self.lbl_name.setText(f"{dossier['full_name']} ({dossier['code']} / {dossier['employee_id']})")
            self.lbl_meta.setText(
                f"{dossier['role_or_designation']}  •  Dept: {dossier['department_name']}  •  "
                f"Contract: {dossier['contract_type']}  •  Exp: {dossier['experience_years']:.1f} yrs"
            )
            self.lbl_extra.setText(
                f"Joined: {dossier['joining_date']}  |  Phone: {dossier['phone']}  |  "
                f"Email: {dossier['email'] or '-'}  |  Emergency: {dossier['emergency_contact_name'] or '-'} ({dossier['emergency_contact_phone'] or '-'})"
            )
            status_lbl = EmployeeStatus.LABELS.get(dossier["status"], dossier["status"]).upper()
            self.lbl_status_badge.setText(status_lbl)

            if self.can_view_salary and dossier["salary"] is not None:
                self.lbl_salary_badge.setText(f"Salary: ৳ {dossier['salary']:,}")
                self.lbl_salary_badge.setStyleSheet(
                    "background-color: #064e3b; color: #a7f3d0; padding: 4px 12px; border-radius: 8px; font-weight: bold;"
                )
            else:
                self.lbl_salary_badge.setText("Salary: [RESTRICTED]")

            # 1. Timeline
            timeline = HRService.get_employee_timeline(db, self.employee_type, self.employee_pk)
            self.tbl_timeline.setRowCount(len(timeline))
            for i, ev in enumerate(timeline):
                self.tbl_timeline.setItem(i, 0, QTableWidgetItem(ev["timestamp"].strftime("%Y-%m-%d")))
                self.tbl_timeline.setItem(i, 1, QTableWidgetItem(ev["category"]))
                self.tbl_timeline.setItem(i, 2, QTableWidgetItem(ev["title"]))
                self.tbl_timeline.setItem(i, 3, QTableWidgetItem(f"{ev['details']}  (by {ev['actor']})"))

            # 2. Qualifications & Experience
            self.tbl_quals.setRowCount(len(emp.qualifications))
            for i, q in enumerate(emp.qualifications):
                self.tbl_quals.setItem(i, 0, QTableWidgetItem(q.degree_or_cert))
                self.tbl_quals.setItem(i, 1, QTableWidgetItem(q.institution))
                self.tbl_quals.setItem(i, 2, QTableWidgetItem(q.specialization or "-"))
                self.tbl_quals.setItem(i, 3, QTableWidgetItem(str(q.completion_year or "-")))
                self.tbl_quals.setItem(i, 4, QTableWidgetItem(q.grade_or_division or "-"))

            self.tbl_exps.setRowCount(len(emp.experiences))
            for i, ex in enumerate(emp.experiences):
                self.tbl_exps.setItem(i, 0, QTableWidgetItem(ex.organization))
                self.tbl_exps.setItem(i, 1, QTableWidgetItem(ex.designation))
                self.tbl_exps.setItem(i, 2, QTableWidgetItem(ex.start_date.isoformat()))
                self.tbl_exps.setItem(i, 3, QTableWidgetItem(ex.end_date.isoformat() if ex.end_date else "Present"))
                self.tbl_exps.setItem(i, 4, QTableWidgetItem(ex.responsibilities or "-"))

            if self.employee_type == "teacher":
                self.tbl_subjects.setRowCount(len(emp.subject_assignments))
                for i, sa in enumerate(emp.subject_assignments):
                    self.tbl_subjects.setItem(i, 0, QTableWidgetItem(sa.academic_year.name if sa.academic_year else "-"))
                    self.tbl_subjects.setItem(i, 1, QTableWidgetItem(sa.school_class.name if sa.school_class else "-"))
                    self.tbl_subjects.setItem(i, 2, QTableWidgetItem(sa.section.name if sa.section else "All"))
                    self.tbl_subjects.setItem(i, 3, QTableWidgetItem(sa.subject.name if sa.subject else "-"))
                    self.tbl_subjects.setItem(i, 4, QTableWidgetItem(str(sa.weekly_periods)))

            # 3. Contracts & Lifecycle
            self.tbl_contracts.setRowCount(len(emp.contracts))
            for i, c in enumerate(emp.contracts):
                col = 0
                self.tbl_contracts.setItem(i, col, QTableWidgetItem(c.contract_number)); col += 1
                self.tbl_contracts.setItem(i, col, QTableWidgetItem(c.contract_type)); col += 1
                self.tbl_contracts.setItem(i, col, QTableWidgetItem(c.start_date.isoformat())); col += 1
                self.tbl_contracts.setItem(i, col, QTableWidgetItem(c.end_date.isoformat() if c.end_date else "Open-Ended")); col += 1
                self.tbl_contracts.setItem(i, col, QTableWidgetItem(str(c.working_hours_per_week))); col += 1
                if self.can_view_salary:
                    self.tbl_contracts.setItem(i, col, QTableWidgetItem(f"৳ {c.basic_salary:,} + {c.allowances:,}")); col += 1
                self.tbl_contracts.setItem(i, col, QTableWidgetItem(c.status))

            self.tbl_lifecycle.setRowCount(len(emp.lifecycle_events))
            for i, ev in enumerate(emp.lifecycle_events):
                trans = []
                if ev.from_designation or ev.to_designation:
                    trans.append(f"{ev.from_designation or '-'} → {ev.to_designation or '-'}")
                if ev.from_department_id or ev.to_department_id:
                    fn = ev.from_department.name if ev.from_department else "-"
                    tn = ev.to_department.name if ev.to_department else "-"
                    trans.append(f"Dept: {fn} → {tn}")
                if ev.from_status or ev.to_status:
                    trans.append(f"Status: {ev.from_status or '-'} → {ev.to_status or '-'}")
                self.tbl_lifecycle.setItem(i, 0, QTableWidgetItem(ev.effective_date.isoformat()))
                self.tbl_lifecycle.setItem(i, 1, QTableWidgetItem(ev.event_type))
                self.tbl_lifecycle.setItem(i, 2, QTableWidgetItem(" | ".join(trans) or "-"))
                self.tbl_lifecycle.setItem(i, 3, QTableWidgetItem(ev.reason or "-"))
                self.tbl_lifecycle.setItem(i, 4, QTableWidgetItem(ev.recorded_by))

            # 4. Leaves
            self.tbl_leaves.setRowCount(len(emp.leave_requests))
            for i, lv in enumerate(emp.leave_requests):
                self.tbl_leaves.setItem(i, 0, QTableWidgetItem(str(lv.id)))
                self.tbl_leaves.setItem(i, 1, QTableWidgetItem(lv.leave_type))
                self.tbl_leaves.setItem(i, 2, QTableWidgetItem(lv.start_date.isoformat()))
                self.tbl_leaves.setItem(i, 3, QTableWidgetItem(lv.end_date.isoformat()))
                self.tbl_leaves.setItem(i, 4, QTableWidgetItem(str(lv.total_days)))
                self.tbl_leaves.setItem(i, 5, QTableWidgetItem(lv.status))
                self.tbl_leaves.setItem(i, 6, QTableWidgetItem(f"{lv.reason} ({lv.review_remarks or 'Pending'})"))

            # 5. Documents & Emergency Contacts
            self.tbl_docs.setRowCount(len(emp.documents))
            for i, doc in enumerate(emp.documents):
                self.tbl_docs.setItem(i, 0, QTableWidgetItem(doc.document_type))
                self.tbl_docs.setItem(i, 1, QTableWidgetItem(doc.title))
                self.tbl_docs.setItem(i, 2, QTableWidgetItem(doc.file_name or "-"))
                self.tbl_docs.setItem(i, 3, QTableWidgetItem("Verified" if doc.is_verified else "Pending"))
                self.tbl_docs.setItem(i, 4, QTableWidgetItem(doc.notes or "-"))

            self.tbl_ec.setRowCount(len(emp.emergency_contacts))
            for i, ec in enumerate(emp.emergency_contacts):
                self.tbl_ec.setItem(i, 0, QTableWidgetItem(ec.contact_name))
                self.tbl_ec.setItem(i, 1, QTableWidgetItem(ec.relationship_label))
                self.tbl_ec.setItem(i, 2, QTableWidgetItem(ec.primary_phone))
                self.tbl_ec.setItem(i, 3, QTableWidgetItem(ec.secondary_phone or "-"))
                self.tbl_ec.setItem(i, 4, QTableWidgetItem(ec.address or "-"))

            # 6. Evaluations
            self.tbl_evals.setRowCount(len(emp.evaluations))
            for i, evl in enumerate(emp.evaluations):
                self.tbl_evals.setItem(i, 0, QTableWidgetItem(evl.review_period))
                self.tbl_evals.setItem(i, 1, QTableWidgetItem(evl.review_date.isoformat()))
                self.tbl_evals.setItem(i, 2, QTableWidgetItem(evl.reviewer_name))
                self.tbl_evals.setItem(i, 3, QTableWidgetItem(f"{evl.overall_rating:.2f} / 5.0"))
                self.tbl_evals.setItem(i, 4, QTableWidgetItem(evl.rating_band))
                self.tbl_evals.setItem(i, 5, QTableWidgetItem(evl.strengths or "-"))
                self.tbl_evals.setItem(i, 6, QTableWidgetItem(evl.goals or "-"))

            # 7. Confidential Salary History
            if self.can_view_salary:
                self.lbl_sal_summary.setText(
                    f"Current Basic Salary: ৳ {emp.salary:,}  |  Bank: {emp.bank_name or '-'} ({emp.bank_account_no or '-'})"
                )
                hist = HRService.get_salary_history(db, self.employee_type, self.employee_pk)
                self.tbl_salary.setRowCount(len(hist))
                for i, sh in enumerate(hist):
                    self.tbl_salary.setItem(i, 0, QTableWidgetItem(sh.effective_date.isoformat()))
                    self.tbl_salary.setItem(i, 1, QTableWidgetItem(f"৳ {sh.previous_salary:,}"))
                    self.tbl_salary.setItem(i, 2, QTableWidgetItem(f"৳ {sh.new_salary:,}"))
                    self.tbl_salary.setItem(i, 3, QTableWidgetItem(f"৳ {sh.allowances:,}"))
                    self.tbl_salary.setItem(i, 4, QTableWidgetItem(sh.change_reason))
                    self.tbl_salary.setItem(i, 5, QTableWidgetItem(sh.approved_by))
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Action Dialogs
    # ------------------------------------------------------------------
    def _add_qualification_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Qualification")
        form = QFormLayout(dlg)
        deg = QLineEdit()
        inst = QLineEdit()
        spec = QLineEdit()
        yr = QSpinBox()
        yr.setRange(1960, 2050)
        yr.setValue(2020)
        grade = QLineEdit()
        form.addRow("Degree / Certificate*:", deg)
        form.addRow("Institution*:", inst)
        form.addRow("Specialization:", spec)
        form.addRow("Completion Year:", yr)
        form.addRow("Grade / Division:", grade)
        btn = QPushButton("Save Qualification")
        btn.clicked.connect(dlg.accept)
        form.addRow(btn)
        if dlg.exec() == QDialog.Accepted:
            db = SessionLocal()
            try:
                ok, _, msg = HRService.add_qualification(
                    db,
                    self.employee_type,
                    self.employee_pk,
                    {
                        "degree_or_cert": deg.text().strip(),
                        "institution": inst.text().strip(),
                        "specialization": spec.text().strip() or None,
                        "completion_year": yr.value(),
                        "grade_or_division": grade.text().strip() or None,
                    },
                )
                if ok:
                    self.reload_all()
                else:
                    QMessageBox.warning(self, "Error", msg)
            except PermissionError as exc:
                QMessageBox.warning(self, "Permission Denied", str(exc))
            finally:
                db.close()

    def _add_experience_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Work Experience")
        form = QFormLayout(dlg)
        org = QLineEdit()
        desig = QLineEdit()
        sd = QDateEdit(QDate(2020, 1, 1)); sd.setCalendarPopup(True)
        ed = QDateEdit(QDate(2024, 1, 1)); ed.setCalendarPopup(True)
        resp = QLineEdit()
        form.addRow("Organization*:", org)
        form.addRow("Designation*:", desig)
        form.addRow("Start Date:", sd)
        form.addRow("End Date:", ed)
        form.addRow("Responsibilities:", resp)
        btn = QPushButton("Save Experience")
        btn.clicked.connect(dlg.accept)
        form.addRow(btn)
        if dlg.exec() == QDialog.Accepted:
            db = SessionLocal()
            try:
                ok, _, msg = HRService.add_experience(
                    db,
                    self.employee_type,
                    self.employee_pk,
                    {
                        "organization": org.text().strip(),
                        "designation": desig.text().strip(),
                        "start_date": sd.date().toPython(),
                        "end_date": ed.date().toPython(),
                        "responsibilities": resp.text().strip() or None,
                    },
                )
                if ok:
                    self.reload_all()
                else:
                    QMessageBox.warning(self, "Error", msg)
            except PermissionError as exc:
                QMessageBox.warning(self, "Permission Denied", str(exc))
            finally:
                db.close()

    def _assign_subject_dialog(self):
        db = SessionLocal()
        try:
            years = db.query(AcademicYear).all()
            classes = db.query(SchoolClass).all()
            subjects = db.query(Subject).all()
            sections = db.query(Section).all()
            if not years or not classes or not subjects:
                QMessageBox.information(
                    self, "Missing Academic Setup", "Please configure Academic Years, Classes, and Subjects first."
                )
                return

            dlg = QDialog(self)
            dlg.setWindowTitle("Assign Subject to Teacher")
            form = QFormLayout(dlg)
            cb_year = QComboBox()
            for y in years:
                cb_year.addItem(y.name, y.id)
            cb_class = QComboBox()
            for c in classes:
                cb_class.addItem(f"{c.name} ({c.group})", c.id)
            cb_sec = QComboBox()
            cb_sec.addItem("All Sections", None)
            for s in sections:
                cb_sec.addItem(s.name, s.id)
            cb_subj = QComboBox()
            for sub in subjects:
                cb_subj.addItem(f"{sub.name} ({sub.code})", sub.id)
            sp_periods = QSpinBox()
            sp_periods.setRange(1, 40)
            sp_periods.setValue(5)

            form.addRow("Academic Year:", cb_year)
            form.addRow("Class:", cb_class)
            form.addRow("Section:", cb_sec)
            form.addRow("Subject:", cb_subj)
            form.addRow("Weekly Periods:", sp_periods)
            btn = QPushButton("Assign Subject")
            btn.clicked.connect(dlg.accept)
            form.addRow(btn)

            if dlg.exec() == QDialog.Accepted:
                ok, _, msg = HRService.assign_subject_to_teacher(
                    db,
                    teacher_pk=self.employee_pk,
                    subject_id=cb_subj.currentData(),
                    class_id=cb_class.currentData(),
                    academic_year_id=cb_year.currentData(),
                    section_id=cb_sec.currentData(),
                    weekly_periods=sp_periods.value(),
                )
                if ok:
                    self.reload_all()
                else:
                    QMessageBox.warning(self, "Notice", msg)
        except PermissionError as exc:
            QMessageBox.warning(self, "Permission Denied", str(exc))
        finally:
            db.close()

    def _issue_contract_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Issue / Renew Employment Contract")
        form = QFormLayout(dlg)
        cb_type = QComboBox()
        cb_type.addItems(["Permanent", "Probation", "Fixed-Term", "Part-Time"])
        sd = QDateEdit(QDate.currentDate()); sd.setCalendarPopup(True)
        ed = QDateEdit(QDate.currentDate().addYears(1)); ed.setCalendarPopup(True)
        hrs = QSpinBox(); hrs.setRange(8, 60); hrs.setValue(40)
        terms = QLineEdit()

        form.addRow("Contract Type:", cb_type)
        form.addRow("Start Date:", sd)
        form.addRow("End Date:", ed)
        form.addRow("Working Hours/Week:", hrs)
        sal_spin = None
        allow_spin = None
        if self.can_manage_salary:
            sal_spin = QSpinBox(); sal_spin.setRange(0, 500000); sal_spin.setValue(35000)
            allow_spin = QSpinBox(); allow_spin.setRange(0, 200000); allow_spin.setValue(0)
            form.addRow("Basic Salary (BDT):", sal_spin)
            form.addRow("Allowances (BDT):", allow_spin)
        form.addRow("Terms Summary:", terms)

        btn = QPushButton("Save Contract")
        btn.clicked.connect(dlg.accept)
        form.addRow(btn)

        if dlg.exec() == QDialog.Accepted:
            payload = {
                "contract_type": cb_type.currentText(),
                "start_date": sd.date().toPython(),
                "end_date": ed.date().toPython(),
                "working_hours_per_week": hrs.value(),
                "terms_summary": terms.text().strip() or None,
            }
            if sal_spin is not None:
                payload["basic_salary"] = sal_spin.value()
                payload["allowances"] = allow_spin.value()
            db = SessionLocal()
            try:
                ok, _, msg = HRService.create_contract(db, self.employee_type, self.employee_pk, payload)
                if ok:
                    self.reload_all()
                else:
                    QMessageBox.warning(self, "Error", msg)
            except PermissionError as exc:
                QMessageBox.warning(self, "Permission Denied", str(exc))
            finally:
                db.close()

    def _promote_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Promote Employee")
        form = QFormLayout(dlg)
        desig = QLineEdit()
        reason = QLineEdit("Merit & Annual Performance Review")
        sal_spin = None
        form.addRow("New Designation / Role*:", desig)
        if self.can_manage_salary:
            sal_spin = QSpinBox(); sal_spin.setRange(0, 500000); sal_spin.setValue(45000)
            form.addRow("Revised Salary (Optional):", sal_spin)
        form.addRow("Reason:", reason)
        btn = QPushButton("Confirm Promotion")
        btn.clicked.connect(dlg.accept)
        form.addRow(btn)

        if dlg.exec() == QDialog.Accepted:
            db = SessionLocal()
            try:
                ok, _, msg = HRService.promote_employee(
                    db,
                    self.employee_type,
                    self.employee_pk,
                    desig.text().strip(),
                    new_salary=sal_spin.value() if sal_spin is not None else None,
                    reason=reason.text().strip() or "Promotion",
                )
                if ok:
                    self.reload_all()
                else:
                    QMessageBox.warning(self, "Error", msg)
            except PermissionError as exc:
                QMessageBox.warning(self, "Permission Denied", str(exc))
            finally:
                db.close()

    def _transfer_dialog(self):
        db = SessionLocal()
        try:
            depts = StaffRepository.get_or_create_departments(db)
            dlg = QDialog(self)
            dlg.setWindowTitle("Department Transfer")
            form = QFormLayout(dlg)
            cb_dept = QComboBox()
            for d in depts:
                cb_dept.addItem(d.name, d.id)
            reason = QLineEdit("Operational Reassignment")
            form.addRow("Target Department:", cb_dept)
            form.addRow("Reason:", reason)
            btn = QPushButton("Transfer Employee")
            btn.clicked.connect(dlg.accept)
            form.addRow(btn)
            if dlg.exec() == QDialog.Accepted:
                ok, _, msg = HRService.transfer_employee(
                    db,
                    self.employee_type,
                    self.employee_pk,
                    cb_dept.currentData(),
                    reason=reason.text().strip(),
                )
                if ok:
                    self.reload_all()
                else:
                    QMessageBox.warning(self, "Error", msg)
        except PermissionError as exc:
            QMessageBox.warning(self, "Permission Denied", str(exc))
        finally:
            db.close()

    def _status_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Update Employment Status")
        form = QFormLayout(dlg)
        cb_status = QComboBox()
        for code in EmployeeStatus.ALL:
            cb_status.addItem(EmployeeStatus.LABELS.get(code, code), code)
        reason = QLineEdit()
        form.addRow("New Status:", cb_status)
        form.addRow("Reason:", reason)
        btn = QPushButton("Update Status")
        btn.clicked.connect(dlg.accept)
        form.addRow(btn)
        if dlg.exec() == QDialog.Accepted:
            db = SessionLocal()
            try:
                ok, _, msg = HRService.change_employment_status(
                    db,
                    self.employee_type,
                    self.employee_pk,
                    cb_status.currentData(),
                    reason=reason.text().strip(),
                )
                if ok:
                    self.reload_all()
                else:
                    QMessageBox.warning(self, "Error", msg)
            except PermissionError as exc:
                QMessageBox.warning(self, "Permission Denied", str(exc))
            finally:
                db.close()

    def _submit_leave_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Submit Leave Request")
        form = QFormLayout(dlg)
        cb_type = QComboBox()
        cb_type.addItems(["Casual", "Sick", "Annual", "Maternity/Paternity", "Study", "Unpaid"])
        sd = QDateEdit(QDate.currentDate()); sd.setCalendarPopup(True)
        ed = QDateEdit(QDate.currentDate()); ed.setCalendarPopup(True)
        reason = QLineEdit()
        backup = QLineEdit()
        form.addRow("Leave Type:", cb_type)
        form.addRow("Start Date:", sd)
        form.addRow("End Date:", ed)
        form.addRow("Reason*:", reason)
        form.addRow("Backup / Substitute:", backup)
        btn = QPushButton("Submit Request")
        btn.clicked.connect(dlg.accept)
        form.addRow(btn)
        if dlg.exec() == QDialog.Accepted:
            db = SessionLocal()
            try:
                ok, _, msg = HRService.submit_leave_request(
                    db,
                    self.employee_type,
                    self.employee_pk,
                    cb_type.currentText(),
                    sd.date().toPython(),
                    ed.date().toPython(),
                    reason.text().strip(),
                    backup_assignee=backup.text().strip() or None,
                )
                if ok:
                    self.reload_all()
                else:
                    QMessageBox.warning(self, "Validation Error", msg)
            except PermissionError as exc:
                QMessageBox.warning(self, "Permission Denied", str(exc))
            finally:
                db.close()

    def _add_document_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Register / Upload Employee Document")
        form = QFormLayout(dlg)
        cb_type = QComboBox()
        cb_type.addItems(["NID / Passport", "Academic Certificate", "Appointment Letter", "Contract", "Experience Letter", "Other"])
        title = QLineEdit()
        path_edit = QLineEdit()
        btn_browse = QPushButton("Browse File...")
        btn_browse.clicked.connect(lambda: path_edit.setText(QFileDialog.getOpenFileName(dlg, "Select Document")[0]))
        notes = QLineEdit()
        form.addRow("Document Type:", cb_type)
        form.addRow("Title*:", title)
        form.addRow("File Path:", path_edit)
        form.addRow("", btn_browse)
        form.addRow("Notes:", notes)
        btn = QPushButton("Save Document")
        btn.clicked.connect(dlg.accept)
        form.addRow(btn)
        if dlg.exec() == QDialog.Accepted and title.text().strip():
            db = SessionLocal()
            try:
                ok, _, msg = HRService.add_document(
                    db,
                    self.employee_type,
                    self.employee_pk,
                    cb_type.currentText(),
                    title.text().strip(),
                    source_file_path=path_edit.text().strip() or None,
                    notes=notes.text().strip() or None,
                )
                if ok:
                    self.reload_all()
                else:
                    QMessageBox.warning(self, "Error", msg)
            except PermissionError as exc:
                QMessageBox.warning(self, "Permission Denied", str(exc))
            finally:
                db.close()

    def _add_emergency_contact_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Emergency Contact")
        form = QFormLayout(dlg)
        cname = QLineEdit()
        rel = QLineEdit("Spouse / Relative")
        p1 = QLineEdit()
        p2 = QLineEdit()
        addr = QLineEdit()
        form.addRow("Contact Name*:", cname)
        form.addRow("Relationship:", rel)
        form.addRow("Primary Phone*:", p1)
        form.addRow("Secondary Phone:", p2)
        form.addRow("Address:", addr)
        btn = QPushButton("Save Contact")
        btn.clicked.connect(dlg.accept)
        form.addRow(btn)
        if dlg.exec() == QDialog.Accepted:
            db = SessionLocal()
            try:
                ok, _, msg = HRService.add_emergency_contact(
                    db,
                    self.employee_type,
                    self.employee_pk,
                    {
                        "contact_name": cname.text().strip(),
                        "relationship_label": rel.text().strip() or "Relative",
                        "primary_phone": p1.text().strip(),
                        "secondary_phone": p2.text().strip() or None,
                        "address": addr.text().strip() or None,
                        "is_primary": True,
                    },
                )
                if ok:
                    self.reload_all()
                else:
                    QMessageBox.warning(self, "Error", msg)
            except PermissionError as exc:
                QMessageBox.warning(self, "Permission Denied", str(exc))
            finally:
                db.close()

    def _add_evaluation_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Record Performance Evaluation")
        form = QFormLayout(dlg)
        period = QLineEdit(f"{date.today().year} Annual Review")
        p_sp = QDoubleSpinBox(); p_sp.setRange(1.0, 5.0); p_sp.setValue(4.0); p_sp.setSingleStep(0.5)
        c_sp = QDoubleSpinBox(); c_sp.setRange(1.0, 5.0); c_sp.setValue(4.0); c_sp.setSingleStep(0.5)
        t_sp = QDoubleSpinBox(); t_sp.setRange(1.0, 5.0); t_sp.setValue(4.0); t_sp.setSingleStep(0.5)
        cp_sp = QDoubleSpinBox(); cp_sp.setRange(1.0, 5.0); cp_sp.setValue(4.0); cp_sp.setSingleStep(0.5)
        strengths = QLineEdit()
        goals = QLineEdit()
        form.addRow("Review Period:", period)
        form.addRow("Punctuality (1-5):", p_sp)
        form.addRow("Competency (1-5):", c_sp)
        form.addRow("Teamwork (1-5):", t_sp)
        form.addRow("Compliance (1-5):", cp_sp)
        form.addRow("Strengths:", strengths)
        form.addRow("Goals:", goals)
        btn = QPushButton("Submit Evaluation")
        btn.clicked.connect(dlg.accept)
        form.addRow(btn)
        if dlg.exec() == QDialog.Accepted:
            db = SessionLocal()
            try:
                ok, _, msg = HRService.record_evaluation(
                    db,
                    self.employee_type,
                    self.employee_pk,
                    {
                        "review_period": period.text().strip(),
                        "punctuality_score": p_sp.value(),
                        "competency_score": c_sp.value(),
                        "teamwork_score": t_sp.value(),
                        "compliance_score": cp_sp.value(),
                        "strengths": strengths.text().strip() or None,
                        "goals": goals.text().strip() or None,
                    },
                )
                if ok:
                    self.reload_all()
                else:
                    QMessageBox.warning(self, "Error", msg)
            except PermissionError as exc:
                QMessageBox.warning(self, "Permission Denied", str(exc))
            finally:
                db.close()

    def _revise_salary_dialog(self):
        if not self.can_manage_salary:
            QMessageBox.warning(self, "Access Denied", "You are not authorized to revise salaries.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Confidential Salary Revision")
        form = QFormLayout(dlg)
        sal = QSpinBox(); sal.setRange(0, 500000); sal.setValue(40000)
        allow = QSpinBox(); allow.setRange(0, 200000); allow.setValue(0)
        reason = QLineEdit("Annual Increment")
        ref = QLineEdit()
        form.addRow("New Basic Salary (BDT):", sal)
        form.addRow("Monthly Allowances (BDT):", allow)
        form.addRow("Change Reason:", reason)
        form.addRow("Reference #:", ref)
        btn = QPushButton("Approve & Save Salary")
        btn.clicked.connect(dlg.accept)
        form.addRow(btn)
        if dlg.exec() == QDialog.Accepted:
            db = SessionLocal()
            try:
                ok, _, msg = HRService.revise_salary(
                    db,
                    self.employee_type,
                    self.employee_pk,
                    new_salary=sal.value(),
                    allowances=allow.value(),
                    change_reason=reason.text().strip() or "Salary Revision",
                    reference_no=ref.text().strip() or None,
                )
                if ok:
                    self.reload_all()
                else:
                    QMessageBox.warning(self, "Error", msg)
            except PermissionError as exc:
                QMessageBox.warning(self, "Permission Denied", str(exc))
            finally:
                db.close()
