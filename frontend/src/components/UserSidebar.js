import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './UserSidebar.css';

const SPORT_LABELS = {
  football: 'Футбол',
  basketball: 'Баскетбол',
  volleyball: 'Волейбол',
  tennis: 'Теннис',
  running: 'Бег',
  other: 'Другое',
};

const STATUS_LABELS = {
  waiting: 'Ожидание',
  full: 'Набрано',
  started: 'Идёт игра',
  finished: 'Завершена',
};

const UserSidebar = ({ user, apiUrl, onLogout, onClose }) => {
  const [activeTab, setActiveTab] = useState('events'); // 'events' or 'history'
  const [events, setEvents] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const response = await axios.get(`${apiUrl}/api/games/user/${user.id}/history`);
        const allEvents = response.data;

        // Разделяем на активные и завершённые
        setEvents(allEvents.filter(e => e.status !== 'finished'));
        setHistory(allEvents.filter(e => e.status === 'finished'));
      } catch (error) {
        console.error('Error loading user events:', error);
      } finally {
        setLoading(false);
      }
    };

    if (user?.id) {
      loadData();
    }
  }, [user?.id, apiUrl]);

  const formatDate = (isoString) => {
    if (!isoString) return '—';
    const date = new Date(isoString);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const currentList = activeTab === 'events' ? events : history;

  return (
    <>
      <div className="user-sidebar-overlay" onClick={onClose} />
      <div className="user-sidebar">
        {/* User Profile Header */}
        <div className="user-sidebar-profile">
          <div className="user-avatar">
            <span className="material-symbols-outlined">person</span>
          </div>
          <div className="user-profile-info">
            <h2 className="user-name">{user.username}</h2>
            <span className="user-email">{user.email || 'Спортсмен'}</span>
          </div>
          <button className="sidebar-close-btn" onClick={onClose}>
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="sidebar-tabs">
          <button
            className={`sidebar-tab ${activeTab === 'events' ? 'active' : ''}`}
            onClick={() => setActiveTab('events')}
          >
            <span className="material-symbols-outlined">sports_score</span>
            <span>Мои события</span>
            {events.length > 0 && <span className="tab-badge">{events.length}</span>}
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            <span className="material-symbols-outlined">history</span>
            <span>История</span>
          </button>
        </div>

        {/* Content */}
        <div className="sidebar-content">
          {loading ? (
            <div className="sidebar-empty">Загрузка...</div>
          ) : currentList.length === 0 ? (
            <div className="sidebar-empty">
              {activeTab === 'events'
                ? 'Нет активных событий'
                : 'История пуста'}
            </div>
          ) : (
            <div className="sidebar-list">
              {currentList.map((item) => (
                <div key={item.id} className="sidebar-card">
                  <div className="sidebar-card-header">
                    <span className="sidebar-card-sport">
                      {SPORT_LABELS[item.sport_type] || item.sport_type}
                    </span>
                    <span className={`sidebar-card-status status-${item.status}`}>
                      {STATUS_LABELS[item.status] || item.status}
                    </span>
                  </div>
                  <div className="sidebar-card-meta">
                    <span className="sidebar-card-date">{formatDate(item.created_at)}</span>
                    <span className="sidebar-card-players">
                      {item.current_players}/{item.max_players} игроков
                    </span>
                  </div>
                  {item.is_creator && (
                    <span className="sidebar-card-creator">Организатор</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Logout Button */}
        <div className="sidebar-footer">
          <button className="logout-btn" onClick={onLogout}>
            <span className="material-symbols-outlined">logout</span>
            <span>Выйти</span>
          </button>
        </div>
      </div>
    </>
  );
};

export default UserSidebar;
