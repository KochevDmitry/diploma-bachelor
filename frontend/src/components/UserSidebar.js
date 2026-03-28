import React from 'react';
import './UserSidebar.css';

const UserSidebar = ({ user, onLogout, onClose, onMyEventsClick, onHistoryClick }) => {
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

        {/* Menu Items */}
        <nav className="sidebar-menu">
          <button className="sidebar-menu-item" onClick={onMyEventsClick}>
            <span className="material-symbols-outlined">sports_score</span>
            <span>Мои события</span>
            <span className="material-symbols-outlined menu-arrow">chevron_right</span>
          </button>
          <button className="sidebar-menu-item" onClick={onHistoryClick}>
            <span className="material-symbols-outlined">history</span>
            <span>История</span>
            <span className="material-symbols-outlined menu-arrow">chevron_right</span>
          </button>
        </nav>

        {/* Spacer */}
        <div className="sidebar-spacer"></div>

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
