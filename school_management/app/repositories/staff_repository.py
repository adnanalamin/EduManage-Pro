"""
EduManage Pro - Teacher & Staff Repository
Data access layer for faculty members, administrative staff, and departments.
"""

from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc, asc, func
from app.models.staff import Teacher, Staff, Department


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
        return db.query(Teacher).options(joinedload(Teacher.department)).filter(Teacher.id == teacher_pk).first()

    @staticmethod
    def search_and_filter_teachers(
        db: Session,
        search_query: Optional[str] = None,
        department_id: Optional[int] = None,
        gender: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 25
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
                    Teacher.primary_subject.ilike(term)
                )
            )

        if department_id:
            query = query.filter(Teacher.department_id == department_id)
        if gender:
            query = query.filter(Teacher.gender == gender)
        if status:
            query = query.filter(Teacher.status == status)

        total_count = query.count()
        offset = (page - 1) * per_page
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
        return db.query(Staff).options(joinedload(Staff.department)).filter(Staff.id == staff_pk).first()

    @staticmethod
    def search_and_filter_staff(
        db: Session,
        search_query: Optional[str] = None,
        department_id: Optional[int] = None,
        position: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 25
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
                    Staff.position.ilike(term)
                )
            )

        if department_id:
            query = query.filter(Staff.department_id == department_id)
        if position:
            query = query.filter(Staff.position == position)
        if status:
            query = query.filter(Staff.status == status)

        total_count = query.count()
        offset = (page - 1) * per_page
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

    # --- Aggregates ---
    @staticmethod
    def get_overview_statistics(db: Session) -> Dict[str, Any]:
        teacher_base = db.query(Teacher).filter(Teacher.is_deleted == False)
        staff_base = db.query(Staff).filter(Staff.is_deleted == False)
        teacher_count = teacher_base.count()
        active_teachers = teacher_base.filter(Teacher.status == "active").count()
        staff_count = staff_base.count()
        active_staff = staff_base.filter(Staff.status == "active").count()
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
            "monthly_payroll": total_payroll
        }
