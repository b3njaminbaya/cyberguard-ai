import asyncio
import json
import logging
import os
import time
from collections import Counter
from contextlib import asynccontextmanager
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
from database import SessionLocal, get_db
from detection.predict import explain_event, get_feature_importance, reload_model, score_event
from detection.train import DATA_PATH as TRAIN_DATA_PATH
from detection.train import train_model
from models import AppSettings, Incident, IncidentNote, LogEvent, NotificationSettings, SystemLog, Threat
from schemas import (
    AppSettingsIn,
    AppSettingsOut,
    EventIn,
    EventOut,
    IncidentIn,
    IncidentNoteIn,
    IncidentOut,
    IncidentUpdate,
    LogStatsOut,
    MeOut,
    ModelMetricsOut,
    NotificationSettingsIn,
    NotificationSettingsOut,
    SeverityCounts,
    SummaryOut,
    SystemHealthOut,
    SystemLogOut,
    ThreatExplanationItem,
    ThreatOut,
    UserBanUpdate,
    UserOut,
    UserRoleUpdate,
)
from syslog_server import SyslogProtocol

logger = logging.getLogger("cyberguard.notifications")
audit_logger = logging.getLogger("cyberguard.audit")

limiter = Limiter(key_func=get_remote_address)

_APP_START = time.time()

SYSLOG_PORT = int(os.environ.get("SYSLOG_PORT", "1514"))


def _persist_syslog_message(parsed: dict) -> None:
    """Called synchronously from the asyncio UDP protocol's datagram_received
    — opens its own session since there's no request to hang a DB dependency
    off of here."""
    db = SessionLocal()
    try:
        db.add(SystemLog(**parsed))
        db.commit()
    except Exception:
        logger.exception("Failed to persist syslog message")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    transport = None
    try:
        loop = asyncio.get_event_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: SyslogProtocol(on_message=_persist_syslog_message),
            local_addr=("0.0.0.0", SYSLOG_PORT),
        )
        logger.info("Syslog UDP listener started on port %d", SYSLOG_PORT)
    except OSError:
        logger.exception("Could not bind syslog UDP listener on port %d — log ingestion disabled", SYSLOG_PORT)
    yield
    if transport is not None:
        transport.close()


app = FastAPI(title="CyberGuard AI Backend", lifespan=lifespan)
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


def get_or_create_app_settings(db: Session) -> AppSettings:
    settings = db.query(AppSettings).first()
    if settings is None:
        settings = AppSettings()
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
        feature_importance=get_feature_importance(),
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


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

