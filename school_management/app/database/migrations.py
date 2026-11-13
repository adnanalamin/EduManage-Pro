"""
EduManage Pro - Non-Destructive Schema Migration & Versioning Runner
Ensures SQLite and PostgreSQL databases evolve safely without destroying existing user data.
Works automatically on desktop startup and pairs with Alembic for enterprise deployments.
"""

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.sql.sqltypes import Boolean, Date, DateTime, Float, Integer, Numeric, String, Text

import app.models  # noqa: F401  Ensure full Base.metadata registration
from app.config.logging_config import app_logger
from app.database.connection import Base, engine as default_engine
from app.models.base import utc_now
from app.models.schema_version import SchemaVersion
from app.models.school import SchoolSetting


CURRENT_SCHEMA_VERSION = 6

MIGRATIONS: List[Dict[str, Any]] = [
    {
        "version": 1,
        "description": "Initial EduManage Pro baseline schema",
    },
    {
        "version": 2,
        "description": (
            "Enterprise relational upgrade: UUID public_id, timezone timestamps, "
            "soft-delete columns, strict FK constraints, inventory module, and idempotency keys"
        ),
    },
    {
        "version": 3,
        "description": (
            "Enterprise authentication & RBAC upgrade: Module->Feature->Action permissions, "
            "role/permission active flags, login_history, password_reset_tokens, and user password policies"
        ),
    },
    {
        "version": 4,
        "description": (
            "Student CRM upgrade: Digital ID/QR fields, multiple guardian links, family links, "
            "admission/academic/previous-school/status histories, document vault, medical profile, "
            "emergency contacts, notes, tags, custom fields, and lifecycle workflow fields"
        ),
    },
    {
        "version": 5,
        "description": (
            "HR Management upgrade: Teacher & Staff attendance, qualifications, work experience, "
            "subject assignments, employment contracts, leave requests & approvals, document vault, "
            "salary history, performance evaluations, lifecycle events, and emergency contacts"
        ),
    },
    {
        "version": 6,
        "description": (
            "Academic Management upgrade: AcademicGroups, AcademicShifts, AcademicRooms, "
            "StudentSubjectEnrollments, StudentTransferHistory, historical promotion metadata, "
            "and AcademicYear-scoped calendar events"
        ),
    },
]


