import {
  HomeOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import { Avatar, Button, Dropdown, Layout, Menu, Space, Typography } from 'antd';
import { createElement, useMemo, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/useAuth';
import { navigationItems } from '../config/navigation';

const { Header, Sider, Content } = Layout;

function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, hasPermission } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

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

  const menuItems = items.map((item) => ({
    key: item.key,
    icon: createElement(item.icon),
    label: item.label,
  }));

  const selectedKey = items.find(
    (item) => location.pathname === item.key || location.pathname.startsWith(`${item.key}/`),
  )?.key || '/';

  return (
    <Layout className="app-layout">
      <Sider
        breakpoint="lg"
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={260}
        className="app-sider"
        style={{
          background: 'var(--bg-sidebar)',
          boxShadow: '18px 0 48px rgba(17, 51, 47, 0.22)',
        }}
      >
        <div className="sidebar-brand">
          <div className="sidebar-brand-badge" aria-label="Biểu tượng hệ thống kho">
            <HomeOutlined />
          </div>
          {!collapsed ? (
            <Typography.Text className="sidebar-brand-text">
              Kho thông minh
            </Typography.Text>
          ) : null}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{
            borderInlineEnd: 'none',
            background: 'transparent',
            color: '#f8efe1',
            paddingInline: 10,
          }}
          theme="dark"
        />
      </Sider>
      <Layout style={{ background: 'transparent' }}>
        <Header
          style={{
            background: 'transparent',
            padding: '18px 24px 0',
            height: 'auto',
            lineHeight: 'normal',
          }}
        >
          <div className="glass-panel" style={{ borderRadius: 24, padding: '14px 18px' }}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space>
                <Button
                  type="text"
                  icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                  onClick={() => setCollapsed((value) => !value)}
                />
                <div>
                  <Typography.Title level={4} style={{ margin: 0, fontFamily: '"Space Grotesk", sans-serif' }}>
                    Hệ thống quản lý kho thông minh
                  </Typography.Title>
                  <Typography.Text type="secondary">
                    Quản lý tài khoản, nhân sự và danh mục nền trên cùng một không gian làm việc rõ ràng, dễ dùng.
                  </Typography.Text>
                </div>
              </Space>
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
                <Space style={{ cursor: 'pointer' }}>
                  <Avatar style={{ background: '#1f6f5f' }}>
                    {user?.full_name?.slice(0, 1)?.toUpperCase()}
                  </Avatar>
                  <div>
                    <Typography.Text strong>{user?.full_name}</Typography.Text>
                    <br />
                    <Typography.Text type="secondary">{user?.role || 'Chưa có vai trò'}</Typography.Text>
                  </div>
                </Space>
              </Dropdown>
            </Space>
          </div>
        </Header>
        <Content className="page-shell">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

export default AppShell;
