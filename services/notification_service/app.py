"""
Notification Service - WebSocket для real-time обновлений + REST для истории уведомлений
"""
# Monkey-patch ДОЛЖЕН быть до любых других импортов, иначе threading/socket
# подменятся уже после того, как Flask/Redis-клиенты захватят оригиналы,
# и фоновый Pub/Sub-слушатель будет запущен реальным OS-потоком — он же
# заблокирует heartbeat у Flask-SocketIO и потеряет socketio.emit из room.
# DNS НЕ патчим: greendns у eventlet 0.33 несовместим с современным dnspython
# (LifetimeTimeout / unexpected kwarg 'ignore_errors'), а штатный getaddrinfo
# вызывается только при установке соединений и для нас не критичен по перформансу.
import os as _os
_os.environ.setdefault('EVENTLET_NO_GREENDNS', 'yes')
import eventlet
eventlet.monkey_patch(socket=True, select=True, thread=True, time=True, os=True)

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
import redis
import os
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Подключение к PostgreSQL для работы с историей уведомлений
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql://sportapp_user:sportapp_password@postgres:5432/sportapp_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Redis для pub/sub
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/1'))
pubsub = redis_client.pubsub()

# Хранение связи socket_id -> user_id
socket_to_user = {}


def _user_id_from_request():
    """Читает user_id из заголовка X-User-Id, инжектированного API Gateway после
    проверки JWT. Сервис не дублирует проверку токена — авторизация централизована.
    """
    raw = request.headers.get('X-User-Id')
    if not raw:
        return None, (jsonify({'error': 'Missing X-User-Id (request must come through API Gateway)'}), 401)
    try:
        return int(raw), None
    except ValueError:
        return None, (jsonify({'error': 'Invalid X-User-Id'}), 400)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'service': 'notification_service'}, 200


