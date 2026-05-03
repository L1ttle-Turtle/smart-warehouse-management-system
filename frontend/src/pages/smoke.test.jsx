import { ConfigProvider } from 'antd';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import api from '../api/client';
import AppShell from '../components/AppShell';
import ProtectedRoute from '../components/ProtectedRoute';
import AuditLogsPage from './AuditLogsPage';
import CatalogsPage from './CatalogsPage';
import DelegationPage from './DelegationPage';
import EmployeesPage from './EmployeesPage';
import ExportReceiptsPage from './ExportReceiptsPage';
import ImportReceiptsPage from './ImportReceiptsPage';
import InventoryPage from './InventoryPage';
import InvoicesPage from './InvoicesPage';
import LoginPage from './LoginPage';
import NotificationsPage from './NotificationsPage';
import ProfilePage from './ProfilePage';
import ProductsPage from './ProductsPage';
import ReportsPage from './ReportsPage';
import RolesPage from './RolesPage';
import ShipmentsPage from './ShipmentsPage';
import StocktakesPage from './StocktakesPage';
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
  'inventory.manage',
  'inventory.view',
  'export_receipts.view',
  'export_receipts.manage',
  'import_receipts.view',
  'import_receipts.manage',
  'stock_transfers.view',
  'stock_transfers.manage',
  'shipments.view',
  'shipments.manage',
  'invoices.view',
  'invoices.manage',
  'notifications.view',
  'notifications.manage',
  'tasks.view',
  'tasks.manage',
  'warehouses.view',
  'warehouses.manage',
  'locations.view',
  'locations.manage',
  'products.view',
  'products.manage',
  'reports.view',
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
  'inventory.manage',
  'inventory.view',
  'export_receipts.view',
  'export_receipts.manage',
  'import_receipts.view',
  'import_receipts.manage',
  'stock_transfers.view',
  'stock_transfers.manage',
  'shipments.view',
  'shipments.manage',
  'invoices.view',
  'invoices.manage',
  'notifications.view',
  'notifications.manage',
  'tasks.view',
  'tasks.manage',
  'warehouses.view',
  'warehouses.manage',
  'locations.view',
  'locations.manage',
  'products.view',
  'products.manage',
  'reports.view',
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
  'invoices.view',
  'invoices.manage',
  'notifications.view',
  'reports.view',
  'tasks.view',
];

const staffPermissions = [
  'dashboard.view',
  'inventory.manage',
  'inventory.view',
  'export_receipts.view',
  'export_receipts.manage',
  'import_receipts.view',
  'import_receipts.manage',
  'stock_transfers.view',
  'stock_transfers.manage',
  'shipments.view',
  'shipments.manage',
  'notifications.view',
  'tasks.view',
  'warehouses.view',
  'locations.view',
  'products.view',
];

