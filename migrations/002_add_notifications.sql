-- Миграция: Добавление поддержки уведомлений о событиях поблизости
-- Выполнить: docker exec -i sportapp_postgres psql -U sportapp_user -d sportapp_db < migrations/002_add_notifications.sql

-- 1. Добавляем колонку notification_location в таблицу users (PostGIS Point)
ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_location geometry(Point, 4326);

-- 2. Создаём индекс для быстрого поиска пользователей по локации
CREATE INDEX IF NOT EXISTS users_notification_location_idx ON users USING GIST(notification_location);

-- 3. Добавляем колонку location в таблицу game_sessions (PostGIS Point)
ALTER TABLE game_sessions ADD COLUMN IF NOT EXISTS location geometry(Point, 4326);

-- 4. Создаём индекс для быстрого поиска сессий по геолокации
CREATE INDEX IF NOT EXISTS game_sessions_location_idx ON game_sessions USING GIST(location);

-- 5. Обновляем существующие сессии - конвертируем lat/lon в PostGIS geometry
UPDATE game_sessions
SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND location IS NULL;

-- 6. Создаём таблицу уведомлений для хранения истории
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT,
    session_id INTEGER,
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Индексы для быстрого поиска уведомлений
CREATE INDEX IF NOT EXISTS notifications_user_idx ON notifications(user_id);
CREATE INDEX IF NOT EXISTS notifications_unread_idx ON notifications(user_id, read) WHERE read = FALSE;

-- Готово!
SELECT 'Migration 002_add_notifications completed successfully!' as status;
