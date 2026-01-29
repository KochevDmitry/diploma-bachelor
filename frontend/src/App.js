import React, { useState, useEffect } from 'react';
import axios from 'axios';
import io from 'socket.io-client';
import MapComponent from './components/MapComponent';
import VenueInfo from './components/VenueInfo';
import LoginForm from './components/LoginForm';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost';
const WS_URL = process.env.REACT_APP_WS_URL || 'http://localhost';
const YANDEX_MAPS_API_KEY = process.env.REACT_APP_YANDEX_MAPS_API_KEY || '';

function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [venues, setVenues] = useState([]);
  const [selectedVenue, setSelectedVenue] = useState(null);
  const [venueSessions, setVenueSessions] = useState([]);
  const [socket, setSocket] = useState(null);

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
      axios.get(`${API_URL}/auth/verify`)
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
  }, []);

  const loadVenues = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/map/venues`);
      setVenues(response.data);
    } catch (error) {
      console.error('Error loading venues:', error);
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
    if (user) {
      loadVenueSessions(venue.id);
      if (socket) {
        socket.emit('subscribe_venue', { venue_id: venue.id });
      }
    }
  };

  const handleCreateSession = async (venueId, sportType, maxPlayers) => {
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

  if (!user) {
    return <LoginForm onLogin={handleLogin} apiUrl={API_URL} />;
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>SportApp - Поиск игроков</h1>
        <div className="user-info">
          <span>Привет, {user.username}!</span>
          <button onClick={handleLogout}>Выйти</button>
        </div>
      </header>
      <div className="app-content">
        <div className="map-container">
          <MapComponent
            venues={venues}
            onVenueSelect={handleVenueSelect}
            yandexApiKey={YANDEX_MAPS_API_KEY}
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
    </div>
  );
}

export default App;
