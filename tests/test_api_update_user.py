import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_update_user_api():
    # create user
    r = client.post('/users', json={'name': 'UpUser', 'email': 'old@example.com'})
    assert r.status_code == 201
    uid = r.json()['id']

    # update
    r2 = client.put(f'/users/{uid}', json={'name': 'Updated', 'email': 'new@example.com'})
    assert r2.status_code == 200
    data = r2.json()
    assert data['name'] == 'Updated'
    assert data['email'] == 'new@example.com'

    # get detail
    r3 = client.get(f'/users/{uid}')
    assert r3.status_code == 200
    assert r3.json()['name'] == 'Updated'