import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './GameHistory.css';

const SPORT_LABELS = {
  football: 'Футбол',
  basketball: 'Баскетбол',
  volleyball: 'Волейбол',
  tennis: 'Теннис',
};

const STATUS_LABELS = {
  waiting: 'Ожидание',
  full: 'Набрано',
  started: 'Идёт игра',
  finished: 'Завершена',
};

const GameHistory = ({ userId, apiUrl, onClose }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  console.log('📋 GameHistory RENDER: userId=', userId, 'apiUrl=', apiUrl, 'loading=', loading, 'history.length=', history.length);

  useEffect(() => {
    console.log('📋 GameHistory useEffect: загрузка истории для userId=', userId);
    const loadHistory = async () => {
      try {
        const url = `${apiUrl}/api/games/user/${userId}/history`;
        console.log('📋 GameHistory fetch:', url);
        const response = await axios.get(url);
        console.log('📋 GameHistory response:', response.status, response.data);
        setHistory(response.data);
      } catch (error) {
        console.error('📋 GameHistory ERROR:', error.response?.status, error.message);
      } finally {
        setLoading(false);
      }
    };

    loadHistory();
  }, [userId, apiUrl]);

  const formatDate = (isoString) => {
    if (!isoString) return '—';
    const date = new Date(isoString);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <>
      <div className="game-history-overlay" onClick={onClose} />
      <div className="game-history">
        <div className="game-history-header">
          <h2>Мои записи</h2>
          <button className="game-history-close" onClick={onClose}>&times;</button>
        </div>

        <div className="game-history-list">
        {loading && <p className="game-history-empty">Загрузка...</p>}

        {!loading && history.length === 0 && (
          <p className="game-history-empty">У вас пока нет записей</p>
        )}

        {history.map((entry) => (
          <div key={entry.id} className="game-history-card">
            <div className="game-history-card-sport">
              {SPORT_LABELS[entry.sport_type] || entry.sport_type}
            </div>
            <div className="game-history-card-date">
              {formatDate(entry.created_at)}
            </div>
            <div className="game-history-card-details">
              <span className={`game-history-card-status status-${entry.status}`}>
                {STATUS_LABELS[entry.status] || entry.status}
              </span>
            </div>
            <div className="game-history-card-players">
              Игроков: {entry.current_players} / {entry.max_players}
              {entry.is_creator && <span className="game-history-card-creator">Организатор</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
    </>
  );
};

export default GameHistory;
