def test_history_empty_for_new_user(client, creator):
    resp = client.get(f'/api/games/user/{creator["id"]}/history')
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_history_includes_created_session(client, creator, existing_session):
    resp = client.get(f'/api/games/user/{creator["id"]}/history')
    assert resp.status_code == 200
    history = resp.get_json()
    assert len(history) == 1
    assert history[0]['id'] == existing_session['id']
    assert history[0]['is_creator'] is True


def test_history_includes_joined_session(client, joiner, existing_session):
    client.post(
        f'/api/games/{existing_session["id"]}/join',
        json={'user_id': joiner['id']}
    )
    resp = client.get(f'/api/games/user/{joiner["id"]}/history')
    history = resp.get_json()
    assert len(history) == 1
    assert history[0]['id'] == existing_session['id']
    assert history[0]['is_creator'] is False


def test_history_separates_created_and_joined(client, creator, joiner, existing_session):
    """Один и тот же пользователь может попасть в обе категории по разным
    сессиям — флаг is_creator должен корректно отражать роль в каждой."""
    # Вторая сессия — joiner создаёт сам
    own = client.post('/api/games', json={
        'creator_id': joiner['id'],
        'latitude': 55.7, 'longitude': 37.6,
    }).get_json()
    # И в первой он же — участник
    client.post(
        f'/api/games/{existing_session["id"]}/join',
        json={'user_id': joiner['id']}
    )

    history = client.get(f'/api/games/user/{joiner["id"]}/history').get_json()
    by_id = {h['id']: h for h in history}
    assert by_id[own['id']]['is_creator'] is True
    assert by_id[existing_session['id']]['is_creator'] is False
