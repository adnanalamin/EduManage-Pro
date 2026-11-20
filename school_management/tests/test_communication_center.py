"""
EduManage Pro - Communication Center Unit Tests
Covers In-App Feed (Notifications, Announcements, Notices, Alerts),
Pluggable Configurable Provider Adapters (SMS, Email, WhatsApp Business),
Real-DB Triggers (Attendance, Fee Due, Result, Admission, Emergency),
Complete Communication Audit Logs, Retries, and Excel/PDF Exports.
"""

from datetime import date
import os
import tempfile

import pytest
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.connection import Base, create_database_engine
from app.models.academic import AcademicYear, SchoolClass
from app.models.admission import AdmissionApplication, AdmissionStatus
from app.models.attendance import AttendanceStatus, StudentAttendance
from app.models.communication import (
    COMM_CHANNELS,
    INAPP_ITEM_TYPES,
    CommunicationLog,
    CommunicationProviderConfig,
    InAppNotification,
)
from app.models.exam import ExamResultSummary, ExamTerm
from app.models.fee import FeeCategory, FeeStructure, StudentFee
from app.models.notice import SchoolNotice
from app.models.school import SchoolSetting
from app.models.staff import Department, Staff, Teacher
from app.models.student import Guardian, Student, StudentStatus
from app.reports.communication_reports_pdf import CommunicationReportsPDFGenerator
from app.repositories.communication_repository import CommunicationRepository
from app.services.communication_adapters import (
    BaseCommunicationAdapter,
    CommunicationAdapterRegistry,
    DeliveryPayload,
    DeliveryRecipient,
    DeliveryResult,
)
from app.services.communication_service import CommunicationService


@pytest.fixture(scope="function")
def db_session(tmp_path):
    db_file = tmp_path / "communication_test.db"
    engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()

    ay = AcademicYear(name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True)
    session.add(ay)
    session.flush()

    cls = SchoolClass(name="Class 9", code="C9", numeric_order=9, academic_year_id=ay.id)
    dept = Department(name="Science", code="SCI")
    session.add_all([cls, dept])
    session.flush()

    guardian = Guardian(
        guardian_name="Mahmudul Hasan",
        guardian_phone="+8801711223344",
        guardian_email="mahmud.parent@example.com",
    )
    session.add(guardian)
    session.flush()

    stu = Student(
        student_id="STU-COM-01",
        admission_number="ADM-COM-01",
        roll_number=1,
        first_name="Ayan",
        last_name="Hasan",
        full_name="Ayan Hasan",
        gender="Male",
        date_of_birth=date(2011, 3, 15),
        phone="+8801711223344",
        email="ayan@example.com",
        class_id=cls.id,
        academic_year_id=ay.id,
        guardian_id=guardian.id,
        status=StudentStatus.ACTIVE,
    )
    session.add(stu)

    tch = Teacher(
        teacher_id="TCH-COM-01",
        employee_id="EMP-COM-01",
        full_name="Dr. Salma Begum",
        gender="Female",
        date_of_birth=date(1984, 2, 2),
        phone="+8801811223344",
        email="salma@school.local",
        qualification="PhD Chemistry",
        department_id=dept.id,
        primary_subject="Chemistry",
    )
    stf = Staff(
        staff_id="STF-COM-01",
        employee_id="EMP-STF-01",
        full_name="Kamrul Office",
        gender="Male",
        date_of_birth=date(1988, 7, 10),
        phone="+8801911223344",
        email="kamrul@school.local",
        role="Office Assistant",
        department_id=dept.id,
    )
    session.add_all([tch, stf])
    session.commit()

    CommunicationService.seed_defaults_if_empty(session)
    yield session
    session.close()
    engine.dispose()


class _MockCustomSMSAdapter(BaseCommunicationAdapter):
    channel = "SMS"
    driver_key = "custom_test_sms"
    driver_label = "Custom Runtime Test SMS"
    description = "Dynamically registered custom SMS provider adapter."

    def dispatch(self, recipient: DeliveryRecipient, payload: DeliveryPayload, config) -> DeliveryResult:
        return DeliveryResult(
            success=True,
            status="Delivered",
            external_message_id=f"CUSTOM-SMS-{recipient.contact}",
        )

    def health_check(self, config):
        return True, "Custom runtime SMS adapter healthy."


