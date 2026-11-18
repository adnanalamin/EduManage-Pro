"""
EduManage Pro - Enterprise Payroll PDF Reports Generator (ReportLab)
Produces permission-protected official PDFs:
1. Official Employee Salary Slip PDF (Earnings, Overtime, Bonus, Tax/TIN, PF, Loans/Advances, Attendance & Leave Deductions)
2. Monthly Payroll Register & Summary Report PDF
3. Employee Payment History & Tax Ledger PDF
"""

from datetime import datetime
import os
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.payroll import PayrollPayslip
from app.models.school import SchoolSetting
from app.models.user import User
from app.repositories.payroll_repository import PayrollRepository
from app.services.payroll_service import PayrollSecurityGuard, PayrollService


def _school_header_info(db: Session) -> Dict[str, str]:
    school = db.query(SchoolSetting).first()
    return {
        "name": getattr(school, "school_name", None) or "EduManage Pro Model High School",
        "address": getattr(school, "address", None) or "Uttara, Dhaka, Bangladesh",
        "eiin": getattr(school, "eiin_number", None) or "134211",
        "phone": getattr(school, "phone", None) or "+880 1712-345678",
        "currency": getattr(school, "currency_code", None) or "BDT",
    }


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PayTitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            alignment=1,
            textColor=colors.HexColor("#0F172A"),
        ),
        "sub": ParagraphStyle(
            "PaySub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=1,
            textColor=colors.HexColor("#475569"),
        ),
        "badge": ParagraphStyle(
            "PayBadge",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=1,
            textColor=colors.HexColor("#1E3A8A"),
        ),
        "cell_b": ParagraphStyle("PayCellB", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11),
        "cell_n": ParagraphStyle("PayCellN", parent=base["Normal"], fontName="Helvetica", fontSize=8.5, leading=11),
        "cell_r": ParagraphStyle(
            "PayCellR", parent=base["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, alignment=2
        ),
        "cell_rb": ParagraphStyle(
            "PayCellRB", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, alignment=2
        ),
    }