def _quote_ident(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'


def _compile_column_sql(col: Any, target_engine: Engine) -> str:
    """
    Build a safe ADD COLUMN clause compatible with SQLite and PostgreSQL.
    Note: SQLite disallows ADD COLUMN with non-constant expressions or inline UNIQUE constraints;
    uniqueness and backfills are applied right after adding the column.
    """
    dialect_name = target_engine.dialect.name
    col_type = col.type.compile(dialect=target_engine.dialect)
    if dialect_name == "postgresql":
        # Map SQLAlchemy type cleanly for PostgreSQL
        if isinstance(col.type, Boolean):
            col_type = "BOOLEAN"
        elif isinstance(col.type, DateTime):
            col_type = "TIMESTAMP WITH TIME ZONE" if getattr(col.type, "timezone", False) else "TIMESTAMP"
        elif isinstance(col.type, Numeric):
            col_type = f"NUMERIC({col.type.precision or 12}, {col.type.scale or 2})"
        elif isinstance(col.type, String):
            col_type = f"VARCHAR({col.type.length})" if col.type.length else "VARCHAR"
        elif isinstance(col.type, Text):
            col_type = "TEXT"
        elif isinstance(col.type, Integer):
            col_type = "INTEGER"
        elif isinstance(col.type, Float):
            col_type = "DOUBLE PRECISION"
        elif isinstance(col.type, Date):
            col_type = "DATE"

    # Determine safe scalar default for SQLite / PG non-null columns
    col_name = col.name
    if col_name == "is_deleted":
        default_clause = "DEFAULT 0 NOT NULL" if dialect_name == "sqlite" else "DEFAULT FALSE NOT NULL"
    elif col_name in ("created_at", "updated_at"):
        default_clause = "DEFAULT CURRENT_TIMESTAMP"
    elif isinstance(col.type, Boolean) and col.default is not None and not callable(col.default.arg):
        bool_val = bool(col.default.arg)
        default_clause = (
            f"DEFAULT {1 if bool_val else 0}"
            if dialect_name == "sqlite"
            else f"DEFAULT {'TRUE' if bool_val else 'FALSE'}"
        )
    elif isinstance(col.type, String) and col.default is not None and isinstance(col.default.arg, str):
        escaped = col.default.arg.replace("'", "''")
        default_clause = f"DEFAULT '{escaped}'"
    elif isinstance(col.type, (Integer, Float, Numeric)) and col.default is not None and isinstance(col.default.arg, (int, float)):
        default_clause = f"DEFAULT {col.default.arg}"
    else:
        default_clause = ""

    parts = [_quote_ident(col_name), col_type]
    if default_clause:
        parts.append(default_clause)
    return " ".join(parts)


def _backfill_public_ids(conn: Any, table_name: str) -> int:
    """Populate UUIDv4 values for any legacy rows missing public_id."""
    q_table = _quote_ident(table_name)
    rows = conn.execute(
        text(f"SELECT id FROM {q_table} WHERE public_id IS NULL OR public_id = ''")
    ).fetchall()
    if not rows:
        return 0

    for (row_id,) in rows:
        conn.execute(
            text(f"UPDATE {q_table} SET public_id = :pid WHERE id = :rid"),
            {"pid": str(uuid.uuid4()), "rid": row_id},
        )
    return len(rows)


def _backfill_timestamps(conn: Any, table_name: str, existing_added: List[str]) -> None:
    q_table = _quote_ident(table_name)
    now_iso = utc_now().isoformat()
    if "created_at" in existing_added:
        conn.execute(
            text(f"UPDATE {q_table} SET created_at = :ts WHERE created_at IS NULL"),
            {"ts": now_iso},
        )
    if "updated_at" in existing_added:
        conn.execute(
            text(f"UPDATE {q_table} SET updated_at = COALESCE(created_at, :ts) WHERE updated_at IS NULL"),
            {"ts": now_iso},
        )


def migrate_database(target_engine: Optional[Engine] = None) -> Dict[str, Any]:
    """
    Non-destructively synchronize the database schema to CURRENT_SCHEMA_VERSION.
    1. Creates any missing tables (preserving all existing tables & rows).
    2. Adds any missing columns on existing tables via ALTER TABLE ... ADD COLUMN.
    3. Backfills UUID public_id & timestamps on pre-existing rows.
    4. Creates missing indexes and records applied schema version in `schema_versions`.
    """
    eng = target_engine or default_engine
    dialect_name = eng.dialect.name
    inspector = inspect(eng)
    pre_existing_tables = set(inspector.get_table_names())

    # Capture columns per pre-existing table before create_all
    pre_columns: Dict[str, set] = {}
    pre_indexes: Dict[str, set] = {}
    for tbl in pre_existing_tables:
        pre_columns[tbl] = {col["name"] for col in inspector.get_columns(tbl)}
        pre_indexes[tbl] = {idx["name"] for idx in inspector.get_indexes(tbl) if idx.get("name")}

    # Step 1: Create any brand-new tables cleanly
    Base.metadata.create_all(bind=eng)

    post_inspector = inspect(eng)
    all_tables = set(post_inspector.get_table_names())
    tables_created = sorted(all_tables - pre_existing_tables)

    columns_added: Dict[str, List[str]] = {}
    backfilled_uuids = 0
    indexes_created: List[str] = []

    # Step 2: Non-destructively add missing columns & backfill legacy rows
    with eng.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            if table_name not in pre_existing_tables:
                continue

            existing_cols = pre_columns.get(table_name, set())
            added_for_table: List[str] = []
            for col in table.columns:
                if col.name in existing_cols:
                    continue
                col_ddl = _compile_column_sql(col, eng)
                stmt = f"ALTER TABLE {_quote_ident(table_name)} ADD COLUMN {col_ddl}"
                conn.execute(text(stmt))
                added_for_table.append(col.name)
                app_logger.info(f"Migrated {table_name}: added column '{col.name}'")

            if added_for_table:
                columns_added[table_name] = added_for_table

            # Ensure public_id exists cleanly on every row if present in table
            if "public_id" in table.columns and ("public_id" in added_for_table or "public_id" in existing_cols):
                backfilled_uuids += _backfill_public_ids(conn, table_name)

            if "created_at" in added_for_table or "updated_at" in added_for_table:
                _backfill_timestamps(conn, table_name, added_for_table)

            # Create missing indexes safely
            existing_idx_names = pre_indexes.get(table_name, set())
            for idx in table.indexes:
                if not idx.name or idx.name in existing_idx_names:
                    continue
                col_list = ", ".join(_quote_ident(c.name) for c in idx.columns)
                unique_kw = "UNIQUE " if idx.unique else ""
                try:
                    conn.execute(
                        text(
                            f"CREATE {unique_kw}INDEX IF NOT EXISTS {_quote_ident(idx.name)} "
                            f"ON {_quote_ident(table_name)} ({col_list})"
                        )
                    )
                    indexes_created.append(idx.name)
                except Exception as exc:
                    app_logger.warning(f"Skipped index '{idx.name}' on '{table_name}': {exc}")

        # Ensure unique index for public_id on tables where it was added cleanly via ALTER TABLE
        for table_name, added_cols in columns_added.items():
            if "public_id" in added_cols:
                idx_name = f"ix_{table_name}_public_id"
                if idx_name not in pre_indexes.get(table_name, set()):
                    conn.execute(
                        text(
                            f"CREATE UNIQUE INDEX IF NOT EXISTS {_quote_ident(idx_name)} "
                            f"ON {_quote_ident(table_name)} (\"public_id\")"
                        )
                    )

    # Step 3: Record SchemaVersion entries & sync SchoolSetting.schema_version
    from sqlalchemy.orm import sessionmaker

    LocalSession = sessionmaker(bind=eng, autocommit=False, autoflush=False)
    session = LocalSession()
    try:
        recorded_versions = {
            row[0] for row in session.query(SchemaVersion.version).all()
        }
        for mig in MIGRATIONS:
            ver = mig["version"]
            if ver <= CURRENT_SCHEMA_VERSION and ver not in recorded_versions:
                session.add(
                    SchemaVersion(
                        version=ver,
                        description=mig["description"],
                        dialect=dialect_name,
                        applied_by="system_migrator",
                    )
                )

        setting_row = session.query(SchoolSetting).first()
        if setting_row and (setting_row.schema_version or 0) < CURRENT_SCHEMA_VERSION:
            setting_row.schema_version = CURRENT_SCHEMA_VERSION

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return {
        "current_version": CURRENT_SCHEMA_VERSION,
        "dialect": dialect_name,
        "tables_created": tables_created,
        "columns_added": columns_added,
        "indexes_created": indexes_created,
        "backfilled_uuids": backfilled_uuids,
    }
