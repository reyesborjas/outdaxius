"""allow 'demo' in company_payment_accounts.provider

Self-contained demo/pitch payment provider (app.services.payments.demo.DemoProvider) -- lets a
company demo the full pay/confirm/refund cycle to a prospective client with zero external signup.
No credentials required; ck_payment_accounts_provider just needs to accept the new value.

Revision ID: 0006_demo_payment_provider
Revises: 0005_team_is_active
Create Date: 2026-08-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_demo_payment_provider"
down_revision: Union[str, None] = "0005_team_is_active"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE company_payment_accounts DROP CONSTRAINT ck_payment_accounts_provider")
    op.execute(
        "ALTER TABLE company_payment_accounts ADD CONSTRAINT ck_payment_accounts_provider "
        "CHECK (provider = ANY (ARRAY['flow'::text, 'stripe'::text, 'transbank'::text, "
        "'mercadopago'::text, 'demo'::text]))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE company_payment_accounts DROP CONSTRAINT ck_payment_accounts_provider")
    op.execute(
        "ALTER TABLE company_payment_accounts ADD CONSTRAINT ck_payment_accounts_provider "
        "CHECK (provider = ANY (ARRAY['flow'::text, 'stripe'::text, 'transbank'::text, "
        "'mercadopago'::text]))"
    )
