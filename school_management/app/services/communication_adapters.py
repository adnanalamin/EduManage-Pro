"""
EduManage Pro - Pluggable Communication Provider Adapter Architecture
Defines abstract provider interfaces and interchangeable adapter implementations for:
- SMS (Twilio, SSL Wireless, Generic HTTP Webhook, Sandbox)
- Email (SMTP, SendGrid API, Generic Email Webhook, Sandbox)
- WhatsApp Business (Meta Cloud API, Twilio WhatsApp, Generic Webhook, Sandbox)
- In-App Delivery

No provider vendor is hard-coded in business workflows; custom adapters can be registered
at runtime via CommunicationAdapterRegistry.register_adapter().
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, List, Optional, Tuple, Type
import urllib.error
import urllib.parse
import urllib.request
import uuid


@dataclass
class DeliveryRecipient:
    name: str
    contact: str  # Phone number, E.164 WhatsApp, email address, or user identifier
    recipient_type: str = "Guardian"
    recipient_id: Optional[int] = None


@dataclass
class DeliveryPayload:
    subject: Optional[str]
    body: str
    scenario_type: str = "Custom"
    whatsapp_template_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeliveryResult:
    success: bool
    status: str  # Sent, Delivered, Failed, Skipped
    external_message_id: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)


class BaseCommunicationAdapter(ABC):
    """Abstract interface that every SMS, Email, WhatsApp Business, or In-App adapter implements."""

    channel: str = ""
    driver_key: str = ""
    driver_label: str = ""
    description: str = ""

    @staticmethod
    def resolve_credential(config: Dict[str, Any]) -> str:
        """Resolve secret token/password from referenced environment variable cleanly without hardcoding."""
        env_key = (config.get("credentials_env_key") or "").strip()
        if env_key:
            val = os.getenv(env_key, "").strip()
            if val:
                return val
        return str(config.get("runtime_secret") or "").strip()

    @staticmethod
    def parse_extra_config(config: Dict[str, Any]) -> Dict[str, Any]:
        raw = config.get("config_json")
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str) and raw.strip():
            try:
                return json.loads(raw)
            except Exception:
                return {}
        return {}

    @abstractmethod
    def dispatch(
        self,
        recipient: DeliveryRecipient,
        payload: DeliveryPayload,
        config: Dict[str, Any],
    ) -> DeliveryResult:
        """Send one message using the configured channel provider."""

    @abstractmethod
    def health_check(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate configuration and verify adapter readiness."""


# =========================================================================
# 1. SMS Provider Adapters (Abstract SMS Base + Pluggable Vendors)
# =========================================================================
class SMSProviderAdapter(BaseCommunicationAdapter):
    channel = "SMS"

    def _validate_phone(self, phone: str) -> str:
        cleaned = (phone or "").strip()
        if not cleaned or len(cleaned) < 5:
            raise ValueError(f"Invalid SMS recipient phone number: '{phone}'")
        return cleaned

    def health_check(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        if config.get("sandbox_mode", True):
            return True, f"{self.driver_label} ready in Sandbox mode (Sender: {config.get('sender_id') or 'SchoolSMS'})."
        if not config.get("endpoint_url"):
            return False, "Endpoint URL is required when Sandbox mode is disabled."
        if not self.resolve_credential(config):
            return False, f"Missing environment credential '{config.get('credentials_env_key') or 'unset'}'."
        return True, f"{self.driver_label} live configuration verified."


class TwilioSMSAdapter(SMSProviderAdapter):
    driver_key = "twilio_sms"
    driver_label = "Twilio Programmable SMS"
    description = "REST API adapter compatible with Twilio Messages endpoint."

    def dispatch(self, recipient: DeliveryRecipient, payload: DeliveryPayload, config: Dict[str, Any]) -> DeliveryResult:
        try:
            to_phone = self._validate_phone(recipient.contact)
        except ValueError as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))

        if config.get("sandbox_mode", True):
            return DeliveryResult(
                success=True,
                status="Sent",
                external_message_id=f"SM-SBX-{uuid.uuid4().hex[:12].upper()}",
                raw_response={"mode": "sandbox", "driver": self.driver_key, "to": to_phone},
            )

        endpoint = (config.get("endpoint_url") or "").strip()
        token = self.resolve_credential(config)
        extra = self.parse_extra_config(config)
        account_sid = extra.get("account_sid", "")
        if not endpoint or not token or not account_sid:
            return DeliveryResult(
                success=False,
                status="Failed",
                error_message="Twilio live mode requires endpoint_url, config_json.account_sid, and credentials_env_key.",
            )

        data = urllib.parse.urlencode(
            {
                "To": to_phone,
                "From": config.get("sender_id") or extra.get("from_number", ""),
                "Body": payload.body,
            }
        ).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, method="POST")
        import base64
        auth = base64.b64encode(f"{account_sid}:{token}".encode("utf-8")).decode("ascii")
        req.add_header("Authorization", f"Basic {auth}")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return DeliveryResult(success=True, status="Sent", external_message_id=body.get("sid"), raw_response=body)
        except Exception as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))


