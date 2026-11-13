"""
EduManage Pro - Attendance Repository Layer
Data access operations for Student, Teacher, and Non-Teaching Staff attendance,
daily/monthly/date-range/individual registers, HR approved-leave detection,
and attendance correction request queries.
"""

import calendar
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import (
    AttendanceCorrectionRequest,
    AttendanceStatus,
    StaffAttendance,
    StudentAttendance,
    TeacherAttendance,
)
from app.models.base import utc_now
from app.models.staff import EmployeeLeaveRequest, Staff, Teacher
from app.models.student import Student


def _compute_pct(numerator: int, denominator: int) -> float:
    return round((numerator / denominator * 100.0), 1) if denominator > 0 else 0.0


class AttendanceRepository:
    # ==================== STUDENT ATTENDANCE ====================
    @staticmethod
    def get_class_students_with_attendance(
        db: Session,
        class_id: int,
        section_id: Optional[int] = None,
        att_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all active students in class/section along with their attendance record for att_date.
        """
        if att_date is None:
            att_date = date.today()

        stu_query = (
            db.query(Student)
            .options(joinedload(Student.school_class), joinedload(Student.section))
            .filter(
                Student.class_id == class_id,
                Student.status == "active",
                Student.is_deleted == False,
            )
        )
        if section_id:
            stu_query = stu_query.filter(Student.section_id == section_id)
        students = stu_query.order_by(Student.roll_number.asc()).all()

        att_query = db.query(StudentAttendance).filter(
            StudentAttendance.class_id == class_id,
            StudentAttendance.date == att_date,
        )
        if section_id:
            att_query = att_query.filter(StudentAttendance.section_id == section_id)
        attendances = {att.student_id: att for att in att_query.all()}

        results = []
        for stu in students:
            att_record = attendances.get(stu.id)
            results.append(
                {
                    "student": stu,
                    "attendance": att_record,
                    "status": att_record.status if att_record else AttendanceStatus.PRESENT,
                    "check_in_time": att_record.check_in_time if att_record else "08:15 AM",
                    "check_out_time": att_record.check_out_time if att_record else None,
                    "remarks": att_record.remarks if att_record else "",
                    "excuse_reason": att_record.excuse_reason if att_record else "",
                    "capture_source": att_record.capture_source if att_record else "Manual",
                    "is_edited": bool(att_record.is_edited) if att_record else False,
                }
            )
        return results

    @staticmethod
    def save_bulk_student_attendance(
        db: Session,
        records: List[Dict[str, Any]],
        marked_by: str = "admin",
        capture_source: str = "Manual",
    ) -> int:
        """
        Upserts (inserts or updates) student attendance records cleanly with edit audit tracking.
        """
        count = 0
        for item in records:
            student_id = item["student_id"]
            att_date = item.get("date", date.today())
            status = AttendanceStatus.normalize(item.get("status", AttendanceStatus.PRESENT))
            remarks = item.get("remarks")
            excuse_reason = item.get("excuse_reason")
            check_in = item.get("check_in_time")
            check_out = item.get("check_out_time")
            class_id = item["class_id"]
            section_id = item.get("section_id")
            academic_year_id = item.get("academic_year_id")
            src = item.get("capture_source") or capture_source
            dev_id = item.get("device_id")

            existing = (
                db.query(StudentAttendance)
                .filter(
                    StudentAttendance.student_id == student_id,
                    StudentAttendance.date == att_date,
                )
                .first()
            )

            if existing:
                changed = (
                    existing.status != status
                    or (remarks is not None and existing.remarks != remarks)
                    or (excuse_reason is not None and existing.excuse_reason != excuse_reason)
                )
                existing.status = status
                existing.remarks = remarks
                if excuse_reason is not None:
                    existing.excuse_reason = excuse_reason
                existing.check_in_time = check_in
                if check_out is not None:
                    existing.check_out_time = check_out
                if section_id is not None:
                    existing.section_id = section_id
                if academic_year_id is not None:
                    existing.academic_year_id = academic_year_id
                existing.marked_by = marked_by
                existing.capture_source = src
                if dev_id is not None:
                    existing.device_id = dev_id
                if changed:
                    existing.is_edited = True
                    existing.edited_by = marked_by
                    existing.edited_at = utc_now()
            else:
                new_att = StudentAttendance(
                    student_id=student_id,
                    class_id=class_id,
                    section_id=section_id,
                    academic_year_id=academic_year_id,
                    date=att_date,
                    status=status,
                    check_in_time=check_in,
                    check_out_time=check_out,
                    remarks=remarks,
                    excuse_reason=excuse_reason,
                    marked_by=marked_by,
                    capture_source=src,
                    device_id=dev_id,
                )
                db.add(new_att)
            count += 1

        db.commit()
        return count

    @staticmethod
    def get_student_daily_stats(
        db: Session,
        class_id: Optional[int] = None,
        att_date: Optional[date] = None,
        section_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        if att_date is None:
            att_date = date.today()

        query = db.query(
            StudentAttendance.status,
            func.count(StudentAttendance.id),
        ).filter(StudentAttendance.date == att_date)

        if class_id:
            query = query.filter(StudentAttendance.class_id == class_id)
        if section_id:
            query = query.filter(StudentAttendance.section_id == section_id)

        rows = query.group_by(StudentAttendance.status).all()
        counts = {s: 0 for s in AttendanceStatus.ALL}
        for st, c in rows:
            if st in counts:
                counts[st] = c

        total_marked = sum(counts.values())
        rate = _compute_pct(counts[AttendanceStatus.PRESENT], total_marked)
        effective_rate = _compute_pct(
            counts[AttendanceStatus.PRESENT] + counts[AttendanceStatus.LATE] + counts[AttendanceStatus.EXCUSED],
            total_marked,
        )

        return {
            "total_marked": total_marked,
            "present": counts[AttendanceStatus.PRESENT],
            "absent": counts[AttendanceStatus.ABSENT],
            "late": counts[AttendanceStatus.LATE],
            "leave": counts[AttendanceStatus.LEAVE],
            "excused": counts[AttendanceStatus.EXCUSED],
            "attendance_rate": rate,
            "effective_rate": effective_rate,
            "date": att_date.isoformat(),
        }

    @staticmethod
    def get_monthly_student_register(
        db: Session,
        class_id: int,
        year: int,
        month: int,
        section_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generates full grid data for monthly student attendance register across all 5 statuses.
        """
        num_days = calendar.monthrange(year, month)[1]
        start_d = date(year, month, 1)
        end_d = date(year, month, num_days)

        stu_query = db.query(Student).filter(
            Student.class_id == class_id,
            Student.status == "active",
            Student.is_deleted == False,
        )
        if section_id:
            stu_query = stu_query.filter(Student.section_id == section_id)
        students = stu_query.order_by(Student.roll_number.asc()).all()

        att_query = db.query(StudentAttendance).filter(
            StudentAttendance.class_id == class_id,
            StudentAttendance.date >= start_d,
            StudentAttendance.date <= end_d,
        )
        if section_id:
            att_query = att_query.filter(StudentAttendance.section_id == section_id)
        attendances = att_query.all()

        lookup = {(att.student_id, att.date.day): att.status for att in attendances}

        grid = []
        for stu in students:
            day_statuses = {}
            counts = {s: 0 for s in AttendanceStatus.ALL}

            for day in range(1, num_days + 1):
                st = lookup.get((stu.id, day), "-")
                day_statuses[day] = st
                if st in counts:
                    counts[st] += 1

            total_recorded = sum(counts.values())
            pct = _compute_pct(counts[AttendanceStatus.PRESENT], total_recorded)
            eff_pct = _compute_pct(
                counts[AttendanceStatus.PRESENT] + counts[AttendanceStatus.LATE] + counts[AttendanceStatus.EXCUSED],
                total_recorded,
            )

            grid.append(
                {
                    "student": stu,
                    "days": day_statuses,
                    "present_count": counts[AttendanceStatus.PRESENT],
                    "absent_count": counts[AttendanceStatus.ABSENT],
                    "late_count": counts[AttendanceStatus.LATE],
                    "leave_count": counts[AttendanceStatus.LEAVE],
                    "excused_count": counts[AttendanceStatus.EXCUSED],
                    "total_recorded": total_recorded,
                    "percentage": pct,
                    "effective_percentage": eff_pct,
                }
            )

        return {
            "year": year,
            "month": month,
            "days_count": num_days,
            "register": grid,
        }

    @staticmethod
    def get_student_attendance_range(
        db: Session,
        start_date: date,
        end_date: date,
        class_id: Optional[int] = None,
        section_id: Optional[int] = None,
        student_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[StudentAttendance]:
        q = (
            db.query(StudentAttendance)
            .options(
                joinedload(StudentAttendance.student),
                joinedload(StudentAttendance.school_class),
                joinedload(StudentAttendance.section),
            )
            .filter(
                StudentAttendance.date >= start_date,
                StudentAttendance.date <= end_date,
            )
        )
        if class_id:
            q = q.filter(StudentAttendance.class_id == class_id)
        if section_id:
            q = q.filter(StudentAttendance.section_id == section_id)
        if student_id:
            q = q.filter(StudentAttendance.student_id == student_id)
        if status:
            q = q.filter(StudentAttendance.status == AttendanceStatus.normalize(status))
        return q.order_by(StudentAttendance.date.desc(), StudentAttendance.student_id.asc()).all()

    @staticmethod
    def get_student_individual_history(
        db: Session,
        student_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        student = (
            db.query(Student)
            .options(joinedload(Student.school_class), joinedload(Student.section))
            .filter(Student.id == student_id)
            .first()
        )
        q = db.query(StudentAttendance).filter(StudentAttendance.student_id == student_id)
        if start_date:
            q = q.filter(StudentAttendance.date >= start_date)
        if end_date:
            q = q.filter(StudentAttendance.date <= end_date)
        records = q.order_by(StudentAttendance.date.desc()).all()

        counts = {s: 0 for s in AttendanceStatus.ALL}
        for r in records:
            if r.status in counts:
                counts[r.status] += 1
        total = len(records)
        return {
            "student": student,
            "records": records,
            "total_days": total,
            "present": counts[AttendanceStatus.PRESENT],
            "absent": counts[AttendanceStatus.ABSENT],
            "late": counts[AttendanceStatus.LATE],
            "leave": counts[AttendanceStatus.LEAVE],
            "excused": counts[AttendanceStatus.EXCUSED],
            "percentage": _compute_pct(counts[AttendanceStatus.PRESENT], total),
            "effective_percentage": _compute_pct(
                counts[AttendanceStatus.PRESENT] + counts[AttendanceStatus.LATE] + counts[AttendanceStatus.EXCUSED],
                total,
            ),
        }

    # ==================== TEACHER & STAFF ATTENDANCE (WITH LEAVE INTEGRATION) ====================
    @staticmethod
    def _approved_leave_lookup(
        db: Session,
        employee_type: str,
        att_date: date,
    ) -> Dict[int, EmployeeLeaveRequest]:
        """Return {employee_pk: EmployeeLeaveRequest} for Approved leaves covering att_date."""
        leaves = (
            db.query(EmployeeLeaveRequest)
            .filter(
                EmployeeLeaveRequest.employee_type == employee_type,
                EmployeeLeaveRequest.status == "Approved",
                EmployeeLeaveRequest.start_date <= att_date,
                EmployeeLeaveRequest.end_date >= att_date,
            )
            .all()
        )
        mapping: Dict[int, EmployeeLeaveRequest] = {}
        for lv in leaves:
            pk = lv.teacher_id if employee_type == "teacher" else lv.staff_id
            if pk:
                mapping[pk] = lv
        return mapping

    @staticmethod
    def get_teachers_with_attendance(
        db: Session,
        att_date: Optional[date] = None,
        department_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if att_date is None:
            att_date = date.today()

        t_query = (
            db.query(Teacher)
            .options(joinedload(Teacher.department))
            .filter(Teacher.status == "active", Teacher.is_deleted == False)
        )
        if department_id:
            t_query = t_query.filter(Teacher.department_id == department_id)
        teachers = t_query.order_by(Teacher.full_name.asc()).all()

        att_query = db.query(TeacherAttendance).filter(TeacherAttendance.date == att_date)
        attendances = {att.teacher_id: att for att in att_query.all()}
        approved_leaves = AttendanceRepository._approved_leave_lookup(db, "teacher", att_date)

        results = []
        for t in teachers:
            att = attendances.get(t.id)
            lv = approved_leaves.get(t.id)
            if att:
                st = att.status
                cin = att.check_in_time or ("-" if st in (AttendanceStatus.ABSENT, AttendanceStatus.LEAVE) else "07:50 AM")
                cout = att.check_out_time or ""
                rem = att.remarks or ""
                src = att.capture_source
            elif lv:
                st = AttendanceStatus.LEAVE
                cin = ""
                cout = ""
                rem = f"{lv.leave_type} Leave (HR Approved #{lv.id})"
                src = "LeaveSync"
            else:
                st = AttendanceStatus.PRESENT
                cin = "07:50 AM"
                cout = "03:15 PM"
                rem = ""
                src = "Manual"

            results.append(
                {
                    "teacher": t,
                    "attendance": att,
                    "approved_leave": lv,
                    "status": st,
                    "check_in_time": cin,
                    "check_out_time": cout,
                    "remarks": rem,
                    "capture_source": src,
                    "is_edited": bool(att.is_edited) if att else False,
                }
            )
        return results

    @staticmethod
    def get_staff_with_attendance(
        db: Session,
        att_date: Optional[date] = None,
        department_id: Optional[int] = None,
        position: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if att_date is None:
            att_date = date.today()

        s_query = (
            db.query(Staff)
            .options(joinedload(Staff.department))
            .filter(Staff.status == "active", Staff.is_deleted == False)
        )
        if department_id:
            s_query = s_query.filter(Staff.department_id == department_id)
        if position:
            s_query = s_query.filter(Staff.position == position)
        staff_members = s_query.order_by(Staff.full_name.asc()).all()

        att_query = db.query(StaffAttendance).filter(StaffAttendance.date == att_date)
        attendances = {att.staff_id: att for att in att_query.all()}
        approved_leaves = AttendanceRepository._approved_leave_lookup(db, "staff", att_date)

        results = []
        for s in staff_members:
            att = attendances.get(s.id)
            lv = approved_leaves.get(s.id)
            if att:
                st = att.status
                cin = att.check_in_time or ""
                cout = att.check_out_time or ""
                rem = att.remarks or ""
                src = att.capture_source
            elif lv:
                st = AttendanceStatus.LEAVE
                cin = ""
                cout = ""
                rem = f"{lv.leave_type} Leave (HR Approved #{lv.id})"
                src = "LeaveSync"
            else:
                st = AttendanceStatus.PRESENT
                cin = "08:00 AM"
                cout = "04:00 PM"
                rem = ""
                src = "Manual"

            results.append(
                {
                    "staff": s,
                    "attendance": att,
                    "approved_leave": lv,
                    "status": st,
                    "check_in_time": cin,
                    "check_out_time": cout,
                    "remarks": rem,
                    "capture_source": src,
                    "is_edited": bool(att.is_edited) if att else False,
                }
            )
        return results

    @staticmethod
    def save_bulk_teacher_attendance(
        db: Session,
        records: List[Dict[str, Any]],
        marked_by: str = "admin",
        capture_source: str = "Manual",
    ) -> int:
        count = 0
        for item in records:
            teacher_id = item["teacher_id"]
            att_date = item.get("date", date.today())
            status = AttendanceStatus.normalize(item.get("status", AttendanceStatus.PRESENT))
            remarks = item.get("remarks")
            excuse_reason = item.get("excuse_reason")
            check_in = item.get("check_in_time")
            check_out = item.get("check_out_time")
            src = item.get("capture_source") or capture_source
            dev_id = item.get("device_id")
            leave_req_id = item.get("leave_request_id")

            existing = (
                db.query(TeacherAttendance)
                .filter(
                    TeacherAttendance.teacher_id == teacher_id,
                    TeacherAttendance.date == att_date,
                )
                .first()
            )

            if existing:
                changed = existing.status != status or (remarks is not None and existing.remarks != remarks)
                existing.status = status
                existing.remarks = remarks
                if excuse_reason is not None:
                    existing.excuse_reason = excuse_reason
                existing.check_in_time = check_in
                existing.check_out_time = check_out
                existing.marked_by = marked_by
                existing.capture_source = src
                if dev_id is not None:
                    existing.device_id = dev_id
                if leave_req_id is not None:
                    existing.leave_request_id = leave_req_id
                if changed:
                    existing.is_edited = True
                    existing.edited_by = marked_by
                    existing.edited_at = utc_now()
            else:
                new_att = TeacherAttendance(
                    teacher_id=teacher_id,
                    date=att_date,
                    status=status,
                    check_in_time=check_in,
                    check_out_time=check_out,
                    remarks=remarks,
                    excuse_reason=excuse_reason,
                    marked_by=marked_by,
                    capture_source=src,
                    device_id=dev_id,
                    leave_request_id=leave_req_id,
                )
                db.add(new_att)
            count += 1

        db.commit()
        return count

    @staticmethod
    def save_bulk_staff_attendance(
        db: Session,
        records: List[Dict[str, Any]],
        marked_by: str = "admin",
        capture_source: str = "Manual",
    ) -> int:
        count = 0
        for item in records:
            staff_id = item["staff_id"]
            att_date = item.get("date", date.today())
            status = AttendanceStatus.normalize(item.get("status", AttendanceStatus.PRESENT))
            remarks = item.get("remarks")
            excuse_reason = item.get("excuse_reason")
            check_in = item.get("check_in_time")
            check_out = item.get("check_out_time")
            src = item.get("capture_source") or capture_source
            dev_id = item.get("device_id")
            leave_req_id = item.get("leave_request_id")

            existing = (
                db.query(StaffAttendance)
                .filter(
                    StaffAttendance.staff_id == staff_id,
                    StaffAttendance.date == att_date,
                )
                .first()
            )

            if existing:
                changed = existing.status != status or (remarks is not None and existing.remarks != remarks)
                existing.status = status
                existing.remarks = remarks
                if excuse_reason is not None:
                    existing.excuse_reason = excuse_reason
                existing.check_in_time = check_in
                existing.check_out_time = check_out
                existing.marked_by = marked_by
                existing.capture_source = src
                if dev_id is not None:
                    existing.device_id = dev_id
                if leave_req_id is not None:
                    existing.leave_request_id = leave_req_id
                if changed:
                    existing.is_edited = True
                    existing.edited_by = marked_by
                    existing.edited_at = utc_now()
            else:
                new_att = StaffAttendance(
                    staff_id=staff_id,
                    date=att_date,
                    status=status,
                    check_in_time=check_in,
                    check_out_time=check_out,
                    remarks=remarks,
                    excuse_reason=excuse_reason,
                    marked_by=marked_by,
                    capture_source=src,
                    device_id=dev_id,
                    leave_request_id=leave_req_id,
                )
                db.add(new_att)
            count += 1

        db.commit()
        return count

    @staticmethod
    def get_teacher_daily_stats(
        db: Session,
        att_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        if att_date is None:
            att_date = date.today()

        total_faculty = db.query(Teacher).filter(Teacher.status == "active", Teacher.is_deleted == False).count()
        rows = (
            db.query(TeacherAttendance.status, func.count(TeacherAttendance.id))
            .filter(TeacherAttendance.date == att_date)
            .group_by(TeacherAttendance.status)
            .all()
        )

        counts = {s: 0 for s in AttendanceStatus.ALL}
        for st, c in rows:
            if st in counts:
                counts[st] = c

        total_marked = sum(counts.values())
        rate = _compute_pct(counts[AttendanceStatus.PRESENT], total_faculty)
        effective_rate = _compute_pct(
            counts[AttendanceStatus.PRESENT] + counts[AttendanceStatus.LATE] + counts[AttendanceStatus.EXCUSED],
            total_faculty,
        )

        return {
            "total_faculty": total_faculty,
            "total_marked": total_marked,
            "present": counts[AttendanceStatus.PRESENT],
            "absent": counts[AttendanceStatus.ABSENT],
            "late": counts[AttendanceStatus.LATE],
            "leave": counts[AttendanceStatus.LEAVE],
            "excused": counts[AttendanceStatus.EXCUSED],
            "attendance_rate": rate,
            "effective_rate": effective_rate,
            "date": att_date.isoformat(),
        }

    @staticmethod
    def get_staff_daily_stats(
        db: Session,
        att_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        if att_date is None:
            att_date = date.today()

        total_staff = db.query(Staff).filter(Staff.status == "active", Staff.is_deleted == False).count()
        rows = (
            db.query(StaffAttendance.status, func.count(StaffAttendance.id))
            .filter(StaffAttendance.date == att_date)
            .group_by(StaffAttendance.status)
            .all()
        )

        counts = {s: 0 for s in AttendanceStatus.ALL}
        for st, c in rows:
            if st in counts:
                counts[st] = c

        total_marked = sum(counts.values())
        rate = _compute_pct(counts[AttendanceStatus.PRESENT], total_staff)
        effective_rate = _compute_pct(
            counts[AttendanceStatus.PRESENT] + counts[AttendanceStatus.LATE] + counts[AttendanceStatus.EXCUSED],
            total_staff,
        )

        return {
            "total_staff": total_staff,
            "total_marked": total_marked,
            "present": counts[AttendanceStatus.PRESENT],
            "absent": counts[AttendanceStatus.ABSENT],
            "late": counts[AttendanceStatus.LATE],
            "leave": counts[AttendanceStatus.LEAVE],
            "excused": counts[AttendanceStatus.EXCUSED],
            "attendance_rate": rate,
            "effective_rate": effective_rate,
            "date": att_date.isoformat(),
        }

    @staticmethod
    def get_monthly_employee_register(
        db: Session,
        target_type: str,
        year: int,
        month: int,
        department_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        etype = (target_type or "").strip().lower()
        num_days = calendar.monthrange(year, month)[1]
        start_d = date(year, month, 1)
        end_d = date(year, month, num_days)

        if etype == "teacher":
            q = db.query(Teacher).options(joinedload(Teacher.department)).filter(
                Teacher.status == "active", Teacher.is_deleted == False
            )
            if department_id:
                q = q.filter(Teacher.department_id == department_id)
            employees = q.order_by(Teacher.full_name.asc()).all()
            att_rows = db.query(TeacherAttendance).filter(
                TeacherAttendance.date >= start_d, TeacherAttendance.date <= end_d
            ).all()
            lookup = {(r.teacher_id, r.date.day): r.status for r in att_rows}
        elif etype == "staff":
            q = db.query(Staff).options(joinedload(Staff.department)).filter(
                Staff.status == "active", Staff.is_deleted == False
            )
            if department_id:
                q = q.filter(Staff.department_id == department_id)
            employees = q.order_by(Staff.full_name.asc()).all()
            att_rows = db.query(StaffAttendance).filter(
                StaffAttendance.date >= start_d, StaffAttendance.date <= end_d
            ).all()
            lookup = {(r.staff_id, r.date.day): r.status for r in att_rows}
        else:
            raise ValueError("target_type must be 'teacher' or 'staff'.")

        grid = []
        for emp in employees:
            day_statuses = {}
            counts = {s: 0 for s in AttendanceStatus.ALL}
            for day in range(1, num_days + 1):
                st = lookup.get((emp.id, day), "-")
                day_statuses[day] = st
                if st in counts:
                    counts[st] += 1

            total_recorded = sum(counts.values())
            grid.append(
                {
                    "employee": emp,
                    "employee_type": etype,
                    "days": day_statuses,
                    "present_count": counts[AttendanceStatus.PRESENT],
                    "absent_count": counts[AttendanceStatus.ABSENT],
                    "late_count": counts[AttendanceStatus.LATE],
                    "leave_count": counts[AttendanceStatus.LEAVE],
                    "excused_count": counts[AttendanceStatus.EXCUSED],
                    "total_recorded": total_recorded,
                    "percentage": _compute_pct(counts[AttendanceStatus.PRESENT], total_recorded),
                    "effective_percentage": _compute_pct(
                        counts[AttendanceStatus.PRESENT] + counts[AttendanceStatus.LATE] + counts[AttendanceStatus.EXCUSED],
                        total_recorded,
                    ),
                }
            )

        return {
            "employee_type": etype,
            "year": year,
            "month": month,
            "days_count": num_days,
            "register": grid,
        }

    @staticmethod
    def get_employee_attendance_range(
        db: Session,
        target_type: str,
        start_date: date,
        end_date: date,
        department_id: Optional[int] = None,
        employee_pk: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Any]:
        etype = (target_type or "").strip().lower()
        if etype == "teacher":
            q = (
                db.query(TeacherAttendance)
                .options(joinedload(TeacherAttendance.teacher).joinedload(Teacher.department))
                .filter(TeacherAttendance.date >= start_date, TeacherAttendance.date <= end_date)
            )
            if employee_pk:
                q = q.filter(TeacherAttendance.teacher_id == employee_pk)
            if department_id:
                q = q.join(Teacher).filter(Teacher.department_id == department_id)
            if status:
                q = q.filter(TeacherAttendance.status == AttendanceStatus.normalize(status))
            return q.order_by(TeacherAttendance.date.desc()).all()

        if etype == "staff":
            q = (
                db.query(StaffAttendance)
                .options(joinedload(StaffAttendance.staff).joinedload(Staff.department))
                .filter(StaffAttendance.date >= start_date, StaffAttendance.date <= end_date)
            )
            if employee_pk:
                q = q.filter(StaffAttendance.staff_id == employee_pk)
            if department_id:
                q = q.join(Staff).filter(Staff.department_id == department_id)
            if status:
                q = q.filter(StaffAttendance.status == AttendanceStatus.normalize(status))
            return q.order_by(StaffAttendance.date.desc()).all()

        raise ValueError("target_type must be 'teacher' or 'staff'.")

    @staticmethod
    def get_employee_individual_history(
        db: Session,
        target_type: str,
        employee_pk: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        etype = (target_type or "").strip().lower()
        if etype == "teacher":
            emp = db.query(Teacher).options(joinedload(Teacher.department)).filter(Teacher.id == employee_pk).first()
            q = db.query(TeacherAttendance).filter(TeacherAttendance.teacher_id == employee_pk)
            date_col = TeacherAttendance.date
        elif etype == "staff":
            emp = db.query(Staff).options(joinedload(Staff.department)).filter(Staff.id == employee_pk).first()
            q = db.query(StaffAttendance).filter(StaffAttendance.staff_id == employee_pk)
            date_col = StaffAttendance.date
        else:
            raise ValueError("target_type must be 'teacher' or 'staff'.")

        if start_date:
            q = q.filter(date_col >= start_date)
        if end_date:
            q = q.filter(date_col <= end_date)
        records = q.order_by(date_col.desc()).all()

        counts = {s: 0 for s in AttendanceStatus.ALL}
        for r in records:
            if r.status in counts:
                counts[r.status] += 1
        total = len(records)
        return {
            "employee": emp,
            "employee_type": etype,
            "records": records,
            "total_days": total,
            "present": counts[AttendanceStatus.PRESENT],
            "absent": counts[AttendanceStatus.ABSENT],
            "late": counts[AttendanceStatus.LATE],
            "leave": counts[AttendanceStatus.LEAVE],
            "excused": counts[AttendanceStatus.EXCUSED],
            "percentage": _compute_pct(counts[AttendanceStatus.PRESENT], total),
            "effective_percentage": _compute_pct(
                counts[AttendanceStatus.PRESENT] + counts[AttendanceStatus.LATE] + counts[AttendanceStatus.EXCUSED],
                total,
            ),
        }

    # ==================== CORRECTION REQUESTS ====================
    @staticmethod
    def list_correction_requests(
        db: Session,
        target_type: Optional[str] = None,
        approval_status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[AttendanceCorrectionRequest]:
        q = db.query(AttendanceCorrectionRequest).options(
            joinedload(AttendanceCorrectionRequest.student),
            joinedload(AttendanceCorrectionRequest.teacher),
            joinedload(AttendanceCorrectionRequest.staff),
        )
        if target_type:
            q = q.filter(AttendanceCorrectionRequest.target_type == target_type.strip().lower())
        if approval_status:
            q = q.filter(AttendanceCorrectionRequest.approval_status == approval_status)
        if start_date:
            q = q.filter(AttendanceCorrectionRequest.attendance_date >= start_date)
        if end_date:
            q = q.filter(AttendanceCorrectionRequest.attendance_date <= end_date)
        return q.order_by(desc(AttendanceCorrectionRequest.id)).all()

    @staticmethod
    def get_correction_request_by_id(db: Session, request_id: int) -> Optional[AttendanceCorrectionRequest]:
        return (
            db.query(AttendanceCorrectionRequest)
            .options(
                joinedload(AttendanceCorrectionRequest.student),
                joinedload(AttendanceCorrectionRequest.teacher),
                joinedload(AttendanceCorrectionRequest.staff),
            )
            .filter(AttendanceCorrectionRequest.id == request_id)
            .first()
        )
