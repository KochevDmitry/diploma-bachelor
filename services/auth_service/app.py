"""
Auth Service - управление пользователями и аутентификация
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import jwt
import bcrypt
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

# Конфигурация
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'postgresql://sportapp_user:sportapp_password@postgres:5432/sportapp_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 1800))  # 30 минут
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 604800))  # 7 дней

db = SQLAlchemy(app)


# Модель пользователя
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text, nullable=True, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'bio': self.bio or '',
            'created_at': self.created_at.isoformat()
        }


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'auth_service'}), 200


@app.route('/auth/register', methods=['POST'])
def register():
    """Регистрация нового пользователя"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Проверка существования пользователя
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    # Хеширование пароля
    password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Создание пользователя
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=password_hash
    )

    try:
        db.session.add(user)
        db.session.commit()
        
        # Генерация Access и Refresh токенов
        access_token = generate_access_token(user)
        refresh_token = generate_refresh_token(user)
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'accessToken': access_token,
            'refreshToken': refresh_token
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/auth/login', methods=['POST'])
def login():
    """Авторизация пользователя"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing username or password'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Проверка пароля
    if not bcrypt.checkpw(data['password'].encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Генерация Access и Refresh токенов
    access_token = generate_access_token(user)
    refresh_token = generate_refresh_token(user)
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'accessToken': access_token,
        'refreshToken': refresh_token
    }), 200


def generate_access_token(user):
    """Генерация Access JWT токена (короткоживущий)"""
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_ACCESS_TOKEN_EXPIRES'])
    }
    return jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')


def generate_refresh_token(user):
    """Генерация Refresh JWT токена (долгоживущий)"""
    payload = {
        'user_id': user.id,
        'username': user.username,
        'type': 'refresh',
        'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_REFRESH_TOKEN_EXPIRES'])
    }
    return jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')


@app.route('/auth/verify', methods=['GET', 'POST'])
def verify():
    """Проверка Access токена"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'error': 'Token missing'}), 401
    
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        
        # Проверяем что это Access token, а не Refresh
        if payload.get('type') == 'refresh':
            return jsonify({'error': 'Use refresh endpoint for refresh token'}), 401
            
        user = User.query.get(payload['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/auth/refresh', methods=['POST'])
def refresh():
    """Обновление Access токена используя Refresh токен"""
    data = request.get_json() or {}
    refresh_token = data.get('refreshToken') or request.headers.get('Authorization', '').replace('Bearer ', '')

    if not refresh_token:
        return jsonify({'error': 'Refresh token missing'}), 401

    try:
        payload = jwt.decode(refresh_token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])

        # Проверяем что это именно Refresh token
        if payload.get('type') != 'refresh':
            return jsonify({'error': 'Invalid token type'}), 401

        user = User.query.get(payload['user_id'])

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Генерируем новый Access token
        access_token = generate_access_token(user)

        return jsonify({
            'message': 'Token refreshed successfully',
            'accessToken': access_token,
            'user': user.to_dict()
        }), 200
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Refresh token expired, please login again'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid refresh token'}), 401


@app.route('/auth/profile', methods=['PUT', 'POST'])
def update_profile():
    """Обновление профиля пользователя"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Token missing'}), 401

    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])

        if payload.get('type') == 'refresh':
            return jsonify({'error': 'Use access token, not refresh token'}), 401

        user = User.query.get(payload['user_id'])

        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Обновляем username если передан и отличается
        if 'username' in data and data['username'] != user.username:
            existing = User.query.filter_by(username=data['username']).first()
            if existing and existing.id != user.id:
                return jsonify({'error': 'Username already taken'}), 400
            user.username = data['username']

        # Обновляем email если передан и отличается
        if 'email' in data and data['email'] != user.email:
            existing = User.query.filter_by(email=data['email']).first()
            if existing and existing.id != user.id:
                return jsonify({'error': 'Email already taken'}), 400
            user.email = data['email']

        # Обновляем bio если передан
        if 'bio' in data:
            user.bio = data['bio']

        try:
            db.session.commit()

            # Генерируем новый токен с обновленным username
            new_access_token = generate_access_token(user)

            return jsonify({
                'message': 'Profile updated successfully',
                'user': user.to_dict(),
                'accessToken': new_access_token
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


def create_default_user():
    """Создание тестового пользователя по умолчанию, если его нет"""
    with app.app_context():
        # Проверка существования пользователей
        if User.query.count() == 0:
            # Хеширование пароля для тестового пользователя
            password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            test_user = User(
                username='admin',
                email='admin@test.com',
                password_hash=password_hash
            )
            
            try:
                db.session.add(test_user)
                db.session.commit()
                print("✅ Тестовый пользователь создан:")
                print("   Username: admin")
                print("   Password: admin123")
            except Exception as e:
                db.session.rollback()
                print(f"⚠️  Не удалось создать тестового пользователя: {e}")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_default_user()
    
    port = int(os.getenv('SERVICE_PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
