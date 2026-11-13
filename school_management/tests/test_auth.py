"""
EduManage Pro - Core Authentication & Password Policy Tests (pytest)
"""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.connection import Base, create_database_engine
from app.models.user import User, Role
from app.security.hasher import PasswordHasher
from app.security.session import session as app_session
from app.services.auth_service import AuthService

STRONG_TEST_PW = "Sup3r$Admin#2026!"


@pytest.fixture
def db_session():
    """Isolated SQLite database with FK enforcement for auth tests."""
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    ok, user, msg = AuthService.create_first_admin(
        session,
        username="chiefadmin",
        email="chief@school.edu",
        full_name="Chief Administrator",
        password=STRONG_TEST_PW,
    )
    assert ok and user, msg
    app_session.clear()

    yield session
    app_session.clear()
    session.close()
    engine.dispose()


def test_password_hasher_and_strength_policy():
    raw_pass = "SecurePass#2026!"
    hashed = PasswordHasher.hash_password(raw_pass)
    assert hashed != raw_pass
    assert PasswordHasher.verify_password(raw_pass, hashed) is True
    assert PasswordHasher.verify_password("WrongPass", hashed) is False

    # Reject banned hardcoded/default password & weak passwords
    ok_banned, _ = PasswordHasher.validate_password_strength("Admin@123")
    assert ok_banned is False
    ok_short, _ = PasswordHasher.validate_password_strength("Ab1!")
    assert ok_short is False


def test_auth_success_and_logout(db_session):
    success, user, msg = AuthService.authenticate(db_session, "chiefadmin", STRONG_TEST_PW)
    assert success is True
    assert user is not None
    assert user.username == "chiefadmin"
    assert "successful" in msg.lower()
    assert app_session.is_authenticated is True

    AuthService.logout(db_session)
    assert app_session.is_authenticated is False


def test_auth_wrong_password_and_lockout(db_session):
    success, user, msg = AuthService.authenticate(db_session, "chiefadmin", "BadPassword!99")
    assert success is False
    assert user is None
    assert "remaining" in msg.lower()

    for i in range(4):
        success, _, _ = AuthService.authenticate(db_session, "chiefadmin", f"WrongPass#{i}")
        assert success is False

    # 6th attempt must be blocked even with correct password while locked
    success, _, msg = AuthService.authenticate(db_session, "chiefadmin", STRONG_TEST_PW)
    assert success is False
    assert "locked" in msg.lower()


def test_password_change_and_reuse_rejection(db_session):
    user = db_session.query(User).filter_by(username="chiefadmin").first()

    # Reuse rejected
    ok_reuse, _ = AuthService.change_password(db_session, user.id, STRONG_TEST_PW, STRONG_TEST_PW)
    assert ok_reuse is False

    # Valid change
    new_pw = "NewEnterprise#2026!"
    success, msg = AuthService.change_password(db_session, user.id, STRONG_TEST_PW, new_pw)
    assert success is True, msg

    # Old password no longer works; new password works
    ok_old, _, _ = AuthService.authenticate(db_session, "chiefadmin", STRONG_TEST_PW)
    assert ok_old is False
    ok_new, _, _ = AuthService.authenticate(db_session, "chiefadmin", new_pw)
    assert ok_new is True
