def test_ui_renders(client):
    r = client.get("/ui")
    assert r.status_code == 200
    assert "SW Testing Mini" in r.text


def test_ui_create_user_and_order_flow(client):
    # Create user via UI form
    r = client.post("/ui/users", data={"name": "UI Alice", "email": "alice@example.com"}, allow_redirects=False)
    assert r.status_code in (303, 307)

    # Fetch UI and verify user appears
    r = client.get("/ui")
    assert "UI Alice" in r.text

    # Find user id via API for convenience
    r_users = client.get("/users")
    user = [u for u in r_users.json() if u["name"] == "UI Alice"][0]

    # Create order via UI
    r = client.post("/ui/orders", data={"user_id": user["id"], "amount": "7.235"}, allow_redirects=False)
    assert r.status_code in (303, 307)

    # Verify order shows in UI (rounded to 2 decimals)
    r = client.get("/ui")
    assert "7.24" in r.text


def test_ui_fk_violation_error_display(client):
    # Try to create order for non-existent user via UI
    r = client.post("/ui/orders", data={"user_id": 999999, "amount": "3.00"})
    assert r.status_code == 400
    assert "foreign key" in r.text.lower()


def test_ui_search_injection_like_input(client):
    # Seed a user
    client.post("/ui/users", data={"name": "Eve"}, allow_redirects=False)
    # Injection-like search should not dump all users
    payload = "%' OR '1'='1"
    r = client.get("/ui", params={"q": payload})
    assert r.status_code == 200
    # We expect 'No results' due to safe like filter
    assert "No results" in r.text
