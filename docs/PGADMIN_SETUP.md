# Local database + pgAdmin

Getting a local Outdaxius database you can browse and edit in pgAdmin.

Two routes. **Route A (Docker)** is the short one — nothing to install, and pgAdmin opens with
the server already registered. **Route B** is for a Postgres and pgAdmin you already have
installed natively. The database ends up identical either way; only steps 1–2 differ.

For what actually goes *in* the database — the demo tenants, logins, and planted scenarios — see
[DEMO_SETUP.md](./DEMO_SETUP.md). This document stops at "you can see the tables".

---

## Route A — Docker

### 1. Start Postgres and pgAdmin

```bash
docker compose up -d
```

From the repo root. First run pulls both images and takes a minute or two.

| | |
| --- | --- |
| Postgres | `localhost:5432`, user `appuser`, password `appsecret`, database `outdaxius` |
| pgAdmin | <http://localhost:5050> |

Both credentials are development-only values for containers bound to localhost.

Check it came up:

```bash
docker compose ps
```

`outdaxius-postgres` should read `healthy`. If it doesn't, `docker compose logs postgres`.

### 2. Open pgAdmin

Browse to <http://localhost:5050>. There is no login screen — the compose file runs pgAdmin in
desktop mode. In the left tree, expand **Servers → Outdaxius (local)**; it connects without
asking for a password.

The tree is empty of tables at this point. That is expected: the container is a bare Postgres
with two extensions. Step 3 creates the schema.

> **Why does the registered server say `Host: postgres`, not `localhost`?** pgAdmin is itself a
> container. It reaches Postgres over the compose network by service name. `localhost` inside
> that container is pgAdmin itself.

