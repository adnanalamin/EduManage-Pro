"""
EduManage Pro - Exam Schedule Dialog (PySide6)
Modal dialog to configure examination routines, timetables, room allocation, and marks distribution.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QComboBox, QDateEdit, QLineEdit, QDoubleSpinBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QDate
from datetime import date
from app.database.connection import SessionLocal
from app.models.academic import SchoolClass, Subject
from app.repositories.exam_repository import ExamRepository


class ExamScheduleDialog(QDialog):
    def __init__(self, parent=None, default_term_id=None):
        super().__init__(parent)
        self.setWindowTitle("Schedule Exam Routine & Room — EduManage Pro")
        self.setMinimumWidth(480)
        self.setModal(True)
        self.default_term_id = default_term_id

        self._build_ui()
        self._load_selectors()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Add Examination Routine Slot")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #3b82f6;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self.combo_term = QComboBox()
        form.addRow("Exam Term *:", self.combo_term)

        self.combo_class = QComboBox()
        self.combo_class.currentIndexChanged.connect(self._on_class_changed)
        form.addRow("Class *:", self.combo_class)

        self.combo_subject = QComboBox()
        form.addRow("Subject *:", self.combo_subject)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Exam Date *:", self.date_edit)

        time_box = QHBoxLayout()
        self.start_time_edit = QLineEdit("10:00 AM")
        self.end_time_edit = QLineEdit("01:00 PM")
        time_box.addWidget(self.start_time_edit)
        time_box.addWidget(QLabel("to"))
        time_box.addWidget(self.end_time_edit)
        form.addRow("Time Slot *:", time_box)

        self.room_edit = QLineEdit("Room 201")
        form.addRow("Exam Hall / Room:", self.room_edit)

        marks_box = QHBoxLayout()
        self.th_spin = QDoubleSpinBox()
        self.th_spin.setRange(0, 100)
        self.th_spin.setValue(70)
        self.mcq_spin = QDoubleSpinBox()
        self.mcq_spin.setRange(0, 50)
        self.mcq_spin.setValue(30)
        marks_box.addWidget(QLabel("Theory:"))
        marks_box.addWidget(self.th_spin)
        marks_box.addWidget(QLabel("MCQ:"))
        marks_box.addWidget(self.mcq_spin)
        form.addRow("Marks Distribution:", marks_box)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Schedule Slot")
        self.btn_save.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 6px 16px;")
        self.btn_save.clicked.connect(self._handle_save)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _load_selectors(self):
        db = SessionLocal()
        try:
            terms = ExamRepository.get_all_exam_terms(db)
            self.combo_term.clear()
            for t in terms:
                self.combo_term.addItem(f"{t.name} ({t.exam_code})", t.id)
            if self.default_term_id:
                idx = self.combo_term.findData(self.default_term_id)
                if idx >= 0:
                    self.combo_term.setCurrentIndex(idx)

            classes = db.query(SchoolClass).order_by(SchoolClass.numeric_order.asc()).all()
            self.combo_class.clear()
            for c in classes:
                self.combo_class.addItem(c.name, c.id)

            self._on_class_changed()
        finally:
            db.close()

    def _on_class_changed(self):
        cls_id = self.combo_class.currentData()
        if not cls_id:
            return
        db = SessionLocal()
        try:
            subjects = db.query(Subject).filter(Subject.class_id == cls_id).all()
            self.combo_subject.clear()
            for s in subjects:
                self.combo_subject.addItem(f"{s.name} ({s.code})", s.id)
        finally:
            db.close()

    def _handle_save(self):
        term_id = self.combo_term.currentData()
        class_id = self.combo_class.currentData()
        subject_id = self.combo_subject.currentData()

        if not term_id or not class_id or not subject_id:
            QMessageBox.warning(self, "Validation Error", "Please select term, class, and subject.")
            return

        qdate = self.date_edit.date()
        exam_date = date(qdate.year(), qdate.month(), qdate.day())

        db = SessionLocal()
        try:
            ExamRepository.create_or_update_schedule(db, {
                "exam_term_id": term_id,
                "class_id": class_id,
                "subject_id": subject_id,
                "exam_date": exam_date,
                "start_time": self.start_time_edit.text().strip(),
                "end_time": self.end_time_edit.text().strip(),
                "room_number": self.room_edit.text().strip() or "Main Hall",
                "full_marks": self.th_spin.value() + self.mcq_spin.value(),
                "pass_marks": 33.0,
                "theory_full": self.th_spin.value(),
                "mcq_full": self.mcq_spin.value()
            })
            QMessageBox.information(self, "Routine Saved", "Exam schedule slot successfully saved.")
            self.accept()
        finally:
            db.close()
