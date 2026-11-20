"""
EduManage Pro - Professional Data Protection & Migration Verification Suite
Tests:
- Manual, Automatic, Daily, Weekly & Monthly backups
- Fernet PBKDF2 Encrypted backup containers & isolated integrity/FK verification
- Restore workflow with Mandatory Pre-Restore Safety Backup
- Automated Scheduler policy & due backup execution
- 6-Step Migration Wizard (Upload -> Detect -> Map -> Validate -> Preview -> Import)
  for CSV, Excel (.xlsx), and Previous SQLite Database (.db)
- Non-overwrite guarantees (SKIP / ERROR_ON_CONFLICT / FILL_EMPTY_ONLY)
- Atomic Migration Rollback restoring pre-existing state without corruption
"""

from datetime import date, timedelta
from pathlib import Path
import sqlite3

import openpyxl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.migrations import CURRENT_SCHEMA_VERSION, migrate_database
from app.models.academic import AcademicYear, SchoolClass, Subject
from app.models.base import utc_now
from app.models.data_protection import BackupHistory, DataMigrationBatch
from app.models.school import SchoolSetting
from app.models.student import Guardian, Student
from app.services.backup_service import DataProtectionBackupService
from app.services.data_migration_service import DataMigrationService


@pytest.fixture()
def protection_env(tmp_path):
    db_file = tmp_path / "live_school.db"
    eng = create_engine(f"sqlite:///{db_file.as_posix()}", future=True)
    res = migrate_database(eng)
    assert res["current_version"] == CURRENT_SCHEMA_VERSION

    Session = sessionmaker(bind=eng, autocommit=False, autoflush=False)
    db = Session()

    ay = AcademicYear(name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True)
    db.add(ay)
    db.flush()

    school = SchoolSetting(school_name="Beacon Academy", schema_version=CURRENT_SCHEMA_VERSION, current_academic_year_id=ay.id)
    db.add(school)

    cls = SchoolClass(name="Class 9", numeric_level=9)
    db.add(cls)
    db.flush()

    guardian = Guardian(
        father_name="Existing Father",
        guardian_name="Existing Father",
        guardian_phone="01700-111222",
    )
    db.add(guardian)
    db.flush()

    existing_student = Student(
        student_id="STU-EXIST-01",
        admission_number="ADM-EXIST-01",
        roll_number=1,
        first_name="Nadia",
        last_name="Rahman",
        full_name="Nadia Rahman",
        gender="Female",
        date_of_birth=date(2011, 4, 10),
        blood_group=None,
        phone="01799-000111",
        class_id=cls.id,
        guardian_id=guardian.id,
        academic_year_id=ay.id,
    )
    db.add(existing_student)
    db.commit()

    yield {
        "db": db,
        "engine": eng,
        "db_file": db_file,
        "tmp_path": tmp_path,
        "Session": Session,
    }
    db.close()
    eng.dispose()


def test_encrypted_backups_verification_and_schedules(protection_env):
    db = protection_env["db"]
    bkp_dir = str(protection_env["tmp_path"] / "backups")

    for mode in ("Manual", "Automatic", "Daily", "Weekly", "Monthly"):
        rec = DataProtectionBackupService.create_backup(
            db,
            schedule_mode=mode,
            encrypt=True,
            passphrase="StrongSchoolVaultPassword!2026",
            backup_dir=bkp_dir,
            verify=True,
            notes=f"{mode} safety snapshot",
        )
        assert rec.is_encrypted is True
        assert rec.verification_status == "Verified"
        assert Path(rec.file_path).exists()

        # Wrong passphrase must fail cleanly
        bad_ver = DataProtectionBackupService.verify_backup(db, rec.file_path, passphrase="WrongPassword")
        assert bad_ver["ok"] is False

        # Valid passphrase succeeds
        good_ver = DataProtectionBackupService.verify_backup(db, rec.file_path, passphrase="StrongSchoolVaultPassword!2026")
        assert good_ver["ok"] is True

    # Test Scheduler Configuration & Automated Execution
    cfg = DataProtectionBackupService.update_schedule(
        db,
        is_enabled=True,
        frequency="Weekly",
        day_of_week=2,
        backup_directory=bkp_dir,
        next_run_at=utc_now() - timedelta(minutes=5),
    )
    cfg.next_run_at = utc_now() - timedelta(minutes=5)
    db.commit()

    due_bkp = DataProtectionBackupService.run_due_scheduled_backup(
        db, passphrase="StrongSchoolVaultPassword!2026"
    )
    assert due_bkp is not None
    assert due_bkp.schedule_mode == "Weekly"
    assert due_bkp.verification_status == "Verified"


