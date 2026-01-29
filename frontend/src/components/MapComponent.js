import React, { useEffect, useRef } from 'react';

const MapComponent = ({ venues, onVenueSelect, yandexApiKey }) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);

  useEffect(() => {
    if (!window.ymaps || !mapRef.current) return;

    // Инициализация карты
    window.ymaps.ready(() => {
      const map = new window.ymaps.Map(mapRef.current, {
        center: [55.751574, 37.573856], // Москва по умолчанию
        zoom: 10
      });

      mapInstanceRef.current = map;

      // Добавление маркеров для всех площадок
      updateMarkers(venues, map);
    });
  }, []);

  useEffect(() => {
    if (mapInstanceRef.current && venues.length > 0) {
      updateMarkers(venues, mapInstanceRef.current);
    }
  }, [venues]);

  const updateMarkers = (venuesList, map) => {
    // Удаление старых маркеров
    markersRef.current.forEach(marker => {
      map.geoObjects.remove(marker);
    });
    markersRef.current = [];

    // Добавление новых маркеров
    venuesList.forEach(venue => {
      if (venue.coordinates && venue.coordinates.lat && venue.coordinates.lon) {
        const marker = new window.ymaps.Placemark(
          [venue.coordinates.lat, venue.coordinates.lon],
          {
            balloonContent: `<strong>${venue.name}</strong><br>${venue.address || ''}`,
            iconCaption: venue.name
          },
          {
            preset: 'islands#sportIcon'
          }
        );

        marker.events.add('click', () => {
          onVenueSelect(venue);
        });

        map.geoObjects.add(marker);
        markersRef.current.push(marker);
      }
    });
  };

  return <div ref={mapRef} style={{ width: '100%', height: '100%' }} />;
};

export default MapComponent;
