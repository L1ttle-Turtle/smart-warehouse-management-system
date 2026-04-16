import {
  TeamOutlined,
  DashboardOutlined,
  SafetyCertificateOutlined,
  SwapOutlined,
  UserOutlined,
} from '@ant-design/icons';

export const navigationItems = [
  { key: '/', label: 'Tổng quan quyền', icon: DashboardOutlined, permission: 'dashboard.view' },
  { key: '/users', label: 'Tài khoản', icon: UserOutlined, permission: 'users.view' },
  { key: '/employees', label: 'Nhân sự', icon: TeamOutlined, permission: 'employees.view' },
  { key: '/delegations', label: 'Ủy quyền quyền hạn', icon: SwapOutlined, permission: 'delegations.manage' },
  { key: '/roles', label: 'Vai trò và quyền', icon: SafetyCertificateOutlined, permission: 'roles.view' },
  { key: '/profile', label: 'Hồ sơ cá nhân', icon: UserOutlined, permission: null },
];
