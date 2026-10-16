"""First checkpoint: verify our Python environment before connecting to Postgres."""

import psycopg
from dotenv import load_dotenv


def main():
    load_dotenv()
    print(f"Environment ready. Psycopg version: {psycopg.__version__}")
    # Next lesson: read DATABASE_URL and execute SELECT 1.


if __name__ == "__main__":
    main()
