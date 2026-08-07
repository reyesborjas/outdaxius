# backend/tests/conftest.py
"""
Shared test fixtures: a real Postgres database, a TestClient wired to it, and the people and
tenants most tests need.

Two things drive the design.

First, **environment before import**. app/db/config.py reads DATABASE_URL and
CREDENTIALS_ENCRYPTION_KEY at import time and raises if the key is missing, and app/db/session.py
builds its engine from that value the moment it is imported. So the environment has to be set at
the top of this file, before anything under `app.` is imported. pytest loads conftest.py before
the test modules in its directory, which makes this the right place for it.

Second, **a real database rather than SQLite**. The schema uses Postgres enums, JSONB, partial
unique indexes (uq_booking_user_activity, uq_assignment_single_leader) and check constraints.
Several of those have already caught real bugs while this suite was being written; SQLite would
silently not have them, and the tests would pass while the application broke.

Isolation: each test runs inside a transaction that is rolled back afterwards. The session joins
that outer transaction in "create_savepoint" mode, so the `db.commit()` calls inside the
endpoints release a savepoint instead of really committing, and the rollback still undoes
everything. Tests are therefore independent without rebuilding the schema between them.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import uuid

# --- environment, before any `app.` import -------------------------------------------------
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://appuser:appsecret@localhost:5432/outdaxius_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["APP_ENV"] = "test"
os.environ.setdefault("SECRET_KEY", "test-secret-not-used-outside-tests")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
if not os.getenv("CREDENTIALS_ENCRYPTION_KEY"):
    from cryptography.fernet import Fernet

    os.environ["CREDENTIALS_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import psycopg2  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.security import create_token, get_password_hash  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.companymember import CompanyMember  # noqa: E402
from app.models.company_payment_account import CompanyPaymentAccount  # noqa: E402
from app.models.location import Location  # noqa: E402
from app.models.team import Team, TeamMember  # noqa: E402
from app.models.types import Types  # noqa: E402
from app.models.user import User  # noqa: E402
from app.core.crypto import encrypt_credentials  # noqa: E402

from scripts.bootstrap_schema import (  # noqa: E402
    SCHEMA_SQL,
    apply_until_fixed_point,
    schema_revision,
    split_statements,
)

TEST_PASSWORD = "test1234"


def _admin_url() -> tuple[str, str]:
    """(server URL without a database, database name) — for CREATE DATABASE."""
    raw = TEST_DATABASE_URL.split("://", 1)[1]
    creds_host, dbname = raw.rsplit("/", 1)
    return creds_host, dbname


def _ensure_database_exists() -> None:
    creds_host, dbname = _admin_url()
    userpass, host = creds_host.split("@", 1)
    user, password = (userpass.split(":", 1) + [""])[:2]
    hostname, _, port = host.partition(":")
    conn = psycopg2.connect(
        dbname="postgres", user=user, password=password, host=hostname, port=port or "5432"
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{dbname}"')
    finally:
        conn.close()


@pytest.fixture(scope="session")
def engine():
    """Build the schema once per test run, the same way a real deployment does it.

    Deliberately NOT Base.metadata.create_all(): the ORM has known, documented drift from the
    migrated schema (bookings.status is a plain String on the model but a booking_status enum in
    the database, and so on). Creating tables from the models would produce a schema the
    application never actually runs against.
    """
    _ensure_database_exists()
    eng = create_engine(TEST_DATABASE_URL, echo=False, future=True)

    with eng.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))

    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    apply_until_fixed_point(eng, split_statements(sql))

    # schema.sql is a pg_dump, and pg_dump opens with
    # SELECT pg_catalog.set_config('search_path', '', false) -- session-level, deliberately, so a
    # restore can only touch fully-qualified names. Every connection that applied the dump is
    # still carrying that empty search_path, and the ORM emits unqualified table names, so
    # reusing one of those pooled connections fails with `relation "users" does not exist` even
    # though the table is right there. Throw the pool away; fresh connections get the server
    # default back.
    eng.dispose()

    env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}
    subprocess.run(
        [sys.executable, "-m", "alembic", "stamp", schema_revision(sql)],
        cwd=BACKEND_DIR, env=env, check=True, capture_output=True,
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR, env=env, check=True, capture_output=True,
    )

    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    """A session inside a transaction that is rolled back when the test ends.

    join_transaction_mode="create_savepoint" is what makes this work against endpoints that call
    db.commit(): those commits release a savepoint rather than committing the outer transaction,
    so the rollback below still undoes everything the test did.

    One consequence worth knowing when writing a test: if the endpoint under test calls
    db.rollback() on its error path -- most of them do -- that unwinds to the current savepoint
    and takes the test's own setup with it. Call db.commit() after arranging the fixture data
    (not db.flush()) so the setup is released into the outer transaction first and survives.
    tests/test_guide_cap.py does exactly this.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    """TestClient sharing the test's transaction, so requests and assertions see one database."""
    def _get_db_override():
        yield db

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# --- people ---------------------------------------------------------------------------------
def make_user(db: Session, *, role: str, email: str | None = None, **kwargs) -> User:
    email = email or f"{role}.{uuid.uuid4().hex[:8]}@example.cl"
    user = User(
        email=email,
        password_hash=get_password_hash(TEST_PASSWORD),
        display_name=kwargs.pop("display_name", f"Test {role.title()}"),
        role=role,
        is_active=True,
        **kwargs,
    )
    db.add(user)
    db.flush()
    return user


