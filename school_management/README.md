# EduManage Pro — Complete School Management System (Desktop)

**EduManage Pro** is an enterprise-grade, offline-first School Management Desktop Software engineered for Windows desktop computers, built with **Python 3.12+**, **PySide6 (Qt 6)**, **SQLAlchemy ORM**, and **SQLite**.

---

## 🏛️ Phase 1 Architecture Overview

Phase 1 establishes the rock-solid foundation, security framework, database models, and modern desktop UI:

- **Clean Architecture**: Strict separation of concerns across Configuration, Database, ORM Models, Security Services, UI Windows, and Widgets.
- **Offline SQLite & WAL Mode**: High concurrency, instant startup, zero external server dependencies, full data integrity.
- **Enterprise Security**:
  - Salting and hashing via `bcrypt` (12 rounds).
  - Rate limiting & lockout protection: 5 consecutive failed login attempts locks account for 60 seconds.
  - Role-Based Access Control (RBAC): Super Admin, Administrator, Teacher, Accountant, Receptionist, Librarian, Student/Guardian.
- **First-Run Setup Wizard**: 5-step guided wizard for school profile, EIIN, admin credentials, academic calendar, and starter curriculum.
- **Multi-File Structured Logging**: `app.log`, `error.log`, `security.log` with size rotation.
- **Responsive Fluent Desktop UI**: High-DPI support, dark/light theme toggle, global search shortcut (`Ctrl+K`), live activity log feed.

---

## 🎓 Phase 2 Student Management Capabilities

Phase 2 adds the complete, enterprise-grade Student Management subsystem:
- **Comprehensive Student Profiles**: Auto-generated Student ID (`STU-YYYY-XXXX`), Admission Number (`ADM-YYYY-XXXX`), Roll Numbers, Gender, DOB, Blood Groups, Bengali/English names, and status tracking.
- **Guardian & Emergency Information**: Father, Mother, Primary Guardian, occupations, phone numbers, and emergency contact linkage.
- **Data Repository & Search**: Paginated queries, multi-column filters (Class, Section, Gender, Status), and fast full-text searching.
- **Standardized Student ID Card Generator (`app/reports/id_card_generator.py`)**: ReportLab vector PDF output for CR80 printable PVC/paper cards with photo frame, barcode placeholder, and authorized school signatures.
- **Official Printable Dossier (`app/reports/student_profile_pdf.py`)**: Standard A4 official admission dossier sheet.
- **Excel (.xlsx) Import & Export**: Batch import rosters with validation warnings, and export active classes to Excel using `openpyxl`.
- **Batch Academic Promotion**: Annual bulk promotion mechanism updating academic levels and sessions.

---

## 📂 Project Directory Structure

```text
school_management/
├── app/
│   ├── main.py                     # Desktop entrypoint & high-DPI initialization
│   ├── config/
│   │   ├── settings.py             # App, database, and localization settings
│   │   └── logging_config.py       # Rotating multi-file logger (app, error, security)
│   ├── database/
│   │   ├── connection.py           # Engine with SQLite PRAGMA & WAL mode
│   │   └── init_db.py              # Schema creation, role seeding, and Super Admin
│   ├── models/
│   │   ├── base.py                 # TimestampMixin & base ORM
│   │   ├── user.py                 # User, Role, Permission models
│   │   ├── school.py               # SchoolSetting (EIIN, contact, branding, currency)
│   │   ├── academic.py             # AcademicYear, SchoolClass, Section, Subject
│   │   ├── activity.py             # ActivityLog (audit trail)
│   │   └── student.py              # Student, Guardian, StudentPromotionHistory [Phase 2]
│   ├── repositories/
│   │   └── student_repository.py   # Student CRUD, filters, pagination & promotion [Phase 2]
│   ├── security/
│   │   ├── hasher.py               # Bcrypt password hashing
│   │   └── session.py              # In-memory session manager
│   ├── services/
│   │   ├── auth_service.py         # Login, lockout counter, password change
│   │   └── student_service.py      # Student validation, Excel import/export & IDs [Phase 2]
│   ├── reports/
│   │   ├── id_card_generator.py    # ReportLab CR80 PVC Student ID Card [Phase 2]
│   │   └── student_profile_pdf.py  # Official Student Dossier Printable PDF [Phase 2]
│   └── ui/
│       ├── themes/
│       │   └── styles.py           # Modern Dark and Light QSS stylesheets
│       ├── dialogs/
│       │   ├── student_form_dialog.py    # 4-tab Admission & Edit dialog [Phase 2]
│       │   ├── student_id_card_dialog.py # ID card preview & export dialog [Phase 2]
│       │   ├── student_import_dialog.py  # Excel .xlsx batch importer [Phase 2]
│       │   └── student_promote_dialog.py # Annual class promotion dialog [Phase 2]
│       ├── widgets/
│       │   ├── sidebar.py          # 19-module enterprise desktop sidebar
│       │   └── topbar.py           # Global search, session badge, theme & profile
│       ├── pages/
│       │   ├── dashboard_page.py   # KPI cards, attendance stats, activity feed
│       │   └── student_management_page.py # Full roster table & pagination [Phase 2]
│       └── windows/
│           ├── login_window.py     # Login dialog with password show/hide & lockout
│           ├── setup_wizard.py     # 5-step first-run setup wizard
│           └── main_window.py      # Main window shell with stacked navigation
├── tests/
│   ├── test_auth.py                # Security & auth unit tests (pytest)
│   └── test_student.py             # Student CRUD, search & promotion unit tests [Phase 2]
├── requirements.txt                # Python dependencies
├── EduManagePro.spec               # PyInstaller Windows build specification
├── build_windows.bat               # Automated Windows packaging batch script
└── README.md                       # Comprehensive guide
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.12+** on Windows 10/11 (or Linux / macOS)
- Git (optional)

### 2. Environment Setup
```bash
# Navigate to the project directory
cd school_management

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Launching EduManage Pro
```bash
python app/main.py
```

- On first launch, the **First-Run Setup Wizard** will guide you to set up your school profile and admin password.
- If you skip or run default, log in with the seeded Super Admin credentials:
  - **Username:** `admin`
  - **Password:** `Admin@123`

---

## 🧪 Running Unit Tests

Verify password hashing, credential validation, and lockout rules:

```bash
pytest tests/ -v
```

---

## 📦 Building Windows Standalone Executable (.exe)

To generate a standalone Windows desktop folder with `EduManagePro.exe`:

### Using the Batch Script:
```cmd
build_windows.bat
```

### Or using PyInstaller directly:
```bash
pyinstaller --clean EduManagePro.spec
```

The resulting executable will be located in `dist/EduManagePro/EduManagePro.exe`.
