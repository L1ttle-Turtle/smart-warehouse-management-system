import { Alert, Card, Space, Table, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';

import api from '../api/client';

function RolesPage() {
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/roles')
      .then((response) => setRoles(response.data.items || []))
      .catch((requestError) => {
        setError(requestError.response?.data?.message || 'Không tải được ma trận quyền.');
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <Card className="page-card" styles={{ body: { padding: 28 } }}>
      <Typography.Title level={2} className="page-title">
        Ma trận vai trò và quyền
      </Typography.Title>
      <Typography.Paragraph className="page-subtitle">
        Màn hình này chỉ mở cho tài khoản có quyền <code>roles.view</code>. Bảng bên dưới thể hiện
        quyền gốc theo từng vai trò. Các quyền được ủy quyền riêng cho từng user sẽ được quản lý ở
        màn hình ủy quyền.
      </Typography.Paragraph>

      {error ? (
        <Alert
          type="error"
          showIcon
          message="Không tải được ma trận quyền"
          description={error}
          style={{ marginBottom: 20 }}
        />
      ) : null}

      <Table
        rowKey="id"
        loading={loading}
        pagination={false}
        dataSource={roles}
        columns={[
          {
            title: 'Vai trò',
            dataIndex: 'role_name',
            key: 'role_name',
          },
          {
            title: 'Mô tả',
            dataIndex: 'description',
            key: 'description',
            render: (value) => value || '-',
          },
          {
            title: 'Số user',
            dataIndex: 'user_count',
            key: 'user_count',
          },
          {
            title: 'Quyền gốc',
            dataIndex: 'base_permissions',
            key: 'base_permissions',
            render: (permissions) => (
              <Space wrap>
                {permissions.map((permission) => (
                  <Tag key={permission} color="blue">
                    {permission}
                  </Tag>
                ))}
              </Space>
            ),
          },
          {
            title: 'Quyền hiệu lực theo role',
            dataIndex: 'effective_permissions',
            key: 'effective_permissions',
            render: (permissions) => (
              <Space wrap>
                {permissions.map((permission) => (
                  <Tag key={permission} color="green">
                    {permission}
                  </Tag>
                ))}
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );
}

export default RolesPage;
