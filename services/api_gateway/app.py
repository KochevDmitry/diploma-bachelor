"""
API Gateway - единая точка входа для всех запросов
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import jwt
import os
from functools import wraps

app = Flask(__name__)
CORS(app)

# Конфигурация
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth_service:5001')
MAP_SERVICE_URL = os.getenv('MAP_SERVICE_URL', 'http://map_service:5002')
GAME_SERVICE_URL = os.getenv('GAME_SERVICE_URL', 'http://game_session_service:5003')
NOTIFICATION_SERVICE_URL = os.getenv('NOTIFICATION_SERVICE_URL', 'http://notification_service:5004')

# Маршруты, не требующие аутентификации
PUBLIC_ROUTES = ['/auth/register', '/auth/login', '/health']


def verify_token(f):
    """Декоратор для проверки JWT токена"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            request.current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    return decorated


def proxy_request(service_url, path, method='GET', data=None, headers=None):
    """Проксирование запроса к микросервису"""
    url = f"{service_url}{path}"
    request_headers = {k: v for k, v in request.headers if k.lower() != 'host'}
    if headers:
        request_headers.update(headers)
    
    try:
        if method == 'GET':
            response = requests.get(url, params=request.args, headers=request_headers, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=request_headers, timeout=10)
        elif method == 'PUT':
            response = requests.put(url, json=data, headers=request_headers, timeout=10)
        elif method == 'DELETE':
            response = requests.delete(url, headers=request_headers, timeout=10)
        else:
            return jsonify({'error': 'Method not allowed'}), 405
        
        try:
            return response.json(), response.status_code
        except ValueError:
            # Ответ не JSON (пустое тело, HTML и т.д.)
            return jsonify({
                'error': 'Upstream service returned invalid response',
                'status': response.status_code,
                'detail': response.text[:200] if response.text else 'empty body'
            }), response.status_code if 400 <= response.status_code < 600 else 502
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Service unavailable: {str(e)}'}), 503


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'api_gateway'}), 200


# Auth Service routes
@app.route('/auth/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def auth_proxy(path):
    """Проксирование запросов к Auth Service"""
    return proxy_request(AUTH_SERVICE_URL, f'/auth/{path}', request.method, request.get_json())


# Map Service routes
@app.route('/api/map/venues', methods=['GET'])
def map_venues_proxy():
    """Проксирование запросов к Map Service для просмотра площадок (публичный)"""
    return proxy_request(MAP_SERVICE_URL, '/api/map/venues', 'GET')

@app.route('/api/map/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@verify_token
def map_proxy(path):
    """Проксирование запросов к Map Service (требует авторизации для изменений)"""
    return proxy_request(MAP_SERVICE_URL, f'/api/map/{path}', request.method, request.get_json())


# Game Session Service routes
@app.route('/api/games/venue/<int:venue_id>', methods=['GET'])
def game_venue_proxy(venue_id):
    """Проксирование запросов к Game Session Service для просмотра сессий на площадке (публичный)"""
    return proxy_request(GAME_SERVICE_URL, f'/api/games/venue/{venue_id}', 'GET')

@app.route('/api/games/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@verify_token
def game_proxy(path):
    """Проксирование запросов к Game Session Service (требует авторизации)"""
    return proxy_request(GAME_SERVICE_URL, f'/api/games/{path}', request.method, request.get_json())


# Notification Service routes (WebSocket будет обрабатываться отдельно)
@app.route('/api/notifications/<path:path>', methods=['GET', 'POST'])
@verify_token
def notification_proxy(path):
    """Проксирование запросов к Notification Service"""
    return proxy_request(NOTIFICATION_SERVICE_URL, f'/api/notifications/{path}', request.method, request.get_json())


if __name__ == '__main__':
    port = int(os.getenv('SERVICE_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
