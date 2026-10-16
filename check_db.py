"""Our smallest database experiment: connect, execute, fetch."""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

# The connection is closed automatically when this block finishes.
with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5) as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1, current_database(), version()")
        result = cursor.fetchone()
        print(f"Connection OK: {result[0]}")
        print(f"Database: {result[1]}")
        print(f"Server: {result[2]}")
