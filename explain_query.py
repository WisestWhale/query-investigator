import argparse
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path

from plan_report import PlanReport


def explain(total, analyze=False):
    import psycopg
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).with_name(".env"))
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("Set DATABASE_URL in .env before using the database.")
    options = "ANALYZE, BUFFERS, FORMAT JSON" if analyze else "FORMAT JSON"
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute("SET LOCAL statement_timeout = '10s'")
            cursor.execute(
                f"EXPLAIN ({options}) SELECT * FROM orders WHERE total = %s",
                (total,),
            )
            return cursor.fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description="Inspect the plan for orders with a chosen total.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--load", type=Path, help="Read a saved EXPLAIN JSON file without connecting.")
    source.add_argument("--demo", action="store_true", help="Read the included sample plan.")
    parser.add_argument("--total", default="40", help="Order total to look up (default: 40).")
    parser.add_argument("--analyze", action="store_true", help="Execute the SELECT to measure its plan.")
    parser.add_argument("--save", type=Path, help="Save the plan to a new JSON file.")
    args = parser.parse_args()
    if (args.load or args.demo) and (args.analyze or args.total != "40"):
        parser.error("--total and --analyze apply to database queries, not saved plans.")
    try:
        if args.save and args.save.exists():
            raise ValueError("The save file already exists. Choose a new filename.")
        if args.load or args.demo:
            path = args.load or Path(__file__).with_name("sample_plan.json")
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            try:
                total = Decimal(args.total)
            except InvalidOperation:
                raise ValueError("Total must be a number.") from None
            if not total.is_finite():
                raise ValueError("Total must be a finite number.")
            try:
                data = explain(total, args.analyze)
            except ValueError:
                raise
            except Exception:
                raise ValueError("Database query failed. Check PostgreSQL, DATABASE_URL and the orders table; the query has a 10-second timeout.") from None
        report = PlanReport(data)
        if args.demo:
            print("Sample data; these are not measurements from your database.")
        print(report.to_text())
        if args.save:
            with args.save.open("x", encoding="utf-8") as output:
                json.dump([report.data], output, indent=2)
                output.write("\n")
            print(f"Saved: {args.save}")
    except (OSError, ValueError, RecursionError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
