import { Button, Card, Col, Form, Input, Row, Space, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';

import { useAuth } from '../auth/useAuth';

function ProfilePage() {
  const { user, updateProfile } = useAuth();
  const [profileForm] = Form.useForm();
  const [passwordForm] = Form.useForm();
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  useEffect(() => {
    profileForm.setFieldsValue({
      email: user?.email || '',
      phone: user?.phone || '',
    });
  }, [profileForm, user]);

  return (
    <Space direction="vertical" size={20} style={{ width: '100%' }}>
      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Typography.Title level={2} className="page-title">
          Hồ sơ cá nhân
        </Typography.Title>
        <Typography.Paragraph className="page-subtitle">
          Trang này cho phép bạn tự cập nhật thông tin liên hệ và đổi mật khẩu mà không đụng sang
          các module quản trị người dùng phía sau.
        </Typography.Paragraph>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card className="page-card" styles={{ body: { padding: 24 } }}>
            <Typography.Text type="secondary">Họ tên</Typography.Text>
            <div className="metric-value">{user?.full_name || '-'}</div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="page-card" styles={{ body: { padding: 24 } }}>
            <Typography.Text type="secondary">Username</Typography.Text>
            <div className="metric-value">{user?.username || '-'}</div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="page-card" styles={{ body: { padding: 24 } }}>
            <Typography.Text type="secondary">Vai trò</Typography.Text>
            <div style={{ marginTop: 12 }}>
              <Tag color="cyan">{user?.role || '-'}</Tag>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card className="page-card" styles={{ body: { padding: 28 } }}>
            <Typography.Title level={4} style={{ marginTop: 0 }}>
              Cập nhật thông tin liên hệ
            </Typography.Title>
            <Typography.Paragraph type="secondary">
              Bạn có thể chỉnh lại email và số điện thoại đang dùng cho tài khoản hiện tại.
            </Typography.Paragraph>

            <Form
              form={profileForm}
              layout="vertical"
              onFinish={async (values) => {
                setSavingProfile(true);
                try {
                  await updateProfile(values);
                  message.success('Đã cập nhật thông tin cá nhân.');
                } catch (error) {
                  message.error(error.response?.data?.message || 'Không thể cập nhật hồ sơ.');
                } finally {
                  setSavingProfile(false);
                }
              }}
            >
              <Form.Item
                name="email"
                label="Email"
                rules={[
                  { required: true, message: 'Nhập email' },
                  { type: 'email', message: 'Email không hợp lệ' },
                ]}
              >
                <Input size="large" />
              </Form.Item>
              <Form.Item
                name="phone"
                label="Số điện thoại"
                rules={[{ max: 20, message: 'Số điện thoại quá dài' }]}
              >
                <Input size="large" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={savingProfile}>
                Lưu thông tin
              </Button>
            </Form>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card className="page-card" styles={{ body: { padding: 28 } }}>
            <Typography.Title level={4} style={{ marginTop: 0 }}>
              Đổi mật khẩu
            </Typography.Title>
            <Typography.Paragraph type="secondary">
              Để an toàn, bạn cần nhập mật khẩu hiện tại trước khi đặt mật khẩu mới.
            </Typography.Paragraph>

            <Form
              form={passwordForm}
              layout="vertical"
              onFinish={async (values) => {
                setSavingPassword(true);
                try {
                  await updateProfile({
                    current_password: values.current_password,
                    new_password: values.new_password,
                  });
                  passwordForm.resetFields();
                  message.success('Đổi mật khẩu thành công.');
                } catch (error) {
                  message.error(error.response?.data?.message || 'Không thể đổi mật khẩu.');
                } finally {
                  setSavingPassword(false);
                }
              }}
            >
              <Form.Item
                name="current_password"
                label="Mật khẩu hiện tại"
                rules={[{ required: true, message: 'Nhập mật khẩu hiện tại' }]}
              >
                <Input.Password size="large" />
              </Form.Item>
              <Form.Item
                name="new_password"
                label="Mật khẩu mới"
                rules={[
                  { required: true, message: 'Nhập mật khẩu mới' },
                  { min: 6, message: 'Mật khẩu mới tối thiểu 6 ký tự' },
                ]}
              >
                <Input.Password size="large" />
              </Form.Item>
              <Form.Item
                name="confirm_password"
                label="Nhập lại mật khẩu mới"
                dependencies={['new_password']}
                rules={[
                  { required: true, message: 'Nhập lại mật khẩu mới' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('new_password') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('Mật khẩu nhập lại chưa khớp.'));
                    },
                  }),
                ]}
              >
                <Input.Password size="large" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={savingPassword}>
                Đổi mật khẩu
              </Button>
            </Form>
          </Card>
        </Col>
      </Row>
    </Space>
  );
}

export default ProfilePage;