class SSLWirelessSMSAdapter(SMSProviderAdapter):
    driver_key = "ssl_wireless_sms"
    driver_label = "SSL Wireless / Local SMS Gateway"
    description = "JSON REST adapter for regional telecom SMS aggregators (SSL Wireless, BulkSMS, etc.)."

    def dispatch(self, recipient: DeliveryRecipient, payload: DeliveryPayload, config: Dict[str, Any]) -> DeliveryResult:
        try:
            to_phone = self._validate_phone(recipient.contact)
        except ValueError as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))

        if config.get("sandbox_mode", True):
            return DeliveryResult(
                success=True,
                status="Sent",
                external_message_id=f"SSL-SBX-{uuid.uuid4().hex[:10].upper()}",
                raw_response={"mode": "sandbox", "driver": self.driver_key, "msisdn": to_phone},
            )

        endpoint = (config.get("endpoint_url") or "").strip()
        api_token = self.resolve_credential(config)
        if not endpoint or not api_token:
            return DeliveryResult(success=False, status="Failed", error_message="Missing SMS gateway endpoint or API token.")
        body_json = json.dumps(
            {
                "api_token": api_token,
                "sid": config.get("sender_id") or "EDUMANAGE",
                "msisdn": to_phone,
                "sms": payload.body,
                "csms_id": uuid.uuid4().hex[:16],
            }
        ).encode("utf-8")
        req = urllib.request.Request(endpoint, data=body_json, method="POST", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return DeliveryResult(success=True, status="Sent", external_message_id=str(res.get("smsinfo", "")), raw_response=res)
        except Exception as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))


class GenericWebhookSMSAdapter(SMSProviderAdapter):
    driver_key = "generic_webhook_sms"
    driver_label = "Generic HTTP / Webhook SMS"
    description = "Configurable JSON webhook adapter for any custom SMS provider."

    def dispatch(self, recipient: DeliveryRecipient, payload: DeliveryPayload, config: Dict[str, Any]) -> DeliveryResult:
        try:
            to_phone = self._validate_phone(recipient.contact)
        except ValueError as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))

        if config.get("sandbox_mode", True):
            return DeliveryResult(
                success=True,
                status="Sent",
                external_message_id=f"WH-SMS-{uuid.uuid4().hex[:10].upper()}",
                raw_response={"mode": "sandbox", "to": to_phone},
            )

        endpoint = (config.get("endpoint_url") or "").strip()
        if not endpoint:
            return DeliveryResult(success=False, status="Failed", error_message="Webhook URL missing.")
        headers = {"Content-Type": "application/json"}
        token = self.resolve_credential(config)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = json.dumps(
            {
                "sender_id": config.get("sender_id"),
                "to": to_phone,
                "recipient_name": recipient.name,
                "message": payload.body,
                "scenario": payload.scenario_type,
            }
        ).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return DeliveryResult(
                    success=200 <= resp.status < 300,
                    status="Sent",
                    external_message_id=f"WH-{uuid.uuid4().hex[:10].upper()}",
                )
        except Exception as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))


