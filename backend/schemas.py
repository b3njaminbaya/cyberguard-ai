from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MeOut(BaseModel):
    id: str
    email: str
    role: str


class EventIn(BaseModel):
    source_ip: str
    dest_ip: str
    protocol: str
    bytes: int = 0
    features: dict[str, float | int | str]


class ThreatOut(BaseModel):
    id: str
    score: float
    label: str
    severity: str
    summary: str | None
    created_at: datetime
    event_id: str
    source_ip: str | None = None
    dest_ip: str | None = None
    protocol: str | None = None
    bytes: int | None = None

    model_config = ConfigDict(from_attributes=True)


class EventOut(BaseModel):
    id: str
    ts: datetime
    source_ip: str
    dest_ip: str
    protocol: str
    bytes: int
    threats: list[ThreatOut] = []

    model_config = ConfigDict(from_attributes=True)


class SeverityCounts(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0


class SummaryOut(BaseModel):
    total_events: int
    total_threats: int
    by_severity: SeverityCounts
    by_category: dict[str, int]
    by_protocol: dict[str, int]


class ModelMetricsOut(BaseModel):
    trained: bool
    trained_at: str | None = None
    accuracy: float | None = None
    macro_f1: float | None = None
    weighted_f1: float | None = None
    per_class: dict[str, dict[str, float]] = {}


class NotificationSettingsIn(BaseModel):
    notifications_enabled: bool = True
    email_enabled: bool = False
    email_recipients: str = ""
    slack_enabled: bool = False
    slack_webhook_url: str | None = None
    slack_channel: str | None = None
    webhook_enabled: bool = False
    webhook_url: str | None = None
    webhook_secret: str | None = None
    alert_on_critical: bool = True
    alert_on_high: bool = True
    alert_on_medium: bool = False


class NotificationSettingsOut(NotificationSettingsIn):
    id: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
