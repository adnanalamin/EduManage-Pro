"""
EduManage Pro - Enterprise Inventory & Fixed Asset PDF Report Generator
Generates printable A4 landscape reports for:
1. Stock Valuation & Low-Stock Reorder Alert Report
2. Purchase Orders, Purchases & Accounting Expense Statement
3. Fixed Assets & Employee Custody Register
"""

from datetime import date
import os
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.inventory import FixedAsset, InventoryItem, InventoryPurchase, InventoryPurchaseOrder
from app.models.school import SchoolSetting


class InventoryReportsPDFGenerator:
    """Generates clean, printable PDF reports for inventory, procurement, and fixed assets."""

    @staticmethod
    def _add_header(story: list, title: str, subtitle: str, school: Optional[SchoolSetting]):
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("InvH1", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=15, alignment=1, textColor=colors.HexColor("#0F172A"))
        h2 = ParagraphStyle("InvH2", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, alignment=1, textColor=colors.HexColor("#1E3A8A"))
        sub = ParagraphStyle("InvSub", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, alignment=1, textColor=colors.HexColor("#64748B"))
        school_name = school.school_name if school and getattr(school, "school_name", None) else "EduManage Campus Inventory"
        story.append(Paragraph(school_name.upper(), h1))
        story.append(Paragraph(title, h2))
        story.append(Paragraph(f"{subtitle} • Generated: {date.today().strftime('%B %d, %Y')}", sub))
        story.append(Spacer(1, 10))

    @classmethod
    def generate_stock_and_low_stock_report(
        cls,
        products: List[InventoryItem],
        alerts: List[Dict[str, Any]],
        school: Optional[SchoolSetting] = None,
        output_path: str = "inventory_stock_report.pdf",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), leftMargin=28, rightMargin=28, topMargin=26, bottomMargin=26)
        styles = getSampleStyleSheet()
        sec = ParagraphStyle("InvSec", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, textColor=colors.HexColor("#1E293B"))
        story = []

        total_val = sum(int(p.quantity_in_stock or 0) * float(p.unit_cost or 0.0) for p in products)
        cls._add_header(
            story,
            "INVENTORY STOCK VALUATION & LOW-STOCK ALERT REPORT",
            f"Products: {len(products)} | Total Stock Valuation: {total_val:,.2f} | Low-Stock Alerts: {len(alerts)}",
            school,
        )

        story.append(Paragraph("1. Low-Stock & Out-of-Stock Alerts", sec))
        story.append(Spacer(1, 4))
        a_rows = [["Code", "Product Name", "Category", "In Stock", "Reorder Level", "Suggested Qty", "Supplier", "Severity"]]
        for al in alerts:
            a_rows.append([
                al["item_code"], al["name"][:28], al["category"][:20], str(al["quantity_in_stock"]),
                str(al["reorder_level"]), str(al["suggested_reorder_qty"]), al["supplier"][:22], al["severity"],
            ])
        if len(a_rows) == 1:
            a_rows.append(["-", "All inventory stock levels are healthy", "-", "-", "-", "-", "-", "OK"])
        at = Table(a_rows, colWidths=[70, 165, 105, 55, 65, 70, 130, 110], repeatRows=1)
        at.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#991B1B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ]))
        story.append(at)
        story.append(Spacer(1, 10))

        story.append(Paragraph("2. Complete Product Stock Valuation", sec))
        story.append(Spacer(1, 4))
        p_rows = [["Code", "Product Name", "Category", "Type", "Unit", "Qty", "Unit Cost", "Stock Value", "Status"]]
        for p in products:
            val = round(int(p.quantity_in_stock or 0) * float(p.unit_cost or 0.0), 2)
            p_rows.append([
                p.item_code, p.name[:30], (p.category.name if p.category else "-")[:20],
                p.item_type, p.unit, str(p.quantity_in_stock), f"{float(p.unit_cost or 0.0):.2f}", f"{val:.2f}", p.status,
            ])
        if len(p_rows) == 1:
            p_rows.append(["-", "No products registered", "-", "-", "-", "0", "0.00", "0.00", "-"])
        pt = Table(p_rows, colWidths=[70, 175, 110, 75, 45, 45, 70, 80, 90], repeatRows=1)
        pt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        story.append(pt)
        doc.build(story)
        return output_path

    @classmethod
    def generate_procurement_and_expense_report(
        cls,
        purchase_orders: List[InventoryPurchaseOrder],
        purchases: List[InventoryPurchase],
        school: Optional[SchoolSetting] = None,
        output_path: str = "inventory_procurement_report.pdf",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), leftMargin=28, rightMargin=28, topMargin=26, bottomMargin=26)
        styles = getSampleStyleSheet()
        sec = ParagraphStyle("InvProcSec", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, textColor=colors.HexColor("#065F46"))
        story = []

        total_spend = sum(float(p.total_amount or 0.0) for p in purchases if p.status == "Received")
        cls._add_header(
            story,
            "PROCUREMENT, PURCHASE ORDERS & ACCOUNTING EXPENSE STATEMENT",
            f"Purchase Orders: {len(purchase_orders)} | Goods Receipts: {len(purchases)} | Total Spend: {total_spend:,.2f}",
            school,
        )

        story.append(Paragraph("1. Purchases & Linked Accounting Expense Vouchers", sec))
        story.append(Spacer(1, 4))
        rows = [["Purchase No", "Date", "Supplier", "Invoice No", "Total", "Paid", "Method", "Accounting Voucher", "Status"]]
        for pur in purchases:
            vch = pur.accounting_tx.voucher_no if pur.accounting_tx else "-"
            rows.append([
                pur.purchase_no, str(pur.purchase_date), (pur.supplier.name if pur.supplier else "-")[:28],
                pur.invoice_no or "-", f"{float(pur.total_amount or 0.0):.2f}", f"{float(pur.paid_amount or 0.0):.2f}",
                pur.payment_method, vch, pur.status,
            ])
        if len(rows) == 1:
            rows.append(["-", "-", "No purchase records", "-", "0.00", "0.00", "-", "-", "-"])
        tbl = Table(rows, colWidths=[95, 70, 150, 80, 70, 70, 70, 115, 60], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ]))
        story.append(tbl)
        doc.build(story)
        return output_path

    @classmethod
    def generate_fixed_asset_register_pdf(
        cls,
        assets: List[FixedAsset],
        school: Optional[SchoolSetting] = None,
        output_path: str = "fixed_asset_register.pdf",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), leftMargin=28, rightMargin=28, topMargin=26, bottomMargin=26)
        story = []
        total_cost = sum(float(a.cost or 0.0) for a in assets if a.status not in ("Disposed", "Lost"))
        cls._add_header(
            story,
            "FIXED ASSETS, CUSTODY & WARRANTY REGISTER",
            f"Total Assets: {len(assets)} | Active Capital Cost: {total_cost:,.2f}",
            school,
        )

        rows = [["Asset ID", "Asset Name", "Serial No", "Purchase Date", "Cost", "Location", "Department", "Assigned Employee", "Warranty", "Status"]]
        for a in assets:
            dept = a.department.name if a.department else (a.department_name or "-")
            rows.append([
                a.asset_id, a.name[:24], (a.serial_number or "-")[:16], str(a.purchase_date),
                f"{float(a.cost or 0.0):.2f}", a.location[:18], dept[:16],
                (a.assigned_employee or "Unassigned")[:20], (a.warranty or "-")[:16], a.status,
            ])
        if len(rows) == 1:
            rows.append(["-", "No fixed assets registered", "-", "-", "0.00", "-", "-", "-", "-", "-"])

        tbl = Table(rows, colWidths=[72, 115, 78, 65, 58, 82, 75, 95, 75, 65], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        story.append(tbl)
        doc.build(story)
        return output_path