const shipperPermissions = [
  'dashboard.view',
  'notifications.view',
  'shipments.view',
  'shipments.manage',
  'tasks.view',
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
    get: vi.fn((url, config) => {
      if (url === '/tasks/meta') {
        return Promise.resolve({
          data: {
            users: [
              {
                id: 3,
                username: 'staff',
                full_name: 'Staff User',
                role_name: 'staff',
                status: 'active',
              },
              {
                id: 4,
                username: 'accountant',
                full_name: 'Accountant User',
                role_name: 'accountant',
                status: 'active',
              },
            ],
          },
        });
      }

      if (url === '/tasks') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                task_code: 'TSK-DEMO-001',
                title: 'Kiểm tra tồn thấp',
                description: 'Kiểm tra các dòng tồn thấp trước ca xuất hàng.',
                assigned_to_id: 3,
                assigned_to_name: 'Staff User',
                assigned_to_role: 'staff',
                created_by: 2,
                created_by_name: 'Manager User',
                status: 'todo',
                priority: 'high',
                due_at: '2026-05-02T09:00:00',
                created_at: '2026-05-02T08:00:00',
              },
            ],
            total: 1,
            page: 1,
            page_size: 20,
          },
        });
      }

      if (url === '/notifications') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                sender_id: 2,
                sender_name: 'Manager User',
                receiver_id: 3,
                receiver_name: 'Staff User',
                title: 'Công việc mới TSK-DEMO-001',
                content: 'Kiểm tra tồn thấp',
                type: 'task',
                is_read: false,
                created_at: '2026-05-02T08:05:00',
              },
            ],
            total: 1,
            page: 1,
            page_size: 20,
          },
        });
      }

      if (url === '/reports/inventory-by-warehouse') {
        return Promise.resolve({
          data: {
            items: [
              { warehouse_name: 'Kho Trung Tam', quantity: 184 },
              { warehouse_name: 'Kho Mien Nam', quantity: 130 },
            ],
          },
        });
      }

      if (url === '/reports/stock-movement') {
        return Promise.resolve({
          data: {
            items: [
              { month: '2026-05', import_quantity: 45, export_quantity: 19 },
            ],
          },
        });
      }

      if (url === '/reports/top-products') {
        return Promise.resolve({
          data: {
            items: [
              { product_id: 1, product_name: 'Máy quét mã vạch', quantity: 12 },
            ],
          },
        });
      }

      if (url === '/reports/shipment-performance') {
        return Promise.resolve({
          data: {
            items: [
              { status: 'assigned', status_label: 'Đã phân công', count: 1 },
              { status: 'delivered', status_label: 'Đã giao', count: 2 },
            ],
          },
        });
      }

      if (url === '/reports/revenue') {
        return Promise.resolve({
          data: {
            revenue: [
              { month: '2026-05', revenue: 4200000 },
            ],
            payment_status: [
              { status: 'unpaid', count: 1 },
              { status: 'paid', count: 1 },
            ],
          },
        });
      }

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
                category_id: 1,
                category_name: 'Äiá»‡n tá»­',
                min_stock: 10,
                quantity: 24,
                stock_status: 'in_stock',
                stock_status_label: 'Äá»§ hÃ ng',
                is_low_stock: false,
                shortage_quantity: 0,
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
                category_id: 1,
                category_name: 'Äiá»‡n tá»­',
                min_stock: 10,
                quantity: 8,
                stock_status: 'low_stock',
                stock_status_label: 'Tá»“n tháº¥p',
                is_low_stock: true,
                shortage_quantity: 2,
                updated_at: '2026-04-22T10:15:00',
              },
              {
                id: 3,
                warehouse_id: 1,
                warehouse_code: 'WH001',
                warehouse_name: 'Kho Trung Tam',
                location_id: 3,
                location_code: 'C-01',
                location_name: 'Ke C-01',
                product_id: 4,
                product_code: 'PRD004',
                product_name: 'Bá»™ Ä‘Ã m kho',
                category_id: 1,
                category_name: 'Äiá»‡n tá»­',
                min_stock: 12,
                quantity: 0,
                stock_status: 'out_of_stock',
                stock_status_label: 'Háº¿t hÃ ng',
                is_low_stock: true,
                shortage_quantity: 12,
                updated_at: '2026-04-22T10:30:00',
              },
            ],
            total: 3,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/stocktakes') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                stocktake_code: 'STK-DEMO-001',
                warehouse_id: 1,
                warehouse_code: 'WH001',
                warehouse_name: 'Kho Trung Tam',
                created_by: 2,
                created_by_name: 'Manager User',
                confirmed_by: null,
                confirmed_by_name: null,
                cancelled_by: null,
                cancelled_by_name: null,
                status: 'draft',
                note: 'Phiáº¿u kiá»ƒm kÃª demo tá»‘i thiá»ƒu',
                detail_count: 2,
                total_actual_quantity: 23,
                total_difference_quantity: -1,
                confirmed_at: null,
                cancelled_at: null,
                created_at: '2026-04-24T08:30:00',
                updated_at: '2026-04-24T08:45:00',
                details: [
                  {
                    id: 1,
                    product_id: 1,
                    product_code: 'PRD001',
                    product_name: 'MÃ¡y quÃ©t mÃ£ váº¡ch',
                    location_id: 1,
                    location_code: 'A-01',
                    location_name: 'Ká»‡ A-01',
                    system_quantity: 24,
                    actual_quantity: 23,
                    difference_quantity: -1,
                    note: 'Thiáº¿u 1 thiáº¿t bá»‹ sau ca sÃ¡ng',
                  },
                  {
                    id: 2,
                    product_id: 4,
                    product_code: 'PRD004',
                    product_name: 'Bá»™ Ä‘Ã m kho',
                    location_id: 3,
                    location_code: 'C-01',
                    location_name: 'Ká»‡ C-01',
                    system_quantity: 0,
                    actual_quantity: 0,
                    difference_quantity: 0,
                    note: '',
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

      if (url === '/shipments') {
        const shipmentItems = [
          {
            id: 1,
            shipment_code: 'SHP-DEMO-001',
            export_receipt_id: 2,
            export_receipt_code: 'EXP-SHP-001',
            warehouse_id: 2,
            warehouse_code: 'WH002',
            warehouse_name: 'Kho Mien Nam',
            customer_id: 1,
            customer_code: 'CUS001',
            customer_name: 'Cong ty Binh Minh',
            shipper_id: 5,
            shipper_name: 'Shipper User',
            created_by: 2,
            created_by_name: 'Manager User',
            status: 'assigned',
            note: 'Giao tuyen noi thanh buoi chieu',
            detail_count: 1,
            total_quantity: 2,
            assigned_at: '2026-04-25T14:00:00',
            in_transit_at: null,
            delivered_at: null,
            cancelled_at: null,
            created_at: '2026-04-25T13:55:00',
            updated_at: '2026-04-25T14:00:00',
            details: [
              {
                id: 1,
                product_id: 6,
                product_code: 'PRD006',
                product_name: 'May in nhan mini',
                location_id: 4,
                location_code: 'A-01',
                location_name: 'Day A-01',
                quantity: 2,
              },
            ],
          },
        ];

        return Promise.resolve({
          data: {
            items: shipmentItems,
            total: shipmentItems.length,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/shipments/meta') {
        return Promise.resolve({
          data: {
            shippers: [
              {
                id: 5,
                username: 'shipper',
                full_name: 'Shipper User',
                email: 'shipper@example.com',
                phone: '0909000005',
                status: 'active',
                role_id: 5,
                role_name: 'shipper',
                employee_id: 5,
                employee_code: 'EMP005',
              },
            ],
            export_receipts: [
              {
                id: 2,
                receipt_code: 'EXP-SHP-001',
                warehouse_id: 2,
                warehouse_code: 'WH002',
                warehouse_name: 'Kho Mien Nam',
                customer_id: 1,
                customer_code: 'CUS001',
                customer_name: 'Cong ty Binh Minh',
                created_by: 2,
                created_by_name: 'Manager User',
                confirmed_by: 2,
                confirmed_by_name: 'Manager User',
                status: 'confirmed',
                note: 'Phieu xuat san sang giao',
                detail_count: 1,
                total_quantity: 2,
                confirmed_at: '2026-04-25T13:50:00',
                created_at: '2026-04-25T13:40:00',
                updated_at: '2026-04-25T13:50:00',
                details: [
                  {
                    id: 1,
                    product_id: 6,
                    product_code: 'PRD006',
                    product_name: 'May in nhan mini',
                    location_id: 4,
                    location_code: 'A-01',
                    location_name: 'Day A-01',
                    quantity: 2,
                  },
                ],
              },
            ],
          },
        });
      }

      if (url === '/invoices') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                invoice_code: 'INV-DEMO-001',
                export_receipt_id: 2,
                export_receipt_code: 'EXP-SHP-001',
                warehouse_id: 2,
                warehouse_code: 'WH002',
                warehouse_name: 'Kho Mien Nam',
                customer_id: 1,
                customer_code: 'CUS001',
                customer_name: 'Cong ty Binh Minh',
                bank_account_id: 1,
                bank_name: 'Vietcombank',
                bank_account_number: '0123456789',
                bank_account_holder: 'Cong ty Kho Thong Minh',
                created_by: 2,
                created_by_name: 'Manager User',
                status: 'unpaid',
                note: 'Hoa don demo tu phieu xuat da xac nhan',
                detail_count: 1,
                total_quantity: 2,
                total_amount: 3000000,
                paid_amount: 0,
                remaining_amount: 3000000,
                issued_at: '2026-04-28T10:00:00',
                created_at: '2026-04-28T10:00:00',
                updated_at: '2026-04-28T10:00:00',
                details: [
                  {
                    id: 1,
                    export_receipt_detail_id: 1,
                    product_id: 6,
                    product_code: 'PRD006',
                    product_name: 'May in nhan mini',
                    location_id: 4,
                    location_code: 'A-01',
                    location_name: 'Day A-01',
                    quantity: 2,
                    unit_price: 1500000,
                    line_total: 3000000,
                  },
                ],
                payments: [],
              },
            ],
            total: 1,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/invoices/meta') {
        return Promise.resolve({
          data: {
            bank_accounts: [
              {
                id: 1,
                bank_name: 'Vietcombank',
                account_number: '0123456789',
                account_holder: 'Cong ty Kho Thong Minh',
                branch: 'Chi nhanh Quan 1',
                status: 'active',
              },
            ],
            export_receipts: [
              {
                id: 2,
                receipt_code: 'EXP-SHP-001',
                warehouse_id: 2,
                warehouse_code: 'WH002',
                warehouse_name: 'Kho Mien Nam',
                customer_id: 1,
                customer_code: 'CUS001',
                customer_name: 'Cong ty Binh Minh',
                created_by: 2,
                created_by_name: 'Manager User',
                confirmed_by: 2,
                confirmed_by_name: 'Manager User',
                status: 'confirmed',
                note: 'Phieu xuat san sang lap hoa don',
                detail_count: 1,
                total_quantity: 2,
                confirmed_at: '2026-04-28T09:55:00',
                created_at: '2026-04-28T09:45:00',
                updated_at: '2026-04-28T09:55:00',
                details: [
                  {
                    id: 1,
                    product_id: 6,
                    product_code: 'PRD006',
                    product_name: 'May in nhan mini',
                    location_id: 4,
                    location_code: 'A-01',
                    location_name: 'Day A-01',
                    quantity: 2,
                  },
                ],
              },
            ],
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
                warehouse_id: 1,
                warehouse_code: 'WH001',
                warehouse_name: 'Kho Trung Tâm',
                location_code: 'B-01',
                location_name: 'Kệ B-01',
                status: 'active',
              },
              {
                id: 3,
                warehouse_id: 1,
                warehouse_code: 'WH001',
                warehouse_name: 'Kho Trung Tâm',
                location_code: 'C-01',
                location_name: 'Kệ C-01',
                status: 'active',
              },
              {
                id: 4,
                warehouse_id: 2,
                warehouse_code: 'WH002',
                warehouse_name: 'Kho Miền Nam',
                location_code: 'A-01',
                location_name: 'Dãy A-01',
                status: 'active',
              },
              {
                id: 5,
                warehouse_id: 2,
                warehouse_code: 'WH002',
                warehouse_name: 'Kho Miền Nam',
                location_code: 'B-01',
                location_name: 'Dãy B-01',
                status: 'active',
              },
            ],
            total: 5,
            page: 1,
            page_size: 10,
          },
        });
      }

      if (url === '/inventory/movements') {
        if (config?.params?.reference_type === 'import_receipt') {
          return Promise.resolve({
            data: {
              items: [
                {
                  id: 11,
                  warehouse_id: 1,
                  warehouse_name: 'Kho Trung Tam',
                  location_id: 1,
                  location_name: 'Ke A-01',
                  product_id: 1,
                  product_code: 'PRD001',
                  product_name: 'Máy quét mã vạch',
                  movement_type: 'import',
                  reference_type: 'import_receipt',
                  reference_id: 1,
                  quantity_before: 18,
                  quantity_change: 6,
                  quantity_after: 24,
                  performer_name: 'Manager User',
                  created_at: '2026-04-22T10:00:00',
                },
              ],
            },
          });
        }

        if (config?.params?.reference_type === 'export_receipt') {
          return Promise.resolve({
            data: {
              items: [
                {
                  id: 12,
                  warehouse_id: 1,
                  warehouse_name: 'Kho Trung Tam',
                  location_id: 1,
                  location_name: 'Ke A-01',
                  product_id: 1,
                  product_code: 'PRD001',
                  product_name: 'Máy quét mã vạch',
                  movement_type: 'export',
                  reference_type: 'export_receipt',
                  reference_id: 1,
                  quantity_before: 24,
                  quantity_change: -4,
                  quantity_after: 20,
                  performer_name: 'Manager User',
                  created_at: '2026-04-22T11:00:00',
                },
              ],
            },
          });
        }

        if (config?.params?.reference_type === 'stock_transfer') {
          return Promise.resolve({
            data: {
              items: [],
            },
          });
        }

        if (config?.params?.reference_type === 'stocktake') {
          return Promise.resolve({
            data: {
              items: [
                {
                  id: 21,
                  warehouse_id: 1,
                  warehouse_code: 'WH001',
                  warehouse_name: 'Kho Trung Tam',
                  location_id: 1,
                  location_code: 'A-01',
                  location_name: 'Ke A-01',
                  product_id: 1,
                  product_code: 'PRD001',
                  product_name: 'Máy quét mã vạch',
                  movement_type: 'stocktake_adjustment',
                  reference_type: 'stocktake',
                  reference_id: 1,
                  quantity_before: 24,
                  quantity_change: -1,
                  quantity_after: 23,
                  performer_name: 'Manager User',
                  note: 'Điều chỉnh sau kiểm kê kho',
                  created_at: '2026-04-24T09:00:00',
                },
              ],
            },
          });
        }

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
  vi.clearAllMocks();
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

test('inventory page shows stock status columns and low-stock filter', async () => {
  renderWithProviders(<InventoryPage />, '/inventory');

  await waitFor(() => expect(screen.getByRole('columnheader', { name: /Trạng thái/i })).toBeInTheDocument());
  expect(screen.getByRole('columnheader', { name: /Tồn hiện tại/i })).toBeInTheDocument();
  expect(screen.getByRole('columnheader', { name: /Tồn tối thiểu/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Chỉ tồn thấp/i })).toBeInTheDocument();
  expect(screen.getAllByText(/Hết hàng/i).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/Tồn thấp/i).length).toBeGreaterThan(0);
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
  expect(screen.getByText(/Lịch sử nhập kho đã ghi nhận/i)).toBeInTheDocument();
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
  expect(screen.getByText(/Lịch sử nhập kho đã ghi nhận/i)).toBeInTheDocument();
});