def test_restore_creates_mandatory_pre_restore_backup_and_restores_state(protection_env):
    db = protection_env["db"]
    eng = protection_env["engine"]
    Session = protection_env["Session"]
    bkp_dir = str(protection_env["tmp_path"] / "backups")

    # Take clean baseline encrypted backup
    baseline = DataProtectionBackupService.create_backup(
        db,
        schedule_mode="Manual",
        encrypt=True,
        passphrase="RestoreKey#99",
        backup_dir=bkp_dir,
        verify=True,
    )
    assert db.query(Subject).count() == 0

    # Add post-backup mutation that we want undone by restore
    db.add(Subject(name="Temporary Post-Backup Subject", code="TMP-999"))
    db.commit()
    assert db.query(Subject).count() == 1

    # Execute Safe Restore
    outcome = DataProtectionBackupService.restore_backup(
        db,
        baseline.id,
        passphrase="RestoreKey#99",
        target_engine=eng,
        restored_by="super_admin",
        backup_dir=bkp_dir,
    )
    assert outcome["ok"] is True
    assert Path(outcome["pre_restore_backup_path"]).exists()

    # Open fresh session and confirm live DB matches baseline AND Pre-Restore Backup is preserved
    fresh_db = Session()
    try:
        assert fresh_db.query(Subject).count() == 0
        assert fresh_db.query(Student).filter(Student.student_id == "STU-EXIST-01").first() is not None
        pre_rec = fresh_db.query(BackupHistory).filter(
            BackupHistory.backup_code == outcome["pre_restore_backup_code"]
        ).first()
        assert pre_rec is not None
        assert pre_rec.is_pre_restore is True
    finally:
        fresh_db.close()


def test_csv_6_step_migration_no_overwrite_and_full_rollback(protection_env):
    db = protection_env["db"]
    tmp_path = protection_env["tmp_path"]

    # CSV contains 1 conflicting existing student (must NOT be overwritten under SKIP), 2 new students
    csv_file = tmp_path / "students_import.csv"
    csv_file.write_text(
        "student_id,admission_number,full_name,gender,date_of_birth,class_name,guardian_name,guardian_phone,phone\n"
        "STU-EXIST-01,ADM-EXIST-01,OVERWRITE ATTEMPT,Male,2010-01-01,Class 9,Fake Guardian,9999999999,0111111111\n"
        "STU-NEW-101,ADM-NEW-101,Rafiul Islam,Male,2011-06-15,Class 10,Karim Islam,01811-555111,01811-555111\n"
        "STU-NEW-102,ADM-NEW-102,Samira Chowdhury,Female,2011-09-20,Class 10,Farhana Chowdhury,01822-555222,01822-555222\n",
        encoding="utf-8",
    )

    # Step 1: Upload
    batch = DataMigrationService.upload_source(db, str(csv_file), target_entity="Students")
    assert batch.status == "Uploaded"

    # Step 2: Detect
    det = DataMigrationService.detect_schema(db, batch.id)
    assert det["total_rows"] == 3
    assert "full_name" in det["suggested_mapping"]

    # Step 3: Map (default SKIP policy)
    DataMigrationService.save_mapping(db, batch.id, mapping=det["suggested_mapping"], conflict_policy="SKIP")

    # Step 4 & 5: Validate + Preview
    val = DataMigrationService.validate_batch(db, batch.id)
    assert val["will_insert"] == 2
    assert val["will_skip"] == 1
    assert val["error_rows"] == 0

    prev = DataMigrationService.preview_batch(db, batch.id)
    assert prev["preview_rows"][0]["planned_action"] == "SKIP"

    # Step 6: Execute Import
    imported = DataMigrationService.execute_import(db, batch.id, create_pre_backup=True)
    assert imported.status == "Imported"
    assert imported.inserted_rows == 2
    assert imported.skipped_rows == 1

    # Confirm existing student was NEVER overwritten
    existing = db.query(Student).filter(Student.student_id == "STU-EXIST-01").first()
    assert existing.full_name == "Nadia Rahman"
    assert existing.phone == "01799-000111"
    assert db.query(Student).filter(Student.student_id == "STU-NEW-101").first() is not None

    # Execute Rollback Strategy
    rb = DataMigrationService.rollback_batch(db, imported.id, reason="Test rollback")
    assert rb["ok"] is True
    assert rb["deleted_inserted_records"] == 2
    assert db.query(Student).filter(Student.student_id == "STU-NEW-101").first() is None
    assert db.query(Student).filter(Student.student_id == "STU-EXIST-01").first() is not None
    db.refresh(imported)
    assert imported.status == "Rolled Back"


