import React from 'react';
import './EventInfo.css';

const EventInfo = ({ event, currentUser, onJoinEvent, onLeaveEvent, onFinishEvent, onUpdateEvent, onClose }) => {
  console.log('EventInfo opened with event:', event);
  
  const isCreator = currentUser && event.creator_id === currentUser.id;
  const isParticipant = currentUser && event.participants && event.participants.includes(currentUser.id);
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

  const getSportLabel = (sportType) => {
    const labels = {
      football: 'Футбол',
      basketball: 'Баскетбол',
      volleyball: 'Волейбол',
      tennis: 'Теннис',
      running: 'Бег',
      other: 'Другое'
    };
    return labels[sportType] || sportType;
  };

  return (
    <div className="event-info-overlay">
      <div className="event-info">
        <button className="close-btn" onClick={onClose}>×</button>

        <div className="event-header">
          <h3>{getSportLabel(event.sport_type)}</h3>
          <div className="event-status">
            <span className={`status-badge ${event.status}`}>
              {event.status === 'waiting' ? 'Ожидание игроков' : event.status}
            </span>
          </div>
        </div>

        <div className="event-details">
          <div className="detail-row">
            <span className="label">Игроки:</span>
            {isCreator ? (
              <span className="value players-edit">
                {event.current_players}/
                <button
                  className="players-btn"
                  onClick={handleDecreaseMaxPlayers}
                  disabled={event.max_players <= event.current_players + 1 || event.max_players <= 2}
                >
                  -
                </button>
                <span className="max-players">{event.max_players}</span>
                <button
                  className="players-btn"
                  onClick={handleIncreaseMaxPlayers}
                >
                  +
                </button>
              </span>
            ) : (
              <span className="value">
                {event.current_players}/{event.max_players}
              </span>
            )}
          </div>

          <div className="detail-row">
            <span className="label">Создано:</span>
            <span className="value">
              {new Date(event.created_at).toLocaleString('ru-RU')}
            </span>
          </div>

          {event.latitude && event.longitude && (
            <div className="detail-row">
              <span className="label">Координаты:</span>
              <span className="value">
                {event.latitude.toFixed(6)}, {event.longitude.toFixed(6)}
              </span>
            </div>
          )}
        </div>

        {canJoin && (
          <div className="event-actions">
            <button
              onClick={handleJoin}
              className="join-btn"
            >
              Участвовать
            </button>
          </div>
        )}

        {isParticipant && (
          <div className="participant-section">
            <div className="participant-notice">
              Вы участвуете в этом событии
            </div>
            <div className="event-actions">
              <button
                onClick={handleLeave}
                className="leave-btn"
              >
                Покинуть событие
              </button>
            </div>
          </div>
        )}

        {isCreator && (
          <div className="creator-section">
            <div className="creator-notice">
              Вы создали это событие
            </div>
            <div className="event-actions">
              <button
                onClick={handleFinish}
                className="finish-btn"
              >
                Завершить сбор
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default EventInfo;