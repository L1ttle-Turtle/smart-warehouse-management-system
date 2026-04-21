import { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Spin } from 'antd';

import ProtectedRoute from './components/ProtectedRoute';
import AppShell from './components/AppShell';
import { useAuth } from './auth/useAuth';

const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const DelegationPage = lazy(() => import('./pages/DelegationPage'));
const EmployeesPage = lazy(() => import('./pages/EmployeesPage'));
const AuditLogsPage = lazy(() => import('./pages/AuditLogsPage'));
const ForbiddenPage = lazy(() => import('./pages/ForbiddenPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
const RolesPage = lazy(() => import('./pages/RolesPage'));
const UsersPage = lazy(() => import('./pages/UsersPage'));

function RouteLoader() {
  return (
    <div style={{ minHeight: '60vh', display: 'grid', placeItems: 'center' }}>
      <Spin size="large" />
    </div>
  );
}

function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Suspense fallback={<RouteLoader />}>
      <Routes>
        <Route
          path="/login"
          element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />}
        />
        <Route
          path="/forbidden"
          element={(
            <ProtectedRoute>
              <ForbiddenPage />
            </ProtectedRoute>
          )}
        />
        <Route
          path="/"
          element={(
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          )}
        >
          <Route index element={<DashboardPage />} />
          <Route
            path="audit-logs"
            element={(
              <ProtectedRoute requiredPermission="audit_logs.view">
                <AuditLogsPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="users"
            element={(
              <ProtectedRoute requiredPermission="users.view">
                <UsersPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="employees"
            element={(
              <ProtectedRoute requiredPermission="employees.view">
                <EmployeesPage />
              </ProtectedRoute>
            )}
          />
          <Route path="profile" element={<ProfilePage />} />
          <Route
            path="delegations"
            element={(
              <ProtectedRoute requiredPermission="delegations.manage">
                <DelegationPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="roles"
            element={(
              <ProtectedRoute requiredPermission="roles.view">
                <RolesPage />
              </ProtectedRoute>
            )}
          />
        </Route>
        <Route path="*" element={<Navigate to={isAuthenticated ? "/" : "/login"} replace />} />
      </Routes>
    </Suspense>
  );
}

export default App;
