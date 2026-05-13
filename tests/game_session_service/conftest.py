"""Общие фикстуры для тестов game_session_service.

Особенности:
- Redis в тестах подменяем на in-process fakeredis — реальный Redis не нужен.
- Celery-задачи `.delay()` мокаются: иначе они попытаются достучаться до
  RabbitMQ и провалятся. В отдельных тестах мок можно проинспектировать,
  чтобы убедиться, что задача была поставлена с правильными аргументами.
- БД — реальный PostgreSQL+PostGIS из tests/docker-compose.test.yml.
  Чисто SQLite нельзя: код использует PostGIS-типы и функции (ST_DWithin,
  Geography), которые SQLite не поддерживает.
"""
import os
import sys
import importlib.util
import pytest
import fakeredis
from sqlalchemy import text
from unittest.mock import MagicMock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SERVICE_DIR = os.path.join(REPO_ROOT, 'services', 'game_session_service')
# celery_config.py лежит рядом с app.py и импортируется относительно — добавим
# каталог сервиса в sys.path, чтобы этот относительный импорт сработал.
if SERVICE_DIR not in sys.path:
    sys.path.insert(0, SERVICE_DIR)

os.environ['DATABASE_URL'] = os.getenv(
    'TEST_DATABASE_URL',
    'postgresql://test:test@localhost:55432/test_db'
)
# Бутафорские значения — реальные брокеры в тестах не дёргаются:
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')

# Грузим под уникальным именем (см. комментарий в auth_service/conftest.py).
_spec = importlib.util.spec_from_file_location(
    'game_service_app', os.path.join(SERVICE_DIR, 'app.py')
)
game_app = importlib.util.module_from_spec(_spec)
sys.modules['game_service_app'] = game_app
_spec.loader.exec_module(game_app)


@pytest.fixture(scope='session')
def flask_app():
    game_app.app.config['TESTING'] = True
    return game_app.app


@pytest.fixture(autouse=True)
def patch_redis_and_celery(monkeypatch):
    """Подменяем Redis на fakeredis и .delay() у Celery-задач — на MagicMock.

    После теста monkeypatch автоматически откатит изменения. MagicMock
    сохраняет вызовы, так что отдельные тесты могут проверить, что
    конкретная задача была действительно поставлена с нужными аргументами.
    """
    fake = fakeredis.FakeStrictRedis()
    monkeypatch.setattr(game_app, 'redis_client', fake)

    for task_name in (
        'notify_new_session',
        'notify_participant_joined',
        'notify_participant_left',
        'notify_session_update',
    ):
        task = getattr(game_app, task_name)
        monkeypatch.setattr(task, 'delay', MagicMock())


@pytest.fixture(autouse=True)
def clean_db(flask_app):
    """TRUNCATE с CASCADE удаляет связанные строки в game_sessions /
    session_participants по FK."""
    with flask_app.app_context():
        game_app.db.session.execute(text(
            'TRUNCATE users, game_sessions, session_participants '
            'RESTART IDENTITY CASCADE'
        ))
        game_app.db.session.commit()
    yield


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture
def creator(flask_app):
    """Создаёт фиктивного пользователя-создателя сессии."""
    with flask_app.app_context():
        result = game_app.db.session.execute(text("""
            INSERT INTO users (username, email, password_hash, notify_own_games)
            VALUES ('creator', 'creator@example.com', 'x', true)
            RETURNING id
        """))
        user_id = result.scalar()
        game_app.db.session.commit()
    return {'id': user_id, 'username': 'creator'}


@pytest.fixture
def joiner(flask_app):
    """Создаёт второго пользователя — для тестов join/leave."""
    with flask_app.app_context():
        result = game_app.db.session.execute(text("""
            INSERT INTO users (username, email, password_hash, notify_own_games)
            VALUES ('joiner', 'joiner@example.com', 'x', true)
            RETURNING id
        """))
        user_id = result.scalar()
        game_app.db.session.commit()
    return {'id': user_id, 'username': 'joiner'}


@pytest.fixture
def existing_session(client, creator):
    """Готовая игровая сессия от creator с координатами в центре Москвы."""
    resp = client.post('/api/games', json={
        'creator_id': creator['id'],
        'latitude': 55.7558,
        'longitude': 37.6173,
        'sport_type': 'football',
        'max_players': 4,
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()