# =========================================================================
# 2. Email Provider Adapters (Abstract Email Base + SMTP / API Drivers)
# =========================================================================
class EmailProviderAdapter(BaseCommunicationAdapter):
    channel = "Email"

    def _validate_email(self, email: str) -> str:
        cleaned = (email or "").strip()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
            raise ValueError(f"Invalid Email address: '{email}'")
        return cleaned

    def health_check(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        if config.get("sandbox_mode", True):
            return True, f"{self.driver_label} ready in Sandbox mode (From: {config.get('sender_id') or 'noreply@school.local'})."
        if not config.get("endpoint_url"):
            return False, "SMTP host or Email API endpoint is required in Live mode."
        return True, f"{self.driver_label} live configuration present."


class SMTPEmailAdapter(EmailProviderAdapter):
    driver_key = "smtp_email"
    driver_label = "Standard SMTP / TLS Email"
    description = "Configurable SMTP relay adapter supporting TLS/STARTTLS."

    def dispatch(self, recipient: DeliveryRecipient, payload: DeliveryPayload, config: Dict[str, Any]) -> DeliveryResult:
        try:
            to_email = self._validate_email(recipient.contact)
        except ValueError as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))

        if config.get("sandbox_mode", True):
            return DeliveryResult(
                success=True,
                status="Sent",
                external_message_id=f"SMTP-SBX-{uuid.uuid4().hex[:12].upper()}",
                raw_response={"mode": "sandbox", "to": to_email, "subject": payload.subject},
            )

        extra = self.parse_extra_config(config)
        host = (config.get("endpoint_url") or extra.get("host") or "").strip()
        port = int(extra.get("port", 587))
        username = extra.get("username") or config.get("sender_id") or ""
        password = self.resolve_credential(config)
        if not host:
            return DeliveryResult(success=False, status="Failed", error_message="SMTP host not configured.")

        msg = EmailMessage()
        msg["Subject"] = payload.subject or f"School Notification ({payload.scenario_type})"
        msg["From"] = config.get("sender_id") or username or "noreply@school.local"
        msg["To"] = to_email
        msg.set_content(payload.body)

        try:
            with smtplib.SMTP(host, port, timeout=10) as server:
                if extra.get("use_tls", True):
                    server.starttls()
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
            return DeliveryResult(success=True, status="Sent", external_message_id=f"SMTP-{uuid.uuid4().hex[:12].upper()}")
        except Exception as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))


class SendGridEmailAdapter(EmailProviderAdapter):
    driver_key = "sendgrid_email"
    driver_label = "SendGrid / REST Email API"
    description = "HTTP REST Email API adapter for SendGrid or compatible transactional mailers."

    def dispatch(self, recipient: DeliveryRecipient, payload: DeliveryPayload, config: Dict[str, Any]) -> DeliveryResult:
        try:
            to_email = self._validate_email(recipient.contact)
        except ValueError as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))

        if config.get("sandbox_mode", True):
            return DeliveryResult(
                success=True,
                status="Sent",
                external_message_id=f"SG-SBX-{uuid.uuid4().hex[:12].upper()}",
                raw_response={"mode": "sandbox", "to": to_email},
            )

        endpoint = (config.get("endpoint_url") or "https://api.sendgrid.com/v3/mail/send").strip()
        token = self.resolve_credential(config)
        if not token:
            return DeliveryResult(success=False, status="Failed", error_message="Missing SendGrid API key env var.")
        body = json.dumps(
            {
                "personalizations": [{"to": [{"email": to_email, "name": recipient.name}]}],
                "from": {"email": config.get("sender_id") or "noreply@school.local"},
                "subject": payload.subject or payload.scenario_type,
                "content": [{"type": "text/plain", "value": payload.body}],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=body,
            method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                msg_id = resp.headers.get("X-Message-Id") or f"SG-{uuid.uuid4().hex[:10].upper()}"
                return DeliveryResult(success=True, status="Sent", external_message_id=msg_id)
        except Exception as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))


