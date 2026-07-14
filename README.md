# CyberGuard AI — AI-Enhanced Cybersecurity Threat Detector

[![CI](https://github.com/b3njaminbaya/cyberguard-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/b3njaminbaya/cyberguard-ai/actions/workflows/ci.yml)

A lightweight threat-detection dashboard for teams too small for an enterprise SIEM: ingest network traffic, score it for anomalies with a real trained ML model, get alerted over Slack/email/webhook, and get plain-language triage help from a locally-run AI assistant — no third-party API spend required.

This is a personal/portfolio project, built incrementally in the open. This README always reflects what's actually implemented, not what's planned — see [Roadmap](#roadmap) for what's not built yet.

---

## Status

| Layer | Status | Notes |
|---|---|---|
| Frontend (React dashboard) | 🟢 Live for 8/8 pages | No page shows demo/mock data anymore |
| Backend API | 🟢 Live | FastAPI, connected to Neon Postgres |
| Database | 🟢 Live | Neon (serverless Postgres) |
| Authentication | 🟢 Live | Neon Auth (Better Auth), JWT verified via JWKS, RBAC via `neon_auth.user.role` |
| Anomaly detection | 🟢 Live | RandomForestClassifier on real UNSW-NB15 data, 82% accuracy — retrainable from the UI |
| Explainability | 🟢 Live | Real `feature_importances_` chart on Models, per-threat z-score "Why Flagged" breakdown on Threats |
| Log-source ingestion | 🟢 Live | Real UDP syslog receiver (RFC 3164-ish), parses/flags/persists actual syslog packets — see below |
| Alert delivery | 🟢 Live | Slack Incoming Webhook, Gmail SMTP, generic HMAC-signed webhook — all fire automatically on detection |
| Incident management | 🟢 Live | Real CRUD, linked to threats, notes, status workflow |
| User management | 🟢 Live | Real roles, real account suspension (enforced, not decorative) |
| Tests / CI | 🟢 Live | 100 backend (pytest) + 15 frontend (Vitest) tests, GitHub Actions on every push/PR |
| AI triage assistant | 🟢 Live | "Triage with AI" on any threat — local Llama 3.1 8B via Ollama, cached per threat, no paid API |
| Security hardening | 🟢 Live | `/events/ingest` requires an API key, secrets masked for non-Admins, rate limiting, audit logging — see below |

🟢 working · 🟡 partial · ⚪ not started

**Log-source ingestion, honestly scoped:** the ML anomaly detector runs on UNSW-NB15 network *flow* data — it was never going to make sense to also claim it "detects threats" in free-text syslog lines, since that's a different data shape the model was never trained on. So `Logs` doesn't reuse the RandomForest model at all. Instead, `backend/syslog_server.py` is a real asyncio UDP listener (started via FastAPI's lifespan hook, default port 1514) that parses actual RFC 3164-ish syslog packets and flags them with simple, honest severity/keyword rules — a genuinely different, correctly-scoped detection approach for a genuinely different kind of data.

---

## Architecture

```
┌─────────────────────────┐
│  Frontend (React/Vite)  │  dashboard, charts, alert triage UI, auth
└────────────┬─────────────┘
             │ HTTPS + Bearer JWT
┌────────────▼─────────────┐
│   Backend (FastAPI)      │  JWT verification, CRUD, detection, alert dispatch
└──┬──────────┬──────────┬─┘
   │          │          │
┌──▼───┐ ┌────▼────┐ ┌───▼──────────────┐
│ Neon │ │ Neon    │ │ Slack / SMTP /   │
│ PG   │ │ Auth    │ │ webhook / Ollama │
└──────┘ └─────────┘ └──────────────────┘
```

Deliberately **one backend service**, not a service-per-concern split: FastAPI owns the database, auth verification, the detection logic, and alert dispatch. Anomaly scoring uses classical, self-hosted ML (not an LLM call) because it needs to be cheap and fast on every ingested log line. Authentication is Neon Auth (Better Auth under the hood) — the frontend talks to it directly for sign-in/sign-up, and the backend verifies the resulting JWT statelessly via Neon's public JWKS endpoint (no shared secret, no Node runtime required on the Python side). The AI assistant is reserved for the low-volume, human-reviewed task of explaining an alert and suggesting next steps — runs locally via [Ollama](https://ollama.com) rather than a paid API, by design. The syslog UDP listener runs inside the same asyncio event loop as uvicorn (via a `lifespan` context manager) rather than as a separate process — one less thing to deploy and monitor for a single-operator portfolio deployment.

See [`backend/`](backend/) for the API and [`src/`](src/) for the frontend.

---

## Local setup

### Frontend
```bash
npm install
cp .env.example .env.local   # fill in VITE_NEON_AUTH_URL from your own Neon project
npm run dev                  # http://localhost:8080
```

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, NEON_AUTH_URL, INGEST_API_KEY, and (optionally) SMTP_* for email alerts
python init_db.py      # creates all tables on your Neon database
uvicorn main:app --reload --port 8000   # http://localhost:8000/health
```

`INGEST_API_KEY` protects `POST /events/ingest` (see [Security](#security)) — generate one with:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Train the detection model once (downloads the real UNSW-NB15 dataset, ~32MB):
```bash
cd backend
./data/download.sh
python -m detection.train
```

Grant yourself Admin (needed to save notification settings — no signup flow grants it automatically):
```bash
python scripts/promote_admin.py you@example.com   # after signing up in the app once
```

Send a test syslog message to the real UDP listener (default port 1514, override with `SYSLOG_PORT`):
```bash
logger -n 127.0.0.1 -P 1514 "Failed password for invalid user admin from 203.0.113.45"
```

### AI triage assistant (optional, local)
```bash
brew install ollama
ollama pull llama3.1:8b   # or another open-weight model that fits your hardware
```

No API keys, no billing accounts, no paid tier required to run this project end to end (a free Gmail App Password is needed only if you want email alerts).

---

## Testing

```bash
# Backend — needs a disposable Postgres (matches what CI uses)
docker run -d --name cyberguard-test-pg -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=cyberguard_test -p 5433:5432 postgres:16
cd backend && source venv/bin/activate
pip install -r requirements-dev.txt
TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5433/cyberguard_test" pytest -v

# Frontend
npm run test
```

CI (`.github/workflows/ci.yml`) runs both suites plus a production build on every push/PR — see the badge above.

---

## Security

A pass over the codebase found and fixed one real, exploitable issue and closed three gaps that existed since earlier phases:

- **Fixed:** `GET /settings/notifications` returned the live Slack webhook URL and the webhook HMAC signing secret to *any* authenticated user, not just Admins — confirmed exploitable with a fresh, self-signed-up account, no privilege escalation needed. Now masked (`null`) for non-Admins; every other field (enabled flags, recipients, channel name) stays visible since none of it is a credential. Regression-tested, including that a non-Admin's read doesn't silently persist the mask over the real secret in the database.
- **Fixed:** `POST /events/ingest` had no authentication at all — anyone could inject fabricated threats and trigger real Slack/email/webhook alerts. Now requires a shared `X-API-Key` header (`INGEST_API_KEY` in `backend/.env`), checked with a constant-time comparison.
- **Added:** rate limiting (`slowapi`) — 60/min on ingest, 5/min on each alert-test endpoint — so the endpoints that send real messages to real destinations can't be used to spam a Slack channel or inbox.
- **Added:** structured audit logging (`cyberguard.audit` logger) for every settings change, manual test-alert trigger, and automatic alert dispatch, including who did it.
- **Reviewed and found clean:** no secrets ever committed to git (verified via `git log` on `.env` patterns), no raw string interpolation into SQL anywhere in the codebase (all queries parameterized), CORS scoped to the dev origin only.

`/events/ingest`'s API key is a static shared secret, appropriate for a single-operator portfolio deployment — a real multi-tenant product would want per-source keys with individual revocation.

---

## Roadmap

Ordered by what unlocks the most, not by calendar date.

**Done**
- [x] Minimal schema on Neon: log events, threats
- [x] Wire dashboard to real API data (8 of 8 pages — see Status)
- [x] Classical anomaly detection service on one log source, retrainable from the UI
- [x] Real authentication (Neon Auth) + role-based access
- [x] Real alert delivery: Slack webhook, email, generic webhook
- [x] Real incident management (CRUD, notes, status workflow, linked to threats)
- [x] Real user management (roles, enforced account suspension)
- [x] Automated tests + CI
- [x] Local AI triage assistant via Ollama
- [x] Basic security hardening (secrets handling, rate limiting, audit log, API-key auth on `/events/ingest`) — see [Security](#security)
- [x] Real log-source ingestion: UDP syslog receiver, made `Logs` real
- [x] Anomaly explainability UI (surface *why*, not just *that*)

**Later**
- [ ] Multi-tenant / organization support
- [ ] SSO for enterprise buyers
- [ ] Compliance evidence export
- [ ] Public API with documentation
- [ ] Additional log-source integrations (cloud audit logs, EDR webhooks) beyond syslog
- [ ] MFA / configurable session policy (needs a Better Auth plugin not currently enabled)
- [ ] Scheduled auto-retraining + data-drift monitoring (today's retraining is real but manually triggered)

**Long-term / vision, not committed**
- [ ] Fine-tuned detection model trained on real accumulated data
- [ ] Multi-agent security operations (specialized agents per domain)
- [ ] Integration marketplace
- [ ] On-prem / self-hosted enterprise edition
- [ ] Managed SOC-as-a-service offering

---

## License
MIT License. See `LICENSE` for details.

## Contact
b3njaminbaya@gmail.com