test('renders export receipts page with draft receipt data', async () => {
  renderWithProviders(<ExportReceiptsPage />, '/export-receipts');

  await waitFor(() => expect(screen.getByText(/Luồng xuất kho tối thiểu/i)).toBeInTheDocument());
  await waitFor(() => expect(screen.getAllByText(/EXP-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('button', { name: /plus Thêm phiếu xuất nháp/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Chỉnh sửa/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Xác nhận/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Hủy phiếu/i })).toBeInTheDocument();
  expect(screen.getByText(/Lịch sử xuất kho đã ghi nhận/i)).toBeInTheDocument();
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
  expect(screen.getByText(/Lịch sử xuất kho đã ghi nhận/i)).toBeInTheDocument();
});

test('renders stock transfers page with draft transfer data', async () => {
  renderWithProviders(<StockTransfersPage />, '/stock-transfers');

  await waitFor(() => expect(screen.getByText(/Luồng điều chuyển kho tối thiểu/i)).toBeInTheDocument());
  await waitFor(() => expect(screen.getAllByText(/TRF-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('button', { name: /plus Thêm phiếu điều chuyển nháp/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Chỉnh sửa/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Xác nhận/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Hủy phiếu/i })).toBeInTheDocument();
  expect(screen.getByText(/Lịch sử điều chuyển đã ghi nhận/i)).toBeInTheDocument();
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
  expect(screen.getByRole('button', { name: /Chỉnh sửa/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Xác nhận/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Hủy phiếu/i })).toBeInTheDocument();
  expect(screen.getByText(/Lịch sử điều chuyển đã ghi nhận/i)).toBeInTheDocument();
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

test('inventory page shows stock adjustment tab for admin', async () => {
  renderWithProviders(<InventoryPage />, '/inventory');

  await waitFor(() => expect(screen.getAllByText(/Kho Trung Tam/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('tab', { name: /Điều chỉnh tồn kho/i })).toBeInTheDocument();
});

test('inventory page shows stock adjustment tab for staff', async () => {
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
  expect(screen.getByRole('tab', { name: /Điều chỉnh tồn kho/i })).toBeInTheDocument();
});

test('renders stocktakes page with draft stocktake and opens stocktake form', async () => {
  renderWithProviders(<StocktakesPage />, '/stocktakes');

  await waitFor(() => expect(screen.getByText(/Kiểm kê kho/i)).toBeInTheDocument());
  await waitFor(() => expect(screen.getAllByText(/STK-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByText(/Lịch sử biến động/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Xác nhận/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Hủy phiếu/i })).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /Thêm phiếu kiểm kê/i }));

  await waitFor(() => expect(screen.getByText(/Kho kiểm kê/i)).toBeInTheDocument());
  expect(screen.getByText(/Sản phẩm 1/i)).toBeInTheDocument();
  expect(screen.getAllByText(/^Vị trí$/i).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/Tồn thực tế/i).length).toBeGreaterThan(0);
  expect(screen.getByRole('button', { name: /Tạo phiếu nháp/i })).toBeInTheDocument();
});

test('renders shipments page with create action for manager flow', async () => {
  renderWithProviders(<ShipmentsPage />, '/shipments');

  await waitFor(() => expect(screen.getByText(/Vận chuyển/i)).toBeInTheDocument());
  await waitFor(() => expect(screen.getAllByText(/SHP-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('button', { name: /Tạo shipment/i })).toBeInTheDocument();
  expect(screen.getByText(/Chi tiết shipment/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /Tạo shipment/i }));

  await waitFor(() => expect(screen.getByText(/Tạo shipment từ phiếu xuất đã xác nhận/i)).toBeInTheDocument());
  expect(screen.getAllByText(/Phiếu xuất đã xác nhận/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/Shipper phụ trách/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /^Tạo shipment$/i })).toBeInTheDocument();
});

test('shipper can render shipments page and see delivery actions', async () => {
  authState = buildAuthState({
    permissions: shipperPermissions,
    user: {
      id: 5,
      full_name: 'Shipper User',
      role: 'shipper',
    },
  });

  renderWithProviders(<ShipmentsPage />, '/shipments');

  await waitFor(() => expect(screen.getAllByText(/SHP-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.queryByRole('button', { name: /Tạo shipment/i })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Bắt đầu giao/i })).toBeInTheDocument();
});

test('renders invoices page with list and create action for manager flow', async () => {
  renderWithProviders(<InvoicesPage />, '/invoices');

  await waitFor(() => expect(screen.getByRole('heading', { name: /^Hóa đơn$/i })).toBeInTheDocument());
  await waitFor(() => expect(screen.getAllByText(/INV-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByText(/Chi tiết hóa đơn/i)).toBeInTheDocument();
  expect(screen.getAllByText(/Ghi nhận thanh toán/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/Lịch sử thanh toán/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Ghi nhận/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Tạo hóa đơn/i })).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /Thu đủ/i }));
  fireEvent.click(screen.getByRole('button', { name: /Ghi nhận/i }));

  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    '/payments',
    expect.objectContaining({
      invoice_id: 1,
      amount: 3000000,
    }),
  ));

  fireEvent.click(screen.getByRole('button', { name: /Tạo hóa đơn/i }));

  await waitFor(() => expect(screen.getByText(/Tạo hóa đơn từ phiếu xuất đã xác nhận/i)).toBeInTheDocument());
  expect(screen.getAllByText(/Phiếu xuất đã xác nhận/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/Tài khoản ngân hàng nhận tiền/i)).toBeInTheDocument();
  expect(screen.getAllByText(/Đơn giá/i).length).toBeGreaterThan(0);
  expect(screen.getAllByRole('button', { name: /Tạo hóa đơn/i }).length).toBeGreaterThan(0);
});

test('accountant can render invoices page for demo review', async () => {
  authState = buildAuthState({
    permissions: accountantPermissions,
    user: {
      id: 4,
      full_name: 'Accountant User',
      role: 'accountant',
    },
  });

  renderWithProviders(<InvoicesPage />, '/invoices');

  await waitFor(() => expect(screen.getAllByText(/INV-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('button', { name: /Tạo hóa đơn/i })).toBeInTheDocument();
  expect(screen.getByText(/Chi tiết hóa đơn/i)).toBeInTheDocument();
});

test('renders reports page with business summary charts', async () => {
  renderWithProviders(<ReportsPage />, '/reports');

  await waitFor(() => expect(screen.getByText(/Tồn kho theo kho/i)).toBeInTheDocument());
  expect(screen.getByText(/Nhập xuất theo tháng/i)).toBeInTheDocument();
  expect(screen.getByText(/Trạng thái vận chuyển/i)).toBeInTheDocument();
  expect(screen.getByText(/Doanh thu hóa đơn/i)).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText(/Máy quét mã vạch/i)).toBeInTheDocument());
  expect(screen.getByText(/Chưa thanh toán/i)).toBeInTheDocument();
  expect(screen.getByText(/Đã thanh toán/i)).toBeInTheDocument();
});

test('renders notifications page with tasks and notification actions', async () => {
  renderWithProviders(<NotificationsPage />, '/notifications');

  await waitFor(() => expect(screen.getByText(/Công việc & thông báo/i)).toBeInTheDocument());
  await waitFor(() => expect(screen.getAllByText(/TSK-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('tab', { name: /Công việc/i })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /Thông báo/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Tạo công việc/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Gửi thông báo/i })).toBeInTheDocument();

  fireEvent.click(screen.getByRole('tab', { name: /Thông báo/i }));

  await waitFor(() => expect(screen.getAllByText(/Công việc mới TSK-DEMO-001/i).length).toBeGreaterThan(0));
  expect(screen.getByRole('button', { name: /Đánh dấu đã đọc/i })).toBeInTheDocument();
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
