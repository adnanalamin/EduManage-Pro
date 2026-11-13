"""
EduManage Pro - Fees Service Layer
Business logic for payment processing, unique receipt number generation, discounts, and audit logging.
"""

from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session
from app.repositories.fee_repository import FeeRepository
from app.models.fee import FeeCategory, FeePayment, StudentFee, FeeStructure
from app.models.activity import ActivityLog
from app.services.database_service import DatabaseService
from app.config.logging_config import app_logger


class FeeService:
    @staticmethod
    def generate_receipt_no(db: Session) -> str:
        count = db.query(FeePayment).count()
        year = datetime.now().year
        return f"REC-{year}-{count + 1:05d}"

    @staticmethod
    def collect_fee_payment(
        db: Session,
        student_fee_id: int,
        amount: float,
        payment_method: str = "Cash",
        transaction_id: Optional[str] = None,
        remarks: Optional[str] = None,
        current_user: str = "admin",
        idempotency_key: Optional[str] = None,
    ) -> Tuple[Optional[FeePayment], str]:
        if idempotency_key:
            existing = (
                db.query(FeePayment)
                .filter(FeePayment.idempotency_key == idempotency_key)
                .first()
            )
            if existing:
                return existing, "Payment already recorded (idempotent replay)."

        fee = FeeRepository.get_student_fee_by_id(db, student_fee_id)
        if not fee or getattr(fee, "is_deleted", False):
            return None, "Fee invoice not found."

        if amount <= 0:
            return None, "Payment amount must be greater than zero."
        if amount > fee.due_amount + 0.01:
            return None, f"Payment (৳{amount:,.2f}) exceeds current due (৳{fee.due_amount:,.2f})."

        receipt_no = FeeService.generate_receipt_no(db)

        payment_data = {
            "receipt_no": receipt_no,
            "idempotency_key": idempotency_key,
            "student_fee_id": student_fee_id,
            "student_id": fee.student_id,
            "amount_paid": amount,
            "payment_method": payment_method,
            "transaction_id": transaction_id,
            "payment_date": date.today(),
            "collected_by": current_user,
            "remarks": remarks
        }

        try:
            payment, updated_fee = FeeRepository.record_payment(db, payment_data)

            # Audit log
            log = ActivityLog(
                user_id=DatabaseService.resolve_user_id(db, current_user),
                username=current_user,
                action="FEE_COLLECTION",
                module="FEES",
                description=f"Collected ৳{amount:,.2f} ({payment_method}) from {fee.student.full_name} [{fee.student.student_id}] (Receipt: {receipt_no})",
                severity="INFO"
            )
            db.add(log)
            db.commit()

            app_logger.info(f"Payment of ৳{amount} recorded for {fee.student.student_id} by {current_user}")
            return payment, "Payment recorded successfully."
        except Exception as exc:
            db.rollback()
            return None, str(exc)

    @staticmethod
    def apply_discount(
        db: Session,
        student_fee_id: int,
        discount_amount: float,
        reason: str,
        current_user: str = "admin"
    ) -> Tuple[Optional[StudentFee], str]:
        fee = db.query(StudentFee).filter(StudentFee.id == student_fee_id).first()
        if not fee:
            return None, "Fee record not found."

        if discount_amount < 0 or discount_amount > fee.total_amount:
            return None, "Invalid discount amount."

        fee.discount_amount = discount_amount
        fee.discount_reason = reason
        fee.net_amount = max(0.0, fee.total_amount - discount_amount)
        fee.due_amount = max(0.0, fee.net_amount - fee.paid_amount)
        fee.status = "Paid" if fee.due_amount <= 0.01 else "Partial" if fee.paid_amount > 0 else "Unpaid"

        log = ActivityLog(
            user_id=DatabaseService.resolve_user_id(db, current_user),
            username=current_user,
            action="FEE_DISCOUNT_APPLIED",
            module="FEES",
            description=f"Applied discount of ৳{discount_amount:,.2f} ({reason}) to {fee.student.full_name} [{fee.student.student_id}]",
            severity="INFO"
        )
        db.add(log)
        db.commit()
        db.refresh(fee)
        return fee, "Discount applied successfully."

    @staticmethod
    def seed_default_fee_categories(db: Session):
        standard_categories = [
            ("Tuition Fee", "TUI", "Monthly academic tuition fee"),
            ("Admission Fee", "ADM", "One-time session admission and registration charge"),
            ("Examination Fee", "EXM", "Term and semester examination fee"),
            ("Library Fee", "LIB", "Annual library maintenance and book circulation fee"),
            ("Transport Fee", "TRN", "Monthly school bus transportation charge"),
            ("Hostel Fee", "HST", "Residential hall and boarding fee"),
            ("Development Fee", "DEV", "Infrastructure and laboratory development fund"),
            ("Other Fee", "OTH", "Miscellaneous school extracurricular charge"),
        ]
        for name, code, desc in standard_categories:
            existing = db.query(FeeCategory).filter(FeeCategory.code == code).first()
            if not existing:
                cat = FeeCategory(name=name, code=code, description=desc, is_active=True)
                db.add(cat)
        db.commit()
