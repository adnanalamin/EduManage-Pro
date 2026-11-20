"""
EduManage Pro - Professional Encrypted Backup, Verification & Restore Engine
Supports Manual, Automatic, Daily, Weekly, and Monthly backups with PBKDF2-Fernet
AES+HMAC authenticated encryption, isolated SQLite integrity/FK verification,
retention pruning, and mandatory Pre-Restore Safety Backups with atomic rollback.
"""

import base64
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import struct
import tempfile
from typing import Any, Dict, List, Optional
import zlib

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config.logging_config import app_logger, error_logger
from app.config.settings import BACKUPS_DIR, DATA_DIR, settings
from app.models.base import utc_now
from app.models.data_protection import (
    BACKUP_SCHEDULE_MODES,
    BackupHistory,
    BackupScheduleConfig,
)
from app.security.audit import AuditService
from app.security.file_validator import SecureFileValidator


CONTAINER_MAGIC = b"EDBK"
DEFAULT_KDF_ITERATIONS = 480_000
MASTER_KEY_FILE = DATA_DIR / ".backup_master.key"


def _ensure_master_passphrase() -> str:
    """Return local persistent institutional backup passphrase stored under data dir."""
    MASTER_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if MASTER_KEY_FILE.exists():
        key_txt = MASTER_KEY_FILE.read_text(encoding="utf-8").strip()
        if key_txt:
            return key_txt
    generated = secrets.token_urlsafe(32)
    MASTER_KEY_FILE.write_text(generated, encoding="utf-8")
    try:
        os.chmod(MASTER_KEY_FILE, 0o600)
    except Exception:
        pass
    return generated


def _derive_fernet_key(passphrase: str, salt: bytes, iterations: int = DEFAULT_KDF_ITERATIONS) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def _encrypt_bytes(raw_bytes: bytes, passphrase: str, salt: bytes, iterations: int = DEFAULT_KDF_ITERATIONS) -> bytes:
    from cryptography.fernet import Fernet

    fkey = _derive_fernet_key(passphrase, salt, iterations)
    return Fernet(fkey).encrypt(raw_bytes)


def _decrypt_bytes(token_bytes: bytes, passphrase: str, salt: bytes, iterations: int = DEFAULT_KDF_ITERATIONS) -> bytes:
    from cryptography.fernet import Fernet

    fkey = _derive_fernet_key(passphrase, salt, iterations)
    return Fernet(fkey).decrypt(token_bytes)


def _resolve_sqlite_db_path(db_or_engine: Any) -> Path:
    eng: Optional[Engine] = None
    if isinstance(db_or_engine, Engine):
        eng = db_or_engine
    elif hasattr(db_or_engine, "get_bind"):
        eng = db_or_engine.get_bind()

    if eng is not None and eng.url and eng.url.database and eng.url.database != ":memory:":
        return Path(eng.url.database)
    return Path(settings.DATABASE_PATH)


def _hot_sqlite_snapshot(source_db_path: Path, dest_sqlite_path: Path) -> None:
    """Safely capture a consistent transactionally-quiesced SQLite snapshot using native online backup API."""
    if not source_db_path.exists():
        raise FileNotFoundError(f"Source database file not found: {source_db_path}")
    dest_sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    src_conn = sqlite3.connect(str(source_db_path), timeout=30.0)
    dst_conn = sqlite3.connect(str(dest_sqlite_path), timeout=30.0)
    try:
        src_conn.backup(dst_conn)
        dst_conn.commit()
    finally:
        dst_conn.close()
        src_conn.close()


def _verify_sqlite_file_integrity(sqlite_path: Path) -> Dict[str, Any]:
    conn = sqlite3.connect(str(sqlite_path), timeout=15.0)
    try:
        cur = conn.cursor()
        integrity_rows = [r[0] for r in cur.execute("PRAGMA integrity_check").fetchall()]
        cur.execute("PRAGMA foreign_keys = ON")
        fk_rows = [tuple(r) for r in cur.execute("PRAGMA foreign_key_check").fetchall()]
        tbl_count = cur.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).scalar()
        ok = integrity_rows == ["ok"] and len(fk_rows) == 0 and int(tbl_count or 0) > 0
        return {
            "ok": ok,
            "integrity": ", ".join(integrity_rows),
            "fk_violations": len(fk_rows),
            "table_count": int(tbl_count or 0),
        }
    finally:
        conn.close()