def token_for(user: User) -> str:
    return create_token({"sub": str(user.id)}, kind="access")


def auth(user: User) -> dict[str, str]:
    """Authorization header for `user`, ready to splat into a request."""
    return {"Authorization": f"Bearer {token_for(user)}"}


@pytest.fixture()
def guide_user(db) -> User:
    return make_user(db, role="guide")


@pytest.fixture()
def client_user(db) -> User:
    return make_user(db, role="client")


@pytest.fixture()
def admin_user(db) -> User:
    return make_user(db, role="admin")


@pytest.fixture()
def auth_guide_token(guide_user) -> str:
    return token_for(guide_user)


@pytest.fixture()
def auth_user_token(client_user) -> str:
    return token_for(client_user)


@pytest.fixture()
def auth_admin_token(admin_user) -> str:
    return token_for(admin_user)


# --- tenants --------------------------------------------------------------------------------
def make_company(
    db: Session,
    *,
    owner: User,
    name: str | None = None,
    tier: str = "pro",
    charges_enabled: bool = True,
) -> tuple[Company, Team]:
    """A company with a team, its owner as a level-1 member, and (by default) a demo payment
    account so its schedules count as sellable."""
    company = Company(
        name=name or f"Company {uuid.uuid4().hex[:6]}",
        description="Test company",
        createdby=owner.id,
        license_tier=tier,
        is_active=True,
        currency="CLP",
    )
    db.add(company)
    db.flush()

    team = Team(
        name=f"{company.name} Team",
        created_by=owner.id,
        company_id=company.id,
        is_active=True,
    )
    db.add(team)
    db.flush()

    db.add(
        CompanyMember(
            companyid=company.id, userid=owner.id, position="Owner", is_admin=True, is_active=True
        )
    )
    db.add(TeamMember(team_id=team.id, user_id=owner.id, role_level=1))

    if charges_enabled:
        db.add(
            CompanyPaymentAccount(
                company_id=company.id,
                provider="demo",
                external_account_id=f"demo-{uuid.uuid4().hex[:8]}",
                credentials_encrypted=encrypt_credentials({"note": "test"}),
                charges_enabled=True,
                currency="CLP",
                is_sandbox=True,
            )
        )

    db.flush()
    return company, team


def add_member(db: Session, *, team: Team, company: Company, user: User, role_level: int = 4):
    db.add(
        CompanyMember(
            companyid=company.id, userid=user.id, position="Guide", is_admin=False, is_active=True
        )
    )
    db.add(TeamMember(team_id=team.id, user_id=user.id, role_level=role_level))
    db.flush()


# --- fixtures the pre-existing tests/test_companies.py expects -------------------------------
# That suite was written before any conftest existed, so it had never run. These give it the
# world it assumes: a company owned by the `guide_user` behind auth_guide_token, on the free tier
# (its licence assertions are about free-tier guide limits).
@pytest.fixture()
def company_and_team(db, guide_user):
    return make_company(db, owner=guide_user, name="Test Tours", tier="free")


@pytest.fixture()
def company_id(company_and_team) -> str:
    company, _team = company_and_team
    return str(company.id)


@pytest.fixture()
def owner_id(guide_user) -> str:
    return str(guide_user.id)


@pytest.fixture()
def member_id(db, company_and_team) -> str:
    """A non-owner member, so removal tests have someone safe to remove."""
    company, team = company_and_team
    member = make_user(db, role="guide", display_name="Team Member")
    add_member(db, team=team, company=company, user=member, role_level=4)
    return str(member.id)


@pytest.fixture()
def outsider_guide(db) -> User:
    """A guide who belongs to no company — the one who can actually accept an invitation."""
    return make_user(db, role="guide", display_name="Outsider Guide")


@pytest.fixture()
def outsider_guide_token(outsider_guide) -> str:
    return token_for(outsider_guide)


@pytest.fixture()
def invitation_code(db, company_and_team, guide_user, outsider_guide) -> str:
    """Addressed to `outsider_guide`: the accept endpoint checks the caller's email against
    invited_email and rejects a mismatch with 400, so the invitation has to name the person who
    is going to accept it."""
    from datetime import datetime, timedelta, timezone

    from app.models.invitation import InvitationCode

    company, _team = company_and_team
    invite = InvitationCode(
        code=f"TEST-{uuid.uuid4().hex[:8].upper()}",
        company_id=company.id,
        created_by=guide_user.id,
        invited_email=outsider_guide.email,
        status="pending",
        used=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invite)
    db.flush()
    return invite.code


@pytest.fixture()
def activity_type(db) -> Types:
    row = db.query(Types).filter(Types.type_name == "Trekking").first()
    if not row:
        row = Types(type_name="Trekking", experience_type="both")
        db.add(row)
        db.flush()
    return row


@pytest.fixture()
def location(db) -> Location:
    row = Location(display_name="Cajón del Maipo", lat=-33.735, lon=-70.35, source="manual")
    db.add(row)
    db.flush()
    return row
