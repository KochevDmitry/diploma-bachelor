"""
Конфигурация Celery для Game Session Service
"""
import os

broker_url = os.getenv('RABBITMQ_URL', 'amqp://sportapp_user:sportapp_password@rabbitmq:5672/')
result_backend = os.getenv('REDIS_URL', 'redis://redis:6379/0')

task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Настройки задач
task_track_started = True
task_time_limit = 30 * 60  # 30 минут
task_soft_time_limit = 25 * 60  # 25 минут

# Периодические задачи
from celery.schedules import crontab

beat_schedule = {
    'cleanup-old-sessions': {
        'task': 'app.cleanup_old_sessions',
        'schedule': crontab(minute=0),  # Каждый час
    },
}
