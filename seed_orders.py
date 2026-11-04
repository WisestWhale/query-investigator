import argparse
import os
from pathlib import Path

CREATE_TABLE = """CREATE TABLE orders (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id int NOT NULL,
    total numeric(10, 2) NOT NULL,
    created_at timestamptz NOT NULL
)"""

# Totals are spread over 0.00-500.00, so a single total such as 40 matches few rows.
INSERT_ROWS = """INSERT INTO orders (customer_id, total, created_at)
SELECT 1 + floor(random() * 5000)::int,
       round((random() * 500)::numeric, 2),
       now() - random() * interval '365 days'
FROM generate_series(1, %s)"""


def seed(rows, reset=False):
    import psycopg
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).with_name(".env"))
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("Set DATABASE_URL in .env before using the database.")
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('orders') IS NOT NULL")
            if cursor.fetchone()[0]:
                if not reset:
                    raise ValueError("The orders table already exists. Use --reset to drop and recreate it.")
                cursor.execute("DROP TABLE orders")
            cursor.execute(CREATE_TABLE)
            # A fixed seed gives the same data on every run, so saved plans stay comparable.
            cursor.execute("SELECT setseed(0.42)")
            cursor.execute(INSERT_ROWS, (rows,))
        # Commit before ANALYZE so the planner statistics describe the new rows.
        connection.commit()
        with connection.cursor() as cursor:
            cursor.execute("ANALYZE orders")


def main():
    parser = argparse.ArgumentParser(description="Create an orders table filled with generated rows.")
    parser.add_argument("--rows", type=int, default=200_000, help="Number of orders to generate (default: 200000).")
    parser.add_argument("--reset", action="store_true", help="Drop the existing orders table first. Its data is lost.")
    args = parser.parse_args()
    if args.rows < 1:
        parser.error("--rows must be at least 1.")
    try:
        try:
            seed(args.rows, args.reset)
        except ValueError:
            raise
        except Exception as error:
            raise ValueError(f"Database setup failed: {error}") from None
        print(f"Created orders with {args.rows} rows.")
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
