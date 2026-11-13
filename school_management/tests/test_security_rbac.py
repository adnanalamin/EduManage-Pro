"""
EduManage Pro - Enterprise Security, RBAC Hierarchy & Audit Automated Tests (pytest)
Covers:
- Absence of hardcoded default credentials after database initialization
- First-run Super Administrator creation & duplicate prevention
- Password policy, password reset tokens (SHA-256 hashed, single-use, expiring)
- Admin user creation, activation/deactivation & last Super Admin guard
- Login attempt lockout & LoginHistory persistence
- Session timeout & logout activity tracking
- Hierarchical RBAC: Module -> Feature -> Action (all 10 actions VIEW..MANAGE)
- Super Admin role creation, cloning, permission assignment & global permission disabling
- Zero plaintext passwords or raw reset tokens in DB or logs
"""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.connection import Base, create_database_engine
from app.database.init_db import SYSTEM_ROLES
from app.models.activity import ActivityLog
from app.models.user import LoginHistory, PasswordResetToken, Permission, Role, User
from app.security.hasher import PasswordHasher
from app.security.permissions import ALL_ACTIONS
from app.security.session import SessionManager, session as app_session
from app.services.auth_service import AuthService


@pytest.fixture
def sec_db():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()

    for code, disp, desc, is_sys in SYSTEM_ROLES:
        db.add(
            Role(
                name=code,
                display_name=disp,
                description=desc,
                is_system_role=is_sys,
                is_active=True,
            )
        )
    db.commit()
    AuthService.sync_permission_catalog(db)
    app_session.clear()

    yield db
    app_session.clear()
    db.close()
    engine.dispose()


def test_no_hardcoded_default_users_on_fresh_database(sec_db):
    assert sec_db.query(User).count() == 0
    assert AuthService.has_super_admin(sec_db) is False
    ok, _, _ = AuthService.authenticate(sec_db, "admin", "Admin@123")
    assert ok is False


def test_first_run_admin_creation_and_duplicate_block(sec_db):
    # Reject weak or banned default password
    ok_weak, _, _ = AuthService.create_first_admin(
        sec_db, "rootadmin", "root@school.edu", "Root Admin", "Admin@123"
    )
    assert ok_weak is False

    # Valid creation succeeds
    secret = "V@lidRootPass99!"
    ok, admin, msg = AuthService.create_first_admin(
        sec_db, "rootadmin", "root@school.edu", "Root Admin", secret
    )
    assert ok is True, msg
    assert admin is not None
    assert admin.password_hash != secret
    assert admin.is_default_password is False
    assert AuthService.has_super_admin(sec_db) is True

    # Cannot create second Super Admin via first-run bootstrap
    ok2, _, msg2 = AuthService.create_first_admin(
        sec_db, "secondadmin", "second@school.edu", "Second Admin", "An0therStr0ng!Pw"
    )
    assert ok2 is False
    assert "already exists" in msg2.lower()


def test_user_lifecycle_activation_and_last_admin_protection(sec_db):
    admin_pw = "Super@Vault2026!"
    _, admin, _ = AuthService.create_first_admin(
        sec_db, "principal", "principal@school.edu", "Principal", admin_pw
    )

    # Cannot deactivate self or last active super admin
    ok_self, msg_self = AuthService.set_user_active(sec_db, admin, admin.id, False)
    assert ok_self is False
    assert "own" in msg_self.lower() or "last" in msg_self.lower()

    teacher_role = sec_db.query(Role).filter_by(name="teacher").first()
    teacher_pw = "T3ach3r@Pass9!"
    ok_u, teacher_user, msg_u = AuthService.create_user(
        sec_db,
        actor_user=admin,
        username="t_rahman",
        email="rahman@school.edu",
        full_name="Mr. Rahman",
        password=teacher_pw,
        role_id=teacher_role.id,
        must_change_password=True,
    )
    assert ok_u is True, msg_u
    assert teacher_user.must_change_password is True

    # Non-admin teacher cannot create users or deactivate accounts
    ok_denied, _, _ = AuthService.create_user(
        sec_db,
        actor_user=teacher_user,
        username="rogue",
        email="rogue@school.edu",
        full_name="Rogue",
        password="R0gue@Pass123!",
        role_id=teacher_role.id,
    )
    assert ok_denied is False

    # Deactivate teacher -> login blocked and recorded in LoginHistory
    ok_deact, _ = AuthService.set_user_active(sec_db, admin, teacher_user.id, False)
    assert ok_deact is True

    ok_login, _, login_msg = AuthService.authenticate(sec_db, "t_rahman", teacher_pw)
    assert ok_login is False
    assert "deactivated" in login_msg.lower()

    # Reactivate teacher -> login allowed
    ok_act, _ = AuthService.set_user_active(sec_db, admin, teacher_user.id, True)
    assert ok_act is True
    ok_login2, _, _ = AuthService.authenticate(sec_db, "t_rahman", teacher_pw)
    assert ok_login2 is True


