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
  onLeaveEvent,
  onFinishEvent,
  onUpdateEvent,
  yandexApiKey,
  currentUser
}) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]); // Отслеживаем маркеры для очистки
  const [mapReady, setMapReady] = useState(false); // State флаг для готовности карты
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createFormCoords, setCreateFormCoords] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const mouseDownRef = useRef(null); // Отслеживаем, был ли это drag или клик

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

      // Используем YMapListener для обработки событий клика
      const mapListener = new window.ymaps3.YMapListener({
        onClick: (object, mapEvent) => {
          console.log('Map clicked - object:', object, 'mapEvent:', mapEvent);
          
          // Проверяем, был ли клик на маркере
          if (object) {
            console.log('Clicked on object, ignoring');
            return;
          }

          // mapEvent.coordinates содержит [longitude, latitude]
          if (mapEvent && mapEvent.coordinates) {
            const [lon, lat] = mapEvent.coordinates;
            console.log('Map clicked, creating event at:', { lat, lon });
            
            setCreateFormCoords({ lat, lon });
            setShowCreateForm(true);
          } else {
            console.error('No coordinates in mapEvent');
          }
        }
      });
      
      map.addChild(mapListener);

      mapInstanceRef.current = map;
      console.log('Map created successfully! venues:', venues?.length || 0, 'events:', events?.length || 0);
      setMapReady(true); // 🗺️ Флаг что карта готова

      // Добавляем маркеры с текущими значениями
      console.log('🗺️  Adding markers after map init');
      addMarkers(map, venues, events);
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
    console.log('🗺️  venues/events changed useEffect');
    console.log('  mapReady:', mapReady, 'venues:', venues?.length || 0, 'events:', events?.length || 0);
    
    if (mapReady && mapInstanceRef.current) {
      console.log('🗺️  Map ready, updating markers');
      addMarkers(mapInstanceRef.current, venues, events);
    } else {
      console.warn('⚠️  Map not ready yet (mapReady:', mapReady, ')');
    }
  }, [venues, events, mapReady]);

  // Функция добавления маркеров
  const addMarkers = (map, venuesList, eventsList = []) => {
    console.log('🗺️  addMarkers called');
    
    // Очищаем старые маркеры
    console.log('  Removing', markersRef.current.length, 'old markers');
    markersRef.current.forEach(marker => {
      map.removeChild(marker);
    });
    markersRef.current = [];

    console.log('Adding markers for venues:', venuesList.length, 'and events:', eventsList.length);

    // Добавляем маркеры для venues
    venuesList.forEach((venue, index) => {
      if (!venue.coordinates || !venue.coordinates.lat || !venue.coordinates.lon) {
        console.warn(`Venue ${venue.name} has invalid coordinates:`, venue.coordinates);
        return;
      }

      console.log(`Adding marker for ${venue.name} at [${venue.coordinates.lon}, ${venue.coordinates.lat}]`);

      // Создаём HTML элемент для маркера - новый дизайн
      const markerElement = document.createElement('div');
      markerElement.className = 'venue-marker';
      markerElement.innerHTML = `
        <div style="
          background: linear-gradient(135deg, #a33800 0%, #ffc4af 100%);
          color: #ffefeb;
          padding: 10px 16px;
          border-radius: 9999px;
          font-family: 'Lexend', sans-serif;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          box-shadow: 0 8px 20px -4px rgba(12, 14, 16, 0.2);
          white-space: nowrap;
          transition: all 0.25s ease;
        ">
          ${venue.name}
        </div>
      `;

      markerElement.onclick = (e) => {
        e.stopPropagation(); // Предотвращаем срабатывание обработчика карты
        mouseDownRef.current = null; // Очищаем флаг
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
      markersRef.current.push(marker);
    });

    // Добавляем маркеры для events
    eventsList.forEach((event, index) => {
      console.log(`Processing event ${index}:`, event);
      let lat, lon;

      if (event.latitude && event.longitude) {
        lat = event.latitude;
        lon = event.longitude;
        console.log(`  ✅ Has direct coordinates: [${lon}, ${lat}]`);
      } else if (event.venue_id) {
        // Если событие привязано к venue, найдем координаты venue
        const venue = venuesList.find(v => v.id === event.venue_id);
        if (venue && venue.coordinates) {
          lat = venue.coordinates.lat;
          lon = venue.coordinates.lon;
          console.log(`  ✅ Found venue ${event.venue_id} coordinates: [${lon}, ${lat}]`);
        } else {
          console.warn(`  ⚠️ Event ${event.id} has venue_id ${event.venue_id} but venue coordinates not found`);
          return;
        }
      } else {
        console.warn(`  ⚠️ Event ${event.id} has no coordinates:`, { latitude: event.latitude, longitude: event.longitude, venue_id: event.venue_id });
        return;
      }

      console.log(`📍 Adding event marker for ${event.sport_type} at [${lon}, ${lat}]`);

      // Создаём HTML элемент для маркера события - новый дизайн
      const markerElement = document.createElement('div');
      markerElement.className = 'event-marker';
      markerElement.innerHTML = `
        <div style="
          background: linear-gradient(135deg, #0049e6 0%, #829bff 100%);
          color: #f2f1ff;
          padding: 10px 16px;
          border-radius: 9999px;
          font-family: 'Inter', sans-serif;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          box-shadow: 0 8px 20px -4px rgba(12, 14, 16, 0.2);
          white-space: nowrap;
          transition: all 0.25s ease;
          display: flex;
          align-items: center;
          gap: 6px;
        ">
          <span style="font-family: 'Lexend', sans-serif;">${event.sport_type}</span>
          <span style="
            background: rgba(255,255,255,0.2);
            padding: 2px 8px;
            border-radius: 9999px;
            font-size: 11px;
          ">${event.current_players}/${event.max_players}</span>
        </div>
      `;

      markerElement.onclick = (e) => {
        e.stopPropagation(); // Предотвращаем клик на карте
        mouseDownRef.current = null; // Очищаем флаг
        console.log('Event marker clicked:', event.id);
        console.log('Setting selected event:', event);
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
      markersRef.current.push(marker);
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

  const handleLeaveEvent = async (eventId) => {
    try {
      await onLeaveEvent(eventId);
      setSelectedEvent(null);
    } catch (error) {
      console.error('Error leaving event:', error);
      alert('Ошибка при выходе из события');
    }
  };

  const handleFinishEvent = async (eventId) => {
    try {
      await onFinishEvent(eventId);
      setSelectedEvent(null);
    } catch (error) {
      console.error('Error finishing event:', error);
      alert('Ошибка при завершении события');
    }
  };

  const handleUpdateEvent = async (eventId, updates) => {
    try {
      const updatedEvent = await onUpdateEvent(eventId, updates);
      setSelectedEvent(updatedEvent);
    } catch (error) {
      console.error('Error updating event:', error);
      alert('Ошибка при обновлении события');
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
          onLeaveEvent={handleLeaveEvent}
          onFinishEvent={handleFinishEvent}
          onUpdateEvent={handleUpdateEvent}
          onClose={handleCloseEventInfo}
        />
      )}
    </>
  );
};

export default MapComponent;