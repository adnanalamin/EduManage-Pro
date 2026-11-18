"""
EduManage Pro - Enterprise Financial PDF Reports (ReportLab)
Generates:
1. Official Student Fee Invoice PDF
2. Official Fee Refund Receipt PDF
3. Student Advance Credit Receipt PDF
4. Fee Due & Aging Report PDF
5. Fee Collection Report PDF
6. General Ledger / Cashbook Report PDF
7. Budget Variance Report PDF
"""

from datetime import datetime
import os
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A5, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _school_meta(school_info: Any) -> Dict[str, str]:
    if isinstance(school_info, dict):
        return {
            "name": str(school_info.get("name") or school_info.get("school_name") or "EduManage Pro Model High School"),
            "eiin": str(school_info.get("eiin") or school_info.get("eiin_number") or "134211"),
            "phone": str(school_info.get("phone") or "+880 1712-345678"),
            "address": str(school_info.get("address") or "Uttara, Dhaka, Bangladesh"),
        }
    if school_info is not None:
        return {
            "name": str(getattr(school_info, "school_name", None) or "EduManage Pro Model High School"),
            "eiin": str(getattr(school_info, "eiin_number", None) or "134211"),
            "phone": str(getattr(school_info, "phone", None) or "+880 1712-345678"),
            "address": str(getattr(school_info, "address", None) or "Uttara, Dhaka, Bangladesh"),
        }
    return {
        "name": "EduManage Pro Model High School",
        "eiin": "134211",
        "phone": "+880 1712-345678",
        "address": "Uttara, Dhaka, Bangladesh",
    }


