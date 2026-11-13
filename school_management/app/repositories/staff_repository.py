"""
EduManage Pro - Teacher, Staff & HR Repository
Data access layer for faculty, non-teaching personnel, departments, HR attendance,
leave queues, contracts, and unified employee searches.
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import StaffAttendance, TeacherAttendance
from app.models.staff import (
    Department,
    EmployeeContract,
    EmployeeLeaveRequest,
    EmployeePerformanceEvaluation,
    Staff,
    Teacher,
    TeacherSubjectAssignment,
)


class StaffRepository:
    # --- Department Operations ---
    @staticmethod
    def get_or_create_departments(db: Session) -> List[Department]:
        standard_depts = [
            ("Science", "SCI", "Physics, Chemistry, Biology"),
            ("Mathematics", "MATH", "General and Higher Mathematics"),
            ("Humanities", "HUM", "History, Geography, Civics"),
            ("Business Studies", "BUS", "Accounting, Finance, Management"),
            ("Languages", "LANG", "Bangla, English, Arabic"),
            ("ICT & Computer Science", "ICT", "Computer and Information Technology"),
            ("Administration & Accounts", "ADMIN", "Accounts, HR, Office Operations"),
            ("Library & Support", "LIB", "Library circulation & Archive"),
            ("Security & Facilities", "SEC", "Campus security, Transport & Maintenance"),
        ]
        results = []
        for name, code, desc_txt in standard_depts:
            dept = db.query(Department).filter_by(code=code).first()
            if not dept:
                dept = Department(name=name, code=code, description=desc_txt)
                db.add(dept)
                db.flush()
            results.append(dept)
        db.commit()
        return results

    # --- Teacher Operations ---
    @staticmethod
    def get_teacher_by_id(db: Session, teacher_pk: int) -> Optional[Teacher]:
        return (
            db.query(Teacher)
            .options(joinedload(Teacher.department))
            .filter(Teacher.id == teacher_pk)
            .first()
        )

    @staticmethod
    def search_and_filter_teachers(
        db: Session,
        search_query: Optional[str] = None,
        department_id: Optional[int] = None,
        gender: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[Teacher], int]:
        query = db.query(Teacher).options(joinedload(Teacher.department)).filter(Teacher.is_deleted == False)

        if search_query and search_query.strip():
            term = f"%{search_query.strip()}%"
            query = query.filter(
                or_(
                    Teacher.full_name.ilike(term),
                    Teacher.teacher_id.ilike(term),
                    Teacher.employee_id.ilike(term),
                    Teacher.phone.ilike(term),
                    Teacher.email.ilike(term),
                    Teacher.primary_subject.ilike(term),
                    Teacher.designation.ilike(term),
                )
            )

        if department_id:
            query = query.filter(Teacher.department_id == department_id)
        if gender:
            query = query.filter(Teacher.gender == gender)
        if status:
            query = query.filter(Teacher.status == status)

        total_count = query.count()
        offset = max(0, (page - 1) * per_page)
        items = query.order_by(asc(Teacher.full_name)).offset(offset).limit(per_page).all()
        return items, total_count

    @staticmethod
    def create_teacher(db: Session, teacher_data: Dict[str, Any]) -> Teacher:
        teacher = Teacher(**teacher_data)
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
        return teacher

    @staticmethod
    def update_teacher(db: Session, teacher: Teacher, teacher_data: Dict[str, Any]) -> Teacher:
        for k, v in teacher_data.items():
            setattr(teacher, k, v)
        db.commit()
        db.refresh(teacher)
        return teacher

    # --- Staff Operations ---
    @staticmethod
    def get_staff_by_id(db: Session, staff_pk: int) -> Optional[Staff]:
        return (
            db.query(Staff)
            .options(joinedload(Staff.department))
            .filter(Staff.id == staff_pk)
            .first()
        )

    @staticmethod
    def search_and_filter_staff(
        db: Session,
        search_query: Optional[str] = None,
        department_id: Optional[int] = None,
        position: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[Staff], int]:
        query = db.query(Staff).options(joinedload(Staff.department)).filter(Staff.is_deleted == False)

        if search_query and search_query.strip():
            term = f"%{search_query.strip()}%"
            query = query.filter(
                or_(
                    Staff.full_name.ilike(term),
                    Staff.staff_id.ilike(term),
                    Staff.employee_id.ilike(term),
                    Staff.phone.ilike(term),
                    Staff.position.ilike(term),
                )
            )

        if department_id:
            query = query.filter(Staff.department_id == department_id)
        if position:
            query = query.filter(Staff.position == position)
        if status:
            query = query.filter(Staff.status == status)

        total_count = query.count()
        offset = max(0, (page - 1) * per_page)
        items = query.order_by(asc(Staff.full_name)).offset(offset).limit(per_page).all()
        return items, total_count

    @staticmethod
    def create_staff(db: Session, staff_data: Dict[str, Any]) -> Staff:
        staff_member = Staff(**staff_data)
        db.add(staff_member)
        db.commit()
        db.refresh(staff_member)
        return staff_member

    @staticmethod
    def update_staff(db: Session, staff_member: Staff, staff_data: Dict[str, Any]) -> Staff:
        for k, v in staff_data.items():
            setattr(staff_member, k, v)
        db.commit()
        db.refresh(staff_member)
        return staff_member

    # --- Unified HR Queries ---
    @staticmethod
    def get_employee(db: Session, employee_type: str, employee_pk: int):
        etype = (employee_type or "").strip().lower()
        if etype == "teacher":
            return StaffRepository.get_teacher_by_id(db, employee_pk)
        if etype == "staff":
            return StaffRepository.get_staff_by_id(db, employee_pk)
        raise ValueError(f"Unsupported employee_type '{employee_type}'. Must be 'teacher' or 'staff'.")

    @staticmethod
    def list_leave_requests(
        db: Session,
        status: Optional[str] = None,
        employee_type: Optional[str] = None,
        teacher_id: Optional[int] = None,
        staff_id: Optional[int] = None,
    ) -> List[EmployeeLeaveRequest]:
        query = db.query(EmployeeLeaveRequest).options(
            joinedload(EmployeeLeaveRequest.teacher),
            joinedload(EmployeeLeaveRequest.staff),
        )
        if status:
            query = query.filter(EmployeeLeaveRequest.status == status)
        if employee_type:
            query = query.filter(EmployeeLeaveRequest.employee_type == employee_type.lower())
        if teacher_id:
            query = query.filter(EmployeeLeaveRequest.teacher_id == teacher_id)
        if staff_id:
            query = query.filter(EmployeeLeaveRequest.staff_id == staff_id)
        return query.order_by(desc(EmployeeLeaveRequest.id)).all()

    @staticmethod
    def list_contracts(
        db: Session,
        status: Optional[str] = None,
        expiring_within_days: Optional[int] = None,
    ) -> List[EmployeeContract]:
        query = db.query(EmployeeContract).options(
            joinedload(EmployeeContract.teacher),
            joinedload(EmployeeContract.staff),
        )
        if status:
            query = query.filter(EmployeeContract.status == status)
        if expiring_within_days is not None:
            cutoff = date.today() + timedelta(days=expiring_within_days)
            query = query.filter(
                EmployeeContract.end_date.isnot(None),
                EmployeeContract.end_date <= cutoff,
            )
        return query.order_by(desc(EmployeeContract.start_date)).all()

    @staticmethod
    def list_evaluations(
        db: Session,
        employee_type: Optional[str] = None,
    ) -> List[EmployeePerformanceEvaluation]:
        query = db.query(EmployeePerformanceEvaluation).options(
            joinedload(EmployeePerformanceEvaluation.teacher),
            joinedload(EmployeePerformanceEvaluation.staff),
        )
        if employee_type:
            query = query.filter(EmployeePerformanceEvaluation.employee_type == employee_type.lower())
        return query.order_by(desc(EmployeePerformanceEvaluation.review_date)).all()

    @staticmethod
    def save_staff_attendance(
        db: Session,
        records: List[Dict[str, Any]],
        marked_by: str = "admin",
    ) -> int:
        saved = 0
        for rec in records:
            staff_id = rec["staff_id"]
            att_date = rec["date"]
            existing = (
                db.query(StaffAttendance)
                .filter(StaffAttendance.staff_id == staff_id, StaffAttendance.date == att_date)
                .first()
            )
            if existing:
                existing.status = rec.get("status", "Present")
                existing.check_in_time = rec.get("check_in_time")
                existing.check_out_time = rec.get("check_out_time")
                existing.remarks = rec.get("remarks")
                existing.marked_by = marked_by
            else:
                db.add(
                    StaffAttendance(
                        staff_id=staff_id,
                        date=att_date,
                        status=rec.get("status", "Present"),
                        check_in_time=rec.get("check_in_time"),
                        check_out_time=rec.get("check_out_time"),
                        remarks=rec.get("remarks"),
                        marked_by=marked_by,
                    )
                )
            saved += 1
        db.commit()
        return saved

    @staticmethod
    def get_staff_attendance_by_date(db: Session, att_date: date) -> Dict[int, StaffAttendance]:
        rows = db.query(StaffAttendance).filter(StaffAttendance.date == att_date).all()
        return {r.staff_id: r for r in rows}

    # --- Aggregates ---
    @staticmethod
    def get_overview_statistics(db: Session) -> Dict[str, Any]:
        teacher_base = db.query(Teacher).filter(Teacher.is_deleted == False)
        staff_base = db.query(Staff).filter(Staff.is_deleted == False)
        teacher_count = teacher_base.count()
        active_teachers = teacher_base.filter(Teacher.status == "active").count()
        staff_count = staff_base.count()
        active_staff = staff_base.filter(Staff.status == "active").count()
        pending_leaves = (
            db.query(EmployeeLeaveRequest).filter(EmployeeLeaveRequest.status == "Pending").count()
        )
        active_contracts = (
            db.query(EmployeeContract).filter(EmployeeContract.status == "Active").count()
        )
        total_payroll = (
            db.query(func.sum(Teacher.salary)).filter(Teacher.is_deleted == False).scalar() or 0
        ) + (
            db.query(func.sum(Staff.salary)).filter(Staff.is_deleted == False).scalar() or 0
        )

        return {
            "total_teachers": teacher_count,
            "active_teachers": active_teachers,
            "total_staff": staff_count,
            "active_staff": active_staff,
            "pending_leaves": pending_leaves,
            "active_contracts": active_contracts,
            "monthly_payroll": total_payroll,
        }
