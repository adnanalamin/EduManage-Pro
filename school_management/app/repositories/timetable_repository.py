"""
EduManage Pro - Advanced Timetable Repository
Supports:
- Multi-Shift Period Slots scoped by Academic Year & Shift
- Teacher, Room, Class & Cross-Shift Time-Overlap Conflict Detection
- Class, Teacher, and Room Weekly Routine Matrices
- Immutable Academic Year Timetable History
"""

from datetime import datetime
import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.models.academic import AcademicRoom, AcademicShift, AcademicYear, SchoolClass, Section, Subject
from app.models.staff import Teacher
from app.models.timetable import PeriodSlot, TimetableEntry, TimetableHistory


def _parse_time_to_minutes(time_str: Optional[str]) -> Optional[int]:
    if not time_str:
        return None
    raw = time_str.strip().upper()
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.hour * 60 + dt.minute
        except ValueError:
            continue
    return None


def _period_slots_overlap(slot_a: Optional[PeriodSlot], slot_b: Optional[PeriodSlot]) -> bool:
    if not slot_a or not slot_b:
        return False
    if slot_a.id == slot_b.id:
        return True
    s1 = _parse_time_to_minutes(slot_a.start_time)
    e1 = _parse_time_to_minutes(slot_a.end_time)
    s2 = _parse_time_to_minutes(slot_b.start_time)
    e2 = _parse_time_to_minutes(slot_b.end_time)
    if s1 is not None and e1 is not None and s2 is not None and e2 is not None:
        return s1 < e2 and s2 < e1
    return slot_a.shift == slot_b.shift and slot_a.period_number == slot_b.period_number


