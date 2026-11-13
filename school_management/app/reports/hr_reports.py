"""
EduManage Pro - HR & Confidential Payroll Reports Generator
Produces PDF (ReportLab) and Excel (openpyxl) reports for:
- Employee Directory (salary strictly omitted unless authorized)
- Leave Requests & Approval Audit
- Teacher & Staff Attendance Summary
- Employment Contracts Register (compensation omitted unless authorized)
- Performance Evaluations Report
- Confidential Payroll & Salary History Register (requires hr.salary.VIEW & hr.salary.EXPORT)
"""

from datetime import date, datetime
import os
from typing import Any, List, Optional

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib.colors import HexColor, colors
from reportlab.lib.pagesizes import landscape, letter, portrait
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import StaffAttendance, TeacherAttendance
from app.models.settings import SchoolSettings
from app.models.staff import (
    EmployeeContract,
    EmployeeLeaveRequest,
    EmployeePerformanceEvaluation,
    EmployeeSalaryHistory,
    EmployeeStatus,
    Staff,
    Teacher,
)
from app.models.user import User
from app.repositories.staff_repository import StaffRepository
from app.services.hr_service import HRSecurityGuard


class HRReportsGenerator:
    """Permission-aware PDF and Excel report generator for HR Management."""

    @staticmethod
    def _export_table_to_excel(
        output_path: str,
        sheet_title: str,
        headers: List[str],
        rows: List[List[Any]],
        header_hex: str = "1E3A8A",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_title[:31]
        ws.append(headers)

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color=header_hex, end_color=header_hex, fill_type="solid")
        for col_idx in range(1, len(headers) + 1):
            c = ws.cell(row=1, column=col_idx)
            c.font = header_font
            c.fill = header_fill
            c.alignment = Alignment(horizontal="center", vertical="center")

        for r in rows:
            ws.append(r)

        for col in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max(max_len + 3, 12), 45)

        wb.save(output_path)
        return output_path

    @staticmethod
    def _export_table_to_pdf(
        db: Session,
        output_path: str,
        report_title: str,
        subtitle: str,
        headers: List[str],
        rows: List[List[Any]],
        col_widths: Optional[List[float]] = None,
        use_landscape: bool = True,
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        school = db.query(SchoolSettings).first()
        school_name = getattr(school, "school_name", None) or "EduManage Pro Model Academy"

        pagesize = landscape(letter) if use_landscape else portrait(letter)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=pagesize,
            leftMargin=28,
            rightMargin=28,
            topMargin=28,
            bottomMargin=28,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "HRReportTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            alignment=1,
            textColor=HexColor("#1E3A8A"),
        )
        sub_style = ParagraphStyle(
            "HRReportSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=1,
            textColor=HexColor("#475569"),
        )
        cell_style = ParagraphStyle(
            "HRCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=HexColor("#0F172A"),
        )
        header_cell_style = ParagraphStyle(
            "HRHeaderCell",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )

        elements = [
            Paragraph(school_name, title_style),
            Paragraph(f"{report_title} — {subtitle}", sub_style),
            Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", sub_style),
            Spacer(1, 8),
            HRFlowable(width="100%", thickness=1, color=HexColor("#CBD5E1")),
            Spacer(1, 10),
        ]

        table_data = [[Paragraph(str(h), header_cell_style) for h in headers]]
        if not rows:
            empty_row = ["No records found."] + [""] * (len(headers) - 1)
            table_data.append([Paragraph(c, cell_style) for c in empty_row])
        else:
            for r in rows:
                table_data.append([Paragraph(str(val if val is not None else "-"), cell_style) for val in r])

        tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1E3A8A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CBD5E1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#F8FAFC")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(tbl)
        doc.build(elements)
        return output_path

    # ------------------------------------------------------------------
    # 1. Employee Directory Report (Salary omitted unless authorized)
    # ------------------------------------------------------------------
    @classmethod
    def generate_employee_directory_report(
        cls,
        db: Session,
        output_path: str,
        fmt: str = "pdf",
        employee_type: Optional[str] = None,
        actor_user: Optional[User] = None,
    ) -> str:
        HRSecurityGuard.require_permission("hr.reports.VIEW", actor_user)
        if fmt.lower() == "xlsx":
            HRSecurityGuard.require_permission("hr.reports.EXPORT", actor_user)

        can_salary = HRSecurityGuard.can_view_salary(actor_user=actor_user, allow_when_no_session=True)
        etype = (employee_type or "").strip().lower()

        headers = ["Category", "Emp ID", "Full Name", "Role / Subject", "Department", "Joined", "Exp (Yrs)", "Phone", "Status"]
        if can_salary:
            headers.append("Salary (BDT)")

        rows: List[List[Any]] = []
        if etype in ("", "all", "teacher"):
            teachers, _ = StaffRepository.search_and_filter_teachers(db, per_page=10000)
            for t in teachers:
                row = [
                    "Teacher",
                    t.employee_id,
                    t.full_name,
                    f"{t.designation} ({t.primary_subject})",
                    t.department.name if t.department else "-",
                    t.joining_date.isoformat() if t.joining_date else "-",
                    f"{t.experience_years:.1f}",
                    t.phone,
                    EmployeeStatus.LABELS.get(t.status, t.status),
                ]
                if can_salary:
                    row.append(t.salary)
                rows.append(row)

        if etype in ("", "all", "staff"):
            staff_list, _ = StaffRepository.search_and_filter_staff(db, per_page=10000)
            for s in staff_list:
                row = [
                    "Staff",
                    s.employee_id,
                    s.full_name,
                    f"{s.position} ({s.shift})",
                    s.department.name if s.department else "-",
                    s.joining_date.isoformat() if s.joining_date else "-",
                    f"{s.experience_years:.1f}",
                    s.phone,
                    EmployeeStatus.LABELS.get(s.status, s.status),
                ]
                if can_salary:
                    row.append(s.salary)
                rows.append(row)

        if fmt.lower() == "xlsx":
            return cls._export_table_to_excel(output_path, "HR Employee Directory", headers, rows)
        return cls._export_table_to_pdf(
            db,
            output_path,
            "HR Employee Directory Report",
            f"Total Personnel: {len(rows)}",
            headers,
            rows,
            use_landscape=True,
        )

    # ------------------------------------------------------------------
    # 2. Leave Management Report
    # ------------------------------------------------------------------
    @classmethod
    def generate_leave_report(
        cls,
        db: Session,
        output_path: str,
        fmt: str = "pdf",
        status: Optional[str] = None,
        actor_user: Optional[User] = None,
    ) -> str:
        HRSecurityGuard.require_permission("hr.reports.VIEW", actor_user)
        if fmt.lower() == "xlsx":
            HRSecurityGuard.require_permission("hr.reports.EXPORT", actor_user)

        reqs = StaffRepository.list_leave_requests(db, status=status)
        headers = ["Leave #", "Category", "Employee", "Leave Type", "From", "To", "Days", "Status", "Reviewed By", "Reason"]
        rows: List[List[Any]] = []
        for lv in reqs:
            emp = lv.teacher if lv.employee_type == "teacher" else lv.staff
            rows.append([
                lv.id,
                lv.employee_type.capitalize(),
                emp.full_name if emp else "-",
                lv.leave_type,
                lv.start_date.isoformat(),
                lv.end_date.isoformat(),
                lv.total_days,
                lv.status,
                lv.reviewed_by or "-",
                lv.reason,
            ])

        if fmt.lower() == "xlsx":
            return cls._export_table_to_excel(output_path, "Leave Requests Report", headers, rows, header_hex="0F766E")
        return cls._export_table_to_pdf(
            db,
            output_path,
            "Employee Leave Management Report",
            f"Filter: {status or 'All Requests'} | Count: {len(rows)}",
            headers,
            rows,
            use_landscape=True,
        )

    # ------------------------------------------------------------------
    # 3. Employee Attendance Report (Teachers & Staff)
    # ------------------------------------------------------------------
    @classmethod
    def generate_attendance_report(
        cls,
        db: Session,
        output_path: str,
        fmt: str = "pdf",
        employee_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        actor_user: Optional[User] = None,
    ) -> str:
        HRSecurityGuard.require_permission("hr.reports.VIEW", actor_user)
        if fmt.lower() == "xlsx":
            HRSecurityGuard.require_permission("hr.reports.EXPORT", actor_user)

        etype = (employee_type or "").strip().lower()
        headers = ["Category", "Date", "Employee ID", "Employee Name", "Status", "Remarks", "Marked By"]
        rows: List[List[Any]] = []

        if etype in ("", "all", "teacher"):
            q = db.query(TeacherAttendance).options(joinedload(TeacherAttendance.teacher))
            if start_date:
                q = q.filter(TeacherAttendance.date >= start_date)
            if end_date:
                q = q.filter(TeacherAttendance.date <= end_date)
            for rec in q.order_by(TeacherAttendance.date.desc()).all():
                rows.append([
                    "Teacher",
                    rec.date.isoformat(),
                    rec.teacher.employee_id if rec.teacher else "-",
                    rec.teacher.full_name if rec.teacher else "-",
                    rec.status,
                    rec.remarks or "-",
                    rec.marked_by,
                ])

        if etype in ("", "all", "staff"):
            q = db.query(StaffAttendance).options(joinedload(StaffAttendance.staff))
            if start_date:
                q = q.filter(StaffAttendance.date >= start_date)
            if end_date:
                q = q.filter(StaffAttendance.date <= end_date)
            for rec in q.order_by(StaffAttendance.date.desc()).all():
                rows.append([
                    "Staff",
                    rec.date.isoformat(),
                    rec.staff.employee_id if rec.staff else "-",
                    rec.staff.full_name if rec.staff else "-",
                    rec.status,
                    rec.remarks or "-",
                    rec.marked_by,
                ])

        if fmt.lower() == "xlsx":
            return cls._export_table_to_excel(output_path, "Employee Attendance", headers, rows, header_hex="1D4ED8")
        return cls._export_table_to_pdf(
            db,
            output_path,
            "Teacher & Staff Attendance Register",
            f"Total Entries: {len(rows)}",
            headers,
            rows,
            use_landscape=True,
        )

    # ------------------------------------------------------------------
    # 4. Employment Contracts Report (Salary omitted unless authorized)
    # ------------------------------------------------------------------
    @classmethod
    def generate_contracts_report(
        cls,
        db: Session,
        output_path: str,
        fmt: str = "pdf",
        actor_user: Optional[User] = None,
    ) -> str:
        HRSecurityGuard.require_permission("hr.reports.VIEW", actor_user)
        if fmt.lower() == "xlsx":
            HRSecurityGuard.require_permission("hr.reports.EXPORT", actor_user)

        can_salary = HRSecurityGuard.can_view_salary(actor_user=actor_user, allow_when_no_session=True)
        contracts = StaffRepository.list_contracts(db)

        headers = ["Contract #", "Category", "Employee", "Type", "Start Date", "End Date", "Hrs/Wk", "Status"]
        if can_salary:
            headers.extend(["Basic Salary", "Allowances"])

        rows: List[List[Any]] = []
        for c in contracts:
            emp = c.teacher if c.employee_type == "teacher" else c.staff
            row = [
                c.contract_number,
                c.employee_type.capitalize(),
                emp.full_name if emp else "-",
                c.contract_type,
                c.start_date.isoformat(),
                c.end_date.isoformat() if c.end_date else "Open-Ended",
                c.working_hours_per_week,
                c.status,
            ]
            if can_salary:
                row.extend([c.basic_salary, c.allowances])
            rows.append(row)

        if fmt.lower() == "xlsx":
            return cls._export_table_to_excel(output_path, "Employee Contracts", headers, rows, header_hex="4338CA")
        return cls._export_table_to_pdf(
            db,
            output_path,
            "Employment Contracts Register",
            f"Total Contracts: {len(rows)}",
            headers,
            rows,
            use_landscape=True,
        )

    # ------------------------------------------------------------------
    # 5. Performance Evaluations Report
    # ------------------------------------------------------------------
    @classmethod
    def generate_performance_report(
        cls,
        db: Session,
        output_path: str,
        fmt: str = "pdf",
        actor_user: Optional[User] = None,
    ) -> str:
        HRSecurityGuard.require_permission("hr.reports.VIEW", actor_user)
        if fmt.lower() == "xlsx":
            HRSecurityGuard.require_permission("hr.reports.EXPORT", actor_user)

        evals = StaffRepository.list_evaluations(db)
        headers = [
            "Category", "Employee", "Period", "Review Date", "Reviewer",
            "Punctuality", "Competency", "Teamwork", "Compliance", "Overall", "Band",
        ]
        rows: List[List[Any]] = []
        for ev in evals:
            emp = ev.teacher if ev.employee_type == "teacher" else ev.staff
            rows.append([
                ev.employee_type.capitalize(),
                emp.full_name if emp else "-",
                ev.review_period,
                ev.review_date.isoformat(),
                ev.reviewer_name,
                f"{ev.punctuality_score:.1f}",
                f"{ev.competency_score:.1f}",
                f"{ev.teamwork_score:.1f}",
                f"{ev.compliance_score:.1f}",
                f"{ev.overall_rating:.2f}/5.0",
                ev.rating_band,
            ])

        if fmt.lower() == "xlsx":
            return cls._export_table_to_excel(output_path, "Performance Evaluations", headers, rows, header_hex="7C3AED")
        return cls._export_table_to_pdf(
            db,
            output_path,
            "Employee Performance Evaluation Summary",
            f"Total Reviews: {len(rows)}",
            headers,
            rows,
            use_landscape=True,
        )

    # ------------------------------------------------------------------
    # 6. Confidential Payroll & Salary Register (STRICT RBAC)
    # ------------------------------------------------------------------
    @classmethod
    def generate_payroll_salary_report(
        cls,
        db: Session,
        output_path: str,
        fmt: str = "pdf",
        actor_user: Optional[User] = None,
    ) -> str:
        """Strictly requires BOTH salary view and salary export permissions."""
        HRSecurityGuard.require_salary_view(actor_user)
        HRSecurityGuard.require_permission(
            "hr.salary.EXPORT",
            actor_user,
            error_msg="Access denied: you are not authorized to export confidential payroll reports.",
        )

        teachers, _ = StaffRepository.search_and_filter_teachers(db, per_page=10000)
        staff_list, _ = StaffRepository.search_and_filter_staff(db, per_page=10000)

        headers = ["Category", "Emp ID", "Full Name", "Role", "Department", "Bank Name", "Account No.", "Monthly Salary (BDT)", "Status"]
        rows: List[List[Any]] = []
        total_payroll = 0

        for t in teachers:
            total_payroll += t.salary or 0
            rows.append([
                "Teacher",
                t.employee_id,
                t.full_name,
                t.designation,
                t.department.name if t.department else "-",
                t.bank_name or "-",
                t.bank_account_no or "-",
                f"{t.salary:,}" if fmt.lower() == "pdf" else t.salary,
                t.status,
            ])

        for s in staff_list:
            total_payroll += s.salary or 0
            rows.append([
                "Staff",
                s.employee_id,
                s.full_name,
                s.position,
                s.department.name if s.department else "-",
                s.bank_name or "-",
                s.bank_account_no or "-",
                f"{s.salary:,}" if fmt.lower() == "pdf" else s.salary,
                s.status,
            ])

        if fmt.lower() == "xlsx":
            return cls._export_table_to_excel(output_path, "Confidential Payroll Register", headers, rows, header_hex="991B1B")
        return cls._export_table_to_pdf(
            db,
            output_path,
            "CONFIDENTIAL — Monthly Payroll & Compensation Register",
            f"Headcount: {len(rows)} | Total Monthly Payroll: BDT {total_payroll:,}",
            headers,
            rows,
            use_landscape=True,
        )
