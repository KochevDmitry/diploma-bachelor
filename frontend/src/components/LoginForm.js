import React, { useState } from 'react';
import axios from 'axios';
import './LoginForm.css';

const LoginForm = ({ onLogin, apiUrl }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const data = isLogin
        ? { username, password }
        : { username, email, password };

      console.log('🔐 LoginForm: отправляем запрос к', endpoint);
      const response = await axios.post(`${apiUrl}${endpoint}`, data);
      console.log('🔐 LoginForm: ответ от сервера:', response.data);
      console.log('  - user:', response.data.user);
      console.log('  - accessToken:', response.data.accessToken ? '(present)' : 'MISSING');
      console.log('  - refreshToken:', response.data.refreshToken ? '(present)' : 'MISSING');
      onLogin(response.data.user, response.data.accessToken, response.data.refreshToken);
    } catch (err) {
      console.error('🔐 LoginForm: ошибка', err);
      setError(err.response?.data?.error || 'Произошла ошибка');
    }
  };

  return (
    <div className="login-form-modal">
      <div className="login-form">
        <h1>SportApp</h1>
        <h2>{isLogin ? 'Вход' : 'Регистрация'}</h2>
        
        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Имя пользователя"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          {!isLogin && (
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          )}
          <input
            type="password"
            placeholder="Пароль"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit">{isLogin ? 'Войти' : 'Зарегистрироваться'}</button>
        </form>
        
        <p>
          {isLogin ? 'Нет аккаунта? ' : 'Уже есть аккаунт? '}
          <button 
            type="button" 
            className="toggle-btn"
            onClick={() => {
              setIsLogin(!isLogin);
              setError('');
            }}
          >
            {isLogin ? 'Зарегистрироваться' : 'Войти'}
          </button>
        </p>
      </div>
    </div>
  );
};

export default LoginForm;
