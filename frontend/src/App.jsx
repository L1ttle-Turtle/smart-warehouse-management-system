import { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Spin } from 'antd';

import ProtectedRoute from './components/ProtectedRoute';
import AppShell from './components/AppShell';
import { useAuth } from './auth/useAuth';

const AuditLogsPage = lazy(() => import('./pages/AuditLogsPage'));
const CatalogsPage = lazy(() => import('./pages/CatalogsPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const DelegationPage = lazy(() => import('./pages/DelegationPage'));
const EmployeesPage = lazy(() => import('./pages/EmployeesPage'));
const ExportReceiptsPage = lazy(() => import('./pages/ExportReceiptsPage'));
const ForbiddenPage = lazy(() => import('./pages/ForbiddenPage'));
const ImportReceiptsPage = lazy(() => import('./pages/ImportReceiptsPage'));
const InventoryPage = lazy(() => import('./pages/InventoryPage'));
const InvoicesPage = lazy(() => import('./pages/InvoicesPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const NotificationsPage = lazy(() => import('./pages/NotificationsPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
const ProductsPage = lazy(() => import('./pages/ProductsPage'));
const RolesPage = lazy(() => import('./pages/RolesPage'));
const ShipmentsPage = lazy(() => import('./pages/ShipmentsPage'));
const StocktakesPage = lazy(() => import('./pages/StocktakesPage'));
const StockTransfersPage = lazy(() => import('./pages/StockTransfersPage'));
const UsersPage = lazy(() => import('./pages/UsersPage'));
const WarehousesPage = lazy(() => import('./pages/WarehousesPage'));

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
          <Route
            path="catalogs"
            element={(
              <ProtectedRoute
                requiredPermissionsAny={[
                  'categories.view',
                  'suppliers.view',
                  'customers.view',
                  'bank_accounts.view',
                ]}
              >
                <CatalogsPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="products"
            element={(
              <ProtectedRoute requiredPermission="products.view">
                <ProductsPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="import-receipts"
            element={(
              <ProtectedRoute requiredPermission="import_receipts.view">
                <ImportReceiptsPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="export-receipts"
            element={(
              <ProtectedRoute requiredPermission="export_receipts.view">
                <ExportReceiptsPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="stock-transfers"
            element={(
              <ProtectedRoute requiredPermission="stock_transfers.view">
                <StockTransfersPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="shipments"
            element={(
              <ProtectedRoute requiredPermission="shipments.view">
                <ShipmentsPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="inventory"
            element={(
              <ProtectedRoute requiredPermission="inventory.view">
                <InventoryPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="stocktakes"
            element={(
              <ProtectedRoute requiredPermission="inventory.view">
                <StocktakesPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="invoices"
            element={(
              <ProtectedRoute requiredPermission="invoices.view">
                <InvoicesPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="notifications"
            element={(
              <ProtectedRoute
                requiredPermissionsAny={[
                  'notifications.view',
                  'tasks.view',
                ]}
              >
                <NotificationsPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="warehouses"
            element={(
              <ProtectedRoute
                requiredPermissionsAny={[
                  'warehouses.view',
                  'locations.view',
                ]}
              >
                <WarehousesPage />
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
        <Route path="*" element={<Navigate to={isAuthenticated ? '/' : '/login'} replace />} />
      </Routes>
    </Suspense>
  );
}

export default App;
