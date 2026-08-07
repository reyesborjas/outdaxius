# backend/scripts/bootstrap_schema.py
"""
Bring a brand-new, empty Postgres database up to the current Alembic head.

Why this exists: `alembic upgrade head` alone does NOT work on an empty database. 0000_baseline
is a deliberate no-op representing "the schema as it already existed when Alembic was introduced",
and 0001_mvp_foundation immediately does ALTER TABLE users ..., which fails with
`relation "users" does not exist`. The actual table definitions live in schema.sql at the repo
root.

schema.sql cannot simply be piped into psql either, for two reasons:

  1. It was produced by reflecting the live database via SQLAlchemy (no pg_dump available), and
     SQLAlchemy reflection does not emit CREATE TYPE. Four enums the tables depend on
     (user_role, attendance_status, payment_status, payment_method_type, booking_status) are
     therefore missing entirely.
  2. Its CREATE TABLE statements carry inline REFERENCES clauses but come out in reflection
     order, not dependency order, so a straight top-to-bottom run fails on forward references.

This script fixes both: it creates the enums first, then applies the CREATE statements
repeatedly until they all succeed (a fixed-point loop, which resolves any dependency ordering
without needing a real topological sort). Finally it stamps the revision schema.sql corresponds
to and upgrades to head.

Usage:
    python -m scripts.bootstrap_schema          # create schema, stamp, upgrade to head
    python -m scripts.bootstrap_schema --drop   # drop and recreate the public schema first
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

from sqlalchemy import create_engine, text

from app.db.config import DATABASE_URL

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA_SQL = REPO_ROOT / "schema.sql"

# schema.sql was dumped from a database at this revision -- it predates 0006 (its
# ck_payment_accounts_provider constraint still lacks 'demo'). Stamping here rather than at head
# means `alembic upgrade head` afterwards genuinely applies 0006, so a bootstrapped database ends
# up byte-identical to one that migrated forward normally.
SCHEMA_SQL_REVISION = "0005_team_is_active"

# Post-0001 enum values, taken from 0001_mvp_foundation's CREATE TYPE ... _new statements. These
# are the values a migrated database actually holds today, which is what schema.sql reflects.
ENUMS: dict[str, tuple[str, ...]] = {
    "user_role": ("admin", "guide", "client"),
    "attendance_status": ("not_attended", "attended", "no_show"),
    "payment_status": ("pending", "succeeded", "failed", "refunded", "partially_refunded"),
    "payment_method_type": ("card", "bank_transfer", "cash", "other"),
    "booking_status": ("pending", "confirmed", "cancelled"),
}


def split_statements(sql: str) -> list[str]:
    """Split the dump on semicolons that terminate a statement. The dump contains no functions,
    triggers, or dollar-quoted bodies, so a naive split on ';\\n' is sufficient and avoids
    dragging in a SQL parser."""
    stripped = re.sub(r"^--.*$", "", sql, flags=re.MULTILINE)
    return [s.strip() for s in stripped.split(";") if s.strip()]


def create_enums(conn) -> None:
    for name, values in ENUMS.items():
        labels = ", ".join(f"'{v}'" for v in values)
        conn.execute(
            text(
                f"DO $$ BEGIN "
                f"CREATE TYPE {name} AS ENUM ({labels}); "
                f"EXCEPTION WHEN duplicate_object THEN NULL; "
                f"END $$;"
            )
        )


def apply_until_fixed_point(engine, statements: list[str]) -> None:
    """Run every statement, retrying the failures on the next pass. Each pass must make progress
    or we are stuck on a genuine error rather than an ordering problem."""
    pending = list(statements)
    last_error: Exception | None = None

    while pending:
        failed: list[str] = []
        for stmt in pending:
            try:
                with engine.begin() as conn:
                    conn.execute(text(stmt))
            except Exception as exc:  # ordering issue, or a real error -- next pass decides which
                last_error = exc
                failed.append(stmt)

        if len(failed) == len(pending):
            head = failed[0][:400]
            raise RuntimeError(
                f"Could not apply {len(failed)} statement(s); no progress on the last pass.\n"
                f"First failing statement:\n{head}\n\nError: {last_error}"
            )
        pending = failed


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap an empty database to Alembic head.")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="DROP SCHEMA public CASCADE first. Destroys everything in the target database.",
    )
    args = parser.parse_args()

    if not SCHEMA_SQL.exists():
        print(f"schema.sql not found at {SCHEMA_SQL}", file=sys.stderr)
        return 1

    engine = create_engine(DATABASE_URL, echo=False, future=True)

    if args.drop:
        print("Dropping and recreating schema public ...")
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))

    with engine.begin() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        create_enums(conn)
    print(f"Created {len(ENUMS)} enum type(s).")

    statements = split_statements(SCHEMA_SQL.read_text(encoding="utf-8"))
    apply_until_fixed_point(engine, statements)
    print(f"Applied {len(statements)} schema statement(s).")

    # schema.sql includes the alembic_version table itself but never a row for it.
    backend_dir = pathlib.Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, "-m", "alembic", "stamp", SCHEMA_SQL_REVISION],
        cwd=backend_dir,
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        check=True,
    )

    print("\nDatabase bootstrapped to Alembic head.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
