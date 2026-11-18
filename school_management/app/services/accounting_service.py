"""
EduManage Pro - Enterprise Accounting, Ledger, Cashbook, Budget & Audit Service
Business logic for Chart of Accounts, Income/Expense Vouchers, Non-Destructive Voucher
Reversals, General Ledger, Cashbook, Budget Variance Alerts, Comprehensive Financial Summary,
Financial Audit Trail, and openpyxl Excel Exports.
"""

from datetime import date, datetime
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.accounting import (
    AccountBudget,
    AccountCategory,
    AccountTransaction,
    FinancialAuditLog,
)
from app.models.base import utc_now
from app.models.fee import PAYMENT_CHANNELS, StudentAdvanceCredit, StudentFee, normalize_payment_channel
from app.repositories.accounting_repository import AccountingRepository
from app.services.database_service import DatabaseService


class AccountingService:
    @staticmethod
    def record_audit_log(
        db: Session,
        module: str,
        entity_type: str,
        entity_id: Optional[int],
        reference_no: Optional[str],
        action: str,
        amount: Optional[float] = None,
        before_snapshot: Optional[Dict[str, Any]] = None,
        after_snapshot: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        actor_username: str = "system",
        commit: bool = False,
    ) -> FinancialAuditLog:
        entry = FinancialAuditLog(
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            reference_no=reference_no,
            action=action,
            amount=amount,
            before_snapshot=json.dumps(before_snapshot, default=str) if before_snapshot is not None else None,
            after_snapshot=json.dumps(after_snapshot, default=str) if after_snapshot is not None else None,
            reason=reason,
            actor_username=actor_username or "system",
        )
        db.add(entry)
        if commit:
            db.commit()
            db.refresh(entry)
        else:
            db.flush()
        return entry

    @staticmethod
    def seed_default_categories(db: Session) -> int:
        """
        Populates default standard school Chart of Accounts if missing.
        """
        default_categories = [
            # Income Heads
            {"name": "Student Fees & Tuition", "code": "INC-FEES", "type": "Income", "description": "Student regular tuition, exam, transport, hostel, library, and admission collections", "is_system": True},
            {"name": "Student Advance Deposits", "code": "INC-ADV", "type": "Income", "description": "Advance fee deposits held in student credit wallets", "is_system": True},
            {"name": "Government & Board Grants", "code": "INC-GRNT", "type": "Income", "description": "Government development grants, subsidies, and education board stipends", "is_system": True},
            {"name": "Donations & Endowments", "code": "INC-DONT", "type": "Income", "description": "Charitable gifts, trustee endowments, and alumni contributions", "is_system": False},
            {"name": "Facilities & Hall Rentals", "code": "INC-RENT", "type": "Income", "description": "Auditorium, sports ground, or cafeteria lease revenues", "is_system": False},
            {"name": "Other School Incomes", "code": "INC-MISC", "type": "Income", "description": "Syllabus sales, ID replacements, and miscellaneous receipts", "is_system": False},

            # Expense Heads
            {"name": "Teacher Salaries & Honorarium", "code": "EXP-TSAL", "type": "Expense", "description": "Monthly payroll disbursements for academic teachers", "is_system": True},
            {"name": "Staff Salaries & Allowances", "code": "EXP-SSAL", "type": "Expense", "description": "Payroll for accountants, librarians, security, and support staff", "is_system": True},
            {"name": "Employee Loans & Salary Advances", "code": "EXP-LOAN", "type": "Expense", "description": "Disbursed staff and teacher loans and salary advances recovered via payroll", "is_system": True},
            {"name": "Fee Refunds & Reversals", "code": "EXP-RFND", "type": "Expense", "description": "Authorized student fee refunds, advance withdrawals, and adjustments", "is_system": True},
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
    def generate_voucher_number(db: Session, trans_type: str, tx_date: Optional[date] = None, prefix_override: Optional[str] = None) -> str:
        """
        Generates sequential unique audit voucher number, e.g. VCH-2026-INC-00042 or REV-2026-00001
        """
        year = (tx_date or date.today()).year
        type_prefix = prefix_override or ("INC" if trans_type == "Income" else "EXP")
        total_in_year = AccountingRepository.get_transaction_count_by_year(db, year)
        seq = total_in_year + 1
        while True:
            candidate = f"VCH-{year}-{type_prefix}-{seq:05d}" if not prefix_override else f"{prefix_override}-{year}-{seq:05d}"
            if not AccountingRepository.get_transaction_by_voucher(db, candidate):
                return candidate
            seq += 1

    @staticmethod
    def record_transaction(
        db: Session,
        data: Dict[str, Any],
        actor_username: str = "admin",
        commit: bool = True,
    ) -> Tuple[Optional[AccountTransaction], Optional[str]]:
        """
        Validates and records a new immutable financial voucher.
        Normalizes payment channel into Cash | Bank | Card | Mobile Banking | Other.
        """
        amount = float(data.get("amount", 0.0))
        if amount <= 0:
            return None, "Transaction amount must be strictly greater than 0.00."

        trans_type = (data.get("type") or "").capitalize()
        if trans_type not in ("Income", "Expense"):
            return None, "Transaction type must be 'Income' or 'Expense'."

        category_id = data.get("category_id")
        category = AccountingRepository.get_category_by_id(db, category_id)
        if not category:
            return None, "Selected account category does not exist."
        if category.type != trans_type and data.get("entry_kind", "Standard") != "Reversal":
            return None, f"Category '{category.name}' belongs to {category.type}, not {trans_type}."

        idempotency_key = data.get("idempotency_key")
        if idempotency_key:
            existing_idem = (
                db.query(AccountTransaction)
                .filter(AccountTransaction.idempotency_key == idempotency_key)
                .first()
            )
            if existing_idem:
                return existing_idem, None

        tx_date = data.get("transaction_date", date.today())
        voucher_no = data.get("voucher_no") or AccountingService.generate_voucher_number(db, trans_type, tx_date)

        existing_vch = AccountingRepository.get_transaction_by_voucher(db, voucher_no)
        if existing_vch:
            return None, f"Voucher number '{voucher_no}' already exists in ledger."

        norm_method, norm_detail = normalize_payment_channel(
            data.get("payment_method", "Cash"), data.get("channel_detail")
        )
        effective_actor = actor_username or data.get("recorded_by") or "Accountant"

        tx_data = {
            "voucher_no": voucher_no,
            "idempotency_key": idempotency_key,
            "transaction_date": tx_date,
            "type": trans_type,
            "entry_kind": data.get("entry_kind", "Standard"),
            "category_id": category_id,
            "academic_year_id": data.get("academic_year_id"),
            "amount": amount,
            "payment_method": norm_method,
            "channel_detail": norm_detail,
            "reference_no": data.get("reference_no"),
            "paid_to_received_from": (data.get("paid_to_received_from") or "").strip() or "General Cashier",
            "description": data.get("description"),
            "recorded_by": effective_actor,
            "approved_by": data.get("approved_by") or effective_actor,
            "approved_at": utc_now(),
            "status": data.get("status", "Approved"),
            "reversal_of_id": data.get("reversal_of_id"),
        }

        tx = AccountingRepository.create_transaction(db, tx_data, commit=False)

        AccountingService.record_audit_log(
            db,
            module="ACCOUNTING",
            entity_type="AccountTransaction",
            entity_id=tx.id,
            reference_no=tx.voucher_no,
            action="ACCOUNTING_VOUCHER_CREATED",
            amount=amount,
            after_snapshot={
                "voucher_no": tx.voucher_no,
                "type": trans_type,
                "category": category.name,
                "amount": amount,
                "payment_method": norm_method,
                "channel_detail": norm_detail,
                "party": tx.paid_to_received_from,
            },
            reason=tx.description,
            actor_username=effective_actor,
            commit=False,
        )
        DatabaseService.log_activity(
            db,
            action="ACCOUNTING_VOUCHER_CREATED",
            module="ACCOUNTING",
            description=f"Created {trans_type} voucher {voucher_no}: ৳{amount:,.2f} [{norm_method}] ({category.name})",
            username=effective_actor,
            entity_type="AccountTransaction",
            entity_id=str(tx.id),
            commit=False,
        )
        if commit:
            db.commit()
            db.refresh(tx)
        else:
            db.flush()
        return tx, None

    @staticmethod
    def reverse_transaction(
        db: Session,
        tx_id: int,
        reason: str,
        actor_username: str = "admin",
        reversal_date: Optional[date] = None,
        commit: bool = True,
    ) -> Tuple[Optional[AccountTransaction], str]:
        """
        Non-destructive voucher reversal. Marks the original voucher `Reversed` and posts
        a compensating contra-entry voucher linked via `reversal_of_id` so the general
        ledger and cashbook stay mathematically balanced with complete audit history.
        """
        if not reason or not reason.strip():
            return None, "Reversal reason is mandatory for audit compliance."

        orig = DatabaseService.lock_for_update(
            db.query(AccountTransaction)
            .options(joinedload(AccountTransaction.category))
            .filter(AccountTransaction.id == tx_id, AccountTransaction.is_deleted == False),
            db,
        ).first()
        if not orig:
            return None, "Original accounting voucher not found."
        if orig.is_reversed or orig.status == "Reversed":
            return None, f"Voucher '{orig.voucher_no}' has already been reversed."
        if orig.entry_kind == "Reversal":
            return None, "A reversal contra-voucher cannot itself be reversed."

        contra_type = "Expense" if orig.type == "Income" else "Income"
        rev_date = reversal_date or date.today()
        rev_voucher = AccountingService.generate_voucher_number(db, contra_type, rev_date, prefix_override="REV")

        before_snap = {
            "voucher_no": orig.voucher_no,
            "type": orig.type,
            "amount": float(orig.amount),
            "status": orig.status,
            "is_reversed": orig.is_reversed,
        }

        orig.is_reversed = True
        orig.status = "Reversed"
        orig.reversed_by = actor_username
        orig.reversed_at = utc_now()
        orig.reversal_reason = reason.strip()

        contra_tx = AccountTransaction(
            voucher_no=rev_voucher,
            transaction_date=rev_date,
            type=contra_type,
            entry_kind="Reversal",
            category_id=orig.category_id,
            academic_year_id=orig.academic_year_id,
            amount=float(orig.amount),
            payment_method=orig.payment_method,
            channel_detail=orig.channel_detail,
            reference_no=orig.voucher_no,
            paid_to_received_from=orig.paid_to_received_from,
            description=f"Reversal of {orig.voucher_no}: {reason.strip()}",
            recorded_by=actor_username,
            approved_by=actor_username,
            approved_at=utc_now(),
            status="Approved",
            is_reversed=False,
            reversal_of_id=orig.id,
        )
        db.add(contra_tx)
        db.flush()

        AccountingService.record_audit_log(
            db,
            module="ACCOUNTING",
            entity_type="AccountTransaction",
            entity_id=orig.id,
            reference_no=f"{orig.voucher_no} -> {rev_voucher}",
            action="ACCOUNTING_VOUCHER_REVERSED",
            amount=float(orig.amount),
            before_snapshot=before_snap,
            after_snapshot={
                "original_status": "Reversed",
                "contra_voucher_no": rev_voucher,
                "contra_type": contra_type,
                "amount": float(orig.amount),
            },
            reason=reason.strip(),
            actor_username=actor_username,
            commit=False,
        )
        DatabaseService.log_activity(
            db,
            action="ACCOUNTING_VOUCHER_REVERSED",
            module="ACCOUNTING",
            description=f"Reversed voucher {orig.voucher_no} via contra-entry {rev_voucher} (৳{float(orig.amount):,.2f}). Reason: {reason.strip()}",
            username=actor_username,
            severity="WARNING",
            entity_type="AccountTransaction",
            entity_id=str(orig.id),
            commit=False,
        )
        if commit:
            db.commit()
            db.refresh(contra_tx)
        else:
            db.flush()
        return contra_tx, f"Voucher {orig.voucher_no} reversed cleanly via contra-entry {rev_voucher}."

    # -------------------------------------------------------------
    # General Ledger & Cashbook
    # -------------------------------------------------------------
    @staticmethod
    def get_general_ledger(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        payment_method: Optional[str] = None,
        include_reversed: bool = True,
    ) -> Dict[str, Any]:
        """
        Builds chronological General Ledger with Opening Balance, Credit, Debit, and Running Balance.
        """
        opening_balance = 0.0
        if start_date:
            prior_q = db.query(AccountTransaction).filter(
                AccountTransaction.is_deleted == False,
                AccountTransaction.status.in_(("Approved", "Reversed")),
                AccountTransaction.transaction_date < start_date,
            )
            if category_id:
                prior_q = prior_q.filter(AccountTransaction.category_id == category_id)
            if payment_method and payment_method.lower() not in ("all", "all channels"):
                prior_q = prior_q.filter(AccountTransaction.payment_method == payment_method)
            for ptx in prior_q.all():
                amt = float(ptx.amount or 0.0)
                opening_balance += amt if ptx.type == "Income" else -amt

        query = (
            db.query(AccountTransaction)
            .options(joinedload(AccountTransaction.category))
            .filter(
                AccountTransaction.is_deleted == False,
                AccountTransaction.status.in_(("Approved", "Reversed")),
            )
        )
        if not include_reversed:
            query = query.filter(AccountTransaction.is_reversed == False, AccountTransaction.entry_kind != "Reversal")
        if start_date:
            query = query.filter(AccountTransaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(AccountTransaction.transaction_date <= end_date)
        if category_id:
            query = query.filter(AccountTransaction.category_id == category_id)
        if payment_method and payment_method.lower() not in ("all", "all channels"):
            query = query.filter(AccountTransaction.payment_method == payment_method)

        txs = query.order_by(AccountTransaction.transaction_date.asc(), AccountTransaction.id.asc()).all()

        running = round(opening_balance, 2)
        total_credit = 0.0
        total_debit = 0.0
        entries: List[Dict[str, Any]] = []

        for tx in txs:
            amt = float(tx.amount or 0.0)
            credit = amt if tx.type == "Income" else 0.0
            debit = amt if tx.type == "Expense" else 0.0
            running = round(running + credit - debit, 2)
            total_credit += credit
            total_debit += debit

            entries.append(
                {
                    "id": tx.id,
                    "date": tx.transaction_date,
                    "voucher_no": tx.voucher_no,
                    "entry_kind": tx.entry_kind,
                    "type": tx.type,
                    "category_code": tx.category.code if tx.category else "-",
                    "category_name": tx.category.name if tx.category else "General",
                    "party": tx.paid_to_received_from,
                    "payment_method": tx.payment_method,
                    "channel_detail": tx.channel_detail or "-",
                    "reference_no": tx.reference_no or "-",
                    "description": tx.description or "",
                    "credit": round(credit, 2),
                    "debit": round(debit, 2),
                    "running_balance": running,
                    "status": tx.status,
                    "is_reversed": bool(tx.is_reversed),
                    "reversal_of_id": tx.reversal_of_id,
                    "recorded_by": tx.recorded_by,
                }
            )

        return {
            "opening_balance": round(opening_balance, 2),
            "total_credit": round(total_credit, 2),
            "total_debit": round(total_debit, 2),
            "closing_balance": running,
            "entry_count": len(entries),
            "entries": entries,
        }

    @staticmethod
    def get_cashbook(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        payment_method: Optional[str] = None,
    ) -> Dict[str, Any]:
        ledger = AccountingService.get_general_ledger(
            db,
            start_date=start_date,
            end_date=end_date,
            payment_method=payment_method,
            include_reversed=True,
        )
        summary = AccountingRepository.get_financial_summary(db, start_date=start_date, end_date=end_date)
        ledger["channel_balances"] = summary["channel_balances"]
        ledger["cash_in_hand"] = summary["cash_in_hand"]
        return ledger

    # -------------------------------------------------------------
    # Budgets & Variance Tracking
    # -------------------------------------------------------------
    @staticmethod
    def create_or_update_budget(
        db: Session,
        data: Dict[str, Any],
        actor_username: str = "admin",
    ) -> Tuple[Optional[AccountBudget], str]:
        category_id = data.get("category_id")
        cat = AccountingRepository.get_category_by_id(db, category_id)
        if not cat:
            return None, "Selected Account Category does not exist."

        allocated = float(data.get("allocated_amount", 0.0))
        if allocated < 0:
            return None, "Allocated budget amount cannot be negative."

        fiscal_year = int(data.get("fiscal_year") or date.today().year)
        threshold = float(data.get("alert_threshold_pct", 80.0))

        budget_id = data.get("id")
        if budget_id:
            budget = db.query(AccountBudget).filter(AccountBudget.id == budget_id, AccountBudget.is_deleted == False).first()
            if not budget:
                return None, "Budget record not found."
            before_snap = {"allocated_amount": float(budget.allocated_amount), "status": budget.status}
            budget.title = (data.get("title") or budget.title).strip()
            budget.fiscal_year = fiscal_year
            budget.academic_year_id = data.get("academic_year_id", budget.academic_year_id)
            budget.category_id = category_id
            budget.period_type = data.get("period_type", budget.period_type)
            budget.period_month = data.get("period_month", budget.period_month)
            budget.allocated_amount = allocated
            budget.alert_threshold_pct = threshold
            budget.status = data.get("status", budget.status)
            budget.notes = data.get("notes", budget.notes)
            action = "BUDGET_UPDATED"
        else:
            count = db.query(func.count(AccountBudget.id)).scalar() or 0
            seq = count + 1
            while True:
                code = f"BDG-{fiscal_year}-{seq:04d}"
                if not db.query(AccountBudget.id).filter(AccountBudget.budget_code == code).first():
                    break
                seq += 1

            before_snap = None
            budget = AccountBudget(
                budget_code=code,
                title=(data.get("title") or f"{cat.name} Budget {fiscal_year}").strip(),
                fiscal_year=fiscal_year,
                academic_year_id=data.get("academic_year_id"),
                category_id=category_id,
                period_type=data.get("period_type", "Annual"),
                period_month=data.get("period_month"),
                allocated_amount=allocated,
                alert_threshold_pct=threshold,
                status=data.get("status", "Active"),
                created_by=actor_username,
                approved_by=data.get("approved_by") or actor_username,
                notes=data.get("notes"),
            )
            db.add(budget)
            db.flush()
            action = "BUDGET_CREATED"

        AccountingService.record_audit_log(
            db,
            module="BUDGET",
            entity_type="AccountBudget",
            entity_id=budget.id,
            reference_no=budget.budget_code,
            action=action,
            amount=allocated,
            before_snapshot=before_snap,
            after_snapshot={"budget_code": budget.budget_code, "allocated_amount": allocated, "category": cat.name},
            reason=budget.notes,
            actor_username=actor_username,
            commit=False,
        )
        db.commit()
        db.refresh(budget)
        return budget, f"Budget '{budget.budget_code}' saved successfully."

    @staticmethod
    def get_budget_variance_report(
        db: Session,
        fiscal_year: Optional[int] = None,
        academic_year_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        target_year = fiscal_year or date.today().year
        budgets = AccountingRepository.get_budgets(
            db, fiscal_year=target_year if not academic_year_id else fiscal_year, academic_year_id=academic_year_id
        )

        # Compute actual utilization per category for the fiscal year / academic year
        tx_q = db.query(AccountTransaction).filter(
            AccountTransaction.is_deleted == False,
            AccountTransaction.status.in_(("Approved", "Reversed")),
        )
        if fiscal_year or not academic_year_id:
            from sqlalchemy import extract
            tx_q = tx_q.filter(extract("year", AccountTransaction.transaction_date) == target_year)
        if academic_year_id:
            tx_q = tx_q.filter(AccountTransaction.academic_year_id == academic_year_id)
        txs = tx_q.all()

        actual_by_cat: Dict[int, float] = {}
        for tx in txs:
            cid = tx.category_id
            amt = float(tx.amount or 0.0)
            if tx.entry_kind == "Reversal":
                actual_by_cat[cid] = actual_by_cat.get(cid, 0.0) - amt
            else:
                actual_by_cat[cid] = actual_by_cat.get(cid, 0.0) + amt

        rows: List[Dict[str, Any]] = []
        total_allocated = 0.0
        total_actual = 0.0
        over_budget_count = 0

        for b in budgets:
            alloc = float(b.allocated_amount or 0.0)
            actual = round(max(0.0, actual_by_cat.get(b.category_id, 0.0)), 2)
            remaining = round(alloc - actual, 2)
            util_pct = round((actual / alloc * 100.0), 1) if alloc > 0 else (100.0 if actual > 0 else 0.0)
            cat_type = b.category.type if b.category else "Expense"

            if cat_type == "Expense":
                if actual > alloc:
                    alert_status = "Over Budget"
                    over_budget_count += 1
                elif util_pct >= float(b.alert_threshold_pct or 80.0):
                    alert_status = "Warning"
                else:
                    alert_status = "Healthy"
            else:
                alert_status = "Achieved" if actual >= alloc else "In Progress"

            total_allocated += alloc
            total_actual += actual

            rows.append(
                {
                    "id": b.id,
                    "budget_code": b.budget_code,
                    "title": b.title,
                    "fiscal_year": b.fiscal_year,
                    "category_id": b.category_id,
                    "category_code": b.category.code if b.category else "-",
                    "category_name": b.category.name if b.category else "-",
                    "category_type": cat_type,
                    "period_type": b.period_type,
                    "allocated_amount": round(alloc, 2),
                    "actual_amount": actual,
                    "remaining_amount": remaining,
                    "utilization_pct": util_pct,
                    "alert_status": alert_status,
                    "status": b.status,
                }
            )

        return {
            "fiscal_year": target_year,
            "budget_count": len(rows),
            "over_budget_count": over_budget_count,
            "total_allocated": round(total_allocated, 2),
            "total_actual": round(total_actual, 2),
            "total_remaining": round(total_allocated - total_actual, 2),
            "rows": rows,
        }

    # -------------------------------------------------------------
    # Comprehensive School Financial Summary
    # -------------------------------------------------------------
    @staticmethod
    def get_comprehensive_financial_summary(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        academic_year_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        acc_summary = AccountingRepository.get_financial_summary(db, start_date=start_date, end_date=end_date)
        inc_breakdown = AccountingRepository.get_category_breakdown(db, trans_type="Income", start_date=start_date, end_date=end_date)
        exp_breakdown = AccountingRepository.get_category_breakdown(db, trans_type="Expense", start_date=start_date, end_date=end_date)

        # Fee receivables & adjustments snapshot
        fee_q = db.query(
            func.coalesce(func.sum(StudentFee.total_amount), 0.0),
            func.coalesce(func.sum(StudentFee.discount_amount), 0.0),
            func.coalesce(func.sum(StudentFee.scholarship_amount), 0.0),
            func.coalesce(func.sum(StudentFee.waiver_amount), 0.0),
            func.coalesce(func.sum(StudentFee.net_amount), 0.0),
            func.coalesce(func.sum(StudentFee.paid_amount), 0.0),
            func.coalesce(func.sum(StudentFee.refunded_amount), 0.0),
            func.coalesce(func.sum(StudentFee.due_amount), 0.0),
        ).filter(StudentFee.is_deleted == False, StudentFee.status != "Cancelled")
        if academic_year_id:
            fee_q = fee_q.filter(StudentFee.academic_year_id == academic_year_id)

        tot_gross, tot_disc, tot_schol, tot_waiv, tot_net, tot_paid, tot_ref, tot_due = fee_q.first()
        advance_balance = float(
            db.query(func.coalesce(func.sum(StudentAdvanceCredit.signed_amount), 0.0)).scalar() or 0.0
        )

        ref_year = end_date.year if end_date else date.today().year
        budget_report = AccountingService.get_budget_variance_report(
            db, fiscal_year=ref_year, academic_year_id=academic_year_id
        )

        net_fee_collected = max(0.0, float(tot_paid or 0.0) - float(tot_ref or 0.0))
        net_billed = float(tot_net or 0.0)
        collection_rate = round((net_fee_collected / net_billed * 100.0), 1) if net_billed > 0 else 0.0

        return {
            **acc_summary,
            "income_breakdown": inc_breakdown,
            "expense_breakdown": exp_breakdown,
            "fee_receivables": {
                "gross_billed": float(tot_gross or 0.0),
                "total_concessions": float(tot_disc or 0.0),
                "scholarships": float(tot_schol or 0.0),
                "waivers": float(tot_waiv or 0.0),
                "net_billed": net_billed,
                "gross_collected": float(tot_paid or 0.0),
                "refunded": float(tot_ref or 0.0),
                "net_collected": net_fee_collected,
                "outstanding_due": float(tot_due or 0.0),
                "collection_rate_pct": collection_rate,
                "advance_wallet_liability": max(0.0, round(advance_balance, 2)),
            },
            "budget_summary": {
                "fiscal_year": budget_report["fiscal_year"],
                "budget_count": budget_report["budget_count"],
                "over_budget_count": budget_report["over_budget_count"],
                "total_allocated": budget_report["total_allocated"],
                "total_actual": budget_report["total_actual"],
                "total_remaining": budget_report["total_remaining"],
            },
            "monthly_trend": AccountingRepository.get_monthly_trend(db, ref_year),
        }

    # -------------------------------------------------------------
    # Excel Exports
    # -------------------------------------------------------------
    @staticmethod
    def export_cash_book_excel(
        db: Session,
        output_file_path: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        school_info: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Exports formatted Cash Book & Running Balance Ledger to Excel (.xlsx).
        """
        try:
            import openpyxl
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Cash_Book_Ledger"
            ws.views.sheetView[0].showGridLines = True

            school_name = school_info.get("name", "EduManage Pro Model High School") if school_info else "EduManage Pro High School"
            eiin = school_info.get("eiin", "134211") if school_info else "134211"

            ws.merge_cells("A1:K1")
            ws["A1"] = school_name.upper()
            ws["A1"].font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
            ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

            ws.merge_cells("A2:K2")
            date_range_str = f"Period: {start_date} to {end_date}" if start_date and end_date else "Complete Financial History"
            ws["A2"] = f"OFFICIAL CASH BOOK & GENERAL LEDGER | EIIN: {eiin} | {date_range_str}"
            ws["A2"].font = Font(name="Calibri", size=11, bold=True, color="475569")
            ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

            headers = [
                "SL", "Date", "Voucher No", "Account Head", "Particulars / Payee",
                "Channel", "Reference", "Status", "Credit (Income)", "Debit (Expense)", "Running Balance"
            ]
            header_row = 4
            header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            thin_border = Border(
                left=Side(style="thin", color="CBD5E1"),
                right=Side(style="thin", color="CBD5E1"),
                top=Side(style="thin", color="CBD5E1"),
                bottom=Side(style="thin", color="CBD5E1"),
            )

            for col_idx, h in enumerate(headers, 1):
                cell = ws.cell(row=header_row, column=col_idx, value=h)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border

            ledger = AccountingService.get_general_ledger(db, start_date=start_date, end_date=end_date)
            entries = ledger["entries"]

            current_row = 5
            for idx, entry in enumerate(entries, 1):
                ws.cell(row=current_row, column=1, value=idx).alignment = Alignment(horizontal="center")
                ws.cell(row=current_row, column=2, value=str(entry["date"])).alignment = Alignment(horizontal="center")
                ws.cell(row=current_row, column=3, value=entry["voucher_no"]).alignment = Alignment(horizontal="center")
                ws.cell(row=current_row, column=4, value=entry["category_name"])
                ws.cell(row=current_row, column=5, value=entry["party"])
                ch_label = entry["payment_method"]
                if entry["channel_detail"] and entry["channel_detail"] != "-":
                    ch_label = f"{ch_label} ({entry['channel_detail']})"
                ws.cell(row=current_row, column=6, value=ch_label).alignment = Alignment(horizontal="center")
                ws.cell(row=current_row, column=7, value=entry["reference_no"]).alignment = Alignment(horizontal="center")
                ws.cell(row=current_row, column=8, value=entry["status"]).alignment = Alignment(horizontal="center")

                inc_cell = ws.cell(row=current_row, column=9)
                exp_cell = ws.cell(row=current_row, column=10)
                bal_cell = ws.cell(row=current_row, column=11, value=entry["running_balance"])
                bal_cell.number_format = "#,##0.00"
                bal_cell.alignment = Alignment(horizontal="right")

                if entry["credit"] > 0:
                    inc_cell.value = entry["credit"]
                    inc_cell.number_format = "#,##0.00"
                    inc_cell.alignment = Alignment(horizontal="right")
                    inc_cell.font = Font(color="047857", bold=True)
                    exp_cell.value = "-"
                    exp_cell.alignment = Alignment(horizontal="center")
                else:
                    inc_cell.value = "-"
                    inc_cell.alignment = Alignment(horizontal="center")
                    exp_cell.value = entry["debit"]
                    exp_cell.number_format = "#,##0.00"
                    exp_cell.alignment = Alignment(horizontal="right")
                    exp_cell.font = Font(color="B91C1C", bold=True)

                for c in range(1, 12):
                    ws.cell(row=current_row, column=c).border = thin_border
                current_row += 1

            summary_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
            ws.merge_cells(f"A{current_row}:H{current_row}")
            summary_label = ws.cell(row=current_row, column=1, value="TOTAL LEDGER CREDITS & DEBITS:")
            summary_label.font = Font(name="Calibri", size=11, bold=True)
            summary_label.alignment = Alignment(horizontal="right")

            tot_inc = ws.cell(row=current_row, column=9, value=ledger["total_credit"])
            tot_inc.font = Font(name="Calibri", size=11, bold=True, color="047857")
            tot_inc.number_format = "#,##0.00"
            tot_inc.alignment = Alignment(horizontal="right")

            tot_exp = ws.cell(row=current_row, column=10, value=ledger["total_debit"])
            tot_exp.font = Font(name="Calibri", size=11, bold=True, color="B91C1C")
            tot_exp.number_format = "#,##0.00"
            tot_exp.alignment = Alignment(horizontal="right")

            tot_bal = ws.cell(row=current_row, column=11, value=ledger["closing_balance"])
            tot_bal.font = Font(name="Calibri", size=11, bold=True, color="1E3A8A")
            tot_bal.number_format = "#,##0.00"
            tot_bal.alignment = Alignment(horizontal="right")

            for c in range(1, 12):
                ws.cell(row=current_row, column=c).fill = summary_fill
                ws.cell(row=current_row, column=c).border = thin_border

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
