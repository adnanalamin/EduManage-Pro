"""
EduManage Pro - Database Initialization & Seed Data
Creates tables, default roles, permissions, initial Super Admin, and school settings.
"""

from datetime import date
from sqlalchemy.orm import Session
from app.database.connection import engine, Base, SessionLocal
from app.models.user import User, Role, Permission
from app.models.school import SchoolSetting
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.models.activity import ActivityLog
from app.models.certificate import CertificateRecord
from app.security.hasher import PasswordHasher
from app.config.logging_config import app_logger

# Define default roles
SYSTEM_ROLES = [
    ("super_admin", "Super Admin", "Full system access without restrictions", True),
    ("administrator", "Administrator", "Operational school management access", True),
    ("teacher", "Teacher", "Class attendance, marks entry, and timetable access", True),
    ("accountant", "Accountant", "Fee collection, expenses, and accounting records", True),
    ("receptionist", "Receptionist", "Visitor management, notices, and student inquiries", True),
    ("librarian", "Librarian", "Book inventory and student issue tracking", True),
    ("student_guardian", "Student / Guardian", "Personal profile, fee dues, and result cards", True),
]

# Define default core permissions
DEFAULT_PERMISSIONS = [
    ("students.view", "STUDENTS", "View Students", "Allow viewing student list and profiles"),
    ("students.create", "STUDENTS", "Create Student", "Allow admitting new students"),
    ("students.edit", "STUDENTS", "Edit Student", "Allow modifying student records"),
    ("students.delete", "STUDENTS", "Delete Student", "Allow deleting or archiving students"),
    ("teachers.view", "TEACHERS", "View Teachers", "Allow viewing teacher directories"),
    ("teachers.manage", "TEACHERS", "Manage Teachers", "Allow adding/editing faculty members"),
    ("fees.collect", "FEES", "Collect Fees", "Allow collecting student fees and issuing receipts"),
    ("fees.view", "FEES", "View Fees", "Allow viewing fee ledgers and reports"),
    ("accounting.manage", "ACCOUNTING", "Manage Accounts", "Allow entering income and expenses"),
    ("attendance.mark", "ATTENDANCE", "Mark Attendance", "Allow marking daily attendance"),
    ("exams.marks", "EXAMS", "Enter Marks", "Allow inputting exam scores and grades"),
    ("reports.view", "REPORTS", "View Reports", "Allow viewing all school operational reports"),
    ("settings.manage", "SETTINGS", "Manage Settings", "Allow altering system settings and backups"),
]