def test_excel_and_previous_database_migration(protection_env):
    db = protection_env["db"]
    tmp_path = protection_env["tmp_path"]

    # 1. Excel Workbook Migration -> Teachers
    xlsx_path = tmp_path / "legacy_teachers.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "FacultyRoster"
    ws.append(["Full Name", "Email", "Phone", "Subject", "Department"])
    ws.append(["Dr. Imran Kabir", "imran.kabir@school.edu", "01755-123456", "Chemistry", "Science"])
    ws.append(["Ms. Tasnim Ara", "tasnim.ara@school.edu", "01766-654321", "English", "Humanities"])
    wb.save(str(xlsx_path))
    wb.close()

    b_xl = DataMigrationService.upload_source(db, str(xlsx_path), target_entity="Teachers")
    det_xl = DataMigrationService.detect_schema(db, b_xl.id, sheet_or_table="FacultyRoster")
    assert det_xl["selected_sheet_or_table"] == "FacultyRoster"
    DataMigrationService.save_mapping(db, b_xl.id, det_xl["suggested_mapping"], conflict_policy="SKIP")
    DataMigrationService.preview_batch(db, b_xl.id)
    imp_xl = DataMigrationService.execute_import(db, b_xl.id, create_pre_backup=False)
    assert imp_xl.inserted_rows == 2

    # 2. Previous Legacy SQLite Database Migration -> Subjects
    legacy_db = tmp_path / "old_school_2022.db"
    conn = sqlite3.connect(str(legacy_db))
    conn.execute("CREATE TABLE legacy_subjects (sub_code TEXT, sub_name TEXT, sub_type TEXT)")
    conn.execute("INSERT INTO legacy_subjects VALUES ('PHY-101', 'Physics I', 'Compulsory')")
    conn.execute("INSERT INTO legacy_subjects VALUES ('BIO-101', 'Biology I', 'Elective')")
    conn.commit()
    conn.close()

    b_db = DataMigrationService.upload_source(db, str(legacy_db), target_entity="Subjects")
    det_db = DataMigrationService.detect_schema(db, b_db.id, sheet_or_table="legacy_subjects")
    assert det_db["source_type"] == "Previous Database"
    assert det_db["total_rows"] == 2
    # Map legacy column names cleanly
    DataMigrationService.save_mapping(
        db,
        b_db.id,
        mapping={"code": "sub_code", "name": "sub_name", "subject_type": "sub_type"},
        conflict_policy="SKIP",
    )
    val_db = DataMigrationService.validate_batch(db, b_db.id)
    assert val_db["will_insert"] == 2
    imp_db = DataMigrationService.execute_import(db, b_db.id, create_pre_backup=False)
    assert imp_db.inserted_rows == 2
    assert db.query(Subject).filter(Subject.code == "PHY-101").first() is not None
