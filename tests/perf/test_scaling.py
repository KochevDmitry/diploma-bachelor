"""Scaling-бенчмарки: смотрим как растёт латентность при росте данных.

Параметризуем по N=10/100/1000, в каждой группе получаем отдельную строку
в отчёте pytest-benchmark — на их основе можно построить график для диплома.
"""
import json
import pytest
from sqlalchemy import text


LAT, LON = 55.7558, 37.6173


SIZES = [10, 100, 1000]


def _bulk_insert_sessions(game_app_module, flask_app, creator_id, n,
                          status='waiting', lat=LAT, lon=LON):
    """Быстрая массовая вставка сессий напрямую в БД, минуя HTTP.

    Сами по себе POST /api/games в количестве 1000 шт. — это уже бенчмарк
    создания, а нам нужно засеять данные, не тратя время прогона на это.
    """
    with flask_app.app_context():
        # Одним statement через unnest — заметно быстрее построчных INSERT.
        game_app_module.db.session.execute(text("""
            INSERT INTO game_sessions
                (venue_id, creator_id, sport_type, max_players, current_players,
                 status, latitude, longitude, location, created_at)
            SELECT
                NULL, :creator_id, 'football', 10, 1,
                :status, :lat, :lon,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                NOW() - (g || ' seconds')::interval
            FROM generate_series(1, :n) g
        """), {'creator_id': creator_id, 'status': status,
               'lat': lat, 'lon': lon, 'n': n})
        game_app_module.db.session.commit()


def _bulk_insert_users_with_location(game_app_module, flask_app, n,
                                     center_lat=LAT, center_lon=LON):
    """Засеваем N пользователей с notification_location вокруг точки —
    нужно для бенча notify_new_session (ST_DWithin)."""
    with flask_app.app_context():
        # Распределяем по сетке ~±0.01° вокруг центра — это ~1 км, попадают
        # в радиус 2 км из notify_new_session. mod() избегает оператора %,
        # который конфликтует с биндингами psycopg2 в text().
        game_app_module.db.session.execute(text("""
            INSERT INTO users (username, email, password_hash, notification_location, notify_own_games)
            SELECT
                'nearby_' || g,
                'nearby_' || g || '@example.com',
                'x',
                ST_SetSRID(
                    ST_MakePoint(
                        :lon + (mod(g, 100) - 50) * 0.0001,
                        :lat + (mod(g / 100, 100) - 50) * 0.0001
                    ),
                    4326
                )::geography,
                true
            FROM generate_series(1, :n) g
        """), {'lat': center_lat, 'lon': center_lon, 'n': n})
        game_app_module.db.session.commit()


@pytest.mark.parametrize('n', SIZES)
def test_perf_user_history_scaling(game_client, make_user, game_flask_app, n,
                                   benchmark):
    """GET /api/games/user/<id>/history при N созданных сессий.

    Здесь два запроса (created + participations) и цикл to_dict, в котором
    для каждой сессии читается Redis. Интересно как растёт время от N.
    """
    # Импортируем модуль из уже загруженного sys.modules — это тот же
    # game_app, что и в conftest, чтобы не плодить второй SQLAlchemy.
    import sys
    game_app_module = sys.modules['game_service_app']

    creator_id = make_user(username='hist_creator')
    _bulk_insert_sessions(game_app_module, game_flask_app, creator_id, n)

    def run():
        r = game_client.get(f'/api/games/user/{creator_id}/history')
        assert r.status_code == 200
        body = r.get_json()
        assert len(body) == n

    benchmark.group = f'user_history(N={n})'
    benchmark.pedantic(run, rounds=20, iterations=1, warmup_rounds=2)


@pytest.mark.parametrize('n', SIZES)
def test_perf_map_sessions_scaling(game_client, make_user, game_flask_app, n,
                                   benchmark):
    """GET /api/games/map при N активных сессий на карте.

    Полный скан active-сессий + to_dict для каждой (Redis на каждую).
    """
    import sys
    game_app_module = sys.modules['game_service_app']

    creator_id = make_user(username='map_creator')
    _bulk_insert_sessions(game_app_module, game_flask_app, creator_id, n,
                          status='waiting')

    def run():
        r = game_client.get('/api/games/map')
        assert r.status_code == 200
        body = r.get_json()
        assert len(body) == n

    benchmark.group = f'map_sessions(N={n})'
    benchmark.pedantic(run, rounds=20, iterations=1, warmup_rounds=2)


@pytest.mark.parametrize('n', SIZES)
def test_perf_notify_new_session_scaling(game_flask_app, make_user, n,
                                         benchmark):
    """Celery-таск notify_new_session при N пользователях с notification_location.

    Это ST_DWithin поверх таблицы users (GIST-индекс по geography) + цикл
    с INSERT в notifications и Redis publish на каждого найденного юзера.
    Запускаем функцию синхронно (минуя брокер).
    """
    import sys
    game_app_module = sys.modules['game_service_app']

    creator_id = make_user(username='notify_creator')
    _bulk_insert_users_with_location(game_app_module, game_flask_app, n)

    # Создаём одну сессию, чтобы был валидный session_id для FK в notifications.
    with game_flask_app.app_context():
        result = game_app_module.db.session.execute(text("""
            INSERT INTO game_sessions
                (creator_id, sport_type, max_players, current_players,
                 status, latitude, longitude, location)
            VALUES (:cid, 'football', 10, 1, 'waiting', :lat, :lon,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)
            RETURNING id
        """), {'cid': creator_id, 'lat': LAT, 'lon': LON})
        session_id = result.scalar()
        game_app_module.db.session.commit()

    # Получаем функцию-обёртку Celery. Можно вызывать как обычную функцию —
    # тело уже создаёт app_context внутри себя.
    notify = game_app_module.notify_new_session

    def run():
        # .run() обходит .delay() (который мы замокали) и зовёт тело таска
        # синхронно — это то, что нам и нужно для замера.
        notify.run(session_id, LAT, LON, 'football', creator_id)
        # Чистим notifications, чтобы вторая итерация не разрослась.
        with game_flask_app.app_context():
            game_app_module.db.session.execute(text(
                'TRUNCATE notifications RESTART IDENTITY'
            ))
            game_app_module.db.session.commit()

    benchmark.group = f'notify_new_session(N={n})'
    benchmark.pedantic(run, rounds=10, iterations=1, warmup_rounds=1)
