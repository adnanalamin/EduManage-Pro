"""
EduManage Pro - Application Configuration
Handles directory paths, database settings, security parameters, and localization.
"""

from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus
from pydantic import BaseModel
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"
ASSETS_DIR = BASE_DIR / "assets"

for d in [DATA_DIR, LOGS_DIR, BACKUPS_DIR, ASSETS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def _resolve_database_url(default_sqlite_path: Path) -> str:
    explicit_url = os.getenv("EDUMANAGE_DATABASE_URL") or os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url.strip()

    backend = os.getenv("EDUMANAGE_DB_BACKEND", "sqlite").strip().lower()
    if backend in ("postgres", "postgresql"):
        host = os.getenv("EDUMANAGE_PG_HOST", "localhost")
        port = os.getenv("EDUMANAGE_PG_PORT", "5432")
        db_name = os.getenv("EDUMANAGE_PG_DB", "edumanage_pro")
        user = quote_plus(os.getenv("EDUMANAGE_PG_USER", "edumanage"))
        password = quote_plus(os.getenv("EDUMANAGE_PG_PASSWORD", ""))
        auth = f"{user}:{password}@" if password else f"{user}@"
        return f"postgresql+psycopg://{auth}{host}:{port}/{db_name}"

    return f"sqlite:///{default_sqlite_path.as_posix()}"


class AppSettings(BaseModel):
    APP_NAME: str = "EduManage Pro"
    APP_SUBTITLE: str = "Complete School Management System"
    APP_VERSION: str = "1.0.0"
    ORGANIZATION: str = "EduManage Technologies"

    # Database (SQLite standalone default, PostgreSQL enterprise-ready)
    DB_BACKEND: str = os.getenv("EDUMANAGE_DB_BACKEND", "sqlite").strip().lower()
    DATABASE_NAME: str = "edumanage.db"
    DATABASE_PATH: Path = DATA_DIR / DATABASE_NAME
    DATABASE_URL: str = _resolve_database_url(DATABASE_PATH)
    DB_POOL_SIZE: int = int(os.getenv("EDUMANAGE_DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("EDUMANAGE_DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT: int = int(os.getenv("EDUMANAGE_DB_POOL_TIMEOUT", "30"))
    DB_ECHO: bool = os.getenv("EDUMANAGE_DB_ECHO", "false").strip().lower() in ("1", "true", "yes")
    SCHEMA_VERSION: int = 4

    # Security
    BCRYPT_ROUNDS: int = 12
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_SECONDS: int = 60
    SESSION_TIMEOUT_MINUTES: int = 120

    # Localization Defaults (Customizable in DB Settings)
    DEFAULT_CURRENCY: str = "BDT"
    DEFAULT_CURRENCY_SYMBOL: str = "৳"
    DEFAULT_LANGUAGE: str = "en"  # "en" or "bn"
    DATE_FORMAT: str = "%Y-%m-%d"
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    # UI Themes
    DEFAULT_THEME: str = "dark"  # "dark" or "light"


settings = AppSettings()

