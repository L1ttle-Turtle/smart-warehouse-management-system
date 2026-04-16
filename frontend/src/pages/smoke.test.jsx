import { ConfigProvider } from 'antd';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';

import AppShell from '../components/AppShell';
import ProtectedRoute from '../components/ProtectedRoute';
import DelegationPage from './DelegationPage';
import EmployeesPage from './EmployeesPage';
import LoginPage from './LoginPage';
import ProfilePage from './ProfilePage';
import RolesPage from './RolesPage';
import UsersPage from './UsersPage';

let authState = {
  loading: false,
  isAuthenticated: true,
  user: {
    id: 1,
    full_name: 'Admin User',
    role: 'admin',
    permissions: ['dashboard.view', 'roles.view', 'delegations.manage', 'users.view', 'users.manage', 'employees.view', 'employees.manage'],
    delegated_permission_sources: [],
  },
  login: vi.fn(),
  logout: vi.fn(),
  updateProfile: vi.fn(),
  hasPermission: (permission) => ['dashboard.view', 'roles.view', 'delegations.manage', 'users.view', 'users.manage', 'employees.view', 'employees.manage'].includes(permission),
};

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn((url) => {
      if (url === '/roles') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                role_name: 'admin',
                description: 'Admin role',
                user_count: 1,
                base_permissions: ['dashboard.view', 'roles.view', 'delegations.manage', 'users.view', 'users.manage', 'employees.view', 'employees.manage'],
                delegated_permissions: [],
                effective_permissions: ['dashboard.view', 'roles.view', 'delegations.manage', 'users.view', 'users.manage', 'employees.view', 'employees.manage'],
              },
            ],
          },
        });
      }

      if (url === '/users') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                username: 'admin',
                full_name: 'Admin User',
                email: 'admin@example.com',
                role: 'admin',
                employee_code: 'EMP001',
                status: 'active',
              },
            ],
          },
        });
      }

      if (url === '/employees') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                employee_code: 'EMP001',
                username: 'admin',
                full_name: 'Admin User',
                department: 'Quản trị',
                position: 'Admin',
                role: 'admin',
                status: 'active',
              },
            ],
          },
        });
      }

      if (url === '/delegations/meta') {
        return Promise.resolve({
          data: {
            grantor: {
              user_id: 1,
              full_name: 'Admin User',
              role_name: 'admin',
              permissions: ['dashboard.view', 'roles.view', 'delegations.manage', 'users.view', 'users.manage', 'employees.view', 'employees.manage'],
            },
            target_roles: [
              { id: 2, role_name: 'manager', description: 'Manager role' },
            ],
            grantable_permissions: [
              { id: 1, permission_name: 'roles.view', description: 'Xem ma trận quyền' },
            ],
          },
        });
      }

      if (url === '/delegations/users') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 2,
                username: 'manager',
                full_name: 'Manager User',
                email: 'manager@example.com',
                role_name: 'manager',
                status: 'active',
                can_receive_delegation_manage: true,
              },
            ],
            total: 1,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/delegations') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                permission_id: 1,
                permission_name: 'roles.view',
                target_user_id: 2,
                target_username: 'manager',
                target_user_name: 'Manager User',
                target_role_id: 2,
                target_role_name: 'manager',
                grantor_user_id: 1,
                grantor_user_name: 'Admin User',
                grantor_role_id: 1,
                grantor_role_name: 'admin',
                note: '',
                created_at: '2026-04-16T08:00:00',
              },
            ],
          },
        });
      }

      return Promise.resolve({ data: { items: [] } });
    }),
    post: vi.fn(() => Promise.resolve({ data: { item: { id: 1 } } })),
    patch: vi.fn(() => Promise.resolve({
      data: {
        user: {
          id: 1,
          username: 'admin',
          full_name: 'Admin User',
          email: 'admin@example.com',
          phone: '090000001',
          role: 'admin',
          permissions: ['dashboard.view', 'roles.view', 'delegations.manage', 'users.view', 'users.manage', 'employees.view', 'employees.manage'],
          delegated_permission_sources: [],
        },
      },
    })),
    delete: vi.fn(() => Promise.resolve({ data: { message: 'ok' } })),
  },
}));

vi.mock('../auth/useAuth', () => ({
  useAuth: () => authState,
}));

function renderWithProviders(node, route = '/') {
  return render(
    <ConfigProvider>
      <MemoryRouter initialEntries={[route]}>
        {node}
      </MemoryRouter>
    </ConfigProvider>,
  );
}

