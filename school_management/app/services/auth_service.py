"""
EduManage Pro - Authentication Service
Handles login validation, failed attempts lockout protection, password changes, and audit logging.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.user import User, Role
from app.models.activity import ActivityLog
from app.security.hasher import PasswordHasher
from app.security.session import session as app_session
from app.config.settings import settings
from app.config.logging_config import security_logger, app_logger


class AuthService:
    @staticmethod
    def authenticate(
        db: Session,
        username_or_email: str,
        password: str,
        ip_address: str = "127.0.0.1"
    ) -> Tuple[bool, Optional[User], str]:
        """
        Authenticate user with username or email.
        Returns: (success, user_obj, message)
        """
        identifier = username_or_email.strip()
        user = db.query(User).filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if not user:
            security_logger.warning(f"Failed login attempt for unknown user: '{identifier}' from IP {ip_address}")
            return False, None, "Invalid username or password"

        if not user.is_active:
            security_logger.warning(f"Login attempt on deactivated user: '{user.username}' from IP {ip_address}")
            return False, None, "Account is deactivated. Contact your Super Administrator."

        # Check account lockout
        if user.locked_until and user.locked_until > datetime.utcnow():
            remaining = int((user.locked_until - datetime.utcnow()).total_seconds())
            security_logger.warning(f"Locked account login attempt for '{user.username}', {remaining}s remaining")
            return False, None, f"Account locked due to multiple failed attempts. Try again in {remaining} seconds."

        # Verify password
        if not PasswordHasher.verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(seconds=settings.LOCKOUT_DURATION_SECONDS)
                db.commit()
                security_logger.critical(
                    f"User '{user.username}' locked out for {settings.LOCKOUT_DURATION_SECONDS}s after {user.failed_login_attempts} failed attempts"
                )
                return False, None, f"Account locked for {settings.LOCKOUT_DURATION_SECONDS} seconds due to too many failed attempts."
            
            db.commit()
            remaining_attempts = settings.MAX_LOGIN_ATTEMPTS - user.failed_login_attempts
            security_logger.warning(
                f"Invalid password for '{user.username}'. Attempt {user.failed_login_attempts}/{settings.MAX_LOGIN_ATTEMPTS}"
            )
            return False, None, f"Invalid username or password. {remaining_attempts} attempts remaining."

        # Successful login: reset failed counters and update login info
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = ip_address
        
        # Log activity
        log = ActivityLog(
            user_id=user.id,
            username=user.username,
            action="LOGIN_SUCCESS",
            module="AUTH",
            description=f"User '{user.username}' logged in successfully as {user.role.name if user.role else 'Unknown'}",
            ip_address=ip_address,
            severity="INFO"
        )
        db.add(log)
        db.commit()

        app_session.set_current_user(user)
        security_logger.info(f"User '{user.username}' authenticated successfully from {ip_address}")
        return True, user, "Login successful"

    @staticmethod
    def change_password(
        db: Session,
        user_id: int,
        old_password: str,
        new_password: str,
        ip_address: str = "127.0.0.1"
    ) -> Tuple[bool, str]:
        """Validate and update user password."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"

        if not PasswordHasher.verify_password(old_password, user.password_hash):
            return False, "Current password is incorrect"

        if len(new_password) < 8:
            return False, "Password must be at least 8 characters long"
        
        has_upper = any(c.isupper() for c in new_password)
        has_lower = any(c.islower() for c in new_password)
        has_digit = any(c.isdigit() for c in new_password)
        if not (has_upper and has_lower and has_digit):
            return False, "Password must contain uppercase letters, lowercase letters, and at least one number"

        user.password_hash = PasswordHasher.hash_password(new_password)
        user.is_default_password = False

        log = ActivityLog(
            user_id=user.id,
            username=user.username,
            action="PASSWORD_CHANGE",
            module="AUTH",
            description=f"User '{user.username}' updated account password",
            ip_address=ip_address,
            severity="SECURITY"
        )
        db.add(log)
        db.commit()
        security_logger.info(f"Password changed successfully for user '{user.username}'")
        return True, "Password updated successfully"

    @staticmethod
    def logout(db: Session, ip_address: str = "127.0.0.1"):
        """Clear active user session and record logout."""
        user = app_session.current_user
        if user:
            log = ActivityLog(
                user_id=user.id,
                username=user.username,
                action="LOGOUT",
                module="AUTH",
                description=f"User '{user.username}' logged out",
                ip_address=ip_address,
                severity="INFO"
            )
            db.add(log)
            db.commit()
            security_logger.info(f"User '{user.username}' logged out")
        app_session.clear()
