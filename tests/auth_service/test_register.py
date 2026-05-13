def test_register_success(client):
    resp = client.post('/auth/register', json={
        'username': 'bob',
        'email': 'bob@example.com',
        'password': 'secret123'
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['user']['username'] == 'bob'
    assert body['user']['email'] == 'bob@example.com'
    assert 'password' not in body['user']
    assert body['accessToken']
    assert body['refreshToken']


def test_register_missing_fields(client):
    resp = client.post('/auth/register', json={'username': 'bob'})
    assert resp.status_code == 400


def test_register_empty_body(client):
    resp = client.post('/auth/register', json={})
    assert resp.status_code == 400


def test_register_duplicate_username(client, registered_user):
    resp = client.post('/auth/register', json={
        'username': 'alice',
        'email': 'other@example.com',
        'password': 'password123'
    })
    assert resp.status_code == 400
    assert 'Username' in resp.get_json()['error']


def test_register_duplicate_email(client, registered_user):
    resp = client.post('/auth/register', json={
        'username': 'other',
        'email': 'alice@example.com',
        'password': 'password123'
    })
    assert resp.status_code == 400
    assert 'Email' in resp.get_json()['error']
