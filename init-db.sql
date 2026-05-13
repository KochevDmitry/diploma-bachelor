-- Инициализация базы данных
-- Создание расширения PostGIS для работы с геоданными
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Обёртка ST_AsEWKB(geography): GeoAlchemy2 при чтении Geography-колонок
-- генерирует ST_AsEWKB(col), но PostGIS такой перегрузки не имеет.
-- Каст к geometry даёт корректный EWKB, т.к. внутри Geography хранится
-- тот же WKB с метаинформацией о SRID.
CREATE OR REPLACE FUNCTION ST_AsEWKB(geog geography) RETURNS bytea AS $$
    SELECT ST_AsEWKB(geog::geometry);
$$ LANGUAGE SQL IMMUTABLE PARALLEL SAFE STRICT;

-- Таблица пользователей (будет использоваться Auth Service)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    bio TEXT DEFAULT '',
    avatar_url VARCHAR(500) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Добавление колонки bio если её нет (для миграции существующей БД)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'bio') THEN
        ALTER TABLE users ADD COLUMN bio TEXT DEFAULT '';
    END IF;
END $$;

-- Добавление колонки avatar_url если её нет (для миграции существующей БД)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'avatar_url') THEN
        ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500) DEFAULT NULL;
    END IF;
END $$;

-- Добавление колонки notification_location для уведомлений о событиях поблизости
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'notification_location') THEN
        ALTER TABLE users ADD COLUMN notification_location geography(Point, 4326) DEFAULT NULL;
    END IF;
END $$;

-- Миграция типа geometry -> geography для существующих БД
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users'
          AND column_name = 'notification_location'
          AND udt_name = 'geometry'
    ) THEN
        DROP INDEX IF EXISTS users_notification_location_idx;
        ALTER TABLE users
            ALTER COLUMN notification_location TYPE geography(Point, 4326)
            USING notification_location::geography;
    END IF;
END $$;

-- Индекс для быстрого поиска пользователей по локации
CREATE INDEX IF NOT EXISTS users_notification_location_idx ON users USING GIST(notification_location);

-- Добавление колонки notify_own_games для настройки уведомлений о своих играх
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'notify_own_games') THEN
        ALTER TABLE users ADD COLUMN notify_own_games BOOLEAN DEFAULT TRUE NOT NULL;
    END IF;
END $$;

-- Таблица площадок (будет использоваться Map Service)
CREATE TABLE IF NOT EXISTS venues (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    sport_type VARCHAR(50), -- football, basketball, volleyball, etc.
    location geography(Point, 4326), -- PostGIS география для координат
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Миграция типа geometry -> geography для существующих БД (venues)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'venues'
          AND column_name = 'location'
          AND udt_name = 'geometry'
    ) THEN
        DROP INDEX IF EXISTS venues_location_idx;
        ALTER TABLE venues
            ALTER COLUMN location TYPE geography(Point, 4326)
            USING location::geography;
    END IF;
END $$;

-- Индекс для быстрого поиска по геолокации
CREATE INDEX IF NOT EXISTS venues_location_idx ON venues USING GIST(location);

-- Таблица игровых сессий (история, будет использоваться Game Session Service)
CREATE TABLE IF NOT EXISTS game_sessions (
    id SERIAL PRIMARY KEY,
    venue_id INTEGER REFERENCES venues(id) ON DELETE CASCADE,
    creator_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    sport_type VARCHAR(50) NOT NULL,
    max_players INTEGER DEFAULT 10,
    current_players INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'waiting', -- waiting, full, started, finished
    latitude FLOAT,
    longitude FLOAT,
    location geography(Point, 4326), -- PostGIS для быстрого поиска поблизости
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);

-- Миграция типа geometry -> geography для существующих БД (game_sessions)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'game_sessions'
          AND column_name = 'location'
          AND udt_name = 'geometry'
    ) THEN
        DROP INDEX IF EXISTS game_sessions_location_idx;
        ALTER TABLE game_sessions
            ALTER COLUMN location TYPE geography(Point, 4326)
            USING location::geography;
    END IF;
END $$;

-- Индекс для быстрого поиска сессий по геолокации
CREATE INDEX IF NOT EXISTS game_sessions_location_idx ON game_sessions USING GIST(location);

-- Таблица участников игровых сессий
CREATE TABLE IF NOT EXISTS session_participants (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES game_sessions(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, user_id)
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS game_sessions_venue_idx ON game_sessions(venue_id);
CREATE INDEX IF NOT EXISTS game_sessions_status_idx ON game_sessions(status);
CREATE INDEX IF NOT EXISTS session_participants_session_idx ON session_participants(session_id);
CREATE INDEX IF NOT EXISTS session_participants_user_idx ON session_participants(user_id);