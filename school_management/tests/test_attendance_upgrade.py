"""
EduManage Pro - Professional Attendance Upgrade Automated Tests (Pytest)
Validates:
- All 5 statuses (Present, Absent, Late, Leave, Excused)
- Student Daily, Monthly, Date Range, Class, Section, Individual History & Percentages
- Teacher & Non-Teaching Staff Attendance + HR Approved Leave Sync
- Edit Audit Trails & Attendance Correction Request Approval / Rejection Workflows + RBAC
- Optional Pluggable Capture Architecture (QR, RFID, Biometric, Face Recognition) with zero hardware requirement
- Attendance Analytics & Chronic Absenteeism Risk Alerts
"""

import os
import tempfile
from datetime import date, datetime, time as dt_time, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.connection import Base
from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.attendance import (
    AttendanceCorrectionRequest,
    AttendanceDeviceConfig,
    AttendanceScanLog,
    AttendanceStatus,
    StaffAttendance,
    StudentAttendance,
    TeacherAttendance,
)
from app.models.staff import Department, EmployeeLeaveRequest, Staff, Teacher
from app.models.student import Guardian, Student
from app.models.user import Permission, Role, User
from app.repositories.attendance_repository import AttendanceRepository
from app.security.hasher import PasswordHasher
from app.services.attendance_integration import AdapterType, AttendanceIntegrationManager, ScanPayload
from app.services.attendance_service import AttendanceService
from app.services.auth_service import AuthService


@pytest.fixture(scope="function")
def att_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    ay = AcademicYear(name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True)
    db.add(ay)
    db.flush()

    cls9 = SchoolClass(name="Class 9", code="C9", numeric_order=9, academic_year_id=ay.id)
    cls10 = SchoolClass(name="Class 10", code="C10", numeric_order=10, academic_year_id=ay.id)
    db.add_all([cls9, cls10])
    db.flush()

    sec9a = Section(name="Section A", room_number="101", capacity=40, class_id=cls9.id)
    sec9b = Section(name="Section B", room_number="102", capacity=40, class_id=cls9.id)
    sec10a = Section(name="Section A", room_number="201", capacity=40, class_id=cls10.id)
    db.add_all([sec9a, sec9b, sec10a])
    db.flush()

    g = Guardian(father_name="Hasan Ali", guardian_name="Hasan Ali", relation="Father", guardian_phone="+8801710000001")
    db.add(g)
    db.flush()

    s1 = Student(
        student_id="STU-2026-0101",
        admission_number="ADM-901",
        digital_id_code="DIGI-STU-0101",
        qr_payload='{"digital_id_code":"DIGI-STU-0101"}',
        roll_number=1,
        first_name="Ayaan",
        last_name="Hasan",
        full_name="Ayaan Hasan",
        gender="Male",
        date_of_birth=date(2011, 3, 15),
        admission_date=date(2024, 1, 10),
        class_id=cls9.id,
        section_id=sec9a.id,
        academic_year_id=ay.id,
        guardian_id=g.id,
        status="active",
    )
    s2 = Student(
        student_id="STU-2026-0102",
        admission_number="ADM-902",
        digital_id_code="DIGI-STU-0102",
        roll_number=2,
        first_name="Nadia",
        last_name="Rahman",
        full_name="Nadia Rahman",
        gender="Female",
        date_of_birth=date(2011, 7, 22),
        admission_date=date(2024, 1, 10),
        class_id=cls9.id,
        section_id=sec9b.id,
        academic_year_id=ay.id,
        guardian_id=g.id,
        status="active",
    )
    s3 = Student(
        student_id="STU-2026-0103",
        admission_number="ADM-1003",
        digital_id_code="DIGI-STU-0103",
        roll_number=1,
        first_name="Tariq",
        last_name="Mahmud",
        full_name="Tariq Mahmud",
        gender="Male",
        date_of_birth=date(2010, 2, 5),
        admission_date=date(2023, 1, 10),
        class_id=cls10.id,
        section_id=sec10a.id,
        academic_year_id=ay.id,
        guardian_id=g.id,
        status="active",
    )
    db.add_all([s1, s2, s3])

    dept_sci = Department(name="Science", code="SCI")
    dept_adm = Department(name="Administration", code="ADM")
    db.add_all([dept_sci, dept_adm])
    db.flush()

    t1 = Teacher(
        teacher_id="TCH-2026-001",
        employee_id="EMP-T001",
        full_name="Prof. Kamal Uddin",
        gender="Male",
        date_of_birth=date(1980, 5, 14),
        phone="+8801710000101",
        email="kamal@school.local",
        qualification="M.Sc Mathematics",
        department_id=dept_sci.id,
        primary_subject="Mathematics",
        salary=48000,
        status="active",
    )
    stf1 = Staff(
        staff_id="STF-2026-001",
        employee_id="EMP-S001",
        full_name="Salma Begum",
        gender="Female",
        date_of_birth=date(1988, 9, 10),
        phone="+8801710000201",
        email="salma@school.local",
        position="Accountant",
        department_id=dept_adm.id,
        salary=32000,
        status="active",
    )
    stf2 = Staff(
        staff_id="STF-2026-002",
        employee_id="EMP-S002",
        full_name="Rafiq Islam",
        gender="Male",
        date_of_birth=date(1990, 1, 20),
        phone="+8801710000202",
        email="rafiq@school.local",
        position="Receptionist",
        department_id=dept_adm.id,
        salary=24000,
        status="active",
    )
    db.add_all([t1, stf1, stf2])
    db.commit()

    yield db
    db.close()


