"""
EduManage Pro - Enterprise HR Management Module Automated Tests (pytest)
Covers:
- Teacher & Non-Teaching Staff onboarding (Office Staff, Accountant, Receptionist, Librarian, Security Guard, Support Staff)
- Qualifications, Work Experience & Teacher Subject Assignments
- Employment Contracts & Lifecycle workflows (Joining, Promotion, Transfer, Status History)
- Leave Request submission, Approval (auto-sync into TeacherAttendance & StaffAttendance) & Rejection
- Daily Employee Attendance (Teachers & Staff)
- Document Vault upload & verification
- Performance Evaluations & Emergency Contacts
- 360° Employee Timeline
- PDF & Excel HR Reports
- Strict RBAC & Salary Confidentiality enforcement across service, export, and report layers
"""

from datetime import date, timedelta
from pathlib import Path
import openpyxl
import pytest
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.connection import Base, create_database_engine
from app.database.init_db import SYSTEM_ROLES
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.models.attendance import StaffAttendance, TeacherAttendance
from app.models.staff import (
    Department,
    EmployeeStatus,
    STAFF_ROLE_CATALOG,
)
from app.models.user import Role
from app.reports.hr_reports import HRReportsGenerator
from app.repositories.staff_repository import StaffRepository
from app.security.session import session as app_session
from app.services.auth_service import AuthService
from app.services.hr_service import HRService
from app.services.staff_service import StaffService


@pytest.fixture
def hr_db():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()

    StaffRepository.get_or_create_departments(db)
    for code, disp, desc, is_sys in SYSTEM_ROLES:
        db.add(
            Role(
                name=code,
                display_name=disp,
                description=desc,
                is_system_role=is_sys,
                is_active=True,
            )
        )
    db.commit()
    AuthService.sync_permission_catalog(db)
    app_session.clear()

    yield db
    app_session.clear()
    db.close()
    engine.dispose()


def _create_actor(db, role_name: str, username: str):
    super_admin = db.query(Role).filter_by(name="super_admin").first()
    existing_admin = AuthService.has_super_admin(db)
    if not existing_admin:
        ok, admin_u, msg = AuthService.create_first_admin(
            db, "root_hr_admin", "root_hr@school.edu", "Root HR Admin", "V@ultRoot#2026!"
        )
        assert ok, msg
    else:
        admin_u = db.query(Role).filter_by(name="super_admin").first().users[0]

    if role_name == "super_admin":
        return admin_u

    role = db.query(Role).filter_by(name=role_name).first()
    ok, user, msg = AuthService.create_user(
        db,
        actor_user=admin_u,
        username=username,
        email=f"{username}@school.edu",
        full_name=username.title(),
        password="Str0ngUser!2026",
        role_id=role.id,
        must_change_password=False,
    )
    assert ok, msg
    return user


def _seed_academics(db):
    ay = AcademicYear(
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
        status="Active",
    )
    db.add(ay)
    db.flush()

    cls = SchoolClass(name="Class 10", code="C10", numeric_order=10, group="Science", academic_year_id=ay.id)
    db.add(cls)
    db.flush()

    sec = Section(name="Section A", capacity=45, class_id=cls.id)
    db.add(sec)
    subj = Subject(
        subject_id="SUB-2026-PHY",
        name="Physics",
        code="136",
        class_id=cls.id,
    )
    db.add(subj)
    db.commit()
    return ay, cls, sec, subj


