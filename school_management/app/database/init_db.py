"""
EduManage Pro - Database Initialization & Seed Data
Runs non-destructive schema migrations and populates baseline roles, hierarchical permissions,
school settings, and starter academic structure.
IMPORTANT: Never seeds hardcoded default administrator passwords in production.
First-Run Setup Wizard handles initial Super Administrator creation securely.
"""

from datetime import date
from sqlalchemy.orm import Session

import app.models  # noqa: F401  Register all ORM tables
from app.database.connection import engine, SessionLocal
from app.database.migrations import migrate_database, CURRENT_SCHEMA_VERSION
from app.models.user import Role
from app.models.school import SchoolSetting
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.services.auth_service import AuthService
from app.config.logging_config import app_logger

# Define default operational roles
SYSTEM_ROLES = [
    ("super_admin", "Super Admin", "Full system access without restrictions", True),
    ("administrator", "Administrator", "Operational school management access", True),
    ("teacher", "Teacher", "Class attendance, marks entry, and timetable access", True),
    ("accountant", "Accountant", "Fee collection, expenses, and accounting records", True),
    ("receptionist", "Receptionist", "Visitor management, notices, and student inquiries", True),
    ("librarian", "Librarian", "Book inventory and student issue tracking", True),
    ("student_guardian", "Student / Guardian", "Personal profile, fee dues, and result cards", True),
]


def init_database() -> bool:
    """
    Synchronizes database schema safely and populates essential baseline reference data.
    Does NOT create any default user or hardcoded password.
    Returns: bool (True if first-run setup / Super Admin creation is required)
    """
    app_logger.info("Verifying database schema & applying non-destructive migrations...")
    migration_report = migrate_database(engine)
    app_logger.info(
        f"Schema ready at v{migration_report['current_version']} ({migration_report['dialect']})"
    )

    session: Session = SessionLocal()
    try:
        # 1. Seed Built-In Roles
        for code, disp, desc, is_sys in SYSTEM_ROLES:
            role = session.query(Role).filter_by(name=code).first()
            if not role:
                role = Role(
                    name=code,
                    display_name=disp,
                    description=desc,
                    is_system_role=is_sys,
                    is_active=True,
                )
                session.add(role)
                session.flush()
                app_logger.info(f"Created system role: {disp}")

        # 2. Seed Hierarchical Permission Catalog (Module -> Feature -> Action) & Default Role Presets
        AuthService.sync_permission_catalog(session)

        # 3. Seed Default Academic Year & Starter Classes if empty
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
                    academic_year_id=ay.id,
                )
                session.add(s_class)
                session.flush()

                sec_a = Section(
                    name="Section A (Padma)",
                    room_number=f"Room {c_order}01",
                    capacity=50,
                    shift=c_shift,
                    group=c_grp,
                    class_id=s_class.id,
                )
                sec_b = Section(
                    name="Section B (Meghna)",
                    room_number=f"Room {c_order}02",
                    capacity=50,
                    shift=c_shift,
                    group=c_grp,
                    class_id=s_class.id,
                )
                session.add_all([sec_a, sec_b])

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
                        class_id=s_class.id,
                    )
                    session.add(sub)
                    sub_counter += 1

        # 4. Seed School Settings if none exists
        settings_record = session.query(SchoolSetting).first()
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
                schema_version=CURRENT_SCHEMA_VERSION,
                current_academic_year_id=ay.id if ay else None,
            )
            session.add(settings_record)
        elif not settings_record.current_academic_year_id and ay:
            settings_record.current_academic_year_id = ay.id

        session.commit()

        # First-run setup is required whenever setup isn't completed OR no active Super Admin exists
        needs_admin_creation = not AuthService.has_super_admin(session)
        return (not settings_record.is_setup_completed) or needs_admin_creation
    except Exception as exc:
        session.rollback()
        app_logger.exception(f"Database initialization failed: {exc}")
        raise
    finally:
        session.close()