# =========================================================================
# 3. WhatsApp Business Adapters (Meta Cloud / Twilio / Webhook)
# =========================================================================
class WhatsAppBusinessAdapter(BaseCommunicationAdapter):
    channel = "WhatsApp"

    def _validate_whatsapp(self, phone: str) -> str:
        cleaned = (phone or "").strip().replace(" ", "")
        if not cleaned or len(cleaned) < 6:
            raise ValueError(f"Invalid WhatsApp Business phone number: '{phone}'")
        return cleaned

    def health_check(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        if config.get("sandbox_mode", True):
            return True, f"{self.driver_label} ready in Sandbox mode (Phone ID/Sender: {config.get('sender_id') or 'WABA-DEFAULT'})."
        if not config.get("endpoint_url") or not self.resolve_credential(config):
            return False, "WhatsApp Cloud API endpoint URL & access token environment variable are required."
        return True, f"{self.driver_label} live configuration verified."


class MetaWhatsAppCloudAdapter(WhatsAppBusinessAdapter):
    driver_key = "meta_whatsapp_cloud"
    driver_label = "Meta WhatsApp Business Cloud API"
    description = "Official Graph API adapter for WhatsApp Business Cloud messaging & approved templates."

    def dispatch(self, recipient: DeliveryRecipient, payload: DeliveryPayload, config: Dict[str, Any]) -> DeliveryResult:
        try:
            to_num = self._validate_whatsapp(recipient.contact)
        except ValueError as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))

        if config.get("sandbox_mode", True):
            return DeliveryResult(
                success=True,
                status="Sent",
                external_message_id=f"wamid.SBX.{uuid.uuid4().hex[:12].upper()}",
                raw_response={"mode": "sandbox", "to": to_num, "template": payload.whatsapp_template_name},
            )

        endpoint = (config.get("endpoint_url") or "").strip()
        token = self.resolve_credential(config)
        if not endpoint or not token:
            return DeliveryResult(success=False, status="Failed", error_message="Missing Meta Cloud API endpoint/token.")

        req_payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to_num,
            "type": "text",
            "text": {"preview_url": False, "body": payload.body},
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(req_payload).encode("utf-8"),
            method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                msg_id = (data.get("messages") or [{}])[0].get("id")
                return DeliveryResult(success=True, status="Sent", external_message_id=msg_id, raw_response=data)
        except Exception as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))


class TwilioWhatsAppAdapter(WhatsAppBusinessAdapter):
    driver_key = "twilio_whatsapp"
    driver_label = "Twilio WhatsApp Business BSP"
    description = "Twilio Business Solution Provider WhatsApp adapter."

    def dispatch(self, recipient: DeliveryRecipient, payload: DeliveryPayload, config: Dict[str, Any]) -> DeliveryResult:
        try:
            to_num = self._validate_whatsapp(recipient.contact)
        except ValueError as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))

        if config.get("sandbox_mode", True):
            return DeliveryResult(
                success=True,
                status="Sent",
                external_message_id=f"WA-TW-{uuid.uuid4().hex[:12].upper()}",
                raw_response={"mode": "sandbox", "to": f"whatsapp:{to_num}"},
            )

        return GenericWebhookWhatsAppAdapter().dispatch(recipient, payload, config)


