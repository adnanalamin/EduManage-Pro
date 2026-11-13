"""
EduManage Pro - Academic Service Layer
Business logic, validations, custom class structures, configuration wizard,
historical preservation guards, promotions, transfers, optional subjects, and calendar.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config.logging_config import app_logger, error_logger
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
from app.models.activity import ActivityLog
from app.models.attendance import StudentAttendance
from app.models.exam import ExamResultSummary, StudentMark
from app.models.notice import SchoolEvent
from app.models.settings import SchoolSettings
from app.models.staff import Department, Teacher, TeacherSubjectAssignment
from app.models.student import (
    Student,
    StudentAcademicHistory,
    StudentPromotionHistory,
    StudentStatus,
    StudentStatusHistory,
    StudentTransferHistory,
)
from app.reports.academic_calendar_pdf import AcademicCalendarPDFGenerator
from app.repositories.academic_repository import AcademicRepository
from app.repositories.notice_repository import NoticeRepository
from app.services.database_service import DatabaseService


STRUCTURE_PRESETS: Dict[str, Dict[str, Any]] = {
    "Standard K-10 (Class 1 - Class 10)": {
        "profile": "Standard K-10",
        "description": "Classes 1 through 10 with default sections and core curriculum.",
        "classes": [
            {"name": f"Class {i}", "code": f"C{i:02d}", "numeric_order": i, "group": "General", "shift": "Morning", "sections": ["Section A", "Section B"]}
            for i in range(1, 9)
        ] + [
            {"name": "Class 9", "code": "C09", "numeric_order": 9, "group": "Science", "shift": "Day", "sections": ["Section A"]},
            {"name": "Class 10", "code": "C10", "numeric_order": 10, "group": "Science", "shift": "Day", "sections": ["Section A"]},
        ],
    },
    "Pre-Primary & Primary (Playgroup - Class 5)": {
        "profile": "Primary",
        "description": "Early childhood through Class 5 (Playgroup, Nursery, KG, Class 1–5).",
        "classes": [
            {"name": "Playgroup", "code": "PG", "numeric_order": 1, "group": "General", "shift": "Morning", "sections": ["Rose"]},
            {"name": "Nursery", "code": "NUR", "numeric_order": 2, "group": "General", "shift": "Morning", "sections": ["Lily"]},
            {"name": "KG", "code": "KG", "numeric_order": 3, "group": "General", "shift": "Morning", "sections": ["Tulip"]},
        ] + [
            {"name": f"Class {i}", "code": f"C{i:02d}", "numeric_order": i + 3, "group": "General", "shift": "Morning", "sections": ["Section A", "Section B"]}
            for i in range(1, 6)
        ],
    },
    "Secondary Streams (Class 9-10 Science/Humanities/Business)": {
        "profile": "Secondary Streams",
        "description": "Stream-separated classes for Grade 9 and Grade 10 across Science, Humanities, and Business Studies.",
        "classes": [
            {"name": "Class 9", "code": "C09-SCI", "numeric_order": 9, "group": "Science", "shift": "Morning", "sections": ["A"]},
            {"name": "Class 9", "code": "C09-HUM", "numeric_order": 9, "group": "Humanities", "shift": "Day", "sections": ["A"]},
            {"name": "Class 9", "code": "C09-BUS", "numeric_order": 9, "group": "Business Studies", "shift": "Day", "sections": ["A"]},
            {"name": "Class 10", "code": "C10-SCI", "numeric_order": 10, "group": "Science", "shift": "Morning", "sections": ["A"]},
            {"name": "Class 10", "code": "C10-HUM", "numeric_order": 10, "group": "Humanities", "shift": "Day", "sections": ["A"]},
            {"name": "Class 10", "code": "C10-BUS", "numeric_order": 10, "group": "Business Studies", "shift": "Day", "sections": ["A"]},
        ],
    },
    "Higher Secondary (Class 11-12)": {
        "profile": "Higher Secondary",
        "description": "Senior secondary / HSC stream structure for Class 11 and Class 12.",
        "classes": [
            {"name": "Class 11", "code": "XI-SCI", "numeric_order": 11, "group": "Science", "shift": "Morning", "sections": ["Science-1"]},
            {"name": "Class 11", "code": "XI-HUM", "numeric_order": 11, "group": "Humanities", "shift": "Day", "sections": ["Hum-1"]},
            {"name": "Class 11", "code": "XI-BUS", "numeric_order": 11, "group": "Business Studies", "shift": "Day", "sections": ["Bus-1"]},
            {"name": "Class 12", "code": "XII-SCI", "numeric_order": 12, "group": "Science", "shift": "Morning", "sections": ["Science-1"]},
            {"name": "Class 12", "code": "XII-HUM", "numeric_order": 12, "group": "Humanities", "shift": "Day", "sections": ["Hum-1"]},
            {"name": "Class 12", "code": "XII-BUS", "numeric_order": 12, "group": "Business Studies", "shift": "Day", "sections": ["Bus-1"]},
        ],
    },
    "Custom Structure": {
        "profile": "Custom",
        "description": "Build any custom class hierarchy, naming scheme, groups, shifts, and sections.",
        "classes": [],
    },
}


class AcademicService:
    @staticmethod
    def _log(
        db: Session,
        action: str,
        description: str,
        username: str = "admin",
        entity_type: Optional[str] = None,
        entity_id: Optional[Any] = None,
        severity: str = "INFO",
    ) -> None:
        DatabaseService.log_activity(
            db,
            action=action,
            module="ACADEMICS",
            description=description,
            username=username,
            severity=severity,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            commit=False,
        )

    @staticmethod
    def ensure_academic_defaults(db: Session) -> Dict[str, Any]:
        """Ensure standard academic groups, shifts, and HR departments exist."""
        groups = AcademicRepository.get_or_create_default_groups(db)
        shifts = AcademicRepository.get_or_create_default_shifts(db)
        from app.repositories.staff_repository import StaffRepository
        depts = StaffRepository.get_or_create_departments(db)
        return {"groups": groups, "shifts": shifts, "departments": depts}

    @staticmethod
    def generate_subject_id(db: Session) -> str:
        year = datetime.now().year
        seq = db.query(Subject).count() + 1
        existing = {r[0] for r in db.query(Subject.subject_id).all()}
        while True:
            cand = f"SUB-{year}-{seq:04d}"
            if cand not in existing:
                return cand
            seq += 1

    # ==================== ACADEMIC YEARS ====================
    @staticmethod
    def create_academic_year(
        db: Session, year_data: Dict[str, Any], current_user: str = "admin"
    ) -> Tuple[Optional[AcademicYear], str]:
        name = (year_data.get("name") or "").strip()
        start_d = year_data.get("start_date")
        end_d = year_data.get("end_date")
        if not name or not start_d or not end_d:
            return None, "Academic year name, start date, and end date are required."
        if end_d < start_d:
            return None, "End date cannot be earlier than start date."

        dup = db.query(AcademicYear).filter(AcademicYear.name == name).first()
        if dup:
            return None, f"Academic year '{name}' already exists."

        payload = dict(year_data)
        payload["name"] = name
        ay = AcademicRepository.create_academic_year(db, payload)
        AcademicService._log(
            db,
            "CREATE_ACADEMIC_YEAR",
            f"Created academic year '{ay.name}' ({ay.start_date} to {ay.end_date}, current={ay.is_current})",
            username=current_user,
            entity_type="AcademicYear",
            entity_id=ay.id,
        )
        db.commit()
        return ay, f"Academic year '{ay.name}' created successfully."

    @staticmethod
    def update_academic_year(
        db: Session, year_id: int, updates: Dict[str, Any], current_user: str = "admin"
    ) -> Tuple[Optional[AcademicYear], str]:
        ay = AcademicRepository.get_academic_year_by_id(db, year_id)
        if not ay:
            return None, "Academic year not found."

        s_date = updates.get("start_date", ay.start_date)
        e_date = updates.get("end_date", ay.end_date)
        if e_date < s_date:
            return None, "End date cannot be earlier than start date."

        updated = AcademicRepository.update_academic_year(db, year_id, updates)
        AcademicService._log(
            db,
            "UPDATE_ACADEMIC_YEAR",
            f"Updated academic year '{updated.name}' (status={updated.status}, current={updated.is_current})",
            username=current_user,
            entity_type="AcademicYear",
            entity_id=updated.id,
        )
        db.commit()
        return updated, f"Academic year '{updated.name}' updated."

    @staticmethod
    def activate_academic_year(
        db: Session, year_id: int, current_user: str = "admin"
    ) -> Tuple[Optional[AcademicYear], str]:
        ay = AcademicRepository.set_active_academic_year(db, year_id)
        if not ay:
            return None, "Academic year not found."
        AcademicService._log(
            db,
            "ACTIVATE_ACADEMIC_YEAR",
            f"Activated academic session '{ay.name}' (historical years preserved untouched).",
            username=current_user,
            entity_type="AcademicYear",
            entity_id=ay.id,
        )
        db.commit()
        return ay, f"Academic year '{ay.name}' is now active."

    @staticmethod
    def close_academic_year(
        db: Session, year_id: int, current_user: str = "admin"
    ) -> Tuple[Optional[AcademicYear], str]:
        ay = AcademicRepository.get_academic_year_by_id(db, year_id)
        if not ay:
            return None, "Academic year not found."
        updated = AcademicRepository.update_academic_year(
            db, year_id, {"status": "Completed", "is_current": False}
        )
        AcademicService._log(
            db,
            "CLOSE_ACADEMIC_YEAR",
            f"Closed academic session '{updated.name}' as Completed (historical records locked).",
            username=current_user,
            entity_type="AcademicYear",
            entity_id=updated.id,
        )
        db.commit()
        return updated, f"Academic year '{updated.name}' marked as Completed."

    # ==================== GROUPS, SHIFTS, DEPARTMENTS & ROOMS ====================
    @staticmethod
    def create_group(
        db: Session, data: Dict[str, Any], current_user: str = "admin"
    ) -> Tuple[Optional[AcademicGroup], str]:
        name = (data.get("name") or "").strip()
        code = (data.get("code") or "").strip().upper()
        if not name or not code:
            return None, "Group name and code are required."
        if db.query(AcademicGroup).filter((AcademicGroup.name == name) | (AcademicGroup.code == code)).first():
            return None, f"Academic group '{name}' ({code}) already exists."
        grp = AcademicRepository.create_group(
            db,
            {
                "name": name,
                "code": code,
                "description": (data.get("description") or "").strip() or None,
                "display_order": int(data.get("display_order", 1)),
                "is_active": bool(data.get("is_active", True)),
            },
        )
        AcademicService._log(db, "CREATE_GROUP", f"Created group '{grp.name}' ({grp.code})", username=current_user)
        db.commit()
        return grp, f"Academic group '{grp.name}' created."

    @staticmethod
    def create_shift(
        db: Session, data: Dict[str, Any], current_user: str = "admin"
    ) -> Tuple[Optional[AcademicShift], str]:
        name = (data.get("name") or "").strip()
        code = (data.get("code") or "").strip().upper()
        if not name or not code:
            return None, "Shift name and code are required."
        if db.query(AcademicShift).filter((AcademicShift.name == name) | (AcademicShift.code == code)).first():
            return None, f"Academic shift '{name}' ({code}) already exists."
        sh = AcademicRepository.create_shift(
            db,
            {
                "name": name,
                "code": code,
                "start_time": (data.get("start_time") or "").strip() or None,
                "end_time": (data.get("end_time") or "").strip() or None,
                "description": (data.get("description") or "").strip() or None,
                "display_order": int(data.get("display_order", 1)),
                "is_active": bool(data.get("is_active", True)),
            },
        )
        AcademicService._log(db, "CREATE_SHIFT", f"Created shift '{sh.name}' ({sh.code})", username=current_user)
        db.commit()
        return sh, f"Academic shift '{sh.name}' created."

    @staticmethod
    def create_department(
        db: Session, data: Dict[str, Any], current_user: str = "admin"
    ) -> Tuple[Optional[Department], str]:
        name = (data.get("name") or "").strip()
        code = (data.get("code") or "").strip().upper()
        if not name or not code:
            return None, "Department name and code are required."
        if db.query(Department).filter((Department.name == name) | (Department.code == code)).first():
            return None, f"Department '{name}' ({code}) already exists."
        dept = AcademicRepository.create_department(
            db,
            {
                "name": name,
                "code": code,
                "description": (data.get("description") or "").strip() or None,
            },
        )
        AcademicService._log(db, "CREATE_DEPARTMENT", f"Created department '{dept.name}' ({dept.code})", username=current_user)
        db.commit()
        return dept, f"Department '{dept.name}' created."

    @staticmethod
    def create_room(
        db: Session, data: Dict[str, Any], current_user: str = "admin"
    ) -> Tuple[Optional[AcademicRoom], str]:
        room_no = (data.get("room_number") or "").strip()
        if not room_no:
            return None, "Room number is required."
        cap = int(data.get("capacity", 50))
        if cap <= 0:
            return None, "Room capacity must be greater than zero."
        if db.query(AcademicRoom).filter(AcademicRoom.room_number == room_no).first():
            return None, f"Room '{room_no}' already exists."
        room = AcademicRepository.create_room(
            db,
            {
                "room_number": room_no,
                "room_name": (data.get("room_name") or "").strip() or None,
                "building": (data.get("building") or "Main Building").strip(),
                "floor": (data.get("floor") or "Ground").strip(),
                "room_type": (data.get("room_type") or "Classroom").strip(),
                "capacity": cap,
                "facilities": (data.get("facilities") or "").strip() or None,
                "is_active": bool(data.get("is_active", True)),
            },
        )
        AcademicService._log(db, "CREATE_ROOM", f"Created room '{room.room_number}' (Cap: {room.capacity})", username=current_user)
        db.commit()
        return room, f"Room '{room.room_number}' created."

    @staticmethod
    def update_room(
        db: Session, room_id: int, updates: Dict[str, Any], current_user: str = "admin"
    ) -> Tuple[Optional[AcademicRoom], str]:
        if "capacity" in updates and int(updates["capacity"]) <= 0:
            return None, "Room capacity must be greater than zero."
        room = AcademicRepository.update_room(db, room_id, updates)
        if not room:
            return None, "Room not found."
        # Keep synced section room_number labels up to date cleanly
        db.query(Section).filter(Section.room_id == room.id).update(
            {Section.room_number: room.room_number}, synchronize_session=False
        )
        AcademicService._log(db, "UPDATE_ROOM", f"Updated room '{room.room_number}'", username=current_user)
        db.commit()
        return room, f"Room '{room.room_number}' updated."

    # ==================== CLASSES ====================
    @staticmethod
    def _resolve_group_shift_ids(db: Session, payload: Dict[str, Any]) -> None:
        if payload.get("group_id") and not payload.get("group"):
            grp = db.query(AcademicGroup).filter(AcademicGroup.id == payload["group_id"]).first()
            if grp:
                payload["group"] = grp.name
        elif payload.get("group") and not payload.get("group_id"):
            grp = db.query(AcademicGroup).filter(AcademicGroup.name == payload["group"]).first()
            if grp:
                payload["group_id"] = grp.id

        if payload.get("shift_id") and not payload.get("shift"):
            sh = db.query(AcademicShift).filter(AcademicShift.id == payload["shift_id"]).first()
            if sh:
                payload["shift"] = sh.name
        elif payload.get("shift") and not payload.get("shift_id"):
            sh = db.query(AcademicShift).filter(AcademicShift.name == payload["shift"]).first()
            if sh:
                payload["shift_id"] = sh.id

    @staticmethod
    def create_class(
        db: Session,
        class_data: dict,
        current_user: str = "admin",
        allow_multi_stream: bool = False,
    ) -> Tuple[Optional[SchoolClass], str]:
        payload = dict(class_data)
        name = (payload.get("name") or "").strip()
        if not name:
            return None, "Class name is required."
        payload["name"] = name
        ay_id = payload.get("academic_year_id")
        if not ay_id:
            return None, "Academic year is required."

        AcademicService._resolve_group_shift_ids(db, payload)
        grp = payload.get("group") or "General"
        sh = payload.get("shift") or "Morning"
        payload["group"] = grp
        payload["shift"] = sh

        if allow_multi_stream:
            existing = (
                db.query(SchoolClass)
                .filter(
                    SchoolClass.name == name,
                    SchoolClass.academic_year_id == ay_id,
                    SchoolClass.group == grp,
                    SchoolClass.shift == sh,
                    SchoolClass.is_deleted == False,
                )
                .first()
            )
            if existing:
                return (
                    None,
                    f"Class '{name}' ({grp} / {sh}) already exists in this academic year.",
                )
        else:
            existing = (
                db.query(SchoolClass)
                .filter(
                    SchoolClass.name == name,
                    SchoolClass.academic_year_id == ay_id,
                    SchoolClass.is_deleted == False,
                )
                .first()
            )
            if existing:
                return None, f"Class '{name}' already exists in this academic year."

        new_class = AcademicRepository.create_class(db, payload)
        AcademicService._log(
            db,
            "CREATE_CLASS",
            f"Created class '{new_class.name}' (Code: {new_class.code}, Group: {new_class.group}, Profile: {new_class.structure_profile})",
            username=current_user,
            entity_type="SchoolClass",
            entity_id=new_class.id,
        )
        db.commit()
        app_logger.info(f"Class '{new_class.name}' created by {current_user}")
        return new_class, "Class created successfully."

    @staticmethod
    def update_class(
        db: Session, class_id: int, updates: dict, current_user: str = "admin"
    ) -> Tuple[Optional[SchoolClass], str]:
        payload = dict(updates)
        AcademicService._resolve_group_shift_ids(db, payload)
        cls_obj = AcademicRepository.update_class(db, class_id, payload)
        if not cls_obj:
            return None, "Class not found."

        AcademicService._log(
            db,
            "UPDATE_CLASS",
            f"Updated details for class '{cls_obj.name}'",
            username=current_user,
            entity_type="SchoolClass",
            entity_id=cls_obj.id,
        )
        db.commit()
        return cls_obj, "Class updated successfully."

    @staticmethod
    def safe_delete_class(
        db: Session, class_id: int, current_user: str = "admin"
    ) -> Tuple[bool, str]:
        """Delete a class ONLY if no historical or current student records depend on it."""
        cls_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        if not cls_obj:
            return False, "Class not found."

        has_students = db.query(Student.id).filter(Student.class_id == class_id).first()
        has_history = db.query(StudentAcademicHistory.id).filter(StudentAcademicHistory.class_id == class_id).first()
        has_prom = (
            db.query(StudentPromotionHistory.id)
            .filter(
                (StudentPromotionHistory.from_class_id == class_id)
                | (StudentPromotionHistory.to_class_id == class_id)
            )
            .first()
        )
        has_xfer = (
            db.query(StudentTransferHistory.id)
            .filter(
                (StudentTransferHistory.from_class_id == class_id)
                | (StudentTransferHistory.to_class_id == class_id)
            )
            .first()
        )
        if has_students or has_history or has_prom or has_xfer:
            return (
                False,
                f"Cannot delete '{cls_obj.name}': historical or current student enrollment records depend on it.",
            )

        cls_name = cls_obj.name
        AcademicRepository.delete_class(db, class_id)
        AcademicService._log(db, "DELETE_CLASS", f"Deleted unused class '{cls_name}'", username=current_user)
        db.commit()
        return True, f"Class '{cls_name}' deleted."

    # ==================== SECTIONS & CLASS TEACHERS ====================
    @staticmethod
    def _sync_section_links(db: Session, payload: Dict[str, Any]) -> None:
        AcademicService._resolve_group_shift_ids(db, payload)
        if payload.get("room_id"):
            room = db.query(AcademicRoom).filter(AcademicRoom.id == payload["room_id"]).first()
            if room and not payload.get("room_number"):
                payload["room_number"] = room.room_number
        elif payload.get("room_number") and not payload.get("room_id"):
            room = db.query(AcademicRoom).filter(AcademicRoom.room_number == payload["room_number"]).first()
            if room:
                payload["room_id"] = room.id

    @staticmethod
    def create_section(
        db: Session, section_data: dict, current_user: str = "admin"
    ) -> Tuple[Optional[Section], str]:
        payload = dict(section_data)
        name = (payload.get("name") or "").strip()
        if not name:
            return None, "Section name is required."
        payload["name"] = name

        existing = (
            db.query(Section)
            .filter(
                Section.name == name,
                Section.class_id == payload.get("class_id"),
                Section.is_deleted == False,
            )
            .first()
        )
        if existing:
            return None, f"Section '{name}' already exists in this class."

        AcademicService._sync_section_links(db, payload)
        sec = AcademicRepository.create_section(db, payload)
        AcademicService._log(
            db,
            "CREATE_SECTION",
            f"Created section '{sec.name}' for Class ID {sec.class_id} (Room: {sec.room_number})",
            username=current_user,
            entity_type="Section",
            entity_id=sec.id,
        )
        db.commit()
        return sec, "Section created successfully."

    @staticmethod
    def update_section(
        db: Session, section_id: int, updates: dict, current_user: str = "admin"
    ) -> Tuple[Optional[Section], str]:
        payload = dict(updates)
        AcademicService._sync_section_links(db, payload)
        sec = AcademicRepository.update_section(db, section_id, payload)
        if not sec:
            return None, "Section not found."
        AcademicService._log(
            db,
            "UPDATE_SECTION",
            f"Updated section '{sec.name}' (Class ID: {sec.class_id})",
            username=current_user,
            entity_type="Section",
            entity_id=sec.id,
        )
        db.commit()
        return sec, "Section updated successfully."

    @staticmethod
    def assign_class_teacher(
        db: Session, section_id: int, teacher_id: Optional[int], current_user: str = "admin"
    ) -> Tuple[Optional[Section], str]:
        sec = AcademicRepository.get_section_by_id(db, section_id)
        if not sec:
            return None, "Section not found."
        if teacher_id is not None:
            teacher = db.query(Teacher).filter(Teacher.id == teacher_id, Teacher.is_deleted == False).first()
            if not teacher:
                return None, "Selected teacher not found."
            t_label = teacher.full_name
        else:
            t_label = "Unassigned"

        updated = AcademicRepository.update_section(db, section_id, {"class_teacher_id": teacher_id})
        AcademicService._log(
            db,
            "ASSIGN_CLASS_TEACHER",
            f"Assigned class teacher '{t_label}' to section '{sec.name}' (Class ID {sec.class_id})",
            username=current_user,
            entity_type="Section",
            entity_id=sec.id,
        )
        db.commit()
        return updated, f"Class teacher set to {t_label}."

    @staticmethod
    def safe_delete_section(
        db: Session, section_id: int, current_user: str = "admin"
    ) -> Tuple[bool, str]:
        sec = db.query(Section).filter(Section.id == section_id).first()
        if not sec:
            return False, "Section not found."
        if (
            db.query(Student.id).filter(Student.section_id == section_id).first()
            or db.query(StudentAcademicHistory.id).filter(StudentAcademicHistory.section_id == section_id).first()
            or db.query(StudentPromotionHistory.id)
            .filter(
                (StudentPromotionHistory.from_section_id == section_id)
                | (StudentPromotionHistory.to_section_id == section_id)
            )
            .first()
        ):
            return False, f"Cannot delete section '{sec.name}': students or historical records depend on it."
        s_name = sec.name
        AcademicRepository.delete_section(db, section_id)
        AcademicService._log(db, "DELETE_SECTION", f"Deleted unused section '{s_name}'", username=current_user)
        db.commit()
        return True, f"Section '{s_name}' deleted."

    # ==================== SUBJECTS, OPTIONAL SUBJECTS & TEACHERS ====================
    @staticmethod
    def create_subject(
        db: Session, subject_data: dict, current_user: str = "admin"
    ) -> Tuple[Optional[Subject], str]:
        payload = dict(subject_data)
        full_marks = int(payload.get("full_marks", 100))
        pass_marks = int(payload.get("pass_marks", 33))
        theory = int(payload.get("theory_marks", 75))
        practical = int(payload.get("practical_marks", 25))

        if pass_marks > full_marks:
            return None, "Pass marks cannot exceed full marks."
        if theory + practical != full_marks:
            payload["theory_marks"] = full_marks - practical

        sub_type = (payload.get("subject_type") or "Mandatory").strip()
        payload["subject_type"] = sub_type
        if "is_optional" not in payload:
            payload["is_optional"] = sub_type in ("Optional", "Elective")

        if not payload.get("subject_id"):
            payload["subject_id"] = AcademicService.generate_subject_id(db)

        existing = (
            db.query(Subject)
            .filter(
                Subject.code == payload.get("code"),
                Subject.class_id == payload.get("class_id"),
                Subject.is_deleted == False,
            )
            .first()
        )
        if existing:
            return None, f"Subject code '{payload.get('code')}' is already registered for this class."

        sub = AcademicRepository.create_subject(db, payload)
        if sub.teacher_id:
            AcademicService._ensure_teacher_subject_assignment(
                db, teacher_id=sub.teacher_id, subject=sub, weekly_periods=5
            )
        AcademicService._log(
            db,
            "CREATE_SUBJECT",
            f"Created {sub.subject_type} subject '{sub.name}' (Code: {sub.code}, Class ID: {sub.class_id})",
            username=current_user,
            entity_type="Subject",
            entity_id=sub.id,
        )
        db.commit()
        return sub, "Subject created successfully."

    @staticmethod
    def update_subject(
        db: Session, subject_id_pk: int, updates: dict, current_user: str = "admin"
    ) -> Tuple[Optional[Subject], str]:
        payload = dict(updates)
        if "subject_type" in payload and "is_optional" not in payload:
            payload["is_optional"] = payload["subject_type"] in ("Optional", "Elective")
        sub = AcademicRepository.update_subject(db, subject_id_pk, payload)
        if not sub:
            return None, "Subject not found."
        if sub.teacher_id:
            AcademicService._ensure_teacher_subject_assignment(
                db, teacher_id=sub.teacher_id, subject=sub, weekly_periods=5
            )
        AcademicService._log(
            db,
            "UPDATE_SUBJECT",
            f"Updated subject '{sub.name}' (Code: {sub.code})",
            username=current_user,
            entity_type="Subject",
            entity_id=sub.id,
        )
        db.commit()
        return sub, "Subject updated successfully."

    @staticmethod
    def _ensure_teacher_subject_assignment(
        db: Session,
        teacher_id: int,
        subject: Subject,
        section_id: Optional[int] = None,
        weekly_periods: int = 5,
    ) -> None:
        cls_obj = db.query(SchoolClass).filter(SchoolClass.id == subject.class_id).first()
        if not cls_obj:
            return
        existing = (
            db.query(TeacherSubjectAssignment)
            .filter_by(
                teacher_id=teacher_id,
                subject_id=subject.id,
                class_id=subject.class_id,
                section_id=section_id,
                academic_year_id=cls_obj.academic_year_id,
            )
            .first()
        )
        if not existing:
            db.add(
                TeacherSubjectAssignment(
                    teacher_id=teacher_id,
                    subject_id=subject.id,
                    class_id=subject.class_id,
                    section_id=section_id,
                    academic_year_id=cls_obj.academic_year_id,
                    is_primary=True,
                    weekly_periods=weekly_periods,
                    remarks="Synced from Academic Curriculum",
                )
            )

    @staticmethod
    def assign_subject_teacher(
        db: Session,
        subject_pk: int,
        teacher_id: Optional[int],
        section_id: Optional[int] = None,
        weekly_periods: int = 5,
        current_user: str = "admin",
    ) -> Tuple[Optional[Subject], str]:
        sub = AcademicRepository.get_subject_by_id(db, subject_pk)
        if not sub:
            return None, "Subject not found."
        if teacher_id is not None:
            teacher = db.query(Teacher).filter(Teacher.id == teacher_id, Teacher.is_deleted == False).first()
            if not teacher:
                return None, "Selected teacher not found."
            t_label = teacher.full_name
        else:
            t_label = "Unassigned"

        updated = AcademicRepository.update_subject(db, subject_pk, {"teacher_id": teacher_id})
        if teacher_id is not None and updated:
            AcademicService._ensure_teacher_subject_assignment(
                db, teacher_id=teacher_id, subject=updated, section_id=section_id, weekly_periods=weekly_periods
            )
        AcademicService._log(
            db,
            "ASSIGN_SUBJECT_TEACHER",
            f"Assigned subject teacher '{t_label}' to '{sub.name}' ({sub.code})",
            username=current_user,
            entity_type="Subject",
            entity_id=sub.id,
        )
        db.commit()
        return updated, f"Subject teacher set to {t_label}."

    @staticmethod
    def safe_delete_subject(
        db: Session, subject_pk: int, current_user: str = "admin"
    ) -> Tuple[bool, str]:
        sub = db.query(Subject).filter(Subject.id == subject_pk).first()
        if not sub:
            return False, "Subject not found."
        if (
            db.query(StudentMark.id).filter(StudentMark.subject_id == subject_pk).first()
            or db.query(StudentSubjectEnrollment.id).filter(StudentSubjectEnrollment.subject_id == subject_pk).first()
        ):
            return (
                False,
                f"Cannot delete subject '{sub.name}': historical exam marks or student enrollments exist.",
            )
        s_name = sub.name
        AcademicRepository.delete_subject(db, subject_pk)
        AcademicService._log(db, "DELETE_SUBJECT", f"Deleted unused subject '{s_name}'", username=current_user)
        db.commit()
        return True, f"Subject '{s_name}' deleted."

    @staticmethod
    def enroll_student_subject(
        db: Session,
        student_id: int,
        subject_id: int,
        academic_year_id: Optional[int] = None,
        is_optional: Optional[bool] = None,
        remarks: Optional[str] = None,
        current_user: str = "admin",
    ) -> Tuple[Optional[StudentSubjectEnrollment], str]:
        student = db.query(Student).filter(Student.id == student_id, Student.is_deleted == False).first()
        if not student:
            return None, "Student not found."
        subject = db.query(Subject).filter(Subject.id == subject_id, Subject.is_deleted == False).first()
        if not subject:
            return None, "Subject not found."

        cls_obj = db.query(SchoolClass).filter(SchoolClass.id == subject.class_id).first()
        target_ay_id = academic_year_id or (cls_obj.academic_year_id if cls_obj else student.academic_year_id)

        if subject.class_id != student.class_id:
            return (
                None,
                f"Subject '{subject.name}' belongs to a different class than the student's current class.",
            )

        existing = (
            db.query(StudentSubjectEnrollment)
            .filter_by(student_id=student.id, academic_year_id=target_ay_id, subject_id=subject.id)
            .first()
        )
        opt_flag = bool(subject.is_optional or subject.subject_type in ("Optional", "Elective")) if is_optional is None else bool(is_optional)

        if existing:
            existing.enrollment_status = "Active"
            existing.is_optional = opt_flag
            if remarks is not None:
                existing.remarks = remarks
            rec = existing
        else:
            rec = StudentSubjectEnrollment(
                student_id=student.id,
                academic_year_id=target_ay_id,
                class_id=subject.class_id,
                subject_id=subject.id,
                is_optional=opt_flag,
                enrollment_status="Active",
                enrolled_date=date.today(),
                remarks=remarks,
            )
            db.add(rec)

        AcademicService._log(
            db,
            "ENROLL_STUDENT_SUBJECT",
            f"Enrolled student '{student.full_name}' in {'Optional' if opt_flag else 'Mandatory'} subject '{subject.name}'",
            username=current_user,
            entity_type="StudentSubjectEnrollment",
        )
        db.commit()
        db.refresh(rec)
        return rec, f"Enrolled '{student.full_name}' in '{subject.name}'."

    @staticmethod
    def drop_student_subject(
        db: Session, enrollment_id: int, current_user: str = "admin"
    ) -> Tuple[bool, str]:
        rec = db.query(StudentSubjectEnrollment).filter(StudentSubjectEnrollment.id == enrollment_id).first()
        if not rec:
            return False, "Subject enrollment record not found."
        rec.enrollment_status = "Dropped"
        AcademicService._log(
            db,
            "DROP_STUDENT_SUBJECT",
            f"Marked subject enrollment #{rec.id} as Dropped",
            username=current_user,
            entity_type="StudentSubjectEnrollment",
            entity_id=rec.id,
        )
        db.commit()
        return True, "Optional subject dropped."

    @staticmethod
    def get_student_subjects(
        db: Session, student_id: int, academic_year_id: Optional[int] = None
    ) -> List[StudentSubjectEnrollment]:
        return AcademicRepository.list_student_subject_enrollments(
            db, student_id=student_id, academic_year_id=academic_year_id
        )

    # ==================== NON-DESTRUCTIVE CLONING & CONFIGURATION WIZARD ====================
    @staticmethod
    def get_preset_structure(preset_name: str) -> Dict[str, Any]:
        return STRUCTURE_PRESETS.get(preset_name, STRUCTURE_PRESETS["Custom Structure"])

    @staticmethod
    def clone_academic_structure(
        db: Session,
        source_year_id: int,
        target_year_id: int,
        include_sections: bool = True,
        include_subjects: bool = True,
        copy_teachers: bool = True,
        current_user: str = "admin",
    ) -> Tuple[bool, Dict[str, int], str]:
        """
        Clone classes, sections, and subjects from `source_year_id` into `target_year_id`
        as brand-new records. NEVER mutates or overwrites `source_year_id` records.
        """
        if source_year_id == target_year_id:
            return False, {}, "Source and target academic years must be different."

        src_year = AcademicRepository.get_academic_year_by_id(db, source_year_id)
        tgt_year = AcademicRepository.get_academic_year_by_id(db, target_year_id)
        if not src_year or not tgt_year:
            return False, {}, "Source or target academic year not found."

        src_classes = AcademicRepository.get_classes(db, academic_year_id=source_year_id, include_inactive=False)
        if not src_classes:
            return False, {}, f"No classes found in source year '{src_year.name}' to clone."

        counts = {"classes_created": 0, "sections_created": 0, "subjects_created": 0, "classes_skipped": 0}
        try:
            for s_cls in src_classes:
                dup = (
                    db.query(SchoolClass)
                    .filter(
                        SchoolClass.academic_year_id == target_year_id,
                        SchoolClass.name == s_cls.name,
                        SchoolClass.group == s_cls.group,
                        SchoolClass.shift == s_cls.shift,
                        SchoolClass.is_deleted == False,
                    )
                    .first()
                )
                if dup:
                    counts["classes_skipped"] += 1
                    new_cls = dup
                else:
                    new_cls = SchoolClass(
                        name=s_cls.name,
                        code=s_cls.code,
                        numeric_order=s_cls.numeric_order,
                        group=s_cls.group,
                        shift=s_cls.shift,
                        academic_year_id=target_year_id,
                        department_id=s_cls.department_id,
                        group_id=s_cls.group_id,
                        shift_id=s_cls.shift_id,
                        structure_profile=s_cls.structure_profile,
                        max_sections=s_cls.max_sections,
                        is_active=True,
                    )
                    db.add(new_cls)
                    db.flush()
                    counts["classes_created"] += 1

                if include_sections:
                    for s_sec in s_cls.sections:
                        if s_sec.is_deleted:
                            continue
                        dup_sec = (
                            db.query(Section)
                            .filter(Section.class_id == new_cls.id, Section.name == s_sec.name)
                            .first()
                        )
                        if not dup_sec:
                            db.add(
                                Section(
                                    name=s_sec.name,
                                    room_number=s_sec.room_number,
                                    room_id=s_sec.room_id,
                                    capacity=s_sec.capacity,
                                    shift=s_sec.shift,
                                    shift_id=s_sec.shift_id,
                                    group=s_sec.group,
                                    group_id=s_sec.group_id,
                                    class_id=new_cls.id,
                                    class_teacher_id=s_sec.class_teacher_id if copy_teachers else None,
                                    is_active=True,
                                )
                            )
                            counts["sections_created"] += 1

                if include_subjects:
                    for s_sub in s_cls.subjects:
                        if s_sub.is_deleted:
                            continue
                        dup_sub = (
                            db.query(Subject)
                            .filter(Subject.class_id == new_cls.id, Subject.code == s_sub.code)
                            .first()
                        )
                        if not dup_sub:
                            new_sub_id = AcademicService.generate_subject_id(db)
                            new_sub = Subject(
                                subject_id=new_sub_id,
                                name=s_sub.name,
                                code=s_sub.code,
                                full_marks=s_sub.full_marks,
                                pass_marks=s_sub.pass_marks,
                                theory_marks=s_sub.theory_marks,
                                practical_marks=s_sub.practical_marks,
                                subject_type=s_sub.subject_type,
                                is_optional=s_sub.is_optional,
                                class_id=new_cls.id,
                                teacher_id=s_sub.teacher_id if copy_teachers else None,
                                department_id=s_sub.department_id,
                                group_id=s_sub.group_id,
                                credit_hours=s_sub.credit_hours,
                                description=s_sub.description,
                                is_active=True,
                            )
                            db.add(new_sub)
                            db.flush()
                            counts["subjects_created"] += 1

            AcademicService._log(
                db,
                "CLONE_ACADEMIC_STRUCTURE",
                (
                    f"Cloned structure from '{src_year.name}' -> '{tgt_year.name}': "
                    f"{counts['classes_created']} classes, {counts['sections_created']} sections, "
                    f"{counts['subjects_created']} subjects (source year untouched)."
                ),
                username=current_user,
                entity_type="AcademicYear",
                entity_id=target_year_id,
            )
            db.commit()
            return (
                True,
                counts,
                f"Cloned {counts['classes_created']} classes, {counts['sections_created']} sections, and {counts['subjects_created']} subjects into '{tgt_year.name}'.",
            )
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Failed cloning structure: {exc}")
            return False, counts, str(exc)

    @staticmethod
    def apply_academic_configuration_wizard(
        db: Session, config: Dict[str, Any], current_user: str = "admin"
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        Atomically provision a complete academic structure from the Configuration Wizard:
        1. Create or reuse target AcademicYear
        2. Ensure Groups, Shifts, Departments, and optional custom Rooms
        3. Optional clone from previous AcademicYear OR build custom class structure
        4. Provision Sections, Rooms, Class Teachers, and Subjects
        Never overwrites prior academic year records.
        """
        try:
            AcademicService.ensure_academic_defaults(db)

            # 1. Target Academic Year
            target_ay_id = config.get("academic_year_id")
            if target_ay_id:
                target_ay = AcademicRepository.get_academic_year_by_id(db, target_ay_id)
                if not target_ay:
                    return False, {}, "Selected target academic year not found."
                if config.get("activate_year"):
                    AcademicRepository.set_active_academic_year(db, target_ay.id)
            else:
                ay_cfg = config.get("academic_year") or {}
                ay_name = (ay_cfg.get("name") or "").strip()
                s_date = ay_cfg.get("start_date")
                e_date = ay_cfg.get("end_date")
                if not ay_name or not s_date or not e_date:
                    return False, {}, "Academic year name, start date, and end date are required."
                if e_date < s_date:
                    return False, {}, "Academic year end date cannot precede start date."

                existing_ay = db.query(AcademicYear).filter(AcademicYear.name == ay_name).first()
                if existing_ay:
                    target_ay = existing_ay
                else:
                    if ay_cfg.get("is_current", True):
                        db.query(AcademicYear).update({AcademicYear.is_current: False})
                    target_ay = AcademicYear(
                        name=ay_name,
                        start_date=s_date,
                        end_date=e_date,
                        is_current=bool(ay_cfg.get("is_current", True)),
                        status=ay_cfg.get("status", "Active"),
                    )
                    db.add(target_ay)
                    db.flush()

            summary: Dict[str, Any] = {
                "academic_year_id": target_ay.id,
                "academic_year_name": target_ay.name,
                "groups_created": 0,
                "shifts_created": 0,
                "rooms_created": 0,
                "classes_created": 0,
                "sections_created": 0,
                "subjects_created": 0,
            }

            # 2. Custom Groups / Shifts / Rooms
            for g in config.get("groups") or []:
                g_name = (g.get("name") or "").strip()
                g_code = (g.get("code") or g_name[:4]).strip().upper()
                if g_name and not db.query(AcademicGroup).filter(
                    (AcademicGroup.name == g_name) | (AcademicGroup.code == g_code)
                ).first():
                    db.add(AcademicGroup(name=g_name, code=g_code, description=g.get("description")))
                    db.flush()
                    summary["groups_created"] += 1

            for sh in config.get("shifts") or []:
                sh_name = (sh.get("name") or "").strip()
                sh_code = (sh.get("code") or sh_name[:4]).strip().upper()
                if sh_name and not db.query(AcademicShift).filter(
                    (AcademicShift.name == sh_name) | (AcademicShift.code == sh_code)
                ).first():
                    db.add(
                        AcademicShift(
                            name=sh_name,
                            code=sh_code,
                            start_time=sh.get("start_time"),
                            end_time=sh.get("end_time"),
                        )
                    )
                    db.flush()
                    summary["shifts_created"] += 1

            for rm in config.get("rooms") or []:
                r_no = (rm.get("room_number") or "").strip()
                if r_no and not db.query(AcademicRoom).filter(AcademicRoom.room_number == r_no).first():
                    db.add(
                        AcademicRoom(
                            room_number=r_no,
                            room_name=rm.get("room_name"),
                            building=rm.get("building") or "Main Building",
                            floor=rm.get("floor") or "Ground",
                            room_type=rm.get("room_type") or "Classroom",
                            capacity=max(1, int(rm.get("capacity", 50))),
                        )
                    )
                    db.flush()
                    summary["rooms_created"] += 1

            # 3. Optional Clone Mode
            clone_src_id = config.get("clone_from_year_id")
            if clone_src_id:
                ok_clone, clone_counts, clone_msg = AcademicService.clone_academic_structure(
                    db,
                    source_year_id=clone_src_id,
                    target_year_id=target_ay.id,
                    include_sections=bool(config.get("clone_sections", True)),
                    include_subjects=bool(config.get("clone_subjects", True)),
                    copy_teachers=bool(config.get("clone_teachers", True)),
                    current_user=current_user,
                )
                if not ok_clone:
                    return False, summary, clone_msg
                summary["classes_created"] += clone_counts.get("classes_created", 0)
                summary["sections_created"] += clone_counts.get("sections_created", 0)
                summary["subjects_created"] += clone_counts.get("subjects_created", 0)

            # 4. Custom Class Structure Specs
            structure_profile = config.get("structure_profile") or "Custom"
            for cls_spec in config.get("classes") or []:
                c_name = (cls_spec.get("name") or "").strip()
                if not c_name:
                    continue
                c_group = (cls_spec.get("group") or "General").strip()
                c_shift = (cls_spec.get("shift") or "Morning").strip()

                cls_obj = (
                    db.query(SchoolClass)
                    .filter(
                        SchoolClass.academic_year_id == target_ay.id,
                        SchoolClass.name == c_name,
                        SchoolClass.group == c_group,
                        SchoolClass.shift == c_shift,
                        SchoolClass.is_deleted == False,
                    )
                    .first()
                )
                if not cls_obj:
                    grp_row = db.query(AcademicGroup).filter(AcademicGroup.name == c_group).first()
                    sh_row = db.query(AcademicShift).filter(AcademicShift.name == c_shift).first()
                    cls_obj = SchoolClass(
                        name=c_name,
                        code=(cls_spec.get("code") or "").strip() or None,
                        numeric_order=int(cls_spec.get("numeric_order", 1)),
                        group=c_group,
                        shift=c_shift,
                        group_id=grp_row.id if grp_row else None,
                        shift_id=sh_row.id if sh_row else None,
                        department_id=cls_spec.get("department_id"),
                        structure_profile=cls_spec.get("structure_profile") or structure_profile,
                        academic_year_id=target_ay.id,
                    )
                    db.add(cls_obj)
                    db.flush()
                    summary["classes_created"] += 1

                # Sections inside class
                sec_list = cls_spec.get("sections") or []
                for sec_item in sec_list:
                    if isinstance(sec_item, str):
                        sec_cfg = {"name": sec_item}
                    else:
                        sec_cfg = dict(sec_item)
                    sec_name = (sec_cfg.get("name") or "").strip()
                    if not sec_name:
                        continue
                    dup_sec = (
                        db.query(Section)
                        .filter(Section.class_id == cls_obj.id, Section.name == sec_name)
                        .first()
                    )
                    if not dup_sec:
                        room_id = sec_cfg.get("room_id")
                        room_no = (sec_cfg.get("room_number") or "").strip() or None
                        if room_no and not room_id:
                            r_obj = db.query(AcademicRoom).filter(AcademicRoom.room_number == room_no).first()
                            room_id = r_obj.id if r_obj else None
                        elif room_id and not room_no:
                            r_obj = db.query(AcademicRoom).filter(AcademicRoom.id == room_id).first()
                            room_no = r_obj.room_number if r_obj else None
                        db.add(
                            Section(
                                name=sec_name,
                                room_number=room_no,
                                room_id=room_id,
                                capacity=max(1, int(sec_cfg.get("capacity", 50))),
                                shift=sec_cfg.get("shift") or c_shift,
                                shift_id=cls_obj.shift_id,
                                group=sec_cfg.get("group") or c_group,
                                group_id=cls_obj.group_id,
                                class_id=cls_obj.id,
                                class_teacher_id=sec_cfg.get("class_teacher_id"),
                            )
                        )
                        summary["sections_created"] += 1

                # Subjects inside class
                for sub_item in cls_spec.get("subjects") or []:
                    s_name = (sub_item.get("name") or "").strip()
                    s_code = (sub_item.get("code") or "").strip()
                    if not s_name or not s_code:
                        continue
                    dup_sub = (
                        db.query(Subject)
                        .filter(Subject.class_id == cls_obj.id, Subject.code == s_code)
                        .first()
                    )
                    if not dup_sub:
                        full_m = int(sub_item.get("full_marks", 100))
                        pass_m = min(full_m, int(sub_item.get("pass_marks", 33)))
                        prac_m = int(sub_item.get("practical_marks", 0))
                        theo_m = int(sub_item.get("theory_marks", full_m - prac_m))
                        if theo_m + prac_m != full_m:
                            theo_m = full_m - prac_m
                        s_type = (sub_item.get("subject_type") or "Mandatory").strip()
                        db.add(
                            Subject(
                                subject_id=AcademicService.generate_subject_id(db),
                                name=s_name,
                                code=s_code,
                                full_marks=full_m,
                                pass_marks=pass_m,
                                theory_marks=theo_m,
                                practical_marks=prac_m,
                                subject_type=s_type,
                                is_optional=bool(sub_item.get("is_optional", s_type in ("Optional", "Elective"))),
                                class_id=cls_obj.id,
                                teacher_id=sub_item.get("teacher_id"),
                                department_id=sub_item.get("department_id") or cls_obj.department_id,
                                group_id=cls_obj.group_id,
                                credit_hours=float(sub_item.get("credit_hours", 1.0)),
                            )
                        )
                        summary["subjects_created"] += 1

            AcademicService._log(
                db,
                "ACADEMIC_WIZARD_APPLIED",
                (
                    f"Applied Academic Configuration Wizard for '{target_ay.name}': "
                    f"+{summary['classes_created']} classes, +{summary['sections_created']} sections, "
                    f"+{summary['subjects_created']} subjects."
                ),
                username=current_user,
                entity_type="AcademicYear",
                entity_id=target_ay.id,
            )
            db.commit()
            return (
                True,
                summary,
                f"Configured session '{target_ay.name}' ({summary['classes_created']} classes, {summary['sections_created']} sections, {summary['subjects_created']} subjects).",
            )
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Academic configuration wizard error: {exc}")
            return False, {}, str(exc)

    # ==================== PROMOTIONS, TRANSFERS & ACADEMIC HISTORY ====================
    @staticmethod
    def _next_roll_for_class_year(
        db: Session, class_id: int, academic_year_id: int, section_id: Optional[int] = None
    ) -> int:
        query = db.query(func.max(Student.roll_number)).filter(
            Student.academic_year_id == academic_year_id,
            Student.class_id == class_id,
            Student.is_deleted == False,
        )
        if section_id is not None:
            query = query.filter(Student.section_id == section_id)
        max_roll = query.scalar()
        return (int(max_roll) + 1) if max_roll is not None else 1

    @staticmethod
    def _close_open_academic_history_non_destructive(
        db: Session,
        student: Student,
        closing_status: str,
        effective_date: date,
        remarks: str,
        gpa: Optional[float] = None,
        final_grade: Optional[str] = None,
    ) -> None:
        """
        Close the active StudentAcademicHistory row for the student's previous placement
        WITHOUT ever overwriting its academic_year_id, class_id, section_id, roll_number,
        group, or shift fields. If no open history row exists (e.g. legacy student),
        backfill a closed historical snapshot of the prior placement first.
        """
        open_row = (
            db.query(StudentAcademicHistory)
            .filter(
                StudentAcademicHistory.student_id == student.id,
                StudentAcademicHistory.academic_year_id == student.academic_year_id,
                StudentAcademicHistory.class_id == student.class_id,
                StudentAcademicHistory.result_status == "Enrolled",
            )
            .order_by(StudentAcademicHistory.id.desc())
            .first()
        )
        if open_row:
            open_row.result_status = closing_status
            open_row.end_date = effective_date
            if gpa is not None:
                open_row.gpa = gpa
            if final_grade is not None:
                open_row.final_grade = final_grade
            if remarks:
                open_row.remarks = remarks[:255]
        else:
            # Ensure historical placement is preserved even if student predated history tracking
            db.add(
                StudentAcademicHistory(
                    student_id=student.id,
                    academic_year_id=student.academic_year_id,
                    class_id=student.class_id,
                    section_id=student.section_id,
                    roll_number=student.roll_number,
                    group=student.group,
                    shift=student.shift,
                    gpa=gpa,
                    final_grade=final_grade,
                    result_status=closing_status,
                    start_date=student.admission_date or effective_date,
                    end_date=effective_date,
                    remarks=(remarks or "Closed historical placement")[:255],
                )
            )

    @staticmethod
    def promote_single_student(
        db: Session,
        student_id: int,
        to_class_id: Optional[int],
        to_academic_year_id: Optional[int],
        to_section_id: Optional[int] = None,
        new_roll_number: Optional[int] = None,
        gpa: Optional[float] = None,
        final_grade: Optional[str] = None,
        mark_graduated: bool = False,
        remarks: str = "Annual Academic Promotion",
        effective_date: Optional[date] = None,
        current_user: str = "admin",
    ) -> Tuple[bool, Optional[Student], str]:
        """
        Promote (or graduate) a single student to a target class/academic year.
        Strictly preserves all previous academic year history rows untouched.
        """
        try:
            student = db.query(Student).filter(Student.id == student_id, Student.is_deleted == False).first()
            if not student:
                return False, None, "Student not found."

            eff_date = effective_date or date.today()
            from_class_id = student.class_id
            from_section_id = student.section_id
            from_ay_id = student.academic_year_id
            from_roll = student.roll_number

            if mark_graduated:
                target_class_id = to_class_id or from_class_id
                target_ay_id = to_academic_year_id or from_ay_id
                target_sec_id = to_section_id if to_section_id is not None else from_section_id
                target_roll = new_roll_number if new_roll_number is not None else from_roll

                AcademicService._close_open_academic_history_non_destructive(
                    db,
                    student=student,
                    closing_status="Graduated",
                    effective_date=eff_date,
                    remarks=remarks or "Graduated",
                    gpa=gpa,
                    final_grade=final_grade,
                )
                db.add(
                    StudentPromotionHistory(
                        student_id=student.id,
                        from_class_id=from_class_id,
                        to_class_id=target_class_id,
                        from_section_id=from_section_id,
                        to_section_id=target_sec_id,
                        from_academic_year_id=from_ay_id,
                        to_academic_year_id=target_ay_id,
                        from_roll_number=from_roll,
                        to_roll_number=target_roll,
                        promotion_type="Graduated",
                        gpa=gpa,
                        final_grade=final_grade,
                        promoted_date=eff_date,
                        remarks=remarks or "Graduated",
                        promoted_by=current_user,
                    )
                )
                old_status = student.status
                student.status = StudentStatus.GRADUATED
                db.add(
                    StudentStatusHistory(
                        student_id=student.id,
                        from_status=old_status,
                        to_status=StudentStatus.GRADUATED,
                        effective_date=eff_date,
                        reason=remarks or "Graduated upon completing academic level",
                        changed_by=current_user,
                    )
                )
                AcademicService._log(
                    db,
                    "STUDENT_GRADUATED",
                    f"Graduated student '{student.full_name}' ({student.student_id})",
                    username=current_user,
                    entity_type="Student",
                    entity_id=student.id,
                )
                db.commit()
                db.refresh(student)
                return True, student, f"Student '{student.full_name}' marked as Graduated."

            # Standard Promotion into target class + year
            if not to_class_id or not to_academic_year_id:
                return False, None, "Target class and target academic year are required for promotion."

            target_cls = db.query(SchoolClass).filter(SchoolClass.id == to_class_id).first()
            target_ay = db.query(AcademicYear).filter(AcademicYear.id == to_academic_year_id).first()
            if not target_cls or not target_ay:
                return False, None, "Target class or target academic year does not exist."
            if target_cls.academic_year_id != target_ay.id:
                return (
                    False,
                    None,
                    f"Target class '{target_cls.name}' does not belong to academic year '{target_ay.name}'.",
                )

            target_sec = None
            if to_section_id is not None:
                target_sec = db.query(Section).filter(Section.id == to_section_id).first()
                if not target_sec or target_sec.class_id != target_cls.id:
                    return False, None, "Selected target section does not belong to the target class."

            assigned_roll = (
                int(new_roll_number)
                if new_roll_number is not None
                else (from_roll if from_roll is not None else AcademicService._next_roll_for_class_year(db, target_cls.id, target_ay.id, to_section_id))
            )

            # 1. Close prior year academic history non-destructively
            AcademicService._close_open_academic_history_non_destructive(
                db,
                student=student,
                closing_status="Promoted",
                effective_date=eff_date,
                remarks=remarks,
                gpa=gpa,
                final_grade=final_grade,
            )

            # 2. Append promotion audit record
            db.add(
                StudentPromotionHistory(
                    student_id=student.id,
                    from_class_id=from_class_id,
                    to_class_id=target_cls.id,
                    from_section_id=from_section_id,
                    to_section_id=to_section_id,
                    from_academic_year_id=from_ay_id,
                    to_academic_year_id=target_ay.id,
                    from_roll_number=from_roll,
                    to_roll_number=assigned_roll,
                    promotion_type="Promoted",
                    gpa=gpa,
                    final_grade=final_grade,
                    promoted_date=eff_date,
                    remarks=remarks,
                    promoted_by=current_user,
                )
            )

            # 3. Update student's current active placement
            student.class_id = target_cls.id
            student.section_id = to_section_id
            student.academic_year_id = target_ay.id
            student.roll_number = assigned_roll
            student.group = target_sec.group if target_sec else target_cls.group
            student.shift = target_sec.shift if target_sec else target_cls.shift

            # 4. Append new academic history record for the target year
            db.add(
                StudentAcademicHistory(
                    student_id=student.id,
                    academic_year_id=target_ay.id,
                    class_id=target_cls.id,
                    section_id=to_section_id,
                    roll_number=assigned_roll,
                    group=student.group,
                    shift=student.shift,
                    result_status="Enrolled",
                    start_date=eff_date,
                    remarks=remarks,
                )
            )

            AcademicService._log(
                db,
                "STUDENT_PROMOTED",
                f"Promoted '{student.full_name}' -> {target_cls.name} ({target_ay.name})",
                username=current_user,
                entity_type="Student",
                entity_id=student.id,
            )
            db.commit()
            db.refresh(student)
            return True, student, f"Promoted '{student.full_name}' to {target_cls.name} ({target_ay.name})."
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error promoting student {student_id}: {exc}")
            return False, None, str(exc)

    @staticmethod
    def bulk_promote_students(
        db: Session,
        student_ids: List[int],
        to_class_id: Optional[int],
        to_academic_year_id: Optional[int],
        to_section_id: Optional[int] = None,
        auto_assign_rolls: bool = False,
        starting_roll: int = 1,
        mark_graduated: bool = False,
        gpas_by_student: Optional[Dict[int, float]] = None,
        remarks: str = "Bulk Year-End Promotion",
        effective_date: Optional[date] = None,
        current_user: str = "admin",
    ) -> Tuple[bool, int, str]:
        """
        Atomically promote (or graduate) a batch of students while preserving all prior year records.
        """
        if not student_ids:
            return False, 0, "No students selected for bulk promotion."

        try:
            eff_date = effective_date or date.today()
            gpas = gpas_by_student or {}

            students = (
                db.query(Student)
                .filter(Student.id.in_(student_ids), Student.is_deleted == False)
                .order_by(Student.roll_number.asc(), Student.id.asc())
                .all()
            )
            if not students:
                return False, 0, "No matching active students found."

            if not mark_graduated:
                if not to_class_id or not to_academic_year_id:
                    return False, 0, "Target class and academic year are required."
                target_cls = db.query(SchoolClass).filter(SchoolClass.id == to_class_id).first()
                target_ay = db.query(AcademicYear).filter(AcademicYear.id == to_academic_year_id).first()
                if not target_cls or not target_ay:
                    return False, 0, "Target class or target academic year does not exist."
                if target_cls.academic_year_id != target_ay.id:
                    return (
                        False,
                        0,
                        f"Target class '{target_cls.name}' does not belong to academic year '{target_ay.name}'.",
                    )
                target_sec = None
                if to_section_id is not None:
                    target_sec = db.query(Section).filter(Section.id == to_section_id).first()
                    if not target_sec or target_sec.class_id != target_cls.id:
                        return False, 0, "Selected target section does not belong to target class."
            else:
                target_cls = None
                target_ay = None
                target_sec = None

            next_roll = max(1, int(starting_roll))
            promoted_count = 0

            for stu in students:
                stu_gpa = gpas.get(stu.id)
                if mark_graduated:
                    AcademicService._close_open_academic_history_non_destructive(
                        db,
                        student=stu,
                        closing_status="Graduated",
                        effective_date=eff_date,
                        remarks=remarks or "Graduated",
                        gpa=stu_gpa,
                    )
                    db.add(
                        StudentPromotionHistory(
                            student_id=stu.id,
                            from_class_id=stu.class_id,
                            to_class_id=to_class_id or stu.class_id,
                            from_section_id=stu.section_id,
                            to_section_id=to_section_id if to_section_id is not None else stu.section_id,
                            from_academic_year_id=stu.academic_year_id,
                            to_academic_year_id=to_academic_year_id or stu.academic_year_id,
                            from_roll_number=stu.roll_number,
                            to_roll_number=stu.roll_number,
                            promotion_type="Graduated",
                            gpa=stu_gpa,
                            promoted_date=eff_date,
                            remarks=remarks or "Graduated",
                            promoted_by=current_user,
                        )
                    )
                    old_status = stu.status
                    stu.status = StudentStatus.GRADUATED
                    db.add(
                        StudentStatusHistory(
                            student_id=stu.id,
                            from_status=old_status,
                            to_status=StudentStatus.GRADUATED,
                            effective_date=eff_date,
                            reason=remarks or "Batch Graduation",
                            changed_by=current_user,
                        )
                    )
                else:
                    assigned_roll = next_roll if auto_assign_rolls else stu.roll_number
                    if auto_assign_rolls:
                        next_roll += 1

                    AcademicService._close_open_academic_history_non_destructive(
                        db,
                        student=stu,
                        closing_status="Promoted",
                        effective_date=eff_date,
                        remarks=remarks,
                        gpa=stu_gpa,
                    )
                    db.add(
                        StudentPromotionHistory(
                            student_id=stu.id,
                            from_class_id=stu.class_id,
                            to_class_id=target_cls.id,
                            from_section_id=stu.section_id,
                            to_section_id=to_section_id,
                            from_academic_year_id=stu.academic_year_id,
                            to_academic_year_id=target_ay.id,
                            from_roll_number=stu.roll_number,
                            to_roll_number=assigned_roll,
                            promotion_type="Bulk Promoted",
                            gpa=stu_gpa,
                            promoted_date=eff_date,
                            remarks=remarks,
                            promoted_by=current_user,
                        )
                    )

                    stu.class_id = target_cls.id
                    stu.section_id = to_section_id
                    stu.academic_year_id = target_ay.id
                    stu.roll_number = assigned_roll
                    stu.group = target_sec.group if target_sec else target_cls.group
                    stu.shift = target_sec.shift if target_sec else target_cls.shift

                    db.add(
                        StudentAcademicHistory(
                            student_id=stu.id,
                            academic_year_id=target_ay.id,
                            class_id=target_cls.id,
                            section_id=to_section_id,
                            roll_number=assigned_roll,
                            group=stu.group,
                            shift=stu.shift,
                            result_status="Enrolled",
                            start_date=eff_date,
                            remarks=remarks,
                        )
                    )
                promoted_count += 1

            AcademicService._log(
                db,
                "BULK_PROMOTION",
                f"{'Graduated' if mark_graduated else 'Promoted'} {promoted_count} student(s) ({remarks})",
                username=current_user,
            )
            db.commit()
            verb = "graduated" if mark_graduated else "promoted"
            return True, promoted_count, f"Successfully {verb} {promoted_count} student(s)."
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Bulk promotion error: {exc}")
            return False, 0, str(exc)

    @staticmethod
    def transfer_student_class(
        db: Session,
        student_id: int,
        to_class_id: int,
        to_section_id: Optional[int] = None,
        new_roll_number: Optional[int] = None,
        to_group: Optional[str] = None,
        to_shift: Optional[str] = None,
        reason: str = "Academic Class Transfer",
        effective_date: Optional[date] = None,
        current_user: str = "admin",
    ) -> Tuple[bool, Optional[Student], str]:
        """
        Transfer a student between classes (or streams) within an academic year.
        Records StudentTransferHistory and preserves prior StudentAcademicHistory row intact.
        """
        try:
            student = db.query(Student).filter(Student.id == student_id, Student.is_deleted == False).first()
            if not student:
                return False, None, "Student not found."

            target_cls = db.query(SchoolClass).filter(SchoolClass.id == to_class_id).first()
            if not target_cls:
                return False, None, "Target class not found."
            if target_cls.academic_year_id != student.academic_year_id:
                return (
                    False,
                    None,
                    "Class transfer must be within the same academic year; use Promotion for a new academic year.",
                )
            if target_cls.id == student.class_id and (to_section_id is None or to_section_id == student.section_id):
                return False, None, "Student is already enrolled in this class and section."

            target_sec = None
            if to_section_id is not None:
                target_sec = db.query(Section).filter(Section.id == to_section_id).first()
                if not target_sec or target_sec.class_id != target_cls.id:
                    return False, None, "Target section does not belong to the target class."
                occ = (
                    db.query(Student)
                    .filter(
                        Student.section_id == target_sec.id,
                        Student.status == StudentStatus.ACTIVE,
                        Student.is_deleted == False,
                    )
                    .count()
                )
                if occ >= target_sec.capacity:
                    return False, None, f"Target section '{target_sec.name}' has reached full capacity ({target_sec.capacity})."

            eff_date = effective_date or date.today()
            next_roll = (
                int(new_roll_number)
                if new_roll_number is not None
                else AcademicService._next_roll_for_class_year(
                    db, target_cls.id, student.academic_year_id, to_section_id
                )
            )
            final_group = to_group or (target_sec.group if target_sec else target_cls.group)
            final_shift = to_shift or (target_sec.shift if target_sec else target_cls.shift)

            # Close current history row cleanly without overwriting old class/section/roll
            AcademicService._close_open_academic_history_non_destructive(
                db,
                student=student,
                closing_status="Class Transferred",
                effective_date=eff_date,
                remarks=reason,
            )

            db.add(
                StudentTransferHistory(
                    student_id=student.id,
                    academic_year_id=student.academic_year_id,
                    transfer_type="CLASS_TRANSFER",
                    from_class_id=student.class_id,
                    to_class_id=target_cls.id,
                    from_section_id=student.section_id,
                    to_section_id=to_section_id,
                    from_roll_number=student.roll_number,
                    to_roll_number=next_roll,
                    from_group=student.group,
                    to_group=final_group,
                    from_shift=student.shift,
                    to_shift=final_shift,
                    effective_date=eff_date,
                    reason=reason,
                    transferred_by=current_user,
                )
            )

            student.class_id = target_cls.id
            student.section_id = to_section_id
            student.roll_number = next_roll
            student.group = final_group
            student.shift = final_shift

            db.add(
                StudentAcademicHistory(
                    student_id=student.id,
                    academic_year_id=student.academic_year_id,
                    class_id=target_cls.id,
                    section_id=to_section_id,
                    roll_number=next_roll,
                    group=final_group,
                    shift=final_shift,
                    result_status="Enrolled",
                    start_date=eff_date,
                    remarks=f"Class Transfer: {reason}",
                )
            )

            AcademicService._log(
                db,
                "STUDENT_CLASS_TRANSFER",
                f"Transferred '{student.full_name}' to class '{target_cls.name}' (Roll {next_roll})",
                username=current_user,
                entity_type="Student",
                entity_id=student.id,
            )
            db.commit()
            db.refresh(student)
            return True, student, f"Transferred '{student.full_name}' to {target_cls.name}."
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Class transfer error: {exc}")
            return False, None, str(exc)

    @staticmethod
    def transfer_student_section(
        db: Session,
        student_id: int,
        to_section_id: int,
        new_roll_number: Optional[int] = None,
        reason: str = "Section Reallocation",
        effective_date: Optional[date] = None,
        current_user: str = "admin",
    ) -> Tuple[bool, Optional[Student], str]:
        """
        Transfer a student between sections within their current class.
        Records StudentTransferHistory and preserves prior StudentAcademicHistory entry.
        """
        try:
            student = db.query(Student).filter(Student.id == student_id, Student.is_deleted == False).first()
            if not student:
                return False, None, "Student not found."

            target_sec = db.query(Section).filter(Section.id == to_section_id).first()
            if not target_sec:
                return False, None, "Target section not found."
            if target_sec.class_id != student.class_id:
                return (
                    False,
                    None,
                    "Target section belongs to a different class; use Class Transfer instead.",
                )
            if student.section_id == target_sec.id:
                return False, None, f"Student is already in section '{target_sec.name}'."

            occ = (
                db.query(Student)
                .filter(
                    Student.section_id == target_sec.id,
                    Student.status == StudentStatus.ACTIVE,
                    Student.is_deleted == False,
                )
                .count()
            )
            if occ >= target_sec.capacity:
                return False, None, f"Target section '{target_sec.name}' is at full capacity ({target_sec.capacity})."

            eff_date = effective_date or date.today()
            next_roll = (
                int(new_roll_number)
                if new_roll_number is not None
                else AcademicService._next_roll_for_class_year(
                    db, student.class_id, student.academic_year_id, target_sec.id
                )
            )

            AcademicService._close_open_academic_history_non_destructive(
                db,
                student=student,
                closing_status="Section Transferred",
                effective_date=eff_date,
                remarks=reason,
            )

            db.add(
                StudentTransferHistory(
                    student_id=student.id,
                    academic_year_id=student.academic_year_id,
                    transfer_type="SECTION_TRANSFER",
                    from_class_id=student.class_id,
                    to_class_id=student.class_id,
                    from_section_id=student.section_id,
                    to_section_id=target_sec.id,
                    from_roll_number=student.roll_number,
                    to_roll_number=next_roll,
                    from_group=student.group,
                    to_group=target_sec.group or student.group,
                    from_shift=student.shift,
                    to_shift=target_sec.shift or student.shift,
                    effective_date=eff_date,
                    reason=reason,
                    transferred_by=current_user,
                )
            )

            student.section_id = target_sec.id
            student.roll_number = next_roll
            student.group = target_sec.group or student.group
            student.shift = target_sec.shift or student.shift

            db.add(
                StudentAcademicHistory(
                    student_id=student.id,
                    academic_year_id=student.academic_year_id,
                    class_id=student.class_id,
                    section_id=target_sec.id,
                    roll_number=next_roll,
                    group=student.group,
                    shift=student.shift,
                    result_status="Enrolled",
                    start_date=eff_date,
                    remarks=f"Section Transfer: {reason}",
                )
            )

            AcademicService._log(
                db,
                "STUDENT_SECTION_TRANSFER",
                f"Transferred '{student.full_name}' to section '{target_sec.name}' (Roll {next_roll})",
                username=current_user,
                entity_type="Student",
                entity_id=student.id,
            )
            db.commit()
            db.refresh(student)
            return True, student, f"Transferred '{student.full_name}' to section '{target_sec.name}'."
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Section transfer error: {exc}")
            return False, None, str(exc)

    @staticmethod
    def get_student_academic_history(db: Session, student_id: int) -> Dict[str, Any]:
        student = (
            db.query(Student)
            .options(
                joinedload(Student.school_class),
                joinedload(Student.section),
                joinedload(Student.academic_year),
            )
            .filter(Student.id == student_id)
            .first()
        )
        if not student:
            return {"student": None, "academic_history": [], "promotions": [], "transfers": [], "subjects": []}

        acad_rows = (
            db.query(StudentAcademicHistory)
            .options(
                joinedload(StudentAcademicHistory.academic_year),
                joinedload(StudentAcademicHistory.school_class),
                joinedload(StudentAcademicHistory.section),
            )
            .filter(StudentAcademicHistory.student_id == student.id)
            .order_by(StudentAcademicHistory.id.asc())
            .all()
        )
        prom_rows = (
            db.query(StudentPromotionHistory)
            .options(
                joinedload(StudentPromotionHistory.from_class),
                joinedload(StudentPromotionHistory.to_class),
                joinedload(StudentPromotionHistory.from_section),
                joinedload(StudentPromotionHistory.to_section),
                joinedload(StudentPromotionHistory.from_academic_year),
                joinedload(StudentPromotionHistory.to_academic_year),
            )
            .filter(StudentPromotionHistory.student_id == student.id)
            .order_by(StudentPromotionHistory.id.asc())
            .all()
        )
        xfer_rows = (
            db.query(StudentTransferHistory)
            .options(
                joinedload(StudentTransferHistory.from_class),
                joinedload(StudentTransferHistory.to_class),
                joinedload(StudentTransferHistory.from_section),
                joinedload(StudentTransferHistory.to_section),
                joinedload(StudentTransferHistory.academic_year),
            )
            .filter(StudentTransferHistory.student_id == student.id)
            .order_by(StudentTransferHistory.id.asc())
            .all()
        )
        subj_rows = AcademicRepository.list_student_subject_enrollments(db, student_id=student.id)

        return {
            "student": student,
            "academic_history": acad_rows,
            "promotions": prom_rows,
            "transfers": xfer_rows,
            "subjects": subj_rows,
        }

    # ==================== ACADEMIC CALENDAR ====================
    @staticmethod
    def create_calendar_event(
        db: Session,
        event_title: str,
        start_date: date,
        end_date: date,
        event_category: str = "Academic",
        academic_year_id: Optional[int] = None,
        term_name: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        venue: str = "Campus Main Auditorium",
        target_audience: str = "All",
        is_holiday: bool = False,
        description: Optional[str] = None,
        organizer: str = "Academic Office",
        current_user: str = "admin",
    ) -> Tuple[Optional[SchoolEvent], str]:
        if not (event_title or "").strip():
            return None, "Event title is required."
        if end_date < start_date:
            return None, "End date cannot precede start date."

        ev = NoticeRepository.create_event(
            db,
            event_title=event_title,
            start_date=start_date,
            end_date=end_date,
            event_category=event_category,
            start_time=start_time,
            end_time=end_time,
            venue=venue,
            target_audience=target_audience,
            is_holiday=is_holiday,
            description=description,
            organizer=organizer,
        )
        if academic_year_id or term_name:
            ev.academic_year_id = academic_year_id
            ev.term_name = term_name
            db.commit()
            db.refresh(ev)

        AcademicService._log(
            db,
            "CREATE_CALENDAR_EVENT",
            f"Scheduled academic calendar event '{ev.event_title}' ({ev.start_date} to {ev.end_date})",
            username=current_user,
            entity_type="SchoolEvent",
            entity_id=ev.id,
        )
        db.commit()
        return ev, f"Event '{ev.event_title}' added to academic calendar."

    @staticmethod
    def export_calendar_pdf(
        db: Session,
        output_pdf_path: str,
        academic_year_id: Optional[int] = None,
    ) -> str:
        events = AcademicRepository.list_calendar_events(db, academic_year_id=academic_year_id)
        school = db.query(SchoolSettings).first()
        return AcademicCalendarPDFGenerator.generate_calendar_pdf(events, school, output_pdf_path)

    # ==================== SUMMARY ====================
    @staticmethod
    def get_academic_summary(
        db: Session, academic_year_id: Optional[int] = None
    ) -> Dict[str, Any]:
        cls_q = db.query(SchoolClass).filter(SchoolClass.is_deleted == False)
        sec_q = db.query(Section).join(SchoolClass, Section.class_id == SchoolClass.id).filter(Section.is_deleted == False)
        sub_q = db.query(Subject).join(SchoolClass, Subject.class_id == SchoolClass.id).filter(Subject.is_deleted == False)
        if academic_year_id:
            cls_q = cls_q.filter(SchoolClass.academic_year_id == academic_year_id)
            sec_q = sec_q.filter(SchoolClass.academic_year_id == academic_year_id)
            sub_q = sub_q.filter(SchoolClass.academic_year_id == academic_year_id)

        current_year = AcademicRepository.get_current_academic_year(db)
        return {
            "total_classes": cls_q.count(),
            "total_sections": sec_q.count(),
            "total_subjects": sub_q.count(),
            "total_groups": db.query(AcademicGroup).filter(AcademicGroup.is_deleted == False).count(),
            "total_shifts": db.query(AcademicShift).filter(AcademicShift.is_deleted == False).count(),
            "total_rooms": db.query(AcademicRoom).filter(AcademicRoom.is_deleted == False).count(),
            "total_departments": db.query(Department).filter(Department.is_deleted == False).count(),
            "total_events": db.query(SchoolEvent).filter(SchoolEvent.is_deleted == False).count(),
            "current_year": current_year.name if current_year else "Not Set",
        }
