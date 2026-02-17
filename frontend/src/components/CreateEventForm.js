import React, { useState } from 'react';
import './CreateEventForm.css';

const CreateEventForm = ({ latitude, longitude, onCreate, onCancel }) => {
  const [sportType, setSportType] = useState('football');
  const [maxPlayers, setMaxPlayers] = useState(10);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const sportOptions = [
    { value: 'football', label: 'Футбол' },
    { value: 'basketball', label: 'Баскетбол' },
    { value: 'volleyball', label: 'Волейбол' },
    { value: 'tennis', label: 'Теннис' },
    { value: 'running', label: 'Бег' },
    { value: 'other', label: 'Другое' }
  ];

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
    <div className="create-event-form-overlay">
      <div className="create-event-form">
        <h3>Создать спортивное событие</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="sportType">Вид спорта:</label>
            <select
              id="sportType"
              value={sportType}
              onChange={(e) => setSportType(e.target.value)}
              required
            >
              {sportOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="maxPlayers">Максимум игроков:</label>
            <input
              type="number"
              id="maxPlayers"
              min="2"
              max="50"
              value={maxPlayers}
              onChange={(e) => setMaxPlayers(parseInt(e.target.value))}
              required
            />
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