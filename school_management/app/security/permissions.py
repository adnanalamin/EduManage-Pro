"""
EduManage Pro - Enterprise Permission Hierarchy & RBAC Catalog
Hierarchy: Module -> Feature -> Action
Actions: VIEW, CREATE, EDIT, DELETE, PRINT, EXPORT, IMPORT, APPROVE, REFUND, MANAGE
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple


class PermissionAction(str, Enum):
    VIEW = "VIEW"
    CREATE = "CREATE"
    EDIT = "EDIT"
    DELETE = "DELETE"
    PRINT = "PRINT"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    APPROVE = "APPROVE"
    REFUND = "REFUND"
    MANAGE = "MANAGE"


ALL_ACTIONS: List[str] = [a.value for a in PermissionAction]

# Hierarchical catalog: Module -> List of (feature_slug, feature_label, supported_actions)
MODULE_FEATURE_CATALOG: Dict[str, List[Tuple[str, str, List[str]]]] = {
    "DASHBOARD": [
        ("overview", "Executive Dashboard", ["VIEW", "EXPORT"]),
    ],
    "STUDENTS": [
        ("directory", "Student Directory & Profiles", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "EXPORT", "IMPORT"]),
        ("promotions", "Student Promotions & Transfers", ["VIEW", "CREATE", "APPROVE", "MANAGE"]),
    ],
    "ADMISSIONS": [
        ("applications", "Admission Applications, Forms & Checklists", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "EXPORT", "IMPORT"]),
        ("evaluation", "Admission Tests, Interviews, Merit List & Approval", ["VIEW", "CREATE", "EDIT", "APPROVE", "PRINT", "EXPORT", "MANAGE"]),
        ("fees", "Configurable Admission Fees & Receipts", ["VIEW", "CREATE", "EDIT", "PRINT", "REFUND", "MANAGE"]),
        ("reports", "Admission Funnel & Conversion Statistics", ["VIEW", "PRINT", "EXPORT"]),
    ],
    "TEACHERS": [
        ("directory", "Faculty Directory", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "EXPORT", "IMPORT"]),
    ],
    "STAFF": [
        ("directory", "Non-Teaching Staff Directory", ["VIEW", "CREATE", "EDIT", "DELETE", "EXPORT"]),
    ],
    "HR": [
        ("directory", "HR Employee Directory & Profiles", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "EXPORT"]),
        ("contracts", "Employee Contracts & Lifecycle (Join/Promote/Transfer)", ["VIEW", "CREATE", "EDIT", "APPROVE", "MANAGE"]),
        ("leave", "Leave Management & Approvals", ["VIEW", "CREATE", "EDIT", "APPROVE", "EXPORT"]),
        ("attendance", "Employee Attendance Tracking", ["VIEW", "CREATE", "EDIT", "EXPORT"]),
        ("documents", "Employee Documents & Credentials", ["VIEW", "CREATE", "EDIT", "DELETE", "APPROVE"]),
        ("evaluations", "Performance Evaluations", ["VIEW", "CREATE", "EDIT", "APPROVE", "EXPORT"]),
        ("salary", "Confidential Compensation & Salary History", ["VIEW", "CREATE", "EDIT", "APPROVE", "EXPORT", "MANAGE"]),
        ("reports", "HR Analytics & Reports", ["VIEW", "PRINT", "EXPORT"]),
    ],
    "PAYROLL": [
        ("structures", "Salary Structures, Allowances, PF & Tax Configuration", ["VIEW", "CREATE", "EDIT", "DELETE", "MANAGE"]),
        ("processing", "Monthly Payroll Runs, Finalization & Period Locking", ["VIEW", "CREATE", "EDIT", "APPROVE", "MANAGE"]),
        ("disbursement", "Salary Disbursement & Payment Posting", ["VIEW", "CREATE", "PRINT", "EXPORT", "APPROVE", "MANAGE"]),
        ("loans", "Employee Loans & Salary Advances", ["VIEW", "CREATE", "EDIT", "APPROVE", "MANAGE"]),
        ("reversals", "Audit-Safe Payroll Reversals & Adjustments", ["VIEW", "CREATE", "APPROVE", "REFUND", "MANAGE"]),
        ("reports", "Salary Slips, Payroll Register & Employee Payment History", ["VIEW", "PRINT", "EXPORT"]),
    ],
    "ACADEMICS": [
        ("structure", "Academic Years, Classes, Sections, Groups, Shifts & Rooms", ["VIEW", "CREATE", "EDIT", "DELETE", "MANAGE"]),
        ("curriculum", "Departments, Subjects, Optional Subjects & Teacher Assignments", ["VIEW", "CREATE", "EDIT", "DELETE", "MANAGE"]),
        ("calendar", "Academic Calendar & Institutional Events", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "EXPORT"]),
        ("movements", "Promotions, Bulk Promotions & Class/Section Transfers", ["VIEW", "CREATE", "APPROVE", "MANAGE"]),
    ],
    "ATTENDANCE": [
        ("register", "Student, Teacher & Staff Attendance Register", ["VIEW", "CREATE", "EDIT", "PRINT", "EXPORT", "MANAGE"]),
        ("corrections", "Attendance Correction Requests & Approvals", ["VIEW", "CREATE", "APPROVE", "MANAGE"]),
        ("analytics", "Attendance Analytics & Risk Reports", ["VIEW", "PRINT", "EXPORT"]),
        ("devices", "Optional QR/RFID/Biometric/Face Integration", ["VIEW", "CREATE", "EDIT", "MANAGE"]),
    ],
    "FEES": [
        ("invoices", "Fee Structures & Student Invoices", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "EXPORT", "MANAGE"]),
        ("collection", "Fee Payments, Waivers, Advances & Refunds", ["VIEW", "CREATE", "PRINT", "EXPORT", "APPROVE", "REFUND"]),
        ("reports", "Due, Collection & Fee Audit Reports", ["VIEW", "PRINT", "EXPORT"]),
    ],
    "ACCOUNTING": [
        ("ledger", "Cash Book, General Ledger & Income/Expense Vouchers", ["VIEW", "CREATE", "EDIT", "EXPORT", "APPROVE", "REFUND", "MANAGE"]),
        ("budgets", "Institutional Budgets & Variance Tracking", ["VIEW", "CREATE", "EDIT", "APPROVE", "EXPORT", "MANAGE"]),
        ("reports", "Financial Statements & Audit Trail", ["VIEW", "PRINT", "EXPORT"]),
    ],
    "EXAMS": [
        ("schedules", "Exam Types, Terms & Routine Schedules", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "MANAGE"]),
        ("question_bank", "Question Bank, Written & MCQ Assessments", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "MANAGE"]),
        ("grading", "Customizable Grading Systems & Rules", ["VIEW", "CREATE", "EDIT", "DELETE", "MANAGE"]),
        ("marks", "Marks Entry & Tabulation Results", ["VIEW", "CREATE", "EDIT", "PRINT", "EXPORT", "IMPORT", "APPROVE", "MANAGE"]),
        ("verification", "Result Verification, Approval, Publish Lock & History", ["VIEW", "CREATE", "EDIT", "APPROVE", "MANAGE"]),
    ],
    "TIMETABLE": [
        ("routines", "Class, Teacher & Room Routines & Period Slots", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "EXPORT", "MANAGE"]),
        ("auto_scheduler", "Automated Timetable Suggestion Engine", ["VIEW", "CREATE", "APPROVE", "MANAGE"]),
        ("history", "Academic Year Timetable History & Cloning", ["VIEW", "CREATE", "EXPORT"]),
    ],
    "LIBRARY": [
        ("catalog", "Books, Authors, Publishers, Categories, Shelves & Barcodes", ["VIEW", "CREATE", "EDIT", "DELETE", "IMPORT", "EXPORT", "PRINT", "MANAGE"]),
        ("circulation", "Book Issue, Return, Renewal & Reservations", ["VIEW", "CREATE", "EDIT", "DELETE", "APPROVE", "MANAGE"]),
        ("members", "Library Members & Barcode/QR Library Cards", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "MANAGE"]),
        ("fines", "Fines, Lost & Damaged Book Incidents", ["VIEW", "CREATE", "EDIT", "APPROVE", "EXPORT", "MANAGE"]),
        ("reports", "Borrowing History, Fine & Inventory Reports", ["VIEW", "PRINT", "EXPORT"]),
    ],
    "TRANSPORT": [
        ("fleet", "Vehicles, Registrations, Crew & Passenger Allocations", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "EXPORT", "MANAGE"]),
        ("routes", "Transit Routes & Pickup Points", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "MANAGE"]),
        ("fees", "Transport Fee Billing & Collection", ["VIEW", "CREATE", "EDIT", "PRINT", "EXPORT", "MANAGE"]),
        ("maintenance", "Fuel, Maintenance Logs, Insurance, Documents & Reminders", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "EXPORT", "MANAGE"]),
        ("gps", "Optional GPS Device Registry & Telemetry Feeds", ["VIEW", "CREATE", "EDIT", "MANAGE"]),
    ],
    "HOSTEL": [
        ("dormitory", "Hostel Blocks, Rooms & Gate Passes", ["VIEW", "CREATE", "EDIT", "DELETE", "APPROVE", "MANAGE"]),
    ],
    "INVENTORY": [
        ("stock", "Campus Assets & Stock Ledger", ["VIEW", "CREATE", "EDIT", "DELETE", "EXPORT", "APPROVE", "MANAGE"]),
    ],
    "NOTICES": [
        ("bulletins", "Notices & Academic Calendar Events", ["VIEW", "CREATE", "EDIT", "DELETE", "APPROVE", "MANAGE"]),
    ],
    "REPORTS": [
        ("analytics", "Operational & Financial Reports", ["VIEW", "PRINT", "EXPORT"]),
    ],
    "CERTIFICATES": [
        ("credentials", "Official Certificates & ID Cards", ["VIEW", "CREATE", "PRINT", "EXPORT", "APPROVE", "MANAGE"]),
    ],
    "SECURITY": [
        ("users", "User Accounts & Password Resets", ["VIEW", "CREATE", "EDIT", "DELETE", "MANAGE"]),
        ("roles", "Roles & Permission Matrix", ["VIEW", "CREATE", "EDIT", "DELETE", "MANAGE"]),
        ("audit", "Login History & Security Activity Logs", ["VIEW", "EXPORT"]),
    ],
    "SETTINGS": [
        ("preferences", "School Profile & System Preferences", ["VIEW", "EDIT", "MANAGE"]),
    ],
}

# Mapping between main sidebar module keys and required Module VIEW access
SIDEBAR_MODULE_PERMISSION_MAP: Dict[str, str] = {
    "dashboard": "DASHBOARD",
    "students": "STUDENTS",
    "admissions": "ADMISSIONS",
    "teachers": "TEACHERS",
    "staff": "STAFF",
    "hr": "HR",
    "payroll": "PAYROLL",
    "academics": "ACADEMICS",
    "attendance": "ATTENDANCE",
    "fees": "FEES",
    "accounting": "ACCOUNTING",
    "exams": "EXAMS",
    "results": "EXAMS",
    "timetable": "TIMETABLE",
    "library": "LIBRARY",
    "transport": "TRANSPORT",
    "hostel": "HOSTEL",
    "notices": "NOTICES",
    "events": "NOTICES",
    "reports": "REPORTS",
    "certificates": "CERTIFICATES",
    "settings": "SETTINGS",  # Also accessible if SECURITY VIEW is granted
}

# Backward-compatibility aliases for any legacy code checking module.action codes
LEGACY_PERMISSION_ALIASES: Dict[str, str] = {
    "students.view": "students.directory.VIEW",
    "students.create": "students.directory.CREATE",
    "students.edit": "students.directory.EDIT",
    "students.delete": "students.directory.DELETE",
    "teachers.view": "teachers.directory.VIEW",
    "teachers.manage": "teachers.directory.EDIT",
    "fees.collect": "fees.collection.CREATE",
    "fees.view": "fees.collection.VIEW",
    "accounting.manage": "accounting.ledger.MANAGE",
    "attendance.mark": "attendance.register.CREATE",
    "exams.marks": "exams.marks.CREATE",
    "reports.view": "reports.analytics.VIEW",
    "settings.manage": "settings.preferences.MANAGE",
}


def make_permission_code(module: str, feature_slug: str, action: str) -> str:
    return f"{module.strip().lower()}.{feature_slug.strip().lower()}.{action.strip().upper()}"


def normalize_permission_code(code: str) -> str:
    stripped = (code or "").strip()
    return LEGACY_PERMISSION_ALIASES.get(stripped.lower(), stripped)


def build_permission_catalog() -> List[Dict[str, str]]:
    """Build flat list of hierarchical permission definitions for database seeding."""
    items: List[Dict[str, str]] = []
    for module, features in MODULE_FEATURE_CATALOG.items():
        for feature_slug, feature_label, actions in features:
            for action in actions:
                code = make_permission_code(module, feature_slug, action)
                items.append(
                    {
                        "code": code,
                        "module": module,
                        "feature": feature_label,
                        "action": action,
                        "name": f"{feature_label} — {action}",
                        "description": f"Allow {action} on {feature_label} ({module})",
                    }
                )
    return items


def default_permission_codes_for_role(role_name: str, all_codes: List[str]) -> List[str]:
    """Return initial curated permission codes for built-in operational roles."""
    name = role_name.lower()
    if name in ("super_admin", "administrator"):
        # Administrator gets all school operational modules + view security audit; super_admin has full override
        if name == "super_admin":
            return list(all_codes)
        return [c for c in all_codes if not c.startswith("security.roles.")]

    if name == "teacher":
        return [
            c
            for c in all_codes
            if any(
                c.startswith(prefix)
                for prefix in (
                    "dashboard.overview.VIEW",
                    "students.directory.VIEW",
                    "academics.structure.VIEW",
                    "academics.curriculum.VIEW",
                    "academics.calendar.VIEW",
                    "attendance.register.",
                    "attendance.corrections.VIEW",
                    "attendance.corrections.CREATE",
                    "attendance.analytics.VIEW",
                    "exams.schedules.VIEW",
                    "exams.question_bank.VIEW",
                    "exams.question_bank.CREATE",
                    "exams.question_bank.EDIT",
                    "exams.question_bank.PRINT",
                    "exams.grading.VIEW",
                    "exams.marks.VIEW",
                    "exams.marks.CREATE",
                    "exams.marks.EDIT",
                    "exams.marks.PRINT",
                    "exams.verification.VIEW",
                    "exams.verification.CREATE",
                    "timetable.routines.VIEW",
                    "timetable.routines.PRINT",
                    "timetable.history.VIEW",
                    "library.catalog.VIEW",
                    "library.circulation.VIEW",
                    "library.reports.VIEW",
                    "notices.bulletins.VIEW",
                    "hr.leave.VIEW",
                    "hr.leave.CREATE",
                )
            )
        ]

    if name == "accountant":
        return [
            c
            for c in all_codes
            if any(
                c.startswith(prefix)
                for prefix in (
                    "dashboard.overview.VIEW",
                    "students.directory.VIEW",
                    "admissions.applications.VIEW",
                    "admissions.fees.",
                    "admissions.reports.VIEW",
                    "fees.",
                    "accounting.",
                    "reports.",
                    "inventory.stock.VIEW",
                    "notices.bulletins.VIEW",
                    "hr.directory.VIEW",
                    "hr.salary.VIEW",
                    "hr.salary.EXPORT",
                    "hr.reports.VIEW",
                    "hr.reports.EXPORT",
                    "payroll.",
                    "transport.fees.",
                )
            )
        ]

    if name == "receptionist":
        return [
            c
            for c in all_codes
            if any(
                c.startswith(prefix)
                for prefix in (
                    "dashboard.overview.VIEW",
                    "students.directory.VIEW",
                    "students.directory.CREATE",
                    "admissions.applications.VIEW",
                    "admissions.applications.CREATE",
                    "admissions.applications.EDIT",
                    "admissions.applications.PRINT",
                    "admissions.fees.VIEW",
                    "admissions.fees.CREATE",
                    "admissions.fees.PRINT",
                    "teachers.directory.VIEW",
                    "staff.directory.VIEW",
                    "hr.directory.VIEW",
                    "hr.attendance.VIEW",
                    "hr.leave.VIEW",
                    "hr.leave.CREATE",
                    "attendance.register.VIEW",
                    "attendance.analytics.VIEW",
                    "notices.bulletins.",
                    "certificates.credentials.VIEW",
                    "certificates.credentials.CREATE",
                    "certificates.credentials.PRINT",
                    "transport.fleet.VIEW",
                    "transport.routes.VIEW",
                    "hostel.dormitory.VIEW",
                )
            )
        ]

    if name == "librarian":
        return [
            c
            for c in all_codes
            if any(
                c.startswith(prefix)
                for prefix in (
                    "dashboard.overview.VIEW",
                    "students.directory.VIEW",
                    "library.",
                    "notices.bulletins.VIEW",
                )
            )
        ]

    if name == "student_guardian":
        return [
            "dashboard.overview.VIEW",
            "attendance.register.VIEW",
            "fees.collection.VIEW",
            "exams.marks.VIEW",
            "timetable.routines.VIEW",
            "notices.bulletins.VIEW",
        ]

    return []
