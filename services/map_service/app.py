"""
Map Service - управление площадками и геолокацией
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_AsGeoJSON, ST_Point, ST_Distance
import redis
import os
import json

app = Flask(__name__)
CORS(app)

# Конфигурация
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'postgresql://sportapp_user:sportapp_password@postgres:5432/sportapp_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Redis для кеширования (опционально)
def get_redis():
    try:
        return redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))
    except Exception:
        return None

redis_client = get_redis()


# Модель площадки
class Venue(db.Model):
    __tablename__ = 'venues'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text)
    sport_type = db.Column(db.String(50))
    location = db.Column(Geography('POINT', srid=4326))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    def to_dict(self):
        """Безопасная сериализация с обработкой ошибок"""
        try:
            # Получение координат из PostGIS
            if self.location is not None:
                location_json = db.session.scalar(
                    ST_AsGeoJSON(self.location)
                )
                location_data = json.loads(location_json) if location_json else None
                
                coordinates = {
                    'lat': location_data['coordinates'][1] if location_data else None,
                    'lon': location_data['coordinates'][0] if location_data else None
                } if location_data else None
            else:
                location_data = None
                coordinates = None
                
        except Exception as e:
            print(f"Error parsing location for venue {self.id}: {e}")
            location_data = None
            coordinates = None
        
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'sport_type': self.sport_type,
            'location': location_data,
            'coordinates': coordinates,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        # Проверка подключения к БД
        db.session.execute(db.text('SELECT 1'))
        db_status = 'ok'
    except Exception as e:
        db_status = f'error: {str(e)}'
    
    return jsonify({
        'status': 'ok', 
        'service': 'map_service',
        'database': db_status
    }), 200


@app.route('/api/map/venues', methods=['GET'])
def get_venues():
    """Получение списка всех площадок"""
    # Попытка использовать кеш
    cache_key = 'venues:all'
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                print("Returning venues from cache")
                return jsonify(json.loads(cached)), 200
        except Exception as e:
            print(f"Redis error: {e}")

    try:
        venues = Venue.query.all()
        result = []
        
        for venue in venues:
            try:
                venue_dict = venue.to_dict()
                result.append(venue_dict)
            except Exception as e:
                print(f"Error serializing venue {venue.id}: {e}")
                # Добавляем минимальную информацию
                result.append({
                    'id': venue.id,
                    'name': venue.name,
                    'address': venue.address,
                    'sport_type': venue.sport_type,
                    'coordinates': None,
                    'location': None,
                    'created_at': venue.created_at.isoformat() if venue.created_at else None,
                    'error': 'Failed to parse location'
                })
        
        # Кешируем результат
        if redis_client:
            try:
                redis_client.setex(cache_key, 300, json.dumps(result))
            except Exception as e:
                print(f"Failed to cache: {e}")

        return jsonify(result), 200
        
    except Exception as e:
        print(f"Database error in get_venues: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'error': 'Service unavailable',
            'detail': str(e)
        }), 503


@app.route('/api/map/venues/nearby', methods=['GET'])
def get_nearby_venues():
    """Поиск площадок поблизости"""
    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        radius = request.args.get('radius', default=5.0, type=float)  # радиус в км
        sport_type = request.args.get('sport_type', type=str)
        
        if not lat or not lon:
            return jsonify({'error': 'Missing lat or lon parameters'}), 400
        
        # Создание точки из координат
        point = ST_Point(lon, lat, srid=4326)
        
        # Запрос площадок в радиусе
        query = db.session.query(
            Venue,
            ST_Distance(Venue.location, point).label('distance')
        ).filter(
            Venue.location.isnot(None),
            ST_Distance(Venue.location, point) <= radius * 1000  # конвертация в метры
        )
        
        if sport_type:
            query = query.filter(Venue.sport_type == sport_type)
        
        results = query.order_by('distance').all()
        
        venues = []
        for venue, distance in results:
            try:
                venue_dict = venue.to_dict()
                venue_dict['distance'] = round(distance / 1000, 2)  # конвертация в км
                venues.append(venue_dict)
            except Exception as e:
                print(f"Error processing nearby venue {venue.id}: {e}")
                continue
        
        return jsonify(venues), 200
        
    except Exception as e:
        print(f"Error in get_nearby_venues: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/map/venues/<int:venue_id>', methods=['GET'])
def get_venue(venue_id):
    """Получение информации о конкретной площадке"""
    try:
        venue = Venue.query.get_or_404(venue_id)
        return jsonify(venue.to_dict()), 200
    except Exception as e:
        print(f"Error getting venue {venue_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/map/venues', methods=['POST'])
def create_venue():
    """Создание новой площадки"""
    try:
        data = request.get_json()
        
        if not data or not data.get('name') or not data.get('lat') or not data.get('lon'):
            return jsonify({'error': 'Missing required fields: name, lat, lon'}), 400
        
        # Создание точки из координат
        point = ST_Point(data['lon'], data['lat'], srid=4326)
        
        venue = Venue(
            name=data['name'],
            address=data.get('address'),
            sport_type=data.get('sport_type', 'football'),
            location=point
        )
        
        db.session.add(venue)
        db.session.commit()
        
        # Очистка кеша
        if redis_client:
            try:
                redis_client.delete('venues:all')
            except Exception:
                pass
                
        return jsonify(venue.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating venue: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/map/venues/<int:venue_id>', methods=['PUT'])
def update_venue(venue_id):
    """Обновление информации о площадке"""
    try:
        venue = Venue.query.get_or_404(venue_id)
        data = request.get_json()
        
        if data.get('name'):
            venue.name = data['name']
        if data.get('address'):
            venue.address = data['address']
        if data.get('sport_type'):
            venue.sport_type = data['sport_type']
        if data.get('lat') and data.get('lon'):
            venue.location = ST_Point(data['lon'], data['lat'], srid=4326)
        
        db.session.commit()
        
        # Очистка кеша
        if redis_client:
            try:
                redis_client.delete('venues:all')
            except Exception:
                pass
                
        return jsonify(venue.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating venue {venue_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/map/venues/<int:venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    """Удаление площадки"""
    try:
        venue = Venue.query.get_or_404(venue_id)
        
        db.session.delete(venue)
        db.session.commit()
        
        # Очистка кеша
        if redis_client:
            try:
                redis_client.delete('venues:all')
            except Exception:
                pass
                
        return jsonify({'message': 'Venue deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting venue {venue_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/map/coordinates', methods=['POST'])
def get_address_from_coordinates():
    """Получение адреса по координатам (для обратного геокодирования)"""
    data = request.get_json()
    
    if not data or not data.get('lat') or not data.get('lon'):
        return jsonify({'error': 'Missing lat or lon'}), 400
    
    # Здесь можно интегрировать с Yandex Geocoder API
    # Пока возвращаем координаты
    return jsonify({
        'lat': data['lat'],
        'lon': data['lon'],
        'address': f"Координаты: {data['lat']}, {data['lon']}"
    }), 200


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Error creating tables: {e}")
    
    port = int(os.getenv('SERVICE_PORT', 5002))
    print(f"Starting map service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)