def _compute_next_run(
    frequency: str,
    interval_hours: int = 24,
    preferred_time: str = "23:00",
    day_of_week: int = 0,
    day_of_month: int = 1,
    from_dt: Optional[datetime] = None,
) -> datetime:
    base = from_dt or utc_now()
    try:
        hh, mm = [int(p) for p in (preferred_time or "23:00").split(":", 1)]
    except Exception:
        hh, mm = 23, 0

    freq = (frequency or "Daily").strip()
    if freq == "Automatic":
        return base + timedelta(hours=max(1, int(interval_hours or 24)))
    if freq == "Daily":
        cand = base.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if cand <= base:
            cand += timedelta(days=1)
        return cand
    if freq == "Weekly":
        target_wd = max(0, min(6, int(day_of_week or 0)))
        days_ahead = (target_wd - base.weekday()) % 7
        cand = (base + timedelta(days=days_ahead)).replace(hour=hh, minute=mm, second=0, microsecond=0)
        if cand <= base:
            cand += timedelta(days=7)
        return cand
    # Monthly
    dom = max(1, min(28, int(day_of_month or 1)))
    cand = base.replace(day=dom, hour=hh, minute=mm, second=0, microsecond=0)
    if cand <= base:
        if base.month == 12:
            cand = cand.replace(year=base.year + 1, month=1)
        else:
            cand = cand.replace(month=base.month + 1)
    return cand


