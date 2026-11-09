"""
EduManage Pro - Academic Repository Layer
Data access operations for Academic Years, Classes, Sections, and Subjects.
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.models.staff import Teacher


class AcademicRepository:
    # ==================== ACADEMIC YEARS ====================
    @staticmethod
    def get_all_academic_years(db: Session) -> List[AcademicYear]:
        return db.query(AcademicYear).order_by(AcademicYear.start_date.desc()).all()

    @staticmethod
    def get_current_academic_year(db: Session) -> Optional[AcademicYear]:
        return db.query(AcademicYear).filter(AcademicYear.is_current == True).first()

    @staticmethod
    def create_academic_year(db: Session, year_data: dict) -> AcademicYear:
        # If set as current, deactivate others
        if year_data.get("is_current"):
            db.query(AcademicYear).update({AcademicYear.is_current: False})
        
        year = AcademicYear(**year_data)
        db.add(year)
        db.commit()
        db.refresh(year)
        return year

    @staticmethod
    def set_active_academic_year(db: Session, year_id: int) -> Optional[AcademicYear]:
        target = db.query(AcademicYear).filter(AcademicYear.id == year_id).first()
        if not target:
            return None
        db.query(AcademicYear).update({AcademicYear.is_current: False})
        target.is_current = True
        db.commit()
        db.refresh(target)
        return target

    # ==================== SCHOOL CLASSES ====================
    @staticmethod
    def get_classes(
        db: Session,
        academic_year_id: Optional[int] = None,
        search: Optional[str] = None
    ) -> List[SchoolClass]:
        query = db.query(SchoolClass).options(
            joinedload(SchoolClass.sections).joinedload(Section.class_teacher),
            joinedload(SchoolClass.subjects).joinedload(Subject.assigned_teacher),
            joinedload(SchoolClass.academic_year)
        )
        if academic_year_id:
            query = query.filter(SchoolClass.academic_year_id == academic_year_id)
        if search:
            term = f"%{search}%"
            query = query.filter(or_(
                SchoolClass.name.ilike(term),
                SchoolClass.code.ilike(term),
                SchoolClass.group.ilike(term)
            ))
        return query.order_by(SchoolClass.numeric_order.asc(), SchoolClass.name.asc()).all()

    @staticmethod
    def get_class_by_id(db: Session, class_id: int) -> Optional[SchoolClass]:
        return db.query(SchoolClass).options(
            joinedload(SchoolClass.sections).joinedload(Section.class_teacher),
            joinedload(SchoolClass.subjects).joinedload(Subject.assigned_teacher),
            joinedload(SchoolClass.academic_year)
        ).filter(SchoolClass.id == class_id).first()

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
        search: Optional[str] = None
    ) -> List[Section]:
        query = db.query(Section).options(
            joinedload(Section.school_class),
            joinedload(Section.class_teacher)
        )
        if class_id:
            query = query.filter(Section.class_id == class_id)
        if search:
            term = f"%{search}%"
            query = query.filter(or_(
                Section.name.ilike(term),
                Section.room_number.ilike(term),
                Section.shift.ilike(term)
            ))
        return query.order_by(Section.class_id.asc(), Section.name.asc()).all()

    @staticmethod
    def get_section_by_id(db: Session, section_id: int) -> Optional[Section]:
        return db.query(Section).options(
            joinedload(Section.school_class),
            joinedload(Section.class_teacher)
        ).filter(Section.id == section_id).first()

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
        search: Optional[str] = None
    ) -> List[Subject]:
        query = db.query(Subject).options(
            joinedload(Subject.school_class),
            joinedload(Subject.assigned_teacher)
        )
        if class_id:
            query = query.filter(Subject.class_id == class_id)
        if search:
            term = f"%{search}%"
            query = query.filter(or_(
                Subject.name.ilike(term),
                Subject.code.ilike(term),
                Subject.subject_id.ilike(term)
            ))
        return query.order_by(Subject.class_id.asc(), Subject.name.asc()).all()

    @staticmethod
    def get_subject_by_id(db: Session, subject_id_pk: int) -> Optional[Subject]:
        return db.query(Subject).options(
            joinedload(Subject.school_class),
            joinedload(Subject.assigned_teacher)
        ).filter(Subject.id == subject_id_pk).first()

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
