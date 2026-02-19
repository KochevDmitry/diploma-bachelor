# SportApp - Приложение для поиска игроков на спортивных площадках

Веб-приложение на базе микросервисной архитектуры для поиска и присоединения к играм на спортивных площадках.

## 🎯 Описание проекта

Приложение позволяет пользователям:
- Просматривать интерактивную карту с отмеченными спортивными площадками
- Видеть активные игровые сессии на каждой площадке
- Создавать новые игровые сессии и присоединяться к существующим
- Получать real-time обновления через WebSocket

## 🏗️ Архитектура

### Микросервисы

1. **API Gateway** (порт 5000)
   - Единая точка входа для всех запросов
   - Маршрутизация к микросервисам
   - JWT аутентификация
   - Технологии: Flask, nginx

2. **Auth Service** (порт 5001)
   - Регистрация и авторизация пользователей
   - Выдача JWT токенов
   - Хеширование паролей (bcrypt)
   - БД: PostgreSQL

3. **Map Service** (порт 5002)
   - Управление площадками (CRUD)
   - Геолокация и поиск площадок
   - Кеширование в Redis
   - БД: PostgreSQL + PostGIS

4. **Game Session Service** (порт 5003)
   - Создание/удаление игровых сессий
   - Управление участниками
   - БД: PostgreSQL (история) + Redis (активные сессии)
   - Celery для фоновых задач

5. **Notification Service** (порт 5004)
   - WebSocket соединения для real-time обновлений
   - Pub/Sub через Redis
   - Технологии: Flask-SocketIO

6. **Frontend** (React)
   - Интерактивная карта на Yandex Maps API
   - Интерфейс пользователя
   - WebSocket клиент для уведомлений

### Инфраструктура

- **PostgreSQL** с расширением PostGIS для геоданных
- **Redis** для кеширования и активных сессий
- **RabbitMQ** как message broker для Celery
- **Nginx** для проксирования и статики

## 🗺️ Работа с картой

### Выбор API карт

Используется **Yandex Maps API** по следующим причинам:
- Простая интеграция
- Хорошая документация на русском языке
- Удобная работа с маркерами и кликами
- Бесплатный тариф для разработки

### Подход к работе с площадками

1. **Площадки хранятся в базе данных** (PostgreSQL + PostGIS)
   - Координаты (lat/lon)
   - Адрес
   - Тип спорта
   - Название

2. **Карта отображает все площадки** с маркерами
   - При загрузке страницы запрашиваются все площадки из БД
   - Маркеры размещаются на карте автоматически

3. **При клике на маркер:**
   - Получаем ID площадки
   - Запрашиваем активные игровые сессии для этой площадки
   - Показываем информацию пользователю

4. **Пользователь может:**
   - Создать новую игровую сессию на площадке
   - Присоединиться к существующей сессии

## 🚀 Быстрый старт

### Требования

