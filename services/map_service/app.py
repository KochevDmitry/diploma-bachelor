"""
Map Service - управление площадками и геолокацией
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
from geoalchemy2.functions import ST_AsGeoJSON, ST_Point, ST_Distance
from sqlalchemy import func
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

# Redis для кеширования
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))


# Модель площадки
class Venue(db.Model):
    __tablename__ = 'venues'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text)
    sport_type = db.Column(db.String(50))
    location = db.Column(Geometry('POINT', srid=4326))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    def to_dict(self):
        # Получение координат из PostGIS
        location_json = db.session.scalar(
            ST_AsGeoJSON(self.location)
        )
        location_data = json.loads(location_json) if location_json else None
        
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'sport_type': self.sport_type,
            'location': location_data,
            'coordinates': {
                'lat': location_data['coordinates'][1] if location_data else None,
                'lon': location_data['coordinates'][0] if location_data else None
            } if location_data else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'map_service'}), 200


@app.route('/api/map/venues', methods=['GET'])
def get_venues():
    """Получение списка всех площадок"""
    # Попытка получить из кеша
    cache_key = 'venues:all'
    cached = redis_client.get(cache_key)
    
    if cached:
        return jsonify(json.loads(cached)), 200
    
    venues = Venue.query.all()
    result = [venue.to_dict() for venue in venues]
    
    # Кеширование на 5 минут
    redis_client.setex(cache_key, 300, json.dumps(result))
    
    return jsonify(result), 200


@app.route('/api/map/venues/nearby', methods=['GET'])
def get_nearby_venues():
    """Поиск площадок поблизости"""
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
        ST_Distance(Venue.location, point) <= radius * 1000  # конвертация в метры
    )
    
    if sport_type:
        query = query.filter(Venue.sport_type == sport_type)
    
    results = query.order_by('distance').all()
    
    venues = []
    for venue, distance in results:
        venue_dict = venue.to_dict()
        venue_dict['distance'] = round(distance / 1000, 2)  # конвертация в км
        venues.append(venue_dict)
    
    return jsonify(venues), 200


@app.route('/api/map/venues/<int:venue_id>', methods=['GET'])
def get_venue(venue_id):
    """Получение информации о конкретной площадке"""
    venue = Venue.query.get_or_404(venue_id)
    return jsonify(venue.to_dict()), 200


@app.route('/api/map/venues', methods=['POST'])
def create_venue():
    """Создание новой площадки"""
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
    
    try:
        db.session.add(venue)
        db.session.commit()
        
        # Очистка кеша
        redis_client.delete('venues:all')
        
        return jsonify(venue.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/map/venues/<int:venue_id>', methods=['PUT'])
def update_venue(venue_id):
    """Обновление информации о площадке"""
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
    
    try:
        db.session.commit()
        
        # Очистка кеша
        redis_client.delete('venues:all')
        
        return jsonify(venue.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/map/venues/<int:venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    """Удаление площадки"""
    venue = Venue.query.get_or_404(venue_id)
    
    try:
        db.session.delete(venue)
        db.session.commit()
        
        # Очистка кеша
        redis_client.delete('venues:all')
        
        return jsonify({'message': 'Venue deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
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


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    port = int(os.getenv('SERVICE_PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=False)
