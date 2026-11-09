"""
EduManage Pro - Student Repository
Encapsulates all database operations, filters, pagination, and queries for Student records.
"""

from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc, asc
from app.models.student import Student, Guardian, StudentStatus, StudentPromotionHistory
from app.models.academic import SchoolClass, Section, AcademicYear


class StudentRepository:
    @staticmethod
    def get_by_id(db: Session, student_pk: int) -> Optional[Student]:
        return db.query(Student).options(
            joinedload(Student.guardian),
            joinedload(Student.school_class),
            joinedload(Student.section),
            joinedload(Student.academic_year)
        ).filter(Student.id == student_pk).first()

    @staticmethod
    def get_by_student_id(db: Session, student_id: str) -> Optional[Student]:
        return db.query(Student).filter(Student.student_id == student_id).first()

    @staticmethod
    def get_by_admission_number(db: Session, admission_number: str) -> Optional[Student]:
        return db.query(Student).filter(Student.admission_number == admission_number).first()

    @staticmethod
    def search_and_filter(
        db: Session,
        search_query: Optional[str] = None,
        class_id: Optional[int] = None,
        section_id: Optional[int] = None,
        gender: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "roll_number",
        sort_order: str = "asc",
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[Student], int]:
        """
        Query students with full-text search, multiple filters, sorting, and pagination.
        Returns: (list_of_students, total_matching_count)
        """
        query = db.query(Student).options(
            joinedload(Student.guardian),
            joinedload(Student.school_class),
            joinedload(Student.section)
        )

        # Full-text search across identifiers, names, phone numbers
        if search_query and search_query.strip():
            term = f"%{search_query.strip()}%"
            query = query.filter(
                or_(
                    Student.full_name.ilike(term),
                    Student.student_id.ilike(term),
                    Student.admission_number.ilike(term),
                    Student.phone.ilike(term),
                    Student.email.ilike(term)
                )
            )

        if class_id:
            query = query.filter(Student.class_id == class_id)
        if section_id:
            query = query.filter(Student.section_id == section_id)
        if gender:
            query = query.filter(Student.gender == gender)
        if status:
            query = query.filter(Student.status == status)

        total_count = query.count()

        # Sorting
        sort_column = getattr(Student, sort_by, Student.roll_number)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Pagination
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()

        return items, total_count

    @staticmethod
    def create(db: Session, student_data: Dict[str, Any], guardian_data: Optional[Dict[str, Any]] = None) -> Student:
        guardian = None
        if guardian_data:
            guardian = Guardian(**guardian_data)
            db.add(guardian)
            db.flush()

        student = Student(**student_data)
        if guardian:
            student.guardian_id = guardian.id

        db.add(student)
        db.commit()
        db.refresh(student)
        return student

    @staticmethod
    def update(
        db: Session,
        student: Student,
        student_data: Dict[str, Any],
        guardian_data: Optional[Dict[str, Any]] = None
    ) -> Student:
        for key, value in student_data.items():
            setattr(student, key, value)

        if guardian_data:
            if student.guardian:
                for k, v in guardian_data.items():
                    setattr(student.guardian, k, v)
            else:
                new_guardian = Guardian(**guardian_data)
                db.add(new_guardian)
                db.flush()
                student.guardian_id = new_guardian.id

        db.commit()
        db.refresh(student)
        return student

    @staticmethod
    def archive_or_delete(db: Session, student: Student, soft_delete: bool = True) -> bool:
        if soft_delete:
            student.status = StudentStatus.INACTIVE
            db.commit()
        else:
            db.delete(student)
            db.commit()
        return True

    @staticmethod
    def bulk_promote(
        db: Session,
        student_ids: List[int],
        target_class_id: int,
        target_academic_year_id: int,
        remarks: str = "Year-end batch promotion"
    ) -> int:
        promoted_count = 0
        students = db.query(Student).filter(Student.id.in_(student_ids)).all()
        for stu in students:
            # Record promotion history
            history = StudentPromotionHistory(
                student_id=stu.id,
                from_class_id=stu.class_id,
                to_class_id=target_class_id,
                from_academic_year_id=stu.academic_year_id,
                to_academic_year_id=target_academic_year_id,
                remarks=remarks
            )
            db.add(history)
            
            # Update student record
            stu.class_id = target_class_id
            stu.academic_year_id = target_academic_year_id
            promoted_count += 1

        db.commit()
        return promoted_count

    @staticmethod
    def get_summary_statistics(db: Session) -> Dict[str, int]:
        total = db.query(Student).count()
        active = db.query(Student).filter(Student.status == StudentStatus.ACTIVE).count()
        male = db.query(Student).filter(Student.gender == "Male").count()
        female = db.query(Student).filter(Student.gender == "Female").count()
        return {
            "total": total,
            "active": active,
            "male": male,
            "female": female
        }
