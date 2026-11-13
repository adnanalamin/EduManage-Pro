"""
EduManage Pro - Student 360° CRM Profile & Timeline Dialog (PySide6)
Full CRM dossier featuring:
- Photo, Digital ID badge, live QR code widget, tags, status badge, lifecycle controls
- 6 CRM Tabs:
  1. Timeline (chronological feed)
  2. Guardians & Family Relationships
  3. Academic, Admission, Previous Schools & Status History
  4. Document Vault (Upload & Verify)
  5. Medical Profile & Emergency Contacts
  6. CRM Notes, Tags & Custom Fields
"""

from datetime import date
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
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
from app.models.student import Student, StudentStatus
from app.reports.student_profile_pdf import StudentProfilePDFGenerator
from app.models.school import SchoolSetting
from app.repositories.student_repository import StudentRepository
from app.services.student_service import StudentService
from app.ui.dialogs.student_form_dialog import StudentFormDialog
from app.ui.dialogs.student_id_card_dialog import StudentIDCardDialog
from app.ui.dialogs.student_lifecycle_dialog import StudentLifecycleDialog
from app.ui.dialogs.student_promote_dialog import StudentPromoteDialog
from app.ui.widgets.qr_code_widget import QRCodeWidget
from app.utils.qr_generator import build_qr_payload, generate_digital_id


