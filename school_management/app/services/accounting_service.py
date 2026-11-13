"""
EduManage Pro - Accounting Service
Business logic for voucher creation, category seeder, validation, and openpyxl Cash Book export.
"""

from typing import Tuple, Optional, Dict, Any, List
from datetime import datetime, date
import os
from sqlalchemy.orm import Session
from app.models.accounting import AccountCategory, AccountTransaction
from app.repositories.accounting_repository import AccountingRepository
from app.models.activity import ActivityLog
from app.services.database_service import DatabaseService


class AccountingService:
    @staticmethod
    def seed_default_categories(db: Session) -> int:
        """
        Populates default standard school Chart of Accounts if empty.
        """
        default_categories = [
            # Income Heads
            {"name": "Student Fees & Tuition", "code": "INC-FEES", "type": "Income", "description": "Student regular tuition, exam, and admission collections", "is_system": True},
            {"name": "Government & Board Grants", "code": "INC-GRNT", "type": "Income", "description": "Government development grants, subsidies, and education board stipends", "is_system": True},
            {"name": "Donations & Endowments", "code": "INC-DONT", "type": "Income", "description": "Charitable gifts, trustee endowments, and alumni contributions", "is_system": False},
            {"name": "Facilities & Hall Rentals", "code": "INC-RENT", "type": "Income", "description": "Auditorium, sports ground, or cafeteria lease revenues", "is_system": False},
            {"name": "Other School Incomes", "code": "INC-MISC", "type": "Income", "description": "Syllabus sales, ID replacements, and miscellaneous receipts", "is_system": False},

            # Expense Heads
            {"name": "Teacher Salaries & Honorarium", "code": "EXP-TSAL", "type": "Expense", "description": "Monthly payroll disbursements for academic teachers", "is_system": True},
            {"name": "Staff Salaries & Allowances", "code": "EXP-SSAL", "type": "Expense", "description": "Payroll for accountants, librarians, security, and support staff", "is_system": True},
            {"name": "Electricity & Water Utilities", "code": "EXP-UTIL", "type": "Expense", "description": "Power, generator fuel, water, and municipal utility bills", "is_system": True},
            {"name": "Internet, IT & Software Subscriptions", "code": "EXP-IT", "type": "Expense", "description": "Broadband, domain hosting, SMS gateway, and computer lab licenses", "is_system": False},
            {"name": "Campus & Building Maintenance", "code": "EXP-MAINT", "type": "Expense", "description": "Plumbing, electrical repairs, painting, and classroom fixtures", "is_system": False},
            {"name": "Office Supplies & Stationery", "code": "EXP-STAT", "type": "Expense", "description": "Printing papers, registers, toner cartridges, and stamps", "is_system": False},
            {"name": "Sports, Cultural & Annual Events", "code": "EXP-EVNT", "type": "Expense", "description": "Annual sports day, prize ceremonies, milad, and debate festivals", "is_system": False},
            {"name": "Exam Papers & Evaluation Logistics", "code": "EXP-EXAM", "type": "Expense", "description": "Printing question papers, answer scripts, and invigilation expenses", "is_system": False},
            {"name": "Science Laboratory & Library", "code": "EXP-LAB", "type": "Expense", "description": "Lab chemicals, equipment, library book purchases, and periodicals", "is_system": False},
            {"name": "General Miscellaneous Expenses", "code": "EXP-MISC", "type": "Expense", "description": "Emergency transport, refreshments, courier, and incidental costs", "is_system": False},
        ]

        created_count = 0
        for item in default_categories:
            existing = AccountingRepository.get_category_by_code(db, item["code"])
            if not existing:
                AccountingRepository.create_category(db, item)
                created_count += 1
        return created_count

    @staticmethod
    def generate_voucher_number(db: Session, trans_type: str, tx_date: Optional[date] = None) -> str:
        """
        Generates sequential audit voucher number, e.g. VCH-2026-INC-00042
        """
        year = tx_date.year if tx_date else datetime.now().year
        type_prefix = "INC" if trans_type == "Income" else "EXP"
        total_in_year = AccountingRepository.get_transaction_count_by_year(db, year)
        return f"VCH-{year}-{type_prefix}-{total_in_year + 1:05d}"

    @staticmethod
    def record_transaction(
        db: Session,
        data: Dict[str, Any],
        actor_username: str = "admin"
    ) -> Tuple[Optional[AccountTransaction], Optional[str]]:
        """
        Validates and records a new financial voucher.
        """
        amount = float(data.get("amount", 0.0))
        if amount <= 0:
            return None, "Transaction amount must be strictly greater than 0.00."

        trans_type = data.get("type", "").capitalize()
        if trans_type not in ("Income", "Expense"):
            return None, "Transaction type must be 'Income' or 'Expense'."

        category_id = data.get("category_id")
        category = AccountingRepository.get_category_by_id(db, category_id)
        if not category:
            return None, "Selected account category does not exist."
        if category.type != trans_type:
            return None, f"Category '{category.name}' belongs to {category.type}, not {trans_type}."

        tx_date = data.get("transaction_date", date.today())
        voucher_no = data.get("voucher_no") or AccountingService.generate_voucher_number(db, trans_type, tx_date)

        # Duplicate check
        existing_vch = AccountingRepository.get_transaction_by_voucher(db, voucher_no)
        if existing_vch:
            return None, f"Voucher number '{voucher_no}' already exists in ledger."

        tx_data = {
            "voucher_no": voucher_no,
            "transaction_date": tx_date,
            "type": trans_type,
            "category_id": category_id,
            "amount": amount,
            "payment_method": data.get("payment_method", "Cash"),
            "reference_no": data.get("reference_no"),
            "paid_to_received_from": data.get("paid_to_received_from", "").strip() or "General Cashier",
            "description": data.get("description"),
            "recorded_by": actor_username,
            "status": "Approved"
        }

        tx = AccountingRepository.create_transaction(db, tx_data)

        # Audit log
        db.add(ActivityLog(
            user_id=DatabaseService.resolve_user_id(db, actor_username),
            username=actor_username,
            action="ACCOUNTING_VOUCHER_CREATED",
            module="ACCOUNTING",
            description=f"Created {trans_type} voucher {voucher_no}: ৳{amount:,.2f} ({category.name})",
            severity="INFO"
        ))
        db.commit()

        return tx, None

    @staticmethod
    def export_cash_book_excel(
        db: Session,
        output_file_path: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        school_info: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Exports clean, formatted Cash Book ledger to an Excel .xlsx workbook using openpyxl.
        """
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Cash_Book_Ledger"
            ws.views.sheetView[0].showGridLines = True

            school_name = school_info.get("name", "EduManage Pro Model High School") if school_info else "EduManage Pro High School"
            eiin = school_info.get("eiin", "134211") if school_info else "134211"

            # 1. School Header
            ws.merge_cells("A1:I1")
            ws["A1"] = school_name.upper()
            ws["A1"].font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
            ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

            ws.merge_cells("A2:I2")
            date_range_str = f"Period: {start_date} to {end_date}" if start_date and end_date else "Complete Financial History"
            ws["A2"] = f"OFFICIAL CASH BOOK & FINANCIAL TRANSACTION LEDGER | EIIN: {eiin} | {date_range_str}"
            ws["A2"].font = Font(name="Calibri", size=11, bold=True, color="475569")
            ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

            # 2. Table Headers
            headers = [
                "SL", "Date", "Voucher No", "Account Head", "Particulars / Payee",
                "Method", "Reference", "Credit (Income)", "Debit (Expense)"
            ]
            header_row = 4
            header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            thin_border = Border(
                left=Side(style="thin", color="CBD5E1"),
                right=Side(style="thin", color="CBD5E1"),
                top=Side(style="thin", color="CBD5E1"),
                bottom=Side(style="thin", color="CBD5E1")
            )

            for col_idx, h in enumerate(headers, 1):
                cell = ws.cell(row=header_row, column=col_idx, value=h)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border

            # 3. Ledger Rows
            transactions, _ = AccountingRepository.get_transactions(
                db, start_date=start_date, end_date=end_date, limit=5000
            )
            # Sort ascending for chronological cash book
            transactions.reverse()

            current_row = 5
            total_income = 0.0
            total_expense = 0.0

            for idx, tx in enumerate(transactions, 1):
                ws.cell(row=current_row, column=1, value=idx).alignment = Alignment(horizontal="center")
                ws.cell(row=current_row, column=2, value=str(tx.transaction_date)).alignment = Alignment(horizontal="center")
                ws.cell(row=current_row, column=3, value=tx.voucher_no).alignment = Alignment(horizontal="center")
                ws.cell(row=current_row, column=4, value=tx.category.name if tx.category else "General")
                ws.cell(row=current_row, column=5, value=tx.paid_to_received_from)
                ws.cell(row=current_row, column=6, value=tx.payment_method).alignment = Alignment(horizontal="center")
                ws.cell(row=current_row, column=7, value=tx.reference_no or "-").alignment = Alignment(horizontal="center")

                inc_cell = ws.cell(row=current_row, column=8)
                exp_cell = ws.cell(row=current_row, column=9)

                if tx.type == "Income":
                    inc_cell.value = tx.amount
                    inc_cell.number_format = "#,##0.00"
                    inc_cell.alignment = Alignment(horizontal="right")
                    inc_cell.font = Font(color="047857", bold=True)
                    exp_cell.value = "-"
                    exp_cell.alignment = Alignment(horizontal="center")
                    total_income += tx.amount
                else:
                    inc_cell.value = "-"
                    inc_cell.alignment = Alignment(horizontal="center")
                    exp_cell.value = tx.amount
                    exp_cell.number_format = "#,##0.00"
                    exp_cell.alignment = Alignment(horizontal="right")
                    exp_cell.font = Font(color="B91C1C", bold=True)
                    total_expense += tx.amount

                for c in range(1, 10):
                    ws.cell(row=current_row, column=c).border = thin_border

                current_row += 1

            # 4. Totals Row
            summary_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
            ws.merge_cells(f"A{current_row}:G{current_row}")
            summary_label = ws.cell(row=current_row, column=1, value="TOTAL TRANSACTIONS:")
            summary_label.font = Font(name="Calibri", size=11, bold=True)
            summary_label.alignment = Alignment(horizontal="right")

            tot_inc = ws.cell(row=current_row, column=8, value=total_income)
            tot_inc.font = Font(name="Calibri", size=11, bold=True, color="047857")
            tot_inc.number_format = "#,##0.00"
            tot_inc.alignment = Alignment(horizontal="right")

            tot_exp = ws.cell(row=current_row, column=9, value=total_expense)
            tot_exp.font = Font(name="Calibri", size=11, bold=True, color="B91C1C")
            tot_exp.number_format = "#,##0.00"
            tot_exp.alignment = Alignment(horizontal="right")

            for c in range(1, 10):
                ws.cell(row=current_row, column=c).fill = summary_fill
                ws.cell(row=current_row, column=c).border = thin_border

            current_row += 1

            # 5. Net Surplus / Deficit Row
            net_balance = total_income - total_expense
            ws.merge_cells(f"A{current_row}:G{current_row}")
            net_label = ws.cell(
                row=current_row,
                column=1,
                value="NET CLOSING CASH BOOK BALANCE (SURPLUS / DEFICIT):"
            )
            net_label.font = Font(name="Calibri", size=12, bold=True)
            net_label.alignment = Alignment(horizontal="right")

            ws.merge_cells(f"H{current_row}:I{current_row}")
            net_val = ws.cell(row=current_row, column=8, value=net_balance)
            net_val.font = Font(name="Calibri", size=13, bold=True, color="1E3A8A" if net_balance >= 0 else "B91C1C")
            net_val.number_format = "#,##0.00"
            net_val.alignment = Alignment(horizontal="center")

            for c in range(1, 10):
                ws.cell(row=current_row, column=c).fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
                ws.cell(row=current_row, column=c).border = thin_border

            # Auto-fit column widths
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

            ws.row_dimensions[1].height = 28
            ws.row_dimensions[2].height = 20
            ws.row_dimensions[4].height = 24

            os.makedirs(os.path.dirname(os.path.abspath(output_file_path)), exist_ok=True)
            wb.save(output_file_path)
            return True
        except Exception as e:
            print(f"[AccountingService] Failed to export Cash Book Excel: {e}")
            return False
