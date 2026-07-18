"""baseline — marks the schema as it exists today, before any Alembic-managed change

This migration is intentionally a no-op. It exists so there is a revision to attach future
migrations to (starting with 0001_mvp_foundation, Phase 2 of the Outdaxius refactor) without
Alembic trying to CREATE TABLE anything that already exists.

Do NOT run `alembic upgrade head` against an existing database that already has these tables —
that path is only for a brand-new, empty database. For an existing database, mark it as being
at this revision without executing anything:

    alembic stamp 0000_baseline

Revision ID: 0000_baseline
Revises:
Create Date: 2026-07-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0000_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op: represents the schema as captured in outdaxius-schema.sql at the time Alembic was
    # introduced (Phase 1 of the refactor). Existing databases should be `alembic stamp`-ed to
    # this revision, not upgraded through it.
    pass


def downgrade() -> None:
    # No-op for the same reason: there's nothing this revision created that it could drop.
    pass
