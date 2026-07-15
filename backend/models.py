import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LogEvent(Base):
    __tablename__ = "log_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    source_ip: Mapped[str] = mapped_column(String(45))
    dest_ip: Mapped[str] = mapped_column(String(45))
    protocol: Mapped[str] = mapped_column(String(20))
    bytes: Mapped[int] = mapped_column(Integer, default=0)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=True)

    threats: Mapped[list["Threat"]] = relationship(back_populates="event")


class Threat(Base):
    __tablename__ = "threats"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("log_events.id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    label: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    event: Mapped["LogEvent"] = relationship(back_populates="threats")


class NotificationSettings(Base):
    """One row per organization — alert configuration is org-scoped."""

    __tablename__ = "notification_settings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), unique=True, index=True)

    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    email_recipients: Mapped[str] = mapped_column(Text, default="")

    slack_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    slack_webhook_url: Mapped[str] = mapped_column(Text, nullable=True)
    slack_channel: Mapped[str] = mapped_column(String(100), nullable=True)

    webhook_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=True)
    webhook_secret: Mapped[str] = mapped_column(Text, nullable=True)

    alert_on_critical: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_on_high: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_on_medium: Mapped[bool] = mapped_column(Boolean, default=False)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class AppSettings(Base):
    """One row per organization — general settings are org-scoped."""

    __tablename__ = "app_settings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), unique=True, index=True)
    org_name: Mapped[str] = mapped_column(String(200), default="CyberGuard Security")
    contact_email: Mapped[str] = mapped_column(String(255), default="")
    timezone: Mapped[str] = mapped_column(String(50), default="utc")
    log_retention_days: Mapped[int] = mapped_column(Integer, default=90)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="open")
    assignee_email: Mapped[str] = mapped_column(String(255), nullable=True)
    created_by_email: Mapped[str] = mapped_column(String(255))
    threat_id: Mapped[str] = mapped_column(ForeignKey("threats.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    threat: Mapped["Threat"] = relationship()
    notes: Mapped[list["IncidentNote"]] = relationship(back_populates="incident", order_by="IncidentNote.created_at")


class IncidentNote(Base):
    __tablename__ = "incident_notes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    author_email: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    incident: Mapped["Incident"] = relationship(back_populates="notes")


class SystemLog(Base):
    """A real syslog message received over UDP (backend/syslog_server.py) —
    genuinely distinct from log_events: those are network flow records fed
    to the ML classifier, these are text log lines from a syslog sender.
    Flagging here is simple pattern matching, not the RandomForest model —
    the two data shapes aren't compatible, and pretending otherwise would be
    exactly the kind of dishonest labeling this project has avoided."""

    __tablename__ = "system_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    source_host: Mapped[str] = mapped_column(String(255))
    facility: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(20), index=True)
    tag: Mapped[str] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    raw: Mapped[str] = mapped_column(Text)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    flag_reason: Mapped[str] = mapped_column(String(200), nullable=True)


class AuditLog(Base):
    """Persisted audit trail — the cyberguard.audit logger writes to
    stdout/log files, which isn't queryable or exportable. This table backs
    the compliance evidence export (GET /compliance/export): a real,
    timestamped record of who did what, not just a log line that scrolls
    away. organization_id is nullable for platform-wide actions (e.g. site
    role changes) that aren't scoped to one org."""

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=True)
    actor_email: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(100), index=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class ApiKey(Base):
    """Per-organization ingest key for the public API (POST /events/ingest).
    Only the SHA-256 hash is ever stored — the raw secret is shown to the
    creator exactly once, in the create-key response, same pattern as
    GitHub/Stripe. This replaces the single shared INGEST_API_KEY with real
    per-tenant keys that can be individually issued and revoked."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)
    name: Mapped[str] = mapped_column(String(100))
    key_prefix: Mapped[str] = mapped_column(String(20))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_by_email: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
