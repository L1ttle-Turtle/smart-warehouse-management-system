import { EnvironmentOutlined, HomeOutlined } from '@ant-design/icons';
import { Card, Empty, Space, Tabs, Typography } from 'antd';
import { Navigate, useSearchParams } from 'react-router-dom';
import { useEffect, useMemo } from 'react';

import { useAuth } from '../auth/useAuth';
import ResourcePage from './ResourcePage';

const TAB_ITEMS = [
  {
    key: 'warehouses',
    label: 'Kho',
    permission: 'warehouses.view',
    resourceKey: 'warehouses',
    icon: <HomeOutlined />,
  },
  {
    key: 'locations',
    label: 'Vị trí kho',
    permission: 'locations.view',
    resourceKey: 'locations',
    icon: <EnvironmentOutlined />,
  },
];

function WarehousesPage() {
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
            Module 5 · Kho bãi và vị trí lưu trữ
          </Typography.Text>
          <Typography.Title level={2} className="page-title">
            Quản lý kho bãi
          </Typography.Title>
          <Typography.Paragraph className="page-subtitle" style={{ marginBottom: 0 }}>
            Theo dõi danh sách kho và vị trí lưu trữ trên cùng một màn hình tab để quản lý
            nhanh, rõ ràng và sẵn sàng cho luồng tồn kho, nhập xuất, điều chuyển ở bước sau.
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
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="Đang chuẩn bị dữ liệu..."
              />
            ),
          }))}
        />
      </Card>
    </Space>
  );
}

export default WarehousesPage;
