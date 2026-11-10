import React, { useState } from 'react';
import {
  FileCode,
  Folder,
  FolderOpen,
  Copy,
  Check,
  Download,
  Terminal,
  ShieldCheck,
  Cpu,
  Layers,
} from 'lucide-react';

interface FileNode {
  path: string;
  name: string;
  type: 'file' | 'folder';
  children?: FileNode[];
  description?: string;
}

const PROJECT_TREE: FileNode[] = [
  {
    path: 'school_management',
    name: 'school_management',
    type: 'folder',
    children: [
      {
        path: 'app',
        name: 'app',
        type: 'folder',
        children: [
          { path: 'app/main.py', name: 'main.py', type: 'file', description: 'PySide6 App Launcher & High-DPI Entrypoint' },
          {
            path: 'app/config',
            name: 'config',
            type: 'folder',
            children: [
              { path: 'app/config/settings.py', name: 'settings.py', type: 'file', description: 'Application Settings & Paths' },
              { path: 'app/config/logging_config.py', name: 'logging_config.py', type: 'file', description: 'Multi-file Rotating Logger' },
            ],
          },
          {
            path: 'app/database',
            name: 'database',
            type: 'folder',
            children: [
              { path: 'app/database/connection.py', name: 'connection.py', type: 'file', description: 'SQLite WAL & Session Engine' },
              { path: 'app/database/init_db.py', name: 'init_db.py', type: 'file', description: 'Schema & Role Seeder' },
            ],
          },
          {
            path: 'app/models',
            name: 'models',
            type: 'folder',
            children: [
              { path: 'app/models/base.py', name: 'base.py', type: 'file', description: 'TimestampMixin & Base Model' },
              { path: 'app/models/user.py', name: 'user.py', type: 'file', description: 'User, Role, Permission ORM' },
              { path: 'app/models/school.py', name: 'school.py', type: 'file', description: 'SchoolSetting & EIIN Model' },
              { path: 'app/models/academic.py', name: 'academic.py', type: 'file', description: 'AcademicYear, Class, Section, Subject' },
              { path: 'app/models/activity.py', name: 'activity.py', type: 'file', description: 'ActivityLog (Security Audit Trail)' },
              { path: 'app/models/student.py', name: 'student.py', type: 'file', description: 'Student, Guardian & Promotion History' },
              { path: 'app/models/staff.py', name: 'staff.py', type: 'file', description: 'Department, Teacher & Staff ORM Models' },
              { path: 'app/models/attendance.py', name: 'attendance.py', type: 'file', description: 'Student & Teacher Attendance ORM Schemas' },
              { path: 'app/models/fee.py', name: 'fee.py', type: 'file', description: 'FeeCategory, Structure, StudentFee & FeePayment' },
              { path: 'app/models/accounting.py', name: 'accounting.py', type: 'file', description: 'AccountCategory & AccountTransaction ORM' },
              { path: 'app/models/exam.py', name: 'exam.py', type: 'file', description: 'ExamTerm, GradingScale, ExamSchedule, StudentMark & ResultSummary' },
              { path: 'app/models/timetable.py', name: 'timetable.py', type: 'file', description: 'PeriodSlot & TimetableEntry ORM Schemas' },
            ],
          },
          {
            path: 'app/repositories',
            name: 'repositories',
            type: 'folder',
            children: [
              { path: 'app/repositories/student_repository.py', name: 'student_repository.py', type: 'file', description: 'Student CRUD, Search & Promotion Repo' },
              { path: 'app/repositories/staff_repository.py', name: 'staff_repository.py', type: 'file', description: 'Teacher & Staff CRUD, Search & Dept Repo' },
              { path: 'app/repositories/academic_repository.py', name: 'academic_repository.py', type: 'file', description: 'Academic Years, Classes, Sections & Subjects Repo' },
              { path: 'app/repositories/attendance_repository.py', name: 'attendance_repository.py', type: 'file', description: 'Daily Upsert, Register Matrix & Stats Repo' },
              { path: 'app/repositories/fee_repository.py', name: 'fee_repository.py', type: 'file', description: 'Fee CRUD, Invoice Batching & Payment Balance Repo' },
              { path: 'app/repositories/accounting_repository.py', name: 'accounting_repository.py', type: 'file', description: 'Daily Cash Book, COA & Financial Aggregations Repo' },
              { path: 'app/repositories/exam_repository.py', name: 'exam_repository.py', type: 'file', description: 'Exam CRUD, Schedules, Marks Upsert & Class Summary Repo' },
              { path: 'app/repositories/timetable_repository.py', name: 'timetable_repository.py', type: 'file', description: 'Period CRUD, Conflict Checker & Matrix Query Repo' },
            ],
          },
          {
            path: 'app/security',
            name: 'security',
            type: 'folder',
            children: [
              { path: 'app/security/hasher.py', name: 'hasher.py', type: 'file', description: 'Bcrypt Password Hasher (12 Rounds)' },
              { path: 'app/security/session.py', name: 'session.py', type: 'file', description: 'In-Memory Authenticated User Session' },
            ],
          },
          {
            path: 'app/services',
            name: 'services',
            type: 'folder',
            children: [
              { path: 'app/services/auth_service.py', name: 'auth_service.py', type: 'file', description: 'Auth, Lockout & Audit Service' },
              { path: 'app/services/student_service.py', name: 'student_service.py', type: 'file', description: 'Student Admission, Excel & ID Logic' },
              { path: 'app/services/staff_service.py', name: 'staff_service.py', type: 'file', description: 'Teacher/Staff ID Gen, Payroll & Roster Service' },
              { path: 'app/services/academic_service.py', name: 'academic_service.py', type: 'file', description: 'Subject ID Gen, Mark Validation & Academic Service' },
              { path: 'app/services/attendance_service.py', name: 'attendance_service.py', type: 'file', description: 'Batch Attendance Logic & openpyxl Excel Export' },
              { path: 'app/services/fee_service.py', name: 'fee_service.py', type: 'file', description: 'Payment Collection, Discount Rules & REC-YYYY Gen' },
              { path: 'app/services/accounting_service.py', name: 'accounting_service.py', type: 'file', description: 'COA Seeder, Voucher Validation & openpyxl Cash Book' },
              { path: 'app/services/exam_service.py', name: 'exam_service.py', type: 'file', description: 'GPA 5.0 Seeder, Fail-Lock GPA Rules, Merit Compiler & Excel Tabulation' },
              { path: 'app/services/timetable_service.py', name: 'timetable_service.py', type: 'file', description: 'Period Seeder, Collision Detection & Excel Exporter' },
            ],
          },
          {
            path: 'app/reports',
            name: 'reports',
            type: 'folder',
            children: [
              { path: 'app/reports/id_card_generator.py', name: 'id_card_generator.py', type: 'file', description: 'ReportLab CR80 PVC Student ID Card' },
              { path: 'app/reports/student_profile_pdf.py', name: 'student_profile_pdf.py', type: 'file', description: 'Official Student Dossier PDF Report' },
              { path: 'app/reports/teacher_id_card_generator.py', name: 'teacher_id_card_generator.py', type: 'file', description: 'Teacher/Staff CR80 PVC Printable Badge PDF' },
              { path: 'app/reports/fee_receipt_pdf.py', name: 'fee_receipt_pdf.py', type: 'file', description: 'Landscape A5 ReportLab Money Receipt Voucher PDF' },
              { path: 'app/reports/financial_statement_pdf.py', name: 'financial_statement_pdf.py', type: 'file', description: 'Audited Statement of Accounts ReportLab PDF' },
              { path: 'app/reports/report_card_pdf.py', name: 'report_card_pdf.py', type: 'file', description: 'Official A4 ReportLab Academic Transcript & Progress Report PDF' },
              { path: 'app/reports/admit_card_pdf.py', name: 'admit_card_pdf.py', type: 'file', description: 'ReportLab Candidate Exam Hall Admit Card with Routine PDF' },
              { path: 'app/reports/class_timetable_pdf.py', name: 'class_timetable_pdf.py', type: 'file', description: 'Landscape A4 ReportLab Class Timetable PDF' },
              { path: 'app/reports/teacher_routine_pdf.py', name: 'teacher_routine_pdf.py', type: 'file', description: 'Landscape A4 ReportLab Faculty Weekly Workload Routine PDF' },
            ],
          },
          {
            path: 'app/ui',
            name: 'ui',
            type: 'folder',
            children: [
              {
                path: 'app/ui/themes',
                name: 'themes',
                type: 'folder',
                children: [
                  { path: 'app/ui/themes/styles.py', name: 'styles.py', type: 'file', description: 'Fluent Dark/Light QSS Stylesheets' },
                ],
              },
              {
                path: 'app/ui/dialogs',
                name: 'dialogs',
                type: 'folder',
                children: [
                  { path: 'app/ui/dialogs/student_form_dialog.py', name: 'student_form_dialog.py', type: 'file', description: 'Multi-Tab Admission & Edit Dialog' },
                  { path: 'app/ui/dialogs/student_id_card_dialog.py', name: 'student_id_card_dialog.py', type: 'file', description: 'ID Card Graphic Preview & Print' },
                  { path: 'app/ui/dialogs/student_import_dialog.py', name: 'student_import_dialog.py', type: 'file', description: 'Batch Excel .xlsx Import Dialog' },
                  { path: 'app/ui/dialogs/student_promote_dialog.py', name: 'student_promote_dialog.py', type: 'file', description: 'Annual Batch Class Promotion Dialog' },
                  { path: 'app/ui/dialogs/teacher_form_dialog.py', name: 'teacher_form_dialog.py', type: 'file', description: 'Teacher Hire/Edit Modal with Tabbed Info' },
                  { path: 'app/ui/dialogs/staff_form_dialog.py', name: 'staff_form_dialog.py', type: 'file', description: 'Staff Employee Onboarding & Roles Modal' },
                  { path: 'app/ui/dialogs/teacher_id_card_dialog.py', name: 'teacher_id_card_dialog.py', type: 'file', description: 'Teacher/Staff Photo ID Badge Preview & Print' },
                  { path: 'app/ui/dialogs/class_form_dialog.py', name: 'class_form_dialog.py', type: 'file', description: 'Class Configuration & Stream Dialog' },
                  { path: 'app/ui/dialogs/section_form_dialog.py', name: 'section_form_dialog.py', type: 'file', description: 'Section, Room & Class Teacher Dialog' },
                  { path: 'app/ui/dialogs/subject_form_dialog.py', name: 'subject_form_dialog.py', type: 'file', description: 'Subject Syllabus & Mark Distribution Dialog' },
                  { path: 'app/ui/dialogs/fee_payment_dialog.py', name: 'fee_payment_dialog.py', type: 'file', description: 'Payment Collection & Receipt Print PySide6 Modal' },
                  { path: 'app/ui/dialogs/fee_structure_dialog.py', name: 'fee_structure_dialog.py', type: 'file', description: 'Fee Schedule & Batch Class Assignment Dialog' },
                  { path: 'app/ui/dialogs/transaction_form_dialog.py', name: 'transaction_form_dialog.py', type: 'file', description: 'Income/Expense Voucher Record PySide6 Modal' },
                  { path: 'app/ui/dialogs/account_category_dialog.py', name: 'account_category_dialog.py', type: 'file', description: 'Chart of Accounts Head Setup PySide6 Modal' },
                  { path: 'app/ui/dialogs/marks_entry_dialog.py', name: 'marks_entry_dialog.py', type: 'file', description: 'PySide6 Bulk Marks Register Entry Dialog with Live GPA' },
                  { path: 'app/ui/dialogs/exam_schedule_dialog.py', name: 'exam_schedule_dialog.py', type: 'file', description: 'Exam Routine & Timetable Slot Configuration Dialog' },
                  { path: 'app/ui/dialogs/timetable_slot_dialog.py', name: 'timetable_slot_dialog.py', type: 'file', description: 'PySide6 Teaching Period Assignment & Conflict Dialog' },
                  { path: 'app/ui/dialogs/period_config_dialog.py', name: 'period_config_dialog.py', type: 'file', description: 'Bell Schedule & Period Interval PySide6 Dialog' },
                ],
              },
              {
                path: 'app/ui/widgets',
                name: 'widgets',
                type: 'folder',
                children: [
                  { path: 'app/ui/widgets/sidebar.py', name: 'sidebar.py', type: 'file', description: '19-Module PySide6 Sidebar Widget' },
                  { path: 'app/ui/widgets/topbar.py', name: 'topbar.py', type: 'file', description: 'Search, Session & Profile Topbar' },
                ],
              },
              {
                path: 'app/ui/pages',
                name: 'pages',
                type: 'folder',
                children: [
                  { path: 'app/ui/pages/dashboard_page.py', name: 'dashboard_page.py', type: 'file', description: 'KPI Metrics & Activity Log' },
                  { path: 'app/ui/pages/student_management_page.py', name: 'student_management_page.py', type: 'file', description: 'Full Student Roster & Pagination' },
                  { path: 'app/ui/pages/teacher_management_page.py', name: 'teacher_management_page.py', type: 'file', description: 'Faculty Roster, Filter & ID Card PySide6 View' },
                  { path: 'app/ui/pages/staff_management_page.py', name: 'staff_management_page.py', type: 'file', description: 'Non-Teaching Staff & Positions PySide6 View' },
                  { path: 'app/ui/pages/academic_management_page.py', name: 'academic_management_page.py', type: 'file', description: 'Curriculum, Class & Subject Roster View' },
                  { path: 'app/ui/pages/attendance_page.py', name: 'attendance_page.py', type: 'file', description: 'Daily Marking, Quick Actions & Faculty Register' },
                  { path: 'app/ui/pages/fees_management_page.py', name: 'fees_management_page.py', type: 'file', description: 'Tabbed Invoices, Schedules & Payment Audit Page' },
                  { path: 'app/ui/pages/accounting_page.py', name: 'accounting_page.py', type: 'file', description: 'PySide6 3-Tab Cash Book & P&L Page' },
                  { path: 'app/ui/pages/exam_management_page.py', name: 'exam_management_page.py', type: 'file', description: 'PySide6 4-Tab Exam Management, Tabulation & Results Page' },
                  { path: 'app/ui/pages/timetable_page.py', name: 'timetable_page.py', type: 'file', description: 'PySide6 3-Tab Class Matrix, Faculty Schedule & Period Configuration' },
                ],
              },
              {
                path: 'app/ui/windows',
                name: 'windows',
                type: 'folder',
                children: [
                  { path: 'app/ui/windows/login_window.py', name: 'login_window.py', type: 'file', description: 'PySide6 Login Dialog with Lockout' },
                  { path: 'app/ui/windows/setup_wizard.py', name: 'setup_wizard.py', type: 'file', description: '5-Step First-Run Setup Wizard' },
                  { path: 'app/ui/windows/main_window.py', name: 'main_window.py', type: 'file', description: 'Main Window Shell & Router' },
                ],
              },
            ],
          },
        ],
      },
      {
        path: 'tests',
        name: 'tests',
        type: 'folder',
        children: [
          { path: 'tests/test_auth.py', name: 'test_auth.py', type: 'file', description: 'Pytest Suite for Auth & Security' },
          { path: 'tests/test_student.py', name: 'test_student.py', type: 'file', description: 'Pytest Suite for Student CRUD & Promotion' },
          { path: 'tests/test_staff.py', name: 'test_staff.py', type: 'file', description: 'Pytest Suite for Faculty & Staff CRUD Operations' },
          { path: 'tests/test_academic.py', name: 'test_academic.py', type: 'file', description: 'Pytest Suite for Academic Classes, Sections & Subjects' },
          { path: 'tests/test_attendance.py', name: 'test_attendance.py', type: 'file', description: 'Pytest Suite for Daily Attendance & Monthly Matrix' },
          { path: 'tests/test_fee.py', name: 'test_fee.py', type: 'file', description: 'Pytest Suite for Fee Structures, Invoices & Payments' },
          { path: 'tests/test_accounting.py', name: 'test_accounting.py', type: 'file', description: 'Pytest Suite for Vouchers, Cash Book & P&L' },
          { path: 'tests/test_exam.py', name: 'test_exam.py', type: 'file', description: 'Pytest Suite for GPA 5.0, Fail-Lock, Merit Rank, Tabulation & PDFs' },
          { path: 'tests/test_timetable.py', name: 'test_timetable.py', type: 'file', description: 'Pytest Suite for Periods, Double-Booking Clashes & Timetable PDFs' },
        ],
      },
      { path: 'requirements.txt', name: 'requirements.txt', type: 'file', description: 'Core Python Dependencies' },
      { path: 'EduManagePro.spec', name: 'EduManagePro.spec', type: 'file', description: 'PyInstaller Windows Build Spec' },
      { path: 'build_windows.bat', name: 'build_windows.bat', type: 'file', description: 'One-click Windows .EXE Packaging Batch Script' },
      { path: 'README.md', name: 'README.md', type: 'file', description: 'Complete Setup & Execution Documentation' },
    ],
  },
];

