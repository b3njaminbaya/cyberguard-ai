import json
import logging
from collections import Counter
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import desc, text
from sqlalchemy.orm import Session, joinedload, selectinload

import notifications
import triage
from auth import CurrentUser, get_current_user, require_ingest_key, require_role
from database import get_db
from detection.predict import score_event
from models import LogEvent, NotificationSettings, Threat
from schemas import (
    EventIn,
    EventOut,
    MeOut,
    ModelMetricsOut,
    NotificationSettingsIn,
    NotificationSettingsOut,
    SeverityCounts,
    SummaryOut,
    ThreatOut,
)

logger = logging.getLogger("cyberguard.notifications")
audit_logger = logging.getLogger("cyberguard.audit")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="CyberGuard AI Backend")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)

METRICS_PATH = Path(__file__).parent / "detection" / "metrics.json"
MODEL_PATH = Path(__file__).parent / "detection" / "model.joblib"


def get_or_create_settings(db: Session) -> NotificationSettings:
    settings = db.query(NotificationSettings).first()
    if settings is None:
        settings = NotificationSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def severity_is_enabled(settings: NotificationSettings, severity: str) -> bool:
    return {
        "critical": settings.alert_on_critical,
        "high": settings.alert_on_high,
        "medium": settings.alert_on_medium,
    }.get(severity, False)


def dispatch_alert(db: Session, threat: Threat, event: LogEvent) -> None:
    """Best-effort fan-out to every enabled channel. Never raises — a broken
    Slack webhook shouldn't take down ingestion."""
    settings = get_or_create_settings(db)
    if not settings.notifications_enabled or not severity_is_enabled(settings, threat.severity):
        return

    message = (
        f"[{threat.severity.upper()}] {threat.label} detected — "
        f"{event.source_ip} -> {event.dest_ip} ({event.protocol}), confidence {threat.score:.0%}"
    )

    if settings.slack_enabled and settings.slack_webhook_url:
        try:
            notifications.send_slack(settings.slack_webhook_url, message)
            audit_logger.info("Slack alert dispatched for threat %s (%s)", threat.id, threat.label)
        except Exception:
            logger.exception("Slack alert delivery failed")

    if settings.email_enabled and settings.email_recipients:
        recipients = [r.strip() for r in settings.email_recipients.split(",") if r.strip()]
        try:
            notifications.send_email(recipients, f"CyberGuard AI alert: {threat.label}", message)
            audit_logger.info("Email alert dispatched for threat %s (%s)", threat.id, threat.label)
        except Exception:
            logger.exception("Email alert delivery failed")

    if settings.webhook_enabled and settings.webhook_url:
        try:
            notifications.send_webhook(
                settings.webhook_url,
                {
                    "threat_id": threat.id,
                    "severity": threat.severity,
                    "label": threat.label,
                    "score": threat.score,
                    "source_ip": event.source_ip,
                    "dest_ip": event.dest_ip,
                    "protocol": event.protocol,
                    "created_at": threat.created_at.isoformat(),
                },
                secret=settings.webhook_secret,
            )
        except Exception:
            logger.exception("Custom webhook alert delivery failed")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.post("/events/ingest", response_model=EventOut, dependencies=[Depends(require_ingest_key)])
@limiter.limit("60/minute")
def ingest_event(request: Request, payload: EventIn, db: Session = Depends(get_db)):
    # Not user-JWT-gated on purpose: this is a service/pipeline endpoint (seed
    # scripts, future log-source ingestion), not called from the browser — it
    # authenticates via a shared X-API-Key instead (require_ingest_key).
    try:
        result = score_event(payload.features)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Detection model not trained yet — run `python -m detection.train` in backend/.",
        )

    event = LogEvent(
        source_ip=payload.source_ip,
        dest_ip=payload.dest_ip,
        protocol=payload.protocol,
        bytes=payload.bytes,
        raw_payload=json.dumps(payload.features),
    )
    db.add(event)
    db.flush()

    threat = None
    if result["is_threat"]:
        threat = Threat(
            event_id=event.id,
            score=result["score"],
            label=result["label"],
            severity=result["severity"],
        )
        db.add(threat)

    db.commit()
    db.refresh(event)

    if threat is not None:
        db.refresh(threat)
        dispatch_alert(db, threat, event)

    return event


