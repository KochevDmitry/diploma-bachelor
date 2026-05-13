def test_update_profile_returns_new_token(client, auth_headers):
    resp = client.put('/auth/profile', headers=auth_headers, json={
        'username': 'alice2',
        'bio': 'Люблю баскетбол'
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['user']['username'] == 'alice2'
    assert body['user']['bio'] == 'Люблю баскетбол'
    # При обновлении username возвращается новый access-токен, потому что
    # username попадает в payload — старый токен теперь "устарел" по полю.
    assert body['accessToken']


def test_update_profile_without_token(client):
    resp = client.put('/auth/profile', json={'username': 'whoever'})
    assert resp.status_code == 401


def test_update_profile_email_already_taken(client, auth_headers):
    # Заводим второго пользователя
    client.post('/auth/register', json={
        'username': 'bob',
        'email': 'bob@example.com',
        'password': 'password123'
    })
    resp = client.put('/auth/profile', headers=auth_headers, json={
        'email': 'bob@example.com'
    })
    assert resp.status_code == 400
    assert 'email' in resp.get_json()['error'].lower()


def test_update_profile_same_email_is_ok(client, auth_headers):
    """Передача того же email, что и сейчас — не должна считаться конфликтом."""
    resp = client.put('/auth/profile', headers=auth_headers, json={
        'email': 'alice@example.com',
        'bio': 'updated'
    })
    assert resp.status_code == 200
