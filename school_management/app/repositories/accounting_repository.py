"""
EduManage Pro - Accounting Repository
Handles database operations for Chart of Accounts, daily cash book, and financial vouchers.
"""

from typing import List, Optional, Tuple, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_, extract
from app.models.accounting import AccountCategory, AccountTransaction


class AccountingRepository:
    # -------------------------------------------------------------
    # Category Management
    # -------------------------------------------------------------
    @staticmethod
    def get_all_categories(
        db: Session,
        trans_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[AccountCategory]:
        query = db.query(AccountCategory)
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
        return db.query(AccountCategory).filter(func.lower(AccountCategory.name) == name.strip().lower()).first()

    @staticmethod
    def get_category_by_code(db: Session, code: str) -> Optional[AccountCategory]:
        return db.query(AccountCategory).filter(func.lower(AccountCategory.code) == code.strip().lower()).first()

    @staticmethod
    def create_category(db: Session, data: Dict[str, Any]) -> AccountCategory:
        category = AccountCategory(
            name=data["name"].strip(),
            code=data["code"].strip().upper(),
            type=data["type"],
            description=data.get("description"),
            is_system=data.get("is_system", False),
            is_active=data.get("is_active", True)
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
        # Check if transactions exist
        tx_count = db.query(AccountTransaction).filter(AccountTransaction.category_id == category_id).count()
        if tx_count > 0:
            return False, f"Cannot delete category with {tx_count} attached financial transactions."
        db.delete(cat)
        db.commit()
        return True, "Category deleted successfully."

    # -------------------------------------------------------------
    # Transaction Management
    # -------------------------------------------------------------
    @staticmethod
    def get_transactions(
        db: Session,
        trans_type: Optional[str] = None,
        category_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[AccountTransaction], int]:
        query = db.query(AccountTransaction).options(joinedload(AccountTransaction.category))

        if trans_type:
            query = query.filter(AccountTransaction.type == trans_type)
        if category_id:
            query = query.filter(AccountTransaction.category_id == category_id)
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
                    AccountTransaction.description.ilike(term)
                )
            )

        total_count = query.count()
        transactions = query.order_by(
            AccountTransaction.transaction_date.desc(),
            AccountTransaction.id.desc()
        ).offset(offset).limit(limit).all()

        return transactions, total_count

    @staticmethod
    def get_transaction_by_id(db: Session, tx_id: int) -> Optional[AccountTransaction]:
        return db.query(AccountTransaction).options(joinedload(AccountTransaction.category)).filter(AccountTransaction.id == tx_id).first()

    @staticmethod
    def get_transaction_by_voucher(db: Session, voucher_no: str) -> Optional[AccountTransaction]:
        return db.query(AccountTransaction).options(joinedload(AccountTransaction.category)).filter(AccountTransaction.voucher_no == voucher_no).first()

    @staticmethod
    def get_transaction_count_by_year(db: Session, year: int) -> int:
        return db.query(func.count(AccountTransaction.id)).filter(
            extract("year", AccountTransaction.transaction_date) == year
        ).scalar() or 0

    @staticmethod
    def create_transaction(db: Session, data: Dict[str, Any]) -> AccountTransaction:
        tx = AccountTransaction(
            voucher_no=data["voucher_no"],
            transaction_date=data["transaction_date"],
            type=data["type"],
            category_id=data["category_id"],
            amount=float(data["amount"]),
            payment_method=data.get("payment_method", "Cash"),
            reference_no=data.get("reference_no"),
            paid_to_received_from=data["paid_to_received_from"].strip(),
            description=data.get("description"),
            recorded_by=data.get("recorded_by", "Accountant"),
            status=data.get("status", "Approved")
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    @staticmethod
    def update_transaction(db: Session, tx_id: int, data: Dict[str, Any]) -> Optional[AccountTransaction]:
        tx = db.query(AccountTransaction).filter(AccountTransaction.id == tx_id).first()
        if not tx:
            return None
        for key, val in data.items():
            if hasattr(tx, key) and key not in ("id", "voucher_no"):
                setattr(tx, key, val)
        db.commit()
        db.refresh(tx)
        return tx

    @staticmethod
    def delete_transaction(db: Session, tx_id: int) -> bool:
        tx = db.query(AccountTransaction).filter(AccountTransaction.id == tx_id).first()
        if not tx:
            return False
        db.delete(tx)
        db.commit()
        return True

    # -------------------------------------------------------------
    # Financial KPI & Aggregation Queries
    # -------------------------------------------------------------
    @staticmethod
    def get_financial_summary(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, float]:
        query = db.query(
            AccountTransaction.type,
            func.coalesce(func.sum(AccountTransaction.amount), 0.0)
        ).filter(AccountTransaction.status == "Approved")

        if start_date:
            query = query.filter(AccountTransaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(AccountTransaction.transaction_date <= end_date)

        results = dict(query.group_by(AccountTransaction.type).all())
        total_income = float(results.get("Income", 0.0))
        total_expense = float(results.get("Expense", 0.0))
        net_balance = total_income - total_expense

        # Payment method breakdown
        cash_in = db.query(func.coalesce(func.sum(AccountTransaction.amount), 0.0)).filter(
            AccountTransaction.type == "Income",
            AccountTransaction.payment_method == "Cash",
            AccountTransaction.status == "Approved"
        ).scalar() or 0.0
        cash_out = db.query(func.coalesce(func.sum(AccountTransaction.amount), 0.0)).filter(
            AccountTransaction.type == "Expense",
            AccountTransaction.payment_method == "Cash",
            AccountTransaction.status == "Approved"
        ).scalar() or 0.0
        cash_in_hand = float(cash_in - cash_out)

        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "net_surplus": net_balance,
            "cash_in_hand": cash_in_hand,
            "is_profit": net_balance >= 0
        }

    @staticmethod
    def get_category_breakdown(
        db: Session,
        trans_type: str = "Expense",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        query = db.query(
            AccountCategory.name,
            AccountCategory.code,
            func.coalesce(func.sum(AccountTransaction.amount), 0.0).label("total_amount"),
            func.count(AccountTransaction.id).label("tx_count")
        ).join(AccountTransaction, AccountCategory.id == AccountTransaction.category_id)\
         .filter(AccountTransaction.type == trans_type, AccountTransaction.status == "Approved")

        if start_date:
            query = query.filter(AccountTransaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(AccountTransaction.transaction_date <= end_date)

        rows = query.group_by(AccountCategory.id).order_by(func.sum(AccountTransaction.amount).desc()).all()
        return [
            {
                "category": r[0],
                "code": r[1],
                "amount": float(r[2]),
                "count": int(r[3])
            }
            for r in rows
        ]

    @staticmethod
    def get_monthly_trend(db: Session, year: int) -> List[Dict[str, Any]]:
        trend = []
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for m in range(1, 13):
            inc = db.query(func.coalesce(func.sum(AccountTransaction.amount), 0.0)).filter(
                AccountTransaction.type == "Income",
                AccountTransaction.status == "Approved",
                extract("year", AccountTransaction.transaction_date) == year,
                extract("month", AccountTransaction.transaction_date) == m
            ).scalar() or 0.0

            exp = db.query(func.coalesce(func.sum(AccountTransaction.amount), 0.0)).filter(
                AccountTransaction.type == "Expense",
                AccountTransaction.status == "Approved",
                extract("year", AccountTransaction.transaction_date) == year,
                extract("month", AccountTransaction.transaction_date) == m
            ).scalar() or 0.0

            trend.append({
                "month": month_names[m - 1],
                "month_num": m,
                "income": float(inc),
                "expense": float(exp),
                "net": float(inc - exp)
            })
        return trend
