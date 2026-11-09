"""
EduManage Pro - Application Configuration
Handles directory paths, database settings, security parameters, and localization.
"""

from pathlib import Path
from pydantic import BaseModel
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"
ASSETS_DIR = BASE_DIR / "assets"

for d in [DATA_DIR, LOGS_DIR, BACKUPS_DIR, ASSETS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class AppSettings(BaseModel):
    APP_NAME: str = "EduManage Pro"
    APP_SUBTITLE: str = "Complete School Management System"
    APP_VERSION: str = "1.0.0"
    ORGANIZATION: str = "EduManage Technologies"
    
    # Database
    DATABASE_NAME: str = "edumanage.db"
    DATABASE_PATH: Path = DATA_DIR / DATABASE_NAME
    DATABASE_URL: str = f"sqlite:///{DATABASE_PATH.as_posix()}"
    
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
