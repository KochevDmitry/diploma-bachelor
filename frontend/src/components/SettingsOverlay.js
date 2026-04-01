import React, { useState, useRef } from 'react';
import './SettingsOverlay.css';

const TABS = [
  { id: 'profile', label: 'Профиль', icon: 'person' },
  { id: 'notifications', label: 'Уведомления', icon: 'notifications' },
  { id: 'security', label: 'Безопасность', icon: 'shield' },
];

const SettingsOverlay = ({ user, onClose, onUpdateProfile }) => {
  const [activeTab, setActiveTab] = useState('profile');
  // Используем useRef чтобы инициализировать formData только один раз
  const initialUser = useRef(user);
  const [formData, setFormData] = useState({
    username: initialUser.current?.username || '',
    email: initialUser.current?.email || '',
    bio: initialUser.current?.bio || '',
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null); // 'success' | 'error' | null
  const [errorMessage, setErrorMessage] = useState('');
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isClosing, setIsClosing] = useState(false);

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => onClose(), 200);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setSaveStatus(null);
  };

  const handleSave = async () => {
    if (!onUpdateProfile) return;
    setIsSaving(true);
    setSaveStatus(null);
    setErrorMessage('');
    try {
      await onUpdateProfile(formData);
      setSaveStatus('success');
      setTimeout(() => setSaveStatus(null), 3000);
    } catch (error) {
      console.error('Error updating profile:', error);
      setSaveStatus('error');
      setErrorMessage(error.response?.data?.error || 'Ошибка сохранения');
    } finally {
      setIsSaving(false);
    }
  };

  const renderProfileTab = () => (
    <div className="settings-tab-content">
      <div className="settings-section">
        <h3 className="settings-section-title">Основная информация</h3>
        <p className="settings-section-desc">Обновите свои личные данные</p>

        <div className="settings-form">
          <div className="settings-field">
            <label htmlFor="username">Имя пользователя</label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleInputChange}
              placeholder="Введите имя"
            />
          </div>

          <div className="settings-field">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              placeholder="Введите email"
            />
          </div>

          <div className="settings-field">
            <label htmlFor="bio">О себе</label>
            <textarea
              id="bio"
              name="bio"
              value={formData.bio}
              onChange={handleInputChange}
              placeholder="Расскажите немного о себе..."
              rows={4}
            />
          </div>
        </div>
      </div>

      <div className="settings-actions">
        {saveStatus === 'error' && (
          <span className="settings-status settings-status-error">
            <span className="material-symbols-outlined">error</span>
            {errorMessage}
          </span>
        )}
        <button
          className={`settings-btn settings-btn-primary ${saveStatus === 'success' ? 'success' : ''}`}
          onClick={handleSave}
          disabled={isSaving || saveStatus === 'success'}
        >
          {isSaving ? 'Сохранение...' : saveStatus === 'success' ? 'Сохранено' : 'Сохранить изменения'}
        </button>
      </div>
    </div>
  );

  const renderNotificationsTab = () => (
    <div className="settings-tab-content">
      <div className="settings-empty-tab">
        <span className="material-symbols-outlined">notifications</span>
        <h3>Уведомления</h3>
        <p>Настройки уведомлений скоро будут доступны</p>
      </div>
    </div>
  );

  const renderSecurityTab = () => (
    <div className="settings-tab-content">
      <div className="settings-empty-tab">
        <span className="material-symbols-outlined">shield</span>
        <h3>Безопасность</h3>
        <p>Настройки безопасности скоро будут доступны</p>
      </div>
    </div>
  );

  const handleTabChange = (tabId) => {
    if (tabId === activeTab) return;
    setIsTransitioning(true);
    setTimeout(() => {
      setActiveTab(tabId);
      setTimeout(() => setIsTransitioning(false), 20);
    }, 150);
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'profile':
        return renderProfileTab();
      case 'notifications':
        return renderNotificationsTab();
      case 'security':
        return renderSecurityTab();
      default:
        return renderProfileTab();
    }
  };

  return (
    <div className={`settings-overlay ${isClosing ? 'closing' : ''}`} onClick={handleClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="settings-header">
          <div className="settings-title">
            <h2>Настройки</h2>
            <p>Управляйте своим аккаунтом</p>
          </div>
          <button className="settings-close" onClick={handleClose}>
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {/* Body */}
        <div className="settings-body">
          {/* Sidebar with tabs */}
          <div className="settings-sidebar">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                className={`settings-tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => handleTabChange(tab.id)}
              >
                <span className="material-symbols-outlined">{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {/* Content */}
          <div className={`settings-content ${isTransitioning ? 'transitioning' : ''}`}>
            {renderTabContent()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsOverlay;