@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Получение списка уведомлений текущего пользователя"""
    user_id, err = _user_id_from_request()
    if err:
        return err

    result = db.session.execute(
        db.text("""
            SELECT id, type, title, message, session_id, read, created_at
            FROM notifications
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 50
        """),
        {'user_id': user_id}
    )

    notifications = [
        {
            'id': row[0],
            'type': row[1],
            'title': row[2],
            'message': row[3],
            'session_id': row[4],
            'read': row[5],
            'timestamp': row[6].isoformat() if row[6] else None,
        }
        for row in result
    ]
    return jsonify(notifications), 200


@app.route('/api/notifications/read', methods=['POST'])
def mark_notifications_read():
    """Пометить уведомления как прочитанные (конкретные id или все непрочитанные)"""
    user_id, err = _user_id_from_request()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    notification_ids = data.get('ids')

    if notification_ids:
        db.session.execute(
            db.text("""
                UPDATE notifications SET read = TRUE
                WHERE user_id = :user_id AND id = ANY(:ids)
            """),
            {'user_id': user_id, 'ids': notification_ids}
        )
    else:
        db.session.execute(
            db.text("""
                UPDATE notifications SET read = TRUE
                WHERE user_id = :user_id AND read = FALSE
            """),
            {'user_id': user_id}
        )
    db.session.commit()
    return jsonify({'message': 'Notifications marked as read'}), 200


@app.route('/api/notifications', methods=['DELETE'])
def delete_notifications():
    """Удалить все уведомления текущего пользователя"""
    user_id, err = _user_id_from_request()
    if err:
        return err

    db.session.execute(
        db.text("DELETE FROM notifications WHERE user_id = :user_id"),
        {'user_id': user_id}
    )
    db.session.commit()
    return jsonify({'message': 'Notifications deleted'}), 200


@socketio.on('connect')
def handle_connect():
    """Обработка подключения клиента"""
    logger.info(f'Client connected: {request.sid}')
    emit('connected', {'message': 'Connected to notification service'})


@socketio.on('disconnect')
def handle_disconnect():
    """Обработка отключения клиента"""
    sid = request.sid
    # Удаляем связь socket -> user при отключении
    if sid in socket_to_user:
        user_id = socket_to_user[sid]
        leave_room(f'user:{user_id}')
        del socket_to_user[sid]
        logger.info(f'User {user_id} disconnected (socket {sid})')
    else:
        logger.info(f'Client disconnected: {sid}')


@socketio.on('authenticate')
def handle_authenticate(data):
    """Аутентификация пользователя и подписка на персональные уведомления"""
    user_id = data.get('user_id')
    if user_id:
        room = f'user:{user_id}'
        join_room(room)
        socket_to_user[request.sid] = user_id
        logger.info(f'User {user_id} authenticated and joined room {room}')
        emit('authenticated', {'user_id': user_id, 'room': room})


@socketio.on('subscribe_venue')
def handle_subscribe_venue(data):
    """Подписка на обновления для конкретной площадки"""
    venue_id = data.get('venue_id')
    if venue_id:
        room = f'venue:{venue_id}'
        join_room(room)
        print(f'Client {request.sid} subscribed to venue {venue_id}')
        emit('subscribed', {'venue_id': venue_id, 'room': room})


@socketio.on('unsubscribe_venue')
def handle_unsubscribe_venue(data):
    """Отписка от обновлений площадки"""
    venue_id = data.get('venue_id')
    if venue_id:
        room = f'venue:{venue_id}'
        leave_room(room)
        print(f'Client {request.sid} unsubscribed from venue {venue_id}')
        emit('unsubscribed', {'venue_id': venue_id})


@socketio.on('subscribe_session')
def handle_subscribe_session(data):
    """Подписка на обновления игровой сессии"""
    session_id = data.get('session_id')
    if session_id:
        room = f'session:{session_id}'
        join_room(room)
        print(f'Client {request.sid} subscribed to session {session_id}')
        emit('subscribed', {'session_id': session_id, 'room': room})


def publish_notification(channel, message):
    """Публикация уведомления в Redis"""
    redis_client.publish(channel, json.dumps(message))


def listen_for_notifications():
    """Прослушивание уведомлений из Redis и отправка клиентам"""
    pubsub.subscribe(['venue_updates', 'session_updates', 'user_notifications'])
    logger.info("Subscribed to Redis channels: venue_updates, session_updates, user_notifications")

    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                channel = message['channel'].decode() if isinstance(message['channel'], bytes) else message['channel']

                logger.debug(f"Received message on channel {channel}: {data}")

                if channel == 'venue_updates':
                    venue_id = data.get('venue_id')
                    if venue_id:
                        room = f'venue:{venue_id}'
                        socketio.emit('venue_update', data, room=room)
                        logger.debug(f"Sent venue_update to room {room}")

                elif channel == 'session_updates':
                    session_id = data.get('session_id')
                    if session_id:
                        room = f'session:{session_id}'
                        socketio.emit('session_update', data, room=room)
                        # Также отправляем обновление в комнату площадки
                        venue_id = data.get('venue_id')
                        if venue_id:
                            venue_room = f'venue:{venue_id}'
                            socketio.emit('venue_update', data, room=venue_room)

                elif channel == 'user_notifications':
                    # Персональные уведомления пользователю
                    user_id = data.get('user_id')
                    if user_id:
                        room = f'user:{user_id}'
                        socketio.emit('notification', data, room=room)
                        logger.info(f"Sent notification to user {user_id}: {data.get('type')}")

            except Exception as e:
                logger.exception(f'Error processing notification: {e}')


# Запуск прослушивания Redis Pub/Sub как greenlet'а, управляемого тем же
# eventlet-хабом, что и WebSocket-соединения. Это даёт двум вещам общую
# очередь событий: и доставка через socketio.emit, и heartbeat сокетов
# теперь шедулятся одинаково кооперативно.
socketio.start_background_task(listen_for_notifications)


if __name__ == '__main__':
    port = int(os.getenv('SERVICE_PORT', 5004))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
