"""
EduManage Pro - Academic Service Layer
Business logic, validations, automated subject code/ID generation, and audit logging.
"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.repositories.academic_repository import AcademicRepository
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.models.activity import ActivityLog
from app.services.database_service import DatabaseService
from app.config.logging_config import app_logger, security_logger


class AcademicService:
    @staticmethod
    def generate_subject_id(db: Session) -> str:
        count = db.query(Subject).count()
        year = datetime.now().year
        return f"SUB-{year}-{count + 1:04d}"

    @staticmethod
    def create_class(db: Session, class_data: dict, current_user: str = "admin") -> Tuple[Optional[SchoolClass], str]:
        # Validate unique name within academic year
        existing = db.query(SchoolClass).filter(
            SchoolClass.name == class_data.get("name"),
            SchoolClass.academic_year_id == class_data.get("academic_year_id")
        ).first()
        if existing:
            return None, f"Class '{class_data.get('name')}' already exists in this academic year."

        new_class = AcademicRepository.create_class(db, class_data)
        
        # Log activity
        log = ActivityLog(
            user_id=DatabaseService.resolve_user_id(db, current_user),
            username=current_user,
            action="CREATE_CLASS",
            module="ACADEMICS",
            description=f"Created class '{new_class.name}' (Code: {new_class.code}, Group: {new_class.group})",
            severity="INFO"
        )
        db.add(log)
        db.commit()
        app_logger.info(f"Class '{new_class.name}' created by {current_user}")
        return new_class, "Class created successfully."

    @staticmethod
    def update_class(db: Session, class_id: int, updates: dict, current_user: str = "admin") -> Tuple[Optional[SchoolClass], str]:
        cls_obj = AcademicRepository.update_class(db, class_id, updates)
        if not cls_obj:
            return None, "Class not found."
        
        log = ActivityLog(
            user_id=DatabaseService.resolve_user_id(db, current_user),
            username=current_user,
            action="UPDATE_CLASS",
            module="ACADEMICS",
            description=f"Updated details for class '{cls_obj.name}'",
            severity="INFO"
        )
        db.add(log)
        db.commit()
        return cls_obj, "Class updated successfully."

    @staticmethod
    def create_section(db: Session, section_data: dict, current_user: str = "admin") -> Tuple[Optional[Section], str]:
        # Validate section name uniqueness within class
        existing = db.query(Section).filter(
            Section.name == section_data.get("name"),
            Section.class_id == section_data.get("class_id")
        ).first()
        if existing:
            return None, f"Section '{section_data.get('name')}' already exists in this class."

        sec = AcademicRepository.create_section(db, section_data)
        log = ActivityLog(
            user_id=DatabaseService.resolve_user_id(db, current_user),
            username=current_user,
            action="CREATE_SECTION",
            module="ACADEMICS",
            description=f"Created section '{sec.name}' for Class ID {sec.class_id} (Room: {sec.room_number})",
            severity="INFO"
        )
        db.add(log)
        db.commit()
        return sec, "Section created successfully."

    @staticmethod
    def update_section(db: Session, section_id: int, updates: dict, current_user: str = "admin") -> Tuple[Optional[Section], str]:
        sec = AcademicRepository.update_section(db, section_id, updates)
        if not sec:
            return None, "Section not found."
        log = ActivityLog(
            user_id=DatabaseService.resolve_user_id(db, current_user),
            username=current_user,
            action="UPDATE_SECTION",
            module="ACADEMICS",
            description=f"Updated section '{sec.name}' (Class ID: {sec.class_id})",
            severity="INFO"
        )
        db.add(log)
        db.commit()
        return sec, "Section updated successfully."

    @staticmethod
    def create_subject(db: Session, subject_data: dict, current_user: str = "admin") -> Tuple[Optional[Subject], str]:
        # Validate marks
        full_marks = int(subject_data.get("full_marks", 100))
        pass_marks = int(subject_data.get("pass_marks", 33))
        theory = int(subject_data.get("theory_marks", 75))
        practical = int(subject_data.get("practical_marks", 25))

        if pass_marks > full_marks:
            return None, "Pass marks cannot exceed full marks."
        if theory + practical != full_marks:
            # Auto adjust theory or notify
            subject_data["theory_marks"] = full_marks - practical

        if not subject_data.get("subject_id"):
            subject_data["subject_id"] = AcademicService.generate_subject_id(db)

        # Check unique code in same class
        existing = db.query(Subject).filter(
            Subject.code == subject_data.get("code"),
            Subject.class_id == subject_data.get("class_id")
        ).first()
        if existing:
            return None, f"Subject code '{subject_data.get('code')}' is already registered for this class."

        sub = AcademicRepository.create_subject(db, subject_data)
        log = ActivityLog(
            user_id=DatabaseService.resolve_user_id(db, current_user),
            username=current_user,
            action="CREATE_SUBJECT",
            module="ACADEMICS",
            description=f"Created subject '{sub.name}' (Code: {sub.code}, Class ID: {sub.class_id})",
            severity="INFO"
        )
        db.add(log)
        db.commit()
        return sub, "Subject created successfully."

    @staticmethod
    def update_subject(db: Session, subject_id_pk: int, updates: dict, current_user: str = "admin") -> Tuple[Optional[Subject], str]:
        sub = AcademicRepository.update_subject(db, subject_id_pk, updates)
        if not sub:
            return None, "Subject not found."
        log = ActivityLog(
            user_id=DatabaseService.resolve_user_id(db, current_user),
            username=current_user,
            action="UPDATE_SUBJECT",
            module="ACADEMICS",
            description=f"Updated subject '{sub.name}' (Code: {sub.code})",
            severity="INFO"
        )
        db.add(log)
        db.commit()
        return sub, "Subject updated successfully."

    @staticmethod
    def get_academic_summary(db: Session) -> Dict[str, Any]:
        total_classes = db.query(SchoolClass).count()
        total_sections = db.query(Section).count()
        total_subjects = db.query(Subject).count()
        current_year = AcademicRepository.get_current_academic_year(db)
        return {
            "total_classes": total_classes,
            "total_sections": total_sections,
            "total_subjects": total_subjects,
            "current_year": current_year.name if current_year else "Not Set",
        }
