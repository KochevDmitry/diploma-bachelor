import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './HistoryOverlay.css';

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

const HistoryOverlay = ({ user, apiUrl, onClose, skipAnimation }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isClosing, setIsClosing] = useState(false);

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => onClose(), 200);
  };

  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true);
      try {
        const response = await axios.get(`${apiUrl}/api/games/user/${user.id}/history`);
        // Только завершённые события
        setHistory(response.data.filter(e => e.status === 'finished'));
      } catch (error) {
        console.error('Error loading history:', error);
      } finally {
        setLoading(false);
      }
    };

    if (user?.id) {
      loadHistory();
    }
  }, [user?.id, apiUrl]);

  const formatDate = (isoString) => {
    if (!isoString) return '—';
    const date = new Date(isoString);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  return (
    <div className={`history-overlay ${isClosing ? 'closing' : ''} ${skipAnimation ? 'fast' : ''}`} onClick={handleClose}>
      <div className="history-modal" onClick={(e) => e.stopPropagation()}>
        <div className="history-header">
          <div className="history-title">
            <h2>История</h2>
            <p>Ваши прошедшие мероприятия</p>
          </div>
          <button className="history-close" onClick={handleClose}>
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <div className="history-content">
          {loading ? (
            <div className="history-empty">Загрузка...</div>
          ) : history.length === 0 ? (
            <div className="history-empty">
              <span className="material-symbols-outlined">history</span>
              <p>История пуста</p>
              <span className="history-empty-hint">
                Завершённые события появятся здесь
              </span>
            </div>
          ) : (
            <div className="history-list">
              {history.map((event) => (
                <div
                  key={event.id}
                  className="history-card"
                >
                  <div className="history-card-icon">
                    <span className="material-symbols-outlined">
                      {SPORT_ICONS[event.sport_type] || 'sports'}
                    </span>
                  </div>
                  <div className="history-card-content">
                    <div className="history-card-header">
                      <span className="history-card-sport">
                        {SPORT_LABELS[event.sport_type] || event.sport_type}
                      </span>
                      {event.is_creator && (
                        <span className="history-card-badge">Организатор</span>
                      )}
                    </div>
                    <div className="history-card-meta">
                      <span className="history-card-date">
                        <span className="material-symbols-outlined">calendar_today</span>
                        {formatDate(event.created_at)}
                      </span>
                    </div>
                    <div className="history-card-players">
                      <span className="material-symbols-outlined">group</span>
                      {event.current_players} участников
                    </div>
                  </div>
                  <div className="history-card-status">
                    <span className="material-symbols-outlined">check_circle</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoryOverlay;
