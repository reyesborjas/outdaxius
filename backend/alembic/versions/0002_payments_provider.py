"""payments gain provider/provider_ref, currency widened -- Phase 4 gap from Phase 2

The target schema's `payments` table adds `provider`/`provider_ref` and widens `currency` to
varchar(3), but 0001_mvp_foundation never touched `payments` at all -- those fields are
provider-integration-specific (Phase 4's concern), not part of the bare schema migration's
numbered change list. This closes that gap now that the payment provider architecture actually
needs it. `payments` has zero rows in dev -- low risk, no data to migrate.

Revision ID: 0002_payments_provider
Revises: 0001_mvp_foundation
Create Date: 2026-07-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_payments_provider"
down_revision: Union[str, None] = "0001_mvp_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE payments ADD COLUMN provider text")
    op.execute("ALTER TABLE payments ADD COLUMN provider_ref text")

    # Existing default 'USD' fits varchar(3) fine; NOT VALID so pre-existing bad data (none in
    # dev) can't block the migration, same reasoning as company.currency in Phase 2.
    op.execute("ALTER TABLE payments ALTER COLUMN currency TYPE varchar(3) USING currency::text::varchar(3)")
    op.execute(
        "ALTER TABLE payments ADD CONSTRAINT ck_payments_currency "
        "CHECK (currency ~ '^[A-Z]{3}$') NOT VALID"
    )

    # Idempotent webhook lookups: a retried Flow callback for the same token must not create a
    # duplicate Payment row.
    op.execute(
        "CREATE UNIQUE INDEX uq_payments_provider_ref ON payments (provider, provider_ref) "
        "WHERE provider_ref IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_payments_provider_ref")
    op.execute("ALTER TABLE payments DROP CONSTRAINT IF EXISTS ck_payments_currency")
    op.execute("ALTER TABLE payments ALTER COLUMN currency TYPE text USING currency::text")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS provider_ref")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS provider")
