import {
  HomeOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { Avatar, Button, Dropdown, Space, Typography } from 'antd';
import { createElement, useMemo } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/useAuth';
import { navigationItems } from '../config/navigation';

function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, hasPermission } = useAuth();

  const items = useMemo(
    () => navigationItems.filter((item) => {
      if (!item.permission && !item.permissionAny) {
        return true;
      }

      if (item.permission && hasPermission(item.permission)) {
        return true;
      }

      if (item.permissionAny?.some((permission) => hasPermission(permission))) {
        return true;
      }

      return false;
    }),
    [hasPermission],
  );

  const selectedKey = items.find(
    (item) => location.pathname === item.key || location.pathname.startsWith(`${item.key}/`),
  )?.key || '/';

  return (
    <div className="app-layout">
      <header className="app-topbar">
        <button className="topbar-brand" type="button" onClick={() => navigate('/')}>
          <div className="topbar-brand-mark" aria-label="Biểu tượng hệ thống kho">
            <HomeOutlined />
          </div>
          <div className="topbar-brand-copy">
            <Typography.Text className="brand-kicker">Warehouse IQ</Typography.Text>
            <Typography.Text className="brand-name">Kho thông minh</Typography.Text>
          </div>
        </button>

        <nav className="topbar-nav" aria-label="Điều hướng chính">
          {items.map((item) => {
            const isActive = selectedKey === item.key;
            return (
              <button
                key={item.key}
                type="button"
                className={`topbar-nav-item${isActive ? ' topbar-nav-item--active' : ''}`}
                aria-current={isActive ? 'page' : undefined}
                onClick={() => navigate(item.key)}
              >
                <span className="topbar-nav-icon">{createElement(item.icon)}</span>
                <span className="topbar-nav-label">{item.label}</span>
              </button>
            );
          })}
        </nav>

        <Dropdown
          menu={{
            items: [{ key: 'logout', label: 'Đăng xuất', icon: <LogoutOutlined /> }],
            onClick: ({ key }) => {
              if (key === 'logout') {
                logout();
              }
            },
          }}
        >
          <Button className="topbar-user" type="text">
            <Space>
              <Avatar className="topbar-user-avatar">
                {user?.full_name?.slice(0, 1)?.toUpperCase()}
              </Avatar>
              <span className="topbar-user-copy">
                <Typography.Text strong>{user?.full_name}</Typography.Text>
                <Typography.Text type="secondary">{user?.role || 'Chưa có vai trò'}</Typography.Text>
              </span>
            </Space>
          </Button>
        </Dropdown>
      </header>

      <main className="page-shell">
        <div className="page-ambient" aria-hidden="true" />
        <Outlet />
      </main>
    </div>
  );
}

export default AppShell;
