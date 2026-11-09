"""
EduManage Pro - Attendance Repository Layer
Data access operations for Student and Teacher attendance marking, registers, and analytics.
"""

from datetime import date, datetime
import calendar
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from app.models.attendance import StudentAttendance, TeacherAttendance
from app.models.student import Student
from app.models.staff import Teacher


class AttendanceRepository:
    # ==================== STUDENT ATTENDANCE ====================
    @staticmethod
    def get_class_students_with_attendance(
        db: Session,
        class_id: int,
        section_id: Optional[int] = None,
        att_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all active students in class/section along with their attendance record for att_date (if already marked).
        """
        if att_date is None:
            att_date = date.today()

        # Query students
        stu_query = db.query(Student).filter(
            Student.class_id == class_id,
            Student.status == "active"
        )
        if section_id:
            stu_query = stu_query.filter(Student.section_id == section_id)
        students = stu_query.order_by(Student.roll_number.asc()).all()

        # Query existing attendances for this date
        att_query = db.query(StudentAttendance).filter(
            StudentAttendance.class_id == class_id,
            StudentAttendance.date == att_date
        )
        if section_id:
            att_query = att_query.filter(StudentAttendance.section_id == section_id)
        attendances = {att.student_id: att for att in att_query.all()}

        results = []
        for stu in students:
            att_record = attendances.get(stu.id)
            results.append({
                "student": stu,
                "attendance": att_record,
                "status": att_record.status if att_record else "Present",  # default to Present
                "check_in_time": att_record.check_in_time if att_record else "08:15 AM",
                "remarks": att_record.remarks if att_record else "",
            })
        return results

    @staticmethod
    def save_bulk_student_attendance(
        db: Session,
        records: List[Dict[str, Any]],
        marked_by: str = "admin"
    ) -> int:
        """
        Upserts (inserts or updates) student attendance records.
        """
        count = 0
        for item in records:
            student_id = item["student_id"]
            att_date = item.get("date", date.today())
            status = item.get("status", "Present")
            remarks = item.get("remarks")
            check_in = item.get("check_in_time")
            class_id = item["class_id"]
            section_id = item.get("section_id")

            existing = db.query(StudentAttendance).filter(
                StudentAttendance.student_id == student_id,
                StudentAttendance.date == att_date
            ).first()

            if existing:
                existing.status = status
                existing.remarks = remarks
                existing.check_in_time = check_in
                existing.marked_by = marked_by
            else:
                new_att = StudentAttendance(
                    student_id=student_id,
                    class_id=class_id,
                    section_id=section_id,
                    date=att_date,
                    status=status,
                    check_in_time=check_in,
                    remarks=remarks,
                    marked_by=marked_by
                )
                db.add(new_att)
            count += 1

        db.commit()
        return count

    @staticmethod
    def get_student_daily_stats(
        db: Session,
        class_id: Optional[int] = None,
        att_date: Optional[date] = None
    ) -> Dict[str, Any]:
        if att_date is None:
            att_date = date.today()

        query = db.query(
            StudentAttendance.status,
            func.count(StudentAttendance.id)
        ).filter(StudentAttendance.date == att_date)

        if class_id:
            query = query.filter(StudentAttendance.class_id == class_id)

        rows = query.group_by(StudentAttendance.status).all()
        counts = {"Present": 0, "Absent": 0, "Late": 0, "Leave": 0}
        for st, c in rows:
            if st in counts:
                counts[st] = c

        total_marked = sum(counts.values())
        rate = round((counts["Present"] / total_marked * 100), 1) if total_marked > 0 else 0.0

        return {
            "total_marked": total_marked,
            "present": counts["Present"],
            "absent": counts["Absent"],
            "late": counts["Late"],
            "leave": counts["Leave"],
            "attendance_rate": rate,
            "date": att_date.isoformat(),
        }

    @staticmethod
    def get_monthly_student_register(
        db: Session,
        class_id: int,
        year: int,
        month: int,
        section_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generates full grid data for monthly attendance register:
        days in month (1..31), list of students, and their daily status.
        """
        num_days = calendar.monthrange(year, month)[1]
        start_d = date(year, month, 1)
        end_d = date(year, month, num_days)

        # Query students
        stu_query = db.query(Student).filter(
            Student.class_id == class_id,
            Student.status == "active"
        )
        if section_id:
            stu_query = stu_query.filter(Student.section_id == section_id)
        students = stu_query.order_by(Student.roll_number.asc()).all()

        # Query attendances
        att_query = db.query(StudentAttendance).filter(
            StudentAttendance.class_id == class_id,
            StudentAttendance.date >= start_d,
            StudentAttendance.date <= end_d
        )
        if section_id:
            att_query = att_query.filter(StudentAttendance.section_id == section_id)
        attendances = att_query.all()

        # Map by (student_id, day)
        lookup = {}
        for att in attendances:
            lookup[(att.student_id, att.date.day)] = att.status

        grid = []
        for stu in students:
            day_statuses = {}
            present_c = 0
            absent_c = 0
            late_c = 0
            leave_c = 0

            for day in range(1, num_days + 1):
                st = lookup.get((stu.id, day), "-")
                day_statuses[day] = st
                if st == "Present":
                    present_c += 1
                elif st == "Absent":
                    absent_c += 1
                elif st == "Late":
                    late_c += 1
                elif st == "Leave":
                    leave_c += 1

            total_recorded = present_c + absent_c + late_c + leave_c
            pct = round((present_c / total_recorded * 100), 1) if total_recorded > 0 else 0.0

            grid.append({
                "student": stu,
                "days": day_statuses,
                "present_count": present_c,
                "absent_count": absent_c,
                "late_count": late_c,
                "leave_count": leave_c,
                "percentage": pct,
            })

        return {
            "year": year,
            "month": month,
            "days_count": num_days,
            "register": grid,
        }

    # ==================== TEACHER ATTENDANCE ====================
    @staticmethod
    def get_teachers_with_attendance(
        db: Session,
        att_date: Optional[date] = None,
        department_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        if att_date is None:
            att_date = date.today()

        t_query = db.query(Teacher).filter(Teacher.status == "active")
        if department_id:
            t_query = t_query.filter(Teacher.department_id == department_id)
        teachers = t_query.order_by(Teacher.full_name.asc()).all()

        att_query = db.query(TeacherAttendance).filter(TeacherAttendance.date == att_date)
        attendances = {att.teacher_id: att for att in att_query.all()}

        results = []
        for t in teachers:
            att = attendances.get(t.id)
            results.append({
                "teacher": t,
                "attendance": att,
                "status": att.status if att else "Present",
                "check_in_time": att.check_in_time if att else "07:50 AM",
                "check_out_time": att.check_out_time if att else "03:15 PM",
                "remarks": att.remarks if att else "",
            })
        return results

    @staticmethod
    def save_bulk_teacher_attendance(
        db: Session,
        records: List[Dict[str, Any]],
        marked_by: str = "admin"
    ) -> int:
        count = 0
        for item in records:
            teacher_id = item["teacher_id"]
            att_date = item.get("date", date.today())
            status = item.get("status", "Present")
            remarks = item.get("remarks")
            check_in = item.get("check_in_time")
            check_out = item.get("check_out_time")

            existing = db.query(TeacherAttendance).filter(
                TeacherAttendance.teacher_id == teacher_id,
                TeacherAttendance.date == att_date
            ).first()

            if existing:
                existing.status = status
                existing.remarks = remarks
                existing.check_in_time = check_in
                existing.check_out_time = check_out
                existing.marked_by = marked_by
            else:
                new_att = TeacherAttendance(
                    teacher_id=teacher_id,
                    date=att_date,
                    status=status,
                    check_in_time=check_in,
                    check_out_time=check_out,
                    remarks=remarks,
                    marked_by=marked_by
                )
                db.add(new_att)
            count += 1

        db.commit()
        return count

    @staticmethod
    def get_teacher_daily_stats(
        db: Session,
        att_date: Optional[date] = None
    ) -> Dict[str, Any]:
        if att_date is None:
            att_date = date.today()

        total_faculty = db.query(Teacher).filter(Teacher.status == "active").count()
        rows = db.query(
            TeacherAttendance.status,
            func.count(TeacherAttendance.id)
        ).filter(TeacherAttendance.date == att_date).group_by(TeacherAttendance.status).all()

        counts = {"Present": 0, "Absent": 0, "Late": 0, "Leave": 0}
        for st, c in rows:
            if st in counts:
                counts[st] = c

        total_marked = sum(counts.values())
        rate = round((counts["Present"] / total_faculty * 100), 1) if total_faculty > 0 else 0.0

        return {
            "total_faculty": total_faculty,
            "total_marked": total_marked,
            "present": counts["Present"],
            "absent": counts["Absent"],
            "late": counts["Late"],
            "leave": counts["Leave"],
            "attendance_rate": rate,
            "date": att_date.isoformat(),
        }
