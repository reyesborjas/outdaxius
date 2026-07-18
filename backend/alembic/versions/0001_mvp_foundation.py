"""mvp foundation — role/team restructure, timestamptz, new payment/membership tables

This is the highest-risk migration in the Outdaxius refactor (spec Phase 2). It is DESTRUCTIVE
and ONE-WAY:
  - user_role enum is reduced (user->client, company->guide, master_guide->guide) — the original
    string label is not recoverable after this runs.
  - team_members.team_role (free text) is replaced by role_level (smallint 1-4). Duplicate
    memberships per user_id are deleted (full rows preserved in
    _migration_0001_dropped_memberships for audit, but NOT restored automatically by downgrade).
  - company.currency is widened from the 1-byte "char" type to varchar(3). Existing single-byte
    values (confirmed in dev: 'U') are preserved as truncated text, not reset to a guessed value —
    see the currency section below for why.
  - attendance_status / payment_status / payment_method_type enums are rebuilt with different
    label sets; unmapped legacy labels are coerced to the closest safe default (see the mapping
    table below, derived from querying the actual live enum labels, not just the target schema).

TAKE A pg_dump BEFORE RUNNING THIS. There is no safe downgrade — see downgrade() below.

Enum remap reference (queried from pg_enum against the live dev database on 2026-07-18 — the
target schema's own header comment warns these must be checked against the real database, and
they turned out to differ from what the narrative implied):

    user_role:            user, guide, master_guide, admin, company
                        -> admin, guide, client
                           (user->client, company->guide, master_guide->guide, admin/guide same)
    attendance_status:     attended, not_attended, late
                        -> not_attended, attended, no_show
                           (late->not_attended, NULL->not_attended)
    payment_status:         pending, completed, failed, refunded
                        -> pending, succeeded, failed, refunded, partially_refunded
                           (completed->succeeded, rest unchanged)
    payment_method_type:   credit_card, debit_card, paypal, bank_transfer
                        -> card, bank_transfer, cash, other
                           (credit_card/debit_card->card, paypal->other, bank_transfer unchanged)
    booking_status:         pending, confirmed, cancelled  (unchanged, additive only)
                        -> + reschedule_pending, + completed

KNOWN GAPS THIS MIGRATION DOES NOT INVENT DATA TO FILL (see spec Part 4 "Known risks" and
Phase 2 instructions: "if some backfills cannot be made perfectly ... preserve that reality and
document follow-up actions instead of inventing data"):
  - programs.team_id / activities.team_id: backfilled only where the row's created_by is (now
    uniquely) a team_members.user_id. In the dev database this resolves almost none of the
    existing rows, because most creators are not team members at all. These columns are added
    NULLABLE here (the target schema wants NOT NULL) specifically because of this gap. A follow-up
    migration should add the NOT NULL constraint only after an operator manually assigns the
    remaining orphaned rows to a team.
  - program_schedules.selling_company_id: backfilled via the schedule's program's team's company;
    falls back to the sole company row only when the `company` table has exactly one row (true in
    dev, NOT a safe assumption for multi-company production data). Also left NULLABLE for the same
    reason, though the target schema wants NOT NULL.

Revision ID: 0001_mvp_foundation
Revises: 0000_baseline
Create Date: 2026-07-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_mvp_foundation"
down_revision: Union[str, None] = "0000_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Naive timestamps in this database were never tagged with a timezone. This reinterprets them as
# having been recorded in Chile local time. If they were actually stored as UTC, change this
# before running (per the spec's own "Known risks" note) — there is no way to tell after the fact
# which assumption is correct, so this must be verified against how the app was actually deployed.
LOCAL_TZ = "America/Santiago"

TIMESTAMP_COLUMNS = [
    ("users", "created_at"), ("users", "updated_at"),
    ("company", "createdat"), ("company", "updatedat"), ("company", "subscription_expires_at"),
    ("teams", "created_at"), ("teams", "updated_at"),
    ("team_members", "joined_at"),
    ("activities", "created_at"), ("activities", "updated_at"),
    ("programs", "created_at"), ("programs", "updated_at"),
    ("locations", "created_at"), ("locations", "updated_at"),
    ("program_schedules", "start_time"), ("program_schedules", "end_time"),
    ("program_schedules", "created_at"), ("program_schedules", "updated_at"),
    ("activity_schedules", "start_time"), ("activity_schedules", "end_time"),
    ("activity_schedules", "created_at"), ("activity_schedules", "updated_at"),
    ("bookings", "created_at"), ("bookings", "updated_at"), ("bookings", "cancelled_at"),
    ("payments", "created_at"), ("payments", "updated_at"),
    ("payment_methods", "created_at"),
    ("invitation_codes", "created_at"), ("invitation_codes", "expires_at"),
    ("invitation_codes", "used_at"),
    ("reviews", "created_at"), ("reviews", "updated_at"),
    ("tax_rates", "created_at"),
    ("temporary_access_tokens", "created_at"), ("temporary_access_tokens", "expires_at"),
    ("audit_logs", "created_at"),
]


def upgrade() -> None:
    # ------------------------------------------------------------------------------------------
    # 1. Every naive timestamp -> timestamptz. Done first and independently of everything else
    #    below so a failure here doesn't leave a half-migrated enum/table state.
    # ------------------------------------------------------------------------------------------
    for table, column in TIMESTAMP_COLUMNS:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN "{column}" TYPE timestamptz '
            f"USING \"{column}\" AT TIME ZONE '{LOCAL_TZ}'"
        )

    # ------------------------------------------------------------------------------------------
    # 2. Enum rebuilds. Postgres cannot drop/rename enum labels in place, so each changed enum is:
    #    create new type -> cast column through a CASE map -> drop old type -> rename new to old.
    # ------------------------------------------------------------------------------------------

    # user_role
    op.execute("CREATE TYPE user_role_new AS ENUM ('admin', 'guide', 'client')")
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE users ALTER COLUMN role TYPE user_role_new USING (
            CASE role::text
                WHEN 'admin' THEN 'admin'
                WHEN 'guide' THEN 'guide'
                WHEN 'company' THEN 'guide'
                WHEN 'master_guide' THEN 'guide'
                WHEN 'user' THEN 'client'
                ELSE 'client'
            END
        )::user_role_new
        """
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'client'")
    op.execute("DROP TYPE user_role")
    op.execute("ALTER TYPE user_role_new RENAME TO user_role")

    # attendance_status
    op.execute("CREATE TYPE attendance_status_new AS ENUM ('not_attended', 'attended', 'no_show')")
    op.execute("ALTER TABLE bookings ALTER COLUMN attendance_status DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE bookings ALTER COLUMN attendance_status TYPE attendance_status_new USING (
            CASE attendance_status::text
                WHEN 'attended' THEN 'attended'
                WHEN 'not_attended' THEN 'not_attended'
                WHEN 'late' THEN 'not_attended'
                ELSE 'not_attended'
            END
        )::attendance_status_new
        """
    )
    op.execute("ALTER TABLE bookings ALTER COLUMN attendance_status SET DEFAULT 'not_attended'")
    op.execute("ALTER TABLE bookings ALTER COLUMN attendance_status SET NOT NULL")
    op.execute("DROP TYPE attendance_status")
    op.execute("ALTER TYPE attendance_status_new RENAME TO attendance_status")

    # payment_status
    op.execute(
        "CREATE TYPE payment_status_new AS ENUM "
        "('pending', 'succeeded', 'failed', 'refunded', 'partially_refunded')"
    )
    op.execute("ALTER TABLE payments ALTER COLUMN status DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE payments ALTER COLUMN status TYPE payment_status_new USING (
            CASE status::text
                WHEN 'pending' THEN 'pending'
                WHEN 'completed' THEN 'succeeded'
                WHEN 'failed' THEN 'failed'
                WHEN 'refunded' THEN 'refunded'
                ELSE 'pending'
            END
        )::payment_status_new
        """
    )
    op.execute("ALTER TABLE payments ALTER COLUMN status SET DEFAULT 'pending'")
    op.execute("DROP TYPE payment_status")
    op.execute("ALTER TYPE payment_status_new RENAME TO payment_status")

    # payment_method_type (no column default to drop/restore — confirmed against live schema)
    op.execute(
        "CREATE TYPE payment_method_type_new AS ENUM ('card', 'bank_transfer', 'cash', 'other')"
    )
    op.execute(
        """
        ALTER TABLE payment_methods ALTER COLUMN type TYPE payment_method_type_new USING (
            CASE type::text
                WHEN 'credit_card' THEN 'card'
                WHEN 'debit_card' THEN 'card'
                WHEN 'paypal' THEN 'other'
                WHEN 'bank_transfer' THEN 'bank_transfer'
                ELSE 'other'
            END
        )::payment_method_type_new
        """
    )
    op.execute("DROP TYPE payment_method_type")
    op.execute("ALTER TYPE payment_method_type_new RENAME TO payment_method_type")

    # booking_status — additive only, no remap needed
    op.execute("ALTER TYPE booking_status ADD VALUE IF NOT EXISTS 'reschedule_pending'")
    op.execute("ALTER TYPE booking_status ADD VALUE IF NOT EXISTS 'completed'")

    # ------------------------------------------------------------------------------------------
    # 3. team_members: team_role (text) -> role_level (smallint 1-4), exclusive membership,
    #    exactly one level-1 (master) per team, duplicate FKs removed.
    # ------------------------------------------------------------------------------------------
    op.execute("ALTER TABLE team_members ADD COLUMN role_level smallint NOT NULL DEFAULT 4")
    op.execute(
        "ALTER TABLE team_members ADD CONSTRAINT ck_team_members_role_level "
        "CHECK (role_level BETWEEN 1 AND 4)"
    )
    op.execute(
        """
        UPDATE team_members SET role_level = CASE
            WHEN lower(team_role) IN ('admin', 'master', 'master_guide', 'level_1', '1') THEN 1
            WHEN lower(team_role) IN ('planner', 'level_2', '2') THEN 2
            WHEN lower(team_role) IN ('coordinator', 'level_3', '3') THEN 3
            ELSE 4
        END
        """
    )

    # Archive + delete duplicate memberships (keep the row with the most authority per user_id,
    # earliest joined_at as tiebreak). Full rows are preserved for audit / manual reconciliation.
    op.execute(
        """
        CREATE TABLE _migration_0001_dropped_memberships AS
        SELECT tm.*, now() AS archived_at
        FROM team_members tm
        WHERE tm.id NOT IN (
            SELECT DISTINCT ON (user_id) id
            FROM team_members
            ORDER BY user_id, role_level ASC, joined_at ASC
        )
        """
    )
    op.execute(
        "DELETE FROM team_members WHERE id IN "
        "(SELECT id FROM _migration_0001_dropped_memberships)"
    )

    # Defensive: if dedup still leaves a team with more than one role_level=1 (possible if
    # distinct users independently had an 'admin'-mapped team_role in the same team), demote all
    # but the earliest-joined to level 2.
    op.execute(
        """
        UPDATE team_members
        SET role_level = 2
        WHERE role_level = 1
        AND id NOT IN (
            SELECT DISTINCT ON (team_id) id
            FROM team_members
            WHERE role_level = 1
            ORDER BY team_id, joined_at ASC
        )
        """
    )

    # Orphan teams (zero level-1 members after the above): promote the most-senior remaining
    # member to level 1 rather than leaving the team without a master guide.
    op.execute(
        """
        UPDATE team_members
        SET role_level = 1
        WHERE id IN (
            SELECT DISTINCT ON (t.team_id) t.id
            FROM team_members t
            WHERE t.team_id IN (
                SELECT team_id FROM team_members
                GROUP BY team_id
                HAVING count(*) FILTER (WHERE role_level = 1) = 0
            )
            ORDER BY t.team_id, t.role_level ASC, t.joined_at ASC
        )
        """
    )

    op.execute("ALTER TABLE team_members ADD CONSTRAINT uq_team_members_user UNIQUE (user_id)")
    op.execute(
        "CREATE UNIQUE INDEX uq_team_single_master ON team_members (team_id) "
        "WHERE role_level = 1"
    )
    op.execute("CREATE INDEX idx_team_members_team ON team_members (team_id)")

    op.execute("ALTER TABLE team_members DROP CONSTRAINT fk_team")
    op.execute("ALTER TABLE team_members DROP CONSTRAINT fk_user")
    op.execute("ALTER TABLE team_members DROP COLUMN team_role")

    # ------------------------------------------------------------------------------------------
    # 4. teams: archive-and-recreate lineage columns.
    # ------------------------------------------------------------------------------------------
    op.execute("ALTER TABLE teams ADD COLUMN archived_at timestamptz")
    op.execute("ALTER TABLE teams ADD COLUMN succeeded_by_team_id uuid REFERENCES teams (id)")

    # ------------------------------------------------------------------------------------------
    # 5. programs / activities: team_id, backfilled from the creator's (now-unique) membership.
    #    NULLABLE — see the module docstring for why this cannot be NOT NULL yet.
    # ------------------------------------------------------------------------------------------
    op.execute("ALTER TABLE programs ADD COLUMN team_id uuid REFERENCES teams (id)")
    op.execute("ALTER TABLE activities ADD COLUMN team_id uuid REFERENCES teams (id)")
    op.execute(
        """
        UPDATE programs p SET team_id = tm.team_id
        FROM team_members tm
        WHERE tm.user_id = p.created_by
        """
    )
    op.execute(
        """
        UPDATE activities a SET team_id = tm.team_id
        FROM team_members tm
        WHERE tm.user_id = a.created_by
        """
    )
    op.execute("CREATE INDEX idx_programs_team ON programs (team_id)")
    op.execute("CREATE INDEX idx_activities_team ON activities (team_id)")

    # ------------------------------------------------------------------------------------------
    # 6. company: currency widened to varchar(3); max_guides dropped (limits move to app config).
    #    Existing truncated currency values (e.g. a single 'U') are preserved as-is rather than
    #    reset to a guessed ISO code — they are not recoverable to their intended meaning, but
    #    fabricating a replacement would be worse than leaving the truncation visible. The new
    #    CHECK is added NOT VALID so it doesn't reject the migration over pre-existing bad data,
    #    but will reject any future write that doesn't fix it — the problem surfaces instead of
    #    being silently papered over.
    # ------------------------------------------------------------------------------------------
    op.execute(
        "ALTER TABLE company ALTER COLUMN currency TYPE varchar(3) USING currency::text::varchar(3)"
    )
    op.execute("ALTER TABLE company ALTER COLUMN currency SET DEFAULT 'CLP'")
    op.execute(
        "ALTER TABLE company ADD CONSTRAINT ck_company_currency "
        "CHECK (currency ~ '^[A-Z]{3}$') NOT VALID"
    )
    op.execute("ALTER TABLE company DROP COLUMN max_guides")

    # ------------------------------------------------------------------------------------------
    # 7. program_schedules: selling_company_id + settlement discount columns.
    #    NULLABLE — see the module docstring for why this cannot be NOT NULL yet.
    # ------------------------------------------------------------------------------------------
    op.execute("ALTER TABLE program_schedules ADD COLUMN selling_company_id uuid REFERENCES company (id)")
    op.execute("ALTER TABLE program_schedules ADD COLUMN settlement_discount_type text")
    op.execute(
        "ALTER TABLE program_schedules ADD CONSTRAINT ck_program_schedules_settlement_type "
        "CHECK (settlement_discount_type IS NULL OR settlement_discount_type IN ('percent', 'fixed'))"
    )
    op.execute("ALTER TABLE program_schedules ADD COLUMN settlement_discount_value numeric(12,2)")

    op.execute(
        """
        UPDATE program_schedules ps
        SET selling_company_id = t.company_id
        FROM programs p
        JOIN teams t ON t.id = p.team_id
        WHERE ps.program_id = p.id AND p.team_id IS NOT NULL
        """
    )
    # Fallback only when the whole database has exactly one company (true in dev; NOT a safe
    # general assumption, so this is explicitly scoped to that single-company case).
    op.execute(
        """
        DO $$
        DECLARE
            single_company_id uuid;
        BEGIN
            IF (SELECT count(*) FROM company) = 1 THEN
                SELECT id INTO single_company_id FROM company LIMIT 1;
                UPDATE program_schedules
                SET selling_company_id = single_company_id
                WHERE selling_company_id IS NULL;
            END IF;
        END $$
        """
    )
    op.execute("CREATE INDEX idx_program_schedules_selling ON program_schedules (selling_company_id)")

    # ------------------------------------------------------------------------------------------
    # 8. activity_schedules: selling_company_id (nullable in the target schema too — no gap here).
    #    Backfilled from the parent program_schedule where linked.
    # ------------------------------------------------------------------------------------------
    op.execute("ALTER TABLE activity_schedules ADD COLUMN selling_company_id uuid REFERENCES company (id)")
    op.execute(
        """
        UPDATE activity_schedules asch
        SET selling_company_id = ps.selling_company_id
        FROM program_schedules ps
        WHERE asch.program_schedule_id = ps.id AND ps.selling_company_id IS NOT NULL
        """
    )

    # ------------------------------------------------------------------------------------------
    # 9. role_permissions / permissions dropped — confirmed empty in dev; role_permissions has an
    #    FK to permissions so it must be dropped first.
    # ------------------------------------------------------------------------------------------
    op.execute("DROP TABLE IF EXISTS role_permissions")
    op.execute("DROP TABLE IF EXISTS permissions")

    # ------------------------------------------------------------------------------------------
    # 10. New tables: membership_requests, assignments, company_payment_accounts. DDL matches
    #     outdaxius-schema_new.sql exactly. All start empty — no data migration needed.
    # ------------------------------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE membership_requests (
            id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            direction               text NOT NULL,
            team_id                 uuid NOT NULL REFERENCES teams (id) ON DELETE CASCADE,
            company_id              uuid NOT NULL REFERENCES company (id) ON DELETE CASCADE,
            target_user_id          uuid REFERENCES users (id),
            target_email            text,
            offered_level           smallint NOT NULL DEFAULT 4,
            created_by              uuid NOT NULL REFERENCES users (id),
            on_behalf_of_company_id uuid REFERENCES company (id),
            target_consent          text NOT NULL DEFAULT 'not_required',
            message                 text,
            status                  text NOT NULL DEFAULT 'pending',
            expires_at              timestamptz,
            responded_at            timestamptz,
            created_at              timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_membership_requests_direction
                CHECK (direction IN ('invitation', 'application')),
            CONSTRAINT ck_membership_requests_level
                CHECK (offered_level BETWEEN 1 AND 4),
            CONSTRAINT ck_membership_requests_status
                CHECK (status IN ('pending', 'accepted', 'rejected', 'cancelled', 'expired')),
            CONSTRAINT ck_membership_requests_consent
                CHECK (target_consent IN ('not_required', 'pending', 'granted', 'refused')),
            CONSTRAINT ck_membership_requests_target
                CHECK (target_user_id IS NOT NULL OR target_email IS NOT NULL)
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_membership_requests_pending ON membership_requests "
        "(team_id, target_user_id) WHERE status = 'pending' AND target_user_id IS NOT NULL"
    )
    op.execute("CREATE INDEX idx_membership_requests_target ON membership_requests (target_user_id)")

    op.execute(
        """
        CREATE TABLE assignments (
            id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            activity_schedule_id uuid NOT NULL REFERENCES activity_schedules (id) ON DELETE CASCADE,
            user_id              uuid NOT NULL REFERENCES users (id),
            home_team_id         uuid NOT NULL REFERENCES teams (id),
            home_company_id      uuid NOT NULL REFERENCES company (id),
            is_leader            boolean NOT NULL DEFAULT false,
            status               text NOT NULL DEFAULT 'proposed',
            proposed_by          uuid NOT NULL REFERENCES users (id),
            proposed_at          timestamptz NOT NULL DEFAULT now(),
            responded_at         timestamptz,
            decline_reason       text,
            CONSTRAINT ck_assignments_status
                CHECK (status IN ('proposed', 'accepted', 'rejected', 'cancelled')),
            CONSTRAINT uq_assignment_once UNIQUE (activity_schedule_id, user_id)
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_assignment_single_leader ON assignments (activity_schedule_id) "
        "WHERE is_leader AND status IN ('proposed', 'accepted')"
    )
    op.execute("CREATE INDEX idx_assignments_user ON assignments (user_id)")
    op.execute("CREATE INDEX idx_assignments_company ON assignments (home_company_id)")

    op.execute(
        """
        CREATE TABLE company_payment_accounts (
            id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id            uuid NOT NULL REFERENCES company (id) ON DELETE CASCADE,
            provider              text NOT NULL,
            external_account_id   text,
            credentials_encrypted bytea NOT NULL,
            charges_enabled       boolean NOT NULL DEFAULT false,
            currency              varchar(3) NOT NULL DEFAULT 'CLP',
            is_sandbox            boolean NOT NULL DEFAULT true,
            verified_at           timestamptz,
            created_at            timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_payment_accounts_provider
                CHECK (provider IN ('flow', 'stripe', 'transbank', 'mercadopago')),
            CONSTRAINT uq_payment_account_provider UNIQUE (company_id, provider)
        )
        """
    )

    # ------------------------------------------------------------------------------------------
    # 11. bookings: cancellation / refund / policy-snapshot columns.
    # ------------------------------------------------------------------------------------------
    op.execute("ALTER TABLE bookings ADD COLUMN cancelled_by uuid REFERENCES users (id)")
    op.execute("ALTER TABLE bookings ADD COLUMN cancelled_by_party text")
    op.execute(
        "ALTER TABLE bookings ADD CONSTRAINT ck_bookings_cancelled_party "
        "CHECK (cancelled_by_party IS NULL OR cancelled_by_party IN ('client', 'vendor', 'system'))"
    )
    op.execute("ALTER TABLE bookings ADD COLUMN cancellation_reason text")
    op.execute("ALTER TABLE bookings ADD COLUMN refund_amount numeric(12,2)")
    op.execute("ALTER TABLE bookings ADD COLUMN refund_status text")
    op.execute(
        "ALTER TABLE bookings ADD CONSTRAINT ck_bookings_refund_status "
        "CHECK (refund_status IS NULL OR refund_status IN "
        "('not_required', 'pending', 'succeeded', 'failed', 'manual'))"
    )
    op.execute("ALTER TABLE bookings ADD COLUMN refund_reference text")
    op.execute(
        "ALTER TABLE bookings ADD COLUMN policy_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb"
    )


def downgrade() -> None:
    # A true safe downgrade is not possible: the enum remaps are lossy (original text labels for
    # user_role/attendance_status/payment_status/payment_method_type are not recoverable), the
    # team_members dedup deletes rows (archived to _migration_0001_dropped_memberships but not
    # restored automatically — re-inserting them would recreate the exact duplicate-membership
    # state this migration exists to eliminate), and the company.currency truncation already
    # happened before this migration ever ran. Restore from the pre-migration pg_dump instead.
    raise NotImplementedError(
        "0001_mvp_foundation has no safe downgrade. Restore from the pg_dump taken before "
        "this migration was applied. See the module docstring for exactly what is lossy."
    )
