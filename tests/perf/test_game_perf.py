"""Бенчмарки game_session_service.

Все сессии создаются по координатам (latitude/longitude) без привязки к
площадке — venue в дипломе игнорируется.
"""
import pytest


# Москва — координаты по умолчанию для всех бенчей.
LAT, LON = 55.7558, 37.6173


def _create_session(client, creator_id, lat=LAT, lon=LON, max_players=10):
    resp = client.post('/api/games', json={
        'creator_id': creator_id,
        'latitude': lat,
        'longitude': lon,
        'sport_type': 'football',
        'max_players': max_players,
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def test_perf_create_session(game_client, make_user, benchmark):
    """Создание сессии: INSERT с PostGIS-точкой + Redis sadd + Celery enqueue (mocked)."""
    creator_id = make_user(username='creator')

    def run():
        _create_session(game_client, creator_id)

    benchmark.pedantic(run, rounds=50, iterations=1, warmup_rounds=2)


def test_perf_get_session(game_client, make_user, benchmark):
    """Получение одной сессии: SELECT + чтение участников из Redis."""
    creator_id = make_user(username='creator')
    session = _create_session(game_client, creator_id)
    sid = session['id']

    def run():
        r = game_client.get(f'/api/games/{sid}')
        assert r.status_code == 200

    benchmark.pedantic(run, rounds=200, iterations=1, warmup_rounds=2)


def test_perf_join_session(game_client, make_user, benchmark):
    """Join: SELECT сессии + INSERT participant + UPDATE сессии + Redis sadd.

    На каждой итерации нужна свежая сессия и свежий пользователь, иначе
    после первого join сессия станет full / повторный join вернёт ошибку.
    """
    creator_id = make_user(username='creator_join')
    state = {'sid': None, 'uid': None}
    counter = iter(range(10**6))

    def setup():
        i = next(counter)
        session = _create_session(game_client, creator_id, max_players=10)
        state['sid'] = session['id']
        state['uid'] = make_user(username=f'joiner_{i}')

    def run():
        r = game_client.post(f"/api/games/{state['sid']}/join",
                             json={'user_id': state['uid']})
        assert r.status_code == 200, r.get_json()

    benchmark.pedantic(run, setup=setup, rounds=30, iterations=1, warmup_rounds=2)


def test_perf_leave_session(game_client, make_user, benchmark):
    """Leave: DELETE participant + UPDATE сессии + Redis sadd (полная перезапись)."""
    creator_id = make_user(username='creator_leave')
    state = {'sid': None, 'uid': None}
    counter = iter(range(10**6))

    def setup():
        i = next(counter)
        session = _create_session(game_client, creator_id, max_players=10)
        uid = make_user(username=f'leaver_{i}')
        game_client.post(f"/api/games/{session['id']}/join", json={'user_id': uid})
        state['sid'] = session['id']
        state['uid'] = uid

    def run():
        r = game_client.post(f"/api/games/{state['sid']}/leave",
                             json={'user_id': state['uid']})
        assert r.status_code == 200

    benchmark.pedantic(run, setup=setup, rounds=30, iterations=1, warmup_rounds=2)


def test_perf_finish_session(game_client, make_user, benchmark):
    """Finish: UPDATE сессии + Redis delete."""
    creator_id = make_user(username='creator_finish')
    state = {'sid': None}

    def setup():
        session = _create_session(game_client, creator_id)
        state['sid'] = session['id']

    def run():
        r = game_client.post(f"/api/games/{state['sid']}/finish",
                             json={'user_id': creator_id})
        assert r.status_code == 200

    benchmark.pedantic(run, setup=setup, rounds=50, iterations=1, warmup_rounds=2)


def test_perf_update_session_max_players(game_client, make_user, benchmark):
    """Update max_players: SELECT + UPDATE + Redis delete."""
    creator_id = make_user(username='creator_update')
    session = _create_session(game_client, creator_id, max_players=4)
    sid = session['id']

    state = {'mp': 4}

    def run():
        state['mp'] = 6 if state['mp'] == 4 else 4
        r = game_client.post(f"/api/games/{sid}/update",
                             json={'user_id': creator_id,
                                   'max_players': state['mp']})
        assert r.status_code == 200

    benchmark.pedantic(run, rounds=100, iterations=1, warmup_rounds=2)
