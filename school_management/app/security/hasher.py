"""
EduManage Pro - Enterprise Password & Token Hashing Utility
Uses bcrypt with secure salt generation and SHA-256 token hashing.
Never stores or logs plaintext passwords or reset tokens.
"""

import hashlib
import re
import secrets
import string
from typing import Optional, Tuple

import bcrypt

from app.config.settings import settings

SPECIAL_CHARS = r"!@#$%^&*()-_=+[]{}|;:'\",.<>?/`~\\"
BANNED_WEAK_PASSWORDS = {
    "admin@123",
    "admin123",
    "password",
    "password123",
    "12345678",
    "123456789",
    "qwerty123",
    "letmein123",
    "edumanage",
    "edumanage123",
    "root@123",
}


class PasswordHasher:
    @staticmethod
    def validate_password_strength(
        password: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        min_length: int = 8,
    ) -> Tuple[bool, str]:
        """
        Enforce enterprise password policy:
        - Minimum length (default 8)
        - Uppercase, lowercase, digit, and special character
        - Not equal to banned common/default passwords or user identifiers
        """
        if not password:
            return False, "Password cannot be empty."
        if len(password) < min_length:
            return False, f"Password must be at least {min_length} characters long."

        lowered = password.strip().lower()
        if lowered in BANNED_WEAK_PASSWORDS:
            return False, "Password is too common or matches a known insecure default."

        if username and len(username.strip()) >= 3 and username.strip().lower() in lowered:
            return False, "Password must not contain your username."
        if email and "@" in email:
            local_part = email.split("@", 1)[0].strip().lower()
            if len(local_part) >= 3 and local_part in lowered:
                return False, "Password must not contain your email address."

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in SPECIAL_CHARS for c in password)

        if not (has_upper and has_lower and has_digit and has_special):
            return (
                False,
                "Password must include uppercase, lowercase, a number, and a special character (e.g. !@#$%).",
            )

        return True, "Password meets security policy."

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """Hash a plaintext password using bcrypt with configurable cost factor."""
        if not plain_password:
            raise ValueError("Password cannot be empty")
        salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify plaintext password against stored bcrypt hash in constant time."""
        if not plain_password or not hashed_password:
            return False
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except Exception:
            return False

    @staticmethod
    def needs_rehash(hashed_password: str) -> bool:
        """Check whether an existing bcrypt hash uses a weaker cost factor than configured."""
        if not hashed_password:
            return True
        match = re.match(r"^\$2[aby]\$(\d{2})\$", hashed_password)
        if not match:
            return True
        return int(match.group(1)) < settings.BCRYPT_ROUNDS

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Compute deterministic SHA-256 hex digest for reset tokens (never store raw tokens)."""
        if not raw_token:
            raise ValueError("Token cannot be empty")
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_secure_token(nbytes: int = 24) -> str:
        """Generate a cryptographically random URL-safe reset token."""
        return secrets.token_urlsafe(nbytes)

    @staticmethod
    def generate_temporary_password(length: int = 14) -> str:
        """Generate a cryptographically random complex temporary password."""
        length = max(length, 12)
        uppers = "ABCDEFGHJKLMNPQRSTUVWXYZ"
        lowers = "abcdefghijkmnopqrstuvwxyz"
        digits = "23456789"
        specials = "!@#$%^&*"
        pool = uppers + lowers + digits + specials

        chars = [
            secrets.choice(uppers),
            secrets.choice(lowers),
            secrets.choice(digits),
            secrets.choice(specials),
        ]
        chars.extend(secrets.choice(pool) for _ in range(length - 4))
        secrets.SystemRandom().shuffle(chars)
        return "".join(chars)
