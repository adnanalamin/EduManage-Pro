"""
EduManage Pro - Communication Center Modals (PySide6)
Covers In-App Compose (Notification/Announcement/Notice/Alert),
Configurable Provider Adapters (SMS/Email/WhatsApp Business/InApp),
Message Templates, and Direct Message Dispatch.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from app.models.communication import (
    COMM_CHANNELS,
    COMM_SCENARIO_TYPES,
    COMM_SEVERITIES,
    INAPP_ITEM_TYPES,
)
from app.repositories.communication_repository import CommunicationRepository
from app.security.session import session as app_session
from app.services.communication_adapters import CommunicationAdapterRegistry


class ComposeInAppDialog(QDialog):
    """Compose an In-App Notification, Announcement, Notice, or Alert."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Compose In-App Notification / Announcement / Notice / Alert")
        self.setMinimumWidth(520)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItems(list(INAPP_ITEM_TYPES))
        form.addRow("Item Type *:", self.type_combo)

        self.scenario_combo = QComboBox()
        self.scenario_combo.addItems(list(COMM_SCENARIO_TYPES))
        form.addRow("Scenario:", self.scenario_combo)

        self.severity_combo = QComboBox()
        self.severity_combo.addItems(list(COMM_SEVERITIES))
        form.addRow("Severity:", self.severity_combo)

        self.audience_combo = QComboBox()
        self.audience_combo.addItems(["All", "Students", "Parents", "Teachers", "Staff", "Admins"])
        form.addRow("Target Audience:", self.audience_combo)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g., Campus Closure Notice / Fee Due Reminder")
        form.addRow("Title *:", self.title_input)

        self.message_input = QTextEdit()
        self.message_input.setMinimumHeight(110)
        self.message_input.setPlaceholderText("Enter full notification, announcement, or alert message...")
        form.addRow("Message *:", self.message_input)

        self.pin_check = QCheckBox("Pin to top of Communication Feed")
        form.addRow("", self.pin_check)

        self.sync_notice_check = QCheckBox("Also publish to Official School Notice Board")
        form.addRow("", self.sync_notice_check)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        title = self.title_input.text().strip()
        msg = self.message_input.toPlainText().strip()
        if not title or not msg:
            QMessageBox.warning(self, "Validation", "Title and Message are required.")
            return
        actor = app_session.current_user.username if app_session.current_user else "admin"
        try:
            CommunicationRepository.send_message(
                self.db,
                channel="InApp",
                recipient_name=f"{self.audience_combo.currentText()} Feed",
                recipient_contact="in-app",
                subject=title,
                message_body=msg,
                scenario_type=self.scenario_combo.currentText(),
                recipient_type=self.audience_combo.currentText(),
                in_app_item_type=self.type_combo.currentText(),
                severity=self.severity_combo.currentText(),
                triggered_by=actor,
            )
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not publish in-app item:\n{exc}")