class GenericWebhookWhatsAppAdapter(WhatsAppBusinessAdapter):
    driver_key = "generic_webhook_whatsapp"
    driver_label = "Generic WhatsApp BSP Webhook"
    description = "Custom HTTP webhook adapter for third-party WhatsApp Business BSPs (360dialog, Gupshup, WATI)."

    def dispatch(self, recipient: DeliveryRecipient, payload: DeliveryPayload, config: Dict[str, Any]) -> DeliveryResult:
        try:
            to_num = self._validate_whatsapp(recipient.contact)
        except ValueError as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))

        if config.get("sandbox_mode", True):
            return DeliveryResult(
                success=True,
                status="Sent",
                external_message_id=f"WA-WH-{uuid.uuid4().hex[:10].upper()}",
                raw_response={"mode": "sandbox", "to": to_num},
            )

        endpoint = (config.get("endpoint_url") or "").strip()
        if not endpoint:
            return DeliveryResult(success=False, status="Failed", error_message="WhatsApp webhook URL not configured.")
        headers = {"Content-Type": "application/json"}
        token = self.resolve_credential(config)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = json.dumps(
            {
                "phone": to_num,
                "sender": config.get("sender_id"),
                "template": payload.whatsapp_template_name,
                "message": payload.body,
            }
        ).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return DeliveryResult(success=200 <= resp.status < 300, status="Sent", external_message_id=f"WABSP-{uuid.uuid4().hex[:8].upper()}")
        except Exception as exc:
            return DeliveryResult(success=False, status="Failed", error_message=str(exc))


# =========================================================================
# 4. In-App Notification Adapter
# =========================================================================
class InAppAdapter(BaseCommunicationAdapter):
    channel = "InApp"
    driver_key = "in_app_feed"
    driver_label = "EduManage In-App Feed"
    description = "Delivers Notifications, Announcements, Notices & Alerts directly inside the desktop app."

    def dispatch(self, recipient: DeliveryRecipient, payload: DeliveryPayload, config: Dict[str, Any]) -> DeliveryResult:
        return DeliveryResult(
            success=True,
            status="Delivered",
            external_message_id=f"INAPP-{uuid.uuid4().hex[:10].upper()}",
            raw_response={"delivered_at": datetime.now(timezone.utc).isoformat()},
        )

    def health_check(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        return True, "Built-in In-App notification engine is active."


# =========================================================================
# 5. Dynamic Pluggable Adapter Registry
# =========================================================================
class CommunicationAdapterRegistry:
    """Central pluggable registry resolving provider adapters dynamically by driver_key."""

    _adapters: Dict[str, BaseCommunicationAdapter] = {
        "in_app_feed": InAppAdapter(),
        "twilio_sms": TwilioSMSAdapter(),
        "ssl_wireless_sms": SSLWirelessSMSAdapter(),
        "generic_webhook_sms": GenericWebhookSMSAdapter(),
        "smtp_email": SMTPEmailAdapter(),
        "sendgrid_email": SendGridEmailAdapter(),
        "meta_whatsapp_cloud": MetaWhatsAppCloudAdapter(),
        "twilio_whatsapp": TwilioWhatsAppAdapter(),
        "generic_webhook_whatsapp": GenericWebhookWhatsAppAdapter(),
    }

    @classmethod
    def register_adapter(cls, adapter: BaseCommunicationAdapter) -> None:
        """Allow registering new or custom provider adapters at runtime without altering core code."""
        if not isinstance(adapter, BaseCommunicationAdapter):
            raise TypeError("Adapter must inherit from BaseCommunicationAdapter.")
        cls._adapters[adapter.driver_key] = adapter

    @classmethod
    def get_adapter(cls, driver_key: str) -> BaseCommunicationAdapter:
        adapter = cls._adapters.get(driver_key)
        if not adapter:
            raise ValueError(f"Communication provider driver '{driver_key}' is not registered.")
        return adapter

    @classmethod
    def list_drivers(cls, channel: Optional[str] = None) -> List[Dict[str, str]]:
        out = []
        for adp in cls._adapters.values():
            if channel and adp.channel != channel:
                continue
            out.append(
                {
                    "driver_key": adp.driver_key,
                    "channel": adp.channel,
                    "driver_label": adp.driver_label,
                    "description": adp.description,
                }
            )
        return sorted(out, key=lambda d: (d["channel"], d["driver_label"]))