class StudentProfileDialog(QDialog):
    def __init__(self, parent=None, student_pk: int = 0, actor: str = "admin"):
        super().__init__(parent)
        self.student_pk = student_pk
        self.actor = actor
        self.modified = False
        self.setWindowTitle("EduManage Pro — Student 360° CRM Profile")
        self.resize(1020, 720)
        self._build_ui()
        self._reload_all()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # 1. Top CRM Identity Banner
        banner = QFrame()
        banner.setStyleSheet(
            "background-color: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 10px;"
        )
        b_row = QHBoxLayout(banner)
        b_row.setSpacing(16)

        self.photo_lbl = QLabel("PHOTO")
        self.photo_lbl.setFixedSize(88, 106)
        self.photo_lbl.setAlignment(Qt.AlignCenter)
        self.photo_lbl.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #475569; border-radius: 8px; color: #94a3b8;"
        )
        b_row.addWidget(self.photo_lbl)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        self.name_lbl = QLabel("Student Name")
        self.name_lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.name_lbl.setStyleSheet("color: #f8fafc;")

        self.meta_lbl = QLabel("ID | Admission # | Digital ID | Class & Section | Roll")
        self.meta_lbl.setStyleSheet("color: #93c5fd; font-size: 12px;")

        self.status_tags_lbl = QLabel("Status | Tags")
        self.status_tags_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")

        action_strip = QHBoxLayout()
        action_strip.setSpacing(6)
        btn_edit = QPushButton("Edit Profile")
        btn_edit.clicked.connect(self._edit_profile)
        btn_id = QPushButton("Digital ID Card")
        btn_id.clicked.connect(self._open_id_card)
        btn_pdf = QPushButton("Export Dossier PDF")
        btn_pdf.clicked.connect(self._export_pdf)
        btn_promote = QPushButton("Promote")
        btn_promote.clicked.connect(self._open_promote)
        btn_transfer = QPushButton("Transfer")
        btn_transfer.clicked.connect(lambda: self._open_lifecycle("transfer"))
        btn_withdraw = QPushButton("Withdraw")
        btn_withdraw.clicked.connect(lambda: self._open_lifecycle("withdraw"))
        self.btn_archive_restore = QPushButton("Archive")
        self.btn_archive_restore.clicked.connect(self._toggle_archive_restore)

        for btn in (btn_edit, btn_id, btn_pdf, btn_promote, btn_transfer, btn_withdraw, self.btn_archive_restore):
            btn.setStyleSheet("padding: 5px 10px; border-radius: 5px; font-size: 11px;")
            action_strip.addWidget(btn)
        action_strip.addStretch()

        info_col.addWidget(self.name_lbl)
        info_col.addWidget(self.meta_lbl)
        info_col.addWidget(self.status_tags_lbl)
        info_col.addLayout(action_strip)
        b_row.addLayout(info_col, stretch=1)

        self.qr_widget = QRCodeWidget(size=92)
        b_row.addWidget(self.qr_widget)
        root.addWidget(banner)

        # 2. CRM Tabs
        self.tabs = QTabWidget()
        self._build_timeline_tab()
        self._build_guardians_family_tab()
        self._build_history_tab()
        self._build_documents_tab()
        self._build_medical_emergency_tab()
        self._build_notes_tags_custom_tab()
        root.addWidget(self.tabs, stretch=1)

        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self._close_dialog)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

    # --- Tab 1: Timeline ---
    def _build_timeline_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self.timeline_table = QTableWidget(0, 5)
        self.timeline_table.setHorizontalHeaderLabels(["Timestamp", "Category", "Event", "Details", "Recorded By"])
        self.timeline_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.timeline_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.timeline_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        layout.addWidget(self.timeline_table)
        self.tabs.addTab(w, "Timeline")

    # --- Tab 2: Guardians & Family ---
    def _build_guardians_family_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        g_hdr = QHBoxLayout()
        g_hdr.addWidget(QLabel("Linked Guardians & Authorized Pickups"))
        g_hdr.addStretch()
        btn_add_g = QPushButton("+ Add Guardian")
        btn_add_g.clicked.connect(self._add_guardian_prompt)
        g_hdr.addWidget(btn_add_g)
        layout.addLayout(g_hdr)

        self.guardians_table = QTableWidget(0, 7)
        self.guardians_table.setHorizontalHeaderLabels(
            ["Priority", "Guardian Name", "Relation", "Phone", "Email", "Primary", "Pickup/Emergency"]
        )
        self.guardians_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.guardians_table)

        f_hdr = QHBoxLayout()
        f_hdr.addWidget(QLabel("Family & Sibling Relationships"))
        f_hdr.addStretch()
        btn_add_f = QPushButton("+ Link Sibling / Relative")
        btn_add_f.clicked.connect(self._link_family_prompt)
        f_hdr.addWidget(btn_add_f)
        layout.addLayout(f_hdr)

        self.family_table = QTableWidget(0, 4)
        self.family_table.setHorizontalHeaderLabels(["Related Student ID", "Full Name", "Class", "Relationship"])
        self.family_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.family_table)

        self.tabs.addTab(w, "Guardians & Family")

    # --- Tab 3: Academic, Admission, Previous Schools & Status History ---
    def _build_history_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        layout.addWidget(QLabel("Admission History"))
        self.admission_hist_table = QTableWidget(0, 5)
        self.admission_hist_table.setHorizontalHeaderLabels(["Date", "Admission #", "Type", "Class / Session", "Remarks"])
        self.admission_hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.admission_hist_table)

        layout.addWidget(QLabel("Academic Year History"))
        self.academic_hist_table = QTableWidget(0, 5)
        self.academic_hist_table.setHorizontalHeaderLabels(["Academic Year", "Class (Sec)", "Roll", "Result Status", "Remarks"])
        self.academic_hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.academic_hist_table)

        ps_hdr = QHBoxLayout()
        ps_hdr.addWidget(QLabel("Previous Schools"))
        ps_hdr.addStretch()
        btn_add_ps = QPushButton("+ Add Previous School")
        btn_add_ps.clicked.connect(self._add_previous_school_prompt)
        ps_hdr.addWidget(btn_add_ps)
        layout.addLayout(ps_hdr)

        self.prev_schools_table = QTableWidget(0, 5)
        self.prev_schools_table.setHorizontalHeaderLabels(["School Name", "Curriculum/Board", "Last Class", "TC #", "Reason"])
        self.prev_schools_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.prev_schools_table)

        layout.addWidget(QLabel("Status Change Audit Trail"))
        self.status_hist_table = QTableWidget(0, 5)
        self.status_hist_table.setHorizontalHeaderLabels(["Effective Date", "Transition", "Reference / School", "Reason", "Changed By"])
        self.status_hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.status_hist_table)

        self.tabs.addTab(w, "Academic & History")

    # --- Tab 4: Documents Vault ---
    def _build_documents_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        bar = QHBoxLayout()
        btn_up = QPushButton("+ Upload Document")
        btn_up.clicked.connect(self._upload_document_prompt)
        btn_ver = QPushButton("Toggle Verification")
        btn_ver.clicked.connect(self._verify_selected_document)
        bar.addWidget(btn_up)
        bar.addWidget(btn_ver)
        bar.addStretch()
        layout.addLayout(bar)

        self.docs_table = QTableWidget(0, 6)
        self.docs_table.setHorizontalHeaderLabels(["Type", "Title", "File Name", "Verified", "Uploaded By", "Path"])
        self.docs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.docs_table)

        self.tabs.addTab(w, "Documents")

    # --- Tab 5: Medical & Emergency ---
    def _build_medical_emergency_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        med_box = QGroupBox("Structured Medical Profile")
        med_form = QFormLayout(med_box)
        self.med_blood = QLineEdit()
        self.med_allergies = QLineEdit()
        self.med_conditions = QLineEdit()
        self.med_medications = QLineEdit()
        self.med_immunization = QLineEdit()
        self.med_physician = QLineEdit()
        self.med_physician_phone = QLineEdit()
        self.med_protocol = QLineEdit()
        med_form.addRow("Blood Group:", self.med_blood)
        med_form.addRow("Allergies:", self.med_allergies)
        med_form.addRow("Chronic Conditions:", self.med_conditions)
        med_form.addRow("Current Medications:", self.med_medications)
        med_form.addRow("Immunization Status:", self.med_immunization)
        med_form.addRow("Physician Name:", self.med_physician)
        med_form.addRow("Physician Phone:", self.med_physician_phone)
        med_form.addRow("Emergency Protocol:", self.med_protocol)

        btn_save_med = QPushButton("Save Medical Profile")
        btn_save_med.setStyleSheet("background-color: #2563eb; color: white; padding: 6px 14px; border-radius: 5px;")
        btn_save_med.clicked.connect(self._save_medical_profile)
        med_form.addRow("", btn_save_med)
        layout.addWidget(med_box)

        ec_hdr = QHBoxLayout()
        ec_hdr.addWidget(QLabel("Emergency Contacts"))
        ec_hdr.addStretch()
        btn_add_ec = QPushButton("+ Add Emergency Contact")
        btn_add_ec.clicked.connect(self._add_emergency_contact_prompt)
        ec_hdr.addWidget(btn_add_ec)
        layout.addLayout(ec_hdr)

        self.emergency_table = QTableWidget(0, 5)
        self.emergency_table.setHorizontalHeaderLabels(["Priority", "Name", "Relationship", "Primary Phone", "Can Pickup"])
        self.emergency_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.emergency_table)

        self.tabs.addTab(w, "Medical & Emergency")

    # --- Tab 6: Notes, Tags & Custom Fields ---
    def _build_notes_tags_custom_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # Tags row
        tag_row = QHBoxLayout()
        tag_row.addWidget(QLabel("CRM Tags (comma-separated):"))
        self.tags_edit = QLineEdit()
        btn_save_tags = QPushButton("Save Tags")
        btn_save_tags.clicked.connect(self._save_tags)
        tag_row.addWidget(self.tags_edit, stretch=1)
        tag_row.addWidget(btn_save_tags)
        layout.addLayout(tag_row)

        # Notes composer & table
        n_box = QGroupBox("Student Notes & Communications")
        n_layout = QVBoxLayout(n_box)
        n_form = QHBoxLayout()
        self.note_cat = QComboBox()
        self.note_cat.addItems(["General", "Academic", "Behavioral", "Financial", "Medical", "Parent Communication"])
        self.note_title = QLineEdit()
        self.note_title.setPlaceholderText("Note title...")
        self.note_content = QLineEdit()
        self.note_content.setPlaceholderText("Note content...")
        self.note_pin = QCheckBox("Pin")
        btn_add_note = QPushButton("Add Note")
        btn_add_note.clicked.connect(self._add_note)
        n_form.addWidget(self.note_cat)
        n_form.addWidget(self.note_title, stretch=1)
        n_form.addWidget(self.note_content, stretch=2)
        n_form.addWidget(self.note_pin)
        n_form.addWidget(btn_add_note)
        n_layout.addLayout(n_form)

        self.notes_table = QTableWidget(0, 5)
        self.notes_table.setHorizontalHeaderLabels(["Pinned", "Category", "Title", "Content", "Author"])
        self.notes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        n_layout.addWidget(self.notes_table)
        layout.addWidget(n_box)

        # Custom fields editor
        cf_box = QGroupBox("Custom Fields (Key / Value)")
        cf_layout = QVBoxLayout(cf_box)
        cf_btn_row = QHBoxLayout()
        btn_add_cf = QPushButton("+ Add Custom Field Row")
        btn_add_cf.clicked.connect(self._add_custom_field_row)
        btn_save_cf = QPushButton("Save Custom Fields")
        btn_save_cf.clicked.connect(self._save_custom_fields)
        cf_btn_row.addWidget(btn_add_cf)
        cf_btn_row.addWidget(btn_save_cf)
        cf_btn_row.addStretch()
        cf_layout.addLayout(cf_btn_row)

        self.custom_fields_table = QTableWidget(0, 2)
        self.custom_fields_table.setHorizontalHeaderLabels(["Field Key", "Field Value"])
        self.custom_fields_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        cf_layout.addWidget(self.custom_fields_table)
        layout.addWidget(cf_box)

        self.tabs.addTab(w, "Notes, Tags & Custom Fields")

    # ------------------------------------------------------------------
    # Data Loading
    # ------------------------------------------------------------------
    def _reload_all(self):
        db = SessionLocal()
        try:
            stu = StudentRepository.get_by_id(db, self.student_pk)
            if not stu:
                QMessageBox.warning(self, "Not Found", "Student record could not be loaded.")
                return

            did = stu.digital_id_code or generate_digital_id(stu.student_id, stu.admission_date)
            qr_payload = stu.qr_payload or build_qr_payload(
                stu.student_id, stu.admission_number, did, getattr(stu, "public_id", None)
            )
            self.qr_widget.set_payload(qr_payload)

            if stu.photo_path and Path(stu.photo_path).exists():
                pix = QPixmap(stu.photo_path)
                if not pix.isNull():
                    self.photo_lbl.setPixmap(pix.scaled(84, 102, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.photo_lbl.setText("NO PHOTO")

            c_str = stu.school_class.name if stu.school_class else "-"
            s_str = stu.section.name if stu.section else "-"
            ay_str = stu.academic_year.name if stu.academic_year else "-"
            self.name_lbl.setText(stu.full_name)
            self.meta_lbl.setText(
                f"ID: {stu.student_id}  |  Adm #: {stu.admission_number}  |  Digital ID: {did}  |  "
                f"Class: {c_str} ({s_str})  |  Roll: {stu.roll_number}  |  Session: {ay_str}"
            )
            tags = stu.get_tag_names()
            self.status_tags_lbl.setText(
                f"Status: {StudentStatus.LABELS.get(stu.status, stu.status.title())}   |   "
                f"Tags: {', '.join(tags) if tags else 'None'}"
            )
            if stu.status in (StudentStatus.ARCHIVED, StudentStatus.INACTIVE, StudentStatus.WITHDRAWN, StudentStatus.TRANSFERRED) or stu.is_deleted:
                self.btn_archive_restore.setText("Restore Active")
            else:
                self.btn_archive_restore.setText("Archive")

            # Timeline
            timeline = StudentService.get_student_timeline(db, stu.id)
            self.timeline_table.setRowCount(len(timeline))
            for idx, ev in enumerate(timeline):
                self.timeline_table.setItem(idx, 0, QTableWidgetItem(ev["timestamp"].strftime("%Y-%m-%d %H:%M")))
                self.timeline_table.setItem(idx, 1, QTableWidgetItem(ev["category"]))
                self.timeline_table.setItem(idx, 2, QTableWidgetItem(ev["title"]))
                self.timeline_table.setItem(idx, 3, QTableWidgetItem(ev["details"]))
                self.timeline_table.setItem(idx, 4, QTableWidgetItem(ev["actor"]))

            # Guardians
            links = list(stu.guardian_links)
            self.guardians_table.setRowCount(len(links))
            for idx, lk in enumerate(links):
                g = lk.guardian
                self.guardians_table.setItem(idx, 0, QTableWidgetItem(str(lk.priority_order)))
                self.guardians_table.setItem(idx, 1, QTableWidgetItem(g.guardian_name if g else "-"))
                self.guardians_table.setItem(idx, 2, QTableWidgetItem(lk.relationship_type))
                self.guardians_table.setItem(idx, 3, QTableWidgetItem(g.guardian_phone if g else "-"))
                self.guardians_table.setItem(idx, 4, QTableWidgetItem((g.guardian_email or "-") if g else "-"))
                self.guardians_table.setItem(idx, 5, QTableWidgetItem("Yes" if lk.is_primary else "No"))
                flags = []
                if lk.can_pickup:
                    flags.append("Pickup")
                if lk.is_emergency_contact:
                    flags.append("Emergency")
                if lk.is_financial_payer:
                    flags.append("Fee Payer")
                self.guardians_table.setItem(idx, 6, QTableWidgetItem(", ".join(flags)))

            # Family Links
            fam_links = list(stu.family_links)
            self.family_table.setRowCount(len(fam_links))
            for idx, fl in enumerate(fam_links):
                rel_stu = fl.related_student
                self.family_table.setItem(idx, 0, QTableWidgetItem(rel_stu.student_id if rel_stu else "-"))
                self.family_table.setItem(idx, 1, QTableWidgetItem(rel_stu.full_name if rel_stu else "-"))
                self.family_table.setItem(idx, 2, QTableWidgetItem(rel_stu.school_class.name if rel_stu and rel_stu.school_class else "-"))
                self.family_table.setItem(idx, 3, QTableWidgetItem(fl.relation_type))

            # Admission History
            adm_rows = list(stu.admission_history)
            self.admission_hist_table.setRowCount(len(adm_rows))
            for idx, a in enumerate(adm_rows):
                self.admission_hist_table.setItem(idx, 0, QTableWidgetItem(str(a.admission_date)))
                self.admission_hist_table.setItem(idx, 1, QTableWidgetItem(a.admission_number))
                self.admission_hist_table.setItem(idx, 2, QTableWidgetItem(a.admission_type))
                cs = f"{a.admitted_class.name if a.admitted_class else '-'} / {a.academic_year.name if a.academic_year else '-'}"
                self.admission_hist_table.setItem(idx, 3, QTableWidgetItem(cs))
                self.admission_hist_table.setItem(idx, 4, QTableWidgetItem(a.remarks or "-"))

            # Academic History
            acad_rows = list(stu.academic_history)
            self.academic_hist_table.setRowCount(len(acad_rows))
            for idx, ac in enumerate(acad_rows):
                self.academic_hist_table.setItem(idx, 0, QTableWidgetItem(ac.academic_year.name if ac.academic_year else "-"))
                self.academic_hist_table.setItem(
                    idx,
                    1,
                    QTableWidgetItem(f"{ac.school_class.name if ac.school_class else '-'} ({ac.section.name if ac.section else '-'})"),
                )
                self.academic_hist_table.setItem(idx, 2, QTableWidgetItem(str(ac.roll_number or "-")))
                self.academic_hist_table.setItem(idx, 3, QTableWidgetItem(ac.result_status))
                self.academic_hist_table.setItem(idx, 4, QTableWidgetItem(ac.remarks or "-"))

            # Previous Schools
            ps_rows = list(stu.previous_schools)
            self.prev_schools_table.setRowCount(len(ps_rows))
            for idx, ps in enumerate(ps_rows):
                self.prev_schools_table.setItem(idx, 0, QTableWidgetItem(ps.school_name))
                self.prev_schools_table.setItem(idx, 1, QTableWidgetItem(ps.board_or_curriculum or "-"))
                self.prev_schools_table.setItem(idx, 2, QTableWidgetItem(ps.last_class_attended or "-"))
                self.prev_schools_table.setItem(idx, 3, QTableWidgetItem(ps.tc_number or "-"))
                self.prev_schools_table.setItem(idx, 4, QTableWidgetItem(ps.reason_for_leaving or "-"))

            # Status History
            st_rows = list(stu.status_history)
            self.status_hist_table.setRowCount(len(st_rows))
            for idx, sh in enumerate(st_rows):
                self.status_hist_table.setItem(idx, 0, QTableWidgetItem(str(sh.effective_date)))
                self.status_hist_table.setItem(idx, 1, QTableWidgetItem(f"{sh.from_status or 'New'} -> {sh.to_status}"))
                ref = sh.destination_school or sh.reference_no or "-"
                self.status_hist_table.setItem(idx, 2, QTableWidgetItem(ref))
                self.status_hist_table.setItem(idx, 3, QTableWidgetItem(sh.reason or "-"))
                self.status_hist_table.setItem(idx, 4, QTableWidgetItem(sh.changed_by))

            # Documents
            docs = list(stu.documents)
            self.docs_table.setRowCount(len(docs))
            for idx, d in enumerate(docs):
                type_item = QTableWidgetItem(d.document_type)
                type_item.setData(Qt.UserRole, d.id)
                self.docs_table.setItem(idx, 0, type_item)
                self.docs_table.setItem(idx, 1, QTableWidgetItem(d.title))
                self.docs_table.setItem(idx, 2, QTableWidgetItem(d.file_name or "-"))
                self.docs_table.setItem(idx, 3, QTableWidgetItem("Verified" if d.is_verified else "Pending"))
                self.docs_table.setItem(idx, 4, QTableWidgetItem(d.uploaded_by))
                self.docs_table.setItem(idx, 5, QTableWidgetItem(d.file_path or "-"))

            # Medical
            mp = stu.medical_profile
            self.med_blood.setText((mp.blood_group if mp else None) or stu.blood_group or "")
            self.med_allergies.setText((mp.allergies if mp else None) or stu.medical_notes or "")
            self.med_conditions.setText((mp.chronic_conditions if mp else None) or "")
            self.med_medications.setText((mp.medications if mp else None) or "")
            self.med_immunization.setText((mp.immunization_status if mp else None) or "")
            self.med_physician.setText((mp.physician_name if mp else None) or "")
            self.med_physician_phone.setText((mp.physician_phone if mp else None) or "")
            self.med_protocol.setText((mp.emergency_protocol if mp else None) or "")

            # Emergency Contacts
            ecs = list(stu.emergency_contacts)
            self.emergency_table.setRowCount(len(ecs))
            for idx, ec in enumerate(ecs):
                self.emergency_table.setItem(idx, 0, QTableWidgetItem(str(ec.priority_order)))
                self.emergency_table.setItem(idx, 1, QTableWidgetItem(ec.contact_name))
                self.emergency_table.setItem(idx, 2, QTableWidgetItem(ec.relationship_label))
                self.emergency_table.setItem(idx, 3, QTableWidgetItem(ec.primary_phone))
                self.emergency_table.setItem(idx, 4, QTableWidgetItem("Yes" if ec.can_pickup else "No"))

            # Tags, Notes, Custom Fields
            self.tags_edit.setText(", ".join(tags))
            notes = list(stu.notes)
            self.notes_table.setRowCount(len(notes))
            for idx, n in enumerate(notes):
                self.notes_table.setItem(idx, 0, QTableWidgetItem("Pinned" if n.is_pinned else ""))
                self.notes_table.setItem(idx, 1, QTableWidgetItem(n.category))
                self.notes_table.setItem(idx, 2, QTableWidgetItem(n.title))
                self.notes_table.setItem(idx, 3, QTableWidgetItem(n.content))
                self.notes_table.setItem(idx, 4, QTableWidgetItem(n.author_username))

            cf = stu.get_custom_fields()
            self.custom_fields_table.setRowCount(len(cf))
            for idx, (k, v) in enumerate(cf.items()):
                self.custom_fields_table.setItem(idx, 0, QTableWidgetItem(str(k)))
                self.custom_fields_table.setItem(idx, 1, QTableWidgetItem(str(v)))
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Interactive Actions
    # ------------------------------------------------------------------
    def _edit_profile(self):
        diag = StudentFormDialog(self, student_id=self.student_pk, actor=self.actor)
        if diag.exec() == QDialog.Accepted:
            self.modified = True
            self._reload_all()

    def _open_id_card(self):
        StudentIDCardDialog(self, student_pk=self.student_pk).exec()

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Student CRM Dossier PDF", f"Student_CRM_Dossier_{self.student_pk}.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        db = SessionLocal()
        try:
            stu = StudentRepository.get_by_id(db, self.student_pk)
            school = db.query(SchoolSetting).first()
            if stu:
                StudentProfilePDFGenerator.generate(stu, school, path)
                QMessageBox.information(self, "Export Completed", f"Saved Student CRM Dossier:\n{path}")
        finally:
            db.close()

    def _open_promote(self):
        diag = StudentPromoteDialog(self, actor=self.actor)
        if diag.exec() == QDialog.Accepted:
            self.modified = True
            self._reload_all()

    def _open_lifecycle(self, action: str):
        diag = StudentLifecycleDialog(
            self,
            student_pk=self.student_pk,
            student_name=self.name_lbl.text(),
            action=action,
            actor=self.actor,
        )
        if diag.exec() == QDialog.Accepted:
            self.modified = True
            self._reload_all()

    def _toggle_archive_restore(self):
        action = "restore" if self.btn_archive_restore.text() == "Restore Active" else "archive"
        self._open_lifecycle(action)

    def _add_guardian_prompt(self):
        name, ok = QInputDialog.getText(self, "Add Guardian", "Guardian Full Name:")
        if not ok or not name.strip():
            return
        rel, ok = QInputDialog.getText(self, "Relationship", "Relationship (Father/Mother/Uncle/Legal Guardian):", text="Mother")
        if not ok:
            return
        phone, ok = QInputDialog.getText(self, "Guardian Phone", "Phone Number:")
        if not ok or not phone.strip():
            return
        db = SessionLocal()
        try:
            success, _link, msg = StudentService.add_guardian(
                db,
                self.student_pk,
                {"guardian_name": name.strip(), "guardian_phone": phone.strip(), "relation": rel.strip() or "Guardian"},
                relationship_type=rel.strip() or "Guardian",
                actor=self.actor,
            )
            if success:
                self.modified = True
                self._reload_all()
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()

    def _link_family_prompt(self):
        sid_text, ok = QInputDialog.getText(self, "Link Sibling / Relative", "Enter Related Student ID (e.g. STU-2025-0002):")
        if not ok or not sid_text.strip():
            return
        rel_type, ok = QInputDialog.getText(self, "Relationship", "Relation Type (Sibling / Twin / Cousin):", text="Sibling")
        if not ok:
            return
        db = SessionLocal()
        try:
            related = StudentRepository.get_by_student_id(db, sid_text.strip())
            if not related:
                QMessageBox.warning(self, "Not Found", f"No student found with Student ID '{sid_text.strip()}'.")
                return
            success, _rel, msg = StudentService.link_family_member(
                db, self.student_pk, related.id, relation_type=rel_type.strip() or "Sibling", actor=self.actor
            )
            if success:
                self.modified = True
                self._reload_all()
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()

    def _add_previous_school_prompt(self):
        school_name, ok = QInputDialog.getText(self, "Previous School", "Previous School Name:")
        if not ok or not school_name.strip():
            return
        last_cls, ok = QInputDialog.getText(self, "Last Class", "Last Class Attended:")
        if not ok:
            return
        tc_no, _ = QInputDialog.getText(self, "TC Number", "Transfer Certificate Number (optional):")
        db = SessionLocal()
        try:
            success, _rec, msg = StudentService.add_previous_school(
                db,
                self.student_pk,
                {
                    "school_name": school_name.strip(),
                    "last_class_attended": last_cls.strip() or None,
                    "tc_number": tc_no.strip() or None,
                },
                actor=self.actor,
            )
            if success:
                self.modified = True
                self._reload_all()
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()

    def _upload_document_prompt(self):
        doc_types = ["Birth Certificate", "Transfer Certificate", "Marksheet", "Medical Report", "Photo", "Guardian ID", "Other"]
        dtype, ok = QInputDialog.getItem(self, "Document Type", "Select Document Category:", doc_types, 0, False)
        if not ok:
            return
        title, ok = QInputDialog.getText(self, "Document Title", "Title / Description:", text=dtype)
        if not ok or not title.strip():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Document File", "", "Documents (*.pdf *.png *.jpg *.jpeg *.docx *.xlsx);;All Files (*)"
        )
        if not file_path:
            return
        db = SessionLocal()
        try:
            success, _doc, msg = StudentService.add_document(
                db,
                self.student_pk,
                doc_type=dtype,
                title=title.strip(),
                source_file_path=file_path,
                copy_to_vault=True,
                actor=self.actor,
            )
            if success:
                self.modified = True
                self._reload_all()
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()

    def _verify_selected_document(self):
        row = self.docs_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Row", "Select a document row first.")
            return
        doc_id = self.docs_table.item(row, 0).data(Qt.UserRole)
        currently_verified = self.docs_table.item(row, 3).text() == "Verified"
        db = SessionLocal()
        try:
            ok, msg = StudentService.verify_document(db, doc_id, verified=not currently_verified, actor=self.actor)
            if ok:
                self.modified = True
                self._reload_all()
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()

    def _save_medical_profile(self):
        db = SessionLocal()
        try:
            ok, _mp, msg = StudentService.upsert_medical_profile(
                db,
                self.student_pk,
                {
                    "blood_group": self.med_blood.text().strip() or None,
                    "allergies": self.med_allergies.text().strip() or None,
                    "chronic_conditions": self.med_conditions.text().strip() or None,
                    "medications": self.med_medications.text().strip() or None,
                    "immunization_status": self.med_immunization.text().strip() or None,
                    "physician_name": self.med_physician.text().strip() or None,
                    "physician_phone": self.med_physician_phone.text().strip() or None,
                    "emergency_protocol": self.med_protocol.text().strip() or None,
                },
                actor=self.actor,
            )
            if ok:
                self.modified = True
                QMessageBox.information(self, "Saved", msg)
                self._reload_all()
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()

    def _add_emergency_contact_prompt(self):
        name, ok = QInputDialog.getText(self, "Emergency Contact", "Contact Full Name:")
        if not ok or not name.strip():
            return
        rel, ok = QInputDialog.getText(self, "Relationship", "Relationship:", text="Relative")
        if not ok:
            return
        phone, ok = QInputDialog.getText(self, "Primary Phone", "Emergency Phone Number:")
        if not ok or not phone.strip():
            return
        db = SessionLocal()
        try:
            ok, _ec, msg = StudentService.add_emergency_contact(
                db,
                self.student_pk,
                {
                    "contact_name": name.strip(),
                    "relationship_label": rel.strip() or "Relative",
                    "primary_phone": phone.strip(),
                    "can_pickup": True,
                },
                actor=self.actor,
            )
            if ok:
                self.modified = True
                self._reload_all()
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()

    def _save_tags(self):
        tag_list = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        db = SessionLocal()
        try:
            ok, _applied, msg = StudentService.set_tags(db, self.student_pk, tag_list, actor=self.actor)
            if ok:
                self.modified = True
                QMessageBox.information(self, "Tags Saved", msg)
                self._reload_all()
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()

    def _add_note(self):
        title = self.note_title.text().strip()
        content = self.note_content.text().strip()
        if not title or not content:
            QMessageBox.warning(self, "Validation Error", "Enter both note title and content.")
            return
        db = SessionLocal()
        try:
            ok, _n, msg = StudentService.add_note(
                db,
                self.student_pk,
                title=title,
                content=content,
                category=self.note_cat.currentText(),
                is_pinned=self.note_pin.isChecked(),
                actor=self.actor,
            )
            if ok:
                self.modified = True
                self.note_title.clear()
                self.note_content.clear()
                self.note_pin.setChecked(False)
                self._reload_all()
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()

    def _add_custom_field_row(self):
        row = self.custom_fields_table.rowCount()
        self.custom_fields_table.insertRow(row)
        self.custom_fields_table.setItem(row, 0, QTableWidgetItem(""))
        self.custom_fields_table.setItem(row, 1, QTableWidgetItem(""))

    def _save_custom_fields(self):
        fields: Dict[str, str] = {}
        for r in range(self.custom_fields_table.rowCount()):
            k_item = self.custom_fields_table.item(r, 0)
            v_item = self.custom_fields_table.item(r, 1)
            k = k_item.text().strip() if k_item else ""
            v = v_item.text().strip() if v_item else ""
            if k:
                fields[k] = v
        db = SessionLocal()
        try:
            ok, _saved, msg = StudentService.update_custom_fields(db, self.student_pk, fields, actor=self.actor)
            if ok:
                self.modified = True
                QMessageBox.information(self, "Saved", msg)
                self._reload_all()
            else:
                QMessageBox.warning(self, "Error", msg)
        finally:
            db.close()

    def _close_dialog(self):
        if self.modified:
            self.accept()
        else:
            self.reject()
