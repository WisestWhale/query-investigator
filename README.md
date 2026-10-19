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

## Inspect a query plan

Try the sample without a database:

```powershell
uv run explain_query.py --demo
```

It prints each step, including child steps, estimated rows and measured rows when available. The sample numbers are made up for testing. A sequential scan is not automatically a problem.

For your local `orders` table (which must have a numeric `total` column):

```powershell
uv run explain_query.py --total 40
uv run explain_query.py --total 40 --analyze --save plan.json
uv run explain_query.py --load plan.json
```

The first command asks PostgreSQL for estimates. `--analyze` executes the SELECT to measure it, using a read-only transaction and a 10-second timeout. `--save` creates a new file and refuses to overwrite existing files. `--load` reads a saved PostgreSQL JSON plan without connecting to the database. Row counts on measured steps are per loop.

This prototype explains the plan structure. It does not change indexes or automatically tune the query.

```powershell
uv run python -B -m unittest discover -p "test_*.py" -v
```
