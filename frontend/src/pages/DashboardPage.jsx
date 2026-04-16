import { Card, Col, Divider, List, Row, Space, Tag, Typography } from 'antd';

import { useAuth } from '../auth/useAuth';

function DashboardPage() {
  const { user } = useAuth();

  return (
    <Space direction="vertical" size={20} style={{ width: '100%' }}>
      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Typography.Title level={2} className="page-title">
          Nền tảng quản trị đang sẵn sàng vận hành
        </Typography.Title>
        <Typography.Paragraph className="page-subtitle">
          Trang này dùng để kiểm tra thông tin phiên đăng nhập, vai trò hiện tại, quyền đang có và các quyền được cấp riêng cho tài khoản.
        </Typography.Paragraph>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card className="page-card" styles={{ body: { padding: 24 } }}>
            <Typography.Text type="secondary">Người dùng hiện tại</Typography.Text>
            <div className="metric-value">{user?.full_name || '-'}</div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="page-card" styles={{ body: { padding: 24 } }}>
            <Typography.Text type="secondary">Vai trò</Typography.Text>
            <div className="metric-value">{user?.role || '-'}</div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="page-card" styles={{ body: { padding: 24 } }}>
            <Typography.Text type="secondary">Số quyền đang có</Typography.Text>
            <div className="metric-value">{user?.permissions?.length || 0}</div>
          </Card>
        </Col>
      </Row>

      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Typography.Title level={4} style={{ marginTop: 0 }}>
          Vai trò và quyền của tài khoản
        </Typography.Title>
        <Divider />
        <List
          dataSource={user?.permissions || []}
          locale={{ emptyText: 'Tài khoản này chưa có quyền nào.' }}
          renderItem={(permission) => (
            <List.Item>
              <Tag color="green">{permission}</Tag>
            </List.Item>
          )}
        />
      </Card>

      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Typography.Title level={4} style={{ marginTop: 0 }}>
          Quyền được ủy quyền và nguồn cấp
        </Typography.Title>
        <Divider />
        <List
          dataSource={user?.delegated_permission_sources || []}
          locale={{ emptyText: 'Hiện chưa có quyền nào được ủy quyền thêm trực tiếp cho tài khoản của bạn.' }}
          renderItem={(item) => (
            <List.Item>
              <Space direction="vertical" size={2}>
                <Tag color="gold">{item.permission_name}</Tag>
                <Typography.Text type="secondary">
                  Được cấp bởi {item.grantor_user_name} ({item.grantor_role_name})
                </Typography.Text>
              </Space>
            </List.Item>
          )}
        />
      </Card>
    </Space>
  );
}

export default DashboardPage;
