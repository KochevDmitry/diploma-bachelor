"""
Notification Service - WebSocket для real-time обновлений
"""
from flask import Flask, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
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

# Redis для pub/sub
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/1'))
pubsub = redis_client.pubsub()

# Хранение связи socket_id -> user_id
socket_to_user = {}


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'service': 'notification_service'}, 200


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


# Запуск прослушивания в фоновом потоке
import threading
notification_thread = threading.Thread(target=listen_for_notifications, daemon=True)
notification_thread.start()


if __name__ == '__main__':
    port = int(os.getenv('SERVICE_PORT', 5004))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
