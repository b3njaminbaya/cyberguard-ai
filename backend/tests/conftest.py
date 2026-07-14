import os

# Must happen before any app module is imported: database.py and auth.py
# read these from os.environ at import time. Point at a disposable test
# Postgres instead of the real Neon database.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/cyberguard_test"
)
os.environ.setdefault("NEON_AUTH_URL", "https://test.invalid/testdb/auth")
os.environ.setdefault("INGEST_API_KEY", "test-ingest-key")
# Port 0 asks the OS for an ephemeral free port — avoids clashing with a real
# dev server's syslog listener (default 1514) if TestClient ever triggers
# the app's lifespan (it doesn't today, but this makes that safe either way).
os.environ.setdefault("SYSLOG_PORT", "0")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import models  # noqa: E402, F401 — registers tables on Base.metadata
from auth import CurrentUser, get_current_user  # noqa: E402
from database import Base, SessionLocal, engine, get_db  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS neon_auth"))
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS neon_auth."user" (
                    id UUID PRIMARY KEY,
                    email TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    banned BOOLEAN NOT NULL DEFAULT false,
                    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS neon_auth.session (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    "userId" UUID NOT NULL,
                    "expiresAt" TIMESTAMPTZ NOT NULL
                )
                """
            )
        )
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text('DROP TABLE IF EXISTS neon_auth.session'))
        conn.execute(text('DROP TABLE IF EXISTS neon_auth."user"'))


@pytest.fixture(autouse=True)
def _clean_tables():
    """Truncate everything between tests so they don't see each other's data."""
    yield
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE threats, log_events, notification_settings, app_settings, "
                "incidents, incident_notes, system_logs CASCADE"
            )
        )
        conn.execute(text('TRUNCATE neon_auth."user", neon_auth.session CASCADE'))


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def admin_user(db_session):
    user_id = "00000000-0000-0000-0000-000000000001"
    db_session.execute(
        text('INSERT INTO neon_auth."user" (id, email, role) VALUES (:id, :email, :role)'),
        {"id": user_id, "email": "admin@test.local", "role": "Admin"},
    )
    db_session.commit()
    return CurrentUser(id=user_id, email="admin@test.local", role="Admin")


@pytest.fixture
def regular_user(db_session):
    user_id = "00000000-0000-0000-0000-000000000002"
    db_session.execute(
        text('INSERT INTO neon_auth."user" (id, email, role) VALUES (:id, :email, :role)'),
        {"id": user_id, "email": "user@test.local", "role": "user"},
    )
    db_session.commit()
    return CurrentUser(id=user_id, email="user@test.local", role="user")


@pytest.fixture
def client(db_session):
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def authed_client(client, regular_user):
    app.dependency_overrides[get_current_user] = lambda: regular_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def admin_client(client, admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)
