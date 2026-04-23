import { ConfigProvider } from 'antd';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import AppShell from '../components/AppShell';
import ProtectedRoute from '../components/ProtectedRoute';
import AuditLogsPage from './AuditLogsPage';
import CatalogsPage from './CatalogsPage';
import DelegationPage from './DelegationPage';
import EmployeesPage from './EmployeesPage';
import ExportReceiptsPage from './ExportReceiptsPage';
import ImportReceiptsPage from './ImportReceiptsPage';
import InventoryPage from './InventoryPage';
import LoginPage from './LoginPage';
import ProfilePage from './ProfilePage';
import ProductsPage from './ProductsPage';
import RolesPage from './RolesPage';
import StockTransfersPage from './StockTransfersPage';
import UsersPage from './UsersPage';
import WarehousesPage from './WarehousesPage';

const adminPermissions = [
  'dashboard.view',
  'audit_logs.view',
  'roles.view',
  'delegations.manage',
  'users.view',
  'users.manage',
  'employees.view',
  'employees.manage',
  'inventory.view',
  'export_receipts.view',
  'export_receipts.manage',
  'import_receipts.view',
  'import_receipts.manage',
  'stock_transfers.view',
  'stock_transfers.manage',
  'warehouses.view',
  'warehouses.manage',
  'locations.view',
  'locations.manage',
  'products.view',
  'products.manage',
  'categories.view',
  'categories.manage',
  'suppliers.view',
  'suppliers.manage',
  'customers.view',
  'customers.manage',
  'bank_accounts.view',
  'bank_accounts.manage',
];

const managerPermissions = [
  'dashboard.view',
  'audit_logs.view',
  'delegations.manage',
  'employees.view',
  'employees.manage',
  'inventory.view',
  'export_receipts.view',
  'export_receipts.manage',
  'import_receipts.view',
  'import_receipts.manage',
  'stock_transfers.view',
  'stock_transfers.manage',
  'warehouses.view',
  'warehouses.manage',
  'locations.view',
  'locations.manage',
  'products.view',
  'products.manage',
  'categories.view',
  'categories.manage',
  'suppliers.view',
  'suppliers.manage',
  'customers.view',
  'customers.manage',
];

const accountantPermissions = [
  'dashboard.view',
  'customers.view',
  'customers.manage',
  'bank_accounts.view',
  'bank_accounts.manage',
];

const staffPermissions = [
  'dashboard.view',
  'inventory.view',
  'export_receipts.view',
  'export_receipts.manage',
  'import_receipts.view',
  'import_receipts.manage',
  'stock_transfers.view',
  'stock_transfers.manage',
  'warehouses.view',
  'locations.view',
  'products.view',
];

function buildAuthState(overrides = {}) {
  const permissions = overrides.permissions || adminPermissions;

  return {
    loading: false,
    isAuthenticated: true,
    user: {
      id: 1,
      full_name: 'Admin User',
      role: 'admin',
      must_change_password: false,
      permissions,
      delegated_permission_sources: [],
      ...(overrides.user || {}),
    },
    login: vi.fn(async () => ({ must_change_password: false })),
    logout: vi.fn(),
    updateProfile: vi.fn(),
    hasPermission: (permission) => permissions.includes(permission),
    ...overrides,
  };
}

