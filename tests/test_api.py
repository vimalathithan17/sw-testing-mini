from decimal import Decimal


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_user_and_order_flow(client):
    r = client.post("/users", json={"name": "Charlie"})
    assert r.status_code == 201
    user = r.json()

    r = client.post("/orders", json={"user_id": user["id"], "amount": "12.345"})
    assert r.status_code == 201
    order = r.json()
    assert order["amount"] == "12.35"

    r = client.get("/orders")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_fk_violation_returns_400(client):
    r = client.post("/orders", json={"user_id": 42, "amount": "9.99"})
    assert r.status_code == 400
    assert "foreign key" in r.json()["detail"]


def test_injection_attack_blocked(client):
    # Create two users
    client.post("/users", json={"name": "Eve"})
    client.post("/users", json={"name": "Mallory"})

    # Attempt SQL injection-like search
    payload = "%' OR '1'='1"
    r = client.get("/search", params={"q": payload})
    assert r.status_code == 200

    # Should not return all users due to proper parameterization; likely 0 matches
    assert r.json() == []