def test_teacher_full_hr_lifecycle_and_timeline(hr_db, tmp_path):
    admin = _create_actor(hr_db, "super_admin", "root_hr_admin")
    sci_dept = hr_db.query(Department).filter_by(code="SCI").first()
    math_dept = hr_db.query(Department).filter_by(code="MATH").first()
    ay, cls, sec, subj = _seed_academics(hr_db)

    ok, teacher, msg = HRService.onboard_employee(
        hr_db,
        "teacher",
        {
            "full_name": "Dr. Nusrat Jahan",
            "gender": "Female",
            "date_of_birth": date(1986, 5, 14),
            "phone": "+880 1711-223344",
            "email": "nusrat.jahan@school.edu",
            "qualification": "Ph.D in Physics",
            "designation": "Lecturer",
            "department_id": sci_dept.id,
            "primary_subject": "Physics",
            "joining_date": date(2026, 1, 10),
            "experience_years": 6.0,
            "salary": 55000,
            "bank_name": "City Bank",
            "bank_account_no": "1102203304",
            "status": EmployeeStatus.PROBATION,
        },
        contract_data={
            "contract_type": "Probation",
            "start_date": date(2026, 1, 10),
            "end_date": date.today() + timedelta(days=20),
            "basic_salary": 55000,
            "allowances": 5000,
        },
        emergency_contact={
            "contact_name": "Tariq Jahan",
            "relationship_label": "Spouse",
            "primary_phone": "+880 1711-998877",
        },
        actor_user=admin,
    )
    assert ok is True, msg
    assert teacher.status == EmployeeStatus.PROBATION

    # Qualification & Experience
    ok_q, qual, msg_q = HRService.add_qualification(
        hr_db,
        "teacher",
        teacher.id,
        {"degree_or_cert": "M.Sc in Physics", "institution": "Dhaka University", "completion_year": 2010},
        actor_user=admin,
    )
    assert ok_q is True, msg_q
    assert qual.teacher_id == teacher.id

    ok_e, exp, msg_e = HRService.add_experience(
        hr_db,
        "teacher",
        teacher.id,
        {
            "organization": "Notre Dame College",
            "designation": "Assistant Professor",
            "start_date": date(2022, 1, 1),
            "end_date": date(2024, 1, 1),
        },
        actor_user=admin,
    )
    assert ok_e is True, msg_e
    assert teacher.experience_years > 6.0

    # Subject Assignment
    ok_sa, sa, msg_sa = HRService.assign_subject_to_teacher(
        hr_db, teacher.id, subj.id, cls.id, ay.id, section_id=sec.id, weekly_periods=6, actor_user=admin
    )
    assert ok_sa is True, msg_sa
    assert sa.weekly_periods == 6

    # Expiring contract check + Contract Renewal
    expiring = StaffRepository.list_contracts(hr_db, status="Active", expiring_within_days=30)
    assert len(expiring) == 1
    ok_c, new_ctr, _ = HRService.create_contract(
        hr_db,
        "teacher",
        teacher.id,
        {"contract_type": "Permanent", "basic_salary": 60000, "allowances": 6000},
        actor_user=admin,
    )
    assert ok_c is True
    assert new_ctr.contract_type == "Permanent"
    assert teacher.salary == 60000

    # Promotion, Transfer & Status transition
    ok_p, _, _ = HRService.promote_employee(
        hr_db, "teacher", teacher.id, "Senior Lecturer", new_salary=65000, actor_user=admin
    )
    assert ok_p is True
    assert teacher.designation == "Senior Lecturer"
    assert teacher.salary == 65000

    ok_t, _, _ = HRService.transfer_employee(hr_db, "teacher", teacher.id, math_dept.id, actor_user=admin)
    assert ok_t is True
    assert teacher.department_id == math_dept.id

    ok_st, _, _ = HRService.change_employment_status(
        hr_db, "teacher", teacher.id, EmployeeStatus.ACTIVE, reason="Probation completed", actor_user=admin
    )
    assert ok_st is True
    assert teacher.status == EmployeeStatus.ACTIVE

    # Document Vault upload & verification
    sample_doc = tmp_path / "phd_cert.pdf"
    sample_doc.write_bytes(b"%PDF-1.4\n%sample")
    ok_doc, doc_rec, msg_doc = HRService.add_document(
        hr_db,
        "teacher",
        teacher.id,
        "Academic Certificate",
        "PhD Degree Certificate",
        source_file_path=str(sample_doc),
        actor_user=admin,
    )
    assert ok_doc is True, msg_doc
    assert Path(doc_rec.file_path).exists()
    ok_ver, _ = HRService.verify_document(hr_db, doc_rec.id, verified=True, actor_user=admin)
    assert ok_ver is True
    assert doc_rec.is_verified is True

    # Performance Evaluation
    ok_ev, ev_rec, _ = HRService.record_evaluation(
        hr_db,
        "teacher",
        teacher.id,
        {
            "review_period": "2026 Mid-Year",
            "punctuality_score": 5.0,
            "competency_score": 4.8,
            "teamwork_score": 4.5,
            "compliance_score": 5.0,
            "strengths": "Strong lab supervision",
        },
        actor_user=admin,
    )
    assert ok_ev is True
    assert ev_rec.overall_rating >= 4.5
    assert ev_rec.rating_band == "Outstanding"

    # Timeline aggregation
    timeline = HRService.get_employee_timeline(hr_db, "teacher", teacher.id, actor_user=admin)
    categories = {item["category"] for item in timeline}
    assert {"Joined", "Promotion", "Transfer", "Status Change", "Salary", "Evaluation", "Document"}.issubset(categories)