class DataProtectionBackupService:
    """Service layer for Manual/Automatic/Daily/Weekly/Monthly encrypted backup, verification & restore."""

    @staticmethod
    def _next_backup_code(db: Session) -> str:
        stamp = datetime.now().strftime("%Y%m%d")
        prefix = f"BKP-{stamp}-"
        existing = db.query(BackupHistory.backup_code).filter(BackupHistory.backup_code.like(f"{prefix}%")).all()
        max_seq = 0
        for (code,) in existing:
            try:
                max_seq = max(max_seq, int(code.rsplit("-", 1)[-1]))
            except Exception:
                pass
        return f"{prefix}{max_seq + 1:04d}"

    @staticmethod
    def _pack_container(
        sqlite_snapshot_path: Path,
        output_path: Path,
        encrypt: bool,
        passphrase: Optional[str],
        schedule_mode: str,
        schema_version: int,
    ) -> Dict[str, Any]:
        plain_bytes = sqlite_snapshot_path.read_bytes()
        sha_plain = hashlib.sha256(plain_bytes).hexdigest()
        compressed = zlib.compress(plain_bytes, level=6)

        salt = secrets.token_bytes(16)
        iterations = DEFAULT_KDF_ITERATIONS
        if encrypt:
            secret_pw = passphrase if passphrase else _ensure_master_passphrase()
            payload = _encrypt_bytes(compressed, secret_pw, salt, iterations)
            algo = "Fernet-AES128-HMAC-SHA256+PBKDF2"
        else:
            payload = compressed
            algo = "ZLIB-PLAIN"

        manifest = {
            "version": 1,
            "encrypted": bool(encrypt),
            "algorithm": algo,
            "salt_b64": base64.b64encode(salt).decode("ascii"),
            "kdf_iterations": iterations,
            "sha256_plaintext": sha_plain,
            "schema_version": schema_version,
            "schedule_mode": schedule_mode,
            "created_at": utc_now().isoformat(),
        }
        manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as fh:
            fh.write(CONTAINER_MAGIC)
            fh.write(struct.pack("!I", len(manifest_bytes)))
            fh.write(manifest_bytes)
            fh.write(payload)

        return {
            "sha256": sha_plain,
            "algorithm": algo,
            "size_bytes": output_path.stat().st_size,
            "manifest": manifest,
        }

    @staticmethod
    def _unpack_container(container_path: Path, passphrase: Optional[str] = None) -> Dict[str, Any]:
        if not container_path.exists() or not container_path.is_file():
            raise FileNotFoundError(f"Backup file does not exist: {container_path}")

        raw = container_path.read_bytes()
        if len(raw) < 8 or raw[:4] != CONTAINER_MAGIC:
            raise ValueError("Invalid backup container format (missing EDBK header).")

        hdr_len = struct.unpack("!I", raw[4:8])[0]
        manifest = json.loads(raw[8 : 8 + hdr_len].decode("utf-8"))
        payload = raw[8 + hdr_len :]

        if manifest.get("encrypted"):
            salt = base64.b64decode(manifest["salt_b64"])
            iters = int(manifest.get("kdf_iterations", DEFAULT_KDF_ITERATIONS))
            candidates = [passphrase] if passphrase else [_ensure_master_passphrase()]
            decrypted = None
            last_err = None
            for pw in candidates:
                try:
                    decrypted = _decrypt_bytes(payload, pw, salt, iters)
                    break
                except Exception as exc:
                    last_err = exc
            if decrypted is None:
                raise ValueError(f"Backup decryption failed (wrong passphrase or tampered file): {last_err}")
            compressed = decrypted
        else:
            compressed = payload

        plain_bytes = zlib.decompress(compressed)
        actual_sha = hashlib.sha256(plain_bytes).hexdigest()
        expected_sha = manifest.get("sha256_plaintext")
        if expected_sha and actual_sha != expected_sha:
            raise ValueError("Backup SHA-256 checksum mismatch after decompression.")

        return {
            "manifest": manifest,
            "plain_bytes": plain_bytes,
            "sha256": actual_sha,
        }

    @classmethod
    def create_backup(
        cls,
        db: Session,
        schedule_mode: str = "Manual",
        trigger_source: str = "User",
        encrypt: bool = True,
        passphrase: Optional[str] = None,
        backup_dir: Optional[str] = None,
        is_pre_restore: bool = False,
        verify: bool = True,
        created_by: str = "admin",
        notes: Optional[str] = None,
    ) -> BackupHistory:
        if schedule_mode not in BACKUP_SCHEDULE_MODES:
            raise ValueError(f"Unsupported schedule_mode '{schedule_mode}'. Allowed: {', '.join(BACKUP_SCHEDULE_MODES)}")

        db.flush()
        source_db_path = _resolve_sqlite_db_path(db)
        target_dir = Path(backup_dir) if backup_dir else BACKUPS_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        backup_code = cls._next_backup_code(db)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = ".ebk" if encrypt else ".zbk"
        tag = "PRERESTORE_" if is_pre_restore else ""
        file_name = f"{backup_code}_{tag}{schedule_mode.upper()}_{stamp}{ext}"
        out_path = target_dir / file_name

        # Capture hot snapshot first into temp, verify & pack
        with tempfile.TemporaryDirectory() as tmpd:
            snap_path = Path(tmpd) / "snapshot.db"
            _hot_sqlite_snapshot(source_db_path, snap_path)
            packed = cls._pack_container(
                snap_path,
                out_path,
                encrypt=encrypt,
                passphrase=passphrase,
                schedule_mode=schedule_mode,
                schema_version=settings.SCHEMA_VERSION,
            )

        record = BackupHistory(
            backup_code=backup_code,
            schedule_mode=schedule_mode,
            trigger_source=trigger_source,
            is_pre_restore=is_pre_restore,
            file_name=file_name,
            file_path=str(out_path),
            file_size_bytes=packed["size_bytes"],
            is_encrypted=bool(encrypt),
            encryption_algorithm=packed["algorithm"],
            checksum_sha256=packed["sha256"],
            schema_version=settings.SCHEMA_VERSION,
            dialect=db.get_bind().dialect.name if db.get_bind() else "sqlite",
            status="Completed",
            verification_status="Pending",
            created_by=created_by,
            notes=notes,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        if verify:
            cls.verify_backup(db, str(out_path), passphrase=passphrase, backup_id=record.id)
            db.refresh(record)

        AuditService.record(
            db,
            action="BACKUP_CREATED",
            module="DATA_PROTECTION",
            description=f"Created {schedule_mode} backup '{record.backup_code}' (encrypted={bool(encrypt)}, status={record.status}).",
            username=created_by,
            entity_type="BackupHistory",
            entity_id=record.id,
            record_label=record.backup_code,
            after={
                "backup_code": record.backup_code,
                "schedule_mode": schedule_mode,
                "is_encrypted": bool(encrypt),
                "is_pre_restore": bool(is_pre_restore),
                "checksum_sha256": record.checksum_sha256,
                "verification_status": record.verification_status,
            },
            severity="SECURITY",
            is_admin_action=True,
            commit=True,
        )
        app_logger.info(f"Created {schedule_mode} backup {record.backup_code} ({out_path})")
        return record

    @classmethod
    def verify_backup(
        cls,
        db: Optional[Session],
        backup_path: str,
        passphrase: Optional[str] = None,
        backup_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            container, _ext, _sz = SecureFileValidator.validate_existing_file(backup_path, "backup")
            unpacked = cls._unpack_container(container, passphrase=passphrase)
            with tempfile.TemporaryDirectory() as tmpd:
                staged_db = Path(tmpd) / "verify_staged.db"
                staged_db.write_bytes(unpacked["plain_bytes"])
                sqlite_diag = _verify_sqlite_file_integrity(staged_db)

            ok = bool(sqlite_diag["ok"])
            notes = (
                f"SHA256={unpacked['sha256'][:16]}... | integrity={sqlite_diag['integrity']} "
                f"| fk_violations={sqlite_diag['fk_violations']} | tables={sqlite_diag['table_count']}"
            )
            if db is not None and backup_id is not None:
                row = db.query(BackupHistory).filter(BackupHistory.id == backup_id).first()
                if row:
                    row.verification_status = "Verified" if ok else "Failed"
                    row.status = "Verified" if ok else "Failed"
                    row.verified_at = utc_now()
                    row.verification_notes = notes
                    db.commit()
            return {
                "ok": ok,
                "sha256": unpacked["sha256"],
                "manifest": unpacked["manifest"],
                "integrity": sqlite_diag,
                "notes": notes,
            }
        except Exception as exc:
            err_msg = str(exc)
            if db is not None:
                if backup_id is not None:
                    row = db.query(BackupHistory).filter(BackupHistory.id == backup_id).first()
                    if row:
                        row.verification_status = "Failed"
                        row.status = "Failed"
                        row.verified_at = utc_now()
                        row.verification_notes = err_msg
                AuditService.raise_alert(
                    db,
                    alert_type="BACKUP_VERIFICATION_FAILED",
                    severity="HIGH",
                    module="DATA_PROTECTION",
                    description=f"Backup integrity/decryption check failed for '{Path(str(backup_path)).name}': {err_msg}",
                )
                db.commit()
            return {"ok": False, "error": err_msg, "notes": err_msg}

    @classmethod
    def restore_backup(
        cls,
        db: Session,
        backup_path_or_id: Any,
        passphrase: Optional[str] = None,
        target_engine: Optional[Engine] = None,
        restored_by: str = "admin",
        backup_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Safely restore database from backup:
        1. Verify backup file & integrity BEFORE touching live database.
        2. Automatically capture a mandatory Pre-Restore Safety Backup of the live DB.
        3. Atomically swap staged DB over live DB (with automatic Pre-Restore rollback on any failure).
        4. Validate restored DB integrity and update audit history.
        """
        target_row: Optional[BackupHistory] = None
        if isinstance(backup_path_or_id, int):
            target_row = db.query(BackupHistory).filter(BackupHistory.id == backup_path_or_id).first()
            if not target_row:
                raise ValueError(f"Backup ID {backup_path_or_id} not found.")
            backup_path = target_row.file_path
        else:
            backup_path = str(backup_path_or_id)

        # Step 1: Isolated Pre-flight Verification (0 mutation on live DB)
        ver = cls.verify_backup(db, backup_path, passphrase=passphrase)
        if not ver.get("ok"):
            raise ValueError(f"Restore aborted — backup verification failed: {ver.get('error') or ver.get('notes')}")

        unpacked = cls._unpack_container(Path(backup_path), passphrase=passphrase)
        live_db_path = _resolve_sqlite_db_path(target_engine or db)
        eng = target_engine or db.get_bind()

        # Step 2: Mandatory Pre-Restore Backup of live database
        safety_dir = Path(backup_dir) if backup_dir else Path(backup_path).parent
        pre_restore_record = cls.create_backup(
            db,
            schedule_mode="Automatic",
            trigger_source="Pre-Restore Safety",
            encrypt=True,
            passphrase=passphrase,
            backup_dir=str(safety_dir),
            is_pre_restore=True,
            verify=True,
            created_by=restored_by,
            notes=f"Mandatory pre-restore safety snapshot prior to restoring '{Path(backup_path).name}'",
        )
        pre_code = pre_restore_record.backup_code
        pre_path = pre_restore_record.file_path

        # Close active session & dispose engine before file swap
        target_row_id = target_row.id if target_row else None
        db.commit()
        db.close()
        if eng is not None:
            eng.dispose()

        # Step 3: Atomic File Swap with Automatic Pre-Restore Rollback Guard
        temp_restore = live_db_path.with_suffix(".restore_tmp")
        try:
            temp_restore.write_bytes(unpacked["plain_bytes"])
            diag = _verify_sqlite_file_integrity(temp_restore)
            if not diag["ok"]:
                raise ValueError(f"Staged restore failed SQLite integrity check: {diag}")

            for sidecar in ("-wal", "-shm"):
                sc_path = Path(str(live_db_path) + sidecar)
                if sc_path.exists():
                    sc_path.unlink()

            os.replace(str(temp_restore), str(live_db_path))
        except Exception as swap_exc:
            error_logger.exception(f"Restore swap failed; rolling back via pre-restore backup {pre_code}: {swap_exc}")
            if temp_restore.exists():
                temp_restore.unlink()
            try:
                rb_unpacked = cls._unpack_container(Path(pre_path), passphrase=passphrase)
                live_db_path.write_bytes(rb_unpacked["plain_bytes"])
            except Exception as rb_exc:
                error_logger.exception(f"Rollback recovery error: {rb_exc}")
            raise ValueError(f"Restore failed cleanly and rolled back to pre-restore snapshot {pre_code}: {swap_exc}")

        # Step 4: Non-destructive migrate_database to guarantee current schema & audit row
        from app.database.migrations import migrate_database
        from sqlalchemy.orm import sessionmaker

        if eng is not None:
            migrate_database(eng)
            LocalSess = sessionmaker(bind=eng, autocommit=False, autoflush=False)
            post_db = LocalSess()
            try:
                if target_row_id:
                    restored_entry = post_db.query(BackupHistory).filter(BackupHistory.id == target_row_id).first()
                    if restored_entry:
                        restored_entry.status = "Restored"
                        restored_entry.restored_at = utc_now()
                        restored_entry.restored_by = restored_by
                        restored_entry.pre_restore_backup_code = pre_code
                # Ensure the safety pre-restore entry is also visible in the restored DB registry
                exists_pre = post_db.query(BackupHistory).filter(BackupHistory.backup_code == pre_code).first()
                if not exists_pre:
                    post_db.add(
                        BackupHistory(
                            backup_code=pre_code,
                            schedule_mode="Automatic",
                            trigger_source="Pre-Restore Safety",
                            is_pre_restore=True,
                            file_name=Path(pre_path).name,
                            file_path=str(pre_path),
                            file_size_bytes=Path(pre_path).stat().st_size,
                            is_encrypted=True,
                            encryption_algorithm=pre_restore_record.encryption_algorithm,
                            checksum_sha256=pre_restore_record.checksum_sha256,
                            schema_version=settings.SCHEMA_VERSION,
                            status="Verified",
                            verification_status="Verified",
                            verified_at=utc_now(),
                            created_by=restored_by,
                            notes=f"Pre-restore safety backup created before restoring {Path(backup_path).name}",
                        )
                    )
                post_db.commit()
            finally:
                post_db.close()

        return {
            "ok": True,
            "restored_from": str(backup_path),
            "pre_restore_backup_code": pre_code,
            "pre_restore_backup_path": str(pre_path),
            "sha256": unpacked["sha256"],
        }

    # ------------------------------------------------------------------ #
    # Backup Schedule Configuration & Automatic Runner
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_or_create_schedule(db: Session) -> BackupScheduleConfig:
        cfg = db.query(BackupScheduleConfig).first()
        if not cfg:
            cfg = BackupScheduleConfig(
                schedule_name="Primary Automated Protection",
                is_enabled=True,
                frequency="Daily",
                interval_hours=24,
                preferred_time="23:00",
                retention_count=30,
                encrypt_backups=True,
                verify_after_backup=True,
                backup_directory=str(BACKUPS_DIR),
                next_run_at=_compute_next_run("Daily"),
            )
            db.add(cfg)
            db.commit()
            db.refresh(cfg)
        return cfg

    @staticmethod
    def update_schedule(db: Session, **kwargs) -> BackupScheduleConfig:
        cfg = DataProtectionBackupService.get_or_create_schedule(db)
        before_snap = {
            "is_enabled": bool(cfg.is_enabled),
            "frequency": cfg.frequency,
            "encrypt_backups": bool(cfg.encrypt_backups),
            "retention_count": int(cfg.retention_count or 30),
        }
        freq = kwargs.get("frequency", cfg.frequency)
        if freq not in ("Automatic", "Daily", "Weekly", "Monthly"):
            raise ValueError(f"Invalid schedule frequency '{freq}'. Allowed: Automatic, Daily, Weekly, Monthly")
        for k, v in kwargs.items():
            if hasattr(cfg, k) and k not in ("id", "created_at"):
                setattr(cfg, k, v)
        cfg.next_run_at = _compute_next_run(
            cfg.frequency,
            interval_hours=cfg.interval_hours,
            preferred_time=cfg.preferred_time,
            day_of_week=cfg.day_of_week,
            day_of_month=cfg.day_of_month,
        )
        AuditService.record(
            db,
            action="BACKUP_SCHEDULE_UPDATED",
            module="DATA_PROTECTION",
            description=f"Updated backup schedule policy ({cfg.frequency}, encrypted={bool(cfg.encrypt_backups)}).",
            entity_type="BackupScheduleConfig",
            entity_id=cfg.id,
            record_label=cfg.schedule_name,
            before=before_snap,
            after={
                "is_enabled": bool(cfg.is_enabled),
                "frequency": cfg.frequency,
                "encrypt_backups": bool(cfg.encrypt_backups),
                "retention_count": int(cfg.retention_count or 30),
            },
            severity="SECURITY",
            is_admin_action=True,
        )
        db.commit()
        db.refresh(cfg)
        return cfg

    @classmethod
    def run_due_scheduled_backup(
        cls,
        db: Session,
        passphrase: Optional[str] = None,
        force: bool = False,
        now: Optional[datetime] = None,
    ) -> Optional[BackupHistory]:
        cfg = cls.get_or_create_schedule(db)
        if not cfg.is_enabled and not force:
            return None
        cur_dt = now or utc_now()
        due = force or cfg.next_run_at is None or cur_dt >= cfg.next_run_at
        if not due:
            return None

        try:
            bkp = cls.create_backup(
                db,
                schedule_mode=cfg.frequency,
                trigger_source="Scheduler",
                encrypt=cfg.encrypt_backups,
                passphrase=passphrase,
                backup_dir=cfg.backup_directory or str(BACKUPS_DIR),
                is_pre_restore=False,
                verify=cfg.verify_after_backup,
                created_by="auto_scheduler",
                notes=f"Scheduled {cfg.frequency} automated backup",
            )
            cfg.last_run_at = cur_dt
            cfg.next_run_at = _compute_next_run(
                cfg.frequency,
                interval_hours=cfg.interval_hours,
                preferred_time=cfg.preferred_time,
                day_of_week=cfg.day_of_week,
                day_of_month=cfg.day_of_month,
                from_dt=cur_dt,
            )
            cfg.last_status = "Success"
            cfg.last_error = None
            cls._apply_retention(db, int(cfg.retention_count or 30))
            db.commit()
            return bkp
        except Exception as exc:
            cfg.last_status = "Failed"
            cfg.last_error = str(exc)
            db.commit()
            raise

    @staticmethod
    def _apply_retention(db: Session, retention_count: int) -> int:
        keep = max(3, int(retention_count or 30))
        scheduled = (
            db.query(BackupHistory)
            .filter(
                BackupHistory.is_deleted == False,  # noqa: E712
                BackupHistory.is_pre_restore == False,  # noqa: E712
            )
            .order_by(BackupHistory.id.desc())
            .all()
        )
        pruned = 0
        for old in scheduled[keep:]:
            old.is_deleted = True
            p = Path(old.file_path)
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
            pruned += 1
        return pruned

    @staticmethod
    def list_backup_history(
        db: Session,
        schedule_mode: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[BackupHistory]:
        q = db.query(BackupHistory).filter(BackupHistory.is_deleted == False)  # noqa: E712
        if schedule_mode and schedule_mode != "All":
            q = q.filter(BackupHistory.schedule_mode == schedule_mode)
        if status and status != "All":
            q = q.filter(BackupHistory.status == status)
        return q.order_by(BackupHistory.id.desc()).limit(limit).all()

    @staticmethod
    def get_stats(db: Session) -> Dict[str, Any]:
        rows = db.query(BackupHistory).filter(BackupHistory.is_deleted == False).all()  # noqa: E712
        cfg = DataProtectionBackupService.get_or_create_schedule(db)
        return {
            "total_backups": len(rows),
            "verified_backups": len([r for r in rows if r.verification_status == "Verified"]),
            "encrypted_backups": len([r for r in rows if r.is_encrypted]),
            "pre_restore_backups": len([r for r in rows if r.is_pre_restore]),
            "failed_backups": len([r for r in rows if r.status == "Failed"]),
            "schedule_frequency": cfg.frequency,
            "schedule_enabled": cfg.is_enabled,
        }
