import React, { useState } from 'react';
import './CreateEventForm.css';

const SPORT_OPTIONS = [
  { value: 'football', label: 'Футбол', icon: 'sports_soccer' },
  { value: 'basketball', label: 'Баскетбол', icon: 'sports_basketball' },
  { value: 'volleyball', label: 'Волейбол', icon: 'sports_volleyball' },
  { value: 'tennis', label: 'Теннис', icon: 'sports_tennis' },
  { value: 'running', label: 'Бег', icon: 'directions_run' },
  { value: 'other', label: 'Другое', icon: 'sports_score' }
];

const CreateEventForm = ({ latitude, longitude, onCreate, onCancel }) => {
  const [sportType, setSportType] = useState('football');
  const [maxPlayers, setMaxPlayers] = useState(5);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      await onCreate({
        sport_type: sportType,
        max_players: maxPlayers,
        latitude,
        longitude
      });
    } catch (error) {
      console.error('Error creating event:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="create-event-form-overlay" onClick={onCancel}>
      <div className="create-event-form" onClick={(e) => e.stopPropagation()}>
        <h3>Создать событие</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Вид спорта</label>
            <div className="sport-chips">
              {SPORT_OPTIONS.map(option => (
                <button
                  key={option.value}
                  type="button"
                  className={`sport-chip ${sportType === option.value ? 'active' : ''}`}
                  onClick={() => setSportType(option.value)}
                >
                  <span className="material-symbols-outlined">{option.icon}</span>
                  <span>{option.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>Количество игроков</label>
            <div className="players-selector">
              <button
                type="button"
                className="players-btn"
                onClick={() => setMaxPlayers(Math.max(2, maxPlayers - 1))}
                disabled={maxPlayers <= 2}
              >
                <span className="material-symbols-outlined">remove</span>
              </button>
              <input
                type="number"
                className="players-input"
                value={maxPlayers}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === '') {
                    setMaxPlayers('');
                  } else {
                    setMaxPlayers(parseInt(val) || '');
                  }
                }}
                onBlur={(e) => {
                  const val = parseInt(e.target.value);
                  if (!val || val < 2) {
                    setMaxPlayers(2);
                  } else if (val > 50) {
                    setMaxPlayers(50);
                  }
                }}
                min="2"
                max="50"
              />
              <button
                type="button"
                className="players-btn"
                onClick={() => setMaxPlayers(Math.min(50, maxPlayers + 1))}
                disabled={maxPlayers >= 50}
              >
                <span className="material-symbols-outlined">add</span>
              </button>
            </div>
          </div>

          <div className="form-actions">
            <button
              type="button"
              onClick={onCancel}
              className="cancel-btn"
              disabled={isSubmitting}
            >
              Отмена
            </button>
            <button
              type="submit"
              className="create-btn"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Создание...' : 'Создать'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateEventForm;
