import React, { useState, useEffect } from 'react';
import axios from 'axios';
import io from 'socket.io-client';
import MapComponent from './components/MapComponent';
import VenueInfo from './components/VenueInfo';
import LoginForm from './components/LoginForm';
import CreateEventForm from './components/CreateEventForm';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || '';
const WS_URL = process.env.REACT_APP_WS_URL || '';
const YANDEX_MAPS_API_KEY = process.env.REACT_APP_YANDEX_MAPS_API_KEY || '';

function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [venues, setVenues] = useState([]);
  const [selectedVenue, setSelectedVenue] = useState(null);
  const [venueSessions, setVenueSessions] = useState([]);
  const [mapEvents, setMapEvents] = useState([]);
  const [socket, setSocket] = useState(null);
  const [showLoginModal, setShowLoginModal] = useState(false);

  // Загрузка Yandex Maps API
  useEffect(() => {
    if (!window.ymaps && YANDEX_MAPS_API_KEY) {
      const script = document.createElement('script');
      script.src = `https://api-maps.yandex.ru/3.0/?apikey=${YANDEX_MAPS_API_KEY}&lang=ru_RU`;
      script.async = true;
      document.head.appendChild(script);
    }
  }, []);

  // Инициализация axios с токеном
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      // Проверка токена
      axios.get(`${API_URL || ''}/auth/verify`)
        .then(response => {
          setUser(response.data.user);
        })
        .catch(() => {
          localStorage.removeItem('token');
          setToken(null);
        });
    }
  }, [token]);

  // Подключение к WebSocket
  useEffect(() => {
    if (user) {
      const newSocket = io(WS_URL);
      setSocket(newSocket);

      newSocket.on('connect', () => {
        console.log('Connected to WebSocket');
      });

      newSocket.on('venue_update', (data) => {
        console.log('Venue update:', data);
        // Обновление данных о площадке
        if (selectedVenue && data.venue_id === selectedVenue.id) {
          loadVenueSessions(selectedVenue.id);
        }
      });

      return () => {
        newSocket.close();
      };
    }
  }, [user, selectedVenue]);

  // Загрузка площадок
  useEffect(() => {
    loadVenues();
    loadMapEvents();
  }, []);

  const loadVenues = async () => {
    try {
      const base = API_URL || '';
      const response = await axios.get(`${base}/api/map/venues`);
      setVenues(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Error loading venues:', error);
      setVenues([]);
    }
  };

  const loadVenueSessions = async (venueId) => {
    try {
      const response = await axios.get(`${API_URL}/api/games/venue/${venueId}`);
      setVenueSessions(response.data);
    } catch (error) {
      console.error('Error loading venue sessions:', error);
    }
  };

  const loadMapEvents = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/games/map`);
      setMapEvents(response.data);
    } catch (error) {
      console.error('Error loading map events:', error);
      setMapEvents([]);
    }
  };

  const handleLogin = (userData, authToken) => {
    setUser(userData);
    setToken(authToken);
    localStorage.setItem('token', authToken);
    axios.defaults.headers.common['Authorization'] = `Bearer ${authToken}`;
  };

  const handleLogout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    if (socket) {
      socket.close();
      setSocket(null);
    }
  };

  const handleVenueSelect = (venue) => {
    setSelectedVenue(venue);
    // Загружаем сессии даже без авторизации (для просмотра)
    loadVenueSessions(venue.id);
    if (user && socket) {
      socket.emit('subscribe_venue', { venue_id: venue.id });
    }
  };

  const handleCreateSession = async (venueId, sportType, maxPlayers) => {
    if (!user) {
      setShowLoginModal(true);
      return;
    }
    try {
      const response = await axios.post(`${API_URL}/api/games`, {
        venue_id: venueId,
        creator_id: user.id,
        sport_type: sportType,
        max_players: maxPlayers
      });
      loadVenueSessions(venueId);
      return response.data;
    } catch (error) {
      console.error('Error creating session:', error);
      throw error;
    }
  };

  const handleJoinSession = async (sessionId) => {
    if (!user) {
      setShowLoginModal(true);
      return;
    }
    try {
      const response = await axios.post(`${API_URL}/api/games/${sessionId}/join`, {
        user_id: user.id
      });
      loadVenueSessions(selectedVenue.id);
      return response.data;
    } catch (error) {
      console.error('Error joining session:', error);
      throw error;
    }
  };

  const handleCreateMapEvent = async (eventData) => {
    if (!user) {
      setShowLoginModal(true);
      return;
    }
    try {
      const response = await axios.post(`${API_URL}/api/games`, eventData, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      loadMapEvents(); // Перезагружаем события на карте
      return response.data;
    } catch (error) {
      console.error('Error creating map event:', error);
      throw error;
    }
  };

  const handleJoinMapEvent = async (eventId) => {
    if (!user) {
      setShowLoginModal(true);
      return;
    }
    try {
      const response = await axios.post(`${API_URL}/api/games/${eventId}/join`, {
        user_id: user.id
      });
      loadMapEvents(); // Перезагружаем события на карте
      return response.data;
    } catch (error) {
      console.error('Error joining map event:', error);
      throw error;
    }
  };

  const handleLoginSuccess = (userData, authToken) => {
    handleLogin(userData, authToken);
    setShowLoginModal(false);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>SportApp - Поиск игроков</h1>
        <div className="user-info">
          {user ? (
            <>
              <span>Привет, {user.username}!</span>
              <button onClick={handleLogout}>Выйти</button>
            </>
          ) : (
            <button onClick={() => setShowLoginModal(true)}>Войти</button>
          )}
        </div>
      </header>
      <div className="app-content">
        <div className="map-container">
          <MapComponent
            venues={venues}
            events={mapEvents}
            onVenueSelect={handleVenueSelect}
            onEventSelect={() => {}} // Пока не используется
            onCreateEvent={handleCreateMapEvent}
            onJoinEvent={handleJoinMapEvent}
            yandexApiKey={YANDEX_MAPS_API_KEY}
            currentUser={user}
          />
        </div>
        {selectedVenue && (
          <VenueInfo
            venue={selectedVenue}
            sessions={venueSessions}
            currentUser={user}
            onCreateSession={handleCreateSession}
            onJoinSession={handleJoinSession}
          />
        )}
      </div>
      {showLoginModal && (
        <div className="modal-overlay" onClick={() => setShowLoginModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowLoginModal(false)}>×</button>
            <LoginForm onLogin={handleLoginSuccess} apiUrl={API_URL} />
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
