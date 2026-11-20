"""
EduManage Pro - Real-Database Analytics & Master Data Export Service
Computes strictly live KPIs and chart series from SQLAlchemy ORM tables with
zero fabricated fallback numbers or fake charts.
"""

from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import csv
import os

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.accounting import AccountCategory, AccountTransaction
from app.models.attendance import StaffAttendance, StudentAttendance, TeacherAttendance
from app.models.exam import ExamResultSummary, ExamTerm
from app.models.fee import FeePayment, StudentFee
from app.models.hostel import HostelAllocation, HostelBed, HostelBlock, HostelRoom
from app.models.inventory import FixedAsset, InventoryItem
from app.models.library import Book, BookCirculation, LibraryFine
from app.models.payroll import PayrollPayslip, PayrollPeriodRun
from app.models.school import SchoolSetting
from app.models.staff import Staff, Teacher
from app.models.student import Student
from app.models.transport import TransportPassenger, TransportRoute, Vehicle


def _month_key(dt: Optional[date]) -> str:
    if not dt:
        return "Unknown"
    return dt.strftime("%Y-%m")


class AnalyticsService:
    @staticmethod
    def get_executive_kpis(
        db: Session,
        academic_year_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Gathers real institutional KPIs across all active modules.
        Returns exact 0 / 0.0 values when database tables are empty (never fake fallbacks).
        """
        today = date.today()

        # 1. Students
        stu_q = db.query(Student).filter(Student.is_deleted == False)  # noqa: E712
        if academic_year_id:
            stu_q = stu_q.filter(Student.academic_year_id == academic_year_id)
        students = stu_q.all()
        total_students = len(students)
        active_students = sum(1 for s in students if (s.status or "").strip().lower() == "active")
        inactive_or_other_students = max(0, total_students - active_students)
        male_students = sum(1 for s in students if (s.gender or "").strip().lower() == "male")
        female_students = sum(1 for s in students if (s.gender or "").strip().lower() == "female")

        # 2. Faculty & Staff (Teachers + Non-Teaching Staff)
        teachers = db.query(Teacher).filter(Teacher.is_deleted == False).all()  # noqa: E712
        staff_list = db.query(Staff).filter(Staff.is_deleted == False).all()  # noqa: E712

        total_teachers = len(teachers)
        active_teachers = sum(1 for t in teachers if (t.status or "").strip().lower() == "active")
        total_non_teaching_staff = len(staff_list)
        active_non_teaching_staff = sum(1 for st in staff_list if (st.status or "").strip().lower() == "active")

        total_staff = total_teachers + total_non_teaching_staff
        active_staff = active_teachers + active_non_teaching_staff
        teaching_staff = total_teachers

        today_t_att = db.query(TeacherAttendance).filter(TeacherAttendance.date == today).all()
        teachers_present_today = sum(1 for a in today_t_att if a.status in ("Present", "Late"))
        teachers_leave_today = sum(1 for a in today_t_att if a.status in ("Leave", "Absent", "Excused"))

        # 3. Fees & Daily/Monthly Collections
        fee_q = db.query(StudentFee).filter(
            StudentFee.is_deleted == False,  # noqa: E712
            StudentFee.status != "Cancelled",
        )
        if academic_year_id:
            fee_q = fee_q.filter(StudentFee.academic_year_id == academic_year_id)
        if start_date:
            fee_q = fee_q.filter(StudentFee.due_date >= start_date)
        if end_date:
            fee_q = fee_q.filter(StudentFee.due_date <= end_date)
        invoices = fee_q.all()

        total_invoiced = sum(float(inv.net_amount if inv.net_amount is not None else inv.total_amount or 0.0) for inv in invoices)
        total_collected = sum(float(inv.paid_amount or 0.0) for inv in invoices)
        total_dues = sum(float(inv.due_amount or 0.0) for inv in invoices)
        collection_efficiency = (total_collected / total_invoiced * 100.0) if total_invoiced > 0 else 0.0
        defaulters_count = sum(1 for inv in invoices if float(inv.due_amount or 0.0) > 0.0)

        pay_q = db.query(FeePayment).filter(
            FeePayment.is_deleted == False,  # noqa: E712
            FeePayment.status.in_(["Completed", "Partially Refunded"]),
        )
        if academic_year_id:
            pay_q = pay_q.join(StudentFee, FeePayment.student_fee_id == StudentFee.id).filter(
                StudentFee.academic_year_id == academic_year_id
            )
        all_payments = pay_q.all()
        today_collections = sum(
            float(p.amount_paid or 0.0) for p in all_payments if p.payment_date == today
        )
        month_collections = sum(
            float(p.amount_paid or 0.0)
            for p in all_payments
            if p.payment_date and p.payment_date.year == today.year and p.payment_date.month == today.month
        )

        # 4. Accounting
        tx_q = db.query(AccountTransaction).filter(
            AccountTransaction.is_deleted == False,  # noqa: E712
            AccountTransaction.status.notin_(["Voided", "Cancelled"]),
        )
        if academic_year_id:
            tx_q = tx_q.filter(AccountTransaction.academic_year_id == academic_year_id)
        if start_date:
            tx_q = tx_q.filter(AccountTransaction.transaction_date >= start_date)
        if end_date:
            tx_q = tx_q.filter(AccountTransaction.transaction_date <= end_date)
        txns = tx_q.all()

        total_income = sum(float(t.amount or 0.0) for t in txns if t.type == "Income")
        total_expenses = sum(float(t.amount or 0.0) for t in txns if t.type == "Expense")
        net_surplus = total_income - total_expenses

        # 5. Payroll
        slip_q = db.query(PayrollPayslip).filter(
            PayrollPayslip.is_deleted == False,  # noqa: E712
            PayrollPayslip.is_reversed == False,  # noqa: E712
        )
        if academic_year_id:
            slip_q = slip_q.join(PayrollPeriodRun, PayrollPayslip.payroll_run_id == PayrollPeriodRun.id).filter(
                PayrollPeriodRun.academic_year_id == academic_year_id
            )
        payslips = slip_q.all()
        total_payroll_net = sum(float(ps.net_payable or 0.0) for ps in payslips)
        total_payroll_paid = sum(float(ps.net_payable or 0.0) for ps in payslips if ps.payment_status == "Paid")

        # 6. Student Attendance (overall + today)
        att_q = db.query(StudentAttendance)
        if academic_year_id:
            att_q = att_q.filter(StudentAttendance.academic_year_id == academic_year_id)
        if start_date:
            att_q = att_q.filter(StudentAttendance.date >= start_date)
        if end_date:
            att_q = att_q.filter(StudentAttendance.date <= end_date)
        attendances = att_q.all()

        total_att_records = len(attendances)
        present_count = sum(1 for a in attendances if a.status in ("Present", "Late"))
        attendance_rate = (present_count / total_att_records * 100.0) if total_att_records > 0 else 0.0

        today_att = [a for a in attendances if a.date == today]
        today_att_total = len(today_att)
        today_att_present = sum(1 for a in today_att if a.status in ("Present", "Late"))
        today_att_absent = sum(1 for a in today_att if a.status == "Absent")
        today_att_rate = (today_att_present / today_att_total * 100.0) if today_att_total > 0 else 0.0

        # 7. Exams & Academics
        term_q = db.query(ExamTerm).filter(ExamTerm.is_deleted == False)  # noqa: E712
        if academic_year_id:
            term_q = term_q.filter(ExamTerm.academic_year_id == academic_year_id)
        exam_terms = term_q.count()

        sum_q = db.query(ExamResultSummary).filter(ExamResultSummary.is_deleted == False)  # noqa: E712
        if academic_year_id:
            sum_q = sum_q.join(ExamTerm, ExamResultSummary.exam_term_id == ExamTerm.id).filter(
                ExamTerm.academic_year_id == academic_year_id
            )
        summaries = sum_q.all()
        total_assessed = len(summaries)
        passed_count = sum(1 for s in summaries if bool(s.passed_all))
        pass_rate = (passed_count / total_assessed * 100.0) if total_assessed > 0 else 0.0
        avg_gpa = (sum(float(s.gpa or 0.0) for s in summaries) / total_assessed) if total_assessed > 0 else 0.0

        # 8. Facilities: Library, Transport, Hostel, Inventory
        total_books = db.query(Book).filter(Book.is_deleted == False).count()  # noqa: E712
        active_loans = db.query(BookCirculation).filter(
            BookCirculation.is_deleted == False,  # noqa: E712
            BookCirculation.status.in_(["Issued", "Renewed", "Overdue"]),
        ).count()
        unpaid_library_fines = float(
            db.query(func.sum(LibraryFine.amount - LibraryFine.paid_amount - LibraryFine.waived_amount))
            .filter(LibraryFine.is_deleted == False, LibraryFine.status.in_(["Unpaid", "Partial"]))  # noqa: E712
            .scalar()
            or 0.0
        )

        total_routes = db.query(TransportRoute).filter(TransportRoute.is_deleted == False).count()  # noqa: E712
        total_vehicles = db.query(Vehicle).filter(Vehicle.is_deleted == False).count()  # noqa: E712
        transport_passengers = db.query(TransportPassenger).filter(
            TransportPassenger.is_deleted == False,  # noqa: E712
            TransportPassenger.status == "Active",
        ).count()

        hostel_capacity = int(
            db.query(func.sum(HostelRoom.capacity))
            .filter(HostelRoom.is_deleted == False)  # noqa: E712
            .scalar()
            or 0
        )
        hostel_occupancy = db.query(HostelAllocation).filter(
            HostelAllocation.is_deleted == False,  # noqa: E712
            HostelAllocation.status == "Active",
        ).count()
        hostel_occupancy_rate = (hostel_occupancy / hostel_capacity * 100.0) if hostel_capacity > 0 else 0.0

        inv_items = db.query(InventoryItem).filter(InventoryItem.is_deleted == False).all()  # noqa: E712
        inventory_items_count = len(inv_items)
        low_stock_count = sum(1 for it in inv_items if it.is_low_stock)
        inventory_stock_value = sum(
            float(it.quantity_in_stock or 0) * float(it.unit_cost or 0.0) for it in inv_items
        )
        fixed_assets_count = db.query(FixedAsset).filter(FixedAsset.is_deleted == False).count()  # noqa: E712

        return {
            "total_students": total_students,
            "active_students": active_students,
            "inactive_or_other_students": inactive_or_other_students,
            "male_students": male_students,
            "female_students": female_students,
            "total_teachers": total_teachers,
            "active_teachers": active_teachers,
            "teachers_present_today": teachers_present_today,
            "teachers_leave_today": teachers_leave_today,
            "total_non_teaching_staff": total_non_teaching_staff,
            "active_non_teaching_staff": active_non_teaching_staff,
            "total_staff": total_staff,
            "active_staff": active_staff,
            "teaching_staff": teaching_staff,
            "total_invoiced": round(total_invoiced, 2),
            "total_collected": round(total_collected, 2),
            "total_dues": round(total_dues, 2),
            "today_collections": round(today_collections, 2),
            "month_collections": round(month_collections, 2),
            "collection_efficiency": round(collection_efficiency, 2),
            "defaulters_count": defaulters_count,
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net_surplus": round(net_surplus, 2),
            "total_payroll_net": round(total_payroll_net, 2),
            "total_payroll_paid": round(total_payroll_paid, 2),
            "total_att_records": total_att_records,
            "attendance_rate": round(attendance_rate, 2),
            "today_att_total": today_att_total,
            "today_att_present": today_att_present,
            "today_att_absent": today_att_absent,
            "today_att_rate": round(today_att_rate, 2),
            "exam_terms_count": exam_terms,
            "total_assessed": total_assessed,
            "pass_rate": round(pass_rate, 2),
            "avg_gpa": round(avg_gpa, 2),
            "total_books": total_books,
            "active_loans": active_loans,
            "unpaid_library_fines": round(max(0.0, unpaid_library_fines), 2),
            "total_routes": total_routes,
            "total_vehicles": total_vehicles,
            "transport_passengers": transport_passengers,
            "hostel_capacity": hostel_capacity,
            "hostel_occupancy": hostel_occupancy,
            "hostel_occupancy_rate": round(hostel_occupancy_rate, 2),
            "inventory_items_count": inventory_items_count,
            "low_stock_count": low_stock_count,
            "inventory_stock_value": round(inventory_stock_value, 2),
            "fixed_assets_count": fixed_assets_count,
        }

    @staticmethod
    def get_dashboard_analytics(
        db: Session,
        academic_year_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Builds structured, strictly database-driven chart series & analytics breakdowns
        for DashboardPage and ReportsPage. Empty queries return empty lists (never fake bars).
        """
        kpis = AnalyticsService.get_executive_kpis(
            db,
            academic_year_id=academic_year_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Chart 1: Student Enrollment by Class
        stu_q = db.query(Student).filter(Student.is_deleted == False)  # noqa: E712
        if academic_year_id:
            stu_q = stu_q.filter(Student.academic_year_id == academic_year_id)
        class_counts: Dict[str, int] = defaultdict(int)
        class_order: Dict[str, int] = {}
        for st in stu_q.all():
            cname = st.school_class.name if st.school_class else "Unassigned"
            class_counts[cname] += 1
            if st.school_class:
                class_order[cname] = int(st.school_class.numeric_order or 999)
            else:
                class_order[cname] = 9999
        enrollment_by_class = [
            {"label": cname, "value": count}
            for cname, count in sorted(class_counts.items(), key=lambda kv: (class_order.get(kv[0], 999), kv[0]))
        ]

        # Chart 2: Monthly Financial Cashflow (Income vs Expense from AccountTransaction)
        tx_q = db.query(AccountTransaction).filter(
            AccountTransaction.is_deleted == False,  # noqa: E712
            AccountTransaction.status.notin_(["Voided", "Cancelled"]),
        )
        if academic_year_id:
            tx_q = tx_q.filter(AccountTransaction.academic_year_id == academic_year_id)
        if start_date:
            tx_q = tx_q.filter(AccountTransaction.transaction_date >= start_date)
        if end_date:
            tx_q = tx_q.filter(AccountTransaction.transaction_date <= end_date)
        monthly_fin: Dict[str, Dict[str, float]] = defaultdict(lambda: {"Income": 0.0, "Expense": 0.0})
        for tx in tx_q.all():
            mk = _month_key(tx.transaction_date)
            if tx.type == "Income":
                monthly_fin[mk]["Income"] += float(tx.amount or 0.0)
            elif tx.type == "Expense":
                monthly_fin[mk]["Expense"] += float(tx.amount or 0.0)
        finance_monthly_series = [
            {
                "label": mk,
                "primary": round(vals["Income"], 2),
                "secondary": round(vals["Expense"], 2),
            }
            for mk, vals in sorted(monthly_fin.items())[-8:]
        ]

        # Chart 3: Attendance Status Distribution
        att_q = db.query(StudentAttendance)
        if academic_year_id:
            att_q = att_q.filter(StudentAttendance.academic_year_id == academic_year_id)
        if start_date:
            att_q = att_q.filter(StudentAttendance.date >= start_date)
        if end_date:
            att_q = att_q.filter(StudentAttendance.date <= end_date)
        att_buckets: Dict[str, int] = defaultdict(int)
        for a in att_q.all():
            att_buckets[a.status or "Unknown"] += 1
        attendance_distribution = [
            {"label": status, "value": att_buckets[status]}
            for status in ("Present", "Absent", "Late", "Leave", "Excused")
            if att_buckets.get(status, 0) > 0
        ]

        # Chart 4: Fee Billed vs Collected by Fee Category
        fee_q = db.query(StudentFee).filter(
            StudentFee.is_deleted == False,  # noqa: E712
            StudentFee.status != "Cancelled",
        )
        if academic_year_id:
            fee_q = fee_q.filter(StudentFee.academic_year_id == academic_year_id)
        if start_date:
            fee_q = fee_q.filter(StudentFee.due_date >= start_date)
        if end_date:
            fee_q = fee_q.filter(StudentFee.due_date <= end_date)
        fee_by_cat: Dict[str, Dict[str, float]] = defaultdict(lambda: {"Billed": 0.0, "Collected": 0.0})
        for sf in fee_q.all():
            cat_name = (
                sf.fee_structure.category.name
                if sf.fee_structure and sf.fee_structure.category
                else "General Fee"
            )
            fee_by_cat[cat_name]["Billed"] += float(sf.net_amount if sf.net_amount is not None else sf.total_amount or 0.0)
            fee_by_cat[cat_name]["Collected"] += float(sf.paid_amount or 0.0)
        fee_collection_by_category = [
            {
                "label": cname,
                "primary": round(vals["Billed"], 2),
                "secondary": round(vals["Collected"], 2),
            }
            for cname, vals in sorted(fee_by_cat.items())
        ]

        # Chart 5: Exam Grade Distribution
        sum_q = db.query(ExamResultSummary).filter(ExamResultSummary.is_deleted == False)  # noqa: E712
        if academic_year_id:
            sum_q = sum_q.join(ExamTerm, ExamResultSummary.exam_term_id == ExamTerm.id).filter(
                ExamTerm.academic_year_id == academic_year_id
            )
        grade_counts: Dict[str, int] = defaultdict(int)
        for s in sum_q.all():
            grade_counts[s.overall_grade or "N/A"] += 1
        grade_order = ["A+", "A", "A-", "B+", "B", "C", "D", "F"]
        exam_grade_distribution = [
            {"label": g, "value": grade_counts[g]}
            for g in grade_order
            if grade_counts.get(g, 0) > 0
        ]
        for g, cnt in sorted(grade_counts.items()):
            if g not in grade_order and cnt > 0:
                exam_grade_distribution.append({"label": g, "value": cnt})

        # Chart 6: Monthly Payroll Disbursement Totals
        slip_q = db.query(PayrollPayslip).filter(
            PayrollPayslip.is_deleted == False,  # noqa: E712
            PayrollPayslip.is_reversed == False,  # noqa: E712
        )
        if academic_year_id:
            slip_q = slip_q.join(PayrollPeriodRun, PayrollPayslip.payroll_run_id == PayrollPeriodRun.id).filter(
                PayrollPeriodRun.academic_year_id == academic_year_id
            )
        payroll_by_month: Dict[str, float] = defaultdict(float)
        for ps in slip_q.all():
            ym = f"{ps.payroll_year:04d}-{ps.payroll_month:02d}"
            payroll_by_month[ym] += float(ps.net_payable or 0.0)
        payroll_monthly_series = [
            {"label": ym, "value": round(val, 2)}
            for ym, val in sorted(payroll_by_month.items())[-8:]
        ]

        return {
            "kpis": kpis,
            "enrollment_by_class": enrollment_by_class,
            "finance_monthly_series": finance_monthly_series,
            "attendance_distribution": attendance_distribution,
            "fee_collection_by_category": fee_collection_by_category,
            "exam_grade_distribution": exam_grade_distribution,
            "payroll_monthly_series": payroll_monthly_series,
        }

    @staticmethod
    def get_fee_defaulters(
        db: Session,
        class_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves list of students with outstanding fee arrears and overdue invoices.
        """
        query = (
            db.query(StudentFee)
            .join(Student, StudentFee.student_id == Student.id)
            .filter(
                StudentFee.is_deleted == False,  # noqa: E712
                StudentFee.status != "Cancelled",
                StudentFee.due_amount > 0,
            )
        )
        if class_id:
            query = query.filter(Student.class_id == class_id)
        if academic_year_id:
            query = query.filter(StudentFee.academic_year_id == academic_year_id)

        invoices = query.order_by(StudentFee.due_date.asc()).all()
        defaulters = []
        today = date.today()

        for inv in invoices:
            student = inv.student
            cls_name = student.school_class.name if student and student.school_class else "N/A"
            sec_name = student.section.name if student and student.section else "N/A"
            g_phone = (
                student.guardian.guardian_phone
                if student and student.guardian
                else (student.emergency_contact if student and student.emergency_contact else "N/A")
            )
            days_overdue = (today - inv.due_date).days if inv.due_date and inv.due_date < today else 0

            defaulters.append({
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "student_id": student.id if student else None,
                "student_name": student.full_name if student else "Unknown",
                "admission_number": student.admission_number if student else "N/A",
                "class_section": f"{cls_name} - {sec_name}",
                "guardian_phone": g_phone,
                "title": inv.display_title,
                "total_amount": float(inv.net_amount if inv.net_amount is not None else inv.total_amount or 0.0),
                "paid_amount": float(inv.paid_amount or 0.0),
                "due_amount": float(inv.due_amount or 0.0),
                "due_date": inv.due_date.strftime("%Y-%m-%d") if inv.due_date else "N/A",
                "days_overdue": max(0, days_overdue),
                "status": inv.status,
            })
        return defaulters

    @staticmethod
    def get_attendance_analytics(
        db: Session,
        academic_year_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Calculates class-wise attendance rates strictly from StudentAttendance records.
        """
        stu_q = db.query(Student).filter(Student.is_deleted == False)  # noqa: E712
        if academic_year_id:
            stu_q = stu_q.filter(Student.academic_year_id == academic_year_id)
        students = stu_q.all()
        active_students = [s for s in students if (s.status or "").strip().lower() == "active"]

        att_q = db.query(StudentAttendance)
        if academic_year_id:
            att_q = att_q.filter(StudentAttendance.academic_year_id == academic_year_id)
        if start_date:
            att_q = att_q.filter(StudentAttendance.date >= start_date)
        if end_date:
            att_q = att_q.filter(StudentAttendance.date <= end_date)
        records = att_q.all()

        class_stats: Dict[str, Dict[str, int]] = {}
        for r in records:
            cname = r.school_class.name if r.school_class else "Unassigned"
            if cname not in class_stats:
                class_stats[cname] = {"total_records": 0, "present": 0, "absent": 0, "late": 0, "leave_excused": 0}
            class_stats[cname]["total_records"] += 1
            if r.status == "Present":
                class_stats[cname]["present"] += 1
            elif r.status == "Late":
                class_stats[cname]["late"] += 1
            elif r.status == "Absent":
                class_stats[cname]["absent"] += 1
            else:
                class_stats[cname]["leave_excused"] += 1

        class_summary = []
        for cname, counts in sorted(class_stats.items()):
            tot = counts["total_records"]
            effective_present = counts["present"] + counts["late"]
            rate = (effective_present / tot * 100.0) if tot > 0 else 0.0
            class_summary.append({
                "class_name": cname,
                "total_records": tot,
                "present_count": counts["present"],
                "absent_count": counts["absent"],
                "late_count": counts["late"],
                "leave_excused_count": counts["leave_excused"],
                "attendance_percentage": round(rate, 2),
            })

        return {
            "class_summary": class_summary,
            "overall_recorded_students": len(active_students),
        }

    @staticmethod
    def export_master_school_report_excel(
        db: Session,
        output_path: str,
        academic_year_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> str:
        """
        Exports a multi-sheet master institutional Excel workbook using openpyxl.
        """
        try:
            import openpyxl
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            raise RuntimeError("openpyxl is required to generate Excel workbooks.")

        wb = openpyxl.Workbook()

        title_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        title_font = Font(name="Calibri", size=15, bold=True, color="FFFFFF")

        header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )

        # SHEET 1: Executive Summary
        ws1 = wb.active
        ws1.title = "Executive Summary"
        ws1.views.sheetView[0].showGridLines = True

        school = db.query(SchoolSetting).first()
        school_name = school.school_name if school else "EduManage Pro Model Academy"
        eiin = school.eiin_number if school else "N/A"

        ws1.merge_cells("A1:F2")
        ws1["A1"] = f"{school_name} - Executive Performance Audit"
        ws1["A1"].font = title_font
        ws1["A1"].fill = title_fill
        ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

        ws1["A3"] = f"EIIN: {eiin} | Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Real DB Audit"
        ws1["A3"].font = Font(italic=True, color="64748B")

        kpis = AnalyticsService.get_executive_kpis(
            db, academic_year_id=academic_year_id, start_date=start_date, end_date=end_date
        )

        ws1.append([])
        ws1.append(["Metric Category", "Indicator", "Value", "Operational Status", "Benchmark Target", "Variance"])
        for col in range(1, 7):
            cell = ws1.cell(row=5, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center" if col > 2 else "left")

        summary_rows = [
            ("Demographics", "Total Enrolled Students", kpis["total_students"], "Recorded", "-", "-"),
            ("Demographics", "Active Students", kpis["active_students"], "Active", "-", "-"),
            ("Demographics", "Total Faculty & Staff", kpis["total_staff"], "Recorded", "-", "-"),
            ("Finance", "Total Fees Billed", f"{kpis['total_invoiced']:,.2f}", "Audited", "-", "-"),
            ("Finance", "Total Fees Realized", f"{kpis['total_collected']:,.2f}", "Collected", "-", "-"),
            ("Finance", "Fee Collection Efficiency", f"{kpis['collection_efficiency']}%", "Healthy" if kpis["collection_efficiency"] >= 80 else "Attention", "85.0%", "-"),
            ("Finance", "Net Operating Surplus", f"{kpis['net_surplus']:,.2f}", "Positive" if kpis["net_surplus"] >= 0 else "Deficit", ">= 0", "-"),
            ("Payroll", "Total Net Payroll Processed", f"{kpis['total_payroll_net']:,.2f}", "Processed", "-", "-"),
            ("Academic", "Student Overall Attendance", f"{kpis['attendance_rate']}%", "Compliant" if kpis["attendance_rate"] >= 75 else "Attention", "90.0%", "-"),
            ("Academic", "Examination Pass Rate", f"{kpis['pass_rate']}%", "Audited", "90.0%", "-"),
            ("Academic", "Institutional Average GPA", f"{kpis['avg_gpa']} / 5.00", "Audited", "3.50", "-"),
            ("Facilities", "Library Active Borrowings", f"{kpis['active_loans']} of {kpis['total_books']} titles", "Live", "-", "-"),
            ("Facilities", "Transport Enrolled Commuters", f"{kpis['transport_passengers']} passengers", "Live", "-", "-"),
            ("Facilities", "Hostel Bed Occupancy Rate", f"{kpis['hostel_occupancy_rate']}% ({kpis['hostel_occupancy']}/{kpis['hostel_capacity']})", "Live", "-", "-"),
            ("Inventory", "Stock Items & Low Stock Alerts", f"{kpis['inventory_items_count']} items ({kpis['low_stock_count']} low stock)", "Live", "0 Low", "-"),
        ]

        for r_idx, row_data in enumerate(summary_rows, start=6):
            ws1.append(list(row_data))
            for c_idx in range(1, 7):
                c = ws1.cell(row=r_idx, column=c_idx)
                c.border = thin_border
                if c_idx in (3, 4, 5, 6):
                    c.alignment = Alignment(horizontal="center")

        # SHEET 2: Student Demographics
        ws2 = wb.create_sheet(title="Student Demographics")
        ws2.views.sheetView[0].showGridLines = True

        ws2.append(["ID", "Admission No", "Full Name", "Class", "Section", "Roll", "Gender", "Date of Birth", "Blood Group", "Guardian Phone", "Status"])
        for col in range(1, 12):
            cell = ws2.cell(row=1, column=col)
            cell.font = header_font
            cell.fill = header_fill

        stu_q = db.query(Student).filter(Student.is_deleted == False)  # noqa: E712
        if academic_year_id:
            stu_q = stu_q.filter(Student.academic_year_id == academic_year_id)
        for st in stu_q.order_by(Student.admission_number).all():
            cls_name = st.school_class.name if st.school_class else "N/A"
            sec_name = st.section.name if st.section else "N/A"
            g_phone = st.guardian.guardian_phone if st.guardian else (st.emergency_contact or "N/A")
            ws2.append([
                st.id,
                st.admission_number,
                st.full_name,
                cls_name,
                sec_name,
                st.roll_number if st.roll_number is not None else "N/A",
                st.gender or "N/A",
                st.date_of_birth.strftime("%Y-%m-%d") if st.date_of_birth else "N/A",
                st.blood_group or "N/A",
                g_phone,
                st.status,
            ])
            for col in range(1, 12):
                ws2.cell(row=ws2.max_row, column=col).border = thin_border

        # SHEET 3: Fee Defaulters & Arrears
        ws3 = wb.create_sheet(title="Fee Defaulters")
        ws3.views.sheetView[0].showGridLines = True

        ws3.append(["Invoice No", "Admission No", "Student Name", "Class & Section", "Invoice Title", "Billed", "Paid", "Outstanding Due", "Due Date", "Days Overdue", "Status", "Guardian Contact"])
        for col in range(1, 13):
            cell = ws3.cell(row=1, column=col)
            cell.font = header_font
            cell.fill = header_fill

        for d in AnalyticsService.get_fee_defaulters(db, academic_year_id=academic_year_id):
            ws3.append([
                d["invoice_number"],
                d["admission_number"],
                d["student_name"],
                d["class_section"],
                d["title"],
                d["total_amount"],
                d["paid_amount"],
                d["due_amount"],
                d["due_date"],
                d["days_overdue"],
                d["status"],
                d["guardian_phone"],
            ])
            for col in range(1, 13):
                cell = ws3.cell(row=ws3.max_row, column=col)
                cell.border = thin_border
                if col in (6, 7, 8):
                    cell.number_format = "#,##0.00"

        # SHEET 4: Attendance Analytics
        ws4 = wb.create_sheet(title="Attendance Analytics")
        ws4.views.sheetView[0].showGridLines = True

        ws4.append(["Class / Grade", "Total Recorded Sessions", "Present Count", "Absent Count", "Late Count", "Attendance Percentage (%)", "Compliance Evaluation"])
        for col in range(1, 8):
            cell = ws4.cell(row=1, column=col)
            cell.font = header_font
            cell.fill = header_fill

        att_data = AnalyticsService.get_attendance_analytics(
            db, academic_year_id=academic_year_id, start_date=start_date, end_date=end_date
        )
        for row in att_data["class_summary"]:
            rate = row["attendance_percentage"]
            evaluation = "Excellent (>=90%)" if rate >= 90 else ("Satisfactory (>=75%)" if rate >= 75 else "Critical (<75%)")
            ws4.append([
                row["class_name"],
                row["total_records"],
                row["present_count"],
                row["absent_count"],
                row["late_count"],
                f"{rate}%",
                evaluation,
            ])
            for col in range(1, 8):
                ws4.cell(row=ws4.max_row, column=col).border = thin_border

        # Auto-adjust column widths
        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value is not None:
                        max_len = max(max_len, len(str(cell.value)))
                sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb.save(output_path)
        return output_path

    @staticmethod
    def export_defaulters_csv(db: Session, output_path: str, academic_year_id: Optional[int] = None) -> str:
        """
        Exports CSV list of fee defaulters with contact numbers.
        """
        defaulters = AnalyticsService.get_fee_defaulters(db, academic_year_id=academic_year_id)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Invoice Number",
                "Admission Number",
                "Student Name",
                "Class & Section",
                "Invoice Description",
                "Billed Amount",
                "Paid Amount",
                "Due Amount",
                "Due Date",
                "Days Overdue",
                "Status",
                "Guardian Phone",
            ])
            for d in defaulters:
                writer.writerow([
                    d["invoice_number"],
                    d["admission_number"],
                    d["student_name"],
                    d["class_section"],
                    d["title"],
                    f"{d['total_amount']:.2f}",
                    f"{d['paid_amount']:.2f}",
                    f"{d['due_amount']:.2f}",
                    d["due_date"],
                    d["days_overdue"],
                    d["status"],
                    d["guardian_phone"],
                ])
        return output_path

    @staticmethod
    def export_students_csv(db: Session, output_path: str, academic_year_id: Optional[int] = None) -> str:
        """
        Exports master CSV roster of students.
        """
        q = db.query(Student).filter(Student.is_deleted == False)  # noqa: E712
        if academic_year_id:
            q = q.filter(Student.academic_year_id == academic_year_id)
        students = q.order_by(Student.admission_number).all()

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Student ID",
                "Admission Number",
                "First Name",
                "Last Name",
                "Class",
                "Section",
                "Roll",
                "Gender",
                "Birth Date",
                "Guardian Phone",
                "Status",
            ])
            for st in students:
                cls_name = st.school_class.name if st.school_class else ""
                sec_name = st.section.name if st.section else ""
                g_phone = st.guardian.guardian_phone if st.guardian else (st.emergency_contact or "")
                writer.writerow([
                    st.student_id or st.id,
                    st.admission_number,
                    st.first_name,
                    st.last_name,
                    cls_name,
                    sec_name,
                    st.roll_number if st.roll_number is not None else "",
                    st.gender or "",
                    st.date_of_birth.strftime("%Y-%m-%d") if st.date_of_birth else "",
                    g_phone,
                    st.status,
                ])
        return output_path
