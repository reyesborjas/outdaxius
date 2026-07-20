"""company legal/business fields become nullable -- support auto-created personal companies

Every guide is meant to always hold a team_members row (so "teamless guide" stops being a
reachable state -- see the 2026-07-19 production incident where teamless content silently lost
all reuse-policy protection). A team requires a company (teams.company_id is NOT NULL), and a
brand-new solo guide has no real legal/business info to supply for one, so the fields that only
make sense for an actually-registered business become optional. Real companies (created via the
existing POST /companies flow) still supply all of them as before -- this migration only relaxes
the constraint, it doesn't touch existing data.

Revision ID: 0004_nullable_legal
Revises: 0003_reuse_flag
Create Date: 2026-07-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_nullable_legal"
down_revision: Union[str, None] = "0003_reuse_flag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NULLABLE_FIELDS = [
    "legal_representive",
    "legal_representive_text",
    "legal_representive_phone",
    "legal_name",
    "trade_name",
    "incorporation_date",
    "country",
    "currency",
    "address",
    "entity_type",
]


def upgrade() -> None:
    for field in NULLABLE_FIELDS:
        op.execute(f"ALTER TABLE company ALTER COLUMN {field} DROP NOT NULL")


def downgrade() -> None:
    # Not reversible in general -- any auto-created personal company with a NULL value in one of
    # these fields would violate the restored NOT NULL constraint. Left as a no-op; a real
    # downgrade would need to backfill placeholder values first.
    pass
