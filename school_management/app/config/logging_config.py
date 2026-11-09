"""
EduManage Pro - Logging Configuration
Configures multi-file structured logging:
- app.log (general system operations)
- error.log (errors and exceptions)
- security.log (logins, logouts, lockouts, permission checks)
"""

import logging
from logging.handlers import RotatingFileHandler
from app.config.settings import LOGS_DIR

MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
BACKUP_COUNT = 5

LOG_FORMAT = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
SECURITY_FORMAT = logging.Formatter(
    "[%(asctime)s] [SECURITY] [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# App logger
app_logger = logging.getLogger("edumanage.app")
app_logger.setLevel(logging.INFO)
app_handler = RotatingFileHandler(LOGS_DIR / "app.log", maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8")
app_handler.setFormatter(LOG_FORMAT)
app_logger.addHandler(app_handler)

# Error logger
error_logger = logging.getLogger("edumanage.error")
error_logger.setLevel(logging.WARNING)
err_handler = RotatingFileHandler(LOGS_DIR / "error.log", maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8")
err_handler.setFormatter(LOG_FORMAT)
error_logger.addHandler(err_handler)

# Security logger
security_logger = logging.getLogger("edumanage.security")
security_logger.setLevel(logging.INFO)
sec_handler = RotatingFileHandler(LOGS_DIR / "security.log", maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8")
sec_handler.setFormatter(SECURITY_FORMAT)
security_logger.addHandler(sec_handler)

# Console logger for debug runs
console_handler = logging.StreamHandler()
console_handler.setFormatter(LOG_FORMAT)
app_logger.addHandler(console_handler)
error_logger.addHandler(console_handler)