def test_configurable_pluggable_provider_adapters_never_hardcoded(db_session):
    """Verify multiple adapters per channel, dynamic driver registration, default switching, and health check."""
    # Register a brand-new third-party SMS driver at runtime
    CommunicationAdapterRegistry.register_adapter(_MockCustomSMSAdapter())

    custom_cfg = CommunicationRepository.create_provider(
        db_session,
        provider_name="Bangladesh Telecom Custom SMS",
        channel="SMS",
        driver_key="custom_test_sms",
        sender_id="EDUSCHOOL",
        is_default=True,
        sandbox_mode=False,
    )
    ok, msg = CommunicationRepository.test_provider_connection(db_session, custom_cfg.id)
    assert ok is True
    assert "healthy" in msg.lower()

    # Dispatch using the dynamically switched default SMS provider
    log = CommunicationRepository.send_message(
        db_session,
        channel="SMS",
        recipient_name="Parent Test",
        recipient_contact="+8801711000999",
        message_body="Provider abstraction check.",
        scenario_type="Custom",
    )
    assert log.driver_used == "custom_test_sms"
    assert log.provider_name == "Bangladesh Telecom Custom SMS"
    assert log.status == "Delivered"
    assert log.external_message_id == "CUSTOM-SMS-+8801711000999"

    # Also verify WhatsApp Business adapter health & dispatch
    wa_cfg = CommunicationRepository.resolve_provider_for_channel(db_session, "WhatsApp")
    assert wa_cfg is not None
    wa_log = CommunicationRepository.send_message(
        db_session,
        channel="WhatsApp",
        recipient_name="Parent WhatsApp",
        recipient_contact="+8801711223344",
        message_body="WhatsApp Business delivery check.",
        whatsapp_template_name="fee_reminder_v1",
    )
    assert wa_log.channel == "WhatsApp"
    assert wa_log.status == "Sent"


def test_in_app_feed_notifications_announcements_notices_and_alerts(db_session):
    """Verify all 4 In-App types (Notification, Announcement, Notice, Alert), Notice Board sync, and read tracking."""
    for idx, item_type in enumerate(INAPP_ITEM_TYPES, start=1):
        CommunicationRepository.create_in_app_item(
            db_session,
            title=f"Sample {item_type} #{idx}",
            message=f"Body content for {item_type}",
            item_type=item_type,
            severity="Critical" if item_type == "Alert" else "Info",
            target_audience="All",
            sync_to_notice_board=(item_type == "Notice"),
        )

    feed = CommunicationRepository.get_in_app_feed(db_session)
    assert len(feed) == 4
    assert {f.item_type for f in feed} == {"Notification", "Announcement", "Notice", "Alert"}

    # Notice must also appear on SchoolNotice board
    notices = db_session.query(SchoolNotice).all()
    assert len(notices) == 1

    # Read / Mark All Read
    first_id = feed[0].id
    CommunicationRepository.mark_in_app_read(db_session, first_id)
    unread = CommunicationRepository.get_in_app_feed(db_session, unread_only=True)
    assert len(unread) == 3

    updated = CommunicationRepository.mark_all_in_app_read(db_session)
    assert updated == 3
    assert len(CommunicationRepository.get_in_app_feed(db_session, unread_only=True)) == 0