let authState = buildAuthState();

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
                base_permissions: adminPermissions,
                delegated_permissions: [],
                effective_permissions: adminPermissions,
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
                must_change_password: false,
              },
            ],
            total: 1,
            page: 1,
            page_size: 10,
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
            total: 1,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/inventory') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                warehouse_id: 1,
                warehouse_code: 'WH001',
                warehouse_name: 'Kho Trung Tam',
                location_id: 1,
                location_code: 'A-01',
                location_name: 'Ke A-01',
                product_id: 1,
                product_code: 'PRD001',
                product_name: 'Máy quét mã vạch',
                quantity: 24,
                updated_at: '2026-04-22T10:00:00',
              },
              {
                id: 2,
                warehouse_id: 2,
                warehouse_code: 'WH002',
                warehouse_name: 'Kho Miền Nam',
                location_id: 4,
                location_code: 'A-01',
                location_name: 'Dãy A-01',
                product_id: 1,
                product_code: 'PRD001',
                product_name: 'Máy quét mã vạch',
                quantity: 8,
                updated_at: '2026-04-22T10:15:00',
              },
            ],
          },
        });
      }

      if (url === '/import-receipts') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                receipt_code: 'IMP-DEMO-001',
                warehouse_id: 1,
                warehouse_code: 'WH001',
                warehouse_name: 'Kho Trung Tam',
                supplier_id: 1,
                supplier_code: 'SUP001',
                supplier_name: 'Công ty Sao Mai',
                created_by: 2,
                created_by_name: 'Manager User',
                confirmed_by: null,
                confirmed_by_name: null,
                status: 'draft',
                note: 'Phiếu nhập demo tối thiểu',
                detail_count: 2,
                total_quantity: 25,
                confirmed_at: null,
                created_at: '2026-04-22T09:00:00',
                updated_at: '2026-04-22T09:10:00',
                details: [
                  {
                    id: 1,
                    product_id: 1,
                    product_code: 'PRD001',
                    product_name: 'Máy quét mã vạch',
                    location_id: 1,
                    location_code: 'A-01',
                    location_name: 'Kệ A-01',
                    quantity: 5,
                  },
                  {
                    id: 2,
                    product_id: 1,
                    product_code: 'PRD001',
                    product_name: 'Máy quét mã vạch',
                    location_id: 2,
                    location_code: 'B-01',
                    location_name: 'Kệ B-01',
                    quantity: 20,
                  },
                ],
              },
            ],
            total: 1,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/export-receipts') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                receipt_code: 'EXP-DEMO-001',
                warehouse_id: 1,
                warehouse_code: 'WH001',
                warehouse_name: 'Kho Trung Tam',
                customer_id: 1,
                customer_code: 'CUS001',
                customer_name: 'Công ty Bình Minh',
                created_by: 2,
                created_by_name: 'Manager User',
                confirmed_by: null,
                confirmed_by_name: null,
                status: 'draft',
                note: 'Phiếu xuất demo tối thiểu',
                detail_count: 2,
                total_quantity: 17,
                confirmed_at: null,
                created_at: '2026-04-22T11:00:00',
                updated_at: '2026-04-22T11:10:00',
                details: [
                  {
                    id: 1,
                    product_id: 1,
                    product_code: 'PRD001',
                    product_name: 'Máy quét mã vạch',
                    location_id: 1,
                    location_code: 'A-01',
                    location_name: 'Kệ A-01',
                    quantity: 2,
                  },
                  {
                    id: 2,
                    product_id: 3,
                    product_code: 'PRD003',
                    product_name: 'Tem dán mã vận',
                    location_id: 2,
                    location_code: 'C-01',
                    location_name: 'Kệ C-01',
                    quantity: 15,
                  },
                ],
              },
            ],
            total: 1,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/stock-transfers') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                transfer_code: 'TRF-DEMO-001',
                source_warehouse_id: 1,
                source_warehouse_code: 'WH001',
                source_warehouse_name: 'Kho Trung Tam',
                target_warehouse_id: 2,
                target_warehouse_code: 'WH002',
                target_warehouse_name: 'Kho Mien Nam',
                created_by: 2,
                created_by_name: 'Manager User',
                confirmed_by: null,
                confirmed_by_name: null,
                status: 'draft',
                note: 'Phiếu điều chuyển demo tối thiểu',
                detail_count: 1,
                total_quantity: 3,
                confirmed_at: null,
                created_at: '2026-04-22T12:00:00',
                updated_at: '2026-04-22T12:10:00',
                details: [
                  {
                    id: 1,
                    product_id: 1,
                    product_code: 'PRD001',
                    product_name: 'Máy quét mã vạch',
                    source_location_id: 1,
                    source_location_code: 'A-01',
                    source_location_name: 'Kệ A-01',
                    target_location_id: 2,
                    target_location_code: 'A-01',
                    target_location_name: 'Dãy A-01',
                    quantity: 3,
                  },
                ],
              },
            ],
            total: 1,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/warehouses') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                warehouse_code: 'WH001',
                warehouse_name: 'Kho Trung Tâm',
                address: '12 Nguyễn Trãi, Hà Nội',
                status: 'active',
              },
              {
                id: 2,
                warehouse_code: 'WH002',
                warehouse_name: 'Kho Miền Nam',
                address: '215 Võ Văn Kiệt, TP.HCM',
                status: 'active',
              },
            ],
            total: 2,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/locations') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                warehouse_id: 1,
                warehouse_code: 'WH001',
                warehouse_name: 'Kho Trung Tâm',
                location_code: 'A-01',
                location_name: 'Kệ A-01',
                status: 'active',
              },
              {
                id: 2,
                warehouse_id: 2,
                warehouse_code: 'WH002',
                warehouse_name: 'Kho Miền Nam',
                location_code: 'B-01',
                location_name: 'Dãy B-01',
                status: 'active',
              },
            ],
            total: 2,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/inventory/movements') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                warehouse_id: 1,
                warehouse_name: 'Kho Trung Tam',
                location_id: 1,
                location_name: 'Ke A-01',
                product_id: 1,
                product_code: 'PRD001',
                product_name: 'Máy quét mã vạch',
                movement_type: 'adjustment',
                reference_type: 'seed',
                quantity_before: 0,
                quantity_change: 24,
                quantity_after: 24,
                performer_name: 'Manager User',
                created_at: '2026-04-22T09:00:00',
              },
            ],
          },
        });
      }

      if (url === '/categories') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                category_name: 'Điện tử',
                description: 'Thiết bị điện tử',
                updated_at: '2026-04-20T08:00:00',
              },
            ],
            total: 1,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/products') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                product_code: 'PRD001',
                product_name: 'Máy quét mã vạch',
                category_id: 1,
                category_name: 'Điện tử',
                quantity_total: 24,
                min_stock: 5,
                status: 'active',
                description: 'Thiết bị quét mã phục vụ kiểm kê',
                is_below_min_stock: false,
              },
            ],
            total: 1,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/suppliers') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                supplier_code: 'SUP001',
                supplier_name: 'Công ty Sao Mai',
                email: 'saomai@example.com',
                phone: '0909000001',
                address: 'Quận 1, TP.HCM',
                status: 'active',
              },
            ],
            total: 1,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/customers') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                customer_code: 'CUS001',
                customer_name: 'Công ty Bình Minh',
                email: 'binhminh@example.com',
                phone: '0909000002',
                address: 'Quận 7, TP.HCM',
                status: 'active',
              },
            ],
            total: 1,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/bank-accounts') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                bank_name: 'Vietcombank',
                account_number: '0123456789',
                account_holder: 'Công ty ABC',
                branch: 'Chi nhánh Quận 1',
                status: 'active',
              },
            ],
            total: 1,
            page: 1,
            page_size: 10,
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
              permissions: adminPermissions,
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
                status: 'active',
                created_at: '2026-04-16T08:00:00',
              },
            ],
          },
        });
      }

      if (url === '/audit-logs') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                action: 'users.created',
                entity_type: 'user',
                entity_label: 'admin',
                actor_user_name: 'Admin User',
                target_user_name: 'Admin User',
                description: 'Tạo tài khoản admin.',
                created_at: '2026-04-16T08:00:00',
              },
            ],
            total: 1,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/dashboard/identity') {
        return Promise.resolve({
          data: {
            profile: {
              username: 'admin',
              full_name: 'Admin User',
              role: 'admin',
              must_change_password: false,
              last_login_at: '2026-04-16T08:00:00',
            },
            employee: {
              employee_code: 'EMP001',
              department: 'Quản trị',
              position: 'Admin',
              status: 'active',
            },
            permission_summary: {
              total_permissions: adminPermissions.length,
              delegated_permissions: 0,
              role_permissions: adminPermissions.length,
            },
            delegation_summary: {
              active_received: 0,
              active_granted: 1,
              expiring_soon: 0,
            },
            management_summary: {
              total_users: 5,
              total_employees: 5,
              must_change_password_users: 1,
            },
            audit_summary: {
              total_logs: 4,
              today_logins: 2,
            },
            recent_activity: [],
          },
        });
      }

      return Promise.resolve({ data: { items: [], total: 0, page: 1, page_size: 10 } });
    }),
    post: vi.fn(() => Promise.resolve({ data: { item: { id: 1 } } })),
    put: vi.fn(() => Promise.resolve({ data: { item: { id: 1 } } })),
    patch: vi.fn(() => Promise.resolve({
      data: {
        user: {
          id: 1,
          username: 'admin',
          full_name: 'Admin User',
          email: 'admin@example.com',
          phone: '090000001',
          role: 'admin',
          must_change_password: false,
          permissions: adminPermissions,
          delegated_permission_sources: [],
        },
      },
    })),
    delete: vi.fn(() => Promise.resolve({ data: { message: 'ok', item: { status: 'revoked' } } })),
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
  authState = buildAuthState();
});

