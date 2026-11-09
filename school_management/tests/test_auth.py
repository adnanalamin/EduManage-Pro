"""
EduManage Pro - Authentication & Security Tests (pytest)
Tests:
- Password hashing with bcrypt
- Default super admin seeding
- Correct credential verification
- Invalid password and lockout behavior
- Password change requirements
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.connection import Base
from app.models.user import User, Role, Permission
from app.models.activity import ActivityLog
from app.security.hasher import PasswordHasher
from app.services.auth_service import AuthService


@pytest.fixture
def db_session():
    """In-memory SQLite database for fast unit testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed Super Admin Role & User
    role = Role(name="super_admin", display_name="Super Admin", is_system_role=True)
    session.add(role)
    session.flush()

    user = User(
        username="admin",
        email="admin@test.local",
        password_hash=PasswordHasher.hash_password("Admin@123"),
        full_name="Super Administrator",
        role_id=role.id,
        is_active=True,
        is_default_password=True,
    )
    session.add(user)
    session.commit()

    yield session
    session.close()


def test_password_hasher():
    raw_pass = "SecurePass123!"
    hashed = PasswordHasher.hash_password(raw_pass)
    assert hashed != raw_pass
    assert PasswordHasher.verify_password(raw_pass, hashed) is True
    assert PasswordHasher.verify_password("WrongPass", hashed) is False


def test_auth_success(db_session):
    success, user, msg = AuthService.authenticate(db_session, "admin", "Admin@123")
    assert success is True
    assert user is not None
    assert user.username == "admin"
    assert "successful" in msg.lower()


def test_auth_wrong_password(db_session):
    success, user, msg = AuthService.authenticate(db_session, "admin", "BadPassword")
    assert success is False
    assert user is None
    assert "remaining" in msg.lower()


def test_account_lockout(db_session):
    # Try 5 failed logins
    for i in range(5):
        success, user, msg = AuthService.authenticate(db_session, "admin", f"WrongPass{i}")
        assert success is False

    # 6th attempt must trigger lockout response
    success, user, msg = AuthService.authenticate(db_session, "admin", "Admin@123")
    assert success is False
    assert "locked" in msg.lower()


def test_password_change(db_session):
    user = db_session.query(User).filter_by(username="admin").first()
    success, msg = AuthService.change_password(db_session, user.id, "Admin@123", "NewSecret#2026")
    assert success is True

    # Test login with new password
    success, _, _ = AuthService.authenticate(db_session, "admin", "NewSecret#2026")
    assert success is True
