import { useCallback, useEffect, useMemo, useState } from 'react';

import api, { setAuthToken } from '../api/client';
import { AuthContext } from './auth-context';

const STORAGE_KEY = 'warehouse-auth';

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const cached = localStorage.getItem(STORAGE_KEY);
    if (!cached) {
      setLoading(false);
      return;
    }

    try {
      const parsed = JSON.parse(cached);
      if (!parsed.token) {
        throw new Error('Missing token');
      }
      setAuthToken(parsed.token);
      setToken(parsed.token);
      api.get('/auth/me')
        .then((response) => setUser(response.data.user))
        .catch(() => {
          localStorage.removeItem(STORAGE_KEY);
          setAuthToken(null);
          setToken(null);
          setUser(null);
        })
        .finally(() => setLoading(false));
    } catch {
      localStorage.removeItem(STORAGE_KEY);
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (credentials) => {
    const response = await api.post('/auth/login', credentials);
    const nextToken = response.data.access_token;
    const nextUser = response.data.user;

    setAuthToken(nextToken);
    setToken(nextToken);
    setUser(nextUser);
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ token: nextToken }));
  }, []);

  const logout = useCallback(async () => {
    try {
      if (token) {
        await api.post('/auth/logout');
      }
    } catch {
      // JWT is stateless in this module, so local cleanup is enough if logout fails.
    } finally {
      localStorage.removeItem(STORAGE_KEY);
      setAuthToken(null);
      setToken(null);
      setUser(null);
    }
  }, [token]);

  const updateProfile = useCallback(async (payload) => {
    const response = await api.patch('/auth/profile', payload);
    setUser(response.data.user);
    return response.data.user;
  }, []);

  const hasPermission = useCallback(
    (permission) => (permission ? Boolean(user?.permissions?.includes(permission)) : true),
    [user],
  );

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      isAuthenticated: Boolean(token && user),
      login,
      logout,
      updateProfile,
      hasPermission,
    }),
    [token, user, loading, login, logout, updateProfile, hasPermission],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
