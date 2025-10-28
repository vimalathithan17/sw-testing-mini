from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_user_detail_create_and_delete_order():
    # Create a user
    r = client.post('/users', json={'name': 'UDUser', 'email': 'ud@example.com'})
    assert r.status_code == 201
    uid = r.json()['id']

    # Visit user detail page
    r2 = client.get(f'/ui/users/{uid}')
    assert r2.status_code == 200
    assert 'UDUser' in r2.text

    # Create order via UI POST
    r3 = client.post(f'/ui/users/{uid}/orders', data={'user_id': uid, 'amount': '9.99'})
    # redirect on success
    assert r3.status_code in (303, 200)

    # Confirm order appears on user detail
    r4 = client.get(f'/ui/users/{uid}')
    assert '9.99' in r4.text

    # Delete order via API
    # find order id from orders endpoint
    orders = client.get('/orders').json()
    oids = [o['id'] for o in orders if o['user_id'] == uid]
    assert oids, 'no order created'
    oid = oids[0]

    delr = client.delete(f'/orders/{oid}')
    assert delr.status_code == 200

    # Confirm it's gone on the user page
    r5 = client.get(f'/ui/users/{uid}')
    assert '9.99' not in r5.text