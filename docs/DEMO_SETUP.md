# Outdaxius Demo — Setup

How to get a fully populated demo database from nothing. Roughly ten minutes on a clean machine.

This is Phase 1 of [DEMO_RUNBOOK.md](./DEMO_RUNBOOK.md).

---

## 1. Prerequisites

- PostgreSQL 14+
- Python 3.11+
- Node 18+ (for the frontend)

## 2. Create the database

```bash
createdb outdaxius_demo
psql outdaxius_demo -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
```

## 3. Configure the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Edit `.env`:

- `DATABASE_URL` — point at the database you just created.
- `APP_ENV=demo` — **required**; the seeder refuses to run otherwise.
- `CREDENTIALS_ENCRYPTION_KEY` — generate one:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
  The app will not boot without it.

## 4. Create the schema

```bash
python -m scripts.bootstrap_schema
```

> **`alembic upgrade head` does not work on an empty database.** `0000_baseline` is a deliberate
> no-op standing for "the schema as it already existed when Alembic was introduced", so
> `0001_mvp_foundation` immediately runs `ALTER TABLE users ...` and fails with
> `relation "users" does not exist`. The table definitions live in `schema.sql` at the repo root.
>
> `schema.sql` cannot be piped into `psql` either: it was produced by reflecting the live database
> through SQLAlchemy, which does not emit `CREATE TYPE`, so the five enums the tables depend on
> are missing; and its statements come out in reflection order rather than dependency order.
>
> `bootstrap_schema.py` handles both — it creates the enums, applies the schema to a fixed point,
> stamps the revision `schema.sql` corresponds to (`0005_team_is_active`), then upgrades to head.
> Use `--drop` to wipe and rebuild.

## 5. Seed the demo

```bash
python -m scripts.seed_demo --reset
python -m scripts.verify_demo
```

`verify_demo` exits non-zero if anything a prospect would see is missing. Run it after every
seed, and after the nightly reset.

## 6. Run it

```bash
uvicorn app.main:app --reload                     # backend on :8000

cd ../frontend
cp .env.example .env                              # VITE_API defaults to the local backend
npm install && npm run dev                        # frontend on :5173
```

---

## Demo logins

Password for every account: **`demo1234`**

| Email | Role in the story |
| --- | --- |
| `owner@andes.demo` | Company owner — revenue, staffing, refunds, settings |
| `guide@andes.demo` | Field guide — my assignments, my schedule |
| `client@outdaxius.demo` | Customer — search, book, pay, cancel |
| `owner@patagonia.demo` | Freemium owner — usage meters, plan limits, upgrade path |
| `admin@outdaxius.demo` | Platform admin — cross-tenant view |

Every other seeded account (guides, ~90 customers) uses the same password.

---

## What gets seeded

Three tenants, so multi-tenancy is visible rather than asserted:

| Tenant | Tier | Role in the demo |
| --- | --- | --- |
| Andes Expeditions | `pro` | The hero. 8 activities, 5 programs, 92 departures. |
| Patagonia Kayak Co. | `basic` | Parked at **48 / 50** schedules — the upgrade moment. |
| Cordillera Ski School | `enterprise` | Unlimited tier, second data shape. |

Plus roughly 600 bookings across every terminal state, ~530 payments on the demo provider,
~180 guide assignments, and an inbox of pending membership requests and open invitations.

Two scenarios are planted deliberately:

- **A live assignment conflict.** The guide login holds an accepted assignment on one upcoming
  departure while a time-overlapping departure is left unstaffed. Assigning them to the second
  one trips `check_schedule_conflict` in front of the prospect. `verify_demo` prints the
  schedule id to target.
- **A tenant two clicks from its plan cap**, so the freemium ceiling can be hit live.

### Properties worth knowing

- **Deterministic.** Fixed seeds; every run produces identical data, so a rehearsed script stays
  valid.
- **Relative dates.** Everything is an offset from `now()`. Nothing goes stale.
- **Idempotent.** `--reset` replaces the demo tenants rather than duplicating them.
- **Scoped.** Deletes are confined to the three demo companies and to users whose email ends in
  `.demo`. There is no `TRUNCATE` in the seeder. Locations and activity types are shared
  reference data and survive a purge.
