-- Runs once, on first start of an empty postgres_data volume.
--
-- schema.sql calls both uuid_generate_v4() (uuid-ossp) and gen_random_uuid() (core since
-- Postgres 13, but pgcrypto is what older dumps expect). scripts/bootstrap_schema.py creates
-- these too, so this file is belt-and-braces -- it matters if you load schema.sql by hand
-- through the pgAdmin query tool instead.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- docs/DEMO_SETUP.md uses a separate database for the demo seed. Create it here so either
-- DATABASE_URL works without touching the container.
CREATE DATABASE outdaxius_demo OWNER appuser;

\connect outdaxius_demo

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
