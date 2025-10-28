import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import config


client = TestClient(app)


def setup_module(module):
    # Ensure deterministic starting mode
    config.set_vulnerable(False)


def test_search_injection_toggle():
    # Clean slate: create two users
    r1 = client.post("/users", json={"name": "Alice"})
    assert r1.status_code == 201
    r2 = client.post("/users", json={"name": "Bob"})
    assert r2.status_code == 201

    # In safe mode: no injection should work
    client.post("/vulnerable?value=false")
    resp = client.get("/search_vuln", params={"q": "' OR '1'='1"})
    assert resp.status_code == 200
    assert resp.json() == []

    # Turn on vulnerable mode
    client.post("/vulnerable?value=true")
    try:
        resp2 = client.get("/search_vuln", params={"q": "' OR '1'='1"})
        assert resp2.status_code == 200
        # Injection should return at least the two created users
        names = {u["name"] for u in resp2.json()}
        assert "Alice" in names and "Bob" in names
    finally:
        # Reset to safe for other tests
        client.post("/vulnerable?value=false")


def test_foreign_key_violation_message_diff():
    # Ensure safe mode: explicit check triggers user-friendly message
    client.post("/vulnerable?value=false")
    r = client.post("/orders", json={"user_id": 999999, "amount": "10.00"})
    assert r.status_code == 400
    assert "foreign key violation" in r.json().get("detail", "").lower()

    # Vulnerable mode: skip defensive check, DB causes integrity error
    client.post("/vulnerable?value=true")
    try:
        r2 = client.post("/orders", json={"user_id": 999999, "amount": "10.00"})
        assert r2.status_code == 400
        assert "integrity error" in r2.json().get("detail", "").lower()
    finally:
        # Reset to safe for other tests
        client.post("/vulnerable?value=false")


def test_ui_toggle_button(client):
    # Using the TestClient fixture that wires an in-memory DB
    # Start in safe mode and ensure UI shows it
    client.post("/vulnerable?value=false")
    r = client.get("/ui")
    assert r.status_code == 200
    assert "Current: False" in r.text

    # Enable via form POST
    try:
        r2 = client.post("/vulnerable", data={"value": "true"})
        assert r2.status_code == 200
        r3 = client.get("/ui")
        assert "Current: True" in r3.text
    finally:
        client.post("/vulnerable?value=false")


def test_ui_toggle_affects_search(client):
    # Create users in this isolated DB
    client.post("/users", json={"name": "Carol"})
    client.post("/users", json={"name": "Dave"})

    # Safe mode: injection payload should not return results
    client.post("/vulnerable?value=false")
    resp = client.get("/search_vuln", params={"q": "' OR '1'='1"})
    assert resp.status_code == 200
    assert resp.json() == []

    # Enable via UI form and confirm injection returns rows
    try:
        client.post("/vulnerable", data={"value": "true"})
        resp2 = client.get("/search_vuln", params={"q": "' OR '1'='1"})
        assert resp2.status_code == 200
        names = {u["name"] for u in resp2.json()}
        assert "Carol" in names and "Dave" in names
    finally:
        client.post("/vulnerable?value=false")


def test_ajax_toggle_updates_ui(client):
    # Toggle using JSON (simulates AJAX) and verify the UI reflects it
    client.post("/vulnerable?value=false")
    r = client.get("/ui")
    assert "Current: False" in r.text

    # Simulate AJAX: POST JSON body
    r2 = client.post("/vulnerable", json={"value": True})
    assert r2.status_code == 200
    r3 = client.get("/ui")
    assert "Current: True" in r3.text

    # Reset
    client.post("/vulnerable?value=false")