def test_five_statuses_bulk_section_individual_and_history(att_db):
    db = att_db
    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    cls9 = db.query(SchoolClass).filter_by(code="C9").first()
    sec9a = db.query(Section).filter_by(class_id=cls9.id, name="Section A").first()
    s1 = db.query(Student).filter_by(student_id="STU-2026-0101").first()
    s2 = db.query(Student).filter_by(student_id="STU-2026-0102").first()

    # Section-filtered bulk marking (only s1 in Section A)
    ok, msg = AttendanceService.bulk_set_status(
        db, "student", two_days_ago, AttendanceStatus.PRESENT, class_id=cls9.id, section_id=sec9a.id
    )
    assert ok is True
    assert "1 students" in msg

    # Individual marking across Late, Excused, Leave, Absent
    ok, _ = AttendanceService.mark_individual_attendance(
        db, "student", s1.id, yesterday, AttendanceStatus.EXCUSED, excuse_reason="Regional Math Olympiad"
    )
    assert ok is True
    ok, _ = AttendanceService.mark_individual_attendance(
        db, "student", s1.id, today, AttendanceStatus.LATE, check_in_time="08:50 AM", remarks="Traffic delay"
    )
    assert ok is True

    ok, _ = AttendanceService.mark_individual_attendance(
        db, "student", s2.id, two_days_ago, AttendanceStatus.ABSENT
    )
    assert ok is True
    ok, _ = AttendanceService.mark_individual_attendance(
        db, "student", s2.id, yesterday, AttendanceStatus.LEAVE, remarks="Family event"
    )
    assert ok is True

    # Daily stats include Excused
    y_stats = AttendanceRepository.get_student_daily_stats(db, class_id=cls9.id, att_date=yesterday)
    assert y_stats["excused"] == 1
    assert y_stats["leave"] == 1
    assert y_stats["total_marked"] == 2

    # Individual history & percentage calculation
    hist_s1 = AttendanceRepository.get_student_individual_history(db, s1.id)
    assert hist_s1["total_days"] == 3
    assert hist_s1["present"] == 1
    assert hist_s1["excused"] == 1
    assert hist_s1["late"] == 1
    assert hist_s1["percentage"] == 33.3
    assert hist_s1["effective_percentage"] == 100.0

    # Date range report
    rng = AttendanceService.get_date_range_report(db, "student", two_days_ago, today, class_id=cls9.id)
    assert rng["total"] == 5
    assert rng["excused"] == 1
    assert rng["leave"] == 1
    assert rng["late"] == 1

    # Excel export with Excused column
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        out_path = tmp.name
    try:
        AttendanceService.export_monthly_register_excel(db, cls9.id, today.year, today.month, out_path)
        assert os.path.exists(out_path) and os.path.getsize(out_path) > 1000
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


