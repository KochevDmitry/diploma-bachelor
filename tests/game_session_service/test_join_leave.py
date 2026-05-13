import game_service_app as game_app  # модуль уже загружен в conftest


def test_join_success(client, joiner, existing_session):
    resp = client.post(
        f'/api/games/{existing_session["id"]}/join',
        json={'user_id': joiner['id']}
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['current_players'] == 2
    assert joiner['id'] in body['participants']
    # Создатель должен получить уведомление о новом участнике
    game_app.notify_participant_joined.delay.assert_called_once()


def test_join_twice_forbidden(client, joiner, existing_session):
    sid = existing_session['id']
    client.post(f'/api/games/{sid}/join', json={'user_id': joiner['id']})
    resp = client.post(f'/api/games/{sid}/join', json={'user_id': joiner['id']})
    assert resp.status_code == 400
    assert 'already' in resp.get_json()['error'].lower()


def test_join_missing_user_id(client, existing_session):
    resp = client.post(f'/api/games/{existing_session["id"]}/join', json={})
    assert resp.status_code == 400


def test_join_unknown_session(client, joiner):
    resp = client.post('/api/games/99999/join', json={'user_id': joiner['id']})
    assert resp.status_code == 404


def test_join_full_session(client, creator, flask_app):
    """Сессия на 2 человека: после второго входа статус full, третий не войдёт."""
    create = client.post('/api/games', json={
        'creator_id': creator['id'],
        'latitude': 55.75,
        'longitude': 37.61,
        'max_players': 2,
    })
    sid = create.get_json()['id']

    # Готовим второго и третьего пользователей
    from sqlalchemy import text
    with flask_app.app_context():
        u2 = game_app.db.session.execute(text(
            "INSERT INTO users (username, email, password_hash) "
            "VALUES ('u2', 'u2@x', 'x') RETURNING id"
        )).scalar()
        u3 = game_app.db.session.execute(text(
            "INSERT INTO users (username, email, password_hash) "
            "VALUES ('u3', 'u3@x', 'x') RETURNING id"
        )).scalar()
        game_app.db.session.commit()

    r2 = client.post(f'/api/games/{sid}/join', json={'user_id': u2})
    assert r2.status_code == 200
    assert r2.get_json()['status'] == 'full'

    r3 = client.post(f'/api/games/{sid}/join', json={'user_id': u3})
    assert r3.status_code == 400


def test_leave_success(client, joiner, existing_session):
    sid = existing_session['id']
    client.post(f'/api/games/{sid}/join', json={'user_id': joiner['id']})

    resp = client.post(f'/api/games/{sid}/leave', json={'user_id': joiner['id']})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['current_players'] == 1
    assert joiner['id'] not in body['participants']
    game_app.notify_participant_left.delay.assert_called_once()


def test_leave_creator_forbidden(client, creator, existing_session):
    """Создатель не может выйти из своей сессии — для этого есть finish."""
    resp = client.post(
        f'/api/games/{existing_session["id"]}/leave',
        json={'user_id': creator['id']}
    )
    assert resp.status_code == 400


def test_leave_missing_user_id(client, existing_session):
    resp = client.post(f'/api/games/{existing_session["id"]}/leave', json={})
    assert resp.status_code == 400