test('renders login page', () => {
  renderWithProviders(<LoginPage />, '/login');
  expect(screen.getByText(/Đăng nhập hệ thống/i)).toBeInTheDocument();
});

test('filters navigation items by permission', () => {
  authState = buildAuthState({
    permissions: managerPermissions,
    user: {
      id: 2,
      full_name: 'Manager User',
      role: 'manager',
    },
  });

  renderWithProviders(
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<div>Dashboard</div>} />
      </Route>
    </Routes>,
  );

  expect(screen.getByText(/Dashboard cá nhân/i)).toBeInTheDocument();
  expect(screen.getAllByText(/Nhân sự/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/^Nhập kho$/i)).toBeInTheDocument();
  expect(screen.getByText(/^Xuất kho$/i)).toBeInTheDocument();
  expect(screen.getByText(/^Danh mục nền$/i)).toBeInTheDocument();
  expect(screen.getByText(/^Ủy quyền quyền hạn$/i)).toBeInTheDocument();
  expect(screen.getByText(/^Audit log$/i)).toBeInTheDocument();
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
  await waitFor(() => expect(screen.getAllByText(/Admin User/i).length).toBeGreaterThan(0));
});

test('renders employees page', async () => {
  renderWithProviders(<EmployeesPage />, '/employees');
  await waitFor(() => expect(screen.getAllByText(/Nhân sự/i).length).toBeGreaterThan(0));
  await waitFor(() => expect(screen.getByText(/EMP001/i)).toBeInTheDocument());
});

