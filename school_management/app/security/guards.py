"""
EduManage Pro - Enterprise RBAC & Session Authorization Guards
Provides declarative and imperative permission enforcement with automatic
ActivityLog + SecurityAlert emission on unauthorized access attempts.
"""

from functools import wraps
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.config.logging_config import security_logger
from app.security.audit import AuditService
from app.security.session import session as app_session


class PermissionDeniedError(PermissionError):
    """Raised when an unauthenticated or unauthorized actor attempts a protected operation."""


def authorize_action(
    db: Optional[Session] = None,
    actor: Optional[Any] = None,
    *,
    permission_code: str = "",
    module: Optional[str] = None,
    feature: Optional[str] = None,
    action: Optional[str] = None,
    record_ref: Optional[str] = None,
    ip_address: str = "127.0.0.1",
) -> Any:
    """
    Verify active authentication and exact/hierarchical RBAC permission.
    Uses explicit `actor` if provided, otherwise falls back to active desktop `app_session`.
    Logs denied attempts into ActivityLog + SecurityAlert when `db` is supplied.
    """
    resolved_actor = actor if actor is not None else (
        app_session.current_user if app_session.is_authenticated else None
    )
    if resolved_actor is None:
        if db is not None:
            AuditService.record(
                db,
                action="UNAUTHENTICATED_ACCESS_BLOCKED",
                module=(module or "SECURITY"),
                description=f"Blocked unauthenticated access to {permission_code or f'{module}.{action}'}.",
                record_label=record_ref,
                severity="SECURITY",
                ip_address=ip_address,
                is_admin_action=False,
            )
            AuditService.raise_alert(
                db,
                alert_type="UNAUTHENTICATED_ACCESS_ATTEMPT",
                severity="HIGH",
                module=(module or "SECURITY"),
                description=f"Unauthenticated attempt to invoke protected operation ({permission_code or f'{module}.{action}'}).",
                ip_address=ip_address,
            )
            db.commit()
        raise PermissionDeniedError("Authentication required to perform this action.")

    # Verify DB-level session validity if validating the desktop singleton session
    if actor is None and db is not None and not app_session.validate_against_db(db):
        raise PermissionDeniedError("Session has expired or been revoked. Please sign in again.")

    allowed = resolved_actor.has_permission(
        permission_code,
        module=module,
        feature=feature,
        action=action,
    )
    if not allowed:
        target = permission_code or f"{module or '*'}.{feature or '*'}.{action or '*'}"
        uname = getattr(resolved_actor, "username", "unknown")
        security_logger.warning(f"Permission denied for user '{uname}' on '{target}'")
        if db is not None:
            AuditService.record(
                db,
                action="PERMISSION_DENIED",
                module=(module or "SECURITY"),
                description=f"Access denied for user '{uname}' attempting '{target}'.",
                who_user=resolved_actor,
                record_label=record_ref,
                severity="SECURITY",
                ip_address=ip_address,
                is_admin_action=False,
            )
            AuditService.raise_alert(
                db,
                alert_type="PERMISSION_DENIED_ATTEMPT",
                severity="MEDIUM",
                module=(module or "SECURITY"),
                user_id=getattr(resolved_actor, "id", None),
                username=uname,
                description=f"User '{uname}' attempted unauthorized operation '{target}'.",
                ip_address=ip_address,
                evidence={"permission": target, "record": record_ref},
            )
            db.commit()
        raise PermissionDeniedError(f"Permission denied: '{target}' privilege required.")

    return resolved_actor


def require_permission(
    permission_code: str = "",
    *,
    module: Optional[str] = None,
    feature: Optional[str] = None,
    action: Optional[str] = None,
) -> Callable:
    """
    Decorator enforcing RBAC before invoking a service or controller function.
    Looks for optional `db` and `actor_user` / `actor` keyword or positional Session argument.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            db = kwargs.get("db")
            if db is None:
                for arg in args:
                    if isinstance(arg, Session):
                        db = arg
                        break
            actor = kwargs.get("actor_user") or kwargs.get("actor")
            authorize_action(
                db=db,
                actor=actor,
                permission_code=permission_code,
                module=module,
                feature=feature,
                action=action,
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator
