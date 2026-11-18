"""
EduManage Pro - Advanced Timetable & Routine Service
Supports:
- Multi-Shift Period Seeding (Morning, Day, Evening, and custom AcademicShifts)
- Strict Teacher, Room, and Class Conflict Detection
- Manual Editing, Slot Moving / Atomic Swapping, and Deletion with History Logging
- Intelligent Constraint-Satisfaction Auto-Suggestion Algorithm
- Immutable Academic Year History Snapshots & Previous-Year Cloning
- Professional Excel Exports (Class & Room Timetables)
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.academic import AcademicRoom, AcademicShift, AcademicYear, SchoolClass, Section, Subject
from app.models.staff import Teacher, TeacherSubjectAssignment
from app.models.timetable import PeriodSlot, TimetableEntry, TimetableHistory
from app.models.user import User
from app.repositories.timetable_repository import TimetableRepository, _period_slots_overlap
from app.security.session import session as app_session


STANDARD_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]

DEFAULT_PERIOD_DEFINITIONS = [
    {"period_number": 0, "name": "Assembly & Homeroom", "start_time": "08:30 AM", "end_time": "08:45 AM", "duration_minutes": 15, "is_break": True},
    {"period_number": 1, "name": "1st Period", "start_time": "08:45 AM", "end_time": "09:30 AM", "duration_minutes": 45, "is_break": False},
    {"period_number": 2, "name": "2nd Period", "start_time": "09:30 AM", "end_time": "10:15 AM", "duration_minutes": 45, "is_break": False},
    {"period_number": 3, "name": "3rd Period", "start_time": "10:15 AM", "end_time": "11:00 AM", "duration_minutes": 45, "is_break": False},
    {"period_number": 4, "name": "4th Period", "start_time": "11:00 AM", "end_time": "11:45 AM", "duration_minutes": 45, "is_break": False},
    {"period_number": 99, "name": "Tiffin & Refreshment", "start_time": "11:45 AM", "end_time": "12:30 PM", "duration_minutes": 45, "is_break": True},
    {"period_number": 5, "name": "5th Period", "start_time": "12:30 PM", "end_time": "01:15 PM", "duration_minutes": 45, "is_break": False},
    {"period_number": 6, "name": "6th Period", "start_time": "01:15 PM", "end_time": "02:00 PM", "duration_minutes": 45, "is_break": False},
    {"period_number": 7, "name": "7th Period", "start_time": "02:00 PM", "end_time": "02:45 PM", "duration_minutes": 45, "is_break": False},
]

SHIFT_PERIOD_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "Morning": DEFAULT_PERIOD_DEFINITIONS,
    "Day": [
        {"period_number": 0, "name": "Day Assembly", "start_time": "01:00 PM", "end_time": "01:15 PM", "duration_minutes": 15, "is_break": True},
        {"period_number": 1, "name": "1st Period (Day)", "start_time": "01:15 PM", "end_time": "02:00 PM", "duration_minutes": 45, "is_break": False},
        {"period_number": 2, "name": "2nd Period (Day)", "start_time": "02:00 PM", "end_time": "02:45 PM", "duration_minutes": 45, "is_break": False},
        {"period_number": 3, "name": "3rd Period (Day)", "start_time": "02:45 PM", "end_time": "03:30 PM", "duration_minutes": 45, "is_break": False},
        {"period_number": 99, "name": "Tiffin Break (Day)", "start_time": "03:30 PM", "end_time": "04:00 PM", "duration_minutes": 30, "is_break": True},
        {"period_number": 4, "name": "4th Period (Day)", "start_time": "04:00 PM", "end_time": "04:45 PM", "duration_minutes": 45, "is_break": False},
        {"period_number": 5, "name": "5th Period (Day)", "start_time": "04:45 PM", "end_time": "05:30 PM", "duration_minutes": 45, "is_break": False},
    ],
    "Evening": [
        {"period_number": 1, "name": "1st Period (Eve)", "start_time": "05:45 PM", "end_time": "06:30 PM", "duration_minutes": 45, "is_break": False},
        {"period_number": 2, "name": "2nd Period (Eve)", "start_time": "06:30 PM", "end_time": "07:15 PM", "duration_minutes": 45, "is_break": False},
        {"period_number": 99, "name": "Evening Recess", "start_time": "07:15 PM", "end_time": "07:35 PM", "duration_minutes": 20, "is_break": True},
        {"period_number": 3, "name": "3rd Period (Eve)", "start_time": "07:35 PM", "end_time": "08:20 PM", "duration_minutes": 45, "is_break": False},
        {"period_number": 4, "name": "4th Period (Eve)", "start_time": "08:20 PM", "end_time": "09:05 PM", "duration_minutes": 45, "is_break": False},
    ],
}


def _actor_username(actor_user: Optional[User] = None, fallback: str = "admin") -> str:
    if actor_user is not None:
        return actor_user.username
    if app_session.is_authenticated and app_session.current_user is not None:
        return app_session.current_user.username
    return fallback


class TimetableService:
    """Enterprise service managing multi-shift routines, conflict resolution, auto-scheduling & year history."""

    @staticmethod
    def seed_default_periods(
        session: Session,
        academic_year_id: Optional[int] = 1,
        shift: str = "Morning",
    ) -> List[PeriodSlot]:
        """Seeds bell schedule for the requested shift (defaults to Morning for backward compatibility)."""
        existing = TimetableRepository.get_period_slots(session, shift=shift, academic_year_id=academic_year_id)
        if existing:
            return existing

        template = SHIFT_PERIOD_TEMPLATES.get(shift, DEFAULT_PERIOD_DEFINITIONS)
        shift_obj = session.query(AcademicShift).filter(AcademicShift.name == shift).first()

        created: List[PeriodSlot] = []
        for defn in template:
            slot = TimetableRepository.create_period_slot(
                session,
                period_number=defn["period_number"],
                name=defn["name"],
                start_time=defn["start_time"],
                end_time=defn["end_time"],
                duration_minutes=defn["duration_minutes"],
                is_break=defn["is_break"],
                shift=shift,
                shift_id=shift_obj.id if shift_obj else None,
                academic_year_id=academic_year_id,
            )
            created.append(slot)
        return created

    @staticmethod
    def seed_all_shift_periods(session: Session, academic_year_id: Optional[int] = 1) -> Dict[str, List[PeriodSlot]]:
        """Ensures period schedules exist for Morning, Day, and Evening shifts."""
        result: Dict[str, List[PeriodSlot]] = {}
        for sh_name in ("Morning", "Day", "Evening"):
            result[sh_name] = TimetableService.seed_default_periods(
                session, academic_year_id=academic_year_id, shift=sh_name
            )
        return result

    @staticmethod
    def assign_timetable_slot(
        session: Session,
        academic_year_id: int,
        class_id: int,
        day_of_week: str,
        period_slot_id: int,
        subject_id: int,
        teacher_id: int,
        room_number: str,
        section_id: Optional[int] = None,
        notes: Optional[str] = None,
        entry_id: Optional[int] = None,
        room_id: Optional[int] = None,
        shift: Optional[str] = None,
        shift_id: Optional[int] = None,
        allow_overwrite: bool = False,
        is_auto_generated: bool = False,
        actor_user: Optional[User] = None,
        record_history: bool = True,
    ) -> Tuple[Optional[TimetableEntry], List[str]]:
        """
        Validates Teacher, Room, and Class conflicts and assigns/updates a timetable slot.
        Records an immutable entry in TimetableHistory on change.
        """
        slot_obj = TimetableRepository.get_period_slot_by_id(session, period_slot_id)
        eff_shift = shift or (slot_obj.shift if slot_obj else "Morning")
        eff_shift_id = shift_id or (slot_obj.shift_id if slot_obj else None)

        check_cls_clash = (entry_id is None) and (not allow_overwrite)
        conflicts = TimetableRepository.check_conflicts(
            session=session,
            day_of_week=day_of_week,
            period_slot_id=period_slot_id,
            teacher_id=teacher_id,
            room_number=room_number,
            exclude_entry_id=entry_id,
            academic_year_id=academic_year_id,
            class_id=class_id,
            section_id=section_id,
            room_id=room_id,
            check_class_conflict=check_cls_clash,
        )
        if conflicts:
            return None, conflicts

        username = _actor_username(actor_user)

        if entry_id:
            entry = TimetableRepository.update_timetable_entry(
                session,
                entry_id=entry_id,
                academic_year_id=academic_year_id,
                class_id=class_id,
                section_id=section_id,
                day_of_week=day_of_week,
                period_slot_id=period_slot_id,
                subject_id=subject_id,
                teacher_id=teacher_id,
                room_id=room_id,
                room_number=room_number,
                shift=eff_shift,
                shift_id=eff_shift_id,
                notes=notes,
            )
            if entry and record_history:
                TimetableRepository.record_history(
                    session,
                    academic_year_id=academic_year_id,
                    action="SLOT_UPDATED",
                    class_id=class_id,
                    section_id=section_id,
                    shift_name=eff_shift,
                    version_no=entry.version_no,
                    entry_summary=f"{day_of_week} {slot_obj.name if slot_obj else period_slot_id} -> {room_number}",
                    snapshot={
                        "entry_id": entry.id,
                        "subject_id": subject_id,
                        "teacher_id": teacher_id,
                        "room_number": room_number,
                        "day_of_week": day_of_week,
                        "period_slot_id": period_slot_id,
                    },
                    reason="Manual timetable edit",
                    performed_by=username,
                    commit=True,
                )
            return entry, []

        existing_class_slot = (
            session.query(TimetableEntry)
            .filter(
                TimetableEntry.academic_year_id == academic_year_id,
                TimetableEntry.class_id == class_id,
                TimetableEntry.section_id == section_id,
                TimetableEntry.day_of_week == day_of_week,
                TimetableEntry.period_slot_id == period_slot_id,
                TimetableEntry.is_deleted == False,
            )
            .first()
        )
        if existing_class_slot:
            entry = TimetableRepository.update_timetable_entry(
                session,
                entry_id=existing_class_slot.id,
                subject_id=subject_id,
                teacher_id=teacher_id,
                room_id=room_id,
                room_number=room_number,
                shift=eff_shift,
                shift_id=eff_shift_id,
                is_auto_generated=is_auto_generated,
                notes=notes,
            )
            if entry and record_history:
                TimetableRepository.record_history(
                    session,
                    academic_year_id=academic_year_id,
                    action="SLOT_UPDATED",
                    class_id=class_id,
                    section_id=section_id,
                    shift_name=eff_shift,
                    version_no=entry.version_no,
                    entry_summary=f"Replaced {day_of_week} {slot_obj.name if slot_obj else period_slot_id}",
                    performed_by=username,
                    commit=True,
                )
            return entry, []

        entry = TimetableRepository.create_timetable_entry(
            session,
            academic_year_id=academic_year_id,
            class_id=class_id,
            section_id=section_id,
            day_of_week=day_of_week,
            period_slot_id=period_slot_id,
            subject_id=subject_id,
            teacher_id=teacher_id,
            room_id=room_id,
            room_number=room_number,
            shift=eff_shift,
            shift_id=eff_shift_id,
            is_auto_generated=is_auto_generated,
            notes=notes,
        )
        if record_history:
            TimetableRepository.record_history(
                session,
                academic_year_id=academic_year_id,
                action="SLOT_CREATED",
                class_id=class_id,
                section_id=section_id,
                shift_name=eff_shift,
                version_no=1,
                entry_summary=f"{day_of_week} {slot_obj.name if slot_obj else period_slot_id} -> {room_number}",
                snapshot={
                    "entry_id": entry.id,
                    "subject_id": subject_id,
                    "teacher_id": teacher_id,
                    "room_number": room_number,
                    "day_of_week": day_of_week,
                    "period_slot_id": period_slot_id,
                },
                reason="Manual timetable assignment" if not is_auto_generated else "Auto-generated slot",
                performed_by=username,
                commit=True,
            )
        return entry, []

    @staticmethod
    def move_or_swap_slot(
        session: Session,
        entry_id: int,
        target_day: str,
        target_period_slot_id: int,
        target_room_number: Optional[str] = None,
        swap_if_occupied: bool = True,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, List[str], str]:
        """
        Moves a timetable entry to another (day, period_slot_id) or atomically swaps it with an
        existing class slot at the destination if swap_if_occupied=True, checking all conflicts.
        """
        src = TimetableRepository.get_timetable_entry_by_id(session, entry_id)
        if not src:
            return False, ["Source slot not found."], "Source slot not found."

        dest = (
            session.query(TimetableEntry)
            .filter(
                TimetableEntry.academic_year_id == src.academic_year_id,
                TimetableEntry.class_id == src.class_id,
                TimetableEntry.section_id == src.section_id,
                TimetableEntry.day_of_week == target_day,
                TimetableEntry.period_slot_id == target_period_slot_id,
                TimetableEntry.is_deleted == False,
            )
            .first()
        )
        eff_room = target_room_number or src.room_number
        username = _actor_username(actor_user)

        if not dest:
            conflicts = TimetableRepository.check_conflicts(
                session,
                day_of_week=target_day,
                period_slot_id=target_period_slot_id,
                teacher_id=src.teacher_id,
                room_number=eff_room,
                exclude_entry_id=src.id,
                academic_year_id=src.academic_year_id,
                class_id=src.class_id,
                section_id=src.section_id,
                check_class_conflict=True,
            )
            if conflicts:
                return False, conflicts, "\n".join(conflicts)

            old_info = f"{src.day_of_week} P{src.period_slot_id}"
            src.day_of_week = target_day
            src.period_slot_id = target_period_slot_id
            src.room_number = eff_room
            src.version_no = int(src.version_no or 1) + 1
            TimetableRepository.record_history(
                session,
                academic_year_id=src.academic_year_id,
                action="SLOT_MOVED",
                class_id=src.class_id,
                section_id=src.section_id,
                shift_name=src.shift,
                version_no=src.version_no,
                entry_summary=f"Moved {old_info} -> {target_day} P{target_period_slot_id}",
                performed_by=username,
                commit=False,
            )
            session.commit()
            return True, [], "Slot moved cleanly."

        if not swap_if_occupied:
            msg = [f"Class Conflict: Target slot {target_day} is already occupied."]
            return False, msg, msg[0]

        # Atomic Swap validation (ignore src & dest themselves while verifying other classes)
        c1 = TimetableRepository.check_conflicts(
            session,
            day_of_week=target_day,
            period_slot_id=target_period_slot_id,
            teacher_id=src.teacher_id,
            room_number=src.room_number,
            exclude_entry_id=src.id,
            academic_year_id=src.academic_year_id,
        )
        # Filter out self-dest false alarm if same teacher/room as dest inside same class
        c1_real = []
        for msg in c1:
            if not (dest.teacher_id == src.teacher_id and "Teacher Conflict" in msg):
                c1_real.append(msg)

        c2 = TimetableRepository.check_conflicts(
            session,
            day_of_week=src.day_of_week,
            period_slot_id=src.period_slot_id,
            teacher_id=dest.teacher_id,
            room_number=dest.room_number,
            exclude_entry_id=dest.id,
            academic_year_id=dest.academic_year_id,
        )
        c2_real = []
        for msg in c2:
            if not (dest.teacher_id == src.teacher_id and "Teacher Conflict" in msg):
                c2_real.append(msg)

        all_c = c1_real + c2_real
        if all_c:
            return False, all_c, "\n".join(all_c)

        orig_day, orig_pid = src.day_of_week, src.period_slot_id
        # Temporarily move dest day_of_week to avoid unique constraint collision during flush
        dest.day_of_week = "__SWAP_TMP__"
        session.flush()
        src.day_of_week = target_day
        src.period_slot_id = target_period_slot_id
        src.version_no = int(src.version_no or 1) + 1
        session.flush()
        dest.day_of_week = orig_day
        dest.period_slot_id = orig_pid
        dest.version_no = int(dest.version_no or 1) + 1

        TimetableRepository.record_history(
            session,
            academic_year_id=src.academic_year_id,
            action="SLOT_SWAPPED",
            class_id=src.class_id,
            section_id=src.section_id,
            shift_name=src.shift,
            version_no=src.version_no,
            entry_summary=f"Swapped {orig_day} P{orig_pid} <-> {target_day} P{target_period_slot_id}",
            performed_by=username,
            commit=False,
        )
        session.commit()
        return True, [], "Slots swapped successfully without conflicts."

    @staticmethod
    def delete_slot_with_history(
        session: Session,
        entry_id: int,
        reason: str = "Removed manually",
        actor_user: Optional[User] = None,
    ) -> bool:
        entry = TimetableRepository.get_timetable_entry_by_id(session, entry_id)
        if not entry:
            return False
        username = _actor_username(actor_user)
        TimetableRepository.record_history(
            session,
            academic_year_id=entry.academic_year_id,
            action="SLOT_DELETED",
            class_id=entry.class_id,
            section_id=entry.section_id,
            shift_name=entry.shift,
            version_no=entry.version_no,
            entry_summary=f"Deleted {entry.day_of_week} {entry.period_slot.name if entry.period_slot else entry.period_slot_id} ({entry.subject.name if entry.subject else entry.subject_id})",
            reason=reason,
            performed_by=username,
            commit=False,
        )
        session.delete(entry)
        session.commit()
        return True

    # ---------------- Automatic Timetable Suggestion Algorithm ----------------
    @staticmethod
    def suggest_timetable(
        session: Session,
        academic_year_id: int,
        class_id: int,
        section_id: Optional[int] = None,
        shift: str = "Morning",
        days: Optional[List[str]] = None,
        subject_weekly_quotas: Optional[Dict[int, int]] = None,
        preferred_room_number: Optional[str] = None,
        preferred_room_id: Optional[int] = None,
        apply_immediately: bool = False,
        clear_existing_class_slots: bool = False,
        actor_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """
        Constraint-satisfaction automatic timetable generator.
        - Spreads subjects evenly across days without exceeding available periods.
        - Strictly avoids Teacher, Room, and Class conflicts (including cross-shift overlaps).
        - Uses TeacherSubjectAssignment -> Subject.teacher_id -> active teacher pool.
        - Selects Laboratory rooms automatically for Lab/Science/Computer subjects when available.
        """
        eff_days = days or list(STANDARD_DAYS)
        all_periods = TimetableService.seed_default_periods(
            session, academic_year_id=academic_year_id, shift=shift
        )
        teaching_periods = [p for p in all_periods if not p.is_break]
        if not teaching_periods:
            return {"suggestions": [], "unplaced": [], "applied_count": 0, "total_requested": 0, "utilization_pct": 0.0}

        cls_obj = session.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        sec_obj = session.query(Section).filter(Section.id == section_id).first() if section_id else None

        subjects = (
            session.query(Subject)
            .filter(Subject.class_id == class_id, Subject.is_active == True, Subject.is_deleted == False)
            .order_by(Subject.id.asc())
            .all()
        )
        if not subjects:
            return {"suggestions": [], "unplaced": [], "applied_count": 0, "total_requested": 0, "utilization_pct": 0.0}

        active_teachers = (
            session.query(Teacher)
            .filter(Teacher.status == "Active", Teacher.is_deleted == False)
            .order_by(Teacher.id.asc())
            .all()
        )
        teacher_map = {t.id: t for t in active_teachers}

        tsa_rows = (
            session.query(TeacherSubjectAssignment)
            .filter(
                TeacherSubjectAssignment.class_id == class_id,
                TeacherSubjectAssignment.academic_year_id == academic_year_id,
                TeacherSubjectAssignment.is_active == True,
                TeacherSubjectAssignment.is_deleted == False,
            )
            .all()
        )
        tsa_by_sub: Dict[int, int] = {r.subject_id: r.teacher_id for r in tsa_rows if r.teacher_id in teacher_map}

        rooms_catalog = TimetableRepository.get_distinct_rooms_and_catalog(session, academic_year_id=academic_year_id)
        lab_rooms = [r for r in rooms_catalog if "lab" in (r.get("room_type") or "").lower() or "lab" in r["room_number"].lower()]

        default_room = (
            preferred_room_number
            or (sec_obj.room_number if sec_obj and sec_obj.room_number else None)
            or (rooms_catalog[0]["room_number"] if rooms_catalog else f"Room {cls_obj.numeric_order if cls_obj else 1}01")
        )
        default_room_id = preferred_room_id or (sec_obj.room_id if sec_obj else None)

        if clear_existing_class_slots and apply_immediately:
            q_del = session.query(TimetableEntry).filter(
                TimetableEntry.academic_year_id == academic_year_id,
                TimetableEntry.class_id == class_id,
                TimetableEntry.shift == shift,
                TimetableEntry.is_deleted == False,
            )
            if section_id is not None:
                q_del = q_del.filter(TimetableEntry.section_id == section_id)
            q_del.delete(synchronize_session=False)
            session.flush()

        # Snapshot all active entries in the academic year for rapid in-memory constraint checking
        year_entries = TimetableRepository.get_all_entries(session, academic_year_id=academic_year_id)
        occupied_class_keys = set()
        for e in year_entries:
            if e.class_id == class_id and (e.section_id == section_id or e.section_id is None or section_id is None):
                occupied_class_keys.add((e.day_of_week, e.period_slot_id))

        # Build weekly demand list per subject
        demand_items: List[Tuple[Subject, int]] = []
        total_slots_cap = len(eff_days) * len(teaching_periods) - len(occupied_class_keys)
        if subject_weekly_quotas:
            for sub in subjects:
                qty = int(subject_weekly_quotas.get(sub.id, 0))
                if qty > 0:
                    demand_items.append((sub, qty))
        else:
            # Distribute balanced periods per subject (min 2, capped proportionally to fill schedule neatly)
            per_sub = max(2, min(6, total_slots_cap // max(1, len(subjects))))
            for idx, sub in enumerate(subjects):
                demand_items.append((sub, per_sub))

        # Sort higher weekly-quota subjects first (harder to fit cleanly without repeats per day)
        demand_items.sort(key=lambda x: x[1], reverse=True)

        # In-memory overlay of newly suggested slots for O(1) conflict checking
        suggested_teacher_slots: List[Tuple[str, PeriodSlot, int]] = []
        suggested_room_slots: List[Tuple[str, PeriodSlot, str]] = []
        subject_day_counts: Dict[Tuple[int, str], int] = defaultdict(int)
        day_load: Dict[str, int] = defaultdict(int)
        for e in year_entries:
            if e.class_id == class_id and e.section_id == section_id:
                day_load[e.day_of_week] += 1
                subject_day_counts[(e.subject_id, e.day_of_week)] += 1

        def _is_teacher_free(day: str, p_slot: PeriodSlot, t_id: int) -> bool:
            for e in year_entries:
                if e.day_of_week == day and e.teacher_id == t_id and _period_slots_overlap(p_slot, e.period_slot):
                    return False
            for s_day, s_pslot, s_tid in suggested_teacher_slots:
                if s_day == day and s_tid == t_id and _period_slots_overlap(p_slot, s_pslot):
                    return False
            return True

        def _is_room_free(day: str, p_slot: PeriodSlot, r_num: str) -> bool:
            r_clean = r_num.strip().lower()
            for e in year_entries:
                if e.day_of_week == day and (e.room_number or "").strip().lower() == r_clean and _period_slots_overlap(p_slot, e.period_slot):
                    return False
            for s_day, s_pslot, s_rnum in suggested_room_slots:
                if s_day == day and s_rnum.strip().lower() == r_clean and _period_slots_overlap(p_slot, s_pslot):
                    return False
            return True

        suggestions: List[Dict[str, Any]] = []
        unplaced: List[Dict[str, Any]] = []
        conflicts_avoided = 0

        for sub_idx, (sub, qty) in enumerate(demand_items):
            primary_tid = tsa_by_sub.get(sub.id) or (sub.teacher_id if sub.teacher_id in teacher_map else None)
            if not primary_tid and active_teachers:
                primary_tid = active_teachers[sub_idx % len(active_teachers)].id
            candidate_tids = ([primary_tid] if primary_tid else []) + [
                t.id for t in active_teachers if t.id != primary_tid
            ]

            sub_lower = sub.name.lower()
            prefers_lab = any(k in sub_lower for k in ("lab", "computer", "ict", "physics", "chemistry", "biology"))
            candidate_rooms: List[Tuple[str, Optional[int]]] = []
            if prefers_lab and lab_rooms:
                for lr in lab_rooms:
                    candidate_rooms.append((lr["room_number"], lr["room_id"]))
            candidate_rooms.append((default_room, default_room_id))
            for rc in rooms_catalog:
                if rc["room_number"] != default_room:
                    candidate_rooms.append((rc["room_number"], rc["room_id"]))

            for _ in range(qty):
                best_candidate = None
                best_score = -10_000.0

                for day in eff_days:
                    for p_idx, p_slot in enumerate(teaching_periods):
                        if (day, p_slot.id) in occupied_class_keys:
                            continue

                        # Pick first conflict-free teacher (strongly prefer primary subject teacher)
                        chosen_tid = None
                        for t_pos, tid in enumerate(candidate_tids):
                            if _is_teacher_free(day, p_slot, tid):
                                chosen_tid = tid
                                break
                            else:
                                conflicts_avoided += 1

                        if chosen_tid is None:
                            continue

                        # Pick first conflict-free room
                        chosen_room, chosen_room_id = None, None
                        for r_num, r_id in candidate_rooms:
                            if _is_room_free(day, p_slot, r_num):
                                chosen_room, chosen_room_id = r_num, r_id
                                break
                            else:
                                conflicts_avoided += 1

                        if chosen_room is None:
                            continue

                        # Heuristic score: spread subjects across days, keep primary teacher, balance day load
                        score = 100.0
                        score -= subject_day_counts[(sub.id, day)] * 45.0
                        score -= day_load[day] * 4.0
                        if chosen_tid == primary_tid:
                            score += 25.0
                        if chosen_room == default_room or (prefers_lab and "lab" in chosen_room.lower()):
                            score += 10.0
                        # Prefer earlier periods slightly
                        score -= p_idx * 0.5

                        if score > best_score:
                            best_score = score
                            best_candidate = (day, p_slot, chosen_tid, chosen_room, chosen_room_id)

                if best_candidate is None:
                    unplaced.append({
                        "subject_id": sub.id,
                        "subject_name": sub.name,
                        "reason": "No conflict-free (day, period, teacher, room) slot available.",
                    })
                    continue

                b_day, b_pslot, b_tid, b_room, b_rid = best_candidate
                occupied_class_keys.add((b_day, b_pslot.id))
                suggested_teacher_slots.append((b_day, b_pslot, b_tid))
                suggested_room_slots.append((b_day, b_pslot, b_room))
                subject_day_counts[(sub.id, b_day)] += 1
                day_load[b_day] += 1

                t_obj = teacher_map.get(b_tid)
                suggestions.append({
                    "academic_year_id": academic_year_id,
                    "class_id": class_id,
                    "section_id": section_id,
                    "day_of_week": b_day,
                    "period_slot_id": b_pslot.id,
                    "period_name": b_pslot.name,
                    "shift": b_pslot.shift,
                    "subject_id": sub.id,
                    "subject_name": sub.name,
                    "teacher_id": b_tid,
                    "teacher_name": t_obj.name if t_obj else f"Teacher #{b_tid}",
                    "room_id": b_rid,
                    "room_number": b_room,
                })

        applied_count = 0
        if apply_immediately and suggestions:
            username = _actor_username(actor_user)
            for s in suggestions:
                entry, _ = TimetableService.assign_timetable_slot(
                    session,
                    academic_year_id=academic_year_id,
                    class_id=class_id,
                    section_id=section_id,
                    day_of_week=s["day_of_week"],
                    period_slot_id=s["period_slot_id"],
                    subject_id=s["subject_id"],
                    teacher_id=s["teacher_id"],
                    room_number=s["room_number"],
                    room_id=s["room_id"],
                    shift=s["shift"],
                    is_auto_generated=True,
                    actor_user=actor_user,
                    record_history=False,
                )
                if entry:
                    applied_count += 1

            TimetableRepository.record_history(
                session,
                academic_year_id=academic_year_id,
                action="AUTO_SUGGESTED_APPLIED",
                class_id=class_id,
                section_id=section_id,
                shift_name=shift,
                entry_summary=f"Auto-scheduler placed {applied_count} conflict-free slots ({len(unplaced)} unplaced)",
                snapshot={"placed": suggestions, "unplaced": unplaced},
                reason="Automatic timetable suggestion algorithm applied",
                performed_by=username,
                commit=True,
            )

        total_cap = len(eff_days) * len(teaching_periods)
        util_pct = round((len(occupied_class_keys) / total_cap) * 100.0, 1) if total_cap > 0 else 0.0
        return {
            "suggestions": suggestions,
            "unplaced": unplaced,
            "applied_count": applied_count,
            "total_requested": sum(q for _, q in demand_items),
            "utilization_pct": util_pct,
            "conflicts_avoided": conflicts_avoided,
        }

    # ---------------- Academic Year History Archive & Cloning ----------------
    @staticmethod
    def save_year_snapshot(
        session: Session,
        academic_year_id: int,
        class_id: Optional[int] = None,
        shift_name: Optional[str] = None,
        reason: str = "Academic Year Archive Snapshot",
        actor_user: Optional[User] = None,
    ) -> TimetableHistory:
        entries = TimetableRepository.get_all_entries(
            session, academic_year_id=academic_year_id, class_id=class_id, shift=shift_name
        )
        snap = [
            {
                "class": e.school_class.name if e.school_class else e.class_id,
                "section": e.section.name if e.section else None,
                "day": e.day_of_week,
                "period": e.period_slot.name if e.period_slot else e.period_slot_id,
                "shift": e.shift,
                "subject": e.subject.name if e.subject else e.subject_id,
                "teacher": e.teacher.name if e.teacher else e.teacher_id,
                "room": e.room_number,
            }
            for e in entries
        ]
        prev_cnt = (
            session.query(func.count(TimetableHistory.id))
            .filter(TimetableHistory.academic_year_id == academic_year_id)
            .scalar()
            or 0
        )
        return TimetableRepository.record_history(
            session,
            academic_year_id=academic_year_id,
            action="YEAR_SNAPSHOT",
            class_id=class_id,
            shift_name=shift_name or "All",
            version_no=prev_cnt + 1,
            entry_summary=f"Archived {len(snap)} timetable slots for Academic Year #{academic_year_id}",
            snapshot=snap,
            reason=reason,
            performed_by=_actor_username(actor_user),
            commit=True,
        )

    @staticmethod
    def clone_timetable_from_year(
        session: Session,
        source_academic_year_id: int,
        target_academic_year_id: int,
        shift: Optional[str] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[int, int]:
        """
        Clones historical timetable from source_academic_year_id into target_academic_year_id,
        matching classes, sections, subjects by name/code and checking conflicts cleanly.
        Returns: (cloned_count, skipped_count)
        """
        src_entries = TimetableRepository.get_all_entries(
            session, academic_year_id=source_academic_year_id, shift=shift
        )
        if not src_entries:
            return 0, 0

        target_classes = {
            c.name: c
            for c in session.query(SchoolClass)
            .filter(SchoolClass.academic_year_id == target_academic_year_id, SchoolClass.is_deleted == False)
            .all()
        }

        cloned = 0
        skipped = 0
        for e in src_entries:
            src_cls_name = e.school_class.name if e.school_class else None
            tgt_cls = target_classes.get(src_cls_name) if src_cls_name else e.school_class
            if not tgt_cls:
                tgt_cls_id = e.class_id
                tgt_sec_id = e.section_id
                tgt_sub_id = e.subject_id
            else:
                tgt_cls_id = tgt_cls.id
                tgt_sec_id = None
                if e.section:
                    sec = (
                        session.query(Section)
                        .filter(Section.class_id == tgt_cls.id, Section.name == e.section.name)
                        .first()
                    )
                    tgt_sec_id = sec.id if sec else None
                tgt_sub_id = e.subject_id
                if e.subject:
                    sub = (
                        session.query(Subject)
                        .filter(Subject.class_id == tgt_cls.id, Subject.name == e.subject.name)
                        .first()
                    )
                    if sub:
                        tgt_sub_id = sub.id
                    else:
                        skipped += 1
                        continue

            new_entry, conflicts = TimetableService.assign_timetable_slot(
                session,
                academic_year_id=target_academic_year_id,
                class_id=tgt_cls_id,
                section_id=tgt_sec_id,
                day_of_week=e.day_of_week,
                period_slot_id=e.period_slot_id,
                subject_id=tgt_sub_id,
                teacher_id=e.teacher_id,
                room_number=e.room_number,
                room_id=e.room_id,
                shift=e.shift,
                shift_id=e.shift_id,
                actor_user=actor_user,
                record_history=False,
            )
            if new_entry and not conflicts:
                cloned += 1
            else:
                skipped += 1

        TimetableRepository.record_history(
            session,
            academic_year_id=target_academic_year_id,
            action="CLONED_FROM_YEAR",
            shift_name=shift or "All",
            entry_summary=f"Cloned {cloned} slots from Academic Year #{source_academic_year_id} ({skipped} skipped)",
            reason=f"Carried forward timetable structure from Year #{source_academic_year_id}",
            performed_by=_actor_username(actor_user),
            commit=True,
        )
        return cloned, skipped

    # ---------------- Excel Exporters (Class & Room) ----------------
    @staticmethod
    def export_class_timetable_excel(
        session: Session,
        class_id: int,
        class_name: str,
        section_name: str,
        school_name: str,
        output_path: str,
        academic_year_id: Optional[int] = None,
        shift: Optional[str] = None,
    ) -> bool:
        try:
            import openpyxl
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Class Timetable"

            header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            period_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
            break_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
            slot_fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
            thin_border = Border(
                left=Side(style="thin", color="CBD5E1"),
                right=Side(style="thin", color="CBD5E1"),
                top=Side(style="thin", color="CBD5E1"),
                bottom=Side(style="thin", color="CBD5E1"),
            )

            periods = TimetableRepository.get_period_slots(session, shift=shift, academic_year_id=academic_year_id)
            teaching_periods = [p for p in periods if not p.is_break or "Tiffin" in p.name or "Break" in p.name]
            last_col = get_column_letter(max(2, len(teaching_periods) + 1))

            ws.merge_cells(f"A1:{last_col}1")
            ws["A1"] = school_name.upper()
            ws["A1"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
            ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
            ws["A1"].fill = header_fill

            ws.merge_cells(f"A2:{last_col}2")
            shift_txt = shift or "Morning"
            ws["A2"] = f"WEEKLY CLASS TIMETABLE — {class_name.upper()} (SECTION: {section_name.upper()} | SHIFT: {shift_txt.upper()})"
            ws["A2"].font = Font(name="Arial", size=11, bold=True, color="1E3A8A")
            ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

            ws.cell(row=4, column=1, value="Day \\ Period").font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
            ws.cell(row=4, column=1).fill = period_fill
            ws.cell(row=4, column=1).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=4, column=1).border = thin_border

            for col_idx, p in enumerate(teaching_periods, start=2):
                cell = ws.cell(row=4, column=col_idx)
                cell.value = f"{p.name}\n({p.start_time} - {p.end_time})"
                cell.font = Font(name="Arial", size=9, bold=True, color="FFFFFF")
                cell.fill = period_fill if not p.is_break else PatternFill(start_color="F59E0B", end_color="F59E0B", fill_type="solid")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = thin_border
            ws.row_dimensions[4].height = 32

            matrix = TimetableRepository.get_class_timetable_matrix(
                session, class_id, academic_year_id=academic_year_id, shift=shift
            )
            current_row = 5
            for day in STANDARD_DAYS:
                day_cell = ws.cell(row=current_row, column=1, value=day)
                day_cell.font = Font(name="Arial", size=10, bold=True, color="0F172A")
                day_cell.alignment = Alignment(horizontal="center", vertical="center")
                day_cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
                day_cell.border = thin_border

                for col_idx, p in enumerate(teaching_periods, start=2):
                    cell = ws.cell(row=current_row, column=col_idx)
                    cell.border = thin_border
                    if p.is_break:
                        cell.value = p.name.upper()
                        cell.fill = break_fill
                        cell.font = Font(name="Arial", size=9, bold=True, color="94A3B8")
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    else:
                        entry = matrix.get(day, {}).get(p.id)
                        if entry:
                            sub_name = entry.subject.name if entry.subject else "Subject"
                            t_name = entry.teacher.name if entry.teacher else ""
                            room = entry.room_number or ""
                            cell.value = f"{sub_name}\n{t_name} | {room}"
                            cell.fill = slot_fill
                            cell.font = Font(name="Arial", size=9, color="1E293B")
                            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                        else:
                            cell.value = "—"
                            cell.alignment = Alignment(horizontal="center", vertical="center")
                            cell.font = Font(name="Arial", size=9, color="CBD5E1")
                ws.row_dimensions[current_row].height = 36
                current_row += 1

            ws.column_dimensions["A"].width = 16
            for col_idx in range(2, len(teaching_periods) + 2):
                ws.column_dimensions[get_column_letter(col_idx)].width = 20

            wb.save(output_path)
            return True
        except Exception as e:
            print(f"[TimetableService] Error exporting Class Excel: {e}")
            return False

    @staticmethod
    def export_room_timetable_excel(
        session: Session,
        room_number: str,
        school_name: str,
        output_path: str,
        academic_year_id: Optional[int] = None,
        shift: Optional[str] = None,
    ) -> bool:
        try:
            import openpyxl
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Room Schedule"

            periods = TimetableRepository.get_period_slots(session, shift=shift, academic_year_id=academic_year_id)
            teaching_periods = [p for p in periods if not p.is_break]
            last_col = get_column_letter(max(2, len(teaching_periods) + 1))

            ws.merge_cells(f"A1:{last_col}1")
            ws["A1"] = f"{school_name.upper()} — ROOM SCHEDULE ({room_number})"
            ws["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
            ws["A1"].fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
            ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

            header_fill = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")
            thin = Border(
                left=Side(style="thin", color="CBD5E1"),
                right=Side(style="thin", color="CBD5E1"),
                top=Side(style="thin", color="CBD5E1"),
                bottom=Side(style="thin", color="CBD5E1"),
            )

            ws.cell(row=3, column=1, value="Day \\ Period").font = Font(bold=True, color="FFFFFF")
            ws.cell(row=3, column=1).fill = header_fill
            ws.cell(row=3, column=1).border = thin
            for col_idx, p in enumerate(teaching_periods, start=2):
                c = ws.cell(row=3, column=col_idx, value=f"{p.name}\n({p.start_time}-{p.end_time})")
                c.font = Font(size=9, bold=True, color="FFFFFF")
                c.fill = header_fill
                c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                c.border = thin

            matrix = TimetableRepository.get_room_timetable_matrix(
                session, room_number=room_number, academic_year_id=academic_year_id, shift=shift
            )
            r_idx = 4
            for day in STANDARD_DAYS:
                ws.cell(row=r_idx, column=1, value=day).font = Font(bold=True)
                ws.cell(row=r_idx, column=1).border = thin
                for col_idx, p in enumerate(teaching_periods, start=2):
                    cell = ws.cell(row=r_idx, column=col_idx)
                    cell.border = thin
                    entry = matrix.get(day, {}).get(p.id)
                    if entry:
                        cls_n = entry.school_class.name if entry.school_class else "Class"
                        sub_n = entry.subject.name if entry.subject else "Subject"
                        t_n = entry.teacher.name if entry.teacher else ""
                        cell.value = f"{cls_n}\n{sub_n} ({t_n})"
                        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                    else:
                        cell.value = "Available"
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                ws.row_dimensions[r_idx].height = 34
                r_idx += 1

            ws.column_dimensions["A"].width = 16
            for col_idx in range(2, len(teaching_periods) + 2):
                ws.column_dimensions[get_column_letter(col_idx)].width = 22
            wb.save(output_path)
            return True
        except Exception as e:
            print(f"[TimetableService] Error exporting Room Excel: {e}")
            return False
