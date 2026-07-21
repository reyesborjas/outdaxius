"""teams gain is_active -- support archiving on last-member departure

Spec 1.7 departure guard, level-1-leaves-an-otherwise-empty-team case: "archive the team, then
transfer." This was previously allowed (get_departure_block_reason returns None) but nothing
actually archived anything -- the team row was just left orphaned with zero members. This column
lets app.services.team_departure.leave_team mark it archived instead.

Revision ID: 0005_team_is_active
Revises: 0004_nullable_legal
Create Date: 2026-07-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_team_is_active"
down_revision: Union[str, None] = "0004_nullable_legal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE teams ADD COLUMN is_active boolean NOT NULL DEFAULT true")


def downgrade() -> None:
    op.execute("ALTER TABLE teams DROP COLUMN IF EXISTS is_active")
