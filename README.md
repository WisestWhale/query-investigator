# Query Investigator

A learning project: reproduce a slow PostgreSQL query, measure it, improve it,
then build an AI assistant that explains the evidence.

## Environment

Python 3.13, uv, Git, and eventually a running PostgreSQL database.

```powershell
uv sync --locked
uv run main.py
```

`uv sync` creates `.venv`, an isolated Python environment. `pyproject.toml`
declares our dependencies; `uv.lock` records the exact resolved versions.
`uv run` uses this environment without requiring manual activation.

## Libraries

- psycopg[binary]: PostgreSQL driver with precompiled client components.
- python-dotenv: loads local connection settings from `.env`.

Copy `.env.example` to `.env` when setting up the database. `.env` and `.venv`
are excluded from Git. The example credentials are for local practice only.

## First exercise

Run `uv run main.py`. Explain why importing psycopg successfully does not yet
prove that a database connection works.

## Start the local database

Open Docker Desktop and wait for its engine to run. In a terminal in this folder:

```powershell
docker compose up -d --wait
uv run check_db.py
```

Expected output begins with `Connection OK: 1` and `Database: query_lab`.

The `compose.yaml` file runs the official PostgreSQL 17 image. Port 5433 on
your computer forwards to port 5432 inside the container. Only localhost can
connect. The named volume keeps database files when the container stops.
The health check waits until Postgres accepts connections.

`.env` contains DATABASE_URL; copy `.env.example` if it does not exist.
The example username/password are disposable local development credentials.

`check_db.py` has just three database steps: connect, execute SELECT, fetch a row.
There are no application tables yet. We'll create the orders table together.

To stop the database while retaining its data:

```powershell
docker compose stop
```

## Browse tables in pgAdmin

```powershell
docker compose up -d pgadmin
```

Open http://localhost:5050 and sign in using `learner@example.com` and
`localadmin` (local practice credentials). Expand Servers > Learning >
Query Lab (local). When asked for the database password, enter `localdev`.
Expand Databases > query_lab > Schemas > public > Tables.
Right-click customers > View/Edit Data > All Rows to browse its data.

pgAdmin uses host `db` and port 5432 because it connects inside Docker's
network; Python on Windows uses localhost and port 5433.
