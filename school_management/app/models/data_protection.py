"""
EduManage Pro - Data Protection, Backup/Restore & Migration Audit Models
Tracks BackupScheduleConfig (Manual, Automatic, Daily, Weekly, Monthly),
encrypted BackupHistory with verification & pre-restore safety snapshots,
and 6-step DataMigrationBatch + DataMigrationRowLog for reversible imports.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


BACKUP_SCHEDULE_MODES = ["Manual", "Automatic", "Daily", "Weekly", "Monthly"]
MIGRATION_SOURCE_TYPES = ["CSV", "Excel", "Previous Database"]
MIGRATION_TARGET_ENTITIES = [
    "Students",
    "Teachers",
    "Staff",
    "Classes",
    "Subjects",
    "FeeCategories",
    "Books",
]
MIGRATION_CONFLICT_POLICIES = ["SKIP", "ERROR_ON_CONFLICT", "FILL_EMPTY_ONLY"]
MIGRATION_STATUSES = [
    "Uploaded",
    "Detected",
    "Mapped",
    "Validated",
    "Previewed",
    "Imported",
    "Failed",
    "Rolled Back",
]


class BackupScheduleConfig(Base, TimestampMixin):
    """Persistent automated backup policy (Automatic, Daily, Weekly, Monthly)."""

    __tablename__ = "backup_schedule_configs"

    schedule_name = Column(String(100), unique=True, nullable=False, default="Primary Automated Protection")
    is_enabled = Column(Boolean, default=True, nullable=False)
    frequency = Column(String(20), default="Daily", nullable=False)  # Automatic | Daily | Weekly | Monthly
    interval_hours = Column(Integer, default=24, nullable=False)
    preferred_time = Column(String(10), default="23:00", nullable=False)
    day_of_week = Column(Integer, default=0, nullable=False)   # 0=Mon .. 6=Sun
    day_of_month = Column(Integer, default=1, nullable=False)  # 1..28
    retention_count = Column(Integer, default=30, nullable=False)
    encrypt_backups = Column(Boolean, default=True, nullable=False)
    verify_after_backup = Column(Boolean, default=True, nullable=False)
    backup_directory = Column(String(300), nullable=True)

    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    last_status = Column(String(30), default="Pending", nullable=False)
    last_error = Column(Text, nullable=True)

    def __repr__(self):
        return f"<BackupScheduleConfig(name='{self.schedule_name}', freq='{self.frequency}', enabled={self.is_enabled})>"


class BackupHistory(Base, TimestampMixin, SoftDeleteMixin):
    """Audit trail of all manual, scheduled, and pre-restore database backups."""

    __tablename__ = "backup_histories"

    backup_code = Column(String(60), unique=True, nullable=False, index=True)
    schedule_mode = Column(String(20), default="Manual", nullable=False, index=True)
    trigger_source = Column(String(60), default="User", nullable=False)
    is_pre_restore = Column(Boolean, default=False, nullable=False, index=True)

    file_name = Column(String(220), nullable=False)
    file_path = Column(String(350), nullable=False)
    file_size_bytes = Column(Integer, default=0, nullable=False)

    is_encrypted = Column(Boolean, default=True, nullable=False)
    encryption_algorithm = Column(String(80), default="Fernet-AES128-HMAC-SHA256", nullable=False)
    checksum_sha256 = Column(String(64), nullable=False)
    schema_version = Column(Integer, default=20, nullable=False)
    dialect = Column(String(30), default="sqlite", nullable=False)

    status = Column(String(30), default="Completed", nullable=False, index=True)
    verification_status = Column(String(30), default="Pending", nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_notes = Column(Text, nullable=True)

    restored_at = Column(DateTime(timezone=True), nullable=True)
    restored_by = Column(String(80), nullable=True)
    pre_restore_backup_code = Column(String(60), nullable=True)

    created_by = Column(String(80), default="admin", nullable=False)
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<BackupHistory(code='{self.backup_code}', mode='{self.schedule_mode}', verified='{self.verification_status}')>"


class DataMigrationBatch(Base, TimestampMixin, SoftDeleteMixin):
    """
    6-Step Migration Wizard state & audit record:
    Upload -> Detect -> Map -> Validate -> Preview -> Import (+ Rollback).
    """

    __tablename__ = "data_migration_batches"

    batch_code = Column(String(60), unique=True, nullable=False, index=True)
    source_type = Column(String(30), nullable=False, index=True)  # CSV | Excel | Previous Database
    source_filename = Column(String(255), nullable=False)
    source_file_path = Column(String(350), nullable=False)
    source_checksum_sha256 = Column(String(64), nullable=False)
    source_sheet_or_table = Column(String(120), nullable=True)

    target_entity = Column(String(50), nullable=False, index=True)
    conflict_policy = Column(String(30), default="SKIP", nullable=False)  # SKIP | ERROR_ON_CONFLICT | FILL_EMPTY_ONLY

    detected_headers_json = Column(Text, default="[]", nullable=False)
    detected_sheets_json = Column(Text, default="[]", nullable=False)
    mapping_json = Column(Text, default="{}", nullable=False)
    validation_summary_json = Column(Text, default="{}", nullable=False)
    preview_summary_json = Column(Text, default="{}", nullable=False)

    total_rows = Column(Integer, default=0, nullable=False)
    valid_rows = Column(Integer, default=0, nullable=False)
    inserted_rows = Column(Integer, default=0, nullable=False)
    skipped_rows = Column(Integer, default=0, nullable=False)
    merged_rows = Column(Integer, default=0, nullable=False)
    error_rows = Column(Integer, default=0, nullable=False)

    status = Column(String(30), default="Uploaded", nullable=False, index=True)
    pre_migration_backup_code = Column(String(60), nullable=True)

    imported_at = Column(DateTime(timezone=True), nullable=True)
    imported_by = Column(String(80), default="admin", nullable=False)
    rolled_back_at = Column(DateTime(timezone=True), nullable=True)
    rolled_back_by = Column(String(80), nullable=True)
    rollback_reason = Column(String(255), nullable=True)

    row_logs = relationship(
        "DataMigrationRowLog",
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="DataMigrationRowLog.row_number.asc()",
    )

    def __repr__(self):
        return f"<DataMigrationBatch(code='{self.batch_code}', entity='{self.target_entity}', status='{self.status}')>"


class DataMigrationRowLog(Base, TimestampMixin):
    """Per-row reversible audit ledger supporting full batch rollback."""

    __tablename__ = "data_migration_row_logs"

    batch_id = Column(
        Integer,
        ForeignKey("data_migration_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_number = Column(Integer, nullable=False)
    action = Column(String(30), nullable=False, index=True)  # INSERTED | UPDATED_EMPTY | SKIPPED | ERROR
    target_table = Column(String(80), nullable=True)
    target_record_id = Column(Integer, nullable=True, index=True)
    auxiliary_records_json = Column(Text, default="[]", nullable=False)
    source_row_json = Column(Text, default="{}", nullable=False)
    before_snapshot_json = Column(Text, nullable=True)
    after_snapshot_json = Column(Text, nullable=True)
    message = Column(String(255), nullable=True)
    is_rolled_back = Column(Boolean, default=False, nullable=False)

    batch = relationship("DataMigrationBatch", back_populates="row_logs")

    def __repr__(self):
        return f"<DataMigrationRowLog(batch_id={self.batch_id}, row={self.row_number}, action='{self.action}')>"