test('renders catalogs page for admin with all tabs', async () => {
  renderWithProviders(<CatalogsPage />, '/catalogs?tab=categories');

  await waitFor(() => expect(screen.getAllByText(/Danh mục nền/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('tab', { name: /Nhóm hàng/i })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /Nhà cung cấp/i })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /Khách hàng/i })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /Tài khoản ngân hàng/i })).toBeInTheDocument();
});

test('accountant only sees customer and bank account tabs', async () => {
  authState = buildAuthState({
    permissions: accountantPermissions,
    user: {
      id: 4,
      full_name: 'Accountant User',
      role: 'accountant',
    },
  });

  renderWithProviders(<CatalogsPage />, '/catalogs?tab=customers');

  await waitFor(() => expect(screen.getByRole('tab', { name: /Khách hàng/i })).toBeInTheDocument());
  expect(screen.getByRole('tab', { name: /Tài khoản ngân hàng/i })).toBeInTheDocument();
  expect(screen.queryByRole('tab', { name: /Nhóm hàng/i })).not.toBeInTheDocument();
  expect(screen.queryByRole('tab', { name: /Nhà cung cấp/i })).not.toBeInTheDocument();
});

test('catalogs page redirects accountant to first allowed tab for invalid query tab', async () => {
  authState = buildAuthState({
    permissions: accountantPermissions,
    user: {
      id: 4,
      full_name: 'Accountant User',
      role: 'accountant',
    },
  });

  renderWithProviders(<CatalogsPage />, '/catalogs?tab=categories');

  await waitFor(() => expect(screen.getByRole('tab', { name: /Khách hàng/i })).toBeInTheDocument());
  expect(screen.queryByRole('tab', { name: /Nhóm hàng/i })).not.toBeInTheDocument();
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

test('renders audit logs page', async () => {
  renderWithProviders(<AuditLogsPage />, '/audit-logs');
  await waitFor(() => expect(screen.getAllByText(/Audit log/i).length).toBeGreaterThan(0));
  await waitFor(() => expect(screen.getAllByText(/users.created/i).length).toBeGreaterThan(0));
});

test('renders products page', async () => {
  renderWithProviders(<ProductsPage />, '/products');
  await waitFor(() => expect(screen.getAllByText(/Sản phẩm/i).length).toBeGreaterThan(0));
  await waitFor(() => expect(screen.getAllByText(/PRD001/i).length).toBeGreaterThan(0));
});

test('staff can render products page but not management actions', async () => {
  authState = buildAuthState({
    permissions: staffPermissions,
    user: {
      id: 3,
      full_name: 'Staff User',
      role: 'staff',
    },
  });

  renderWithProviders(<ProductsPage />, '/products');

  await waitFor(() => expect(screen.getAllByText(/PRD001/i).length).toBeGreaterThan(0));
  expect(screen.queryByRole('button', { name: /Thêm sản phẩm/i })).not.toBeInTheDocument();
});

test('renders inventory page', async () => {
  renderWithProviders(<InventoryPage />, '/inventory');
  await waitFor(() => expect(screen.getAllByText(/Tồn kho/i).length).toBeGreaterThan(0));
  await waitFor(() => expect(screen.getAllByText(/Kho Trung Tam/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('tab', { name: /Tồn hiện tại/i })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /Lịch sử biến động/i })).toBeInTheDocument();
});

test('renders warehouses page with warehouse and location tabs', async () => {
  renderWithProviders(<WarehousesPage />, '/warehouses?tab=warehouses');

  await waitFor(() => expect(screen.getAllByText(/Quản lý kho bãi/i).length).toBeGreaterThan(0));
  expect(screen.getAllByRole('tab')).toHaveLength(2);
  expect(screen.getByText(/Vị trí kho/i)).toBeInTheDocument();
  await waitFor(() => expect(screen.getAllByText(/WH001/i).length).toBeGreaterThan(0));
});

test('staff can render warehouses page but not management actions', async () => {
  authState = buildAuthState({
    permissions: staffPermissions,
    user: {
      id: 3,
      full_name: 'Staff User',
      role: 'staff',
    },
  });

  renderWithProviders(<WarehousesPage />, '/warehouses?tab=locations');

  await waitFor(() => expect(screen.getAllByText(/Kho Trung Tâm/i).length).toBeGreaterThan(0));
  expect(screen.queryByRole('button', { name: /Thêm kho/i })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /Thêm vị trí kho/i })).not.toBeInTheDocument();
});

