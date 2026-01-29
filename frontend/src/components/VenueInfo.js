import React, { useState } from 'react';
import './VenueInfo.css';

const VenueInfo = ({ venue, sessions, currentUser, onCreateSession, onJoinSession }) => {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [sportType, setSportType] = useState('football');
  const [maxPlayers, setMaxPlayers] = useState(10);

  const handleCreateSession = async (e) => {
    e.preventDefault();
    try {
      await onCreateSession(venue.id, sportType, parseInt(maxPlayers));
      setShowCreateForm(false);
    } catch (error) {
      alert('Ошибка при создании сессии');
    }
  };

  const handleJoin = async (sessionId) => {
    try {
      await onJoinSession(sessionId);
    } catch (error) {
      alert('Ошибка при присоединении к сессии');
    }
  };

  return (
    <div className="venue-info">
      <div className="venue-header">
        <h2>{venue.name}</h2>
        <p>{venue.address}</p>
        <p className="sport-type">Вид спорта: {venue.sport_type || 'Разные'}</p>
      </div>

      <div className="sessions-section">
        <h3>Активные игры</h3>
        {sessions.length === 0 ? (
          <div className="no-sessions">
            <p>На этой площадке пока нет активных игр</p>
            {!showCreateForm && (
              <button onClick={() => setShowCreateForm(true)} className="create-btn">
                Создать игру
              </button>
            )}
          </div>
        ) : (
          <div className="sessions-list">
            {sessions.map(session => (
              <div key={session.id} className="session-card">
                <div className="session-info">
                  <p><strong>Вид спорта:</strong> {session.sport_type}</p>
                  <p><strong>Игроков:</strong> {session.current_players} / {session.max_players}</p>
                  <p><strong>Статус:</strong> {session.status}</p>
                </div>
                {session.current_players < session.max_players && 
                 currentUser &&
                 !(session.participants || []).includes(currentUser.id) && (
                  <button 
                    onClick={() => handleJoin(session.id)}
                    className="join-btn"
                  >
                    Присоединиться
                  </button>
                )}
                {session.current_players < session.max_players && 
                 !currentUser && (
                  <button 
                    onClick={() => handleJoin(session.id)}
                    className="join-btn"
                  >
                    Войти для присоединения
                  </button>
                )}
              </div>
            ))}
            {!showCreateForm && (
              <button onClick={() => setShowCreateForm(true)} className="create-btn">
                Создать новую игру
              </button>
            )}
          </div>
        )}

        {showCreateForm && (
          <form onSubmit={handleCreateSession} className="create-session-form">
            <h4>Создать новую игру</h4>
            <label>
              Вид спорта:
              <select value={sportType} onChange={(e) => setSportType(e.target.value)}>
                <option value="football">Футбол</option>
                <option value="basketball">Баскетбол</option>
                <option value="volleyball">Волейбол</option>
                <option value="tennis">Теннис</option>
              </select>
            </label>
            <label>
              Максимум игроков:
              <input
                type="number"
                value={maxPlayers}
                onChange={(e) => setMaxPlayers(e.target.value)}
                min="2"
                max="22"
              />
            </label>
            <div className="form-actions">
              <button type="submit">Создать</button>
              <button type="button" onClick={() => setShowCreateForm(false)}>Отмена</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default VenueInfo;
