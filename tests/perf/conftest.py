"""Фикстуры для перформанс-тестов.

Поднимаем оба Flask-приложения (auth_service и game_session_service) в одном
процессе на той же тестовой БД, что и интеграционные тесты. Redis подменяем
на fakeredis, .delay() у Celery-задач мокается — мы измеряем латентность
синхронной части обработки запроса, а не работу брокера.

Замечание про модули: оба сервиса лежат в файлах с именем `app.py`, поэтому
грузим их через importlib под уникальными именами. Дополнительно регистрируем
`game_service_app` ещё и как `app` в sys.modules — Celery-таски внутри
game_session_service делают `from app import app as flask_app`, и без алиаса
это импортировало бы второй экземпляр модуля с отдельным SQLAlchemy-контекстом.
"""
import os
import sys
import tempfile
import importlib.util
import pytest
import fakeredis
from sqlalchemy import text
from unittest.mock import MagicMock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
AUTH_DIR = os.path.join(REPO_ROOT, 'services', 'auth_service')
GAME_DIR = os.path.join(REPO_ROOT, 'services', 'game_session_service')

os.environ['DATABASE_URL'] = os.getenv(
    'TEST_DATABASE_URL',
    'postgresql://test:test@localhost:55432/test_db'
)
os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
os.environ['JWT_ACCESS_TOKEN_EXPIRES'] = '3600'
os.environ['JWT_REFRESH_TOKEN_EXPIRES'] = '604800'
os.environ['UPLOAD_FOLDER'] = tempfile.mkdtemp(prefix='perf_avatars_')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')

if GAME_DIR not in sys.path:
    sys.path.insert(0, GAME_DIR)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


auth_app = _load('auth_service_app', os.path.join(AUTH_DIR, 'app.py'))
game_app = _load('game_service_app', os.path.join(GAME_DIR, 'app.py'))
# Celery-таски в game_app делают `from app import app` — алиасим, чтобы они
# получали тот же модуль, а не загружали повторно.
sys.modules['app'] = game_app


@pytest.fixture(scope='session', autouse=True)
def _ensure_notifications_table():
    """init-db.sql из тестового compose не создаёт notifications — её добавляет
    миграция 002. notify_new_session пишет в эту таблицу, поэтому создаём её
    один раз на сессию тестов."""
    with game_app.app.app_context():
        game_app.db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                type VARCHAR(50) NOT NULL,
                title VARCHAR(255) NOT NULL,
                message TEXT,
                session_id INTEGER,
                read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        game_app.db.session.commit()


@pytest.fixture(scope='session')
def auth_flask_app():
    auth_app.app.config['TESTING'] = True
    return auth_app.app


@pytest.fixture(scope='session')
def game_flask_app():
    game_app.app.config['TESTING'] = True
    return game_app.app


@pytest.fixture(autouse=True)
def patch_redis_and_celery(monkeypatch):
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
    return fake


@pytest.fixture(autouse=True)
def clean_db(game_flask_app):
    """Чистим обе схемы перед каждым бенчем — стартовое состояние должно быть
    воспроизводимым, иначе медианы поплывут от прогона к прогону."""
    with game_flask_app.app_context():
        game_app.db.session.execute(text(
            'TRUNCATE users, game_sessions, session_participants, notifications '
            'RESTART IDENTITY CASCADE'
        ))
        game_app.db.session.commit()
    yield


@pytest.fixture
def auth_client(auth_flask_app):
    return auth_flask_app.test_client()


@pytest.fixture
def game_client(game_flask_app):
    return game_flask_app.test_client()


@pytest.fixture
def real_redis(monkeypatch, patch_redis_and_celery):
    """Подменяет fakeredis на НАСТОЯЩИЙ Redis на localhost:56379.

    Нужно только для замера абсолютной задержки кеш-операций
    (tests/perf/test_cache.py). Все остальные перф-тесты этот fixture не
    запрашивают и остаются на fakeredis — там Redis не доминирует во времени
    запроса и реальный сетевой раунд-трип не имеет смысла мерить.

    Зависит от patch_redis_and_celery, чтобы гарантированно отработать ПОСЛЕ
    него и перекрыть его подмену redis_client.

    Если контейнер redis_test не поднят — тест скипается, а не падает: это
    оставляет основной набор тестов запускаемым без перф-инфраструктуры.
    """
    import redis as redis_lib
    client = redis_lib.Redis(host='localhost', port=56379, db=0,
                             socket_connect_timeout=1)
    try:
        client.ping()
    except (redis_lib.ConnectionError, redis_lib.TimeoutError):
        pytest.skip(
            'Real Redis для перф-тестов не поднят. Запусти: '
            'docker compose -f tests/docker-compose.test.yml up -d redis_test'
        )
    client.flushdb()
    monkeypatch.setattr(game_app, 'redis_client', client)
    yield client
    client.flushdb()


@pytest.fixture
def make_user(game_flask_app):
    """Прямая вставка пользователя в БД без bcrypt — нужно для бенчей, где
    bcrypt не интересует, важно только наличие user_id."""
    def _make(username='user', email=None, notification_lat=None, notification_lon=None):
        email = email or f'{username}@example.com'
        with game_flask_app.app_context():
            if notification_lat is not None and notification_lon is not None:
                result = game_app.db.session.execute(text("""
                    INSERT INTO users (username, email, password_hash, notification_location)
                    VALUES (:u, :e, 'x',
                            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)
                    RETURNING id
                """), {'u': username, 'e': email,
                       'lat': notification_lat, 'lon': notification_lon})
            else:
                result = game_app.db.session.execute(text("""
                    INSERT INTO users (username, email, password_hash)
                    VALUES (:u, :e, 'x')
                    RETURNING id
                """), {'u': username, 'e': email})
            uid = result.scalar()
            game_app.db.session.commit()
        return uid
    return _make