def _build_header(story: List[Any], school_info: Any, doc_title: str, subtitle: str) -> Dict[str, ParagraphStyle]:
    meta = _school_meta(school_info)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("FinTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=15, leading=19, alignment=1, textColor=colors.HexColor("#1E3A8A"))
    sub_s = ParagraphStyle("FinSub", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, alignment=1, textColor=colors.HexColor("#475569"))
    badge_s = ParagraphStyle("FinBadge", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, leading=14, alignment=1, textColor=colors.HexColor("#0F172A"))
    cell_b = ParagraphStyle("FinCellB", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11)
    cell_n = ParagraphStyle("FinCellN", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10.5)
    cell_r = ParagraphStyle("FinCellR", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10.5, alignment=2)
    cell_rb = ParagraphStyle("FinCellRB", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, alignment=2)

    story.append(Paragraph(meta["name"].upper(), title_s))
    story.append(Paragraph(f"{meta['address']} &bull; EIIN: {meta['eiin']} &bull; Tel: {meta['phone']}", sub_s))
    story.append(Spacer(1, 6))
    story.append(Paragraph(doc_title, badge_s))
    story.append(Paragraph(f"{subtitle} | Generated: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}", sub_s))
    story.append(Spacer(1, 12))
    return {"cell_b": cell_b, "cell_n": cell_n, "cell_r": cell_r, "cell_rb": cell_rb, "sub": sub_s}


class FinancePDFGenerator:
    @staticmethod
    def generate_invoice_pdf(invoice, school_info: Any, output_path: str) -> bool:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
            story: List[Any] = []
            st = _build_header(story, school_info, f"STUDENT FEE INVOICE — {invoice.invoice_number}", f"Invoice Status: {invoice.status} | Due Date: {invoice.due_date}")

            stu = invoice.student
            cls_name = stu.school_class.name if stu and getattr(stu, "school_class", None) else "-"
            sec_name = stu.section.name if stu and getattr(stu, "section", None) else "-"
            info_tbl = Table([
                [Paragraph("<b>Student Name:</b>", st["cell_b"]), Paragraph(stu.full_name if stu else "-", st["cell_n"]), Paragraph("<b>Student ID:</b>", st["cell_b"]), Paragraph(stu.student_id if stu else "-", st["cell_n"])],
                [Paragraph("<b>Class / Section:</b>", st["cell_b"]), Paragraph(f"{cls_name} ({sec_name})", st["cell_n"]), Paragraph("<b>Roll Number:</b>", st["cell_b"]), Paragraph(f"#{stu.roll_number}" if stu else "-", st["cell_n"])],
            ], colWidths=[95, 175, 95, 155])
            info_tbl.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")), ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
            story.append(info_tbl)
            story.append(Spacer(1, 14))

            cat_name = invoice.fee_structure.category.name if invoice.fee_structure and invoice.fee_structure.category else "School Fee"
            rows = [
                [Paragraph("<b>Fee Head / Category</b>", st["cell_b"]), Paragraph("<b>Description</b>", st["cell_b"]), Paragraph("<b>Amount (BDT)</b>", st["cell_rb"])],
                [Paragraph(cat_name, st["cell_n"]), Paragraph(invoice.display_title, st["cell_n"]), Paragraph(f"{float(invoice.total_amount):,.2f}", st["cell_r"])],
                [Paragraph("Concessions", st["cell_n"]), Paragraph(f"Discount / Scholarship / Waiver ({invoice.discount_reason or '-'})", st["cell_n"]), Paragraph(f"- {float(invoice.discount_amount or 0.0):,.2f}", st["cell_r"])],
                [Paragraph("<b>Net Payable</b>", st["cell_b"]), Paragraph("", st["cell_n"]), Paragraph(f"<b>{float(invoice.net_amount):,.2f}</b>", st["cell_rb"])],
                [Paragraph("Payments Received", st["cell_n"]), Paragraph(f"Includes Advance Wallet Applied: BDT {float(invoice.advance_applied_amount or 0.0):,.2f}", st["cell_n"]), Paragraph(f"{float(invoice.paid_amount or 0.0):,.2f}", st["cell_r"])],
                [Paragraph("Refunded", st["cell_n"]), Paragraph("Authorized reversals / refunds", st["cell_n"]), Paragraph(f"{float(invoice.refunded_amount or 0.0):,.2f}", st["cell_r"])],
                [Paragraph("<b>OUTSTANDING DUE</b>", st["cell_b"]), Paragraph("", st["cell_n"]), Paragraph(f"<b>BDT {float(invoice.due_amount):,.2f}</b>", st["cell_rb"])],
            ]
            t = Table(rows, colWidths=[130, 270, 120])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FEF2F2") if float(invoice.due_amount) > 0.01 else colors.HexColor("#ECFDF5")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t)
            doc.build(story)
            return True
        except Exception as exc:
            print(f"[FinancePDFGenerator] Invoice PDF failed: {exc}")
            return False

    @staticmethod
    def generate_refund_receipt_pdf(refund, school_info: Any, output_path: str) -> bool:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            doc = SimpleDocTemplate(output_path, pagesize=landscape(A5), leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
            story: List[Any] = []
            st = _build_header(story, school_info, f"OFFICIAL REFUND VOUCHER — {refund.refund_no}", f"Refund Date: {refund.refund_date} | Processed By: {refund.processed_by}")
            stu = refund.student
            pay = refund.fee_payment
            t = Table([
                [Paragraph("<b>Student Name</b>", st["cell_b"]), Paragraph(stu.full_name if stu else "-", st["cell_n"]), Paragraph("<b>Student ID</b>", st["cell_b"]), Paragraph(stu.student_id if stu else "-", st["cell_n"])],
                [Paragraph("<b>Original Receipt</b>", st["cell_b"]), Paragraph(pay.receipt_no if pay else "-", st["cell_n"]), Paragraph("<b>Refund Channel</b>", st["cell_b"]), Paragraph(f"{refund.refund_method} ({refund.channel_detail or '-'})", st["cell_n"])],
                [Paragraph("<b>Reason</b>", st["cell_b"]), Paragraph(refund.reason, st["cell_n"]), Paragraph("<b>Refunded Amount</b>", st["cell_b"]), Paragraph(f"<b>BDT {float(refund.refund_amount):,.2f}</b>", st["cell_rb"])],
            ], colWidths=[105, 165, 105, 155])
            t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor("#B91C1C")), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FECACA")), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
            story.append(t)
            doc.build(story)
            return True
        except Exception as exc:
            print(f"[FinancePDFGenerator] Refund PDF failed: {exc}")
            return False

    @staticmethod
    def generate_due_report_pdf(report: Dict[str, Any], school_info: Any, output_path: str) -> bool:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=28, rightMargin=28, topMargin=30, bottomMargin=30)
            story: List[Any] = []
            st = _build_header(story, school_info, "STUDENT FEE DUE & AGING REPORT", f"As of {report['as_of_date']} | Defaulter Invoices: {report['invoice_count']} | Total Due: BDT {report['total_due']:,.2f}")

            rows = [[Paragraph("<b>Invoice</b>", st["cell_b"]), Paragraph("<b>Student</b>", st["cell_b"]), Paragraph("<b>Class</b>", st["cell_b"]), Paragraph("<b>Fee Head</b>", st["cell_b"]), Paragraph("<b>Aging</b>", st["cell_b"]), Paragraph("<b>Due (BDT)</b>", st["cell_rb"])]]
            for r in report["rows"][:250]:
                rows.append([
                    Paragraph(r["invoice_no"], st["cell_n"]),
                    Paragraph(f"{r['student_name']}<br/><font size='7' color='#64748B'>{r['student_id']}</font>", st["cell_n"]),
                    Paragraph(r["class_name"], st["cell_n"]),
                    Paragraph(r["title"][:36], st["cell_n"]),
                    Paragraph(r["aging_bucket"], st["cell_n"]),
                    Paragraph(f"{r['due_amount']:,.2f}", st["cell_rb"]),
                ])
            rows.append([Paragraph("", st["cell_b"]), Paragraph("<b>TOTAL OUTSTANDING</b>", st["cell_b"]), Paragraph("", st["cell_n"]), Paragraph("", st["cell_n"]), Paragraph("", st["cell_n"]), Paragraph(f"<b>{report['total_due']:,.2f}</b>", st["cell_rb"])])

            t = Table(rows, colWidths=[80, 130, 70, 125, 65, 70])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
            story.append(t)
            doc.build(story)
            return True
        except Exception as exc:
            print(f"[FinancePDFGenerator] Due report PDF failed: {exc}")
            return False

    @staticmethod
    def generate_collection_report_pdf(report: Dict[str, Any], school_info: Any, output_path: str) -> bool:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=28, rightMargin=28, topMargin=30, bottomMargin=30)
            story: List[Any] = []
            period_lbl = f"{report.get('start_date') or 'All'} to {report.get('end_date') or 'Present'}"
            st = _build_header(story, school_info, "FEE COLLECTION REPORT", f"Period: {period_lbl} | Receipts: {report['payment_count']} | Net Collected: BDT {report['net_collected']:,.2f}")

            rows = [[Paragraph("<b>Receipt</b>", st["cell_b"]), Paragraph("<b>Date</b>", st["cell_b"]), Paragraph("<b>Student</b>", st["cell_b"]), Paragraph("<b>Category</b>", st["cell_b"]), Paragraph("<b>Channel</b>", st["cell_b"]), Paragraph("<b>Net Paid</b>", st["cell_rb"])]]
            for r in report["rows"][:250]:
                rows.append([
                    Paragraph(r["receipt_no"], st["cell_n"]),
                    Paragraph(str(r["payment_date"]), st["cell_n"]),
                    Paragraph(r["student_name"], st["cell_n"]),
                    Paragraph(r["category"], st["cell_n"]),
                    Paragraph(r["payment_method"], st["cell_n"]),
                    Paragraph(f"{r['net_amount']:,.2f}", st["cell_rb"]),
                ])
            rows.append([Paragraph("", st["cell_b"]), Paragraph("", st["cell_n"]), Paragraph("<b>NET COLLECTED</b>", st["cell_b"]), Paragraph("", st["cell_n"]), Paragraph("", st["cell_n"]), Paragraph(f"<b>{report['net_collected']:,.2f}</b>", st["cell_rb"])])

            t = Table(rows, colWidths=[85, 65, 135, 95, 80, 80])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ECFDF5")), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
            story.append(t)
            doc.build(story)
            return True
        except Exception as exc:
            print(f"[FinancePDFGenerator] Collection report PDF failed: {exc}")
            return False

    @staticmethod
    def generate_cashbook_pdf(ledger: Dict[str, Any], school_info: Any, output_path: str) -> bool:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=26, rightMargin=26, topMargin=28, bottomMargin=28)
            story: List[Any] = []
            st = _build_header(story, school_info, "GENERAL LEDGER & CASHBOOK STATEMENT", f"Entries: {ledger['entry_count']} | Closing Balance: BDT {ledger['closing_balance']:,.2f}")

            rows = [[Paragraph("<b>Voucher</b>", st["cell_b"]), Paragraph("<b>Date</b>", st["cell_b"]), Paragraph("<b>Head / Party</b>", st["cell_b"]), Paragraph("<b>Channel</b>", st["cell_b"]), Paragraph("<b>Credit</b>", st["cell_rb"]), Paragraph("<b>Debit</b>", st["cell_rb"]), Paragraph("<b>Balance</b>", st["cell_rb"])]]
            for e in ledger["entries"][:250]:
                rows.append([
                    Paragraph(e["voucher_no"], st["cell_n"]),
                    Paragraph(str(e["date"]), st["cell_n"]),
                    Paragraph(f"{e['category_name']}<br/><font size='7' color='#64748B'>{e['party']}</font>", st["cell_n"]),
                    Paragraph(e["payment_method"], st["cell_n"]),
                    Paragraph(f"{e['credit']:,.2f}" if e["credit"] > 0 else "-", st["cell_r"]),
                    Paragraph(f"{e['debit']:,.2f}" if e["debit"] > 0 else "-", st["cell_r"]),
                    Paragraph(f"{e['running_balance']:,.2f}", st["cell_rb"]),
                ])
            rows.append([Paragraph("", st["cell_b"]), Paragraph("", st["cell_n"]), Paragraph("<b>CLOSING TOTALS</b>", st["cell_b"]), Paragraph("", st["cell_n"]), Paragraph(f"<b>{ledger['total_credit']:,.2f}</b>", st["cell_rb"]), Paragraph(f"<b>{ledger['total_debit']:,.2f}</b>", st["cell_rb"]), Paragraph(f"<b>{ledger['closing_balance']:,.2f}</b>", st["cell_rb"])])

            t = Table(rows, colWidths=[85, 60, 145, 65, 62, 62, 66])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
            story.append(t)
            doc.build(story)
            return True
        except Exception as exc:
            print(f"[FinancePDFGenerator] Cashbook PDF failed: {exc}")
            return False

    @staticmethod
    def generate_budget_report_pdf(report: Dict[str, Any], school_info: Any, output_path: str) -> bool:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
            story: List[Any] = []
            st = _build_header(story, school_info, f"INSTITUTIONAL BUDGET VARIANCE REPORT — FY {report['fiscal_year']}", f"Allocated: BDT {report['total_allocated']:,.2f} | Utilized: BDT {report['total_actual']:,.2f}")

            rows = [[Paragraph("<b>Code</b>", st["cell_b"]), Paragraph("<b>Budget Title / Head</b>", st["cell_b"]), Paragraph("<b>Allocated</b>", st["cell_rb"]), Paragraph("<b>Actual</b>", st["cell_rb"]), Paragraph("<b>Remaining</b>", st["cell_rb"]), Paragraph("<b>Status</b>", st["cell_b"])]]
            for r in report["rows"]:
                rows.append([
                    Paragraph(r["budget_code"], st["cell_n"]),
                    Paragraph(f"{r['title']}<br/><font size='7' color='#64748B'>{r['category_name']} ({r['period_type']})</font>", st["cell_n"]),
                    Paragraph(f"{r['allocated_amount']:,.2f}", st["cell_r"]),
                    Paragraph(f"{r['actual_amount']:,.2f}", st["cell_r"]),
                    Paragraph(f"{r['remaining_amount']:,.2f}", st["cell_r"]),
                    Paragraph(f"{r['alert_status']} ({r['utilization_pct']}%)", st["cell_b"]),
                ])

            t = Table(rows, colWidths=[75, 175, 72, 72, 72, 74])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
            story.append(t)
            doc.build(story)
            return True
        except Exception as exc:
            print(f"[FinancePDFGenerator] Budget report PDF failed: {exc}")
            return False
