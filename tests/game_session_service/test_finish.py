def test_finish_by_creator(client, creator, existing_session):
    resp = client.post(
        f'/api/games/{existing_session["id"]}/finish',
        json={'user_id': creator['id']}
    )
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'finished'


def test_finish_by_non_creator_forbidden(client, joiner, existing_session):
    resp = client.post(
        f'/api/games/{existing_session["id"]}/finish',
        json={'user_id': joiner['id']}
    )
    assert resp.status_code == 403


def test_finish_already_finished(client, creator, existing_session):
    sid = existing_session['id']
    client.post(f'/api/games/{sid}/finish', json={'user_id': creator['id']})
    resp = client.post(f'/api/games/{sid}/finish', json={'user_id': creator['id']})
    assert resp.status_code == 400


def test_finish_missing_user_id(client, existing_session):
    resp = client.post(f'/api/games/{existing_session["id"]}/finish', json={})
    assert resp.status_code == 400


def test_finish_unknown_session(client, creator):
    resp = client.post('/api/games/99999/finish', json={'user_id': creator['id']})
    assert resp.status_code == 404
