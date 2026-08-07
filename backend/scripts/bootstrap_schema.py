# backend/scripts/bootstrap_schema.py
"""
Bring a brand-new, empty Postgres database up to the current Alembic head.

Why this exists: `alembic upgrade head` alone does NOT work on an empty database. 0000_baseline is
a deliberate no-op representing "the schema as it already existed when Alembic was introduced",
and 0001_mvp_foundation immediately does ALTER TABLE users ..., which fails with
`relation "users" does not exist`. The table definitions live in schema.sql at the repo root.

schema.sql is a pg_dump of a database at a known revision (regenerate it with
`python -m scripts.dump_schema --from-scratch`). It is complete and correctly ordered, so this
script is thin: apply it, stamp the revision it records, then upgrade to head.

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

REVISION_MARKER = "-- Alembic revision:"
# Used only for a dump old enough to predate the marker. Anything current states its own revision.
FALLBACK_REVISION = "0005_team_is_active"


def schema_revision(sql: str) -> str:
    """The Alembic revision schema.sql corresponds to, from its header.

    Read rather than hardcoded so that regenerating the dump after a new migration does not
    silently leave this script stamping a revision the file no longer matches -- which would make
    `alembic upgrade head` skip migrations the database actually needs.
    """
    for line in sql.splitlines()[:40]:
        if line.startswith(REVISION_MARKER):
            return line[len(REVISION_MARKER):].strip()
    print(
        f"schema.sql has no '{REVISION_MARKER}' header; assuming {FALLBACK_REVISION}. "
        "Regenerate it with: python -m scripts.dump_schema --from-scratch",
        file=sys.stderr,
    )
    return FALLBACK_REVISION


def split_statements(sql: str) -> list[str]:
    """Split the dump into executable statements.

    Drops psql meta-commands (\\restrict, \\connect and friends): this script talks to Postgres
    through SQLAlchemy, which has no idea what those are. dump_schema.py already strips the ones
    pg_dump emits; this is belt-and-braces for a hand-edited or older file.

    The dump contains no functions or dollar-quoted bodies, so splitting on ';' is sufficient and
    avoids pulling in a SQL parser.
    """
    without_comments = re.sub(r"^\s*--.*$", "", sql, flags=re.MULTILINE)
    without_meta = re.sub(r"^\s*\\[a-zA-Z]+.*$", "", without_comments, flags=re.MULTILINE)
    return [s.strip() for s in without_meta.split(";") if s.strip()]


def apply_until_fixed_point(engine, statements: list[str]) -> None:
    """Run every statement, retrying failures on the next pass.

    A pg_dump is already in dependency order, so this normally completes in one pass. It is kept
    because it costs nothing and makes the script tolerant of a hand-edited or reflection-order
    schema.sql. Each pass must make progress, or we are looking at a real error rather than an
    ordering problem.
    """
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

    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    revision = schema_revision(sql)

    engine = create_engine(DATABASE_URL, echo=False, future=True)

    if args.drop:
        print("Dropping and recreating schema public ...")
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))

    with engine.begin() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))

    statements = split_statements(sql)
    apply_until_fixed_point(engine, statements)
    # pg_dump's preamble sets an empty session search_path so a restore can only touch qualified
    # names. The connections that applied it are still carrying that, and anything emitting
    # unqualified names afterwards would fail with `relation ... does not exist`. Drop the pool.
    engine.dispose()
    print(f"Applied {len(statements)} schema statement(s) (revision {revision}).")

    # schema.sql includes the alembic_version table but never a row for it.
    backend_dir = pathlib.Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, "-m", "alembic", "stamp", revision], cwd=backend_dir, check=True
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=backend_dir, check=True
    )

    print("\nDatabase bootstrapped to Alembic head.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