@app.get("/incidents", response_model=list[IncidentOut])
def list_incidents(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return (
        db.query(Incident)
        .options(selectinload(Incident.notes))
        .order_by(desc(Incident.created_at))
        .all()
    )


@app.post("/incidents", response_model=IncidentOut)
def create_incident(
    payload: IncidentIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if payload.threat_id and not db.query(Threat).filter(Threat.id == payload.threat_id).first():
        raise HTTPException(status_code=404, detail="Linked threat not found")

    incident = Incident(
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        threat_id=payload.threat_id,
        created_by_email=user.email,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    audit_logger.info("Incident %s created by %s", incident.id, user.email)
    return incident


@app.get("/incidents/{incident_id}", response_model=IncidentOut)
def get_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    incident = (
        db.query(Incident)
        .options(selectinload(Incident.notes))
        .filter(Incident.id == incident_id)
        .first()
    )
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.patch("/incidents/{incident_id}", response_model=IncidentOut)
def update_incident(
    incident_id: str,
    payload: IncidentUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(incident, field, value)
    db.commit()
    db.refresh(incident)
    audit_logger.info("Incident %s updated by %s: %s", incident.id, user.email, payload.model_dump(exclude_unset=True))
    return incident


@app.post("/incidents/{incident_id}/notes", response_model=IncidentOut)
def add_incident_note(
    incident_id: str,
    payload: IncidentNoteIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    db.add(IncidentNote(incident_id=incident_id, author_email=user.email, content=payload.content))
    db.commit()

    return (
        db.query(Incident)
        .options(selectinload(Incident.notes))
        .filter(Incident.id == incident_id)
        .first()
    )


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

@app.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("Admin")),
):
    rows = db.execute(
        text('SELECT id, email, role, banned, "createdAt" AS created_at FROM neon_auth."user" ORDER BY "createdAt" DESC')
    ).all()
    return [UserOut(id=str(r.id), email=r.email, role=r.role, banned=r.banned, created_at=r.created_at) for r in rows]


@app.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("Admin")),
):
    row = db.execute(
        text('SELECT id, email, role, banned, "createdAt" AS created_at FROM neon_auth."user" WHERE id = :id'),
        {"id": user_id},
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.execute(
        text('UPDATE neon_auth."user" SET role = :role WHERE id = :id'),
        {"role": payload.role, "id": user_id},
    )
    db.commit()
    audit_logger.info("User %s role changed to %s by %s", row.email, payload.role, user.email)
    return UserOut(id=str(row.id), email=row.email, role=payload.role, banned=row.banned, created_at=row.created_at)


@app.patch("/users/{user_id}/ban", response_model=UserOut)
def update_user_ban(
    user_id: str,
    payload: UserBanUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("Admin")),
):
    if user_id == user.id and payload.banned:
        raise HTTPException(status_code=400, detail="You can't suspend your own account")

    row = db.execute(
        text('SELECT id, email, role, banned, "createdAt" AS created_at FROM neon_auth."user" WHERE id = :id'),
        {"id": user_id},
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.execute(
        text('UPDATE neon_auth."user" SET banned = :banned WHERE id = :id'),
        {"banned": payload.banned, "id": user_id},
    )
    db.commit()
    audit_logger.info("User %s %s by %s", row.email, "suspended" if payload.banned else "reinstated", user.email)
    return UserOut(id=str(row.id), email=row.email, role=row.role, banned=payload.banned, created_at=row.created_at)


# ---------------------------------------------------------------------------
# General settings
# ---------------------------------------------------------------------------

@app.get("/settings/general", response_model=AppSettingsOut)
def get_general_settings(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return get_or_create_app_settings(db)


@app.put("/settings/general", response_model=AppSettingsOut)
def update_general_settings(
    payload: AppSettingsIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("Admin")),
):
    settings = get_or_create_app_settings(db)
    for field, value in payload.model_dump().items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    audit_logger.info("General settings updated by %s", user.email)
    return settings


# ---------------------------------------------------------------------------
# Model retraining
# ---------------------------------------------------------------------------

@app.post("/model/retrain", response_model=ModelMetricsOut)
@limiter.limit("3/hour")
def retrain_model(
    request: Request,
    user: CurrentUser = Depends(require_role("Admin")),
):
    if not TRAIN_DATA_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Training dataset not found — run `./data/download.sh` in backend/ first.",
        )
    audit_logger.info("Model retrain started by %s", user.email)
    report = train_model()
    reload_model()
    audit_logger.info("Model retrain completed by %s — accuracy=%.3f", user.email, report.get("accuracy", 0))

    from datetime import datetime, timezone

    per_class = {k: v for k, v in report.items() if isinstance(v, dict) and k not in ("accuracy",)}
    return ModelMetricsOut(
        trained=True,
        trained_at=datetime.now(tz=timezone.utc).isoformat(),
        accuracy=report.get("accuracy"),
        macro_f1=report.get("macro avg", {}).get("f1-score"),
        weighted_f1=report.get("weighted avg", {}).get("f1-score"),
        per_class=per_class,
        feature_importance=get_feature_importance(),
    )


@app.get("/threats/{threat_id}/explain", response_model=list[ThreatExplanationItem])
def explain_threat(
    threat_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    t = db.query(Threat).options(joinedload(Threat.event)).filter(Threat.id == threat_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail="Threat not found")
    if not t.event or not t.event.raw_payload:
        return []

    features = json.loads(t.event.raw_payload)
    return explain_event(features)


# ---------------------------------------------------------------------------
# System logs (real UDP syslog receiver — backend/syslog_server.py)
# ---------------------------------------------------------------------------

@app.get("/logs", response_model=list[SystemLogOut])
def list_logs(
    limit: int = 100,
    severity: str | None = None,
    flagged_only: bool = False,
    search: str | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    query = db.query(SystemLog)
    if severity:
        query = query.filter(SystemLog.severity == severity)
    if flagged_only:
        query = query.filter(SystemLog.flagged.is_(True))
    if search:
        query = query.filter(SystemLog.message.ilike(f"%{search}%"))
    return query.order_by(desc(SystemLog.received_at)).limit(limit).all()


@app.get("/logs/stats", response_model=LogStatsOut)
def log_stats(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    rows = db.query(SystemLog.severity, SystemLog.facility, SystemLog.source_host, SystemLog.flagged).all()
    return LogStatsOut(
        total_logs=len(rows),
        flagged_logs=sum(1 for r in rows if r.flagged),
        unique_hosts=len({r.source_host for r in rows}),
        by_severity=dict(Counter(r.severity for r in rows)),
        by_facility=dict(Counter(r.facility for r in rows)),
        listening_port=SYSLOG_PORT,
    )


# ---------------------------------------------------------------------------
# System health & danger zone
# ---------------------------------------------------------------------------

@app.get("/system/health", response_model=SystemHealthOut)
def system_health(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    db_connected = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_connected = False

    model_trained = METRICS_PATH.exists() and MODEL_PATH.exists()
    model_accuracy = None
    model_trained_at = None
    if model_trained:
        report = json.loads(METRICS_PATH.read_text())
        model_accuracy = report.get("accuracy")
        from datetime import datetime, timezone

        model_trained_at = datetime.fromtimestamp(MODEL_PATH.stat().st_mtime, tz=timezone.utc).isoformat()

    dataset_rows = None
    if TRAIN_DATA_PATH.exists():
        with open(TRAIN_DATA_PATH) as f:
            dataset_rows = sum(1 for _ in f) - 1  # minus header

    active_sessions = db.execute(
        text('SELECT COUNT(*) FROM neon_auth.session WHERE "expiresAt" > now()')
    ).scalar()

    return SystemHealthOut(
        database_connected=db_connected,
        model_trained=model_trained,
        model_accuracy=model_accuracy,
        model_trained_at=model_trained_at,
        dataset_rows=dataset_rows,
        total_events=db.query(LogEvent).count(),
        total_threats=db.query(Threat).count(),
        total_incidents=db.query(Incident).count(),
        active_sessions=active_sessions or 0,
        uptime_seconds=time.time() - _APP_START,
        ingest_rate_limit="60/minute per IP",
        alert_test_rate_limit="5/minute per IP",
        log_level=logging.getLevelName(logging.getLogger().getEffectiveLevel()),
    )


@app.post("/settings/notifications/reset")
def reset_notification_settings(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("Admin")),
):
    settings = get_or_create_settings(db)
    for field, value in NotificationSettingsIn().model_dump().items():
        setattr(settings, field, value)
    db.commit()
    audit_logger.info("Notification settings reset to defaults by %s", user.email)
    return {"status": "reset"}


@app.post("/system/factory-reset")
def factory_reset(
    confirm: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("Admin")),
):
    """Wipes ingested detection data (events, threats, incidents) — not users
    or configuration. Requires the literal string "RESET" to guard against
    accidental clicks; there is no undo."""
    if confirm != "RESET":
        raise HTTPException(status_code=400, detail='Type "RESET" to confirm this action.')

    db.execute(text("TRUNCATE threats, log_events, incidents, incident_notes, system_logs CASCADE"))
    db.commit()
    audit_logger.warning("FACTORY RESET performed by %s — all events/threats/incidents/logs wiped", user.email)
    return {"status": "reset"}
