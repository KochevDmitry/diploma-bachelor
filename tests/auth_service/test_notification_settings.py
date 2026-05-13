def test_set_notification_location(client, auth_headers):
    resp = client.post('/auth/notification-location', headers=auth_headers, json={
        'lat': 55.7558, 'lon': 37.6173
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['notification_location'] == {'lat': 55.7558, 'lon': 37.6173}
    assert body['user']['notification_location']['lat'] == 55.7558


def test_set_notification_location_invalid_coords(client, auth_headers):
    resp = client.post('/auth/notification-location', headers=auth_headers, json={
        'lat': 'not-a-number', 'lon': 37.6
    })
    assert resp.status_code == 400


def test_set_notification_location_missing(client, auth_headers):
    resp = client.post('/auth/notification-location', headers=auth_headers, json={
        'lat': 55.7
    })
    assert resp.status_code == 400


def test_delete_notification_location(client, auth_headers):
    client.post('/auth/notification-location', headers=auth_headers, json={
        'lat': 55.7558, 'lon': 37.6173
    })
    resp = client.delete('/auth/notification-location', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['user']['notification_location'] is None


def test_toggle_notify_own_games(client, auth_headers):
    resp = client.put('/auth/notify-own-games', headers=auth_headers, json={
        'enabled': False
    })
    assert resp.status_code == 200
    assert resp.get_json()['user']['notify_own_games'] is False

    resp = client.put('/auth/notify-own-games', headers=auth_headers, json={
        'enabled': True
    })
    assert resp.status_code == 200
    assert resp.get_json()['user']['notify_own_games'] is True


def test_notification_settings_require_auth(client):
    assert client.put('/auth/notify-own-games', json={'enabled': False}).status_code == 401
    assert client.post('/auth/notification-location', json={'lat': 1, 'lon': 1}).status_code == 401
    assert client.delete('/auth/notification-location').status_code == 401
