"""
EduManage Pro - Certificate, Testimonials & ID Card Center Page
Phase 15: 3-Tab PySide6 GUI for Official Certificate Issuance, Bulk ID Card Printing & Serial Verification
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QHeaderView, QMessageBox,
    QFileDialog, QFrame, QComboBox, QLineEdit, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from app.models.student import Student
from app.models.academic import SchoolClass
from app.models.school import SchoolSetting
from app.repositories.certificate_repository import CertificateRepository
from app.services.certificate_service import CertificateService
from app.reports.certificate_pdf import CertificatePDFGenerator
from app.reports.id_card_generator import StudentIDCardGenerator
from app.ui.dialogs.certificate_issue_dialog import CertificateIssueDialog


class CertificatePage(QWidget):
    """Main PySide6 page for Certificates, Testimonials, Verification & Bulk ID Cards."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Certificate, Credential & ID Card Generator")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        subtitle = QLabel("Issue Transfer Certificates, Testimonials, Merit Awards, Bulk CR80 PVC ID Sheets & Verify Serials")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        btn_seed = QPushButton("🌱 Seed Sample Certificates")
        btn_seed.setStyleSheet("background-color: #059669; color: white; padding: 7px 12px; font-weight: bold; border-radius: 6px;")
        btn_seed.clicked.connect(self._seed_certificates)
        header_layout.addWidget(btn_seed)

        btn_issue = QPushButton("➕ Issue New Certificate")
        btn_issue.setStyleSheet("background-color: #1E3A8A; color: white; padding: 7px 14px; font-weight: bold; border-radius: 6px;")
        btn_issue.clicked.connect(self._open_issue_dialog)
        header_layout.addWidget(btn_issue)

        main_layout.addLayout(header_layout)

        # 2. KPI Cards
        self.kpi_layout = QHBoxLayout()
        self._build_kpi_cards()
        main_layout.addLayout(self.kpi_layout)

        # 3. Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 8px; }
            QTabBar::tab { padding: 8px 16px; font-weight: 600; font-size: 12px; }
            QTabBar::tab:selected { background: #1E3A8A; color: white; border-top-left-radius: 6px; border-top-right-radius: 6px; }
        """)

        self.tab_registry = QWidget()
        self._init_registry_tab()
        self.tabs.addTab(self.tab_registry, "📜 Certificate Registry & Issuance")

        self.tab_id_cards = QWidget()
        self._init_id_cards_tab()
        self.tabs.addTab(self.tab_id_cards, "🪪 Bulk CR80 ID Card Studio")

        self.tab_verify = QWidget()
        self._init_verify_tab()
        self.tabs.addTab(self.tab_verify, "🔍 Credential Verification")

        main_layout.addWidget(self.tabs)
        self.refresh_all()

    def _build_kpi_cards(self):
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cards = [
            ("Total Issued", "0", "#1E3A8A", "📜"),
            ("Transfer Certificates", "0", "#D97706", "🎓"),
            ("Merit & Testimonials", "0", "#059669", "🏆"),
            ("Revoked Credentials", "0", "#DC2626", "⛔"),
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
                    padding: 8px;
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
            v_lbl.setFont(QFont("Segoe UI", 15, QFont.Bold))
            v_lbl.setStyleSheet("color: #0F172A;")
            fl.addWidget(v_lbl)
            self.kpi_labels[title] = v_lbl
            self.kpi_layout.addWidget(frame)

    def _init_registry_tab(self):
        layout = QVBoxLayout(self.tab_registry)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        filter_row = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by serial, verify code, recipient name or ID...")
        self.txt_search.textChanged.connect(self._load_certificates)
        filter_row.addWidget(self.txt_search, 2)

        self.cmb_filter_type = QComboBox()
        self.cmb_filter_type.addItems(["All"] + CertificateService.CERTIFICATE_TYPES)
        self.cmb_filter_type.currentTextChanged.connect(self._load_certificates)
        filter_row.addWidget(self.cmb_filter_type, 1)

        btn_print_sel = QPushButton("🖨️ Export Official Certificate PDF")
        btn_print_sel.setStyleSheet("background-color: #2563EB; color: white; padding: 6px 12px; font-weight: bold; border-radius: 5px;")
        btn_print_sel.clicked.connect(self._export_selected_certificate_pdf)
        filter_row.addWidget(btn_print_sel)

        btn_revoke = QPushButton("⛔ Revoke Selected")
        btn_revoke.setStyleSheet("background-color: #DC2626; color: white; padding: 6px 12px; font-weight: bold; border-radius: 5px;")
        btn_revoke.clicked.connect(self._revoke_selected)
        filter_row.addWidget(btn_revoke)

        layout.addLayout(filter_row)

        self.tbl_certs = QTableWidget()
        self.tbl_certs.setColumnCount(8)
        self.tbl_certs.setHorizontalHeaderLabels([
            "ID", "Serial Number", "Certificate Type", "Recipient Name",
            "Class / Designation", "Issue Date", "Verify Token", "Status"
        ])
        self.tbl_certs.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_certs.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_certs.setAlternatingRowColors(True)
        self.tbl_certs.verticalHeader().setVisible(False)
        layout.addWidget(self.tbl_certs)

    def _init_id_cards_tab(self):
        layout = QVBoxLayout(self.tab_id_cards)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("<b>Filter Class:</b>"))
        self.cmb_id_class = QComboBox()
        self.cmb_id_class.addItem("All Classes", None)
        self.cmb_id_class.currentIndexChanged.connect(self._load_students_for_id)
        bar.addWidget(self.cmb_id_class)
        bar.addStretch()

        btn_single = QPushButton("🪪 Print Selected CR80 Card")
        btn_single.setStyleSheet("background-color: #2563EB; color: white; padding: 7px 14px; font-weight: bold; border-radius: 6px;")
        btn_single.clicked.connect(self._print_single_id_card)
        bar.addWidget(btn_single)

        btn_batch = QPushButton("📑 Print A4 Batch Sheet (8 Cards/Page)")
        btn_batch.setStyleSheet("background-color: #059669; color: white; padding: 7px 14px; font-weight: bold; border-radius: 6px;")
        btn_batch.clicked.connect(self._print_batch_id_sheet)
        bar.addWidget(btn_batch)

        layout.addLayout(bar)

        self.tbl_id_students = QTableWidget()
        self.tbl_id_students.setColumnCount(6)
        self.tbl_id_students.setHorizontalHeaderLabels([
            "ID", "Student ID", "Full Name", "Class & Section", "Roll", "Blood Group"
        ])
        self.tbl_id_students.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_id_students.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_id_students.setSelectionMode(QAbstractItemView.MultiSelection)
        self.tbl_id_students.setAlternatingRowColors(True)
        self.tbl_id_students.verticalHeader().setVisible(False)
        layout.addWidget(self.tbl_id_students)

    def _init_verify_tab(self):
        layout = QVBoxLayout(self.tab_verify)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        lbl = QLabel("Enter Certificate Serial Number (e.g., CERT-TC-2026-0001) or Verification Token (e.g., VER-XXXX):")
        lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        layout.addWidget(lbl)

        row = QHBoxLayout()
        self.txt_verify_input = QLineEdit()
        self.txt_verify_input.setPlaceholderText("CERT-...")
        self.txt_verify_input.setStyleSheet("padding: 8px; font-size: 13px;")
        row.addWidget(self.txt_verify_input)

        btn_check = QPushButton("🔍 Verify Authenticity")
        btn_check.setStyleSheet("background-color: #1E3A8A; color: white; padding: 8px 18px; font-weight: bold; border-radius: 6px;")
        btn_check.clicked.connect(self._run_verification)
        row.addWidget(btn_check)
        layout.addLayout(row)

        self.lbl_verify_result = QLabel("Awaiting verification lookup...")
        self.lbl_verify_result.setWordWrap(True)
        self.lbl_verify_result.setStyleSheet("background: #F8FAFC; border: 1px solid #CBD5E1; padding: 16px; border-radius: 8px; font-size: 13px;")
        layout.addWidget(self.lbl_verify_result)
        layout.addStretch()

    def refresh_all(self):
        if not self.db:
            return
        stats = CertificateRepository.get_stats(self.db)
        self.kpi_labels["Total Issued"].setText(str(stats["issued"]))
        self.kpi_labels["Transfer Certificates"].setText(str(stats["transfer_certificates"]))
        self.kpi_labels["Merit & Testimonials"].setText(str(stats["merit_and_testimonials"]))
        self.kpi_labels["Revoked Credentials"].setText(str(stats["revoked"]))

        self.cmb_id_class.blockSignals(True)
        self.cmb_id_class.clear()
        self.cmb_id_class.addItem("All Classes", None)
        for c in self.db.query(SchoolClass).order_by(SchoolClass.name).all():
            self.cmb_id_class.addItem(c.name, c.id)
        self.cmb_id_class.blockSignals(False)

        self._load_certificates()
        self._load_students_for_id()

    def _load_certificates(self):
        if not self.db:
            return
        ctype = self.cmb_filter_type.currentText()
        search = self.txt_search.text()
        certs = CertificateRepository.get_all(self.db, certificate_type=ctype, search=search)
        self.tbl_certs.setRowCount(len(certs))
        for r, cert in enumerate(certs):
            self.tbl_certs.setItem(r, 0, QTableWidgetItem(str(cert.id)))
            self.tbl_certs.setItem(r, 1, QTableWidgetItem(cert.certificate_number))
            self.tbl_certs.setItem(r, 2, QTableWidgetItem(cert.certificate_type))
            self.tbl_certs.setItem(r, 3, QTableWidgetItem(f"{cert.recipient_name} ({cert.recipient_code})"))
            self.tbl_certs.setItem(r, 4, QTableWidgetItem(cert.class_or_designation or ""))
            self.tbl_certs.setItem(r, 5, QTableWidgetItem(cert.issue_date.strftime("%Y-%m-%d") if cert.issue_date else ""))
            self.tbl_certs.setItem(r, 6, QTableWidgetItem(cert.verification_code))
            status_item = QTableWidgetItem(cert.status)
            status_item.setForeground(QColor("#059669" if cert.status == "Issued" else "#DC2626"))
            self.tbl_certs.setItem(r, 7, status_item)

    def _load_students_for_id(self):
        if not self.db:
            return
        cls_id = self.cmb_id_class.currentData()
        q = self.db.query(Student)
        if cls_id:
            q = q.filter(Student.class_id == cls_id)
        students = q.order_by(Student.roll_number).all()
        self.tbl_id_students.setRowCount(len(students))
        for r, s in enumerate(students):
            cls_str = s.school_class.name if s.school_class else "N/A"
            sec_str = s.section.name if s.section else "A"
            self.tbl_id_students.setItem(r, 0, QTableWidgetItem(str(s.id)))
            self.tbl_id_students.setItem(r, 1, QTableWidgetItem(s.student_id))
            self.tbl_id_students.setItem(r, 2, QTableWidgetItem(s.full_name))
            self.tbl_id_students.setItem(r, 3, QTableWidgetItem(f"{cls_str} - {sec_str}"))
            self.tbl_id_students.setItem(r, 4, QTableWidgetItem(str(s.roll_number)))
            self.tbl_id_students.setItem(r, 5, QTableWidgetItem(s.blood_group or "N/A"))

    def _open_issue_dialog(self):
        dlg = CertificateIssueDialog(self.db, self)
        if dlg.exec():
            self.refresh_all()
            if dlg.issued_certificate:
                QMessageBox.information(
                    self,
                    "Certificate Issued",
                    f"Credential {dlg.issued_certificate.certificate_number} issued successfully!"
                )

    def _seed_certificates(self):
        count = CertificateService.seed_sample_certificates(self.db)
        self.refresh_all()
        QMessageBox.information(self, "Seed Complete", f"Seeded {count} sample official certificates.")

    def _export_selected_certificate_pdf(self):
        row = self.tbl_certs.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a certificate row first.")
            return
        cert_id = int(self.tbl_certs.item(row, 0).text())
        cert = CertificateRepository.get_by_id(self.db, cert_id)
        if not cert:
            return
        default_name = f"{cert.certificate_number}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Official Certificate PDF", default_name, "PDF Files (*.pdf)")
        if not file_path:
            return
        school = self.db.query(SchoolSetting).first()
        CertificatePDFGenerator.generate_certificate_pdf(cert, school, file_path)
        QMessageBox.information(self, "PDF Generated", f"Certificate saved to:\n{file_path}")

    def _revoke_selected(self):
        row = self.tbl_certs.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a certificate to revoke.")
            return
        cert_id = int(self.tbl_certs.item(row, 0).text())
        confirm = QMessageBox.question(self, "Confirm Revocation", "Are you sure you want to revoke this official credential?")
        if confirm == QMessageBox.Yes:
            CertificateRepository.revoke(self.db, cert_id, "Revoked by Principal Office")
            self.refresh_all()

    def _print_single_id_card(self):
        rows = sorted(set(idx.row() for idx in self.tbl_id_students.selectedIndexes()))
        if not rows:
            QMessageBox.warning(self, "Selection Required", "Select a student row first.")
            return
        student_id = int(self.tbl_id_students.item(rows[0], 0).text())
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save CR80 ID Card", f"ID_{student.student_id}.pdf", "PDF Files (*.pdf)")
        if not file_path:
            return
        school = self.db.query(SchoolSetting).first()
        StudentIDCardGenerator.generate_single_card(student, school, file_path)
        QMessageBox.information(self, "ID Card Generated", f"CR80 ID Card saved to:\n{file_path}")

    def _print_batch_id_sheet(self):
        rows = sorted(set(idx.row() for idx in self.tbl_id_students.selectedIndexes()))
        if rows:
            ids = [int(self.tbl_id_students.item(r, 0).text()) for r in rows]
            students = self.db.query(Student).filter(Student.id.in_(ids)).all()
        else:
            students = self.db.query(Student).limit(16).all()
        if not students:
            QMessageBox.warning(self, "No Students", "No students available for batch printing.")
            return
        default_name = f"Batch_ID_Cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Batch A4 ID Sheet", default_name, "PDF Files (*.pdf)")
        if not file_path:
            return
        school = self.db.query(SchoolSetting).first()
        CertificatePDFGenerator.generate_batch_student_id_sheet(students, school, file_path)
        QMessageBox.information(self, "Batch Sheet Generated", f"Generated {len(students)} ID cards on A4 sheet:\n{file_path}")

    def _run_verification(self):
        token = self.txt_verify_input.text().strip()
        cert = CertificateRepository.verify_credential(self.db, token)
        if not cert:
            self.lbl_verify_result.setText("❌ <b>NOT FOUND:</b> No official credential matches that Serial Number or Verification Token.")
            self.lbl_verify_result.setStyleSheet("background: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; padding: 16px; border-radius: 8px;")
            return

        status_color = "#065F46" if cert.status == "Issued" else "#991B1B"
        bg_color = "#ECFDF5" if cert.status == "Issued" else "#FEF2F2"
        self.lbl_verify_result.setText(
            f"<b>Status: {cert.status.upper()}</b><br/>"
            f"<b>Serial:</b> {cert.certificate_number} | <b>Token:</b> {cert.verification_code}<br/>"
            f"<b>Type:</b> {cert.certificate_type}<br/>"
            f"<b>Recipient:</b> {cert.recipient_name} ({cert.recipient_code})<br/>"
            f"<b>Class / Designation:</b> {cert.class_or_designation}<br/>"
            f"<b>Issued Date:</b> {cert.issue_date} | <b>Conduct:</b> {cert.conduct_grade}"
        )
        self.lbl_verify_result.setStyleSheet(f"background: {bg_color}; border: 1px solid {status_color}; color: {status_color}; padding: 16px; border-radius: 8px;")
