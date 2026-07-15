"""One-time migration: introduce multi-tenancy.

Creates a "Default Organization" using Neon Auth's real `organization`
plugin tables, adds every existing user as a member, adds an
`organization_id` column to every domain table, and backfills existing rows
to the default org. Safe to re-run (every step checks before acting).

Run once against the live database:
    python scripts/migrate_to_organizations.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text  # noqa: E402

from database import SessionLocal  # noqa: E402

DEFAULT_ORG_SLUG = "default"
DEFAULT_ORG_NAME = "Default Organization"

# (table, nullable) — system_logs stays nullable: UDP syslog has no per-org
# auth mechanism, so ingested messages can't be genuinely attributed to an
# organization without a design we haven't built yet (see README).
TABLES = [
    ("log_events", False),
    ("threats", False),
    ("incidents", False),
    ("notification_settings", False),
    ("app_settings", False),
    ("system_logs", True),
]

UNIQUE_ORG_TABLES = {"notification_settings", "app_settings"}


def main():
    db = SessionLocal()
    try:
        org_row = db.execute(
            text('SELECT id FROM neon_auth.organization WHERE slug = :slug'),
            {"slug": DEFAULT_ORG_SLUG},
        ).first()
        if org_row is None:
            org_row = db.execute(
                text(
                    'INSERT INTO neon_auth.organization (id, name, slug, "createdAt") '
                    'VALUES (gen_random_uuid(), :name, :slug, now()) RETURNING id'
                ),
                {"name": DEFAULT_ORG_NAME, "slug": DEFAULT_ORG_SLUG},
            ).first()
            db.commit()
            print(f"Created {DEFAULT_ORG_NAME} ({org_row.id})")
        else:
            print(f"{DEFAULT_ORG_NAME} already exists ({org_row.id})")
        default_org_id = str(org_row.id)

        users = db.execute(text('SELECT id, role FROM neon_auth."user"')).all()
        added = 0
        for u in users:
            exists = db.execute(
                text('SELECT 1 FROM neon_auth.member WHERE "organizationId" = :org_id AND "userId" = :user_id'),
                {"org_id": default_org_id, "user_id": u.id},
            ).first()
            if exists:
                continue
            org_role = "owner" if u.role == "Admin" else "member"
            db.execute(
                text(
                    'INSERT INTO neon_auth.member (id, "organizationId", "userId", role, "createdAt") '
                    'VALUES (gen_random_uuid(), :org_id, :user_id, :role, now())'
                ),
                {"org_id": default_org_id, "user_id": u.id, "role": org_role},
            )
            added += 1
        db.commit()
        print(f"Added {added} user(s) as members of {DEFAULT_ORG_NAME} (skipped {len(users) - added} already-members)")

        for table, nullable in TABLES:
            col_exists = db.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = :t AND column_name = 'organization_id'"
                ),
                {"t": table},
            ).first()
            if not col_exists:
                db.execute(text(f"ALTER TABLE {table} ADD COLUMN organization_id UUID"))
                db.commit()
                print(f"{table}: added organization_id column")
            else:
                print(f"{table}: organization_id column already present")

            result = db.execute(
                text(f"UPDATE {table} SET organization_id = :org_id WHERE organization_id IS NULL"),
                {"org_id": default_org_id},
            )
            db.commit()
            if result.rowcount:
                print(f"{table}: backfilled {result.rowcount} row(s) to {DEFAULT_ORG_NAME}")

            if not nullable:
                db.execute(text(f"ALTER TABLE {table} ALTER COLUMN organization_id SET NOT NULL"))
                db.commit()

            if table in UNIQUE_ORG_TABLES:
                constraint_exists = db.execute(
                    text(
                        "SELECT 1 FROM pg_constraint WHERE conname = :name"
                    ),
                    {"name": f"{table}_organization_id_key"},
                ).first()
                if not constraint_exists:
                    db.execute(
                        text(f"ALTER TABLE {table} ADD CONSTRAINT {table}_organization_id_key UNIQUE (organization_id)")
                    )
                    db.commit()
                    print(f"{table}: added unique constraint on organization_id")

        print("Migration complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