Now continue to [step 3](#3-configure-the-backend), shared with Route B.

---

## Route B — Postgres and pgAdmin you already have

### 1. Create the role and database

In pgAdmin, connect to your existing server (usually `PostgreSQL 16` under **Servers**, as the
`postgres` superuser). Open **Tools → Query Tool** on the `postgres` database and run:

```sql
CREATE ROLE appuser WITH LOGIN PASSWORD 'appsecret' CREATEDB;
CREATE DATABASE outdaxius OWNER appuser;
```

Then right-click **Databases → Refresh**, select the new `outdaxius` database, open a Query Tool
on *it*, and run:

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
```

Both extensions have to exist in `outdaxius` itself — extensions are per-database, not
per-server. `schema.sql` uses `uuid_generate_v4()` and `gen_random_uuid()` as column defaults and
will fail without them.

If you would rather not create a dedicated role, you can point `DATABASE_URL` at your existing
superuser instead. Just keep the URL in step 3 consistent with whatever you actually created.

### 2. Register the connection

If it isn't already there: right-click **Servers → Register → Server**.

| Tab | Field | Value |
| --- | --- | --- |
| General | Name | `Outdaxius (local)` |
| Connection | Host | `localhost` |
| Connection | Port | `5432` |
| Connection | Maintenance database | `outdaxius` |
| Connection | Username | `appuser` |
| Connection | Password | `appsecret`, tick **Save password** |

Save. The server should connect immediately.

---

## 3. Configure the backend

The schema is created by a Python script, not by pgAdmin, because it has to run Alembic
afterwards. So the backend needs its environment first.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                 # Windows PowerShell: Copy-Item .env.example .env
```

Open `backend/.env` and set two things:

**`DATABASE_URL`** — the default already matches Route A exactly, so leave it alone unless you
changed the port or used different credentials in Route B:

```
DATABASE_URL=postgresql+psycopg2://appuser:appsecret@localhost:5432/outdaxius
```

**`CREDENTIALS_ENCRYPTION_KEY`** — has no default and the app refuses to boot without it
(`app/db/config.py` raises on import). Generate one and paste it in:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Leave `APP_ENV=dev` as it is. If you plan to run the demo seeder, `dev` is already an accepted
value — see [DEMO_SETUP.md](./DEMO_SETUP.md).

## 4. Create the schema

Still in `backend/`, with the venv active:

```bash
python -m scripts.bootstrap_schema
```

That creates the five enum types, applies `schema.sql` from the repo root, stamps Alembic at
`0005_team_is_active`, and upgrades to head. It ends with `Database bootstrapped to Alembic head.`

> **Do not run `alembic upgrade head` on an empty database.** `0000_baseline` is a deliberate
> no-op, so `0001_mvp_foundation` immediately runs `ALTER TABLE users ...` and fails with
> `relation "users" does not exist`. `schema.sql` cannot be piped into `psql` either — it was
> produced by SQLAlchemy reflection, which emits no `CREATE TYPE` and no dependency ordering.
> `bootstrap_schema.py` exists to handle both. The full explanation is in its docstring.

`python -m scripts.bootstrap_schema --drop` wipes and rebuilds from scratch.

## 5. Look at it in pgAdmin

Right-click the server → **Refresh**, then expand:

```
Outdaxius (local) → Databases → outdaxius → Schemas → public → Tables
```

25 tables. To edit rows directly, right-click any table → **View/Edit Data → All Rows**, change
cells in the grid, and hit the save icon (or `F6`) to commit. For anything structural, use
**Tools → Query Tool** and write the SQL — but read the warning below first.

## 6. Optional — put data in it

An empty schema is awkward to explore. To get three tenants, ~600 bookings, and working logins:

```bash
python -m scripts.seed_demo --reset
python -m scripts.verify_demo
```

Every seeded account uses the password `demo1234`; the login table is in
[DEMO_SETUP.md](./DEMO_SETUP.md).

## 7. Optional — run the app against it

```bash
uvicorn app.main:app --reload        # backend on :8000

cd ../frontend
cp .env.example .env                 # VITE_API already points at the local backend
npm install && npm run dev           # frontend on :5173
```

---

## Making schema changes

Editing **rows** in pgAdmin is fine and is the point of this setup.

Editing **structure** in pgAdmin — adding a column, changing a type, dropping a constraint — will
work locally and then silently diverge from everyone else, because the change exists only in your
container. The schema of record is `backend/alembic/versions/`. So:

1. Prototype in the pgAdmin query tool until the SQL is right.
2. Write it up as a migration: `alembic revision -m "short description"`, fill in `upgrade()` and
   `downgrade()`, and update the ORM model in `backend/app/models/`.
3. Rebuild clean and confirm the migration reproduces what you prototyped:
   ```bash
   python -m scripts.bootstrap_schema --drop
   ```
4. Commit the migration.

Note that `schema.sql` is already known to be stale — it reflects revision `0005` and omits every
`CREATE TYPE` (issue 3 in DEMO_SETUP.md). Do not treat it as the source of truth, and do not hand-
edit it to match your change.

---

## Troubleshooting

**`port is already allocated` on `docker compose up`** — something already holds 5432, usually a
natively installed Postgres. Either stop it, or publish on another port and match it in
`backend/.env`:

```bash
POSTGRES_HOST_PORT=5433 docker compose up -d
# then: DATABASE_URL=postgresql+psycopg2://appuser:appsecret@localhost:5433/outdaxius
```

**pgAdmin asks for a password** — enter `appsecret` and tick **Save password**. It means the
container's entrypoint override didn't write the password file; harmless, and you only answer once.

**`relation "users" does not exist`** — you ran `alembic upgrade head` instead of
`scripts.bootstrap_schema`. See the note in step 4.

**`RuntimeError: CREDENTIALS_ENCRYPTION_KEY environment variable is not set`** — step 3. It fires
on import, so it hits any script that touches `app.db.config`, not just the server.

**`password authentication failed for user "appuser"`** — for Route A, the volume was probably
created by an earlier run with different credentials; `POSTGRES_PASSWORD` only applies when
initialising an empty volume. `docker compose down -v` and start over. For Route B, check the role
actually exists: `SELECT rolname FROM pg_roles WHERE rolname = 'appuser';`

**`could not translate host name "postgres"`** — you copied the compose server settings into a
natively installed pgAdmin. Outside the compose network that host is `localhost`.

**Changed `.env` and nothing happened** — it is read at import time. Restart uvicorn.
