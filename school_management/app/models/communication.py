"""
EduManage Pro - Enterprise Communication Center ORM Models
Covers In-App Communication (Notifications, Announcements, Notices, Alerts),
Configurable Multi-Provider Adapter Configs (SMS, Email, WhatsApp Business, InApp),
Scenario Message Templates, Broadcast Campaigns, and Complete Audit Communication Logs.
"""

from datetime import datetime
from typing import Tuple

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, utc_now


COMM_CHANNELS: Tuple[str, ...] = ("InApp", "SMS", "Email", "WhatsApp")
INAPP_ITEM_TYPES: Tuple[str, ...] = ("Notification", "Announcement", "Notice", "Alert")
COMM_SEVERITIES: Tuple[str, ...] = ("Info", "Success", "Warning", "Critical")
COMM_SCENARIO_TYPES: Tuple[str, ...] = (
    "Attendance Alert",
    "Fee Due Alert",
    "Result Notification",
    "Admission Notification",
    "Emergency Notification",
    "Announcement",
    "Notice",
    "Custom",
)
DELIVERY_STATUSES: Tuple[str, ...] = ("Pending", "Queued", "Sent", "Delivered", "Read", "Failed", "Skipped")


class CommunicationProviderConfig(Base, TimestampMixin, SoftDeleteMixin):
    """
    Database-stored configurable provider profile for SMS, Email, WhatsApp Business, or In-App delivery.
    No provider is hard-coded; admins can add, prioritize, switch defaults, or toggle sandbox/live modes.
    """

    __tablename__ = "communication_provider_configs"

    provider_code = Column(String(40), unique=True, nullable=False, index=True)
    provider_name = Column(String(120), nullable=False)
    channel = Column(String(20), nullable=False, index=True)  # InApp, SMS, Email, WhatsApp
    driver_key = Column(String(60), nullable=False, index=True)  # Matches CommunicationAdapterRegistry key
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_default = Column(Boolean, default=False, nullable=False, index=True)
    priority_order = Column(Integer, default=1, nullable=False)
    sandbox_mode = Column(Boolean, default=True, nullable=False)

    sender_id = Column(String(120), nullable=True)  # SMS SenderID, Email From, WhatsApp Phone Number ID
    endpoint_url = Column(String(255), nullable=True)  # Gateway API URL or SMTP host:port
    credentials_env_key = Column(String(120), nullable=True)  # Env var storing API key/token/password
    config_json = Column(Text, default="{}", nullable=False)  # Driver-specific non-secret parameters JSON
    rate_limit_per_min = Column(Integer, default=60, nullable=False)

    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    last_test_status = Column(String(40), nullable=True)
    last_test_message = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    logs = relationship("CommunicationLog", back_populates="provider_config")

    __table_args__ = (
        CheckConstraint("channel IN ('InApp', 'SMS', 'Email', 'WhatsApp')", name="ck_comm_provider_channel"),
        CheckConstraint("priority_order >= 1", name="ck_comm_provider_priority"),
        Index("idx_comm_provider_channel_default", "channel", "is_active", "is_default"),
    )

    def __repr__(self):
        return f"<CommunicationProviderConfig(code='{self.provider_code}', channel='{self.channel}', driver='{self.driver_key}')>"


class CommunicationTemplate(Base, TimestampMixin, SoftDeleteMixin):
    """Reusable scenario-aware message template with placeholder substitution tokens."""

    __tablename__ = "communication_templates"

    template_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(140), nullable=False)
    scenario_type = Column(String(40), nullable=False, index=True)
    channel = Column(String(20), nullable=False, index=True)
    subject_template = Column(String(200), nullable=True)
    body_template = Column(Text, nullable=False)
    whatsapp_template_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    variables_hint = Column(String(255), nullable=True)

    __table_args__ = (
        CheckConstraint("channel IN ('InApp', 'SMS', 'Email', 'WhatsApp')", name="ck_comm_template_channel"),
        Index("idx_comm_template_scenario_channel", "scenario_type", "channel"),
    )

    def __repr__(self):
        return f"<CommunicationTemplate(code='{self.template_code}', scenario='{self.scenario_type}', channel='{self.channel}')>"