def test_password_reset_token_and_admin_reset_never_store_plaintext(sec_db):
    admin_pw = "Adm1n#Master88!"
    _, admin, _ = AuthService.create_first_admin(
        sec_db, "sysadmin", "sys@school.edu", "Sys Admin", admin_pw
    )
    acc_role = sec_db.query(Role).filter_by(name="accountant").first()
    initial_pw = "Acc0unt@2026!"
    _, acc_user, _ = AuthService.create_user(
        sec_db, admin, "acc_sara", "sara@school.edu", "Sara Khan", initial_pw, acc_role.id
    )

    # Lock out acc_sara first
    for i in range(5):
        AuthService.authenticate(sec_db, "acc_sara", f"BadTry#{i}!")
    locked_ok, _, _ = AuthService.authenticate(sec_db, "acc_sara", initial_pw)
    assert locked_ok is False

    # Issue password reset token
    ok_req, raw_token, _ = AuthService.request_password_reset(sec_db, "acc_sara", actor_username="sysadmin")
    assert ok_req is True
    assert raw_token is not None

    # Raw token MUST NOT be stored in DB or ActivityLogs
    stored_token = sec_db.query(PasswordResetToken).filter_by(user_id=acc_user.id).first()
    assert stored_token is not None
    assert stored_token.token_hash != raw_token
    assert stored_token.token_hash == PasswordHasher.hash_token(raw_token)

    # Redeem token resets password AND clears lockout
    reset_pw = "SaraReset#2026!"
    ok_comp, _ = AuthService.complete_password_reset(sec_db, raw_token, reset_pw)
    assert ok_comp is True

    # Single-use: reusing token fails
    ok_reuse, _ = AuthService.complete_password_reset(sec_db, raw_token, "An0ther#2026!")
    assert ok_reuse is False

    # Login with reset password succeeds
    ok_auth, _, _ = AuthService.authenticate(sec_db, "acc_sara", reset_pw)
    assert ok_auth is True

    # Admin-initiated temporary password reset
    ok_adm_rst, temp_pw, _ = AuthService.admin_reset_password(sec_db, admin, acc_user.id)
    assert ok_adm_rst is True
    assert temp_pw is not None
    sec_db.refresh(acc_user)
    assert acc_user.must_change_password is True

    # Ensure ZERO plaintext passwords or raw tokens appear in logs/DB tables
    all_logs = sec_db.query(ActivityLog).all()
    all_hist = sec_db.query(LoginHistory).all()
    forbidden_secrets = [admin_pw, initial_pw, reset_pw, temp_pw, raw_token]
    for secret in forbidden_secrets:
        for log in all_logs:
            assert secret not in (log.description or "")
        for h in all_hist:
            assert secret not in (h.failure_reason or "")
        for u in sec_db.query(User).all():
            assert secret not in u.password_hash


def test_session_timeout_and_login_history_tracking(sec_db):
    admin_pw = "SecTimeout#2026!"
    _, admin, _ = AuthService.create_first_admin(
        sec_db, "secadmin", "sec@school.edu", "Security Admin", admin_pw
    )

    ok, _, _ = AuthService.authenticate(sec_db, "secadmin", admin_pw, ip_address="192.168.1.50")
    assert ok is True
    assert app_session.is_authenticated is True

    # Simulate idle time exceeding timeout window
    app_session.timeout_minutes = 15
    future_time = app_session.last_activity_at + timedelta(minutes=16)
    assert app_session.is_expired(now=future_time) is True

    # Trigger timeout logout
    AuthService.logout(sec_db, ip_address="192.168.1.50", reason="SESSION_TIMEOUT")
    assert app_session.is_authenticated is False

    hist = sec_db.query(LoginHistory).filter_by(username_attempted="secadmin").first()
    assert hist is not None
    assert hist.status == "SUCCESS"
    assert hist.logout_at is not None
    assert "timeout" in (hist.failure_reason or "").lower()

    timeout_log = sec_db.query(ActivityLog).filter_by(action="SESSION_TIMEOUT").first()
    assert timeout_log is not None


def test_permission_hierarchy_actions_clone_and_global_disable(sec_db):
    # Verify all 10 required actions exist in catalog
    actions_in_db = {p.action for p in sec_db.query(Permission).all()}
    for required_action in ALL_ACTIONS:
        assert required_action in actions_in_db

    admin_pw = "Matrix@Admin99!"
    _, admin, _ = AuthService.create_first_admin(
        sec_db, "matrixadmin", "matrix@school.edu", "Matrix Admin", admin_pw
    )

    # Create custom role + assign specific hierarchical permissions
    view_perm = sec_db.query(Permission).filter_by(code="fees.collection.VIEW").first()
    refund_perm = sec_db.query(Permission).filter_by(code="fees.collection.REFUND").first()
    assert view_perm is not None and refund_perm is not None

    ok_role, custom_role, msg_r = AuthService.create_role(
        sec_db,
        admin,
        name="bursar_lead",
        display_name="Lead Bursar",
        permission_ids=[view_perm.id, refund_perm.id],
    )
    assert ok_role is True, msg_r

    # Clone role copies permissions cleanly
    ok_clone, cloned_role, msg_c = AuthService.clone_role(
        sec_db, admin, custom_role.id, "bursar_assistant", "Assistant Bursar"
    )
    assert ok_clone is True, msg_c
    assert {p.code for p in cloned_role.permissions} == {"fees.collection.VIEW", "fees.collection.REFUND"}

    # Assign user to cloned role
    _, bursar_user, _ = AuthService.create_user(
        sec_db, admin, "bursar1", "bursar@school.edu", "Bursar One", "Bursar#2026!", cloned_role.id
    )
    assert bursar_user.has_permission("fees.collection.REFUND") is True
    assert bursar_user.has_permission(module="FEES", action="REFUND") is True
    assert bursar_user.has_permission("students.directory.DELETE") is False

    # Super Admin globally disables REFUND permission -> immediately revoked for non-super-admin
    ok_dis, _ = AuthService.set_permission_enabled(sec_db, admin, refund_perm.id, False)
    assert ok_dis is True
    sec_db.refresh(bursar_user)
    assert bursar_user.has_permission("fees.collection.REFUND") is False
    assert bursar_user.has_permission("fees.collection.VIEW") is True
    assert admin.has_permission("fees.collection.REFUND") is True

    # Re-enable restores access
    AuthService.set_permission_enabled(sec_db, admin, refund_perm.id, True)
    sec_db.refresh(bursar_user)
    assert bursar_user.has_permission("fees.collection.REFUND") is True
