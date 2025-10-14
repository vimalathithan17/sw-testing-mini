# sw-testing-mini

A tiny FastAPI + SQLite app with a complete testing suite demonstrating:

- Black-box and white-box testing (pytest + FastAPI TestClient)
- Performance and stress testing (Locust)
- Regression testing
- Migration validation (detect data mismatch after migration)
- Security checks: foreign key violations and SQL injection attempts

## Prerequisites

- Python 3.11+

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the API server

```bash
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for interactive API.

## Test suites

Run all tests:

```bash
pytest -q
```

What’s included:

- Unit/white-box tests: `tests/test_unit.py` test internal CRUD logic
- API/black-box tests: `tests/test_api.py` validate endpoints, FK violation, injection attempts
- Migration tests: `tests/test_migration.py` creates a V1 schema, runs migration, verifies backfill
- Regression tests: `tests/test_regression.py` guards rounding and non-negative rules

## Performance and stress testing (Locust)

Start the server first (see above), then run Locust headless for a quick smoke load:

```bash
locust -f locustfile.py --host http://localhost:8000 -u 50 -r 10 -t 15s --headless
```

Or start the web UI:

```bash
locust -f locustfile.py --host http://localhost:8000
```

## Migration: V1 -> V2

We simulate a stored DB at `app.db` with users lacking the `email` column. The migration adds `email` and backfills from the name.

Run against a SQLite database file:

```bash
python -m migration.migration_v1_to_v2 --db app.db
```

The migration test shows how we detect and prevent data mismatches after migration.

## User Acceptance Testing (UAT)

Automated happy-path UAT is covered in `tests/test_api.py::test_user_and_order_flow`. Manual steps:

1. Start the server.
2. In Swagger UI, call POST /users with `{ "name": "Alice" }`.
3. Call POST /orders with `{ "user_id": <Alice id>, "amount": "12.34" }`.
4. Call GET /orders and verify the order is present.
5. Try POST /orders with a non-existent `user_id` to confirm a 400 error.
6. Try GET /search with `q=%' OR '1'='1` and confirm it does not return all users.

## Notes

- Foreign keys are enforced for SQLite via PRAGMA; SQLAlchemy sets this on connect.
- For a real project, use Alembic; here we implement a minimal migration to exercise testing.