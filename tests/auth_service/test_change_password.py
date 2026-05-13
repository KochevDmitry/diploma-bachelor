def test_change_password_success(client, auth_headers):
    resp = client.post('/auth/change-password', headers=auth_headers, json={
        'currentPassword': 'password123',
        'newPassword': 'new-password',
        'confirmPassword': 'new-password'
    })
    assert resp.status_code == 200

    # Старый пароль больше не работает
    old = client.post('/auth/login', json={
        'username': 'alice', 'password': 'password123'
    })
    assert old.status_code == 401

    # Новый — работает
    new = client.post('/auth/login', json={
        'username': 'alice', 'password': 'new-password'
    })
    assert new.status_code == 200


def test_change_password_wrong_current(client, auth_headers):
    resp = client.post('/auth/change-password', headers=auth_headers, json={
        'currentPassword': 'not-the-real-one',
        'newPassword': 'new-password',
        'confirmPassword': 'new-password'
    })
    assert resp.status_code == 400


def test_change_password_mismatch(client, auth_headers):
    resp = client.post('/auth/change-password', headers=auth_headers, json={
        'currentPassword': 'password123',
        'newPassword': 'aaaaaa',
        'confirmPassword': 'bbbbbb'
    })
    assert resp.status_code == 400


def test_change_password_too_short(client, auth_headers):
    resp = client.post('/auth/change-password', headers=auth_headers, json={
        'currentPassword': 'password123',
        'newPassword': '12345',
        'confirmPassword': '12345'
    })
    assert resp.status_code == 400


def test_change_password_no_token(client):
    resp = client.post('/auth/change-password', json={
        'currentPassword': 'password123',
        'newPassword': 'new-password',
        'confirmPassword': 'new-password'
    })
    assert resp.status_code == 401
