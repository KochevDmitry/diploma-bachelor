"""
Game Session Service - управление игровыми сессиями
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from celery import Celery
import redis
import os
import json
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Конфигурация
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'postgresql://sportapp_user:sportapp_password@postgres:5432/sportapp_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Redis для активных сессий
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))

# Celery для фоновых задач
celery = Celery(
    'game_session_service',
    broker=os.getenv('RABBITMQ_URL', 'amqp://sportapp_user:sportapp_password@rabbitmq:5672/'),
    backend=os.getenv('REDIS_URL', 'redis://redis:6379/0')
)

# Загрузка конфигурации
try:
    from celery_config import broker_url, result_backend, task_serializer, accept_content, result_serializer, timezone, enable_utc, beat_schedule
    celery.conf.update(
        broker_url=broker_url,
        result_backend=result_backend,
        task_serializer=task_serializer,
        accept_content=accept_content,
        result_serializer=result_serializer,
        timezone=timezone,
        enable_utc=enable_utc,
        beat_schedule=beat_schedule
    )
except ImportError:
    pass  # Используем значения по умолчанию


# Модели
class GameSession(db.Model):
    __tablename__ = 'game_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, nullable=True)  # Ссылка на Venue ID из map_service
    creator_id = db.Column(db.Integer, nullable=False)  # Ссылка на User ID из auth_service
    sport_type = db.Column(db.String(50), nullable=False)
    max_players = db.Column(db.Integer, default=10)
    current_players = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='waiting')  # waiting, full, started, finished
    latitude = db.Column(db.Float, nullable=True)  # Координаты для произвольных событий
    longitude = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    
    def to_dict(self):
        # Получение участников из Redis
        participants = get_session_participants(self.id)
        
        return {
            'id': self.id,
            'venue_id': self.venue_id,
            'creator_id': self.creator_id,
            'sport_type': self.sport_type,
            'max_players': self.max_players,
            'current_players': self.current_players,
            'status': self.status,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'participants': participants,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None
        }


class SessionParticipant(db.Model):
    __tablename__ = 'session_participants'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('game_sessions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('session_id', 'user_id', name='unique_participant'),)


def get_session_participants(session_id):
    """Получение участников сессии из Redis"""
    key = f'session:{session_id}:participants'
    participants = redis_client.smembers(key)
    return [int(p.decode()) for p in participants] if participants else []


def set_session_participants(session_id, user_ids):
    """Сохранение участников сессии в Redis"""
    key = f'session:{session_id}:participants'
    if user_ids:
        redis_client.sadd(key, *user_ids)
        redis_client.expire(key, 3600 * 24)  # TTL 24 часа
    else:
        redis_client.delete(key)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'game_session_service'}), 200


@app.route('/api/games/venue/<int:venue_id>', methods=['GET'])
def get_venue_sessions(venue_id):
    """Получение активных сессий для площадки"""
    # Сначала проверяем Redis
    cache_key = f'venue:{venue_id}:sessions'
    cached = redis_client.get(cache_key)
    
    if cached:
        return jsonify(json.loads(cached)), 200
    
    # Получаем активные сессии из БД
    sessions = GameSession.query.filter_by(
        venue_id=venue_id,
        status='waiting'
    ).all()
    
    result = [session.to_dict() for session in sessions]
    
    # Кеширование на 30 секунд
    redis_client.setex(cache_key, 30, json.dumps(result))
    
    return jsonify(result), 200


@app.route('/api/games/map', methods=['GET'])
def get_map_sessions():
    """Получение всех активных сессий с координатами для карты"""
    # Получаем сессии с координатами (не привязанные к venue или с venue)
    sessions = GameSession.query.filter(
        GameSession.status == 'waiting',
        db.or_(
            GameSession.latitude.isnot(None),
            GameSession.venue_id.isnot(None)
        )
    ).all()
    
    result = []
    for session in sessions:
        session_dict = session.to_dict()
        # Если сессия привязана к venue, добавим координаты venue
        if session.venue_id and not session.latitude:
            # Здесь нужно получить координаты venue из другого сервиса
            # Пока что пропустим, frontend должен сам знать координаты venues
            pass
        result.append(session_dict)
    
    return jsonify(result), 200


@app.route('/api/games/<int:session_id>', methods=['GET'])
def get_session(session_id):
    """Получение информации о сессии"""
    session = GameSession.query.get_or_404(session_id)
    return jsonify(session.to_dict()), 200


@app.route('/api/games', methods=['POST'])
def create_session():
    """Создание новой игровой сессии"""
    data = request.get_json()
    
    if not data or not data.get('creator_id'):
        return jsonify({'error': 'Missing required field: creator_id'}), 400
    
    # Проверяем, что либо venue_id, либо координаты указаны
    if not data.get('venue_id') and (not data.get('latitude') or not data.get('longitude')):
        return jsonify({'error': 'Either venue_id or latitude/longitude coordinates are required'}), 400
    
    session = GameSession(
        venue_id=data.get('venue_id'),
        creator_id=data['creator_id'],
        sport_type=data.get('sport_type', 'football'),
        max_players=data.get('max_players', 10),
        current_players=1,
        status='waiting',
        latitude=data.get('latitude'),
        longitude=data.get('longitude')
    )
    
    try:
        db.session.add(session)
        db.session.commit()
        
        # Сохранение создателя в Redis
        set_session_participants(session.id, [data['creator_id']])
        
        # Очистка кеша
        if data.get('venue_id'):
            redis_client.delete(f'venue:{data["venue_id"]}:sessions')
        
        # Отправка уведомления через Celery
        notify_new_session.delay(session.id, data.get('venue_id'))
        
        return jsonify(session.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/games/<int:session_id>/join', methods=['POST'])
def join_session(session_id):
    """Присоединение к игровой сессии"""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400
    
    session = GameSession.query.get_or_404(session_id)
    
    if session.status != 'waiting':
        return jsonify({'error': 'Session is not available for joining'}), 400
    
    # Проверка, не присоединился ли уже
    participants = get_session_participants(session_id)
    if user_id in participants:
        return jsonify({'error': 'User already in session'}), 400
    
    if session.current_players >= session.max_players:
        return jsonify({'error': 'Session is full'}), 400
    
    try:
        # Добавление участника в БД
        participant = SessionParticipant(
            session_id=session_id,
            user_id=user_id
        )
        db.session.add(participant)
        
        # Обновление счетчика
        session.current_players += 1
        if session.current_players >= session.max_players:
            session.status = 'full'
        
        db.session.commit()
        
        # Обновление Redis
        participants.append(user_id)
        set_session_participants(session_id, participants)
        
        # Очистка кеша
        redis_client.delete(f'venue:{session.venue_id}:sessions')
        
        # Уведомление о присоединении
        notify_session_update.delay(session_id)
        
        return jsonify(session.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/games/<int:session_id>/leave', methods=['POST'])
def leave_session(session_id):
    """Покидание игровой сессии"""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400
    
    session = GameSession.query.get_or_404(session_id)
    
    if session.creator_id == user_id:
        return jsonify({'error': 'Creator cannot leave session'}), 400
    
    try:
        # Удаление участника
        SessionParticipant.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).delete()
        
        # Обновление счетчика
        session.current_players = max(1, session.current_players - 1)
        if session.status == 'full':
            session.status = 'waiting'
        
        db.session.commit()
        
        # Обновление Redis
        participants = get_session_participants(session_id)
        if user_id in participants:
            participants.remove(user_id)
        set_session_participants(session_id, participants)
        
        # Очистка кеша
        redis_client.delete(f'venue:{session.venue_id}:sessions')
        
        return jsonify(session.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/games/<int:session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Удаление игровой сессии"""
    session = GameSession.query.get_or_404(session_id)
    
    try:
        # Удаление из Redis
        redis_client.delete(f'session:{session_id}:participants')
        
        # Удаление из БД
        db.session.delete(session)
        db.session.commit()
        
        # Очистка кеша
        redis_client.delete(f'venue:{session.venue_id}:sessions')
        
        return jsonify({'message': 'Session deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# Celery задачи
@celery.task
def notify_new_session(session_id, venue_id):
    """Уведомление о новой сессии"""
    # Здесь можно отправить уведомление через Notification Service
    pass


@celery.task
def notify_session_update(session_id):
    """Уведомление об обновлении сессии"""
    # Здесь можно отправить уведомление через Notification Service
    pass


@celery.task(name='app.cleanup_old_sessions')
def cleanup_old_sessions():
    """Очистка старых завершенных сессий"""
    from app import app as flask_app
    with flask_app.app_context():
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        old_sessions = GameSession.query.filter(
            GameSession.status == 'finished',
            GameSession.finished_at < cutoff_time
        ).all()
        
        for session in old_sessions:
            redis_client.delete(f'session:{session.id}:participants')
            db.session.delete(session)
        
        db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    port = int(os.getenv('SERVICE_PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=False)
