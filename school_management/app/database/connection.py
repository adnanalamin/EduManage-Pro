"""
EduManage Pro - Database Connection & Dialect-Aware Engine Factory
Supports Standalone SQLite (WAL + FK enforcement) and Enterprise/LAN PostgreSQL (connection pooling).
"""

from contextlib import contextmanager
from typing import Optional, Iterator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.config.settings import settings
from app.config.logging_config import app_logger, error_logger


def is_sqlite_url(database_url: str) -> bool:
    return database_url.strip().lower().startswith("sqlite")


def is_postgresql_url(database_url: str) -> bool:
    lowered = database_url.strip().lower()
    return lowered.startswith("postgresql") or lowered.startswith("postgres")


def _attach_sqlite_pragmas(target_engine: Engine, is_memory: bool = False) -> None:
    @event.listens_for(target_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=15000")
        if not is_memory:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()


def create_database_engine(database_url: Optional[str] = None, echo: Optional[bool] = None) -> Engine:
    """
    Create a SQLAlchemy Engine tuned for either SQLite (standalone) or PostgreSQL (LAN/Enterprise).
    """
    url = (database_url or settings.DATABASE_URL).strip()
    sql_echo = settings.DB_ECHO if echo is None else echo

    if is_sqlite_url(url):
        is_memory = ":memory:" in url
        eng = create_engine(
            url,
            echo=sql_echo,
            future=True,
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        _attach_sqlite_pragmas(eng, is_memory=is_memory)
        return eng

    # PostgreSQL / Enterprise pool configuration
    return create_engine(
        url,
        echo=sql_echo,
        future=True,
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=1800,
    )


engine = create_database_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)
Base = declarative_base()


def is_sqlite(target: Optional[Session | Engine] = None) -> bool:
    if isinstance(target, Session):
        return target.bind.dialect.name == "sqlite" if target.bind else is_sqlite_url(settings.DATABASE_URL)
    if isinstance(target, Engine):
        return target.dialect.name == "sqlite"
    return engine.dialect.name == "sqlite"


def is_postgresql(target: Optional[Session | Engine] = None) -> bool:
    if isinstance(target, Session):
        return target.bind.dialect.name == "postgresql" if target.bind else is_postgresql_url(settings.DATABASE_URL)
    if isinstance(target, Engine):
        return target.dialect.name == "postgresql"
    return engine.dialect.name == "postgresql"


def configure_engine(database_url: str, echo: Optional[bool] = None) -> Engine:
    """Reconfigure the global engine and SessionLocal (useful for runtime DB switching or tests)."""
    global engine
    engine.dispose()
    engine = create_database_engine(database_url, echo=echo)
    SessionLocal.configure(bind=engine)
    app_logger.info(f"Database engine reconfigured for dialect: {engine.dialect.name}")
    return engine


@contextmanager
def get_db() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        error_logger.exception(f"Database session error: {exc}")
        raise
    finally:
        session.close()


@contextmanager
def transaction_scope(session: Session) -> Iterator[Session]:
    """
    Provide an atomic transaction boundary on an existing Session.
    Uses a SAVEPOINT (begin_nested) if a transaction is already active.
    """
    if session.in_transaction():
        with session.begin_nested():
            yield session
    else:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
