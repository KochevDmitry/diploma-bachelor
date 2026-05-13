import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import io from 'socket.io-client';
import MapComponent from './components/MapComponent';
import VenueInfo from './components/VenueInfo';
import UserSidebar from './components/UserSidebar';
import MyEventsOverlay from './components/MyEventsOverlay';
import HistoryOverlay from './components/HistoryOverlay';
import SettingsOverlay from './components/SettingsOverlay';
import EventInfo from './components/EventInfo';
import LoginForm from './components/LoginForm';
import CreateEventForm from './components/CreateEventForm';
import NotificationsModal from './components/NotificationsModal';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || '';
const WS_URL = process.env.REACT_APP_WS_URL || '';
const YANDEX_MAPS_API_KEY = process.env.REACT_APP_YANDEX_MAPS_API_KEY || '';

// Типы спорта для фильтрации
const SPORT_FILTERS = [
  { id: 'all', label: 'Все', icon: 'sports' },
  { id: 'football', label: 'Футбол', icon: 'sports_soccer' },
  { id: 'basketball', label: 'Баскетбол', icon: 'sports_basketball' },
  { id: 'volleyball', label: 'Волейбол', icon: 'sports_volleyball' },
  { id: 'tennis', label: 'Теннис', icon: 'sports_tennis' },
  { id: 'running', label: 'Бег', icon: 'directions_run' },
  { id: 'other', label: 'Другое', icon: 'sports_score' },
];