def init_database() -> bool:
    """
    Initializes database schema and populates essential baseline data.
    Returns: bool (True if setup wizard is required, False if already completed)
    """
    app_logger.info("Verifying database schema...")
    Base.metadata.create_all(bind=engine)
    
    session: Session = SessionLocal()
    try:
        # 1. Seed Roles
        role_map = {}
        for code, disp, desc, is_sys in SYSTEM_ROLES:
            role = session.query(Role).filter_by(name=code).first()
            if not role:
                role = Role(name=code, display_name=disp, description=desc, is_system_role=is_sys)
                session.add(role)
                session.flush()
                app_logger.info(f"Created system role: {disp}")
            role_map[code] = role

        # 2. Seed Permissions
        perm_map = {}
        for code, mod, name, desc in DEFAULT_PERMISSIONS:
            perm = session.query(Permission).filter_by(code=code).first()
            if not perm:
                perm = Permission(code=code, module=mod, name=name, description=desc)
                session.add(perm)
                session.flush()
            perm_map[code] = perm

        # Assign permissions to Administrator
        admin_role = role_map.get("administrator")
        if admin_role and not admin_role.permissions:
            admin_role.permissions = list(perm_map.values())

        # 3. Seed Default Super Admin Account if none exists
        super_admin_role = role_map["super_admin"]
        existing_admin = session.query(User).filter(User.role_id == super_admin_role.id).first()
        if not existing_admin:
            default_admin = User(
                username="admin",
                email="admin@school.local",
                password_hash=PasswordHasher.hash_password("Admin@123"),
                full_name="System Super Administrator",
                phone="+880 1700-000000",
                role_id=super_admin_role.id,
                is_active=True,
                is_default_password=True,
            )
            session.add(default_admin)
            app_logger.info("Default Super Admin created: username='admin', password='Admin@123'")

        # 4. Seed School Settings if none exists
        settings_record = session.query(SchoolSetting).first()
        is_first_run = False
        if not settings_record:
            settings_record = SchoolSetting(
                school_name="Ideal Model High School & College",
                school_name_bn="আইডিয়াল মডেল হাই স্কুল অ্যান্ড কলেজ",
                motto="Excellence in Education & Character",
                eiin_number="134211",
                registration_no="REG-DH-2024-889",
                address="Plot 12, Road 4, Sector 7, Uttara",
                city="Dhaka",
                district="Dhaka",
                country="Bangladesh",
                phone="+880 1712-345678",
                email="contact@idealmodel.edu.bd",
                currency_code="BDT",
                currency_symbol="৳",
                is_setup_completed=False,
            )
            session.add(settings_record)
            is_first_run = True

        # 5. Seed Default Academic Year if none exists
        ay = session.query(AcademicYear).first()
        if not ay:
            current_year = date.today().year
            ay = AcademicYear(
                name=f"{current_year}-{current_year + 1}",
                start_date=date(current_year, 1, 1),
                end_date=date(current_year, 12, 31),
                is_current=True,
            )
            session.add(ay)
            session.flush()

            # Seed standard starter classes
            classes_to_seed = [
                ("Class 6", "C6", 6, "General", "Morning"),
                ("Class 7", "C7", 7, "General", "Morning"),
                ("Class 8", "C8", 8, "General", "Morning"),
                ("Class 9", "C9", 9, "Science", "Day"),
                ("Class 10", "C10", 10, "Science", "Day"),
            ]
            sub_counter = 1
            for c_name, c_code, c_order, c_grp, c_shift in classes_to_seed:
                s_class = SchoolClass(
                    name=c_name,
                    code=c_code,
                    numeric_order=c_order,
                    group=c_grp,
                    shift=c_shift,
                    academic_year_id=ay.id
                )
                session.add(s_class)
                session.flush()

                # Add default Section A & B
                sec_a = Section(
                    name="Section A (Padma)",
                    room_number=f"Room {c_order}01",
                    capacity=50,
                    shift=c_shift,
                    group=c_grp,
                    class_id=s_class.id
                )
                sec_b = Section(
                    name="Section B (Meghna)",
                    room_number=f"Room {c_order}02",
                    capacity=50,
                    shift=c_shift,
                    group=c_grp,
                    class_id=s_class.id
                )
                session.add_all([sec_a, sec_b])

                # Add core subjects with theory and practical breakdown
                core_subs = [
                    ("Bangla 1st Paper", "101", 100, 33, 100, 0, "Mandatory"),
                    ("English 1st Paper", "107", 100, 33, 100, 0, "Mandatory"),
                    ("Mathematics", "109", 100, 33, 100, 0, "Mandatory"),
                    ("General Science", "127", 100, 33, 75, 25, "Mandatory"),
                ]
                for s_name, s_code, f_m, p_m, th_m, pr_m, s_type in core_subs:
                    sub = Subject(
                        subject_id=f"SUB-{current_year}-{sub_counter:04d}",
                        name=s_name,
                        code=s_code,
                        full_marks=f_m,
                        pass_marks=p_m,
                        theory_marks=th_m,
                        practical_marks=pr_m,
                        subject_type=s_type,
                        is_optional=(s_type == "Optional"),
                        class_id=s_class.id
                    )
                    session.add(sub)
                    sub_counter += 1

        session.commit()
        return not settings_record.is_setup_completed
    except Exception as exc:
        session.rollback()
        app_logger.exception(f"Database initialization failed: {exc}")
        raise
    finally:
        session.close()
