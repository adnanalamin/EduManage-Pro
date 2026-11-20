"""
EduManage Pro - Professional 11-Domain Dynamic Reporting Engine
Supports:
  1. Student Reports
  2. Attendance Reports
  3. Finance Reports (Fees & Accounting Ledger)
  4. Payroll Reports
  5. Academic Reports
  6. Exam Reports
  7. Library Reports
  8. Transport Reports
  9. Hostel Reports
 10. Inventory & Fixed Asset Reports
 11. HR Reports

Capabilities:
- Dynamic Report Builder: Column selection, custom multi-criteria filters,
  Grouping with numeric aggregations (count/sum/avg), Multi-type Sorting (Asc/Desc),
  Date Range filtering, and Academic Year scoping.
- Saved Report Definitions stored in SQLite/PostgreSQL.
- Universal Export to Excel (.xlsx) and CSV (.csv) (plus PDF via DynamicReportPDFGenerator).
"""

from collections import defaultdict
from datetime import date, datetime
import csv
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.models.accounting import AccountTransaction
from app.models.attendance import StaffAttendance, StudentAttendance, TeacherAttendance
from app.models.exam import ExamResultSummary, ExamTerm
from app.models.fee import StudentFee
from app.models.hostel import HostelAllocation, HostelFeeCharge, HostelRoom
from app.models.inventory import FixedAsset, InventoryItem
from app.models.library import Book, BookCirculation, LibraryFine
from app.models.payroll import PayrollPayslip, PayrollPeriodRun
from app.models.report import SavedReportDefinition
from app.models.staff import EmployeeContract, EmployeeLeaveRequest, EmployeePerformanceEvaluation, Staff, Teacher
from app.models.student import Student
from app.models.transport import TransportFeeCharge, TransportMaintenanceLog, TransportPassenger, Vehicle


def _parse_date(val: Any) -> Optional[date]:
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


def _fmt_date(val: Any) -> str:
    if val is None or val == "":
        return ""
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, date):
        return val.strftime("%Y-%m-%d")
    return str(val)


def _to_float(val: Any) -> Optional[float]:
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


