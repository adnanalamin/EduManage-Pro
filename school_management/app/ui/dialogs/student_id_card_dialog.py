"""
EduManage Pro - Student ID Card Preview & Print Dialog (PySide6)
Displays graphical preview of CR80 Student ID card with direct PDF export and printing.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from app.database.connection import SessionLocal
from app.models.student import Student
from app.models.school import SchoolSetting
from app.reports.id_card_generator import StudentIDCardGenerator


class StudentIDCardDialog(QDialog):
    def __init__(self, parent=None, student_pk: int = 0):
        super().__init__(parent)
        self.student_pk = student_pk
        self.setWindowTitle("EduManage Pro — Student ID Card Preview")
        self.setFixedSize(480, 400)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Digital Student Identity Card (CR80 Standard)")
        header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        header.setStyleSheet("color: #3b82f6;")
        layout.addWidget(header)

        # ID Card Graphical Container
        self.card_frame = QFrame()
        self.card_frame.setStyleSheet(
            "background-color: #ffffff; border: 2px solid #cbd5e1; border-radius: 12px; overflow: hidden;"
        )
        self.card_frame.setFixedHeight(220)

        card_vbox = QVBoxLayout(self.card_frame)
        card_vbox.setContentsMargins(0, 0, 0, 0)
        card_vbox.setSpacing(0)

        # Blue School Header Bar
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #1e3a8a; padding: 6px;")
        top_vbox = QVBoxLayout(top_bar)
        top_vbox.setContentsMargins(8, 6, 8, 6)
        top_vbox.setSpacing(1)

        self.school_title_lbl = QLabel("Ideal Model High School & College")
        self.school_title_lbl.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
        self.school_title_lbl.setAlignment(Qt.AlignCenter)

        sub_tag = QLabel("STUDENT IDENTITY CARD")
        sub_tag.setStyleSheet("color: #93c5fd; font-size: 9px; font-weight: bold;")
        sub_tag.setAlignment(Qt.AlignCenter)

        top_vbox.addWidget(self.school_title_lbl)
        top_vbox.addWidget(sub_tag)
        card_vbox.addWidget(top_bar)

        # Body Row (Photo & Info)
        body_row = QHBoxLayout()
        body_row.setContentsMargins(16, 12, 16, 12)
        body_row.setSpacing(16)

        # Photo Box
        photo_box = QFrame()
        photo_box.setFixedSize(70, 85)
        photo_box.setStyleSheet("background-color: #f1f5f9; border: 1px solid #94a3b8; border-radius: 4px;")
        photo_layout = QVBoxLayout(photo_box)
        p_lbl = QLabel("PHOTO")
        p_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        p_lbl.setAlignment(Qt.AlignCenter)
        photo_layout.addWidget(p_lbl)
        body_row.addWidget(photo_box)

        # Details Column
        details_col = QVBoxLayout()
        details_col.setSpacing(3)

        self.name_lbl = QLabel("Student Full Name")
        self.name_lbl.setStyleSheet("color: #0f172a; font-size: 13px; font-weight: bold;")

        self.id_lbl = QLabel("ID: STU-2024-0001")
        self.id_lbl.setStyleSheet("color: #334155; font-size: 11px;")

        self.class_lbl = QLabel("Class: 10 (A)  |  Roll: 1")
        self.class_lbl.setStyleSheet("color: #334155; font-size: 11px;")

        self.blood_lbl = QLabel("Blood Group: B+")
        self.blood_lbl.setStyleSheet("color: #dc2626; font-size: 11px; font-weight: bold;")

        self.emergency_lbl = QLabel("Emergency: +880 1712-345678")
        self.emergency_lbl.setStyleSheet("color: #475569; font-size: 10px;")

        details_col.addWidget(self.name_lbl)
        details_col.addWidget(self.id_lbl)
        details_col.addWidget(self.class_lbl)
        details_col.addWidget(self.blood_lbl)
        details_col.addWidget(self.emergency_lbl)
        details_col.addStretch()

        body_row.addLayout(details_col)
        card_vbox.addLayout(body_row)

        # Bottom Bar
        bot_bar = QFrame()
        bot_bar.setStyleSheet("background-color: #0f172a; padding: 4px 12px;")
        bot_layout = QHBoxLayout(bot_bar)
        bot_layout.setContentsMargins(10, 2, 10, 2)
        p_text = QLabel("Authorized Institutional Card")
        p_text.setStyleSheet("color: #ffffff; font-size: 9px;")
        sig_text = QLabel("Principal Signature")
        sig_text.setStyleSheet("color: #94a3b8; font-size: 9px;")
        bot_layout.addWidget(p_text)
        bot_layout.addStretch()
        bot_layout.addWidget(sig_text)
        card_vbox.addWidget(bot_bar)

        layout.addWidget(self.card_frame)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)

        self.btn_export_pdf = QPushButton("🖨️ Export Printable PDF")
        self.btn_export_pdf.setStyleSheet("background-color: #2563eb; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        self.btn_export_pdf.clicked.connect(self._export_pdf)

        btn_box.addWidget(btn_close)
        btn_box.addWidget(self.btn_export_pdf)
        layout.addLayout(btn_box)

    def _load_data(self):
        db = SessionLocal()
        try:
            stu = db.query(Student).filter_by(id=self.student_pk).first()
            school = db.query(SchoolSetting).first()
            if stu:
                self.name_lbl.setText(stu.full_name)
                self.id_lbl.setText(f"ID: {stu.student_id}")
                c_name = stu.school_class.name if stu.school_class else "Class 10"
                s_name = stu.section.name if stu.section else "A"
                self.class_lbl.setText(f"Class: {c_name} ({s_name})  |  Roll: {stu.roll_number}")
                self.blood_lbl.setText(f"Blood Group: {stu.blood_group or 'N/A'}")
                e_phone = stu.guardian.guardian_phone if stu.guardian else stu.emergency_contact or "+880 1700-000000"
                self.emergency_lbl.setText(f"Emergency: {e_phone}")
            if school:
                self.school_title_lbl.setText(school.school_name)
        finally:
            db.close()

    def _export_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Student ID Card PDF", f"StudentID_{self.student_pk}.pdf", "PDF Files (*.pdf)"
        )
        if file_path:
            db = SessionLocal()
            try:
                stu = db.query(Student).filter_by(id=self.student_pk).first()
                school = db.query(SchoolSetting).first()
                if stu:
                    StudentIDCardGenerator.generate_single_card(stu, school, file_path)
                    QMessageBox.information(self, "Export Success", f"ID Card PDF generated successfully at:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to generate ID card PDF: {e}")
            finally:
                db.close()