class TimetableRepository:
    """Repository handling multi-shift period slots, timetable entries, conflict detection, and year history."""

    # ---------------- Period Slot Operations ----------------
    @staticmethod
    def get_period_slots(
        session: Session,
        shift: Optional[str] = None,
        academic_year_id: Optional[int] = None,
        active_only: bool = True,
    ) -> List[PeriodSlot]:
        query = session.query(PeriodSlot).filter(PeriodSlot.is_deleted == False)
        if active_only:
            query = query.filter(PeriodSlot.is_active == True)
        if shift and shift != "All":
            query = query.filter(PeriodSlot.shift == shift)
        if academic_year_id is not None:
            # Prefer slots explicitly bound to the academic year, fallback cleanly to shared/null slots if none
            year_slots = (
                query.filter(PeriodSlot.academic_year_id == academic_year_id)
                .order_by(PeriodSlot.period_number.asc(), PeriodSlot.id.asc())
                .all()
            )
            if year_slots:
                return year_slots
        return query.order_by(PeriodSlot.period_number.asc(), PeriodSlot.id.asc()).all()

    @staticmethod
    def get_period_slot_by_id(session: Session, slot_id: int) -> Optional[PeriodSlot]:
        return session.query(PeriodSlot).filter(PeriodSlot.id == slot_id, PeriodSlot.is_deleted == False).first()

    @staticmethod
    def create_period_slot(session: Session, **kwargs) -> PeriodSlot:
        if kwargs.get("shift") and not kwargs.get("shift_id"):
            sh = session.query(AcademicShift).filter(AcademicShift.name == kwargs["shift"]).first()
            if sh:
                kwargs["shift_id"] = sh.id
        slot = PeriodSlot(**kwargs)
        session.add(slot)
        session.commit()
        session.refresh(slot)
        return slot

    @staticmethod
    def update_period_slot(session: Session, slot_id: int, **kwargs) -> Optional[PeriodSlot]:
        slot = session.query(PeriodSlot).filter(PeriodSlot.id == slot_id, PeriodSlot.is_deleted == False).first()
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
        slot.is_deleted = True
        slot.is_active = False
        session.commit()
        return True

    # ---------------- Conflict Detection (Teacher, Room, Class & Cross-Shift) ----------------
    @staticmethod
    def check_conflicts(
        session: Session,
        day_of_week: str,
        period_slot_id: int,
        teacher_id: int,
        room_number: str,
        exclude_entry_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        class_id: Optional[int] = None,
        section_id: Optional[int] = None,
        room_id: Optional[int] = None,
        check_class_conflict: bool = False,
    ) -> List[str]:
        """
        Detects scheduling conflicts across active entries on the given day & academic year:
        1. Teacher double-booking conflict (same period OR overlapping clock time across shifts)
        2. Room/Lab double-booking conflict (normalized room_number or room_id, including time overlap)
        3. Class/Section double-booking conflict (when check_class_conflict=True)
        """
        conflicts: List[str] = []
        target_slot = TimetableRepository.get_period_slot_by_id(session, period_slot_id)
        eff_year_id = academic_year_id or (target_slot.academic_year_id if target_slot else None)

        base_q = (
            session.query(TimetableEntry)
            .options(
                joinedload(TimetableEntry.period_slot),
                joinedload(TimetableEntry.school_class),
                joinedload(TimetableEntry.section),
                joinedload(TimetableEntry.subject),
                joinedload(TimetableEntry.teacher),
            )
            .filter(
                TimetableEntry.is_deleted == False,
                TimetableEntry.day_of_week == day_of_week,
            )
        )
        if eff_year_id is not None:
            base_q = base_q.filter(TimetableEntry.academic_year_id == eff_year_id)
        if exclude_entry_id is not None:
            base_q = base_q.filter(TimetableEntry.id != exclude_entry_id)

        day_entries = base_q.all()
        room_clean = (room_number or "").strip().lower()

        teacher_clashed = False
        room_clashed = False
        class_clashed = False

        for entry in day_entries:
            overlaps = (
                entry.period_slot_id == period_slot_id
                or _period_slots_overlap(target_slot, entry.period_slot)
            )
            if not overlaps:
                continue

            cls_name = entry.school_class.name if entry.school_class else f"Class #{entry.class_id}"
            sec_label = f" ({entry.section.name})" if entry.section else ""
            slot_label = entry.period_slot.name if entry.period_slot else f"Period #{entry.period_slot_id}"

            # 1. Teacher Conflict
            if not teacher_clashed and teacher_id and entry.teacher_id == teacher_id:
                t_name = entry.teacher.name if entry.teacher else f"Teacher #{teacher_id}"
                conflicts.append(
                    f"Teacher Conflict: {t_name} is already assigned to {cls_name}{sec_label} "
                    f"on {day_of_week} during {slot_label} ({entry.shift})."
                )
                teacher_clashed = True

            # 2. Room Conflict
            entry_room_clean = (entry.room_number or "").strip().lower()
            same_room = (room_id is not None and entry.room_id == room_id) or (
                room_clean and entry_room_clean == room_clean
            )
            if not room_clashed and same_room:
                conflicts.append(
                    f"Room Conflict: {room_number} is already occupied by {cls_name}{sec_label} "
                    f"on {day_of_week} during {slot_label} ({entry.shift})."
                )
                room_clashed = True

            # 3. Class / Section Conflict
            if check_class_conflict and not class_clashed and class_id is not None and entry.class_id == class_id:
                same_sec = (
                    entry.section_id == section_id
                    or entry.section_id is None
                    or section_id is None
                )
                if same_sec:
                    sub_name = entry.subject.name if entry.subject else f"Subject #{entry.subject_id}"
                    conflicts.append(
                        f"Class Conflict: {cls_name}{sec_label} already has '{sub_name}' scheduled "
                        f"on {day_of_week} during {slot_label}."
                    )
                    class_clashed = True

        return conflicts

    @staticmethod
    def scan_all_conflicts(
        session: Session,
        academic_year_id: Optional[int] = None,
        shift: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Scans existing timetable entries and returns any Teacher, Room, or Class conflicts."""
        entries = TimetableRepository.get_all_entries(
            session, academic_year_id=academic_year_id, shift=shift
        )
        issues: List[Dict[str, Any]] = []
        for idx, e1 in enumerate(entries):
            for e2 in entries[idx + 1 :]:
                if e1.day_of_week != e2.day_of_week or e1.academic_year_id != e2.academic_year_id:
                    continue
                if not (e1.period_slot_id == e2.period_slot_id or _period_slots_overlap(e1.period_slot, e2.period_slot)):
                    continue

                if e1.teacher_id == e2.teacher_id:
                    issues.append({
                        "type": "Teacher Conflict",
                        "day": e1.day_of_week,
                        "period": e1.period_slot.name if e1.period_slot else str(e1.period_slot_id),
                        "detail": (
                            f"{e1.teacher.name if e1.teacher else e1.teacher_id} booked in "
                            f"{e1.school_class.name if e1.school_class else e1.class_id} & "
                            f"{e2.school_class.name if e2.school_class else e2.class_id}"
                        ),
                    })
                r1 = (e1.room_number or "").strip().lower()
                r2 = (e2.room_number or "").strip().lower()
                if (e1.room_id and e1.room_id == e2.room_id) or (r1 and r1 == r2):
                    issues.append({
                        "type": "Room Conflict",
                        "day": e1.day_of_week,
                        "period": e1.period_slot.name if e1.period_slot else str(e1.period_slot_id),
                        "detail": (
                            f"{e1.room_number} double-booked by "
                            f"{e1.school_class.name if e1.school_class else e1.class_id} & "
                            f"{e2.school_class.name if e2.school_class else e2.class_id}"
                        ),
                    })
                if e1.class_id == e2.class_id and (
                    e1.section_id == e2.section_id or e1.section_id is None or e2.section_id is None
                ):
                    issues.append({
                        "type": "Class Conflict",
                        "day": e1.day_of_week,
                        "period": e1.period_slot.name if e1.period_slot else str(e1.period_slot_id),
                        "detail": (
                            f"{e1.school_class.name if e1.school_class else e1.class_id} "
                            f"has multiple lessons ({e1.subject.name if e1.subject else e1.subject_id} & "
                            f"{e2.subject.name if e2.subject else e2.subject_id})"
                        ),
                    })
        return issues

    # ---------------- Timetable Entry CRUD ----------------
    @staticmethod
    def create_timetable_entry(session: Session, **kwargs) -> TimetableEntry:
        if kwargs.get("room_id") and not kwargs.get("room_number"):
            rm = session.query(AcademicRoom).filter(AcademicRoom.id == kwargs["room_id"]).first()
            if rm:
                kwargs["room_number"] = rm.room_number
        elif kwargs.get("room_number") and not kwargs.get("room_id"):
            rm = session.query(AcademicRoom).filter(AcademicRoom.room_number == kwargs["room_number"]).first()
            if rm:
                kwargs["room_id"] = rm.id

        if not kwargs.get("shift") and kwargs.get("period_slot_id"):
            ps = TimetableRepository.get_period_slot_by_id(session, kwargs["period_slot_id"])
            if ps:
                kwargs["shift"] = ps.shift
                kwargs.setdefault("shift_id", ps.shift_id)

        entry = TimetableEntry(**kwargs)
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry

    @staticmethod
    def get_timetable_entry_by_id(session: Session, entry_id: int) -> Optional[TimetableEntry]:
        return (
            session.query(TimetableEntry)
            .options(
                joinedload(TimetableEntry.period_slot),
                joinedload(TimetableEntry.school_class),
                joinedload(TimetableEntry.section),
                joinedload(TimetableEntry.subject),
                joinedload(TimetableEntry.teacher),
                joinedload(TimetableEntry.room),
                joinedload(TimetableEntry.academic_year),
            )
            .filter(TimetableEntry.id == entry_id, TimetableEntry.is_deleted == False)
            .first()
        )

    @staticmethod
    def update_timetable_entry(session: Session, entry_id: int, **kwargs) -> Optional[TimetableEntry]:
        entry = (
            session.query(TimetableEntry)
            .filter(TimetableEntry.id == entry_id, TimetableEntry.is_deleted == False)
            .first()
        )
        if not entry:
            return None
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        entry.version_no = int(entry.version_no or 1) + 1
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
        day_of_week: Optional[str] = None,
        academic_year_id: Optional[int] = None,
        shift: Optional[str] = None,
        room_number: Optional[str] = None,
        room_id: Optional[int] = None,
    ) -> List[TimetableEntry]:
        query = (
            session.query(TimetableEntry)
            .options(
                joinedload(TimetableEntry.period_slot),
                joinedload(TimetableEntry.school_class),
                joinedload(TimetableEntry.section),
                joinedload(TimetableEntry.subject),
                joinedload(TimetableEntry.teacher),
                joinedload(TimetableEntry.room),
                joinedload(TimetableEntry.academic_year),
            )
            .filter(TimetableEntry.is_deleted == False)
        )
        if academic_year_id is not None:
            query = query.filter(TimetableEntry.academic_year_id == academic_year_id)
        if shift and shift != "All":
            query = query.filter(TimetableEntry.shift == shift)
        if class_id is not None:
            query = query.filter(TimetableEntry.class_id == class_id)
        if section_id is not None:
            query = query.filter(TimetableEntry.section_id == section_id)
        if teacher_id is not None:
            query = query.filter(TimetableEntry.teacher_id == teacher_id)
        if day_of_week:
            query = query.filter(TimetableEntry.day_of_week == day_of_week)
        if room_id is not None:
            query = query.filter(TimetableEntry.room_id == room_id)
        if room_number:
            query = query.filter(TimetableEntry.room_number == room_number)

        return query.order_by(TimetableEntry.day_of_week, TimetableEntry.period_slot_id).all()

    # ---------------- Grid Matrix Queries (Class, Teacher & Room) ----------------
    @staticmethod
    def get_class_timetable_matrix(
        session: Session,
        class_id: int,
        section_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        shift: Optional[str] = None,
    ) -> Dict[str, Dict[int, TimetableEntry]]:
        query = (
            session.query(TimetableEntry)
            .options(
                joinedload(TimetableEntry.period_slot),
                joinedload(TimetableEntry.subject),
                joinedload(TimetableEntry.teacher),
                joinedload(TimetableEntry.section),
                joinedload(TimetableEntry.room),
            )
            .filter(TimetableEntry.class_id == class_id, TimetableEntry.is_deleted == False)
        )
        if section_id is not None:
            query = query.filter(TimetableEntry.section_id == section_id)
        if academic_year_id is not None:
            query = query.filter(TimetableEntry.academic_year_id == academic_year_id)
        if shift and shift != "All":
            query = query.filter(TimetableEntry.shift == shift)

        matrix: Dict[str, Dict[int, TimetableEntry]] = {}
        for entry in query.all():
            matrix.setdefault(entry.day_of_week, {})[entry.period_slot_id] = entry
        return matrix

    @staticmethod
    def get_teacher_routine_matrix(
        session: Session,
        teacher_id: int,
        academic_year_id: Optional[int] = None,
        shift: Optional[str] = None,
    ) -> Dict[str, Dict[int, TimetableEntry]]:
        query = (
            session.query(TimetableEntry)
            .options(
                joinedload(TimetableEntry.period_slot),
                joinedload(TimetableEntry.school_class),
                joinedload(TimetableEntry.section),
                joinedload(TimetableEntry.subject),
                joinedload(TimetableEntry.room),
            )
            .filter(TimetableEntry.teacher_id == teacher_id, TimetableEntry.is_deleted == False)
        )
        if academic_year_id is not None:
            query = query.filter(TimetableEntry.academic_year_id == academic_year_id)
        if shift and shift != "All":
            query = query.filter(TimetableEntry.shift == shift)

        matrix: Dict[str, Dict[int, TimetableEntry]] = {}
        for entry in query.all():
            matrix.setdefault(entry.day_of_week, {})[entry.period_slot_id] = entry
        return matrix

    @staticmethod
    def get_room_timetable_matrix(
        session: Session,
        room_number: Optional[str] = None,
        room_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        shift: Optional[str] = None,
    ) -> Dict[str, Dict[int, TimetableEntry]]:
        query = (
            session.query(TimetableEntry)
            .options(
                joinedload(TimetableEntry.period_slot),
                joinedload(TimetableEntry.school_class),
                joinedload(TimetableEntry.section),
                joinedload(TimetableEntry.subject),
                joinedload(TimetableEntry.teacher),
                joinedload(TimetableEntry.room),
            )
            .filter(TimetableEntry.is_deleted == False)
        )
        if room_id is not None:
            query = query.filter(TimetableEntry.room_id == room_id)
        elif room_number:
            query = query.filter(TimetableEntry.room_number == room_number)
        if academic_year_id is not None:
            query = query.filter(TimetableEntry.academic_year_id == academic_year_id)
        if shift and shift != "All":
            query = query.filter(TimetableEntry.shift == shift)

        matrix: Dict[str, Dict[int, TimetableEntry]] = {}
        for entry in query.all():
            matrix.setdefault(entry.day_of_week, {})[entry.period_slot_id] = entry
        return matrix

    @staticmethod
    def get_distinct_rooms_and_catalog(session: Session, academic_year_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns combined catalog of AcademicRoom records plus any ad-hoc room strings in TimetableEntry."""
        rooms: List[Dict[str, Any]] = []
        seen = set()
        for rm in session.query(AcademicRoom).filter(AcademicRoom.is_deleted == False, AcademicRoom.is_active == True).order_by(AcademicRoom.room_number.asc()).all():
            rooms.append({
                "room_id": rm.id,
                "room_number": rm.room_number,
                "label": f"{rm.room_number} ({rm.room_type}, Cap {rm.capacity})",
                "room_type": rm.room_type,
                "capacity": rm.capacity,
                "building": rm.building,
            })
            seen.add(rm.room_number.strip().lower())

        q = session.query(TimetableEntry.room_number).filter(TimetableEntry.is_deleted == False).distinct()
        if academic_year_id is not None:
            q = q.filter(TimetableEntry.academic_year_id == academic_year_id)
        for (rnum,) in q.all():
            if rnum and rnum.strip().lower() not in seen:
                rooms.append({
                    "room_id": None,
                    "room_number": rnum,
                    "label": rnum,
                    "room_type": "Classroom",
                    "capacity": 40,
                    "building": "Main Building",
                })
                seen.add(rnum.strip().lower())
        return rooms

    # ---------------- Academic Year Timetable History ----------------
    @staticmethod
    def record_history(
        session: Session,
        academic_year_id: int,
        action: str,
        *,
        class_id: Optional[int] = None,
        section_id: Optional[int] = None,
        shift_name: Optional[str] = "Morning",
        version_no: int = 1,
        entry_summary: Optional[str] = None,
        snapshot: Optional[Any] = None,
        reason: Optional[str] = None,
        performed_by: str = "system",
        commit: bool = False,
    ) -> TimetableHistory:
        rec = TimetableHistory(
            academic_year_id=academic_year_id,
            class_id=class_id,
            section_id=section_id,
            shift_name=shift_name,
            action=action,
            version_no=version_no,
            entry_summary=entry_summary,
            snapshot_json=json.dumps(snapshot, default=str) if snapshot is not None else None,
            reason=reason,
            performed_by=performed_by or "system",
        )
        session.add(rec)
        if commit:
            session.commit()
            session.refresh(rec)
        else:
            session.flush()
        return rec

    @staticmethod
    def list_history(
        session: Session,
        academic_year_id: Optional[int] = None,
        class_id: Optional[int] = None,
        shift_name: Optional[str] = None,
    ) -> List[TimetableHistory]:
        q = session.query(TimetableHistory).options(
            joinedload(TimetableHistory.academic_year),
            joinedload(TimetableHistory.school_class),
            joinedload(TimetableHistory.section),
        )
        if academic_year_id is not None:
            q = q.filter(TimetableHistory.academic_year_id == academic_year_id)
        if class_id is not None:
            q = q.filter(TimetableHistory.class_id == class_id)
        if shift_name and shift_name != "All":
            q = q.filter(TimetableHistory.shift_name == shift_name)
        return q.order_by(TimetableHistory.performed_at.desc(), TimetableHistory.id.desc()).all()
