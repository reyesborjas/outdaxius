"""activities/programs gain is_shared -- cross-company reuse flag

Reuse policy: a team may always schedule its own, or another team's in the SAME company. A
different company may only schedule it if is_shared=true. See app.core.permissions.check_can_reuse.

Revision ID: 0003_reuse_flag
Revises: 0002_payments_provider
Create Date: 2026-07-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_reuse_flag"
down_revision: Union[str, None] = "0002_payments_provider"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE activities ADD COLUMN is_shared boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE programs ADD COLUMN is_shared boolean NOT NULL DEFAULT false")


def downgrade() -> None:
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS is_shared")
    op.execute("ALTER TABLE activities DROP COLUMN IF EXISTS is_shared")
