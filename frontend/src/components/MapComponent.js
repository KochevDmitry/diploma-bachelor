import React, { useEffect, useRef, useState } from 'react';
import CreateEventForm from './CreateEventForm';
import EventInfo from './EventInfo';

const MapComponent = ({
  venues,
  events,
  onVenueSelect,
  onEventSelect,
  onCreateEvent,
  onJoinEvent,
  yandexApiKey,
  currentUser
}) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createFormCoords, setCreateFormCoords] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);

  useEffect(() => {
    console.log('=== MapComponent Debug ===');
    console.log('mapRef.current:', mapRef.current);
    console.log('window.ymaps3:', window.ymaps3);
    console.log('yandexApiKey:', yandexApiKey);
    console.log('venues:', venues);

    if (!mapRef.current) {
      console.error('ERROR: mapRef.current is null!');
      return;
    }

    // Функция инициализации карты
    const initMap = async () => {
      console.log('Waiting for ymaps3...');

      // Ждём загрузки API (с таймаутом)
      let attempts = 0;
      while (!window.ymaps3 && attempts < 50) {
        await new Promise(resolve => setTimeout(resolve, 100));
        attempts++;
      }

      if (!window.ymaps3) {
        console.error('ERROR: ymaps3 failed to load after 5 seconds');
        return;
      }

      console.log('ymaps3 loaded, waiting for ready...');
      await window.ymaps3.ready;
      console.log('ymaps3 is ready!');

      const {
        YMap,
        YMapDefaultSchemeLayer,
        YMapDefaultFeaturesLayer,
        YMapMarker,
        YMapControls
      } = window.ymaps3;

      const { YMapZoomControl } = await window.ymaps3.import('@yandex/ymaps3-controls@0.0.1');

      console.log('Creating map...');

      // Создаём карту
      const map = new YMap(mapRef.current, {
        location: {
          center: [37.617644, 55.755819], // [longitude, latitude] Москва
          zoom: 10
        }
      });

      // Добавляем базовые слои
      map.addChild(new YMapDefaultSchemeLayer());
      map.addChild(new YMapDefaultFeaturesLayer());

      // Добавляем контролы
      const controls = new YMapControls({ position: 'right' });
      controls.addChild(new YMapZoomControl({}));
      map.addChild(controls);

      // Обработчик клика для создания события
      // Используем встроенный в страницу обработчик на контейнер
      const handleMapClick = (e) => {
        // Находим был ли клик на маркере или на пустой части карты
        const targetElement = e.target;
        
        // Проверяем, что это не клик на маркер
        const isMarker = targetElement.closest('[class*="marker"]') || 
                        targetElement.closest('[class*="YMapMarker"]') ||
                        targetElement.closest('.event-marker') ||
                        targetElement.closest('.venue-marker');
        
        if (!isMarker) {
          // Используем центр карты с некторым смещением для демонстрации
          const lat = 55.755819 + (Math.random() - 0.5) * 0.05 * (Math.random() > 0.5 ? 1 : -1);
          const lon = 37.617644 + (Math.random() - 0.5) * 0.05 * (Math.random() > 0.5 ? 1 : -1);
          
          console.log('Map clicked, creating event at:', { lat, lon });
          setCreateFormCoords({ lat, lon });
          setShowCreateForm(true);
        }
      };
      
      // Регистрируем обработчик после небольшой задержки для стабильности
      setTimeout(() => {
        if (mapRef.current) {
          mapRef.current.addEventListener('click', handleMapClick, true);
          console.log('Map click handler registered');
        }
      }, 500);

      mapInstanceRef.current = map;
      console.log('Map created successfully!');

      // Добавляем маркеры
      addMarkers(map, venues);
    };

    initMap().catch(err => {
      console.error('Map initialization error:', err);
    });

    // Cleanup при размонтировании
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current = null;
      }
    };
  }, []); // Пустой массив зависимостей - инициализация один раз

  // Обновление маркеров при изменении venues или events
  useEffect(() => {
    if (mapInstanceRef.current) {
      console.log('Updating markers, venues count:', venues.length, 'events count:', events?.length || 0);
      addMarkers(mapInstanceRef.current, venues, events);
    }
  }, [venues, events]);

  // Функция добавления маркеров
  const addMarkers = (map, venuesList, eventsList = []) => {
    console.log('Adding markers for venues:', venuesList, 'and events:', eventsList);

    // Добавляем маркеры для venues
    venuesList.forEach((venue, index) => {
      if (!venue.coordinates || !venue.coordinates.lat || !venue.coordinates.lon) {
        console.warn(`Venue ${venue.name} has invalid coordinates:`, venue.coordinates);
        return;
      }

      console.log(`Adding marker for ${venue.name} at [${venue.coordinates.lon}, ${venue.coordinates.lat}]`);

      // Создаём HTML элемент для маркера
      const markerElement = document.createElement('div');
      markerElement.className = 'venue-marker';
      markerElement.innerHTML = `
        <div style="
          background: #ff0000;
          color: white;
          padding: 8px 12px;
          border-radius: 20px;
          font-size: 14px;
          font-weight: bold;
          cursor: pointer;
          box-shadow: 0 2px 6px rgba(0,0,0,0.3);
          white-space: nowrap;
        ">
          ${venue.name}
        </div>
      `;

      markerElement.onclick = () => {
        console.log('Venue marker clicked:', venue.name);
        onVenueSelect(venue);
      };

      const marker = new window.ymaps3.YMapMarker(
        {
          coordinates: [venue.coordinates.lon, venue.coordinates.lat], // [longitude, latitude]
          id: `venue-${venue.id}`
        },
        markerElement
      );

      map.addChild(marker);
    });

    // Добавляем маркеры для events
    eventsList.forEach((event, index) => {
      let lat, lon;

      if (event.latitude && event.longitude) {
        lat = event.latitude;
        lon = event.longitude;
      } else if (event.venue_id) {
        // Если событие привязано к venue, найдем координаты venue
        const venue = venuesList.find(v => v.id === event.venue_id);
        if (venue && venue.coordinates) {
          lat = venue.coordinates.lat;
          lon = venue.coordinates.lon;
        } else {
          console.warn(`Event ${event.id} has venue_id but venue coordinates not found`);
          return;
        }
      } else {
        console.warn(`Event ${event.id} has no coordinates`);
        return;
      }

      console.log(`Adding event marker for ${event.sport_type} at [${lon}, ${lat}]`);

      // Создаём HTML элемент для маркера события
      const markerElement = document.createElement('div');
      markerElement.className = 'event-marker';
      markerElement.innerHTML = `
        <div style="
          background: #28a745;
          color: white;
          padding: 6px 10px;
          border-radius: 15px;
          font-size: 12px;
          font-weight: bold;
          cursor: pointer;
          box-shadow: 0 2px 6px rgba(0,0,0,0.3);
          white-space: nowrap;
          border: 2px solid white;
        ">
          ${event.sport_type} (${event.current_players}/${event.max_players})
        </div>
      `;

      markerElement.onclick = (e) => {
        e.stopPropagation(); // Предотвращаем клик на карте
        console.log('Event marker clicked:', event.id);
        setSelectedEvent(event);
      };

      const marker = new window.ymaps3.YMapMarker(
        {
          coordinates: [lon, lat], // [longitude, latitude]
          id: `event-${event.id}`
        },
        markerElement
      );

      map.addChild(marker);
    });
  };

  const handleCreateEvent = async (eventData) => {
    try {
      await onCreateEvent(eventData);
      setShowCreateForm(false);
      setCreateFormCoords(null);
    } catch (error) {
      console.error('Error creating event:', error);
      alert('Ошибка при создании события');
    }
  };

  const handleCancelCreate = () => {
    setShowCreateForm(false);
    setCreateFormCoords(null);
  };

  const handleJoinEvent = async (eventId) => {
    try {
      await onJoinEvent(eventId);
      setSelectedEvent(null);
    } catch (error) {
      console.error('Error joining event:', error);
      alert('Ошибка при присоединении к событию');
    }
  };

  const handleCloseEventInfo = () => {
    setSelectedEvent(null);
  };

  // Рендерим формы поверх карты
  return (
    <>
      <div 
        ref={mapRef} 
        style={{ 
          width: '100%', 
          height: '100%',
          minHeight: '600px',
          backgroundColor: '#e0e0e0'
        }} 
      />
      
      {showCreateForm && createFormCoords && (
        <CreateEventForm
          latitude={createFormCoords.lat}
          longitude={createFormCoords.lon}
          onCreate={handleCreateEvent}
          onCancel={handleCancelCreate}
        />
      )}
      
      {selectedEvent && (
        <EventInfo
          event={selectedEvent}
          currentUser={currentUser}
          onJoinEvent={handleJoinEvent}
          onClose={handleCloseEventInfo}
        />
      )}
    </>
  );
};

export default MapComponent;