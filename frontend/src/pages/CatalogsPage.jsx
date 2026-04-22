import { AppstoreOutlined, BankOutlined, ShopOutlined, TagsOutlined } from '@ant-design/icons';
import { Card, Empty, Space, Tabs, Typography } from 'antd';
import { Navigate, useSearchParams } from 'react-router-dom';
import { useEffect, useMemo } from 'react';

import { useAuth } from '../auth/useAuth';
import ResourcePage from './ResourcePage';

const TAB_ITEMS = [
  {
    key: 'categories',
    label: 'Nhóm hàng',
    permission: 'categories.view',
    resourceKey: 'categories',
    icon: <TagsOutlined />,
  },
  {
    key: 'suppliers',
    label: 'Nhà cung cấp',
    permission: 'suppliers.view',
    resourceKey: 'suppliers',
    icon: <ShopOutlined />,
  },
  {
    key: 'customers',
    label: 'Khách hàng',
    permission: 'customers.view',
    resourceKey: 'customers',
    icon: <AppstoreOutlined />,
  },
  {
    key: 'bank-accounts',
    label: 'Tài khoản ngân hàng',
    permission: 'bank_accounts.view',
    resourceKey: 'bank_accounts',
    icon: <BankOutlined />,
  },
];

function CatalogsPage() {
  const { hasPermission } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const visibleTabs = useMemo(
    () => TAB_ITEMS.filter((item) => hasPermission(item.permission)),
    [hasPermission],
  );

  const activeTab = searchParams.get('tab');
  const fallbackTab = visibleTabs[0]?.key || null;
  const safeTab = visibleTabs.some((item) => item.key === activeTab) ? activeTab : fallbackTab;
  const currentTab = visibleTabs.find((item) => item.key === safeTab) || null;

  useEffect(() => {
    if (!fallbackTab || activeTab === safeTab) {
      return;
    }

    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('tab', safeTab);
    setSearchParams(nextParams, { replace: true });
  }, [activeTab, fallbackTab, safeTab, searchParams, setSearchParams]);

  if (!visibleTabs.length) {
    return <Navigate to="/forbidden" replace />;
  }

  return (
    <Space orientation="vertical" size={18} style={{ width: '100%' }}>
      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Space orientation="vertical" size={10} style={{ width: '100%' }}>
          <Typography.Text className="resource-eyebrow">
            Module 3 · Danh mục nền
          </Typography.Text>
          <Typography.Title level={2} className="page-title">
            Danh mục nền
          </Typography.Title>
          <Typography.Paragraph className="page-subtitle" style={{ marginBottom: 0 }}>
            Quản lý nhóm hàng, nhà cung cấp, khách hàng và tài khoản ngân hàng trên cùng
            một màn hình tab để thao tác nhanh, gọn và đúng theo quyền của từng vai trò.
          </Typography.Paragraph>
        </Space>
      </Card>

      <Card className="page-card" styles={{ body: { padding: 24 } }}>
        <Tabs
          activeKey={safeTab || undefined}
          onChange={(nextTab) => {
            const nextParams = new URLSearchParams(searchParams);
            nextParams.set('tab', nextTab);
            setSearchParams(nextParams, { replace: true });
          }}
          items={visibleTabs.map((item) => ({
            key: item.key,
            label: (
              <Space size={8}>
                {item.icon}
                <span>{item.label}</span>
              </Space>
            ),
            children: currentTab?.key === item.key ? (
              <ResourcePage resourceKey={item.resourceKey} />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Đang chuẩn bị dữ liệu..." />
            ),
          }))}
        />
      </Card>
    </Space>
  );
}

export default CatalogsPage;
