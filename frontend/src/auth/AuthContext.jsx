import { useCallback, useEffect, useMemo, useState } from 'react';
import { io } from 'socket.io-client';

import api, { setAuthToken } from '../api/client';
import { AuthContext } from './auth-context';

const STORAGE_KEY = 'warehouse-auth';

function removeLegacyPersistentAuth() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage can be unavailable in restricted browser modes.
  }
}

function readSessionAuth() {
  removeLegacyPersistentAuth();
  try {
    const cached = sessionStorage.getItem(STORAGE_KEY);
    return cached ? JSON.parse(cached) : null;
  } catch {
    return null;
  }
}

function writeSessionAuth(token) {
  removeLegacyPersistentAuth();
  sessionStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      token,
      storage: 'session',
      saved_at: new Date().toISOString(),
    }),
  );
}

function clearSessionAuth() {
  removeLegacyPersistentAuth();
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Best-effort cleanup.
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [socket, setSocket] = useState(null);
  const [socketConnected, setSocketConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const parsed = readSessionAuth();
    if (!parsed) {
      setLoading(false);
      return;
    }

    try {
      if (!parsed.token) {
        throw new Error('Missing token');
      }
      setAuthToken(parsed.token);
      setToken(parsed.token);
      api.get('/auth/me')
        .then((response) => setUser(response.data.user))
        .catch(() => {
          clearSessionAuth();
          setAuthToken(null);
          setToken(null);
          setUser(null);
        })
        .finally(() => setLoading(false));
    } catch {
      clearSessionAuth();
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
    writeSessionAuth(nextToken);
    return nextUser;
  }, []);

  const logout = useCallback(async () => {
    try {
      if (token) {
        await api.post('/auth/logout');
      }
    } catch {
      // Backend revokes the token when reachable; local cleanup still protects this tab if the network fails.
    } finally {
      clearSessionAuth();
      setAuthToken(null);
      setToken(null);
      setUser(null);
    }
  }, [token]);

  useEffect(() => {
    if (!token || !user) {
      setSocketConnected(false);
      setSocket((currentSocket) => {
        if (currentSocket) {
          currentSocket.disconnect();
        }
        return null;
      });
      return undefined;
    }

    const nextSocket = io(import.meta.env.VITE_API_URL || 'http://localhost:5000', {
      auth: { token },
      // Flask dev server in this project is most stable with HTTP long-polling.
      transports: ['polling'],
    });

    nextSocket.on('connect', () => setSocketConnected(true));
    nextSocket.on('disconnect', () => setSocketConnected(false));
    setSocket(nextSocket);

    return () => {
      nextSocket.disconnect();
    };
  }, [token, user]);

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
      socket,
      socketConnected,
    }),
    [token, user, loading, login, logout, updateProfile, hasPermission, socket, socketConnected],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
