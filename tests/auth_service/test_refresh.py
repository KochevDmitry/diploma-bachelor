def test_refresh_success(client, registered_user):
    resp = client.post('/auth/refresh', json={
        'refreshToken': registered_user['refreshToken']
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['accessToken']
    # Новый access-токен пригоден для защищённых ручек
    verify = client.get(
        '/auth/verify',
        headers={'Authorization': f'Bearer {body["accessToken"]}'}
    )
    assert verify.status_code == 200


def test_refresh_rejects_access_token(client, registered_user):
    """Подставить access вместо refresh нельзя — проверяется поле type в payload."""
    resp = client.post('/auth/refresh', json={
        'refreshToken': registered_user['accessToken']
    })
    assert resp.status_code == 401


def test_refresh_missing(client):
    resp = client.post('/auth/refresh', json={})
    assert resp.status_code == 401


def test_refresh_invalid(client):
    resp = client.post('/auth/refresh', json={'refreshToken': 'garbage'})
    assert resp.status_code == 401
