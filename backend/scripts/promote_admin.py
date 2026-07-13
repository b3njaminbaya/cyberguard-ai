"""One-off bootstrap: grant the Admin role to a user by email.

RBAC-gated endpoints (e.g. saving notification settings) require the
Admin role, but there's no signup flow that grants it — someone has to be
promoted manually the first time. Usage:

    python scripts/promote_admin.py someone@example.com
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text  # noqa: E402

from database import engine  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/promote_admin.py <email>")
        sys.exit(1)

    email = sys.argv[1]
    with engine.begin() as conn:
        result = conn.execute(
            text('UPDATE neon_auth."user" SET role = :role WHERE email = :email'),
            {"role": "Admin", "email": email},
        )
        if result.rowcount == 0:
            print(f"No user found with email {email} — sign up in the app first, then re-run this.")
            sys.exit(1)
        print(f"{email} is now Admin.")


if __name__ == "__main__":
    main()
