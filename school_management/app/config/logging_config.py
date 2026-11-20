"""
EduManage Pro - Logging Configuration
Configures multi-file structured logging with automatic secret redaction:
- app.log (general system operations)
- error.log (errors and exceptions)
- security.log (logins, logouts, lockouts, permission checks)
Guarantees passwords, bearer tokens, API keys, and hashes are never written in plaintext.
"""

import logging
from logging.handlers import RotatingFileHandler

from app.config.settings import LOGS_DIR
from app.security.audit import redact_text_secrets

MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
BACKUP_COUNT = 5


class SecretRedactingFilter(logging.Filter):
    """Automatically scrubs secret tokens, passwords, and key material from all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            scrubbed = redact_text_secrets(msg)
            if scrubbed != msg:
                record.msg = scrubbed
                record.args = ()
        except Exception:
            pass
        return True


LOG_FORMAT = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
SECURITY_FORMAT = logging.Formatter(
    "[%(asctime)s] [SECURITY] [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_redactor = SecretRedactingFilter()

# App logger
app_logger = logging.getLogger("edumanage.app")
app_logger.setLevel(logging.INFO)
app_handler = RotatingFileHandler(LOGS_DIR / "app.log", maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8")
app_handler.setFormatter(LOG_FORMAT)
app_handler.addFilter(_redactor)
app_logger.addHandler(app_handler)

# Error logger
error_logger = logging.getLogger("edumanage.error")
error_logger.setLevel(logging.WARNING)
err_handler = RotatingFileHandler(LOGS_DIR / "error.log", maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8")
err_handler.setFormatter(LOG_FORMAT)
err_handler.addFilter(_redactor)
error_logger.addHandler(err_handler)

# Security logger
security_logger = logging.getLogger("edumanage.security")
security_logger.setLevel(logging.INFO)
sec_handler = RotatingFileHandler(LOGS_DIR / "security.log", maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8")
sec_handler.setFormatter(SECURITY_FORMAT)
sec_handler.addFilter(_redactor)
security_logger.addHandler(sec_handler)

# Console logger for debug runs
console_handler = logging.StreamHandler()
console_handler.setFormatter(LOG_FORMAT)
console_handler.addFilter(_redactor)
app_logger.addHandler(console_handler)
error_logger.addHandler(console_handler)
