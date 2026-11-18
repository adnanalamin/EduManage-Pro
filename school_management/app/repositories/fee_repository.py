"""
EduManage Pro - Enterprise Fees Repository Layer
Data access operations for fee categories, rate structures, monthly/custom student invoices,
immutable payments, adjustments (discount/scholarship/waiver), advance credit wallets,
refunds, due aging reports, and collection analytics.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, extract, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.academic import AcademicYear, SchoolClass
from app.models.fee import (
    FeeAdjustment,
    FeeCategory,
    FeePayment,
    FeeRefund,
    FeeStructure,
    StudentAdvanceCredit,
    StudentFee,
)
from app.models.student import Student
from app.services.database_service import DatabaseService


class FeeRepository:
    # ==================== CATEGORIES & STRUCTURES ====================
    @staticmethod
    def get_categories(db: Session, active_only: bool = True) -> List[FeeCategory]:
        query = db.query(FeeCategory).filter(FeeCategory.is_deleted == False)
        if active_only:
            query = query.filter(FeeCategory.is_active == True)
        return query.order_by(FeeCategory.name.asc()).all()

    @staticmethod
    def get_all_categories(db: Session) -> List[FeeCategory]:
        return FeeRepository.get_categories(db, active_only=True)

    @staticmethod
    def get_category_by_code(db: Session, code: str) -> Optional[FeeCategory]:
        return (
            db.query(FeeCategory)
            .filter(func.lower(FeeCategory.code) == (code or "").strip().lower(), FeeCategory.is_deleted == False)
            .first()
        )

    @staticmethod
    def create_category(db: Session, data: dict) -> FeeCategory:
        payload = dict(data)
        if "code" not in payload or not payload["code"]:
            raw_name = (payload.get("name") or "FEE").strip().upper()
            base = "".join(ch for ch in raw_name if ch.isalnum())[:4] or "FEE"
            suffix = db.query(FeeCategory).count() + 1
            payload["code"] = f"{base}{suffix:02d}"
        cat = FeeCategory(**payload)
        db.add(cat)
        db.commit()
        db.refresh(cat)
        return cat

    @staticmethod
    def get_fee_structures(
        db: Session,
        class_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> List[FeeStructure]:
        query = (
            db.query(FeeStructure)
            .options(
                joinedload(FeeStructure.category),
                joinedload(FeeStructure.school_class),
                joinedload(FeeStructure.academic_year),
            )
            .filter(FeeStructure.is_deleted == False)
        )
        if class_id:
            query = query.filter(FeeStructure.class_id == class_id)
        if academic_year_id:
            query = query.filter(FeeStructure.academic_year_id == academic_year_id)
        if category_id:
            query = query.filter(FeeStructure.category_id == category_id)
        return query.order_by(FeeStructure.due_date.desc(), FeeStructure.id.desc()).all()

    @staticmethod
    def create_fee_structure(db: Session, data: dict) -> FeeStructure:
        struct = FeeStructure(**data)
        db.add(struct)
        db.commit()
        db.refresh(struct)
        return struct

    @staticmethod
    def generate_invoice_no(db: Session, ref_date: Optional[date] = None) -> str:
        year = (ref_date or date.today()).year
        count = db.query(func.count(StudentFee.id)).scalar() or 0
        seq = count + 1
        while True:
            candidate = f"INV-{year}-{seq:05d}"
            exists = db.query(StudentFee.id).filter(StudentFee.invoice_no == candidate).first()
            if not exists:
                return candidate
            seq += 1

    @staticmethod
    def batch_assign_fee_structure(
        db: Session,
        fee_structure_id: int,
        class_id: int,
        academic_year_id: Optional[int] = None,
    ) -> int:
        """
        Assigns a fee structure to all active students in the specified class.
        Avoids duplicate assignment of the same structure to the same student in the same session.
        """
        struct = db.query(FeeStructure).filter(FeeStructure.id == fee_structure_id).first()
        if not struct:
            return 0
        ay_id = academic_year_id or struct.academic_year_id

        students = (
            db.query(Student)
            .filter(
                Student.class_id == class_id,
                func.lower(Student.status) == "active",
                Student.is_deleted == False,
            )
            .all()
        )

        assigned_count = 0
        for stu in students:
            existing = (
                db.query(StudentFee)
                .filter(
                    StudentFee.student_id == stu.id,
                    StudentFee.fee_structure_id == fee_structure_id,
                    StudentFee.academic_year_id == ay_id,
                )
                .first()
            )
            if not existing:
                inv_no = FeeRepository.generate_invoice_no(db, struct.due_date)
                invoice = StudentFee(
                    invoice_no=inv_no,
                    student_id=stu.id,
                    fee_structure_id=fee_structure_id,
                    academic_year_id=ay_id,
                    title=struct.title,
                    total_amount=float(struct.amount),
                    discount_amount=0.0,
                    scholarship_amount=0.0,
                    waiver_amount=0.0,
                    net_amount=float(struct.amount),
                    paid_amount=0.0,
                    refunded_amount=0.0,
                    advance_applied_amount=0.0,
                    due_amount=float(struct.amount),
                    status="Unpaid",
                    due_date=struct.due_date,
                    billing_month=struct.billing_month,
                    billing_year=struct.billing_year,
                )
                db.add(invoice)
                db.flush()
                assigned_count += 1

        db.commit()
        return assigned_count

    @staticmethod
    def batch_assign_fee_to_class(
        db: Session,
        fee_structure_id: int,
        class_id: int,
        academic_year_id: Optional[int] = None,
    ) -> int:
        return FeeRepository.batch_assign_fee_structure(
            db, fee_structure_id=fee_structure_id, class_id=class_id, academic_year_id=academic_year_id
        )

    # ==================== STUDENT FEES (INVOICES) ====================
    @staticmethod
    def get_student_fees(
        db: Session,
        class_id: Optional[int] = None,
        student_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[StudentFee], int]:
        query = (
            db.query(StudentFee)
            .options(
                joinedload(StudentFee.student).joinedload(Student.school_class),
                joinedload(StudentFee.fee_structure).joinedload(FeeStructure.category),
                joinedload(StudentFee.academic_year),
            )
            .filter(StudentFee.is_deleted == False)
        )

        joined_student = False
        if class_id:
            query = query.join(StudentFee.student).filter(Student.class_id == class_id)
            joined_student = True
        if student_id:
            query = query.filter(StudentFee.student_id == student_id)
        if academic_year_id:
            query = query.filter(StudentFee.academic_year_id == academic_year_id)
        if category_id:
            query = query.join(StudentFee.fee_structure).filter(FeeStructure.category_id == category_id)
        if status and status.lower() != "all":
            if status == "Overdue":
                query = query.filter(
                    StudentFee.due_amount > 0.01,
                    StudentFee.due_date < date.today(),
                    StudentFee.status != "Cancelled",
                )
            else:
                query = query.filter(StudentFee.status == status)
        if search:
            term = f"%{search.strip()}%"
            if not joined_student:
                query = query.join(StudentFee.student)
            query = query.filter(
                or_(
                    Student.full_name.ilike(term),
                    Student.student_id.ilike(term),
                    StudentFee.invoice_no.ilike(term),
                    StudentFee.title.ilike(term),
                )
            )

        total = query.count()
        items = (
            query.order_by(StudentFee.due_date.asc(), StudentFee.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    @staticmethod
    def list_student_fees(
        db: Session,
        student_id: Optional[int] = None,
        class_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 200,
    ) -> List[StudentFee]:
        items, _ = FeeRepository.get_student_fees(
            db, class_id=class_id, student_id=student_id, status=status, page=1, per_page=limit
        )
        return items

    @staticmethod
    def get_student_fee_by_id(db: Session, fee_id: int) -> Optional[StudentFee]:
        return (
            db.query(StudentFee)
            .options(
                joinedload(StudentFee.student).joinedload(Student.school_class),
                joinedload(StudentFee.student).joinedload(Student.section),
                joinedload(StudentFee.fee_structure).joinedload(FeeStructure.category),
                joinedload(StudentFee.payments),
                joinedload(StudentFee.adjustments),
                joinedload(StudentFee.refunds),
            )
            .filter(StudentFee.id == fee_id)
            .first()
        )

    @staticmethod
    def delete_invoice(db: Session, fee_id: int) -> None:
        raise ValueError(
            "Permanent deletion of financial invoices is prohibited. Use cancel_invoice() instead."
        )

    @staticmethod
    def delete_payment(db: Session, payment_id: int) -> None:
        raise ValueError(
            "Permanent deletion of payment receipts is prohibited. Use process_refund() instead."
        )

    # ==================== PAYMENTS ====================
    @staticmethod
    def record_payment(db: Session, payment_data: dict, commit: bool = True) -> Tuple[FeePayment, StudentFee]:
        fee = DatabaseService.lock_for_update(
            db.query(StudentFee).filter(
                StudentFee.id == payment_data["student_fee_id"],
                StudentFee.is_deleted == False,
            ),
            db,
        ).first()
        if not fee:
            raise ValueError("Student fee invoice not found.")
        if fee.status == "Cancelled":
            raise ValueError("Cannot collect payment on a cancelled invoice.")

        existing_idem = DatabaseService.prevent_duplicate_payment(
            db,
            student_fee_id=fee.id,
            receipt_no=payment_data.get("receipt_no"),
            idempotency_key=payment_data.get("idempotency_key"),
            transaction_id=payment_data.get("transaction_id"),
        )
        if existing_idem:
            return existing_idem, fee

        amount = float(payment_data["amount_paid"])
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        if amount > fee.due_amount + 0.01:
            raise ValueError(f"Payment amount (৳{amount:,.2f}) cannot exceed due amount (৳{fee.due_amount:,.2f}).")

        payment = FeePayment(**payment_data)
        db.add(payment)

        fee.paid_amount = round(float(fee.paid_amount or 0.0) + amount, 2)
        if payment_data.get("is_advance_allocation"):
            fee.advance_applied_amount = round(float(fee.advance_applied_amount or 0.0) + amount, 2)

        effective_paid = max(0.0, float(fee.paid_amount) - float(fee.refunded_amount or 0.0))
        fee.due_amount = round(max(0.0, float(fee.net_amount) - effective_paid), 2)
        fee.status = "Paid" if fee.due_amount <= 0.01 else "Partial"

        if commit:
            db.commit()
            db.refresh(payment)
            db.refresh(fee)
        else:
            db.flush()
        return payment, fee

    @staticmethod
    def get_payments(
        db: Session,
        search: Optional[str] = None,
        student_id: Optional[int] = None,
        payment_method: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Tuple[List[FeePayment], int]:
        query = (
            db.query(FeePayment)
            .options(
                joinedload(FeePayment.student).joinedload(Student.school_class),
                joinedload(FeePayment.student_fee).joinedload(StudentFee.fee_structure).joinedload(FeeStructure.category),
            )
            .filter(FeePayment.is_deleted == False)
        )
        if student_id:
            query = query.filter(FeePayment.student_id == student_id)
        if payment_method and payment_method.lower() not in ("all", "all channels"):
            query = query.filter(FeePayment.payment_method == payment_method)
        if status and status.lower() != "all":
            query = query.filter(FeePayment.status == status)
        if start_date:
            query = query.filter(FeePayment.payment_date >= start_date)
        if end_date:
            query = query.filter(FeePayment.payment_date <= end_date)
        if search:
            term = f"%{search.strip()}%"
            query = query.join(FeePayment.student).filter(
                or_(
                    FeePayment.receipt_no.ilike(term),
                    FeePayment.transaction_id.ilike(term),
                    FeePayment.channel_detail.ilike(term),
                    Student.full_name.ilike(term),
                    Student.student_id.ilike(term),
                )
            )

        total = query.count()
        items = (
            query.order_by(FeePayment.payment_date.desc(), FeePayment.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    @staticmethod
    def get_payment_by_id(db: Session, payment_id: int) -> Optional[FeePayment]:
        return (
            db.query(FeePayment)
            .options(
                joinedload(FeePayment.student),
                joinedload(FeePayment.student_fee).joinedload(StudentFee.fee_structure),
                joinedload(FeePayment.refunds),
            )
            .filter(FeePayment.id == payment_id)
            .first()
        )

    # ==================== ADVANCE WALLET, REFUNDS, ADJUSTMENTS ====================
    @staticmethod
    def get_student_advance_balance(db: Session, student_id: int) -> float:
        total = (
            db.query(func.coalesce(func.sum(StudentAdvanceCredit.signed_amount), 0.0))
            .filter(StudentAdvanceCredit.student_id == student_id)
            .scalar()
        )
        return round(max(0.0, float(total or 0.0)), 2)

    @staticmethod
    def get_advance_credits(
        db: Session,
        student_id: Optional[int] = None,
        limit: int = 200,
    ) -> List[StudentAdvanceCredit]:
        query = db.query(StudentAdvanceCredit).options(
            joinedload(StudentAdvanceCredit.student),
            joinedload(StudentAdvanceCredit.student_fee),
        )
        if student_id:
            query = query.filter(StudentAdvanceCredit.student_id == student_id)
        return query.order_by(StudentAdvanceCredit.transaction_date.desc(), StudentAdvanceCredit.id.desc()).limit(limit).all()

    @staticmethod
    def get_refunds(
        db: Session,
        student_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        limit: int = 200,
    ) -> List[FeeRefund]:
        query = db.query(FeeRefund).options(
            joinedload(FeeRefund.student),
            joinedload(FeeRefund.fee_payment),
            joinedload(FeeRefund.student_fee).joinedload(StudentFee.fee_structure),
        )
        if student_id:
            query = query.filter(FeeRefund.student_id == student_id)
        if start_date:
            query = query.filter(FeeRefund.refund_date >= start_date)
        if end_date:
            query = query.filter(FeeRefund.refund_date <= end_date)
        if search:
            term = f"%{search.strip()}%"
            query = query.join(FeeRefund.student).filter(
                or_(
                    FeeRefund.refund_no.ilike(term),
                    FeeRefund.reason.ilike(term),
                    Student.full_name.ilike(term),
                    Student.student_id.ilike(term),
                )
            )
        return query.order_by(FeeRefund.refund_date.desc(), FeeRefund.id.desc()).limit(limit).all()

    @staticmethod
    def get_adjustments(
        db: Session,
        student_fee_id: Optional[int] = None,
        student_id: Optional[int] = None,
        limit: int = 200,
    ) -> List[FeeAdjustment]:
        query = db.query(FeeAdjustment).options(
            joinedload(FeeAdjustment.student),
            joinedload(FeeAdjustment.student_fee),
        )
        if student_fee_id:
            query = query.filter(FeeAdjustment.student_fee_id == student_fee_id)
        if student_id:
            query = query.filter(FeeAdjustment.student_id == student_id)
        return query.order_by(FeeAdjustment.applied_at.desc(), FeeAdjustment.id.desc()).limit(limit).all()

    # ==================== KPI, DUE & COLLECTION REPORTS ====================
    @staticmethod
    def get_financial_kpi(db: Session, academic_year_id: Optional[int] = None) -> Dict[str, float]:
        query = db.query(
            func.coalesce(func.sum(StudentFee.total_amount), 0.0),
            func.coalesce(func.sum(StudentFee.discount_amount), 0.0),
            func.coalesce(func.sum(StudentFee.scholarship_amount), 0.0),
            func.coalesce(func.sum(StudentFee.waiver_amount), 0.0),
            func.coalesce(func.sum(StudentFee.paid_amount), 0.0),
            func.coalesce(func.sum(StudentFee.refunded_amount), 0.0),
            func.coalesce(func.sum(StudentFee.due_amount), 0.0),
        ).filter(
            StudentFee.is_deleted == False,
            StudentFee.status != "Cancelled",
        )
        if academic_year_id:
            query = query.filter(StudentFee.academic_year_id == academic_year_id)

        tot_invoiced, tot_discount, tot_schol, tot_waiver, tot_paid, tot_refunded, tot_due = query.first()
        advance_pool = (
            db.query(func.coalesce(func.sum(StudentAdvanceCredit.signed_amount), 0.0)).scalar() or 0.0
        )
        net_collected = max(0.0, float(tot_paid or 0.0) - float(tot_refunded or 0.0))
        return {
            "total_invoiced": float(tot_invoiced or 0.0),
            "total_discount": float(tot_discount or 0.0),
            "total_scholarship": float(tot_schol or 0.0),
            "total_waiver": float(tot_waiver or 0.0),
            "total_collected": net_collected,
            "gross_collected": float(tot_paid or 0.0),
            "total_refunded": float(tot_refunded or 0.0),
            "total_due": float(tot_due or 0.0),
            "total_advance_balance": max(0.0, float(advance_pool)),
        }

    @staticmethod
    def get_due_report(
        db: Session,
        class_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        category_id: Optional[int] = None,
        overdue_only: bool = False,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        ref_date = as_of_date or date.today()
        query = (
            db.query(StudentFee)
            .options(
                joinedload(StudentFee.student).joinedload(Student.school_class),
                joinedload(StudentFee.student).joinedload(Student.section),
                joinedload(StudentFee.fee_structure).joinedload(FeeStructure.category),
            )
            .join(StudentFee.student)
            .filter(
                StudentFee.is_deleted == False,
                StudentFee.status != "Cancelled",
                StudentFee.due_amount > 0.01,
            )
        )
        if class_id:
            query = query.filter(Student.class_id == class_id)
        if academic_year_id:
            query = query.filter(StudentFee.academic_year_id == academic_year_id)
        if category_id:
            query = query.join(StudentFee.fee_structure).filter(FeeStructure.category_id == category_id)
        if overdue_only:
            query = query.filter(StudentFee.due_date < ref_date)

        invoices = query.order_by(StudentFee.due_date.asc(), StudentFee.id.asc()).all()
        rows: List[Dict[str, Any]] = []
        aging = {
            "Current": 0.0,
            "1-30 Days": 0.0,
            "31-60 Days": 0.0,
            "61-90 Days": 0.0,
            "90+ Days": 0.0,
        }
        class_totals: Dict[str, float] = {}
        total_due = 0.0

        for inv in invoices:
            stu = inv.student
            cls_name = stu.school_class.name if stu and stu.school_class else "Unassigned"
            sec_name = stu.section.name if stu and stu.section else "-"
            cat_name = inv.fee_structure.category.name if inv.fee_structure and inv.fee_structure.category else "Other"
            days_overdue = max(0, (ref_date - inv.due_date).days) if inv.due_date else 0

            if days_overdue == 0:
                bucket = "Current"
            elif days_overdue <= 30:
                bucket = "1-30 Days"
            elif days_overdue <= 60:
                bucket = "31-60 Days"
            elif days_overdue <= 90:
                bucket = "61-90 Days"
            else:
                bucket = "90+ Days"

            due_val = float(inv.due_amount or 0.0)
            aging[bucket] += due_val
            class_totals[cls_name] = class_totals.get(cls_name, 0.0) + due_val
            total_due += due_val

            rows.append(
                {
                    "student_fee_id": inv.id,
                    "invoice_no": inv.invoice_number,
                    "student_id": stu.student_id if stu else "-",
                    "student_pk": stu.id if stu else None,
                    "student_name": stu.full_name if stu else "Unknown",
                    "roll_number": stu.roll_number if stu else "-",
                    "class_name": cls_name,
                    "section_name": sec_name,
                    "phone": stu.phone or "-",
                    "category": cat_name,
                    "title": inv.display_title,
                    "due_date": inv.due_date,
                    "days_overdue": days_overdue,
                    "aging_bucket": bucket,
                    "total_amount": float(inv.total_amount or 0.0),
                    "concession_amount": float(inv.discount_amount or 0.0),
                    "net_amount": float(inv.net_amount or 0.0),
                    "paid_amount": float(inv.paid_amount or 0.0),
                    "due_amount": due_val,
                    "status": "Overdue" if days_overdue > 0 else inv.status,
                }
            )

        return {
            "as_of_date": ref_date,
            "invoice_count": len(rows),
            "student_count": len({r["student_pk"] for r in rows if r["student_pk"] is not None}),
            "total_due": round(total_due, 2),
            "aging_summary": {k: round(v, 2) for k, v in aging.items()},
            "class_breakdown": {k: round(v, 2) for k, v in sorted(class_totals.items())},
            "rows": rows,
        }

    @staticmethod
    def get_collection_report(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        payment_method: Optional[str] = None,
        category_id: Optional[int] = None,
        class_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        query = (
            db.query(FeePayment)
            .options(
                joinedload(FeePayment.student).joinedload(Student.school_class),
                joinedload(FeePayment.student_fee).joinedload(StudentFee.fee_structure).joinedload(FeeStructure.category),
            )
            .join(FeePayment.student)
            .join(FeePayment.student_fee)
            .filter(FeePayment.is_deleted == False)
        )
        if start_date:
            query = query.filter(FeePayment.payment_date >= start_date)
        if end_date:
            query = query.filter(FeePayment.payment_date <= end_date)
        if payment_method and payment_method.lower() not in ("all", "all channels"):
            query = query.filter(FeePayment.payment_method == payment_method)
        if class_id:
            query = query.filter(Student.class_id == class_id)
        if category_id:
            query = query.join(StudentFee.fee_structure).filter(FeeStructure.category_id == category_id)

        payments = query.order_by(FeePayment.payment_date.desc(), FeePayment.id.desc()).all()

        by_channel: Dict[str, float] = {}
        by_category: Dict[str, float] = {}
        rows: List[Dict[str, Any]] = []
        gross_collected = 0.0
        refunded_total = 0.0

        for p in payments:
            amt = float(p.amount_paid or 0.0)
            ref = float(p.refunded_amount or 0.0)
            net_amt = max(0.0, amt - ref)
            gross_collected += amt
            refunded_total += ref

            channel = p.payment_method or "Other"
            by_channel[channel] = by_channel.get(channel, 0.0) + net_amt

            cat_name = (
                p.student_fee.fee_structure.category.name
                if p.student_fee and p.student_fee.fee_structure and p.student_fee.fee_structure.category
                else "Other Fee"
            )
            by_category[cat_name] = by_category.get(cat_name, 0.0) + net_amt

            rows.append(
                {
                    "payment_id": p.id,
                    "receipt_no": p.receipt_no,
                    "invoice_no": p.student_fee.invoice_number if p.student_fee else "-",
                    "payment_date": p.payment_date,
                    "student_id": p.student.student_id if p.student else "-",
                    "student_name": p.student.full_name if p.student else "-",
                    "class_name": p.student.school_class.name if p.student and p.student.school_class else "-",
                    "category": cat_name,
                    "fee_title": p.student_fee.display_title if p.student_fee else "-",
                    "payment_method": channel,
                    "channel_detail": p.channel_detail or "-",
                    "transaction_id": p.transaction_id or "-",
                    "amount_paid": amt,
                    "refunded_amount": ref,
                    "net_amount": net_amt,
                    "collected_by": p.collected_by,
                    "status": p.status,
                }
            )

        return {
            "start_date": start_date,
            "end_date": end_date,
            "payment_count": len(rows),
            "gross_collected": round(gross_collected, 2),
            "total_refunded": round(refunded_total, 2),
            "net_collected": round(max(0.0, gross_collected - refunded_total), 2),
            "by_channel": {k: round(v, 2) for k, v in sorted(by_channel.items())},
            "by_category": {k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda x: -x[1])},
            "rows": rows,
        }
