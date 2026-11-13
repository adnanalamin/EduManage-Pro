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
    "ACADEMICS": [
        ("structure", "Academic Years, Classes, Sections & Subjects", ["VIEW", "CREATE", "EDIT", "DELETE", "MANAGE"]),
    ],
    "ATTENDANCE": [
        ("register", "Student & Faculty Attendance Register", ["VIEW", "CREATE", "EDIT", "PRINT", "EXPORT"]),
    ],
    "FEES": [
        ("invoices", "Fee Structures & Student Invoices", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "MANAGE"]),
        ("collection", "Fee Payments, Waivers & Refunds", ["VIEW", "CREATE", "PRINT", "EXPORT", "APPROVE", "REFUND"]),
    ],
    "ACCOUNTING": [
        ("ledger", "Cash Book, Income & Expense Vouchers", ["VIEW", "CREATE", "EDIT", "DELETE", "EXPORT", "APPROVE", "MANAGE"]),
    ],
    "EXAMS": [
        ("schedules", "Exam Terms & Routine Schedules", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "MANAGE"]),
        ("marks", "Marks Entry & Tabulation Results", ["VIEW", "CREATE", "EDIT", "PRINT", "EXPORT", "IMPORT", "APPROVE"]),
    ],
    "TIMETABLE": [
        ("routines", "Period Slots & Class Routines", ["VIEW", "CREATE", "EDIT", "DELETE", "PRINT", "MANAGE"]),
    ],
    "LIBRARY": [
        ("circulation", "Book Catalog, Members & Circulation", ["VIEW", "CREATE", "EDIT", "DELETE", "MANAGE"]),
    ],
    "TRANSPORT": [
        ("fleet", "Vehicles, Routes & Passenger Allocations", ["VIEW", "CREATE", "EDIT", "DELETE", "MANAGE"]),
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
    "teachers": "TEACHERS",
    "staff": "STAFF",
    "hr": "HR",
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
                    "attendance.register.",
                    "exams.schedules.VIEW",
                    "exams.marks.VIEW",
                    "exams.marks.CREATE",
                    "exams.marks.EDIT",
                    "exams.marks.PRINT",
                    "timetable.routines.VIEW",
                    "library.circulation.VIEW",
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
                    "teachers.directory.VIEW",
                    "staff.directory.VIEW",
                    "hr.directory.VIEW",
                    "hr.attendance.VIEW",
                    "hr.leave.VIEW",
                    "hr.leave.CREATE",
                    "notices.bulletins.",
                    "certificates.credentials.VIEW",
                    "certificates.credentials.CREATE",
                    "certificates.credentials.PRINT",
                    "transport.fleet.VIEW",
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
