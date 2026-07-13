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
    event_id: Mapped[str] = mapped_column(ForeignKey("log_events.id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    label: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    event: Mapped["LogEvent"] = relationship(back_populates="threats")


class NotificationSettings(Base):
    """Single-row table — one global alert configuration for this deployment."""

    __tablename__ = "notification_settings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)

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
