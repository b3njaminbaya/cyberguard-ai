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
from auth import CurrentUser, OrgMember, get_current_user, require_org_member  # noqa: E402
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
        # Shadows Neon Auth's real `organization` plugin tables (verified
        # live against the actual schema — see project memory) so tests
        # exercise the same shape without needing a real Neon Auth instance.
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS neon_auth.organization (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS neon_auth.member (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    "organizationId" UUID NOT NULL,
                    "userId" UUID NOT NULL,
                    role TEXT NOT NULL,
                    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text('DROP TABLE IF EXISTS neon_auth.member'))
        conn.execute(text('DROP TABLE IF EXISTS neon_auth.organization'))
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
                "incidents, incident_notes, system_logs, api_keys, audit_log CASCADE"
            )
        )
        conn.execute(
            text('TRUNCATE neon_auth."user", neon_auth.session, neon_auth.organization, neon_auth.member CASCADE')
        )


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


@pytest.fixture(autouse=True)
def default_org(db_session):
    """The org that admin_user/regular_user both belong to, and — using
    slug="default" to match main.DEFAULT_ORG_SLUG — the same org
    /events/ingest and the syslog listener attribute data to. Autouse so any
    test hitting the API-key ingest path (no user session, no org header)
    has a default org to land in without every such test wiring it up by
    hand. Cross-org isolation itself is exercised in test_organizations.py
    against the real dependency, with a second, distinct org."""
    org_id = "00000000-0000-0000-0000-0000000000f1"
    db_session.execute(
        text('INSERT INTO neon_auth.organization (id, name, slug) VALUES (:id, :name, :slug)'),
        {"id": org_id, "name": "Test Org", "slug": "default"},
    )
    db_session.commit()
    return org_id


@pytest.fixture
def admin_org_member(db_session, admin_user, default_org):
    db_session.execute(
        text(
            'INSERT INTO neon_auth.member (id, "organizationId", "userId", role) '
            'VALUES (gen_random_uuid(), :org_id, :user_id, :role)'
        ),
        {"org_id": default_org, "user_id": admin_user.id, "role": "owner"},
    )
    db_session.commit()
    return OrgMember(user=admin_user, org_id=default_org, org_role="owner")


@pytest.fixture
def regular_org_member(db_session, regular_user, default_org):
    db_session.execute(
        text(
            'INSERT INTO neon_auth.member (id, "organizationId", "userId", role) '
            'VALUES (gen_random_uuid(), :org_id, :user_id, :role)'
        ),
        {"org_id": default_org, "user_id": regular_user.id, "role": "member"},
    )
    db_session.commit()
    return OrgMember(user=regular_user, org_id=default_org, org_role="member")


@pytest.fixture
def client(db_session):
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def authed_client(client, regular_org_member):
    app.dependency_overrides[get_current_user] = lambda: regular_org_member.user
    app.dependency_overrides[require_org_member] = lambda: regular_org_member
    yield client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_org_member, None)


@pytest.fixture
def admin_client(client, admin_org_member):
    app.dependency_overrides[get_current_user] = lambda: admin_org_member.user
    app.dependency_overrides[require_org_member] = lambda: admin_org_member
    yield client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_org_member, None)
