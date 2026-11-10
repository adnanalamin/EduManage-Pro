"""
EduManage Pro - Timetable Repository
Phase 9: Period Slots, Teaching Assignments, Routine Matrix & Conflict Detection
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from app.models.timetable import PeriodSlot, TimetableEntry
from app.models.academic import SchoolClass, Section, Subject
from app.models.staff import Teacher


class TimetableRepository:
    """Repository handling period slot configuration, timetable slots and routine queries."""

    # ---------------- Period Slot Operations ----------------
    @staticmethod
    def get_period_slots(session: Session, shift: Optional[str] = None) -> List[PeriodSlot]:
        """Fetch all periods ordered by period number."""
        query = session.query(PeriodSlot)
        if shift:
            query = query.filter(PeriodSlot.shift == shift)
        return query.order_by(PeriodSlot.period_number.asc()).all()

    @staticmethod
    def get_period_slot_by_id(session: Session, slot_id: int) -> Optional[PeriodSlot]:
        return session.query(PeriodSlot).filter(PeriodSlot.id == slot_id).first()

    @staticmethod
    def create_period_slot(session: Session, **kwargs) -> PeriodSlot:
        slot = PeriodSlot(**kwargs)
        session.add(slot)
        session.commit()
        session.refresh(slot)
        return slot

    @staticmethod
    def update_period_slot(session: Session, slot_id: int, **kwargs) -> Optional[PeriodSlot]:
        slot = session.query(PeriodSlot).filter(PeriodSlot.id == slot_id).first()
        if not slot:
            return None
        for key, value in kwargs.items():
            if hasattr(slot, key):
                setattr(slot, key, value)
        session.commit()
        session.refresh(slot)
        return slot

    @staticmethod
    def delete_period_slot(session: Session, slot_id: int) -> bool:
        slot = session.query(PeriodSlot).filter(PeriodSlot.id == slot_id).first()
        if not slot:
            return False
        session.delete(slot)
        session.commit()
        return True

    # ---------------- Conflict Detection ----------------
    @staticmethod
    def check_conflicts(
        session: Session,
        day_of_week: str,
        period_slot_id: int,
        teacher_id: int,
        room_number: str,
        exclude_entry_id: Optional[int] = None
    ) -> List[str]:
        """
        Detects scheduling conflicts:
        1. Teacher double-booking clash
        2. Classroom / Laboratory double-booking clash
        Returns a list of conflict warning/error strings.
        """
        conflicts = []

        # 1. Teacher Clash Check
        teacher_query = session.query(TimetableEntry).options(
            joinedload(TimetableEntry.school_class),
            joinedload(TimetableEntry.section),
            joinedload(TimetableEntry.teacher)
        ).filter(
            TimetableEntry.day_of_week == day_of_week,
            TimetableEntry.period_slot_id == period_slot_id,
            TimetableEntry.teacher_id == teacher_id
        )
        if exclude_entry_id:
            teacher_query = teacher_query.filter(TimetableEntry.id != exclude_entry_id)

        teacher_clash = teacher_query.first()
        if teacher_clash:
            teacher_name = teacher_clash.teacher.name if teacher_clash.teacher else f"Teacher #{teacher_id}"
            class_name = teacher_clash.school_class.name if teacher_clash.school_class else "another class"
            conflicts.append(
                f"Teacher Conflict: {teacher_name} is already assigned to {class_name} on {day_of_week} during this period."
            )

        # 2. Room Clash Check (normalize room name)
        room_clean = room_number.strip().lower()
        room_query = session.query(TimetableEntry).options(
            joinedload(TimetableEntry.school_class),
            joinedload(TimetableEntry.section)
        ).filter(
            TimetableEntry.day_of_week == day_of_week,
            TimetableEntry.period_slot_id == period_slot_id
        )
        if exclude_entry_id:
            room_query = room_query.filter(TimetableEntry.id != exclude_entry_id)

        for entry in room_query.all():
            if entry.room_number.strip().lower() == room_clean:
                class_name = entry.school_class.name if entry.school_class else "another class"
                conflicts.append(
                    f"Room Conflict: {room_number} is already occupied by {class_name} on {day_of_week} during this period."
                )
                break

        return conflicts

    # ---------------- Timetable Entry CRUD ----------------
    @staticmethod
    def create_timetable_entry(session: Session, **kwargs) -> TimetableEntry:
        entry = TimetableEntry(**kwargs)
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry

    @staticmethod
    def get_timetable_entry_by_id(session: Session, entry_id: int) -> Optional[TimetableEntry]:
        return session.query(TimetableEntry).options(
            joinedload(TimetableEntry.period_slot),
            joinedload(TimetableEntry.school_class),
            joinedload(TimetableEntry.section),
            joinedload(TimetableEntry.subject),
            joinedload(TimetableEntry.teacher),
        ).filter(TimetableEntry.id == entry_id).first()

    @staticmethod
    def update_timetable_entry(session: Session, entry_id: int, **kwargs) -> Optional[TimetableEntry]:
        entry = session.query(TimetableEntry).filter(TimetableEntry.id == entry_id).first()
        if not entry:
            return None
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        session.commit()
        session.refresh(entry)
        return entry

    @staticmethod
    def delete_timetable_entry(session: Session, entry_id: int) -> bool:
        entry = session.query(TimetableEntry).filter(TimetableEntry.id == entry_id).first()
        if not entry:
            return False
        session.delete(entry)
        session.commit()
        return True

    @staticmethod
    def get_all_entries(
        session: Session,
        class_id: Optional[int] = None,
        section_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        day_of_week: Optional[str] = None
    ) -> List[TimetableEntry]:
        query = session.query(TimetableEntry).options(
            joinedload(TimetableEntry.period_slot),
            joinedload(TimetableEntry.school_class),
            joinedload(TimetableEntry.section),
            joinedload(TimetableEntry.subject),
            joinedload(TimetableEntry.teacher),
        )
        if class_id:
            query = query.filter(TimetableEntry.class_id == class_id)
        if section_id:
            query = query.filter(TimetableEntry.section_id == section_id)
        if teacher_id:
            query = query.filter(TimetableEntry.teacher_id == teacher_id)
        if day_of_week:
            query = query.filter(TimetableEntry.day_of_week == day_of_week)

        return query.order_by(TimetableEntry.day_of_week, TimetableEntry.period_slot_id).all()

    # ---------------- Grid Matrix Queries ----------------
    @staticmethod
    def get_class_timetable_matrix(
        session: Session,
        class_id: int,
        section_id: Optional[int] = None
    ) -> Dict[str, Dict[int, TimetableEntry]]:
        """
        Returns a 2D mapping: { "Sunday": { 1: entry, 2: entry }, "Monday": ... }
        where keys are day strings and period_slot_id numbers.
        """
        query = session.query(TimetableEntry).options(
            joinedload(TimetableEntry.period_slot),
            joinedload(TimetableEntry.subject),
            joinedload(TimetableEntry.teacher),
        ).filter(TimetableEntry.class_id == class_id)

        if section_id:
            query = query.filter(TimetableEntry.section_id == section_id)

        entries = query.all()
        matrix: Dict[str, Dict[int, TimetableEntry]] = {}

        for entry in entries:
            day = entry.day_of_week
            if day not in matrix:
                matrix[day] = {}
            matrix[day][entry.period_slot_id] = entry

        return matrix

    @staticmethod
    def get_teacher_routine_matrix(
        session: Session,
        teacher_id: int
    ) -> Dict[str, Dict[int, TimetableEntry]]:
        """
        Returns a 2D mapping for teacher's weekly routine:
        { "Sunday": { 1: entry, 3: entry }, ... }
        """
        entries = session.query(TimetableEntry).options(
            joinedload(TimetableEntry.period_slot),
            joinedload(TimetableEntry.school_class),
            joinedload(TimetableEntry.section),
            joinedload(TimetableEntry.subject),
        ).filter(TimetableEntry.teacher_id == teacher_id).all()

        matrix: Dict[str, Dict[int, TimetableEntry]] = {}
        for entry in entries:
            day = entry.day_of_week
            if day not in matrix:
                matrix[day] = {}
            matrix[day][entry.period_slot_id] = entry

        return matrix
