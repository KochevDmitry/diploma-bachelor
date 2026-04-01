import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './MyEventsOverlay.css';

const SPORT_LABELS = {
  football: 'Футбол',
  basketball: 'Баскетбол',
  volleyball: 'Волейбол',
  tennis: 'Теннис',
  running: 'Бег',
  other: 'Другое',
};

const SPORT_ICONS = {
  football: 'sports_soccer',
  basketball: 'sports_basketball',
  volleyball: 'sports_volleyball',
  tennis: 'sports_tennis',
  running: 'directions_run',
  other: 'sports_score',
};

const STATUS_LABELS = {
  waiting: 'Ожидание',
  full: 'Набрано',
  started: 'Идёт игра',
  finished: 'Завершена',
};

const MyEventsOverlay = ({ user, apiUrl, onClose, onEventClick, skipAnimation }) => {
  const [createdEvents, setCreatedEvents] = useState([]);
  const [joinedEvents, setJoinedEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isClosing, setIsClosing] = useState(false);

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => onClose(), 200);
  };

  useEffect(() => {
    const loadEvents = async () => {
      setLoading(true);
      try {
        const response = await axios.get(`${apiUrl}/api/games/user/${user.id}/history`);
        const allEvents = response.data;

        // Фильтруем только активные (не завершённые)
        const activeEvents = allEvents.filter(e => e.status !== 'finished');

        // Разделяем на созданные и присоединённые
        setCreatedEvents(activeEvents.filter(e => e.is_creator));
        setJoinedEvents(activeEvents.filter(e => !e.is_creator));
      } catch (error) {
        console.error('Error loading events:', error);
      } finally {
        setLoading(false);
      }
    };

    if (user?.id) {
      loadEvents();
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

  const getSpotsText = (current, max) => {
    const spots = max - current;
    if (spots === 0) return 'Мест нет';
    if (spots === 1) return '1 место';
    if (spots < 5) return `${spots} места`;
    return `${spots} мест`;
  };

  const renderEventCard = (event) => (
    <div
      key={event.id}
      className="my-event-card"
      onClick={() => onEventClick(event)}
    >
      <div className="my-event-card-icon">
        <span className="material-symbols-outlined">
          {SPORT_ICONS[event.sport_type] || 'sports'}
        </span>
      </div>
      <div className="my-event-card-content">
        <div className="my-event-card-header">
          <span className="my-event-card-sport">
            {SPORT_LABELS[event.sport_type] || event.sport_type}
          </span>
          <span className={`my-event-card-status status-${event.status}`}>
            {STATUS_LABELS[event.status] || event.status}
          </span>
        </div>
        <div className="my-event-card-meta">
          <span className="my-event-card-date">
            <span className="material-symbols-outlined">calendar_today</span>
            {formatDate(event.created_at)}
          </span>
          <span className="my-event-card-players">
            <span className="material-symbols-outlined">group</span>
            {event.current_players}/{event.max_players}
          </span>
        </div>
        <div className="my-event-card-spots">
          {getSpotsText(event.current_players, event.max_players)}
        </div>
      </div>
      <div className="my-event-card-arrow">
        <span className="material-symbols-outlined">chevron_right</span>
      </div>
    </div>
  );

  return (
    <div className={`my-events-overlay ${isClosing ? 'closing' : ''} ${skipAnimation ? 'fast' : ''}`} onClick={handleClose}>
      <div className="my-events-modal" onClick={(e) => e.stopPropagation()}>
        <div className="my-events-header">
          <div className="my-events-title">
            <h2>Мои события</h2>
            <p>Управляйте своими мероприятиями</p>
          </div>
          <button className="my-events-close" onClick={handleClose}>
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <div className="my-events-content">
          {loading ? (
            <div className="my-events-empty">Загрузка...</div>
          ) : (
            <>
              {/* Созданные события */}
              <div className="my-events-section">
                <div className="my-events-section-header">
                  <span className="material-symbols-outlined">star</span>
                  <h3>Я организатор</h3>
                  <span className="my-events-count">{createdEvents.length}</span>
                </div>
                {createdEvents.length === 0 ? (
                  <div className="my-events-empty-section">
                    Вы пока не создали ни одного события
                  </div>
                ) : (
                  <div className="my-events-list">
                    {createdEvents.map(renderEventCard)}
                  </div>
                )}
              </div>

              {/* Присоединённые события */}
              <div className="my-events-section">
                <div className="my-events-section-header">
                  <span className="material-symbols-outlined">group</span>
                  <h3>Я участник</h3>
                  <span className="my-events-count">{joinedEvents.length}</span>
                </div>
                {joinedEvents.length === 0 ? (
                  <div className="my-events-empty-section">
                    Вы пока не присоединились ни к одному событию
                  </div>
                ) : (
                  <div className="my-events-list">
                    {joinedEvents.map(renderEventCard)}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default MyEventsOverlay;
