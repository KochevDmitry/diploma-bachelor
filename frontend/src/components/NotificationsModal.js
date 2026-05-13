import React, { useState } from 'react';
import './NotificationsModal.css';

const NOTIFICATION_ICONS = {
  nearby_game: 'location_on',
  participant_joined: 'person_add',
  participant_left: 'person_remove',
  session_update: 'update',
};

const NOTIFICATION_COLORS = {
  nearby_game: 'blue',
  participant_joined: 'green',
  participant_left: 'orange',
  session_update: 'gray',
};

const NotificationsModal = ({ notifications, onClose, onClear, onNotificationClick }) => {
  const [isClosing, setIsClosing] = useState(false);

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => onClose(), 200);
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'только что';
    if (diffMins < 60) return `${diffMins} мин назад`;
    if (diffHours < 24) return `${diffHours} ч назад`;
    if (diffDays < 7) return `${diffDays} дн назад`;
    return date.toLocaleDateString('ru-RU');
  };

  return (
    <div className={`notifications-overlay ${isClosing ? 'closing' : ''}`} onClick={handleClose}>
      <div className="notifications-modal" onClick={(e) => e.stopPropagation()}>
        <div className="notifications-header">
          <div className="notifications-title">
            <span className="material-symbols-outlined">notifications</span>
            <h2>Уведомления</h2>
          </div>
          <div className="notifications-header-actions">
            {notifications.length > 0 && (
              <button className="notifications-clear-btn" onClick={onClear} title="Очистить все">
                <span className="material-symbols-outlined">delete_sweep</span>
              </button>
            )}
            <button className="notifications-close-btn" onClick={handleClose}>
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>
        </div>

        <div className="notifications-body">
          {notifications.length === 0 ? (
            <div className="notifications-empty">
              <span className="material-symbols-outlined">notifications_off</span>
              <h3>Нет уведомлений</h3>
              <p>Здесь будут появляться уведомления о событиях</p>
            </div>
          ) : (
            <div className="notifications-list">
              {notifications.map((notification, index) => (
                <div
                  key={notification.id || index}
                  className={`notification-item ${notification.read ? 'read' : 'unread'} ${NOTIFICATION_COLORS[notification.type] || 'gray'}`}
                  onClick={() => onNotificationClick && onNotificationClick(notification)}
                >
                  <div className={`notification-icon ${NOTIFICATION_COLORS[notification.type] || 'gray'}`}>
                    <span className="material-symbols-outlined">
                      {NOTIFICATION_ICONS[notification.type] || 'notifications'}
                    </span>
                  </div>
                  <div className="notification-content">
                    <div className="notification-title">{notification.title}</div>
                    <div className="notification-message">{notification.message}</div>
                    <div className="notification-time">{formatTime(notification.timestamp)}</div>
                  </div>
                  {!notification.read && <div className="notification-unread-dot" />}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default NotificationsModal;
