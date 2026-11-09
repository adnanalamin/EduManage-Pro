"""
EduManage Pro - Teacher & Staff ID Card Dialog (PySide6)
Graphical preview and printable ReportLab PDF export for Employee ID badges.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from app.database.connection import SessionLocal
from app.models.staff import Teacher, Staff
from app.models.school import SchoolSetting
from app.reports.teacher_id_card_generator import StaffIDCardGenerator


class TeacherIDCardDialog(QDialog):
    def __init__(self, parent=None, entity_id: int = 0, is_teacher: bool = True):
        super().__init__(parent)
        self.entity_pk = entity_id
        self.is_teacher = is_teacher
        self.setWindowTitle("EduManage Pro — " + ("Faculty ID Badge" if is_teacher else "Staff ID Badge"))
        self.setFixedSize(480, 400)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Employee Identity Badge (CR80 Standard)")
        header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        header.setStyleSheet("color: #10b981;" if self.is_teacher else "color: #6366f1;")
        layout.addWidget(header)

        # Card Graphical Container
        self.card_frame = QFrame()
        self.card_frame.setStyleSheet(
            "background-color: #ffffff; border: 2px solid #cbd5e1; border-radius: 12px; overflow: hidden;"
        )
        self.card_frame.setFixedHeight(220)

        card_vbox = QVBoxLayout(self.card_frame)
        card_vbox.setContentsMargins(0, 0, 0, 0)
        card_vbox.setSpacing(0)

        # Header Bar
        top_bar = QFrame()
        top_bar.setStyleSheet(
            f"background-color: {'#065f46' if self.is_teacher else '#3730a3'}; padding: 6px;"
        )
        top_vbox = QVBoxLayout(top_bar)
        top_vbox.setContentsMargins(8, 6, 8, 6)
        top_vbox.setSpacing(1)

        self.school_title_lbl = QLabel("Ideal Model High School & College")
        self.school_title_lbl.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
        self.school_title_lbl.setAlignment(Qt.AlignCenter)

        sub_tag = QLabel("FACULTY IDENTITY BADGE" if self.is_teacher else "STAFF IDENTITY BADGE")
        sub_tag.setStyleSheet("color: #a7f3d0;" if self.is_teacher else "color: #c7d2fe;")
        sub_tag.setStyleSheet(sub_tag.styleSheet() + " font-size: 9px; font-weight: bold;")
        sub_tag.setAlignment(Qt.AlignCenter)

        top_vbox.addWidget(self.school_title_lbl)
        top_vbox.addWidget(sub_tag)
        card_vbox.addWidget(top_bar)

        # Body Row
        body_row = QHBoxLayout()
        body_row.setContentsMargins(16, 12, 16, 12)
        body_row.setSpacing(16)

        photo_box = QFrame()
        photo_box.setFixedSize(70, 85)
        photo_box.setStyleSheet("background-color: #f1f5f9; border: 1px solid #94a3b8; border-radius: 4px;")
        photo_layout = QVBoxLayout(photo_box)
        p_lbl = QLabel("PHOTO")
        p_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        p_lbl.setAlignment(Qt.AlignCenter)
        photo_layout.addWidget(p_lbl)
        body_row.addWidget(photo_box)

        details_col = QVBoxLayout()
        details_col.setSpacing(3)

        self.name_lbl = QLabel("Employee Full Name")
        self.name_lbl.setStyleSheet("color: #0f172a; font-size: 13px; font-weight: bold;")

        self.id_lbl = QLabel("ID: TCH-2024-0001 (EMP-1001)")
        self.id_lbl.setStyleSheet("color: #334155; font-size: 11px;")

        self.role_lbl = QLabel("Assistant Teacher — Physics")
        self.role_lbl.setStyleSheet("color: #059669; font-size: 11px; font-weight: bold;")

        self.dept_lbl = QLabel("Department: Science")
        self.dept_lbl.setStyleSheet("color: #334155; font-size: 11px;")

        self.phone_lbl = QLabel("Phone: +880 1711-000000")
        self.phone_lbl.setStyleSheet("color: #475569; font-size: 10px;")

        details_col.addWidget(self.name_lbl)
        details_col.addWidget(self.id_lbl)
        details_col.addWidget(self.role_lbl)
        details_col.addWidget(self.dept_lbl)
        details_col.addWidget(self.phone_lbl)
        details_col.addStretch()

        body_row.addLayout(details_col)
        card_vbox.addLayout(body_row)

        # Bottom Bar
        bot_bar = QFrame()
        bot_bar.setStyleSheet("background-color: #0f172a; padding: 4px 12px;")
        bot_layout = QHBoxLayout(bot_bar)
        bot_layout.setContentsMargins(10, 2, 10, 2)
        p_text = QLabel("Official Institutional Employee")
        p_text.setStyleSheet("color: #ffffff; font-size: 9px;")
        sig_text = QLabel("Principal Signature")
        sig_text.setStyleSheet("color: #94a3b8; font-size: 9px;")
        bot_layout.addWidget(p_text)
        bot_layout.addStretch()
        bot_layout.addWidget(sig_text)
        card_vbox.addWidget(bot_bar)

        layout.addWidget(self.card_frame)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)

        self.btn_export = QPushButton("🖨️ Export PDF Badge")
        self.btn_export.setStyleSheet("background-color: #2563eb; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        self.btn_export.clicked.connect(self._export_pdf)

        btn_box.addWidget(btn_close)
        btn_box.addWidget(self.btn_export)
        layout.addLayout(btn_box)

    def _load_data(self):
        db = SessionLocal()
        try:
            school = db.query(SchoolSetting).first()
            if school:
                self.school_title_lbl.setText(school.school_name)

            if self.is_teacher:
                t = db.query(Teacher).filter_by(id=self.entity_pk).first()
                if t:
                    self.name_lbl.setText(t.full_name)
                    self.id_lbl.setText(f"ID: {t.teacher_id} ({t.employee_id})")
                    self.role_lbl.setText(f"{t.designation} — {t.primary_subject}")
                    dept_name = t.department.name if t.department else "General"
                    self.dept_lbl.setText(f"Department: {dept_name}")
                    self.phone_lbl.setText(f"Phone: {t.phone}")
            else:
                s = db.query(Staff).filter_by(id=self.entity_pk).first()
                if s:
                    self.name_lbl.setText(s.full_name)
                    self.id_lbl.setText(f"ID: {s.staff_id} ({s.employee_id})")
                    self.role_lbl.setText(f"Position: {s.position} ({s.shift} Shift)")
                    dept_name = s.department.name if s.department else "Admin"
                    self.dept_lbl.setText(f"Department: {dept_name}")
                    self.phone_lbl.setText(f"Phone: {s.phone}")
        finally:
            db.close()

    def _export_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Employee ID Badge PDF", f"Badge_{self.entity_pk}.pdf", "PDF Files (*.pdf)"
        )
        if file_path:
            db = SessionLocal()
            try:
                school = db.query(SchoolSetting).first()
                if self.is_teacher:
                    t = db.query(Teacher).filter_by(id=self.entity_pk).first()
                    if t and school:
                        StaffIDCardGenerator.generate_teacher_card(t, school, file_path)
                else:
                    s = db.query(Staff).filter_by(id=self.entity_pk).first()
                    if s and school:
                        StaffIDCardGenerator.generate_staff_card(s, school, file_path)
                QMessageBox.information(self, "Export Success", f"ID Badge PDF created at:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to generate ID badge: {e}")
            finally:
                db.close()
