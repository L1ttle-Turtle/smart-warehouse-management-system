import { Alert, Card, Col, Row, Space, Spin, Table, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';

import api from '../api/client';

function renderStatusTag(value) {
  const colorMap = {
    active: 'green',
    revoked: 'red',
    expired: 'orange',
    inactive: 'default',
  };
  return <Tag color={colorMap[value] || 'blue'}>{value || '-'}</Tag>;
}

function MetricCard({ label, value, helper }) {
  return (
    <Card className="page-card" styles={{ body: { padding: 24 } }}>
      <Typography.Text type="secondary">{label}</Typography.Text>
      <div className="metric-value">{value ?? 0}</div>
      {helper ? <Typography.Text type="secondary">{helper}</Typography.Text> : null}
    </Card>
  );
}

function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  useEffect(() => {
    const loadDashboard = async () => {
      setLoading(true);
      try {
        const response = await api.get('/dashboard/identity');
        setData(response.data);
      } catch (error) {
        message.error(error.response?.data?.message || 'Không tải được dashboard.');
      } finally {
        setLoading(false);
      }
    };

    loadDashboard();
  }, []);

  if (loading) {
    return (
      <div style={{ minHeight: '50vh', display: 'grid', placeItems: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!data) {
    return (
      <Alert
        type="error"
        showIcon
        message="Không có dữ liệu dashboard"
        description="Vui lòng tải lại trang hoặc kiểm tra kết nối tới backend."
      />
    );
  }

  return (
    <Space orientation="vertical" size={20} style={{ width: '100%' }}>
      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Typography.Title level={2} className="page-title">
          Dashboard cá nhân và nhân sự
        </Typography.Title>
        <Typography.Paragraph className="page-subtitle">
          Trang này tập trung vào người đang đăng nhập: thông tin phiên, hồ sơ nhân sự,
          quyền đang có, tình trạng ủy quyền và hoạt động gần đây.
        </Typography.Paragraph>
      </Card>

      {data.profile.must_change_password ? (
        <Alert
          type="warning"
          showIcon
          message="Bạn đang ở trạng thái bắt buộc đổi mật khẩu"
          description="Hãy vào trang Hồ sơ cá nhân để đổi mật khẩu rồi tiếp tục sử dụng hệ thống."
        />
      ) : null}

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <MetricCard label="Người dùng hiện tại" value={data.profile.full_name || '-'} helper={data.profile.role || '-'} />
        </Col>
        <Col xs={24} md={8}>
          <MetricCard label="Tổng quyền đang có" value={data.permission_summary.total_permissions} helper="Bao gồm quyền vai trò và quyền được ủy quyền" />
        </Col>
        <Col xs={24} md={8}>
          <MetricCard label="Lần đăng nhập gần nhất" value={data.profile.last_login_at ? new Date(data.profile.last_login_at).toLocaleString('vi-VN') : '-'} />
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card className="page-card" styles={{ body: { padding: 28 } }}>
            <Typography.Title level={4} style={{ marginTop: 0 }}>
              Hồ sơ nhân sự gắn với tài khoản
            </Typography.Title>
            <Space orientation="vertical" size={12} style={{ width: '100%' }}>
              <Typography.Text>Mã nhân sự: <strong>{data.employee.employee_code || 'Chưa liên kết'}</strong></Typography.Text>
              <Typography.Text>Phòng ban: <strong>{data.employee.department || 'Chưa cập nhật'}</strong></Typography.Text>
              <Typography.Text>Chức vụ: <strong>{data.employee.position || 'Chưa cập nhật'}</strong></Typography.Text>
              <Typography.Text>Trạng thái: {renderStatusTag(data.employee.status || 'inactive')}</Typography.Text>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card className="page-card" styles={{ body: { padding: 28 } }}>
            <Typography.Title level={4} style={{ marginTop: 0 }}>
              Tóm tắt ủy quyền
            </Typography.Title>
            <Row gutter={[12, 12]}>
              <Col span={8}>
                <MetricCard label="Nhận hiệu lực" value={data.delegation_summary.active_received} />
              </Col>
              <Col span={8}>
                <MetricCard label="Đã cấp hiệu lực" value={data.delegation_summary.active_granted} />
              </Col>
              <Col span={8}>
                <MetricCard label="Sắp hết hạn" value={data.delegation_summary.expiring_soon} />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {data.management_summary ? (
        <Card className="page-card" styles={{ body: { padding: 28 } }}>
          <Typography.Title level={4} style={{ marginTop: 0 }}>
            Tóm tắt quản trị người dùng - nhân sự
          </Typography.Title>
          <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              <MetricCard label="Tổng tài khoản" value={data.management_summary.total_users} />
            </Col>
            <Col xs={24} md={8}>
              <MetricCard label="Tổng nhân sự" value={data.management_summary.total_employees} />
            </Col>
            <Col xs={24} md={8}>
              <MetricCard label="Đang chờ đổi mật khẩu" value={data.management_summary.must_change_password_users} />
            </Col>
          </Row>
        </Card>
      ) : null}

      {data.audit_summary ? (
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <MetricCard label="Tổng bản ghi audit" value={data.audit_summary.total_logs} />
          </Col>
          <Col xs={24} md={12}>
            <MetricCard label="Đăng nhập thành công hôm nay" value={data.audit_summary.today_logins} />
          </Col>
        </Row>
      ) : null}

      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Typography.Title level={4} style={{ marginTop: 0 }}>
          Hoạt động gần đây của tài khoản
        </Typography.Title>
        <Table
          rowKey="id"
          pagination={false}
          dataSource={data.recent_activity}
          locale={{ emptyText: 'Chưa có hoạt động nào để hiển thị.' }}
          columns={[
            {
              title: 'Thời điểm',
              dataIndex: 'created_at',
              key: 'created_at',
              render: (value) => (value ? new Date(value).toLocaleString('vi-VN') : '-'),
            },
            {
              title: 'Hành động',
              dataIndex: 'action',
              key: 'action',
              render: (value) => <Tag color="blue">{value}</Tag>,
            },
            {
              title: 'Đối tượng',
              dataIndex: 'entity_label',
              key: 'entity_label',
              render: (value) => value || '-',
            },
            {
              title: 'Mô tả',
              dataIndex: 'description',
              key: 'description',
            },
          ]}
        />
      </Card>
    </Space>
  );
}

export default DashboardPage;