- Docker и Docker Compose
- Yandex Maps API ключ (получить на https://developer.tech.yandex.ru/)

### Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd diploma-bachelor
```

2. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

3. Отредактируйте `.env` и укажите:
   - `JWT_SECRET_KEY` - секретный ключ для JWT (измените на случайный!)
   - `YANDEX_MAPS_API_KEY` - ваш API ключ Yandex Maps

4. Запустите все сервисы:
```bash
docker-compose up -d
```

5. Дождитесь инициализации всех сервисов (может занять несколько минут)

6. Откройте браузер и перейдите на:
```
http://localhost:3000
```

### Тестовый аккаунт

При первом запуске автоматически создается тестовый пользователь:

- **Username:** `admin`
- **Password:** `admin123`
- **Email:** `admin@test.com`

Вы можете использовать эти данные для входа в систему.

### Проверка работы

Проверьте статус сервисов:
```bash
docker-compose ps
```

Проверьте логи:
```bash
docker-compose logs -f
```

## 📁 Структура проекта

```
diploma-bachelor/
├── docker-compose.yml          # Docker Compose конфигурация
├── init-db.sql                 # SQL скрипт инициализации БД
├── .env.example                # Пример переменных окружения
├── README.md                   # Этот файл
│
├── services/
│   ├── api_gateway/           # API Gateway сервис
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app.py
│   │
│   ├── auth_service/          # Сервис аутентификации
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app.py
│   │
│   ├── map_service/           # Сервис карты и площадок
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app.py
│   │
│   ├── game_session_service/  # Сервис игровых сессий
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app.py
│   │
│   └── notification_service/  # Сервис уведомлений
│       ├── Dockerfile
│       ├── requirements.txt
│       └── app.py
│
├── frontend/                  # React приложение
│   ├── Dockerfile
│   ├── package.json
│   ├── nginx.conf
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── App.js
│       ├── App.css
│       ├── index.js
│       ├── index.css
│       └── components/
│           ├── MapComponent.js
│           ├── VenueInfo.js
│           ├── VenueInfo.css
│           ├── LoginForm.js
│           └── LoginForm.css
│
└── nginx/                     # Nginx конфигурация
    └── nginx.conf
```

## 🔧 API Endpoints

### Auth Service

- `POST /auth/register` - Регистрация пользователя
- `POST /auth/login` - Авторизация
- `POST /auth/verify` - Проверка токена

### Map Service

- `GET /api/map/venues` - Список всех площадок
- `GET /api/map/venues/nearby?lat=X&lon=Y&radius=Z` - Поиск поблизости
- `GET /api/map/venues/{id}` - Информация о площадке
- `POST /api/map/venues` - Создание площадки
- `PUT /api/map/venues/{id}` - Обновление площадки
- `DELETE /api/map/venues/{id}` - Удаление площадки

### Game Session Service

- `GET /api/games/venue/{venue_id}` - Активные сессии на площадке
- `GET /api/games/{session_id}` - Информация о сессии
- `POST /api/games` - Создание сессии
- `POST /api/games/{session_id}/join` - Присоединение к сессии
- `POST /api/games/{session_id}/leave` - Покидание сессии
- `DELETE /api/games/{session_id}` - Удаление сессии

## 🗄️ База данных

### Схема БД

- **users** - пользователи
- **venues** - спортивные площадки (с геоданными PostGIS)
- **game_sessions** - игровые сессии
- **session_participants** - участники сессий

### Инициализация

База данных инициализируется автоматически при первом запуске через `init-db.sql`.

## 🔐 Безопасность

- Пароли хешируются с помощью bcrypt
- JWT токены для аутентификации
- CORS настроен для безопасности
- В production обязательно измените `JWT_SECRET_KEY`!

## 📝 Разработка

### Локальная разработка

Для разработки отдельных сервисов:

1. Остановите конкретный сервис:
```bash
docker-compose stop <service_name>
```

2. Запустите локально:
```bash
cd services/<service_name>
pip install -r requirements.txt
python app.py
```

### Добавление площадок

Площадки можно добавлять через API или напрямую в БД:

```sql
INSERT INTO venues (name, address, sport_type, location)
VALUES (
    'Футбольная площадка "Центральная"',
    'Москва, ул. Примерная, 1',
    'football',
    ST_SetSRID(ST_MakePoint(37.573856, 55.751574), 4326)
);
```
### Удаление всех площадок
```sql
docker-compose exec db psql -U postgres -d diploma_db < /dev/stdin << EOF
TRUNCATE TABLE session_participants CASCADE;
TRUNCATE TABLE game_sessions CASCADE;
EOF
```

## 🐛 Troubleshooting

### Проблемы с подключением к БД

Убедитесь, что PostgreSQL полностью инициализирован:
```bash
docker-compose logs postgres
```

### Проблемы с картой

1. Проверьте, что `YANDEX_MAPS_API_KEY` указан в `.env`
2. Проверьте консоль браузера на ошибки
3. Убедитесь, что API ключ активен в личном кабинете Yandex

### Проблемы с WebSocket

Проверьте, что Notification Service запущен:
```bash
docker-compose logs notification_service
```

## 📚 Технологии

- **Backend**: Flask, Flask-SQLAlchemy, Flask-SocketIO
- **Database**: PostgreSQL + PostGIS
- **Cache**: Redis
- **Message Broker**: RabbitMQ
- **Task Queue**: Celery
- **Frontend**: React, Yandex Maps API
- **Web Server**: Nginx
- **Containerization**: Docker, Docker Compose

## 🔄 Дальнейшее развитие

- [ ] Добавление геокодирования через Yandex Geocoder API
- [ ] Push-уведомления
- [ ] История игр пользователя
- [ ] Рейтинг игроков
- [ ] Чат для игровых сессий
- [ ] Мобильное приложение

## 📄 Лицензия

Этот проект создан в образовательных целях.

## 👤 Автор

Дипломная работа бакалавра
