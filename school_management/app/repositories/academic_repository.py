"""
EduManage Pro - Academic Repository Layer
Data access operations for Academic Years, Groups, Shifts, Rooms, Departments,
Classes, Sections, Subjects, Optional Subject Enrollments, and Academic Calendar.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.models.academic import (
    AcademicGroup,
    AcademicRoom,
    AcademicShift,
    AcademicYear,
    SchoolClass,
    Section,
    StudentSubjectEnrollment,
    Subject,
)
from app.models.notice import SchoolEvent
from app.models.staff import Department, Teacher


class AcademicRepository:
    # ==================== ACADEMIC YEARS ====================
    @staticmethod
    def get_all_academic_years(db: Session, include_deleted: bool = False) -> List[AcademicYear]:
        query = db.query(AcademicYear)
        if not include_deleted:
            query = query.filter(AcademicYear.is_deleted == False)
        return query.order_by(AcademicYear.start_date.desc()).all()

    @staticmethod
    def get_academic_year_by_id(db: Session, year_id: int) -> Optional[AcademicYear]:
        return db.query(AcademicYear).filter(AcademicYear.id == year_id).first()

    @staticmethod
    def get_current_academic_year(db: Session) -> Optional[AcademicYear]:
        return (
            db.query(AcademicYear)
            .filter(AcademicYear.is_current == True, AcademicYear.is_deleted == False)
            .first()
        )

    @staticmethod
    def create_academic_year(db: Session, year_data: dict) -> AcademicYear:
        if year_data.get("is_current"):
            db.query(AcademicYear).update({AcademicYear.is_current: False})

        year = AcademicYear(**year_data)
        db.add(year)
        db.commit()
        db.refresh(year)
        return year

    @staticmethod
    def update_academic_year(db: Session, year_id: int, updates: dict) -> Optional[AcademicYear]:
        target = db.query(AcademicYear).filter(AcademicYear.id == year_id).first()
        if not target:
            return None
        if updates.get("is_current"):
            db.query(AcademicYear).filter(AcademicYear.id != year_id).update({AcademicYear.is_current: False})
        for k, v in updates.items():
            if hasattr(target, k):
                setattr(target, k, v)
        db.commit()
        db.refresh(target)
        return target

    @staticmethod
    def set_active_academic_year(db: Session, year_id: int) -> Optional[AcademicYear]:
        target = db.query(AcademicYear).filter(AcademicYear.id == year_id).first()
        if not target:
            return None
        db.query(AcademicYear).update({AcademicYear.is_current: False})
        target.is_current = True
        target.status = "Active"
        db.commit()
        db.refresh(target)
        return target

    # ==================== ACADEMIC GROUPS / STREAMS ====================
    @staticmethod
    def get_or_create_default_groups(db: Session) -> List[AcademicGroup]:
        defaults = [
            ("General", "GEN", "Core general education curriculum (Pre-Primary to Class 8)", 1),
            ("Science", "SCI", "Physics, Chemistry, Biology, Higher Mathematics", 2),
            ("Humanities", "HUM", "History, Civics, Geography, Sociology, Economics", 3),
            ("Business Studies", "BUS", "Accounting, Finance, Management, Business Entrepreneurship", 4),
        ]
        out: List[AcademicGroup] = []
        created = False
        for name, code, desc, order in defaults:
            grp = db.query(AcademicGroup).filter(
                or_(AcademicGroup.code == code, AcademicGroup.name == name)
            ).first()
            if not grp:
                grp = AcademicGroup(name=name, code=code, description=desc, display_order=order, is_active=True)
                db.add(grp)
                db.flush()
                created = True
            out.append(grp)
        if created:
            db.commit()
        return out

    @staticmethod
    def get_groups(db: Session, include_inactive: bool = False) -> List[AcademicGroup]:
        query = db.query(AcademicGroup).filter(AcademicGroup.is_deleted == False)
        if not include_inactive:
            query = query.filter(AcademicGroup.is_active == True)
        return query.order_by(AcademicGroup.display_order.asc(), AcademicGroup.name.asc()).all()

    @staticmethod
    def get_group_by_id(db: Session, group_id: int) -> Optional[AcademicGroup]:
        return db.query(AcademicGroup).filter(AcademicGroup.id == group_id).first()

    @staticmethod
    def create_group(db: Session, data: dict) -> AcademicGroup:
        grp = AcademicGroup(**data)
        db.add(grp)
        db.commit()
        db.refresh(grp)
        return grp

    @staticmethod
    def update_group(db: Session, group_id: int, updates: dict) -> Optional[AcademicGroup]:
        grp = db.query(AcademicGroup).filter(AcademicGroup.id == group_id).first()
        if not grp:
            return None
        for k, v in updates.items():
            if hasattr(grp, k):
                setattr(grp, k, v)
        db.commit()
        db.refresh(grp)
        return grp

    @staticmethod
    def delete_group(db: Session, group_id: int) -> bool:
        grp = db.query(AcademicGroup).filter(AcademicGroup.id == group_id).first()
        if not grp:
            return False
        db.delete(grp)
        db.commit()
        return True

    # ==================== ACADEMIC SHIFTS ====================
    @staticmethod
    def get_or_create_default_shifts(db: Session) -> List[AcademicShift]:
        defaults = [
            ("Morning", "MRN", "07:30 AM", "12:15 PM", "Morning campus shift", 1),
            ("Day", "DAY", "12:30 PM", "05:00 PM", "Afternoon / Day shift", 2),
            ("Evening", "EVE", "05:15 PM", "08:30 PM", "Evening / Coaching shift", 3),
        ]
        out: List[AcademicShift] = []
        created = False
        for name, code, st, et, desc, order in defaults:
            sh = db.query(AcademicShift).filter(
                or_(AcademicShift.code == code, AcademicShift.name == name)
            ).first()
            if not sh:
                sh = AcademicShift(
                    name=name,
                    code=code,
                    start_time=st,
                    end_time=et,
                    description=desc,
                    display_order=order,
                    is_active=True,
                )
                db.add(sh)
                db.flush()
                created = True
            out.append(sh)
        if created:
            db.commit()
        return out

    @staticmethod
    def get_shifts(db: Session, include_inactive: bool = False) -> List[AcademicShift]:
        query = db.query(AcademicShift).filter(AcademicShift.is_deleted == False)
        if not include_inactive:
            query = query.filter(AcademicShift.is_active == True)
        return query.order_by(AcademicShift.display_order.asc(), AcademicShift.name.asc()).all()

    @staticmethod
    def get_shift_by_id(db: Session, shift_id: int) -> Optional[AcademicShift]:
        return db.query(AcademicShift).filter(AcademicShift.id == shift_id).first()

    @staticmethod
    def create_shift(db: Session, data: dict) -> AcademicShift:
        sh = AcademicShift(**data)
        db.add(sh)
        db.commit()
        db.refresh(sh)
        return sh

    @staticmethod
    def update_shift(db: Session, shift_id: int, updates: dict) -> Optional[AcademicShift]:
        sh = db.query(AcademicShift).filter(AcademicShift.id == shift_id).first()
        if not sh:
            return None
        for k, v in updates.items():
            if hasattr(sh, k):
                setattr(sh, k, v)
        db.commit()
        db.refresh(sh)
        return sh

    @staticmethod
    def delete_shift(db: Session, shift_id: int) -> bool:
        sh = db.query(AcademicShift).filter(AcademicShift.id == shift_id).first()
        if not sh:
            return False
        db.delete(sh)
        db.commit()
        return True

    # ==================== ACADEMIC ROOMS ====================
    @staticmethod
    def get_rooms(
        db: Session,
        room_type: Optional[str] = None,
        search: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[AcademicRoom]:
        query = db.query(AcademicRoom).filter(AcademicRoom.is_deleted == False)
        if not include_inactive:
            query = query.filter(AcademicRoom.is_active == True)
        if room_type and room_type != "All":
            query = query.filter(AcademicRoom.room_type == room_type)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    AcademicRoom.room_number.ilike(term),
                    AcademicRoom.room_name.ilike(term),
                    AcademicRoom.building.ilike(term),
                )
            )
        return query.order_by(AcademicRoom.building.asc(), AcademicRoom.room_number.asc()).all()

    @staticmethod
    def get_room_by_id(db: Session, room_id: int) -> Optional[AcademicRoom]:
        return db.query(AcademicRoom).filter(AcademicRoom.id == room_id).first()

    @staticmethod
    def create_room(db: Session, data: dict) -> AcademicRoom:
        room = AcademicRoom(**data)
        db.add(room)
        db.commit()
        db.refresh(room)
        return room

    @staticmethod
    def update_room(db: Session, room_id: int, updates: dict) -> Optional[AcademicRoom]:
        room = db.query(AcademicRoom).filter(AcademicRoom.id == room_id).first()
        if not room:
            return None
        for k, v in updates.items():
            if hasattr(room, k):
                setattr(room, k, v)
        db.commit()
        db.refresh(room)
        return room

    @staticmethod
    def delete_room(db: Session, room_id: int) -> bool:
        room = db.query(AcademicRoom).filter(AcademicRoom.id == room_id).first()
        if not room:
            return False
        db.delete(room)
        db.commit()
        return True

    # ==================== DEPARTMENTS ====================
    @staticmethod
    def get_departments(db: Session) -> List[Department]:
        return (
            db.query(Department)
            .filter(Department.is_deleted == False)
            .order_by(Department.name.asc())
            .all()
        )

    @staticmethod
    def create_department(db: Session, data: dict) -> Department:
        dept = Department(**data)
        db.add(dept)
        db.commit()
        db.refresh(dept)
        return dept

    @staticmethod
    def update_department(db: Session, dept_id: int, updates: dict) -> Optional[Department]:
        dept = db.query(Department).filter(Department.id == dept_id).first()
        if not dept:
            return None
        for k, v in updates.items():
            if hasattr(dept, k):
                setattr(dept, k, v)
        db.commit()
        db.refresh(dept)
        return dept

    # ==================== SCHOOL CLASSES ====================
    @staticmethod
    def get_classes(
        db: Session,
        academic_year_id: Optional[int] = None,
        search: Optional[str] = None,
        group: Optional[str] = None,
        shift: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[SchoolClass]:
        query = db.query(SchoolClass).options(
            joinedload(SchoolClass.sections).joinedload(Section.class_teacher),
            joinedload(SchoolClass.sections).joinedload(Section.room),
            joinedload(SchoolClass.subjects).joinedload(Subject.assigned_teacher),
            joinedload(SchoolClass.academic_year),
            joinedload(SchoolClass.department),
            joinedload(SchoolClass.academic_group),
            joinedload(SchoolClass.academic_shift),
        ).filter(SchoolClass.is_deleted == False)
        if not include_inactive:
            query = query.filter(SchoolClass.is_active == True)
        if academic_year_id:
            query = query.filter(SchoolClass.academic_year_id == academic_year_id)
        if group and group != "All":
            query = query.filter(SchoolClass.group == group)
        if shift and shift != "All":
            query = query.filter(SchoolClass.shift == shift)
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    SchoolClass.name.ilike(term),
                    SchoolClass.code.ilike(term),
                    SchoolClass.group.ilike(term),
                    SchoolClass.structure_profile.ilike(term),
                )
            )
        return query.order_by(SchoolClass.numeric_order.asc(), SchoolClass.name.asc()).all()

    @staticmethod
    def get_class_by_id(db: Session, class_id: int) -> Optional[SchoolClass]:
        return (
            db.query(SchoolClass)
            .options(
                joinedload(SchoolClass.sections).joinedload(Section.class_teacher),
                joinedload(SchoolClass.sections).joinedload(Section.room),
                joinedload(SchoolClass.subjects).joinedload(Subject.assigned_teacher),
                joinedload(SchoolClass.academic_year),
                joinedload(SchoolClass.department),
                joinedload(SchoolClass.academic_group),
                joinedload(SchoolClass.academic_shift),
            )
            .filter(SchoolClass.id == class_id)
            .first()
        )

    @staticmethod
    def create_class(db: Session, class_data: dict) -> SchoolClass:
        cls_obj = SchoolClass(**class_data)
        db.add(cls_obj)
        db.commit()
        db.refresh(cls_obj)
        return cls_obj

    @staticmethod
    def update_class(db: Session, class_id: int, updates: dict) -> Optional[SchoolClass]:
        cls_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        if not cls_obj:
            return None
        for k, v in updates.items():
            if hasattr(cls_obj, k):
                setattr(cls_obj, k, v)
        db.commit()
        db.refresh(cls_obj)
        return cls_obj

    @staticmethod
    def delete_class(db: Session, class_id: int) -> bool:
        cls_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        if not cls_obj:
            return False
        db.delete(cls_obj)
        db.commit()
        return True

    # ==================== SECTIONS ====================
    @staticmethod
    def get_sections(
        db: Session,
        class_id: Optional[int] = None,
        search: Optional[str] = None,
        academic_year_id: Optional[int] = None,
        shift: Optional[str] = None,
    ) -> List[Section]:
        query = db.query(Section).options(
            joinedload(Section.school_class),
            joinedload(Section.class_teacher),
            joinedload(Section.room),
            joinedload(Section.academic_group),
            joinedload(Section.academic_shift),
        ).filter(Section.is_deleted == False)
        if class_id:
            query = query.filter(Section.class_id == class_id)
        if academic_year_id:
            query = query.join(SchoolClass, Section.class_id == SchoolClass.id).filter(
                SchoolClass.academic_year_id == academic_year_id
            )
        if shift and shift != "All":
            query = query.filter(Section.shift == shift)
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    Section.name.ilike(term),
                    Section.room_number.ilike(term),
                    Section.shift.ilike(term),
                    Section.group.ilike(term),
                )
            )
        return query.order_by(Section.class_id.asc(), Section.name.asc()).all()

    @staticmethod
    def get_section_by_id(db: Session, section_id: int) -> Optional[Section]:
        return (
            db.query(Section)
            .options(
                joinedload(Section.school_class),
                joinedload(Section.class_teacher),
                joinedload(Section.room),
                joinedload(Section.academic_group),
                joinedload(Section.academic_shift),
            )
            .filter(Section.id == section_id)
            .first()
        )

    @staticmethod
    def create_section(db: Session, section_data: dict) -> Section:
        sec = Section(**section_data)
        db.add(sec)
        db.commit()
        db.refresh(sec)
        return sec

    @staticmethod
    def update_section(db: Session, section_id: int, updates: dict) -> Optional[Section]:
        sec = db.query(Section).filter(Section.id == section_id).first()
        if not sec:
            return None
        for k, v in updates.items():
            if hasattr(sec, k):
                setattr(sec, k, v)
        db.commit()
        db.refresh(sec)
        return sec

    @staticmethod
    def delete_section(db: Session, section_id: int) -> bool:
        sec = db.query(Section).filter(Section.id == section_id).first()
        if not sec:
            return False
        db.delete(sec)
        db.commit()
        return True

    # ==================== SUBJECTS ====================
    @staticmethod
    def get_subjects(
        db: Session,
        class_id: Optional[int] = None,
        search: Optional[str] = None,
        academic_year_id: Optional[int] = None,
        subject_type: Optional[str] = None,
        department_id: Optional[int] = None,
    ) -> List[Subject]:
        query = db.query(Subject).options(
            joinedload(Subject.school_class),
            joinedload(Subject.assigned_teacher),
            joinedload(Subject.department),
            joinedload(Subject.academic_group),
        ).filter(Subject.is_deleted == False)
        if class_id:
            query = query.filter(Subject.class_id == class_id)
        if academic_year_id:
            query = query.join(SchoolClass, Subject.class_id == SchoolClass.id).filter(
                SchoolClass.academic_year_id == academic_year_id
            )
        if subject_type and subject_type != "All":
            query = query.filter(Subject.subject_type == subject_type)
        if department_id:
            query = query.filter(Subject.department_id == department_id)
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    Subject.name.ilike(term),
                    Subject.code.ilike(term),
                    Subject.subject_id.ilike(term),
                )
            )
        return query.order_by(Subject.class_id.asc(), Subject.name.asc()).all()

    @staticmethod
    def get_subject_by_id(db: Session, subject_id_pk: int) -> Optional[Subject]:
        return (
            db.query(Subject)
            .options(
                joinedload(Subject.school_class),
                joinedload(Subject.assigned_teacher),
                joinedload(Subject.department),
                joinedload(Subject.academic_group),
            )
            .filter(Subject.id == subject_id_pk)
            .first()
        )

    @staticmethod
    def create_subject(db: Session, subject_data: dict) -> Subject:
        sub = Subject(**subject_data)
        db.add(sub)
        db.commit()
        db.refresh(sub)
        return sub

    @staticmethod
    def update_subject(db: Session, subject_pk: int, updates: dict) -> Optional[Subject]:
        sub = db.query(Subject).filter(Subject.id == subject_pk).first()
        if not sub:
            return None
        for k, v in updates.items():
            if hasattr(sub, k):
                setattr(sub, k, v)
        db.commit()
        db.refresh(sub)
        return sub

    @staticmethod
    def delete_subject(db: Session, subject_pk: int) -> bool:
        sub = db.query(Subject).filter(Subject.id == subject_pk).first()
        if not sub:
            return False
        db.delete(sub)
        db.commit()
        return True

    # ==================== STUDENT SUBJECT ENROLLMENTS (OPTIONAL SUBJECTS) ====================
    @staticmethod
    def list_student_subject_enrollments(
        db: Session,
        student_id: int,
        academic_year_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[StudentSubjectEnrollment]:
        query = (
            db.query(StudentSubjectEnrollment)
            .options(
                joinedload(StudentSubjectEnrollment.subject).joinedload(Subject.assigned_teacher),
                joinedload(StudentSubjectEnrollment.school_class),
                joinedload(StudentSubjectEnrollment.academic_year),
            )
            .filter(StudentSubjectEnrollment.student_id == student_id)
        )
        if academic_year_id:
            query = query.filter(StudentSubjectEnrollment.academic_year_id == academic_year_id)
        if status:
            query = query.filter(StudentSubjectEnrollment.enrollment_status == status)
        return query.order_by(StudentSubjectEnrollment.academic_year_id.desc(), StudentSubjectEnrollment.id.asc()).all()

    @staticmethod
    def list_subject_students(
        db: Session,
        subject_id: int,
        academic_year_id: Optional[int] = None,
    ) -> List[StudentSubjectEnrollment]:
        query = (
            db.query(StudentSubjectEnrollment)
            .options(
                joinedload(StudentSubjectEnrollment.student),
                joinedload(StudentSubjectEnrollment.academic_year),
            )
            .filter(
                StudentSubjectEnrollment.subject_id == subject_id,
                StudentSubjectEnrollment.enrollment_status == "Active",
            )
        )
        if academic_year_id:
            query = query.filter(StudentSubjectEnrollment.academic_year_id == academic_year_id)
        return query.all()

    # ==================== ACADEMIC CALENDAR EVENTS ====================
    @staticmethod
    def list_calendar_events(
        db: Session,
        academic_year_id: Optional[int] = None,
        category: Optional[str] = None,
    ) -> List[SchoolEvent]:
        query = db.query(SchoolEvent).filter(SchoolEvent.is_deleted == False)
        if academic_year_id:
            query = query.filter(
                or_(
                    SchoolEvent.academic_year_id == academic_year_id,
                    SchoolEvent.academic_year_id.is_(None),
                )
            )
        if category and category != "All":
            query = query.filter(SchoolEvent.event_category == category)
        return query.order_by(SchoolEvent.start_date.asc()).all()
