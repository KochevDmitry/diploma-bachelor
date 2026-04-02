import React, { useState } from 'react';
import './EventInfo.css';

const SPORT_ICONS = {
  football: 'sports_soccer',
  basketball: 'sports_basketball',
  volleyball: 'sports_volleyball',
  tennis: 'sports_tennis',
  running: 'directions_run',
  other: 'sports_score'
};

const SPORT_LABELS = {
  football: 'Футбол',
  basketball: 'Баскетбол',
  volleyball: 'Волейбол',
  tennis: 'Теннис',
  running: 'Бег',
  other: 'Другое'
};

const EventInfo = ({ event, currentUser, onJoinEvent, onLeaveEvent, onFinishEvent, onUpdateEvent, onClose }) => {
  const [isClosing, setIsClosing] = useState(false);

  const handleClose = () => {
    if (event._returnTo) {
      onClose();
    } else {
      setIsClosing(true);
      setTimeout(() => onClose(), 200);
    }
  };

  const isCreator = currentUser && String(event.creator_id) === String(currentUser.id);
  const isParticipant = currentUser && event.participants && event.participants.map(p => String(p)).includes(String(currentUser.id));
  const canJoin = !isCreator && !isParticipant && event.status === 'waiting';

  const handleJoin = async () => {
    try {
      await onJoinEvent(event.id);
    } catch (error) {
      alert('Ошибка при присоединении к событию');
    }
  };

  const handleLeave = async () => {
    try {
      await onLeaveEvent(event.id);
    } catch (error) {
      alert('Ошибка при выходе из события');
    }
  };

  const handleFinish = async () => {
    try {
      await onFinishEvent(event.id);
    } catch (error) {
      alert('Ошибка при завершении события');
    }
  };

  const handleIncreaseMaxPlayers = async () => {
    try {
      await onUpdateEvent(event.id, { max_players: event.max_players + 1 });
    } catch (error) {
      alert('Ошибка при изменении количества игроков');
    }
  };

  const handleDecreaseMaxPlayers = async () => {
    if (event.max_players <= event.current_players + 1) {
      alert('Нельзя уменьшить до текущего количества игроков');
      return;
    }
    if (event.max_players <= 2) {
      alert('Минимум 2 игрока');
      return;
    }
    try {
      await onUpdateEvent(event.id, { max_players: event.max_players - 1 });
    } catch (error) {
      alert('Ошибка при изменении количества игроков');
    }
  };

  const getSportLabel = (sportType) => SPORT_LABELS[sportType] || sportType;
  const getSportIcon = (sportType) => SPORT_ICONS[sportType] || 'sports_score';

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();

    if (isToday) {
      return `Сегодня, ${date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`;
    }
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusLabel = (status) => {
    const labels = {
      waiting: 'Ожидание игроков',
      in_progress: 'В процессе',
      finished: 'Завершено'
    };
    return labels[status] || status;
  };

  return (
    <div className={`event-info-overlay ${isClosing ? 'closing' : ''}`} onClick={handleClose}>
      <div className="event-card" onClick={(e) => e.stopPropagation()}>
        {/* Close Button */}
        <button className="event-card-close" onClick={handleClose}>
          <span className="material-symbols-outlined">close</span>
        </button>

        {/* Header with gradient */}
        <div className="event-card-header">
          <div className="event-card-header-icon">
            <span className="material-symbols-outlined">{getSportIcon(event.sport_type)}</span>
          </div>
        </div>

        {/* Content */}
        <div className="event-card-content">
          {/* Title Section */}
          <div className="event-card-title-section">
            <div className="event-card-type-badge">
              <span className="material-symbols-outlined">{getSportIcon(event.sport_type)}</span>
            </div>
            <div className="event-card-title-wrapper">
              <h1 className="event-card-title">{getSportLabel(event.sport_type)}</h1>
              <span className={`event-card-status ${event.status}`}>
                {getStatusLabel(event.status)}
              </span>
            </div>
          </div>

          {/* Details */}
          <div className="event-card-details">
            <div className="event-card-detail">
              <span className="material-symbols-outlined">schedule</span>
              <span>{formatDate(event.created_at)}</span>
            </div>

            <div className="event-card-detail">
              <span className="material-symbols-outlined">groups</span>
              {isCreator ? (
                <div className="event-card-players-edit">
                  <span>{event.current_players}/</span>
                  <button
                    className="players-btn"
                    onClick={handleDecreaseMaxPlayers}
                    disabled={event.max_players <= event.current_players + 1 || event.max_players <= 2}
                  >
                    <span className="material-symbols-outlined">remove</span>
                  </button>
                  <span className="max-players">{event.max_players}</span>
                  <button
                    className="players-btn"
                    onClick={handleIncreaseMaxPlayers}
                  >
                    <span className="material-symbols-outlined">add</span>
                  </button>
                  <span>игроков</span>
                </div>
              ) : (
                <span>{event.current_players}/{event.max_players} игроков</span>
              )}
            </div>

            {event.latitude && event.longitude && (
              <div className="event-card-detail">
                <span className="material-symbols-outlined">location_on</span>
                <span>{event.latitude.toFixed(4)}, {event.longitude.toFixed(4)}</span>
              </div>
            )}
          </div>

          {/* Creator Section */}
          {event.creator_name && (
            <div className="event-card-creator">
              <div className="event-card-creator-avatar">
                <span className="material-symbols-outlined">person</span>
              </div>
              <div className="event-card-creator-info">
                <p className="event-card-creator-label">Организатор</p>
                <p className="event-card-creator-name">{event.creator_name}</p>
              </div>
            </div>
          )}

          {/* Status notices */}
          {isParticipant && (
            <div className="event-card-notice participant">
              <span className="material-symbols-outlined">check_circle</span>
              <span>Вы участвуете в этом событии</span>
            </div>
          )}

          {isCreator && (
            <div className="event-card-notice creator">
              <span className="material-symbols-outlined">star</span>
              <span>Вы создали это событие</span>
            </div>
          )}

          {/* Action Buttons */}
          <div className="event-card-buttons">
            {canJoin && (
              <button className="btn-primary" onClick={handleJoin}>
                <span className="material-symbols-outlined">group_add</span>
                Присоединиться
              </button>
            )}

            {isParticipant && (
              <button className="btn-danger" onClick={handleLeave}>
                <span className="material-symbols-outlined">logout</span>
                Покинуть событие
              </button>
            )}

            {isCreator && (
              <button className="btn-secondary" onClick={handleFinish}>
                <span className="material-symbols-outlined">check</span>
                Завершить сбор
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default EventInfo;