function App() {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [venues, setVenues] = useState([]);
  const [selectedVenue, setSelectedVenue] = useState(null);
  const [venueSessions, setVenueSessions] = useState([]);
  const [mapEvents, setMapEvents] = useState([]);
  const [socket, setSocket] = useState(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [isClosingLoginModal, setIsClosingLoginModal] = useState(false);
  const [showUserSidebar, setShowUserSidebar] = useState(false);
  const [showMyEvents, setShowMyEvents] = useState(false);
  const [skipMyEventsAnimation, setSkipMyEventsAnimation] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [skipHistoryAnimation, setSkipHistoryAnimation] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [selectedEventFromList, setSelectedEventFromList] = useState(null);
  const [activeFilter, setActiveFilter] = useState('all');
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  // Загрузка уведомлений из БД
  const loadNotifications = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/notifications`);
      const notifs = response.data.map(n => ({
        ...n,
        read: n.read || false
      }));
      setNotifications(notifs);
      setUnreadCount(notifs.filter(n => !n.read).length);
    } catch (error) {
      console.error('Error loading notifications:', error);
    }
  };

  const handleCloseLoginModal = () => {
    setIsClosingLoginModal(true);
    setTimeout(() => {
      setShowLoginModal(false);
      setIsClosingLoginModal(false);
    }, 200);
  };

  // Загрузка Yandex Maps API
  useEffect(() => {
    if (!window.ymaps && YANDEX_MAPS_API_KEY) {
      const script = document.createElement('script');
      script.src = `https://api-maps.yandex.ru/3.0/?apikey=${YANDEX_MAPS_API_KEY}&lang=ru_RU`;
      script.async = true;
      document.head.appendChild(script);
    }
  }, []);

  // Функции logout (определяем перед использованием в интерцепторе)
  const handleLogout = () => {
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    delete axios.defaults.headers.common['Authorization'];
    if (socket) {
      socket.close();
      setSocket(null);
    }
  };

  // Setup axios перехватчик для автоматического обновления токена
  useEffect(() => {
    const responseInterceptor = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const storedRefreshToken = localStorage.getItem('refreshToken');
        if (error.response?.status === 401 && storedRefreshToken) {
          try {
            // Пытаемся обновить токен
            const refreshResponse = await axios.post(
              `${API_URL || ''}/auth/refresh`,
              { refreshToken: storedRefreshToken }
            );
            
            const newAccessToken = refreshResponse.data.accessToken;
            localStorage.setItem('accessToken', newAccessToken);
            setAccessToken(newAccessToken);
            axios.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`;
            
            // Повторяем оригинальный запрос с новым токеном
            error.config.headers['Authorization'] = `Bearer ${newAccessToken}`;
            return axios(error.config);
          } catch (refreshError) {
            // Refresh не удался, очищаем все
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            setUser(null);
            setAccessToken(null);
            setRefreshToken(null);
            delete axios.defaults.headers.common['Authorization'];
            if (socket) {
              socket.close();
              setSocket(null);
            }
            return Promise.reject(refreshError);
          }
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.response.eject(responseInterceptor);
    };
  }, [socket]);

  // Инициализация сессии при монтировании компонента
  useEffect(() => {
    const initializeSession = async () => {
      const storedAccessToken = localStorage.getItem('accessToken');
      const storedRefreshToken = localStorage.getItem('refreshToken');

      if (storedAccessToken && storedRefreshToken) {
        setAccessToken(storedAccessToken);
        setRefreshToken(storedRefreshToken);
        axios.defaults.headers.common['Authorization'] = `Bearer ${storedAccessToken}`;

        try {
          // Проверяем валидность токена
          const response = await axios.post(`${API_URL || ''}/auth/verify`);
          console.log('✅ Токен валидный, пользователь восстановлен:', response.data.user.username);
          setUser(response.data.user);
          loadNotifications(); // Загружаем уведомления
          setIsInitializing(false);
          return;
        } catch (error) {
          console.warn('⚠️ Access token истек, пытаемся обновить...');
          // Токен истек, пытаемся обновить
          try {
            const refreshResponse = await axios.post(
              `${API_URL || ''}/auth/refresh`,
              { refreshToken: storedRefreshToken }
            );
            
            const newAccessToken = refreshResponse.data.accessToken;
            localStorage.setItem('accessToken', newAccessToken);
            setAccessToken(newAccessToken);
            setRefreshToken(storedRefreshToken);
            axios.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`;
            console.log('✅ Токен обновлен, пользователь восстановлен:', refreshResponse.data.user.username);
            setUser(refreshResponse.data.user);
            loadNotifications(); // Загружаем уведомления
            setIsInitializing(false);
            return;
          } catch (refreshError) {
            console.error('❌ Оба токена невалидны');
            // Оба токена невалидны
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            delete axios.defaults.headers.common['Authorization'];
          }
        }
      } else {
        console.log('ℹ️ Токены не найдены в localStorage');
      }

      setIsInitializing(false);
    };

    initializeSession();
  }, []);

  // Свежий selectedVenue для использования внутри WS-обработчиков
  // без пересоздания самого сокета на каждый клик по площадке.
  const selectedVenueRef = useRef(selectedVenue);
  useEffect(() => {
    selectedVenueRef.current = selectedVenue;
  }, [selectedVenue]);

  // Подключение к WebSocket
  useEffect(() => {
    if (user) {
      const newSocket = io(WS_URL);
      setSocket(newSocket);

      newSocket.on('connect', () => {
        console.log('Connected to WebSocket');
        // Аутентификация для получения персональных уведомлений
        newSocket.emit('authenticate', { user_id: user.id });
      });

      newSocket.on('connect_error', (err) => {
        console.error('WS connect_error:', err.message);
      });

      newSocket.on('disconnect', (reason) => {
        console.warn('WS disconnect:', reason);
      });

      newSocket.on('authenticated', (data) => {
        console.log('WebSocket authenticated:', data);
      });

      newSocket.on('venue_update', (data) => {
        console.log('Venue update:', data);
        const venue = selectedVenueRef.current;
        if (venue && data.venue_id === venue.id) {
          loadVenueSessions(venue.id);
        }
      });

      // Персональные уведомления (фильтрация на бэкенде)
      newSocket.on('notification', (data) => {
        console.log('Received notification:', data);

        const newNotification = {
          ...data,
          id: data.id || Date.now(),
          read: false,
        };

        setNotifications(prev => [newNotification, ...prev]);
        setUnreadCount(prev => prev + 1);
      });

      return () => {
        newSocket.close();
      };
    }
  }, [user]);

  // Загрузка площадок при монтировании
  useEffect(() => {
    console.log('� MOUNT useEffect: начальная загрузка площадок');
    loadVenues();
  }, []);

  // Загрузка событий когда инициализация завершена
  useEffect(() => {
    console.log('🔄 INIT_CHECK useEffect: isInitializing =', isInitializing);
    if (!isInitializing) {
      console.log('✅ Инициализация завершена, загружаем события. User:', user?.username);
      loadMapEvents();
    }
  }, [isInitializing]);

  // Перезагрузка событий когда пользователь входит/выходит
  useEffect(() => {
    if (user && !isInitializing) {
      console.log('👤 User вошел:', user.username, ', перезагружаем события');
      loadMapEvents();
    }
  }, [user?.id, isInitializing]);

  const loadVenues = async () => {
    try {
      console.log('📍 loadVenues: начинаем загрузку');
      const base = API_URL || '';
      const response = await axios.get(`${base}/api/map/venues`);
      console.log('📍 loadVenues: успешно, количество:', Array.isArray(response.data) ? response.data.length : 0);
      setVenues(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('❌ loadVenues ошибка:', error.response?.status, error.message);
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
      console.log('📍 loadMapEvents: начинаем загрузку');
      const response = await axios.get(`${API_URL}/api/games/map`);
      console.log('📍 loadMapEvents: успешно загружены', response.data);
      setMapEvents(response.data);
    } catch (error) {
      console.error('❌ loadMapEvents ошибка:', error.response?.status, error.message);
      setMapEvents([]);
    }
  };

  const handleLogin = (userData, newAccessToken, newRefreshToken) => {
    console.log('🔐 handleLogin called');
    console.log('  userData:', userData);
    console.log('  newAccessToken:', newAccessToken ? '(present)' : 'MISSING');
    console.log('  newRefreshToken:', newRefreshToken ? '(present)' : 'MISSING');
    
    setUser(userData);
    setAccessToken(newAccessToken);
    setRefreshToken(newRefreshToken);
    
    localStorage.setItem('accessToken', newAccessToken);
    localStorage.setItem('refreshToken', newRefreshToken);
    
    console.log('✅ localStorage after save:');
    console.log('  accessToken:', localStorage.getItem('accessToken') ? '(saved)' : 'NOT SAVED');
    console.log('  refreshToken:', localStorage.getItem('refreshToken') ? '(saved)' : 'NOT SAVED');
    
    axios.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`;
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
      // API Gateway будет добавлять creator_id из токена, но мы отправляем все данные
      const response = await axios.post(`${API_URL}/api/games`, eventData);
      console.log('Event created:', response.data);
      // Перезагружаем события на карте после небольшой задержки
      setTimeout(() => {
        loadMapEvents();
      }, 500);
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
      console.log('Joined event:', response.data);
      // Перезагружаем события на карте после небольшой задержки
      setTimeout(() => {
        loadMapEvents();
      }, 500);
      return response.data;
    } catch (error) {
      console.error('Error joining map event:', error);
      throw error;
    }
  };

  const handleLeaveMapEvent = async (eventId) => {
    if (!user) {
      setShowLoginModal(true);
      return;
    }
    try {
      const response = await axios.post(`${API_URL}/api/games/${eventId}/leave`, {
        user_id: user.id
      });
      console.log('Left event:', response.data);
      // Перезагружаем события на карте после небольшой задержки
      setTimeout(() => {
        loadMapEvents();
      }, 500);
      return response.data;
    } catch (error) {
      console.error('Error leaving map event:', error);
      throw error;
    }
  };

  const handleFinishMapEvent = async (eventId) => {
    if (!user) {
      setShowLoginModal(true);
      return;
    }
    try {
      const response = await axios.post(`${API_URL}/api/games/${eventId}/finish`, {
        user_id: user.id
      });
      console.log('Finished event:', response.data);
      // Перезагружаем события на карте после небольшой задержки
      setTimeout(() => {
        loadMapEvents();
      }, 500);
      return response.data;
    } catch (error) {
      console.error('Error finishing map event:', error);
      throw error;
    }
  };

  const handleUpdateMapEvent = async (eventId, updates) => {
    if (!user) {
      setShowLoginModal(true);
      return;
    }
    try {
      const response = await axios.post(`${API_URL}/api/games/${eventId}/update`, {
        user_id: user.id,
        ...updates
      });
      console.log('Updated event:', response.data);
      // Перезагружаем события на карте после небольшой задержки
      setTimeout(() => {
        loadMapEvents();
      }, 500);
      return response.data;
    } catch (error) {
      console.error('Error updating map event:', error);
      throw error;
    }
  };

  const handleLoginSuccess = (userData, newAccessToken, newRefreshToken) => {
    console.log('🔐 handleLoginSuccess: вход успешен, загружаем события');
    handleLogin(userData, newAccessToken, newRefreshToken);
    setShowLoginModal(false);
    // Явно загружаем события и уведомления после входа
    setTimeout(() => {
      console.log('📍 После входа: загружаем события и уведомления');
      loadMapEvents();
      loadNotifications();
    }, 100);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>SportSpot</h1>
        <div className="header-actions">
          {user ? (
            <>
              <button
                className={`header-icon-btn ${unreadCount > 0 ? 'has-badge' : ''}`}
                title="Уведомления"
                onClick={() => setShowNotifications(true)}
              >
                <span className="material-symbols-outlined">notifications</span>
                {unreadCount > 0 && (
                  <span className="header-badge">{unreadCount > 9 ? '9+' : unreadCount}</span>
                )}
              </button>
              <button className="header-icon-btn" title="Настройки" onClick={() => setShowSettings(true)}>
                <span className="material-symbols-outlined">settings</span>
              </button>
              <button
                className={`header-avatar-btn ${user.avatar_url ? 'has-avatar' : ''}`}
                onClick={() => setShowUserSidebar(true)}
                title={user.username}
              >
                {user.avatar_url ? (
                  <img
                    src={`${API_URL}${user.avatar_url}`}
                    alt={user.username}
                    className="header-avatar-img"
                  />
                ) : (
                  <span className="material-symbols-outlined">person</span>
                )}
              </button>
            </>
          ) : (
            <button className="header-login-btn" onClick={() => setShowLoginModal(true)}>
              Войти
            </button>
          )}
        </div>
      </header>
      <div className="app-content">
        <div className="map-container">
          {/* Filter Chips */}
          <div className="filter-bar">
            {SPORT_FILTERS.map((filter) => (
              <button
                key={filter.id}
                className={`filter-chip ${activeFilter === filter.id ? 'active' : ''}`}
                onClick={() => setActiveFilter(filter.id)}
              >
                <span className="material-symbols-outlined">{filter.icon}</span>
                <span>{filter.label}</span>
              </button>
            ))}
          </div>
          <MapComponent
            venues={venues}
            events={activeFilter === 'all' ? mapEvents : mapEvents.filter(e => e.sport_type === activeFilter)}
            onVenueSelect={handleVenueSelect}
            onEventSelect={() => {}} // Пока не используется
            onCreateEvent={handleCreateMapEvent}
            onJoinEvent={handleJoinMapEvent}
            onLeaveEvent={handleLeaveMapEvent}
            onFinishEvent={handleFinishMapEvent}
            onUpdateEvent={handleUpdateMapEvent}
            yandexApiKey={YANDEX_MAPS_API_KEY}
            currentUser={user}
          />
        </div>
        {selectedVenue && !showUserSidebar && (
          <VenueInfo
            venue={selectedVenue}
            sessions={venueSessions}
            currentUser={user}
            onCreateSession={handleCreateSession}
            onJoinSession={handleJoinSession}
          />
        )}
        {showUserSidebar && user && (
          <UserSidebar
            user={user}
            onLogout={() => {
              handleLogout();
              setShowUserSidebar(false);
            }}
            onClose={() => setShowUserSidebar(false)}
            onMyEventsClick={() => {
              setShowUserSidebar(false);
              setShowMyEvents(true);
            }}
            onHistoryClick={() => {
              setShowUserSidebar(false);
              setShowHistory(true);
            }}
          />
        )}

        {showMyEvents && user && (
          <MyEventsOverlay
            user={user}
            apiUrl={API_URL}
            skipAnimation={skipMyEventsAnimation}
            onClose={() => {
              setShowMyEvents(false);
              setSkipMyEventsAnimation(false);
              // setShowUserSidebar(true); // Возврат в сайдбар (закомментировано: возврат на карту)
            }}
            onEventClick={(event) => {
              setShowMyEvents(false);
              setSelectedEventFromList({ ...event, _returnTo: 'myEvents' });
            }}
          />
        )}

        {showHistory && user && (
          <HistoryOverlay
            user={user}
            apiUrl={API_URL}
            skipAnimation={skipHistoryAnimation}
            onClose={() => {
              setShowHistory(false);
              setSkipHistoryAnimation(false);
              // setShowUserSidebar(true); // Возврат в сайдбар (закомментировано: возврат на карту)
            }}
          />
        )}

        {showSettings && user && (
          <SettingsOverlay
            user={user}
            onClose={() => setShowSettings(false)}
            onUpdateProfile={async (profileData) => {
              try {
                const response = await axios.post(`${API_URL}/auth/profile`, profileData);
                if (response.data.user) {
                  setUser(response.data.user);
                }
                if (response.data.accessToken) {
                  localStorage.setItem('accessToken', response.data.accessToken);
                  setAccessToken(response.data.accessToken);
                  axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.accessToken}`;
                }
                return response.data;
              } catch (error) {
                console.error('Error updating profile:', error);
                throw error;
              }
            }}
            onUserUpdate={(updatedUser) => setUser(updatedUser)}
          />
        )}

        {selectedEventFromList && (
          <EventInfo
            event={selectedEventFromList}
            currentUser={user}
            onJoinEvent={async (eventId) => {
              await handleJoinMapEvent(eventId);
              const returnTo = selectedEventFromList._returnTo;
              setSelectedEventFromList(null);
              if (returnTo === 'myEvents') setShowMyEvents(true);
              else if (returnTo === 'history') setShowHistory(true);
            }}
            onLeaveEvent={async (eventId) => {
              await handleLeaveMapEvent(eventId);
              const returnTo = selectedEventFromList._returnTo;
              setSelectedEventFromList(null);
              if (returnTo === 'myEvents') setShowMyEvents(true);
              else if (returnTo === 'history') setShowHistory(true);
            }}
            onFinishEvent={async (eventId) => {
              await handleFinishMapEvent(eventId);
              const returnTo = selectedEventFromList._returnTo;
              setSelectedEventFromList(null);
              if (returnTo === 'myEvents') setShowMyEvents(true);
              else if (returnTo === 'history') setShowHistory(true);
            }}
            onUpdateEvent={async (eventId, updates) => {
              const updated = await handleUpdateMapEvent(eventId, updates);
              setSelectedEventFromList({ ...updated, _returnTo: selectedEventFromList._returnTo });
            }}
            onClose={() => {
              const returnTo = selectedEventFromList._returnTo;
              setSelectedEventFromList(null);
              if (returnTo === 'myEvents') {
                setSkipMyEventsAnimation(true);
                setShowMyEvents(true);
              } else if (returnTo === 'history') {
                setSkipHistoryAnimation(true);
                setShowHistory(true);
              }
            }}
          />
        )}
      </div>
      {showLoginModal && (
        <div className={`modal-overlay ${isClosingLoginModal ? 'closing' : ''}`} onClick={handleCloseLoginModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={handleCloseLoginModal}>×</button>
            <LoginForm onLogin={handleLoginSuccess} apiUrl={API_URL} />
          </div>
        </div>
      )}

      {showNotifications && (
        <NotificationsModal
          notifications={notifications}
          onClose={() => setShowNotifications(false)}
          onClear={async () => {
            // Удаляем все уведомления из БД
            try {
              await axios.delete(`${API_URL}/api/notifications`);
            } catch (e) {
              console.error('Error deleting notifications:', e);
            }
            setNotifications([]);
            setUnreadCount(0);
          }}
          onNotificationClick={async (notification) => {
            // Помечаем как прочитанное если ещё не прочитано
            if (!notification.read) {
              try {
                await axios.post(`${API_URL}/api/notifications/read`, { ids: [notification.id] });
                setNotifications(prev => prev.map(n =>
                  n.id === notification.id ? { ...n, read: true } : n
                ));
                setUnreadCount(prev => Math.max(0, prev - 1));
              } catch (e) {
                console.error('Error marking notification read:', e);
              }
            }
          }}
        />
      )}
    </div>
  );
}

export default App;
