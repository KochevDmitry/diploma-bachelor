import React, { useState, useRef } from 'react';
import axios from 'axios';
import './SettingsOverlay.css';

const API_URL = process.env.REACT_APP_API_URL || '';

const TABS = [
  { id: 'profile', label: 'Профиль', icon: 'person' },
  { id: 'notifications', label: 'Уведомления', icon: 'notifications' },
  { id: 'security', label: 'Безопасность', icon: 'shield' },
];

const SettingsOverlay = ({ user, onClose, onUpdateProfile, onUserUpdate }) => {
  const [activeTab, setActiveTab] = useState('profile');
  const initialUser = useRef(user);
  const [formData, setFormData] = useState({
    username: initialUser.current?.username || '',
    email: initialUser.current?.email || '',
    bio: initialUser.current?.bio || '',
  });
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [isSaving, setIsSaving] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);
  const [passwordStatus, setPasswordStatus] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [avatarPreview, setAvatarPreview] = useState(user?.avatar_url || null);
  const fileInputRef = useRef(null);

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => onClose(), 200);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setSaveStatus(null);
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData((prev) => ({ ...prev, [name]: value }));
    setPasswordStatus(null);
    setPasswordError('');
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

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Проверка типа файла
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      alert('Разрешены только изображения: PNG, JPG, GIF, WebP');
      return;
    }

    // Проверка размера (5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('Максимальный размер файла: 5MB');
      return;
    }

    // Показываем превью
    const reader = new FileReader();
    reader.onload = (e) => setAvatarPreview(e.target.result);
    reader.readAsDataURL(file);

    // Загружаем на сервер
    setIsUploadingAvatar(true);
    try {
      const formData = new FormData();
      formData.append('avatar', file);

      const response = await axios.post(`${API_URL}/auth/avatar`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setAvatarPreview(response.data.avatar_url);

      // Обновляем user в родительском компоненте
      if (onUserUpdate) {
        onUserUpdate(response.data.user);
      }
    } catch (error) {
      console.error('Error uploading avatar:', error);
      alert(error.response?.data?.error || 'Ошибка загрузки фото');
      // Возвращаем старое превью
      setAvatarPreview(user?.avatar_url || null);
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  const handleChangePassword = async () => {
    setIsChangingPassword(true);
    setPasswordStatus(null);
    setPasswordError('');

    // Валидация
    if (!passwordData.currentPassword || !passwordData.newPassword || !passwordData.confirmPassword) {
      setPasswordError('Заполните все поля');
      setIsChangingPassword(false);
      return;
    }

    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setPasswordError('Пароли не совпадают');
      setIsChangingPassword(false);
      return;
    }

    if (passwordData.newPassword.length < 6) {
      setPasswordError('Пароль должен быть не менее 6 символов');
      setIsChangingPassword(false);
      return;
    }

    try {
      await axios.post(`${API_URL}/auth/change-password`, passwordData);
      setPasswordStatus('success');
      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
      setTimeout(() => setPasswordStatus(null), 3000);
    } catch (error) {
      console.error('Error changing password:', error);
      setPasswordStatus('error');
      setPasswordError(error.response?.data?.error || 'Ошибка смены пароля');
    } finally {
      setIsChangingPassword(false);
    }
  };

  const renderProfileTab = () => (
    <div className="settings-tab-content">
      {/* Avatar Section */}
      <div className="settings-avatar-section">
        <div className="settings-avatar-wrapper" onClick={handleAvatarClick}>
          {avatarPreview ? (
            <img
              src={avatarPreview.startsWith('data:') ? avatarPreview : `${API_URL}${avatarPreview}`}
              alt="Avatar"
              className="settings-avatar-img"
            />
          ) : (
            <div className="settings-avatar-placeholder">
              <span className="material-symbols-outlined">person</span>
            </div>
          )}
          <div className="settings-avatar-overlay">
            {isUploadingAvatar ? (
              <span className="material-symbols-outlined spinning">sync</span>
            ) : (
              <span className="material-symbols-outlined">photo_camera</span>
            )}
          </div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <p className="settings-avatar-hint">Нажмите, чтобы изменить фото</p>
      </div>

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
      <div className="settings-section">
        <h3 className="settings-section-title">Изменить пароль</h3>
        <p className="settings-section-desc">Обновите пароль для защиты аккаунта</p>

        <div className="settings-form">
          <div className="settings-field">
            <label htmlFor="currentPassword">Текущий пароль</label>
            <input
              type="password"
              id="currentPassword"
              name="currentPassword"
              value={passwordData.currentPassword}
              onChange={handlePasswordChange}
              placeholder="Введите текущий пароль"
            />
          </div>

          <div className="settings-field">
            <label htmlFor="newPassword">Новый пароль</label>
            <input
              type="password"
              id="newPassword"
              name="newPassword"
              value={passwordData.newPassword}
              onChange={handlePasswordChange}
              placeholder="Введите новый пароль"
            />
          </div>

          <div className="settings-field">
            <label htmlFor="confirmPassword">Подтвердите пароль</label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={passwordData.confirmPassword}
              onChange={handlePasswordChange}
              placeholder="Повторите новый пароль"
            />
          </div>
        </div>
      </div>

      <div className="settings-actions">
        {passwordStatus === 'error' && (
          <span className="settings-status settings-status-error">
            <span className="material-symbols-outlined">error</span>
            {passwordError}
          </span>
        )}
        {passwordStatus === 'success' && (
          <span className="settings-status settings-status-success">
            <span className="material-symbols-outlined">check_circle</span>
            Пароль изменён
          </span>
        )}
        <button
          className={`settings-btn settings-btn-primary ${passwordStatus === 'success' ? 'success' : ''}`}
          onClick={handleChangePassword}
          disabled={isChangingPassword || passwordStatus === 'success'}
        >
          {isChangingPassword ? 'Сохранение...' : passwordStatus === 'success' ? 'Изменено' : 'Изменить пароль'}
        </button>
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
