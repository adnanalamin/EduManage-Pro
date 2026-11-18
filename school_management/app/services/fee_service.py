"""
EduManage Pro - Enterprise Fees Service Layer
Business logic for Fee Categories, Fee Structures, Monthly Batch Billing,
Custom Invoices, Adjustments (Discount / Scholarship / Waiver), Partial & Full Payments,
Student Advance Credit Wallets, Refunds, Non-Destructive Invoice Cancellation,
Due & Collection Reports, Excel Exports, and Automatic Accounting Synchronization.
"""

from datetime import date, datetime
import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.logging_config import app_logger
from app.models.academic import AcademicYear, SchoolClass
from app.models.accounting import AccountCategory, AccountTransaction
from app.models.base import utc_now
from app.models.fee import (
    FeeAdjustment,
    FeeCategory,
    FeePayment,
    FeeRefund,
    FeeStructure,
    StudentAdvanceCredit,
    StudentFee,
    normalize_payment_channel,
)
from app.models.student import Student
from app.repositories.accounting_repository import AccountingRepository
from app.repositories.fee_repository import FeeRepository
from app.services.accounting_service import AccountingService
from app.services.database_service import DatabaseService


MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


class FeeService:
    # ==================== NUMBER GENERATORS ====================
    @staticmethod
    def generate_receipt_no(db: Session) -> str:
        year = datetime.now().year
        count = db.query(func.count(FeePayment.id)).scalar() or 0
        seq = count + 1
        while True:
            candidate = f"REC-{year}-{seq:05d}"
            if not db.query(FeePayment.id).filter(FeePayment.receipt_no == candidate).first():
                return candidate
            seq += 1

    @staticmethod
    def generate_refund_no(db: Session) -> str:
        year = datetime.now().year
        count = db.query(func.count(FeeRefund.id)).scalar() or 0
        seq = count + 1
        while True:
            candidate = f"RFD-{year}-{seq:05d}"
            if not db.query(FeeRefund.id).filter(FeeRefund.refund_no == candidate).first():
                return candidate
            seq += 1

    @staticmethod
    def generate_advance_receipt_no(db: Session) -> str:
        year = datetime.now().year
        count = db.query(func.count(StudentAdvanceCredit.id)).scalar() or 0
        seq = count + 1
        while True:
            candidate = f"ADV-{year}-{seq:05d}"
            if not db.query(StudentAdvanceCredit.id).filter(StudentAdvanceCredit.receipt_no == candidate).first():
                return candidate
            seq += 1

    # ==================== CATEGORIES & STRUCTURES ====================
    @staticmethod
    def seed_default_fee_categories(db: Session) -> int:
        standard_categories = [
            ("Tuition Fee", "TUI", "Monthly academic tuition fee", True),
            ("Admission Fee", "ADM", "One-time session admission and registration charge", False),
            ("Examination Fee", "EXM", "Term and semester examination fee", False),
            ("Library Fee", "LIB", "Annual library maintenance and book circulation fee", False),
            ("Transport Fee", "TRN", "Monthly school bus transportation charge", True),
            ("Hostel Fee", "HST", "Residential hall and boarding fee", True),
            ("Development Fee", "DEV", "Infrastructure and laboratory development fund", False),
            ("Other Fee", "OTH", "Miscellaneous school extracurricular charge", False),
        ]
        created = 0
        for name, code, desc, recurring in standard_categories:
            existing = db.query(FeeCategory).filter(FeeCategory.code == code).first()
            if not existing:
                cat = FeeCategory(
                    name=name,
                    code=code,
                    description=desc,
                    is_recurring=recurring,
                    is_active=True,
                )
                db.add(cat)
                created += 1
        if created:
            db.commit()
        return created

    @staticmethod
    def seed_default_categories(db: Session) -> int:
        return FeeService.seed_default_fee_categories(db)

    @staticmethod
    def create_fee_structure(db: Session, data: Dict[str, Any]) -> Tuple[Optional[FeeStructure], Optional[str]]:
        try:
            amt = float(data.get("amount", 0.0))
            if amt < 0:
                return None, "Fee amount cannot be negative."
            if not data.get("title"):
                return None, "Fee structure title is required."
            struct = FeeRepository.create_fee_structure(db, data)
            return struct, None
        except Exception as exc:
            db.rollback()
            return None, str(exc)

    # ==================== MONTHLY BILLING & CUSTOM INVOICES ====================
    @staticmethod
    def generate_monthly_fees(
        db: Session,
        category_id: int,
        class_id: int,
        academic_year_id: int,
        month: int,
        year: int,
        amount: float,
        due_date: Optional[date] = None,
        title: Optional[str] = None,
        current_user: str = "admin",
    ) -> Tuple[Optional[FeeStructure], int, str]:
        """
        Generates monthly recurring fee invoices (Monthly Tuition / Transport / Hostel)
        for all active students in a class, preventing duplicate billing for the same month.
        """
        if month < 1 or month > 12:
            return None, 0, "Month must be between 1 and 12."
        if amount <= 0:
            return None, 0, "Monthly fee amount must be greater than zero."

        cat = db.query(FeeCategory).filter(FeeCategory.id == category_id, FeeCategory.is_deleted == False).first()
        cls_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        if not cat or not cls_obj:
            return None, 0, "Valid Fee Category and School Class are required."

        month_label = MONTH_NAMES[month - 1]
        struct_title = title or f"{cls_obj.name} {cat.name} — {month_label} {year}"
        effective_due = due_date or date(year, month, 10)

        struct = (
            db.query(FeeStructure)
            .filter(
                FeeStructure.category_id == category_id,
                FeeStructure.class_id == class_id,
                FeeStructure.academic_year_id == academic_year_id,
                FeeStructure.billing_month == month,
                FeeStructure.billing_year == year,
                FeeStructure.is_deleted == False,
            )
            .first()
        )
        if not struct:
            struct = FeeStructure(
                title=struct_title,
                category_id=category_id,
                class_id=class_id,
                academic_year_id=academic_year_id,
                amount=amount,
                due_date=effective_due,
                frequency="Monthly",
                billing_month=month,
                billing_year=year,
                description=f"Monthly billing cycle {month_label} {year}",
            )
            db.add(struct)
            db.flush()

        assigned_count = FeeRepository.batch_assign_fee_structure(
            db, fee_structure_id=struct.id, class_id=class_id, academic_year_id=academic_year_id
        )
        AccountingService.record_audit_log(
            db,
            module="FEES",
            entity_type="FeeStructure",
            entity_id=struct.id,
            reference_no=f"MTH-{year}-{month:02d}",
            action="FEE_MONTHLY_BATCH",
            amount=amount * assigned_count,
            after_snapshot={
                "title": struct.title,
                "class": cls_obj.name,
                "month": month_label,
                "year": year,
                "invoices_created": assigned_count,
            },
            actor_username=current_user,
            commit=True,
        )
        return struct, assigned_count, f"Generated {assigned_count} invoice(s) for {struct.title}."

    @staticmethod
    def create_student_invoice(
        db: Session,
        student_id: int,
        category_id: int,
        amount: float,
        due_date: Optional[date] = None,
        academic_year_id: Optional[int] = None,
        title: Optional[str] = None,
        current_user: str = "admin",
    ) -> Tuple[Optional[StudentFee], str]:
        """
        Creates an individual ad-hoc student invoice (e.g. Admission Fee, Library Fine,
        Hostel, Transport, Exam, or Other charge).
        """
        if amount <= 0:
            return None, "Invoice amount must be greater than zero."

        stu = db.query(Student).filter(Student.id == student_id, Student.is_deleted == False).first()
        if not stu:
            return None, "Student not found."

        cat = db.query(FeeCategory).filter(FeeCategory.id == category_id).first()
        if not cat:
            return None, "Fee category not found."

        ay_id = academic_year_id or stu.academic_year_id
        if not ay_id:
            ay = db.query(AcademicYear).filter(AcademicYear.is_current == True).first() or db.query(AcademicYear).first()
            ay_id = ay.id if ay else None
        if not ay_id:
            return None, "Academic year could not be resolved."

        eff_due = due_date or date.today()
        inv_title = (title or f"{cat.name} — {stu.full_name}").strip()

        struct = FeeStructure(
            title=inv_title,
            category_id=category_id,
            class_id=stu.class_id,
            academic_year_id=ay_id,
            amount=amount,
            due_date=eff_due,
            frequency="One-Time",
            description=f"Individual invoice for {stu.student_id}",
        )
        db.add(struct)
        db.flush()

        inv_no = FeeRepository.generate_invoice_no(db, eff_due)
        inv = StudentFee(
            invoice_no=inv_no,
            student_id=stu.id,
            fee_structure_id=struct.id,
            academic_year_id=ay_id,
            title=inv_title,
            total_amount=amount,
            discount_amount=0.0,
            scholarship_amount=0.0,
            waiver_amount=0.0,
            net_amount=amount,
            paid_amount=0.0,
            refunded_amount=0.0,
            advance_applied_amount=0.0,
            due_amount=amount,
            status="Unpaid",
            due_date=eff_due,
        )
        db.add(inv)
        db.flush()

        AccountingService.record_audit_log(
            db,
            module="FEES",
            entity_type="StudentFee",
            entity_id=inv.id,
            reference_no=inv_no,
            action="FEE_INVOICE_CREATED",
            amount=amount,
            after_snapshot={"invoice_no": inv_no, "student_id": stu.student_id, "title": inv_title, "amount": amount},
            actor_username=current_user,
            commit=False,
        )
        DatabaseService.log_activity(
            db,
            action="FEE_INVOICE_CREATED",
            module="FEES",
            description=f"Issued invoice {inv_no} (৳{amount:,.2f}) to {stu.full_name} [{stu.student_id}]",
            username=current_user,
            entity_type="StudentFee",
            entity_id=str(inv.id),
            commit=False,
        )
        db.commit()
        db.refresh(inv)
        return inv, f"Invoice {inv_no} created successfully."

    # ==================== ADJUSTMENTS: DISCOUNT, SCHOLARSHIP, WAIVER ====================
    @staticmethod
    def apply_adjustment(
        db: Session,
        student_fee_id: int,
        adjustment_type: str,
        amount: float,
        reason: str,
        approved_by: Optional[str] = None,
        current_user: str = "admin",
    ) -> Tuple[Optional[StudentFee], str]:
        """
        Applies an additive Discount, Scholarship, or Waiver onto an invoice with full audit history.
        """
        adj_type = (adjustment_type or "").strip().capitalize()
        if adj_type not in ("Discount", "Scholarship", "Waiver"):
            return None, "Adjustment type must be 'Discount', 'Scholarship', or 'Waiver'."
        if amount <= 0:
            return None, "Adjustment amount must be greater than zero."
        if not reason or not reason.strip():
            return None, "Reason is required for applying a discount, scholarship, or waiver."

        fee = DatabaseService.lock_for_update(
            db.query(StudentFee).filter(StudentFee.id == student_fee_id, StudentFee.is_deleted == False),
            db,
        ).first()
        if not fee:
            return None, "Fee invoice not found."
        if fee.status == "Cancelled":
            return None, "Cannot apply adjustments to a cancelled invoice."

        new_total_concession = round(float(fee.discount_amount or 0.0) + float(amount), 2)
        if new_total_concession > float(fee.total_amount):
            return None, f"Total concessions (৳{new_total_concession:,.2f}) cannot exceed invoice total (৳{float(fee.total_amount):,.2f})."

        effective_paid = max(0.0, float(fee.paid_amount or 0.0) - float(fee.refunded_amount or 0.0))
        new_net = round(max(0.0, float(fee.total_amount) - new_total_concession), 2)
        if new_net + 0.01 < effective_paid:
            return None, (
                f"Net invoice amount (৳{new_net:,.2f}) would fall below already collected net payment "
                f"(৳{effective_paid:,.2f}). Process a refund first."
            )

        before_snap = {
            "discount_amount": float(fee.discount_amount or 0.0),
            "scholarship_amount": float(fee.scholarship_amount or 0.0),
            "waiver_amount": float(fee.waiver_amount or 0.0),
            "net_amount": float(fee.net_amount),
            "due_amount": float(fee.due_amount),
        }

        fee.discount_amount = new_total_concession
        if adj_type == "Scholarship":
            fee.scholarship_amount = round(float(fee.scholarship_amount or 0.0) + float(amount), 2)
        elif adj_type == "Waiver":
            fee.waiver_amount = round(float(fee.waiver_amount or 0.0) + float(amount), 2)
        fee.discount_type = adj_type
        fee.discount_reason = reason.strip()
        fee.net_amount = new_net
        fee.due_amount = round(max(0.0, new_net - effective_paid), 2)
        fee.status = "Paid" if fee.due_amount <= 0.01 else ("Partial" if effective_paid > 0.01 else "Unpaid")

        adj = FeeAdjustment(
            student_fee_id=fee.id,
            student_id=fee.student_id,
            adjustment_type=adj_type,
            amount=float(amount),
            reason=reason.strip(),
            approved_by=approved_by or current_user,
            applied_by=current_user,
        )
        db.add(adj)
        db.flush()

        AccountingService.record_audit_log(
            db,
            module="FEES",
            entity_type="FeeAdjustment",
            entity_id=adj.id,
            reference_no=fee.invoice_number,
            action=f"FEE_{adj_type.upper()}_APPLIED",
            amount=float(amount),
            before_snapshot=before_snap,
            after_snapshot={
                "discount_amount": float(fee.discount_amount),
                "net_amount": float(fee.net_amount),
                "due_amount": float(fee.due_amount),
                "status": fee.status,
            },
            reason=reason.strip(),
            actor_username=current_user,
            commit=False,
        )
        DatabaseService.log_activity(
            db,
            action=f"FEE_{adj_type.upper()}_APPLIED",
            module="FEES",
            description=f"Applied {adj_type} of ৳{amount:,.2f} ({reason.strip()}) on invoice {fee.invoice_number}",
            username=current_user,
            entity_type="StudentFee",
            entity_id=str(fee.id),
            commit=False,
        )
        db.commit()
        db.refresh(fee)
        return fee, f"{adj_type} of ৳{amount:,.2f} applied successfully."

    @staticmethod
    def apply_discount(
        db: Session,
        student_fee_id: int,
        discount_amount: float,
        reason: str,
        current_user: str = "admin",
    ) -> Tuple[Optional[StudentFee], str]:
        fee = db.query(StudentFee).filter(StudentFee.id == student_fee_id).first()
        if not fee:
            return None, "Fee record not found."
        if discount_amount < 0 or discount_amount > float(fee.total_amount):
            return None, "Invalid discount amount."

        effective_paid = max(0.0, float(fee.paid_amount or 0.0) - float(fee.refunded_amount or 0.0))
        fee.discount_amount = float(discount_amount)
        fee.discount_type = "Discount"
        fee.discount_reason = reason
        fee.net_amount = round(max(0.0, float(fee.total_amount) - float(discount_amount)), 2)
        fee.due_amount = round(max(0.0, fee.net_amount - effective_paid), 2)
        fee.status = "Paid" if fee.due_amount <= 0.01 else ("Partial" if effective_paid > 0 else "Unpaid")

        if discount_amount > 0:
            db.add(
                FeeAdjustment(
                    student_fee_id=fee.id,
                    student_id=fee.student_id,
                    adjustment_type="Discount",
                    amount=float(discount_amount),
                    reason=reason or "Fee discount",
                    approved_by=current_user,
                    applied_by=current_user,
                )
            )

        AccountingService.record_audit_log(
            db,
            module="FEES",
            entity_type="StudentFee",
            entity_id=fee.id,
            reference_no=fee.invoice_number,
            action="FEE_DISCOUNT_APPLIED",
            amount=float(discount_amount),
            after_snapshot={"discount_amount": float(discount_amount), "net_amount": fee.net_amount, "due_amount": fee.due_amount},
            reason=reason,
            actor_username=current_user,
            commit=False,
        )
        DatabaseService.log_activity(
            db,
            action="FEE_DISCOUNT_APPLIED",
            module="FEES",
            description=f"Applied discount of ৳{discount_amount:,.2f} ({reason}) to {fee.student.full_name} [{fee.student.student_id}]",
            username=current_user,
            entity_type="StudentFee",
            entity_id=str(fee.id),
            commit=False,
        )
        db.commit()
        db.refresh(fee)
        return fee, "Discount applied successfully."

    # ==================== PAYMENT COLLECTION & ACCOUNTING SYNC ====================
    @staticmethod
    def _ensure_income_category(db: Session, code: str = "INC-FEES") -> AccountCategory:
        cat = AccountingRepository.get_category_by_code(db, code)
        if not cat:
            AccountingService.seed_default_categories(db)
            cat = AccountingRepository.get_category_by_code(db, code)
        return cat

    @staticmethod
    def _ensure_expense_category(db: Session, code: str = "EXP-RFND") -> AccountCategory:
        cat = AccountingRepository.get_category_by_code(db, code)
        if not cat:
            AccountingService.seed_default_categories(db)
            cat = AccountingRepository.get_category_by_code(db, code)
        return cat

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
        channel_detail: Optional[str] = None,
        payment_date: Optional[date] = None,
        post_to_accounting: bool = True,
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
        if fee.status == "Cancelled":
            return None, "Cannot collect payment on a cancelled invoice."
        if amount <= 0:
            return None, "Payment amount must be greater than zero."
        if amount > float(fee.due_amount) + 0.01:
            return None, f"Payment (৳{amount:,.2f}) exceeds current due (৳{float(fee.due_amount):,.2f})."

        norm_method, norm_detail = normalize_payment_channel(payment_method, channel_detail)
        receipt_no = FeeService.generate_receipt_no(db)
        pay_date = payment_date or date.today()

        payment_data = {
            "receipt_no": receipt_no,
            "idempotency_key": idempotency_key,
            "student_fee_id": student_fee_id,
            "student_id": fee.student_id,
            "amount_paid": float(amount),
            "payment_method": norm_method,
            "channel_detail": norm_detail,
            "transaction_id": transaction_id,
            "payment_date": pay_date,
            "collected_by": current_user,
            "remarks": remarks,
            "status": "Completed",
            "refunded_amount": 0.0,
            "is_advance_allocation": False,
        }

        try:
            payment, updated_fee = FeeRepository.record_payment(db, payment_data, commit=False)

            if post_to_accounting:
                inc_cat = FeeService._ensure_income_category(db, "INC-FEES")
                if inc_cat:
                    tx, tx_err = AccountingService.record_transaction(
                        db,
                        {
                            "type": "Income",
                            "entry_kind": "FeeCollection",
                            "category_id": inc_cat.id,
                            "academic_year_id": fee.academic_year_id,
                            "amount": float(amount),
                            "transaction_date": pay_date,
                            "payment_method": norm_method,
                            "channel_detail": norm_detail,
                            "reference_no": receipt_no,
                            "paid_to_received_from": f"{fee.student.full_name} ({fee.student.student_id})",
                            "description": f"Fee collection for {updated_fee.display_title} [{updated_fee.invoice_number}]",
                            "idempotency_key": f"acct_{idempotency_key}" if idempotency_key else None,
                        },
                        actor_username=current_user,
                        commit=False,
                    )
                    if tx and not tx_err:
                        payment.accounting_tx_id = tx.id

            AccountingService.record_audit_log(
                db,
                module="FEES",
                entity_type="FeePayment",
                entity_id=payment.id,
                reference_no=receipt_no,
                action="FEE_PAYMENT_COLLECTED",
                amount=float(amount),
                after_snapshot={
                    "receipt_no": receipt_no,
                    "invoice_no": updated_fee.invoice_number,
                    "student_id": fee.student.student_id,
                    "amount_paid": float(amount),
                    "payment_method": norm_method,
                    "channel_detail": norm_detail,
                    "remaining_due": float(updated_fee.due_amount),
                },
                reason=remarks,
                actor_username=current_user,
                commit=False,
            )
            DatabaseService.log_activity(
                db,
                action="FEE_COLLECTION",
                module="FEES",
                description=(
                    f"Collected ৳{amount:,.2f} ({norm_method}) from {fee.student.full_name} "
                    f"[{fee.student.student_id}] (Receipt: {receipt_no})"
                ),
                username=current_user,
                entity_type="FeePayment",
                entity_id=str(payment.id),
                commit=False,
            )
            db.commit()
            db.refresh(payment)

            app_logger.info(f"Payment of ৳{amount} recorded for {fee.student.student_id} by {current_user}")
            return payment, "Payment recorded successfully."
        except Exception as exc:
            db.rollback()
            return None, str(exc)

    @staticmethod
    def collect_payment(db: Session, data: Dict[str, Any]) -> Tuple[Optional[FeePayment], Optional[str]]:
        """
        Dictionary-payload wrapper supporting legacy callers & UI forms.
        Returns `(payment, None)` on success or `(None, error_message)` on failure.
        """
        fee_id = data.get("student_fee_id")
        disc = float(data.get("discount_amount", 0.0) or 0.0)
        if disc > 0:
            _, d_msg = FeeService.apply_discount(
                db,
                fee_id,
                disc,
                data.get("discount_reason", "Collected-time concession"),
                current_user=data.get("received_by", "admin"),
            )
        pmt, msg = FeeService.collect_fee_payment(
            db,
            student_fee_id=fee_id,
            amount=float(data.get("amount", data.get("amount_paid", 0.0))),
            payment_method=data.get("payment_method", "Cash"),
            transaction_id=data.get("transaction_ref", data.get("transaction_id")),
            remarks=data.get("remarks"),
            current_user=data.get("received_by", data.get("collected_by", "admin")),
            idempotency_key=data.get("idempotency_key"),
            channel_detail=data.get("channel_detail"),
            post_to_accounting=data.get("post_to_accounting", True),
        )
        if pmt is None:
            if "exceeds" in msg.lower():
                return None, f"Payment amount exceeds balance due ({msg})"
            return None, msg
        return pmt, None

    # ==================== ADVANCE PAYMENT & CREDIT WALLET ====================
    @staticmethod
    def record_advance_payment(
        db: Session,
        student_id: int,
        amount: float,
        payment_method: str = "Cash",
        reference_no: Optional[str] = None,
        remarks: Optional[str] = None,
        current_user: str = "admin",
        channel_detail: Optional[str] = None,
        post_to_accounting: bool = True,
    ) -> Tuple[Optional[StudentAdvanceCredit], str]:
        if amount <= 0:
            return None, "Advance payment amount must be greater than zero."

        stu = db.query(Student).filter(Student.id == student_id, Student.is_deleted == False).first()
        if not stu:
            return None, "Student not found."

        norm_method, norm_detail = normalize_payment_channel(payment_method, channel_detail)
        curr_bal = FeeRepository.get_student_advance_balance(db, student_id)
        new_bal = round(curr_bal + float(amount), 2)
        adv_no = FeeService.generate_advance_receipt_no(db)
        tx_date = date.today()

        tx_id = None
        if post_to_accounting:
            inc_cat = FeeService._ensure_income_category(db, "INC-ADV")
            if inc_cat:
                tx, tx_err = AccountingService.record_transaction(
                    db,
                    {
                        "type": "Income",
                        "entry_kind": "AdvanceDeposit",
                        "category_id": inc_cat.id,
                        "academic_year_id": stu.academic_year_id,
                        "amount": float(amount),
                        "transaction_date": tx_date,
                        "payment_method": norm_method,
                        "channel_detail": norm_detail,
                        "reference_no": adv_no,
                        "paid_to_received_from": f"{stu.full_name} ({stu.student_id})",
                        "description": remarks or f"Advance fee wallet deposit ({adv_no})",
                    },
                    actor_username=current_user,
                    commit=False,
                )
                if tx and not tx_err:
                    tx_id = tx.id

        entry = StudentAdvanceCredit(
            receipt_no=adv_no,
            student_id=student_id,
            transaction_type="Deposit",
            amount=float(amount),
            signed_amount=float(amount),
            balance_after=new_bal,
            payment_method=norm_method,
            channel_detail=norm_detail,
            reference_no=reference_no,
            transaction_date=tx_date,
            accounting_tx_id=tx_id,
            recorded_by=current_user,
            remarks=remarks or "Advance fee deposit",
        )
        db.add(entry)
        db.flush()

        AccountingService.record_audit_log(
            db,
            module="FEES",
            entity_type="StudentAdvanceCredit",
            entity_id=entry.id,
            reference_no=adv_no,
            action="FEE_ADVANCE_DEPOSIT",
            amount=float(amount),
            after_snapshot={"student_id": stu.student_id, "balance_after": new_bal, "payment_method": norm_method},
            reason=remarks,
            actor_username=current_user,
            commit=False,
        )
        DatabaseService.log_activity(
            db,
            action="FEE_ADVANCE_DEPOSIT",
            module="FEES",
            description=f"Recorded advance deposit of ৳{amount:,.2f} for {stu.full_name} [{stu.student_id}] ({adv_no})",
            username=current_user,
            entity_type="StudentAdvanceCredit",
            entity_id=str(entry.id),
            commit=False,
        )
        db.commit()
        db.refresh(entry)
        return entry, f"Advance deposit {adv_no} recorded. Wallet balance: ৳{new_bal:,.2f}"

    @staticmethod
    def apply_advance_to_invoice(
        db: Session,
        student_fee_id: int,
        amount: Optional[float] = None,
        current_user: str = "admin",
    ) -> Tuple[Optional[FeePayment], str]:
        """
        Applies available student advance credit balance toward an open invoice without
        double-booking cash into accounting.
        """
        fee = FeeRepository.get_student_fee_by_id(db, student_fee_id)
        if not fee or getattr(fee, "is_deleted", False):
            return None, "Fee invoice not found."
        if fee.status == "Cancelled":
            return None, "Cannot apply advance credit to a cancelled invoice."
        if float(fee.due_amount) <= 0.01:
            return None, "Invoice has no remaining due balance."

        avail_bal = FeeRepository.get_student_advance_balance(db, fee.student_id)
        if avail_bal <= 0.01:
            return None, "Student has zero advance credit balance."

        req_amt = float(amount) if amount is not None else min(avail_bal, float(fee.due_amount))
        if req_amt <= 0:
            return None, "Allocation amount must be greater than zero."
        if req_amt > avail_bal + 0.01:
            return None, f"Requested amount (৳{req_amt:,.2f}) exceeds advance balance (৳{avail_bal:,.2f})."
        if req_amt > float(fee.due_amount) + 0.01:
            return None, f"Requested amount (৳{req_amt:,.2f}) exceeds invoice due (৳{float(fee.due_amount):,.2f})."

        new_bal = round(max(0.0, avail_bal - req_amt), 2)
        adv_no = FeeService.generate_advance_receipt_no(db)
        receipt_no = FeeService.generate_receipt_no(db)

        adv_entry = StudentAdvanceCredit(
            receipt_no=adv_no,
            student_id=fee.student_id,
            transaction_type="AppliedToInvoice",
            amount=req_amt,
            signed_amount=-req_amt,
            balance_after=new_bal,
            payment_method="Other",
            channel_detail="Advance Wallet",
            reference_no=fee.invoice_number,
            transaction_date=date.today(),
            student_fee_id=fee.id,
            recorded_by=current_user,
            remarks=f"Allocated to invoice {fee.invoice_number}",
        )
        db.add(adv_entry)
        db.flush()

        payment, updated_fee = FeeRepository.record_payment(
            db,
            {
                "receipt_no": receipt_no,
                "student_fee_id": fee.id,
                "student_id": fee.student_id,
                "amount_paid": req_amt,
                "payment_method": "Other",
                "channel_detail": "Advance Wallet",
                "transaction_id": adv_no,
                "payment_date": date.today(),
                "collected_by": current_user,
                "remarks": f"Settled via Advance Wallet ({adv_no})",
                "status": "Completed",
                "refunded_amount": 0.0,
                "is_advance_allocation": True,
            },
            commit=False,
        )

        AccountingService.record_audit_log(
            db,
            module="FEES",
            entity_type="FeePayment",
            entity_id=payment.id,
            reference_no=receipt_no,
            action="FEE_ADVANCE_APPLIED",
            amount=req_amt,
            after_snapshot={
                "advance_ref": adv_no,
                "invoice_no": updated_fee.invoice_number,
                "wallet_balance_after": new_bal,
                "invoice_due_after": float(updated_fee.due_amount),
            },
            actor_username=current_user,
            commit=False,
        )
        db.commit()
        db.refresh(payment)
        return payment, f"Applied ৳{req_amt:,.2f} from advance wallet to {updated_fee.invoice_number}."

    # ==================== REFUNDS & INVOICE CANCELLATION ====================
    @staticmethod
    def process_refund(
        db: Session,
        fee_payment_id: int,
        refund_amount: float,
        refund_method: str = "Cash",
        reason: str = "",
        reference_no: Optional[str] = None,
        approved_by: Optional[str] = None,
        current_user: str = "admin",
        channel_detail: Optional[str] = None,
        post_to_accounting: bool = True,
    ) -> Tuple[Optional[FeeRefund], str]:
        """
        Non-destructive fee refund mechanism. Never deletes the original FeePayment;
        creates an immutable FeeRefund voucher + compensating AccountTransaction expense.
        """
        if not reason or not reason.strip():
            return None, "Refund reason is mandatory for audit compliance."
        if refund_amount <= 0:
            return None, "Refund amount must be greater than zero."

        payment = DatabaseService.lock_for_update(
            db.query(FeePayment).filter(FeePayment.id == fee_payment_id, FeePayment.is_deleted == False),
            db,
        ).first()
        if not payment:
            return None, "Original payment receipt not found."

        avail = payment.refundable_balance
        if avail <= 0.001:
            return None, f"Receipt {payment.receipt_no} has already been fully refunded."
        if refund_amount > avail + 0.01:
            return None, f"Refund amount (৳{refund_amount:,.2f}) exceeds refundable balance (৳{avail:,.2f})."

        fee = DatabaseService.lock_for_update(
            db.query(StudentFee).filter(StudentFee.id == payment.student_fee_id),
            db,
        ).first()
        stu = db.query(Student).filter(Student.id == payment.student_id).first()

        norm_method, norm_detail = normalize_payment_channel(refund_method, channel_detail)
        refund_no = FeeService.generate_refund_no(db)
        ref_date = date.today()

        tx_id = None
        if post_to_accounting:
            exp_cat = FeeService._ensure_expense_category(db, "EXP-RFND")
            if exp_cat:
                tx, tx_err = AccountingService.record_transaction(
                    db,
                    {
                        "type": "Expense",
                        "entry_kind": "FeeRefund",
                        "category_id": exp_cat.id,
                        "academic_year_id": fee.academic_year_id if fee else None,
                        "amount": float(refund_amount),
                        "transaction_date": ref_date,
                        "payment_method": norm_method,
                        "channel_detail": norm_detail,
                        "reference_no": refund_no,
                        "paid_to_received_from": f"{stu.full_name} ({stu.student_id})" if stu else "Student Refund",
                        "description": f"Refund for {payment.receipt_no}: {reason.strip()}",
                    },
                    actor_username=current_user,
                    commit=False,
                )
                if tx and not tx_err:
                    tx_id = tx.id

        refund = FeeRefund(
            refund_no=refund_no,
            fee_payment_id=payment.id,
            student_fee_id=payment.student_fee_id,
            student_id=payment.student_id,
            refund_amount=float(refund_amount),
            refund_method=norm_method,
            channel_detail=norm_detail,
            reference_no=reference_no,
            refund_date=ref_date,
            reason=reason.strip(),
            processed_by=current_user,
            approved_by=approved_by or current_user,
            status="Completed",
            accounting_tx_id=tx_id,
        )
        db.add(refund)
        db.flush()

        # Update original payment without deleting it
        payment.refunded_amount = round(float(payment.refunded_amount or 0.0) + float(refund_amount), 2)
        payment.status = "Refunded" if payment.refundable_balance <= 0.01 else "Partially Refunded"

        # Update StudentFee invoice balances
        if fee:
            fee.refunded_amount = round(float(fee.refunded_amount or 0.0) + float(refund_amount), 2)
            effective_paid = max(0.0, float(fee.paid_amount or 0.0) - float(fee.refunded_amount))
            fee.due_amount = round(max(0.0, float(fee.net_amount) - effective_paid), 2)
            if effective_paid <= 0.01:
                fee.status = "Refunded"
            elif fee.refunded_amount > 0:
                fee.status = "Partially Refunded"

        AccountingService.record_audit_log(
            db,
            module="FEES",
            entity_type="FeeRefund",
            entity_id=refund.id,
            reference_no=refund_no,
            action="FEE_REFUND_PROCESSED",
            amount=float(refund_amount),
            after_snapshot={
                "refund_no": refund_no,
                "receipt_no": payment.receipt_no,
                "payment_status": payment.status,
                "invoice_status": fee.status if fee else None,
            },
            reason=reason.strip(),
            actor_username=current_user,
            commit=False,
        )
        DatabaseService.log_activity(
            db,
            action="FEE_REFUND_PROCESSED",
            module="FEES",
            description=f"Processed refund {refund_no} of ৳{refund_amount:,.2f} against receipt {payment.receipt_no}. Reason: {reason.strip()}",
            username=current_user,
            severity="WARNING",
            entity_type="FeeRefund",
            entity_id=str(refund.id),
            commit=False,
        )
        db.commit()
        db.refresh(refund)
        return refund, f"Refund {refund_no} processed successfully."

    @staticmethod
    def cancel_invoice(
        db: Session,
        student_fee_id: int,
        reason: str,
        current_user: str = "admin",
    ) -> Tuple[Optional[StudentFee], str]:
        """
        Non-destructive invoice cancellation.
        Blocks cancellation if active unrefunded payments exist on the invoice.
        """
        if not reason or not reason.strip():
            return None, "Cancellation reason is mandatory."

        fee = DatabaseService.lock_for_update(
            db.query(StudentFee).filter(StudentFee.id == student_fee_id, StudentFee.is_deleted == False),
            db,
        ).first()
        if not fee:
            return None, "Student fee invoice not found."
        if fee.status == "Cancelled":
            return fee, "Invoice is already cancelled."

        net_paid = round(max(0.0, float(fee.paid_amount or 0.0) - float(fee.refunded_amount or 0.0)), 2)
        if net_paid > 0.01:
            return None, (
                f"Cannot cancel invoice {fee.invoice_number}: ৳{net_paid:,.2f} net payment remains unrefunded. "
                f"Process a refund first."
            )

        before_snap = {"status": fee.status, "due_amount": float(fee.due_amount)}
        fee.status = "Cancelled"
        fee.due_amount = 0.0
        fee.cancelled_at = utc_now()
        fee.cancelled_by = current_user
        fee.cancellation_reason = reason.strip()

        AccountingService.record_audit_log(
            db,
            module="FEES",
            entity_type="StudentFee",
            entity_id=fee.id,
            reference_no=fee.invoice_number,
            action="FEE_INVOICE_CANCELLED",
            amount=float(fee.net_amount),
            before_snapshot=before_snap,
            after_snapshot={"status": "Cancelled", "due_amount": 0.0},
            reason=reason.strip(),
            actor_username=current_user,
            commit=False,
        )
        DatabaseService.log_activity(
            db,
            action="FEE_INVOICE_CANCELLED",
            module="FEES",
            description=f"Cancelled invoice {fee.invoice_number}. Reason: {reason.strip()}",
            username=current_user,
            severity="WARNING",
            entity_type="StudentFee",
            entity_id=str(fee.id),
            commit=False,
        )
        db.commit()
        db.refresh(fee)
        return fee, f"Invoice {fee.invoice_number} cancelled cleanly."

    # ==================== EXCEL EXPORTS: DUE & COLLECTION REPORTS ====================
    @staticmethod
    def export_due_report_excel(
        db: Session,
        output_file_path: str,
        class_id: Optional[int] = None,
        overdue_only: bool = False,
        school_info: Optional[Dict[str, str]] = None,
    ) -> bool:
        try:
            import openpyxl
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
            from openpyxl.utils import get_column_letter

            report = FeeRepository.get_due_report(db, class_id=class_id, overdue_only=overdue_only)
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Fee_Due_Report"

            school_name = school_info.get("name", "EduManage Pro Model High School") if school_info else "EduManage Pro High School"
            ws.merge_cells("A1:K1")
            ws["A1"] = school_name.upper()
            ws["A1"].font = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
            ws["A1"].alignment = Alignment(horizontal="center")

            ws.merge_cells("A2:K2")
            ws["A2"] = f"STUDENT FEE DUE & AGING REPORT | As of: {report['as_of_date']} | Total Due: ৳{report['total_due']:,.2f}"
            ws["A2"].font = Font(name="Calibri", size=11, bold=True, color="B91C1C")
            ws["A2"].alignment = Alignment(horizontal="center")

            headers = [
                "SL", "Invoice No", "Student ID", "Student Name", "Class", "Phone",
                "Category", "Fee Title", "Due Date", "Aging Bucket", "Due Amount (BDT)"
            ]
            header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            thin = Border(
                left=Side(style="thin", color="CBD5E1"),
                right=Side(style="thin", color="CBD5E1"),
                top=Side(style="thin", color="CBD5E1"),
                bottom=Side(style="thin", color="CBD5E1"),
            )

            for idx, h in enumerate(headers, 1):
                c = ws.cell(row=4, column=idx, value=h)
                c.font = header_font
                c.fill = header_fill
                c.alignment = Alignment(horizontal="center")
                c.border = thin

            r_idx = 5
            for sl, row in enumerate(report["rows"], 1):
                ws.cell(row=r_idx, column=1, value=sl).alignment = Alignment(horizontal="center")
                ws.cell(row=r_idx, column=2, value=row["invoice_no"])
                ws.cell(row=r_idx, column=3, value=row["student_id"])
                ws.cell(row=r_idx, column=4, value=row["student_name"])
                ws.cell(row=r_idx, column=5, value=row["class_name"])
                ws.cell(row=r_idx, column=6, value=row["phone"])
                ws.cell(row=r_idx, column=7, value=row["category"])
                ws.cell(row=r_idx, column=8, value=row["title"])
                ws.cell(row=r_idx, column=9, value=str(row["due_date"])).alignment = Alignment(horizontal="center")
                ws.cell(row=r_idx, column=10, value=row["aging_bucket"]).alignment = Alignment(horizontal="center")
                d_cell = ws.cell(row=r_idx, column=11, value=row["due_amount"])
                d_cell.number_format = "#,##0.00"
                d_cell.alignment = Alignment(horizontal="right")
                d_cell.font = Font(bold=True, color="B91C1C")
                for col_i in range(1, 12):
                    ws.cell(row=r_idx, column=col_i).border = thin
                r_idx += 1

            ws.merge_cells(f"A{r_idx}:J{r_idx}")
            ws.cell(row=r_idx, column=1, value="TOTAL OUTSTANDING RECEIVABLES:").alignment = Alignment(horizontal="right")
            ws.cell(row=r_idx, column=1).font = Font(bold=True)
            tot_c = ws.cell(row=r_idx, column=11, value=report["total_due"])
            tot_c.font = Font(bold=True, color="B91C1C")
            tot_c.number_format = "#,##0.00"

            for col in ws.columns:
                max_len = max((len(str(cell.value or "")) for cell in col), default=10)
                ws.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 4, 12)

            os.makedirs(os.path.dirname(os.path.abspath(output_file_path)), exist_ok=True)
            wb.save(output_file_path)
            return True
        except Exception as exc:
            app_logger.error(f"Due report Excel export failed: {exc}")
            return False

    @staticmethod
    def export_collection_report_excel(
        db: Session,
        output_file_path: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        payment_method: Optional[str] = None,
        school_info: Optional[Dict[str, str]] = None,
    ) -> bool:
        try:
            import openpyxl
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
            from openpyxl.utils import get_column_letter

            report = FeeRepository.get_collection_report(
                db, start_date=start_date, end_date=end_date, payment_method=payment_method
            )
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Collection_Report"

            school_name = school_info.get("name", "EduManage Pro Model High School") if school_info else "EduManage Pro High School"
            ws.merge_cells("A1:K1")
            ws["A1"] = school_name.upper()
            ws["A1"].font = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
            ws["A1"].alignment = Alignment(horizontal="center")

            ws.merge_cells("A2:K2")
            ws["A2"] = f"FEE COLLECTION REPORT | Net Collected: ৳{report['net_collected']:,.2f} | Refunded: ৳{report['total_refunded']:,.2f}"
            ws["A2"].font = Font(name="Calibri", size=11, bold=True, color="047857")
            ws["A2"].alignment = Alignment(horizontal="center")

            headers = [
                "SL", "Receipt No", "Date", "Student ID", "Student Name", "Class",
                "Category", "Channel", "Paid (BDT)", "Refunded (BDT)", "Net (BDT)"
            ]
            header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            thin = Border(
                left=Side(style="thin", color="CBD5E1"),
                right=Side(style="thin", color="CBD5E1"),
                top=Side(style="thin", color="CBD5E1"),
                bottom=Side(style="thin", color="CBD5E1"),
            )

            for idx, h in enumerate(headers, 1):
                c = ws.cell(row=4, column=idx, value=h)
                c.font = header_font
                c.fill = header_fill
                c.alignment = Alignment(horizontal="center")
                c.border = thin

            r_idx = 5
            for sl, row in enumerate(report["rows"], 1):
                ws.cell(row=r_idx, column=1, value=sl).alignment = Alignment(horizontal="center")
                ws.cell(row=r_idx, column=2, value=row["receipt_no"])
                ws.cell(row=r_idx, column=3, value=str(row["payment_date"])).alignment = Alignment(horizontal="center")
                ws.cell(row=r_idx, column=4, value=row["student_id"])
                ws.cell(row=r_idx, column=5, value=row["student_name"])
                ws.cell(row=r_idx, column=6, value=row["class_name"])
                ws.cell(row=r_idx, column=7, value=row["category"])
                ws.cell(row=r_idx, column=8, value=row["payment_method"])
                for col_num, val in ((9, row["amount_paid"]), (10, row["refunded_amount"]), (11, row["net_amount"])):
                    cell = ws.cell(row=r_idx, column=col_num, value=val)
                    cell.number_format = "#,##0.00"
                    cell.alignment = Alignment(horizontal="right")
                for col_i in range(1, 12):
                    ws.cell(row=r_idx, column=col_i).border = thin
                r_idx += 1

            ws.merge_cells(f"A{r_idx}:H{r_idx}")
            ws.cell(row=r_idx, column=1, value="TOTAL COLLECTIONS:").alignment = Alignment(horizontal="right")
            ws.cell(row=r_idx, column=1).font = Font(bold=True)
            for col_num, val in ((9, report["gross_collected"]), (10, report["total_refunded"]), (11, report["net_collected"])):
                c = ws.cell(row=r_idx, column=col_num, value=val)
                c.font = Font(bold=True)
                c.number_format = "#,##0.00"

            for col in ws.columns:
                max_len = max((len(str(cell.value or "")) for cell in col), default=10)
                ws.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 4, 12)

            os.makedirs(os.path.dirname(os.path.abspath(output_file_path)), exist_ok=True)
            wb.save(output_file_path)
            return True
        except Exception as exc:
            app_logger.error(f"Collection report Excel export failed: {exc}")
            return False
