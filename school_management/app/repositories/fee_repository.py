"""
EduManage Pro - Fees Repository Layer
Data access operations for fee categories, rate structures, student billings, payments, and financial summaries.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_
from app.models.fee import FeeCategory, FeeStructure, StudentFee, FeePayment
from app.models.student import Student
from app.models.academic import SchoolClass, AcademicYear


class FeeRepository:
    # ==================== CATEGORIES & STRUCTURES ====================
    @staticmethod
    def get_categories(db: Session) -> List[FeeCategory]:
        return db.query(FeeCategory).filter(FeeCategory.is_active == True).order_by(FeeCategory.name.asc()).all()

    @staticmethod
    def create_category(db: Session, data: dict) -> FeeCategory:
        cat = FeeCategory(**data)
        db.add(cat)
        db.commit()
        db.refresh(cat)
        return cat

    @staticmethod
    def get_fee_structures(
        db: Session,
        class_id: Optional[int] = None,
        academic_year_id: Optional[int] = None
    ) -> List[FeeStructure]:
        query = db.query(FeeStructure).options(
            joinedload(FeeStructure.category),
            joinedload(FeeStructure.school_class),
            joinedload(FeeStructure.academic_year)
        )
        if class_id:
            query = query.filter(FeeStructure.class_id == class_id)
        if academic_year_id:
            query = query.filter(FeeStructure.academic_year_id == academic_year_id)
        return query.order_by(FeeStructure.due_date.desc()).all()

    @staticmethod
    def create_fee_structure(db: Session, data: dict) -> FeeStructure:
        struct = FeeStructure(**data)
        db.add(struct)
        db.commit()
        db.refresh(struct)
        return struct

    @staticmethod
    def batch_assign_fee_structure(
        db: Session,
        fee_structure_id: int,
        class_id: int,
        academic_year_id: int
    ) -> int:
        """
        Assigns a fee structure to all active students in the specified class.
        Avoids duplicate assignment of the same structure to the same student in the same session.
        """
        struct = db.query(FeeStructure).filter(FeeStructure.id == fee_structure_id).first()
        if not struct:
            return 0

        students = db.query(Student).filter(
            Student.class_id == class_id,
            Student.status == "active"
        ).all()

        assigned_count = 0
        for stu in students:
            # Check if already assigned
            existing = db.query(StudentFee).filter(
                StudentFee.student_id == stu.id,
                StudentFee.fee_structure_id == fee_structure_id,
                StudentFee.academic_year_id == academic_year_id
            ).first()

            if not existing:
                invoice = StudentFee(
                    student_id=stu.id,
                    fee_structure_id=fee_structure_id,
                    academic_year_id=academic_year_id,
                    total_amount=struct.amount,
                    discount_amount=0.0,
                    net_amount=struct.amount,
                    paid_amount=0.0,
                    due_amount=struct.amount,
                    status="Unpaid",
                    due_date=struct.due_date
                )
                db.add(invoice)
                assigned_count += 1

        db.commit()
        return assigned_count

    # ==================== STUDENT FEES (INVOICES) ====================
    @staticmethod
    def get_student_fees(
        db: Session,
        class_id: Optional[int] = None,
        student_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 25
    ) -> Tuple[List[StudentFee], int]:
        query = db.query(StudentFee).options(
            joinedload(StudentFee.student),
            joinedload(StudentFee.fee_structure).joinedload(FeeStructure.category)
        )

        if class_id:
            query = query.join(StudentFee.student).filter(Student.class_id == class_id)
        if student_id:
            query = query.filter(StudentFee.student_id == student_id)
        if status and status != "all":
            query = query.filter(StudentFee.status == status)
        if search:
            term = f"%{search}%"
            query = query.join(StudentFee.student).filter(
                or_(
                    Student.full_name.ilike(term),
                    Student.student_id.ilike(term)
                )
            )

        total = query.count()
        items = query.order_by(StudentFee.due_date.asc(), StudentFee.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return items, total

    @staticmethod
    def get_student_fee_by_id(db: Session, fee_id: int) -> Optional[StudentFee]:
        return db.query(StudentFee).options(
            joinedload(StudentFee.student),
            joinedload(StudentFee.fee_structure).joinedload(FeeStructure.category),
            joinedload(StudentFee.payments)
        ).filter(StudentFee.id == fee_id).first()

    # ==================== PAYMENTS ====================
    @staticmethod
    def record_payment(db: Session, payment_data: dict) -> Tuple[FeePayment, StudentFee]:
        fee = db.query(StudentFee).filter(StudentFee.id == payment_data["student_fee_id"]).first()
        if not fee:
            raise ValueError("Student fee invoice not found.")

        amount = float(payment_data["amount_paid"])
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        if amount > fee.due_amount + 0.01:
            raise ValueError(f"Payment amount (৳{amount}) cannot exceed due amount (৳{fee.due_amount}).")

        # Create Payment Record
        payment = FeePayment(**payment_data)
        db.add(payment)

        # Update Student Fee Record
        fee.paid_amount += amount
        fee.due_amount = max(0.0, fee.net_amount - fee.paid_amount)
        if fee.due_amount <= 0.01:
            fee.status = "Paid"
        else:
            fee.status = "Partial"

        db.commit()
        db.refresh(payment)
        db.refresh(fee)
        return payment, fee

    @staticmethod
    def get_payments(
        db: Session,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 25
    ) -> Tuple[List[FeePayment], int]:
        query = db.query(FeePayment).options(
            joinedload(FeePayment.student),
            joinedload(FeePayment.student_fee).joinedload(StudentFee.fee_structure)
        )
        if search:
            term = f"%{search}%"
            query = query.join(FeePayment.student).filter(
                or_(
                    FeePayment.receipt_no.ilike(term),
                    FeePayment.transaction_id.ilike(term),
                    Student.full_name.ilike(term),
                    Student.student_id.ilike(term)
                )
            )

        total = query.count()
        items = query.order_by(FeePayment.payment_date.desc(), FeePayment.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return items, total

    @staticmethod
    def get_financial_kpi(db: Session, academic_year_id: Optional[int] = None) -> Dict[str, float]:
        query = db.query(
            func.coalesce(func.sum(StudentFee.total_amount), 0.0),
            func.coalesce(func.sum(StudentFee.discount_amount), 0.0),
            func.coalesce(func.sum(StudentFee.paid_amount), 0.0),
            func.coalesce(func.sum(StudentFee.due_amount), 0.0)
        )
        if academic_year_id:
            query = query.filter(StudentFee.academic_year_id == academic_year_id)

        tot_invoiced, tot_discount, tot_paid, tot_due = query.first()
        return {
            "total_invoiced": float(tot_invoiced),
            "total_discount": float(tot_discount),
            "total_collected": float(tot_paid),
            "total_due": float(tot_due),
        }
