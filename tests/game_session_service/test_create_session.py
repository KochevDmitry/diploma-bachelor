import game_service_app as game_app  # модуль уже загружен в conftest


def test_create_session_success(client, creator):
    resp = client.post('/api/games', json={
        'creator_id': creator['id'],
        'latitude': 55.75,
        'longitude': 37.61,
        'sport_type': 'basketball',
        'max_players': 4,
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['creator_id'] == creator['id']
    assert body['sport_type'] == 'basketball'
    assert body['max_players'] == 4
    assert body['current_players'] == 1
    assert body['status'] == 'waiting'
    assert body['latitude'] == 55.75
    assert body['longitude'] == 37.61
    # Создание сессии с координатами должно дёрнуть задачу о рассылке
    # уведомлений ближайшим пользователям. Создатель должен передаваться
    # в задачу, чтобы она могла исключить его из рассылки.
    game_app.notify_new_session.delay.assert_called_once()
    args = game_app.notify_new_session.delay.call_args.args
    assert args[1] == 55.75 and args[2] == 37.61
    assert args[3] == 'basketball'
    assert args[4] == creator['id']


def test_create_session_missing_creator(client):
    resp = client.post('/api/games', json={'latitude': 55.7, 'longitude': 37.6})
    assert resp.status_code == 400


def test_create_session_missing_coords(client, creator):
    resp = client.post('/api/games', json={'creator_id': creator['id']})
    assert resp.status_code == 400
