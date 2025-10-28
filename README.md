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

Run all tests

The project uses pytest. From the repository root run:

```bash
# (recommended) create and activate a virtualenv first
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the full test suite
PYTHONPATH=$(pwd) pytest -q
```

Notes:
- We set `PYTHONPATH=$(pwd)` when running tests to ensure the `app` package is importable in environments where the package isn't installed system-wide. If you install the package into the venv (`pip install -e .`) this is not necessary.
- Tests are grouped across `tests/` and include unit, API, migration, regression and UI tests.

What’s included (high level):

- Unit/white-box tests: `tests/test_unit.py` (internal CRUD logic)
- API/black-box tests: `tests/test_api.py` (end-to-end endpoint checks, FK violation, injection attempts)
- Migration tests: `tests/test_migration.py` (V1 -> V2 migration and backfill validation)
- Regression tests: `tests/test_regression.py` (business rules like rounding and non-negative amounts)
- Extra security/UI tests: `tests/test_security_extra.py` (vulnerability toggle, injection behavior)
- Optional Selenium UI tests: `tests/test_ui_selenium.py` (browser-based, may be skipped if Chrome or a display/driver isn't available)

Running specific tests

Run a single test file:

```bash
PYTHONPATH=$(pwd) pytest tests/test_security_extra.py -q
```

Run a single test function:

```bash
PYTHONPATH=$(pwd) pytest tests/test_security_extra.py::test_search_injection_toggle -q
```

Why some tests may be skipped

- The Selenium-based UI tests in `tests/test_ui_selenium.py` will automatically call `pytest.skip` from fixtures when their prerequisites aren't available. Typical skip reasons:
	- The test suite couldn't start a local uvicorn server (the fixture tries to start one and pings `/health`).
	- Chrome/Chromium or the WebDriver isn't available/usable in the environment.

To run the Selenium tests, ensure you have a headless-capable Chrome/Chromium and supporting OS libs. On Debian/Ubuntu you can often install:

```bash
# install Chromium
sudo apt-get update && sudo apt-get install -y chromium-browser chromium

# ensure Python deps
pip install selenium requests

# then run just the selenium tests
PYTHONPATH=$(pwd) pytest tests/test_ui_selenium.py -q
```

If you run in CI or a container you'll often need additional system libraries (fonts, libnss, libatk-bridge2.0-0, etc.). If Chrome still fails to start, the fixture will emit the failure reason in the skip message.

Vulnerability toggle in the UI and tests

- The app exposes a runtime toggle endpoint `/vulnerable` and UI buttons on `/ui` to enable/disable the intentionally vulnerable code paths.
- Tests toggle this flag programmatically and via the UI. The toggle is in-memory for this process (file: `app/config.py`). It is intentional for local testing and educational demos only — do NOT expose this in production.

Performance and stress testing (Locust)
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

## Manual testing checklist (step-by-step)

The following steps let you manually exercise the behaviors covered by the automated tests and demonstrate the vulnerability toggle and migration checks.

1) Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

2) Basic UI / UAT

- Open http://localhost:8000/ui
- Create a user via the "Create User" card. Note the user id from the Users list or GET /users.
- Create an order via the "Create Order" card using the user id and a decimal amount like 12.345 — verify the amount is rounded half-up (12.35) in the Orders card.
- Try creating an order with a non-existent user id (e.g., 999999) — you should see an error about foreign key violation.

3) Vulnerability toggle and SQL injection testing

- On the UI you'll see the Vulnerability Mode card. It shows the current state ("Current: True/False") and a badge reading SAFE or VULNERABLE.
- By default the app runs in SAFE mode. In SAFE mode, the `/search_vuln` endpoint uses ORM/parameterized queries and the UI search is safe.
- Toggle to VULNERABLE by clicking Enable. The page will update the status via AJAX.
- While VULNERABLE is enabled, try the injection payload in the search box or call directly:

```bash
# example injection payload
curl 'http://localhost:8000/search_vuln?q=%27%20OR%20%271%27%3D%271'
```

- In VULNERABLE mode the raw SQL path may return more rows (demonstrating SQL injection). Toggle back to SAFE and verify the injection payload no longer returns rows.

4) Foreign key violation behavior difference

- In SAFE mode, the app performs a defensive check and returns a friendly 400 with "foreign key violation" when you try to create an order for a missing user.
- In VULNERABLE mode we skip the explicit check to simulate weaker validation; trying to insert an order for a missing user will surface a DB integrity error (also reported as a 400 but with different message). Use the `/vulnerable` endpoint to switch modes (UI or API):

```bash
# set vulnerable = true
curl -X POST 'http://localhost:8000/vulnerable' -H 'Content-Type: application/json' -d '{"value": true}'

# set vulnerable = false
curl -X POST 'http://localhost:8000/vulnerable' -H 'Content-Type: application/json' -d '{"value": false}'
```

5) Migration and data mismatch check (manual)

- Create a V1 database file that simulates the older schema (no `email` column):

```bash
python - <<'PY'
import sqlite3
conn = sqlite3.connect('test_v1.db')
conn.execute('PRAGMA foreign_keys=ON')
conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)')
conn.execute('CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, amount NUMERIC NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)')
conn.execute("INSERT INTO users (name) VALUES ('Alice'), ('Bob')")
conn.execute("INSERT INTO orders (user_id, amount) VALUES (1, 10.50), (2, 20.00)")
conn.commit(); conn.close()
PY
```

- Run the migration script:

```bash
python -m migration.migration_v1_to_v2 --db test_v1.db
```

- Inspect the DB (for example using sqlite3) and confirm the `email` column exists and was backfilled with `name || '@example.com'`.

6) Regression after a patch (manual workflow)

- Before applying a code change that might be risky (e.g., changing rounding behavior), run the test suite to capture the baseline:

```bash
PYTHONPATH=$(pwd) pytest -q
```

- Make your code change (e.g., edit `app/crud.py` or `app/models.py`).
- Re-run the test suite. Any failing tests indicate regressions. The automated regression tests include rounding checks, FK checks and migration tests.

7) Performance / Stress (Locust)

- Start the server and run Locust headless for a short smoke test (this will generate controlled load):

```bash
locust -f locustfile.py --host http://localhost:8000 -u 50 -r 10 -t 30s --headless
```

- Review Locust output for request failures and response times. For deeper profiling increase duration and user count.

8) Black-box (API) manual tests

- Use the interactive Swagger UI at http://localhost:8000/docs to call POST /users, POST /orders, GET /orders, GET /search, /search_vuln and observe responses and status codes.

9) White-box (unit) manual tests

- Use `tests/test_unit.py` to exercise CRUD logic locally with an in-memory DB. Run:

```bash
PYTHONPATH=$(pwd) pytest tests/test_unit.py -q
```

10) Selenium/manual browser tests

- If you want to check JS-driven flows end-to-end, install Chromium/Chrome and run `tests/test_ui_selenium.py` (see earlier section). The Selenium fixtures will attempt to start a local server and skip tests if prerequisites are missing.

Troubleshooting notes

- If UI toggles aren't visible or the page doesn't update, check the browser console for network errors to `/vulnerable` and ensure the server is running.
- If Selenium tests are skipped, see the "Why some tests may be skipped" section above.


## Notes

- Foreign keys are enforced for SQLite via PRAGMA; SQLAlchemy sets this on connect.
- For a real project, use Alembic; here we implement a minimal migration to exercise testing.