# Declarative Catalog for all 11 Reporting Domains
REPORT_DOMAIN_CATALOG: Dict[str, Dict[str, Any]] = {
    "students": {
        "label": "Student Reports",
        "description": "Enrolled students, class & section placement, demographics, guardian contacts & status",
        "date_field": "admission_date",
        "supports_academic_year": True,
        "columns": [
            {"key": "admission_number", "label": "Admission No", "type": "str"},
            {"key": "student_id", "label": "Student ID", "type": "str"},
            {"key": "full_name", "label": "Student Name", "type": "str"},
            {"key": "class_name", "label": "Class", "type": "str"},
            {"key": "section_name", "label": "Section", "type": "str"},
            {"key": "roll_number", "label": "Roll No", "type": "num"},
            {"key": "gender", "label": "Gender", "type": "str"},
            {"key": "blood_group", "label": "Blood Group", "type": "str"},
            {"key": "group_stream", "label": "Group", "type": "str"},
            {"key": "shift", "label": "Shift", "type": "str"},
            {"key": "guardian_name", "label": "Guardian Name", "type": "str"},
            {"key": "guardian_phone", "label": "Guardian Phone", "type": "str"},
            {"key": "admission_date", "label": "Admission Date", "type": "date"},
            {"key": "academic_year", "label": "Academic Year", "type": "str"},
            {"key": "status", "label": "Status", "type": "str"},
        ],
    },
    "attendance": {
        "label": "Attendance Reports",
        "description": "Student, Teacher, and Staff attendance logs with check-in/out times and capture source",
        "date_field": "attendance_date",
        "supports_academic_year": True,
        "columns": [
            {"key": "record_type", "label": "Person Type", "type": "str"},
            {"key": "person_code", "label": "ID / Code", "type": "str"},
            {"key": "person_name", "label": "Full Name", "type": "str"},
            {"key": "class_or_dept", "label": "Class / Dept", "type": "str"},
            {"key": "section", "label": "Section", "type": "str"},
            {"key": "attendance_date", "label": "Date", "type": "date"},
            {"key": "status", "label": "Status", "type": "str"},
            {"key": "check_in_time", "label": "Check-In", "type": "str"},
            {"key": "check_out_time", "label": "Check-Out", "type": "str"},
            {"key": "capture_source", "label": "Source", "type": "str"},
            {"key": "academic_year", "label": "Academic Year", "type": "str"},
            {"key": "remarks", "label": "Remarks", "type": "str"},
        ],
    },
    "finance": {
        "label": "Finance Reports",
        "description": "Student fee billing, collections & arrears alongside Accounting income/expense vouchers",
        "date_field": "transaction_date",
        "supports_academic_year": True,
        "columns": [
            {"key": "entry_type", "label": "Record Type", "type": "str"},
            {"key": "reference_no", "label": "Invoice / Voucher", "type": "str"},
            {"key": "category", "label": "Category", "type": "str"},
            {"key": "party_name", "label": "Student / Party", "type": "str"},
            {"key": "class_name", "label": "Class", "type": "str"},
            {"key": "title", "label": "Description", "type": "str"},
            {"key": "gross_amount", "label": "Gross Amount", "type": "num"},
            {"key": "discount_amount", "label": "Concession", "type": "num"},
            {"key": "net_amount", "label": "Net Amount", "type": "num"},
            {"key": "paid_amount", "label": "Paid / Realized", "type": "num"},
            {"key": "due_amount", "label": "Balance Due", "type": "num"},
            {"key": "payment_method", "label": "Channel", "type": "str"},
            {"key": "transaction_date", "label": "Date", "type": "date"},
            {"key": "academic_year", "label": "Academic Year", "type": "str"},
            {"key": "status", "label": "Status", "type": "str"},
        ],
    },
    "payroll": {
        "label": "Payroll Reports",
        "description": "Monthly employee payslips, earnings, overtime, bonuses, attendance/leave/tax/loan deductions & net pay",
        "date_field": "period_start",
        "supports_academic_year": True,
        "columns": [
            {"key": "slip_no", "label": "Payslip No", "type": "str"},
            {"key": "run_code", "label": "Run Code", "type": "str"},
            {"key": "employee_code", "label": "Emp ID", "type": "str"},
            {"key": "employee_name", "label": "Employee Name", "type": "str"},
            {"key": "employee_type", "label": "Emp Type", "type": "str"},
            {"key": "designation", "label": "Designation", "type": "str"},
            {"key": "department_name", "label": "Department", "type": "str"},
            {"key": "payroll_period", "label": "Period", "type": "str"},
            {"key": "basic_salary", "label": "Basic Salary", "type": "num"},
            {"key": "total_allowances", "label": "Allowances", "type": "num"},
            {"key": "overtime_amount", "label": "Overtime", "type": "num"},
            {"key": "bonus_amount", "label": "Bonus", "type": "num"},
            {"key": "gross_earnings", "label": "Gross Pay", "type": "num"},
            {"key": "attendance_deduction", "label": "Att. Ded.", "type": "num"},
            {"key": "leave_deduction", "label": "Leave Ded.", "type": "num"},
            {"key": "tax_deduction", "label": "Tax (TDS)", "type": "num"},
            {"key": "loan_deduction", "label": "Loan Ded.", "type": "num"},
            {"key": "advance_deduction", "label": "Advance Ded.", "type": "num"},
            {"key": "total_deductions", "label": "Total Ded.", "type": "num"},
            {"key": "net_payable", "label": "Net Payable", "type": "num"},
            {"key": "payment_status", "label": "Status", "type": "str"},
            {"key": "paid_date", "label": "Paid Date", "type": "date"},
            {"key": "period_start", "label": "Period Start", "type": "date"},
            {"key": "academic_year", "label": "Academic Year", "type": "str"},
        ],
    },
    "academic": {
        "label": "Academic Reports",
        "description": "Classes, streams, shifts, subject curriculum allocations, credit hours, full/pass marks & class size",
        "date_field": "year_start_date",
        "supports_academic_year": True,
        "columns": [
            {"key": "academic_year", "label": "Academic Year", "type": "str"},
            {"key": "class_name", "label": "Class", "type": "str"},
            {"key": "group_stream", "label": "Group / Stream", "type": "str"},
            {"key": "shift", "label": "Shift", "type": "str"},
            {"key": "subject_code", "label": "Subject Code", "type": "str"},
            {"key": "subject_name", "label": "Subject", "type": "str"},
            {"key": "subject_type", "label": "Type", "type": "str"},
            {"key": "teacher_name", "label": "Assigned Teacher", "type": "str"},
            {"key": "sections_count", "label": "Sections", "type": "num"},
            {"key": "enrolled_students", "label": "Class Students", "type": "num"},
            {"key": "full_marks", "label": "Full Marks", "type": "num"},
            {"key": "pass_marks", "label": "Pass Marks", "type": "num"},
            {"key": "credit_hours", "label": "Credits", "type": "num"},
            {"key": "year_start_date", "label": "Year Start", "type": "date"},
            {"key": "status", "label": "Status", "type": "str"},
        ],
    },
    "exam": {
        "label": "Exam Reports",
        "description": "Exam terms, compiled student scores, percentages, GPA, CGPA, merit positions & approval lock status",
        "date_field": "term_start_date",
        "supports_academic_year": True,
        "columns": [
            {"key": "exam_term", "label": "Exam Term", "type": "str"},
            {"key": "exam_code", "label": "Exam Code", "type": "str"},
            {"key": "exam_type", "label": "Exam Type", "type": "str"},
            {"key": "academic_year", "label": "Academic Year", "type": "str"},
            {"key": "class_name", "label": "Class", "type": "str"},
            {"key": "admission_number", "label": "Admission No", "type": "str"},
            {"key": "student_name", "label": "Student Name", "type": "str"},
            {"key": "total_obtained", "label": "Obtained", "type": "num"},
            {"key": "total_full_marks", "label": "Full Marks", "type": "num"},
            {"key": "percentage", "label": "Percent (%)", "type": "num"},
            {"key": "gpa", "label": "GPA", "type": "num"},
            {"key": "cgpa", "label": "CGPA", "type": "num"},
            {"key": "overall_grade", "label": "Grade", "type": "str"},
            {"key": "class_rank", "label": "Class Pos", "type": "num"},
            {"key": "section_rank", "label": "Section Pos", "type": "num"},
            {"key": "passed_status", "label": "Pass / Fail", "type": "str"},
            {"key": "result_status", "label": "Workflow", "type": "str"},
            {"key": "is_published", "label": "Published", "type": "str"},
            {"key": "term_start_date", "label": "Term Date", "type": "date"},
        ],
    },
    "library": {
        "label": "Library Reports",
        "description": "Catalog inventory, active/overdue circulations, return history, and library fines",
        "date_field": "event_date",
        "supports_academic_year": False,
        "columns": [
            {"key": "record_kind", "label": "Record Kind", "type": "str"},
            {"key": "accession_no", "label": "Accession / Code", "type": "str"},
            {"key": "book_title", "label": "Book Title", "type": "str"},
            {"key": "author", "label": "Author", "type": "str"},
            {"key": "category", "label": "Category", "type": "str"},
            {"key": "isbn", "label": "ISBN", "type": "str"},
            {"key": "member_id", "label": "Member ID", "type": "str"},
            {"key": "member_name", "label": "Member Name", "type": "str"},
            {"key": "event_date", "label": "Issue / Assessed Date", "type": "date"},
            {"key": "due_date", "label": "Due Date", "type": "date"},
            {"key": "return_date", "label": "Return Date", "type": "date"},
            {"key": "total_copies", "label": "Total Copies", "type": "num"},
            {"key": "available_copies", "label": "Available", "type": "num"},
            {"key": "fine_amount", "label": "Fine Amount", "type": "num"},
            {"key": "status", "label": "Status", "type": "str"},
        ],
    },
    "transport": {
        "label": "Transport Reports",
        "description": "Fleet vehicles, routes, passenger seat assignments, transport fees, and maintenance costs",
        "date_field": "event_date",
        "supports_academic_year": False,
        "columns": [
            {"key": "record_type", "label": "Record Type", "type": "str"},
            {"key": "vehicle_number", "label": "Vehicle No", "type": "str"},
            {"key": "vehicle_type", "label": "Vehicle Type", "type": "str"},
            {"key": "registration_no", "label": "Registration", "type": "str"},
            {"key": "driver_name", "label": "Driver", "type": "str"},
            {"key": "route_code", "label": "Route Code", "type": "str"},
            {"key": "route_name", "label": "Route Name", "type": "str"},
            {"key": "stop_name", "label": "Pickup Point", "type": "str"},
            {"key": "passenger_name", "label": "Passenger / Workshop", "type": "str"},
            {"key": "amount_or_fare", "label": "Monthly Fare / Cost", "type": "num"},
            {"key": "paid_amount", "label": "Paid Amount", "type": "num"},
            {"key": "balance_due", "label": "Balance Due", "type": "num"},
            {"key": "odometer_km", "label": "Odometer (km)", "type": "num"},
            {"key": "event_date", "label": "Date", "type": "date"},
            {"key": "status", "label": "Status", "type": "str"},
        ],
    },
    "hostel": {
        "label": "Hostel Reports",
        "description": "Dormitory buildings, rooms, beds, student check-in/out allocations, and hostel/mess fees",
        "date_field": "event_date",
        "supports_academic_year": False,
        "columns": [
            {"key": "block_name", "label": "Hostel Building", "type": "str"},
            {"key": "gender_type", "label": "Wing Type", "type": "str"},
            {"key": "floor_number", "label": "Floor", "type": "num"},
            {"key": "room_number", "label": "Room No", "type": "str"},
            {"key": "room_type", "label": "Room Type", "type": "str"},
            {"key": "capacity", "label": "Room Cap", "type": "num"},
            {"key": "bed_number", "label": "Bed No", "type": "str"},
            {"key": "admission_number", "label": "Admission No", "type": "str"},
            {"key": "student_name", "label": "Boarder Name", "type": "str"},
            {"key": "event_date", "label": "Check-In / Adm Date", "type": "date"},
            {"key": "check_out_date", "label": "Check-Out Date", "type": "date"},
            {"key": "monthly_fee", "label": "Monthly Fee", "type": "num"},
            {"key": "total_billed_fees", "label": "Billed Fees", "type": "num"},
            {"key": "paid_fees", "label": "Paid Fees", "type": "num"},
            {"key": "clearance_status", "label": "Clearance", "type": "str"},
            {"key": "status", "label": "Status", "type": "str"},
        ],
    },
    "inventory": {
        "label": "Inventory & Asset Reports",
        "description": "Catalog products, stock levels, low-stock alerts, valuation, and Fixed Asset custody/warranty",
        "date_field": "record_date",
        "supports_academic_year": False,
        "columns": [
            {"key": "record_kind", "label": "Record Kind", "type": "str"},
            {"key": "code_or_asset_id", "label": "Item / Asset ID", "type": "str"},
            {"key": "name", "label": "Product / Asset Name", "type": "str"},
            {"key": "category", "label": "Category", "type": "str"},
            {"key": "item_type", "label": "Type", "type": "str"},
            {"key": "supplier", "label": "Supplier", "type": "str"},
            {"key": "serial_number", "label": "Serial Number", "type": "str"},
            {"key": "location", "label": "Location", "type": "str"},
            {"key": "department", "label": "Department", "type": "str"},
            {"key": "assigned_employee", "label": "Assigned Employee", "type": "str"},
            {"key": "quantity", "label": "Qty", "type": "num"},
            {"key": "reorder_level", "label": "Reorder Lvl", "type": "num"},
            {"key": "unit_cost", "label": "Unit Cost", "type": "num"},
            {"key": "total_value", "label": "Total Value / Cost", "type": "num"},
            {"key": "low_stock_alert", "label": "Low Stock Alert", "type": "str"},
            {"key": "record_date", "label": "Purchase / Entry Date", "type": "date"},
            {"key": "warranty", "label": "Warranty", "type": "str"},
            {"key": "status", "label": "Status", "type": "str"},
        ],
    },
    "hr": {
        "label": "HR Reports",
        "description": "Teachers & Staff directory, departments, contract types, salaries, leave usage & evaluations",
        "date_field": "joining_date",
        "supports_academic_year": False,
        "columns": [
            {"key": "employee_code", "label": "Employee ID", "type": "str"},
            {"key": "employee_type", "label": "Category", "type": "str"},
            {"key": "full_name", "label": "Full Name", "type": "str"},
            {"key": "gender", "label": "Gender", "type": "str"},
            {"key": "department", "label": "Department", "type": "str"},
            {"key": "designation_or_position", "label": "Designation / Role", "type": "str"},
            {"key": "contract_type", "label": "Contract", "type": "str"},
            {"key": "joining_date", "label": "Joining Date", "type": "date"},
            {"key": "salary", "label": "Base Salary", "type": "num"},
            {"key": "approved_leave_days", "label": "Approved Leave Days", "type": "num"},
            {"key": "pending_leaves", "label": "Pending Leaves", "type": "num"},
            {"key": "latest_rating", "label": "Perf Rating", "type": "num"},
            {"key": "phone", "label": "Phone", "type": "str"},
            {"key": "email", "label": "Email", "type": "str"},
            {"key": "status", "label": "Status", "type": "str"},
        ],
    },
}


