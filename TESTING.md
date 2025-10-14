# Testing Guide

This document explains all tests in this repository, grouped by category, and how to run them. It maps directly to the requested coverage: black-box, white-box, performance/stress, migration (data mismatch), regression after patch, foreign key violations, injection attacks, and user acceptance testing (UAT).

- Stack: FastAPI + SQLAlchemy + SQLite + Pydantic
- App paths: `app/main.py`, `app/crud.py`, `app/models.py`, `app/schemas.py`, `app/db.py`
- Tests: `tests/`
- Load test: `locustfile.py`
- Migration: `migration/migration_v1_to_v2.py`

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Server (for manual checks or Locust):

```bash
uvicorn app.main:app --reload --port 8000
```

## Test categories

### 1) Black-box API tests (functional)

- Files
  - `tests/test_api.py`
- What they cover
  - Health check: API is up (`/health`).
  - Happy path (also serves as basic UAT): create user → create order → list orders.
  - Foreign key violation: creating an order for a non-existent user returns 400.
  - Injection attempt: sending `"%' OR '1'='1"` to `/search` does not dump all users and returns empty list.
- How they work
  - Use FastAPI TestClient (requests-like) against the app in-process.
  - DB is in-memory SQLite, provided via a fixture that overrides the app’s DB dependency.
- Run
  ```bash
  pytest -q tests/test_api.py
  ```

### 2) White-box unit tests (business logic)

- Files
  - `tests/test_unit.py`
- What they cover
  - `crud.create_user` creates a user.
  - `crud.create_order` applies HALF_UP rounding to 2 decimals (e.g., 10.125 → 10.13).
  - Non-negative amounts enforced.
  - Foreign key rule enforced (raises ValueError when user doesn’t exist).
- How they work
  - Call `crud` functions directly, not via HTTP.
  - Use in-memory SQLite via SQLAlchemy with a shared connection pool.
- Run
  ```bash
  pytest -q tests/test_unit.py
  ```

### 3) Migration and data mismatch after migration

- Files
  - `tests/test_migration.py`
  - `migration/migration_v1_to_v2.py`
- What they cover
  - Simulate a V1 DB schema: users table without `email`.
  - Run migration: adds `email` column and backfills with `<name>@example.com`.
  - Validate schema change and data backfill (prevents data mismatches post-migration).
- How they work
  - Build a temporary SQLite file with V1 schema using `sqlite3`.
  - Call the migration function.
  - Assert new column exists and data is correct.
- Run
  ```bash
  pytest -q tests/test_migration.py
  ```
  Manual migration against a DB file:
  ```bash
  python -m migration.migration_v1_to_v2 --db app.db
  ```

### 4) Regression after a patch

- Files
  - `tests/test_regression.py`
- What they cover
  - Guard the agreed rounding behavior: 2.675 → 2.68 using HALF_UP.
  - Prevents subtle changes from breaking financial calculations.
- How they work
  - Uses the white-box CRUD path to store and then asserts persisted amount.
- Run
  ```bash
  pytest -q tests/test_regression.py
  ```

### 5) Performance and stress testing

- File
  - `locustfile.py`
- What it does
  - Each simulated user creates a real user on start, then:
    - Repeatedly creates orders (3x weight)
    - Lists orders (1x weight)
  - Helps observe error rate/latency under load and check stability.
- How to run
  - Start the server first:
    ```bash
    uvicorn app.main:app --reload --port 8000
    ```
  - Quick headless smoke load:
    ```bash
    locust -f locustfile.py --host http://localhost:8000 -u 50 -r 10 -t 15s --headless
    ```
  - With web UI:
    ```bash
    locust -f locustfile.py --host http://localhost:8000
    ```
  - Watch failure rate and response times; the API should sustain moderate load without 5xx spikes.

### 6) User Acceptance Testing (UAT)

- Automated
  - `tests/test_api.py::test_user_and_order_flow` mirrors a real user flow.
- Manual
  1. Start the server and open http://localhost:8000/ui
  2. Create a user (name + optional email).
  3. Create an order for that user (amount).
  4. Verify both appear in their lists; check rounding on the amount.
  5. Try creating an order with a non-existent user_id → UI displays an error.
  6. Try a search like `"%' OR '1'='1"` → should not dump all users.

### 7) UI tests (server-rendered pages)

- File
  - `tests/test_ui.py`
- What they cover
  - UI renders (`/ui`) and shows title.
  - Create user via form → visible in UI.
  - Create order via form with amount rounding → visible in UI.
  - FK violation via form shows error message.
  - Injection-like search renders “No results”.
- How they work
  - Use TestClient to submit form data to `/ui/users` and `/ui/orders` and to fetch `/ui` for verification.
  - Requires `python-multipart` for form parsing (already in requirements).
- Run
  ```bash
  pytest -q tests/test_ui.py
  ```

### 8) Browser UI tests (Selenium)

- File
  - `tests/test_ui_selenium.py`
- What they cover
  - Same flows as server-rendered UI tests, but through a real browser (headless Chrome) using Selenium Manager (no separate WebDriver).
  - Start a temporary uvicorn server on a free port, navigate to `/ui`, submit forms, assert visible content.
- How they work
  - A session-scoped fixture boots uvicorn in a background thread and waits for `/health`.
  - A Selenium fixture launches headless Chrome with Selenium Manager (auto driver install).
  - Tests interact with inputs by name attributes and rely on simple page-source assertions.
  - If Chrome/driver setup is unavailable, tests are skipped gracefully (not failed).
- Run
  ```bash
  # All Selenium tests
  pytest -q tests/test_ui_selenium.py

  # Single test example
  pytest -q tests/test_ui_selenium.py::test_ui_homepage_loads
  ```

## Security-specific checks

- Foreign Key Violation
  - Black-box: `tests/test_api.py::test_fk_violation_returns_400` (returns 400)
  - White-box: `tests/test_unit.py::test_create_order_fk_violation` (raises ValueError)
  - UI: `tests/test_ui.py::test_ui_fk_violation_error_display` (shows error banner)

- Injection Attacks
  - API: `tests/test_api.py::test_injection_attack_blocked` (ORM LIKE, returns empty)
  - UI: `tests/test_ui.py::test_ui_search_injection_like_input` (No results)

## Running subsets and tips

- Run everything:
  ```bash
  pytest -q
  ```
- Run a category:
  ```bash
  pytest -q tests/test_api.py
  pytest -q tests/test_unit.py
  pytest -q tests/test_migration.py
  pytest -q tests/test_regression.py
  pytest -q tests/test_ui.py
  ```
- Run a single test:
  ```bash
  pytest -q tests/test_api.py::test_user_and_order_flow
  ```

## Tooling and fixtures

- Pytest fixtures in `tests/conftest.py` provide:
  - `db_session`: in-memory SQLite with SQLAlchemy StaticPool
  - `client`: FastAPI TestClient with dependency override to use the same in-memory DB
- Migration tests use temporary SQLite files to simulate versioned DBs.

## Current status

- As of last run: all tests passing
- You might see deprecation warnings from Starlette about TemplateResponse and redirect flags; they don’t impact behavior.

## Traceability (requirements → tests)

- Foreign Key Violation → API (black-box), Unit (white-box), UI
- Injection Attacks → API (black-box), UI
- Data Mismatch After Migration → Migration tests
- Regression After a Patch → Regression tests
- Performance/Stress → Locust
- Black Box → API tests
- White Box → Unit tests
- UAT → Automated flow test + manual steps
