"""Бенчмарки auth_service.

pytest-benchmark прогоняет каждый таргет N итераций, отбрасывает прогрев и
выдаёт min/median/mean/stddev/IQR. Используем `pedantic`-режим там, где
требуется уникальный сетап на каждой итерации (например, register не может
дважды создать одного и того же пользователя).
"""
import uuid


def _new_creds():
    """Уникальные креды на итерацию — register падает на дубликате."""
    suffix = uuid.uuid4().hex[:10]
    return {
        'username': f'u_{suffix}',
        'email': f'{suffix}@example.com',
        'password': 'password123',
    }


def test_perf_register(auth_client, benchmark):
    """Регистрация: bcrypt-хеш пароля — самая тяжёлая операция в auth."""
    def run():
        resp = auth_client.post('/auth/register', json=_new_creds())
        assert resp.status_code == 201

    benchmark.pedantic(run, rounds=20, iterations=1, warmup_rounds=1)


def test_perf_login(auth_client, benchmark):
    """Логин: bcrypt-проверка пароля."""
    creds = _new_creds()
    auth_client.post('/auth/register', json=creds)
    login_payload = {'username': creds['username'], 'password': creds['password']}

    def run():
        resp = auth_client.post('/auth/login', json=login_payload)
        assert resp.status_code == 200

    benchmark.pedantic(run, rounds=30, iterations=1, warmup_rounds=1)


def test_perf_verify_token(auth_client, benchmark):
    """Проверка access-токена: JWT decode + один SELECT по users."""
    creds = _new_creds()
    resp = auth_client.post('/auth/register', json=creds)
    token = resp.get_json()['accessToken']
    headers = {'Authorization': f'Bearer {token}'}

    def run():
        r = auth_client.get('/auth/verify', headers=headers)
        assert r.status_code == 200

    benchmark.pedantic(run, rounds=200, iterations=1, warmup_rounds=2)


def test_perf_refresh_token(auth_client, benchmark):
    """Обновление access-токена через refresh: JWT decode + SELECT + новый JWT."""
    creds = _new_creds()
    resp = auth_client.post('/auth/register', json=creds)
    refresh_token = resp.get_json()['refreshToken']

    def run():
        r = auth_client.post('/auth/refresh', json={'refreshToken': refresh_token})
        assert r.status_code == 200

    benchmark.pedantic(run, rounds=200, iterations=1, warmup_rounds=2)


def test_perf_update_profile(auth_client, benchmark):
    """Обновление профиля: JWT decode + 1-2 SELECT + UPDATE + новый JWT."""
    creds = _new_creds()
    resp = auth_client.post('/auth/register', json=creds)
    token = resp.get_json()['accessToken']
    headers = {'Authorization': f'Bearer {token}'}

    counter = iter(range(10**6))

    def run():
        i = next(counter)
        r = auth_client.post('/auth/profile', headers=headers,
                             json={'bio': f'bio update #{i}'})
        assert r.status_code == 200

    benchmark.pedantic(run, rounds=100, iterations=1, warmup_rounds=2)


def test_perf_change_password(auth_client, benchmark):
    """Смена пароля: bcrypt verify + bcrypt hash — двойной bcrypt."""
    creds = _new_creds()
    resp = auth_client.post('/auth/register', json=creds)
    token = resp.get_json()['accessToken']
    headers = {'Authorization': f'Bearer {token}'}

    # Будем чередовать два пароля, чтобы каждый раз currentPassword был валиден.
    state = {'current': creds['password'], 'next': 'newpass1234'}

    def run():
        r = auth_client.post('/auth/change-password', headers=headers, json={
            'currentPassword': state['current'],
            'newPassword': state['next'],
            'confirmPassword': state['next'],
        })
        assert r.status_code == 200, r.get_json()
        state['current'], state['next'] = state['next'], state['current']

    benchmark.pedantic(run, rounds=20, iterations=1, warmup_rounds=1)


def test_perf_notification_location_update(auth_client, benchmark):
    """Обновление notification_location: JWT decode + UPDATE с PostGIS-точкой."""
    creds = _new_creds()
    resp = auth_client.post('/auth/register', json=creds)
    token = resp.get_json()['accessToken']
    headers = {'Authorization': f'Bearer {token}'}

    counter = iter(range(10**6))

    def run():
        i = next(counter)
        # слегка варьируем координаты, чтобы UPDATE реально что-то менял
        r = auth_client.post('/auth/notification-location', headers=headers,
                             json={'lat': 55.75 + (i % 100) * 0.0001,
                                   'lon': 37.61 + (i % 100) * 0.0001})
        assert r.status_code == 200

    benchmark.pedantic(run, rounds=100, iterations=1, warmup_rounds=2)
