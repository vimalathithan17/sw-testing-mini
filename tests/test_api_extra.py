import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_delete_order_and_user_flow():
    # Create user
    r1 = client.post("/users", json={"name": "DelUser"})
    assert r1.status_code == 201
    uid = r1.json()["id"]

    # Create order
    r2 = client.post("/orders", json={"user_id": uid, "amount": "5.00"})
    assert r2.status_code == 201
    oid = r2.json()["id"]

    # Delete order
    r3 = client.delete(f"/orders/{oid}")
    assert r3.status_code == 200
    assert r3.json()["deleted"] == oid

    # Delete user
    r4 = client.delete(f"/users/{uid}")
    assert r4.status_code == 200
    assert r4.json()["deleted"] == uid

    # Deleting again should return 404
    r5 = client.delete(f"/users/{uid}")
    assert r5.status_code == 404