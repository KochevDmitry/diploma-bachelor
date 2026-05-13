def test_update_max_players_by_creator(client, creator, existing_session):
    resp = client.post(
        f'/api/games/{existing_session["id"]}/update',
        json={'user_id': creator['id'], 'max_players': 10}
    )
    assert resp.status_code == 200
    assert resp.get_json()['max_players'] == 10


def test_update_by_non_creator_forbidden(client, joiner, existing_session):
    resp = client.post(
        f'/api/games/{existing_session["id"]}/update',
        json={'user_id': joiner['id'], 'max_players': 10}
    )
    assert resp.status_code == 403


def test_update_cannot_set_below_current_players(client, creator, joiner, existing_session):
    """В сессии уже 2 игрока (создатель + joiner). Понизить max_players
    до 2 нельзя — это сразу сделает её полной без места для новых, что
    нарушает условие 'строго больше current_players'."""
    sid = existing_session['id']
    client.post(f'/api/games/{sid}/join', json={'user_id': joiner['id']})

    resp = client.post(
        f'/api/games/{sid}/update',
        json={'user_id': creator['id'], 'max_players': 2}
    )
    assert resp.status_code == 400


def test_update_finished_session(client, creator, existing_session):
    sid = existing_session['id']
    client.post(f'/api/games/{sid}/finish', json={'user_id': creator['id']})
    resp = client.post(
        f'/api/games/{sid}/update',
        json={'user_id': creator['id'], 'max_players': 5}
    )
    assert resp.status_code == 400
