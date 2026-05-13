def test_verify_with_access_token(client, registered_user):
    resp = client.get(
        '/auth/verify',
        headers={'Authorization': f'Bearer {registered_user["accessToken"]}'}
    )
    assert resp.status_code == 200
    assert resp.get_json()['user']['username'] == 'alice'


def test_verify_no_token(client):
    resp = client.get('/auth/verify')
    assert resp.status_code == 401


def test_verify_invalid_token(client):
    resp = client.get('/auth/verify', headers={'Authorization': 'Bearer garbage'})
    assert resp.status_code == 401


def test_verify_rejects_refresh_token(client, registered_user):
    """В /auth/verify должен идти access-токен. Refresh — отдельный поток
    через /auth/refresh, перепутать их нельзя."""
    resp = client.get(
        '/auth/verify',
        headers={'Authorization': f'Bearer {registered_user["refreshToken"]}'}
    )
    assert resp.status_code == 401
