"""
Migration V1 -> V2
- Adds 'email' column to users if missing
- Backfills email as '<name>@example.com' when NULL

Usage:
  python -m migration.migration_v1_to_v2 --db path/to/app.db
"""
import argparse
import os
import sqlite3
from contextlib import closing


def has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def migrate(db_path: str):
    if db_path == ":memory:":
        raise ValueError("Use a file-backed DB for migration script")

    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)

    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row

        # Ensure users table exists
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "users" not in tables:
            raise RuntimeError("users table missing; cannot migrate")

        # Add column if missing
        if not has_column(conn, "users", "email"):
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")

        # Backfill where NULL
        conn.execute("UPDATE users SET email = name || '@example.com' WHERE email IS NULL")
        conn.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, help="Path to SQLite database file")
    args = parser.parse_args()
    migrate(args.db)

if __name__ == "__main__":
    main()
