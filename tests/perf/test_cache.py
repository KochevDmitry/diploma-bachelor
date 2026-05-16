"""Бенчмарк эффекта Redis-кеша: hit vs miss.

Объект — `get_session_participants` (services/game_session_service/app.py:117).
Hit-путь: одно SMEMBERS из Redis.
Miss-путь: тот же SMEMBERS (пусто) + SELECT game_sessions по id + SELECT
session_participants по session_id + SADD + EXPIRE для прогрева.

Сценарий специально без HTTP-обёртки — мы хотим изолировано измерить
именно функцию кеша, без шума от Flask / роутинга.

Важно: используется НАСТОЯЩИЙ Redis (контейнер redis_test, см.
tests/docker-compose.test.yml), а не fakeredis. Иначе hit-путь измерял бы
просто in-process вызов Python-функции, без сетевого раунд-трипа и
RESP-сериализации, и абсолютная цифра была бы на порядок занижена.
"""
import sys
import pytest
from sqlalchemy import text


LAT, LON = 55.7558, 37.6173


@pytest.fixture
def session_with_participants(game_flask_app, make_user):
    """Создаёт сессию с creator и 5 присоединившимися участниками."""
    game_app_module = sys.modules['game_service_app']
    creator_id = make_user(username='cache_creator')

    with game_flask_app.app_context():
        result = game_app_module.db.session.execute(text("""
            INSERT INTO game_sessions
                (creator_id, sport_type, max_players, current_players,
                 status, latitude, longitude, location)
            VALUES (:cid, 'football', 10, 6, 'waiting', :lat, :lon,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)
            RETURNING id
        """), {'cid': creator_id, 'lat': LAT, 'lon': LON})
        session_id = result.scalar()

        for i in range(5):
            uid = make_user(username=f'cache_joiner_{i}')
            game_app_module.db.session.execute(text("""
                INSERT INTO session_participants (session_id, user_id)
                VALUES (:sid, :uid)
            """), {'sid': session_id, 'uid': uid})
        game_app_module.db.session.commit()

    return session_id


def test_perf_participants_cache_hit(session_with_participants, game_flask_app,
                                     real_redis, benchmark):
    """Кеш прогрет → SMEMBERS из Redis, без обращения к PG."""
    game_app_module = sys.modules['game_service_app']
    sid = session_with_participants

    # Прогреваем кеш одним вызовом — он сам положит участников в Redis.
    with game_flask_app.app_context():
        game_app_module.get_session_participants(sid)

    def run():
        with game_flask_app.app_context():
            participants = game_app_module.get_session_participants(sid)
            assert len(participants) == 6

    benchmark.group = 'participants_cache'
    benchmark.pedantic(run, rounds=200, iterations=1, warmup_rounds=5)


def test_perf_participants_cache_miss(session_with_participants, game_flask_app,
                                      real_redis, benchmark):
    """Кеш холодный → fallback в PG (2 запроса) + прогрев Redis."""
    game_app_module = sys.modules['game_service_app']
    sid = session_with_participants

    def run():
        # Принудительно сбрасываем ключ перед каждой итерацией, чтобы это был
        # именно miss, а не hit после первого прогона.
        real_redis.delete(f'session:{sid}:participants')
        with game_flask_app.app_context():
            participants = game_app_module.get_session_participants(sid)
            assert len(participants) == 6

    benchmark.group = 'participants_cache'
    benchmark.pedantic(run, rounds=100, iterations=1, warmup_rounds=2)