def test_staff_roles_leave_approval_and_attendance_sync(hr_db):
    admin = _create_actor(hr_db, "super_admin", "root_hr_admin")
    admin_dept = hr_db.query(Department).filter_by(code="ADMIN").first()

    required_roles = [
        "Office Staff",
        "Accountant",
        "Receptionist",
        "Librarian",
        "Security Guard",
        "Support Staff",
    ]
    created_staff = []
    for idx, role_name in enumerate(required_roles):
        assert role_name in STAFF_ROLE_CATALOG
        ok, stf, msg = HRService.onboard_employee(
            hr_db,
            "staff",
            {
                "full_name": f"Staff {role_name}",
                "gender": "Male",
                "date_of_birth": date(1990, 2, 10 + idx),
                "phone": f"+880 1811-00001{idx}",
                "position": role_name,
                "department_id": admin_dept.id,
                "shift": "Day" if role_name != "Security Guard" else "Night",
                "salary": 24000 + idx * 2000,
                "status": EmployeeStatus.ACTIVE,
            },
            actor_user=admin,
        )
        assert ok is True, msg
        created_staff.append(stf)

    # Mark daily attendance for Staff
    today = date.today()
    ok_att, msg_att = HRService.mark_employee_attendance(
        hr_db,
        "staff",
        today,
        [{"staff_id": created_staff[0].id, "date": today, "status": "Present"}],
        actor_user=admin,
    )
    assert ok_att is True, msg_att
    assert hr_db.query(StaffAttendance).filter_by(staff_id=created_staff[0].id, date=today).first().status == "Present"

    # Submit Leave & Approve -> auto-syncs into StaffAttendance
    lv_start = today - timedelta(days=3)
    lv_end = today - timedelta(days=2)
    ok_lv, req, msg_lv = HRService.submit_leave_request(
        hr_db, "staff", created_staff[1].id, "Sick", lv_start, lv_end, "Fever & rest", actor_user=admin
    )
    assert ok_lv is True, msg_lv
    assert req.total_days == 2

    ok_app, req_app, _ = HRService.approve_leave_request(hr_db, req.id, remarks="Get well soon", actor_user=admin)
    assert ok_app is True
    assert req_app.status == "Approved"

    synced_rows = hr_db.query(StaffAttendance).filter_by(staff_id=created_staff[1].id, status="Leave").all()
    assert len(synced_rows) == 2