class PayrollPDFGenerator:
    @staticmethod
    def generate_salary_slip_pdf(
        db: Session,
        payslip_id: int,
        output_path: str,
        actor_user: Optional[User] = None,
    ) -> str:
        PayrollSecurityGuard.require_permission("payroll.reports.VIEW", actor_user)
        slip: Optional[PayrollPayslip] = PayrollRepository.get_payslip_by_id(db, payslip_id)
        if not slip:
            raise ValueError("Payslip not found.")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        meta = _school_header_info(db)
        st = _styles()
        doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=34, rightMargin=34, topMargin=32, bottomMargin=32)
        story: List[Any] = []

        run = slip.payroll_run
        period_lbl = run.period_label if run else f"{slip.payroll_year}-{slip.payroll_month:02d}"
        cur = meta["currency"]

        story.append(Paragraph(meta["name"].upper(), st["title"]))
        story.append(Paragraph(f"{meta['address']} &bull; EIIN: {meta['eiin']} &bull; Tel: {meta['phone']}", st["sub"]))
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1")))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"OFFICIAL EMPLOYEE SALARY SLIP — {period_lbl.upper()}", st["badge"]))
        status_note = f"Slip No: {slip.slip_no} | Status: {slip.payment_status}"
        if slip.is_reversed:
            status_note += f" [REVERSED: {slip.reversal_reason or ''}]"
        elif run and run.is_locked:
            status_note += " | Period Locked"
        story.append(Paragraph(status_note, st["sub"]))
        story.append(Spacer(1, 12))

        # Employee Metadata Box
        vch_no = slip.accounting_tx.voucher_no if slip.accounting_tx else "-"
        info_tbl = Table(
            [
                [
                    Paragraph("<b>Employee Name:</b>", st["cell_b"]),
                    Paragraph(slip.employee_name, st["cell_n"]),
                    Paragraph("<b>Employee ID:</b>", st["cell_b"]),
                    Paragraph(slip.employee_code, st["cell_n"]),
                ],
                [
                    Paragraph("<b>Designation:</b>", st["cell_b"]),
                    Paragraph(slip.designation or "-", st["cell_n"]),
                    Paragraph("<b>Department:</b>", st["cell_b"]),
                    Paragraph(slip.department_name or "-", st["cell_n"]),
                ],
                [
                    Paragraph("<b>Payment Method:</b>", st["cell_b"]),
                    Paragraph(f"{slip.payment_method} ({slip.bank_name or '-'} {slip.bank_account_no or ''})", st["cell_n"]),
                    Paragraph("<b>TIN / Voucher:</b>", st["cell_b"]),
                    Paragraph(f"TIN: {slip.tax_tin or '-'} | {vch_no}", st["cell_n"]),
                ],
            ],
            colWidths=[95, 180, 90, 160],
        )
        info_tbl.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#94A3B8")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(info_tbl)
        story.append(Spacer(1, 10))

        # Attendance & Leave Strip
        att_tbl = Table(
            [
                [
                    Paragraph("<b>Working Days</b>", st["cell_b"]),
                    Paragraph("<b>Present</b>", st["cell_b"]),
                    Paragraph("<b>Late Days</b>", st["cell_b"]),
                    Paragraph("<b>Absent Days</b>", st["cell_b"]),
                    Paragraph("<b>Paid Leave</b>", st["cell_b"]),
                    Paragraph("<b>Unpaid Leave</b>", st["cell_b"]),
                ],
                [
                    Paragraph(str(slip.working_days), st["cell_n"]),
                    Paragraph(str(slip.present_days), st["cell_n"]),
                    Paragraph(str(slip.late_days), st["cell_n"]),
                    Paragraph(f"{float(slip.absent_days or 0):g}", st["cell_n"]),
                    Paragraph(f"{float(slip.paid_leave_days or 0):g}", st["cell_n"]),
                    Paragraph(f"{float(slip.unpaid_leave_days or 0):g}", st["cell_n"]),
                ],
            ],
            colWidths=[87, 87, 87, 88, 88, 88],
        )
        att_tbl.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(att_tbl)
        story.append(Spacer(1, 12))

        # Two-column Earnings vs Deductions
        earnings = [
            ("Basic Salary", float(slip.basic_salary or 0.0)),
            ("House Rent Allowance", float(slip.house_rent_allowance or 0.0)),
            ("Medical Allowance", float(slip.medical_allowance or 0.0)),
            ("Transport Allowance", float(slip.transport_allowance or 0.0)),
            ("Special Allowance", float(slip.special_allowance or 0.0)),
            ("Other Allowances", float(slip.other_allowance or 0.0)),
            (f"Overtime ({float(slip.overtime_hours or 0):g} hrs)", float(slip.overtime_amount or 0.0)),
            (f"Bonus ({slip.bonus_reason or 'Incentive'})", float(slip.bonus_amount or 0.0)),
        ]
        deductions = [
            ("Provident Fund (PF)", float(slip.provident_fund_deduction or 0.0)),
            ("Group Insurance", float(slip.insurance_deduction or 0.0)),
            ("Income Tax (TDS)", float(slip.tax_deduction or 0.0)),
            ("Attendance Deduction", float(slip.attendance_deduction or 0.0)),
            ("Unpaid Leave Deduction", float(slip.leave_deduction or 0.0)),
            ("Loan Installment", float(slip.loan_deduction or 0.0)),
            ("Advance Recovery", float(slip.advance_deduction or 0.0)),
            (f"Other ({slip.other_deduction_reason or '-'})", float(slip.other_deduction or 0.0)),
        ]

        comp_rows = [
            [
                Paragraph("<b>EARNINGS</b>", st["cell_b"]),
                Paragraph(f"<b>AMOUNT ({cur})</b>", st["cell_rb"]),
                Paragraph("<b>DEDUCTIONS</b>", st["cell_b"]),
                Paragraph(f"<b>AMOUNT ({cur})</b>", st["cell_rb"]),
            ]
        ]
        max_len = max(len(earnings), len(deductions))
        for idx in range(max_len):
            elbl, eamt = earnings[idx] if idx < len(earnings) else ("", None)
            dlbl, damt = deductions[idx] if idx < len(deductions) else ("", None)
            comp_rows.append(
                [
                    Paragraph(elbl, st["cell_n"]),
                    Paragraph(f"{eamt:,.2f}" if eamt is not None else "", st["cell_r"]),
                    Paragraph(dlbl, st["cell_n"]),
                    Paragraph(f"{damt:,.2f}" if damt is not None else "", st["cell_r"]),
                ]
            )

        comp_rows.append(
            [
                Paragraph("<b>TOTAL GROSS EARNINGS</b>", st["cell_b"]),
                Paragraph(f"<b>{float(slip.gross_earnings or 0.0):,.2f}</b>", st["cell_rb"]),
                Paragraph("<b>TOTAL DEDUCTIONS</b>", st["cell_b"]),
                Paragraph(f"<b>{float(slip.total_deductions or 0.0):,.2f}</b>", st["cell_rb"]),
            ]
        )

        comp_tbl = Table(comp_rows, colWidths=[170, 92, 170, 93])
        comp_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(comp_tbl)
        story.append(Spacer(1, 12))

        net_box = Table(
            [
                [
                    Paragraph(f"<b>NET PAYABLE SALARY ({cur})</b>", st["cell_b"]),
                    Paragraph(f"<b>{cur} {float(slip.net_payable or 0.0):,.2f}</b>", st["cell_rb"]),
                ]
            ],
            colWidths=[350, 175],
        )
        net_box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ECFDF5")),
                    ("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor("#059669")),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(net_box)
        story.append(Spacer(1, 28))

        sig_tbl = Table(
            [
                [
                    Paragraph("_________________________<br/>Employee Signature", st["sub"]),
                    Paragraph("_________________________<br/>Accounts / Payroll Officer", st["sub"]),
                    Paragraph("_________________________<br/>Principal / Authorized", st["sub"]),
                ]
            ],
            colWidths=[175, 175, 175],
        )
        story.append(sig_tbl)
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Generated electronically on {datetime.now().strftime('%d-%b-%Y %I:%M %p')}", st["sub"]))

        doc.build(story)
        return output_path

    @staticmethod
    def generate_payroll_report_pdf(
        db: Session,
        run_id: int,
        output_path: str,
        actor_user: Optional[User] = None,
    ) -> str:
        PayrollSecurityGuard.require_permission("payroll.reports.VIEW", actor_user)
        summary = PayrollService.get_monthly_payroll_summary(db, run_id, actor_user=actor_user)
        run = summary["run"]

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        meta = _school_header_info(db)
        st = _styles()
        cur = meta["currency"]

        doc = SimpleDocTemplate(
            output_path, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24
        )
        story: List[Any] = []
        story.append(Paragraph(meta["name"].upper(), st["title"]))
        story.append(Paragraph(f"MONTHLY PAYROLL REGISTER — {run.period_label.upper()} ({run.run_code})", st["badge"]))
        story.append(
            Paragraph(
                f"Status: {run.status} | Locked: {'YES' if run.is_locked else 'NO'} | "
                f"Active Slips: {summary['active_count']} | Reversed: {summary['reversed_count']}",
                st["sub"],
            )
        )
        story.append(Spacer(1, 10))

        # Register table
        headers = [
            "Slip No",
            "Employee",
            "Type",
            "Basic",
            "Allowances",
            "OT + Bonus",
            "Gross",
            "Att/Leave",
            "Tax/PF",
            "Loan/Adv",
            "Net Payable",
            "Status",
        ]
        rows = [[Paragraph(f"<b>{h}</b>", st["cell_b"]) for h in headers]]
        for s in summary["payslips"]:
            ot_bon = float(s.overtime_amount or 0.0) + float(s.bonus_amount or 0.0)
            att_lv = float(s.attendance_deduction or 0.0) + float(s.leave_deduction or 0.0)
            tax_pf = float(s.tax_deduction or 0.0) + float(s.provident_fund_deduction or 0.0) + float(s.insurance_deduction or 0.0)
            ln_adv = float(s.loan_deduction or 0.0) + float(s.advance_deduction or 0.0) + float(s.other_deduction or 0.0)
            rows.append(
                [
                    Paragraph(s.slip_no, st["cell_n"]),
                    Paragraph(f"{s.employee_name} ({s.employee_code})", st["cell_n"]),
                    Paragraph(s.employee_type.title(), st["cell_n"]),
                    Paragraph(f"{float(s.basic_salary or 0.0):,.0f}", st["cell_r"]),
                    Paragraph(f"{s.total_allowances:,.0f}", st["cell_r"]),
                    Paragraph(f"{ot_bon:,.0f}", st["cell_r"]),
                    Paragraph(f"{float(s.gross_earnings or 0.0):,.0f}", st["cell_r"]),
                    Paragraph(f"{att_lv:,.0f}", st["cell_r"]),
                    Paragraph(f"{tax_pf:,.0f}", st["cell_r"]),
                    Paragraph(f"{ln_adv:,.0f}", st["cell_r"]),
                    Paragraph(f"<b>{float(s.net_payable or 0.0):,.2f}</b>", st["cell_rb"]),
                    Paragraph(s.payment_status, st["cell_n"]),
                ]
            )

        rows.append(
            [
                Paragraph("<b>TOTAL (ACTIVE)</b>", st["cell_b"]),
                Paragraph(f"{summary['active_count']} Employees", st["cell_b"]),
                Paragraph("-", st["cell_n"]),
                Paragraph(f"<b>{summary['total_basic']:,.0f}</b>", st["cell_rb"]),
                Paragraph(f"<b>{summary['total_allowances']:,.0f}</b>", st["cell_rb"]),
                Paragraph(f"<b>{summary['total_overtime'] + summary['total_bonus']:,.0f}</b>", st["cell_rb"]),
                Paragraph(f"<b>{summary['total_gross']:,.2f}</b>", st["cell_rb"]),
                Paragraph(f"<b>{summary['total_att_leave_ded']:,.0f}</b>", st["cell_rb"]),
                Paragraph(f"<b>{summary['total_tax']:,.0f}</b>", st["cell_rb"]),
                Paragraph(f"<b>{summary['total_loan_adv_ded']:,.0f}</b>", st["cell_rb"]),
                Paragraph(f"<b>{cur} {summary['total_net']:,.2f}</b>", st["cell_rb"]),
                Paragraph(run.status, st["cell_b"]),
            ]
        )

        tbl = Table(rows, colWidths=[76, 130, 44, 54, 54, 56, 62, 54, 54, 54, 72, 54], repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(tbl)
        doc.build(story)
        return output_path

    @staticmethod
    def generate_employee_payment_history_pdf(
        db: Session,
        employee_type: str,
        employee_pk: int,
        output_path: str,
        actor_user: Optional[User] = None,
    ) -> str:
        PayrollSecurityGuard.require_permission("payroll.reports.VIEW", actor_user)
        hist = PayrollService.get_employee_payment_history(db, employee_type, employee_pk, actor_user=actor_user)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        meta = _school_header_info(db)
        st = _styles()
        cur = meta["currency"]

        doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
        story: List[Any] = []
        story.append(Paragraph(meta["name"].upper(), st["title"]))
        story.append(Paragraph("EMPLOYEE PAYROLL & PAYMENT HISTORY LEDGER", st["badge"]))
        story.append(
            Paragraph(
                f"{hist['employee_name']} ({hist['employee_code']}) &bull; {hist['designation']} &bull; Dept: {hist['department']}",
                st["sub"],
            )
        )
        story.append(Spacer(1, 10))

        headers = ["Period", "Slip No", "Gross", "Deductions", "Tax", "Net Paid", "Method", "Status"]
        rows = [[Paragraph(f"<b>{h}</b>", st["cell_b"]) for h in headers]]
        for s in hist["payslips"]:
            rows.append(
                [
                    Paragraph(f"{s.payroll_year}-{s.payroll_month:02d}", st["cell_n"]),
                    Paragraph(s.slip_no, st["cell_n"]),
                    Paragraph(f"{float(s.gross_earnings or 0.0):,.2f}", st["cell_r"]),
                    Paragraph(f"{float(s.total_deductions or 0.0):,.2f}", st["cell_r"]),
                    Paragraph(f"{float(s.tax_deduction or 0.0):,.2f}", st["cell_r"]),
                    Paragraph(f"<b>{float(s.net_payable or 0.0):,.2f}</b>", st["cell_rb"]),
                    Paragraph(s.payment_method, st["cell_n"]),
                    Paragraph(s.payment_status, st["cell_n"]),
                ]
            )
        rows.append(
            [
                Paragraph("<b>CUMULATIVE PAID</b>", st["cell_b"]),
                Paragraph("-", st["cell_n"]),
                Paragraph(f"<b>{hist['total_gross_paid']:,.2f}</b>", st["cell_rb"]),
                Paragraph(f"<b>{hist['total_deductions']:,.2f}</b>", st["cell_rb"]),
                Paragraph(f"<b>{hist['total_tax_paid']:,.2f}</b>", st["cell_rb"]),
                Paragraph(f"<b>{cur} {hist['total_net_paid']:,.2f}</b>", st["cell_rb"]),
                Paragraph("", st["cell_n"]),
                Paragraph(f"Loan Bal: {hist['active_loan_balance']:,.0f}", st["cell_b"]),
            ]
        )

        tbl = Table(rows, colWidths=[52, 85, 68, 68, 56, 75, 58, 65], repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(tbl)
        doc.build(story)
        return output_path