beforeEach(() => {
  authState = {
    loading: false,
    isAuthenticated: true,
    user: {
      id: 1,
      full_name: 'Admin User',
      role: 'admin',
      permissions: ['dashboard.view', 'roles.view', 'delegations.manage', 'users.view', 'users.manage', 'employees.view', 'employees.manage'],
      delegated_permission_sources: [],
    },
    login: vi.fn(),
    logout: vi.fn(),
    updateProfile: vi.fn(),
    hasPermission: (permission) => ['dashboard.view', 'roles.view', 'delegations.manage', 'users.view', 'users.manage', 'employees.view', 'employees.manage'].includes(permission),
  };
});

test('renders login page', () => {
  renderWithProviders(<LoginPage />, '/login');
  expect(screen.getByText(/Đăng nhập hệ thống/i)).toBeInTheDocument();
});

test('filters navigation items by permission', () => {
  authState = {
    ...authState,
    user: {
      id: 2,
      full_name: 'Manager User',
      role: 'manager',
      permissions: ['dashboard.view', 'delegations.manage', 'employees.view', 'employees.manage'],
      delegated_permission_sources: [],
    },
    updateProfile: vi.fn(),
    hasPermission: (permission) => ['dashboard.view', 'delegations.manage', 'employees.view', 'employees.manage'].includes(permission),
  };

  renderWithProviders(
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<div>Dashboard</div>} />
      </Route>
    </Routes>,
  );

  expect(screen.getByText(/Tổng quan quyền/i)).toBeInTheDocument();
  expect(screen.getAllByText(/Nhân sự/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/Ủy quyền quyền hạn/i)).toBeInTheDocument();
  expect(screen.queryByText(/^Tài khoản$/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/^Vai trò và quyền$/i)).not.toBeInTheDocument();
});

test('renders role matrix page', async () => {
  renderWithProviders(<RolesPage />, '/roles');
  await waitFor(() => expect(screen.getByText(/Ma trận vai trò và quyền/i)).toBeInTheDocument());
  expect(screen.getByText(/^admin$/i)).toBeInTheDocument();
  expect(screen.getAllByText(/roles.view/i).length).toBeGreaterThan(0);
});

test('renders users page', async () => {
  renderWithProviders(<UsersPage />, '/users');
  await waitFor(() => expect(screen.getAllByText(/Tài khoản người dùng/i).length).toBeGreaterThan(0));
  expect(screen.getAllByText(/Admin User/i).length).toBeGreaterThan(0);
});

test('renders employees page', async () => {
  renderWithProviders(<EmployeesPage />, '/employees');
  await waitFor(() => expect(screen.getAllByText(/Nhân sự/i).length).toBeGreaterThan(0));
  expect(screen.getByText(/EMP001/i)).toBeInTheDocument();
});

test('renders delegation page', async () => {
  renderWithProviders(<DelegationPage />, '/delegations');
  await waitFor(() => expect(screen.getByText(/Ủy quyền quyền hạn theo từng user/i)).toBeInTheDocument());
  expect(screen.getByText(/Chọn user nhận ủy quyền/i)).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText(/Bảng kéo thả ủy quyền cho user đã chọn/i)).toBeInTheDocument());
  expect(screen.getAllByText(/Manager User/i).length).toBeGreaterThan(0);
});

test('renders profile page', async () => {
  renderWithProviders(<ProfilePage />, '/profile');
  await waitFor(() => expect(screen.getByText(/Hồ sơ cá nhân/i)).toBeInTheDocument());
  expect(screen.getByRole('heading', { name: /Cập nhật thông tin liên hệ/i })).toBeInTheDocument();
  expect(screen.getAllByText(/Đổi mật khẩu/i).length).toBeGreaterThan(0);
});

test('redirects unauthenticated users to login', async () => {
  authState = {
    ...authState,
    isAuthenticated: false,
  };

  renderWithProviders(
    <Routes>
      <Route path="/login" element={<div>Login route</div>} />
      <Route
        path="/protected"
        element={(
          <ProtectedRoute>
            <div>Protected content</div>
          </ProtectedRoute>
        )}
      />
    </Routes>,
    '/protected',
  );

  await waitFor(() => expect(screen.getByText(/Login route/i)).toBeInTheDocument());
});

test('redirects unauthorized users to forbidden page', async () => {
  authState = {
    ...authState,
    user: {
      id: 3,
      full_name: 'Staff User',
      role: 'staff',
      permissions: ['dashboard.view'],
      delegated_permission_sources: [],
    },
    updateProfile: vi.fn(),
    hasPermission: (permission) => permission === 'dashboard.view',
  };

  renderWithProviders(
    <Routes>
      <Route path="/forbidden" element={<div>Forbidden route</div>} />
      <Route
        path="/roles"
        element={(
          <ProtectedRoute requiredPermission="roles.view">
            <div>Role matrix</div>
          </ProtectedRoute>
        )}
      />
    </Routes>,
    '/roles',
  );

  await waitFor(() => expect(screen.getByText(/Forbidden route/i)).toBeInTheDocument());
});
