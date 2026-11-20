"""
EduManage Pro - Enterprise Communication Center Repository
Handles CRUD & Dispatch for:
- Configurable Provider Adapters (SMS, Email, WhatsApp Business, In-App)
- Scenario-Based Templates
- In-App Feed (Notifications, Announcements, Notices, Alerts)
- Bulk Campaigns & Immutable Communication Audit Logs
"""

from datetime import date, datetime
import json
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.base import utc_now
from app.models.communication import (
    CommunicationCampaign,
    CommunicationLog,
    CommunicationProviderConfig,
    CommunicationTemplate,
    InAppNotification,
)
from app.models.notice import SchoolNotice
from app.services.communication_adapters import (
    CommunicationAdapterRegistry,
    DeliveryPayload,
    DeliveryRecipient,
)


class _SafeFormatDict(dict):
    def __missing__(self, key):
        return f"{{{key}}}"


class CommunicationRepository:
    """Repository for multi-channel Communication Center & In-App feed."""

    # -------------------------------------------------------------
    # 1. Configurable Provider Adapters
    # -------------------------------------------------------------
    @staticmethod
    def get_providers(
        session: Session,
        channel: Optional[str] = None,
        active_only: bool = False,
    ) -> List[CommunicationProviderConfig]:
        q = session.query(CommunicationProviderConfig).filter(
            CommunicationProviderConfig.is_deleted == False
        )
        if channel and channel != "All":
            q = q.filter(CommunicationProviderConfig.channel == channel)
        if active_only:
            q = q.filter(CommunicationProviderConfig.is_active == True)
        return q.order_by(
            CommunicationProviderConfig.channel.asc(),
            CommunicationProviderConfig.is_default.desc(),
            CommunicationProviderConfig.priority_order.asc(),
        ).all()

    @staticmethod
    def create_provider(
        session: Session,
        provider_name: str,
        channel: str,
        driver_key: str,
        provider_code: Optional[str] = None,
        is_active: bool = True,
        is_default: bool = False,
        priority_order: int = 1,
        sandbox_mode: bool = True,
        sender_id: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        credentials_env_key: Optional[str] = None,
        config_json: str = "{}",
        rate_limit_per_min: int = 60,
        notes: Optional[str] = None,
    ) -> CommunicationProviderConfig:
        # Validate driver exists in pluggable registry
        adapter = CommunicationAdapterRegistry.get_adapter(driver_key)
        if adapter.channel != channel:
            raise ValueError(
                f"Driver '{driver_key}' belongs to channel '{adapter.channel}', not '{channel}'."
            )

        if is_default:
            session.query(CommunicationProviderConfig).filter(
                CommunicationProviderConfig.channel == channel,
                CommunicationProviderConfig.is_deleted == False,
            ).update({"is_default": False})

        code = provider_code.strip().upper() if provider_code else f"PRV-{channel[:3].upper()}-{uuid.uuid4().hex[:5].upper()}"
        cfg = CommunicationProviderConfig(
            provider_code=code,
            provider_name=provider_name.strip(),
            channel=channel,
            driver_key=driver_key,
            is_active=is_active,
            is_default=is_default,
            priority_order=max(1, int(priority_order or 1)),
            sandbox_mode=sandbox_mode,
            sender_id=sender_id.strip() if sender_id else None,
            endpoint_url=endpoint_url.strip() if endpoint_url else None,
            credentials_env_key=credentials_env_key.strip() if credentials_env_key else None,
            config_json=config_json or "{}",
            rate_limit_per_min=max(1, int(rate_limit_per_min or 60)),
            notes=notes,
        )
        session.add(cfg)
        session.commit()
        session.refresh(cfg)
        return cfg

    @staticmethod
    def update_provider(session: Session, provider_id: int, **kwargs) -> Optional[CommunicationProviderConfig]:
        cfg = session.query(CommunicationProviderConfig).filter(
            CommunicationProviderConfig.id == provider_id
        ).first()
        if not cfg:
            return None
        if kwargs.get("is_default"):
            session.query(CommunicationProviderConfig).filter(
                CommunicationProviderConfig.channel == cfg.channel,
                CommunicationProviderConfig.id != cfg.id,
            ).update({"is_default": False})
        for k, v in kwargs.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        session.commit()
        session.refresh(cfg)
        return cfg

    @staticmethod
    def set_default_provider(session: Session, provider_id: int) -> Optional[CommunicationProviderConfig]:
        return CommunicationRepository.update_provider(session, provider_id, is_default=True, is_active=True)

    @staticmethod
    def resolve_provider_for_channel(
        session: Session,
        channel: str,
        provider_id: Optional[int] = None,
    ) -> Optional[CommunicationProviderConfig]:
        if provider_id is not None:
            return session.query(CommunicationProviderConfig).filter(
                CommunicationProviderConfig.id == provider_id,
                CommunicationProviderConfig.channel == channel,
                CommunicationProviderConfig.is_deleted == False,
                CommunicationProviderConfig.is_active == True,
            ).first()
        return session.query(CommunicationProviderConfig).filter(
            CommunicationProviderConfig.channel == channel,
            CommunicationProviderConfig.is_deleted == False,
            CommunicationProviderConfig.is_active == True,
        ).order_by(
            CommunicationProviderConfig.is_default.desc(),
            CommunicationProviderConfig.priority_order.asc(),
            CommunicationProviderConfig.id.asc(),
        ).first()

    @staticmethod
    def test_provider_connection(session: Session, provider_id: int) -> Tuple[bool, str]:
        cfg = session.query(CommunicationProviderConfig).filter(
            CommunicationProviderConfig.id == provider_id
        ).first()
        if not cfg:
            return False, "Provider configuration not found."
        adapter = CommunicationAdapterRegistry.get_adapter(cfg.driver_key)
        cfg_dict = {
            "sender_id": cfg.sender_id,
            "endpoint_url": cfg.endpoint_url,
            "credentials_env_key": cfg.credentials_env_key,
            "config_json": cfg.config_json,
            "sandbox_mode": cfg.sandbox_mode,
        }
        ok, msg = adapter.health_check(cfg_dict)
        cfg.last_tested_at = utc_now()
        cfg.last_test_status = "Healthy" if ok else "Failed"
        cfg.last_test_message = msg[:250]
        session.commit()
        return ok, msg

    # -------------------------------------------------------------
    # 2. Message Templates
    # -------------------------------------------------------------
    @staticmethod
    def get_templates(
        session: Session,
        scenario_type: Optional[str] = None,
        channel: Optional[str] = None,
        active_only: bool = False,
    ) -> List[CommunicationTemplate]:
        q = session.query(CommunicationTemplate).filter(CommunicationTemplate.is_deleted == False)
        if scenario_type and scenario_type != "All":
            q = q.filter(CommunicationTemplate.scenario_type == scenario_type)
        if channel and channel != "All":
            q = q.filter(CommunicationTemplate.channel == channel)
        if active_only:
            q = q.filter(CommunicationTemplate.is_active == True)
        return q.order_by(CommunicationTemplate.scenario_type.asc(), CommunicationTemplate.channel.asc()).all()

    @staticmethod
    def create_template(
        session: Session,
        name: str,
        scenario_type: str,
        channel: str,
        body_template: str,
        subject_template: Optional[str] = None,
        template_code: Optional[str] = None,
        whatsapp_template_name: Optional[str] = None,
        variables_hint: Optional[str] = None,
    ) -> CommunicationTemplate:
        code = template_code.strip().upper() if template_code else f"TPL-{uuid.uuid4().hex[:6].upper()}"
        tpl = CommunicationTemplate(
            template_code=code,
            name=name.strip(),
            scenario_type=scenario_type,
            channel=channel,
            subject_template=subject_template,
            body_template=body_template,
            whatsapp_template_name=whatsapp_template_name,
            variables_hint=variables_hint,
            is_active=True,
        )
        session.add(tpl)
        session.commit()
        session.refresh(tpl)
        return tpl

    @staticmethod
    def render_template_text(template_str: str, variables: Dict[str, Any]) -> str:
        return (template_str or "").format_map(_SafeFormatDict(variables))

    # -------------------------------------------------------------
    # 3. In-App Notifications, Announcements, Notices & Alerts
    # -------------------------------------------------------------
    @staticmethod
    def get_in_app_feed(
        session: Session,
        item_type: Optional[str] = None,
        scenario_type: Optional[str] = None,
        unread_only: bool = False,
        target_user_id: Optional[int] = None,
        audience: Optional[str] = None,
        limit: int = 200,
    ) -> List[InAppNotification]:
        q = session.query(InAppNotification).options(
            joinedload(InAppNotification.target_class),
            joinedload(InAppNotification.student),
        ).filter(InAppNotification.is_deleted == False)

        if item_type and item_type != "All":
            q = q.filter(InAppNotification.item_type == item_type)
        if scenario_type and scenario_type != "All":
            q = q.filter(InAppNotification.scenario_type == scenario_type)
        if unread_only:
            q = q.filter(InAppNotification.is_read == False)
        if target_user_id is not None:
            q = q.filter(
                or_(
                    InAppNotification.target_user_id == target_user_id,
                    InAppNotification.target_user_id.is_(None),
                )
            )
        if audience and audience != "All":
            q = q.filter(
                or_(
                    InAppNotification.target_audience == audience,
                    InAppNotification.target_audience == "All",
                )
            )
        return q.order_by(
            InAppNotification.is_pinned.desc(),
            InAppNotification.created_at.desc(),
            InAppNotification.id.desc(),
        ).limit(limit).all()

    @staticmethod
    def create_in_app_item(
        session: Session,
        title: str,
        message: str,
        item_type: str = "Notification",
        scenario_type: str = "Custom",
        severity: str = "Info",
        target_audience: str = "All",
        target_user_id: Optional[int] = None,
        target_class_id: Optional[int] = None,
        student_id: Optional[int] = None,
        is_pinned: bool = False,
        action_module: Optional[str] = None,
        created_by: str = "admin",
        sync_to_notice_board: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        commit: bool = True,
    ) -> InAppNotification:
        ref = f"COM-{item_type[:3].upper()}-{uuid.uuid4().hex[:6].upper()}"
        linked_notice_id = None

        if sync_to_notice_board or item_type == "Notice":
            notice_ref = f"CIR-{date.today().year}/{uuid.uuid4().hex[:4].upper()}"
            priority = "Urgent" if severity == "Critical" else ("Important" if severity == "Warning" else "Normal")
            notice = SchoolNotice(
                reference_no=notice_ref,
                title=title.strip(),
                category=scenario_type if scenario_type in ("Academic", "Exam", "Event", "Holiday") else "General",
                target_audience=target_audience,
                target_class_id=target_class_id,
                priority=priority,
                is_pinned=is_pinned or (severity == "Critical"),
                publish_date=date.today(),
                content=message.strip(),
                status="Published",
                created_by=created_by,
            )
            session.add(notice)
            session.flush()
            linked_notice_id = notice.id

        item = InAppNotification(
            reference_no=ref,
            item_type=item_type,
            scenario_type=scenario_type,
            severity=severity,
            title=title.strip(),
            message=message.strip(),
            target_audience=target_audience,
            target_user_id=target_user_id,
            target_class_id=target_class_id,
            student_id=student_id,
            school_notice_id=linked_notice_id,
            is_pinned=is_pinned or (severity == "Critical"),
            is_read=False,
            action_module=action_module,
            metadata_json=json.dumps(metadata or {}),
            created_by=created_by,
        )
        session.add(item)
        session.flush()
        if commit:
            session.commit()
            session.refresh(item)
        return item

    @staticmethod
    def mark_in_app_read(session: Session, notif_id: int) -> Optional[InAppNotification]:
        item = session.query(InAppNotification).filter(InAppNotification.id == notif_id).first()
        if not item:
            return None
        item.is_read = True
        item.read_at = utc_now()
        session.commit()
        session.refresh(item)
        return item

    @staticmethod
    def mark_all_in_app_read(session: Session, item_type: Optional[str] = None) -> int:
        q = session.query(InAppNotification).filter(
            InAppNotification.is_deleted == False,
            InAppNotification.is_read == False,
        )
        if item_type and item_type != "All":
            q = q.filter(InAppNotification.item_type == item_type)
        updated = q.update({"is_read": True, "read_at": utc_now()})
        session.commit()
        return int(updated or 0)

    # -------------------------------------------------------------
    # 4. Unified Multi-Channel Dispatch & Complete Communication Logs
    # -------------------------------------------------------------
    @staticmethod
    def create_campaign(
        session: Session,
        title: str,
        scenario_type: str,
        channels: List[str],
        target_summary: str = "",
        triggered_by: str = "admin",
        commit: bool = False,
    ) -> CommunicationCampaign:
        camp = CommunicationCampaign(
            campaign_code=f"CMP-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}",
            title=title.strip(),
            scenario_type=scenario_type,
            channels_json=json.dumps(list(channels)),
            target_summary=target_summary,
            status="Running",
            triggered_by=triggered_by,
        )
        session.add(camp)
        session.flush()
        if commit:
            session.commit()
            session.refresh(camp)
        return camp

    @staticmethod
    def send_message(
        session: Session,
        channel: str,
        recipient_name: str,
        recipient_contact: str,
        message_body: str,
        subject: Optional[str] = None,
        scenario_type: str = "Custom",
        recipient_type: str = "Guardian",
        recipient_id: Optional[int] = None,
        student_id: Optional[int] = None,
        provider_id: Optional[int] = None,
        template_id: Optional[int] = None,
        whatsapp_template_name: Optional[str] = None,
        campaign_id: Optional[int] = None,
        in_app_item_type: str = "Notification",
        severity: str = "Info",
        action_module: Optional[str] = None,
        triggered_by: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
        commit: bool = True,
    ) -> CommunicationLog:
        """Dispatches one message through configured provider adapter & persists an immutable CommunicationLog."""
        in_app_id = None
        provider_cfg = CommunicationRepository.resolve_provider_for_channel(session, channel, provider_id=provider_id)

        if channel == "InApp":
            in_app = CommunicationRepository.create_in_app_item(
                session,
                title=subject or f"{scenario_type}",
                message=message_body,
                item_type=in_app_item_type,
                scenario_type=scenario_type,
                severity=severity,
                target_audience=recipient_type if recipient_type in ("All", "Students", "Parents", "Teachers", "Staff") else "All",
                student_id=student_id,
                is_pinned=(severity == "Critical"),
                action_module=action_module,
                created_by=triggered_by,
                sync_to_notice_board=(in_app_item_type == "Notice"),
                metadata=metadata,
                commit=False,
            )
            in_app_id = in_app.id
            driver_key = provider_cfg.driver_key if provider_cfg else "in_app_feed"
            provider_name = provider_cfg.provider_name if provider_cfg else "Built-in In-App Feed"
            adapter = CommunicationAdapterRegistry.get_adapter(driver_key)
            cfg_dict = {"sandbox_mode": False}
            res = adapter.dispatch(
                DeliveryRecipient(name=recipient_name, contact=recipient_contact or "in-app", recipient_type=recipient_type, recipient_id=recipient_id),
                DeliveryPayload(subject=subject, body=message_body, scenario_type=scenario_type, metadata=metadata or {}),
                cfg_dict,
            )
        else:
            if not provider_cfg:
                log = CommunicationLog(
                    log_code=f"LOG-{uuid.uuid4().hex[:10].upper()}",
                    campaign_id=campaign_id,
                    provider_config_id=None,
                    template_id=template_id,
                    channel=channel,
                    driver_used="unconfigured",
                    provider_name=f"No Active {channel} Provider",
                    scenario_type=scenario_type,
                    recipient_type=recipient_type,
                    recipient_id=recipient_id,
                    recipient_name=recipient_name,
                    recipient_contact=recipient_contact or "-",
                    subject=subject,
                    message_body=message_body,
                    status="Failed",
                    error_message=f"No active {channel} provider adapter configured.",
                    triggered_by=triggered_by,
                    metadata_json=json.dumps(metadata or {}),
                )
                session.add(log)
                session.flush()
                if commit:
                    session.commit()
                    session.refresh(log)
                return log

            adapter = CommunicationAdapterRegistry.get_adapter(provider_cfg.driver_key)
            cfg_dict = {
                "sender_id": provider_cfg.sender_id,
                "endpoint_url": provider_cfg.endpoint_url,
                "credentials_env_key": provider_cfg.credentials_env_key,
                "config_json": provider_cfg.config_json,
                "sandbox_mode": provider_cfg.sandbox_mode,
            }
            res = adapter.dispatch(
                DeliveryRecipient(
                    name=recipient_name,
                    contact=recipient_contact,
                    recipient_type=recipient_type,
                    recipient_id=recipient_id,
                ),
                DeliveryPayload(
                    subject=subject,
                    body=message_body,
                    scenario_type=scenario_type,
                    whatsapp_template_name=whatsapp_template_name,
                    metadata=metadata or {},
                ),
                cfg_dict,
            )
            driver_key = provider_cfg.driver_key
            provider_name = provider_cfg.provider_name

        log = CommunicationLog(
            log_code=f"LOG-{uuid.uuid4().hex[:10].upper()}",
            campaign_id=campaign_id,
            provider_config_id=provider_cfg.id if provider_cfg else None,
            template_id=template_id,
            in_app_notification_id=in_app_id,
            channel=channel,
            driver_used=driver_key,
            provider_name=provider_name,
            scenario_type=scenario_type,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            recipient_contact=recipient_contact or "-",
            subject=subject,
            message_body=message_body,
            status=res.status,
            external_message_id=res.external_message_id,
            error_message=res.error_message,
            attempt_count=1,
            sent_at=utc_now(),
            delivered_at=utc_now() if res.status == "Delivered" else None,
            triggered_by=triggered_by,
            metadata_json=json.dumps(metadata or {}),
        )
        session.add(log)
        session.flush()
        if commit:
            session.commit()
            session.refresh(log)
        return log

    @staticmethod
    def retry_failed_log(session: Session, log_id: int, actor_username: str = "admin") -> Optional[CommunicationLog]:
        orig = session.query(CommunicationLog).filter(CommunicationLog.id == log_id).first()
        if not orig:
            return None
        provider_cfg = CommunicationRepository.resolve_provider_for_channel(
            session, orig.channel, provider_id=orig.provider_config_id
        )
        if not provider_cfg:
            raise ValueError(f"No active provider available for channel '{orig.channel}'.")
        adapter = CommunicationAdapterRegistry.get_adapter(provider_cfg.driver_key)
        res = adapter.dispatch(
            DeliveryRecipient(
                name=orig.recipient_name,
                contact=orig.recipient_contact,
                recipient_type=orig.recipient_type,
                recipient_id=orig.recipient_id,
            ),
            DeliveryPayload(subject=orig.subject, body=orig.message_body, scenario_type=orig.scenario_type),
            {
                "sender_id": provider_cfg.sender_id,
                "endpoint_url": provider_cfg.endpoint_url,
                "credentials_env_key": provider_cfg.credentials_env_key,
                "config_json": provider_cfg.config_json,
                "sandbox_mode": provider_cfg.sandbox_mode,
            },
        )
        orig.attempt_count = int(orig.attempt_count or 1) + 1
        orig.status = res.status
        orig.external_message_id = res.external_message_id or orig.external_message_id
        orig.error_message = res.error_message
        orig.provider_config_id = provider_cfg.id
        orig.driver_used = provider_cfg.driver_key
        orig.provider_name = provider_cfg.provider_name
        orig.sent_at = utc_now()
        session.commit()
        session.refresh(orig)
        return orig

    @staticmethod
    def get_communication_logs(
        session: Session,
        channel: Optional[str] = None,
        scenario_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 300,
    ) -> List[CommunicationLog]:
        q = session.query(CommunicationLog).options(
            joinedload(CommunicationLog.provider_config),
            joinedload(CommunicationLog.campaign),
        ).filter(CommunicationLog.is_deleted == False)

        if channel and channel != "All":
            q = q.filter(CommunicationLog.channel == channel)
        if scenario_type and scenario_type != "All":
            q = q.filter(CommunicationLog.scenario_type == scenario_type)
        if status and status != "All":
            q = q.filter(CommunicationLog.status == status)
        if search:
            pat = f"%{search.strip()}%"
            q = q.filter(
                or_(
                    CommunicationLog.log_code.ilike(pat),
                    CommunicationLog.recipient_name.ilike(pat),
                    CommunicationLog.recipient_contact.ilike(pat),
                    CommunicationLog.message_body.ilike(pat),
                    CommunicationLog.provider_name.ilike(pat),
                )
            )
        return q.order_by(CommunicationLog.sent_at.desc(), CommunicationLog.id.desc()).limit(limit).all()

    @staticmethod
    def get_campaigns(session: Session, limit: int = 100) -> List[CommunicationCampaign]:
        return session.query(CommunicationCampaign).filter(
            CommunicationCampaign.is_deleted == False
        ).order_by(CommunicationCampaign.id.desc()).limit(limit).all()

    @staticmethod
    def get_communication_stats(session: Session) -> Dict[str, Any]:
        unread_inapp = session.query(InAppNotification).filter(
            InAppNotification.is_deleted == False,
            InAppNotification.is_read == False,
        ).count()
        total_inapp = session.query(InAppNotification).filter(
            InAppNotification.is_deleted == False
        ).count()
        active_providers = session.query(CommunicationProviderConfig).filter(
            CommunicationProviderConfig.is_deleted == False,
            CommunicationProviderConfig.is_active == True,
        ).count()

        logs = session.query(CommunicationLog).filter(CommunicationLog.is_deleted == False).all()
        total_logs = len(logs)
        sent_ok = sum(1 for l in logs if l.status in ("Sent", "Delivered", "Read"))
        failed_logs = sum(1 for l in logs if l.status == "Failed")
        emergency_count = sum(1 for l in logs if l.scenario_type == "Emergency Notification")
        success_rate = round((sent_ok / total_logs) * 100.0, 1) if total_logs > 0 else 100.0

        return {
            "unread_inapp": unread_inapp,
            "total_inapp": total_inapp,
            "active_providers": active_providers,
            "total_logs": total_logs,
            "sent_ok": sent_ok,
            "failed_logs": failed_logs,
            "emergency_count": emergency_count,
            "success_rate": success_rate,
        }
