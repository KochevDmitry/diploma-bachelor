def test_login_success(client, registered_user):
    resp = client.post('/auth/login', json={
        'username': 'alice',
        'password': 'password123'
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['user']['username'] == 'alice'
    assert body['accessToken']
    assert body['refreshToken']


def test_login_wrong_password(client, registered_user):
    resp = client.post('/auth/login', json={
        'username': 'alice',
        'password': 'wrong-password'
    })
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post('/auth/login', json={
        'username': 'nobody',
        'password': 'whatever'
    })
    assert resp.status_code == 401


def test_login_missing_fields(client):
    resp = client.post('/auth/login', json={'username': 'alice'})
    assert resp.status_code == 400
