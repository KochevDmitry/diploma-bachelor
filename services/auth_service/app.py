"""
Auth Service - управление пользователями и аутентификация
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import jwt
import bcrypt
from datetime import datetime, timedelta
import os
import uuid

# Папка для хранения аватаров
UPLOAD_FOLDER = '/app/uploads/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max

# Создаём папку для аватаров если её нет
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)


# Модель пользователя
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text, nullable=True, default='')
    avatar_url = db.Column(db.String(500), nullable=True, default=None)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'bio': self.bio or '',
            'avatar_url': self.avatar_url,
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


@app.route('/auth/avatar', methods=['POST'])
def upload_avatar():
    """Загрузка аватара пользователя"""
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

        if 'avatar' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['avatar']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Use: png, jpg, jpeg, gif, webp'}), 400

        # Генерируем уникальное имя файла
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{user.id}_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Удаляем старый аватар если есть
        if user.avatar_url:
            old_filename = user.avatar_url.split('/')[-1]
            old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
            if os.path.exists(old_filepath):
                os.remove(old_filepath)

        # Сохраняем новый файл
        file.save(filepath)

        # Обновляем URL в базе
        user.avatar_url = f"/auth/avatars/{filename}"

        try:
            db.session.commit()
            return jsonify({
                'message': 'Avatar uploaded successfully',
                'avatar_url': user.avatar_url,
                'user': user.to_dict()
            }), 200
        except Exception as e:
            db.session.rollback()
            # Удаляем загруженный файл при ошибке
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': str(e)}), 500

    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/auth/avatars/<filename>')
def serve_avatar(filename):
    """Отдача файла аватара"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/auth/change-password', methods=['POST'])
def change_password():
    """Смена пароля пользователя"""
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

        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        confirm_password = data.get('confirmPassword')

        if not current_password or not new_password or not confirm_password:
            return jsonify({'error': 'All fields are required'}), 400

        # Проверяем текущий пароль
        if not bcrypt.checkpw(current_password.encode('utf-8'), user.password_hash.encode('utf-8')):
            return jsonify({'error': 'Current password is incorrect'}), 400

        # Проверяем совпадение нового пароля
        if new_password != confirm_password:
            return jsonify({'error': 'New passwords do not match'}), 400

        # Проверяем минимальную длину
        if len(new_password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400

        # Хешируем и сохраняем новый пароль
        user.password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        try:
            db.session.commit()
            return jsonify({
                'message': 'Password changed successfully'
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
