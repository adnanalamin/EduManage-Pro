"""
EduManage Pro - Centralized Database Service & Transaction Management
Provides savepoint-safe transactions, lock helpers, soft-delete guards, duplicate prevention,
activity logging without hardcoded user FKs, and cross-dialect integrity diagnostics.
"""

from contextlib import contextmanager
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Type, TypeVar

from sqlalchemy import inspect, or_, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Query, Session

from app.config.logging_config import app_logger, error_logger
from app.database.connection import is_postgresql, is_sqlite, transaction_scope
from app.models.activity import ActivityLog
from app.models.fee import FeePayment
from app.models.student import Guardian, Student
from app.models.user import User

T = TypeVar("T")


class DatabaseService:
    """Enterprise database coordination service for SQLite and PostgreSQL."""

    @staticmethod
    @contextmanager
    def transaction(db: Session) -> Iterator[Session]:
        """
        Savepoint-aware transaction boundary.
        Commits if outermost transaction, or opens a nested SAVEPOINT if already in one.
        """
        with transaction_scope(db) as tx_session:
            yield tx_session

    @staticmethod
    def run_in_transaction(
        session_factory: Callable[[], Session],
        fn: Callable[[Session], T],
        max_retries: int = 3,
        retry_delay_seconds: float = 0.05,
    ) -> T:
        """
        Execute `fn(db)` inside an atomic session transaction.
        Automatically retries transient SQLite lock contention (`database is locked`).
        """
        last_error: Optional[Exception] = None
        for attempt in range(max_retries):
            session = session_factory()
            try:
                result = fn(session)
                session.commit()
                return result
            except OperationalError as exc:
                session.rollback()
                last_error = exc
                if "locked" in str(exc).lower() and attempt < max_retries - 1:
                    time.sleep(retry_delay_seconds * (attempt + 1))
                    continue
                error_logger.exception(f"OperationalError in transaction: {exc}")
                raise
            except Exception as exc:
                session.rollback()
                error_logger.exception(f"Transaction aborted and rolled back: {exc}")
                raise
            finally:
                session.close()

        assert last_error is not None
        raise last_error

    @staticmethod
    def lock_for_update(query: Query, db: Session) -> Query:
        """
        Apply SELECT ... FOR UPDATE row locking on PostgreSQL/multi-user engines.
        SQLite relies on database-level write locking + busy_timeout, so this is a safe no-op there.
        """
        if is_postgresql(db):
            return query.with_for_update()
        return query

    @staticmethod
    def active_only(query: Query, model: Type[Any]) -> Query:
        """Filter out soft-deleted rows when the model implements SoftDeleteMixin."""
        if hasattr(model, "is_deleted"):
            return query.filter(getattr(model, "is_deleted") == False)
        return query

    @staticmethod
    def soft_delete(db: Session, obj: Any, actor: str = "system", commit: bool = True) -> bool:
        """Mark an ORM record soft-deleted cleanly if supported."""
        if not hasattr(obj, "mark_deleted"):
            raise ValueError(f"Model {type(obj).__name__} does not support soft delete.")
        obj.mark_deleted(deleted_by=actor)
        if commit:
            db.commit()
            db.refresh(obj)
        else:
            db.flush()
        return True

    @staticmethod
    def restore(db: Session, obj: Any, commit: bool = True) -> bool:
        """Restore a soft-deleted ORM record."""
        if not hasattr(obj, "restore"):
            raise ValueError(f"Model {type(obj).__name__} does not support restore.")
        obj.restore()
        if commit:
            db.commit()
            db.refresh(obj)
        else:
            db.flush()
        return True

    @staticmethod
    def safe_hard_delete(db: Session, obj: Any, commit: bool = True) -> bool:
        """
        Hard-delete an object only if no child relationships with active rows block deletion.
        Raises ValueError instead of allowing silent cascade destruction or cryptic IntegrityError.
        """
        mapper = inspect(type(obj))
        for rel in mapper.relationships:
            if not rel.direction.name.endswith("MANY"):
                continue
            if "delete-orphan" in rel.cascade:
                continue
            child_val = getattr(obj, rel.key, None)
            if child_val:
                active_children = [
                    c for c in child_val if not getattr(c, "is_deleted", False)
                ]
                if active_children:
                    raise ValueError(
                        f"Cannot permanently delete {type(obj).__name__}: "
                        f"{len(active_children)} dependent '{rel.key}' record(s) still exist."
                    )

        db.delete(obj)
        if commit:
            db.commit()
        else:
            db.flush()
        return True

    @staticmethod
    def resolve_user_id(db: Session, username: Optional[str]) -> Optional[int]:
        """
        Resolve an optional User primary key from a username without assuming user_id=1 exists.
        """
        if not username:
            return None
        user = db.query(User.id).filter(User.username == username).first()
        return user[0] if user else None

    @staticmethod
    def log_activity(
        db: Session,
        action: str,
        module: str,
        description: str,
        username: str = "system",
        severity: str = "INFO",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        commit: bool = False,
    ) -> ActivityLog:
        """Insert an audit log record with valid optional user_id FK resolution."""
        uid = DatabaseService.resolve_user_id(db, username)
        entry = ActivityLog(
            user_id=uid,
            username=username or "system",
            action=action,
            module=module,
            description=description,
            severity=severity,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
        )
        db.add(entry)
        if commit:
            db.commit()
            db.refresh(entry)
        else:
            db.flush()
        return entry

    @staticmethod
    def check_duplicate_student(
        db: Session,
        student_id: Optional[str] = None,
        admission_number: Optional[str] = None,
        birth_certificate_no: Optional[str] = None,
        digital_id_code: Optional[str] = None,
        full_name: Optional[str] = None,
        date_of_birth: Any = None,
        guardian_phone: Optional[str] = None,
        student_phone: Optional[str] = None,
        exclude_student_pk: Optional[int] = None,
    ) -> Optional[str]:
        """
        Detect duplicate student records across hard unique identifiers and identity heuristics
        (full_name + date_of_birth + guardian_phone/student_phone).
        Returns a descriptive conflict message if found, else None.
        """
        from app.models.student import StudentGuardianLink

        base_q = db.query(Student)
        if exclude_student_pk is not None:
            base_q = base_q.filter(Student.id != exclude_student_pk)

        if admission_number and admission_number.strip():
            dup_adm = base_q.filter(Student.admission_number == admission_number.strip()).first()
            if dup_adm:
                return f"Admission number '{admission_number}' is already in use."

        if student_id and student_id.strip():
            dup_sid = base_q.filter(Student.student_id == student_id.strip()).first()
            if dup_sid:
                return f"Student ID '{student_id}' is already assigned."

        if digital_id_code and digital_id_code.strip():
            dup_did = base_q.filter(Student.digital_id_code == digital_id_code.strip()).first()
            if dup_did:
                return f"Digital ID '{digital_id_code}' is already assigned."

        if birth_certificate_no and birth_certificate_no.strip():
            dup_bc = base_q.filter(
                Student.birth_certificate_no == birth_certificate_no.strip()
            ).first()
            if dup_bc:
                return f"Birth certificate number '{birth_certificate_no}' is already registered."

        if full_name and full_name.strip() and date_of_birth:
            normalized_name = full_name.strip()
            if guardian_phone and guardian_phone.strip():
                normalized_phone = guardian_phone.strip()
                # Check primary guardian
                dup_person = (
                    base_q.join(Student.guardian)
                    .filter(
                        Student.is_deleted == False,
                        Student.full_name.ilike(normalized_name),
                        Student.date_of_birth == date_of_birth,
                        Guardian.guardian_phone == normalized_phone,
                    )
                    .first()
                )
                if not dup_person:
                    # Also check linked secondary guardians
                    dup_person = (
                        base_q.join(Student.guardian_links)
                        .join(StudentGuardianLink.guardian)
                        .filter(
                            Student.is_deleted == False,
                            Student.full_name.ilike(normalized_name),
                            Student.date_of_birth == date_of_birth,
                            Guardian.guardian_phone == normalized_phone,
                        )
                        .first()
                    )
                if dup_person:
                    return (
                        f"Potential duplicate student detected: '{dup_person.full_name}' "
                        f"(ID: {dup_person.student_id}) with the same DOB and guardian phone."
                    )

            if student_phone and student_phone.strip():
                dup_phone_person = (
                    base_q.filter(
                        Student.is_deleted == False,
                        Student.full_name.ilike(normalized_name),
                        Student.date_of_birth == date_of_birth,
                        Student.phone == student_phone.strip(),
                    )
                    .first()
                )
                if dup_phone_person:
                    return (
                        f"Potential duplicate student detected: '{dup_phone_person.full_name}' "
                        f"(ID: {dup_phone_person.student_id}) with the same DOB and student phone."
                    )

        return None

    @staticmethod
    def prevent_duplicate_payment(
        db: Session,
        student_fee_id: int,
        receipt_no: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        transaction_id: Optional[str] = None,
    ) -> Optional[FeePayment]:
        """
        Enforce idempotency and prevent accidental duplicate fee payments.
        - If `idempotency_key` matches an existing payment, return that existing FeePayment cleanly.
        - If `receipt_no` or non-empty external `transaction_id` already exists on the invoice, raise ValueError.
        """
        if idempotency_key:
            existing_idem = (
                db.query(FeePayment)
                .filter(FeePayment.idempotency_key == idempotency_key)
                .first()
            )
            if existing_idem:
                app_logger.info(
                    f"Idempotent fee payment hit for key '{idempotency_key}' -> receipt {existing_idem.receipt_no}"
                )
                return existing_idem

        if receipt_no:
            existing_rec = db.query(FeePayment).filter(FeePayment.receipt_no == receipt_no).first()
            if existing_rec:
                raise ValueError(f"Duplicate receipt number '{receipt_no}' is already recorded.")

        if transaction_id and transaction_id.strip():
            existing_trx = (
                db.query(FeePayment)
                .filter(
                    FeePayment.student_fee_id == student_fee_id,
                    FeePayment.transaction_id == transaction_id.strip(),
                    FeePayment.is_deleted == False,
                )
                .first()
            )
            if existing_trx:
                raise ValueError(
                    f"Duplicate transaction reference '{transaction_id}' already exists for this invoice "
                    f"(Receipt: {existing_trx.receipt_no})."
                )

        return None

    @staticmethod
    def verify_integrity(db: Session) -> Dict[str, Any]:
        """
        Run database integrity and foreign-key verification diagnostics.
        Works cleanly on both SQLite and PostgreSQL.
        """
        if is_sqlite(db):
            fk_enabled = bool(db.execute(text("PRAGMA foreign_keys")).scalar())
            fk_violations = [
                tuple(row) for row in db.execute(text("PRAGMA foreign_key_check")).fetchall()
            ]
            integrity_rows = [
                row[0] for row in db.execute(text("PRAGMA integrity_check")).fetchall()
            ]
            journal_mode = db.execute(text("PRAGMA journal_mode")).scalar()
            ok = fk_enabled and len(fk_violations) == 0 and integrity_rows == ["ok"]
            return {
                "ok": ok,
                "dialect": "sqlite",
                "foreign_keys_enabled": fk_enabled,
                "fk_violations": fk_violations,
                "integrity": ", ".join(integrity_rows),
                "journal_mode": str(journal_mode),
            }

        # PostgreSQL / other SQL dialect verification
        ping = db.execute(text("SELECT 1")).scalar()
        eng = db.get_bind()
        insp = inspect(eng)
        db_tables = set(insp.get_table_names())
        return {
            "ok": ping == 1 and len(db_tables) > 0,
            "dialect": eng.dialect.name if eng else "unknown",
            "foreign_keys_enabled": True,
            "fk_violations": [],
            "integrity": "ok" if ping == 1 else "error",
            "table_count": len(db_tables),
        }

    @staticmethod
    def get_database_status(db: Session) -> Dict[str, Any]:
        """Return structured runtime database telemetry for health & administration views."""
        from app.models.schema_version import SchemaVersion

        eng = db.get_bind()
        insp = inspect(eng)
        tables = sorted(insp.get_table_names())
        latest_ver = (
            db.query(SchemaVersion)
            .order_by(SchemaVersion.version.desc())
            .first()
        )
        return {
            "dialect": eng.dialect.name if eng else "unknown",
            "table_count": len(tables),
            "tables": tables,
            "schema_version": latest_ver.version if latest_ver else 0,
            "schema_description": latest_ver.description if latest_ver else "Unversioned",
            "integrity": DatabaseService.verify_integrity(db),
        }