class ProviderConfigDialog(QDialog):
    """Add or edit a configurable SMS, Email, WhatsApp Business, or In-App provider adapter."""

    def __init__(self, parent=None, db_session=None, provider=None):
        super().__init__(parent)
        self.db = db_session
        self.provider = provider
        self.setWindowTitle("Configure Provider Adapter" if not provider else f"Edit Provider: {provider.provider_name}")
        self.setMinimumWidth(540)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Twilio Primary SMS / Corporate SMTP / Meta WhatsApp")
        form.addRow("Provider Name *:", self.name_input)

        self.channel_combo = QComboBox()
        self.channel_combo.addItems(list(COMM_CHANNELS))
        self.channel_combo.currentTextChanged.connect(self._reload_drivers)
        form.addRow("Channel *:", self.channel_combo)

        self.driver_combo = QComboBox()
        form.addRow("Adapter Driver *:", self.driver_combo)

        self.sender_input = QLineEdit()
        self.sender_input.setPlaceholderText("Sender ID / From Email / WhatsApp Phone Number ID")
        form.addRow("Sender ID / From:", self.sender_input)

        self.endpoint_input = QLineEdit()
        self.endpoint_input.setPlaceholderText("API Endpoint URL or SMTP Host (e.g., smtp.gmail.com)")
        form.addRow("Endpoint / Host:", self.endpoint_input)

        self.env_key_input = QLineEdit()
        self.env_key_input.setPlaceholderText("Env Var Key for Token/Password (e.g., TWILIO_AUTH_TOKEN)")
        form.addRow("Credentials Env Key:", self.env_key_input)

        self.config_json_input = QTextEdit()
        self.config_json_input.setMaximumHeight(80)
        self.config_json_input.setPlainText("{}")
        form.addRow("Extra Config (JSON):", self.config_json_input)

        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 99)
        self.priority_spin.setValue(1)
        form.addRow("Priority Order:", self.priority_spin)

        self.sandbox_check = QCheckBox("Sandbox / Safe Dry-Run Mode (logs without live network call)")
        self.sandbox_check.setChecked(True)
        form.addRow("", self.sandbox_check)

        self.default_check = QCheckBox("Set as Default Provider for this Channel")
        self.default_check.setChecked(True)
        form.addRow("", self.default_check)

        self.active_check = QCheckBox("Active")
        self.active_check.setChecked(True)
        form.addRow("", self.active_check)

        layout.addLayout(form)
        self._reload_drivers(self.channel_combo.currentText())

        if self.provider:
            self.name_input.setText(self.provider.provider_name)
            idx_c = self.channel_combo.findText(self.provider.channel)
            if idx_c >= 0:
                self.channel_combo.setCurrentIndex(idx_c)
            self.channel_combo.setEnabled(False)
            self._reload_drivers(self.provider.channel)
            idx_d = self.driver_combo.findData(self.provider.driver_key)
            if idx_d >= 0:
                self.driver_combo.setCurrentIndex(idx_d)
            self.sender_input.setText(self.provider.sender_id or "")
            self.endpoint_input.setText(self.provider.endpoint_url or "")
            self.env_key_input.setText(self.provider.credentials_env_key or "")
            self.config_json_input.setPlainText(self.provider.config_json or "{}")
            self.priority_spin.setValue(int(self.provider.priority_order or 1))
            self.sandbox_check.setChecked(bool(self.provider.sandbox_mode))
            self.default_check.setChecked(bool(self.provider.is_default))
            self.active_check.setChecked(bool(self.provider.is_active))

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _reload_drivers(self, channel: str):
        self.driver_combo.clear()
        for drv in CommunicationAdapterRegistry.list_drivers(channel=channel):
            self.driver_combo.addItem(f"{drv['driver_label']} ({drv['driver_key']})", drv["driver_key"])

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Provider Name is required.")
            return
        try:
            if self.provider:
                CommunicationRepository.update_provider(
                    self.db,
                    self.provider.id,
                    provider_name=name,
                    driver_key=self.driver_combo.currentData(),
                    sender_id=self.sender_input.text().strip() or None,
                    endpoint_url=self.endpoint_input.text().strip() or None,
                    credentials_env_key=self.env_key_input.text().strip() or None,
                    config_json=self.config_json_input.toPlainText().strip() or "{}",
                    priority_order=self.priority_spin.value(),
                    sandbox_mode=self.sandbox_check.isChecked(),
                    is_default=self.default_check.isChecked(),
                    is_active=self.active_check.isChecked(),
                )
            else:
                CommunicationRepository.create_provider(
                    self.db,
                    provider_name=name,
                    channel=self.channel_combo.currentText(),
                    driver_key=self.driver_combo.currentData(),
                    sender_id=self.sender_input.text().strip() or None,
                    endpoint_url=self.endpoint_input.text().strip() or None,
                    credentials_env_key=self.env_key_input.text().strip() or None,
                    config_json=self.config_json_input.toPlainText().strip() or "{}",
                    priority_order=self.priority_spin.value(),
                    sandbox_mode=self.sandbox_check.isChecked(),
                    is_default=self.default_check.isChecked(),
                    is_active=self.active_check.isChecked(),
                )
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not save provider configuration:\n{exc}")