/* Removed duplicate import-receipt smoke tests whose matchers were encoding-corrupted.
  renderWithProviders(<ImportReceiptsPage />, '/import-receipts');

  await waitFor(() => expect(screen.getAllByText(/Nháº­p kho/i).length).toBeGreaterThan(0));
  await waitFor(() => expect(screen.getAllByText(/IMP-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('button', { name: /ThÃªm phiáº¿u nháº­p nhÃ¡p/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /XÃ¡c nháº­n/i })).toBeInTheDocument();
});

Duplicate staff import-receipt smoke test removed.
  authState = buildAuthState({
    permissions: staffPermissions,
    user: {
      id: 3,
      full_name: 'Staff User',
      role: 'staff',
    },
  });

  renderWithProviders(<ImportReceiptsPage />, '/import-receipts');

  await waitFor(() => expect(screen.getAllByText(/IMP-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('button', { name: /ThÃªm phiáº¿u nháº­p nhÃ¡p/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /XÃ¡c nháº­n/i })).toBeInTheDocument();
});

*/

test('renders import receipts page with draft receipt data', async () => {
  renderWithProviders(<ImportReceiptsPage />, '/import-receipts');

  await waitFor(() => expect(screen.getByText(/Module 6/i)).toBeInTheDocument());
  await waitFor(() => expect(screen.getAllByText(/IMP-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('button', { name: /plus Thêm phiếu nhập nháp/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Chỉnh sửa/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Xác nhận/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Hủy phiếu/i })).toBeInTheDocument();
});

test('staff can render import receipts page and see inbound actions', async () => {
  authState = buildAuthState({
    permissions: staffPermissions,
    user: {
      id: 3,
      full_name: 'Staff User',
      role: 'staff',
    },
  });

  renderWithProviders(<ImportReceiptsPage />, '/import-receipts');

  await waitFor(() => expect(screen.getAllByText(/IMP-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('button', { name: /plus Thêm phiếu nhập nháp/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Chỉnh sửa/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Xác nhận/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Hủy phiếu/i })).toBeInTheDocument();
});

test('renders export receipts page with draft receipt data', async () => {
  renderWithProviders(<ExportReceiptsPage />, '/export-receipts');

  await waitFor(() => expect(screen.getByText(/Luồng xuất kho tối thiểu/i)).toBeInTheDocument());
  await waitFor(() => expect(screen.getAllByText(/EXP-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('button', { name: /plus Thêm phiếu xuất nháp/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Chỉnh sửa/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Xác nhận/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Hủy phiếu/i })).toBeInTheDocument();
});

test('staff can render export receipts page and see outbound actions', async () => {
  authState = buildAuthState({
    permissions: staffPermissions,
    user: {
      id: 3,
      full_name: 'Staff User',
      role: 'staff',
    },
  });

  renderWithProviders(<ExportReceiptsPage />, '/export-receipts');

  await waitFor(() => expect(screen.getAllByText(/EXP-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('button', { name: /plus Thêm phiếu xuất nháp/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Chỉnh sửa/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Xác nhận/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Hủy phiếu/i })).toBeInTheDocument();
});

test('renders stock transfers page with draft transfer data', async () => {
  renderWithProviders(<StockTransfersPage />, '/stock-transfers');

  await waitFor(() => expect(screen.getByText(/Luồng điều chuyển kho tối thiểu/i)).toBeInTheDocument());
  await waitFor(() => expect(screen.getAllByText(/TRF-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('button', { name: /plus Thêm phiếu điều chuyển nháp/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Xác nhận/i })).toBeInTheDocument();
});

test('staff can render stock transfers page and see transfer actions', async () => {
  authState = buildAuthState({
    permissions: staffPermissions,
    user: {
      id: 3,
      full_name: 'Staff User',
      role: 'staff',
    },
  });

  renderWithProviders(<StockTransfersPage />, '/stock-transfers');

  await waitFor(() => expect(screen.getAllByText(/TRF-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('button', { name: /plus Thêm phiếu điều chuyển nháp/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Xác nhận/i })).toBeInTheDocument();
});

test('staff can render inventory page', async () => {
  authState = buildAuthState({
    permissions: staffPermissions,
    user: {
      id: 3,
      full_name: 'Staff User',
      role: 'staff',
    },
  });

  renderWithProviders(<InventoryPage />, '/inventory');

  await waitFor(() => expect(screen.getAllByText(/Kho Trung Tam/i).length).toBeGreaterThan(0));
});

test('redirects unauthenticated users to login', async () => {
  authState = buildAuthState({ isAuthenticated: false });

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
  authState = buildAuthState({
    permissions: ['dashboard.view'],
    user: {
      id: 3,
      full_name: 'Staff User',
      role: 'staff',
    },
  });

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