class ReportingEngine:
    """Central 11-Domain Report Builder, Grouping/Aggregation & Export Engine."""

    @staticmethod
    def get_domain_catalog() -> Dict[str, Dict[str, Any]]:
        return REPORT_DOMAIN_CATALOG

    @staticmethod
    def list_domains() -> List[Dict[str, Any]]:
        return [
            {
                "key": key,
                "label": meta["label"],
                "description": meta["description"],
                "date_field": meta["date_field"],
                "supports_academic_year": meta["supports_academic_year"],
                "columns": meta["columns"],
            }
            for key, meta in REPORT_DOMAIN_CATALOG.items()
        ]

    @staticmethod
    def get_domain_columns(domain_key: str) -> List[Dict[str, str]]:
        if domain_key not in REPORT_DOMAIN_CATALOG:
            raise ValueError(f"Unsupported report domain '{domain_key}'.")
        return list(REPORT_DOMAIN_CATALOG[domain_key]["columns"])

    @classmethod
    def build_report(
        cls,
        db: Session,
        domain_key: str,
        selected_columns: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        group_by: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_desc: bool = False,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        academic_year_id: Optional[int] = None,
        report_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Queries real database records for the specified domain and applies:
        - Academic Year filtering (when supported)
        - Date Range filtering (`date_from`..`date_to`)
        - Multi-criteria Custom Filters (`eq`, `neq`, `contains`, `starts_with`, `gt`, `gte`, `lt`, `lte`, `in`)
        - Dynamic Sorting (`sort_by`, `sort_desc`)
        - Column Projection (`selected_columns`)
        - Dynamic Grouping with numeric Sum/Avg rollups (`group_by`)
        """
        if domain_key not in REPORT_DOMAIN_CATALOG:
            raise ValueError(f"Unsupported report domain '{domain_key}'.")

        meta = REPORT_DOMAIN_CATALOG[domain_key]
        all_cols = meta["columns"]
        col_map = {c["key"]: c for c in all_cols}

        # Validate selected columns (keep order)
        if selected_columns:
            active_col_keys = [c for c in selected_columns if c in col_map]
        else:
            active_col_keys = [c["key"] for c in all_cols]

        if not active_col_keys:
            active_col_keys = [c["key"] for c in all_cols]

        # Extract raw rows from DB for domain
        raw_rows = cls._fetch_domain_rows(db, domain_key, academic_year_id=academic_year_id)

        # Resolve academic year label for metadata
        year_label = "All Academic Years"
        if academic_year_id:
            ay = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
            year_label = ay.name if ay else f"Year #{academic_year_id}"

        # 1. Date Range Filtering
        date_field = meta.get("date_field")
        if (date_from or date_to) and date_field:
            d_from = _parse_date(date_from)
            d_to = _parse_date(date_to)
            filtered_by_date: List[Dict[str, Any]] = []
            for row in raw_rows:
                rv_date = _parse_date(row.get(date_field))
                if rv_date is None:
                    continue
                if d_from and rv_date < d_from:
                    continue
                if d_to and rv_date > d_to:
                    continue
                filtered_by_date.append(row)
            raw_rows = filtered_by_date

        # 2. Custom Attribute Filters
        applied_filters: List[Dict[str, Any]] = []
        if filters:
            for flt in filters:
                field = (flt.get("field") or "").strip()
                op = (flt.get("op") or "contains").strip().lower()
                val = flt.get("value")
                if not field or val is None or str(val).strip() == "":
                    continue
                applied_filters.append({"field": field, "op": op, "value": val})
                raw_rows = [r for r in raw_rows if cls._matches_filter(r.get(field), op, val, col_map.get(field, {}).get("type", "str"))]

        # 3. Sorting
        if sort_by and sort_by in col_map:
            col_type = col_map[sort_by]["type"]
            raw_rows.sort(
                key=lambda r: cls._sort_key(r.get(sort_by), col_type),
                reverse=bool(sort_desc),
            )

        # 4. Compute Numeric Totals on filtered dataset for selected columns
        totals: Dict[str, float] = {}
        for ck in active_col_keys:
            if col_map[ck]["type"] == "num":
                vals = [_to_float(r.get(ck)) for r in raw_rows]
                numeric_vals = [v for v in vals if v is not None]
                totals[ck] = round(sum(numeric_vals), 2) if numeric_vals else 0.0

        # 5. Project rows to selected columns
        projected_rows: List[Dict[str, Any]] = []
        for r in raw_rows:
            projected_rows.append({ck: r.get(ck) for ck in active_col_keys})

        # 6. Dynamic Grouping & Aggregations
        grouped_rows: List[Dict[str, Any]] = []
        group_columns: List[Dict[str, str]] = []
        if group_by and group_by in col_map:
            grouped_rows, group_columns = cls._compute_grouping(
                raw_rows=raw_rows,
                group_by=group_by,
                active_col_keys=active_col_keys,
                col_map=col_map,
            )

        selected_col_defs = [col_map[ck] for ck in active_col_keys]

        return {
            "domain_key": domain_key,
            "domain_label": meta["label"],
            "title": report_title or meta["label"],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "academic_year_id": academic_year_id,
            "academic_year_label": year_label,
            "date_from": _fmt_date(date_from),
            "date_to": _fmt_date(date_to),
            "filters": applied_filters,
            "sort_by": sort_by if sort_by in col_map else None,
            "sort_desc": bool(sort_desc),
            "group_by": group_by if group_by in col_map else None,
            "group_by_label": col_map[group_by]["label"] if group_by and group_by in col_map else None,
            "columns": selected_col_defs,
            "rows": projected_rows,
            "row_count": len(projected_rows),
            "totals": totals,
            "group_columns": group_columns,
            "grouped_rows": grouped_rows,
        }

    @staticmethod
    def _matches_filter(cell_val: Any, op: str, target_val: Any, col_type: str) -> bool:
        if op in ("eq", "=", "equals"):
            if col_type == "num":
                cn, tn = _to_float(cell_val), _to_float(target_val)
                return cn is not None and tn is not None and cn == tn
            if col_type == "date":
                cd, td = _parse_date(cell_val), _parse_date(target_val)
                return cd is not None and td is not None and cd == td
            return str(cell_val or "").strip().lower() == str(target_val).strip().lower()

        if op in ("neq", "!="):
            if col_type == "num":
                cn, tn = _to_float(cell_val), _to_float(target_val)
                return cn is not None and tn is not None and cn != tn
            return str(cell_val or "").strip().lower() != str(target_val).strip().lower()

        if op == "contains":
            return str(target_val).strip().lower() in str(cell_val or "").strip().lower()

        if op == "starts_with":
            return str(cell_val or "").strip().lower().startswith(str(target_val).strip().lower())

        if op == "in":
            choices = [x.strip().lower() for x in str(target_val).split(",") if x.strip()]
            return str(cell_val or "").strip().lower() in choices

        if op in ("gt", "gte", "lt", "lte", ">", ">=", "<", "<="):
            if col_type == "date":
                cd, td = _parse_date(cell_val), _parse_date(target_val)
                if cd is None or td is None:
                    return False
                if op in ("gt", ">"):
                    return cd > td
                if op in ("gte", ">="):
                    return cd >= td
                if op in ("lt", "<"):
                    return cd < td
                return cd <= td
            else:
                cn, tn = _to_float(cell_val), _to_float(target_val)
                if cn is None or tn is None:
                    return False
                if op in ("gt", ">"):
                    return cn > tn
                if op in ("gte", ">="):
                    return cn >= tn
                if op in ("lt", "<"):
                    return cn < tn
                return cn <= tn

        return str(target_val).strip().lower() in str(cell_val or "").strip().lower()

    @staticmethod
    def _sort_key(val: Any, col_type: str) -> Tuple[int, Any]:
        if val is None or val == "":
            return (1, "")
        if col_type == "num":
            n = _to_float(val)
            return (0, n if n is not None else 0.0)
        if col_type == "date":
            d = _parse_date(val)
            return (0, d or date.min)
        return (0, str(val).strip().lower())

    @staticmethod
    def _compute_grouping(
        raw_rows: List[Dict[str, Any]],
        group_by: str,
        active_col_keys: List[str],
        col_map: Dict[str, Dict[str, str]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in raw_rows:
            gval = r.get(group_by)
            gkey = str(gval) if (gval is not None and gval != "") else "(Unspecified)"
            buckets[gkey].append(r)

        numeric_cols = [ck for ck in active_col_keys if ck != group_by and col_map[ck]["type"] == "num"]
        group_columns: List[Dict[str, str]] = [
            {"key": group_by, "label": col_map[group_by]["label"], "type": "str"},
            {"key": "_record_count", "label": "Record Count", "type": "num"},
        ]
        for nck in numeric_cols:
            group_columns.append({"key": f"{nck}_sum", "label": f"Sum: {col_map[nck]['label']}", "type": "num"})
            group_columns.append({"key": f"{nck}_avg", "label": f"Avg: {col_map[nck]['label']}", "type": "num"})

        grouped_rows: List[Dict[str, Any]] = []
        for gkey in sorted(buckets.keys()):
            items = buckets[gkey]
            grow: Dict[str, Any] = {group_by: gkey, "_record_count": len(items)}
            for nck in numeric_cols:
                nums = [_to_float(it.get(nck)) for it in items]
                valid = [v for v in nums if v is not None]
                total = round(sum(valid), 2) if valid else 0.0
                avg = round(total / len(valid), 2) if valid else 0.0
                grow[f"{nck}_sum"] = total
                grow[f"{nck}_avg"] = avg
            grouped_rows.append(grow)

        return grouped_rows, group_columns

    # ------------------------------------------------------------------
    # Domain Fetchers (100% Real SQLAlchemy Queries across all 11 modules)
    # ------------------------------------------------------------------
    @classmethod
    def _fetch_domain_rows(
        cls,
        db: Session,
        domain_key: str,
        academic_year_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if domain_key == "students":
            return cls._fetch_students(db, academic_year_id)
        if domain_key == "attendance":
            return cls._fetch_attendance(db, academic_year_id)
        if domain_key == "finance":
            return cls._fetch_finance(db, academic_year_id)
        if domain_key == "payroll":
            return cls._fetch_payroll(db, academic_year_id)
        if domain_key == "academic":
            return cls._fetch_academic(db, academic_year_id)
        if domain_key == "exam":
            return cls._fetch_exam(db, academic_year_id)
        if domain_key == "library":
            return cls._fetch_library(db)
        if domain_key == "transport":
            return cls._fetch_transport(db)
        if domain_key == "hostel":
            return cls._fetch_hostel(db)
        if domain_key == "inventory":
            return cls._fetch_inventory(db)
        if domain_key == "hr":
            return cls._fetch_hr(db)
        raise ValueError(f"Unsupported domain: {domain_key}")

    @staticmethod
    def _fetch_students(db: Session, academic_year_id: Optional[int]) -> List[Dict[str, Any]]:
        q = db.query(Student).filter(Student.is_deleted == False)  # noqa: E712
        if academic_year_id:
            q = q.filter(Student.academic_year_id == academic_year_id)
        rows = []
        for s in q.order_by(Student.admission_number).all():
            rows.append({
                "admission_number": s.admission_number,
                "student_id": s.student_id,
                "full_name": s.full_name,
                "class_name": s.school_class.name if s.school_class else "N/A",
                "section_name": s.section.name if s.section else "N/A",
                "roll_number": s.roll_number,
                "gender": s.gender,
                "blood_group": s.blood_group or "",
                "group_stream": s.group or "General",
                "shift": s.shift or "Day",
                "guardian_name": s.guardian.guardian_name if s.guardian else "",
                "guardian_phone": s.guardian.guardian_phone if s.guardian else (s.emergency_contact or ""),
                "admission_date": _fmt_date(s.admission_date),
                "academic_year": s.academic_year.name if s.academic_year else "",
                "status": (s.status or "").title(),
            })
        return rows

    @staticmethod
    def _fetch_attendance(db: Session, academic_year_id: Optional[int]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        sq = db.query(StudentAttendance)
        if academic_year_id:
            sq = sq.filter(StudentAttendance.academic_year_id == academic_year_id)
        for sa in sq.order_by(StudentAttendance.date.desc(), StudentAttendance.id.desc()).all():
            st = sa.student
            rows.append({
                "record_type": "Student",
                "person_code": st.admission_number if st else str(sa.student_id),
                "person_name": st.full_name if st else f"Student #{sa.student_id}",
                "class_or_dept": sa.school_class.name if sa.school_class else "N/A",
                "section": sa.section.name if sa.section else "N/A",
                "attendance_date": _fmt_date(sa.date),
                "status": sa.status,
                "check_in_time": sa.check_in_time or "",
                "check_out_time": sa.check_out_time or "",
                "capture_source": sa.capture_source or "Manual",
                "academic_year": sa.academic_year.name if sa.academic_year else "",
                "remarks": sa.remarks or "",
            })

        # Include Teacher and Staff attendance unless strictly scoped to a specific academic year without them
        if not academic_year_id:
            for ta in db.query(TeacherAttendance).order_by(TeacherAttendance.date.desc()).all():
                t = ta.teacher
                rows.append({
                    "record_type": "Teacher",
                    "person_code": t.employee_id if t else str(ta.teacher_id),
                    "person_name": t.full_name if t else f"Teacher #{ta.teacher_id}",
                    "class_or_dept": t.department.name if t and t.department else "Faculty",
                    "section": t.primary_subject if t else "",
                    "attendance_date": _fmt_date(ta.date),
                    "status": ta.status,
                    "check_in_time": ta.check_in_time or "",
                    "check_out_time": ta.check_out_time or "",
                    "capture_source": ta.capture_source or "Manual",
                    "academic_year": "All",
                    "remarks": ta.remarks or "",
                })
            for sta in db.query(StaffAttendance).order_by(StaffAttendance.date.desc()).all():
                stf = sta.staff
                rows.append({
                    "record_type": "Staff",
                    "person_code": stf.employee_id if stf else str(sta.staff_id),
                    "person_name": stf.full_name if stf else f"Staff #{sta.staff_id}",
                    "class_or_dept": stf.department.name if stf and stf.department else "Admin/Support",
                    "section": stf.position if stf else "",
                    "attendance_date": _fmt_date(sta.date),
                    "status": sta.status,
                    "check_in_time": sta.check_in_time or "",
                    "check_out_time": sta.check_out_time or "",
                    "capture_source": sta.capture_source or "Manual",
                    "academic_year": "All",
                    "remarks": sta.remarks or "",
                })
        return rows

    @staticmethod
    def _fetch_finance(db: Session, academic_year_id: Optional[int]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        fq = db.query(StudentFee).filter(StudentFee.is_deleted == False)  # noqa: E712
        if academic_year_id:
            fq = fq.filter(StudentFee.academic_year_id == academic_year_id)
        for sf in fq.order_by(StudentFee.due_date.desc(), StudentFee.id.desc()).all():
            stu = sf.student
            cat_name = (
                sf.fee_structure.category.name
                if sf.fee_structure and sf.fee_structure.category
                else "Student Fee"
            )
            cls_name = stu.school_class.name if stu and stu.school_class else "N/A"
            rows.append({
                "entry_type": "Fee Invoice",
                "reference_no": sf.invoice_number,
                "category": cat_name,
                "party_name": stu.full_name if stu else f"Student #{sf.student_id}",
                "class_name": cls_name,
                "title": sf.display_title,
                "gross_amount": round(float(sf.total_amount or 0.0), 2),
                "discount_amount": round(float(sf.discount_amount or 0.0), 2),
                "net_amount": round(float(sf.net_amount if sf.net_amount is not None else sf.total_amount or 0.0), 2),
                "paid_amount": round(float(sf.paid_amount or 0.0), 2),
                "due_amount": round(float(sf.due_amount or 0.0), 2),
                "payment_method": "Invoice",
                "transaction_date": _fmt_date(sf.due_date),
                "academic_year": sf.academic_year.name if sf.academic_year else "",
                "status": sf.status,
            })

        tq = db.query(AccountTransaction).filter(AccountTransaction.is_deleted == False)  # noqa: E712
        if academic_year_id:
            tq = tq.filter(AccountTransaction.academic_year_id == academic_year_id)
        for tx in tq.order_by(AccountTransaction.transaction_date.desc(), AccountTransaction.id.desc()).all():
            amt = round(float(tx.amount or 0.0), 2)
            rows.append({
                "entry_type": f"Accounting {tx.type}",
                "reference_no": tx.voucher_no,
                "category": tx.category.name if tx.category else tx.entry_kind,
                "party_name": tx.paid_to_received_from,
                "class_name": "-",
                "title": tx.description or tx.entry_kind,
                "gross_amount": amt,
                "discount_amount": 0.0,
                "net_amount": amt,
                "paid_amount": amt if tx.type == "Income" else 0.0,
                "due_amount": amt if tx.type == "Expense" else 0.0,
                "payment_method": tx.payment_method,
                "transaction_date": _fmt_date(tx.transaction_date),
                "academic_year": tx.academic_year.name if tx.academic_year else "",
                "status": tx.status,
            })

        return rows

    @staticmethod
    def _fetch_payroll(db: Session, academic_year_id: Optional[int]) -> List[Dict[str, Any]]:
        q = (
            db.query(PayrollPayslip)
            .join(PayrollPeriodRun, PayrollPayslip.payroll_run_id == PayrollPeriodRun.id)
            .filter(PayrollPayslip.is_deleted == False)  # noqa: E712
        )
        if academic_year_id:
            q = q.filter(PayrollPeriodRun.academic_year_id == academic_year_id)

        rows: List[Dict[str, Any]] = []
        for ps in q.order_by(PayrollPayslip.payroll_year.desc(), PayrollPayslip.payroll_month.desc(), PayrollPayslip.slip_no).all():
            run = ps.payroll_run
            rows.append({
                "slip_no": ps.slip_no,
                "run_code": run.run_code if run else "",
                "employee_code": ps.employee_code,
                "employee_name": ps.employee_name,
                "employee_type": (ps.employee_type or "").title(),
                "designation": ps.designation or "",
                "department_name": ps.department_name or "",
                "payroll_period": f"{ps.payroll_year:04d}-{ps.payroll_month:02d}",
                "basic_salary": round(float(ps.basic_salary or 0.0), 2),
                "total_allowances": ps.total_allowances,
                "overtime_amount": round(float(ps.overtime_amount or 0.0), 2),
                "bonus_amount": round(float(ps.bonus_amount or 0.0), 2),
                "gross_earnings": round(float(ps.gross_earnings or 0.0), 2),
                "attendance_deduction": round(float(ps.attendance_deduction or 0.0), 2),
                "leave_deduction": round(float(ps.leave_deduction or 0.0), 2),
                "tax_deduction": round(float(ps.tax_deduction or 0.0), 2),
                "loan_deduction": round(float(ps.loan_deduction or 0.0), 2),
                "advance_deduction": round(float(ps.advance_deduction or 0.0), 2),
                "total_deductions": round(float(ps.total_deductions or 0.0), 2),
                "net_payable": round(float(ps.net_payable or 0.0), 2),
                "payment_status": "Reversed" if ps.is_reversed else ps.payment_status,
                "paid_date": _fmt_date(ps.paid_date),
                "period_start": _fmt_date(run.period_start if run else date(ps.payroll_year, ps.payroll_month, 1)),
                "academic_year": run.academic_year.name if run and run.academic_year else "",
            })
        return rows

    @staticmethod
    def _fetch_academic(db: Session, academic_year_id: Optional[int]) -> List[Dict[str, Any]]:
        cq = db.query(SchoolClass).filter(SchoolClass.is_deleted == False)  # noqa: E712
        if academic_year_id:
            cq = cq.filter(SchoolClass.academic_year_id == academic_year_id)

        # Precompute active student counts by class_id
        stu_counts: Dict[int, int] = defaultdict(int)
        for st in db.query(Student).filter(Student.is_deleted == False).all():  # noqa: E712
            stu_counts[st.class_id] += 1

        rows: List[Dict[str, Any]] = []
        for sc in cq.order_by(SchoolClass.numeric_order, SchoolClass.name).all():
            sec_count = len([sec for sec in sc.sections if not sec.is_deleted])
            active_subjects = [sub for sub in sc.subjects if not sub.is_deleted]
            ay_name = sc.academic_year.name if sc.academic_year else ""
            ay_start = _fmt_date(sc.academic_year.start_date if sc.academic_year else None)

            if active_subjects:
                for sub in active_subjects:
                    rows.append({
                        "academic_year": ay_name,
                        "class_name": sc.name,
                        "group_stream": sc.group or "General",
                        "shift": sc.shift or "Morning",
                        "subject_code": sub.code,
                        "subject_name": sub.name,
                        "subject_type": sub.subject_type,
                        "teacher_name": sub.assigned_teacher.full_name if sub.assigned_teacher else "Unassigned",
                        "sections_count": sec_count,
                        "enrolled_students": stu_counts.get(sc.id, 0),
                        "full_marks": sub.full_marks,
                        "pass_marks": sub.pass_marks,
                        "credit_hours": float(sub.credit_hours or 1.0),
                        "year_start_date": ay_start,
                        "status": "Active" if sub.is_active else "Inactive",
                    })
            else:
                rows.append({
                    "academic_year": ay_name,
                    "class_name": sc.name,
                    "group_stream": sc.group or "General",
                    "shift": sc.shift or "Morning",
                    "subject_code": "-",
                    "subject_name": "(No subjects assigned yet)",
                    "subject_type": "-",
                    "teacher_name": "-",
                    "sections_count": sec_count,
                    "enrolled_students": stu_counts.get(sc.id, 0),
                    "full_marks": 0,
                    "pass_marks": 0,
                    "credit_hours": 0.0,
                    "year_start_date": ay_start,
                    "status": "Active" if sc.is_active else "Inactive",
                })
        return rows

    @staticmethod
    def _fetch_exam(db: Session, academic_year_id: Optional[int]) -> List[Dict[str, Any]]:
        q = (
            db.query(ExamResultSummary)
            .join(ExamTerm, ExamResultSummary.exam_term_id == ExamTerm.id)
            .filter(ExamResultSummary.is_deleted == False)  # noqa: E712
        )
        if academic_year_id:
            q = q.filter(ExamTerm.academic_year_id == academic_year_id)

        rows: List[Dict[str, Any]] = []
        for res in q.order_by(ExamTerm.start_date.desc(), ExamResultSummary.class_rank.asc()).all():
            term = res.exam_term
            stu = res.student
            sc = res.school_class
            rows.append({
                "exam_term": term.name if term else "",
                "exam_code": term.exam_code if term else "",
                "exam_type": term.exam_type.name if term and term.exam_type else "Standard",
                "academic_year": term.academic_year.name if term and term.academic_year else "",
                "class_name": sc.name if sc else "",
                "admission_number": stu.admission_number if stu else "",
                "student_name": stu.full_name if stu else f"Student #{res.student_id}",
                "total_obtained": round(float(res.total_obtained or 0.0), 2),
                "total_full_marks": round(float(res.total_full_marks or 0.0), 2),
                "percentage": round(float(res.percentage or 0.0), 2),
                "gpa": round(float(res.gpa or 0.0), 2),
                "cgpa": round(float(res.cgpa or 0.0), 2),
                "overall_grade": res.overall_grade,
                "class_rank": res.class_rank or 0,
                "section_rank": res.section_rank or 0,
                "passed_status": "Pass" if res.passed_all else "Fail",
                "result_status": res.result_status,
                "is_published": "Yes" if res.is_published else "No",
                "term_start_date": _fmt_date(term.start_date if term else None),
            })
        return rows

    @staticmethod
    def _fetch_library(db: Session) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        # Catalog Inventory rows
        for bk in db.query(Book).filter(Book.is_deleted == False).order_by(Book.title).all():  # noqa: E712
            rows.append({
                "record_kind": "Catalog Inventory",
                "accession_no": bk.accession_no,
                "book_title": bk.title,
                "author": bk.author,
                "category": bk.category.name if bk.category else "",
                "isbn": bk.isbn or bk.isbn_13 or "",
                "member_id": "-",
                "member_name": "-",
                "event_date": _fmt_date(bk.created_at),
                "due_date": "",
                "return_date": "",
                "total_copies": bk.total_copies,
                "available_copies": bk.available_copies,
                "fine_amount": 0.0,
                "status": bk.status,
            })

        # Circulation & Borrowing History rows
        for circ in db.query(BookCirculation).filter(BookCirculation.is_deleted == False).order_by(BookCirculation.issue_date.desc()).all():  # noqa: E712
            bk = circ.book
            mem = circ.member
            rows.append({
                "record_kind": "Circulation",
                "accession_no": bk.accession_no if bk else f"BK-{circ.book_id}",
                "book_title": bk.title if bk else "",
                "author": bk.author if bk else "",
                "category": bk.category.name if bk and bk.category else "",
                "isbn": bk.isbn or "" if bk else "",
                "member_id": mem.member_id if mem else "",
                "member_name": mem.display_name if mem else "",
                "event_date": circ.issue_date,
                "due_date": circ.due_date,
                "return_date": circ.return_date or "",
                "total_copies": bk.total_copies if bk else 0,
                "available_copies": bk.available_copies if bk else 0,
                "fine_amount": round(float(circ.fine_amount or 0.0) + float(circ.damage_or_lost_fee or 0.0), 2),
                "status": circ.status,
            })

        # Library Fines rows
        for fn in db.query(LibraryFine).filter(LibraryFine.is_deleted == False).order_by(LibraryFine.assessed_date.desc()).all():  # noqa: E712
            bk = fn.book
            mem = fn.member
            rows.append({
                "record_kind": f"Fine ({fn.fine_type})",
                "accession_no": fn.fine_code,
                "book_title": bk.title if bk else "Library Fine",
                "author": bk.author if bk else "",
                "category": bk.category.name if bk and bk.category else fn.fine_type,
                "isbn": bk.isbn or "" if bk else "",
                "member_id": mem.member_id if mem else "",
                "member_name": mem.display_name if mem else "",
                "event_date": fn.assessed_date,
                "due_date": "",
                "return_date": fn.paid_date or "",
                "total_copies": 0,
                "available_copies": 0,
                "fine_amount": round(float(fn.amount or 0.0), 2),
                "status": fn.status,
            })

        return rows

    @staticmethod
    def _fetch_transport(db: Session) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        # Commuter Allocations + Fees
        for pax in db.query(TransportPassenger).filter(TransportPassenger.is_deleted == False).all():  # noqa: E712
            veh = pax.vehicle or (pax.route.vehicle if pax.route else None)
            rt = pax.route
            stp = pax.stop
            if pax.student:
                pname = pax.student.full_name
            elif pax.teacher:
                pname = pax.teacher.full_name
            elif pax.staff:
                pname = pax.staff.full_name
            else:
                pname = f"Passenger #{pax.id}"

            charges = [fc for fc in pax.fee_charges if not fc.is_deleted]
            total_billed = sum(fc.net_payable for fc in charges)
            total_paid = sum(float(fc.paid_amount or 0.0) for fc in charges)
            total_due = sum(fc.balance_due for fc in charges)

            rows.append({
                "record_type": f"Passenger ({pax.passenger_type})",
                "vehicle_number": veh.vehicle_number if veh else "Unassigned",
                "vehicle_type": veh.vehicle_type if veh else "",
                "registration_no": veh.registration_no or "" if veh else "",
                "driver_name": veh.driver_name if veh else "",
                "route_code": rt.route_code if rt else "",
                "route_name": rt.route_name if rt else "",
                "stop_name": stp.stop_name if stp else (pax.pickup_address or ""),
                "passenger_name": pname,
                "amount_or_fare": round(total_billed if charges else float(pax.monthly_fare or 0.0), 2),
                "paid_amount": round(total_paid, 2),
                "balance_due": round(total_due, 2),
                "odometer_km": round(float(veh.current_odometer_km or 0.0), 1) if veh else 0.0,
                "event_date": pax.allocation_date,
                "status": pax.status,
            })

        # Maintenance Logs
        for ml in db.query(TransportMaintenanceLog).filter(TransportMaintenanceLog.is_deleted == False).all():  # noqa: E712
            veh = ml.vehicle
            rows.append({
                "record_type": f"Maintenance ({ml.service_type})",
                "vehicle_number": veh.vehicle_number if veh else f"VEH-{ml.vehicle_id}",
                "vehicle_type": veh.vehicle_type if veh else "",
                "registration_no": veh.registration_no or "" if veh else "",
                "driver_name": veh.driver_name if veh else "",
                "route_code": "-",
                "route_name": "-",
                "stop_name": "-",
                "passenger_name": ml.workshop_name or "Workshop",
                "amount_or_fare": round(float(ml.cost or 0.0), 2),
                "paid_amount": round(float(ml.cost or 0.0), 2) if ml.status == "Completed" else 0.0,
                "balance_due": 0.0,
                "odometer_km": round(float(ml.odometer_km or 0.0), 1),
                "event_date": ml.service_date,
                "status": ml.status,
            })

        # Vehicles without passenger or maintenance records still appear if fleet-only
        seen_vehicles = {r["vehicle_number"] for r in rows}
        for veh in db.query(Vehicle).filter(Vehicle.is_deleted == False).all():  # noqa: E712
            if veh.vehicle_number not in seen_vehicles:
                rows.append({
                    "record_type": "Fleet Vehicle",
                    "vehicle_number": veh.vehicle_number,
                    "vehicle_type": veh.vehicle_type,
                    "registration_no": veh.registration_no or "",
                    "driver_name": veh.driver_name,
                    "route_code": veh.routes[0].route_code if veh.routes else "-",
                    "route_name": veh.routes[0].route_name if veh.routes else "-",
                    "stop_name": "-",
                    "passenger_name": f"Cap: {veh.seating_capacity}",
                    "amount_or_fare": 0.0,
                    "paid_amount": 0.0,
                    "balance_due": 0.0,
                    "odometer_km": round(float(veh.current_odometer_km or 0.0), 1),
                    "event_date": _fmt_date(veh.created_at),
                    "status": veh.status,
                })

        return rows

    @staticmethod
    def _fetch_hostel(db: Session) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        allocated_rooms = set()

        for alloc in db.query(HostelAllocation).filter(HostelAllocation.is_deleted == False).all():  # noqa: E712
            rm = alloc.room
            blk = rm.block if rm else None
            stu = alloc.student
            if rm:
                allocated_rooms.add(rm.id)

            charges = [fc for fc in alloc.fee_charges if not fc.is_deleted]
            total_billed = sum(fc.net_payable for fc in charges)
            paid_fees = sum(float(fc.paid_amount or 0.0) for fc in charges)

            rows.append({
                "block_name": blk.block_name if blk else "",
                "gender_type": blk.gender_type if blk else "",
                "floor_number": rm.floor_number if rm else 0,
                "room_number": rm.room_number if rm else "",
                "room_type": rm.room_type if rm else "",
                "capacity": rm.capacity if rm else 0,
                "bed_number": alloc.bed_number,
                "admission_number": stu.admission_number if stu else "",
                "student_name": stu.full_name if stu else f"Student #{alloc.student_id}",
                "event_date": _fmt_date(alloc.check_in_date or alloc.admission_date),
                "check_out_date": _fmt_date(alloc.check_out_date or alloc.vacate_date),
                "monthly_fee": round(float(alloc.monthly_fee if alloc.monthly_fee is not None else (rm.monthly_fee if rm else 0.0)), 2),
                "total_billed_fees": round(total_billed, 2),
                "paid_fees": round(paid_fees, 2),
                "clearance_status": alloc.clearance_status,
                "status": alloc.status,
            })

        # Also list vacant rooms so capacity audits show empty beds/rooms
        for rm in db.query(HostelRoom).filter(HostelRoom.is_deleted == False).all():  # noqa: E712
            if rm.id not in allocated_rooms:
                blk = rm.block
                rows.append({
                    "block_name": blk.block_name if blk else "",
                    "gender_type": blk.gender_type if blk else "",
                    "floor_number": rm.floor_number,
                    "room_number": rm.room_number,
                    "room_type": rm.room_type,
                    "capacity": rm.capacity,
                    "bed_number": "(Vacant)",
                    "admission_number": "",
                    "student_name": "(Unallocated Room)",
                    "event_date": _fmt_date(rm.created_at),
                    "check_out_date": "",
                    "monthly_fee": round(float(rm.monthly_fee or 0.0), 2),
                    "total_billed_fees": 0.0,
                    "paid_fees": 0.0,
                    "clearance_status": "-",
                    "status": rm.status,
                })

        return rows

    @staticmethod
    def _fetch_inventory(db: Session) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        for item in db.query(InventoryItem).filter(InventoryItem.is_deleted == False).all():  # noqa: E712
            qty = int(item.quantity_in_stock or 0)
            uc = round(float(item.unit_cost or 0.0), 2)
            rows.append({
                "record_kind": "Product / Stock",
                "code_or_asset_id": item.item_code,
                "name": item.name,
                "category": item.category.name if item.category else "",
                "item_type": item.item_type,
                "supplier": item.preferred_supplier.name if item.preferred_supplier else (item.supplier_name or ""),
                "serial_number": item.sku or item.barcode or "",
                "location": item.storage_location or "",
                "department": item.department.name if item.department else "",
                "assigned_employee": "-",
                "quantity": qty,
                "reorder_level": int(item.reorder_level or 0),
                "unit_cost": uc,
                "total_value": round(qty * uc, 2),
                "low_stock_alert": "LOW STOCK" if item.is_low_stock else "OK",
                "record_date": _fmt_date(item.created_at),
                "warranty": "-",
                "status": item.status,
            })

        for ast in db.query(FixedAsset).filter(FixedAsset.is_deleted == False).all():  # noqa: E712
            cost = round(float(ast.cost or 0.0), 2)
            emp_name = ast.assigned_employee or (
                ast.assigned_teacher.full_name
                if ast.assigned_teacher
                else (ast.assigned_staff.full_name if ast.assigned_staff else "Unassigned")
            )
            dept_name = ast.department.name if ast.department else (ast.department_name or "")
            rows.append({
                "record_kind": "Fixed Asset",
                "code_or_asset_id": ast.asset_id,
                "name": ast.name,
                "category": ast.category.name if ast.category else "",
                "item_type": "Fixed Asset",
                "supplier": ast.supplier.name if ast.supplier else "",
                "serial_number": ast.serial_number or "",
                "location": ast.location,
                "department": dept_name,
                "assigned_employee": emp_name,
                "quantity": 1,
                "reorder_level": 0,
                "unit_cost": cost,
                "total_value": cost,
                "low_stock_alert": "N/A",
                "record_date": _fmt_date(ast.purchase_date),
                "warranty": ast.warranty or "",
                "status": ast.status,
            })

        return rows

    @staticmethod
    def _fetch_hr(db: Session) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        for t in db.query(Teacher).filter(Teacher.is_deleted == False).all():  # noqa: E712
            approved_days = sum(
                int(lr.total_days or 0) for lr in t.leave_requests if lr.status == "Approved"
            )
            pending_cnt = sum(1 for lr in t.leave_requests if lr.status == "Pending")
            latest_eval = t.evaluations[0].overall_rating if t.evaluations else 0.0
            rows.append({
                "employee_code": t.employee_id,
                "employee_type": "Teacher",
                "full_name": t.full_name,
                "gender": t.gender,
                "department": t.department.name if t.department else "",
                "designation_or_position": t.designation,
                "contract_type": t.contract_type,
                "joining_date": _fmt_date(t.joining_date),
                "salary": float(t.salary or 0.0),
                "approved_leave_days": approved_days,
                "pending_leaves": pending_cnt,
                "latest_rating": round(float(latest_eval), 2),
                "phone": t.phone,
                "email": t.email or "",
                "status": (t.status or "").title(),
            })

        for st in db.query(Staff).filter(Staff.is_deleted == False).all():  # noqa: E712
            approved_days = sum(
                int(lr.total_days or 0) for lr in st.leave_requests if lr.status == "Approved"
            )
            pending_cnt = sum(1 for lr in st.leave_requests if lr.status == "Pending")
            latest_eval = st.evaluations[0].overall_rating if st.evaluations else 0.0
            rows.append({
                "employee_code": st.employee_id,
                "employee_type": "Staff",
                "full_name": st.full_name,
                "gender": st.gender,
                "department": st.department.name if st.department else "",
                "designation_or_position": st.position,
                "contract_type": st.contract_type,
                "joining_date": _fmt_date(st.joining_date),
                "salary": float(st.salary or 0.0),
                "approved_leave_days": approved_days,
                "pending_leaves": pending_cnt,
                "latest_rating": round(float(latest_eval), 2),
                "phone": st.phone,
                "email": st.email or "",
                "status": (st.status or "").title(),
            })

        return rows

    # ------------------------------------------------------------------
    # Saved Report Templates CRUD
    # ------------------------------------------------------------------
    @staticmethod
    def save_report_definition(
        db: Session,
        name: str,
        domain_key: str,
        selected_columns: List[str],
        filters: Optional[List[Dict[str, Any]]] = None,
        group_by: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_desc: bool = False,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        academic_year_id: Optional[int] = None,
        description: Optional[str] = None,
        created_by: str = "admin",
    ) -> SavedReportDefinition:
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Template name is required.")
        if domain_key not in REPORT_DOMAIN_CATALOG:
            raise ValueError(f"Unsupported report domain '{domain_key}'.")

        existing = (
            db.query(SavedReportDefinition)
            .filter(SavedReportDefinition.name == clean_name, SavedReportDefinition.is_deleted == False)  # noqa: E712
            .first()
        )
        if existing:
            tpl = existing
        else:
            tpl = SavedReportDefinition(name=clean_name, created_by=created_by)
            db.add(tpl)

        tpl.domain_key = domain_key
        tpl.description = description
        tpl.columns_json = json.dumps(list(selected_columns or []))
        tpl.filters_json = json.dumps(list(filters or []))
        tpl.group_by = group_by or None
        tpl.sort_by = sort_by or None
        tpl.sort_desc = bool(sort_desc)
        tpl.date_from = _fmt_date(date_from) or None
        tpl.date_to = _fmt_date(date_to) or None
        tpl.academic_year_id = academic_year_id
        db.commit()
        db.refresh(tpl)
        return tpl

    @staticmethod
    def list_saved_definitions(db: Session) -> List[SavedReportDefinition]:
        return (
            db.query(SavedReportDefinition)
            .filter(SavedReportDefinition.is_deleted == False)  # noqa: E712
            .order_by(SavedReportDefinition.name)
            .all()
        )

    @classmethod
    def run_saved_definition(cls, db: Session, template_id: int) -> Dict[str, Any]:
        tpl = (
            db.query(SavedReportDefinition)
            .filter(SavedReportDefinition.id == template_id, SavedReportDefinition.is_deleted == False)  # noqa: E712
            .first()
        )
        if not tpl:
            raise ValueError("Saved report template not found.")
        return cls.build_report(
            db=db,
            domain_key=tpl.domain_key,
            selected_columns=tpl.get_columns(),
            filters=tpl.get_filters(),
            group_by=tpl.group_by,
            sort_by=tpl.sort_by,
            sort_desc=tpl.sort_desc,
            date_from=_parse_date(tpl.date_from),
            date_to=_parse_date(tpl.date_to),
            academic_year_id=tpl.academic_year_id,
            report_title=tpl.name,
        )

    @staticmethod
    def delete_saved_definition(db: Session, template_id: int) -> bool:
        tpl = db.query(SavedReportDefinition).filter(SavedReportDefinition.id == template_id).first()
        if not tpl:
            return False
        tpl.is_deleted = True
        db.commit()
        return True

    # ------------------------------------------------------------------
    # Universal Export Helpers (CSV & Excel)
    # ------------------------------------------------------------------
    @staticmethod
    def export_to_csv(
        report_result: Dict[str, Any],
        output_path: str,
        use_grouped_if_present: bool = False,
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        grouped = use_grouped_if_present and bool(report_result.get("grouped_rows"))
        cols = report_result["group_columns"] if grouped else report_result["columns"]
        rows = report_result["grouped_rows"] if grouped else report_result["rows"]

        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([c["label"] for c in cols])
            for r in rows:
                writer.writerow([
                    "" if r.get(c["key"]) is None else r.get(c["key"])
                    for c in cols
                ])
        return output_path

    @staticmethod
    def export_to_excel(report_result: Dict[str, Any], output_path: str) -> str:
        try:
            import openpyxl
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            raise RuntimeError("openpyxl is required to export Excel files.")

        wb = openpyxl.Workbook()
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        total_fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
        total_font = Font(name="Calibri", size=11, bold=True, color="1E3A8A")
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )

        # Sheet 1: Report Data
        ws = wb.active
        ws.title = "Report Data"
        ws.views.sheetView[0].showGridLines = True

        cols = report_result["columns"]
        col_count = max(1, len(cols))

        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=col_count)
        ws["A1"] = f"{report_result['title']} ({report_result['domain_label']})"
        ws["A1"].font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")

        meta_parts = [
            f"Generated: {report_result['generated_at']}",
            f"Academic Year: {report_result.get('academic_year_label', 'All')}",
        ]
        if report_result.get("date_from") or report_result.get("date_to"):
            meta_parts.append(f"Date Range: {report_result.get('date_from') or '...'} to {report_result.get('date_to') or '...'}")
        if report_result.get("group_by_label"):
            meta_parts.append(f"Grouped By: {report_result['group_by_label']}")
        meta_parts.append(f"Rows: {report_result['row_count']}")

        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=col_count)
        ws["A2"] = " | ".join(meta_parts)
        ws["A2"].font = Font(name="Calibri", size=10, italic=True, color="475569")

        ws.append([])
        header_row_idx = 4
        ws.append([c["label"] for c in cols])
        for c_idx in range(1, col_count + 1):
            cell = ws.cell(row=header_row_idx, column=c_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center" if cols[c_idx - 1]["type"] == "num" else "left")

        for r in report_result["rows"]:
            row_vals = [r.get(c["key"]) for c in cols]
            ws.append(row_vals)
            for c_idx, cdef in enumerate(cols, start=1):
                cell = ws.cell(row=ws.max_row, column=c_idx)
                cell.border = thin_border
                if cdef["type"] == "num" and isinstance(cell.value, (int, float)):
                    cell.alignment = Alignment(horizontal="right")
                    if isinstance(cell.value, float):
                        cell.number_format = "#,##0.00"

        # Totals Footer Row
        totals = report_result.get("totals") or {}
        if totals:
            tot_vals: List[Any] = []
            for idx, cdef in enumerate(cols):
                if cdef["key"] in totals:
                    tot_vals.append(totals[cdef["key"]])
                elif idx == 0:
                    tot_vals.append("TOTAL")
                else:
                    tot_vals.append("")
            ws.append(tot_vals)
            for c_idx, cdef in enumerate(cols, start=1):
                cell = ws.cell(row=ws.max_row, column=c_idx)
                cell.fill = total_fill
                cell.font = total_font
                cell.border = thin_border
                if cdef["type"] == "num" and isinstance(cell.value, (int, float)):
                    cell.alignment = Alignment(horizontal="right")
                    cell.number_format = "#,##0.00"

        # Sheet 2: Grouped Rollup Summary (if group_by was applied)
        if report_result.get("grouped_rows"):
            ws_grp = wb.create_sheet(title="Grouped Summary")
            ws_grp.views.sheetView[0].showGridLines = True
            gcols = report_result["group_columns"]
            ws_grp.append([gc["label"] for gc in gcols])
            for c_idx in range(1, len(gcols) + 1):
                cell = ws_grp.cell(row=1, column=c_idx)
                cell.fill = header_fill
                cell.font = header_font
            for gr in report_result["grouped_rows"]:
                ws_grp.append([gr.get(gc["key"]) for gc in gcols])
                for c_idx, gc in enumerate(gcols, start=1):
                    cell = ws_grp.cell(row=ws_grp.max_row, column=c_idx)
                    cell.border = thin_border
                    if gc["type"] == "num" and isinstance(cell.value, float):
                        cell.number_format = "#,##0.00"

        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value is not None:
                        max_len = max(max_len, len(str(cell.value)))
                sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 42)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb.save(output_path)
        return output_path