@app.get("/events", response_model=list[EventOut])
def list_events(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return (
        db.query(LogEvent)
        .options(selectinload(LogEvent.threats))
        .order_by(desc(LogEvent.ts))
        .limit(limit)
        .all()
    )


@app.get("/threats", response_model=list[ThreatOut])
def list_threats(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    rows = (
        db.query(Threat)
        .options(joinedload(Threat.event))
        .order_by(desc(Threat.created_at))
        .limit(limit)
        .all()
    )
    return [
        ThreatOut(
            id=t.id,
            score=t.score,
            label=t.label,
            severity=t.severity,
            summary=t.summary,
            created_at=t.created_at,
            event_id=t.event_id,
            source_ip=t.event.source_ip if t.event else None,
            dest_ip=t.event.dest_ip if t.event else None,
            protocol=t.event.protocol if t.event else None,
            bytes=t.event.bytes if t.event else None,
        )
        for t in rows
    ]


@app.get("/stats/summary", response_model=SummaryOut)
def stats_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    total_events = db.query(LogEvent).count()
    threats = db.query(Threat).all()
    events = db.query(LogEvent).all()

    severity_counter = Counter(t.severity for t in threats)
    category_counter = Counter(t.label for t in threats)
    protocol_counter = Counter(e.protocol for e in events)

    return SummaryOut(
        total_events=total_events,
        total_threats=len(threats),
        by_severity=SeverityCounts(
            critical=severity_counter.get("critical", 0),
            high=severity_counter.get("high", 0),
            medium=severity_counter.get("medium", 0),
        ),
        by_category=dict(category_counter),
        by_protocol=dict(protocol_counter),
    )


@app.get("/model/metrics", response_model=ModelMetricsOut)
def model_metrics(user: CurrentUser = Depends(get_current_user)):
    if not METRICS_PATH.exists() or not MODEL_PATH.exists():
        return ModelMetricsOut(trained=False)

    report = json.loads(METRICS_PATH.read_text())
    per_class = {
        k: v
        for k, v in report.items()
        if isinstance(v, dict) and k not in ("accuracy",)
    }
    trained_at = MODEL_PATH.stat().st_mtime
    from datetime import datetime, timezone

    return ModelMetricsOut(
        trained=True,
        trained_at=datetime.fromtimestamp(trained_at, tz=timezone.utc).isoformat(),
        accuracy=report.get("accuracy"),
        macro_f1=report.get("macro avg", {}).get("f1-score"),
        weighted_f1=report.get("weighted avg", {}).get("f1-score"),
        per_class=per_class,
    )


@app.get("/users/me", response_model=MeOut)
def get_me(user: CurrentUser = Depends(get_current_user)):
    return MeOut(id=user.id, email=user.email, role=user.role)


@app.get("/settings/notifications", response_model=NotificationSettingsOut)
def get_notification_settings(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    settings = get_or_create_settings(db)
    # Build a detached Pydantic copy rather than mutating the ORM-tracked
    # instance in place — mutating `settings` directly here would be a trap
    # for a future change: any `db.commit()` elsewhere in the same request
    # would persist the mask and destroy the real secret in the database.
    out = NotificationSettingsOut.model_validate(settings)
    if user.role != "Admin":
        # slack_webhook_url and webhook_secret are bearer secrets — anyone who
        # holds them can post to the Slack channel or forge signed webhook
        # calls. Every other field (enabled flags, recipients, thresholds) is
        # fine for any authenticated user to see, so only these two are hidden
        # rather than gating the whole endpoint behind Admin.
        out.slack_webhook_url = None
        out.webhook_secret = None
    return out


@app.put("/settings/notifications", response_model=NotificationSettingsOut)
def update_notification_settings(
    payload: NotificationSettingsIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("Admin")),
):
    settings = get_or_create_settings(db)
    for field, value in payload.model_dump().items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    audit_logger.info("notification_settings updated by %s (%s)", user.email, user.id)
    return settings


@app.post("/settings/notifications/test/slack")
@limiter.limit("5/minute")
def test_slack(
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("Admin")),
):
    settings = get_or_create_settings(db)
    if not settings.slack_webhook_url:
        raise HTTPException(status_code=400, detail="No Slack webhook URL saved yet.")
    try:
        notifications.send_slack(
            settings.slack_webhook_url,
            "🔧 CyberGuard AI test alert — if you can see this, Slack delivery is working.",
        )
    except notifications.NotificationError as e:
        raise HTTPException(status_code=502, detail=str(e))
    audit_logger.info("Slack test alert triggered by %s (%s)", user.email, user.id)
    return {"status": "sent"}


@app.post("/settings/notifications/test/email")
@limiter.limit("5/minute")
def test_email(
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("Admin")),
):
    settings = get_or_create_settings(db)
    recipients = [r.strip() for r in settings.email_recipients.split(",") if r.strip()]
    if not recipients:
        raise HTTPException(status_code=400, detail="No email recipients saved yet.")
    try:
        notifications.send_email(
            recipients,
            "CyberGuard AI test alert",
            "This is a test alert from CyberGuard AI. If you're reading this, email delivery is working.",
        )
    except notifications.NotificationError as e:
        raise HTTPException(status_code=502, detail=str(e))
    audit_logger.info("Email test alert triggered by %s (%s)", user.email, user.id)
    return {"status": "sent"}


