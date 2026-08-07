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
> `bootstrap_schema.py` applies `schema.sql`, stamps the revision that file records in its
> header, then runs `alembic upgrade head` for anything newer. Use `--drop` to wipe and rebuild.

`schema.sql` is a `pg_dump --schema-only`, so it is also directly restorable if you prefer:

```bash
psql outdaxius_demo -f ../schema.sql     # then: alembic stamp <revision in its header>
```

**Regenerate it whenever a migration lands**, or new environments come up on a schema nobody is
running:

```bash
python -m scripts.dump_schema --from-scratch   # build a pristine DB from the migrations, dump it
python -m scripts.dump_schema --check          # CI: fail if the dump has drifted
```

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
python -m scripts.dump_schema --from-scratch # regenerate schema.sql after a migration
python -m scripts.dump_schema --check        # CI: fail if schema.sql has drifted
```

---

## Testing

`tests/conftest.py` gives the suite a real Postgres database, a `TestClient` wired to it, and
factories for people and tenants. Each test runs inside a transaction that is rolled back
afterwards, joined in savepoint mode so the endpoints' own `db.commit()` calls do not escape it.

```bash
cd backend
createdb outdaxius_test          # or set TEST_DATABASE_URL
python -m pytest tests/ -q
```

The schema is built once per run the same way a deployment builds it — `schema.sql` plus the
Alembic migrations — deliberately **not** `Base.metadata.create_all()`, because the ORM has known
drift from the migrated schema (`bookings.status` is a plain `String` on the model but a
`booking_status` enum in the database). Creating tables from the models would produce a schema the
application never actually runs against. Postgres rather than SQLite for the same reason: the
partial unique indexes and check constraints have already caught real bugs here.

`tests/test_companies.py` predated any conftest and had never run — every test errored at setup on
missing fixtures, and it built its own module-level `TestClient` that bypassed the `get_db`
override. It runs now. Five of its assertions were stale rather than failing: `max_guides` was
deliberately dropped from the schema by migration `0001`, one test sent an invalid payload so
`422` fired before the authorisation check it meant to assert, and the licence-cap test invited
six people when the cap counts accepted members. Those were corrected against what the code
deliberately does, not weakened to go green.

## Known issues found while building this

Documented rather than silently fixed, because each is a product decision rather than seeder work.

1. **`POST /companies/{id}/invitations` returns 200, not 201**, because it declares a
   `response_model` and no `status_code`. Arguably wrong for a resource-creating POST; left alone
   because changing it is an API contract change.

### schema.sql — regenerated, and now reproducible

The dump had drifted badly. It sat at revision `0005`, so its
`ck_payment_accounts_provider` constraint predated the `demo` payment provider; it contained no
`CREATE TYPE` at all, so the five enums the tables depend on were simply absent; and its
statements came out in SQLAlchemy reflection order rather than dependency order. It could not
build a database, which is the one job it has.

The cause was in its own header: it had been produced by reflecting a live database because
`pg_dump` was unavailable on the machine that made it. `pg_dump` is a normal dependency of a
Postgres install, so `scripts/dump_schema.py` now drives it and records the Alembic revision in
the header, and `bootstrap_schema.py` reads that revision rather than hardcoding one — so
regenerating after a new migration cannot silently leave the bootstrap stamping the wrong
revision and skipping migrations.

Three fixes were needed to make a `pg_dump` genuinely reusable here:

- **`\restrict` / `\unrestrict` are stripped.** pg_dump 16.13+ wraps its output in these, but
  they are psql *meta-commands* — anything talking to Postgres directly chokes on them. They also
  carry a fresh random nonce per run, which alone would make the file differ on every
  regeneration and break `--check`.
- **`CREATE SCHEMA public` is made conditional.** Postgres creates `public` with the database, so
  the bare form aborts a restore into exactly the empty database this file exists to serve.
- **Extensions are included.** Passing `--schema=public` makes pg_dump skip `CREATE EXTENSION`,
  and the column defaults call `public.uuid_generate_v4()`, so the restore died on the first
  table.

One subtlety worth knowing if you apply the dump programmatically: pg_dump's preamble sets an
empty session `search_path` so a restore can only touch fully-qualified names. Every connection
that applied the dump keeps that setting, and the ORM emits unqualified table names — so a reused
pooled connection fails with `relation "users" does not exist` while the table is sitting right
there. `bootstrap_schema.py` and the test fixtures both dispose the pool afterwards.

Verified four ways: `psql -f schema.sql` into an empty database (25 tables, 5 enums, no errors),
`bootstrap_schema` → seed → `verify_demo`, the test suite (which builds its schema from this
file), and `dump_schema --check`, which confirms a dump built purely from the migrations is
byte-identical to the committed file.

### Guide cap — fixed

Documented earlier as "a company at its cap can still issue invitations that will fail on
acceptance". That understated it: **`accept_invitation` never checked the cap at all.** Only
invitation *creation* validated the licence, so a company under its limit could issue any number
of invitations and every one would be accepted. Reproduced against a free-tier company with one
seat left: four invitees accepted, four `200`s, eight members against a cap of five. The cap was
bypassable, not merely leaky.

Two changes:

- **Acceptance is now the authoritative check.** `InvitationManager.accept_invitation` calls
  `LicenseManager.validate_can_add_member` before creating the membership. A refusal is `402`,
  not `400` — the request is valid, the company is out of seats — and it leaves the invitation
  `pending` and unused, so the company can upgrade and the same code still works. The check is
  skipped when reactivating an already-active member, which consumes no seat.
- **Outstanding invitations reserve a seat.** `get_company_license_info` now reports
  `pending_invitations`, `seats_taken`, and a `can_invite_guides` distinct from `can_add_guides`:
  issuing an invitation counts members *plus* reservations, while accepting one counts members
  only (the invitation being accepted is still pending and would otherwise count against
  itself). Expired invitations release their seat, so an unanswered invite cannot hold one
  forever.

`LicenseLimitError` subclasses `ValueError`, so existing handlers keep working while the endpoint
can distinguish "out of seats" from "bad request".

Also fixed in passing: **`GET /companies/{id}/license` was broken for every enterprise company.**
`LicenseInfo.max_guides` was declared `int`, but the unlimited tier maps to `None`, so the
response failed validation. It is `Optional[int]` now. Cordillera Ski School, the demo's
enterprise tenant, hit this on every request.

Covered by `tests/test_guide_cap.py` (9 tests), which reproduces the original bypass before
asserting the fix.

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

### Catalogue scoping — fixed

`GET /activities/`, `/activities/search`, `/activities/{id}`, `/programs/`, `/programs/search`
and `/programs/{id}/activities` took no authentication and applied no filter, so they returned
every row on the platform — other companies' private (`is_shared = false`) content included — to
any caller. The write path was already correct (`check_can_reuse` returns 403), so this was a
disclosure, and it also misled the UI into offering actions the API would then refuse.

Two audiences now, because one filter cannot serve both — `SearchActivities`/`SearchPrograms`/
`SearchTrips` are customer-facing, so scoping the single listing to team members would leave
travellers nothing to browse:

| View | Who | What they see |
| --- | --- | --- |
| **Public** (default) | anyone, signed in or not | Offerings with an upcoming, non-cancelled departure from a charges-enabled company. Plus, when signed in, anything they have already booked — so past trips keep resolving in "My bookings". |
| **Internal** (`?mine_only=true`) | authenticated only, 401 otherwise | Their own company's whole catalogue plus anything `is_shared`. Deliberately mirrors `check_can_reuse`, so the list offers exactly what the write path accepts. |

Platform admins bypass both. Detail endpoints return **404**, not 403, for something the caller
may not see — 403 would confirm that a competitor's private entry exists.

Rules live in `app/services/catalogue.py`. Frontend: `Activities.jsx`/`Programs.jsx` already knew
whether they were rendering the public route or the dashboard (`inDashboard`), so that flag now
drives `mine_only` too; `Schedules.jsx`, `CreateSchedule.jsx` and `EditProgramModal.jsx` are
back-office only and always request the internal view. `Bookings.jsx` deliberately stays on the
public list — the booked-by-me rule is what keeps its titles resolving.

Verified by `tests/test_catalogue_scoping.py` (14 request-level tests; 9 fail without the fix),
against the seeded tenants, and in a browser. On demo data: cancelling every departure of an
activity drops it from the public catalogue and from an anonymous `GET` by id (404) while its
owning company still sees and manages it.

### Catalogue PII exposure — fixed

`ActivityOut` embedded the full `UserOut` as `creator` and `leader`; `ProgramOut` did the same for
`creator`. Those endpoints require no authentication, so every field of `UserOut` was
world-readable: `email`, `national_id`, `passport_number`, `phone`, `birth_date`, `tax_id`, and
the entire `fiscal_data` blob (legal representative name and ID, tax address, economic activity).

An unauthenticated request returned, for each of 18 activities, the creator's and lead guide's
full records — enough to enumerate every operator on the platform and harvest their staff's
personal and tax data. `GET /users/{id}` is properly locked down (authenticated, admin-or-self),
so this embedded object was the only route to it.

Fixed by adding `UserPublicOut` (id, display_name, first_name, last_name, role, profile_picture)
and using it for `creator`/`leader` in both catalogue schemas. That keeps what a listing
legitimately renders — who to credit, and an avatar — and drops everything that identifies a
person off-platform. `UserOut` is unchanged where it belongs: `/users/me`, `/users/{id}` and the
auth responses still return the caller's own full record.

Verified unauthenticated against the seeded data: creator objects now carry only
`display_name`, `first_name`, `last_name`, `id`, `role`, `profile_picture`. Verified in the
browser that the activities list still renders its "By &lt;name&gt;" credit and that owner
edit/delete still resolves — the frontend's ownership check reads `creator.id`, with
`creator.email` only ever a redundant fallback.

`tests/test_catalogue_pii.py` guards it by walking the resolved Pydantic models, so it also
catches the field reappearing through a newly nested model. Confirmed to fail when `UserOut` is
put back.

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