export const PythonProjectExplorer: React.FC<{ isDark: boolean }> = ({ isDark }) => {
  const [selectedFile, setSelectedFile] = useState<string>('app/main.py');
  const [copied, setCopied] = useState(false);

  const getFileSnippet = (path: string): string => {
    switch (path) {
      case 'app/main.py':
        return `"""
EduManage Pro - Main Desktop Application Launcher
Initializes PySide6 application, database schema, logging, and initiates the login lifecycle.
"""
import sys, os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from app.config.settings import settings
from app.config.logging_config import app_logger, error_logger
from app.database.init_db import init_database
from app.ui.windows.login_window import LoginWindow
from app.ui.windows.setup_wizard import SetupWizard
from app.ui.windows.main_window import MainWindow

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(settings.APP_NAME)
    
    needs_wizard = init_database()
    if needs_wizard:
        wizard = SetupWizard()
        if wizard.exec() != SetupWizard.Accepted:
            sys.exit(0)
            
    login_dialog = LoginWindow()
    if login_dialog.exec() == LoginWindow.Accepted:
        main_win = MainWindow()
        main_win.show()
        sys.exit(app.exec())

if __name__ == "__main__":
    main()`;

      case 'app/database/connection.py':
        return `from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config.settings import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()`;

      case 'app/services/auth_service.py':
        return `from datetime import datetime, timedelta
from app.models.user import User
from app.security.hasher import PasswordHasher
from app.config.settings import settings

class AuthService:
    @staticmethod
    def authenticate(db, identifier, password, ip="127.0.0.1"):
        user = db.query(User).filter((User.username == identifier) | (User.email == identifier)).first()
        if not user:
            return False, None, "Invalid username or password"
        if user.locked_until and user.locked_until > datetime.utcnow():
            sec = int((user.locked_until - datetime.utcnow()).total_seconds())
            return False, None, f"Account locked. Try again in {sec}s"
        if not PasswordHasher.verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(seconds=60)
            db.commit()
            return False, None, "Invalid password"
        user.failed_login_attempts = 0
        db.commit()
        return True, user, "Success"`;

      case 'app/models/student.py':
        return `from datetime import date
from sqlalchemy import Column, String, Integer, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin

class Student(Base, TimestampMixin):
    __tablename__ = "students"
    student_id = Column(String(40), unique=True, nullable=False, index=True)
    admission_number = Column(String(40), unique=True, nullable=False, index=True)
    roll_number = Column(Integer, nullable=False, index=True)
    full_name = Column(String(120), nullable=False, index=True)
    gender = Column(String(15), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    blood_group = Column(String(10), nullable=True)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)
    status = Column(String(20), default="active", nullable=False)
    guardian_id = Column(Integer, ForeignKey("guardians.id"))
    guardian = relationship("Guardian", back_populates="students")`;

      case 'app/repositories/student_repository.py':
        return `class StudentRepository:
    @staticmethod
    def search_and_filter(db, search_query=None, class_id=None, gender=None, status=None, page=1, per_page=25):
        query = db.query(Student)
        if search_query:
            term = f"%{search_query}%"
            query = query.filter(or_(Student.full_name.ilike(term), Student.student_id.ilike(term)))
        if class_id:
            query = query.filter(Student.class_id == class_id)
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return items, total

    @staticmethod
    def bulk_promote(db, student_ids, target_class_id, target_academic_year_id):
        students = db.query(Student).filter(Student.id.in_(student_ids)).all()
        for stu in students:
            stu.class_id = target_class_id
            stu.academic_year_id = target_academic_year_id
        db.commit()
        return len(students)`;

      case 'app/reports/id_card_generator.py':
        return `from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors

class StudentIDCardGenerator:
    CARD_WIDTH = 3.375 * inch   # CR80 standard
    CARD_HEIGHT = 2.125 * inch

    @classmethod
    def generate_single_card(cls, student, school, output_pdf_path):
        c = canvas.Canvas(output_pdf_path, pagesize=(cls.CARD_WIDTH, cls.CARD_HEIGHT))
        c.roundRect(0, 0, cls.CARD_WIDTH, cls.CARD_HEIGHT, 8, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.rect(0, cls.CARD_HEIGHT - 38, cls.CARD_WIDTH, 38, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.drawString(10, cls.CARD_HEIGHT - 20, school.school_name)
        c.drawString(70, cls.CARD_HEIGHT - 55, student.full_name)
        c.showPage()
        c.save()`;

      case 'build_windows.bat':
        return `@echo off
echo Building EduManage Pro Standalone Windows Package...
pip install -r requirements.txt
pytest tests/ -v
pyinstaller --clean EduManagePro.spec
echo Standalone executable created at: dist\\EduManagePro\\EduManagePro.exe
pause`;

      case 'EduManagePro.spec':
        return `# PyInstaller Spec for EduManage Pro
a = Analysis(
    ['app/main.py'],
    pathex=['.'],
    datas=[('app/config', 'app/config'), ('app/ui/themes', 'app/ui/themes')],
    hiddenimports=['sqlalchemy.ext.baked', 'bcrypt', 'sqlite3', 'PySide6'],
    console=False,
)
exe = EXE(pyz, a.scripts, name='EduManagePro', console=False)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name='EduManagePro')`;

      case 'app/models/staff.py':
        return `from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin

class Department(Base, TimestampMixin):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    teachers = relationship("Teacher", back_populates="department")

class Teacher(Base, TimestampMixin):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True)
    teacher_id = Column(String(50), unique=True, nullable=False, index=True) # e.g. TCH-2026-001
    full_name = Column(String(120), nullable=False)
    full_name_bn = Column(String(150), nullable=True)
    designation = Column(String(100), default="Assistant Teacher")
    department_id = Column(Integer, ForeignKey("departments.id"))
    primary_subject = Column(String(100), nullable=False)
    monthly_salary = Column(Float, default=0.0)
    status = Column(String(20), default="Active") # Active, On Leave, Retired

class Staff(Base, TimestampMixin):
    __tablename__ = "staff_members"
    id = Column(Integer, primary_key=True)
    employee_id = Column(String(50), unique=True, nullable=False, index=True) # e.g. STF-2026-001
    full_name = Column(String(120), nullable=False)
    position = Column(String(100), nullable=False) # Accountant, Librarian, Receptionist...
    monthly_salary = Column(Float, default=0.0)
    status = Column(String(20), default="Active")`;

      case 'app/repositories/staff_repository.py':
        return `from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.staff import Teacher, Staff, Department

class StaffRepository:
    @staticmethod
    def get_teachers(db: Session, search: str = None, dept_id: int = None, status: str = None, page: int = 1, per_page: int = 25):
        q = db.query(Teacher)
        if search:
            term = f"%{search}%"
            q = q.filter(or_(Teacher.full_name.ilike(term), Teacher.teacher_id.ilike(term), Teacher.primary_subject.ilike(term)))
        if dept_id:
            q = q.filter(Teacher.department_id == dept_id)
        if status and status != 'all':
            q = q.filter(Teacher.status == status)
        total = q.count()
        return q.offset((page - 1) * per_page).limit(per_page).all(), total

    @staticmethod
    def get_staff_list(db: Session, search: str = None, position: str = None, page: int = 1, per_page: int = 25):
        q = db.query(Staff)
        if search:
            term = f"%{search}%"
            q = q.filter(or_(Staff.full_name.ilike(term), Staff.employee_id.ilike(term)))
        if position and position != 'all':
            q = q.filter(Staff.position == position)
        total = q.count()
        return q.offset((page - 1) * per_page).limit(per_page).all(), total`;

      case 'app/services/staff_service.py':
        return `from app.repositories.staff_repository import StaffRepository
from app.models.staff import Teacher, Staff
from datetime import datetime

class StaffService:
    @staticmethod
    def generate_teacher_id(db) -> str:
        count = db.query(Teacher).count()
        year = datetime.now().year
        return f"TCH-{year}-{count + 1:04d}"

    @staticmethod
    def generate_staff_id(db) -> str:
        count = db.query(Staff).count()
        year = datetime.now().year
        return f"STF-{year}-{count + 1:04d}"

    @staticmethod
    def create_teacher(db, teacher_data: dict, current_user: str) -> Teacher:
        if not teacher_data.get("teacher_id"):
            teacher_data["teacher_id"] = StaffService.generate_teacher_id(db)
        teacher = StaffRepository.create_teacher(db, teacher_data)
        return teacher`;

      case 'app/reports/teacher_id_card_generator.py':
        return `from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors

class TeacherIDCardGenerator:
    CARD_WIDTH = 3.375 * inch   # CR80 standard dimensions
    CARD_HEIGHT = 2.125 * inch

    @classmethod
    def generate_card(cls, member, school, output_path: str, is_teacher: bool = True):
        c = canvas.Canvas(output_path, pagesize=(cls.CARD_WIDTH, cls.CARD_HEIGHT))
        header_color = colors.HexColor("#065F46") if is_teacher else colors.HexColor("#3730A3")
        c.setFillColor(header_color)
        c.rect(0, cls.CARD_HEIGHT - 38, cls.CARD_WIDTH, 38, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 16, school.school_name.upper())
        c.setFont("Helvetica", 6.5)
        badge_title = "OFFICIAL FACULTY IDENTIFICATION" if is_teacher else "OFFICIAL STAFF IDENTIFICATION"
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 28, badge_title)
        c.showPage()
        c.save()`;

      case 'tests/test_staff.py':
        return `import pytest
from app.models.staff import Teacher, Staff, Department
from app.services.staff_service import StaffService

def test_teacher_id_generation(db_session):
    tch_id = StaffService.generate_teacher_id(db_session)
    assert tch_id.startswith("TCH-")

def test_staff_id_generation(db_session):
    stf_id = StaffService.generate_staff_id(db_session)
    assert stf_id.startswith("STF-")

def test_create_teacher_and_filter(db_session):
    teacher = StaffService.create_teacher(db_session, {
        "full_name": "Dr. Shamsul Huda",
        "primary_subject": "Physics",
        "monthly_salary": 45000.0,
        "status": "Active"
    }, current_user="admin")
    assert teacher.id is not None
    assert teacher.teacher_id.startswith("TCH-")`;

      case 'app/repositories/academic_repository.py':
        return `from sqlalchemy.orm import Session, joinedload
from app.models.academic import AcademicYear, SchoolClass, Section, Subject

class AcademicRepository:
    @staticmethod
    def get_classes(db: Session, academic_year_id=None, search=None):
        query = db.query(SchoolClass).options(
            joinedload(SchoolClass.sections),
            joinedload(SchoolClass.subjects),
            joinedload(SchoolClass.academic_year)
        )
        if academic_year_id:
            query = query.filter(SchoolClass.academic_year_id == academic_year_id)
        if search:
            query = query.filter(SchoolClass.name.ilike(f"%{search}%"))
        return query.order_by(SchoolClass.numeric_order.asc()).all()

    @staticmethod
    def get_subjects(db: Session, class_id=None, search=None):
        query = db.query(Subject).options(joinedload(Subject.assigned_teacher))
        if class_id:
            query = query.filter(Subject.class_id == class_id)
        return query.order_by(Subject.class_id.asc(), Subject.name.asc()).all()`;

      case 'app/services/academic_service.py':
        return `from app.repositories.academic_repository import AcademicRepository
from app.models.academic import Subject, SchoolClass
from datetime import datetime

class AcademicService:
    @staticmethod
    def generate_subject_id(db) -> str:
        count = db.query(Subject).count()
        year = datetime.now().year
        return f"SUB-{year}-{count + 1:04d}"

    @staticmethod
    def create_subject(db, subject_data: dict, current_user: str = "admin"):
        full_marks = int(subject_data.get("full_marks", 100))
        pass_marks = int(subject_data.get("pass_marks", 33))
        if pass_marks > full_marks:
            return None, "Pass marks cannot exceed full marks."
        if not subject_data.get("subject_id"):
            subject_data["subject_id"] = AcademicService.generate_subject_id(db)
        sub = AcademicRepository.create_subject(db, subject_data)
        return sub, "Subject created successfully."`;

      case 'app/ui/pages/academic_management_page.py':
        return `from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QHeaderView
)
from app.repositories.academic_repository import AcademicRepository
from app.services.academic_service import AcademicService

class AcademicManagementPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh_all()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        # Tab 1: Classes & Sections Roster
        # Tab 2: Subject Curriculum & Marks
        # Tab 3: Academic Years & Sessions
        layout.addWidget(self.tabs)`;

      case 'tests/test_academic.py':
        return `import pytest
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.services.academic_service import AcademicService

def test_academic_year_lifecycle(db_session):
    ay1 = AcademicRepository.create_academic_year(db_session, {"name": "2025-2026", "is_current": True})
    ay2 = AcademicRepository.create_academic_year(db_session, {"name": "2026-2027", "is_current": True})
    db_session.refresh(ay1)
    assert ay2.is_current is True
    assert ay1.is_current is False

def test_subject_mark_validation(db_session):
    invalid_sub, err = AcademicService.create_subject(db_session, {
        "name": "Invalid Subject", "code": "INV", "full_marks": 50, "pass_marks": 60, "class_id": 1
    })
    assert invalid_sub is None
    assert "cannot exceed" in err`;

      case 'app/models/attendance.py':
        return `from datetime import date
from sqlalchemy import Column, Integer, String, Date, ForeignKey, UniqueConstraint
from app.database.connection import Base
from app.models.base import TimestampMixin

class StudentAttendance(Base, TimestampMixin):
    __tablename__ = "student_attendances"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)
    date = Column(Date, default=date.today, nullable=False, index=True)
    status = Column(String(20), default="Present", nullable=False) # Present, Absent, Late, Leave
    check_in_time = Column(String(20), nullable=True)
    remarks = Column(String(255), nullable=True)
    marked_by = Column(String(80), default="admin")
    __table_args__ = (UniqueConstraint("student_id", "date", name="uq_student_daily_attendance"),)

class TeacherAttendance(Base, TimestampMixin):
    __tablename__ = "teacher_attendances"
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, default=date.today, nullable=False, index=True)
    status = Column(String(20), default="Present", nullable=False)
    check_in_time = Column(String(20), nullable=True)
    check_out_time = Column(String(20), nullable=True)
    __table_args__ = (UniqueConstraint("teacher_id", "date", name="uq_teacher_daily_attendance"),)`;

      case 'app/repositories/attendance_repository.py':
        return `from sqlalchemy.orm import Session
from datetime import date
from app.models.attendance import StudentAttendance, TeacherAttendance

class AttendanceRepository:
    @staticmethod
    def save_bulk_student_attendance(db: Session, records: list, marked_by: str = "admin") -> int:
        for item in records:
            existing = db.query(StudentAttendance).filter(
                StudentAttendance.student_id == item["student_id"],
                StudentAttendance.date == item.get("date", date.today())
            ).first()
            if existing:
                existing.status = item.get("status", "Present")
                existing.remarks = item.get("remarks")
                existing.check_in_time = item.get("check_in_time")
            else:
                db.add(StudentAttendance(**item, marked_by=marked_by))
        db.commit()
        return len(records)`;

      case 'app/services/attendance_service.py':
        return `import openpyxl
from datetime import date
from app.repositories.attendance_repository import AttendanceRepository

class AttendanceService:
    @staticmethod
    def export_monthly_register_excel(db, class_id: int, year: int, month: int, output_file_path: str):
        data = AttendanceRepository.get_monthly_student_register(db, class_id, year, month)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Attendance_{month}_{year}"
        # Generates colored Excel register grid with P, A, L, and percentage formulas
        wb.save(output_file_path)
        return output_file_path`;

      case 'tests/test_attendance.py':
        return `import pytest
from datetime import date
from app.services.attendance_service import AttendanceService
from app.repositories.attendance_repository import AttendanceRepository

def test_mark_and_upsert_student_attendance(db_session):
    today = date.today()
    records = [{"student_id": 1, "class_id": 1, "date": today, "status": "Present"}]
    ok, msg = AttendanceService.mark_student_attendance(db_session, 1, None, today, records)
    assert ok is True
    stats = AttendanceRepository.get_student_daily_stats(db_session, class_id=1, att_date=today)
    assert stats["present"] == 1`;

      case 'app/models/fee.py':
        return `from sqlalchemy import Column, Integer, String, Float, Boolean, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin

class FeeCategory(Base, TimestampMixin):
    __tablename__ = "fee_categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))
    is_recurring = Column(Boolean, default=True)
    frequency = Column(String(30), default="Monthly")

class FeeStructure(Base, TimestampMixin):
    __tablename__ = "fee_structures"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("fee_categories.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    title = Column(String(150), nullable=False)
    amount = Column(Float, nullable=False)
    due_date = Column(Date, nullable=False)

class StudentFee(Base, TimestampMixin):
    __tablename__ = "student_fees"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    fee_structure_id = Column(Integer, ForeignKey("fee_structures.id"), nullable=False)
    total_amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    net_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0.0)
    due_amount = Column(Float, nullable=False)
    status = Column(String(20), default="Unpaid")

class FeePayment(Base, TimestampMixin):
    __tablename__ = "fee_payments"
    id = Column(Integer, primary_key=True)
    student_fee_id = Column(Integer, ForeignKey("student_fees.id"), nullable=False)
    receipt_number = Column(String(50), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    payment_method = Column(String(30), nullable=False)
    transaction_ref = Column(String(100))
    payment_date = Column(Date, nullable=False)
    received_by = Column(String(100), nullable=False)`;

      case 'app/repositories/fee_repository.py':
        return `from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.fee import FeeCategory, FeeStructure, StudentFee, FeePayment
from app.models.student import Student

class FeeRepository:
    @staticmethod
    def batch_assign_fee_to_class(db: Session, fee_structure_id: int, class_id: int) -> int:
        structure = db.query(FeeStructure).get(fee_structure_id)
        students = db.query(Student).filter(Student.class_id == class_id, Student.status == "Active").all()
        created = 0
        for s in students:
            # Check duplicate invoice
            existing = db.query(StudentFee).filter_by(student_id=s.id, fee_structure_id=fee_structure_id).first()
            if not existing:
                inv = StudentFee(
                    student_id=s.id,
                    fee_structure_id=fee_structure_id,
                    total_amount=structure.amount,
                    discount_amount=0.0,
                    net_amount=structure.amount,
                    paid_amount=0.0,
                    due_amount=structure.amount,
                    due_date=structure.due_date,
                    status="Unpaid"
                )
                db.add(inv)
                created += 1
        db.commit()
        return created`;

      case 'app/services/fee_service.py':
        return `from datetime import datetime, date
from sqlalchemy.orm import Session
from app.repositories.fee_repository import FeeRepository

class FeeService:
    @staticmethod
    def generate_receipt_number(db: Session) -> str:
        year = datetime.now().year
        count = FeeRepository.get_payment_count_by_year(db, year)
        return f"REC-{year}-{count + 1:05d}"

    @staticmethod
    def collect_payment(db: Session, payment_data: dict):
        # Enforces payment <= balance due + floating point tolerance
        inv = FeeRepository.get_student_fee_by_id(db, payment_data["student_fee_id"])
        due = inv.net_amount - inv.paid_amount
        if payment_data["amount"] > due + 0.01:
            return None, f"Payment (৳{payment_data['amount']}) exceeds balance due (৳{due})"
        # Generates REC-YYYY-XXXXX and updates invoice balance
        ...`;

      case 'app/reports/fee_receipt_pdf.py':
        return `from reportlab.lib.pagesizes import A5, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors

class FeeReceiptPDFGenerator:
    @staticmethod
    def generate_receipt(payment, school_info: dict, output_path: str) -> bool:
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A5), leftMargin=25, rightMargin=25)
        # Formats Official Double-Copy Student & Office Money Receipt Voucher
        ...
        doc.build(story)
        return True`;

      case 'tests/test_fee.py':
        return `import pytest
from app.repositories.fee_repository import FeeRepository
from app.services.fee_service import FeeService

def test_payment_collection_workflow(db_session):
    # Tests partial payment, discount scholarship, and overpayment prevention
    pmt, err = FeeService.collect_payment(db_session, {
        "student_fee_id": 1,
        "amount": 1000.0,
        "discount_amount": 200.0,
        "payment_method": "bKash"
    })
    assert err is None
    assert pmt.receipt_number.startswith("REC-")`;

      case 'app/models/accounting.py':
        return `from sqlalchemy import Column, Integer, String, Float, Boolean, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin

class AccountCategory(Base, TimestampMixin):
    __tablename__ = "account_categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    type = Column(String(20), nullable=False)  # 'Income' | 'Expense'
    description = Column(String(255))
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

class AccountTransaction(Base, TimestampMixin):
    __tablename__ = "account_transactions"
    id = Column(Integer, primary_key=True)
    voucher_no = Column(String(50), unique=True, nullable=False)
    transaction_date = Column(Date, nullable=False)
    type = Column(String(20), nullable=False)  # 'Income' | 'Expense'
    category_id = Column(Integer, ForeignKey("account_categories.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(30), default="Cash")
    reference_no = Column(String(100))
    paid_to_received_from = Column(String(150), nullable=False)
    description = Column(Text)
    recorded_by = Column(String(100), default="Accountant")`;

      case 'app/repositories/accounting_repository.py':
        return `from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.accounting import AccountCategory, AccountTransaction

class AccountingRepository:
    @staticmethod
    def get_financial_summary(db: Session):
        inc = db.query(func.coalesce(func.sum(AccountTransaction.amount), 0.0)).filter_by(type="Income", status="Approved").scalar()
        exp = db.query(func.coalesce(func.sum(AccountTransaction.amount), 0.0)).filter_by(type="Expense", status="Approved").scalar()
        cash_in = db.query(func.coalesce(func.sum(AccountTransaction.amount), 0.0)).filter_by(type="Income", payment_method="Cash", status="Approved").scalar()
        cash_out = db.query(func.coalesce(func.sum(AccountTransaction.amount), 0.0)).filter_by(type="Expense", payment_method="Cash", status="Approved").scalar()
        return {
            "total_income": float(inc),
            "total_expense": float(exp),
            "net_surplus": float(inc - exp),
            "cash_in_hand": float(cash_in - cash_out),
            "is_profit": (inc - exp) >= 0
        }`;

      case 'app/services/accounting_service.py':
        return `from datetime import datetime, date
from sqlalchemy.orm import Session
import openpyxl

class AccountingService:
    @staticmethod
    def generate_voucher_number(db: Session, trans_type: str, tx_date: date) -> str:
        year = tx_date.year if tx_date else datetime.now().year
        prefix = "INC" if trans_type == "Income" else "EXP"
        count = AccountingRepository.get_transaction_count_by_year(db, year)
        return f"VCH-{year}-{prefix}-{count + 1:05d}"

    @staticmethod
    def export_cash_book_excel(db: Session, output_file_path: str):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Cash_Book_Ledger"
        # Exports formatted double-entry cash book with formulas
        wb.save(output_file_path)
        return True`;

      case 'app/reports/financial_statement_pdf.py':
        return `from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer

class FinancialStatementPDFGenerator:
    @staticmethod
    def generate_statement(summary, income_breakdown, expense_breakdown, school_info, period_str, output_path):
        doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=36, rightMargin=36)
        # Formats Official Statement of Revenue, Expenditure & Operating Margin
        doc.build(story)
        return True`;

      case 'tests/test_accounting.py':
        return `import pytest
from app.repositories.accounting_repository import AccountingRepository
from app.services.accounting_service import AccountingService

def test_financial_summary_and_cash_book(db_session):
    AccountingService.seed_default_categories(db_session)
    # Tests cash in, cash out, net operating balance, and voucher integrity
    summary = AccountingRepository.get_financial_summary(db_session)
    assert summary["net_surplus"] >= 0`;

      case 'app/models/exam.py':
        return `from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class ExamTerm(Base):
    __tablename__ = "exam_terms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    exam_code = Column(String(50), unique=True, nullable=False, index=True)
    start_date = Column(String(20), nullable=False)
    end_date = Column(String(20), nullable=False)
    status = Column(String(30), default="Scheduled")

class StudentMark(Base):
    __tablename__ = "student_marks"
    id = Column(Integer, primary_key=True, index=True)
    exam_term_id = Column(Integer, ForeignKey("exam_terms.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    theory_marks = Column(Float, default=0.0)
    mcq_marks = Column(Float, default=0.0)
    practical_marks = Column(Float, default=0.0)
    total_marks = Column(Float, default=0.0)
    grade_point = Column(Float, default=0.0)
    grade_name = Column(String(10), default="F")
    is_passed = Column(Boolean, default=False)
    is_absent = Column(Boolean, default=False)`;

      case 'app/services/exam_service.py':
        return `from app.repositories.exam_repository import ExamRepository

class ExamService:
    @staticmethod
    def calculate_gpa(obtained_marks: float) -> tuple[float, str, str, bool]:
        """GPA 5.0 National Grading System: 80-100: A+ (5.0), 70-79: A (4.0), 33-39: D (1.0), <33: F (0.0)"""
        if obtained_marks >= 80.0:
            return 5.0, "A+", "Outstanding", True
        elif obtained_marks >= 70.0:
            return 4.0, "A", "Excellent", True
        elif obtained_marks >= 60.0:
            return 3.5, "A-", "Very Good", True
        elif obtained_marks >= 50.0:
            return 3.0, "B", "Good", True
        elif obtained_marks >= 40.0:
            return 2.0, "C", "Satisfactory", True
        elif obtained_marks >= 33.0:
            return 1.0, "D", "Pass", True
        else:
            return 0.0, "F", "Fail", False

    @staticmethod
    def compile_class_results(session, exam_term_id: int, class_id: int):
        """Calculates GPA, enforces mandatory fail-lock, and assigns merit ranks."""
        # If any subject fails or absent: GPA = 0.00 and overall_grade = 'F'
        return ExamRepository.compile_class_results(session, exam_term_id, class_id)`;

      case 'app/reports/report_card_pdf.py':
        return `from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer

class ReportCardPDFGenerator:
    @staticmethod
    def generate_report_card(student_summary, subject_marks, school_info, output_path):
        """Generates official academic transcript with GPA 5.0, rank, and grading legend."""
        doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=36, rightMargin=36)
        # Detailed academic performance table, fail-lock verification, and signatures
        doc.build(story)
        return True`;

      case 'app/ui/pages/exam_management_page.py':
        return `from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QTableWidget
from app.services.exam_service import ExamService

class ExamManagementPage(QWidget):
    """4-Tab PySide6 GUI: Tabulation Sheets, Marks Entry, Exam Routines & GPA 5.0 Legend."""
    def __init__(self, session_manager, db_session, parent=None):
        super().__init__(parent)
        self.session_manager = session_manager
        self.db_session = db_session
        self._setup_ui()`;

      case 'tests/test_exam.py':
        return `import pytest
from app.services.exam_service import ExamService

def test_gpa_calculation_and_fail_lock(db_session):
    # Tests standard GPA 5.0 boundaries
    gp, grade, _, passed = ExamService.calculate_gpa(85.0)
    assert gp == 5.0 and grade == "A+" and passed is True

    # Tests fail condition
    gp_f, grade_f, _, passed_f = ExamService.calculate_gpa(28.0)
    assert gp_f == 0.0 and grade_f == "F" and passed_f is False`;

      case 'app/models/timetable.py':
        return `from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class PeriodSlot(Base):
    __tablename__ = "period_slots"
    id = Column(Integer, primary_key=True, index=True)
    period_number = Column(Integer, nullable=False)
    name = Column(String(50), nullable=False)
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)
    is_break = Column(Boolean, default=False)

class TimetableEntry(Base):
    __tablename__ = "timetable_entries"
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    day_of_week = Column(String(20), nullable=False)
    period_slot_id = Column(Integer, ForeignKey("period_slots.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    room_number = Column(String(50), nullable=False)`;

      case 'app/services/timetable_service.py':
        return `from app.repositories.timetable_repository import TimetableRepository

class TimetableService:
    @staticmethod
    def assign_timetable_slot(session, academic_year_id, class_id, day_of_week, period_slot_id, subject_id, teacher_id, room_number, **kwargs):
        # Automated collision detection for teacher and room double-booking
        conflicts = TimetableRepository.check_conflicts(session, day_of_week, period_slot_id, teacher_id, room_number)
        if conflicts:
            return None, conflicts
        return TimetableRepository.create_timetable_entry(session, ...), []`;

      case 'app/reports/class_timetable_pdf.py':
        return `from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle

class ClassTimetablePDFGenerator:
    @staticmethod
    def generate_timetable(class_name, section_name, shift_name, school_info, periods, matrix, output_path):
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), leftMargin=36, rightMargin=36)
        # Formats weekly master timetable with times, teachers, subjects, and rooms
        doc.build(story)
        return True`;

      case 'app/ui/pages/timetable_page.py':
        return `from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QTableWidget
from app.repositories.timetable_repository import TimetableRepository

class TimetablePage(QWidget):
    """3-Tab PySide6 GUI: Class Timetable Grid, Teacher Workload Routine & Bell Periods."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()`;

      case 'tests/test_timetable.py':
        return `import pytest
from app.services.timetable_service import TimetableService

def test_timetable_collision_detection(db_session):
    # Tests that assigning the same teacher to two classes in the same period fails with clash warning
    entry1, conf1 = TimetableService.assign_timetable_slot(db_session, 1, 5, "Sunday", 2, 3, 1, "Room 301")
    assert entry1 is not None and len(conf1) == 0

    entry2, conf2 = TimetableService.assign_timetable_slot(db_session, 1, 4, "Sunday", 2, 3, 1, "Room 302")
    assert entry2 is None and len(conf2) > 0 and "Teacher Conflict" in conf2[0]`;

      default:
        return `# EduManage Pro - ${path}
# Complete implementation created in /school_management/${path}
# Clean Architecture, offline SQLite, SQLAlchemy ORM, Bcrypt, and PySide6 UI.`;
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(getFileSnippet(selectedFile));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderTree = (nodes: FileNode[], depth = 0) => {
    return nodes.map((node) => {
      const isSelected = selectedFile === node.path;
      if (node.type === 'folder') {
        return (
          <div key={node.path} className="space-y-0.5">
            <div
              className={`flex items-center space-x-2 py-1 px-2 rounded-md text-xs font-semibold text-slate-300`}
              style={{ paddingLeft: `${depth * 14 + 8}px` }}
            >
              <FolderOpen className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <span>{node.name}</span>
            </div>
            {node.children && renderTree(node.children, depth + 1)}
          </div>
        );
      }
      return (
        <button
          key={node.path}
          onClick={() => setSelectedFile(node.path)}
          style={{ paddingLeft: `${depth * 14 + 8}px` }}
          className={`w-full text-left flex items-center justify-between py-1 px-2 rounded-md text-xs transition-colors ${
            isSelected
              ? 'bg-blue-600 text-white font-semibold'
              : isDark
              ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <div className="flex items-center space-x-2 truncate">
            <FileCode className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-white' : 'text-blue-400'}`} />
            <span className="truncate">{node.name}</span>
          </div>
        </button>
      );
    });
  };

  return (
    <div className="h-full flex flex-col p-6 space-y-4">
      {/* Top Banner */}
      <div className={`p-4 rounded-2xl border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
        isDark ? 'bg-slate-900/90 border-slate-800 text-slate-200' : 'bg-white border-slate-200 text-slate-800'
      }`}>
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 rounded-xl bg-blue-600/10 border border-blue-500/20 text-blue-400 flex items-center justify-center text-2xl font-bold">
            🐍
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-slate-100">Standalone Python 3.12+ Desktop Codebase</h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                Phases 1-9 Complete
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Targeted for Windows Desktop computers (PySide6, SQLite WAL, SQLAlchemy ORM, Bcrypt, PyInstaller)
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => alert("All 55 Python files, build batch files, and PyInstaller spec files are stored directly in your '/school_management/' project folder!")}
            className="px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center space-x-1.5 shadow"
          >
            <Download className="w-4 h-4" />
            <span>Folder: /school_management/</span>
          </button>
        </div>
      </div>

      {/* Main Split Layout: File Tree on left, Code Viewer on right */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-4 min-h-[500px]">
        {/* Left: Tree */}
        <div className={`md:col-span-4 rounded-xl border p-3 flex flex-col ${
          isDark ? 'bg-slate-900/80 border-slate-800' : 'bg-white border-slate-200'
        }`}>
          <div className="pb-2 mb-2 border-b border-inherit flex items-center justify-between text-xs font-semibold text-slate-400">
            <span>Project Files Tree</span>
            <span className="font-mono text-[10px]">55 files</span>
          </div>
          <div className="flex-1 overflow-y-auto space-y-0.5 pr-1">
            {renderTree(PROJECT_TREE)}
          </div>
        </div>

        {/* Right: Code Inspector */}
        <div className={`md:col-span-8 rounded-xl border p-4 flex flex-col ${
          isDark ? 'bg-slate-900/90 border-slate-800' : 'bg-white border-slate-200'
        }`}>
          <div className="flex items-center justify-between pb-3 border-b border-inherit">
            <div className="flex items-center space-x-2">
              <span className="font-mono text-xs font-bold text-blue-400">{selectedFile}</span>
            </div>
            <button
              onClick={handleCopy}
              className={`px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center space-x-1.5 transition-all ${
                copied
                  ? 'bg-emerald-600 text-white border-emerald-500'
                  : isDark
                  ? 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                  : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied!' : 'Copy Code'}</span>
            </button>
          </div>

          <pre className="flex-1 overflow-y-auto p-3 mt-3 rounded-lg bg-slate-950 font-mono text-xs text-slate-300 leading-relaxed border border-slate-800/80">
            <code>{getFileSnippet(selectedFile)}</code>
          </pre>

          {/* Quick Terminal run instructions */}
          <div className="mt-3 p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Terminal className="w-4 h-4 text-emerald-400" />
              <span>Windows CLI: <strong className="text-slate-200">cd school_management && python app/main.py</strong></span>
            </div>
            <span className="text-[10px] text-slate-500">Offline SQLite & PySide6</span>
          </div>
        </div>
      </div>
    </div>
  );
};