class CommunicationTemplateDialog(QDialog):
    """Create a reusable scenario template."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Create Communication Template")
        self.setMinimumWidth(520)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit()
        form.addRow("Template Name *:", self.name_input)

        self.scenario_combo = QComboBox()
        self.scenario_combo.addItems(list(COMM_SCENARIO_TYPES))
        form.addRow("Scenario Type *:", self.scenario_combo)

        self.channel_combo = QComboBox()
        self.channel_combo.addItems(list(COMM_CHANNELS))
        form.addRow("Channel *:", self.channel_combo)

        self.subject_input = QLineEdit()
        form.addRow("Subject:", self.subject_input)

        self.wa_tpl_input = QLineEdit()
        self.wa_tpl_input.setPlaceholderText("Optional WhatsApp approved template slug")
        form.addRow("WhatsApp Slug:", self.wa_tpl_input)

        self.body_input = QTextEdit()
        self.body_input.setMinimumHeight(100)
        form.addRow("Message Body *:", self.body_input)

        hint = QLabel("Tokens supported: {school_name}, {guardian_name}, {student_name}, {due_amount}, {status}, {gpa}")
        hint.setStyleSheet("color: #64748B; font-size: 11px;")
        form.addRow("", hint)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        name = self.name_input.text().strip()
        body = self.body_input.toPlainText().strip()
        if not name or not body:
            QMessageBox.warning(self, "Validation", "Template Name and Body are required.")
            return
        try:
            CommunicationRepository.create_template(
                self.db,
                name=name,
                scenario_type=self.scenario_combo.currentText(),
                channel=self.channel_combo.currentText(),
                subject_template=self.subject_input.text().strip() or None,
                body_template=body,
                whatsapp_template_name=self.wa_tpl_input.text().strip() or None,
            )
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not create template:\n{exc}")


class DirectMessageDialog(QDialog):
    """Send an individual message via any configured SMS / Email / WhatsApp / InApp provider."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Send Direct Message")
        self.setMinimumWidth(500)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.channel_combo = QComboBox()
        self.channel_combo.addItems(list(COMM_CHANNELS))
        form.addRow("Channel *:", self.channel_combo)

        self.scenario_combo = QComboBox()
        self.scenario_combo.addItems(list(COMM_SCENARIO_TYPES))
        form.addRow("Scenario:", self.scenario_combo)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Recipient full name")
        form.addRow("Recipient Name *:", self.name_input)

        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("Phone number (+8801...), Email, or User ID")
        form.addRow("Recipient Contact *:", self.contact_input)

        self.subject_input = QLineEdit()
        form.addRow("Subject:", self.subject_input)

        self.body_input = QTextEdit()
        self.body_input.setMinimumHeight(90)
        form.addRow("Message *:", self.body_input)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Send Message")
        buttons.accepted.connect(self._send)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _send(self):
        name = self.name_input.text().strip()
        contact = self.contact_input.text().strip()
        body = self.body_input.toPlainText().strip()
        if not name or not body:
            QMessageBox.warning(self, "Validation", "Recipient name and message body are required.")
            return
        actor = app_session.current_user.username if app_session.current_user else "admin"
        try:
            log = CommunicationRepository.send_message(
                self.db,
                channel=self.channel_combo.currentText(),
                recipient_name=name,
                recipient_contact=contact,
                subject=self.subject_input.text().strip() or None,
                message_body=body,
                scenario_type=self.scenario_combo.currentText(),
                triggered_by=actor,
            )
            QMessageBox.information(
                self,
                "Dispatch Complete",
                f"Status: {log.status}\nProvider: {log.provider_name}\nLog Code: {log.log_code}",
            )
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Dispatch Error", f"Failed to send message:\n{exc}")