- **Guarded.** Refuses to run unless `APP_ENV` is `demo`/`dev`/`development`/`local`/`test`. An
  unset `APP_ENV` counts as unsafe.
- **Honest.** Fees and refunds come from calling `app.services.cancellation`, not from writing
  plausible numbers. `verify_demo` asserts `fee + refund == amount paid` on every cancellation.

### Commands

```bash
python -m scripts.seed_demo                 # seed; refuses if demo data already present
python -m scripts.seed_demo --reset         # purge, then seed
python -m scripts.seed_demo --purge         # purge and stop
python -m scripts.seed_demo --customers 150 # bigger booking population
python -m scripts.verify_demo               # assert the demo is showable
python -m scripts.bootstrap_schema --drop   # rebuild the schema from scratch
```

---

## Known issues found while building this

Documented rather than silently fixed, because each is a product decision rather than seeder work.

1. **The test suite does not run.** There is no `tests/conftest.py`, so all 8 tests in
   `test_companies.py` error at setup on missing fixtures (`auth_guide_token`, `db`,
   `company_id`). Pre-existing. Phase 6 work. (`tests/test_plan_limit_wiring.py`, added with the
   enforcement fix below, needs no fixtures and does run.)

2. **`schema.sql` is stale and incomplete.** It reflects revision `0005` (its
   `ck_payment_accounts_provider` constraint predates the `demo` provider) and omits every
   `CREATE TYPE`. `bootstrap_schema.py` compensates, but the dump should be regenerated.

### Plan limit enforcement — fixed

Plan limits were advertised by `GET /companies/{id}/limits` and enforced on only half the paths
that consume quota. `app/api/activities.py` imported `enforce_company_creation_limits`, took the
`get_current_company_id` dependency, and never called it; `app/api/activity_schedules.py` never
referenced it at all. A `basic` tenant walked from 48 to 52 schedules against a cap of 50 without
an error.

Three call sites were wired:

| Path | Gate |
| --- | --- |
| `POST /activities` | `metric="activities"`, against the caller's company context — matches `programs.py`. |
| `POST /activity-schedules` (standalone) | `metric="schedules_total"`, against the **selling** company. |
| `POST /activity-schedules` (child of a program schedule) | `metric="schedules_total"`, against the parent's selling company. |

Two decisions worth knowing:

- **Activity schedules gate on the selling company, not the caller.** `company_usage` counts an
  activity schedule toward the company that owns the underlying activity, so that is whose quota
  the row consumes. Gating on the caller (as `program_schedules.py` does) would let a guest
  company schedule a shared activity straight through the owner's cap.
- **Child activity schedules are gated too.** `schedules_total` counts rows in both
  `program_schedules` and `activity_schedules`, so each child consumes quota of its own. Leaving
  this path open kept the cap trivially bypassable — create one program schedule, then attach
  children forever. The cost is that filling a program schedule can stop partway once the cap is
  reached; parent and children are already separate requests, so a partial build is an existing
  failure mode rather than a new one.

Verified end to end against a running server: activities block at 20/20, standalone schedules at
50/50, child schedules at 50/50, and `pro`/`enterprise` tenants are unaffected.

`tests/test_plan_limit_wiring.py` guards the regression. It parses the route modules and asserts
the enforcer is actually called — the original bug is invisible in review, since the import is
present and the module reads as if it enforces. The tests cover wiring, not behaviour; they
cannot check that the right company or metric is passed. Confirmed to fail on the pre-fix code.

### Fixed in passing

- `app/models/company_payment_account.py` — the ORM `CheckConstraint` still listed only the four
  original providers, having drifted from migration `0006`, which added `demo`. Harmless at
  runtime (SQLAlchemy does not enforce check constraints) but wrong the moment anyone runs
  `create_all()` or autogenerates a migration.
- `app/db/session.py` — `echo=True` was hardcoded, logging every statement and its bound
  parameters. Now opt-in via `SQL_ECHO=1`.
- `scripts/create_super_admin.py` — imported `app.utils.security` (unreachable: `app/utils.py`
  shadows the `app/utils/` directory, which has no `__init__.py`) and `get_session` (does not
  exist; it is `get_db`). The only documented way to bootstrap an admin raised
  `ModuleNotFoundError` before it prompted for anything.
- `frontend/.env.example` — did not exist, so `VITE_API` was tribal knowledge.