@app.post("/settings/notifications/test/webhook")
@limiter.limit("5/minute")
def test_webhook(
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("Admin")),
):
    settings = get_or_create_settings(db)
    if not settings.webhook_url:
        raise HTTPException(status_code=400, detail="No webhook URL saved yet.")
    try:
        notifications.send_webhook(
            settings.webhook_url,
            {"event": "test", "message": "CyberGuard AI test webhook delivery"},
            secret=settings.webhook_secret,
        )
    except notifications.NotificationError as e:
        raise HTTPException(status_code=502, detail=str(e))
    audit_logger.info("Webhook test alert triggered by %s (%s)", user.email, user.id)
    return {"status": "sent"}


@app.post("/threats/{threat_id}/triage", response_model=ThreatOut)
def triage_threat(
    threat_id: str,
    regenerate: bool = False,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    t = (
        db.query(Threat)
        .options(joinedload(Threat.event))
        .filter(Threat.id == threat_id)
        .first()
    )
    if t is None:
        raise HTTPException(status_code=404, detail="Threat not found")

    if not t.summary or regenerate:
        raw_features = json.loads(t.event.raw_payload) if t.event and t.event.raw_payload else {}
        try:
            t.summary = triage.generate_triage(
                label=t.label,
                severity=t.severity,
                score=t.score,
                source_ip=t.event.source_ip if t.event else "unknown",
                dest_ip=t.event.dest_ip if t.event else "unknown",
                protocol=t.event.protocol if t.event else "unknown",
                bytes_transferred=t.event.bytes if t.event else 0,
                raw_features=raw_features,
            )
        except triage.TriageError as e:
            raise HTTPException(status_code=502, detail=str(e))
        db.commit()
        db.refresh(t)

    return ThreatOut(
        id=t.id,
        score=t.score,
        label=t.label,
        severity=t.severity,
        summary=t.summary,
        created_at=t.created_at,
        event_id=t.event_id,
        source_ip=t.event.source_ip if t.event else None,
        dest_ip=t.event.dest_ip if t.event else None,
        protocol=t.event.protocol if t.event else None,
        bytes=t.event.bytes if t.event else None,
    )