def test_staff_and_teacher_attendance_with_hr_leave_sync(att_db):
    db = att_db
    today = date.today()
    yesterday = today - timedelta(days=1)

    teacher = db.query(Teacher).first()
    salma = db.query(Staff).filter_by(employee_id="EMP-S001").first()
    rafiq = db.query(Staff).filter_by(employee_id="EMP-S002").first()

    # Approved HR Leave for Salma covering yesterday..today
    lv = EmployeeLeaveRequest(
        employee_type="staff",
        staff_id=salma.id,
        leave_type="Medical",
        start_date=yesterday,
        end_date=today,
        total_days=2,
        reason="Medical checkup",
        status="Approved",
        reviewed_by="principal",
    )
    db.add(lv)
    db.commit()

    # Before explicit save, roster lookup auto-detects Approved HR Leave for Salma
    roster = AttendanceRepository.get_staff_with_attendance(db, att_date=today)
    salma_entry = next(r for r in roster if r["staff"].id == salma.id)
    assert salma_entry["status"] == AttendanceStatus.LEAVE
    assert salma_entry["capture_source"] == "LeaveSync"

    # Explicit HR leave sync persists rows cleanly
    ok, synced_count, _ = AttendanceService.sync_approved_hr_leaves_to_attendance(db, start_date=yesterday, end_date=today)
    assert ok is True
    assert synced_count == 2
    persisted = db.query(StaffAttendance).filter_by(staff_id=salma.id, date=today).first()
    assert persisted is not None
    assert persisted.status == AttendanceStatus.LEAVE
    assert persisted.leave_request_id == lv.id
    assert persisted.capture_source == "LeaveSync"

    # Mark Rafiq & Teacher manually with Excused/Present
    ok, _ = AttendanceService.mark_individual_attendance(db, "staff", rafiq.id, today, AttendanceStatus.PRESENT, "07:55 AM")
    assert ok is True
    ok, _ = AttendanceService.mark_individual_attendance(db, "teacher", teacher.id, today, AttendanceStatus.EXCUSED, excuse_reason="Board Exam Duty")
    assert ok is True

    stf_stats = AttendanceRepository.get_staff_daily_stats(db, today)
    assert stf_stats["total_staff"] == 2
    assert stf_stats["present"] == 1
    assert stf_stats["leave"] == 1

    # Employee Monthly Register
    reg = AttendanceRepository.get_monthly_employee_register(db, "staff", today.year, today.month)
    assert len(reg["register"]) == 2


