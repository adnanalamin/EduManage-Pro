"""
EduManage Pro - Enterprise Inventory & Fixed Assets Service
Business validation, Accounting Expense/Income reconciliation,
and Multi-Sheet openpyxl Workbook Export.
"""

from datetime import date
import os
from typing import Any, Dict, List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.repositories.inventory_repository import InventoryRepository
from app.services.accounting_service import AccountingService


class InventoryService:
    """Service layer for enterprise inventory reporting and accounting reconciliation."""

    @staticmethod
    def ensure_accounting_setup(session: Session) -> int:
        return AccountingService.seed_default_categories(session)

    @staticmethod
    def get_accounting_expense_summary(session: Session) -> Dict[str, Any]:
        purchases = InventoryRepository.get_purchases(session)
        received = [p for p in purchases if p.status == "Received"]
        assets = InventoryRepository.get_assets(session)
        sales_disposals = InventoryRepository.get_disposals_sales(session)

        purchase_spend = sum(float(p.total_amount or 0.0) for p in received)
        linked_purchase_vouchers = sum(1 for p in received if p.accounting_tx_id is not None)
        asset_spend = sum(float(a.cost or 0.0) for a in assets)
        linked_asset_vouchers = sum(1 for a in assets if a.accounting_tx_id is not None)
        sales_income = sum(float(s.total_amount or 0.0) for s in sales_disposals if s.record_type == "Sale")

        return {
            "total_purchase_spend": round(purchase_spend, 2),
            "linked_purchase_vouchers": linked_purchase_vouchers,
            "total_asset_cost": round(asset_spend, 2),
            "linked_asset_vouchers": linked_asset_vouchers,
            "total_sales_recovery": round(sales_income, 2),
        }

    @staticmethod
    def _style_headers(ws, headers: List[str], row_idx: int = 3, fill_hex: str = "1E3A8A") -> Border:
        fill = PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid")
        font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )
        for c_idx, title in enumerate(headers, 1):
            cell = ws.cell(row=row_idx, column=c_idx, value=title)
            cell.fill = fill
            cell.font = font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border
        ws.row_dimensions[row_idx].height = 24
        return border

    @staticmethod
    def _autofit(ws):
        for col in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col), default=10)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(max_len + 3, 12), 45)

    @staticmethod
    def export_inventory_comprehensive_excel(session: Session, file_path: str) -> str:
        """Exports complete 8-sheet Enterprise Inventory, Procurement & Fixed Asset Workbook."""
        products = InventoryRepository.get_products(session)
        alerts = InventoryRepository.get_low_stock_alerts(session)
        suppliers = InventoryRepository.get_suppliers(session)
        pos = InventoryRepository.get_purchase_orders(session)
        purchases = InventoryRepository.get_purchases(session)
        adjustments = InventoryRepository.get_adjustments(session)
        transfers = InventoryRepository.get_transfers(session)
        disposals = InventoryRepository.get_disposals_sales(session)
        assets = InventoryRepository.get_assets(session)

        wb = Workbook()

        # Sheet 1: Products & Stock
        ws1 = wb.active
        ws1.title = "Products & Stock"
        ws1["A1"] = f"EDUMANAGE PRO - INVENTORY CATALOG & STOCK VALUATION ({date.today().isoformat()})"
        ws1["A1"].font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
        b1 = InventoryService._style_headers(
            ws1,
            ["Code", "SKU", "Product Name", "Category", "Type", "In Stock", "Reorder Level", "Unit Cost", "Stock Value", "Status"],
            row_idx=3,
            fill_hex="1E3A8A",
        )
        for r_idx, p in enumerate(products, start=4):
            val = round(int(p.quantity_in_stock or 0) * float(p.unit_cost or 0.0), 2)
            vals = [
                p.item_code, p.sku or "-", p.name, p.category.name if p.category else "-", p.item_type,
                p.quantity_in_stock, p.reorder_level, float(p.unit_cost or 0.0), val, p.status,
            ]
            for c_idx, v in enumerate(vals, 1):
                ws1.cell(row=r_idx, column=c_idx, value=v).border = b1
        InventoryService._autofit(ws1)

        # Sheet 2: Low-Stock Alerts
        ws2 = wb.create_sheet("Low-Stock Alerts")
        ws2["A1"] = "LOW-STOCK & OUT-OF-STOCK REORDER ALERTS"
        b2 = InventoryService._style_headers(
            ws2, ["Code", "Product", "Category", "In Stock", "Reorder Level", "Suggested Reorder", "Unit", "Preferred Supplier", "Severity"],
            row_idx=3, fill_hex="991B1B",
        )
        for r_idx, al in enumerate(alerts, start=4):
            vals = [
                al["item_code"], al["name"], al["category"], al["quantity_in_stock"],
                al["reorder_level"], al["suggested_reorder_qty"], al["unit"], al["supplier"], al["severity"],
            ]
            for c_idx, v in enumerate(vals, 1):
                ws2.cell(row=r_idx, column=c_idx, value=v).border = b2
        InventoryService._autofit(ws2)

        # Sheet 3: Suppliers
        ws3 = wb.create_sheet("Suppliers")
        ws3["A1"] = "APPROVED VENDOR & SUPPLIER DIRECTORY"
        b3 = InventoryService._style_headers(
            ws3, ["Supplier Code", "Name", "Contact Person", "Phone", "Email", "Payment Terms", "Status"],
            row_idx=3, fill_hex="065F46",
        )
        for r_idx, s in enumerate(suppliers, start=4):
            vals = [s.supplier_code, s.name, s.contact_person or "-", s.phone or "-", s.email or "-", s.payment_terms, s.status]
            for c_idx, v in enumerate(vals, 1):
                ws3.cell(row=r_idx, column=c_idx, value=v).border = b3
        InventoryService._autofit(ws3)

        # Sheet 4: Purchase Orders
        ws4 = wb.create_sheet("Purchase Orders")
        ws4["A1"] = "PURCHASE ORDERS"
        b4 = InventoryService._style_headers(
            ws4, ["PO Number", "Order Date", "Supplier", "Destination Store", "Total Amount", "Status"],
            row_idx=3, fill_hex="0369A1",
        )
        for r_idx, po in enumerate(pos, start=4):
            vals = [
                po.po_number, str(po.order_date), po.supplier.name if po.supplier else "-",
                po.location.name if po.location else "-", float(po.total_amount or 0.0), po.status,
            ]
            for c_idx, v in enumerate(vals, 1):
                ws4.cell(row=r_idx, column=c_idx, value=v).border = b4
        InventoryService._autofit(ws4)

        # Sheet 5: Purchases & Accounting Vouchers
        ws5 = wb.create_sheet("Purchases & Expenses")
        ws5["A1"] = "GOODS PURCHASES & ACCOUNTING EXPENSE INTEGRATION"
        b5 = InventoryService._style_headers(
            ws5, ["Purchase No", "Date", "Supplier", "Invoice No", "Total Amount", "Paid", "Method", "Accounting Voucher", "Status"],
            row_idx=3, fill_hex="047857",
        )
        for r_idx, pur in enumerate(purchases, start=4):
            vch = pur.accounting_tx.voucher_no if pur.accounting_tx else "-"
            vals = [
                pur.purchase_no, str(pur.purchase_date), pur.supplier.name if pur.supplier else "-",
                pur.invoice_no or "-", float(pur.total_amount or 0.0), float(pur.paid_amount or 0.0),
                pur.payment_method, vch, pur.status,
            ]
            for c_idx, v in enumerate(vals, 1):
                ws5.cell(row=r_idx, column=c_idx, value=v).border = b5
        InventoryService._autofit(ws5)

        # Sheet 6: Adjustments & Transfers
        ws6 = wb.create_sheet("Adjustments & Transfers")
        ws6["A1"] = "STOCK ADJUSTMENTS & INTER-STORE TRANSFERS"
        b6 = InventoryService._style_headers(
            ws6, ["Kind", "Ref No", "Date", "Product", "From / Store", "To / Reason", "Delta / Qty", "Status"],
            row_idx=3, fill_hex="B45309",
        )
        r_idx = 4
        for adj in adjustments:
            vals = [
                "Adjustment", adj.adjustment_no, str(adj.adjustment_date), adj.item.name if adj.item else "-",
                adj.location.name if adj.location else "Global", adj.reason, adj.quantity_change, adj.adjustment_type,
            ]
            for c_idx, v in enumerate(vals, 1):
                ws6.cell(row=r_idx, column=c_idx, value=v).border = b6
            r_idx += 1
        for trf in transfers:
            vals = [
                "Transfer", trf.transfer_no, str(trf.transfer_date), trf.item.name if trf.item else "-",
                trf.from_location.name if trf.from_location else "-", trf.to_location.name if trf.to_location else "-",
                trf.quantity, trf.status,
            ]
            for c_idx, v in enumerate(vals, 1):
                ws6.cell(row=r_idx, column=c_idx, value=v).border = b6
            r_idx += 1
        InventoryService._autofit(ws6)

        # Sheet 7: Sales & Disposals
        ws7 = wb.create_sheet("Sales & Disposals")
        ws7["A1"] = "STOCK SALES, ISSUES & DISPOSALS"
        b7 = InventoryService._style_headers(
            ws7, ["Ref No", "Date", "Type", "Product", "Qty", "Unit Price", "Total", "Buyer / Recipient", "Voucher"],
            row_idx=3, fill_hex="4338CA",
        )
        for idx, d in enumerate(disposals, start=4):
            vch = d.accounting_tx.voucher_no if d.accounting_tx else "-"
            vals = [
                d.reference_no, str(d.transaction_date), d.record_type, d.item.name if d.item else "-",
                d.quantity, float(d.unit_price or 0.0), float(d.total_amount or 0.0), d.buyer_or_recipient or "-", vch,
            ]
            for c_idx, v in enumerate(vals, 1):
                ws7.cell(row=idx, column=c_idx, value=v).border = b7
        InventoryService._autofit(ws7)

        # Sheet 8: Fixed Assets
        ws8 = wb.create_sheet("Fixed Assets")
        ws8["A1"] = "SCHOOL FIXED ASSETS & EMPLOYEE CUSTODY REGISTER"
        b8 = InventoryService._style_headers(
            ws8, ["Asset ID", "Asset Name", "Serial Number", "Purchase Date", "Cost", "Location", "Department", "Assigned Employee", "Warranty", "Status"],
            row_idx=3, fill_hex="0F172A",
        )
        for idx, a in enumerate(assets, start=4):
            dept = a.department.name if a.department else (a.department_name or "-")
            vals = [
                a.asset_id, a.name, a.serial_number or "-", str(a.purchase_date), float(a.cost or 0.0),
                a.location, dept, a.assigned_employee or "Unassigned", a.warranty or "-", a.status,
            ]
            for c_idx, v in enumerate(vals, 1):
                ws8.cell(row=idx, column=c_idx, value=v).border = b8
        InventoryService._autofit(ws8)

        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        wb.save(file_path)
        return file_path
