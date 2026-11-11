"""
EduManage Pro - Notice Board & Event Calendar Page
Phase 13: 3-Tab PySide6 GUI for Circulars, Academic Events & Official Letterheads
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QHeaderView, QMessageBox,
    QFileDialog, QFrame, QComboBox, QTextBrowser
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from app.repositories.notice_repository import NoticeRepository
from app.services.notice_service import NoticeService
from app.reports.notice_pdf import NoticeLetterheadGenerator
from app.reports.academic_calendar_pdf import AcademicCalendarPDFGenerator
from app.ui.dialogs.notice_form_dialog import NoticeFormDialog
from app.ui.dialogs.event_form_dialog import EventFormDialog


class NoticePage(QWidget):
    """Main PySide6 page for Notice Board, Circulars, and Academic Calendar Management."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header & Quick Actions
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Notice Board, Circulars & Academic Events")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        subtitle = QLabel("Official institutional directives, circular memos, academic calendar & holiday schedules")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        seed_btn = QPushButton("🌱 Seed Demo Notices & Events")
        seed_btn.setStyleSheet("background-color: #059669; color: white; padding: 6px 12px; font-weight: bold; border-radius: 6px;")
        seed_btn.clicked.connect(self._seed_data)
        header_layout.addWidget(seed_btn)

        main_layout.addLayout(header_layout)

        # KPI Stats Grid
        self.kpi_layout = QHBoxLayout()
        self._build_kpi_cards()
        main_layout.addLayout(self.kpi_layout)

        # 2. Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 8px; }
            QTabBar::tab { padding: 8px 16px; font-weight: 600; font-size: 12px; }
            QTabBar::tab:selected { background: #1E3A8A; color: white; border-top-left-radius: 6px; border-top-right-radius: 6px; }
        """)

        # Tab 1: Notice Board
        self.tab_notices = QWidget()
        self._init_notices_tab()
        self.tabs.addTab(self.tab_notices, "📋 Notice Board & Circulars")

        # Tab 2: Events & Calendar
        self.tab_events = QWidget()
        self._init_events_tab()
        self.tabs.addTab(self.tab_events, "📅 Academic Calendar & Holidays")

        # Tab 3: Official Circular Letterhead
        self.tab_preview = QWidget()
        self._init_preview_tab()
        self.tabs.addTab(self.tab_preview, "📄 Circular Letterhead Preview (PDF)")

        main_layout.addWidget(self.tabs)
        self.refresh_all()

    def _build_kpi_cards(self):
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        stats = NoticeRepository.get_notice_stats(self.db) if self.db else {}

        cards_data = [
            ("Total Circulars", str(stats.get("total_notices", 0)), "#1E3A8A"),
            ("Published Memos", str(stats.get("published_notices", 0)), "#0D9488"),
            ("Urgent Priority", str(stats.get("urgent_alerts", 0)), "#DC2626"),
            ("Upcoming Events", str(stats.get("upcoming_events", 0)), "#059669"),
            ("Official Holidays", str(stats.get("total_holidays", 0)), "#D97706")
        ]

        for label, val, color in cards_data:
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-left: 4px solid {color};
                    border-radius: 8px;
                    padding: 8px 12px;
                }}
            """)
            flayout = QVBoxLayout(frame)
            flayout.setContentsMargins(4, 4, 4, 4)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
            val_lbl = QLabel(val)
            val_lbl.setStyleSheet(f"color: {color}; font-size: 17px; font-weight: bold;")
            flayout.addWidget(lbl)
            flayout.addWidget(val_lbl)
            self.kpi_layout.addWidget(frame)

    # -------------------------------------------------------------
    # TAB 1: Notice Board
    # -------------------------------------------------------------
    def _init_notices_tab(self):
        layout = QVBoxLayout(self.tab_notices)
        layout.setContentsMargins(12, 12, 12, 12)

        btn_bar = QHBoxLayout()
        add_btn = QPushButton("➕ Publish New Circular")
        add_btn.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold;")
        add_btn.clicked.connect(self._add_notice)

        pdf_btn = QPushButton("📄 Print Selected Circular PDF")
        pdf_btn.clicked.connect(self._print_selected_notice)

        del_btn = QPushButton("🗑️ Archive / Delete")
        del_btn.clicked.connect(self._delete_notice)

        self.aud_filter = QComboBox()
        self.aud_filter.addItems(["All Audiences", "Students", "Teachers", "Parents", "Staff"])
        self.aud_filter.currentIndexChanged.connect(self._filter_notices)

        self.cat_filter = QComboBox()
        self.cat_filter.addItems(["All Categories", "Academic", "Exam", "Holiday", "Administrative", "Sports", "Fee"])
        self.cat_filter.currentIndexChanged.connect(self._filter_notices)

        btn_bar.addWidget(add_btn)
        btn_bar.addWidget(pdf_btn)
        btn_bar.addWidget(del_btn)
        btn_bar.addSpacing(16)
        btn_bar.addWidget(QLabel("Audience:"))
        btn_bar.addWidget(self.aud_filter)
        btn_bar.addWidget(QLabel("Category:"))
        btn_bar.addWidget(self.cat_filter)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self.notices_table = QTableWidget()
        self.notices_table.setColumnCount(8)
        self.notices_table.setHorizontalHeaderLabels([
            "ID", "Ref No", "Title / Subject", "Category", "Audience", "Priority", "Publish Date", "Status"
        ])
        self.notices_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.notices_table.setAlternatingRowColors(True)
        self.notices_table.itemSelectionChanged.connect(self._on_notice_selected)
        layout.addWidget(self.notices_table)

    def _add_notice(self):
        dlg = NoticeFormDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _delete_notice(self):
        row = self.notices_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Row", "Please select a notice to delete.")
            return

        notice_id = int(self.notices_table.item(row, 0).text())
        confirm = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this notice?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            NoticeRepository.delete_notice(self.db, notice_id)
            self.refresh_all()

    def _filter_notices(self):
        aud = self.aud_filter.currentText()
        cat = self.cat_filter.currentText()
        notices = NoticeRepository.get_all_notices(
            self.db,
            audience=None if aud == "All Audiences" else aud,
            category=None if cat == "All Categories" else cat
        )
        self.notices_table.setRowCount(len(notices))
        for r_idx, n in enumerate(notices):
            ref_str = f"📌 {n.reference_no}" if n.is_pinned else n.reference_no
            pub_str = n.publish_date.strftime("%Y-%m-%d") if n.publish_date else ""

            self.notices_table.setItem(r_idx, 0, QTableWidgetItem(str(n.id)))
            self.notices_table.setItem(r_idx, 1, QTableWidgetItem(ref_str))
            self.notices_table.setItem(r_idx, 2, QTableWidgetItem(n.title))
            self.notices_table.setItem(r_idx, 3, QTableWidgetItem(n.category))
            self.notices_table.setItem(r_idx, 4, QTableWidgetItem(n.target_audience))

            prio_item = QTableWidgetItem(n.priority)
            if n.priority == "Urgent":
                prio_item.setForeground(QColor("#DC2626"))
            elif n.priority == "Important":
                prio_item.setForeground(QColor("#D97706"))
            self.notices_table.setItem(r_idx, 5, prio_item)

            self.notices_table.setItem(r_idx, 6, QTableWidgetItem(pub_str))
            self.notices_table.setItem(r_idx, 7, QTableWidgetItem(n.status))

    def _print_selected_notice(self):
        row = self.notices_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Row", "Please select a circular row to print.")
            return

        notice_id = int(self.notices_table.item(row, 0).text())
        notice = NoticeRepository.get_notice_by_id(self.db, notice_id)
        from app.models.school import SchoolSetting
        school = self.db.query(SchoolSetting).first()

        path, _ = QFileDialog.getSaveFileName(self, "Save Circular Letterhead PDF", f"Circular_{notice.reference_no.replace('/', '_')}.pdf", "PDF Files (*.pdf)")
        if path:
            try:
                NoticeLetterheadGenerator.generate_notice_pdf(notice, school, path)
                QMessageBox.information(self, "PDF Complete", f"Official Circular Memo PDF generated at:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "PDF Error", str(e))

    # -------------------------------------------------------------
    # TAB 2: Academic Events & Calendar
    # -------------------------------------------------------------
    def _init_events_tab(self):
        layout = QVBoxLayout(self.tab_events)
        layout.setContentsMargins(12, 12, 12, 12)

        btn_bar = QHBoxLayout()
        add_event_btn = QPushButton("➕ Schedule Event")
        add_event_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        add_event_btn.clicked.connect(self._add_event)

        excel_btn = QPushButton("📊 Export Calendar (.xlsx)")
        excel_btn.clicked.connect(self._export_events_excel)

        pdf_cal_btn = QPushButton("📑 Print Academic Calendar PDF")
        pdf_cal_btn.clicked.connect(self._print_academic_calendar)

        del_event_btn = QPushButton("🗑️ Delete Event")
        del_event_btn.clicked.connect(self._delete_event)

        btn_bar.addWidget(add_event_btn)
        btn_bar.addWidget(excel_btn)
        btn_bar.addWidget(pdf_cal_btn)
        btn_bar.addWidget(del_event_btn)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self.events_table = QTableWidget()
        self.events_table.setColumnCount(8)
        self.events_table.setHorizontalHeaderLabels([
            "ID", "Event Title", "Category", "Start Date", "End Date", "Timing", "Venue", "Holiday?"
        ])
        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.events_table.setAlternatingRowColors(True)
        layout.addWidget(self.events_table)

    def _add_event(self):
        dlg = EventFormDialog(self, self.db)
        if dlg.exec():
            self.refresh_all()

    def _delete_event(self):
        row = self.events_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Row", "Please select an event to delete.")
            return

        ev_id = int(self.events_table.item(row, 0).text())
        confirm = QMessageBox.question(self, "Confirm Delete", "Delete this academic event?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            NoticeRepository.delete_event(self.db, ev_id)
            self.refresh_all()

    def _export_events_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Academic Calendar", "Academic_Calendar_2026.xlsx", "Excel Files (*.xlsx)")
        if path:
            try:
                NoticeService.export_events_excel(self.db, path)
                QMessageBox.information(self, "Export Complete", f"Academic calendar exported to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def _print_academic_calendar(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Academic Calendar PDF", "Academic_Calendar_2026.pdf", "PDF Files (*.pdf)")
        if path:
            try:
                from app.models.school import SchoolSetting
                school = self.db.query(SchoolSetting).first()
                events = NoticeRepository.get_all_events(self.db)
                AcademicCalendarPDFGenerator.generate_calendar_pdf(events, school, path)
                QMessageBox.information(self, "Calendar PDF Generated", f"Annual Academic Calendar PDF generated at:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    # -------------------------------------------------------------
    # TAB 3: Circular Letterhead Preview
    # -------------------------------------------------------------
    def _init_preview_tab(self):
        layout = QVBoxLayout(self.tab_preview)
        layout.setContentsMargins(12, 12, 12, 12)

        self.preview_browser = QTextBrowser()
        self.preview_browser.setStyleSheet("background: #F8FAFC; color: #0F172A; padding: 16px; border: 1px solid #CBD5E1; border-radius: 8px;")
        layout.addWidget(self.preview_browser)

    def _on_notice_selected(self):
        row = self.notices_table.currentRow()
        if row >= 0:
            notice_id = int(self.notices_table.item(row, 0).text())
            notice = NoticeRepository.get_notice_by_id(self.db, notice_id)
            if notice:
                html = f"""
                <div style="font-family: Arial, sans-serif; max-width: 650px; margin: auto;">
                    <div style="text-align: center; border-bottom: 2px solid #1E3A8A; padding-bottom: 8px;">
                        <h2 style="color: #1E3A8A; margin: 0;">IDEAL MODEL HIGH SCHOOL & COLLEGE</h2>
                        <p style="font-size: 11px; color: #475569; margin: 2px 0;">Official Institutional Circular & Executive Bulletin</p>
                    </div>
                    <table style="width: 100%; font-size: 11px; margin: 12px 0; background: #E2E8F0; padding: 6px;">
                        <tr>
                            <td><strong>Memo Ref:</strong> {notice.reference_no}</td>
                            <td style="text-align: right;"><strong>Date:</strong> {notice.publish_date}</td>
                        </tr>
                        <tr>
                            <td><strong>Audience:</strong> {notice.target_audience}</td>
                            <td style="text-align: right;"><strong>Priority:</strong> {notice.priority}</td>
                        </tr>
                    </table>
                    <h3 style="color: #0F172A; text-decoration: underline; margin-top: 14px;">SUBJECT: {notice.title}</h3>
                    <p style="font-size: 12px; line-height: 1.6; color: #1E293B; white-space: pre-wrap;">{notice.content}</p>
                    <div style="margin-top: 40px; text-align: right; font-size: 11px;">
                        <p>___________________________<br/><strong>Prof. Dr. Mohammad Rafiqul Islam</strong><br/>Principal & Head of Institution</p>
                    </div>
                </div>
                """
                self.preview_browser.setHtml(html)

    # -------------------------------------------------------------
    # Refresh & Seeder
    # -------------------------------------------------------------
    def _seed_data(self):
        try:
            res = NoticeService.seed_default_notices_and_events(self.db)
            QMessageBox.information(self, "Seed Successful", res.get("message", "Notices seeded."))
            self.refresh_all()
        except Exception as e:
            QMessageBox.critical(self, "Seed Error", str(e))

    def refresh_all(self):
        self._build_kpi_cards()
        self._filter_notices()

        # Events
        events = NoticeRepository.get_all_events(self.db)
        self.events_table.setRowCount(len(events))
        for r_idx, ev in enumerate(events):
            s_str = ev.start_date.strftime("%Y-%m-%d") if ev.start_date else ""
            e_str = ev.end_date.strftime("%Y-%m-%d") if ev.end_date else ""
            timing = f"{ev.start_time or ''} - {ev.end_time or ''}".strip(" -") or "All Day"

            self.events_table.setItem(r_idx, 0, QTableWidgetItem(str(ev.id)))
            self.events_table.setItem(r_idx, 1, QTableWidgetItem(ev.event_title))
            self.events_table.setItem(r_idx, 2, QTableWidgetItem(ev.event_category))
            self.events_table.setItem(r_idx, 3, QTableWidgetItem(s_str))
            self.events_table.setItem(r_idx, 4, QTableWidgetItem(e_str))
            self.events_table.setItem(r_idx, 5, QTableWidgetItem(timing))
            self.events_table.setItem(r_idx, 6, QTableWidgetItem(ev.venue))

            hol_item = QTableWidgetItem("★ HOLIDAY" if ev.is_holiday else "Regular")
            if ev.is_holiday:
                hol_item.setForeground(QColor("#DC2626"))
            self.events_table.setItem(r_idx, 7, hol_item)