def test_edit_audit_and_correction_approval_workflow_with_rbac(att_db):
    db = att_db
    AuthService.sync_permission_catalog(db)

    today = date.today()
    s1 = db.query(Student).filter_by(student_id="STU-2026-0101").first()
    teacher = db.query(Teacher).first()

    # Initial mark as Absent
    AttendanceService.mark_individual_attendance(db, "student", s1.id, today, AttendanceStatus.ABSENT)
    att_row = db.query(StudentAttendance).filter_by(student_id=s1.id, date=today).first()
    assert att_row.status == AttendanceStatus.ABSENT
    assert att_row.is_edited is False

    # Direct edit marks audit trail
    ok, _ = AttendanceService.edit_attendance_record(
        db, "student", att_row.id, AttendanceStatus.LATE, check_in_time="08:40 AM", remarks="Arrived late"
    )
    assert ok is True
    db.refresh(att_row)
    assert att_row.is_edited is True
    assert att_row.status == AttendanceStatus.LATE

    # Create Teacher (can submit corrections, CANNOT approve corrections) and Super Admin
    teacher_role = db.query(Role).filter_by(name="teacher").first()
    admin_role = db.query(Role).filter_by(name="super_admin").first()
    u_teacher = User(
        username="tch_user",
        email="tch@school.local",
        full_name="Teacher User",
        password_hash=PasswordHasher.hash_password("StrongPass!123"),
        role_id=teacher_role.id,
        is_active=True,
    )
    u_admin = User(
        username="principal_admin",
        email="principal@school.local",
        full_name="Principal Admin",
        password_hash=PasswordHasher.hash_password("StrongPass!123"),
        role_id=admin_role.id,
        is_active=True,
    )
    db.add_all([u_teacher, u_admin])
    db.commit()

    # Submit correction request #1 -> Rejected (must NOT modify attendance)
    ok, req_rej, _ = AttendanceService.submit_correction_request(
        db, "student", s1.id, today, AttendanceStatus.PRESENT, "Claimed on time", actor_user=u_teacher
    )
    assert ok is True
    assert req_rej.approval_status == "Pending"

    # Teacher attempting approval must fail RBAC
    with pytest.raises(PermissionError):
        AttendanceService.review_correction_request(db, req_rej.id, approve=True, actor_user=u_teacher)

    # Principal rejects request -> student stays Late
    ok, req_rej, _ = AttendanceService.review_correction_request(
        db, req_rej.id, approve=False, review_notes="Gate log confirms 08:40 arrival", actor_user=u_admin
    )
    assert ok is True
    assert req_rej.approval_status == "Rejected"
    db.refresh(att_row)
    assert att_row.status == AttendanceStatus.LATE

    # Submit correction request #2 -> Approved (updates student to Excused)
    ok, req_app, _ = AttendanceService.submit_correction_request(
        db, "student", s1.id, today, AttendanceStatus.EXCUSED, "Medical clinic visit slip attached", actor_user=u_teacher
    )
    assert ok is True
    ok, req_app, _ = AttendanceService.review_correction_request(
        db, req_app.id, approve=True, review_notes="Slip verified", actor_user=u_admin
    )
    assert ok is True
    assert req_app.approval_status == "Approved"
    db.refresh(att_row)
    assert att_row.status == AttendanceStatus.EXCUSED
    assert att_row.capture_source == "Correction"
    assert att_row.edited_by == "principal_admin"

    # Correction for previously unmarked teacher creates TeacherAttendance upon approval
    ok, req_tch, _ = AttendanceService.submit_correction_request(
        db, "teacher", teacher.id, today, AttendanceStatus.PRESENT, "Forgot morning sign-in", requested_check_in="07:50 AM", actor_user=u_teacher
    )
    assert ok is True
    ok, req_tch, _ = AttendanceService.review_correction_request(db, req_tch.id, approve=True, actor_user=u_admin)
    assert ok is True
    t_att = db.query(TeacherAttendance).filter_by(teacher_id=teacher.id, date=today).first()
    assert t_att is not None and t_att.status == AttendanceStatus.PRESENT


