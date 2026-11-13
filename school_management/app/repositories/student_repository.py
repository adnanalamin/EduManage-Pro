"""
EduManage Pro - Student CRM Repository
Encapsulates all database queries, advanced multi-criteria CRM search, pagination,
statistics, and atomic mutations for Student CRM records.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import asc, cast, desc, exists, or_, String
from sqlalchemy.orm import Session, joinedload

from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.student import (
    Guardian,
    Student,
    StudentAcademicHistory,
    StudentEmergencyContact,
    StudentGuardianLink,
    StudentPromotionHistory,
    StudentStatus,
    StudentTag,
)
from app.services.database_service import DatabaseService
from app.utils.qr_generator import build_qr_payload, generate_digital_id


class StudentRepository:
    @staticmethod
    def get_by_id(db: Session, student_pk: int) -> Optional[Student]:
        return (
            db.query(Student)
            .options(
                joinedload(Student.guardian),
                joinedload(Student.school_class),
                joinedload(Student.section),
                joinedload(Student.academic_year),
                joinedload(Student.medical_profile),
                joinedload(Student.tags),
            )
            .filter(Student.id == student_pk)
            .first()
        )

    @staticmethod
    def get_by_student_id(db: Session, student_id: str) -> Optional[Student]:
        return db.query(Student).filter(Student.student_id == student_id).first()

    @staticmethod
    def get_by_admission_number(db: Session, admission_number: str) -> Optional[Student]:
        return db.query(Student).filter(Student.admission_number == admission_number).first()

    @staticmethod
    def get_by_digital_id(db: Session, digital_id_code: str) -> Optional[Student]:
        return db.query(Student).filter(Student.digital_id_code == digital_id_code).first()

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
        include_deleted: bool = False,
        # Extended Student CRM advanced search filters
        name: Optional[str] = None,
        student_id_code: Optional[str] = None,
        admission_number: Optional[str] = None,
        roll_number: Optional[Union[int, str]] = None,
        guardian: Optional[str] = None,
        phone: Optional[str] = None,
        academic_year_id: Optional[int] = None,
        tag: Optional[str] = None,
        include_archived: bool = True,
    ) -> Tuple[List[Student], int]:
        """
        Query students with full CRM search across:
        Name, Student ID / Digital ID, Admission #, Roll, Class, Section,
        Guardian (primary + linked guardians), Phone, Status, Academic Year, Tags, and Gender.
        Returns: (list_of_students, total_matching_count)
        """
        query = db.query(Student).options(
            joinedload(Student.guardian),
            joinedload(Student.school_class),
            joinedload(Student.section),
            joinedload(Student.academic_year),
            joinedload(Student.tags),
        )

        if not include_deleted:
            query = query.filter(Student.is_deleted == False)

        # Global multi-field search
        if search_query and search_query.strip():
            raw = search_query.strip()
            term = f"%{raw}%"
            guardian_match = exists().where(
                StudentGuardianLink.student_id == Student.id,
                StudentGuardianLink.guardian_id == Guardian.id,
                or_(
                    Guardian.guardian_name.ilike(term),
                    Guardian.father_name.ilike(term),
                    Guardian.mother_name.ilike(term),
                    Guardian.guardian_phone.ilike(term),
                ),
            )
            primary_guardian_match = exists().where(
                Guardian.id == Student.guardian_id,
                or_(
                    Guardian.guardian_name.ilike(term),
                    Guardian.guardian_phone.ilike(term),
                ),
            )
            query = query.filter(
                or_(
                    Student.full_name.ilike(term),
                    Student.full_name_bn.ilike(term),
                    Student.student_id.ilike(term),
                    Student.admission_number.ilike(term),
                    Student.digital_id_code.ilike(term),
                    cast(Student.roll_number, String).ilike(term),
                    Student.phone.ilike(term),
                    Student.email.ilike(term),
                    Student.emergency_contact.ilike(term),
                    Student.tags_text.ilike(term),
                    primary_guardian_match,
                    guardian_match,
                )
            )

        # Dedicated field filters
        if name and name.strip():
            n_term = f"%{name.strip()}%"
            query = query.filter(
                or_(
                    Student.full_name.ilike(n_term),
                    Student.full_name_bn.ilike(n_term),
                    Student.first_name.ilike(n_term),
                    Student.last_name.ilike(n_term),
                )
            )

        if student_id_code and student_id_code.strip():
            sid_term = f"%{student_id_code.strip()}%"
            query = query.filter(
                or_(
                    Student.student_id.ilike(sid_term),
                    Student.digital_id_code.ilike(sid_term),
                )
            )

        if admission_number and admission_number.strip():
            adm_term = f"%{admission_number.strip()}%"
            query = query.filter(Student.admission_number.ilike(adm_term))

        if roll_number is not None and str(roll_number).strip() != "":
            roll_str = str(roll_number).strip()
            if roll_str.isdigit():
                query = query.filter(Student.roll_number == int(roll_str))
            else:
                query = query.filter(cast(Student.roll_number, String).ilike(f"%{roll_str}%"))

        if class_id:
            query = query.filter(Student.class_id == class_id)
        if section_id:
            query = query.filter(Student.section_id == section_id)
        if academic_year_id:
            query = query.filter(Student.academic_year_id == academic_year_id)
        if gender:
            query = query.filter(Student.gender == gender)

        if status:
            query = query.filter(Student.status == status)
        elif not include_archived:
            query = query.filter(Student.status != StudentStatus.ARCHIVED)

        if guardian and guardian.strip():
            g_term = f"%{guardian.strip()}%"
            primary_g = exists().where(
                Guardian.id == Student.guardian_id,
                or_(
                    Guardian.guardian_name.ilike(g_term),
                    Guardian.father_name.ilike(g_term),
                    Guardian.mother_name.ilike(g_term),
                    Guardian.guardian_phone.ilike(g_term),
                ),
            )
            linked_g = exists().where(
                StudentGuardianLink.student_id == Student.id,
                StudentGuardianLink.guardian_id == Guardian.id,
                or_(
                    Guardian.guardian_name.ilike(g_term),
                    Guardian.father_name.ilike(g_term),
                    Guardian.mother_name.ilike(g_term),
                    Guardian.guardian_phone.ilike(g_term),
                ),
            )
            query = query.filter(or_(primary_g, linked_g))

        if phone and phone.strip():
            p_term = f"%{phone.strip()}%"
            primary_gp = exists().where(
                Guardian.id == Student.guardian_id,
                Guardian.guardian_phone.ilike(p_term),
            )
            linked_gp = exists().where(
                StudentGuardianLink.student_id == Student.id,
                StudentGuardianLink.guardian_id == Guardian.id,
                Guardian.guardian_phone.ilike(p_term),
            )
            emergency_p = exists().where(
                StudentEmergencyContact.student_id == Student.id,
                or_(
                    StudentEmergencyContact.primary_phone.ilike(p_term),
                    StudentEmergencyContact.secondary_phone.ilike(p_term),
                ),
            )
            query = query.filter(
                or_(
                    Student.phone.ilike(p_term),
                    Student.emergency_contact.ilike(p_term),
                    primary_gp,
                    linked_gp,
                    emergency_p,
                )
            )

        if tag and tag.strip():
            t_clean = tag.strip()
            t_term = f"%{t_clean}%"
            has_tag = Student.tags.any(StudentTag.name.ilike(t_term))
            query = query.filter(or_(has_tag, Student.tags_text.ilike(t_term)))

        total_count = query.count()

        # Sorting
        sort_column = getattr(Student, sort_by, Student.roll_number)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column), desc(Student.id))
        else:
            query = query.order_by(asc(sort_column), asc(Student.id))

        # Pagination
        offset = max(0, (page - 1) * per_page)
        items = query.offset(offset).limit(per_page).all()

        return items, total_count

    @staticmethod
    def create(
        db: Session,
        student_data: Dict[str, Any],
        guardian_data: Optional[Dict[str, Any]] = None,
    ) -> Student:
        guardian = None
        if guardian_data:
            guardian = Guardian(**guardian_data)
            db.add(guardian)
            db.flush()

        payload = dict(student_data)
        if not payload.get("digital_id_code") and payload.get("student_id"):
            payload["digital_id_code"] = generate_digital_id(
                payload["student_id"],
                payload.get("admission_date"),
            )

        student = Student(**payload)
        if guardian:
            student.guardian_id = guardian.id

        db.add(student)
        db.flush()

        if not student.qr_payload:
            student.qr_payload = build_qr_payload(
                student_id=student.student_id,
                admission_number=student.admission_number,
                digital_id_code=student.digital_id_code,
                public_id=student.public_id,
            )

        if guardian:
            existing_link = (
                db.query(StudentGuardianLink)
                .filter_by(student_id=student.id, guardian_id=guardian.id)
                .first()
            )
            if not existing_link:
                db.add(
                    StudentGuardianLink(
                        student_id=student.id,
                        guardian_id=guardian.id,
                        relationship_type=guardian.relation or "Father",
                        is_primary=True,
                        is_emergency_contact=True,
                        is_financial_payer=True,
                        can_pickup=True,
                        priority_order=1,
                    )
                )

        db.commit()
        db.refresh(student)
        return student

    @staticmethod
    def update(
        db: Session,
        student: Student,
        student_data: Dict[str, Any],
        guardian_data: Optional[Dict[str, Any]] = None,
    ) -> Student:
        for key, value in student_data.items():
            setattr(student, key, value)

        if not student.digital_id_code:
            student.digital_id_code = generate_digital_id(student.student_id, student.admission_date)
        student.qr_payload = build_qr_payload(
            student_id=student.student_id,
            admission_number=student.admission_number,
            digital_id_code=student.digital_id_code,
            public_id=student.public_id,
        )

        if guardian_data:
            if student.guardian:
                for k, v in guardian_data.items():
                    setattr(student.guardian, k, v)
            else:
                new_guardian = Guardian(**guardian_data)
                db.add(new_guardian)
                db.flush()
                student.guardian_id = new_guardian.id
                db.add(
                    StudentGuardianLink(
                        student_id=student.id,
                        guardian_id=new_guardian.id,
                        relationship_type=new_guardian.relation or "Father",
                        is_primary=True,
                        is_emergency_contact=True,
                        is_financial_payer=True,
                        can_pickup=True,
                        priority_order=1,
                    )
                )

        db.commit()
        db.refresh(student)
        return student

    @staticmethod
    def archive_or_delete(
        db: Session,
        student: Student,
        soft_delete: bool = True,
        deleted_by: str = "system",
    ) -> bool:
        if soft_delete:
            student.status = StudentStatus.INACTIVE
            student.mark_deleted(deleted_by=deleted_by)
            db.commit()
        else:
            DatabaseService.safe_hard_delete(db, student, commit=True)
        return True

    @staticmethod
    def bulk_promote(
        db: Session,
        student_ids: List[int],
        target_class_id: int,
        target_academic_year_id: int,
        remarks: str = "Year-end batch promotion",
        target_section_id: Optional[int] = None,
    ) -> int:
        promoted_count = 0
        students = db.query(Student).filter(Student.id.in_(student_ids)).all()
        for stu in students:
            history = StudentPromotionHistory(
                student_id=stu.id,
                from_class_id=stu.class_id,
                to_class_id=target_class_id,
                from_academic_year_id=stu.academic_year_id,
                to_academic_year_id=target_academic_year_id,
                remarks=remarks,
            )
            db.add(history)

            # Close out current academic history row if open
            prev_acad = (
                db.query(StudentAcademicHistory)
                .filter(
                    StudentAcademicHistory.student_id == stu.id,
                    StudentAcademicHistory.academic_year_id == stu.academic_year_id,
                    StudentAcademicHistory.class_id == stu.class_id,
                    StudentAcademicHistory.result_status == "Enrolled",
                )
                .order_by(StudentAcademicHistory.id.desc())
                .first()
            )
            if prev_acad:
                prev_acad.result_status = "Promoted"
                prev_acad.end_date = date.today()
                prev_acad.remarks = remarks

            # Update student record
            stu.class_id = target_class_id
            if target_section_id is not None:
                stu.section_id = target_section_id
            stu.academic_year_id = target_academic_year_id

            # Record new academic year enrollment entry
            db.add(
                StudentAcademicHistory(
                    student_id=stu.id,
                    academic_year_id=target_academic_year_id,
                    class_id=target_class_id,
                    section_id=stu.section_id,
                    roll_number=stu.roll_number,
                    group=stu.group,
                    shift=stu.shift,
                    result_status="Enrolled",
                    start_date=date.today(),
                    remarks=remarks,
                )
            )
            promoted_count += 1

        db.commit()
        return promoted_count

    @staticmethod
    def get_summary_statistics(db: Session) -> Dict[str, int]:
        base = db.query(Student).filter(Student.is_deleted == False)
        total = base.count()
        active = base.filter(Student.status == StudentStatus.ACTIVE).count()
        inactive = base.filter(Student.status == StudentStatus.INACTIVE).count()
        transferred = base.filter(Student.status == StudentStatus.TRANSFERRED).count()
        graduated = base.filter(Student.status == StudentStatus.GRADUATED).count()
        withdrawn = base.filter(Student.status == StudentStatus.WITHDRAWN).count()
        suspended = base.filter(Student.status == StudentStatus.SUSPENDED).count()
        archived = base.filter(Student.status == StudentStatus.ARCHIVED).count()
        male = base.filter(Student.gender == "Male").count()
        female = base.filter(Student.gender == "Female").count()
        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "transferred": transferred,
            "graduated": graduated,
            "withdrawn": withdrawn,
            "suspended": suspended,
            "archived": archived,
            "male": male,
            "female": female,
        }