def test_strict_salary_confidentiality_and_hr_rbac(hr_db, tmp_path):
    admin = _create_actor(hr_db, "super_admin", "root_hr_admin")
    teacher_user = _create_actor(hr_db, "teacher", "faculty_user")
    receptionist_user = _create_actor(hr_db, "receptionist", "frontdesk_user")
    accountant_user = _create_actor(hr_db, "accountant", "finance_user")

    dept = hr_db.query(Department).filter_by(code="SCI").first()
    ok, t, _ = HRService.onboard_employee(
        hr_db,
        "teacher",
        {
            "full_name": "Confidential Salary Teacher",
            "gender": "Male",
            "date_of_birth": date(1987, 4, 1),
            "phone": "+880 1755-123123",
            "email": "conf.teacher@school.edu",
            "qualification": "M.Sc",
            "designation": "Senior Teacher",
            "department_id": dept.id,
            "primary_subject": "Chemistry",
            "salary": 72500,
            "bank_name": "BRAC Bank",
            "bank_account_no": "9988776655",
            "status": EmployeeStatus.ACTIVE,
        },
        actor_user=admin,
    )
    assert ok is True

    # 1. Unauthorized roles (teacher, receptionist) MUST NOT see or change salary
    for unauth_user in (teacher_user, receptionist_user):
        dossier = HRService.get_employee_dossier(hr_db, "teacher", t.id, actor_user=unauth_user)
        assert dossier["salary_visible"] is False
        assert dossier["salary"] is None
        assert dossier["salary_display"] == "[RESTRICTED]"
        assert dossier["bank_name"] == "[RESTRICTED]"
        assert dossier["bank_account_no"] == "[RESTRICTED]"

        kpis = HRService.get_hr_kpis(hr_db, actor_user=unauth_user)
        assert kpis["salary_visible"] is False
        assert kpis["monthly_payroll"] is None

        timeline = HRService.get_employee_timeline(hr_db, "teacher", t.id, actor_user=unauth_user)
        assert all(ev["category"] != "Salary" for ev in timeline)

        with pytest.raises(PermissionError):
            HRService.get_salary_history(hr_db, "teacher", t.id, actor_user=unauth_user)

        with pytest.raises(PermissionError):
            HRService.revise_salary(hr_db, "teacher", t.id, new_salary=99999, actor_user=unauth_user)

        with pytest.raises(PermissionError):
            HRService.promote_employee(
                hr_db, "teacher", t.id, "Principal", new_salary=120000, actor_user=unauth_user
            )

        with pytest.raises(PermissionError):
            HRReportsGenerator.generate_payroll_salary_report(
                hr_db, str(tmp_path / f"payroll_{unauth_user.username}.pdf"), actor_user=unauth_user
            )

        # Excel directory export must omit salary column for unauthorized roles
        xlsx_path = tmp_path / f"teachers_{unauth_user.username}.xlsx"
        StaffService.export_teachers_to_excel(hr_db, str(xlsx_path), actor_user=unauth_user)
        wb = openpyxl.load_workbook(xlsx_path)
        headers = [cell.value for cell in wb.active[1]]
        assert not any("Salary" in str(h) for h in headers)

    # Receptionist / Teacher also cannot approve leave requests
    ok_lv, req, _ = HRService.submit_leave_request(
        hr_db, "teacher", t.id, "Casual", date.today(), date.today(), "Personal errand", actor_user=teacher_user
    )
    assert ok_lv is True
    with pytest.raises(PermissionError):
        HRService.approve_leave_request(hr_db, req.id, actor_user=teacher_user)
    with pytest.raises(PermissionError):
        HRService.approve_leave_request(hr_db, req.id, actor_user=receptionist_user)

    # 2. Accountant CAN view salary & export payroll, but CANNOT revise salary without EDIT permission
    acc_dossier = HRService.get_employee_dossier(hr_db, "teacher", t.id, actor_user=accountant_user)
    assert acc_dossier["salary_visible"] is True
    assert acc_dossier["salary"] == 72500

    acc_hist = HRService.get_salary_history(hr_db, "teacher", t.id, actor_user=accountant_user)
    assert len(acc_hist) >= 1

    with pytest.raises(PermissionError):
        HRService.revise_salary(hr_db, "teacher", t.id, new_salary=80000, actor_user=accountant_user)

    payroll_pdf = tmp_path / "payroll_accountant.pdf"
    HRReportsGenerator.generate_payroll_salary_report(
        hr_db, str(payroll_pdf), fmt="pdf", actor_user=accountant_user
    )
    assert payroll_pdf.exists() and payroll_pdf.stat().st_size > 0

    # 3. Admin CAN revise salary and generate all HR reports
    ok_rev, rev_entry, _ = HRService.revise_salary(
        hr_db, "teacher", t.id, new_salary=78000, allowances=4000, change_reason="Annual Increment", actor_user=admin
    )
    assert ok_rev is True
    assert rev_entry.new_salary == 78000

    dir_pdf = tmp_path / "hr_dir.pdf"
    leave_xlsx = tmp_path / "hr_leaves.xlsx"
    att_pdf = tmp_path / "hr_att.pdf"
    ctr_pdf = tmp_path / "hr_ctr.pdf"
    perf_xlsx = tmp_path / "hr_perf.xlsx"
    HRReportsGenerator.generate_employee_directory_report(hr_db, str(dir_pdf), fmt="pdf", actor_user=admin)
    HRReportsGenerator.generate_leave_report(hr_db, str(leave_xlsx), fmt="xlsx", actor_user=admin)
    HRReportsGenerator.generate_attendance_report(hr_db, str(att_pdf), fmt="pdf", actor_user=admin)
    HRReportsGenerator.generate_contracts_report(hr_db, str(ctr_pdf), fmt="pdf", actor_user=admin)
    HRReportsGenerator.generate_performance_report(hr_db, str(perf_xlsx), fmt="xlsx", actor_user=admin)
    for p in (dir_pdf, leave_xlsx, att_pdf, ctr_pdf, perf_xlsx):
        assert p.exists() and p.stat().st_size > 0
