"""
EduManage Pro - Enterprise Accounting Repository
Handles database operations for Chart of Accounts, Cash Book, General Ledger,
Vouchers & Non-Destructive Reversals, Budgets, Financial Audit Trail, and P&L Summaries.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, extract, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.accounting import (
    AccountBudget,
    AccountCategory,
    AccountTransaction,
    FinancialAuditLog,
)


class AccountingRepository:
    # -------------------------------------------------------------
    # Category Management
    # -------------------------------------------------------------
    @staticmethod
    def get_all_categories(
        db: Session,
        trans_type: Optional[str] = None,
        active_only: bool = True,
    ) -> List[AccountCategory]:
        query = db.query(AccountCategory).filter(AccountCategory.is_deleted == False)
        if trans_type:
            query = query.filter(AccountCategory.type == trans_type)
        if active_only:
            query = query.filter(AccountCategory.is_active == True)
        return query.order_by(AccountCategory.type.asc(), AccountCategory.name.asc()).all()

    @staticmethod
    def get_category_by_id(db: Session, category_id: int) -> Optional[AccountCategory]:
        return db.query(AccountCategory).filter(AccountCategory.id == category_id).first()

    @staticmethod
    def get_category_by_name(db: Session, name: str) -> Optional[AccountCategory]:
        return (
            db.query(AccountCategory)
            .filter(func.lower(AccountCategory.name) == name.strip().lower())
            .first()
        )

    @staticmethod
    def get_category_by_code(db: Session, code: str) -> Optional[AccountCategory]:
        return (
            db.query(AccountCategory)
            .filter(func.lower(AccountCategory.code) == code.strip().lower())
            .first()
        )

    @staticmethod
    def create_category(db: Session, data: Dict[str, Any]) -> AccountCategory:
        category = AccountCategory(
            name=data["name"].strip(),
            code=data["code"].strip().upper(),
            type=data["type"],
            description=data.get("description"),
            is_system=data.get("is_system", False),
            is_active=data.get("is_active", True),
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    @staticmethod
    def update_category(db: Session, category_id: int, data: Dict[str, Any]) -> Optional[AccountCategory]:
        cat = db.query(AccountCategory).filter(AccountCategory.id == category_id).first()
        if not cat:
            return None
        for key, val in data.items():
            if hasattr(cat, key) and key not in ("id", "is_system"):
                setattr(cat, key, val)
        db.commit()
        db.refresh(cat)
        return cat

    @staticmethod
    def delete_category(db: Session, category_id: int) -> Tuple[bool, str]:
        cat = db.query(AccountCategory).filter(AccountCategory.id == category_id).first()
        if not cat:
            return False, "Category not found."
        if cat.is_system:
            return False, "System account categories cannot be deleted."
        tx_count = db.query(AccountTransaction).filter(AccountTransaction.category_id == category_id).count()
        if tx_count > 0:
            return False, f"Cannot delete category with {tx_count} attached financial transactions."
        db.delete(cat)
        db.commit()
        return True, "Category deleted successfully."

    # -------------------------------------------------------------
    # Transaction Management (Immutable — No Hard Deletes!)
    # -------------------------------------------------------------
    @staticmethod
    def get_transactions(
        db: Session,
        trans_type: Optional[str] = None,
        category_id: Optional[int] = None,
        payment_method: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> Tuple[List[AccountTransaction], int]:
        query = db.query(AccountTransaction).options(
            joinedload(AccountTransaction.category)
        ).filter(AccountTransaction.is_deleted == False)

        if trans_type and trans_type != "All Types":
            query = query.filter(AccountTransaction.type == trans_type)
        if category_id:
            query = query.filter(AccountTransaction.category_id == category_id)
        if payment_method and payment_method.lower() not in ("all", "all channels", "all methods"):
            query = query.filter(AccountTransaction.payment_method == payment_method)
        if status and status.lower() != "all":
            query = query.filter(AccountTransaction.status == status)
        if start_date:
            query = query.filter(AccountTransaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(AccountTransaction.transaction_date <= end_date)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    AccountTransaction.voucher_no.ilike(term),
                    AccountTransaction.paid_to_received_from.ilike(term),
                    AccountTransaction.reference_no.ilike(term),
                    AccountTransaction.description.ilike(term),
                    AccountTransaction.channel_detail.ilike(term),
                )
            )

        total_count = query.count()
        transactions = (
            query.order_by(AccountTransaction.transaction_date.desc(), AccountTransaction.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return transactions, total_count

    @staticmethod
    def get_transaction_by_id(db: Session, tx_id: int) -> Optional[AccountTransaction]:
        return (
            db.query(AccountTransaction)
            .options(joinedload(AccountTransaction.category))
            .filter(AccountTransaction.id == tx_id)
            .first()
        )

    @staticmethod
    def get_transaction_by_voucher(db: Session, voucher_no: str) -> Optional[AccountTransaction]:
        return (
            db.query(AccountTransaction)
            .options(joinedload(AccountTransaction.category))
            .filter(AccountTransaction.voucher_no == voucher_no)
            .first()
        )

    @staticmethod
    def get_transaction_count_by_year(db: Session, year: int) -> int:
        return (
            db.query(func.count(AccountTransaction.id))
            .filter(extract("year", AccountTransaction.transaction_date) == year)
            .scalar()
            or 0
        )

    @staticmethod
    def create_transaction(db: Session, data: Dict[str, Any], commit: bool = True) -> AccountTransaction:
        tx = AccountTransaction(
            voucher_no=data["voucher_no"],
            idempotency_key=data.get("idempotency_key"),
            transaction_date=data["transaction_date"],
            type=data["type"],
            entry_kind=data.get("entry_kind", "Standard"),
            category_id=data["category_id"],
            academic_year_id=data.get("academic_year_id"),
            amount=float(data["amount"]),
            payment_method=data.get("payment_method", "Cash"),
            channel_detail=data.get("channel_detail"),
            reference_no=data.get("reference_no"),
            paid_to_received_from=data["paid_to_received_from"].strip(),
            description=data.get("description"),
            recorded_by=data.get("recorded_by", "Accountant"),
            approved_by=data.get("approved_by"),
            approved_at=data.get("approved_at"),
            status=data.get("status", "Approved"),
            is_reversed=bool(data.get("is_reversed", False)),
            reversal_of_id=data.get("reversal_of_id"),
        )
        db.add(tx)
        if commit:
            db.commit()
            db.refresh(tx)
        else:
            db.flush()
        return tx

    @staticmethod
    def update_transaction(db: Session, tx_id: int, data: Dict[str, Any]) -> Optional[AccountTransaction]:
        """
        Update non-immutable descriptive fields only. Monetary amounts, types, and voucher numbers
        cannot be altered once posted (use reverse_transaction instead).
        """
        tx = db.query(AccountTransaction).filter(AccountTransaction.id == tx_id).first()
        if not tx:
            return None
        allowed = {"description", "reference_no", "approved_by", "approved_at"}
        for key, val in data.items():
            if key in allowed and hasattr(tx, key):
                setattr(tx, key, val)
        db.commit()
        db.refresh(tx)
        return tx

    @staticmethod
    def delete_transaction(db: Session, tx_id: int) -> bool:
        """
        Permanent deletion is strictly prohibited by financial audit policy.
        """
        raise ValueError(
            "Permanent deletion of financial transactions is prohibited. Use reverse_transaction() instead."
        )

    # -------------------------------------------------------------
    # Financial KPI, Channel & Category Breakdowns (Reversal-Aware)
    # -------------------------------------------------------------
    @staticmethod
    def _effective_totals_for_rows(txs: List[AccountTransaction]) -> Dict[str, Any]:
        """
        Double-entry reversal-aware aggregation:
        - Normal Income adds to total_income & net.
        - Reversal of Income (type=='Expense', entry_kind=='Reversal') subtracts from total_income.
        - Normal Expense adds to total_expense & subtracts from net.
        - Reversal of Expense (type=='Income', entry_kind=='Reversal') subtracts from total_expense.
        - Channel balances always sum raw Cash/Bank/Card/Mobile/Other inflows minus outflows.
        """
        total_income = 0.0
        total_expense = 0.0
        channel_balances: Dict[str, float] = {
            "Cash": 0.0,
            "Bank": 0.0,
            "Card": 0.0,
            "Mobile Banking": 0.0,
            "Other": 0.0,
        }

        for tx in txs:
            if tx.status not in ("Approved", "Reversed"):
                continue
            amt = float(tx.amount or 0.0)
            method = tx.payment_method or "Other"
            # Normalize legacy raw channel labels cleanly if pre-existing DB rows exist
            if method in ("Bank Transfer", "Cheque"):
                method_key = "Bank"
            elif method in ("bKash", "Nagad", "Rocket"):
                method_key = "Mobile Banking"
            elif method in ("Debit/Credit Card",):
                method_key = "Card"
            elif method in channel_balances:
                method_key = method
            else:
                method_key = "Other"

            if tx.type == "Income":
                channel_balances[method_key] += amt
                if tx.entry_kind == "Reversal":
                    total_expense -= amt
                else:
                    total_income += amt
            else:
                channel_balances[method_key] -= amt
                if tx.entry_kind == "Reversal":
                    total_income -= amt
                else:
                    total_expense += amt

        total_income = round(total_income, 2)
        total_expense = round(total_expense, 2)
        net_balance = round(total_income - total_expense, 2)
        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "net_surplus": net_balance,
            "cash_in_hand": round(channel_balances["Cash"], 2),
            "channel_balances": {k: round(v, 2) for k, v in channel_balances.items()},
            "is_profit": net_balance >= 0,
        }

    @staticmethod
    def get_financial_summary(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        query = db.query(AccountTransaction).filter(
            AccountTransaction.status.in_(("Approved", "Reversed")),
            AccountTransaction.is_deleted == False,
        )
        if start_date:
            query = query.filter(AccountTransaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(AccountTransaction.transaction_date <= end_date)
        txs = query.all()
        return AccountingRepository._effective_totals_for_rows(txs)

    @staticmethod
    def get_category_breakdown(
        db: Session,
        trans_type: str = "Expense",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        query = (
            db.query(AccountTransaction)
            .options(joinedload(AccountTransaction.category))
            .filter(
                AccountTransaction.status.in_(("Approved", "Reversed")),
                AccountTransaction.is_deleted == False,
            )
        )
        if start_date:
            query = query.filter(AccountTransaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(AccountTransaction.transaction_date <= end_date)

        txs = query.all()
        grouped: Dict[int, Dict[str, Any]] = {}
        for tx in txs:
            cat = tx.category
            if not cat or cat.type != trans_type:
                continue
            entry = grouped.setdefault(
                cat.id,
                {"category_id": cat.id, "category": cat.name, "code": cat.code, "amount": 0.0, "count": 0},
            )
            amt = float(tx.amount or 0.0)
            if tx.entry_kind == "Reversal":
                entry["amount"] -= amt
            else:
                entry["amount"] += amt
                entry["count"] += 1

        result = [
            {
                "category_id": v["category_id"],
                "category": v["category"],
                "code": v["code"],
                "amount": round(v["amount"], 2),
                "count": v["count"],
            }
            for v in grouped.values()
            if abs(v["amount"]) > 0.001 or v["count"] > 0
        ]
        result.sort(key=lambda r: r["amount"], reverse=True)
        return result

    @staticmethod
    def get_monthly_trend(db: Session, year: int) -> List[Dict[str, Any]]:
        txs = (
            db.query(AccountTransaction)
            .filter(
                AccountTransaction.status.in_(("Approved", "Reversed")),
                AccountTransaction.is_deleted == False,
                extract("year", AccountTransaction.transaction_date) == year,
            )
            .all()
        )
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        buckets: Dict[int, List[AccountTransaction]] = {m: [] for m in range(1, 13)}
        for tx in txs:
            if tx.transaction_date:
                buckets[tx.transaction_date.month].append(tx)

        trend = []
        for m in range(1, 13):
            stats = AccountingRepository._effective_totals_for_rows(buckets[m])
            trend.append(
                {
                    "month": month_names[m - 1],
                    "month_num": m,
                    "income": stats["total_income"],
                    "expense": stats["total_expense"],
                    "net": stats["net_surplus"],
                }
            )
        return trend

    # -------------------------------------------------------------
    # Budgets & Audit Trail Queries
    # -------------------------------------------------------------
    @staticmethod
    def get_budgets(
        db: Session,
        fiscal_year: Optional[int] = None,
        academic_year_id: Optional[int] = None,
    ) -> List[AccountBudget]:
        query = (
            db.query(AccountBudget)
            .options(joinedload(AccountBudget.category), joinedload(AccountBudget.academic_year))
            .filter(AccountBudget.is_deleted == False)
        )
        if fiscal_year:
            query = query.filter(AccountBudget.fiscal_year == fiscal_year)
        if academic_year_id:
            query = query.filter(AccountBudget.academic_year_id == academic_year_id)
        return query.order_by(AccountBudget.fiscal_year.desc(), AccountBudget.id.desc()).all()

    @staticmethod
    def get_audit_logs(
        db: Session,
        module: Optional[str] = None,
        action: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 200,
    ) -> List[FinancialAuditLog]:
        query = db.query(FinancialAuditLog)
        if module and module.upper() != "ALL":
            query = query.filter(FinancialAuditLog.module == module.upper())
        if action and action.upper() != "ALL":
            query = query.filter(FinancialAuditLog.action == action.upper())
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    FinancialAuditLog.reference_no.ilike(term),
                    FinancialAuditLog.action.ilike(term),
                    FinancialAuditLog.reason.ilike(term),
                    FinancialAuditLog.actor_username.ilike(term),
                )
            )
        return query.order_by(FinancialAuditLog.created_at.desc(), FinancialAuditLog.id.desc()).limit(limit).all()
