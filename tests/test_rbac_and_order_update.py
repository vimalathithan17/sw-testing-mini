import pytest

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_role_change_requires_admin():
    # create admin and normal user
    r = client.post('/users', json={'name': 'Admin', 'role': 'admin', 'password': 'adminpass'})
    assert r.status_code == 201
    admin_id = r.json()['id']

    r2 = client.post('/users', json={'name': 'Regular', 'role': 'user', 'password': 'userpass'})
    assert r2.status_code == 201
    user_id = r2.json()['id']

    # regular user cannot change roles (before promotion)
    token_regular = client.post('/auth/login', json={'user_id': user_id, 'password': 'userpass'}).json()['access_token']
    resp_forbid = client.put(f'/users/{admin_id}', json={'role':'user'}, headers={'Authorization': f'Bearer {token_regular}'})
    assert resp_forbid.status_code == 403

    # get token for admin and promote regular -> admin
    token = client.post('/auth/login', json={'user_id': admin_id, 'password': 'adminpass'}).json()['access_token']
    resp = client.put(f'/users/{user_id}', json={'role':'admin'}, headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    assert resp.json()['role'] == 'admin'


def test_order_update_authorization():
    # create owner and other user and admin
    r1 = client.post('/users', json={'name': 'Owner', 'password': 'ownpass'})
    owner_id = r1.json()['id']
    r2 = client.post('/users', json={'name': 'Other', 'password': 'otherpass'})
    other_id = r2.json()['id']
    r3 = client.post('/users', json={'name': 'Admin2', 'role': 'admin', 'password': 'admin2pass'})
    admin_id = r3.json()['id']

    # create order for owner
    r = client.post('/orders', json={'user_id': owner_id, 'amount': '5.00'})
    assert r.status_code == 201
    order_id = r.json()['id']

    # owner updates order
    token_owner = client.post('/auth/login', json={'user_id': owner_id, 'password': 'ownpass'}).json()['access_token']
    resp = client.put(f'/orders/{order_id}', json={'amount':'6.00'}, headers={'Authorization': f'Bearer {token_owner}'})
    assert resp.status_code == 200
    assert resp.json()['amount'] == '6.00' or float(resp.json()['amount']) == 6.0

    # other user cannot update
    token_other = client.post('/auth/login', json={'user_id': other_id, 'password': 'otherpass'}).json()['access_token']
    resp2 = client.put(f'/orders/{order_id}', json={'amount':'7.00'}, headers={'Authorization': f'Bearer {token_other}'})
    assert resp2.status_code == 403

    # admin can update
    token_admin = client.post('/auth/login', json={'user_id': admin_id, 'password': 'admin2pass'}).json()['access_token']
    resp3 = client.put(f'/orders/{order_id}', json={'amount':'8.00'}, headers={'Authorization': f'Bearer {token_admin}'})
    assert resp3.status_code == 200
    assert resp3.json()['amount'] == '8.00' or float(resp3.json()['amount']) == 8.0
