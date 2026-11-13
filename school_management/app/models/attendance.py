"""
EduManage Pro - Attendance Models (SQLAlchemy)
Normalized enterprise models for Student, Teacher, and Non-Teaching Staff Attendance,
Correction Approval Workflows, and Optional Pluggable Hardware Capture (QR, RFID, Biometric, Face).
Manual attendance never depends on hardware availability.
"""

from datetime import date
from typing import Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin, utc_now


class AttendanceStatus:
    PRESENT = "Present"
    ABSENT = "Absent"
    LATE = "Late"
    LEAVE = "Leave"
    EXCUSED = "Excused"

    ALL: List[str] = [PRESENT, ABSENT, LATE, LEAVE, EXCUSED]

    SHORT_CODES: Dict[str, str] = {
        PRESENT: "P",
        ABSENT: "A",
        LATE: "L",
        LEAVE: "Lv",
        EXCUSED: "Ex",
    }

    _CASE_MAP: Dict[str, str] = {
        "present": PRESENT,
        "p": PRESENT,
        "absent": ABSENT,
        "a": ABSENT,
        "late": LATE,
        "l": LATE,
        "leave": LEAVE,
        "lv": LEAVE,
        "excused": EXCUSED,
        "ex": EXCUSED,
    }

    @classmethod
    def normalize(cls, raw_status: Optional[str]) -> str:
        key = (raw_status or "").strip().lower()
        if key in cls._CASE_MAP:
            return cls._CASE_MAP[key]
        raise ValueError(
            f"Unsupported attendance status '{raw_status}'. Must be one of: {', '.join(cls.ALL)}"
        )

    @classmethod
    def is_valid(cls, raw_status: Optional[str]) -> bool:
        return (raw_status or "").strip().lower() in cls._CASE_MAP


class StudentAttendance(Base, TimestampMixin):
    __tablename__ = "student_attendances"

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="RESTRICT"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True)
    date = Column(Date, default=date.today, nullable=False, index=True)

    # Status: 'Present', 'Absent', 'Late', 'Leave', 'Excused'
    status = Column(String(20), default=AttendanceStatus.PRESENT, nullable=False)
    check_in_time = Column(String(20), nullable=True)
    check_out_time = Column(String(20), nullable=True)
    remarks = Column(String(255), nullable=True)
    excuse_reason = Column(String(255), nullable=True)
    marked_by = Column(String(80), default="admin", nullable=False)

    # Capture & Edit Audit Metadata
    capture_source = Column(String(30), default="Manual", nullable=False)
    device_id = Column(String(80), nullable=True)
    is_edited = Column(Boolean, default=False, nullable=False)
    edited_by = Column(String(80), nullable=True)
    edited_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    student = relationship("Student", backref="attendances")
    school_class = relationship("SchoolClass")
    section = relationship("Section")
    academic_year = relationship("AcademicYear")

    __table_args__ = (
        UniqueConstraint("student_id", "date", name="uq_student_daily_attendance"),
        Index("idx_student_att_class_date", "class_id", "date"),
        Index("idx_student_att_date_status", "date", "status"),
    )

    def __repr__(self):
        return f"<StudentAttendance(student_id={self.student_id}, date={self.date}, status='{self.status}')>"


class TeacherAttendance(Base, TimestampMixin):
    __tablename__ = "teacher_attendances"

    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, default=date.today, nullable=False, index=True)

    # Status: 'Present', 'Absent', 'Late', 'Leave', 'Excused'
    status = Column(String(20), default=AttendanceStatus.PRESENT, nullable=False)
    check_in_time = Column(String(20), nullable=True)
    check_out_time = Column(String(20), nullable=True)
    remarks = Column(String(255), nullable=True)
    excuse_reason = Column(String(255), nullable=True)
    marked_by = Column(String(80), default="admin", nullable=False)

    # Leave & Capture Audit Metadata
    capture_source = Column(String(30), default="Manual", nullable=False)
    device_id = Column(String(80), nullable=True)
    leave_request_id = Column(Integer, ForeignKey("hr_leave_requests.id", ondelete="SET NULL"), nullable=True, index=True)
    is_edited = Column(Boolean, default=False, nullable=False)
    edited_by = Column(String(80), nullable=True)
    edited_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    teacher = relationship("Teacher", backref="attendances")

    __table_args__ = (
        UniqueConstraint("teacher_id", "date", name="uq_teacher_daily_attendance"),
        Index("idx_teacher_att_date", "date"),
        Index("idx_teacher_att_date_status", "date", "status"),
    )

    def __repr__(self):
        return f"<TeacherAttendance(teacher_id={self.teacher_id}, date={self.date}, status='{self.status}')>"


