"""Общие фикстуры для тестов auth_service.

Важно: env-переменные DATABASE_URL и JWT_SECRET_KEY должны быть выставлены
ДО импорта модуля сервиса — Flask и SQLAlchemy читают конфигурацию на этапе
инициализации модуля. Поэтому переменные ставим в самом верху, и только
потом импортируем `app`.
"""
import os
import sys
import tempfile
import importlib.util
import pytest
from sqlalchemy import text

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SERVICE_DIR = os.path.join(REPO_ROOT, 'services', 'auth_service')

os.environ['DATABASE_URL'] = os.getenv(
    'TEST_DATABASE_URL',
    'postgresql://test:test@localhost:55432/test_db'
)
os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
os.environ['JWT_ACCESS_TOKEN_EXPIRES'] = '3600'
os.environ['JWT_REFRESH_TOKEN_EXPIRES'] = '604800'

# Перенаправляем папку аватаров во временную директорию, иначе сервис
# попытается создать /app/uploads/avatars при импорте.
os.environ['UPLOAD_FOLDER'] = tempfile.mkdtemp(prefix='auth_test_avatars_')

# Оба сервиса используют файл app.py — если просто `import app`, Python
# закеширует первый импорт в sys.modules и второй сервис получит чужой
# модуль. Грузим каждый под уникальным именем через importlib.
_spec = importlib.util.spec_from_file_location(
    'auth_service_app', os.path.join(SERVICE_DIR, 'app.py')
)
auth_app = importlib.util.module_from_spec(_spec)
sys.modules['auth_service_app'] = auth_app
_spec.loader.exec_module(auth_app)


@pytest.fixture(scope='session')
def flask_app():
    auth_app.app.config['TESTING'] = True
    return auth_app.app


@pytest.fixture(autouse=True)
def clean_db(flask_app):
    """Сбрасывает состояние таблицы users перед каждым тестом."""
    with flask_app.app_context():
        auth_app.db.session.execute(text('TRUNCATE users RESTART IDENTITY CASCADE'))
        auth_app.db.session.commit()
    yield


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture
def registered_user(client):
    """Регистрирует пользователя alice и возвращает ответ сервиса
    (содержит user, accessToken, refreshToken)."""
    resp = client.post('/auth/register', json={
        'username': 'alice',
        'email': 'alice@example.com',
        'password': 'password123'
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


@pytest.fixture
def auth_headers(registered_user):
    return {'Authorization': f'Bearer {registered_user["accessToken"]}'}