class InAppNotification(Base, TimestampMixin, SoftDeleteMixin):
    """
    Unified In-App Communication Center Feed supporting:
    - Notifications (personal or event-triggered updates)
    - Announcements (institutional news & updates)
    - Notices (official directives linked optionally with SchoolNotice)
    - Alerts (high-visibility warnings: Attendance Alert, Fee Due Alert, Emergency Alert)
    """

    __tablename__ = "in_app_notifications"

    reference_no = Column(String(50), unique=True, nullable=False, index=True)
    item_type = Column(String(20), default="Notification", nullable=False, index=True)  # Notification, Announcement, Notice, Alert
    scenario_type = Column(String(40), default="Custom", nullable=False, index=True)
    severity = Column(String(20), default="Info", nullable=False, index=True)  # Info, Success, Warning, Critical
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    target_audience = Column(String(40), default="All", nullable=False, index=True)  # All, Students, Parents, Teachers, Staff, Admins, Applicants
    target_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    target_class_id = Column(Integer, ForeignKey("school_classes.id", ondelete="SET NULL"), nullable=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    school_notice_id = Column(Integer, ForeignKey("school_notices.id", ondelete="SET NULL"), nullable=True, index=True)

    is_pinned = Column(Boolean, default=False, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    action_module = Column(String(40), nullable=True)
    metadata_json = Column(Text, default="{}", nullable=False)
    created_by = Column(String(100), default="System", nullable=False)

    target_user = relationship("User")
    target_class = relationship("SchoolClass")
    student = relationship("Student")
    school_notice = relationship("SchoolNotice")

    __table_args__ = (
        CheckConstraint("item_type IN ('Notification', 'Announcement', 'Notice', 'Alert')", name="ck_inapp_item_type"),
        CheckConstraint("severity IN ('Info', 'Success', 'Warning', 'Critical')", name="ck_inapp_severity"),
        Index("idx_inapp_feed_filter", "item_type", "is_read", "created_at"),
    )

    def __repr__(self):
        return f"<InAppNotification(ref='{self.reference_no}', type='{self.item_type}', severity='{self.severity}')>"


class CommunicationCampaign(Base, TimestampMixin, SoftDeleteMixin):
    """Batch broadcast or automated trigger run header."""

    __tablename__ = "communication_campaigns"

    campaign_code = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    scenario_type = Column(String(40), nullable=False, index=True)
    channels_json = Column(String(120), default='["InApp"]', nullable=False)
    target_summary = Column(String(200), nullable=True)
    total_recipients = Column(Integer, default=0, nullable=False)
    sent_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    status = Column(String(30), default="Completed", nullable=False, index=True)
    triggered_by = Column(String(100), default="admin", nullable=False)
    completed_at = Column(DateTime(timezone=True), default=utc_now, nullable=True)

    logs = relationship("CommunicationLog", back_populates="campaign")

    def __repr__(self):
        return f"<CommunicationCampaign(code='{self.campaign_code}', scenario='{self.scenario_type}', sent={self.sent_count})>"


class CommunicationLog(Base, TimestampMixin, SoftDeleteMixin):
    """Complete immutable audit log for every communication dispatched across any channel or adapter."""

    __tablename__ = "communication_logs"

    log_code = Column(String(60), unique=True, nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("communication_campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    provider_config_id = Column(Integer, ForeignKey("communication_provider_configs.id", ondelete="SET NULL"), nullable=True, index=True)
    template_id = Column(Integer, ForeignKey("communication_templates.id", ondelete="SET NULL"), nullable=True, index=True)
    in_app_notification_id = Column(Integer, ForeignKey("in_app_notifications.id", ondelete="SET NULL"), nullable=True, index=True)

    channel = Column(String(20), nullable=False, index=True)
    driver_used = Column(String(60), nullable=False)
    provider_name = Column(String(120), nullable=False)
    scenario_type = Column(String(40), nullable=False, index=True)

    recipient_type = Column(String(30), default="Student", nullable=False, index=True)  # Student, Guardian, Applicant, Teacher, Staff, User, Group
    recipient_id = Column(Integer, nullable=True, index=True)
    recipient_name = Column(String(140), nullable=False)
    recipient_contact = Column(String(160), nullable=False, index=True)

    subject = Column(String(220), nullable=True)
    message_body = Column(Text, nullable=False)
    status = Column(String(20), default="Sent", nullable=False, index=True)  # Pending, Queued, Sent, Delivered, Read, Failed, Skipped
    external_message_id = Column(String(120), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    attempt_count = Column(Integer, default=1, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=utc_now, nullable=True, index=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    triggered_by = Column(String(100), default="system", nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)

    campaign = relationship("CommunicationCampaign", back_populates="logs")
    provider_config = relationship("CommunicationProviderConfig", back_populates="logs")
    template = relationship("CommunicationTemplate")
    in_app_notification = relationship("InAppNotification")

    __table_args__ = (
        CheckConstraint("channel IN ('InApp', 'SMS', 'Email', 'WhatsApp')", name="ck_comm_log_channel"),
        CheckConstraint(
            "status IN ('Pending', 'Queued', 'Sent', 'Delivered', 'Read', 'Failed', 'Skipped')",
            name="ck_comm_log_status",
        ),
        Index("idx_comm_log_channel_status_date", "channel", "status", "sent_at"),
    )

    def __repr__(self):
        return f"<CommunicationLog(code='{self.log_code}', channel='{self.channel}', status='{self.status}')>"