class StaffAttendance(Base, TimestampMixin):
    __tablename__ = "staff_attendances"

    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, default=date.today, nullable=False, index=True)

    # Status: 'Present', 'Absent', 'Late', 'Leave', 'Excused'
    status = Column(String(20), default=AttendanceStatus.PRESENT, nullable=False)
    check_in_time = Column(String(20), nullable=True)
    check_out_time = Column(String(20), nullable=True)
    remarks = Column(String(255), nullable=True)
    excuse_reason = Column(String(255), nullable=True)
    marked_by = Column(String(80), default="admin", nullable=False)

    # Leave & Capture Audit Metadata
    capture_source = Column(String(30), default="Manual", nullable=False)
    device_id = Column(String(80), nullable=True)
    leave_request_id = Column(Integer, ForeignKey("hr_leave_requests.id", ondelete="SET NULL"), nullable=True, index=True)
    is_edited = Column(Boolean, default=False, nullable=False)
    edited_by = Column(String(80), nullable=True)
    edited_at = Column(DateTime(timezone=True), nullable=True)

    staff = relationship("Staff", backref="attendances")

    __table_args__ = (
        UniqueConstraint("staff_id", "date", name="uq_staff_daily_attendance"),
        Index("idx_staff_att_date", "date"),
        Index("idx_staff_att_date_status", "date", "status"),
    )

    def __repr__(self):
        return f"<StaffAttendance(staff_id={self.staff_id}, date={self.date}, status='{self.status}')>"


class AttendanceCorrectionRequest(Base, TimestampMixin):
    """
    Workflow table for attendance correction requests & supervisor approvals
    across Students, Teachers, and Non-Teaching Staff.
    """
    __tablename__ = "attendance_correction_requests"

    target_type = Column(String(20), nullable=False, index=True)  # student | teacher | staff
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="CASCADE"), nullable=True, index=True)

    student_attendance_id = Column(Integer, ForeignKey("student_attendances.id", ondelete="SET NULL"), nullable=True)
    teacher_attendance_id = Column(Integer, ForeignKey("teacher_attendances.id", ondelete="SET NULL"), nullable=True)
    staff_attendance_id = Column(Integer, ForeignKey("staff_attendances.id", ondelete="SET NULL"), nullable=True)

    attendance_date = Column(Date, nullable=False, index=True)
    original_status = Column(String(20), nullable=True)
    requested_status = Column(String(20), nullable=False)
    requested_check_in = Column(String(20), nullable=True)
    requested_check_out = Column(String(20), nullable=True)
    reason = Column(Text, nullable=False)
    supporting_doc = Column(String(255), nullable=True)

    approval_status = Column(String(20), default="Pending", nullable=False, index=True)  # Pending | Approved | Rejected
    requested_by = Column(String(80), default="admin", nullable=False)
    requested_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    reviewed_by = Column(String(80), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(String(255), nullable=True)

    student = relationship("Student")
    teacher = relationship("Teacher")
    staff = relationship("Staff")

    __table_args__ = (
        Index("idx_att_corr_target_status", "target_type", "approval_status"),
        Index("idx_att_corr_date", "attendance_date"),
    )


class AttendanceDeviceConfig(Base, TimestampMixin):
    """
    Optional capture channel registry for QR, RFID, Biometric, and future Face Recognition.
    Hardware is strictly optional; manual attendance never requires any device entry.
    """
    __tablename__ = "attendance_devices"

    device_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    adapter_type = Column(String(30), nullable=False, index=True)  # QR | RFID | Biometric | FaceRecognition
    connection_mode = Column(String(40), default="Simulated", nullable=False)  # USB_HID | Serial | TCP_IP | REST_Webhook | Camera | Simulated
    endpoint_or_port = Column(String(180), nullable=True)
    location = Column(String(120), nullable=True)
    is_enabled = Column(Boolean, default=False, nullable=False)
    is_mandatory = Column(Boolean, default=False, nullable=False)
    config_json = Column(Text, nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)


class AttendanceCredentialMapping(Base, TimestampMixin):
    """
    Optional badge / biometric / QR / face template bindings for Students, Teachers, and Staff.
    """
    __tablename__ = "attendance_credentials"

    subject_type = Column(String(20), nullable=False, index=True)  # student | teacher | staff
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="CASCADE"), nullable=True, index=True)

    qr_code_value = Column(String(120), unique=True, nullable=True, index=True)
    rfid_uid = Column(String(80), unique=True, nullable=True, index=True)
    biometric_template_id = Column(String(120), unique=True, nullable=True, index=True)
    face_profile_id = Column(String(120), unique=True, nullable=True, index=True)

    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(String(255), nullable=True)

    student = relationship("Student")
    teacher = relationship("Teacher")
    staff = relationship("Staff")


class AttendanceScanLog(Base, TimestampMixin):
    """Audit log for QR, RFID, Biometric, or Face Recognition scan events."""
    __tablename__ = "attendance_scan_logs"

    adapter_type = Column(String(30), nullable=False, index=True)
    device_id = Column(String(80), nullable=True, index=True)
    raw_identifier = Column(String(180), nullable=False)
    matched_subject_type = Column(String(20), nullable=True)
    matched_subject_id = Column(Integer, nullable=True)
    scan_timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    direction = Column(String(20), default="CHECK_IN", nullable=False)  # CHECK_IN | CHECK_OUT
    confidence_score = Column(Float, nullable=True)
    processing_status = Column(String(20), default="Applied", nullable=False)  # Applied | Duplicate | Unmatched | Error
    notes = Column(String(255), nullable=True)
