import React, { useEffect, useRef } from 'react';

const MapComponent = ({ venues, onVenueSelect, yandexApiKey }) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);

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

  // Обновление маркеров при изменении venues
  useEffect(() => {
    if (mapInstanceRef.current && venues.length > 0) {
      console.log('Updating markers, venues count:', venues.length);
      addMarkers(mapInstanceRef.current, venues);
    }
  }, [venues]);

  // Функция добавления маркеров
  const addMarkers = (map, venuesList) => {
    console.log('Adding markers for venues:', venuesList);

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
        console.log('Marker clicked:', venue.name);
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
  };

  return (
    <div 
      ref={mapRef} 
      style={{ 
        width: '100%', 
        height: '100%',
        minHeight: '600px',
        backgroundColor: '#e0e0e0' // Чтобы видеть, что контейнер есть
      }} 
    />
  );
};

export default MapComponent;