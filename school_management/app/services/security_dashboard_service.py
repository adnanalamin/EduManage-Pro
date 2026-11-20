"""
EduManage Pro - Security Operations Center & Dashboard Service
Real-DB aggregations and actions for:
- Failed logins & locked accounts (with unlock)
- Active sessions (with expiry sweep & admin revocation)
- Suspicious activity alerts (with acknowledge / resolve workflow)
- Recent administrator actions & structured Audit Log viewer (WHO/WHAT/WHEN/MODULE/RECORD/BEFORE/AFTER)
- Formula-safe, secret-redacted CSV audit export
"""

import csv
from datetime import timedelta
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.models.activity import ActivityLog
from app.models.base import utc_now
from app.models.user import LoginHistory, SecurityAlert, User, UserSession
from app.security.audit import AuditService, redact_text_secrets
from app.security.data_protection import SensitiveDataProtector
from app.security.db_security import DatabaseSecurityValidator
from app.security.guards import authorize_action


class SecurityDashboardService:
    """Backend service backing the Enterprise Security Dashboard & Audit Inspector."""

    @staticmethod
    def sweep_expired_sessions(db: Session) -> int:
        """Mark elapsed active sessions inactive automatically."""
        now = utc_now()
        active = db.query(UserSession).filter(UserSession.is_active == True).all()
        closed = 0
        for s in active:
            exp = s.expires_at
            if exp and exp.tzinfo is None:
                from datetime import timezone
                exp = exp.replace(tzinfo=timezone.utc)
            if exp and exp <= now:
                s.is_active = False
                s.revoked_at = now
                s.revoked_by = "system_expiry"
                s.revoke_reason = "Session idle timeout reached"
                closed += 1
        if closed:
            db.commit()
        return closed

    @staticmethod
    def get_dashboard_summary(db: Session) -> Dict[str, Any]:
        """Return live KPI counts from database tables."""
        SecurityDashboardService.sweep_expired_sessions(db)
        now = utc_now()
        since_24h = now - timedelta(hours=24)

        failed_24h = (
            db.query(LoginHistory.id)
            .filter(LoginHistory.status != "SUCCESS", LoginHistory.login_at >= since_24h)
            .count()
        )
        locked_accounts = (
            db.query(User.id)
            .filter(User.is_deleted == False, User.locked_until.isnot(None), User.locked_until > now)
            .count()
        )
        active_sessions = db.query(UserSession.id).filter(UserSession.is_active == True).count()
        open_alerts = db.query(SecurityAlert.id).filter(SecurityAlert.status == "OPEN").count()
        critical_alerts = (
            db.query(SecurityAlert.id)
            .filter(SecurityAlert.status == "OPEN", SecurityAlert.severity.in_(["HIGH", "CRITICAL"]))
            .count()
        )
        admin_actions_24h = (
            db.query(ActivityLog.id)
            .filter(ActivityLog.is_admin_action == True, ActivityLog.created_at >= since_24h)
            .count()
        )

        return {
            "failed_logins_24h": failed_24h,
            "locked_accounts": locked_accounts,
            "active_sessions": active_sessions,
            "open_alerts": open_alerts,
            "critical_or_high_alerts": critical_alerts,
            "admin_actions_24h": admin_actions_24h,
        }

    @staticmethod
    def get_failed_logins(db: Session, limit: int = 100) -> List[LoginHistory]:
        return (
            db.query(LoginHistory)
            .filter(LoginHistory.status != "SUCCESS")
            .order_by(LoginHistory.login_at.desc(), LoginHistory.id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_locked_users(db: Session) -> List[User]:
        now = utc_now()
        return (
            db.query(User)
            .options(joinedload(User.role))
            .filter(User.is_deleted == False, User.locked_until.isnot(None), User.locked_until > now)
            .order_by(User.locked_until.desc())
            .all()
        )

    @staticmethod
    def get_active_sessions(db: Session, limit: int = 100) -> List[UserSession]:
        SecurityDashboardService.sweep_expired_sessions(db)
        return (
            db.query(UserSession)
            .filter(UserSession.is_active == True)
            .order_by(UserSession.last_activity_at.desc(), UserSession.id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_suspicious_alerts(
        db: Session,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[SecurityAlert]:
        q = db.query(SecurityAlert)
        if status and status != "ALL":
            q = q.filter(SecurityAlert.status == status)
        if severity and severity != "ALL":
            q = q.filter(SecurityAlert.severity == severity)
        return q.order_by(SecurityAlert.created_at.desc(), SecurityAlert.id.desc()).limit(limit).all()

    @staticmethod
    def resolve_alert(
        db: Session,
        actor_user: User,
        alert_id: int,
        new_status: str = "RESOLVED",
        notes: str = "",
        ip_address: str = "127.0.0.1",
    ) -> Tuple[bool, str]:
        authorize_action(
            db,
            actor_user,
            permission_code="security.audit.VIEW",
            module="SECURITY",
            action="VIEW",
            record_ref=f"SecurityAlert#{alert_id}",
            ip_address=ip_address,
        )
        st = new_status.strip().upper()
        if st not in ("OPEN", "ACKNOWLEDGED", "RESOLVED"):
            return False, "Invalid alert status."

        alert = db.query(SecurityAlert).filter(SecurityAlert.id == alert_id).first()
        if not alert:
            return False, "Security alert not found."

        before = {"status": alert.status, "resolved_by": alert.resolved_by, "resolution_notes": alert.resolution_notes}
        alert.status = st
        alert.resolved_by = actor_user.username
        alert.resolved_at = utc_now()
        alert.resolution_notes = redact_text_secrets(notes or f"Marked {st} by {actor_user.username}")[:255]

        AuditService.record(
            db,
            action=f"SECURITY_ALERT_{st}",
            module="SECURITY",
            description=f"Security alert {alert.alert_code} ({alert.alert_type}) marked {st}.",
            who_user=actor_user,
            entity_type="SecurityAlert",
            entity_id=alert.id,
            record_label=alert.alert_code,
            before=before,
            after={"status": alert.status, "resolved_by": alert.resolved_by, "resolution_notes": alert.resolution_notes},
            severity="SECURITY",
            ip_address=ip_address,
            is_admin_action=True,
        )
        db.commit()
        return True, f"Alert {alert.alert_code} updated to {st}."

    @staticmethod
    def get_recent_admin_actions(db: Session, limit: int = 100) -> List[ActivityLog]:
        return (
            db.query(ActivityLog)
            .filter(ActivityLog.is_admin_action == True)
            .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def query_audit_logs(
        db: Session,
        *,
        module: Optional[str] = None,
        severity: Optional[str] = None,
        username: Optional[str] = None,
        admin_only: bool = False,
        limit: int = 200,
    ) -> List[ActivityLog]:
        q = db.query(ActivityLog)
        if module and module != "ALL":
            q = q.filter(ActivityLog.module == module)
        if severity and severity != "ALL":
            q = q.filter(ActivityLog.severity == severity)
        if username and username.strip():
            esc = DatabaseSecurityValidator.escape_like_pattern(username.strip())
            q = q.filter(ActivityLog.username.ilike(f"%{esc}%", escape="\\"))
        if admin_only:
            q = q.filter(ActivityLog.is_admin_action == True)
        return q.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(limit).all()

    @staticmethod
    def export_audit_logs_csv(db: Session, output_path: str, limit: int = 500) -> int:
        """Export WHO/WHAT/WHEN/MODULE/RECORD/BEFORE/AFTER logs with secret redaction & formula neutralization."""
        logs = SecurityDashboardService.query_audit_logs(db, limit=limit)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["WHEN (UTC)", "WHO", "ROLE", "WHAT", "MODULE", "RECORD", "SEVERITY", "IP", "BEFORE", "AFTER", "DESCRIPTION"])
        for a in logs:
            writer.writerow([
                SensitiveDataProtector.sanitize_csv_cell(a.created_at.isoformat() if a.created_at else ""),
                SensitiveDataProtector.sanitize_csv_cell(a.username),
                SensitiveDataProtector.sanitize_csv_cell(a.actor_role or "-"),
                SensitiveDataProtector.sanitize_csv_cell(a.action),
                SensitiveDataProtector.sanitize_csv_cell(a.module),
                SensitiveDataProtector.sanitize_csv_cell(a.record_ref),
                SensitiveDataProtector.sanitize_csv_cell(a.severity),
                SensitiveDataProtector.sanitize_csv_cell(a.ip_address or ""),
                SensitiveDataProtector.sanitize_csv_cell(redact_text_secrets(a.before_data or "")),
                SensitiveDataProtector.sanitize_csv_cell(redact_text_secrets(a.after_data or "")),
                SensitiveDataProtector.sanitize_csv_cell(redact_text_secrets(a.description)),
            ])
        Path(output_path).write_text(buf.getvalue(), encoding="utf-8-sig")
        return len(logs)
