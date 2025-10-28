from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_password_login_flow():
    # create a user with password
    r = client.post('/users', json={'name': 'PwUser', 'password': 'secret'})
    assert r.status_code == 201
    uid = r.json()['id']

    # login with wrong password
    r2 = client.post('/auth/login', json={'user_id': uid, 'password': 'wrong'})
    assert r2.status_code == 401

    # login with correct password
    r3 = client.post('/auth/login', json={'user_id': uid, 'password': 'secret'})
    assert r3.status_code == 200
    assert 'access_token' in r3.json()