def test_optional_hardware_qr_rfid_biometric_face_and_analytics(att_db):
    db = att_db
    now_morning = datetime.combine(date.today(), dt_time(8, 10))
    now_late = datetime.combine(date.today(), dt_time(9, 15))
    now_checkout = datetime.combine(date.today(), dt_time(15, 30))

    s1 = db.query(Student).filter_by(student_id="STU-2026-0101").first()
    s2 = db.query(Student).filter_by(student_id="STU-2026-0102").first()
    s3 = db.query(Student).filter_by(student_id="STU-2026-0103").first()
    teacher = db.query(Teacher).first()
    salma = db.query(Staff).filter_by(employee_id="EMP-S001").first()

    # Zero devices registered initially — confirm manual + QR still work seamlessly
    assert db.query(AttendanceDeviceConfig).count() == 0

    # 1. QR scan using Student JSON QR payload -> Present
    ok, res, _ = AttendanceService.process_scan_event(
        db, AdapterType.QR, '{"digital_id_code":"DIGI-STU-0101"}', direction="CHECK_IN", scan_timestamp=now_morning
    )
    assert ok is True
    assert res["status"] == AttendanceStatus.PRESENT
    assert res["adapter_type"] == AdapterType.QR

    # QR Check-Out updates check_out_time without overwriting status
    ok, res_out, _ = AttendanceService.process_scan_event(
        db, AdapterType.QR, "STU-2026-0101", direction="CHECK_OUT", scan_timestamp=now_checkout
    )
    assert ok is True
    s1_att = db.query(StudentAttendance).filter_by(student_id=s1.id, date=date.today()).first()
    assert s1_att.check_out_time is not None and s1_att.capture_source == "QR"

    # 2. Register optional RFID device & bind Staff RFID UID (with colon normalization)
    ok, dev, _ = AttendanceService.register_capture_device(
        db, "GATE-RFID-01", "Staff Gate RFID", AdapterType.RFID, connection_mode="USB_HID", location="Main Gate"
    )
    assert ok is True and dev.is_mandatory is False

    ok, _, _ = AttendanceService.bind_capture_credential(db, "staff", salma.id, rfid_uid="aa:bb:cc:11")
    assert ok is True
    ok, res_rfid, _ = AttendanceService.process_scan_event(
        db, AdapterType.RFID, "AABBCC11", device_code="GATE-RFID-01", scan_timestamp=now_late
    )
    assert ok is True
    assert res_rfid["subject_type"] == "staff"
    assert res_rfid["status"] == AttendanceStatus.LATE

    # 3. Bind Biometric template for Teacher -> Present
    ok, _, _ = AttendanceService.bind_capture_credential(db, "teacher", teacher.id, biometric_template_id="BIO-FP-9001")
    assert ok is True
    ok, res_bio, _ = AttendanceService.process_scan_event(
        db, AdapterType.BIOMETRIC, "BIO-FP-9001", scan_timestamp=now_morning, confidence_score=0.96
    )
    assert ok is True
    assert res_bio["subject_type"] == "teacher"
    assert res_bio["status"] == AttendanceStatus.PRESENT

    # 4. Future Face Recognition adapter threshold validation
    ok, _, _ = AttendanceService.bind_capture_credential(db, "student", s2.id, face_profile_id="FACE-S2-001")
    assert ok is True
    # Low confidence rejected cleanly
    ok_low, _, msg_low = AttendanceService.process_scan_event(
        db, AdapterType.FACE_RECOGNITION, "FACE-S2-001", scan_timestamp=now_morning, confidence_score=0.60
    )
    assert ok_low is False
    assert "below required threshold" in msg_low

    # High confidence accepted
    ok_hi, res_face, _ = AttendanceService.process_scan_event(
        db, AdapterType.FACE_RECOGNITION, "FACE-S2-001", scan_timestamp=now_morning, confidence_score=0.93
    )
    assert ok_hi is True and res_face["status"] == AttendanceStatus.PRESENT

    # Mark s3 Absent for analytics chronic-absentee alert check (0% < 75%)
    AttendanceService.mark_individual_attendance(db, "student", s3.id, date.today(), AttendanceStatus.ABSENT)

    analytics = AttendanceService.get_attendance_analytics(db, chronic_threshold_pct=75.0)
    assert analytics["overall"]["total"] == 5
    assert analytics["source_breakdown"].get("QR", 0) >= 1
    assert analytics["source_breakdown"].get("RFID", 0) >= 1
    assert analytics["source_breakdown"].get("Biometric", 0) >= 1
    assert analytics["source_breakdown"].get("FaceRecognition", 0) >= 1
    assert analytics["source_breakdown"].get("Manual", 0) >= 1
    assert len(analytics["class_breakdown"]) == 2
    assert len(analytics["department_breakdown"]) == 2
    assert any(c["student_code"] == "STU-2026-0103" for c in analytics["chronic_absentee_students"])
    assert db.query(AttendanceScanLog).count() >= 5