def test_real_db_triggers_attendance_fee_result_admission_emergency(db_session):
    """Verify real DB queries drive Attendance, Fee Due, Result, Admission, and Emergency notifications + logs."""
    stu = db_session.query(Student).first()
    ay = db_session.query(AcademicYear).first()
    cls = db_session.query(SchoolClass).first()

    # 1. Attendance Alert trigger
    att = StudentAttendance(
        student_id=stu.id,
        class_id=stu.class_id,
        attendance_date=date.today(),
        status=AttendanceStatus.ABSENT,
        marked_by="teacher1",
    )
    db_session.add(att)
    db_session.flush()
    att_res = CommunicationService.dispatch_attendance_alerts(
        db_session, target_date=date.today(), channels=("InApp", "SMS")
    )
    assert att_res["matched_records"] == 1
    assert att_res["dispatched"] == 2
    assert att_res["sent"] == 2

    # 2. Fee Due Alert trigger
    fcat = FeeCategory(name="Tuition", code="TUI")
    db_session.add(fcat)
    db_session.flush()
    fs = FeeStructure(
        title="Monthly Tuition",
        category_id=fcat.id,
        class_id=cls.id,
        academic_year_id=ay.id,
        amount=2500.0,
        due_date=date.today(),
    )
    db_session.add(fs)
    db_session.flush()
    sf = StudentFee(
        invoice_no="INV-COM-1001",
        student_id=stu.id,
        fee_structure_id=fs.id,
        academic_year_id=ay.id,
        total_amount=2500.0,
        discount_amount=0.0,
        net_amount=2500.0,
        paid_amount=0.0,
        due_amount=2500.0,
        status="Unpaid",
        due_date=date.today(),
    )
    db_session.add(sf)
    db_session.flush()
    fee_res = CommunicationService.dispatch_fee_due_alerts(
        db_session, channels=("InApp", "SMS", "Email")
    )
    assert fee_res["matched_invoices"] == 1
    assert fee_res["dispatched"] == 3
    assert fee_res["sent"] == 3

    # 3. Result Notification trigger
    term = ExamTerm(
        name="Midterm 2026",
        exam_code="MID-2026",
        academic_year_id=ay.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 15),
    )
    db_session.add(term)
    db_session.flush()
    ers = ExamResultSummary(
        exam_term_id=term.id,
        student_id=stu.id,
        class_id=cls.id,
        total_obtained=460.0,
        total_full_marks=500.0,
        percentage=92.0,
        gpa=5.0,
        cgpa=5.0,
        overall_grade="A+",
        class_rank=1,
        passed_all=True,
        is_published=True,
    )
    db_session.add(ers)
    db_session.flush()
    res_out = CommunicationService.dispatch_result_notifications(
        db_session, exam_term_id=term.id, channels=("InApp", "Email", "WhatsApp")
    )
    assert res_out["matched_results"] == 1
    assert res_out["sent"] == 3

    # 4. Admission Notification trigger
    adm = AdmissionApplication(
        applicant_id="APP-2026-0099",
        academic_year_id=ay.id,
        applying_class_id=cls.id,
        first_name="Rafi",
        last_name="Karim",
        full_name="Rafi Karim",
        gender="Male",
        date_of_birth=date(2012, 1, 10),
        guardian_name="Karim Uddin",
        guardian_phone="+8801755667788",
        guardian_email="karim.adm@example.com",
        status=AdmissionStatus.SELECTED,
        merit_rank=3,
    )
    db_session.add(adm)
    db_session.flush()
    adm_out = CommunicationService.dispatch_admission_notifications(
        db_session, status_filter=AdmissionStatus.SELECTED, channels=("InApp", "Email", "SMS")
    )
    assert adm_out["matched_applications"] == 1
    assert adm_out["sent"] == 3

    # 5. Emergency Notification trigger
    emg_out = CommunicationService.dispatch_emergency_notification(
        db_session,
        title="Cyclone Weather Closure",
        message="Campus closed tomorrow due to severe cyclone warning.",
        target_audience="All",
        channels=("InApp", "SMS", "WhatsApp", "Email"),
    )
    assert emg_out["recipients_targeted"] == 3  # 1 student/guardian + 1 teacher + 1 staff
    assert emg_out["in_app_alert_created"] is True
    assert emg_out["sent"] == 1 + (3 * 3)  # 1 pinned InApp + 3 external channels * 3 recipients

    # Verify failed log + retry + exports
    bad_log = CommunicationRepository.send_message(
        db_session,
        channel="Email",
        recipient_name="Invalid Mail User",
        recipient_contact="not-an-email",
        message_body="Test failure path",
    )
    assert bad_log.status == "Failed"
    bad_log.recipient_contact = "fixed@example.com"
    db_session.commit()
    retried = CommunicationRepository.retry_failed_log(db_session, bad_log.id)
    assert retried.status == "Sent"
    assert retried.attempt_count == 2

    stats = CommunicationRepository.get_communication_stats(db_session)
    assert stats["total_logs"] >= 20
    assert stats["emergency_count"] >= 4

    with tempfile.TemporaryDirectory() as tmpdir:
        xlsx_path = os.path.join(tmpdir, "comm_logs.xlsx")
        CommunicationService.export_communication_logs_excel(db_session, xlsx_path)
        assert os.path.exists(xlsx_path) and os.path.getsize(xlsx_path) > 2000

        pdf_path = os.path.join(tmpdir, "comm_audit.pdf")
        logs = CommunicationRepository.get_communication_logs(db_session)
        CommunicationReportsPDFGenerator.generate_communication_audit_pdf(
            logs, school=db_session.query(SchoolSetting).first(), output_path=pdf_path
        )
        assert os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000
