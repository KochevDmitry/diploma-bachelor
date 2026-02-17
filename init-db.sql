-- Инициализация базы данных
-- Создание расширения PostGIS для работы с геоданными
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Таблица пользователей (будет использоваться Auth Service)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица площадок (будет использоваться Map Service)
CREATE TABLE IF NOT EXISTS venues (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    sport_type VARCHAR(50), -- football, basketball, volleyball, etc.
    location geometry(Point, 4326), -- PostGIS география для координат
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);

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

INSERT INTO venues (name, address, sport_type, location) VALUES
    ('Спортивный комплекс "Олимп"', 'Москва, ул. Ленинградский проспект, 31', 'football', 
     ST_SetSRID(ST_MakePoint(37.537800, 55.788155), 4326)),
    ('Футбольное поле "Спартак"', 'Москва, ул. Народного Ополчения, 2', 'football',
     ST_SetSRID(ST_MakePoint(37.440262, 55.818351), 4326)),
    ('Баскетбольная площадка "Динамо"', 'Москва, Ленинградский просп., 36', 'basketball',
     ST_SetSRID(ST_MakePoint(37.559028, 55.790688), 4326)),
    ('Теннисный корт "Лужники"', 'Москва, ул. Лужники, 24', 'tennis',
     ST_SetSRID(ST_MakePoint(37.553308, 55.715551), 4326)),
    ('Волейбольная площадка "Сокол"', 'Москва, ул. Волоколамское шоссе, 2', 'volleyball',
     ST_SetSRID(ST_MakePoint(37.513900, 55.804700), 4326)),
    ('Футбольное поле "Локомотив"', 'Москва, ул. Большая Черкизовская, 125', 'football',
     ST_SetSRID(ST_MakePoint(37.740519, 55.815511), 4326))
ON CONFLICT DO NOTHING;