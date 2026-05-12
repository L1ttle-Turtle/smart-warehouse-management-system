import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';

import { AuthProvider } from './AuthContext';
import { useAuth } from './useAuth';

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
}));

const setAuthTokenMock = vi.hoisted(() => vi.fn());
const disconnectMock = vi.hoisted(() => vi.fn());

vi.mock('../api/client', () => ({
  default: apiMock,
  setAuthToken: setAuthTokenMock,
}));

vi.mock('socket.io-client', () => ({
  io: vi.fn(() => ({
    on: vi.fn(),
    disconnect: disconnectMock,
  })),
}));

const demoUser = {
  id: 1,
  username: 'admin',
  full_name: 'Admin User',
  role: 'admin',
  permissions: ['dashboard.view'],
};

function AuthHarness() {
  const { isAuthenticated, loading, login, logout, user } = useAuth();

  return (
    <div>
      <div data-testid="loading">{loading ? 'loading' : 'ready'}</div>
      <div data-testid="status">{isAuthenticated ? 'authenticated' : 'guest'}</div>
      <div data-testid="username">{user?.username || '-'}</div>
      <button type="button" onClick={() => login({ username: 'admin', password: 'Admin@123' })}>
        login
      </button>
      <button type="button" onClick={logout}>
        logout
      </button>
    </div>
  );
}

function renderAuth() {
  return render(
    <AuthProvider>
      <AuthHarness />
    </AuthProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  apiMock.get.mockResolvedValue({ data: { user: demoUser } });
  apiMock.post.mockResolvedValue({
    data: {
      access_token: 'demo-token',
      user: demoUser,
    },
  });
});

test('stores login token in sessionStorage instead of localStorage', async () => {
  renderAuth();

  await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('ready'));
  fireEvent.click(screen.getByRole('button', { name: 'login' }));

  await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('authenticated'));

  expect(localStorage.getItem('warehouse-auth')).toBeNull();
  expect(JSON.parse(sessionStorage.getItem('warehouse-auth'))).toMatchObject({
    token: 'demo-token',
    storage: 'session',
  });
  expect(setAuthTokenMock).toHaveBeenCalledWith('demo-token');
});

test('restores auth from sessionStorage and purges legacy localStorage token', async () => {
  localStorage.setItem('warehouse-auth', JSON.stringify({ token: 'legacy-local-token' }));
  sessionStorage.setItem('warehouse-auth', JSON.stringify({ token: 'session-token' }));

  renderAuth();

  await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('authenticated'));

  expect(localStorage.getItem('warehouse-auth')).toBeNull();
  expect(screen.getByTestId('username')).toHaveTextContent('admin');
  expect(setAuthTokenMock).toHaveBeenCalledWith('session-token');
  expect(apiMock.get).toHaveBeenCalledWith('/auth/me');
});

test('logout clears session token even when backend logout fails', async () => {
  apiMock.post
    .mockResolvedValueOnce({
      data: {
        access_token: 'demo-token',
        user: demoUser,
      },
    })
    .mockRejectedValueOnce(new Error('network'));

  renderAuth();

  await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('ready'));
  fireEvent.click(screen.getByRole('button', { name: 'login' }));
  await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('authenticated'));

  fireEvent.click(screen.getByRole('button', { name: 'logout' }));

  await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('guest'));
  expect(sessionStorage.getItem('warehouse-auth')).toBeNull();
  expect(localStorage.getItem('warehouse-auth')).toBeNull();
  expect(setAuthTokenMock).toHaveBeenLastCalledWith(null);
});
