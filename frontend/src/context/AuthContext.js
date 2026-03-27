import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    const storedToken = localStorage.getItem('token');
    if (!storedToken) {
      setLoading(false);
      return;
    }

    try {
      const response = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${storedToken}` }
      });
      setUser(response.data);
      setToken(storedToken);
    } catch (error) {
      console.error('Auth check failed:', error);
      localStorage.removeItem('token');
      setUser(null);
      setToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // CRITICAL: If returning from OAuth callback, skip the /me check.
    // AuthCallback will exchange the session_id and establish the session first.
    if (window.location.hash?.includes('session_id=')) {
      setLoading(false);
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, { email, password });
    const { token: newToken, user: userData } = response.data;
    localStorage.setItem('token', newToken);
    setToken(newToken);
    setUser(userData);
    return userData;
  };

  const register = async (email, password, name, role = 'employee') => {
    const response = await axios.post(`${API}/auth/register`, { email, password, name, role });
    const { token: newToken, user: userData } = response.data;
    localStorage.setItem('token', newToken);
    setToken(newToken);
    setUser(userData);
    return userData;
  };

  const loginWithGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/portal/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const handleOAuthCallback = async (sessionId) => {
    const response = await axios.post(`${API}/auth/session`, {}, {
      headers: { 'X-Session-ID': sessionId }
    });
    const { token: newToken, user: userData } = response.data;
    localStorage.setItem('token', newToken);
    setToken(newToken);
    setUser(userData);
    return userData;
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const isAdmin = () => {
    return user?.role === 'super_admin' || user?.role === 'admin';
  };

  const isManagerOrAdmin = () => {
    return user?.role === 'super_admin' || user?.role === 'admin' || user?.role === 'branch_manager';
  };

  const isAuditor = () => {
    return user?.role === 'auditor';
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    loginWithGoogle,
    handleOAuthCallback,
    logout,
    isAdmin,
    isManagerOrAdmin,
    isAuditor,
    checkAuth
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
