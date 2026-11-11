"""
EduManage Pro - Notice Form Dialog
Phase 13: PySide6 Modal for Creating & Editing School Notices & Circulars
"""

from typing import Optional
from datetime import date
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QTextEdit, QDateEdit, QCheckBox, QPushButton, QMessageBox
)
from PySide6.QtCore import QDate
from app.repositories.notice_repository import NoticeRepository


class NoticeFormDialog(QDialog):
    """Dialog to create or edit an official school notice / circular."""

    def __init__(self, parent=None, db_session=None, notice=None):
        super().__init__(parent)
        self.db = db_session
        self.notice = notice
        self.setWindowTitle("Edit Notice" if notice else "Publish New Notice / Circular")
        self.resize(520, 500)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Circular Title / Subject Heading")
        if self.notice:
            self.title_edit.setText(self.notice.title)
        form.addRow("Subject / Title:*", self.title_edit)

        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["Academic", "Exam", "Holiday", "Administrative", "Sports", "Fee", "Emergency"])
        if self.notice:
            self.cat_combo.setCurrentText(self.notice.category)
        form.addRow("Category:*", self.cat_combo)

        self.aud_combo = QComboBox()
        self.aud_combo.addItems(["All", "Students", "Teachers", "Parents", "Staff"])
        if self.notice:
            self.aud_combo.setCurrentText(self.notice.target_audience)
        form.addRow("Target Audience:*", self.aud_combo)

        self.prio_combo = QComboBox()
        self.prio_combo.addItems(["Normal", "Important", "Urgent"])
        if self.notice:
            self.prio_combo.setCurrentText(self.notice.priority)
        form.addRow("Priority Level:", self.prio_combo)

        self.pin_check = QCheckBox("Pin to top of bulletin board (Urgent Circular)")
        if self.notice:
            self.pin_check.setChecked(self.notice.is_pinned)
        form.addRow("", self.pin_check)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        if self.notice and self.notice.publish_date:
            d = self.notice.publish_date
            self.date_edit.setDate(QDate(d.year, d.month, d.day))
        else:
            self.date_edit.setDate(QDate.currentDate())
        form.addRow("Publish Date:", self.date_edit)

        self.expiry_edit = QDateEdit()
        self.expiry_edit.setCalendarPopup(True)
        if self.notice and self.notice.expiry_date:
            d = self.notice.expiry_date
            self.expiry_edit.setDate(QDate(d.year, d.month, d.day))
        else:
            self.expiry_edit.setDate(QDate.currentDate().addDays(30))
        form.addRow("Expiry Date:", self.expiry_edit)

        self.by_edit = QLineEdit()
        self.by_edit.setPlaceholderText("e.g., Principal Office, Exam Controller")
        self.by_edit.setText(self.notice.created_by if self.notice else "Principal Office")
        form.addRow("Issued By:", self.by_edit)

        self.att_edit = QLineEdit()
        self.att_edit.setPlaceholderText("Optional attachment name (e.g. Routine_2026.pdf)")
        if self.notice and self.notice.attachment_name:
            self.att_edit.setText(self.notice.attachment_name)
        form.addRow("Attachment:", self.att_edit)

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Official notice body text or directive...")
        if self.notice:
            self.content_edit.setPlainText(self.notice.content)
        form.addRow("Circular Content:*", self.content_edit)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Publish Notice")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _save(self):
        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText().strip()

        if not title:
            QMessageBox.warning(self, "Validation Error", "Title cannot be empty.")
            return

        if not content:
            QMessageBox.warning(self, "Validation Error", "Notice body content cannot be empty.")
            return

        p_qdate = self.date_edit.date()
        pub_dt = date(p_qdate.year(), p_qdate.month(), p_qdate.day())

        e_qdate = self.expiry_edit.date()
        exp_dt = date(e_qdate.year(), e_qdate.month(), e_qdate.day())

        try:
            if self.notice:
                NoticeRepository.update_notice(
                    self.db,
                    self.notice.id,
                    title=title,
                    content=content,
                    category=self.cat_combo.currentText(),
                    target_audience=self.aud_combo.currentText(),
                    priority=self.prio_combo.currentText(),
                    is_pinned=self.pin_check.isChecked(),
                    publish_date=pub_dt,
                    expiry_date=exp_dt,
                    created_by=self.by_edit.text().strip() or "Principal Office",
                    attachment_name=self.att_edit.text().strip() or None
                )
            else:
                NoticeRepository.create_notice(
                    self.db,
                    title=title,
                    content=content,
                    category=self.cat_combo.currentText(),
                    target_audience=self.aud_combo.currentText(),
                    priority=self.prio_combo.currentText(),
                    is_pinned=self.pin_check.isChecked(),
                    publish_date=pub_dt,
                    expiry_date=exp_dt,
                    created_by=self.by_edit.text().strip() or "Principal Office",
                    attachment_name=self.att_edit.text().strip() or None
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))
