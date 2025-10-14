import os
import sqlite3
import tempfile

from migration.migration_v1_to_v2 import migrate


def create_v1_db(path: str):
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        conn.execute(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, amount NUMERIC NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)"
        )
        # Seed data
        conn.execute("INSERT INTO users (name) VALUES ('Alice'), ('Bob')")
        conn.execute("INSERT INTO orders (user_id, amount) VALUES (1, 10.50), (2, 20.00)")
        conn.commit()
    finally:
        conn.close()


def test_migration_adds_email_and_backfills():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        create_v1_db(db_path)

        # Run migration
        migrate(db_path)

        # Validate
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.execute("PRAGMA table_info(users)")
            cols = [r[1] for r in cur.fetchall()]
            assert "email" in cols

            cur = conn.execute("SELECT name, email FROM users ORDER BY id")
            rows = cur.fetchall()
            assert rows[0][1] == "Alice@example.com"
            assert rows[1][1] == "Bob@example.com"
        finally:
            conn.close()
